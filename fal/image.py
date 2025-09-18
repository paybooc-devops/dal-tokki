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
    if style == "3D":
        prompt = f"""Based on the provided sketch, render a 3D rabbit character with fully drawn limbs (arms and legs), keeping the pose and proportions inspired by the sketch.
Preserve the sketch’s charm and gesture while refining details into a polished, high-quality 3D animated movie style.
Proportions
2.5–3 heads tall, balanced body.
Not an oversized head.
Slightly longer torso and legs for natural proportions.
Face & Expression
Soft, plush, cushion-like fur texture.
Natural, rabbit-like features.
Large almond-shaped eyes with depth, natural highlights, and expressive charm (not plain round dots).
Softly rounded cheeks, but natural (not overly puffy).
Subtle plump lips for gentle cuteness.
Gentle baby-like charm, slightly youthful.
Style & Rendering
Plush, cushion-like texture, softly huggable like a stuffed animal.
Polished 3D animated movie style: soft, rounded, clean, and expressive.
Highly detailed fur shading and realistic lighting for depth.
White background, centered composition, high resolution, no shadows.
Clothing (Hanbok Variations)
Dress the rabbit in a traditional Korean hanbok that fits naturally and looks elegant and cute.
Hanbok should use a pastel-toned palette (pink, sky blue, lavender, mint, or beige).
Include details like floral patterns, saekdong (striped sleeves), or small accessories (jokduri, jobawi, norigae).
Balance 50:50 ratio across the full set of outputs for male and female hanbok (not within a single image).
Female hanbok: pastel flower-patterned chima + jeogori, pastel saekdong hanbok, elegant accessories.
Male hanbok: pastel-toned with baji (pants), do-po style with belt, saekdong-sleeved jeogori, accessories like gat, hogeon, or belt.
Male hanbok must always include baji (pants) and no chima (skirts).
Props
Include at most one Chuseok-themed prop only if it exists in the sketch, otherwise leave it out.
"""
    elif style == "SKETCH":
        prompt = """Based on the provided sketch, render a complete rabbit with fully drawn limbs (arms and legs) while preserving the sketch’s pose, proportions, and overall charm.
Preserve the sketch’s original details and organic charm.
The face and eyes must remain natural and rabbit-like (almond, round, crescent, etc.).
Enhance the sketch into a refined, high-quality illustration with soft painterly fur shading, smooth gradients, and subtle lighting to give a natural, slightly 3D feel.
Include at most one Chuseok-themed prop (mortar & pestle, kite, lantern, rice cakes, or moon) only if it exists in the sketch, otherwise leave it out.
Avoid geometric or symbolic eyes.
Do not include any shadows.
No background; keep it empty.
Output should be centered, high resolution, with a white background.
**Clothing and accessory style variations:**
Traditional Korean hanbok styles should overall follow a **50:50 ratio of male to female hanbok** across the full set of outputs (not within a single image).
All hanbok should use a pastel-toned color palette for a soft, elegant look.
- **Female hanbok:** pastel flower-patterned hanbok with skirt (chima) and jeogori, pastel-toned elegant hanbok, pastel saekdong hanbok (striped sleeves), accessories like jokduri, jobawi, norigae.
- **Male hanbok:** pastel-toned hanbok with loose pants (baji), pastel do-po style with baji and belt, pastel saekdong-sleeved hanbok with baji, accessories like gat, belt, traditional headgear (hogeon). Male hanbok must always include baji (pants) and must not include skirts (no chima).
"""
    elif style == "2D":
        prompt = """Based on the provided sketch, render a flat 2D cartoon-style rabbit with a full-body view (the entire rabbit must be shown from head to toe, including torso, arms, legs, and feet).
Preserve the original sketch’s pose, proportions, and key details. Keep key elements from the sketch, such as ear shape, limb positions, and facial expression, while refining details and adding softness and a plush, cushion-like texture. Retain the charm and gesture of the sketch.
Use bold, clean line-art with minimal variation in line width.
Apply flat, solid color blocks with little to no shading or gradient.
Apply a soft pastel color palette with low contrast.
Eyes should be natural rabbit eyes (almond, round, crescent), but stylized in a cute, cartoonish way. The rabbit should look slightly cuter and younger, with a slightly larger head, softly rounded cheeks, and a gentle baby-like charm. The rabbit should also have a soft, plush, cushion-like texture, giving it a slightly squishy, huggable appearance like a stuffed animal. Keep it natural and subtle, not overly shiny or plastic-like.
Include at most one Chuseok-themed prop only if it exists in the sketch, otherwise leave it out.
Emphasize a completely 2D, graphic, illustration look, without painterly textures or realistic lighting.
Do not include any shadows.
No background; keep it empty.
Final output should be high resolution, centered, with the rabbit’s entire body visible within the frame.
Clothing and accessory style variations:
Traditional Korean hanbok styles should overall follow a 50:50 ratio of male to female hanbok across the full set of outputs (not within a single image).
All hanbok should use a pastel-toned color palette for a soft, elegant look.
Female hanbok: pastel flower-patterned hanbok with skirt (chima) and jeogori, pastel-toned elegant hanbok, accessories like jokduri, jobawi, norigae.
Male hanbok: pastel-toned hanbok with loose pants (baji), pastel do-po style with baji and belt, accessories like gat, belt, traditional headgear (hogeon). Male hanbok must always include baji (pants) and should not include skirts (no chima).
"""
    else:
        prompt = """Based on the provided sketch, render a 3D rabbit character with fully drawn limbs (arms and legs), keeping the pose and proportions inspired by the sketch. Preserve key elements from the sketch—ear shape, limb positions, and facial expression—while refining details and adding softness and a plush, cushion‑like texture. Retain the charm and gesture of the sketch, but design a new character inspired by the reference vibe only (not an identical copy).
Species lock: rabbit only (lagomorph). Maintain correct rabbit anatomy—long oval ears, small triangular nose with a vertical philtrum, short round cottontail, hind legs proportionally longer than forelegs; do not drift to other species.
Style and proportions: cute chibi body with rounded shapes; slightly larger head, softly rounded cheeks, gentle baby‑like charm.
Materials: matte plush/velvet, softly squishy and huggable; minimize photoreal micro‑fur; soft SSS on ears and nose; low specular, moderate surface roughness so it never looks plastic or overly shiny.
Eyes: very large dark‑brown irises covering 88–92% of the visible eye; minimal sclera as a thin rim; tiny pupils; small natural catchlights; moderate eye roughness (not glassy).
Shading/lighting: highly detailed 3D shading and subtle fur rendering to create depth, but use high‑key, shadowless light‑tent lighting. Do not include any cast or drop shadows or ambient‑occlusion halos. White seamless background only; keep the frame empty besides the character. Output centered, high resolution.
Chuseok prop: include at most one prop only if it exists in the sketch; otherwise exclude.
Add-on for Chuseok props: if the sketch/reference shows any Chuseok-related item such as a mortar (jeolgu), lantern (cho‑rong), or songpyeon, recognize it and optionally include exactly one such prop together with the character; if none are present, leave the image without props.
Clothing and accessory style variations across the full set (not per image):
Overall 50:50 ratio of male to female hanbok.
All hanbok use a pastel‑toned color palette for a soft, elegant look.
Female hanbok: pastel flower‑patterned hanbok with skirt (chima) and jeogori; pastel saekdong sleeves; accessories like jokduri, jobawi, norigae.
Male hanbok: pastel‑toned hanbok with loose pants (baji) always included (no chima); options like pastel do‑po with belt; pastel saekdong sleeves; accessories like gat, belt, traditional headgear (hogeon).
Background: no scene; pure white seamless background only. Do not include any shadows.
identical copy, text/watermark, logos/IP, photoreal micro‑fur, hard shadows, cast/drop shadows, ambient‑occlusion halos, gradient or textured background, vignette, overly glossy eyes, plastic/wet sheen, background objects, UI/HUD, heavy rim light
"""
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