"""
题目查询MCP工具

此模块为在线测试系统中查询试卷和题目提供MCP工具.
"""

import requests
from typing import Annotated
from pydantic import Field
import json

from ...types.types import (
    AnswerChecked,
    AutoScoreType,
    AutoStatType,
    QuestionType,
    RequiredType,
)
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, create_headers, MCP


@MCP.tool()
def query_paper(
    group_id: Annotated[str, Field(description="组id")],
    paper_id: Annotated[str, Field(description="试卷paper_id")],
    need_parse: Annotated[
        bool, Field(description="是否解析题目内容,默认不解析")
    ] = False,
) -> dict:
    """查询指定卷子的所有题目信息"""
    try:
        response = requests.get(
            f"{MAIN_URL}/survey/queryPaperEditBuffer",
            headers=create_headers(),
            params={"paper_id": str(paper_id), "group_id": str(group_id)},
        ).json()
        if response.get("success"):
            data = response["data"]
            questions = {
                "question_shuffle": data["random"],
                "option_shuffle": data["question_random"],
                "id": data["id"],
                "paper_id": data["paper_id"],
                "title": data["title"],
                "updated_at": data["updated_at"],
            }
            questions["questions"] = []
            for question in data["questions"]:
                questions["questions"].append(parse_question(question, need_parse))
            return ResponseUtil.success(questions, "试卷查询成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("查询指定试卷题目失败", e)


def parse_question(question, need_parse=True):
    question_data = {
        "id": question["id"],
        "title": parse_text(question["title"]) if need_parse else question["title"],
        "description": question["description"],
        "type": QuestionType.get(question["type"]),
        "score": question["score"],
        "required": RequiredType.get(question["required"]),
        "answer_items_sort": question["answer_items_sort"],
    }
    question_data["options"] = (
        parse_answer_items(question["answer_items"], question["type"])
        if need_parse and question.get("answer_items")
        else question.get("answer_items")
    )
    if question["type"] == QuestionType.FILL_BLANK.value:
        question_data.update(
            {
                "is_split_answer": question["is_split_answer"],
                "automatic_type": AutoStatType.get(question["automatic_type"]),
                "automatic_stat": AutoScoreType.get(question["automatic_stat"]),
            }
        )
    if question["type"] == QuestionType.CODE.value:
        question_data["program_setting"] = question["program_setting"]

    return question_data


def parse_text(text):
    try:
        json_data = json.loads(text)
        blocks = json_data.get("blocks", [])
        return (
            " ".join(block.get("text", "") for block in blocks) if blocks else json_data
        )
    except Exception:
        return text


def parse_answer_items(answer_items, question_type, need_parse=True):
    """解析答案项，根据题目类型返回不同格式的答案"""
    parsers = {
        QuestionType.MULTIPLE_CHOICE.value: lambda item: {
            "answer_item_id": item["id"],
            "value": parse_text(item["value"]) if need_parse else item["value"],
            "answer": AnswerChecked.get(item["answer_checked"]),
        },
        QuestionType.SINGLE_CHOICE.value: lambda item: {
            "answer_item_id": item["id"],
            "value": parse_text(item["value"]) if need_parse else item["value"],
            "answer": AnswerChecked.get(item["answer_checked"]),
        },
        QuestionType.FILL_BLANK.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": parse_text(item["answer"]) if need_parse else item["answer"],
        },
        QuestionType.TRUE_FALSE.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": AnswerChecked.get(item["answer_checked"]),
        },
        QuestionType.SHORT_ANSWER.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": parse_text(item["answer"]) if need_parse else item["answer"],
        },
        QuestionType.ATTACHMENT.value: None,
        QuestionType.CODE.value: lambda item: {
            "answer_item_id": item["id"],
            "answer": parse_text(item["answer"]) if need_parse else item["answer"],
        },
    }

    parser = parsers.get(question_type)
    return [parser(item) for item in answer_items] if parser else []
