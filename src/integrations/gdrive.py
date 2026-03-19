from __future__ import annotations

import logging

from src.config import settings

logger = logging.getLogger(__name__)


class GDriveClient:
    def __init__(self, credentials_path: str) -> None:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        scopes = [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive.file",
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self._docs_service = build("docs", "v1", credentials=creds)
        self._drive_service = build("drive", "v3", credentials=creds)

    def create_doc(self, title: str, content: str) -> str:
        doc = self._docs_service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]

        self._docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {"insertText": {"location": {"index": 1}, "text": content}}
                ]
            },
        ).execute()

        return f"https://docs.google.com/document/d/{doc_id}/edit"


_gdrive_client_instance: GDriveClient | None = None


def get_gdrive_client() -> GDriveClient | None:
    global _gdrive_client_instance
    if _gdrive_client_instance is not None:
        return _gdrive_client_instance

    creds_path = settings.google_credentials_path
    if creds_path is None or not creds_path.exists():
        logger.debug("Google credentials not configured, GDrive integration disabled")
        return None

    try:
        _gdrive_client_instance = GDriveClient(str(creds_path))
        return _gdrive_client_instance
    except Exception:
        logger.warning("Failed to initialize GDrive client", exc_info=True)
        return None
