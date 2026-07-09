"""任务附件下载与本地缓存辅助。"""

from __future__ import annotations

import mimetypes
import re
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context
from pathlib import Path
from typing import Any

from ...utils.client import APIRequestError

AttachmentDownloader = Callable[[str, str], dict[str, Any]]


def collect_answer_attachments(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        attachment
        for question in questions
        for attachment in question.get("attachments", [])
        if attachment.get("quote_id")
    ]


def default_attachment_dir(record_id: str) -> Path:
    return (
        Path(tempfile.gettempdir())
        / "xiaoya-teacher-mcp-server"
        / "grading-attachments"
        / _safe_path_part(record_id)
    )


def download_answer_attachments(
    attachments: list[dict[str, Any]],
    attachment_dir: Path,
    max_workers: int,
    downloader: AttachmentDownloader,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    attachment_dir.mkdir(parents=True, exist_ok=True)
    unique = {str(item["quote_id"]): item for item in attachments if item.get("quote_id")}
    downloaded = _collect_cached_attachments(unique, attachment_dir)
    missing = [item for quote_id, item in unique.items() if quote_id not in downloaded]
    if not missing:
        return downloaded, []

    errors: list[dict[str, Any]] = []
    workers = max(1, min(max_workers, len(missing)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for attachment in missing:
            ctx = copy_context()
            future = executor.submit(
                ctx.run, _download_attachment, attachment, attachment_dir, downloader
            )
            futures[future] = attachment
        for future in as_completed(futures):
            attachment = futures[future]
            quote_id = str(attachment["quote_id"])
            try:
                downloaded[quote_id] = future.result()
            except (APIRequestError, OSError, KeyError) as exc:
                errors.append(
                    {
                        "quote_id": quote_id,
                        "name": attachment.get("name"),
                        "message": str(exc),
                    }
                )
    return downloaded, errors


def merge_downloaded_attachments(
    questions: list[dict[str, Any]],
    downloaded: dict[str, dict[str, Any]],
) -> None:
    for question in questions:
        question["attachments"] = [
            downloaded.get(str(attachment.get("quote_id")), attachment)
            for attachment in question.get("attachments", [])
        ]


def _safe_path_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return safe or "item"


def _collect_cached_attachments(
    attachments: dict[str, dict[str, Any]],
    attachment_dir: Path,
) -> dict[str, dict[str, Any]]:
    return {
        quote_id: _attachment_info_from_path(attachment, cached)
        for quote_id, attachment in attachments.items()
        if (cached := _find_cached_attachment(attachment_dir, quote_id))
    }


def _content_head_looks_like_html(content: bytes) -> bool:
    head = content.lstrip()[:64].lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def looks_like_html_payload(content: bytes, mimetype: str) -> bool:
    if mimetype.startswith("text/html"):
        return True
    return _content_head_looks_like_html(content)


def _looks_like_html_file(file_path: Path) -> bool:
    try:
        return _content_head_looks_like_html(file_path.read_bytes()[:64])
    except OSError:
        return True


def _find_cached_attachment(directory: Path, quote_id: str) -> Path | None:
    safe_quote_id = _safe_path_part(quote_id)
    if not directory.exists():
        return None
    for child in directory.iterdir():
        if child.is_file() and (child.name == safe_quote_id or child.stem == safe_quote_id):
            if _looks_like_html_file(child):
                continue
            return child
    return None


def _attachment_info_from_path(
    attachment: dict[str, Any],
    file_path: Path,
) -> dict[str, Any]:
    mimetype = attachment.get("mimetype") or mimetypes.guess_type(file_path.name)[0]
    return {
        **attachment,
        "file_path": str(file_path),
        "mimetype": mimetype or "application/octet-stream",
    }


def _download_attachment(
    attachment: dict[str, Any],
    attachment_dir: Path,
    downloader: AttachmentDownloader,
) -> dict[str, Any]:
    quote_id = str(attachment["quote_id"])
    cached = _find_cached_attachment(attachment_dir, quote_id)
    if cached:
        return _attachment_info_from_path(attachment, cached)

    result = downloader(quote_id, str(attachment_dir))
    if not result.get("success"):
        raise APIRequestError(result.get("message", "附件下载失败"))

    data = result["data"]
    return {
        **attachment,
        "file_path": data["file_path"],
        "mimetype": data.get("mimetype") or attachment.get("mimetype", ""),
    }
