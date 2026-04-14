from __future__ import annotations

from enum import IntEnum, StrEnum


class QuestionType(IntEnum):
    """题目类型枚举"""

    SINGLE_CHOICE = 1
    MULTIPLE_CHOICE = 2
    FILL_BLANK = 4
    TRUE_FALSE = 5
    SHORT_ANSWER = 6
    ATTACHMENT = 7
    CODE = 10

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "单选题",
            2: "多选题",
            4: "填空题",
            5: "判断题",
            6: "简答题",
            7: "附件题",
            10: "代码题",
        }.get(value, default)


class AutoScoreType(IntEnum):
    """自动评分类型枚举"""

    EXACT_ORDERED = 1
    PARTIAL_ORDERED = 2
    EXACT_UNORDERED = 11
    PARTIAL_UNORDERED = 12

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "精确匹配+有序",
            2: "部分匹配+有序",
            11: "精确匹配+无序",
            12: "部分匹配+无序",
        }.get(value, default)


class QuestionScoreType(IntEnum):
    """题目评分类型枚举"""

    STRICT = 1
    LENIENT = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "严格计分",
            2: "宽分模式",
        }.get(value, default)


class RequiredType(IntEnum):
    """是否必答枚举"""

    NO = 1
    YES = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "否",
            2: "是",
        }.get(value, default)


class AutoStatType(IntEnum):
    """自动评分设置枚举"""

    OFF = 1
    ON = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "关闭",
            2: "开启",
        }.get(value, default)


class RandomizationType(IntEnum):
    """随机化类型枚举"""

    DISABLED = 1
    ENABLED = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "关闭",
            2: "开启",
        }.get(value, default)


class AnswerChecked(IntEnum):
    """答案正确性枚举"""

    WRONG = 1
    CORRECT = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "错误",
            2: "正确",
        }.get(value, default)


class AllowTrialRun(IntEnum):
    """是否允许试运行枚举"""

    NO = 1
    YES = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "否",
            2: "是",
        }.get(value, default)


class ProgrammingLanguage(StrEnum):
    """编程语言枚举"""

    C = "c"
    CPP = "c++"
    JAVA = "java"
    CSHARP = "c#"
    R = "r"
    SQL = "sql"
    JAVASCRIPT = "javascript"
    PYTHON3 = "python3"
    MATLAB = "matlab"
    ADA = "ada"
    FORTRAN = "fortran"
    SCRATCH = "scratch"
    PHP = "php"
    VISUAL_BASIC = "visual_basic"
    ASSEMBLY = "assembly"
    GO = "go"
    RUST = "rust"
    KOTLIN = "kotlin"
    PERL = "perl"
    OBJECT_PASCAL = "object_pascal"
