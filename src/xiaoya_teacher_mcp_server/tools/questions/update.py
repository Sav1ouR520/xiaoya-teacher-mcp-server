"""题目更新 MCP 工具"""

import json
import requests
import random
import string
from typing import Annotated, List, Optional
from pydantic import Field

from ...tools.questions.query import parse_question, parse_text
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, headers, MCP
from ...types.types import (
    AnswerChecked,
    AutoScoreType,
    LineText,
    ProgramSetting,
    QuestionScoreType,
    RequiredType,
    AutoStatType,
    RandomizationType,
    QUESTION_RICH_TEXT_DESC,
    REFERENCE_RICH_TEXT_DESC,
    ANSWER_EXPLANATION_DESC,
    IN_CASES_DESC,
)


@MCP.tool()
def update_question(
    question_id: Annotated[str, Field(description="题目id")],
    title: Annotated[
        Optional[list[LineText]],
        Field(description=QUESTION_RICH_TEXT_DESC),
    ] = None,
    score: Annotated[Optional[int], Field(description="题目分值", ge=0)] = None,
    description: Annotated[
        Optional[str],
        Field(description=ANSWER_EXPLANATION_DESC),
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
            description="填空题自动评分: 1精确/有序, 2部分/有序, 11精确/无序, 12部分/无序"
        ),
    ] = None,
    program_setting: Annotated[
        Optional[ProgramSetting], Field(description="编程题配置(仅编程题)")
    ] = None,
    need_parse: Annotated[bool, Field(description="是否返回解析题目内容")] = False,
) -> dict:
    """更新任意题目的通用配置"""
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
            payload["program_setting"] = program_setting.model_dump(
                exclude_none=True, exclude_defaults=True, exclude_unset=True
            )
            payload["program_setting"]["example_language"] = (
                program_setting.answer_language
            )
            payload["program_setting"]["example_code"] = program_setting.code_answer
            del payload["program_setting"]["in_cases"]
            del payload["program_setting"]["answer_item_id"]
        response = requests.post(url, json=payload, headers=headers()).json()
        if not response.get("success"):
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
        message = "题目设置更新成功"
        if program_setting is not None:
            case_response = _update_code_cases(
                question_id,
                program_setting.answer_item_id,
                program_setting.answer_language,
                program_setting.code_answer,
                program_setting.in_cases,
            )
            response["data"]["answer_items"] = case_response[0]
            message = "题目设置及测试用例更新成功"
        return ResponseUtil.success(
            parse_question(response["data"], need_parse), message
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
    """[仅限单选/多选题]更新单选或多选题的选项内容"""
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
            headers=headers(),
        ).json()

        if response.get("success"):
            simplified_data = [
                {
                    "answer_item_id": item["id"],
                    "value": parse_text(item["value"]),
                    "answer": AnswerChecked.get(item["answer_checked"]),
                }
                for item in response["data"]
            ]
            return ResponseUtil.success(simplified_data, "单/多选题选项更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("单/多选题选项更新失败", e)


@MCP.tool()
def update_fill_blank_answer(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="答案项id")],
    answer: Annotated[str, Field(description="答案文本内容")],
) -> dict:
    """[仅限填空题]更新填空题指定填空答案"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/updateAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
                "answer": answer,
            },
            headers=headers(),
        ).json()
        if response.get("success"):
            simplified_data = [
                {
                    "answer_item_id": item["id"],
                    "answer": item["answer"],
                }
                for item in response["data"]
            ]
            return ResponseUtil.success(simplified_data, "填空题指定填空答案更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("填空题答案更新失败", e)


@MCP.tool()
def update_true_false_answer(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="答案项id")],
) -> dict:
    """[仅限判断题]更新判断题答案,将选项id对应的选项设为正确答案"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/updateAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
                "answer_checked": 2,
            },
            headers=headers(),
        ).json()
        if response.get("success"):
            simplified_data = [
                {
                    "answer_item_id": item["id"],
                    "answer": AnswerChecked.get(item["answer_checked"]),
                }
                for item in response["data"]
            ]
            return ResponseUtil.success(simplified_data, "判断题答案更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("判断题答案更新失败", e)


@MCP.tool()
def update_short_answer_answer(
    question_id: Annotated[str, Field(description="题目id")],
    answer_item_id: Annotated[str, Field(description="答案项id")],
    answer: Annotated[
        list[LineText],
        Field(description=REFERENCE_RICH_TEXT_DESC),
    ],
) -> dict:
    """[仅限简答题]更新简答题参考答案"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/updateAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_id": str(answer_item_id),
                "answer": word_text(answer),
            },
            headers=headers(),
        ).json()
        if response.get("success"):
            simplified_data = [
                {
                    "answer_item_id": item["id"],
                    "answer": parse_text(item["answer"]),
                }
                for item in response["data"]
            ]
            return ResponseUtil.success(simplified_data, "简答题参考答案更新成功")
    except Exception as e:
        return ResponseUtil.error("简答题参考答案更新失败", e)


@MCP.tool()
def update_code_test_cases(
    question_id: Annotated[str, Field(description="题目id")],
    program_setting_id: Annotated[str, Field(description="题目设置ID")],
    answer_item_id: Annotated[str, Field(description="题目答案项ID")],
    answer_language: Annotated[str, Field(description="答案代码编程语言")],
    code_answer: Annotated[str, Field(description="答案代码[即将运行的代码]")],
    in_cases: Annotated[
        List[dict[str, str]],
        Field(description=IN_CASES_DESC, min_length=1),
    ],
) -> dict:
    """更新编程题答案代码和测试用例(会覆盖原用例)"""
    try:
        result = update_question(
            question_id=question_id,
            program_setting=ProgramSetting(
                id=program_setting_id,
                answer_item_id=answer_item_id,
                answer_language=answer_language,
                code_answer=code_answer,
                in_cases=in_cases,
            ),
        )
        if result.get("success"):
            return ResponseUtil.success(result["data"], "编程题测试用例更新成功")
        else:
            return ResponseUtil.error(
                result.get("msg") or result.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("编程题测试用例更新失败", e)


@MCP.tool()
def update_paper_randomization(
    paper_id: Annotated[str, Field(description="试卷ID")],
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
            headers=headers(),
        ).json()

        if response.get("success"):
            return ResponseUtil.success(None, "试卷随机化设置更新成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
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
    """[不限制题型]调整题目选项顺序"""
    try:
        response = requests.post(
            f"{MAIN_URL}/survey/moveAnswerItem",
            json={
                "question_id": str(question_id),
                "answer_item_ids": answer_item_ids,
            },
            headers=headers(),
        ).json()
        if response.get("success"):
            return ResponseUtil.success(None, "题目选项顺序调整成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("题目选项顺序调整失败", e)


@MCP.tool()
def update_paper_question_order(
    paper_id: Annotated[str, Field(description="试卷ID")],
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
            headers=headers(),
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
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("试卷题目顺序更新失败", e)


def _update_code_cases(
    question_id: Annotated[str, Field(description="题目ID")],
    answer_item_id: Annotated[str, Field(description="答案项ID")],
    language: Annotated[str, Field(description="编程语言")],
    code: Annotated[str, Field(description="运行代码")],
    in_cases: Annotated[
        List[dict[str, str]],
        Field(description="测试用例的输入列表[{'in': '输入内容'}]", min_length=1),
    ],
) -> dict:
    if not all(
        isinstance(case, dict) and set(case.keys()) == {"in"} for case in in_cases
    ):
        raise ValueError("测试用例格式错误, 每个测试用例必须仅包含'in'字段")
    case_result = requests.post(
        f"{MAIN_URL}/survey/program/runcase",
        json={
            "answer_item_id": str(answer_item_id),
            "language": language,
            "code": code,
            "input": json.dumps(in_cases),
        },
        headers=headers(),
    ).json()

    if not case_result.get("success"):
        raise ValueError(
            case_result.get("msg") or case_result.get("message") or "未知错误"
        )
    if not case_result["data"]["pass"]:
        raise ValueError(f"代码运行测试用例失败, 运行结果:{case_result['data']}")

    formatted_cases = [
        {"id": f"use_case_{index}", "in": case["in"], "out": case["out"]}
        for index, case in enumerate(case_result["data"]["result"])
    ]

    response = requests.post(
        f"{MAIN_URL}/survey/updateAnswerItem",
        json={
            "question_id": str(question_id),
            "answer_item_id": str(answer_item_id),
            "answer": json.dumps(formatted_cases),
        },
        headers=headers(),
    ).json()

    if not response.get("success"):
        raise ValueError(response.get("msg") or response.get("message") or "未知错误")
    simplified_data = [
        {
            "answer_item_id": item["id"],
            "answer": parse_text(item["answer"]),
        }
        for item in response["data"]
    ]
    return simplified_data


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
