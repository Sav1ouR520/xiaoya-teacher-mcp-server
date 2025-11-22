"""题目创建 MCP 工具"""

import requests
from typing import Annotated, List, Optional
from pydantic import Field

from ..questions.query import parse_question

from ..questions.update import (
    update_fill_blank_answer,
    update_question,
    update_question_options,
    update_short_answer_answer,
    update_true_false_answer,
)
from ..questions.delete import delete_questions
from ...types.types import (
    AttachmentQuestion,
    AttachmentQuestionData,
    ChoiceQuestion,
    CodeQuestion,
    CodeQuestionData,
    FillBlankQuestionData,
    LineText,
    MultipleChoiceQuestion,
    MultipleChoiceQuestionData,
    QuestionType,
    ShortAnswerQuestion,
    ShortAnswerQuestionData,
    SingleChoiceQuestionData,
    TrueFalseQuestion,
    FillBlankQuestion,
    TrueFalseQuestionData,
)
from typing import Union
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, headers, MCP


@MCP.tool()
def create_single_choice_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question: Annotated[ChoiceQuestion, Field(description="单选题信息")],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """创建单选题"""
    question_id = None
    try:
        question_id, answer_items, _ = _create_question_base(
            paper_id,
            QuestionType.SINGLE_CHOICE,
            question.score,
            question.insert_question_id,
        )

        question_data = _update_question_base(
            question_id,
            question.title,
            question.description,
            question.required,
            need_parse=need_parse,
        )

        for _ in range(len(answer_items), len(question.options)):
            resp = create_answer_item(paper_id, question_id)
            if not resp.get("success"):
                raise ValueError(resp.get("msg") or resp.get("message") or "未知错误")
            answer_items.append(resp["data"])

        for item, option in zip(answer_items, question.options):
            result = update_question_options(
                question_id, item["id"], option.text, option.answer
            )
            if not result["success"]:
                raise ValueError(
                    result.get("msg") or result.get("message") or "未知错误"
                )
        question_data["options"] = result["data"]
        if not need_detail:
            return ResponseUtil.success(None, "单选题创建成功")
        return ResponseUtil.success(question_data, "单选题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建单选题时发生异常", e)


@MCP.tool()
def create_multiple_choice_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question: Annotated[MultipleChoiceQuestion, Field(description="多选题信息")],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """创建多选题"""
    question_id = None
    try:
        question_id, answer_items, _ = _create_question_base(
            paper_id,
            QuestionType.MULTIPLE_CHOICE,
            question.score,
            question.insert_question_id,
        )

        question_data = _update_question_base(
            question_id,
            question.title,
            question.description,
            question.required,
            need_parse=need_parse,
        )

        for _ in range(len(answer_items), len(question.options)):
            resp = create_answer_item(paper_id, question_id)
            if not resp.get("success"):
                raise ValueError(resp.get("msg") or resp.get("message") or "未知错误")
            answer_items.append(resp["data"])

        for item, option in zip(answer_items, question.options):
            result = update_question_options(
                question_id, item["id"], option.text, option.answer
            )
            if not result["success"]:
                raise ValueError(
                    result.get("msg") or result.get("message") or "未知错误"
                )
        question_data["options"] = result["data"]
        if not need_detail:
            return ResponseUtil.success(None, "多选题创建成功")
        return ResponseUtil.success(question_data, "多选题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建多选题时发生异常", e)


@MCP.tool()
def create_fill_blank_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question: Annotated[FillBlankQuestion, Field(description="填空题信息")],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """创建填空题"""
    question_id = None
    try:
        question_id = _create_question_base(
            paper_id,
            QuestionType.FILL_BLANK,
            question.score,
            question.insert_question_id,
        )[0]

        _validate_fill_blank_question(question.title, len(question.options))
        count = sum(line.text.count("____") for line in question.title)

        result = create_blank_answer_items(paper_id, question_id, count)
        if not result["success"]:
            raise ValueError(result.get("msg") or result.get("message") or "未知错误")
        answer_items = result["data"]

        question_data = _update_question_base(
            question_id,
            question.title,
            question.description,
            question.required,
            is_split_answer=question.is_split_answer,
            automatic_stat=question.automatic_stat,
            automatic_type=question.automatic_type,
            need_parse=need_parse,
        )

        for item, option in zip(answer_items, question.options):
            result = update_fill_blank_answer(question_id, item["id"], option.text)
            if not result["success"]:
                raise ValueError(
                    result.get("msg") or result.get("message") or "未知错误"
                )
        question_data["options"] = result["data"]
        if not need_detail:
            return ResponseUtil.success(None, "填空题创建成功")
        return ResponseUtil.success(question_data, "填空题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建填空题时发生异常", e)


