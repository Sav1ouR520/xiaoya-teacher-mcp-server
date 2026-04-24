import os
import uuid

import pytest
from dotenv import find_dotenv, load_dotenv

from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.resources import (
    create as resource_create,
)
from xiaoya_teacher_mcp_server.tools.resources import (
    delete as resource_delete,
)
from xiaoya_teacher_mcp_server.tools.resources import (
    query as resource_query,
)
from xiaoya_teacher_mcp_server.tools.resources import (
    update as resource_update,
)
from xiaoya_teacher_mcp_server.types import ResourceType

load_dotenv(find_dotenv())

requires_live_auth = pytest.mark.skipif(
    not (
        os.getenv("XIAOYA_AUTH_TOKEN")
        or (os.getenv("XIAOYA_ACCOUNT") and os.getenv("XIAOYA_PASSWORD"))
    ),
    reason="需要配置小雅认证环境变量",
)


def _flatten_resources(resource_tree):
    """递归扁平化资源树"""
    result = []
    for resource in resource_tree:
        result.append(resource)
        if "children" in resource and resource["children"]:
            result.extend(_flatten_resources(resource["children"]))
    return result


def _find_root_resource(resource_tree):
    """递归查找名为 'root' 的资源"""
    for resource in resource_tree:
        if resource.get("name") == "root":
            return resource
        if "children" in resource and resource["children"]:
            found = _find_root_resource(resource["children"])
            if found:
                return found
    return None


def _get_group_and_root() -> tuple:
    """获取group_id和root资源id"""
    group_id = group_query.query_teacher_groups()["data"][0]["group_id"]
    summary_result = resource_query.query_course_resources_summary(group_id)
    assert summary_result["success"], f"查询资源失败: {summary_result}"

    root = _find_root_resource(summary_result["data"])
    assert root is not None, "找不到root资源"

    # 获取 root 资源的完整属性以获取 id
    root_attr = resource_query.query_resource_attributes(group_id, root["id"])
    assert root_attr["success"], f"查询root资源属性失败: {root_attr}"
    return group_id, root_attr["data"]["id"]


@requires_live_auth
def test_query_resource():
    """测试查询课程资源列表"""
    group_id, _ = _get_group_and_root()
    result = resource_query.query_course_resources_summary(group_id)
    assert result["success"]
    all_resources = _flatten_resources(result["data"])
    print(f"\n✓ 查询成功,共{len(all_resources)}个资源")


@requires_live_auth
def test_create_update_and_delete():
    """测试创建、更新和删除资源"""
    group_id, root_id = _get_group_and_root()
    resource_name = f"test_folder_{uuid.uuid4().hex[:8]}"

    created = resource_create.create_course_resource(
        group_id, ResourceType.FOLDER, root_id, resource_name
    )
    assert created["success"]
    node_id = created["data"]["id"]

    try:
        # 1. 更新名称
        new_name = f"{resource_name}_renamed"
        updated = resource_update.update_resource_name(group_id, node_id, new_name)
        assert updated["success"]
        assert updated["data"]["name"] == new_name
        print(f"\n1. ✓ 创建并更新资源名称成功: {resource_name} -> {new_name}")

        # 2. 验证更新生效
        summary_result = resource_query.query_course_resources_summary(group_id)
        assert summary_result["success"]
        all_resources = _flatten_resources(summary_result["data"])
        updated_item = next((r for r in all_resources if r["id"] == node_id), None)
        if updated_item:
            # 获取完整属性以验证名称
            attr_result = resource_query.query_resource_attributes(group_id, node_id)
            assert attr_result["success"]
            assert attr_result["data"]["name"] == new_name
        print("2. ✓ 验证更新生效")

        # 3. 删除资源
        deleted = resource_delete.delete_course_resource(group_id, node_id)
        assert deleted["success"]
        summary_after = resource_query.query_course_resources_summary(group_id)
        assert summary_after["success"]
        all_resources_after = _flatten_resources(summary_after["data"])
        assert not any(r.get("id") == node_id for r in all_resources_after)
        print("3. ✓ 删除资源成功")
    finally:
        try:
            resource_delete.delete_course_resource(group_id, node_id)
        except Exception:
            pass


