import os
from dotenv import load_dotenv
import asyncio
import fal_client

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")
HOST_ADDRESS = os.getenv("HOST_ADDRESS")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env에 OPENAI_API_KEY=...를 추가하세요.")

if not FAL_KEY:
    raise RuntimeError("FAL_KEY가 설정되어 있지 않습니다. .env에 FAL_KEY=...를 추가하세요.")

async def submit(job_id: str):
    handler = await fal_client.submit_async(
        "fal-ai/stable-diffusion-v3-medium/image-to-image",
        arguments={
            "image_url": f"{HOST_ADDRESS}/static/image/origin/{job_id}.png",
            "prompt": "A cute rabbit, line art, delicate drawing, elegant lines, beautiful, clean style, high quality, soft shadows, white background, transparent background",
            "negative_prompt": "ugly, deformed, bad anatomy, disfigured, poor quality, low resolution, blurry, text, watermark, (not a rabbit), multiple rabbits, realistic"
        },
        webhook_url=f"{HOST_ADDRESS}/hook/v1/image-jobs/{job_id}",
    )

    request_id = handler.request_id
    print(request_id)

if __name__ == "__main__":
    asyncio.run(submit('9d30a2bc-3f56-4983-aff2-8d87f4761f3e'))