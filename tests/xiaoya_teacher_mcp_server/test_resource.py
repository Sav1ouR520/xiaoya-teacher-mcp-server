import uuid
from dotenv import load_dotenv, find_dotenv
from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.resources import (
    query as resource_query,
    create as resource_create,
    delete as resource_delete,
    update as resource_update,
)
from xiaoya_teacher_mcp_server.types.types import ResourceType

load_dotenv(find_dotenv())


def _get_group_and_root() -> tuple:
    """获取group_id和root资源id"""
    group_id = group_query.query_teacher_groups()["data"][0]["group_id"]
    resources = resource_query.query_course_resources(group_id, "flat")["data"]
    root = next((r for r in resources if r.get("name") == "root"), None)
    assert root is not None, "找不到root资源"
    return group_id, root["id"]


def test_query_resource():
    """测试查询课程资源列表"""
    group_id, _ = _get_group_and_root()
    result = resource_query.query_course_resources(group_id, "flat")
    assert result["success"]
    print(f"\n✓ 查询成功,共{len(result['data'])}个资源")


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
        resources = resource_query.query_course_resources(group_id, "flat")["data"]
        updated_item = next((r for r in resources if r["id"] == node_id), None)
        assert updated_item and updated_item["name"] == new_name
        print("2. ✓ 验证更新生效")

        # 3. 删除资源
        deleted = resource_delete.delete_course_resource(group_id, node_id)
        assert deleted["success"]
        resources_after = resource_query.query_course_resources(group_id, "flat")[
            "data"
        ]
        assert not any(r.get("id") == node_id for r in resources_after)
        print("3. ✓ 删除资源成功")
    finally:
        try:
            resource_delete.delete_course_resource(group_id, node_id)
        except Exception:
            pass


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
        all_items = resource_query.query_course_resources(group_id, "flat")["data"]
        dst_children = [r for r in all_items if r.get("parent_id") == dst_id]
        ordered_ids = [
            r["id"]
            for r in sorted(dst_children, key=lambda x: x.get("sort_position", 0))
        ]
        assert ordered_ids == desired_order
        print("3. ✓ 验证排序正确")
    finally:
        for _id in [child_c_id, child_b_id, child_a_id, src_id, dst_id]:
            try:
                if _id:
                    resource_delete.delete_course_resource(group_id, _id)
            except Exception:
                pass
