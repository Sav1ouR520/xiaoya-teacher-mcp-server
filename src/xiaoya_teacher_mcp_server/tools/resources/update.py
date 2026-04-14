"""资源更新 MCP 工具"""

from __future__ import annotations

import json
from typing import Annotated

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...tools.resources.normalize import normalize_resource_item
from ...types.resource_models import DownloadType, VisibilityType
from ...utils.client import APIRequestError, expect_success, extract_response_message, post_json
from ...utils.response import ResponseUtil


def _run_batch_resource_update(
    *,
    node_ids: list[str],
    request_builder,
) -> tuple[list[str], list[dict[str, str]]]:
    success_ids: list[str] = []
    failed_items: list[dict[str, str]] = []
    for node_id in node_ids:
        try:
            response = request_builder(node_id)
            if response["success"]:
                success_ids.append(node_id)
            else:
                failed_items.append(
                    {"node_id": node_id, "message": extract_response_message(response)}
                )
        except APIRequestError as exc:
            failed_items.append({"node_id": node_id, "message": str(exc)})
    return success_ids, failed_items


def _batch_update_response(
    *,
    success_ids: list[str],
    failed_items: list[dict[str, str]],
    message_prefix: str,
) -> dict:
    data = {
        "success_count": len(success_ids),
        "failed_count": len(failed_items),
        "partial_success": bool(success_ids and failed_items),
        "success_ids": success_ids,
        "failed_items": failed_items,
        "failed_ids": failed_items,
    }
    message = f"{message_prefix}:成功{len(success_ids)}个,失败{len(failed_items)}个"
    if failed_items:
        return ResponseUtil.error(message, data=data)
    return ResponseUtil.success(data, message)


@MCP.tool()
def update_resource_name(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    node_id: Annotated[str, Field(description=desc.NODE_ID_DESC)],
    new_name: Annotated[str, Field(description=desc.RESOURCE_NEW_NAME_DESC)],
) -> dict:
    """更新教育资源的名称"""
    try:
        data = expect_success(
            post_json(
                f"{MAIN_URL}/resource/updateResource",
                payload={"node_id": str(node_id), "group_id": str(group_id), "name": new_name},
            )
        )
        return ResponseUtil.success(
            normalize_resource_item(data, detail_level="full"), "资源名称更新成功"
        )
    except APIRequestError as e:
        return ResponseUtil.error("更新资源名称时发生异常", e)


@MCP.tool()
def move_resource(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    node_id: Annotated[str, Field(description=desc.NODE_ID_DESC)],
    from_parent_id: Annotated[str, Field(description=desc.FROM_PARENT_ID_DESC)],
    parent_id: Annotated[str, Field(description=desc.TO_PARENT_ID_DESC)],
) -> dict:
    """将资源移动到新的父文件夹"""
    try:
        data = expect_success(
            post_json(
                f"{MAIN_URL}/resource/moveResource",
                payload={
                    "group_id": str(group_id),
                    "node_ids": [str(node_id)],
                    "from_parent_id": str(from_parent_id),
                    "parent_id": str(parent_id),
                },
            )
        )
        return ResponseUtil.success(
            [normalize_resource_item(item, detail_level="full") for item in data],
            "资源移动成功",
        )
    except APIRequestError as e:
        return ResponseUtil.error("移动资源时发生异常", e)


@MCP.tool()
def batch_update_resource_download(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    node_ids: Annotated[list[str], Field(description=desc.NODE_ID_LIST_DESC)],
    download: Annotated[DownloadType, Field(description=desc.DOWNLOAD_TYPE_DESC)],
) -> dict:
    """批量更新资源的下载属性"""
    try:
        success_ids, failed_items = _run_batch_resource_update(
            node_ids=node_ids,
            request_builder=lambda node_id: post_json(
                f"{MAIN_URL}/resource/batch/update/attribute",
                payload={
                    "group_id": str(group_id),
                    "node_id": str(node_id),
                    "download": int(download),
                },
            ),
        )
        return _batch_update_response(
            success_ids=success_ids,
            failed_items=failed_items,
            message_prefix="资源下载属性批量更新完成",
        )
    except APIRequestError as e:
        return ResponseUtil.error("批量更新资源下载属性时发生异常", e)


@MCP.tool()
def batch_update_resource_visibility(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    activity_node_ids: Annotated[list[str], Field(description=desc.RESOURCE_ID_LIST_DESC)],
    pub: Annotated[VisibilityType, Field(description=desc.VISIBILITY_TYPE_DESC)],
) -> dict:
    """批量更新课程组内资源的可见性"""
    try:
        success_ids, failed_items = _run_batch_resource_update(
            node_ids=activity_node_ids,
            request_builder=lambda node_id: post_json(
                f"{MAIN_URL}/resource/publicResources",
                payload={"group_id": str(group_id), "activity_node_ids": str(node_id), "pub": pub},
            ),
        )
        return _batch_update_response(
            success_ids=success_ids,
            failed_items=failed_items,
            message_prefix="资源可见性批量更新完成",
        )
    except APIRequestError as e:
        return ResponseUtil.error("批量更新资源可见性时发生异常", e)


@MCP.tool()
def update_resource_sort(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    sorted_ids: Annotated[
        list[str], Field(description=desc.RESOURCE_ID_LIST_ORDER_DESC, min_length=1)
    ],
) -> dict:
    """更新课程组内资源的排序"""
    try:
        data = expect_success(
            post_json(
                f"{MAIN_URL}/resource/sortNode",
                payload={
                    "group_id": str(group_id),
                    "sort_content": json.dumps(
                        [
                            {"node_id": str(node_id), "sort_position": index}
                            for index, node_id in enumerate(sorted_ids)
                        ],
                        ensure_ascii=False,
                    ),
                },
            )
        )
        return ResponseUtil.success(
            sorted(data, key=lambda item: item["sort_position"]),
            "资源排序成功",
        )
    except APIRequestError as e:
        return ResponseUtil.error("更新资源排序时发生异常", e)
