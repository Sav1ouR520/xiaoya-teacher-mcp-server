"""
题目更新MCP工具

此模块为在线测试系统中更新题目及其选项提供MCP工具.
"""

import json
import requests
import random
import string
from typing import Annotated, List, Optional
from pydantic import Field

from ...utils.response import ResponseUtil
from ...config import MAIN_URL, create_headers, MCP
from ...types.types import (
    AnswerChecked,
    AutoScoreType,
    LineText,
    ProgramSetting,
    QuestionScoreType,
    RequiredType,
    AutoStatType,
    RandomizationType,
)


@MCP.tool()
def update_question(
    question_id: Annotated[str, Field(description="题目id")],
    title: Annotated[
        Optional[list[LineText]],
        Field(
            description="题目描述(支持富文本，多行):\n"
            "- 多行:列表形式\n"
            "- 富文本样式:BOLD(粗体)、ITALIC(斜体)、UNDERLINE(下划线)、CODE(代码)\n"
            "- 题目描述格式例下(一行版本,可以多行,必须时换行):\n"
            "  {\n"
            "    'text': '题目内容', 'line_type': 'unstyled'(或 unordered-list-item, ordered-list-item, code-block), \n"
            "    'inlineStyleRanges': [ {'offset': 0, 'length': 4, 'style': 'BOLD'} ]\n"
            "  }\n"
        ),
    ] = None,
    score: Annotated[Optional[int], Field(description="题目分值", ge=0)] = None,
    description: Annotated[
        Optional[str],
        Field(
            description="答案解析(答案请提供足够详细解析,避免过于简短或过长,注意不要搞错成题目描述)"
        ),
    ] = None,
    required: Annotated[
        Optional[RequiredType], Field(description="是否必答 1=否, 2=是")
    ] = None,
    is_split_answer: Annotated[
        Optional[bool], Field(description="是否允许多个答案(仅填空题)")
    ] = None,
    automatic_stat: Annotated[
        Optional[AutoStatType],
        Field(description="自动评分设置(仅填空题) 1=关闭, 2=开启"),
    ] = None,
    automatic_type: Annotated[
        Optional[AutoScoreType],
        Field(
            description="""填空题自动评分类型(仅填空题)[必须严格根据题目情况选择]:
                        - 1=精确匹配+有序排序: 答案必须完全匹配且顺序一致,适用于每个空只有一个正确答案的情况;
                        - 2=部分匹配+有序排序: 答案部分匹配且顺序一致,适用于每个空有多个正确答案的情况;
                        - 11=精确匹配+无序排序: 答案必须完全匹配但顺序不限,适用于每个空只有一个正确答案且答案顺序不重要的情况;
                        - 12=部分匹配+无序排序: 答案部分匹配且顺序不限,适用于每个空有多个正确答案且答案顺序不重要的情况;
                    """.replace("\n", " ").strip(),
        ),
    ] = None,
    program_setting: Annotated[
        Optional[ProgramSetting], Field(description="编程题配置(仅编程题)")
    ] = None,
) -> dict:
    """更新题目设置"""
    try:
        url = f"{MAIN_URL}/survey/updateQuestion"
        payload = {"question_id": str(question_id)}

        if title is not None:
            payload["title"] = word_text(title)
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
            if program_setting.id is None:
                raise ValueError("编程题创建失败, 没有题目设置ID")
            payload["program_setting"] = program_setting.model_dump()
            payload["program_setting"]["example_language"] = (
                program_setting.answer_language
            )
            payload["program_setting"]["example_code"] = program_setting.code_answer

        response = requests.post(url, json=payload, headers=create_headers()).json()

        if response.get("success"):
            return ResponseUtil.success(None, "题目设置更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message", "未知错误")
            )
    except Exception as e:
        return ResponseUtil.error("题目设置更新失败", e)


