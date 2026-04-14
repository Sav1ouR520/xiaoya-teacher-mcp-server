"""题目删除 MCP 工具"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...utils.client import APIRequestError, expect_success, extract_response_message, post_json
from ...utils.response import ResponseUtil


@MCP.tool()
def delete_questions(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_ids: Annotated[list[str], Field(description=desc.QUESTION_ID_LIST_DESC)],
) -> dict:
    """从试卷中批量删除题目"""
    url = f"{MAIN_URL}/survey/delQuestion"
    failed_items, success_ids = [], []
    for question_id in question_ids:
        try:
            response = post_json(
                url, payload={"paper_id": str(paper_id), "question_id": str(question_id)}
            )
            if response["success"]:
                success_ids.append(question_id)
            else:
                failed_items.append(
                    {"question_id": question_id, "message": extract_response_message(response)}
                )
        except APIRequestError as exc:
            failed_items.append({"question_id": question_id, "message": str(exc)})

    data = {
        "success_count": len(success_ids),
        "failed_count": len(failed_items),
        "partial_success": bool(success_ids and failed_items),
        "success_ids": success_ids,
        "failed_items": failed_items,
        "failed_ids": failed_items,
    }
    message = f"题目批量删除完成:成功{len(success_ids)}个,失败{len(failed_items)}个"
    if failed_items:
        return ResponseUtil.error(message, data=data)
    return ResponseUtil.success(data, message)


@MCP.tool()
def delete_answer_item(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    answer_item_id: Annotated[str, Field(description=desc.OPTION_ID_DESC)],
) -> dict:
    """删除题目的某个选项"""
    try:
        expect_success(
            post_json(
                f"{MAIN_URL}/survey/delAnswerItem",
                payload={
                    "paper_id": str(paper_id),
                    "question_id": str(question_id),
                    "answer_item_id": str(answer_item_id),
                },
            )
        )
        return ResponseUtil.success(None, "选项删除成功")
    except APIRequestError as e:
        return ResponseUtil.error("删除题目选项时发生异常", e)
