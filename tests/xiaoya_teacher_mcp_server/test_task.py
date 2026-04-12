import os

import pytest
from dotenv import load_dotenv, find_dotenv
from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.task import query as task_query

load_dotenv(find_dotenv())

requires_live_auth = pytest.mark.skipif(
    not (
        os.getenv("XIAOYA_AUTH_TOKEN")
        or (os.getenv("XIAOYA_ACCOUNT") and os.getenv("XIAOYA_PASSWORD"))
    ),
    reason="需要配置小雅认证环境变量",
)


def _latest_group_and_task():
    groups = group_query.query_teacher_groups().get("data") or []
    assert groups, "未找到课程组"
    group_id = groups[0]["group_id"]

    tasks = task_query.query_group_tasks(group_id).get("data") or []
    assert tasks, "未找到任务"
    return group_id, tasks[-1]


@requires_live_auth
def test_query_tasks():
    group_id, _ = _latest_group_and_task()
    result = task_query.query_group_tasks(group_id)
    assert result.get("success")
    print(f"\n✓ 查询任务成功, 共 {len(result.get('data', []))} 个任务")


@requires_live_auth
def test_query_test_result_and_student_paper():
    group_id, task = _latest_group_and_task()
    test_result = task_query.query_test_result(group_id, task["paper_id"], task["publish_id"])
    assert test_result.get("success")
    data = test_result.get("data", {})
    records = data.get("answer_records") or []
    print(f"\n1. ✓ 查询测试结果成功, 共 {len(records)} 条记录")

    if not records:
        return

    record = next((item for item in reversed(records) if item["status"] == "已提交"), None)
    if record is None:
        pytest.skip("当前任务没有已提交答题卡，跳过学生答卷预览")

    paper_result = task_query.query_preview_student_paper(
        group_id,
        task["paper_id"],
        data["mark_mode_id"],
        task["publish_id"],
        record["record_id"],
    )
    assert paper_result["success"]
    print(f"2. ✓ 查询学生答卷成功: {record['nickname']} ({record['class_name']})")


def test_query_group_task_notices(monkeypatch):
    monkeypatch.setattr(
        task_query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": {"teacher_tasks": [], "student_tasks": []},
        },
    )

    result = task_query.query_group_task_notices("group-1")

    assert result["success"]
    assert result["data"] == {"teacher_tasks": [], "student_tasks": []}


def test_query_group_discussion_task_detail(monkeypatch):
    monkeypatch.setattr(
        task_query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": [],
        },
    )

    result = task_query.query_group_discussion_task_detail("group-1")

    assert result["success"]
    assert result["data"] == []


def test_query_group_tasks_defaults_to_summary(monkeypatch):
    monkeypatch.setattr(
        task_query,
        "_load_course_resource_map",
        lambda *args, **kwargs: {
            "node-1": {
                "id": "node-1",
                "name": "课堂作业",
                "type": 7,
                "paper_id": "paper-1",
                "link_tasks": [
                    {
                        "task_id": "task-1",
                        "publish_id": "publish-1",
                        "start_time": "2026-03-09 08:00:00",
                        "end_time": "2026-03-09 10:00:00",
                    }
                ],
            }
        },
    )

    result = task_query.query_group_tasks("group-1")

    assert result["success"]
    assert result["data"] == [
        {
            "resource_id": "node-1",
            "name": "课堂作业",
            "paper_id": "paper-1",
            "publish_id": "publish-1",
        }
    ]


def test_query_test_result_defaults_to_summary(monkeypatch):
    monkeypatch.setattr(
        task_query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": {
                "lost_members": [{"nickname": "张三"}],
                "answer_records": [
                    {
                        "id": "record-1",
                        "actual_score": 88,
                        "answer_time": "2026-03-09 08:10:00",
                        "created_at": "2026-03-09 08:00:00",
                        "nickname": "李四",
                        "student_number": "2024001",
                        "class_id": "class-1",
                        "class_name": "机器人1班",
                        "status": 2,
                        "answer_rate": 100,
                    }
                ],
                "mark_mode": {"mark_mode_id": "mark-1"},
            },
        },
    )

    result = task_query.query_test_result("group-1", "paper-1", "publish-1")

    assert result["success"]
    assert result["data"]["mark_mode_id"] == "mark-1"
    assert result["data"]["record_count"] == 1
    assert result["data"]["submitted_count"] == 1
    assert result["data"]["lost_member_count"] == 1
    assert result["data"]["answer_records"] == [
        {
            "record_id": "record-1",
            "actual_score": 88,
            "nickname": "李四",
            "student_number": "2024001",
            "class_name": "机器人1班",
            "status": "已提交",
        }
    ]


def test_query_preview_student_paper_defaults_to_summary(monkeypatch):
    monkeypatch.setattr(
        task_query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": {
                "answer_record": {
                    "id": "record-1",
                    "answers": [
                        {
                            "question_id": "question-1",
                            "score": 5,
                            "answer": "学生答案",
                        }
                    ],
                },
                "mark_records": [
                    {
                        "id": "mpr-1",
                        "mark_answers": [
                            {
                                "question_id": "question-1",
                                "answer_id": "ans-1",
                                "check_score": 5,
                                "check_status": 2,
                            }
                        ],
                    }
                ],
                "questions": [
                    {
                        "id": "question-1",
                        "title": '{"blocks":[{"text":"题目1"}],"entityMap":{}}',
                        "description": '{"blocks":[{"text":"说明"}],"entityMap":{}}',
                        "type": 6,
                        "score": 5,
                        "answer_items": [],
                    }
                ],
            },
        },
    )

    result = task_query.query_preview_student_paper(
        "group-1", "paper-1", "mark-1", "publish-1", "record-1"
    )

    assert result["success"]
    assert result["data"]["record_id"] == "record-1"
    assert result["data"]["mark_paper_record_id"] == "mpr-1"
    assert result["data"]["question_count"] == 1
    assert result["data"]["earned_score"] == 5
    assert result["data"]["questions"] == [
        {
            "id": "question-1",
            "title": "题目1",
            "type": "简答题",
            "score": 5,
            "user_score": 5,
            "has_answer": True,
            "answer_id": "ans-1",
            "check_score": 5,
        }
    ]
