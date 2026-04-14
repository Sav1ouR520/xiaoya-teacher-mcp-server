"""批改/评分模块"""

from __future__ import annotations

import base64
import mimetypes
import os
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
    """[批改 3/4] 给学生某道题打分。

    何时调用：仅简答题（type=6）和附件题（type=7）需要；选择/填空/判断/编程系统自动评分，跳过。
    score 上限 = query_preview_student_paper 返回的该题 score 字段；未 submit 前可重复打分覆盖。
    四步流程：query_test_result → query_preview_student_paper → grade_student_question → submit_student_mark。
    """
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
    """[批改 4/4] 提交整卷批阅结果。

    调用前需对该卷所有需手工批改的题都执行过 grade_student_question；
    本工具一旦成功，该学生本卷的分数即写入学生端，不可再改。
    """
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
    save_path: Annotated[
        str | None,
        Field(
            description=(
                "附件保存路径（可选）。传文件路径或已存在目录时直接落盘，响应里只返回 file_path。"
                "图片/PDF 批阅推荐用这个配合 Read 工具看图，避免 base64 撑爆上下文。"
            ),
            default=None,
        ),
    ] = None,
) -> dict:
    """获取学生答题附件（图片/PDF/文件等均可）。

    两种模式：
      - 不传 save_path：返回 base64 + mimetype（适合小附件解析）。
      - 传 save_path：落盘后返回 file_path（适合图片批阅，agent 直接 Read 查看）。
    """
    try:
        resp = request_response(
            "GET",
            f"{DOWNLOAD_URL}/cloud/file_access/{quote_id}",
            timeout=30,
        )
        mimetype = (
            resp.headers.get("content-type", "application/octet-stream").split(";")[0].strip()
        )
        size = len(resp.content)

        if save_path:
            file_path = _resolve_attachment_path(save_path, quote_id, mimetype)
            parent = os.path.dirname(file_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(file_path, "wb") as handle:
                handle.write(resp.content)
            return ResponseUtil.success(
                {
                    "file_path": file_path,
                    "mimetype": mimetype,
                    "size": size,
                },
                f"附件已保存: {file_path}",
            )

        return ResponseUtil.success(
            {
                "content": base64.b64encode(resp.content).decode(),
                "mimetype": mimetype,
                "size": size,
            },
            "获取附件成功",
        )
    except (APIRequestError, OSError) as e:
        return ResponseUtil.error("获取附件失败", e)


def _resolve_attachment_path(save_path: str, quote_id: str, mimetype: str) -> str:
    """save_path 是已存在目录或以分隔符结尾 → 拼 quote_id + 推断扩展名；否则当成完整文件路径。"""
    is_dir = os.path.isdir(save_path) or save_path.endswith(("/", os.sep))
    if is_dir:
        ext = mimetypes.guess_extension(mimetype) or ""
        return os.path.join(save_path, f"{quote_id}{ext}")
    return save_path
