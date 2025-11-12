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


def test_query_resource():
    """测试查询课程资源列表"""
    group_id, _ = _get_group_and_root()
    result = resource_query.query_course_resources_summary(group_id)
    assert result["success"]
    all_resources = _flatten_resources(result["data"])
    print(f"\n✓ 查询成功,共{len(all_resources)}个资源")


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
        dst_children = []
        for item in all_items:
            attr_result = resource_query.query_resource_attributes(group_id, item["id"])
            if attr_result["success"]:
                attr_data = attr_result["data"]
                if attr_data.get("parent_id") == dst_id:
                    dst_children.append(attr_data)
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
