"""题目创建 MCP 工具"""

from __future__ import annotations

from typing import Annotated, Any, Optional, Union

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
    extract_response_message,
    post_json,
)
from ...utils.response import ResponseUtil
from ...utils.rich_text import render_rich_text_output
from .delete import delete_questions
from .update import update_short_answer_answer, update_true_false_answer

KNOWN_CREATION_ERRORS = (APIRequestError, ValueError)


def resolve_parse_mode(need_parse: bool) -> str:
    return "plain" if need_parse else "raw"


def extract_plain_title(title: Optional[str], title_raw: Optional[dict[str, Any]]) -> str:
    return (
        render_rich_text_output(title_raw if title_raw is not None else title, "plain")
        or ""
    )


def create_question_data(
    paper_id: str,
    question_type: QuestionType,
    score: int,
    insert_question_id: Optional[str] = None,
) -> dict[str, Any]:
    payload = {"paper_id": str(paper_id), "type": question_type.value, "score": score}
    if insert_question_id is not None and len(insert_question_id) == 19:
        payload["insert_question_id"] = str(insert_question_id)
    response = post_json(f"{MAIN_URL}/survey/addQuestion", payload=payload)
    return parse_question(expect_success(response), parse_mode="raw")


def create_blank_answer_items_data(
    paper_id: str,
    question_id: str,
    count: int,
) -> list[dict[str, Any]]:
    response = post_json(
        f"{MAIN_URL}/survey/createBlankAnswerItems",
        payload={
            "paper_id": str(paper_id),
            "question_id": str(question_id),
            "count": count,
        },
    )
    return expect_success(response)["answer_items"]


def create_answer_item_data(paper_id: str, question_id: str) -> dict[str, Any]:
    response = post_json(
        f"{MAIN_URL}/survey/createAnswerItem",
        payload={"paper_id": str(paper_id), "question_id": str(question_id)},
    )
    return expect_success(response)


def run_question_creation(
    *,
    paper_id: str,
    operation,
) -> dict[str, Any]:
    context: dict[str, Any] = {"question_id": None}
    try:
        return operation(context)
    except Exception:
        # Roll back the partially-created question even on unexpected internal errors.
        question_id = context.get("question_id")
        if question_id:
            delete_questions(paper_id, [question_id])
        raise


def _unwrap_tool_result(result: dict[str, Any]) -> Any:
    if not result.get("success"):
        raise ValueError(extract_response_message(result))
    return result["data"]


def update_question_base(
    *,
    question_id: str,
    title: Optional[str],
    title_raw: Optional[dict[str, Any]],
    description: str,
    required: bool,
    parse_mode: str,
    **kwargs,
) -> dict[str, Any]:
    from .update import update_question

    result = update_question(
        question_id=question_id,
        title=title,
        title_raw=title_raw,
        description=description,
        required=required,
        parse_mode=parse_mode,
        **kwargs,
    )
    return _unwrap_tool_result(result)


def initialize_question(
    context: dict[str, Any],
    *,
    paper_id: str,
    question_type: QuestionType,
    score: int,
    insert_question_id: Optional[str],
    title: Optional[str],
    title_raw: Optional[dict[str, Any]],
    description: str,
    required: bool,
    parse_mode: str,
    **kwargs,
) -> tuple[str, list[dict[str, Any]], Optional[str], dict[str, Any]]:
    question_data = create_question_data(
        paper_id=paper_id,
        question_type=question_type,
        score=score,
        insert_question_id=insert_question_id,
    )
    question_id = question_data["id"]
    context["question_id"] = question_id
    updated_question = update_question_base(
        question_id=question_id,
        title=title,
        title_raw=title_raw,
        description=description,
        required=required,
        parse_mode=parse_mode,
        **kwargs,
    )
    program_setting_id = None
    if question_type == QuestionType.CODE:
        program_setting_id = question_data["program_setting"]["id"]
    return question_id, question_data["options"], program_setting_id, updated_question


def ensure_answer_items(
    paper_id: str,
    question_id: str,
    answer_items: list[dict[str, Any]],
    expected_count: int,
) -> list[dict[str, Any]]:
    items = list(answer_items)
    for _ in range(len(items), expected_count):
        items.append(create_answer_item_data(paper_id, question_id))
    return items


def apply_choice_options(
    *,
    question_id: str,
    answer_items: list[dict[str, Any]],
    options: list[Any],
    parse_mode: str,
) -> list[dict[str, Any]]:
    from .update import update_question_options

    last_result: list[dict[str, Any]] = []
    for item, option in zip(answer_items, options):
        last_result = _unwrap_tool_result(
            update_question_options(
                question_id=question_id,
                answer_item_id=item["id"],
                option_text=option.text,
                option_text_raw=option.text_raw,
                is_answer=option.answer,
                parse_mode=parse_mode,
            )
        )
    return last_result


