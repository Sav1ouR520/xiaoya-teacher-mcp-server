"""MCP 工具和数据模型的字段说明常量。"""

# ── IDs ──────────────────────────────────────────────────────────────────────
REGISTER_USER_ID_DESC = "用户ID"
GROUP_ID_DESC = "课程组id（通过 query_teacher_groups 获取）"
PAPER_ID_DESC = "试卷ID（通过 query_group_tasks 获取）"
PAPER_ID_FILE_DESC = "资源文件的 paper_id（通过 query_course_resources 获取）"
QUESTION_ID_DESC = "题目id（通过 query_paper 获取）"
QUESTION_TYPE_DESC = "题目类型编号（1=单选 2=多选 4=填空 5=判断 6=简答 7=附件 10=编程）"
RESOURCE_ID_DESC = "资源id"
NODE_ID_DESC = "资源节点id（通过 query_course_resources 获取）"
NODE_ID_LIST_DESC = "资源节点id列表"
RESOURCE_ID_LIST_DESC = "资源id列表"
PARENT_ID_DESC = "父资源id（根目录填 group_id）"
FROM_PARENT_ID_DESC = "当前父文件夹id"
TO_PARENT_ID_DESC = "目标父文件夹id"
COURSE_ID_DESC = "课程id"
COURSE_ID_FROM_ATTENDANCE_DESC = "课程id（来自 query_attendance_records 的 course_id 字段）"
REGISTER_ID_DESC = "签到id（来自 query_attendance_records 的 id 字段）"
MARK_MODE_ID_DESC = "阅卷模式id（来自 query_test_result 的 mark_mode_id 字段）"
MARK_PAPER_RECORD_ID_DESC = "批阅记录id（来自 query_preview_student_paper 的 mark_paper_record_id 字段）"
PUBLISH_ID_DESC = "发布id（来自 query_group_tasks 的 publish_id 字段）"
RECORD_ID_DESC = "答题记录id（来自 query_test_result 的 answer_records[].record_id 字段）"
ANSWER_ID_DESC = "学生单题答案id（来自 query_preview_student_paper 的 questions[].answer_id 字段）"
QUOTE_ID_DESC = "附件文件id（来自 query_preview_student_paper 的 questions[].attachments[].quote_id，支持图片/PDF/视频）"
ANSWER_ITEM_ID_DESC = "答案项id"
OPTION_ID_DESC = "选项id"
QUESTION_ID_LIST_DESC = "要删除的题目id列表"
ANSWER_ITEM_ID_LIST_DESC = "按新顺序排列的选项id列表"
QUESTION_ID_LIST_ORDER_DESC = "按新顺序排列的题目id列表"
RESOURCE_ID_LIST_ORDER_DESC = "按所需顺序排列的资源id列表"

# ── 名称 / 文件 ───────────────────────────────────────────────────────────────
RESOURCE_NAME_DESC = "资源名称"
RESOURCE_NEW_NAME_DESC = "资源的新名称"
FILENAME_DESC = "资源文件名（通过 query_course_resources 获取）"
FILE_PATH_DESC = "本地磁盘文件路径"
SAVE_PATH_DESC = "文件保存路径（不填则保存到临时文件夹）"
ROLE_DESC = "角色类型（3=教师）"

# ── 分值 / 必答 ───────────────────────────────────────────────────────────────
QUESTION_SCORE_DESC = "题目分数（大于0的整数）"
QUESTION_SCORE_UPDATE_DESC = "题目分值（大于等于0的整数）"
REQUIRED_DESC = "是否必答（1=否 2=是）"
INSERT_AFTER_DESC = "插入到指定题目ID后面（不填则追加到末尾）"

# ── 批改 ──────────────────────────────────────────────────────────────────────
CHECK_SCORE_DESC = "批改得分（不能超过题目满分）"
CHECK_COMMENT_DESC = "批改评语（可为空）"

# ── 查询粒度 / 模式 ───────────────────────────────────────────────────────────
NEED_DETAIL_DESC = "是否在返回中包含完整题目内容（选项、答案等），仅需确认成功时设为 false"
RETURN_PARSE_DESC = "true 返回纯文本（plain），false 返回原始富文本结构（raw）"
PARSE_MODE_DESC = "富文本解析模式：plain=纯文本，raw=原始结构"
PAPER_DETAIL_LEVEL_DESC = "试卷粒度：summary=仅元信息，full=含全部题目"
RESOURCE_DETAIL_LEVEL_DESC = "资源粒度：summary=名称/类型，full=全字段，raw=原始 API 数据"
RESOURCE_VIEW_MODE_DESC = "资源视图：tree=树形结构，flat=平铺列表"
TASK_DETAIL_LEVEL_DESC = "任务粒度：summary=基础信息，full=含时间/任务id"
ANSWER_DETAIL_LEVEL_DESC = "答题粒度：summary=得分/状态，full=含答题内容"
RESOURCE_TYPE_DESC = "资源类型"
DOWNLOAD_TYPE_DESC = "下载权限（1=禁止 2=允许）"
VISIBILITY_TYPE_DESC = "资源可见性（1=隐藏 2=可见）"

# ── 题干 / 选项文本 ───────────────────────────────────────────────────────────
QUESTION_TITLE_DESC = "题干"
FILL_BLANK_TITLE_DESC = "题干（必须包含 ____ 作为填空占位符，有几个空就写几个 ____）"

QUESTION_RICH_TEXT_DESC = "题干纯文本，与 title_raw 二选一（优先用 title_raw 以支持富文本格式）"

