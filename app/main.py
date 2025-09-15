from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi import Body, Query, Header
from fastapi import BackgroundTasks
from uuid import uuid4
from pathlib import Path
import asyncio
import base64
from typing import Any, Dict, Optional
import logging
import json
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from dotenv import load_dotenv
import os
import sys
load_dotenv()
HOST_ADDRESS = os.getenv("HOST_ADDRESS")

# Ensure project root is on sys.path when running as a script
_current_dir = Path(__file__).resolve().parent
_project_root = str(_current_dir.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.schemas import (
    CreateVideoJobRequest,
    CreateVideoJobResponse,
    ErrorResponse,
    GetVideoJobStatusResponse,
)
from fal.video import submit as submit_video_job
from fal.image import submit as submit_image_job
from fal.transparent import submit as submit_transparent_job


app = FastAPI(title="Tokki Video Jobs API", version="0.1.0")

# Mount static files to serve generated assets under /static
_data_root = Path(__file__).resolve().parent / "data"
_data_root.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_data_root)), name="static")

# Logger for webhook and API events (prints to Uvicorn console)
logger = logging.getLogger("uvicorn.error")

# Global header verification middleware for TOKKEY
TOKKEY_SECRET = os.getenv("TOKKEY")
_EXEMPT_PATH_PREFIXES = ("/static", "/docs", "/hook", "/redoc", "/openapi")


@app.middleware("http")
async def require_tokkey_header(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(prefix) for prefix in _EXEMPT_PATH_PREFIXES):
        return await call_next(request)

    if not TOKKEY_SECRET:
        return JSONResponse(
            status_code=500,
            content={"code": "CONFIG_ERROR", "message": "서버 설정 오류: TOKKEY 미설정"},
        )

    incoming = request.headers.get("TOKKEY")
    if incoming != TOKKEY_SECRET:
        return JSONResponse(
            status_code=401,
            content={"code": "UNAUTHORIZED", "message": "유효하지 않은 접근"},
        )

    return await call_next(request)
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
        logger.info("File downloaded: url=%s -> %s", url, str(output_path))
    except (HTTPError, URLError) as e:
        logger.error("File download failed (network): url=%s err=%s", url, str(e))
    except Exception as e:
        logger.error("File download failed: url=%s err=%s", url, str(e))


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
async def create_video_job(payload: CreateVideoJobRequest) -> CreateVideoJobResponse:
    job_id = str(uuid4())

    # Build output path: app/data/image/origin/<uuid>.png
    base_dir = Path(__file__).resolve().parent / "data" / "image" / "origin"
    output_path = base_dir / f"{job_id}.png"

    # Save the incoming data URI as PNG
    save_data_uri_png(payload.image_data_uri, output_path)

    # Trigger image generation for this job_id in background (within running event loop)
    asyncio.create_task(submit_image_job(job_id))

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
    base_dir = Path(__file__).resolve().parent / "data"

    # Precompute URLs
    video_url = f"{HOST_ADDRESS}/static/video/result/{job_id}.mp4"
    gen_url = f"{HOST_ADDRESS}/static/image/transparent/{job_id}.png"
    origin_url = f"{HOST_ADDRESS}/static/image/origin/{job_id}.png"

    # 1) Video result → finish (세 URL 모두 제공)
    video_path = base_dir / "video" / "result" / f"{job_id}.mp4"
    if video_path.exists():
        return GetVideoJobStatusResponse(
            status="finish",
            video_url=video_url,
            gen_url=gen_url,
            origin_url=origin_url,
        )

    # 2) Transparent image exists → processing-3 (video_url만 없음)
    transparent_path = base_dir / "image" / "transparent" / f"{job_id}.png"
    if transparent_path.exists():
        return GetVideoJobStatusResponse(
            status="processing-3",
            video_url=None,
            gen_url=gen_url,
            origin_url=origin_url,
        )

    # 3) Origin image exists → processing-2 (origin_url만 있음)
    origin_path = base_dir / "image" / "origin" / f"{job_id}.png"
    if origin_path.exists():
        return GetVideoJobStatusResponse(
            status="processing-2",
            video_url=None,
            gen_url=None,
            origin_url=origin_url,
        )

    # 4) Default → processing-1 (모두 없음)
    return GetVideoJobStatusResponse(
        status="processing-1",
        video_url=None,
        gen_url=None,
        origin_url=None,
    )


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


