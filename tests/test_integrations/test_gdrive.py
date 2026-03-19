from unittest.mock import MagicMock, patch

import pytest

from src.integrations.gdrive import GDriveClient, get_gdrive_client


@pytest.fixture
def mock_docs_service():
    service = MagicMock()
    create = MagicMock()
    create.execute.return_value = {"documentId": "abc123"}
    service.documents.return_value.create.return_value = create

    batch_update = MagicMock()
    batch_update.execute.return_value = {}
    service.documents.return_value.batchUpdate.return_value = batch_update

    return service


@pytest.fixture
def mock_drive_service():
    service = MagicMock()
    return service


@pytest.fixture
def gdrive_client(mock_docs_service, mock_drive_service):
    client = GDriveClient.__new__(GDriveClient)
    client._docs_service = mock_docs_service
    client._drive_service = mock_drive_service
    return client


class TestGDriveClientCreateDoc:
    def test_creates_doc_and_returns_url(self, gdrive_client, mock_docs_service):
        url = gdrive_client.create_doc("Test Title", "Some content here")

        mock_docs_service.documents.return_value.create.assert_called_once()
        create_call = mock_docs_service.documents.return_value.create.call_args
        assert create_call.kwargs["body"]["title"] == "Test Title"
        assert url == "https://docs.google.com/document/d/abc123/edit"

    def test_inserts_content_via_batch_update(self, gdrive_client, mock_docs_service):
        gdrive_client.create_doc("Title", "Hello world")

        mock_docs_service.documents.return_value.batchUpdate.assert_called_once()
        batch_call = mock_docs_service.documents.return_value.batchUpdate.call_args
        assert batch_call.kwargs["documentId"] == "abc123"
        requests = batch_call.kwargs["body"]["requests"]
        assert any(
            "insertText" in r and r["insertText"]["text"] == "Hello world"
            for r in requests
        )


class TestGetGDriveClient:
    def test_returns_none_when_no_credentials(self):
        with patch("src.integrations.gdrive.settings") as mock_settings:
            mock_settings.google_credentials_path = None
            import src.integrations.gdrive as mod
            mod._gdrive_client_instance = None
            result = get_gdrive_client()
            assert result is None

    def test_returns_none_when_credentials_file_missing(self, tmp_path):
        with patch("src.integrations.gdrive.settings") as mock_settings:
            mock_settings.google_credentials_path = tmp_path / "nonexistent.json"
            import src.integrations.gdrive as mod
            mod._gdrive_client_instance = None
            result = get_gdrive_client()
            assert result is None
