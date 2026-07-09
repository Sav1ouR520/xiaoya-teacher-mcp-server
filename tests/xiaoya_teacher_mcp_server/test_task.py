import base64
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from dotenv import find_dotenv, load_dotenv

from xiaoya_teacher_mcp_server.config import DOWNLOAD_URL
from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.task import grade as task_grade
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


def test_query_preview_student_paper_markdown_mode_returns_markdown_fields(monkeypatch):
    monkeypatch.setattr(
        task_query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": {
                "answer_record": {
                    "id": "record-1",
                    "answers": [{"question_id": "question-1", "score": 5, "answer": "学生答案"}],
                },
                "mark_records": [{"id": "mpr-1", "mark_answers": []}],
                "questions": [
                    {
                        "id": "question-1",
                        "title": (
                            '{"blocks":[{"text":"题目1","type":"unstyled","data":{}},'
                            '{"text":"","type":"atomic","data":{"type":"IMAGE","src":"'
                            f"{DOWNLOAD_URL}/cloud/file_access/quote-1"
                            '"}}],"entityMap":{}}'
                        ),
                        "description": '{"blocks":[{"text":"说明","type":"unstyled","data":{}}],"entityMap":{}}',
                        "type": 6,
                        "score": 5,
                        "answer_items": [],
                    }
                ],
            },
        },
    )

    result = task_query.query_preview_student_paper(
        "group-1",
        "paper-1",
        "mark-1",
        "publish-1",
        "record-1",
        detail_level="full",
        parse_mode="markdown",
    )

    question = result["data"]["questions"][0]
    assert result["success"]
    assert "title" not in question
    assert question["title_md"] == "题目1\n\n![image_1](asset://img_1)"
    assert question["title_assets"][0]["quote_id"] == "quote-1"
    assert question["description_md"] == "说明"
    assert question["user"]["answer_md"] == "学生答案"