@app.post("/hook/v1/image-jobs/{job_id}")
async def webhook_image_post(
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

    try:
        body_for_log = json.dumps(body, ensure_ascii=False)
    except Exception:
        body_for_log = str(body)

    client = request.client.host if request.client else None
    logger.info(
        "Image Webhook POST job_id=%s client=%s headers=%s query=%s body=%s",
        job_id,
        client,
        json.dumps(headers, ensure_ascii=False),
        json.dumps(query_params, ensure_ascii=False),
        body_for_log,
    )

    # Try scheduling image download if payload contains image URL
    scheduled_to: Optional[str] = None
    try:
        if isinstance(body, dict):
            payload = body.get("payload") or {}
            image_url: Optional[str] = None
            content_type: Optional[str] = None
            if isinstance(payload, dict):
                images = payload.get("images")
                if isinstance(images, list) and images:
                    first = images[0] or {}
                    if isinstance(first, dict):
                        image_url = first.get("url")
                        content_type = first.get("content_type")
                if not image_url:
                    image_obj = payload.get("image") or {}
                    if isinstance(image_obj, dict):
                        image_url = image_obj.get("url")
                        content_type = image_obj.get("content_type") or content_type

            if isinstance(image_url, str) and image_url.startswith("http"):
                # Determine extension from URL or content-type
                ext: Optional[str] = None
                try:
                    path = urlparse(image_url).path
                    if "." in path:
                        ext = path.rsplit(".", 1)[1].lower()
                except Exception:
                    ext = None
                allowed = {"png", "jpg", "jpeg", "webp"}
                if ext not in allowed:
                    if content_type == "image/jpeg":
                        ext = "jpg"
                    elif content_type == "image/webp":
                        ext = "webp"
                    else:
                        ext = "png"

                img_dir = Path(__file__).resolve().parent / "data" / "image" / "new"
                img_path = img_dir / f"{job_id}.{ext}"
                background_tasks.add_task(download_file, image_url, img_path)
                scheduled_to = str(img_path)

                # Trigger transparent background processing using the external URL immediately
                try:
                    asyncio.create_task(submit_transparent_job(job_id, source_image_url=image_url))
                except Exception as e:
                    logger.error("Scheduling transparent submit failed job_id=%s err=%s", job_id, str(e))
    except Exception as e:
        logger.error("Image webhook processing error job_id=%s err=%s", job_id, str(e))

    return {
        "job_id": job_id,
        "method": "POST",
        "path": str(request.url.path),
        "headers": headers,
        "query": query_params,
        "body": body,
        "scheduled_download_to": scheduled_to,
    }


@app.post("/hook/v1/transparent-jobs/{job_id}")
async def webhook_transparent_post(
    job_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    headers: Dict[str, str] = {k: v for k, v in request.headers.items()}
    query_params: Dict[str, str] = dict(request.query_params)
    try:
        body: Optional[Any] = await request.json()
    except Exception:
        body_bytes = await request.body()
        body = body_bytes.decode("utf-8", errors="replace") if body_bytes else None

    try:
        body_for_log = json.dumps(body, ensure_ascii=False)
    except Exception:
        body_for_log = str(body)

    client = request.client.host if request.client else None
    logger.info(
        "Transparent Webhook POST job_id=%s client=%s headers=%s query=%s body=%s",
        job_id,
        client,
        json.dumps(headers, ensure_ascii=False),
        json.dumps(query_params, ensure_ascii=False),
        body_for_log,
    )

    scheduled_to: Optional[str] = None
    try:
        image_url: Optional[str] = None
        if isinstance(body, dict):
            payload = body.get("payload") or {}
            if isinstance(payload, dict):
                # Common response shape: payload.image.url or payload.images[0].url
                image_obj = payload.get("image") or {}
                if isinstance(image_obj, dict):
                    image_url = image_obj.get("url")
                if not image_url:
                    images = payload.get("images")
                    if isinstance(images, list) and images:
                        first = images[0] or {}
                        if isinstance(first, dict):
                            image_url = first.get("url")

        if isinstance(image_url, str) and image_url.startswith("http"):
            img_dir = Path(__file__).resolve().parent / "data" / "image" / "transparent"
            img_path = img_dir / f"{job_id}.png"
            background_tasks.add_task(download_file, image_url, img_path)
            scheduled_to = str(img_path)

            # After transparent image is saved (scheduled), trigger video generation using this transparent URL
            try:
                asyncio.create_task(submit_video_job(job_id, video_url=image_url))
            except Exception as e:
                logger.error("Scheduling video submit (after transparent) failed job_id=%s err=%s", job_id, str(e))
    except Exception as e:
        logger.error("Transparent webhook processing error job_id=%s err=%s", job_id, str(e))

    return {
        "job_id": job_id,
        "method": "POST",
        "path": str(request.url.path),
        "headers": headers,
        "query": query_params,
        "body": body,
        "scheduled_download_to": scheduled_to,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


