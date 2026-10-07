import json
import os
import time
from typing import List

from google import genai
from google.genai import types
from PIL import Image


class GeminiMatcher:
    """
    Gemini-based implementation of TagMatcher.
    Uses the Gemini API to analyze images and select the best matching tag.
    """

    def __init__(self, model_name: str = "gemini-3.8-flash"):
        self.client = genai.Client()
        self.preferred_models = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]

    def match(
        self, image_paths: List[str], available_tags: List[str], top_k: int = 5
    ) -> dict:
        if not available_tags or not image_paths:
            return {"positive": [], "negative": []}

        pil_images = [Image.open(path).convert("RGB") for path in image_paths]
        
        contents = pil_images + [
            f"Here are some frames from a video.\n"
            f"Tags: {available_tags}\n\n"
            f"Based on the content of the video frames, please select exactly the top {top_k} tags that BEST describe the video (positive), and the top {top_k} tags that LEAST describe the video / definitely do NOT fit (negative).\n"
            f"Return a JSON object strictly following this schema:\n"
            f'{{"positive": ["tag1", "tag2"], "negative": ["tag1", "tag2"]}}'
        ]

        response = None
        last_error = None
        
        # Try multiple stable endpoints to avoid 503 spikes
        for model in self.preferred_models:
            try:
                print(f"Attempting inference with {model}...")
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                print(f"Successfully generated content with {model}")
                break
            except Exception as e:
                last_error = e
                print(f"Model {model} failed: {e}")
                time.sleep(1) # Backoff before trying next model
                continue
                
        if response is None:
            raise Exception(f"All preferred Gemini models failed. Last error: {last_error}")

        try:
            matched_tags = json.loads(response.text)
            if not isinstance(matched_tags, dict):
                matched_tags = {"positive": [], "negative": []}
        except json.JSONDecodeError:
            matched_tags = {"positive": [], "negative": []}

        # Filter out hallucinations
        result_dict = {"positive": [], "negative": []}
        for key in ["positive", "negative"]:
            for tag in matched_tags.get(key, []):
                tag_str = str(tag)
                if tag_str in available_tags and tag_str not in result_dict[key]:
                    result_dict[key].append(tag_str)
                    
        return {
            "positive": result_dict["positive"][:top_k],
            "negative": result_dict["negative"][:top_k]
        }
