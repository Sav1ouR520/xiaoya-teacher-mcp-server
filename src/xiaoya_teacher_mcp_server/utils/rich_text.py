"""小雅富文本转换工具。"""

from __future__ import annotations

import json
import random
import re
import string
from typing import Any

from ..config import DOWNLOAD_URL

ASSET_ID_RE = re.compile(r"asset://([A-Za-z0-9_.:-]+)")
ASSET_IMAGE_LINE_RE = re.compile(r"^!\[([^\]]*)\]\(asset://([A-Za-z0-9_.:-]+)\)$")
ASSET_LINK_LINE_RE = re.compile(r"^\[([^\]]+)\]\(asset://([A-Za-z0-9_.:-]+)\)$")
CLOUD_FILE_ID_RE = re.compile(r"/cloud/file_(?:access|url)/([^/?#]+)")
HEADER_BLOCK_TYPES = {
    1: "header-one",
    2: "header-two",
    3: "header-three",
    4: "header-four",
    5: "header-five",
    6: "header-six",
}
MARKDOWN_HEADERS = {
    "header-one": "#",
    "header-two": "##",
    "header-three": "###",
    "header-four": "####",
    "header-five": "#####",
    "header-six": "######",
}
MARKDOWN_INLINE_MARKERS = {
    "BOLD": ("**", "**"),
    "ITALIC": ("*", "*"),
    "UNDERLINE": ("<u>", "</u>"),
    "CODE": ("`", "`"),
    "lineThrough": ("~~", "~~"),
}


def _generate_block_key(length: int = 5) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def load_rich_text_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def is_rich_text_document(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("blocks"), list)


def rich_text_to_plain_text(value: Any) -> Any:
    parsed = load_rich_text_value(value)
    if is_rich_text_document(parsed):
        blocks = parsed.get("blocks") or []
        return "\n".join(
            "" if block.get("type") == "atomic" else block.get("text", "") for block in blocks
        )
    return parsed


def plain_text_to_rich_text_raw(text: str) -> str:
    return json.dumps(
        {
            "blocks": [
                {
                    "key": _generate_block_key(),
                    "text": text,
                    "type": "unstyled",
                    "depth": 0,
                    "inlineStyleRanges": [],
                    "entityRanges": [],
                    "data": {},
                }
            ],
            "entityMap": {},
        },
        ensure_ascii=False,
    )


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _rich_text_block(
    text: str,
    block_type: str = "unstyled",
    inline_style_ranges: list[dict[str, Any]] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "key": _generate_block_key(),
        "text": text,
        "type": block_type,
        "depth": 0,
        "inlineStyleRanges": inline_style_ranges or [],
        "entityRanges": [],
        "data": data or {},
    }


def _append_inline_text(
    output_parts: list[str],
    style_ranges: list[dict[str, Any]],
    text: str,
    style: str | None = None,
) -> None:
    if not text:
        return
    offset = _utf16_len("".join(output_parts))
    output_parts.append(text)
    if style:
        style_ranges.append({"offset": offset, "length": _utf16_len(text), "style": style})


def _parse_inline_markdown(text: str) -> tuple[str, list[dict[str, Any]]]:
    output_parts: list[str] = []
    style_ranges: list[dict[str, Any]] = []
    i = 0

    while i < len(text):
        if text.startswith("<u>", i):
            end = text.find("</u>", i + 3)
            if end != -1:
                _append_inline_text(output_parts, style_ranges, text[i + 3 : end], "UNDERLINE")
                i = end + 4
                continue

        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                _append_inline_text(output_parts, style_ranges, text[i + 1 : end], "CODE")
                i = end + 1
                continue

        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                _append_inline_text(output_parts, style_ranges, text[i + 2 : end], "BOLD")
                i = end + 2
                continue

        if text.startswith("__", i):
            end = text.find("__", i + 2)
            if end != -1:
                _append_inline_text(output_parts, style_ranges, text[i + 2 : end], "BOLD")
                i = end + 2
                continue

        if text[i] == "*":
            end = text.find("*", i + 1)
            if end != -1:
                _append_inline_text(output_parts, style_ranges, text[i + 1 : end], "ITALIC")
                i = end + 1
                continue

        if text[i] == "_":
            end = text.find("_", i + 1)
            if end != -1:
                _append_inline_text(output_parts, style_ranges, text[i + 1 : end], "ITALIC")
                i = end + 1
                continue

        output_parts.append(text[i])
        i += 1

    return "".join(output_parts), style_ranges