def test_query_preview_student_paper_full_includes_check_comment(monkeypatch):
    monkeypatch.setattr(
        task_query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": {
                "answer_record": {
                    "id": "record-1",
                    "answers": [{"question_id": "question-1", "score": 4, "answer": "学生答案"}],
                },
                "mark_records": [
                    {
                        "id": "mpr-1",
                        "mark_answers": [
                            {
                                "question_id": "question-1",
                                "answer_id": "ans-1",
                                "check_score": 4,
                                "check_description": "步骤基本完整",
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
        "group-1",
        "paper-1",
        "mark-1",
        "publish-1",
        "record-1",
        detail_level="full",
    )

    question = result["data"]["questions"][0]
    assert result["success"]
    assert question["check_score"] == 4
    assert question["check_description"] == "步骤基本完整"
    assert question["check_status"] == 2
    assert question["grading_state"] == "graded"


def _stub_response(content: bytes, content_type: str = "image/png") -> SimpleNamespace:
    return SimpleNamespace(
        content=content,
        headers={"content-type": content_type},
        raise_for_status=lambda: None,
    )


def _stub_quote_download(monkeypatch, payload: bytes, *, content_type: str = "image/png"):
    def fake_get_json(url, **kwargs):
        quote_id = url.rstrip("/").rsplit("/", 2)[-2]
        return {
            "success": True,
            "data": {"download_url": f"https://oss.example.test/{quote_id}"},
        }

    def fake_requests_get(url, **kwargs):
        return _stub_response(payload, content_type)

    monkeypatch.setattr(task_grade, "get_json", fake_get_json)
    monkeypatch.setattr(task_grade.requests, "get", fake_requests_get)


def test_get_answer_file_returns_base64_when_no_save_path(monkeypatch):
    payload = b"\x89PNG\r\n\x1a\nfake"
    _stub_quote_download(monkeypatch, payload)

    result = task_grade.get_answer_file("quote-1")

    assert result["success"]
    assert result["data"]["content"] == base64.b64encode(payload).decode()
    assert result["data"]["mimetype"] == "image/png"
    assert "size" not in result["data"]
    assert "file_path" not in result["data"]


def test_get_answer_file_writes_to_save_path_file(monkeypatch, tmp_path):
    payload = b"PDF-BYTES"
    _stub_quote_download(monkeypatch, payload, content_type="application/pdf")

    target = tmp_path / "sub" / "answer.pdf"
    result = task_grade.get_answer_file("quote-2", save_path=str(target))

    assert result["success"]
    assert result["data"]["file_path"] == str(target)
    assert result["data"]["mimetype"] == "application/pdf"
    assert "content" not in result["data"]
    assert "size" not in result["data"]
    assert Path(target).read_bytes() == payload


def test_get_answer_file_save_path_directory_auto_names(monkeypatch, tmp_path):
    payload = b"\x89PNG\r\nok"
    _stub_quote_download(monkeypatch, payload, content_type="image/png")

    result = task_grade.get_answer_file("quote-3", save_path=str(tmp_path))

    assert result["success"]
    expected = tmp_path / "quote-3.png"
    assert result["data"]["file_path"] == str(expected)
    assert expected.read_bytes() == payload


def test_get_answer_file_rejects_html_preview_payload(monkeypatch):
    html = b"<!DOCTYPE html><html><body>preview</body></html>"
    _stub_quote_download(monkeypatch, html, content_type="text/html; charset=utf-8")

    result = task_grade.get_answer_file("quote-html")

    assert not result["success"]
    assert "HTML" in result["message"]


def test_get_student_grading_bundle_downloads_attachments_once_and_reuses_cache(
    monkeypatch, tmp_path
):
    def fake_preview(*args, **kwargs):
        return {
            "success": True,
            "data": {
                "record_id": "record-1",
                "mark_paper_record_id": "mpr-1",
                "question_count": 1,
                "questions": [
                    {
                        "id": "question-auto",
                        "type": "单选题",
                        "score": 5,
                        "answer_id": "answer-auto",
                        "check_score": 5,
                        "check_description": "",
                        "has_answer": True,
                        "title": "自动题",
                        "user": {"answer": ["A"]},
                    },
                    {
                        "id": "question-1",
                        "type": "附件题",
                        "score": 10,
                        "title": "上传实验截图",
                        "description": "按截图完整性评分",
                        "answer_id": "answer-1",
                        "check_score": None,
                        "check_description": "",
                        "has_answer": True,
                        "user": {"answer": []},
                        "attachments": [
                            {
                                "name": "截图.png",
                                "quote_id": "quote-1",
                                "mimetype": "image/png",
                            }
                        ],
                    },
                ],
            },
        }

    calls = []

    def fake_get_json(url, **kwargs):
        quote_id = url.rstrip("/").rsplit("/", 2)[-2]
        calls.append(("get_json", url))
        return {
            "success": True,
            "data": {"download_url": f"https://oss.example.test/{quote_id}"},
        }

    def fake_requests_get(url, **kwargs):
        calls.append(("requests.get", url))
        return _stub_response(b"\x89PNG\r\nbundle", "image/png")

    monkeypatch.setattr(task_grade, "query_preview_student_paper", fake_preview)
    monkeypatch.setattr(task_grade, "get_json", fake_get_json)
    monkeypatch.setattr(task_grade.requests, "get", fake_requests_get)

    first = task_grade.get_student_grading_bundle(
        group_id="group-1",
        paper_id="paper-1",
        mark_mode_id="mark-1",
        publish_id="publish-1",
        record_id="record-1",
        save_dir=str(tmp_path),
    )
    second = task_grade.get_student_grading_bundle(
        group_id="group-1",
        paper_id="paper-1",
        mark_mode_id="mark-1",
        publish_id="publish-1",
        record_id="record-1",
        save_dir=str(tmp_path),
    )

    first_question = first["data"]["questions"][0]
    second_question = second["data"]["questions"][0]
    first_attachment = first_question["attachments"][0]
    assert first["success"]
    assert second["success"]
    assert len(calls) == 2
    assert calls[0][0] == "get_json"
    assert calls[1][0] == "requests.get"
    assert first["data"] == {
        "grading_context": {
            "group_id": "group-1",
            "publish_id": "publish-1",
            "mark_mode_id": "mark-1",
            "record_id": "record-1",
            "mark_paper_record_id": "mpr-1",
        },
        "questions": [
            {
                "question_id": "question-1",
                "answer_id": "answer-1",
                "type": "附件题",
                "max_score": 10,
                "title": "上传实验截图",
                "description": "按截图完整性评分",
                "attachments": [
                    {
                        "name": "截图.png",
                        "mimetype": "image/png",
                        "file_path": str(tmp_path / "quote-1.png"),
                    }
                ],
            }
        ],
    }
    assert second_question["question_id"] == "question-1"
    assert Path(first_attachment["file_path"]).read_bytes() == b"\x89PNG\r\nbundle"
    assert set(first_attachment) == {"name", "mimetype", "file_path"}
    assert "question_count" not in first["data"]
    assert "attachment_dir" not in first["data"]
    assert "quote_id" not in first_attachment
    assert "size" not in first_attachment
    assert "from_cache" not in first_attachment


def test_get_student_grading_bundle_redownloads_when_cached_file_is_html(monkeypatch, tmp_path):
    (tmp_path / "quote-1.png").write_text(
        "<!DOCTYPE html><html><body>preview</body></html>",
        encoding="utf-8",
    )

    def fake_preview(*args, **kwargs):
        return {
            "success": True,
            "data": {
                "record_id": "record-1",
                "mark_paper_record_id": "mpr-1",
                "questions": [
                    {
                        "id": "question-1",
                        "type": "附件题",
                        "score": 10,
                        "title": "上传实验截图",
                        "answer_id": "answer-1",
                        "user": {"answer": []},
                        "attachments": [
                            {
                                "name": "截图.png",
                                "quote_id": "quote-1",
                                "mimetype": "image/png",
                            }
                        ],
                    }
                ],
            },
        }

    calls = []

    def fake_get_json(url, **kwargs):
        calls.append(url)
        return {
            "success": True,
            "data": {"download_url": "https://oss.example.test/quote-1"},
        }

    def fake_requests_get(url, **kwargs):
        calls.append(url)
        return _stub_response(b"\x89PNG\r\nfresh", "image/png")

    monkeypatch.setattr(task_grade, "query_preview_student_paper", fake_preview)
    monkeypatch.setattr(task_grade, "get_json", fake_get_json)
    monkeypatch.setattr(task_grade.requests, "get", fake_requests_get)

    result = task_grade.get_student_grading_bundle(
        group_id="group-1",
        paper_id="paper-1",
        mark_mode_id="mark-1",
        publish_id="publish-1",
        record_id="record-1",
        save_dir=str(tmp_path),
    )

    assert result["success"]
    assert len(calls) == 2
    file_path = Path(result["data"]["questions"][0]["attachments"][0]["file_path"])
    assert file_path.read_bytes() == b"\x89PNG\r\nfresh"


def test_grade_student_question_returns_slim_result(monkeypatch):
    captured = {}

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        captured["payload"] = payload
        return {"success": True, "data": {"official": "noise"}}

    monkeypatch.setattr(task_grade, "post_json", fake_post)

    result = task_grade.grade_student_question(
        group_id="group-1",
        publish_id="publish-1",
        mark_paper_record_id="mark-paper-1",
        record_id="record-1",
        question_id="question-1",
        answer_id="answer-1",
        score=9,
        comment="清楚",
    )

    assert result["success"]
    assert result["data"] == {
        "question_id": "question-1",
        "answer_id": "answer-1",
        "score": 9,
    }
    assert "official" not in result["data"]
    assert captured["payload"]["check_description"] == "清楚"


def test_submit_student_mark_returns_slim_result(monkeypatch):
    monkeypatch.setattr(
        task_grade,
        "post_json",
        lambda *args, **kwargs: {"success": True, "data": {"official": "noise"}},
    )

    result = task_grade.submit_student_mark(
        group_id="group-1",
        answer_record_id="record-1",
        mark_mode_id="mark-mode-1",
        mark_paper_record_id="mark-paper-1",
    )

    assert result["success"]
    assert result["data"] == {"submitted": True}


def test_withdraw_student_mark_uses_normal_reset_by_default(monkeypatch):
    captured = {}

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        captured["url"] = url
        captured["payload"] = payload
        return {"success": True, "data": {"ok": True}}

    monkeypatch.setattr(task_grade, "post_json", fake_post)

    result = task_grade.withdraw_student_mark(
        group_id="group-1",
        answer_record_id="record-1",
        mark_mode_id="mark-mode-1",
        mark_paper_record_id="mark-paper-1",
    )

    assert result["success"]
    assert result["data"] == {"reopened": True}
    assert captured["url"].endswith("/survey/course/normal/mark/reset")
    assert captured["payload"] == {
        "group_id": "group-1",
        "answer_record_id": "record-1",
        "mark_mode_id": "mark-mode-1",
        "mark_paper_record_id": "mark-paper-1",
    }


def test_withdraw_student_mark_uses_review_reset_when_teacher_recheck(monkeypatch):
    captured = {}

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        captured["url"] = url
        captured["payload"] = payload
        return {"success": True, "data": {"ok": True}}

    monkeypatch.setattr(task_grade, "post_json", fake_post)

    result = task_grade.withdraw_student_mark(
        group_id="group-1",
        answer_record_id="record-1",
        mark_mode_id="mark-mode-1",
        mark_paper_record_id="mark-paper-1",
        is_teacher_recheck=True,
    )

    assert result["success"]
    assert captured["url"].endswith("/survey/course/review/mark/reset")


def test_revise_student_mark_reopens_grades_and_submits_in_order(monkeypatch):
    calls = []

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        calls.append((url, payload))
        return {"success": True, "data": {"step": len(calls)}}

    monkeypatch.setattr(task_grade, "post_json", fake_post)

    result = task_grade.revise_student_mark(
        group_id="group-1",
        publish_id="publish-1",
        mark_paper_record_id="mark-paper-1",
        record_id="record-1",
        mark_mode_id="mark-mode-1",
        question_id="question-1",
        answer_id="answer-1",
        score=88,
        comment="重新评分",
        allow_reopen=True,
        submit_after=True,
    )

    assert result["success"]
    assert result["data"] == {"graded_count": 1, "reopened": True, "submitted": True}
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == [
        "reset",
        "checkStuAnswer",
        "submitMark",
    ]
    assert calls[1][1]["check_score"] == 88
    assert calls[1][1]["check_description"] == "重新评分"


def test_revise_student_mark_does_not_reopen_by_default(monkeypatch):
    calls = []

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        calls.append((url, payload))
        return {"success": True, "data": {"step": len(calls)}}

    monkeypatch.setattr(task_grade, "post_json", fake_post)

    result = task_grade.revise_student_mark(
        group_id="group-1",
        publish_id="publish-1",
        mark_paper_record_id="mark-paper-1",
        record_id="record-1",
        mark_mode_id="mark-mode-1",
        question_id="question-1",
        answer_id="answer-1",
        score=90,
        comment="只改未提交批阅",
    )

    assert result["success"]
    assert result["data"] == {"graded_count": 1, "reopened": False, "submitted": False}
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == ["checkStuAnswer"]


def test_grade_student_paper_grades_all_questions_and_submits(monkeypatch):
    calls = []

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        calls.append((url, payload))
        return {"success": True, "data": {"ok": True, "index": len(calls)}}

    monkeypatch.setattr(task_grade, "post_json", fake_post)

    result = task_grade.grade_student_paper(
        grading_context={
            "group_id": "group-1",
            "publish_id": "publish-1",
            "mark_paper_record_id": "mark-paper-1",
            "record_id": "record-1",
            "mark_mode_id": "mark-mode-1",
        },
        grades=[
            {
                "question_id": "question-1",
                "answer_id": "answer-1",
                "score": 10,
                "comment": "完整",
            },
            {
                "question_id": "question-2",
                "answer_id": "answer-2",
                "score": 8,
                "comment": "步骤略少",
            },
        ],
        submit_after=True,
    )

    assert result["success"]
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == [
        "checkStuAnswer",
        "checkStuAnswer",
        "submitMark",
    ]
    assert result["data"] == {"graded_count": 2, "submitted": True}
    assert calls[0][1]["check_score"] == 10
    assert calls[1][1]["check_description"] == "步骤略少"


def test_grade_student_paper_stops_before_submit_when_a_grade_fails(monkeypatch):
    calls = []

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        calls.append((url, payload))
        if len(calls) == 2:
            return {"success": False, "msg": "打分失败"}
        return {"success": True, "data": {"ok": True}}

    monkeypatch.setattr(task_grade, "post_json", fake_post)

    result = task_grade.grade_student_paper(
        grading_context={
            "group_id": "group-1",
            "publish_id": "publish-1",
            "mark_paper_record_id": "mark-paper-1",
            "record_id": "record-1",
            "mark_mode_id": "mark-mode-1",
        },
        grades=[
            {"question_id": "question-1", "answer_id": "answer-1", "score": 10},
            {"question_id": "question-2", "answer_id": "answer-2", "score": 8},
        ],
        submit_after=True,
    )

    assert not result["success"]
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == [
        "checkStuAnswer",
        "checkStuAnswer",
    ]
    assert result["data"]["failed_index"] == 1
    assert result["data"]["graded_count"] == 1
    assert "grade_results" not in result["data"]