def apply_fill_blank_answers(
    question_id: str,
    answer_items: list[dict[str, Any]],
    answers: list[Any],
) -> list[dict[str, Any]]:
    from .update import update_fill_blank_answer

    last_result: list[dict[str, Any]] = []
    for item, answer in zip(answer_items, answers):
        last_result = _unwrap_tool_result(
            update_fill_blank_answer(question_id, item["id"], answer.text)
        )
    return last_result


def validate_fill_blank_question(
    title: Optional[str], title_raw: Optional[dict[str, Any]], answers_count: int
) -> str:
    plain_title = extract_plain_title(title, title_raw)
    if "____" not in plain_title:
        raise ValueError("填空题标题必须包含空白标记'____'")
    blank_count = plain_title.count("____")
    if blank_count != answers_count:
        raise ValueError(
            f"空白标记数量({blank_count})与答案数量({answers_count})不匹配"
        )
    return plain_title


def _wrap_creation(
    *,
    paper_id: str,
    success_message: str,
    error_message: str,
    need_detail: bool,
    operation,
) -> dict:
    try:
        question_data = run_question_creation(paper_id=paper_id, operation=operation)
        return ResponseUtil.success(
            question_data if need_detail else None, success_message
        )
    except KNOWN_CREATION_ERRORS as e:
        return ResponseUtil.error(error_message, e)


def _initialize_from_question(
    context: dict[str, Any],
    *,
    paper_id: str,
    question_type: QuestionType,
    question: (
        ChoiceQuestion
        | MultipleChoiceQuestion
        | TrueFalseQuestion
        | FillBlankQuestion
        | AttachmentQuestion
        | ShortAnswerQuestion
        | CodeQuestion
    ),
    parse_mode: str,
    **kwargs,
) -> tuple[str, list[dict[str, Any]], Optional[str], dict[str, Any]]:
    return initialize_question(
        context,
        paper_id=paper_id,
        question_type=question_type,
        score=question.score,
        insert_question_id=question.insert_question_id,
        title=question.title,
        title_raw=question.title_raw,
        description=question.description,
        required=question.required,
        parse_mode=parse_mode,
        **kwargs,
    )


def _create_initialized_question(
    *,
    paper_id: str,
    question_type: QuestionType,
    question: (
        ChoiceQuestion
        | MultipleChoiceQuestion
        | TrueFalseQuestion
        | FillBlankQuestion
        | AttachmentQuestion
        | ShortAnswerQuestion
        | CodeQuestion
    ),
    need_detail: bool,
    need_parse: bool,
    success_message: str,
    error_message: str,
    finalize,
    **kwargs,
) -> dict:
    parse_mode = resolve_parse_mode(need_parse)

    def operation(context: dict[str, Any]) -> dict[str, Any]:
        question_id, answer_items, program_setting_id, question_data = (
            _initialize_from_question(
                context,
                paper_id=paper_id,
                question_type=question_type,
                question=question,
                parse_mode=parse_mode,
                **kwargs,
            )
        )
        return finalize(
            question_id,
            answer_items,
            program_setting_id,
            question_data,
            parse_mode,
        )

    return _wrap_creation(
        paper_id=paper_id,
        success_message=success_message,
        error_message=error_message,
        need_detail=need_detail,
        operation=operation,
    )


def _validate_office_import_question(question: Any) -> None:
    if question.type == QuestionType.FILL_BLANK:
        validate_fill_blank_question(question.title, None, len(question.standard_answers))


def _build_office_import_question(question: Any) -> dict[str, Any]:
    data = question.model_dump()
    answer_items = {
        QuestionType.SHORT_ANSWER: [{"seqno": "A"}],
        QuestionType.TRUE_FALSE: [
            {"seqno": "A", "context": "true"},
            {"seqno": "B", "context": ""},
        ],
        QuestionType.ATTACHMENT: [{"seqno": "A"}],
        QuestionType.CODE: [],
    }.get(question.type)
    if answer_items is not None:
        data["answer_items"] = answer_items
    return data


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
    question: Annotated[MultipleChoiceQuestion, Field(description=desc.MULTIPLE_CHOICE_QUESTION_DESC)],
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
    parse_mode = resolve_parse_mode(need_parse)

    def operation(context: dict[str, Any]) -> dict[str, Any]:
        plain_title = validate_fill_blank_question(
            question.title, question.title_raw, len(question.options)
        )
        question_id, _, _, question_data = _initialize_from_question(
            context,
            paper_id=paper_id,
            question_type=QuestionType.FILL_BLANK,
            question=question,
            is_split_answer=question.is_split_answer,
            automatic_stat=question.automatic_stat,
            automatic_type=question.automatic_type,
            parse_mode=parse_mode,
        )
        answer_items = create_blank_answer_items_data(
            paper_id, question_id, plain_title.count("____")
        )
        question_data["options"] = apply_fill_blank_answers(
            question_id, answer_items, question.options
        )
        return question_data

    return _wrap_creation(
        paper_id=paper_id,
        success_message="填空题创建成功",
        error_message="创建填空题时发生异常",
        need_detail=need_detail,
        operation=operation,
    )


