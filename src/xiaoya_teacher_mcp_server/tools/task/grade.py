"""批改/评分模块"""

from __future__ import annotations

import base64
from typing import Annotated

from pydantic import Field

from ... import field_descriptions as desc
from ...config import DOWNLOAD_URL, MAIN_URL, MCP
from ...utils.client import APIRequestError, expect_success, post_json, request_response
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
    """[批改第3步] 给学生某道题打分。完整批改流程：
    1. query_test_result        → 获取 mark_mode_id、record_id
    2. query_preview_student_paper → 获取 mark_paper_record_id、各题 answer_id
    3. grade_student_question   → 对每道题逐一打分（本工具）
    4. submit_student_mark      → 提交整卷批阅结果
    注意：简答/附件题需要手动批改；选择题/填空/判断系统已自动评分，无需调用本工具。"""
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
    """[批改第4步] 提交整卷批阅结果（必须在 grade_student_question 对所有题打分后调用，否则提交无效）"""
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
        resp = request_response(
            "GET",
            f"{DOWNLOAD_URL}/cloud/file_access/{quote_id}",
            timeout=30,
        )
        mimetype = resp.headers.get("content-type", "application/octet-stream").split(";")[0].strip()
        return ResponseUtil.success(
            {
                "content": base64.b64encode(resp.content).decode(),
                "mimetype": mimetype,
                "size": len(resp.content),
            },
            "获取附件成功",
        )
    except APIRequestError as e:
        return ResponseUtil.error("获取附件失败", e)
