from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi import Body, Query, Header
from fastapi import BackgroundTasks
from uuid import uuid4
from pathlib import Path
import base64
from typing import Any, Dict, Optional
import logging
import json
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from dotenv import load_dotenv
import os
load_dotenv()
HOST_ADDRESS = os.getenv("HOST_ADDRESS")

from .schemas import (
    CreateVideoJobRequest,
    CreateVideoJobResponse,
    ErrorResponse,
    GetVideoJobStatusResponse,
)


app = FastAPI(title="Tokki Video Jobs API", version="0.1.0")

# Mount static files to serve generated assets under /static
_data_root = Path(__file__).resolve().parent / "data"
_data_root.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_data_root)), name="static")

# Logger for webhook and API events (prints to Uvicorn console)
logger = logging.getLogger("uvicorn.error")
def save_data_uri_png(data_uri: str, output_path: Path) -> None:
    """Save a base64 data URI image to a PNG file at the given path.

    The function assumes the data URI contains base64-encoded image data.
    It ensures the parent directory exists before writing the file.
    """

    try:
        # Expecting format like: data:image/png;base64,<BASE64_DATA>
        if ";base64," not in data_uri:
            raise HTTPException(status_code=422, detail="유효하지 않은 Data URI 형식입니다.")
        base64_part = data_uri.split(";base64,", 1)[1]
        image_bytes = base64.b64decode(base64_part)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
    except HTTPException:
        # Re-raise HTTPException as-is to preserve status code
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="이미지 저장 중 오류가 발생했습니다.")


def download_file(url: str, output_path: Path, *, chunk_size: int = 1 << 15) -> None:
    """Download a file from URL to output_path.

    Runs in background for webhook processing. Logs errors instead of raising.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(url) as resp, open(output_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        logger.info("Video downloaded: url=%s -> %s", url, str(output_path))
    except (HTTPError, URLError) as e:
        logger.error("Video download failed (network): url=%s err=%s", url, str(e))
    except Exception as e:
        logger.error("Video download failed: url=%s err=%s", url, str(e))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": "요청 값이 유효하지 않습니다."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "알 수 없는 오류가 발생했습니다."},
    )


@app.post(
    "/api/v1/video-jobs",
    response_model=CreateVideoJobResponse,
    status_code=202,
    responses={
        422: {"model": ErrorResponse, "description": "유효성 검사 실패"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"},
    },
)
def create_video_job(payload: CreateVideoJobRequest) -> CreateVideoJobResponse:
    job_id = str(uuid4())

    # Build output path: app/data/image/origin/<uuid>.png
    base_dir = Path(__file__).resolve().parent / "data" / "image" / "origin"
    output_path = base_dir / f"{job_id}.png"

    # Save the incoming data URI as PNG
    save_data_uri_png(payload.image_data_uri, output_path)

    return CreateVideoJobResponse(job_id=job_id)


@app.get(
    "/api/v1/video-jobs/{job_id}",
    response_model=GetVideoJobStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "존재하지 않는 작업"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"},
    },
)
def get_video_job(job_id: str) -> GetVideoJobStatusResponse:
    # Finished when result video exists
    video_dir = Path(__file__).resolve().parent / "data" / "video" / "result"
    video_path = video_dir / f"{job_id}.mp4"

    if video_path.exists():
        url = f"{HOST_ADDRESS}/static/video/result/{job_id}.mp4"
        return GetVideoJobStatusResponse(status="finish", url=url)

    return GetVideoJobStatusResponse(status="processing", url=None)


@app.post("/hook/v1/video-jobs/{job_id}")
async def webhook_post(
    job_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    headers: Dict[str, str] = {k: v for k, v in request.headers.items()}
    query_params: Dict[str, str] = dict(request.query_params)
    try:
        body: Optional[Any] = await request.json()
    except Exception:
        # Fallback to raw body if not JSON
        body_bytes = await request.body()
        body = body_bytes.decode("utf-8", errors="replace") if body_bytes else None

    # Prepare body for logging (pretty JSON when possible)
    try:
        body_for_log = json.dumps(body, ensure_ascii=False)
    except Exception:
        body_for_log = str(body)

    client = request.client.host if request.client else None
    logger.info(
        "Webhook POST job_id=%s client=%s headers=%s query=%s body=%s",
        job_id,
        client,
        json.dumps(headers, ensure_ascii=False),
        json.dumps(query_params, ensure_ascii=False),
        body_for_log,
    )

    # Process payload: download result video if present
    saved_to: Optional[str] = None
    try:
        if isinstance(body, dict):
            payload = body.get("payload") or {}
            if isinstance(payload, dict):
                video_info = payload.get("video") or {}
                if isinstance(video_info, dict):
                    video_url = video_info.get("url")
                    if isinstance(video_url, str) and video_url.startswith("http"):
                        video_dir = Path(__file__).resolve().parent / "data" / "video" / "result"
                        video_path = video_dir / f"{job_id}.mp4"
                        background_tasks.add_task(download_file, video_url, video_path)
                        saved_to = str(video_path)
    except Exception as e:
        logger.error("Webhook processing error job_id=%s err=%s", job_id, str(e))

    return {
        "job_id": job_id,
        "method": "POST",
        "path": str(request.url.path),
        "headers": headers,
        "query": query_params,
        "body": body,
        "scheduled_download_to": saved_to,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


