import os
from dotenv import load_dotenv
import asyncio
import fal_client
from typing import Optional
import random

load_dotenv()
FAL_KEY = os.getenv("FAL_KEY")
HOST_ADDRESS = os.getenv("HOST_ADDRESS")

if not FAL_KEY:
    raise RuntimeError("FAL_KEY가 설정되어 있지 않습니다. .env에 FAL_KEY=...를 추가하세요.")

def generate_prompt() -> str:
    ACTIONS = [
        "gently wiggles both ears",
        "twitches its nose naturally",
        "slowly blinks",
        "rubs its face lightly with front paws (like grooming)",
        "tilts its head slightly to one side",
        "turns its head left and right to look around",
        "shakes its body briefly to fluff its fur",
        "taps the ground softly with a hind leg",
        "sits down and then rises slowly",
        "bows forward a little, then returns upright",
        "grooms its fur with short, realistic motions",
        "makes a tiny hop and lands in the same spot",
        "takes a short step forward and stops",
        "raises both ears alertly, as if listening",
        "slightly moves its tail up and down",
        "sits on hind legs for a moment with front paws lifted",
        "lowers its head as if nibbling grass (no grass added)",
        "raises its head to look upward briefly",
        "leans to the side, as if getting comfortable",
        "moves only one ear in reaction"
    ]

    BASE_TEMPLATE = (
        "Generate a natural and stable 5-second video using the provided rabbit image only. "
        "Do not add any new objects, characters, or overlays. No surreal or distorted effects. "
        "Keep the scene clean and realistic. Preserve the rabbit as the single subject. "
        "Background must be a plain white screen with nothing else."
        "Actions: {actions}. Ensure duration is exactly 5 seconds."
    )
    # INSERT_YOUR_CODE
    action = random.choice(ACTIONS)
    actions_phrase = f"The rabbit {action}."
    return BASE_TEMPLATE.format(actions=actions_phrase)

async def submit(job_id: str, video_url: Optional[str] = None):
    # Default endpoints
    image_url = f"{HOST_ADDRESS}/static/image/transparent/{job_id}.png"
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
            #"prompt": "A cute and beautiful rabbit from a line drawing, animated to be hopping and nibbling on a carrot. The lines are delicate and elegant, with a smooth, fluid motion. The video should have a peaceful and charming atmosphere.",
            #"prompt": "Photorealistic 5-second animated clip of the rabbit from the reference photo — preserve its exact fur color, unique markings, eye color, ear shape, body proportions, and fur texture; maintain the original lighting and background. Action: the rabbit, seated, smoothly lifts its right front paw and waves it once gently, then returns to a relaxed resting pose (clear, simple motion completed within ~5 seconds). Medium close-up framing showing the full rabbit body, static camera, 30 fps, smooth natural animation with subtle breathing and realistic fur movement. No other animals, people, objects, or added props; do not alter the rabbit’s distinctive features",
            "prompt": generate_prompt(),
            "image_url": image_url
        },
        webhook_url=webhook,
    )

    request_id = handler.request_id
    print(request_id)
    return request_id

if __name__ == "__main__":
    asyncio.run(submit('7ef5156e-008c-43d0-be4c-5971da1a477f'))