@MCP.tool()
def create_true_false_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question: Annotated[TrueFalseQuestion, Field(description="判断题信息")],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """创建判断题"""
    question_id = None
    try:
        question_id, answer_items, _ = _create_question_base(
            paper_id,
            QuestionType.TRUE_FALSE,
            question.score,
            question.insert_question_id,
        )

        question_data = _update_question_base(
            question_id,
            question.title,
            question.description,
            question.required,
            need_parse=need_parse,
        )

        answer_id = next(
            (
                item["id"]
                for item in answer_items
                if item["value"] == ("true" if question.answer else "")
            ),
            None,
        )
        if answer_id is None:
            raise ValueError("未找到匹配的答案项")
        result = update_true_false_answer(question_id, answer_id)
        if not result["success"]:
            raise ValueError(result.get("msg") or result.get("message") or "未知错误")
        question_data["options"] = result["data"]
        if not need_detail:
            return ResponseUtil.success(None, "判断题创建成功")
        return ResponseUtil.success(question_data, "判断题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建判断题时发生异常", e)


@MCP.tool()
def create_short_answer_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question: Annotated[ShortAnswerQuestion, Field(description="简答题信息")],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """创建简答题"""
    question_id = None
    try:
        question_id, answer_items, _ = _create_question_base(
            paper_id,
            QuestionType.SHORT_ANSWER,
            question.score,
            question.insert_question_id,
        )

        result = _update_question_base(
            question_id,
            question.title,
            question.description,
            question.required,
            need_parse=need_parse,
        )

        result["options"] = update_short_answer_answer(
            question_id=question_id,
            answer_item_id=answer_items[0]["id"],
            answer=question.answer,
        )
        if not need_detail:
            return ResponseUtil.success(None, "简答题创建成功")
        return ResponseUtil.success(result, "简答题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建简答题时发生异常", e)


@MCP.tool()
def create_attachment_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question: Annotated[AttachmentQuestion, Field(description="附件题信息")],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """创建附件题"""
    question_id = None
    try:
        question_id = _create_question_base(
            paper_id,
            QuestionType.ATTACHMENT,
            question.score,
            question.insert_question_id,
        )[0]

        result = _update_question_base(
            question_id,
            question.title,
            question.description,
            question.required,
            need_parse=need_parse,
        )
        if not need_detail:
            return ResponseUtil.success(None, "附件题创建成功")
        return ResponseUtil.success(result, "附件题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建附件题时发生异常", e)


@MCP.tool()
def create_code_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question: Annotated[CodeQuestion, Field(description="编程题信息")],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """创建编程题"""
    question_id = None
    try:
        question_id, answer_items, program_setting_id = _create_question_base(
            paper_id,
            QuestionType.CODE,
            question.score,
            question.insert_question_id,
        )

        if program_setting_id is None:
            raise ValueError("编程题创建失败, 未分配编程设置ID")
        if len(answer_items) == 0:
            raise ValueError("编程题创建失败, 未分配答案项ID")
        question.program_setting.id = program_setting_id
        question.program_setting.answer_item_id = answer_items[0]["id"]
        result = _update_question_base(
            question_id,
            question.title,
            question.description,
            question.required,
            program_setting=question.program_setting,
            need_parse=need_parse,
        )
        if not need_detail:
            return ResponseUtil.success(None, "编程题创建并配置编程设置和测试用例成功")
        return ResponseUtil.success(result, "编程题创建并配置编程设置和测试用例成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建编程题时发生异常", e)