@requires_live_auth
def test_move_and_sort():
    """测试移动和排序资源"""
    group_id, root_id = _get_group_and_root()

    # 创建源和目标文件夹
    src_folder = resource_create.create_course_resource(
        group_id, ResourceType.FOLDER, root_id, f"src_{uuid.uuid4().hex[:8]}"
    )
    dst_folder = resource_create.create_course_resource(
        group_id, ResourceType.FOLDER, root_id, f"dst_{uuid.uuid4().hex[:8]}"
    )
    assert src_folder["success"] and dst_folder["success"]
    src_id, dst_id = src_folder["data"]["id"], dst_folder["data"]["id"]

    # 创建子资源
    child_a = resource_create.create_course_resource(
        group_id, ResourceType.FOLDER, src_id, f"child_a_{uuid.uuid4().hex[:8]}"
    )
    child_b = resource_create.create_course_resource(
        group_id, ResourceType.FOLDER, src_id, f"child_b_{uuid.uuid4().hex[:8]}"
    )
    assert child_a["success"] and child_b["success"]
    child_a_id, child_b_id = child_a["data"]["id"], child_b["data"]["id"]

    child_c_id = None
    try:
        # 1. 移动资源
        move_resp = resource_update.move_resource(
            group_id, node_id=child_b_id, from_parent_id=src_id, parent_id=dst_id
        )
        assert move_resp["success"]
        moved = next((i for i in move_resp["data"] if i["id"] == child_b_id), None)
        assert moved and moved.get("parent_id") == dst_id
        print("\n1. ✓ 移动资源成功")

        # 2. 创建新资源用于排序
        child_c = resource_create.create_course_resource(
            group_id, ResourceType.FOLDER, dst_id, f"child_c_{uuid.uuid4().hex[:8]}"
        )
        assert child_c["success"]
        child_c_id = child_c["data"]["id"]

        # 3. 更新排序
        desired_order = [child_c_id, child_b_id]
        sort_resp = resource_update.update_resource_sort(group_id, desired_order)
        assert sort_resp["success"]
        print("2. ✓ 更新排序成功")

        # 4. 验证排序
        summary_result = resource_query.query_course_resources_summary(group_id)
        assert summary_result["success"]
        all_items = _flatten_resources(summary_result["data"])
        # 需要获取每个资源的完整属性以获取 parent_id 和 sort_position
        dst_children_by_id = {}
        for item in all_items:
            attr_result = resource_query.query_resource_attributes(group_id, item["id"])
            if attr_result["success"]:
                attr_data = attr_result["data"]
                if attr_data.get("parent_id") == dst_id:
                    dst_children_by_id[attr_data["id"]] = attr_data
        ordered_ids = [
            r["id"]
            for r in sorted(dst_children_by_id.values(), key=lambda x: x.get("sort_position", 0))
        ]
        assert [
            resource_id for resource_id in ordered_ids if resource_id in desired_order
        ] == desired_order
        print("3. ✓ 验证排序正确")
    finally:
        for _id in [child_c_id, child_b_id, child_a_id, src_id, dst_id]:
            try:
                if _id:
                    resource_delete.delete_course_resource(group_id, _id)
            except Exception:
                pass


def test_query_course_resources_full_includes_extended_fields(monkeypatch):
    monkeypatch.setattr(
        resource_query,
        "_fetch_course_resources_response",
        lambda group_id: {
            "success": True,
            "data": [
                {
                    "id": "node-1",
                    "parent_id": "",
                    "quote_id": "paper-1",
                    "name": "课堂作业",
                    "type": 7,
                    "path": "root/node-1",
                    "mimetype": None,
                    "sort_position": 1,
                    "created_at": "2026-03-09T00:00:00Z",
                    "updated_at": "2026-03-09T00:00:00Z",
                    "download": 2,
                    "public": 2,
                    "published": 1,
                    "finish_teaching": 0,
                    "resource_type": 11,
                    "property": {"k": "v"},
                    "tag": "linux",
                    "link_tasks": [],
                }
            ],
        },
    )

    result = resource_query.query_course_resources("group-1", detail_level="full")

    assert result["success"]
    data = result["data"]["node-1"]
    assert data["paper_id"] == "paper-1"
    assert data["public"] == 2
    assert data["download"] == 2
    assert data["resource_type"] == 11
    assert data["tag"] == "linux"


