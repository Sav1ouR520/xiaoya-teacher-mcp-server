"""
题目删除MCP工具

此模块为在线测试系统中从试卷删除题目提供MCP工具.
"""

import requests
from typing import Annotated
from pydantic import Field

from ...utils.response import ResponseUtil
from ...config import MAIN_URL, create_headers, MCP


@MCP.tool()
def delete_questions(
    paper_id: Annotated[str, Field(description="试卷paper_id")],
    question_ids: Annotated[list[str], Field(description="要删除的题目id列表")],
) -> dict:
    """从试卷中批量删除题目"""
    url = f"{MAIN_URL}/survey/delQuestion"
    failed_ids, success_ids = [], []
    for question_id in question_ids:
        try:
            response = requests.post(
                url,
                json={"paper_id": str(paper_id), "question_id": str(question_id)},
                headers=create_headers(),
            )

            response = response.json()
            if response.get("success"):
                success_ids.append(question_id)
            else:
                failed_ids.append(question_id)
        except Exception:
            failed_ids.append(question_id)
    return ResponseUtil.success(
        {"success_ids": success_ids, "failed_ids": failed_ids},
        f"题目批量删除完成:成功{len(success_ids)}个,失败{len(failed_ids)}个",
    )


@MCP.tool()
def delete_answer_item(
    paper_id: Annotated[str, Field(description="试卷id")],
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="选项id")],
) -> dict:
    """删除题目的某个选项"""
    try:
        url = f"{MAIN_URL}/survey/delAnswerItem"
        response = requests.post(
            url,
            json={
                "paper_id": str(paper_id),
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
            },
            headers=create_headers(),
        ).json()
        if response.get("success"):
            return ResponseUtil.success(None, "选项删除成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("删除题目选项时发生异常", e)
