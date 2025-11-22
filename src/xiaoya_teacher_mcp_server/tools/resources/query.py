"""资源查询 MCP 工具"""

import requests
import tempfile
from markitdown import MarkItDown
from pathlib import Path
from typing import Annotated, Optional
from pydantic import Field
from urllib.parse import quote

from ...types.types import ResourceType
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, DOWNLOAD_URL, headers, MCP


def _fetch_course_resources_raw(group_id: str) -> dict:
    """获取课程资源的原始API响应"""
    response = requests.get(
        f"{MAIN_URL}/resource/queryCourseResources/v2",
        headers=headers(),
        params={"group_id": str(group_id)},
    ).json()

    if not response.get("success"):
        return ResponseUtil.error(
            f"查询课程资源失败: {response.get('msg') or response.get('message', '未知错误')}"
        )
    return response


def _query_course_resources(group_id: str) -> dict:
    """根据group_id获取全部的课程资源"""
    try:
        response = _fetch_course_resources_raw(group_id)
        if not response.get("success"):
            return response

        resource_map = {}
        for item in response["data"]:
            res = {
                ("paper_id" if k == "quote_id" else k): item[k]
                for k in (
                    "id",
                    "parent_id",
                    "quote_id",
                    "name",
                    "type",
                    "path",
                    "mimetype",
                    "sort_position",
                    "created_at",
                    "updated_at",
                )
                if k in item
            }
            res["level"] = (
                len(res.get("path", "").split("/")) - 1 if res.get("path") else 0
            )
            resource_map[res["id"]] = res

        for item in response["data"]:
            if item.get("link_tasks"):
                res = resource_map[item["id"]]
                res["link_tasks"] = [
                    {
                        ("publish_id" if k == "paper_publish_id" else k): t[k]
                        for k in (
                            "task_id",
                            "start_time",
                            "end_time",
                            "paper_publish_id",
                        )
                        if k in t
                    }
                    for t in item["link_tasks"]
                ]

        def build_file_path(res_id):
            path = []
            cur = resource_map.get(res_id)
            while cur:
                path.append(cur.get("name", ""))
                cur = resource_map.get(cur.get("parent_id"))
            return "/".join(reversed([i for i in path if i]))

        for res in resource_map.values():
            res["file_path"] = build_file_path(res["id"])

        return ResponseUtil.success(
            resource_map, f"成功获取课程资源,共{len(resource_map)}项"
        )
    except Exception as e:
        return ResponseUtil.error("查询课程资源时发生异常", e)


@MCP.tool()
def query_resource_attributes(
    group_id: Annotated[str, Field(description="课程组id")],
    resource_id: Annotated[str, Field(description="资源id")],
) -> dict:
    """根据group_id和resource_id获取对应资源的属性"""
    try:
        result = _query_course_resources(group_id)
        if not result.get("success"):
            return result

        target = result["data"].get(resource_id)
        if not target:
            return ResponseUtil.error(f"未找到id: {resource_id} 对应的课程资源")

        return ResponseUtil.success(target, f"查询成功: id={resource_id}")
    except Exception as e:
        return ResponseUtil.error("查询课程资源属性时发生异常", e)


