"""题目创建 MCP 工具"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...tools.questions.normalize import parse_question, validate_office_import_results
from ...types.enums import QuestionType
from ...types.question_models import (
    AttachmentQuestion,
    AttachmentQuestionData,
    ChoiceQuestion,
    CodeQuestion,
    CodeQuestionData,
    FillBlankQuestion,
    FillBlankQuestionData,
    MultipleChoiceQuestion,
    MultipleChoiceQuestionData,
    ShortAnswerQuestion,
    ShortAnswerQuestionData,
    SingleChoiceQuestionData,
    TrueFalseQuestion,
    TrueFalseQuestionData,
)
from ...utils.client import (
    APIRequestError,
    expect_success,
    post_json,
)
from ...utils.response import ResponseUtil
from ...utils.rich_text import render_rich_text_output
from .delete import delete_questions
from .update import (
    update_fill_blank_answer,
    update_question,
    update_question_options,
    update_short_answer_answer,
    update_true_false_answer,
)

KNOWN_CREATION_ERRORS = (APIRequestError, ValueError)


def resolve_parse_mode(need_parse: bool) -> str:
    return "plain" if need_parse else "raw"


def extract_plain_title(title: str | None, title_raw: dict[str, Any] | None) -> str:
    return render_rich_text_output(title_raw if title_raw is not None else title, "plain") or ""


def create_question_data(
    paper_id: str,
    question_type: QuestionType,
    score: int,
    insert_question_id: str | None = None,
) -> dict[str, Any]:
    payload = {"paper_id": str(paper_id), "type": question_type.value, "score": score}
    if insert_question_id is not None and len(insert_question_id) == 19:
        payload["insert_question_id"] = str(insert_question_id)
    return parse_question(
        expect_success(post_json(f"{MAIN_URL}/survey/addQuestion", payload=payload)),
        parse_mode="raw",
    )


def create_blank_answer_items_data(
    paper_id: str, question_id: str, count: int
) -> list[dict[str, Any]]:
    return expect_success(
        post_json(
            f"{MAIN_URL}/survey/createBlankAnswerItems",
            payload={"paper_id": str(paper_id), "question_id": str(question_id), "count": count},
        )
    )["answer_items"]


def create_answer_item_data(paper_id: str, question_id: str) -> dict[str, Any]:
    return expect_success(
        post_json(
            f"{MAIN_URL}/survey/createAnswerItem",
            payload={"paper_id": str(paper_id), "question_id": str(question_id)},
        )
    )


def update_question_base(
    *,
    question_id: str,
    title: str | None,
    title_raw: dict[str, Any] | None,
    description: str,
    required: bool,
    parse_mode: str,
    **kwargs,
) -> dict[str, Any]:
    result = update_question(
        question_id=question_id,
        title=title,
        title_raw=title_raw,
        description=description,
        required=required,
        parse_mode=parse_mode,
        **kwargs,
    )
    if not result.get("success"):
        raise ValueError(result.get("message") or "题目设置更新失败")
    return result["data"]


def validate_fill_blank_question(
    title: str | None, title_raw: dict[str, Any] | None, answers_count: int
) -> str:
    plain_title = extract_plain_title(title, title_raw)
    if "____" not in plain_title:
        raise ValueError("填空题标题必须包含空白标记'____'")
    blank_count = plain_title.count("____")
    if blank_count != answers_count:
        raise ValueError(f"空白标记数量({blank_count})与答案数量({answers_count})不匹配")
    return plain_title


@MCP.tool()
def create_single_choice_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[ChoiceQuestion, Field(description=desc.SINGLE_CHOICE_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建单选题"""
    return _create_choice_question(
        paper_id=paper_id,
        question_type=QuestionType.SINGLE_CHOICE,
        question=question,
        need_detail=need_detail,
        need_parse=need_parse,
    )


@MCP.tool()
def create_multiple_choice_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[
        MultipleChoiceQuestion, Field(description=desc.MULTIPLE_CHOICE_QUESTION_DESC)
    ],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建多选题"""
    return _create_choice_question(
        paper_id=paper_id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question=question,
        need_detail=need_detail,
        need_parse=need_parse,
    )


@MCP.tool()
def create_fill_blank_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[FillBlankQuestion, Field(description=desc.FILL_BLANK_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建填空题"""
    question_id = None
    try:
        parse_mode = resolve_parse_mode(need_parse)
        validate_fill_blank_question(question.title, question.title_raw, len(question.options))

        question_data = create_question_data(
            paper_id, QuestionType.FILL_BLANK, question.score, question.insert_question_id
        )
        question_id = question_data["id"]
        question_data = update_question_base(
            question_id=question_id,
            title=question.title,
            title_raw=question.title_raw,
            description=question.description,
            required=question.required,
            is_split_answer=question.is_split_answer,
            automatic_stat=question.automatic_stat,
            automatic_type=question.automatic_type,
            parse_mode=parse_mode,
        )
        blank_items = create_blank_answer_items_data(paper_id, question_id, len(question.options))
        last_blank_data = []
        for item, answer in zip(blank_items, question.options, strict=False):
            r = update_fill_blank_answer(question_id, item["id"], answer.text)
            if not r.get("success"):
                raise ValueError(r.get("message") or "填空答案更新失败")
            last_blank_data = r["data"]
        question_data["options"] = last_blank_data
        return ResponseUtil.success(question_data if need_detail else None, "填空题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建填空题时发生异常", e)


