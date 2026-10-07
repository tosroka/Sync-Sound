import chromadb
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor


class ClipMatcher:
    """
    CLIP-based implementation of TagMatcher.
    Uses ChromaDB to cache tag embeddings.
    """

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        db_path: str = "./chroma_db",
    ):
        # We can use CUDA if available, otherwise fallback to CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

        # Initialize embedded ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="clip_tag_embeddings"
        )

    def _get_or_create_tag_embeddings(self, tags: list[str]):
        """
        Checks ChromaDB for existing tag embeddings.
        If any are missing, calculates them using CLIP and saves them.
        """
        # Fetch existing tags from Chroma
        result = self.collection.get(ids=tags)
        existing_ids = set(result["ids"])

        missing_tags = [tag for tag in tags if tag not in existing_ids]

        if missing_tags:
            # Batch process missing tags to prevent OOM errors if the list is large
            batch_size = 64
            for i in range(0, len(missing_tags), batch_size):
                batch_tags = missing_tags[i : i + batch_size]

                # Calculate embeddings
                inputs = self.processor.tokenizer(
                    text=batch_tags, return_tensors="pt", padding=True
                ).to(self.device)
                with torch.no_grad():
                    text_outputs = self.model.text_model(
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs.get("attention_mask"),
                    )
                    text_features = self.model.text_projection(text_outputs[1])
                    # Normalize features for cosine similarity
                    text_features = text_features / text_features.norm(
                        p=2, dim=-1, keepdim=True
                    )

                embeddings = text_features.cpu().numpy().tolist()

                # Store the tag as metadata so we can filter by it later
                metadatas = [{"tag": t} for t in batch_tags]

                self.collection.add(
                    embeddings=embeddings,
                    documents=batch_tags,
                    metadatas=metadatas,
                    ids=batch_tags,
                )

    def match(
        self, image_paths: list[str], available_tags: list[str], top_k: int = 5
    ) -> dict:
        if not available_tags or not image_paths:
            return {"positive": [], "negative": []}

        # 1. Ensure all candidate tags are embedded and cached in ChromaDB
        self._get_or_create_tag_embeddings(available_tags)

        # 2. Load and embed the images
        images = [Image.open(path).convert("RGB") for path in image_paths]

        inputs = self.processor.image_processor(images=images, return_tensors="pt").to(
            self.device
        )
        with torch.no_grad():
            vision_outputs = self.model.vision_model(
                pixel_values=inputs["pixel_values"]
            )
            image_features = self.model.visual_projection(vision_outputs[1])

            # Average the features across the multiple frames to get a single vector representing the video
            image_feature = image_features.mean(dim=0, keepdim=True)
            image_feature = image_feature / image_feature.norm(
                p=2, dim=-1, keepdim=True
            )

        image_embedding = image_feature.cpu().numpy().tolist()[0]

        # 3. Query ChromaDB to find the closest tags, restricting the search to `available_tags`
        # We query for ALL available tags to get both the best and worst matches
        results = self.collection.query(
            query_embeddings=[image_embedding],
            n_results=len(available_tags),
            where={"tag": {"$in": available_tags}},
        )

        if results["ids"] and len(results["ids"]) > 0:
            all_sorted_tags = results["ids"][0]
            top_positive = all_sorted_tags[:top_k]
            top_negative = all_sorted_tags[-top_k:] if len(all_sorted_tags) >= top_k else []
            return {"positive": top_positive, "negative": top_negative}

        return {"positive": [], "negative": []}
