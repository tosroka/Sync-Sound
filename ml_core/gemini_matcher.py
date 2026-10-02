import json
import os
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
        # The genai client will automatically pick up GEMINI_API_KEY from the environment
        self.client = genai.Client()
        self.model_name = model_name

    def match(
        self, image_paths: List[str], available_tags: List[str], top_k: int = 5
    ) -> List[str]:
        if not available_tags or not image_paths:
            return []

        # Load images
        pil_images = [Image.open(path).convert("RGB") for path in image_paths]
        
        # We can pass PIL images directly to the genai SDK
        contents = pil_images + [
            f"Here are some frames from a video. Which of the following tags best describe the content?\n"
            f"Tags: {available_tags}\n\n"
            f"Return exactly the top {top_k} matching tags from the list, ordered by relevance (best match first).\n"
            f"Return them as a JSON array of strings."
        ]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.0,  # We want a deterministic, factual choice
                response_mime_type="application/json",
            ),
        )

        try:
            # Parse the JSON array
            matched_tags = json.loads(response.text)
            if not isinstance(matched_tags, list):
                matched_tags = [str(matched_tags)]
        except json.JSONDecodeError:
            # Fallback if Gemini didn't return valid JSON
            matched_tags = [response.text.strip().strip('"').strip("'")]

        # Filter out hallucinations and ensure exact matching
        valid_tags = []
        for tag in matched_tags:
            tag_str = str(tag)
            if tag_str in available_tags and tag_str not in valid_tags:
                valid_tags.append(tag_str)
                
        return valid_tags[:top_k]