@MCP.tool()
def update_question_options(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[list[LineText], Field(description="选项id")],
    option_text: Annotated[Optional[str], Field(description="选项文本内容")] = None,
    is_answer: Annotated[Optional[bool], Field(description="是否为正确答案")] = False,
) -> dict:
    """更新单选或多选题的选项内容"""
    try:
        payload = {
            "question_id": str(question_id),
            "answer_item_id": str(answer_item_id),
        }
        if option_text is not None:
            payload["value"] = word_text(option_text)
        if is_answer:
            payload["answer_checked"] = 2

        response = requests.post(
            url=f"{MAIN_URL}/survey/updateAnswerItem",
            json=payload,
            headers=create_headers(),
        ).json()

        if response.get("success"):
            simplified_data = [
                {
                    "id": item["id"],
                    "question_id": item["question_id"],
                    "answer": item["value"],
                    "correct": AnswerChecked.get(item["answer_checked"]),
                }
                for item in response["data"]
            ]
            return ResponseUtil.success(simplified_data, "单/多选题选项更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message", "未知错误")
            )
    except Exception as e:
        return ResponseUtil.error("单/多选题选项更新失败", e)


@MCP.tool()
def update_fill_blank_options(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="选项id")],
    answer: Annotated[str, Field(description="选项文本内容")],
) -> dict:
    """更新填空题的选项内容"""
    try:
        response = requests.post(
            url=f"{MAIN_URL}/survey/updateAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
                "value": answer,
            },
            headers=create_headers(),
        ).json()

        if response.get("success"):
            simplified_data = [
                {
                    "id": item["id"],
                    "question_id": item["question_id"],
                    "answer": item["answer"],
                }
                for item in response["data"]
            ]
            return ResponseUtil.success(simplified_data, "填空题选项更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message", "未知错误")
            )
    except Exception as e:
        return ResponseUtil.error("填空题选项更新失败", e)


@MCP.tool()
def update_fill_blank_answer(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="答案项id")],
    answer_text: Annotated[str, Field(description="答案文本内容")],
) -> dict:
    """更新填空答案"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/updateAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
                "answer": answer_text,
            },
            headers=create_headers(),
        ).json()
        return ResponseUtil.success(response, "填空题答案更新成功")
    except Exception as e:
        return ResponseUtil.error("填空题答案更新失败", e)


@MCP.tool()
def update_true_false_answer(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="答案项id")],
) -> dict:
    """更新判断题答案,将选项id对应的选项设为正确答案"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/updateAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
                "answer_checked": 2,
            },
            headers=create_headers(),
        ).json()
        return ResponseUtil.success(response, "判断题答案更新成功")
    except Exception as e:
        return ResponseUtil.error("判断题答案更新失败", e)


@MCP.tool()
def update_code_test_cases(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="答案项ID")],
    answer_language: Annotated[str, Field(description="答案代码编程语言")],
    code_answer: Annotated[str, Field(description="答案代码[即将运行的代码]")],
    input: Annotated[
        List[dict[str, str]], Field(description="输入数据[{'in': '输入内容'}]")
    ],
) -> dict:
    """更新编程题答案代码和测试用例,运行答案代码,自动生成测试用例(注意:会覆盖原有用例)"""
    try:
        result = update_question(
            question_id=question_id,
            program_setting=ProgramSetting(
                id=answer_item_id,
                answer_language=answer_language,
                code_answer=code_answer,
            ),
        )
        if not result.get("success"):
            return ResponseUtil.error(
                result.get("msg") or result.get("message", "未知错误")
            )
        return _update_code_cases(answer_item_id, answer_language, code_answer, input)
    except Exception as e:
        return ResponseUtil.error("编程题测试用例更新失败", e)


