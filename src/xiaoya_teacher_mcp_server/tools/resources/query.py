"""资源查询 MCP 工具"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated, Any, Optional
from urllib.parse import quote

import requests
from markitdown import MarkItDown
from pydantic import Field

from ... import field_descriptions as desc
from ...config import DOWNLOAD_URL, MAIN_URL, MCP
from ...utils.client import (
    APIRequestError,
    expect_success,
    get_json,
)
from ...utils.response import ResponseUtil
from .normalize import build_resource_map, build_resource_tree


def _fetch_course_resources_response(group_id: str) -> dict:
    response = get_json(
        f"{MAIN_URL}/resource/queryCourseResources/v2",
        params={"group_id": str(group_id)},
    )
    return response


def _load_course_resources(group_id: str) -> list[dict]:
    response = _fetch_course_resources_response(group_id)
    try:
        return expect_success(response)
    except APIRequestError as exc:
        raise APIRequestError(f"查询课程资源失败: {exc}") from exc


def _load_course_resource_map(
    group_id: str, detail_level: str = "full"
) -> dict[str, dict[str, Any]]:
    return build_resource_map(_load_course_resources(group_id), detail_level=detail_level)


def _sort_position_map(items: list[dict]) -> dict[str, int]:
    return {item["id"]: item.get("sort_position", 0) for item in items}


def _get_download_url(paper_id: str, filename: str) -> str:
    response = get_json(
        f"{DOWNLOAD_URL}/cloud/file_down/{paper_id}/v2?filename={quote(filename)}"
    )
    try:
        return expect_success(response)["download_url"]
    except APIRequestError as exc:
        raise APIRequestError(
            f"获取文件下载链接失败 (文件名: {filename}): {exc}"
        ) from exc


def _fetch_download_response(
    paper_id: str, filename: str, *, stream: bool = False
) -> requests.Response:
    response = requests.get(_get_download_url(paper_id, filename), stream=stream, timeout=20)
    response.raise_for_status()
    return response


def _build_resource_summary_view(raw_data: list[dict[str, Any]], view_mode: str) -> Any:
    if view_mode == "flat":
        sort_positions = _sort_position_map(raw_data)
        flat_list = list(build_resource_map(raw_data, detail_level="summary").values())
        flat_list.sort(key=lambda item: sort_positions.get(item["id"], 0))
        return flat_list
    return build_resource_tree(raw_data, detail_level="summary")


def _query_course_resource_map(group_id: str, detail_level: str = "full") -> dict:
    try:
        resource_map = _load_course_resource_map(group_id, detail_level=detail_level)
        return ResponseUtil.success(
            resource_map, f"成功获取课程资源,共{len(resource_map)}项"
        )
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("查询课程资源时发生异常", e)


@MCP.tool()
def query_course_resources(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    detail_level: Annotated[
        str,
        Field(
            description=desc.RESOURCE_DETAIL_LEVEL_DESC,
            default="summary",
            pattern="^(summary|full|raw)$",
        ),
    ] = "summary",
) -> dict:
    """获取课程资源；默认返回摘要，明细请设 detail_level=full/raw"""
    return _query_course_resource_map(group_id, detail_level=detail_level)


@MCP.tool()
def query_resource_attributes(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    resource_id: Annotated[str, Field(description=desc.RESOURCE_ID_DESC)],
    detail_level: Annotated[
        str,
        Field(
            description=desc.RESOURCE_DETAIL_LEVEL_DESC,
            default="full",
            pattern="^(summary|full|raw)$",
        ),
    ] = "full",
) -> dict:
    """根据group_id和resource_id获取对应资源的属性"""
    try:
        target = _load_course_resource_map(group_id, detail_level=detail_level).get(resource_id)
        if not target:
            return ResponseUtil.error(f"未找到id: {resource_id} 对应的课程资源")
        return ResponseUtil.success(target, f"查询成功: id={resource_id}")
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("查询课程资源属性时发生异常", e)


@MCP.tool()
def query_course_resources_summary(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    view_mode: Annotated[
        str,
        Field(
            description=desc.RESOURCE_VIEW_MODE_DESC, default="tree", pattern="^(tree|flat)$"
        ),
    ] = "tree",
) -> dict:
    """获取课程资源摘要(推荐 AI 默认使用)"""
    try:
        raw_data = _load_course_resources(group_id)
        summary_data = _build_resource_summary_view(raw_data, view_mode)
        if view_mode == "flat":
            return ResponseUtil.success(
                summary_data, f"课程资源(flat)查询成功, 共{len(summary_data)}项"
            )
        return ResponseUtil.success(
            summary_data, f"课程资源简要信息查询成功,共{len(raw_data)}项资源"
        )
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("查询课程资源简要信息时发生异常", e)


@MCP.tool()
def query_group_order_setting(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
) -> dict:
    """查询课程目录排序设置"""
    try:
        data = expect_success(
            get_json(
                f"{MAIN_URL}/group_order_setting",
                params={"group_id": str(group_id)},
            )
        )
        return ResponseUtil.success(data, "课程目录排序设置查询成功")
    except APIRequestError as e:
        return ResponseUtil.error("查询课程目录排序设置失败", e)


@MCP.tool()
def query_resource_folder_snapshot(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    parent_id: Annotated[str, Field(description=desc.PARENT_ID_DESC)],
) -> dict:
    """查询指定文件夹下的直接子资源快照"""
    try:
        children = [
            resource
            for resource in _load_course_resource_map(group_id, detail_level="full").values()
            if resource.get("parent_id") == str(parent_id)
        ]
        children.sort(key=lambda item: item.get("sort_position", 0))
        snapshot = [
            {
                "id": item["id"],
                "paper_id": item.get("paper_id"),
                "name": item["name"],
                "type": item.get("type_name"),
                "sort_position": item.get("sort_position"),
                "public": item.get("public"),
                "download": item.get("download"),
                "published": item.get("published"),
                "finish_teaching": item.get("finish_teaching"),
            }
            for item in children
        ]
        return ResponseUtil.success(
            {
                "parent_id": str(parent_id),
                "child_count": len(snapshot),
                "children": snapshot,
            },
            "文件夹资源快照查询成功",
        )
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("查询文件夹资源快照失败", e)


@MCP.tool()
def download_file(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_FILE_DESC)],
    filename: Annotated[str, Field(description=desc.FILENAME_DESC)],
    save_path: Annotated[
        Optional[str],
        Field(description=desc.SAVE_PATH_DESC, default=None),
    ] = None,
) -> dict:
    """获取下载链接并自动下载文件内容,保存到本地磁盘"""
    try:
        download_response = _fetch_download_response(paper_id, filename, stream=True)

        file_path = (
            save_path
            if save_path
            else tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}").name
        )
        with open(file_path, "wb") as handle:
            handle.write(download_response.content)

        return ResponseUtil.success(
            {
                "filename": filename,
                "file_path": file_path,
                "content_type": download_response.headers["Content-Type"],
            },
            f"文件下载成功: {file_path}",
        )
    except (APIRequestError, OSError, requests.RequestException) as e:
        return ResponseUtil.error("文件下载时发生异常", e)


@MCP.tool()
def read_file_by_markdown(
    paper_id: Annotated[
        Optional[str], Field(description=desc.PAPER_ID_FILE_DESC, default=None)
    ] = None,
    filename: Annotated[
        Optional[str], Field(description=desc.FILENAME_DESC, default=None)
    ] = None,
    file_path: Annotated[
        Optional[str], Field(description=desc.FILE_PATH_DESC, default=None)
    ] = None,
) -> dict:
    """使用markitdown工具读取本地文件路径(提供file_path)或小雅资源(需同时提供paper_id和filename)的文件内容并转换为markdown格式"""
    try:
        if file_path:
            result = MarkItDown().convert(Path(file_path))
            return ResponseUtil.success(
                {"content": result.text_content},
                f"本地文件转换为markdown成功: {file_path}",
            )

        if paper_id and filename:
            result = MarkItDown().convert(
                _fetch_download_response(paper_id, filename, stream=False)
            )
            return ResponseUtil.success(
                {"content": result.text_content},
                f"文件下载且转换为markdown成功: {filename}",
            )

        return ResponseUtil.error("请提供file_path或者同时提供paper_id和filename")
    except (APIRequestError, OSError, requests.RequestException, ValueError) as e:
        return ResponseUtil.error("文件转换为markdown时发生异常", e)