@MCP.tool()
def batch_create_questions(
    paper_id: Annotated[str, Field(description="试卷ID")],
    questions: Annotated[
        List[
            Union[
                ChoiceQuestion,
                TrueFalseQuestion,
                FillBlankQuestion,
                AttachmentQuestion,
                ShortAnswerQuestion,
                CodeQuestion,
            ]
        ],
        Field(description="题目列表", min_length=1),
    ],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """批量创建题目(非官方接口),不稳定但功能更强大[支持单选、多选、填空、判断、附件、简答题、编程题]"""
    success_count, failed_count, results = 0, 0, {"details": [], "questions": []}

    question_handlers = {
        QuestionType.SINGLE_CHOICE: create_single_choice_question,
        QuestionType.MULTIPLE_CHOICE: create_multiple_choice_question,
        QuestionType.TRUE_FALSE: create_true_false_question,
        QuestionType.FILL_BLANK: create_fill_blank_question,
        QuestionType.SHORT_ANSWER: create_short_answer_question,
        QuestionType.ATTACHMENT: create_attachment_question,
        QuestionType.CODE: create_code_question,
    }

    for i, question in enumerate(questions, 1):
        try:
            handler = question_handlers.get(question.type)
            if handler is None:
                failed_count += 1
                results["details"].append(f"第{i}题: 创建失败 - 不支持的题目类型")
                continue

            result = handler(
                paper_id, question, need_detail=need_detail, need_parse=need_parse
            )

            if result["success"]:
                success_count += 1
                results["questions"].append(result["data"])
                results["details"].append(
                    f"[第{i}题][创建成功][{QuestionType.get(question.type)}][{''.join(line.text for line in question.title)}]"
                )
            else:
                failed_count += 1
                results["details"].append(
                    f"[第{i}题][创建失败][{QuestionType.get(question.type)}][{result['message']}]"
                )
        except Exception as e:
            failed_count += 1
            results["details"].append(
                f"[第{i}题][创建异常][{QuestionType.get(question.type)}][{str(e)}]"
            )
    if not need_detail:
        results.pop("questions", None)
    summary = f"[批量创建完成][成功{success_count}题][失败{failed_count}题][总计{len(questions)}题]"
    return ResponseUtil.success(results, summary)


@MCP.tool()
def office_create_questions(
    paper_id: Annotated[str, Field(description="试卷ID")],
    questions: Annotated[
        List[
            Union[
                SingleChoiceQuestionData,
                MultipleChoiceQuestionData,
                FillBlankQuestionData,
                TrueFalseQuestionData,
                ShortAnswerQuestionData,
                AttachmentQuestionData,
                CodeQuestionData,
            ]
        ],
        Field(description="题目列表", min_length=1),
    ],
    need_detail: Annotated[bool, Field(description="是否返回详细题目信息")] = False,
    need_parse: Annotated[bool, Field(description="是否返回原始题目内容")] = False,
) -> dict:
    """批量导入题目(官方接口),稳定性强[仅支持单选、多选、填空、判断、简答、附件题]"""
    url = f"{MAIN_URL}/survey/question/import"
    try:
        for i, question in enumerate(questions, 1):
            if question.type == QuestionType.FILL_BLANK:
                try:
                    _validate_fill_blank_question(
                        question.title, len(question.standard_answers)
                    )
                except ValueError as e:
                    return ResponseUtil.error(f"第{i}题格式错误", e)
            elif question.type not in QuestionType:
                return ResponseUtil.error(f"第{i}题类型不支持导入: {question.type}")

        questions_data = []
        for question in questions:
            data = question.model_dump()
            if question.type == QuestionType.SHORT_ANSWER:
                data["answer_items"] = [{"seqno": "A"}]
            elif question.type == QuestionType.TRUE_FALSE:
                data["answer_items"] = [
                    {"seqno": "A", "context": "true"},
                    {"seqno": "B", "context": ""},
                ]
            elif question.type == QuestionType.ATTACHMENT:
                data["answer_items"] = [{"seqno": "A"}]
            elif question.type == QuestionType.CODE:
                data["answer_items"] = []
            questions_data.append(data)
        response = requests.post(
            url,
            json={"paper_id": str(paper_id), "questions": questions_data},
            headers=headers(),
        ).json()
        if response.get("success"):
            if not need_detail:
                return ResponseUtil.success(
                    None,
                    f"[批量导入完成][共{len(response['data'])}题]",
                )
            return ResponseUtil.success(
                [parse_question(question, need_parse) for question in response["data"]],
                f"[批量导入完成][共{len(response['data'])}题]",
            )
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("批量导入题目时发生异常", e)


@MCP.tool()
def create_question(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question_type: Annotated[int, Field(description="题目类型编号")],
    score: Annotated[int, Field(description="题目分数", gt=0)],
    insert_question_id: Annotated[
        Optional[str], Field(description="插入指定题目ID后面")
    ] = None,
) -> dict:
    """在试卷中创建新题目(空白题目)"""
    try:
        payload = {
            "paper_id": str(paper_id),
            "type": question_type,
            "score": score,
        }
        if insert_question_id is not None and len(insert_question_id) == 19:
            payload["insert_question_id"] = str(insert_question_id)

        response = requests.post(
            f"{MAIN_URL}/survey/addQuestion",
            json=payload,
            headers=headers(),
        ).json()
        if response.get("success"):
            return ResponseUtil.success(
                parse_question(response["data"], False), "题目创建成功"
            )
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )

    except Exception as e:
        return ResponseUtil.error("题目创建失败", e)