@MCP.tool()
def update_paper_randomization(
    paper_id: Annotated[str, Field(description="试卷paper_id")],
    question_shuffle: Annotated[
        RandomizationType, Field(description="是否启用题目随机化,1为关闭,2为开启")
    ] = RandomizationType.DISABLED,
    option_shuffle: Annotated[
        RandomizationType, Field(description="是否启用选项随机化,1为关闭,2为开启")
    ] = RandomizationType.DISABLED,
    question_score_type: Annotated[
        QuestionScoreType, Field(description="题目评分类型 1=严格计分, 2=宽分模式")
    ] = QuestionScoreType.LENIENT,
) -> dict:
    """更新试卷的题目和选项随机化设置"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/updatePaper",
            json={
                "paper_id": str(paper_id),
                "question_random": option_shuffle,
                "random": question_shuffle,
                "question_score_type": question_score_type,
            },
            headers=create_headers(),
        ).json()

        if response.get("success"):
            return ResponseUtil.success(None, "试卷随机化设置更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message", "未知错误")
            )
    except Exception as e:
        return ResponseUtil.error("试卷随机化设置更新失败", e)


@MCP.tool()
def move_answer_item(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_ids: Annotated[
        list[str], Field(description="按新顺序排列的选项id列表", min_length=1)
    ],
) -> dict:
    """调整题目选项顺序"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/moveAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_ids": answer_item_ids,
            },
            headers=create_headers(),
        ).json()
        if response.get("success"):
            return ResponseUtil.success(None, "题目选项顺序调整成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message", "未知错误")
            )
    except Exception as e:
        return ResponseUtil.error("题目选项顺序调整失败", e)


@MCP.tool()
def update_paper_question_order(
    paper_id: Annotated[str, Field(description="试卷paper_id")],
    question_ids: Annotated[
        List[str], Field(description="按新顺序排列的题目id列表", min_length=1)
    ],
) -> dict:
    """更新试卷的题目顺序"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/moveQuestion",
            json={
                "paper_id": str(paper_id),
                "question_ids": [str(qid) for qid in question_ids],
            },
            headers=create_headers(),
        ).json()
        if response.get("success"):
            filtered_data = {
                k: response["data"][k]
                if k != "questions_sort"
                else response["data"][k].split(",")
                for k in ["id", "title", "updated_at", "questions_sort"]
                if k in response["data"]
            }
            return ResponseUtil.success(filtered_data, "试卷题目顺序更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message", "未知错误")
            )
    except Exception as e:
        return ResponseUtil.error("试卷题目顺序更新失败", e)


def _update_code_cases(
    answer_item_id: Annotated[str, Field(description="答案项ID")],
    language: Annotated[str, Field(description="编程语言")],
    code: Annotated[str, Field(description="运行代码")],
    input: Annotated[
        List[dict[str, str]], Field(description="输入数据[{'in': '输入内容'}]")
    ],
) -> dict:
    try:
        case_result = requests.post(
            f"{MAIN_URL}/survey/program/runcase",
            json={
                "answer_item_id": answer_item_id,
                "language": language,
                "code": code,
                "input": json.dumps(input),
            },
            headers=create_headers(),
        ).json()

        if not case_result.get("success"):
            return ResponseUtil.error(
                case_result.get("msg") or case_result.get("message", "未知错误")
            )

        if not case_result["data"]["pass"]:
            return ResponseUtil.error(case_result["data"], "测试用例运行失败")

        formatted_cases = [
            {"id": f"use_case_{index}", "in": case["in"], "out": case["out"]}
            for index, case in enumerate(case_result["data"]["result"])
        ]

        response = requests.post(
            f"{MAIN_URL}/survey/updateAnswerItem",
            json={
                "answer_item_id": str(answer_item_id),
                "answer": json.dumps(formatted_cases),
            },
            headers=create_headers(),
        ).json()

        return ResponseUtil.success(response, "编程题测试用例更新成功")
    except Exception as e:
        return ResponseUtil.error("编程题测试用例更新失败", e)


def word_text(lines: list[LineText]) -> dict:
    return json.dumps(
        {
            "blocks": [
                {
                    "key": "".join(
                        random.choices(string.ascii_lowercase + string.digits, k=5)
                    ),
                    "text": line.text,
                    "type": line.line_type,
                    "depth": 0,
                    "inlineStyleRanges": [
                        style.dict() for style in line.inlineStyleRanges
                    ],
                    "entityRanges": [],
                    "data": {},
                }
                for line in lines
            ],
            "entityMap": {},
        }
    )
