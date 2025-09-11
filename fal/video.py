import os
from dotenv import load_dotenv
import asyncio
import fal_client
from typing import Optional

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")
HOST_ADDRESS = os.getenv("HOST_ADDRESS")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env에 OPENAI_API_KEY=...를 추가하세요.")

if not FAL_KEY:
    raise RuntimeError("FAL_KEY가 설정되어 있지 않습니다. .env에 FAL_KEY=...를 추가하세요.")

async def submit(job_id: str, video_url: Optional[str] = None):
    # Default endpoints
    image_url = f"{HOST_ADDRESS}/static/image/origin/{job_id}.png"
    webhook = f"{HOST_ADDRESS}/hook/v1/video-jobs/{job_id}"

    # If a URL is provided:
    # - If it looks like an image URL, use it as image_url
    # - Otherwise, treat it as a webhook override
    if isinstance(video_url, str) and video_url:
        lower_url = video_url.lower()
        if lower_url.startswith("http") and (
            lower_url.endswith(".png")
            or lower_url.endswith(".jpg")
            or lower_url.endswith(".jpeg")
            or lower_url.endswith(".webp")
            or lower_url.endswith(".gif")
            or lower_url.endswith(".bmp")
        ):
            image_url = video_url
        elif lower_url.startswith("http"):
            webhook = video_url

    handler = await fal_client.submit_async(
        "fal-ai/kling-video/v2.1/standard/image-to-video",
        arguments={
            "prompt": "A cute and beautiful rabbit from a line drawing, animated to be hopping and nibbling on a carrot. The lines are delicate and elegant, with a smooth, fluid motion. The video should have a peaceful and charming atmosphere.",
            "image_url": image_url
        },
        webhook_url=webhook,
    )

    request_id = handler.request_id
    print(request_id)
    return request_id

if __name__ == "__main__":
    asyncio.run(submit('7ef5156e-008c-43d0-be4c-5971da1a477f'))
