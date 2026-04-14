import os

import pytest
from dotenv import find_dotenv, load_dotenv

from xiaoya_teacher_mcp_server.tools.group import query

load_dotenv(find_dotenv())

requires_live_auth = pytest.mark.skipif(
    not (
        os.getenv("XIAOYA_AUTH_TOKEN")
        or (os.getenv("XIAOYA_ACCOUNT") and os.getenv("XIAOYA_PASSWORD"))
    ),
    reason="需要配置小雅认证环境变量",
)


@requires_live_auth
def test_query_groups_and_classes():
    """测试查询教师课程组和班级"""
    groups_result = query.query_teacher_groups()
    assert groups_result["success"]
    print(f"\n1. ✓ 查询课程组成功,共{len(groups_result['data'])}个")

    group_id = groups_result["data"][0]["group_id"]
    classes_result = query.query_group_classes(group_id)
    assert classes_result["success"]
    print(f"2. ✓ 查询班级成功,共{len(classes_result['data'])}个")


@requires_live_auth
def test_query_attendance():
    """测试查询签到记录"""
    groups_result = query.query_teacher_groups()
    assert groups_result["success"]
    group_id = groups_result["data"][0]["group_id"]

    records_result = query.query_attendance_records(group_id)
    assert records_result["success"]
    print(f"\n1. ✓ 查询签到记录成功,共{len(records_result['data'])}条")

    if records_result["data"]:
        record = records_result["data"][-1]
        students_result = query.query_single_attendance_students(
            group_id, record["id"], record["course_id"]
        )
        assert students_result["success"]
        print(f"2. ✓ 查询单次签到学生成功,共{len(students_result['data'])}人")


def test_query_group_snapshot(monkeypatch):
    monkeypatch.setattr(
        query,
        "query_teacher_groups",
        lambda: {
            "success": True,
            "data": [
                {
                    "group_id": "group-1",
                    "name": "机器人课程",
                    "teacher_names": "张老师",
                    "term_name": "2025-2026-2",
                    "department_name": "智能制造学院",
                    "member_count": 48,
                }
            ],
        },
    )
    monkeypatch.setattr(
        query,
        "query_group_classes",
        lambda group_id: {
            "success": True,
            "data": [{"class_id": "class-1"}, {"class_id": "class-2"}],
        },
    )
    monkeypatch.setattr(
        query.task_query,
        "query_group_tasks",
        lambda group_id, detail_level="summary": {
            "success": True,
            "data": [{"paper_id": "paper-1"}, {"paper_id": "paper-2"}],
        },
    )
    monkeypatch.setattr(
        query.resource_query,
        "query_course_resources",
        lambda group_id, detail_level="summary": {
            "success": True,
            "data": {"n1": {}, "n2": {}, "n3": {}},
        },
    )
    monkeypatch.setattr(
        query,
        "query_attendance_records",
        lambda group_id: {
            "success": True,
            "data": [
                {"id": "r1", "start_time": "2026-03-09 08:00:00"},
                {"id": "r2", "start_time": "2026-03-10 08:00:00"},
            ],
        },
    )

    result = query.query_group_snapshot("group-1")

    assert result["success"]
    assert result["data"]["class_count"] == 2
    assert result["data"]["task_count"] == 2
    assert result["data"]["resource_count"] == 3
    assert result["data"]["recent_attendance_count"] == 2
    assert result["data"]["recent_attendances"][0]["id"] == "r2"
