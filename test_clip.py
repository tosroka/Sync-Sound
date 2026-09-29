import os
from PIL import Image
from ml_core.clip_matcher import ClipMatcher


def create_dummy_images() -> list[str]:
    """Creates a few basic colored images to test the model."""
    os.makedirs("test_images", exist_ok=True)
    img_paths = []

    # Red image
    img1_path = "test_images/red.jpg"
    Image.new("RGB", (224, 224), color="red").save(img1_path)
    img_paths.append(img1_path)

    # Blue image
    img2_path = "test_images/blue.jpg"
    Image.new("RGB", (224, 224), color="blue").save(img2_path)
    img_paths.append(img2_path)

    return img_paths


def main():
    print(
        "1. Initializing ClipMatcher (this will download the model if it's the first time)..."
    )
    matcher = ClipMatcher(db_path="./test_chroma_db")

    print("2. Creating dummy images...")
    image_paths = create_dummy_images()

    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a bright sunny day at the beach",
        "a cute fluffy dog",
        "a dark night sky full of stars",
    ]

    print(f"3. Running matches against these tags: {available_tags}")

    # Test 1: Red Image
    print("\n--- Testing with the Red Image ---")
    top_tags_red = matcher.match([image_paths[0]], available_tags, top_k=2)
    print(f"Matches for Red image: {top_tags_red}")

    # Test 2: Blue Image
    print("\n--- Testing with the Blue Image ---")
    top_tags_blue = matcher.match([image_paths[1]], available_tags, top_k=2)
    print(f"Matches for Blue image: {top_tags_blue}")

    # Test 3: Both Images
    print("\n--- Testing with Both Images (Averaging) ---")
    top_tags_both = matcher.match(image_paths, available_tags, top_k=3)
    print(f"Matches for Both images combined: {top_tags_both}")

    print(
        "\nDone! Check the generated `test_chroma_db` folder to see where embeddings are saved."
    )


if __name__ == "__main__":
    main()
