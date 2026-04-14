"""小雅富文本转换工具。"""

from __future__ import annotations

import json
import random
import string
from typing import Any


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
        return "\n".join(block.get("text", "") for block in blocks)
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


def dump_rich_text_raw(raw: dict[str, Any]) -> str:
    return json.dumps(raw, ensure_ascii=False)


def normalize_rich_text_input(
    *,
    text: str | None = None,
    raw: dict[str, Any] | None = None,
    default_text: str = "",
) -> str | None:
    if raw is not None:
        return dump_rich_text_raw(raw)
    if text is None:
        return None
    return plain_text_to_rich_text_raw(text or default_text)


def render_rich_text_output(value: Any, parse_mode: str = "plain") -> Any:
    parsed = load_rich_text_value(value)
    if parse_mode == "raw":
        return parsed
    if parse_mode != "plain":
        raise ValueError("parse_mode 仅支持 plain 或 raw")
    return rich_text_to_plain_text(parsed)