@MCP.tool()
def create_blank_answer_items(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question_id: Annotated[str, Field(description="题目id")],
    count: Annotated[int, Field(description="空白答案项数量", gt=0)],
) -> dict:
    """创建空白答案项"""

    try:
        response = requests.post(
            f"{MAIN_URL}/survey/createBlankAnswerItems",
            json={
                "paper_id": str(paper_id),
                "question_id": str(question_id),
                "count": count,
            },
            headers=headers(),
        )
        response = response.json()
        if response.get("success"):
            return ResponseUtil.success(
                response["data"]["answer_items"], "空白答案项创建成功"
            )
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("空白答案项创建失败", e)


@MCP.tool()
def create_answer_item(
    paper_id: Annotated[str, Field(description="试卷ID")],
    question_id: Annotated[str, Field(description="题目id")],
) -> dict:
    """创建答案项"""

    try:
        response = requests.post(
            f"{MAIN_URL}/survey/createAnswerItem",
            json={"paper_id": str(paper_id), "question_id": str(question_id)},
            headers=headers(),
        ).json()["data"]
        return ResponseUtil.success(response, "答案项创建成功")
    except Exception as e:
        return ResponseUtil.error("答案项创建失败", e)


def _create_question_base(
    paper_id: str,
    question_type: QuestionType,
    score: int,
    insert_question_id: Optional[str] = None,
) -> tuple:
    """创建题目基础信息并返回question_id和answer_items"""
    data = create_question(paper_id, question_type.value, score, insert_question_id)
    if not data["success"]:
        raise ValueError(data.get("msg") or data.get("message") or "未知错误")
    program_setting_id = None
    if question_type == QuestionType.CODE:
        program_setting_id = data["data"]["program_setting"]["id"]
    return (data["data"]["id"], data["data"]["options"], program_setting_id)


def _update_question_base(
    question_id: str,
    title: List[LineText],
    description: str,
    required: bool,
    **kwargs,
) -> None:
    """更新题目基础信息, 失败时清理题目"""
    result = update_question(
        question_id, title=title, description=description, required=required, **kwargs
    )

    if not result["success"]:
        raise ValueError(result.get("msg") or result.get("message") or "未知错误")
    return result["data"]


def _validate_fill_blank_question(
    title: List[LineText] | str, answers_count: int
) -> None:
    """验证填空题的格式是否正确"""
    if isinstance(title, str):
        title = [LineText(text=title)]
    if not any("____" in line.text for line in title):
        raise ValueError("填空题标题必须包含空白标记'____'")

    blank_count = sum(line.text.count("____") for line in title)
    if blank_count != answers_count:
        raise ValueError(
            f"空白标记数量({blank_count})与答案数量({answers_count})不匹配"
        )
