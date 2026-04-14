"""课程资源解析工具。"""

from __future__ import annotations

from typing import Any

from ...types.resource_models import ResourceType

RESOURCE_FULL_FIELDS = (
    "id",
    "parent_id",
    "name",
    "type",
    "path",
    "mimetype",
    "sort_position",
    "created_at",
    "updated_at",
    "group_id",
    "creator",
    "author",
    "download",
    "public",
    "published",
    "finish_teaching",
    "resource_type",
    "property",
    "tag",
)


def normalize_link_task(link_task: dict[str, Any]) -> dict[str, Any]:
    return {
        ("publish_id" if key == "paper_publish_id" else key): link_task[key]
        for key in ("task_id", "start_time", "end_time", "paper_publish_id")
        if key in link_task
    }


def normalize_resource_item(item: dict[str, Any], detail_level: str = "full") -> dict[str, Any]:
    if detail_level == "raw":
        return dict(item)

    normalized = {
        ("paper_id" if key == "quote_id" else key): item[key]
        for key in RESOURCE_FULL_FIELDS + ("quote_id",)
        if key in item
    }
    normalized["level"] = (
        len(normalized.get("path", "").split("/")) - 1 if normalized.get("path") else 0
    )
    normalized["type_name"] = ResourceType.get(item["type"], "unknown")

    if detail_level == "summary":
        return {
            "id": normalized["id"],
            "paper_id": normalized.get("paper_id"),
            "name": normalized["name"],
            "type": normalized["type_name"],
        }

    if item.get("link_tasks"):
        normalized["link_tasks"] = [
            normalize_link_task(link_task) for link_task in item["link_tasks"]
        ]
    return normalized


def _is_folder_resource(resource: dict[str, Any]) -> bool:
    resource_type = resource["type"]
    return resource_type in (ResourceType.FOLDER.value, ResourceType.get(ResourceType.FOLDER.value))


def build_file_path(resource_id: str, resource_map: dict[str, dict[str, Any]]) -> str:
    path = []
    current = resource_map.get(resource_id)
    while current:
        path.append(current["name"])
        current = resource_map.get(current.get("parent_id"))
    return "/".join(reversed([part for part in path if part]))


def build_resource_map(
    items: list[dict[str, Any]], detail_level: str = "full"
) -> dict[str, dict[str, Any]]:
    resource_map = {
        normalized["id"]: normalized
        for normalized in (
            normalize_resource_item(item, detail_level=detail_level) for item in items
        )
    }

    if detail_level == "full":
        for resource in resource_map.values():
            resource["file_path"] = build_file_path(resource["id"], resource_map)
    return resource_map


def build_resource_tree(
    items: list[dict[str, Any]], detail_level: str = "summary"
) -> list[dict[str, Any]]:
    id_to_sort_position = {item["id"]: item["sort_position"] for item in items}
    item_ids = set(id_to_sort_position)
    resource_list = [normalize_resource_item(item, detail_level) for item in items]

    if detail_level != "raw":
        for resource in resource_list:
            if _is_folder_resource(resource):
                resource["children"] = []

    resource_list.sort(key=lambda resource: id_to_sort_position[resource["id"]])
    id_to_resource = {resource["id"]: resource for resource in resource_list}

    for item in items:
        parent_id = item.get("parent_id")
        parent = id_to_resource.get(parent_id)
        if parent and "children" in parent:
            parent["children"].append(id_to_resource[item["id"]])

    return [
        resource
        for resource_id, resource in id_to_resource.items()
        if resource_id in item_ids and resource.get("parent_id") not in item_ids
    ]
