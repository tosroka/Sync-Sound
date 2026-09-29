from transformers import CLIPProcessor, CLIPModel
import torch

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
available_tags = [
    "a solid red color",
    "a solid blue color",
    "a bright sunny day at the beach",
    "a cute fluffy dog",
    "a dark night sky full of stars",
]
text_inputs = processor(text=available_tags, return_tensors="pt", padding=True)
with torch.no_grad():
    text_outputs = model.text_model(
        input_ids=text_inputs["input_ids"], attention_mask=text_inputs["attention_mask"]
    )
    text_features = model.text_projection(text_outputs[1])
    text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
    print("text_embeds_manual:", text_features[0, :3].tolist())
