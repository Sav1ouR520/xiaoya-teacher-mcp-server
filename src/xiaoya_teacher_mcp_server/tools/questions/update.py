"""题目更新 MCP 工具"""

from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...tools.questions.normalize import parse_question
from ...tools.questions.query import _fetch_paper_edit_buffer
from ...types.enums import (
    AnswerChecked,
    AutoScoreType,
    AutoStatType,
    QuestionScoreType,
    RandomizationType,
    RequiredType,
)
from ...types.question_models import ProgramSetting
from ...utils.client import (
    APIRequestError,
    expect_success,
    post_json,
)
from ...utils.response import ResponseUtil
from ...utils.rich_text import normalize_rich_text_input, render_rich_text_output

KNOWN_UPDATE_ERRORS = (APIRequestError, ValueError)


def _post_update_answer_item(**payload) -> list[dict[str, Any]]:
    response = post_json(f"{MAIN_URL}/survey/updateAnswerItem", payload=payload)
    return expect_success(response)


def _post_update_question(**payload) -> dict[str, Any]:
    response = post_json(f"{MAIN_URL}/survey/updateQuestion", payload=payload)
    return expect_success(response)


def _format_choice_items(items: list[dict[str, Any]], parse_mode: str) -> list[dict[str, Any]]:
    return [
        {
            "answer_item_id": item["id"],
            "value": render_rich_text_output(item["value"], parse_mode),
            "answer": AnswerChecked.get(item["answer_checked"]),
        }
        for item in items
    ]


def _format_answer_items(
    items: list[dict[str, Any]], field: str, *, parse_mode: str | None = None
) -> list[dict[str, Any]]:
    return [
        {
            "answer_item_id": item["id"],
            field: render_rich_text_output(item[field], parse_mode) if parse_mode else item[field],
        }
        for item in items
    ]


def _format_true_false_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "answer_item_id": item["id"],
            "answer": AnswerChecked.get(item["answer_checked"]),
        }
        for item in items
    ]


def _format_question_order(data: dict[str, Any]) -> dict[str, Any]:
    return {
        key: data[key] if key != "questions_sort" else data[key].split(",")
        for key in ["id", "title", "updated_at", "questions_sort"]
        if key in data
    }


def _update_paper_settings(
    *,
    paper_id: str,
    question_shuffle: RandomizationType | None = None,
    option_shuffle: RandomizationType | None = None,
    question_score_type: QuestionScoreType | None = None,
) -> None:
    payload: dict[str, Any] = {"paper_id": str(paper_id)}
    if option_shuffle is not None:
        payload["question_random"] = option_shuffle
    if question_shuffle is not None:
        payload["random"] = question_shuffle
    if question_score_type is not None:
        payload["question_score_type"] = question_score_type
    if len(payload) == 1:
        raise ValueError("至少提供一个试卷配置项")
    expect_success(post_json(f"{MAIN_URL}/survey/updatePaper", payload=payload))


def _update_question_required(question_id: str, required: RequiredType) -> None:
    _post_update_question(question_id=str(question_id), required=required)


def _validate_in_cases(in_cases: list[dict[str, str]]) -> None:
    if not in_cases:
        raise ValueError("测试用例列表不能为空")
    if not all(isinstance(case, dict) and set(case.keys()) == {"in"} for case in in_cases):
        raise ValueError("测试用例格式错误, 每个测试用例必须仅包含'in'字段")


def _validate_program_case_update(program_setting: ProgramSetting) -> None:
    if not program_setting.in_cases:
        return
    if not program_setting.answer_item_id:
        raise ValueError("提供 in_cases 时必须同时提供 answer_item_id")
    if not program_setting.answer_language:
        raise ValueError("提供 in_cases 时必须同时提供 answer_language")
    if not program_setting.code_answer:
        raise ValueError("提供 in_cases 时必须同时提供 code_answer")
    _validate_in_cases(program_setting.in_cases)


