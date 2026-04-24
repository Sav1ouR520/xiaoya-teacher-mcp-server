from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field, model_validator

from .. import field_descriptions as desc
from .enums import (
    AllowTrialRun,
    AutoScoreType,
    AutoStatType,
    ProgrammingLanguage,
    QuestionType,
    RequiredType,
)

RawRichText = dict[str, Any]


def _validate_text_or_raw_input(text: str | None, raw: RawRichText | None, field_name: str) -> None:
    if text is None and raw is None:
        raise ValueError(f"{field_name} 和 {field_name}_raw 至少提供一个")
    if text is not None and raw is not None:
        raise ValueError(f"{field_name} 和 {field_name}_raw 不能同时提供")


class RichTextModel(BaseModel):
    _rich_fields: ClassVar[tuple[tuple[str, str], ...]] = ()

    @model_validator(mode="after")
    def validate_rich_fields(self):
        for text_field, raw_field in self._rich_fields:
            _validate_text_or_raw_input(
                getattr(self, text_field), getattr(self, raw_field), text_field
            )
        return self


class QuestionOption(RichTextModel):
    """题目选项(单选题/多选题使用)"""

    _rich_fields = (("text", "text_raw"),)

    text: str | None = Field(description=desc.OPTION_TEXT_DESC, default=None)
    text_raw: RawRichText | None = Field(description=desc.OPTION_RAW_TEXT_DESC, default=None)
    answer: bool = Field(description=desc.OPTION_ANSWER_DESC)


class FillBlankAnswer(BaseModel):
    """填空题答案"""

    text: str = Field(description=desc.ANSWER_TEXT_DESC)


class StandardAnswer(BaseModel):
    """标准答案"""

    seqno: str = Field(description=desc.STANDARD_SEQ_DESC, min_length=1)
    standard_answer: str = Field(description=desc.STANDARD_CONTENT_DESC, min_length=1)


class AnswerItem(BaseModel):
    """题目选项项"""

    seqno: str = Field(description=desc.STANDARD_SEQ_DESC, min_length=1)
    context: str | None = Field(description=desc.ANSWER_ITEM_CONTEXT_DESC, default=None)


class OfficeQuestionBase(BaseModel):
    title: str = Field(description=desc.QUESTION_TITLE_DESC, min_length=1)
    description: str = Field(description=desc.ANSWER_EXPLANATION_DESC, min_length=1)
    score: int = Field(description=desc.QUESTION_SCORE_DESC, gt=0, default=2)


class OfficeStandardAnswerQuestionBase(OfficeQuestionBase):
    standard_answers: list[StandardAnswer] = Field(
        description=desc.STANDARD_ANSWERS_LIST_DESC, min_length=1
    )


class OfficeChoiceQuestionBase(OfficeStandardAnswerQuestionBase):
    answer_items: list[AnswerItem] = Field(description=desc.ANSWER_ITEMS_LIST_DESC, min_length=1)


class SingleChoiceQuestionData(OfficeChoiceQuestionBase):
    """官方批量导入单选题数据结构"""

    type: Literal[QuestionType.SINGLE_CHOICE] = QuestionType.SINGLE_CHOICE


class MultipleChoiceQuestionData(OfficeChoiceQuestionBase):
    """官方批量导入多选题数据结构"""

    type: Literal[QuestionType.MULTIPLE_CHOICE] = QuestionType.MULTIPLE_CHOICE


class FillBlankQuestionData(OfficeStandardAnswerQuestionBase):
    """官方批量导入填空题数据结构"""

    type: Literal[QuestionType.FILL_BLANK] = QuestionType.FILL_BLANK
    title: str = Field(description=desc.FILL_BLANK_TITLE_DESC, min_length=1)
    answer_items: list[AnswerItem] = Field(description="填空项列表", min_length=1)
    automatic_type: AutoScoreType = Field(description=desc.AUTO_SCORE_DESC)


class TrueFalseQuestionData(OfficeStandardAnswerQuestionBase):
    """官方批量导入判断题数据结构"""

    type: Literal[QuestionType.TRUE_FALSE] = QuestionType.TRUE_FALSE


class ShortAnswerQuestionData(OfficeStandardAnswerQuestionBase):
    """官方批量导入简答题数据结构"""

    type: Literal[QuestionType.SHORT_ANSWER] = QuestionType.SHORT_ANSWER
    standard_answers: list[StandardAnswer] = Field(
        description=desc.STANDARD_ANSWERS_LIST_DESC, min_length=1, max_length=1
    )


class AttachmentQuestionData(OfficeQuestionBase):
    """官方批量导入附件题数据结构"""

    type: Literal[QuestionType.ATTACHMENT] = QuestionType.ATTACHMENT