@MCP.tool()
def create_true_false_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[TrueFalseQuestion, Field(description=desc.TRUE_FALSE_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建判断题"""
    question_id = None
    try:
        parse_mode = resolve_parse_mode(need_parse)
        question_data = create_question_data(
            paper_id, QuestionType.TRUE_FALSE, question.score, question.insert_question_id
        )
        question_id = question_data["id"]
        answer_items = question_data["options"]

        answer_id = next(
            (
                item["answer_item_id"]
                for item in answer_items
                if item["value"] == ("true" if question.answer else "")
            ),
            None,
        )
        if answer_id is None:
            raise ValueError("未找到匹配的答案项")

        question_data = update_question_base(
            question_id=question_id,
            title=question.title,
            title_raw=question.title_raw,
            description=question.description,
            required=question.required,
            parse_mode=parse_mode,
        )
        r = update_true_false_answer(question_id, answer_id)
        if not r.get("success"):
            raise ValueError(r.get("message") or "判断题答案设置失败")
        question_data["options"] = r["data"]
        return ResponseUtil.success(question_data if need_detail else None, "判断题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建判断题时发生异常", e)


@MCP.tool()
def create_short_answer_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[ShortAnswerQuestion, Field(description=desc.SHORT_ANSWER_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建简答题"""
    question_id = None
    try:
        parse_mode = resolve_parse_mode(need_parse)
        question_data = create_question_data(
            paper_id, QuestionType.SHORT_ANSWER, question.score, question.insert_question_id
        )
        question_id = question_data["id"]
        if not question_data.get("options"):
            raise ValueError("简答题创建失败: 服务端未返回答案项")
        answer_item_id = question_data["options"][0]["answer_item_id"]

        question_data = update_question_base(
            question_id=question_id,
            title=question.title,
            title_raw=question.title_raw,
            description=question.description,
            required=question.required,
            parse_mode=parse_mode,
        )
        r = update_short_answer_answer(
            question_id=question_id,
            answer_item_id=answer_item_id,
            answer=question.answer,
            answer_raw=question.answer_raw,
            parse_mode=parse_mode,
        )
        if not r.get("success"):
            raise ValueError(r.get("message") or "简答题答案设置失败")
        question_data["options"] = r["data"]
        return ResponseUtil.success(question_data if need_detail else None, "简答题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建简答题时发生异常", e)


@MCP.tool()
def create_attachment_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[AttachmentQuestion, Field(description=desc.ATTACHMENT_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建附件题"""
    question_id = None
    try:
        parse_mode = resolve_parse_mode(need_parse)
        question_data = create_question_data(
            paper_id, QuestionType.ATTACHMENT, question.score, question.insert_question_id
        )
        question_id = question_data["id"]
        question_data = update_question_base(
            question_id=question_id,
            title=question.title,
            title_raw=question.title_raw,
            description=question.description,
            required=question.required,
            parse_mode=parse_mode,
        )
        return ResponseUtil.success(question_data if need_detail else None, "附件题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建附件题时发生异常", e)


@MCP.tool()
def create_code_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[CodeQuestion, Field(description=desc.CODE_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建编程题"""
    question_id = None
    try:
        parse_mode = resolve_parse_mode(need_parse)
        question_data = create_question_data(
            paper_id, QuestionType.CODE, question.score, question.insert_question_id
        )
        question_id = question_data["id"]
        options = question_data["options"]
        program_setting_id = question_data["program_setting"]["id"]

        if not options:
            raise ValueError("编程题创建失败, 未分配答案项")

        program_setting = question.program_setting
        program_setting.id = program_setting_id
        program_setting.answer_item_id = options[0]["answer_item_id"]
        # 如果未指定答案语言, 默认使用第一个允许的语言
        if program_setting.answer_language is None and program_setting.language:
            program_setting.answer_language = program_setting.language[0]

        question_data = update_question_base(
            question_id=question_id,
            title=question.title,
            title_raw=question.title_raw,
            description=question.description,
            required=question.required,
            program_setting=program_setting,
            parse_mode=parse_mode,
        )
        return ResponseUtil.success(question_data if need_detail else None, "编程题创建成功")
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        return ResponseUtil.error("创建编程题时发生异常", e)


@MCP.tool()
def batch_create_questions(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    questions: Annotated[
        list[
            Annotated[
                ChoiceQuestion
                | MultipleChoiceQuestion
                | TrueFalseQuestion
                | FillBlankQuestion
                | AttachmentQuestion
                | ShortAnswerQuestion
                | CodeQuestion,
                Field(discriminator="type"),
            ]
        ],
        Field(description=desc.QUESTION_LIST_DESC, min_length=1),
    ],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """批量创建题目(非官方接口),不稳定但功能更强大[支持单选、多选、填空、判断、附件、简答题、编程题]"""
    question_handlers = {
        QuestionType.SINGLE_CHOICE: create_single_choice_question,
        QuestionType.MULTIPLE_CHOICE: create_multiple_choice_question,
        QuestionType.TRUE_FALSE: create_true_false_question,
        QuestionType.FILL_BLANK: create_fill_blank_question,
        QuestionType.SHORT_ANSWER: create_short_answer_question,
        QuestionType.ATTACHMENT: create_attachment_question,
        QuestionType.CODE: create_code_question,
    }
    success_count, failed_count = 0, 0
    results: dict[str, Any] = {
        "details": [],
        "questions": [],
        "success_items": [],
        "failed_items": [],
    }

    for index, question in enumerate(questions, 1):
        question_title = extract_plain_title(
            getattr(question, "title", None),
            getattr(question, "title_raw", None),
        )
        question_type = QuestionType.get(question.type)
        try:
            handler = question_handlers.get(question.type)
            if handler is None:
                failed_count += 1
                results["failed_items"].append(
                    {
                        "index": index,
                        "type": question_type,
                        "title": question_title,
                        "message": "不支持的题目类型",
                    }
                )
                results["details"].append(f"第{index}题: 创建失败 - 不支持的题目类型")
                continue
            result = handler(paper_id, question, need_detail=True, need_parse=need_parse)
            if result["success"]:
                success_count += 1
                question_data = result["data"]
                question_id = question_data.get("id") if isinstance(question_data, dict) else None
                results["questions"].append(question_data)
                results["success_items"].append(
                    {
                        "index": index,
                        "type": question_type,
                        "title": question_title,
                        "question_id": question_id,
                    }
                )
                results["details"].append(
                    f"[第{index}题][创建成功][{question_type}][{question_title}]"
                )
            else:
                failed_count += 1
                results["failed_items"].append(
                    {
                        "index": index,
                        "type": question_type,
                        "title": question_title,
                        "message": result["message"],
                    }
                )
                results["details"].append(
                    f"[第{index}题][创建失败][{question_type}][{result['message']}]"
                )
        except Exception as e:
            failed_count += 1
            results["failed_items"].append(
                {
                    "index": index,
                    "type": question_type,
                    "title": question_title,
                    "message": str(e),
                }
            )
            results["details"].append(f"[第{index}题][创建异常][{question_type}][{str(e)}]")

    results["success_count"] = success_count
    results["failed_count"] = failed_count
    results["partial_success"] = bool(success_count and failed_count)
    if not need_detail:
        results.pop("questions", None)
    summary = f"[批量创建完成][成功{success_count}题][失败{failed_count}题][总计{len(questions)}题]"
    if failed_count:
        return ResponseUtil.error(summary, data=results)
    return ResponseUtil.success(results, summary)


@MCP.tool()
def office_create_questions(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    questions: Annotated[
        list[
            Annotated[
                SingleChoiceQuestionData
                | MultipleChoiceQuestionData
                | FillBlankQuestionData
                | TrueFalseQuestionData
                | ShortAnswerQuestionData
                | AttachmentQuestionData
                | CodeQuestionData,
                Field(discriminator="type"),
            ]
        ],
        Field(description=desc.QUESTION_LIST_DESC, min_length=1),
    ],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """批量导入题目(官方接口),稳定性强[仅支持单选、多选、填空、判断、简答、附件题]"""
    try:
        for index, question in enumerate(questions, 1):
            if question.type == QuestionType.FILL_BLANK:
                try:
                    validate_fill_blank_question(
                        question.title, None, len(question.standard_answers)
                    )
                except ValueError as e:
                    return ResponseUtil.error(f"第{index}题格式错误", e)

        fixed_answer_items = {
            QuestionType.SHORT_ANSWER: [{"seqno": "A"}],
            QuestionType.TRUE_FALSE: [
                {"seqno": "A", "context": "true"},
                {"seqno": "B", "context": ""},
            ],
            QuestionType.ATTACHMENT: [{"seqno": "A"}],
            QuestionType.CODE: [],
        }
        questions_data = []
        for q in questions:
            data = q.model_dump()
            items = fixed_answer_items.get(q.type)
            if items is not None:
                data["answer_items"] = items
            questions_data.append(data)

        imported_questions = expect_success(
            post_json(
                f"{MAIN_URL}/survey/question/import",
                payload={"paper_id": str(paper_id), "questions": questions_data},
            )
        )
        validation_errors = validate_office_import_results(questions, imported_questions)
        if validation_errors:
            return ResponseUtil.error("批量导入完成但结果校验失败: " + "; ".join(validation_errors))
        if not need_detail:
            return ResponseUtil.success(None, f"[批量导入完成][共{len(imported_questions)}题]")
        return ResponseUtil.success(
            [
                parse_question(q, parse_mode=resolve_parse_mode(need_parse))
                for q in imported_questions
            ],
            f"[批量导入完成][共{len(imported_questions)}题]",
        )
    except KNOWN_CREATION_ERRORS as e:
        return ResponseUtil.error("批量导入题目时发生异常", e)


@MCP.tool()
def create_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_type: Annotated[int, Field(description=desc.QUESTION_TYPE_DESC)],
    score: Annotated[int, Field(description=desc.QUESTION_SCORE_DESC, gt=0)],
    insert_question_id: Annotated[str | None, Field(description=desc.INSERT_AFTER_DESC)] = None,
) -> dict:
    """在试卷中创建新题目(空白题目)"""
    try:
        question_data = create_question_data(
            paper_id=paper_id,
            question_type=QuestionType(question_type),
            score=score,
            insert_question_id=insert_question_id,
        )
        return ResponseUtil.success(question_data, "题目创建成功")
    except KNOWN_CREATION_ERRORS as e:
        return ResponseUtil.error("题目创建失败", e)


@MCP.tool()
def create_blank_answer_items(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    count: Annotated[int, Field(description=desc.BLANK_ANSWER_COUNT_DESC, gt=0)],
) -> dict:
    """创建空白答案项"""
    try:
        return ResponseUtil.success(
            create_blank_answer_items_data(paper_id, question_id, count),
            "空白答案项创建成功",
        )
    except KNOWN_CREATION_ERRORS as e:
        return ResponseUtil.error("空白答案项创建失败", e)


@MCP.tool()
def create_answer_item(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
) -> dict:
    """创建答案项"""
    try:
        return ResponseUtil.success(
            create_answer_item_data(paper_id, question_id),
            "答案项创建成功",
        )
    except KNOWN_CREATION_ERRORS as e:
        return ResponseUtil.error("答案项创建失败", e)


def _create_choice_question(
    *,
    paper_id: str,
    question_type: QuestionType,
    question: ChoiceQuestion | MultipleChoiceQuestion,
    need_detail: bool,
    need_parse: bool,
) -> dict:
    is_single = question_type == QuestionType.SINGLE_CHOICE
    question_id = None
    try:
        parse_mode = resolve_parse_mode(need_parse)
        question_data = create_question_data(
            paper_id, question_type, question.score, question.insert_question_id
        )
        question_id = question_data["id"]
        answer_items = question_data["options"]

        question_data = update_question_base(
            question_id=question_id,
            title=question.title,
            title_raw=question.title_raw,
            description=question.description,
            required=question.required,
            parse_mode=parse_mode,
        )
        # 确保选项数量足够
        for _ in range(len(answer_items), len(question.options)):
            raw = create_answer_item_data(paper_id, question_id)
            answer_items.append({"answer_item_id": raw["id"]})
        # 设置每个选项的内容和答案标记
        last_options_data = []
        for item, option in zip(answer_items, question.options, strict=False):
            r = update_question_options(
                question_id=question_id,
                answer_item_id=item["answer_item_id"],
                option_text=option.text,
                option_text_raw=option.text_raw,
                is_answer=option.answer,
                parse_mode=parse_mode,
            )
            if not r.get("success"):
                raise ValueError(r.get("message") or "选项更新失败")
            last_options_data = r["data"]
        question_data["options"] = last_options_data
        msg = "单选题创建成功" if is_single else "多选题创建成功"
        return ResponseUtil.success(question_data if need_detail else None, msg)
    except Exception as e:
        if question_id:
            delete_questions(paper_id, [question_id])
        msg = "创建单选题时发生异常" if is_single else "创建多选题时发生异常"
        return ResponseUtil.error(msg, e)
