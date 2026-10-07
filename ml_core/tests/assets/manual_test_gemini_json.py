import os, sys
from google import genai
from google.genai import types
from PIL import Image

# Read .env manually
with open('.env') as f:
    for line in f:
        if line.startswith('GEMINI_API_KEY='):
            os.environ['GEMINI_API_KEY'] = line.strip().split('=', 1)[1]

client = genai.Client()
test_img_path = "test_red_gemini.jpg"
Image.new("RGB", (224, 224), color="red").save(test_img_path)
pil_image = Image.open(test_img_path).convert("RGB")

available_tags = ["a solid blue color", "a bright sunny day", "a solid red color", "red", "blue", "dog"]
top_k = 3

prompt = f"""Here is an image. Which of the following tags best describe the content?
Tags: {available_tags}

Return exactly the top {top_k} matching tags from the list, ordered by relevance (best match first).
Return them as a JSON array of strings."""

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=[pil_image, prompt],
    config=types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
    ),
)

print(response.text)
os.remove(test_img_path)