class OfficeCodeSetting(BaseModel):
    class Case_Type(BaseModel):
        input: str = Field(description=desc.TEST_CASE_INPUT_DESC, default="")
        output: str = Field(description=desc.TEST_CASE_OUTPUT_DESC, default="")

    answer_language: ProgrammingLanguage = Field(
        description=desc.ANSWER_LANGUAGE_DESC, default=ProgrammingLanguage.C
    )
    cases: list[Case_Type] = Field(description=desc.TEST_CASE_LIST_DESC, default_factory=list)
    max_memory: int = Field(description=desc.PROGRAM_MAX_MEMORY_DESC, default=5000, gt=0)
    max_time: int = Field(description=desc.PROGRAM_MAX_TIME_DESC, default=1000, gt=0)
    debug: AllowTrialRun = Field(description=desc.DEBUG_DESC, ge=1, le=2, default=2)
    debug_count: int = Field(description=desc.DEBUG_COUNT_DESC, ge=0, le=9999, default=9999)
    example_code: str | None = Field(description=desc.EXAMPLE_CODE_DESC, default=None)
    example_language: ProgrammingLanguage | None = Field(default=None)
    language: ProgrammingLanguage = Field(default=ProgrammingLanguage.C)
    runcase: AllowTrialRun = Field(description=desc.RUNCASE_DESC, ge=1, le=2, default=2)
    runcase_count: int = Field(description=desc.RUNCASE_COUNT_DESC, ge=0, le=100, default=100)


class CodeQuestionData(OfficeQuestionBase):
    """官方批量导入代码题数据结构"""

    type: Literal[QuestionType.CODE] = QuestionType.CODE
    program_setting: OfficeCodeSetting = Field(description=desc.PROGRAM_SETTING_DESC)


class QuestionBase(RichTextModel):
    _rich_fields = (("title", "title_raw"),)

    title: str | None = Field(description=desc.QUESTION_RICH_TEXT_DESC, default=None)
    title_raw: RawRichText | None = Field(
        description=desc.QUESTION_RAW_RICH_TEXT_DESC, default=None
    )
    description: str = Field(description=desc.ANSWER_EXPLANATION_DESC, min_length=1)
    score: int = Field(description=desc.QUESTION_SCORE_DESC, gt=0, default=2)
    required: RequiredType | None = Field(description=desc.REQUIRED_DESC, default=RequiredType.YES)
    insert_question_id: str | None = Field(description=desc.INSERT_AFTER_DESC, default=None)


class ChoiceQuestionBase(QuestionBase):
    options: list[QuestionOption] = Field(description=desc.QUESTION_OPTIONS_DESC, min_length=4)


class ChoiceQuestion(ChoiceQuestionBase):
    """单选题"""

    type: Literal[QuestionType.SINGLE_CHOICE] = QuestionType.SINGLE_CHOICE


class MultipleChoiceQuestion(ChoiceQuestionBase):
    """多选题"""

    type: Literal[QuestionType.MULTIPLE_CHOICE] = QuestionType.MULTIPLE_CHOICE


class TrueFalseQuestion(QuestionBase):
    """判断题"""

    type: Literal[QuestionType.TRUE_FALSE] = QuestionType.TRUE_FALSE
    answer: bool = Field(description=desc.TRUE_FALSE_ANSWER_DESC)


class FillBlankQuestion(QuestionBase):
    """填空题"""

    type: Literal[QuestionType.FILL_BLANK] = QuestionType.FILL_BLANK
    title: str | None = Field(description=desc.FILL_BLANK_TITLE_DESC, default=None)
    options: list[FillBlankAnswer] = Field(description=desc.FILL_BLANK_ANSWERS_DESC)
    is_split_answer: bool | None = Field(description=desc.SPLIT_ANSWER_DESC, default=None)
    automatic_stat: AutoStatType | None = Field(description=desc.AUTO_STAT_DESC, default=None)
    automatic_type: AutoScoreType = Field(description=desc.AUTO_SCORE_DESC)


class AttachmentQuestion(QuestionBase):
    """附件题"""

    type: Literal[QuestionType.ATTACHMENT] = QuestionType.ATTACHMENT


class ShortAnswerQuestion(QuestionBase):
    """简答题"""

    _rich_fields = QuestionBase._rich_fields + (("answer", "answer_raw"),)

    type: Literal[QuestionType.SHORT_ANSWER] = QuestionType.SHORT_ANSWER
    answer: str | None = Field(description=desc.REFERENCE_RICH_TEXT_DESC, default=None)
    answer_raw: RawRichText | None = Field(
        description=desc.REFERENCE_RAW_RICH_TEXT_DESC, default=None
    )