def _markdown_block_type_and_text(line: str) -> tuple[str, str]:
    header = re.match(r"^(#{1,6})\s+(.*)$", line)
    if header:
        return HEADER_BLOCK_TYPES[len(header.group(1))], header.group(2).strip()

    unordered = re.match(r"^\s*[-*+]\s+(.*)$", line)
    if unordered:
        return "unordered-list-item", unordered.group(1).strip()

    ordered = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
    if ordered:
        return "ordered-list-item", ordered.group(1).strip()

    quote = re.match(r"^\s*>\s?(.*)$", line)
    if quote:
        return "blockquote", quote.group(1).strip()

    return "unstyled", line


def collect_markdown_asset_ids(markdown: str) -> set[str]:
    return set(ASSET_ID_RE.findall(markdown or ""))


def markdown_without_asset_references(markdown: str) -> str:
    lines = []
    for line in (markdown or "").splitlines():
        stripped = line.strip()
        if ASSET_IMAGE_LINE_RE.match(stripped) or ASSET_LINK_LINE_RE.match(stripped):
            continue
        lines.append(line)
    return "\n".join(lines)


def _normalized_asset_type(asset: dict[str, Any]) -> str:
    asset_type = str(asset.get("type") or "").strip().lower()
    if asset_type in {"file", "disk"}:
        return "attachment"
    return asset_type


def _uploaded_asset_url(asset: dict[str, Any]) -> str:
    url = str(asset.get("url") or "").strip()
    if url:
        return url
    quote_id = str(asset.get("quote_id") or "").strip()
    if quote_id:
        return f"{DOWNLOAD_URL}/cloud/file_access/{quote_id}"
    return ""


def _require_uploaded_asset(
    uploaded_assets: dict[str, dict[str, Any]],
    asset_id: str,
    expected_type: str,
) -> dict[str, Any]:
    asset = uploaded_assets.get(asset_id)
    if asset is None:
        raise ValueError(f"Markdown asset 引用缺少上传结果: {asset_id}")
    actual_type = _normalized_asset_type(asset)
    if actual_type != expected_type:
        raise ValueError(
            f"Markdown asset {asset_id} 类型应为 {expected_type}, 实际为 {actual_type}"
        )
    return asset


def _image_asset_blocks(asset: dict[str, Any]) -> list[dict[str, Any]]:
    url = _uploaded_asset_url(asset)
    if not url:
        raise ValueError(f"图片 asset 缺少 url 或 quote_id: {asset.get('id')}")
    return [
        _rich_text_block(
            "",
            "atomic",
            data={"type": "IMAGE", "src": url, "resizeData": {"width": 15, "height": 0}},
        ),
        _rich_text_block(""),
    ]


def _attachment_asset_blocks(asset: dict[str, Any]) -> list[dict[str, Any]]:
    quote_id = str(asset.get("quote_id") or "").strip()
    if not quote_id:
        raise ValueError(f"附件 asset 缺少 quote_id: {asset.get('id')}")
    name = str(asset.get("name") or f"{asset.get('id')}.file").strip()
    return [
        _rich_text_block(
            " ",
            "atomic",
            data={"type": "DISK", "data": {"name": name, "quote_id": quote_id, "uploading": False}},
        ),
        _rich_text_block(""),
    ]