def _update_code_cases(
    *,
    question_id: str,
    answer_item_id: str,
    language: str,
    code: str,
    in_cases: list[dict[str, str]],
) -> list[dict[str, Any]]:
    _validate_in_cases(in_cases)

    case_data = expect_success(
        post_json(
            f"{MAIN_URL}/survey/program/runcase",
            payload={
                "answer_item_id": str(answer_item_id),
                "language": language,
                "code": code,
                "input": json.dumps(in_cases),
            },
        )
    )
    if not case_data["pass"]:
        raise ValueError(f"代码运行测试用例失败, 运行结果:{case_data}")

    formatted_cases = [
        {"id": f"use_case_{i}", "in": case["in"], "out": case["out"]}
        for i, case in enumerate(case_data["result"])
    ]
    return expect_success(
        post_json(
            f"{MAIN_URL}/survey/updateAnswerItem",
            payload={
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
                "answer": json.dumps(formatted_cases, ensure_ascii=False),
            },
        )
    )


@MCP.tool()
def update_question(
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    title: Annotated[str | None, Field(description=desc.QUESTION_RICH_TEXT_DESC)] = None,
    title_raw: Annotated[
        dict[str, Any] | None, Field(description=desc.QUESTION_RAW_RICH_TEXT_DESC)
    ] = None,
    score: Annotated[int | None, Field(description=desc.QUESTION_SCORE_UPDATE_DESC, ge=0)] = None,
    description: Annotated[str | None, Field(description=desc.ANSWER_EXPLANATION_DESC)] = None,
    required: Annotated[RequiredType | None, Field(description=desc.REQUIRED_DESC)] = None,
    is_split_answer: Annotated[bool | None, Field(description=desc.SPLIT_ANSWER_DESC)] = None,
    automatic_stat: Annotated[AutoStatType | None, Field(description=desc.AUTO_STAT_DESC)] = None,
    automatic_type: Annotated[AutoScoreType | None, Field(description=desc.AUTO_SCORE_DESC)] = None,
    program_setting: Annotated[
        ProgramSetting | None, Field(description=desc.PROGRAM_SETTING_OPTIONAL_DESC)
    ] = None,
    parse_mode: Annotated[
        str, Field(description=desc.PARSE_MODE_DESC, default="plain", pattern="^(plain|raw)$")
    ] = "plain",
) -> dict:
    """更新任意题目的通用配置"""
    try:
        payload: dict[str, Any] = {"question_id": str(question_id)}
        normalized_title = normalize_rich_text_input(text=title, raw=title_raw)
        if normalized_title is not None:
            payload["title"] = normalized_title
        if description is not None:
            payload["description"] = description
        if required is not None:
            payload["required"] = required
        if score is not None:
            payload["score"] = score
        if is_split_answer is not None:
            payload["is_split_answer"] = is_split_answer
        if automatic_stat is not None:
            payload["automatic_stat"] = automatic_stat
        if automatic_type is not None:
            payload["automatic_type"] = automatic_type
        if program_setting is not None:
            _validate_program_case_update(program_setting)
            program_setting_payload = program_setting.model_dump(
                exclude_none=True, exclude_defaults=True, exclude_unset=True
            )
            program_setting_payload.pop("in_cases", None)
            program_setting_payload.pop("answer_item_id", None)
            if program_setting.answer_language is not None:
                program_setting_payload["example_language"] = program_setting.answer_language
            if program_setting.code_answer is not None:
                program_setting_payload["example_code"] = program_setting.code_answer
            payload["program_setting"] = program_setting_payload

        response_data = _post_update_question(**payload)
        message = "题目设置更新成功"
        if program_setting is not None and program_setting.in_cases:
            response_data["answer_items"] = _update_code_cases(
                question_id=question_id,
                answer_item_id=program_setting.answer_item_id,
                language=program_setting.answer_language,
                code=program_setting.code_answer,
                in_cases=program_setting.in_cases,
            )
            message = "题目设置及测试用例更新成功"
        return ResponseUtil.success(parse_question(response_data, parse_mode=parse_mode), message)
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("题目设置更新失败", e)


@MCP.tool()
def update_question_options(
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_item_id: Annotated[str, Field(description=desc.OPTION_ID_DESC)],
    option_text: Annotated[str | None, Field(description=desc.OPTION_TEXT_DESC)] = None,
    option_text_raw: Annotated[
        dict[str, Any] | None, Field(description=desc.OPTION_RAW_TEXT_DESC)
    ] = None,
    is_answer: Annotated[bool | None, Field(description=desc.OPTION_ANSWER_DESC)] = False,
    parse_mode: Annotated[
        str, Field(description=desc.PARSE_MODE_DESC, default="plain", pattern="^(plain|raw)$")
    ] = "plain",
) -> dict:
    """[仅限单选/多选题]更新单选或多选题的选项内容"""
    try:
        payload: dict[str, Any] = {
            "question_id": str(question_id),
            "answer_item_id": str(answer_item_id),
        }
        normalized_value = normalize_rich_text_input(text=option_text, raw=option_text_raw)
        if normalized_value is not None:
            payload["value"] = normalized_value
        if is_answer is not None:
            payload["answer_checked"] = 2 if is_answer else 1
        return ResponseUtil.success(
            _format_choice_items(_post_update_answer_item(**payload), parse_mode),
            "单/多选题选项更新成功",
        )
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("单/多选题选项更新失败", e)


