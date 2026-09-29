import os
import shutil

import pytest
from ml_core.clip_matcher import ClipMatcher
from PIL import Image

TEST_DB_PATH = "./pytest_chroma_db"


@pytest.fixture(scope="module")
def matcher():
    """Fixture to provide a single instance of ClipMatcher for tests, using a test db."""
    # Ensure a clean slate for the test database
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

    m = ClipMatcher(db_path=TEST_DB_PATH)
    yield m

    # Cleanup after tests
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)


@pytest.fixture(scope="module")
def dummy_images(tmp_path_factory):
    """Fixture to create dummy red and blue images for testing."""
    test_dir = tmp_path_factory.mktemp("test_images")

    red_path = str(test_dir / "red.jpg")
    Image.new("RGB", (224, 224), color="red").save(red_path)

    blue_path = str(test_dir / "blue.jpg")
    Image.new("RGB", (224, 224), color="blue").save(blue_path)

    return {"red": red_path, "blue": blue_path}


def test_clip_matcher_red_image(matcher, dummy_images):
    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a cute dog",
    ]

    # Test just the red image
    top_tags = matcher.match([dummy_images["red"]], available_tags, top_k=1)

    # Assert that a result was found
    assert len(top_tags) > 0
    # Assert that the red tag was correctly identified as the closest match
    assert top_tags[0] == "a solid red color"


def test_clip_matcher_blue_image(matcher, dummy_images):
    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a cute dog",
    ]

    # Test just the blue image
    top_tags = matcher.match([dummy_images["blue"]], available_tags, top_k=1)

    assert len(top_tags) > 0
    assert top_tags[0] == "a solid blue color"


def test_clip_matcher_averaging(matcher, dummy_images):
    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a cute dog",
    ]

    # Test both images (should average the embeddings)
    # The top 2 matches should naturally be the red and blue tags, ignoring the dog
    top_tags = matcher.match(
        [dummy_images["red"], dummy_images["blue"]], available_tags, top_k=2
    )

    assert len(top_tags) == 2
    assert "a solid red color" in top_tags
    assert "a solid blue color" in top_tags
    assert "a cute dog" not in top_tags


def test_clip_matcher_empty_inputs(matcher, dummy_images):
    # Test graceful degradation with empty tags or images
    assert matcher.match([dummy_images["red"]], []) == []
    assert matcher.match([], ["a tag"]) == []