@MCP.tool()
def create_true_false_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[TrueFalseQuestion, Field(description=desc.TRUE_FALSE_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建判断题"""
    def finalize(question_id, answer_items, _program_setting_id, question_data, _parse_mode):
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
        question_data["options"] = _unwrap_tool_result(
            update_true_false_answer(question_id, answer_id)
        )
        return question_data

    return _create_initialized_question(
        paper_id=paper_id,
        question_type=QuestionType.TRUE_FALSE,
        question=question,
        need_detail=need_detail,
        need_parse=need_parse,
        success_message="判断题创建成功",
        error_message="创建判断题时发生异常",
        finalize=finalize,
    )


@MCP.tool()
def create_short_answer_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[ShortAnswerQuestion, Field(description=desc.SHORT_ANSWER_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建简答题"""
    def finalize(question_id, answer_items, _program_setting_id, question_data, parse_mode):
        answer_result = update_short_answer_answer(
            question_id=question_id,
            answer_item_id=answer_items[0]["id"],
            answer=question.answer,
            answer_raw=question.answer_raw,
            parse_mode=parse_mode,
        )
        question_data["options"] = _unwrap_tool_result(answer_result)
        return question_data

    return _create_initialized_question(
        paper_id=paper_id,
        question_type=QuestionType.SHORT_ANSWER,
        question=question,
        need_detail=need_detail,
        need_parse=need_parse,
        success_message="简答题创建成功",
        error_message="创建简答题时发生异常",
        finalize=finalize,
    )


@MCP.tool()
def create_attachment_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[AttachmentQuestion, Field(description=desc.ATTACHMENT_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建附件题"""
    def finalize(
        _question_id, _answer_items, _program_setting_id, question_data, _parse_mode
    ):
        return question_data

    return _create_initialized_question(
        paper_id=paper_id,
        question_type=QuestionType.ATTACHMENT,
        question=question,
        need_detail=need_detail,
        need_parse=need_parse,
        success_message="附件题创建成功",
        error_message="创建附件题时发生异常",
        finalize=finalize,
    )


@MCP.tool()
def create_code_question(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question: Annotated[CodeQuestion, Field(description=desc.CODE_QUESTION_DESC)],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """创建编程题"""
    def finalize(question_id, answer_items, program_setting_id, _question_data, parse_mode):
        if program_setting_id is None:
            raise ValueError("编程题创建失败, 未分配编程设置ID")
        if not answer_items:
            raise ValueError("编程题创建失败, 未分配答案项ID")
        question.program_setting.id = program_setting_id
        question.program_setting.answer_item_id = answer_items[0]["id"]
        return update_question_base(
            question_id=question_id,
            title=question.title,
            title_raw=question.title_raw,
            description=question.description,
            required=question.required,
            program_setting=question.program_setting,
            parse_mode=parse_mode,
        )

    return _create_initialized_question(
        paper_id=paper_id,
        question_type=QuestionType.CODE,
        question=question,
        need_detail=need_detail,
        need_parse=need_parse,
        success_message="编程题创建并配置编程设置和测试用例成功",
        error_message="创建编程题时发生异常",
        finalize=finalize,
    )


@MCP.tool()
def batch_create_questions(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    questions: Annotated[
        list[
            Annotated[
                Union[
                    ChoiceQuestion,
                    MultipleChoiceQuestion,
                    TrueFalseQuestion,
                    FillBlankQuestion,
                    AttachmentQuestion,
                    ShortAnswerQuestion,
                    CodeQuestion,
                ],
                Field(discriminator="type"),
            ]
        ],
        Field(description=desc.QUESTION_LIST_DESC, min_length=1),
    ],
    need_detail: Annotated[bool, Field(description=desc.NEED_DETAIL_DESC)] = False,
    need_parse: Annotated[bool, Field(description=desc.RETURN_PARSE_DESC)] = False,
) -> dict:
    """批量创建题目(非官方接口),不稳定但功能更强大[支持单选、多选、填空、判断、附件、简答题、编程题]"""
    success_count, failed_count = 0, 0
    results = {"details": [], "questions": []}

    question_handlers = {
        QuestionType.SINGLE_CHOICE: create_single_choice_question,
        QuestionType.MULTIPLE_CHOICE: create_multiple_choice_question,
        QuestionType.TRUE_FALSE: create_true_false_question,
        QuestionType.FILL_BLANK: create_fill_blank_question,
        QuestionType.SHORT_ANSWER: create_short_answer_question,
        QuestionType.ATTACHMENT: create_attachment_question,
        QuestionType.CODE: create_code_question,
    }

    for index, question in enumerate(questions, 1):
        try:
            handler = question_handlers.get(question.type)
            if handler is None:
                failed_count += 1
                results["details"].append(f"第{index}题: 创建失败 - 不支持的题目类型")
                continue

            result = handler(
                paper_id, question, need_detail=need_detail, need_parse=need_parse
            )
            question_title = extract_plain_title(
                getattr(question, "title", None),
                getattr(question, "title_raw", None),
            )
            if result["success"]:
                success_count += 1
                results["questions"].append(result["data"])
                results["details"].append(
                    f"[第{index}题][创建成功][{QuestionType.get(question.type)}][{question_title}]"
                )
            else:
                failed_count += 1
                results["details"].append(
                    f"[第{index}题][创建失败][{QuestionType.get(question.type)}][{result['message']}]"
                )
        except KNOWN_CREATION_ERRORS as e:
            failed_count += 1
            results["details"].append(
                f"[第{index}题][创建异常][{QuestionType.get(question.type)}][{str(e)}]"
            )

    if not need_detail:
        results.pop("questions", None)
    summary = f"[批量创建完成][成功{success_count}题][失败{failed_count}题][总计{len(questions)}题]"
    return ResponseUtil.success(results, summary)


@MCP.tool()
def office_create_questions(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    questions: Annotated[
        list[
            Annotated[
                Union[
                    SingleChoiceQuestionData,
                    MultipleChoiceQuestionData,
                    FillBlankQuestionData,
                    TrueFalseQuestionData,
                    ShortAnswerQuestionData,
                    AttachmentQuestionData,
                    CodeQuestionData,
                ],
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
            try:
                _validate_office_import_question(question)
            except ValueError as e:
                return ResponseUtil.error(f"第{index}题格式错误", e)

        questions_data = [_build_office_import_question(question) for question in questions]

        response = post_json(
            f"{MAIN_URL}/survey/question/import",
            payload={"paper_id": str(paper_id), "questions": questions_data},
        )
        imported_questions = expect_success(response)
        validation_errors = validate_office_import_results(
            questions, imported_questions
        )
        if validation_errors:
            return ResponseUtil.error(
                "批量导入完成但结果校验失败: " + "; ".join(validation_errors)
            )
        if not need_detail:
            return ResponseUtil.success(
                None,
                f"[批量导入完成][共{len(imported_questions)}题]",
            )
        return ResponseUtil.success(
            [
                parse_question(question, parse_mode=resolve_parse_mode(need_parse))
                for question in imported_questions
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
    insert_question_id: Annotated[
        Optional[str], Field(description=desc.INSERT_AFTER_DESC)
    ] = None,
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
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("题目创建失败", e)


@MCP.tool()
def create_blank_answer_items(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
    count: Annotated[int, Field(description=desc.BLANK_ANSWER_COUNT_DESC, gt=0)],
) -> dict:
    """创建空白答案项"""
    try:
        answer_items = create_blank_answer_items_data(
            paper_id=paper_id,
            question_id=question_id,
            count=count,
        )
        return ResponseUtil.success(answer_items, "空白答案项创建成功")
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("空白答案项创建失败", e)


@MCP.tool()
def create_answer_item(
    paper_id: Annotated[str, Field(description=desc.PAPER_ID_DESC)],
    question_id: Annotated[str, Field(description=desc.QUESTION_ID_DESC)],
) -> dict:
    """创建答案项"""
    try:
        answer_item = create_answer_item_data(paper_id=paper_id, question_id=question_id)
        return ResponseUtil.success(answer_item, "答案项创建成功")
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("答案项创建失败", e)


def _create_choice_question(
    *,
    paper_id: str,
    question_type: QuestionType,
    question: ChoiceQuestion | MultipleChoiceQuestion,
    need_detail: bool,
    need_parse: bool,
) -> dict:
    success_message = (
        "单选题创建成功"
        if question_type == QuestionType.SINGLE_CHOICE
        else "多选题创建成功"
    )
    error_message = (
        "创建单选题时发生异常"
        if question_type == QuestionType.SINGLE_CHOICE
        else "创建多选题时发生异常"
    )

    def finalize(question_id, answer_items, _program_setting_id, question_data, parse_mode):
        ensured_items = ensure_answer_items(
            paper_id, question_id, answer_items, len(question.options)
        )
        question_data["options"] = apply_choice_options(
            question_id=question_id,
            answer_items=ensured_items,
            options=question.options,
            parse_mode=parse_mode,
        )
        return question_data

    return _create_initialized_question(
        paper_id=paper_id,
        question_type=question_type,
        question=question,
        need_detail=need_detail,
        need_parse=need_parse,
        success_message=success_message,
        error_message=error_message,
        finalize=finalize,
    )