QUESTION_RAW_RICH_TEXT_DESC = (
    "题干富文本（Draft.js 格式），与 title 二选一。\n"
    "格式：{\"blocks\": [{\"text\": \"行内容\", \"type\": \"unstyled\", \"inlineStyleRanges\": []}, ...], \"entityMap\": {}}\n"
    "  type 可选：unstyled（普通段落）| code-block（代码块）\n"
    "           | ordered-list-item（有序列表）| unordered-list-item（无序列表）\n"
    "  inlineStyleRanges 可选：[{\"offset\": 起始位, \"length\": 长度, \"style\": \"BOLD\"}]\n"
    "    style 可选：BOLD | ITALIC | UNDERLINE | CODE\n"
    "编程题建议分行：题目说明 → 输入格式 → 输出格式 → 样例输入 → 样例输出"
)

OPTION_TEXT_DESC = "选项纯文本，与 text_raw 二选一"
OPTION_RAW_TEXT_DESC = "选项富文本，与 text 二选一"
OPTION_ANSWER_DESC = "是否为正确答案"
REFERENCE_RICH_TEXT_DESC = "参考答案纯文本，与 answer_raw 二选一"
REFERENCE_RAW_RICH_TEXT_DESC = "参考答案富文本，与 answer 二选一"
ANSWER_TEXT_DESC = "答案文本"
TRUE_FALSE_ANSWER_DESC = "正确答案（true=正确，false=错误）"

# ── 答案 / 解析 ───────────────────────────────────────────────────────────────
ANSWER_EXPLANATION_DESC = "答案解析或补充说明；编程题参考代码请填写到 program_setting.code_answer"

STANDARD_SEQ_DESC = "答案序号：选择题 A/B/C…，填空 1/2/3，判断 A/B，简答/附件 A"
STANDARD_CONTENT_DESC = "答案内容"
ANSWER_ITEM_CONTEXT_DESC = "选项内容"
STANDARD_ANSWERS_LIST_DESC = "标准答案列表"
ANSWER_ITEMS_LIST_DESC = "选项列表"
QUESTION_OPTIONS_DESC = "选项列表（至少 4 项）"
FILL_BLANK_ANSWERS_DESC = "填空答案列表"
BLANK_ANSWER_COUNT_DESC = "空白答案项数量"

# ── 题目类型 ──────────────────────────────────────────────────────────────────
QUESTION_LIST_DESC = "题目列表"
SINGLE_CHOICE_QUESTION_DESC = "单选题"
MULTIPLE_CHOICE_QUESTION_DESC = "多选题"
FILL_BLANK_QUESTION_DESC = "填空题"
TRUE_FALSE_QUESTION_DESC = "判断题"
SHORT_ANSWER_QUESTION_DESC = "简答题"
ATTACHMENT_QUESTION_DESC = "附件题"
CODE_QUESTION_DESC = (
    "编程题。各字段说明：\n"
    "  title_raw  题干富文本，建议分行写：题目说明 / 输入格式 / 输出格式 / 样例\n"
    "  description  解析或补充说明，不能放参考代码\n"
    "  program_setting  配置语言、code_answer 参考代码、in_cases 测试输入列表、内存/时间限制"
)

# ── 编程题配置 ────────────────────────────────────────────────────────────────
PROGRAM_SETTING_DESC = "编程题配置（语言、参考答案、测试用例、内存/时间限制）"
PROGRAM_SETTING_OPTIONAL_DESC = "编程题配置（仅编程题需要填写）"
PROGRAM_SETTING_ID_DESC = "编程配置ID（内部字段，创建时由系统自动赋值，无需手动填写）"
PROGRAM_SETTING_ANSWER_ITEM_DESC = "编程答案项ID（内部字段，创建时由系统自动赋值，无需手动填写）"
ANSWER_LANGUAGE_DESC = "参考答案代码语言（如 python3 / c / java 等）"
CODE_ANSWER_DESC = "参考答案代码（用 \\n 换行，需能独立运行并产生正确输出）"
RUN_CODE_ANSWER_DESC = "运行测试用的参考代码（需能根据输入产生正确输出）"
IN_CASES_DESC = (
    "测试用例输入列表，格式：[{\"in\": \"输入内容\"}, ...]。\n"
    "平台自动运行参考答案生成期望输出，每条只需提供输入。\n"
    "多行输入用 \\n 分隔，如 {\"in\": \"3\\n4\"}"
)

TEST_CASE_LIST_DESC = "测试用例列表（含输入和期望输出）"
TEST_CASE_INPUT_DESC = "测试输入"
TEST_CASE_OUTPUT_DESC = "期望输出"
PROGRAM_MAX_MEMORY_DESC = "内存限制（KB，默认 5000）"
PROGRAM_MAX_TIME_DESC = "时间限制（ms，默认 1000）"
DEBUG_COUNT_DESC = "试运行次数上限（0=禁用，9999=不限）"
EXAMPLE_CODE_DESC = "示例代码"

# ── 其他 ──────────────────────────────────────────────────────────────────────
ATTENDANCE_LIST_DESC = "签到用户列表"
AUTO_SCORE_DESC = "自动评分类型（1=精确匹配+有序 2=部分匹配+有序 11=精确匹配+无序 12=部分匹配+无序）"
AUTO_STAT_DESC = "是否开启自动评分（1=关闭 2=开启）"
SPLIT_ANSWER_DESC = "是否允许每个空有多个答案（仅填空题，true=允许）"
RANDOMIZE_QUESTION_DESC = "题目顺序随机（1=关闭 2=开启）"
RANDOMIZE_OPTION_DESC = "选项顺序随机（1=关闭 2=开启，仅对选择题生效）"
QUESTION_SCORE_TYPE_DESC = "计分方式（1=严格计分：全对才得分 2=宽分模式：按正确选项比例得分）"
