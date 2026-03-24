"""任务查询模块"""

from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...tools.questions.normalize import parse_answer_items
from ...tools.resources.query import _load_course_resource_map
from ...types.enums import QuestionType
from ...types.resource_models import ResourceType
from ...types.task_models import AnswerStatus
from ...utils.client import (
    APIRequestError,
    expect_success,
    get_json,
)
from ...utils.response import ResponseUtil
from ...utils.rich_text import render_rich_text_output


def _safe_score(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _query_payload(
    *,
    url: str,
    params: dict[str, Any],
    builder=None,
    success_message: str,
    error_message: str,
) -> dict:
    try:
        data = expect_success(get_json(url, params=params))
        return ResponseUtil.success(builder(data) if builder else data, success_message)
    except APIRequestError as e:
        return ResponseUtil.error(error_message, e)


def _build_group_tasks(group_id: str, detail_level: str = "summary") -> dict:
    try:
        resources = _load_course_resource_map(group_id, detail_level="full").values()
        flattened_tasks = []
        for task_folder in resources:
            is_assignment = (
                task_folder.get("type") == ResourceType.ASSIGNMENT.value
                or task_folder.get("type_name") == "作业"
            )
            if not is_assignment:
                continue
            for link_task in task_folder.get("link_tasks") or []:
                task = {
                    "resource_id": task_folder["id"],
                    "name": task_folder["name"],
                    "paper_id": task_folder["paper_id"],
                    "publish_id": link_task["publish_id"],
                }
                if detail_level == "full":
                    task.update(
                        {
                            "task_id": link_task.get("task_id"),
                            "start_time": link_task.get("start_time"),
                            "end_time": link_task.get("end_time"),
                        }
                    )
                flattened_tasks.append(task)
        flattened_tasks.sort(key=lambda task: task["publish_id"])
        return ResponseUtil.success(
            flattened_tasks, f"课程测试/考试/任务查询成功,共{len(flattened_tasks)}项"
        )
    except APIRequestError as e:
        return ResponseUtil.error("课程测试/考试/任务查询失败", e)


def _build_test_result_record(record: dict[str, Any], detail_level: str) -> dict[str, Any]:
    summary = {
        "record_id": record["id"],
        "actual_score": record["actual_score"],
        "nickname": record["nickname"],
        "student_number": record["student_number"],
        "class_name": record["class_name"],
        "status": AnswerStatus.get(record["status"]),
    }
    if detail_level == "full":
        summary.update(
            {
                "answer_time": record.get("answer_time"),
                "created_at": record.get("created_at"),
                "class_id": record.get("class_id"),
                "answer_rate": record.get("answer_rate", 0),
            }
        )
    return summary


def _build_test_result_payload(data: dict[str, Any], detail_level: str) -> dict[str, Any]:
    raw_records = data.get("answer_records", [])
    answer_records = [
        _build_test_result_record(record, detail_level) for record in raw_records
    ]
    submitted_count = sum(
        1 for record in raw_records if record.get("status") == AnswerStatus.SUBMITTED
    )
    total_score = sum(_safe_score(record.get("actual_score")) for record in raw_records)
    record_count = len(answer_records)

    payload = {
        "mark_mode_id": data.get("mark_mode", {}).get("mark_mode_id"),
        "record_count": record_count,
        "submitted_count": submitted_count,
        "in_progress_count": max(record_count - submitted_count, 0),
        "lost_member_count": len(data.get("lost_members", [])),
        "average_score": round(total_score / record_count, 2) if record_count else 0,
        "answer_records": answer_records,
    }
    if detail_level == "full":
        keep_keys = ["class_id", "class_name", "nickname", "student_number"]
        payload["lost_members"] = [
            {key: member[key] for key in keep_keys if key in member}
            for member in data.get("lost_members", [])
        ]
    return payload


def _extract_attachments(answer_raw: Any) -> list[dict[str, Any]]:
    """从附件题答案中提取文件信息(quote_id, name, mimetype)"""
    try:
        items = json.loads(answer_raw) if isinstance(answer_raw, str) else (answer_raw or [])
        if not isinstance(items, list):
            return []
        return [
            {
                "name": item["name"],
                "quote_id": item["quote_id"],
                "mimetype": item.get("mimetype", ""),
            }
            for item in items
            if item.get("type") == "dist" and item.get("quote_id")
        ]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def _build_preview_question(
    question: dict[str, Any],
    answer: dict[str, Any],
    mark_answer: dict[str, Any] | None,
    *,
    parse_mode: str,
    detail_level: str,
) -> dict[str, Any]:
    user_answer = answer.get("answer_items") or answer.get("answer", "")
    question_data = {
        "id": question["id"],
        "title": render_rich_text_output(question["title"], parse_mode),
        "type": QuestionType.get(question["type"]),
        "score": question["score"],
        "user_score": answer.get("score", 0),
        "has_answer": bool(user_answer),
        "answer_id": mark_answer.get("answer_id") if mark_answer else None,
        "check_score": mark_answer.get("check_score") if mark_answer else None,
    }
    if detail_level == "full":
        question_data["description"] = render_rich_text_output(
            question["description"], parse_mode
        )
        question_data["user"] = {
            "answer": render_rich_text_output(user_answer, parse_mode),
            "score": answer.get("score", 0),
        }
        if question.get("answer_items"):
            question_data["options"] = parse_answer_items(
                question["answer_items"], question["type"], parse_mode
            )
        if question["type"] == QuestionType.CODE.value:
            question_data["program_setting"] = question.get("program_setting")
            raw_info = render_rich_text_output(answer.get("info"), "raw")
            question_data["user"]["test_case_info"] = (
                raw_info.get("data", []) if isinstance(raw_info, dict) else []
            )
        if question["type"] == QuestionType.ATTACHMENT.value:
            question_data["attachments"] = _extract_attachments(answer.get("answer", ""))
    return question_data


def _build_preview_payload(
    response_data: dict[str, Any],
    *,
    parse_mode: str,
    detail_level: str,
) -> dict[str, Any]:
    answers = response_data["answer_record"]["answers"]
    answer_map = {answer["question_id"]: answer for answer in answers}

    mark_records = response_data.get("mark_records") or []
    mark_record = mark_records[0] if mark_records else {}
    mark_paper_record_id = mark_record.get("id")
    mark_answers_map = {
        ma["question_id"]: ma
        for ma in (mark_record.get("mark_answers") or [])
    }

    questions = [
        _build_preview_question(
            question,
            answer_map[question["id"]],
            mark_answers_map.get(question["id"]),
            parse_mode=parse_mode,
            detail_level=detail_level,
        )
        for question in response_data["questions"]
    ]
    return {
        "record_id": response_data["answer_record"].get("id"),
        "mark_paper_record_id": mark_paper_record_id,
        "question_count": len(questions),
        "earned_score": sum(_safe_score(answer.get("score")) for answer in answers),
        "questions": questions,
    }


@MCP.tool()
def query_group_tasks(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    detail_level: Annotated[
        str,
        Field(description=desc.TASK_DETAIL_LEVEL_DESC, default="summary", pattern="^(summary|full)$"),
    ] = "summary",
) -> dict:
    """查询课程组发布的全部测试/考试/任务"""
    return _build_group_tasks(group_id, detail_level=detail_level)


@MCP.tool()
def query_group_task_notices(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    role: Annotated[int, Field(description=desc.ROLE_DESC, ge=1, default=3)] = 3,
) -> dict:
    """查询课程任务统计公告"""
    return _query_payload(
        url="https://fzrjxy.ai-augmented.com/api/jx-stat/group/task/queryTaskNotices",
        params={"group_id": str(group_id), "role": role},
        success_message="课程任务统计查询成功",
        error_message="查询课程任务统计失败",
    )


@MCP.tool()
def query_group_discussion_task_detail(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    role: Annotated[int, Field(description=desc.ROLE_DESC, ge=1, default=3)] = 3,
) -> dict:
    """查询讨论任务统计详情"""
    return _query_payload(
        url="https://fzrjxy.ai-augmented.com/api/jx-stat/discussion/queryDiscussionTaskDetail",
        params={"group_id": str(group_id), "role": role},
        success_message="讨论任务统计查询成功",
        error_message="查询讨论任务统计失败",
    )


@MCP.tool()
def query_test_result(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    publish_id: Annotated[str, Field(description=desc.PUBLISH_ID_DESC)],
    detail_level: Annotated[
        str,
        Field(description=desc.ANSWER_DETAIL_LEVEL_DESC, default="summary", pattern="^(summary|full)$"),
    ] = "summary",
) -> dict:
    """查询学生的测试/考试/任务的答题情况(包含mark_mode_id)"""
    return _query_payload(
        url=f"{MAIN_URL}/survey/course/queryStuAnswerList/v2",
        params={
            "group_id": str(group_id),
            "paper_id": str(paper_id),
            "publish_id": str(publish_id),
        },
        builder=lambda data: _build_test_result_payload(data, detail_level),
        success_message="小测答题情况查询成功",
        error_message="查询任务详情时发生异常",
    )


@MCP.tool()
def query_preview_student_paper(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    mark_mode_id: Annotated[str, Field(description=desc.MARK_MODE_ID_DESC)],
    publish_id: Annotated[str, Field(description=desc.PUBLISH_ID_DESC)],
    record_id: Annotated[str, Field(description=desc.RECORD_ID_DESC)],
    detail_level: Annotated[
        str,
        Field(description=desc.ANSWER_DETAIL_LEVEL_DESC, default="summary", pattern="^(summary|full)$"),
    ] = "summary",
    parse_mode: Annotated[
        str,
        Field(description=desc.PARSE_MODE_DESC, default="plain", pattern="^(plain|raw)$"),
    ] = "plain",
) -> dict:
    """查询学生答题信息(部分id通过query_test_result获取)"""
    return _query_payload(
        url=f"{MAIN_URL}/survey/course/queryMarkRecord",
        params={
            "group_id": str(group_id),
            "paper_id": str(paper_id),
            "publish_id": str(publish_id),
            "mark_mode_id": str(mark_mode_id),
            "answer_record_id": str(record_id),
        },
        builder=lambda data: _build_preview_payload(
            data,
            parse_mode=parse_mode,
            detail_level=detail_level,
        ),
        success_message="学生答题预览查询成功",
        error_message="查询学生答题预览时发生异常",
    )
