"""资源创建 MCP 工具"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...tools.resources.normalize import normalize_resource_item
from ...types.resource_models import ResourceType
from ...utils.client import APIRequestError, expect_success, post_json
from ...utils.response import ResponseUtil


@MCP.tool()
def create_course_resource(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    type_val: Annotated[ResourceType, Field(description=desc.RESOURCE_TYPE_DESC)],
    parent_id: Annotated[str, Field(description=desc.PARENT_ID_DESC)],
    name: Annotated[str, Field(description=desc.RESOURCE_NAME_DESC)],
) -> dict:
    """创建新的教育资源"""
    try:
        data = expect_success(
            post_json(
                f"{MAIN_URL}/resource/addResource",
                payload={
                    "type": str(type_val),
                    "parent_id": str(parent_id),
                    "group_id": str(group_id),
                    "name": name,
                },
            )
        )
        return ResponseUtil.success(
            normalize_resource_item(data, detail_level="full"), "资源创建成功"
        )
    except APIRequestError as e:
        return ResponseUtil.error("创建教育资源时发生异常", e)
