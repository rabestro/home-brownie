"""Async REST client for Paperless-ngx API and document upload state machine."""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_MAX_CONSECUTIVE_POLL_FAILURES = 5
_DEFAULT_MAX_WAIT = 180.0
_DEFAULT_POLL_INTERVAL = 3.0

StatusCallback = Callable[[str], Awaitable[None]]


class DuplicateDocumentError(Exception):
    """Raised when an uploaded document is identified as a duplicate."""

    def __init__(self, doc_id: int) -> None:
        super().__init__(f"Duplicate of document #{doc_id}")
        self.doc_id = doc_id


class PaperlessDocument(BaseModel):
    """Subset of a Paperless-ngx document metadata."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    original_file_name: str | None = None
    created: str | None = None
    created_date: str | None = None


class PaperlessTask(BaseModel):
    """Subset of a Paperless-ngx task record from /api/tasks/."""

    model_config = ConfigDict(extra="ignore")

    status: str = ""
    related_document: int | None = None
    result: str | None = None


def _parse_task_id(response: httpx.Response) -> str:
    """Extracts task ID from a post_document response.

    Args:
        response: HTTP response from post_document.

    Returns:
        Extracted task ID string.
    """
    try:
        data = response.json()
    except ValueError:
        return response.text.strip().strip('"')
    if isinstance(data, dict):
        task_id = data.get("task_id")
        return str(task_id) if task_id else ""
    return str(data or "")


def _normalize_tasks(task_data: object) -> list[dict[str, object]]:
    """Normalizes /api/tasks/ JSON body to a list of dicts."""
    if isinstance(task_data, dict) and "results" in task_data:
        results = task_data["results"]
        return results if isinstance(results, list) else []
    if isinstance(task_data, list):
        return task_data
    return []


def _extract_document_id(task: PaperlessTask) -> int | None:
    """Extracts document ID from a succeeded task."""
    if task.related_document is not None:
        return task.related_document
    match = re.search(r"document id (\d+) created", task.result or "", re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_duplicate_id(result_text: str) -> int | None:
    """Extracts existing document ID from a duplicate failure message."""
    if "duplicate" not in result_text.lower():
        return None
    match = re.search(r"#(\d+)", result_text)
    if match:
        return int(match.group(1))
    match = re.search(r"id\s+(\d+)", result_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


async def _notify(on_status: StatusCallback | None, message: str) -> None:
    if on_status is not None:
        await on_status(message)


class PaperlessClient:
    """Async HTTP client for Paperless-ngx.

    Args:
        base_url: Paperless-ngx base URL.
        token: User API token.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Token {token}"}

    async def fetch_document_info(self, doc_id: int) -> PaperlessDocument | None:
        """Fetches metadata for a document ID.

        Args:
            doc_id: Paperless document ID.

        Returns:
            PaperlessDocument or None if 404.
        """
        url = f"{self._base_url}/api/documents/{doc_id}/"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code == httpx.codes.NOT_FOUND:
                return None
            resp.raise_for_status()
            return PaperlessDocument.model_validate(resp.json())

    async def download_pdf(self, doc_id: int) -> bytes:
        """Downloads the original PDF bytes for a document ID.

        Args:
            doc_id: Paperless document ID.

        Returns:
            Raw bytes of the PDF.
        """
        url = f"{self._base_url}/api/documents/{doc_id}/download/"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.content

    async def upload_and_wait_for_ocr(
        self,
        *,
        file_bytes: bytes,
        file_name: str,
        on_status: StatusCallback | None = None,
        max_wait: float = _DEFAULT_MAX_WAIT,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
    ) -> int:
        """Uploads a document and polls OCR status until completion.

        Args:
            file_bytes: Raw file bytes.
            file_name: Original file name.
            on_status: Progress callback.
            max_wait: Max seconds to wait.
            poll_interval: Seconds between status polls.

        Returns:
            Created document ID.
        """
        upload_url = f"{self._base_url}/api/documents/post_document/"
        files = {"document": (file_name, file_bytes)}

        async with httpx.AsyncClient(timeout=30) as client:
            await _notify(on_status, "📤 Uploading document to Paperless-ngx...")
            response = await client.post(upload_url, headers=self._headers, files=files)
            response.raise_for_status()

            task_id = _parse_task_id(response)
            if not task_id:
                raise ValueError(f"Failed to retrieve task ID: {response.text}")

            tasks_url = f"{self._base_url}/api/tasks/?task_id={task_id}"
            await _notify(on_status, "⚙️ Document queued. Waiting for OCR...")

            start_time = datetime.now(UTC)
            consecutive_failures = 0
            while (datetime.now(UTC) - start_time).total_seconds() < max_wait:
                await asyncio.sleep(poll_interval)
                try:
                    task_response = await client.get(tasks_url, headers=self._headers)
                    task_response.raise_for_status()
                    tasks = _normalize_tasks(task_response.json())
                    task = PaperlessTask.model_validate(tasks[0]) if tasks else None
                    consecutive_failures = 0
                except (httpx.HTTPError, ValueError) as err:
                    consecutive_failures += 1
                    if consecutive_failures >= _MAX_CONSECUTIVE_POLL_FAILURES:
                        raise ValueError(f"Task polling failed: {err}") from err
                    continue

                if task is None:
                    continue

                status = task.status.upper()
                if status == "SUCCESS":
                    doc_id = _extract_document_id(task)
                    if doc_id is not None:
                        return doc_id
                    raise ValueError(f"Task succeeded but document ID missing: {task.result}")

                if status in ("FAILED", "FAILURE"):
                    result_text = task.result or ""
                    duplicate_id = _extract_duplicate_id(result_text)
                    if duplicate_id is not None:
                        raise DuplicateDocumentError(doc_id=duplicate_id)
                    raise ValueError(f"Processing failed: {result_text}")

            raise TimeoutError("Timed out waiting for OCR processing.")