def test_query_group_order_setting(monkeypatch):
    monkeypatch.setattr(
        resource_query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": {"is_setting": False, "setting_order": None},
        },
    )

    result = resource_query.query_group_order_setting("group-1")

    assert result["success"]
    assert result["data"] == {"is_setting": False, "setting_order": None}


def test_fetch_download_response_does_not_send_app_authorization(monkeypatch):
    captured = {}

    class DummyResponse:
        status_code = 200
        content = b"PK\x03\x04"
        headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        resource_query,
        "_get_download_url",
        lambda paper_id, filename: "https://oss.example.test/signed-url",
    )

    def fake_get(url, *, headers, stream, timeout):
        captured.update(url=url, headers=headers, stream=stream, timeout=timeout)
        return DummyResponse()

    monkeypatch.setattr(resource_query.requests, "get", fake_get)

    response = resource_query._fetch_download_response("paper-1", "课件.pptx", stream=True)

    assert response.content == b"PK\x03\x04"
    assert captured["url"] == "https://oss.example.test/signed-url"
    assert captured["stream"] is True
    assert captured["headers"] == {"User-Agent": resource_query.HEADERS["User-Agent"]}


def test_query_course_resources_defaults_to_summary(monkeypatch):
    monkeypatch.setattr(
        resource_query,
        "_fetch_course_resources_response",
        lambda group_id: {
            "success": True,
            "data": [
                {
                    "id": "node-1",
                    "parent_id": "",
                    "quote_id": "paper-1",
                    "name": "课堂作业",
                    "type": 7,
                    "path": "root/node-1",
                    "sort_position": 1,
                }
            ],
        },
    )

    result = resource_query.query_course_resources("group-1")

    assert result["success"]
    assert result["data"] == {
        "node-1": {
            "id": "node-1",
            "paper_id": "paper-1",
            "name": "课堂作业",
            "type": "作业",
        }
    }


def test_query_resource_folder_snapshot(monkeypatch):
    monkeypatch.setattr(
        resource_query,
        "_load_course_resource_map",
        lambda *args, **kwargs: {
            "folder-1": {
                "id": "folder-1",
                "parent_id": "root",
                "name": "课堂作业",
                "type_name": "文件夹",
                "sort_position": 0,
                "public": 2,
                "download": 1,
                "published": 1,
                "finish_teaching": 0,
            },
            "node-1": {
                "id": "node-1",
                "parent_id": "folder-1",
                "paper_id": "paper-1",
                "name": "练习1",
                "type_name": "作业",
                "sort_position": 2,
                "public": 2,
                "download": 2,
                "published": 1,
                "finish_teaching": 0,
            },
            "node-2": {
                "id": "node-2",
                "parent_id": "folder-1",
                "paper_id": None,
                "name": "讲义",
                "type_name": "文件",
                "sort_position": 1,
                "public": 1,
                "download": 1,
                "published": 1,
                "finish_teaching": 1,
            },
        },
    )

    result = resource_query.query_resource_folder_snapshot("group-1", "folder-1")

    assert result["success"]
    assert result["data"]["child_count"] == 2
    assert [item["id"] for item in result["data"]["children"]] == ["node-2", "node-1"]


def test_batch_update_resource_download_returns_failed_items(monkeypatch):
    def fake_post_json(url, *, payload=None, timeout=20, allow_http_error=False):
        if payload["node_id"] == "node-1":
            return {"success": True, "data": None}
        return {"success": False, "msg": "无权限"}

    monkeypatch.setattr(resource_update, "post_json", fake_post_json)

    result = resource_update.batch_update_resource_download("group-1", ["node-1", "node-2"], 2)

    assert not result["success"]
    assert result["data"]["success_count"] == 1
    assert result["data"]["failed_count"] == 1
    assert result["data"]["partial_success"] is True
    assert result["data"]["success_ids"] == ["node-1"]
    assert result["data"]["failed_items"] == [{"node_id": "node-2", "message": "无权限"}]