@MCP.tool()
def query_course_resources_summary(
    group_id: Annotated[str, Field(description="课程组id")],
    view_mode: Annotated[
        str,
        Field(
            description="视图模式(tree/flat)", default="tree", pattern="^(tree|flat)$"
        ),
    ] = "tree",
) -> dict:
    """获取课程所有资源的简要信息"""
    try:
        response = _fetch_course_resources_raw(group_id)
        if not response.get("success"):
            return response

        raw_data = response["data"]

        if view_mode == "flat":
            flat_list = [
                {
                    "id": item["id"],
                    "paper_id": item["quote_id"],
                    "name": item["name"],
                    "type": ResourceType.get(item["type"]),
                }
                for item in sorted(raw_data, key=lambda i: i["sort_position"])
            ]
            return ResponseUtil.success(
                flat_list, f"课程资源(flat)查询成功, 共{len(flat_list)}项"
            )

        id_to_sort_position = {item["id"]: item["sort_position"] for item in raw_data}

        resource_brief_list = [
            {
                "id": item["id"],
                "paper_id": item["quote_id"],
                "name": item["name"],
                "type": ResourceType.get(item["type"]),
                **(
                    {"children": []}
                    if item["type"] == ResourceType.FOLDER.value
                    else {}
                ),
            }
            for item in raw_data
        ]
        resource_brief_list.sort(key=lambda r: id_to_sort_position[r["id"]])
        id_to_resource_brief = {r["id"]: r for r in resource_brief_list}

        for item in raw_data:
            parent_id = item["parent_id"]
            if (
                parent_id
                and parent_id in id_to_resource_brief
                and "children" in id_to_resource_brief[parent_id]
            ):
                id_to_resource_brief[parent_id]["children"].append(
                    id_to_resource_brief[item["id"]]
                )

        root_resources = [
            resource_brief
            for resource_id, resource_brief in id_to_resource_brief.items()
            if not any(
                resource_id == item["id"]
                and item.get("parent_id") in id_to_resource_brief
                for item in raw_data
            )
        ]

        return ResponseUtil.success(
            root_resources, f"课程资源简要信息查询成功,共{len(raw_data)}项资源"
        )
    except Exception as e:
        return ResponseUtil.error("查询课程资源简要信息时发生异常", e)


@MCP.tool()
def download_file(
    paper_id: Annotated[str, Field(description="文件paper_id")],
    filename: Annotated[str, Field(description="资源文件名")],
    save_path: Annotated[
        Optional[str],
        Field(description="文件保存路径[默认临时文件夹]", default=None),
    ] = None,
) -> dict:
    """获取下载链接并自动下载文件内容,保存到本地磁盘"""
    try:
        url = f"{DOWNLOAD_URL}/cloud/file_down/{paper_id}/v2?filename={quote(filename)}"
        response = requests.get(url, headers=headers()).json()
        if not response.get("success"):
            return ResponseUtil.error(
                f"获取文件下载链接失败 (文件名: {filename}): {response.get('msg', {}).get('message', '未知错误')}"
            )

        download_response = requests.get(response["data"]["download_url"], stream=True)
        download_response.raise_for_status()

        file_path = (
            save_path
            if save_path
            else tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}").name
        )

        with open(file_path, "wb") as f:
            f.write(download_response.content)

        return ResponseUtil.success(
            {
                "filename": filename,
                "file_path": file_path,
                "content_type": download_response.headers["Content-Type"],
            },
            f"文件下载成功: {file_path}",
        )
    except Exception as e:
        return ResponseUtil.error("文件下载时发生异常", e)


@MCP.tool()
def read_file_by_markdown(
    paper_id: Annotated[
        Optional[str], Field(description="文件paper_id", default=None)
    ] = None,
    filename: Annotated[
        Optional[str], Field(description="资源文件名", default=None)
    ] = None,
    file_path: Annotated[
        Optional[str], Field(description="本地磁盘文件路径", default=None)
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
        elif paper_id and filename:
            url = f"{DOWNLOAD_URL}/cloud/file_down/{paper_id}/v2?filename={quote(filename)}"
            response = requests.get(url, headers=headers()).json()
            if not response.get("success"):
                return ResponseUtil.error(f"获取文件下载链接失败,文件名:{filename}")

            download_response = requests.get(response["data"]["download_url"])
            download_response.raise_for_status()
            result = MarkItDown().convert(download_response)
            return ResponseUtil.success(
                {"content": result.text_content},
                f"文件下载且转换为markdown成功: {filename}",
            )
        else:
            return ResponseUtil.error("请提供file_path或者同时提供file_id和filename")

    except Exception as e:
        return ResponseUtil.error("文件转换为markdown时发生异常", e)
