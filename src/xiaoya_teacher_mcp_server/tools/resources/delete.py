"""资源删除 MCP 工具"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...utils.client import APIRequestError, expect_success, post_json
from ...utils.response import ResponseUtil


@MCP.tool()
def delete_course_resource(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    node_id: Annotated[str, Field(description=desc.NODE_ID_DESC)],
) -> dict:
    """删除教育资源"""
    try:
        expect_success(post_json(
            f"{MAIN_URL}/resource/delResource",
            payload={"node_id": str(node_id), "group_id": str(group_id)},
        ))
        return ResponseUtil.success(None, "资源删除成功")
    except APIRequestError as e:
        return ResponseUtil.error("删除教育资源时发生异常", e)
