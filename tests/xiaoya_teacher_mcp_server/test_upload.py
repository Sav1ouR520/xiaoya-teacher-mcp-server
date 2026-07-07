from pathlib import Path

import pytest

from xiaoya_teacher_mcp_server.config import DOWNLOAD_URL
from xiaoya_teacher_mcp_server.utils import upload


class DummyUploadResponse:
    def __init__(self, json_data=None):
        self._json_data = json_data or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._json_data


def test_upload_rich_text_asset_uses_xiaoya_web_flow(monkeypatch, tmp_path):
    source = tmp_path / "diagram.png"
    source.write_bytes(b"png-bytes")
    captured = {}

    def fake_get_json(url):
        captured["bucket_url"] = url
        return {"success": True, "data": {"aliyun_oss_host": "https://oss.example.test"}}

    def fake_post_json(url, *, payload=None):
        captured["register_url"] = url
        captured["register_payload"] = payload
        return {
            "success": True,
            "data": {
                "multipart": {
                    "x:id": "quote-1",
                    "x:user_id": "user-1",
                    "key": "uploads/diagram.png",
                    "OSSAccessKeyId": "access",
                    "policy": "policy",
                    "signature": "signature",
                    "callback": "callback",
                }
            },
        }

    def fake_post(url, *, data=None, files=None, headers=None, timeout=None):
        captured["oss_url"] = url
        captured["oss_data"] = data
        captured["oss_file_name"] = files["file"][0]
        captured["oss_file_bytes"] = files["file"][1].read()
        captured["oss_headers"] = headers
        captured["oss_timeout"] = timeout
        return DummyUploadResponse({"id": "quote-1", "filename": "diagram.png"})

    monkeypatch.setattr(upload, "get_json", fake_get_json)
    monkeypatch.setattr(upload, "post_json", fake_post_json)
    monkeypatch.setattr(upload.requests, "post", fake_post)

    result = upload.upload_rich_text_asset(
        {"id": "img_1", "type": "image", "name": "diagram.png", "file_path": str(source)}
    )

    assert captured["bucket_url"] == f"{DOWNLOAD_URL}/cloud/bucket"
    assert captured["register_url"] == f"{DOWNLOAD_URL}/disk/files"
    assert captured["register_payload"]["filename"] == "diagram.png"
    assert captured["register_payload"]["file_size"] == len(b"png-bytes")
    assert captured["register_payload"]["uploadId"]
    assert captured["oss_url"] == "https://oss.example.test"
    assert captured["oss_data"]["x:id"] == "quote-1"
    assert captured["oss_file_name"] == "diagram.png"
    assert captured["oss_file_bytes"] == b"png-bytes"
    assert captured["oss_headers"] == {}
    assert captured["oss_timeout"] == 60
    assert result == {
        "id": "img_1",
        "type": "image",
        "name": "diagram.png",
        "quote_id": "quote-1",
        "url": f"{DOWNLOAD_URL}/cloud/file_access/quote-1",
    }


def test_upload_rich_text_assets_uploads_only_referenced_assets(monkeypatch, tmp_path):
    source = tmp_path / "diagram.png"
    source.write_bytes(b"png")
    calls = []

    def fake_upload(asset):
        calls.append(asset["id"])
        return {
            "id": asset["id"],
            "type": asset["type"],
            "name": asset["name"],
            "quote_id": f"quote-{asset['id']}",
            "url": f"{DOWNLOAD_URL}/cloud/file_access/quote-{asset['id']}",
        }

    monkeypatch.setattr(upload, "upload_rich_text_asset", fake_upload)

    result = upload.upload_rich_text_assets(
        [
            {"id": "img_1", "type": "image", "name": "diagram.png", "file_path": str(source)},
            {"id": "unused", "type": "attachment", "name": "unused.zip", "file_path": str(source)},
        ],
        {"img_1"},
    )

    assert calls == ["img_1"]
    assert result["img_1"]["quote_id"] == "quote-img_1"
    assert "unused" not in result


def test_upload_rich_text_assets_rejects_missing_references(tmp_path):
    source = tmp_path / "diagram.png"
    source.write_bytes(b"png")

    with pytest.raises(ValueError, match="missing"):
        upload.upload_rich_text_assets(
            [{"id": "img_1", "type": "image", "name": "diagram.png", "file_path": str(source)}],
            {"missing"},
        )


def test_upload_rich_text_asset_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        upload.upload_rich_text_asset(
            {
                "id": "file_1",
                "type": "attachment",
                "name": "missing.zip",
                "file_path": str(Path("/tmp/does-not-exist.zip")),
            }
        )
