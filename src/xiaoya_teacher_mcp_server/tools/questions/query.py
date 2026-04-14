"""题目查询 MCP 工具"""

from typing import Annotated

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...tools.questions.normalize import parse_question, summarize_paper
from ...utils.client import APIRequestError, expect_success, get_json
from ...utils.response import ResponseUtil


def _fetch_paper_edit_buffer(group_id: str, paper_id: str) -> dict:
    response = get_json(
        f"{MAIN_URL}/survey/queryPaperEditBuffer",
        params={"paper_id": str(paper_id), "group_id": str(group_id)},
    )
    return expect_success(response)


def _build_paper_payload(data: dict, detail_level: str, parse_mode: str) -> dict:
    paper_data = summarize_paper(data, parse_mode=parse_mode)
    if detail_level == "full":
        paper_data["questions"] = [
            parse_question(question, parse_mode=parse_mode) for question in data["questions"]
        ]
    return paper_data


@MCP.tool()
def query_paper(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    detail_level: Annotated[
        str,
        Field(
            description=desc.PAPER_DETAIL_LEVEL_DESC,
            default="summary",
            pattern="^(summary|full)$",
        ),
    ] = "summary",
    parse_mode: Annotated[
        str,
        Field(
            description=desc.PARSE_MODE_DESC,
            default="plain",
            pattern="^(plain|raw)$",
        ),
    ] = "plain",
) -> dict:
    """查询试卷；默认返回摘要，完整内容请设 detail_level=full"""
    try:
        data = _fetch_paper_edit_buffer(group_id, paper_id)
        paper_data = _build_paper_payload(data, detail_level, parse_mode)
        if detail_level == "summary":
            return ResponseUtil.success(paper_data, "试卷摘要查询成功")
        return ResponseUtil.success(paper_data, "试卷查询成功")
    except APIRequestError as e:
        return ResponseUtil.error("查询指定试卷题目失败", e)


@MCP.tool()
def query_paper_summary(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
) -> dict:
    """获取试卷摘要(推荐 AI 默认使用)"""
    return query_paper(
        group_id=group_id,
        paper_id=paper_id,
        detail_level="summary",
        parse_mode="plain",
    )