class ProgramSettingBase(BaseModel):
    id: str | None = Field(description=desc.PROGRAM_SETTING_ID_DESC, default=None)
    answer_item_id: str | None = Field(
        description=desc.PROGRAM_SETTING_ANSWER_ITEM_DESC, default=None
    )


_PROGRAM_FIELDS = dict(
    max_memory=desc.PROGRAM_MAX_MEMORY_DESC,
    max_time=desc.PROGRAM_MAX_TIME_DESC,
    debug_count=desc.DEBUG_COUNT_DESC,
    runcase_count=desc.RUNCASE_COUNT_DESC,
    code_answer=desc.CODE_ANSWER_DESC,
    in_cases=desc.IN_CASES_DESC,
)


class ProgramSetting(ProgramSettingBase):
    """编程题配置（更新用，所有字段可选，传 None 则保持原值）"""

    max_memory: int | None = Field(description=_PROGRAM_FIELDS["max_memory"], gt=0, default=None)
    max_time: int | None = Field(description=_PROGRAM_FIELDS["max_time"], gt=0, default=None)
    debug: AllowTrialRun | None = Field(description=desc.DEBUG_DESC, ge=1, le=2, default=None)
    debug_count: int | None = Field(
        description=_PROGRAM_FIELDS["debug_count"], ge=0, le=9999, default=None
    )
    runcase: AllowTrialRun | None = Field(description=desc.RUNCASE_DESC, ge=1, le=2, default=None)
    runcase_count: int | None = Field(
        description=desc.RUNCASE_COUNT_DESC, ge=0, le=100, default=None
    )
    language: list[ProgrammingLanguage] | None = Field(
        description=(
            "允许学生提交的语言列表（至少 1 种）。常用组合：['python3'] 只收 Python；"
            "['c', 'c++'] 只收 C 系列。"
        ),
        default_factory=list,
        min_length=1,
    )
    answer_language: ProgrammingLanguage | None = Field(
        description=desc.ANSWER_LANGUAGE_DESC, default=None
    )
    code_answer: str | None = Field(description=_PROGRAM_FIELDS["code_answer"], default=None)
    in_cases: list[dict[str, str]] | None = Field(
        description=_PROGRAM_FIELDS["in_cases"], default_factory=list, min_length=1
    )


class ProgramSettingAllNeed(ProgramSettingBase):
    """编程题配置（创建用，带默认值）。

    默认值来自官方平台推荐：
      - max_memory=5000 KB（<5000 时 Python 常规 import 可能内存超限）
      - max_time=1000 ms
      - debug=YES + debug_count=9999 （学生自测不限次数）
      - runcase=YES + runcase_count=100 （学生跑全部测试用例不限次数）
    除非老师明确要求限制，否则使用默认值即可。
    """

    max_memory: int = Field(description=_PROGRAM_FIELDS["max_memory"], gt=0, default=5000)
    max_time: int = Field(description=_PROGRAM_FIELDS["max_time"], gt=0, default=1000)
    debug: AllowTrialRun = Field(description=desc.DEBUG_DESC, ge=1, le=2, default=2)
    debug_count: int = Field(
        description=_PROGRAM_FIELDS["debug_count"], ge=0, le=9999, default=9999
    )
    runcase: AllowTrialRun = Field(description=desc.RUNCASE_DESC, ge=1, le=2, default=2)
    runcase_count: int = Field(description=desc.RUNCASE_COUNT_DESC, ge=0, le=100, default=100)
    language: list[ProgrammingLanguage] = Field(
        description=(
            "允许学生提交的语言列表（至少 1 种）。常用组合：['python3'] 只收 Python；"
            "['c', 'c++'] 只收 C 系列；多语言题可 ['python3', 'java', 'c++']。"
        ),
        default_factory=list,
        min_length=1,
    )
    answer_language: ProgrammingLanguage | None = Field(
        description=desc.ANSWER_LANGUAGE_DESC, default=None
    )
    code_answer: str | None = Field(description=_PROGRAM_FIELDS["code_answer"], default=None)
    in_cases: list[dict[str, str]] = Field(
        description=_PROGRAM_FIELDS["in_cases"], default_factory=list, min_length=1
    )


class CodeQuestion(QuestionBase):
    """编程题"""

    type: Literal[QuestionType.CODE] = QuestionType.CODE
    description: str = Field(
        description=desc.ANSWER_EXPLANATION_DESC,
        min_length=1,
    )
    program_setting: ProgramSettingAllNeed = Field(description=desc.PROGRAM_SETTING_DESC)
