"""资源更新 MCP 工具"""

import json
import requests
from typing import Annotated, List
from pydantic import Field

from ...types.types import ResourceType, DownloadType, VisibilityType
from ...config import MAIN_URL, headers, MCP
from ...utils.response import ResponseUtil


@MCP.tool()
def update_resource_name(
    group_id: Annotated[str, Field(description="课程组id")],
    node_id: Annotated[str, Field(description="要更新的资源节点id")],
    new_name: Annotated[str, Field(description="资源的新名称")],
) -> dict:
    """更新教育资源的名称"""
    try:
        response = requests.post(
            f"{MAIN_URL}/resource/updateResource",
            json={
                "node_id": str(node_id),
                "group_id": str(group_id),
                "name": new_name,
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
            return ResponseUtil.success(resource_data, "资源名称更新成功")
        else:
            return ResponseUtil.error(
                f"移动资源失败: {response.get('msg') or response.get('message', '未知错误')}"
            )
    except Exception as e:
        return ResponseUtil.error("更新资源名称时发生异常", e)


@MCP.tool()
def move_resource(
    group_id: Annotated[str, Field(description="课程组id")],
    node_id: Annotated[str, Field(description="要移动的资源节点id")],
    from_parent_id: Annotated[str, Field(description="当前父文件夹id")],
    parent_id: Annotated[str, Field(description="新父文件夹id")],
) -> dict:
    """将资源移动到新的父文件夹"""
    try:
        response = requests.post(
            f"{MAIN_URL}/resource/moveResource",
            json={
                "group_id": str(group_id),
                "node_ids": [str(node_id)],
                "from_parent_id": str(from_parent_id),
                "parent_id": str(parent_id),
            },
            headers=headers(),
        ).json()
        resource_data = []
        if response.get("success"):
            for data in response["data"]:
                item = {
                    key: data[key]
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
                item["paper_id"] = data["quote_id"]
                item["type_name"] = ResourceType.get(data["type"], "unknown")
                resource_data.append(item)
            return ResponseUtil.success(resource_data, "资源移动成功")
        else:
            return ResponseUtil.error(
                f"更新资源名称失败: {response.get('msg') or response.get('message', '未知错误')}"
            )
    except Exception as e:
        return ResponseUtil.error("移动资源时发生异常", e)


@MCP.tool()
def batch_update_resource_download(
    group_id: Annotated[str, Field(description="课程组id")],
    node_ids: Annotated[list[str], Field(description="资源节点id列表")],
    download: Annotated[
        DownloadType, Field(description="下载属性 1=不可下载, 2=可下载")
    ],
) -> dict:
    """批量更新资源的下载属性"""
    try:
        url = f"{MAIN_URL}/resource/batch/update/attribute"
        success_ids, failed_ids = [], []
        for node_id in node_ids:
            response = requests.post(
                url,
                json={
                    "group_id": str(group_id),
                    "node_id": str(node_id),
                    "download": int(download),
                },
                headers=headers(),
            ).json()
            if response.get("success"):
                success_ids.append(node_id)
            else:
                failed_ids.append(
                    {
                        "node_id": node_id,
                        "msg": response.get("msg")
                        or response.get("message")
                        or "未知错误",
                    }
                )
        result = {
            "success_ids": success_ids,
            "failed_ids": failed_ids,
        }
        return ResponseUtil.success(
            result,
            f"资源下载属性批量更新完成:成功{len(success_ids)}个,失败{len(failed_ids)}个",
        )
    except Exception as e:
        return ResponseUtil.error("批量更新资源下载属性时发生异常", e)


@MCP.tool()
def batch_update_resource_visibility(
    group_id: Annotated[str, Field(description="课程组id")],
    activity_node_ids: Annotated[list[str], Field(description="资源id列表")],
    pub: Annotated[
        VisibilityType, Field(description="资源可见性,1为学生不可见,2为学生可见")
    ],
) -> dict:
    """批量更新课程组内资源的可见性"""
    try:
        url = f"{MAIN_URL}/resource/publicResources"
        success_ids, failed_ids = [], []
        for nid in activity_node_ids:
            response = requests.post(
                url,
                json={
                    "group_id": str(group_id),
                    "activity_node_ids": str(nid),
                    "pub": pub,
                },
                headers=headers(),
            ).json()
            if response.get("success"):
                success_ids.append(nid)
            else:
                failed_ids.append(
                    {
                        "node_id": nid,
                        "msg": response.get("msg")
                        or response.get("message")
                        or "未知错误",
                    }
                )
        result = {
            "success_ids": success_ids,
            "failed_ids": failed_ids,
        }
        return ResponseUtil.success(
            result,
            f"资源可见性批量更新完成:成功{len(success_ids)}个,失败{len(failed_ids)}个",
        )
    except Exception as e:
        return ResponseUtil.error("批量更新资源可见性时发生异常", e)


@MCP.tool()
def update_resource_sort(
    group_id: Annotated[str, Field(description="课程组id")],
    sorted_ids: Annotated[
        List[str], Field(description="按所需顺序排列的资源id列表", min_length=1)
    ],
) -> dict:
    """更新课程组内资源的排序"""
    try:
        response = requests.post(
            f"{MAIN_URL}/resource/sortNode",
            json={
                "group_id": str(group_id),
                "sort_content": json.dumps(
                    [
                        {"node_id": str(node_id), "sort_position": index}
                        for index, node_id in enumerate(sorted_ids)
                    ],
                    ensure_ascii=False,
                ),
            },
            headers=headers(),
        ).json()

        if response.get("success"):
            sorted_data = sorted(response["data"], key=lambda x: x["sort_position"])
            return ResponseUtil.success(sorted_data, "资源排序成功")
        else:
            return ResponseUtil.error(
                f"更新资源排序失败: {response.get('msg') or response.get('message', '未知错误')}"
            )
    except Exception as e:
        return ResponseUtil.error("更新资源排序时发生异常", e)
