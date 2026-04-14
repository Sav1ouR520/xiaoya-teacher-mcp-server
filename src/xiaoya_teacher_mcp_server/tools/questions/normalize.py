"""题目解析和校验工具。"""

from __future__ import annotations

from collections import Counter
from string import ascii_uppercase
from typing import Any

from ...types.enums import (
    AnswerChecked,
    AutoScoreType,
    AutoStatType,
    QuestionType,
    RequiredType,
)
from ...utils.rich_text import render_rich_text_output


def parse_answer_items(
    answer_items: list[dict[str, Any]],
    question_type: int,
    parse_mode: str = "plain",
) -> list[dict[str, Any]]:
    def _parse_choice(item):
        return {
            "answer_item_id": item["id"],
            "value": render_rich_text_output(item["value"], parse_mode),
            "answer": AnswerChecked.get(item["answer_checked"]),
        }

    parsers = {
        QuestionType.MULTIPLE_CHOICE.value: _parse_choice,
        QuestionType.SINGLE_CHOICE.value: _parse_choice,
        QuestionType.FILL_BLANK.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": render_rich_text_output(item["answer"], parse_mode),
        },
        QuestionType.TRUE_FALSE.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": AnswerChecked.get(item["answer_checked"]),
            "value": item.get("value", ""),
        },
        QuestionType.SHORT_ANSWER.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": render_rich_text_output(item["answer"], parse_mode),
        },
        QuestionType.ATTACHMENT.value: None,
        QuestionType.CODE.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": render_rich_text_output(item["answer"], parse_mode),
        },
    }
    parser = parsers.get(question_type)
    return [parser(item) for item in answer_items] if parser else []


def parse_question(
    question: dict[str, Any],
    parse_mode: str = "plain",
) -> dict[str, Any]:
    question_data = {
        "id": question["id"],
        "title": render_rich_text_output(question["title"], parse_mode),
        "description": question["description"],
        "type": QuestionType.get(question["type"]),
        "score": question["score"],
        "required": RequiredType.get(question["required"]),
        "answer_items_sort": question["answer_items_sort"],
    }
    question_data["options"] = (
        parse_answer_items(question["answer_items"], question["type"], parse_mode)
        if question.get("answer_items")
        else question.get("answer_items")
    )
    if question["type"] == QuestionType.FILL_BLANK.value:
        question_data.update(
            {
                "is_split_answer": question["is_split_answer"],
                "automatic_type": AutoScoreType.get(question["automatic_type"]),
                "automatic_stat": AutoStatType.get(question["automatic_stat"]),
            }
        )
    if question["type"] == QuestionType.CODE.value:
        question_data["program_setting"] = question["program_setting"]
    return question_data


def summarize_question(
    question: dict[str, Any],
    parse_mode: str = "plain",
) -> dict[str, Any]:
    answer_items = question.get("answer_items") or []
    summary = {
        "id": question["id"],
        "title": render_rich_text_output(question["title"], parse_mode),
        "type": QuestionType.get(question["type"]),
        "score": question["score"],
        "required": RequiredType.get(question["required"]),
        "option_count": len(answer_items),
    }
    if question["type"] == QuestionType.FILL_BLANK.value:
        summary["blank_count"] = len(answer_items)
    if question["type"] == QuestionType.CODE.value:
        summary["has_program_setting"] = bool(question.get("program_setting"))
    return summary


def summarize_paper(
    paper: dict[str, Any],
    parse_mode: str = "plain",
) -> dict[str, Any]:
    questions = [
        summarize_question(question, parse_mode=parse_mode)
        for question in paper.get("questions", [])
    ]
    type_counts = dict(Counter(question["type"] for question in questions))
    return {
        "question_shuffle": paper["random"],
        "option_shuffle": paper["question_random"],
        "id": paper["id"],
        "paper_id": paper["paper_id"],
        "title": paper["title"],
        "updated_at": paper["updated_at"],
        "question_count": len(questions),
        "total_score": sum(question["score"] for question in questions),
        "type_counts": type_counts,
        "questions": questions,
    }


def answer_item_seqno(item: dict[str, Any], index: int) -> str:
    seqno = item.get("seqno")
    if seqno:
        return str(seqno).strip().upper()
    if index < len(ascii_uppercase):
        return ascii_uppercase[index]
    return str(index + 1)


def validate_office_import_results(
    questions: list[Any], imported_questions: list[dict[str, Any]]
) -> list[str]:
    if len(questions) != len(imported_questions):
        return [f"导入返回题目数量异常: 预期{len(questions)}题, 实际{len(imported_questions)}题"]

    errors = []
    for index, (expected, actual) in enumerate(zip(questions, imported_questions, strict=False), 1):
        if expected.type != actual.get("type"):
            errors.append(
                f"第{index}题类型不一致: 预期{QuestionType.get(expected.type)}, 实际{QuestionType.get(actual.get('type'))}"
            )
            continue

        if expected.type in (
            QuestionType.SINGLE_CHOICE,
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.TRUE_FALSE,
        ):
            expected_answers = {
                str(answer.standard_answer).strip().upper() for answer in expected.standard_answers
            }
            answer_items = actual.get("answer_items", [])
            can_validate_answers = any(
                "answer_checked" in item or "answer" in item for item in answer_items
            )
            actual_answers = {
                answer_item_seqno(item, item_index)
                for item_index, item in enumerate(answer_items)
                if item.get("answer_checked") == 2 or item.get("answer") == "正确"
            }
            if can_validate_answers and expected_answers != actual_answers:
                errors.append(
                    f"第{index}题答案不一致: 预期{sorted(expected_answers)}, 实际{sorted(actual_answers)}"
                )
        elif expected.type == QuestionType.FILL_BLANK:
            expected_answers = [
                str(answer.standard_answer).strip() for answer in expected.standard_answers
            ]
            actual_answers = [
                str(item.get("answer", "")).strip() for item in actual.get("answer_items", [])
            ]
            if expected_answers != actual_answers:
                errors.append(
                    f"第{index}题填空答案不一致: 预期{expected_answers}, 实际{actual_answers}"
                )
    return errors
