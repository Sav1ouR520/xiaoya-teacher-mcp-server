# 类型枚举定义
from enum import IntEnum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class LineTitle(BaseModel):
    class InlineStyleRange(BaseModel):
        """内联样式范围"""

        offset: int = Field(description="样式开始位置的偏移量", default=0)
        length: int = Field(description="样式的长度")
        style: Literal["BOLD", "ITALIC", "UNDERLINE", "CODE", "lineThrough"] = Field(
            description="样式类型"
        )

    """编程题目描述的单行内容"""
    text: str = Field(description="行内容")
    line_type: Literal[
        "unordered-list-item", "ordered-list-item", "unstyled", "code-block"
    ] = Field(description="行类型", default="unstyled")
    inlineStyleRanges: List[InlineStyleRange] = Field(
        default_factory=list, description="内联样式范围数组"
    )


class ResourceType(IntEnum):
    """资源类型枚举"""

    FOLDER = 1  # 文件夹
    NOTE = 2  # 笔记
    MINDMAP = 3  # 思维导图
    FILE = 6  # 文件
    ASSIGNMENT = 7  # 作业
    TEACHING_DESIGN = 11  # 教学设计

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取资源类型名称"""
        name_map = {
            1: "文件夹",
            2: "笔记",
            3: "思维导图",
            6: "文件",
            7: "作业",
            11: "教学设计",
        }
        return name_map.get(value, default)


class QuestionType(IntEnum):
    """题目类型枚举"""

    SINGLE_CHOICE = 1  # 单选题
    MULTIPLE_CHOICE = 2  # 多选题
    FILL_BLANK = 4  # 填空题
    TRUE_FALSE = 5  # 判断题
    SHORT_ANSWER = 6  # 简答题
    CODE = 10  # 代码题

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取题目类型名称"""
        name_map = {
            1: "单选题",
            2: "多选题",
            4: "填空题",
            5: "判断题",
            6: "简答题",
            10: "代码题",
        }
        return name_map.get(value, default)


class AttendanceStatus(IntEnum):
    """签到状态枚举"""

    ATTENDANCE = 1  # 签到
    ABSENT = 2  # 旷课
    LATE = 3  # 迟到
    EARLY_LEAVE = 4  # 早退
    PERSONAL_LEAVE = 5  # 事假
    SICK_LEAVE = 6  # 病假
    OFFICIAL_LEAVE = 7  # 公假
    OTHER = 8  # 其他

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取状态名称"""
        name_map = {
            1: "签到",
            2: "旷课",
            3: "迟到",
            4: "早退",
            5: "事假",
            6: "病假",
            7: "公假",
            8: "其他",
        }
        return name_map.get(value, default)


class AttendanceUser(BaseModel):
    """签到用户信息"""

    register_user_id: str = Field(description="用户ID")
    status: AttendanceStatus = Field(
        description="签到状态码 1=签到, 2=旷课, 3=迟到, 4=早退, 5=事假, 6=病假, 7=公假, 8=其他"
    )


class QuestionOption(BaseModel):
    """题目选项(单选题/多选题使用)"""

    text: str = Field(description="选项文本内容")
    answer: bool = Field(description="是否为正确答案")


class FillBlankAnswer(BaseModel):
    """填空题答案"""

    text: str = Field(
        description="""答案内容
                        - 对于答案顺序固定的填空题: 提供每个空的唯一答案
                        - 存在答案顺序无关的填空题(需设置is_split_answer=True): 每个空的 'text' 包含所有可能的答案,用英文分号';'隔开,例如: 'A;B'
                    """.replace("\n", " ").strip(),
    )


class AutoScoreType(IntEnum):
    """自动评分类型枚举"""

    EXACT_ORDERED = 1  # 精确匹配+有序
    PARTIAL_ORDERED = 2  # 部分匹配+有序
    EXACT_UNORDERED = 11  # 精确匹配+无序
    PARTIAL_UNORDERED = 12  # 部分匹配+无序

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取自动评分类型名称"""
        name_map = {
            1: "精确匹配+有序",
            2: "部分匹配+有序",
            11: "精确匹配+无序",
            12: "部分匹配+无序",
        }
        return name_map.get(value, default)


class QuestionScoreType(IntEnum):
    """题目评分类型枚举"""

    STRICT = 1  # 严格计分
    LENIENT = 2  # 宽分模式

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取题目评分类型名称"""
        name_map = {
            1: "严格计分",
            2: "宽分模式",
        }
        return name_map.get(value, default)


class RequiredType(IntEnum):
    """是否必答枚举"""

    NO = 1  # 否
    YES = 2  # 是

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取是否必答名称"""
        name_map = {
            1: "否",
            2: "是",
        }
        return name_map.get(value, default)


