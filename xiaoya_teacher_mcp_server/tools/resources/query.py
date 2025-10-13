"""
资源查询MCP工具

此模块为查询课程管理系统中的教育资源提供MCP工具.
"""

import requests
import tempfile
from markitdown import MarkItDown
from pathlib import Path
from typing import Annotated, Literal, Optional
from pydantic import Field
from urllib.parse import quote


from ...utils.response import ResponseUtil
from ...config import MAIN_URL, DOWNLOAD_URL, create_headers, MCP


@MCP.tool()
def query_course_resources(
    group_id: Annotated[str, Field(description="课程组id")],
    format_type: Annotated[
        Literal["tree", "flat"],
        Field(
            description='返回格式("tree"为层级式,"flat"为列表式)',
            pattern="^(tree|flat)$",
        ),
    ],
) -> dict:
    """查询特定组的所有课程资源"""
    try:
        response = requests.get(
            f"{MAIN_URL}/resource/queryCourseResources/v2",
            headers=create_headers(),
            params={"group_id": str(group_id)},
        ).json()

        if not response.get("success"):
            return ResponseUtil.error(
                f"查询课程资源失败: {response.get('msg') or response.get('message', '未知错误')}"
            )

        resources = [
            {
                key: item[key]
                for key in [
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
                ]
                if key in item
            }
            for item in response["data"]
        ]

        for idx, item in enumerate(response["data"]):
            if "link_tasks" in item and item["link_tasks"]:
                resources[idx]["link_tasks"] = [
                    {
                        (k if k != "paper_publish_id" else "publish_id"): t[k]
                        for k in [
                            "task_id",
                            "start_time",
                            "end_time",
                            "paper_publish_id",
                        ]
                        if k in t
                    }
                    for t in item["link_tasks"]
                ]

        for resource in resources:
            resource["is_folder"] = resource["mimetype"] is None
            resource["sort_position"] = resource["sort_position"]
            resource["level"] = len(resource["path"].split("/")) - 1
            if format_type == "tree" and resource["is_folder"]:
                resource["children"] = []
        resources.sort(key=lambda x: x["sort_position"])

        resource_map = {r["id"]: r for r in resources}

        def build_file_path(resource_id):
            if not resource_id or resource_id not in resource_map:
                return ""
            path_parts = []
            current = resource_map[resource_id]
            while current:
                path_parts.append(current["name"])
                parent_id = current["parent_id"]
                current = resource_map.get(parent_id) if parent_id else None
            return "/".join(reversed(path_parts))

        for resource in resources:
            resource["file_path"] = build_file_path(resource["id"])

        if format_type == "tree":
            root_resources = []
            for resource in resources:
                parent_id = resource["parent_id"]
                if parent_id in resource_map and resource_map[parent_id].get(
                    "is_folder"
                ):
                    resource_map[parent_id]["children"].append(resource)
                else:
                    root_resources.append(resource)
            return ResponseUtil.success(
                root_resources, f"课程资源树形结构查询成功,共{len(root_resources)}项"
            )

        return ResponseUtil.success(
            resources, f"课程资源列表查询成功,共{len(resources)}项"
        )
    except Exception as e:
        return ResponseUtil.error("查询课程资源时发生异常", e)


@MCP.tool()
def download_file(
    quote_id: Annotated[str, Field(description="文件quote_id")],
    filename: Annotated[str, Field(description="资源文件名")],
    save_path: Annotated[
        Optional[str],
        Field(description="文件保存路径[默认临时文件夹]", default=None),
    ] = None,
) -> dict:
    """获取下载链接并自动下载文件内容,保存到本地磁盘"""
    try:
        url = f"{DOWNLOAD_URL}/cloud/file_down/{quote_id}/v2?filename={quote(filename)}"
        response = requests.get(url, headers=create_headers()).json()
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
    quote_id: Annotated[
        Optional[str], Field(description="文件quote_id", default=None)
    ] = None,
    filename: Annotated[
        Optional[str], Field(description="资源文件名", default=None)
    ] = None,
    file_path: Annotated[
        Optional[str], Field(description="本地磁盘文件路径", default=None)
    ] = None,
) -> dict:
    """使用markitdown工具读取本地文件路径(提供file_path)或小雅资源(需同时提供quote_id和filename)的文件内容并转换为markdown格式"""
    try:
        if file_path:
            result = MarkItDown().convert(Path(file_path))
            return ResponseUtil.success(
                {"content": result.text_content},
                f"本地文件转换为markdown成功: {file_path}",
            )
        elif quote_id and filename:
            url = f"{DOWNLOAD_URL}/cloud/file_down/{quote_id}/v2?filename={quote(filename)}"
            response = requests.get(url, headers=create_headers()).json()
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
