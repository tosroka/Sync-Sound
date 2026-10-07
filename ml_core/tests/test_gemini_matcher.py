import os
import sys

# Ensure ml_core is in the path regardless of where pytest is run from
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from gemini_matcher import GeminiMatcher

@pytest.fixture(scope="module")
def dummy_images(tmp_path_factory):
    """Fixture to create dummy red and blue images for testing."""
    test_dir = tmp_path_factory.mktemp("test_images")
    
    red_path = str(test_dir / "red.jpg")
    Image.new("RGB", (224, 224), color="red").save(red_path)
    
    return {"red": red_path}

@patch('google.genai.Client')
def test_gemini_matcher_success(MockClient, dummy_images):
    # Setup mock response
    mock_client_instance = MockClient.return_value
    mock_response = MagicMock()
    mock_response.text = '{"positive": ["a solid red color"], "negative": ["a cute dog"]}'
    mock_client_instance.models.generate_content.return_value = mock_response

    # Initialize matcher (it will use the mocked client)
    matcher = GeminiMatcher()
    
    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a cute dog",
    ]
    
    # Test matching
    tags_dict = matcher.match([dummy_images["red"]], available_tags, top_k=1)
    
    assert len(tags_dict["positive"]) > 0
    assert tags_dict["positive"][0] == "a solid red color"
    assert "a cute dog" in tags_dict["negative"]
    
    # Verify the client was called with correct arguments
    mock_client_instance.models.generate_content.assert_called_once()
    call_kwargs = mock_client_instance.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-3.8-flash"
    assert len(call_kwargs["contents"]) == 2 # 1 image + 1 text prompt
    assert call_kwargs["config"].temperature == 0.0
    assert call_kwargs["config"].response_mime_type == "application/json"

@patch('google.genai.Client')
def test_gemini_matcher_fallback(MockClient, dummy_images):
    # Setup mock response where Gemini hallucinates a bit but contains the tag inside JSON
    mock_client_instance = MockClient.return_value
    mock_response = MagicMock()
    mock_response.text = '{"positive": ["I think it is a solid blue color", "a solid blue color", "hallucination"], "negative": []}'
    mock_client_instance.models.generate_content.return_value = mock_response

    matcher = GeminiMatcher()
    
    available_tags = [
        "a solid red color",
        "a solid blue color",
        "a cute dog",
    ]
    
    # Test matching
    tags_dict = matcher.match([dummy_images["red"]], available_tags, top_k=2)
    
    assert len(tags_dict["positive"]) == 1
    assert tags_dict["positive"][0] == "a solid blue color"

def test_gemini_matcher_empty_inputs():
    with patch('google.genai.Client'):
        matcher = GeminiMatcher()
        assert matcher.match(["dummy.jpg"], []) == {"positive": [], "negative": []}
        assert matcher.match([], ["a tag"]) == {"positive": [], "negative": []}
