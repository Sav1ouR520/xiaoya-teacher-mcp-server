"""批改/评分模块"""

from __future__ import annotations

import base64
import copy
import mimetypes
import os
from pathlib import Path
from typing import Annotated, Any

import requests
from pydantic import Field

from ... import field_descriptions as desc
from ...config import DOWNLOAD_URL, HEADERS, MAIN_URL, MCP
from ...utils.client import APIRequestError, expect_success, get_json, post_json
from ...utils.response import ResponseUtil
from .attachments import (
    collect_answer_attachments,
    default_attachment_dir,
    download_answer_attachments,
    looks_like_html_payload,
    merge_downloaded_attachments,
)
from .query import query_preview_student_paper

MANUAL_QUESTION_TYPES = {"简答题", "附件题"}
ATTACHMENT_DOWNLOAD_WORKERS = 4


def _validate_grade_item(item: dict[str, Any], index: int) -> tuple[str, str, float, str]:
    missing = [key for key in ("question_id", "answer_id", "score") if key not in item]
    if missing:
        raise ValueError(f"grades[{index}] 缺少字段: {', '.join(missing)}")
    try:
        score = float(item["score"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"grades[{index}].score 必须是数字") from exc
    if score < 0:
        raise ValueError(f"grades[{index}].score 不能小于 0")
    return str(item["question_id"]), str(item["answer_id"]), score, str(item.get("comment", ""))


def _require_grading_context(context: dict[str, Any]) -> dict[str, str]:
    required = ("group_id", "publish_id", "mark_mode_id", "record_id", "mark_paper_record_id")
    missing = [key for key in required if not context.get(key)]
    if missing:
        raise ValueError(f"grading_context 缺少字段: {', '.join(missing)}")
    return {key: str(context[key]) for key in required}


def _build_grading_context(
    *,
    group_id: str,
    publish_id: str,
    mark_mode_id: str,
    record_id: str,
    mark_paper_record_id: str | None,
) -> dict[str, str]:
    return {
        "group_id": str(group_id),
        "publish_id": str(publish_id),
        "mark_mode_id": str(mark_mode_id),
        "record_id": str(record_id),
        "mark_paper_record_id": str(mark_paper_record_id or ""),
    }


def _student_answer_text(question: dict[str, Any]) -> str:
    answer = (question.get("user") or {}).get("answer", "")
    return answer if isinstance(answer, str) else ""


def _format_grading_attachment(attachment: dict[str, Any]) -> dict[str, Any]:
    formatted = {
        "name": attachment.get("name", ""),
        "mimetype": attachment.get("mimetype", ""),
    }
    if attachment.get("file_path"):
        formatted["file_path"] = attachment["file_path"]
    return formatted


def _format_grading_question(question: dict[str, Any]) -> dict[str, Any] | None:
    if question.get("type") not in MANUAL_QUESTION_TYPES:
        return None
    formatted = {
        "question_id": question.get("id"),
        "answer_id": question.get("answer_id"),
        "type": question.get("type"),
        "max_score": question.get("score"),
        "current_score": question.get("check_score"),
        "current_comment": question.get("check_description") or "",
        "title": question.get("title") or question.get("title_md") or "",
        "description": question.get("description") or question.get("description_md") or "",
        "student_answer": _student_answer_text(question),
        "attachments": [
            _format_grading_attachment(attachment)
            for attachment in question.get("attachments", [])
            if attachment.get("file_path")
        ],
    }
    return {key: value for key, value in formatted.items() if value not in (None, [], "")}


def _build_grading_bundle(
    *,
    group_id: str,
    publish_id: str,
    mark_mode_id: str,
    record_id: str,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    questions = [
        question
        for question in (_format_grading_question(item) for item in bundle.get("questions", []))
        if question
    ]
    return {
        "grading_context": _build_grading_context(
            group_id=group_id,
            publish_id=publish_id,
            mark_mode_id=mark_mode_id,
            record_id=bundle.get("record_id") or record_id,
            mark_paper_record_id=bundle.get("mark_paper_record_id"),
        ),
        "questions": questions,
    }


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
    若整卷已提交批阅，先调用 withdraw_student_mark 重开，再重新打分。
    四步流程：query_test_result → query_preview_student_paper → grade_student_question → submit_student_mark。
    """
    try:
        expect_success(
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
        return ResponseUtil.success(
            {
                "question_id": str(question_id),
                "answer_id": str(answer_id),
                "score": score,
            },
            f"题目打分成功: {score}分",
        )
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
    本工具成功后成绩写入学生端。若之后确需修改，必须先调用 withdraw_student_mark 重开批阅。
    """
    try:
        expect_success(
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
        return ResponseUtil.success({"submitted": True}, "提交批阅成功")
    except APIRequestError as e:
        return ResponseUtil.error("提交批阅失败", e)


@MCP.tool()
def withdraw_student_mark(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    answer_record_id: Annotated[str, Field(description=desc.RECORD_ID_DESC)],
    mark_mode_id: Annotated[str, Field(description=desc.MARK_MODE_ID_DESC)],
    mark_paper_record_id: Annotated[str, Field(description=desc.MARK_PAPER_RECORD_ID_DESC)],
    is_teacher_recheck: Annotated[
        bool,
        Field(
            description=(
                "是否为复评/教师重批模式。普通整卷批阅填 false；"
                "复评模式填 true，会调用 review reset 接口。"
            ),
            default=False,
        ),
    ] = False,
) -> dict:
    """重开已提交的学生整卷批阅，使分数和评语可以再次修改。

    调用前必须确认老师确实要修改已提交成绩。重开后通常继续调用
    grade_student_question 或 revise_student_mark，再调用 submit_student_mark 重新提交。
    """
    endpoint = "review" if is_teacher_recheck else "normal"
    try:
        expect_success(
            post_json(
                f"{MAIN_URL}/survey/course/{endpoint}/mark/reset",
                payload={
                    "group_id": str(group_id),
                    "answer_record_id": str(answer_record_id),
                    "mark_mode_id": str(mark_mode_id),
                    "mark_paper_record_id": str(mark_paper_record_id),
                },
            )
        )
        return ResponseUtil.success({"reopened": True}, "批阅已重开，可重新修改分数和评语")
    except APIRequestError as e:
        return ResponseUtil.error("重开批阅失败", e)


@MCP.tool()
def revise_student_mark(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    publish_id: Annotated[str, Field(description=desc.PUBLISH_ID_DESC)],
    mark_paper_record_id: Annotated[str, Field(description=desc.MARK_PAPER_RECORD_ID_DESC)],
    record_id: Annotated[str, Field(description=desc.RECORD_ID_DESC)],
    mark_mode_id: Annotated[str, Field(description=desc.MARK_MODE_ID_DESC)],
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_id: Annotated[str, Field(description=desc.ANSWER_ID_DESC)],
    score: Annotated[float, Field(description=desc.CHECK_SCORE_DESC, ge=0)],
    comment: Annotated[str, Field(description=desc.CHECK_COMMENT_DESC, default="")] = "",
    allow_reopen: Annotated[
        bool,
        Field(
            description=(
                "是否允许先重开已提交批阅。默认 false，避免无意修改已发布成绩；"
                "确认要改已提交成绩时设为 true。"
            ),
            default=False,
        ),
    ] = False,
    submit_after: Annotated[
        bool,
        Field(description="修改后是否立即重新提交整卷批阅。默认 false。", default=False),
    ] = False,
    is_teacher_recheck: Annotated[
        bool,
        Field(
            description="重开时是否使用复评 reset 接口。仅 allow_reopen=true 时生效。",
            default=False,
        ),
    ] = False,
) -> dict:
    """修改学生某题分数/评语，可选重开已提交批阅并重新提交。

    默认只覆盖未提交批阅中的单题分数。若成绩已经提交，调用方必须显式传
    allow_reopen=true，工具才会先重开批阅。
    """
    if allow_reopen:
        reopened = withdraw_student_mark(
            group_id=group_id,
            answer_record_id=record_id,
            mark_mode_id=mark_mode_id,
            mark_paper_record_id=mark_paper_record_id,
            is_teacher_recheck=is_teacher_recheck,
        )
        if not reopened.get("success"):
            return ResponseUtil.error(
                "修改批阅失败: 重开批阅未成功",
                data={"message": reopened.get("message", "")},
            )

    graded = grade_student_question(
        group_id=group_id,
        publish_id=publish_id,
        mark_paper_record_id=mark_paper_record_id,
        record_id=record_id,
        question_id=question_id,
        answer_id=answer_id,
        score=score,
        comment=comment,
    )
    if not graded.get("success"):
        return ResponseUtil.error(
            "修改批阅失败: 题目打分未成功",
            data={"message": graded.get("message", "")},
        )

    if submit_after:
        submitted = submit_student_mark(
            group_id=group_id,
            answer_record_id=record_id,
            mark_mode_id=mark_mode_id,
            mark_paper_record_id=mark_paper_record_id,
        )
        if not submitted.get("success"):
            return ResponseUtil.error(
                "修改批阅失败: 重新提交未成功",
                data={"message": submitted.get("message", "")},
            )

    return ResponseUtil.success(
        {
            "graded_count": 1,
            "reopened": allow_reopen,
            "submitted": submit_after,
        },
        "批阅修改完成",
    )


@MCP.tool()
def get_student_grading_bundle(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    mark_mode_id: Annotated[str, Field(description=desc.MARK_MODE_ID_DESC)],
    publish_id: Annotated[str, Field(description=desc.PUBLISH_ID_DESC)],
    record_id: Annotated[str, Field(description=desc.RECORD_ID_DESC)],
    save_dir: Annotated[
        str | None,
        Field(
            description=(
                "附件保存目录。默认使用当前系统临时目录；同一附件已下载时自动复用本地文件。"
            ),
            default=None,
        ),
    ] = None,
) -> dict:
    """获取单个学生的 AI 批改包，并下载附件到本地。

    只返回 AI 批改必需字段：grading_context、需人工批改的题目、
    当前分数/评语、学生答案和附件 file_path。
    """
    preview = query_preview_student_paper(
        group_id=group_id,
        paper_id=paper_id,
        mark_mode_id=mark_mode_id,
        publish_id=publish_id,
        record_id=record_id,
        detail_level="full",
        parse_mode="plain",
    )
    if not preview.get("success"):
        return ResponseUtil.error(
            "学生批改包获取失败: 答卷预览未成功",
            data={"message": preview.get("message", "")},
        )

    bundle = copy.deepcopy(preview.get("data") or {})
    questions = bundle.get("questions") or []
    attachments = collect_answer_attachments(questions)

    if attachments:
        cache_dir = Path(save_dir) if save_dir else default_attachment_dir(record_id)
        download_map, attachment_errors = download_answer_attachments(
            attachments,
            cache_dir,
            max_workers=ATTACHMENT_DOWNLOAD_WORKERS,
            downloader=lambda quote_id, save_path: get_answer_file(quote_id, save_path),
        )
        merge_downloaded_attachments(questions, download_map)
        if attachment_errors:
            return ResponseUtil.error(
                "学生批改包获取失败: 附件下载失败",
                data={
                    "failed_attachments": [
                        {
                            "name": item.get("name", ""),
                            "message": item.get("message", ""),
                        }
                        for item in attachment_errors
                    ]
                },
            )

    return ResponseUtil.success(
        _build_grading_bundle(
            group_id=group_id,
            publish_id=publish_id,
            mark_mode_id=mark_mode_id,
            record_id=record_id,
            bundle=bundle,
        ),
        "学生批改包获取成功",
    )


@MCP.tool()
def grade_student_paper(
    grading_context: Annotated[
        dict[str, Any],
        Field(
            description=("来自 get_student_grading_bundle.data.grading_context，原样传回即可。"),
        ),
    ],
    grades: Annotated[
        list[dict[str, Any]],
        Field(
            description=(
                "需人工批改的题目分数列表。每项包含 question_id、answer_id、score，可选 comment。"
            ),
            min_length=1,
        ),
    ],
    submit_after: Annotated[
        bool,
        Field(description="所有题打分成功后是否立即提交整卷批阅。默认 true。", default=True),
    ] = True,
    allow_reopen: Annotated[
        bool,
        Field(
            description=(
                "是否允许先重开已提交批阅。默认 false，避免无意修改已发布成绩；"
                "确认要改已提交成绩时设为 true。"
            ),
            default=False,
        ),
    ] = False,
) -> dict:
    """批量写入单个学生多道题的分数/评语，可选提交整卷。"""
    try:
        context = _require_grading_context(grading_context)
    except ValueError as exc:
        return ResponseUtil.error("整卷批量打分失败: 参数无效", data={"error": str(exc)})

    if allow_reopen:
        reopened = withdraw_student_mark(
            group_id=context["group_id"],
            answer_record_id=context["record_id"],
            mark_mode_id=context["mark_mode_id"],
            mark_paper_record_id=context["mark_paper_record_id"],
        )
        if not reopened.get("success"):
            return ResponseUtil.error(
                "整卷批量打分失败: 重开批阅未成功",
                data={"message": reopened.get("message", "")},
            )

    graded_count = 0
    for index, item in enumerate(grades):
        try:
            question_id, answer_id, score, comment = _validate_grade_item(item, index)
        except ValueError as exc:
            return ResponseUtil.error(
                "整卷批量打分失败: 参数无效",
                data={
                    "failed_index": index,
                    "graded_count": graded_count,
                    "error": str(exc),
                },
            )

        graded = grade_student_question(
            group_id=context["group_id"],
            publish_id=context["publish_id"],
            mark_paper_record_id=context["mark_paper_record_id"],
            record_id=context["record_id"],
            question_id=question_id,
            answer_id=answer_id,
            score=score,
            comment=comment,
        )
        if not graded.get("success"):
            return ResponseUtil.error(
                "整卷批量打分失败: 题目打分未成功",
                data={
                    "failed_index": index,
                    "graded_count": graded_count,
                    "message": graded.get("message", ""),
                },
            )
        graded_count += 1

    if submit_after:
        submitted = submit_student_mark(
            group_id=context["group_id"],
            answer_record_id=context["record_id"],
            mark_mode_id=context["mark_mode_id"],
            mark_paper_record_id=context["mark_paper_record_id"],
        )
        if not submitted.get("success"):
            return ResponseUtil.error(
                "整卷批量打分失败: 提交批阅未成功",
                data={
                    "graded_count": graded_count,
                    "message": submitted.get("message", ""),
                },
            )

    return ResponseUtil.success(
        {
            "graded_count": graded_count,
            "submitted": submit_after,
        },
        "整卷批量打分完成",
    )


def _get_quote_download_url(quote_id: str) -> str:
    try:
        meta = expect_success(get_json(f"{DOWNLOAD_URL}/cloud/file_down/{quote_id}/v2"))
        download_url = str(meta.get("download_url") or "").strip()
        if not download_url:
            raise APIRequestError("附件下载链接为空")
        return download_url
    except APIRequestError as exc:
        raise APIRequestError(f"获取附件下载链接失败 (quote_id: {quote_id}): {exc}") from exc


def _fetch_quote_file_response(quote_id: str) -> requests.Response:
    try:
        response = requests.get(
            _get_quote_download_url(quote_id),
            headers={"User-Agent": HEADERS["User-Agent"]},
            timeout=60,
        )
        response.raise_for_status()
        return response
    except requests.Timeout as exc:
        raise APIRequestError("HTTP 请求超时") from exc
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise APIRequestError(f"HTTP 请求失败: {status_code}") from exc
    except requests.RequestException as exc:
        raise APIRequestError(f"HTTP 请求失败: {exc.__class__.__name__}") from exc


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
        resp = _fetch_quote_file_response(quote_id)
        mimetype = (
            resp.headers.get("content-type", "application/octet-stream").split(";")[0].strip()
        )
        if looks_like_html_payload(resp.content, mimetype):
            raise APIRequestError("附件下载返回了 HTML 预览页，而非真实文件")

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
                },
                f"附件已保存: {file_path}",
            )

        return ResponseUtil.success(
            {
                "content": base64.b64encode(resp.content).decode(),
                "mimetype": mimetype,
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