@MCP.tool()
def update_fill_blank_answer(
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_item_id: Annotated[str, Field(description=desc.ANSWER_ITEM_ID_DESC)],
    answer: Annotated[str, Field(description=desc.ANSWER_TEXT_DESC)],
) -> dict:
    """[仅限填空题]更新填空题指定填空答案"""
    try:
        return ResponseUtil.success(
            _format_answer_items(
                _post_update_answer_item(
                    question_id=str(question_id),
                    answer_item_id=str(answer_item_id),
                    answer=answer,
                ),
                "answer",
            ),
            "填空题指定填空答案更新成功",
        )
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("填空题答案更新失败", e)


@MCP.tool()
def update_true_false_answer(
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_item_id: Annotated[str, Field(description=desc.ANSWER_ITEM_ID_DESC)],
) -> dict:
    """[仅限判断题]更新判断题答案,将选项id对应的选项设为正确答案"""
    try:
        return ResponseUtil.success(
            _format_true_false_items(
                _post_update_answer_item(
                    question_id=str(question_id),
                    answer_item_id=str(answer_item_id),
                    answer_checked=2,
                )
            ),
            "判断题答案更新成功",
        )
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("判断题答案更新失败", e)


@MCP.tool()
def update_short_answer_answer(
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_item_id: Annotated[str, Field(description=desc.ANSWER_ITEM_ID_DESC)],
    answer: Annotated[str | None, Field(description=desc.REFERENCE_RICH_TEXT_DESC)] = None,
    answer_raw: Annotated[
        dict[str, Any] | None, Field(description=desc.REFERENCE_RAW_RICH_TEXT_DESC)
    ] = None,
    parse_mode: Annotated[
        str, Field(description=desc.PARSE_MODE_DESC, default="plain", pattern="^(plain|raw)$")
    ] = "plain",
) -> dict:
    """[仅限简答题]更新简答题参考答案"""
    try:
        normalized_answer = normalize_rich_text_input(text=answer, raw=answer_raw)
        return ResponseUtil.success(
            _format_answer_items(
                _post_update_answer_item(
                    question_id=str(question_id),
                    answer_item_id=str(answer_item_id),
                    answer=normalized_answer,
                ),
                "answer",
                parse_mode=parse_mode,
            ),
            "简答题参考答案更新成功",
        )
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("简答题参考答案更新失败", e)


@MCP.tool()
def update_code_test_cases(
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_item_id: Annotated[str, Field(description=desc.PROGRAM_SETTING_ANSWER_ITEM_DESC)],
    program_setting_id: Annotated[str, Field(description=desc.PROGRAM_SETTING_ID_DESC)],
    code_answer: Annotated[str, Field(description=desc.RUN_CODE_ANSWER_DESC)],
    answer_language: Annotated[str, Field(description=desc.ANSWER_LANGUAGE_DESC)],
    in_cases: Annotated[list[dict[str, str]], Field(description=desc.IN_CASES_DESC, min_length=1)],
) -> dict:
    """更新编程题答案代码和测试用例(会覆盖原用例)"""
    try:
        _validate_in_cases(in_cases)
        _post_update_question(
            question_id=str(question_id),
            program_setting={
                "id": str(program_setting_id),
                "example_language": answer_language,
                "example_code": code_answer,
            },
        )
        result = _update_code_cases(
            question_id=question_id,
            answer_item_id=answer_item_id,
            language=answer_language,
            code=code_answer,
            in_cases=in_cases,
        )
        return ResponseUtil.success(result, "编程题测试用例更新成功")
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("编程题测试用例更新失败", e)


