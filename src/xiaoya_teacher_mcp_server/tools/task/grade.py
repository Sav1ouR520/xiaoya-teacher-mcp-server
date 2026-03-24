"""批改/评分模块"""

from __future__ import annotations

import base64
from typing import Annotated

import requests
from pydantic import Field

from ... import field_descriptions as desc
from ...config import DOWNLOAD_URL, MAIN_URL, MCP, headers
from ...utils.client import APIRequestError, expect_success, post_json
from ...utils.response import ResponseUtil


@MCP.tool()
def grade_student_question(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    publish_id: Annotated[str, Field(description=desc.PUBLISH_ID_DESC)],
    mark_paper_record_id: Annotated[str, Field(description=desc.MARK_PAPER_RECORD_ID_DESC)],
    record_id: Annotated[str, Field(description=desc.RECORD_ID_DESC)],
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_id: Annotated[str, Field(description=desc.ANSWER_ID_DESC)],
    score: Annotated[float, Field(description=desc.CHECK_SCORE_DESC, ge=0)],
    comment: Annotated[str, Field(description=desc.CHECK_COMMENT_DESC, default="")] = "",
) -> dict:
    """给学生某道题打分(部分id通过query_preview_student_paper获取)"""
    try:
        data = expect_success(
            post_json(
                f"{MAIN_URL}/survey/mark/checkStuAnswer",
                payload={
                    "mark_paper_record_id": str(mark_paper_record_id),
                    "group_id": str(group_id),
                    "publish_id": str(publish_id),
                    "record_id": str(record_id),
                    "question_id": str(question_id),
                    "answer_id": str(answer_id),
                    "check_score": score,
                    "check_description": comment,
                },
            )
        )
        return ResponseUtil.success(data, f"题目打分成功: {score}分")
    except APIRequestError as e:
        return ResponseUtil.error("题目打分失败", e)


@MCP.tool()
def submit_student_mark(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    answer_record_id: Annotated[str, Field(description=desc.RECORD_ID_DESC)],
    mark_mode_id: Annotated[str, Field(description=desc.MARK_MODE_ID_DESC)],
    mark_paper_record_id: Annotated[str, Field(description=desc.MARK_PAPER_RECORD_ID_DESC)],
) -> dict:
    """提交批阅(完成对某学生的整卷批改,需先用grade_student_question对各题打分)"""
    try:
        data = expect_success(
            post_json(
                f"{MAIN_URL}/survey/course/submitMark",
                payload={
                    "group_id": str(group_id),
                    "answer_record_id": str(answer_record_id),
                    "mark_mode_id": str(mark_mode_id),
                    "mark_paper_record_id": str(mark_paper_record_id),
                },
            )
        )
        return ResponseUtil.success(data, "提交批阅成功")
    except APIRequestError as e:
        return ResponseUtil.error("提交批阅失败", e)


@MCP.tool()
def get_answer_file(
    quote_id: Annotated[str, Field(description=desc.QUOTE_ID_DESC)],
) -> dict:
    """获取学生答题附件内容(图片/PDF/文件等均支持),返回base64编码内容及MIME类型"""
    try:
        resp = requests.get(
            f"{DOWNLOAD_URL}/cloud/file_access/{quote_id}",
            headers=headers(),
            timeout=30,
        )
        resp.raise_for_status()
        mimetype = resp.headers.get("content-type", "application/octet-stream").split(";")[0].strip()
        return ResponseUtil.success(
            {
                "content": base64.b64encode(resp.content).decode(),
                "mimetype": mimetype,
                "size": len(resp.content),
            },
            "获取附件成功",
        )
    except requests.RequestException as e:
        return ResponseUtil.error("获取附件失败", e)
