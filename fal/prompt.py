from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-5-mini",
    input="""You are an expert prompt engineer for video generation.  
I will provide you with an input image of a rabbit.  
Your task is to generate a video-generation prompt.  

Rules:  
1. The video must always feature a rabbit — no other animals or subjects are allowed.  
2. The rabbit must preserve the unique features and characteristics of the input image.  
3. The rabbit must perform a short, simple, and clear action that can be completed within about 5 seconds  
   (e.g., hopping twice, waving its paw, nibbling food, turning around, stretching, or making a small jump).  
   - Do not repeat the same action every time.  
   - Ensure diversity so that each prompt produces a different 5-second behavior.  
4. Use clear, descriptive language suitable for video-generation prompts (e.g., “animated, smooth motion, cute rabbit, 5-second clip”).  
5. Do not include unrelated objects or subjects.  

Return only the final video-generation prompt.

"""
)

print(response.output_text)
