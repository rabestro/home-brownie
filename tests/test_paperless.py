"""Unit tests for PaperlessClient and helper functions in paperless.py."""

import httpx
import pytest
import respx

from home_brownie.paperless import (
    DuplicateDocumentError,
    PaperlessClient,
    PaperlessTask,
    _extract_document_id,
    _extract_duplicate_id,
    _parse_task_id,
)


def test_parse_task_id_json_dict() -> None:
    resp = httpx.Response(200, json={"task_id": "abc-123"})
    assert _parse_task_id(resp) == "abc-123"


def test_parse_task_id_raw_string() -> None:
    resp = httpx.Response(200, text='"xyz-999"')
    assert _parse_task_id(resp) == "xyz-999"


def test_extract_document_id() -> None:
    task = PaperlessTask(status="SUCCESS", related_document=42)
    assert _extract_document_id(task) == 42

    task_fallback = PaperlessTask(status="SUCCESS", result="Document ID 99 created")
    assert _extract_document_id(task_fallback) == 99


def test_extract_duplicate_id() -> None:
    assert _extract_duplicate_id("It is a duplicate of #416") == 416
    assert _extract_duplicate_id("Found duplicate ID 88") == 88
    assert _extract_duplicate_id("Normal error without duplicate") is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_document_info_success() -> None:
    respx.get("https://docs.local/api/documents/10/").respond(
        200, json={"title": "Invoice 2026", "original_file_name": "inv.pdf"}
    )

    client = PaperlessClient("https://docs.local", "token123")
    doc = await client.fetch_document_info(10)
    assert doc is not None
    assert doc.title == "Invoice 2026"
    assert doc.original_file_name == "inv.pdf"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_document_info_not_found() -> None:
    respx.get("https://docs.local/api/documents/999/").respond(404)

    client = PaperlessClient("https://docs.local", "token123")
    doc = await client.fetch_document_info(999)
    assert doc is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_and_wait_for_ocr_success() -> None:
    respx.post("https://docs.local/api/documents/post_document/").respond(
        200, json={"task_id": "task-1"}
    )
    respx.get("https://docs.local/api/tasks/?task_id=task-1").respond(
        200, json=[{"status": "SUCCESS", "related_document": 50}]
    )

    client = PaperlessClient("https://docs.local", "token123")
    doc_id = await client.upload_and_wait_for_ocr(
        file_bytes=b"dummy pdf",
        file_name="test.pdf",
        poll_interval=0.01,
    )
    assert doc_id == 50


@pytest.mark.asyncio
@respx.mock
async def test_upload_duplicate_error() -> None:
    respx.post("https://docs.local/api/documents/post_document/").respond(
        200, json={"task_id": "task-dup"}
    )
    respx.get("https://docs.local/api/tasks/?task_id=task-dup").respond(
        200, json=[{"status": "FAILURE", "result": "This file is a duplicate of #416"}]
    )

    client = PaperlessClient("https://docs.local", "token123")
    with pytest.raises(DuplicateDocumentError) as exc_info:
        await client.upload_and_wait_for_ocr(
            file_bytes=b"dup pdf",
            file_name="dup.pdf",
            poll_interval=0.01,
        )
    assert exc_info.value.doc_id == 416
