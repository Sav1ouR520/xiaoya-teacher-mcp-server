"""资源删除 MCP 工具"""

import requests
from typing import Annotated
from pydantic import Field

from ...config import MAIN_URL, headers, MCP
from ...utils.response import ResponseUtil


@MCP.tool()
def delete_course_resource(
    group_id: Annotated[str, Field(description="课程组id")],
    node_id: Annotated[str, Field(description="要删除的资源节点id")],
) -> dict:
    """删除教育资源"""
    try:
        response = requests.post(
            f"{MAIN_URL}/resource/delResource",
            json={"node_id": str(node_id), "group_id": str(group_id)},
            headers=headers(),
        ).json()

        if response.get("success"):
            return ResponseUtil.success(None, "资源删除成功")
        else:
            return ResponseUtil.error(
                f"删除教育资源失败: {response.get('msg') or response.get('message', '未知错误')}"
            )
    except Exception as e:
        return ResponseUtil.error("删除教育资源时发生异常", e)
