"""资源创建 MCP 工具"""

import requests
from typing import Annotated
from pydantic import Field

from ...types.types import ResourceType
from ...config import MAIN_URL, headers, MCP
from ...utils.response import ResponseUtil


@MCP.tool()
def create_course_resource(
    group_id: Annotated[str, Field(description="课程组id")],
    type_val: Annotated[
        ResourceType,
        Field(
            description="资源类型(1=文件夹,2=笔记,3=思维导图,6=文件,7=作业,11=教学设计)"
        ),
    ],
    parent_id: Annotated[str, Field(description="父资源id")],
    name: Annotated[str, Field(description="资源名称")],
) -> dict:
    """创建新的教育资源"""
    try:
        response = requests.post(
            f"{MAIN_URL}/resource/addResource",
            json={
                "type": str(type_val),
                "parent_id": str(parent_id),
                "group_id": str(group_id),
                "name": name,
            },
            headers=headers(),
        ).json()
        if response.get("success"):
            resource_data = {
                key: response["data"][key]
                for key in [
                    "id",
                    "parent_id",
                    "name",
                    "type",
                    "path",
                    "mimetype",
                    "sort_position",
                    "created_at",
                    "updated_at",
                ]
            }
            resource_data["paper_id"] = response["data"]["quote_id"]
            resource_data["type_name"] = ResourceType.get(
                response["data"]["type"], "unknown"
            )
            return ResponseUtil.success(resource_data, "资源创建成功")
        else:
            return ResponseUtil.error(
                f"创建教育资源失败: {response.get('msg') or response.get('message', '未知错误')}"
            )
    except Exception as e:
        return ResponseUtil.error("创建教育资源时发生异常", e)