class AutoStatType(IntEnum):
    """自动评分设置枚举"""

    OFF = 1  # 关闭
    ON = 2  # 开启

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取自动评分设置名称"""
        name_map = {
            1: "关闭",
            2: "开启",
        }
        return name_map.get(value, default)


class DownloadType(IntEnum):
    """下载属性枚举"""

    DISABLED = 1  # 不可下载
    ENABLED = 2  # 可下载

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取下载属性名称"""
        name_map = {
            1: "不可下载",
            2: "可下载",
        }
        return name_map.get(value, default)


class VisibilityType(IntEnum):
    """资源可见性枚举"""

    HIDDEN = 1  # 学生不可见
    VISIBLE = 2  # 学生可见

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取资源可见性名称"""
        name_map = {
            1: "学生不可见",
            2: "学生可见",
        }
        return name_map.get(value, default)


class RandomizationType(IntEnum):
    """随机化类型枚举"""

    DISABLED = 1  # 关闭
    ENABLED = 2  # 开启

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取随机化类型名称"""
        name_map = {
            1: "关闭",
            2: "开启",
        }
        return name_map.get(value, default)


class AnswerStatus(IntEnum):
    """答题状态枚举"""

    IN_PROGRESS = 1  # 答题中
    SUBMITTED = 2  # 已提交

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取答题状态名称"""
        name_map = {
            1: "答题中",
            2: "已提交",
        }
        return name_map.get(value, default)


class AnswerChecked(IntEnum):
    """答案正确性枚举"""

    WRONG = 1  # 错误
    CORRECT = 2  # 正确

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        """获取答案正确性名称"""
        name_map = {
            1: "错误",
            2: "正确",
        }
        return name_map.get(value, default)


class ProgrammingLanguage(Enum):
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


class QuestionData(BaseModel):
    """题目数据结构"""

    class StandardAnswer(BaseModel):
        """标准答案"""

        seqno: str = Field(
            description="""标准答案内容(保持与standard_answers一致):
                            - 单选/多选题:填写A/B/C/D/E...;
                            - 填空题: 顺序填写1/2/3 (表示第几个空和answer_items的seqno对应);
                            - 判断题: 填写A/B;
                        """.replace("\n", " ").strip(),
            min_length=1,
        )
        standard_answer: str = Field(
            description="""标准答案内容(保持与seqno一致):
                            - 单选/多选题:填写A/B/C/D/E...;
                            - 填空题: 具体答案内容 (填空支持乱序/填空有多个答案时用英文分号';'隔开);
                            - 判断题: 填写A/B;
                        """.replace("\n", " ").strip(),
            min_length=1,
        )

    class AnswerItem(BaseModel):
        """题目选项项"""

        seqno: str = Field(
            description="""选项序号:
                            - 单选/多选题:填写A/B/C/D/E...;
                            - 填空题: 填写1/2/3 (表示第几个空和standard_answers的seqno对应);
                            - 判断题: 填写A/B;
                        """.replace("\n", " ").strip(),
            min_length=1,
        )
        context: Optional[str] = Field(
            description="""选项内容
                            - 单选/多选题:填写具体选项内容;
                            - 填空题: 这里填写空字符串"";
                            - 判断题: 如果是A填写"true", 如果是B填写空字符串"";
                        """.replace("\n", " ").strip(),
            default=None,
        )

    type: QuestionType = Field(
        description="题目类型(1=单选题, 2=多选题, 4=填空题, 5=判断题)", ge=1, le=10
    )
    title: List[LineTitle] = Field(
        description="题目描述(支持富文本，多行)(必须包含'____'作为空白标记,后续会自动根据'____'的多少创建填空框,选项数量必须与空白标记数量一致):\n"
        "- 多行:列表形式\n"
        "- 富文本样式:BOLD(粗体)、ITALIC(斜体)、UNDERLINE(下划线)、CODE(代码)\n"
        "- 题目描述格式例下(一行版本,可以多行,必须时换行):\n"
        "  {\n"
        "    'text': '题目内容', 'line_type': 'unstyled'(或 unordered-list-item, ordered-list-item, code-block), \n"
        "    'inlineStyleRanges': [ {'offset': 0, 'length': 4, 'style': 'BOLD'} ]\n"
        "  }\n",
        min_length=1,
    )
    standard_answers: List[StandardAnswer] = Field(
        description="""标准答案列表:
                        - 单选题/多选题: [{'seqno': 'X', 'standard_answer': 'X'}*n] (X为A/B/C...的形式,而且seqno和standard_answer两者一致);
                        - 填空题: [{'seqno': 'X', 'standard_answer': '答案内容'}*n] (X为第X个空,和answer_items的seqno对应,standard_answers中答案数量和填空题题目描述中____的数量一致,填空题支持乱序/一个填空允许多个答案时用英文分号';'隔开);
                        - 判断题为[{'seqno': 'X', 'standard_answer': 'X'}] (X为A/B,而且seqno和standard_answer两者一致,判断题只有一个正确答案,A为正确,B为错误);
                    """.replace("\n", " ").strip(),
        min_length=1,
    )
    description: str = Field(
        description="答案解析(答案请提供足够详细解析,避免过于简短或过长,注意不要搞错成题目描述)",
        min_length=1,
    )
    score: int = Field(description="题目分数", ge=0, default=2)
    answer_items: List[AnswerItem] = Field(
        description="""选项列表:
                        - 单选题/多选题: [{'seqno': 'X', 'context': '选项内容'}*n]; (X为选项,如A/B/C...的形式);
                        - 填空题:[{'seqno': '1'}, {'seqno': '2'}, ...] (表示第几个空和standard_answers的seqno对应,应该和填空题____数量一致);
                        - 判断题为固定[{"seqno": "A", "context": "true"},{"seqno": "B","context": ""}],不要传递其他内容;
                    """.replace("\n", " ").strip(),
        min_length=1,
    )
    automatic_type: Optional[AutoScoreType] = Field(
        default=None,
        description="""填空题自动评分类型(仅填空题)[必须严格根据题目情况选择]:
                        - 1=精确匹配+有序排序: 答案必须完全匹配且顺序一致,适用于每个空只有一个正确答案的情况;
                        - 2=部分匹配+有序排序: 答案部分匹配且顺序一致,适用于每个空有多个正确答案的情况;
                        - 11=精确匹配+无序排序: 答案必须完全匹配但顺序不限,适用于每个空只有一个正确答案且答案顺序不重要的情况;
                        - 12=部分匹配+无序排序: 答案部分匹配且顺序不限,适用于每个空有多个正确答案且答案顺序不重要的情况;
                    """.replace("\n", " ").strip(),
    )


class ChoiceQuestion(BaseModel):
    """单选题/多选题"""

    type: QuestionType = Field(description="题目类型 1=单选题, 2=多选题")
    title: List[LineTitle] = Field(
        description="题目描述(支持富文本，多行):\n"
        "- 多行:列表形式\n"
        "- 富文本样式:BOLD(粗体)、ITALIC(斜体)、UNDERLINE(下划线)、CODE(代码)\n"
        "- 题目描述格式例下(一行版本,可以多行,必须时换行):\n"
        "  {\n"
        "    'text': '题目内容', 'line_type': 'unstyled'(或 unordered-list-item, ordered-list-item, code-block), \n"
        "    'inlineStyleRanges': [ {'offset': 0, 'length': 4, 'style': 'BOLD'} ]\n"
        "  }\n",
        min_length=1,
    )
    description: str = Field(
        description="答案解析(答案请提供足够详细解析,避免过于简短或过长,注意不要搞错成题目描述)",
        min_length=1,
    )
    options: List[QuestionOption] = Field(description="选项列", min_length=4)
    score: int = Field(default=2, description="题目分数", gt=0)
    required: Optional[RequiredType] = Field(
        default=RequiredType.YES, description="是否必答(1=否, 2=是)"
    )
    insert_question_id: Optional[str] = Field(
        default=None, description="插入指定题目ID后面"
    )


class TrueFalseQuestion(BaseModel):
    """判断题"""

    title: List[LineTitle] = Field(
        description="题目描述(支持富文本，多行):\n"
        "- 多行:列表形式\n"
        "- 富文本样式:BOLD(粗体)、ITALIC(斜体)、UNDERLINE(下划线)、CODE(代码)\n"
        "- 题目描述格式例下(一行版本,可以多行,必须时换行):\n"
        "  {\n"
        "    'text': '题目内容', 'line_type': 'unstyled'(或 unordered-list-item, ordered-list-item, code-block), \n"
        "    'inlineStyleRanges': [ {'offset': 0, 'length': 4, 'style': 'BOLD'} ]\n"
        "  }\n",
        min_length=1,
    )
    description: str = Field(
        description="答案解析(答案请提供足够详细解析,避免过于简短或过长,注意不要搞错成题目描述)",
        min_length=1,
    )
    answer: bool = Field(description="正确答案")
    score: int = Field(default=2, description="题目分数", gt=0)
    required: Optional[RequiredType] = Field(
        default=RequiredType.YES, description="是否必答(1=否, 2=是)"
    )
    insert_question_id: Optional[str] = Field(
        default=None, description="插入指定题目ID后面"
    )


class FillBlankQuestion(BaseModel):
    """填空题"""

    title: List[LineTitle] = Field(
        description="题目描述(支持富文本，多行)(必须包含'____'作为空白标记,后续会自动根据'____'的多少创建填空框,选项数量必须与空白标记数量一致):\n"
        "- 多行:列表形式\n"
        "- 富文本样式:BOLD(粗体)、ITALIC(斜体)、UNDERLINE(下划线)、CODE(代码)\n"
        "- 题目描述格式例下(一行版本,可以多行,必须时换行):\n"
        "  {\n"
        "    'text': '题目内容', 'line_type': 'unstyled'(或 unordered-list-item, ordered-list-item, code-block), \n"
        "    'inlineStyleRanges': [ {'offset': 0, 'length': 4, 'style': 'BOLD'} ]\n"
        "  }\n",
        min_length=1,
    )
    description: str = Field(
        description="答案解析(答案请提供足够详细解析,避免过于简短或过长,注意不要搞错成题目描述)",
        min_length=1,
    )
    options: List[FillBlankAnswer] = Field(description="答案列表")
    score: int = Field(default=2, description="题目分数", gt=0)
    required: Optional[RequiredType] = Field(
        default=RequiredType.YES, description="是否必答(1=否, 2=是)"
    )
    is_split_answer: Optional[bool] = Field(
        default=None, description="是否允许多个答案"
    )
    automatic_stat: Optional[AutoStatType] = Field(
        default=None, description="自动评分设置(1=关闭, 2=开启)"
    )
    automatic_type: Optional[AutoScoreType] = Field(
        default=None,
        description="""自动评分类型:
                        - 1=精确匹配+有序排序: 答案必须完全匹配且顺序一致,适用于每个空只有一个正确答案的情况;
                        - 2=部分匹配+有序排序: 答案部分匹配且顺序一致,适用于每个空有多个正确答案的情况;
                        - 11=精确匹配+无序排序: 答案必须完全匹配但顺序不限,适用于每个空只有一个正确答案且答案顺序不重要的情况;
                        - 12=部分匹配+无序排序: 答案部分匹配且顺序不限,适用于每个空有多个正确答案且答案顺序不重要的情况;
                    """.replace("\n", " ").strip(),
    )
    insert_question_id: Optional[str] = Field(
        default=None, description="插入指定题目ID后面"
    )


class ProgramConfig(BaseModel):
    """编程题配置"""

    max_memory: Optional[int] = Field(default=5000, description="内存限制(kb)", gt=0)
    max_time: Optional[int] = Field(default=500, description="时间限制(ms)", gt=0)

    debug: Optional[int] = Field(
        default=2, description="是否允许试运行(1是关闭,2是开启)", ge=1, le=2
    )
    debug_count: Optional[int] = Field(
        default=9999, description="试运行次数", gt=0, le=9999
    )

    runcase: Optional[int] = Field(
        default=1, description="是否允许运行测试用例(1是关闭,2是开启)", ge=1, le=2
    )
    runcase_count: Optional[int] = Field(
        default=9999, description="运行测试用例次数", gt=0, le=9999
    )

    language: List[ProgrammingLanguage] = Field(
        description="允许使用的编程语言列表",
        min_length=1,
        default=[ProgrammingLanguage.C],
    )

    example_language: ProgrammingLanguage = Field(
        default=ProgrammingLanguage.C,
        description="示例代码语言(默认和language第一个一致)",
    )
    example_code: str = Field(
        default=None,
        description="参考答案代码,必须要足够详细的注释(通过\n换行;code_answer和example_code可以一致)",
    )

    answer_language: ProgrammingLanguage = Field(
        default=ProgrammingLanguage.C,
        description="参考答案代码语言(默认和language第一个一致)",
    )
    code_answer: str = Field(
        default=None,
        description="参考答案代码,必须要足够详细的注释(通过\n换行;code_answer和example_code可以一致)",
    )


# 编程题
class CodeQuestion(BaseModel):
    """编程题"""

    title: List[LineTitle] = Field(
        description="题目描述(支持富文本，多行):\n"
        "- 多行:列表形式\n"
        "- 富文本样式:BOLD(粗体)、ITALIC(斜体)、UNDERLINE(下划线)、CODE(代码)\n"
        "- 题目描述格式例下(一行版本,可以多行,必须时换行):\n"
        "  {\n"
        "    'text': '题目内容', 'line_type': 'unstyled'(或 unordered-list-item, ordered-list-item, code-block), \n"
        "    'inlineStyleRanges': [ {'offset': 0, 'length': 4, 'style': 'BOLD'} ]\n"
        "  }\n",
        min_length=1,
    )
    description: str = Field(
        description="答案解析(答案请提供足够详细解析,避免过于简短或过长,注意不要搞错成题目描述)",
        min_length=1,
    )
    program_config: ProgramConfig = Field(description="编程题配置")
    score: int = Field(default=2, description="题目分数", gt=0)
    required: Optional[RequiredType] = Field(
        default=RequiredType.YES, description="是否必答(1=否, 2=是)"
    )
    insert_question_id: Optional[str] = Field(
        default=None, description="插入指定题目ID后面"
    )
