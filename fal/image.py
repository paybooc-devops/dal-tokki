import os
from dotenv import load_dotenv
import asyncio
import fal_client
import random

load_dotenv()
FAL_KEY = os.getenv("FAL_KEY")
HOST_ADDRESS = os.getenv("HOST_ADDRESS")

if not FAL_KEY:
    raise RuntimeError("FAL_KEY가 설정되어 있지 않습니다. .env에 FAL_KEY=...를 추가하세요.")

async def submit(job_id: str, style="3D"):
    cloth_style = [
        "The character should be **unclothed**", 
        "The character should be wearing a **overalls**", 
        "The character should be wearing a **korean hanbok**"
        ]
    cloth_style = random.choice(cloth_style)
    if style == "3D":
        prompt = f"""Transform the uploaded sketch into a single 3D rabbit character in a modern animated movie style.  
- The final image must be in a 1:1 ratio with a pure white background.  
- The rabbit should always be shown as a full-body character, even if only the face is drawn in the sketch.  
- Faithfully preserve the sketch’s unique features but refine them into a cute and appealing design.  
- Eyebrows should only be drawn if they are clearly present in the sketch; if not, do not add them.  
- The style should be soft, rounded, and polished, with smooth fur-like textures and vibrant colors.  
- The result should look like a professional 3D animated character: charming, lively, and aesthetically balanced.
- The original drawing's unique linework, the cat's distinctive pose and facial expression, and its overall endearing quality must be faithfully preserved. Maintain the original composition as much as possible
- The essence and 'DNA' of the original cat drawing are paramount and should shine through the new style.
- {cloth_style}"""
        prompt = prompt.format(cloth_style=cloth_style)
    else:
        prompt = """Based on the provided sketch reference, render a single rabbit (bunny) that faithfully preserves the sketch’s unique features — exact pose, proportions, linework, facial expression and distinctive markings — while enhancing into a highly detailed illustration; maintain the original strokes and stylization, crisp clean line-art with soft painterly fur shading and subtle color matching the sketch, high resolution, centered composition, transparent background, alpha channel"""
    handler = await fal_client.submit_async(
        #"fal-ai/stable-diffusion-v3-medium/image-to-image",
        "fal-ai/nano-banana/edit",
        arguments={
            "image_urls": [f"{HOST_ADDRESS}/static/image/origin/{job_id}.png"],
            "prompt": prompt,
            #"negative_prompt": "ugly, deformed, bad anatomy, disfigured, poor quality, low resolution, blurry, text, watermark, (not a rabbit), multiple rabbits, realistic"
            "num_images": 1,
            "output_format": "png"
        },
        webhook_url=f"{HOST_ADDRESS}/hook/v1/image-jobs/{job_id}",
    )

    request_id = handler.request_id
    print(request_id)

if __name__ == "__main__":
    asyncio.run(submit('9d30a2bc-3f56-4983-aff2-8d87f4761f3e'))