"""小雅网页端同款上传工具。"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import Any

import requests

from ..config import DOWNLOAD_URL
from .client import APIRequestError, expect_success, get_json, post_json

UPLOAD_TIMEOUT = 60


def _asset_name(asset: dict[str, Any], path: Path) -> str:
    name = str(asset.get("name") or path.name).strip()
    if not name:
        raise ValueError("asset.name 不能为空")
    return name


def _guess_content_type(filename: str) -> str | None:
    return mimetypes.guess_type(filename)[0]


def _quote_id_from_upload(
    *,
    upload_response: requests.Response,
    multipart: dict[str, Any],
) -> str:
    try:
        data = upload_response.json()
    except ValueError:
        data = {}
    candidates = (
        data.get("id"),
        data.get("quote_id"),
        data.get("file_id"),
        data.get("data", {}).get("id") if isinstance(data.get("data"), dict) else None,
        data.get("data", {}).get("quote_id") if isinstance(data.get("data"), dict) else None,
        multipart.get("x:id"),
        multipart.get("id"),
        multipart.get("quote_id"),
    )
    quote_id = next((str(value) for value in candidates if value), "")
    if not quote_id:
        raise APIRequestError("上传成功但未返回文件 quote_id")
    return quote_id


def _get_bucket_url() -> str:
    data = expect_success(get_json(f"{DOWNLOAD_URL}/cloud/bucket"), "获取上传 bucket 失败")
    bucket_url = str(data.get("aliyun_oss_host") or "").strip()
    if not bucket_url:
        raise APIRequestError("上传 bucket 为空")
    return bucket_url


def _register_disk_file(*, upload_id: str, filename: str, file_size: int) -> dict[str, Any]:
    data = expect_success(
        post_json(
            f"{DOWNLOAD_URL}/disk/files",
            payload={"uploadId": upload_id, "filename": filename, "file_size": file_size},
        ),
        "注册上传文件失败",
    )
    multipart = data.get("multipart")
    if not isinstance(multipart, dict):
        raise APIRequestError("注册上传文件未返回 multipart 参数")
    return dict(multipart)


def upload_rich_text_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """上传单个 Markdown 资源，返回可嵌入小雅富文本的文件信息。"""
    file_path = Path(str(asset.get("file_path") or ""))
    if not file_path.is_file():
        raise FileNotFoundError(str(file_path))

    filename = _asset_name(asset, file_path)
    upload_id = str(asset.get("upload_id") or uuid.uuid4())
    bucket_url = _get_bucket_url()
    multipart = _register_disk_file(
        upload_id=upload_id, filename=filename, file_size=file_path.stat().st_size
    )
    content_type = _guess_content_type(filename)
    if content_type and "x-oss-content-type" not in multipart:
        multipart["x-oss-content-type"] = content_type

    with file_path.open("rb") as handle:
        response = requests.post(
            bucket_url,
            data=multipart,
            files={"file": (filename, handle, content_type or "application/octet-stream")},
            headers={},
            timeout=UPLOAD_TIMEOUT,
        )
    response.raise_for_status()

    quote_id = _quote_id_from_upload(upload_response=response, multipart=multipart)
    return {
        "id": str(asset["id"]),
        "type": str(asset["type"]),
        "name": filename,
        "quote_id": quote_id,
        "url": f"{DOWNLOAD_URL}/cloud/file_access/{quote_id}",
    }


def upload_rich_text_assets(
    assets: list[dict[str, Any]] | None,
    referenced_ids: set[str],
) -> dict[str, dict[str, Any]]:
    """上传 Markdown 中引用到的 assets，返回 id 到上传结果的映射。"""
    asset_map = {str(asset.get("id")): asset for asset in assets or [] if asset.get("id")}
    missing = sorted(referenced_ids - set(asset_map))
    if missing:
        raise ValueError(f"Markdown asset 引用缺少对应资源: {', '.join(missing)}")
    return {asset_id: upload_rich_text_asset(asset_map[asset_id]) for asset_id in referenced_ids}
