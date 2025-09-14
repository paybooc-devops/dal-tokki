import os
from dotenv import load_dotenv
import asyncio
import fal_client
from typing import Optional

load_dotenv()
FAL_KEY = os.getenv("FAL_KEY")
HOST_ADDRESS = os.getenv("HOST_ADDRESS")

async def submit(job_id: str, source_image_url: Optional[str] = None):
    image_url = source_image_url or f"{HOST_ADDRESS}/static/image/new/{job_id}.png"
    handler = await fal_client.submit_async(
        "fal-ai/bria/background/remove",
        arguments={
            "image_url": image_url
        },
        webhook_url=f"{HOST_ADDRESS}/hook/v1/transparent-jobs/{job_id}",
    )

    request_id = handler.request_id
    print(request_id)

if __name__ == "__main__":
    asyncio.run(submit('63fa03ec-4cdb-4806-aee0-a092db1795aa'))