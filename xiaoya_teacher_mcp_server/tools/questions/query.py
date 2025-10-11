"""
题目查询MCP工具

此模块为在线测试系统中查询试卷和题目提供MCP工具.
"""

import requests
from typing import Annotated
from pydantic import Field
import json

from ...types.types import AnswerChecked
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, create_headers, MCP


@MCP.tool()
def query_paper(
    group_id: Annotated[str, Field(description="组id")],
    paper_id: Annotated[str, Field(description="试卷paper_id")],
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

            def parse_text(text):
                try:
                    blocks = json.loads(text).get("blocks", [])
                    return (
                        " ".join(block.get("text", "") for block in blocks)
                        if blocks
                        else text
                    )
                except Exception:
                    return text

            def parse_answer_items(answer_items, question_type):
                if question_type in [1, 2]:
                    return [
                        {
                            "id": item["id"],
                            "value": parse_text(item["value"]),
                            "answer": AnswerChecked.get(item["answer_checked"]),
                        }
                        for item in answer_items
                    ]
                elif question_type == 5:
                    return [
                        {
                            "id": item["id"],
                            "answer": AnswerChecked.get(item["answer_checked"]),
                        }
                        for item in answer_items
                    ]
                elif question_type == 4:
                    return [
                        {"id": item["id"], "answer": item["answer"]}
                        for item in answer_items
                    ]
                elif question_type == 10:
                    return [
                        {"id": item["id"], "answer": json.loads(item["answer"])}
                        for item in answer_items
                    ]

            questions["questions"] = [
                {
                    "id": q["id"],
                    "title": parse_text(q["title"]),
                    "description": q["description"],
                    "score": q["score"],
                    "required": q["required"],
                    "is_split_answer": q["is_split_answer"],
                    "automatic_type": q["automatic_type"],
                    "automatic_stat": q["automatic_stat"],
                    "answer_items_sort": q["answer_items_sort"],
                    "answer_items": parse_answer_items(
                        q["answer_items"], q.get("type", 1)
                    ),
                    "program_setting": q.get("program_setting", None),
                }
                for q in data["questions"]
            ]
            return ResponseUtil.success(questions, "试卷查询成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message", "未知错误")
            )
    except Exception as e:
        return ResponseUtil.error("查询指定试卷题目失败", e)