@MCP.tool()
def update_paper_randomization(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_shuffle: Annotated[
        RandomizationType | None, Field(description=desc.RANDOMIZE_QUESTION_DESC)
    ] = None,
    option_shuffle: Annotated[
        RandomizationType | None, Field(description=desc.RANDOMIZE_OPTION_DESC)
    ] = None,
    question_score_type: Annotated[
        QuestionScoreType | None, Field(description=desc.QUESTION_SCORE_TYPE_DESC)
    ] = None,
) -> dict:
    """更新试卷的题目和选项随机化设置"""
    try:
        _update_paper_settings(
            paper_id=paper_id,
            question_shuffle=question_shuffle,
            option_shuffle=option_shuffle,
            question_score_type=question_score_type,
        )
        return ResponseUtil.success(None, "试卷随机化设置更新成功")
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("试卷随机化设置更新失败", e)


@MCP.tool()
def configure_paper_basics(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    required: Annotated[RequiredType | None, Field(description=desc.REQUIRED_DESC)] = None,
    question_shuffle: Annotated[
        RandomizationType | None, Field(description=desc.RANDOMIZE_QUESTION_DESC)
    ] = None,
    option_shuffle: Annotated[
        RandomizationType | None, Field(description=desc.RANDOMIZE_OPTION_DESC)
    ] = None,
    question_score_type: Annotated[
        QuestionScoreType | None, Field(description=desc.QUESTION_SCORE_TYPE_DESC)
    ] = None,
) -> dict:
    """一键配置整卷常用基础设置"""
    try:
        if all(
            v is None for v in (required, question_shuffle, option_shuffle, question_score_type)
        ):
            raise ValueError("至少提供一个配置项")

        summary: dict[str, Any] = {
            "paper_id": str(paper_id),
            "required_updated": 0,
            "required_failed_question_ids": [],
            "randomization_updated": False,
        }

        if required is not None:
            paper_data = _fetch_paper_edit_buffer(group_id, paper_id)
            question_ids = [q["id"] for q in paper_data.get("questions", []) if q.get("id")]
            summary["question_count"] = len(question_ids)
            for question_id in question_ids:
                try:
                    _update_question_required(question_id, required)
                    summary["required_updated"] += 1
                except KNOWN_UPDATE_ERRORS:
                    summary["required_failed_question_ids"].append(question_id)

        if any(v is not None for v in (question_shuffle, option_shuffle, question_score_type)):
            _update_paper_settings(
                paper_id=paper_id,
                question_shuffle=question_shuffle,
                option_shuffle=option_shuffle,
                question_score_type=question_score_type,
            )
            summary["randomization_updated"] = True

        if required is not None:
            summary["required"] = RequiredType.get(required)
        if question_shuffle is not None:
            summary["question_shuffle"] = RandomizationType.get(question_shuffle)
        if option_shuffle is not None:
            summary["option_shuffle"] = RandomizationType.get(option_shuffle)
        if question_score_type is not None:
            summary["question_score_type"] = QuestionScoreType.get(question_score_type)
        return ResponseUtil.success(summary, "试卷基础设置更新成功")
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("试卷基础设置更新失败", e)


@MCP.tool()
def move_answer_item(
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_item_ids: Annotated[
        list[str], Field(description=desc.ANSWER_ITEM_ID_LIST_DESC, min_length=1)
    ],
) -> dict:
    """[不限制题型]调整题目选项顺序"""
    try:
        expect_success(
            post_json(
                f"{MAIN_URL}/survey/moveAnswerItem",
                payload={"question_id": str(question_id), "answer_item_ids": answer_item_ids},
            )
        )
        return ResponseUtil.success(None, "题目选项顺序调整成功")
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("题目选项顺序调整失败", e)


@MCP.tool()
def update_paper_question_order(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_ids: Annotated[
        list[str], Field(description=desc.QUESTION_ID_LIST_ORDER_DESC, min_length=1)
    ],
) -> dict:
    """更新试卷的题目顺序"""
    try:
        data = expect_success(
            post_json(
                f"{MAIN_URL}/survey/moveQuestion",
                payload={
                    "paper_id": str(paper_id),
                    "question_ids": [str(qid) for qid in question_ids],
                },
            )
        )
        return ResponseUtil.success(_format_question_order(data), "试卷题目顺序更新成功")
    except KNOWN_UPDATE_ERRORS as e:
        return ResponseUtil.error("试卷题目顺序更新失败", e)
