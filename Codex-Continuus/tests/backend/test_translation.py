import pytest
from unittest.mock import MagicMock, patch

import backend.translation.groqTranslation as translation_module

def test_webTranslation_success():
    """Test successful translation with mocked API."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_text = "Translated text"
    mock_client.responses.create.return_value = mock_response

    with patch('backend.translation.groqTranslation.client', mock_client):
        result = translation_module.webTranslation("Latin text")
        assert result == "Translated text"
        mock_client.responses.create.assert_called_once_with(
            input="Latin to English translation for: Latin text",
            model="openai/gpt-oss-20b"
        )

def test_webTranslation_with_env_var():
    """Test that GROQAPIKEY is used from environment."""
    import os
    original_key = os.environ.get("GROQAPIKEY")
    os.environ["GROQAPIKEY"] = "test_key"

    try:
        # Re-import to pick up env var
        import importlib
        importlib.reload(translation_module)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "Env translated"
        mock_client.responses.create.return_value = mock_response

        with patch('backend.translation.groqTranslation.client', mock_client):
            result = translation_module.webTranslation("Test")
            assert result == "Env translated"
    finally:
        if original_key:
            os.environ["GROQAPIKEY"] = original_key
        else:
            os.environ.pop("GROQAPIKEY", None)

def test_webTranslation_api_error():
    """Test handling of API errors."""
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = Exception("API Error")

    with patch('backend.translation.groqTranslation.client', mock_client):
        with pytest.raises(Exception, match="API Error"):
            translation_module.webTranslation("Error text")
