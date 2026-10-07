import os
import shutil
import sys

# Ensure ml_core is in the path regardless of where pytest is run from
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from clip_matcher import ClipMatcher
from PIL import Image

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "assets", "pytest_chroma_db")


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
    tags_dict = matcher.match([dummy_images["red"]], available_tags, top_k=1)
    
    # Check return structure
    assert isinstance(tags_dict, dict)
    assert "positive" in tags_dict
    assert "negative" in tags_dict

    # Assert that a result was found
    assert len(tags_dict["positive"]) > 0
    # Assert that the red tag was correctly identified as the closest match
    assert tags_dict["positive"][0] == "a solid red color"


def test_clip_matcher_blue_image(matcher, dummy_images):
    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a cute dog",
    ]

    # Test just the blue image
    tags_dict = matcher.match([dummy_images["blue"]], available_tags, top_k=1)

    assert len(tags_dict["positive"]) > 0
    assert tags_dict["positive"][0] == "a solid blue color"


def test_clip_matcher_averaging(matcher, dummy_images):
    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a cute dog",
    ]

    # Test both images (should average the embeddings)
    # The top 2 matches should naturally be the red and blue tags, ignoring the dog
    tags_dict = matcher.match(
        [dummy_images["red"], dummy_images["blue"]], available_tags, top_k=2
    )

    assert len(tags_dict["positive"]) == 2
    assert "a solid red color" in tags_dict["positive"]
    assert "a solid blue color" in tags_dict["positive"]
    assert "a cute dog" not in tags_dict["positive"]


def test_clip_matcher_empty_inputs(matcher, dummy_images):
    # Test graceful degradation with empty tags or images
    assert matcher.match([dummy_images["red"]], []) == {"positive": [], "negative": []}
    assert matcher.match([], ["a tag"]) == {"positive": [], "negative": []}

