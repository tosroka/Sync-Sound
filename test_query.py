import sys

sys.path.append("ml_core")
from ml_core.clip_matcher import ClipMatcher

matcher = ClipMatcher(db_path="./test_chroma_db")
images = ["test_images/red.jpg"]
tags = ["a solid red color", "a solid blue color"]

import torch
from PIL import Image

images_opened = [Image.open(p).convert("RGB") for p in images]
inputs = matcher.processor(images=images_opened, return_tensors="pt", padding=True).to(
    matcher.device
)
with torch.no_grad():
    vision_outputs = matcher.model.vision_model(pixel_values=inputs["pixel_values"])
    image_features = matcher.model.visual_projection(vision_outputs[1])
    image_feature = image_features.mean(dim=0, keepdim=True)
    image_feature = image_feature / image_feature.norm(p=2, dim=-1, keepdim=True)
image_embedding = image_feature.cpu().numpy().tolist()[0]
print("red image embedding:", image_embedding[:3])

results = matcher.collection.query(
    query_embeddings=[image_embedding], n_results=2, where={"tag": {"$in": tags}}
)
print(results["ids"])
print(results["distances"])
