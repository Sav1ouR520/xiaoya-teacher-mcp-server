"""资源创建 MCP 工具"""

from typing import Annotated
from pydantic import Field

from ... import field_descriptions as desc
from ...types.resource_models import ResourceType
from ...config import MAIN_URL, MCP
from ...tools.resources.normalize import normalize_resource_item
from ...utils.client import APIRequestError, extract_response_message, post_json
from ...utils.response import ResponseUtil


@MCP.tool()
def create_course_resource(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    type_val: Annotated[
        ResourceType,
        Field(description=desc.RESOURCE_TYPE_DESC),
    ],
    parent_id: Annotated[str, Field(description=desc.PARENT_ID_DESC)],
    name: Annotated[str, Field(description=desc.RESOURCE_NAME_DESC)],
) -> dict:
    """创建新的教育资源"""
    try:
        response = post_json(
            f"{MAIN_URL}/resource/addResource",
            payload={
                "type": str(type_val),
                "parent_id": str(parent_id),
                "group_id": str(group_id),
                "name": name,
            },
        )
        if response.get("success"):
            resource_data = normalize_resource_item(response["data"], detail_level="full")
            return ResponseUtil.success(resource_data, "资源创建成功")
        return ResponseUtil.error(
            f"创建教育资源失败: {extract_response_message(response)}"
        )
    except APIRequestError as e:
        return ResponseUtil.error("创建教育资源时发生异常", e)