def _asset_blocks_from_markdown_line(
    line: str,
    uploaded_assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]] | None:
    image = ASSET_IMAGE_LINE_RE.match(line)
    if image:
        asset = _require_uploaded_asset(uploaded_assets, image.group(2), "image")
        return _image_asset_blocks(asset)

    link = ASSET_LINK_LINE_RE.match(line)
    if link:
        asset = _require_uploaded_asset(uploaded_assets, link.group(2), "attachment")
        return _attachment_asset_blocks(asset)

    if "asset://" in line:
        raise ValueError(
            "Markdown asset:// 引用必须单独占一行，图片用 ![alt](asset://id)，附件用 [name](asset://id)"
        )
    return None


def markdown_to_rich_text_raw(
    markdown: str,
    *,
    uploaded_assets: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Convert a conservative Markdown subset to XiaoYa Draft.js raw JSON."""
    blocks: list[dict[str, Any]] = []
    in_code_block = False
    code_lines: list[str] = []
    uploaded_assets = uploaded_assets or {}

    def flush_code_block() -> None:
        nonlocal code_lines
        if not code_lines:
            blocks.append(_rich_text_block("", "code-block"))
        else:
            for code_line in code_lines:
                blocks.append(_rich_text_block(code_line, "code-block"))
        code_lines = []

    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            if in_code_block:
                flush_code_block()
                in_code_block = False
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not line:
            blocks.append(_rich_text_block(""))
            continue

        asset_blocks = _asset_blocks_from_markdown_line(line.strip(), uploaded_assets)
        if asset_blocks is not None:
            blocks.extend(asset_blocks)
            continue

        block_type, block_markdown = _markdown_block_type_and_text(line)
        text, inline_style_ranges = _parse_inline_markdown(block_markdown)
        blocks.append(_rich_text_block(text, block_type, inline_style_ranges))

    if in_code_block:
        flush_code_block()

    if not blocks:
        blocks.append(_rich_text_block(""))

    return json.dumps({"blocks": blocks, "entityMap": {}}, ensure_ascii=False)


def dump_rich_text_raw(raw: dict[str, Any]) -> str:
    return json.dumps(raw, ensure_ascii=False)


def normalize_rich_text_input(
    *,
    text: str | None = None,
    raw: dict[str, Any] | None = None,
    markdown: str | None = None,
    assets: list[dict[str, Any]] | None = None,
    default_text: str = "",
) -> str | None:
    if raw is not None:
        return dump_rich_text_raw(raw)
    if markdown is not None:
        markdown_value = markdown or default_text
        referenced_ids = collect_markdown_asset_ids(markdown_value)
        uploaded_assets = None
        if referenced_ids:
            from . import upload

            uploaded_assets = upload.upload_rich_text_assets(assets, referenced_ids)
        return markdown_to_rich_text_raw(markdown_value, uploaded_assets=uploaded_assets)
    if text is None:
        return None
    return plain_text_to_rich_text_raw(text or default_text)


def _quote_id_from_url(url: str) -> str | None:
    match = CLOUD_FILE_ID_RE.search(url)
    return match.group(1) if match else None


def _utf16_offset_to_index(text: str, target_offset: int) -> int:
    offset = 0
    for index, char in enumerate(text):
        if offset >= target_offset:
            return index
        offset += _utf16_len(char)
    return len(text)


def _apply_inline_markdown(text: str, ranges: list[dict[str, Any]]) -> str:
    result = text
    normalized_ranges = []
    for style_range in ranges or []:
        marker = MARKDOWN_INLINE_MARKERS.get(style_range.get("style"))
        if not marker:
            continue
        start = _utf16_offset_to_index(text, int(style_range.get("offset") or 0))
        end = _utf16_offset_to_index(
            text,
            int(style_range.get("offset") or 0) + int(style_range.get("length") or 0),
        )
        normalized_ranges.append((start, end, marker))
    for start, end, (open_marker, close_marker) in sorted(normalized_ranges, reverse=True):
        result = f"{result[:start]}{open_marker}{result[start:end]}{close_marker}{result[end:]}"
    return result


def _markdown_for_text_block(block: dict[str, Any]) -> str:
    text = _apply_inline_markdown(block.get("text", ""), block.get("inlineStyleRanges", []))
    block_type = block.get("type")
    if block_type in MARKDOWN_HEADERS:
        return f"{MARKDOWN_HEADERS[block_type]} {text}".rstrip()
    if block_type == "unordered-list-item":
        return f"- {text}".rstrip()
    if block_type == "ordered-list-item":
        return f"1. {text}".rstrip()
    if block_type == "blockquote":
        return f"> {text}".rstrip()
    return text


def _atomic_block_to_markdown(
    block: dict[str, Any],
    *,
    image_count: int,
    file_count: int,
) -> tuple[str, dict[str, Any] | None]:
    data = block.get("data") or {}
    block_data = data.get("data") if isinstance(data.get("data"), dict) else {}
    data_type = str(data.get("type") or block_data.get("type") or "").upper()

    if data_type == "IMAGE":
        url = str(data.get("src") or block_data.get("src") or "").strip()
        quote_id = _quote_id_from_url(url) if url else None
        asset_id = f"img_{image_count}"
        name = str(data.get("name") or block_data.get("name") or f"image_{image_count}")
        asset = {"id": asset_id, "type": "image", "name": name}
        if quote_id:
            asset["quote_id"] = quote_id
        if url:
            asset["url"] = url
        return f"![{name}](asset://{asset_id})", asset

    if data_type == "DISK":
        quote_id = str(block_data.get("quote_id") or data.get("quote_id") or "").strip()
        name = str(block_data.get("name") or data.get("name") or f"file_{file_count}")
        url = f"{DOWNLOAD_URL}/cloud/file_access/{quote_id}" if quote_id else ""
        asset_id = f"file_{file_count}"
        asset = {"id": asset_id, "type": "attachment", "name": name}
        if quote_id:
            asset["quote_id"] = quote_id
        if url:
            asset["url"] = url
        return f"[{name}](asset://{asset_id})", asset

    return block.get("text", ""), None


def _join_markdown_parts(parts: list[str]) -> str:
    return "\n\n".join(part for part in parts if part)


def rich_text_to_markdown_document(value: Any) -> dict[str, Any]:
    parsed = load_rich_text_value(value)
    if not is_rich_text_document(parsed):
        return {"markdown": str(parsed or ""), "assets": []}

    parts: list[str] = []
    assets: list[dict[str, Any]] = []
    code_lines: list[str] = []
    image_count = 0
    file_count = 0

    def flush_code_lines() -> None:
        nonlocal code_lines
        if code_lines:
            parts.append("```\n" + "\n".join(code_lines) + "\n```")
            code_lines = []

    for block in parsed.get("blocks") or []:
        if block.get("type") == "code-block":
            code_lines.append(block.get("text", ""))
            continue
        flush_code_lines()

        if block.get("type") == "atomic":
            data_type = str((block.get("data") or {}).get("type") or "").upper()
            if data_type == "IMAGE":
                image_count += 1
            elif data_type == "DISK":
                file_count += 1
            markdown, asset = _atomic_block_to_markdown(
                block, image_count=image_count, file_count=file_count
            )
            if markdown:
                parts.append(markdown)
            if asset:
                assets.append(asset)
            continue

        parts.append(_markdown_for_text_block(block))

    flush_code_lines()
    return {"markdown": _join_markdown_parts(parts), "assets": assets}


def render_rich_text_output(value: Any, parse_mode: str = "plain") -> Any:
    parsed = load_rich_text_value(value)
    if parse_mode == "raw":
        return parsed
    if parse_mode == "markdown":
        return rich_text_to_markdown_document(parsed)
    if parse_mode != "plain":
        raise ValueError("parse_mode 仅支持 plain、raw 或 markdown")
    return rich_text_to_plain_text(parsed)
