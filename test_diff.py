from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
text_inputs = processor(
    text=["a solid red color", "a solid blue color"], return_tensors="pt", padding=True
)
image_inputs = processor(
    images=Image.new("RGB", (224, 224), "red"), return_tensors="pt"
)
with torch.no_grad():
    out = model(**text_inputs, **image_inputs)
    print("image_embeds_1[:3]:", out.image_embeds[0, :3])

    vision_outputs = model.vision_model(pixel_values=image_inputs["pixel_values"])
    image_features = model.visual_projection(vision_outputs[1])
    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
    print("image_embeds_2[:3]:", image_features[0, :3])
