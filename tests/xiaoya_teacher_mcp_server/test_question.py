import uuid
from dotenv import load_dotenv, find_dotenv
from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.resources import (
    create as resource_create,
    delete as resource_delete,
    query as resource_query,
)
from xiaoya_teacher_mcp_server.tools.questions import create, query, update, delete
from xiaoya_teacher_mcp_server.types.types import (
    ChoiceQuestion,
    CodeQuestion,
    ProgramSettingAllNeed,
    ProgrammingLanguage,
    TrueFalseQuestion,
    FillBlankQuestion,
    ShortAnswerQuestion,
    AttachmentQuestion,
    LineText,
    QuestionOption,
    FillBlankAnswer,
    AutoScoreType,
    RandomizationType,
    ResourceType,
    SingleChoiceQuestionData,
    MultipleChoiceQuestionData,
    TrueFalseQuestionData,
    StandardAnswer,
    AnswerItem,
)

load_dotenv(find_dotenv())


def _create_test_paper(test_name: str) -> tuple:
    group_id = group_query.query_teacher_groups()["data"][0]["group_id"]
    resources = resource_query.query_course_resources(group_id, "flat")["data"]
    root = next((r for r in resources if r.get("name") == "root"), None)
    assert root is not None, "找不到root资源"

    resource_name = f"test_{test_name}_{uuid.uuid4().hex[:8]}"
    result = resource_create.create_course_resource(
        group_id, ResourceType.ASSIGNMENT, root["id"], resource_name
    )
    assert result["success"], f"创建测试试卷失败: {result}"
    return result["data"]["paper_id"], group_id, result["data"]["id"]


def test_create_and_query_paper():
    """测试创建7种题型并查询"""
    paper_id, group_id, resource_id = _create_test_paper("query")
    try:
        questions_data = [
            ChoiceQuestion(
                title=[LineText(text="Python中哪个关键字用于定义函数?")],
                description="函数定义使用def关键字。Python使用def关键字定义函数,这是Python的基本语法之一。",
                options=[
                    QuestionOption(text=[LineText(text="def")], answer=True),
                    QuestionOption(text=[LineText(text="function")], answer=False),
                    QuestionOption(text=[LineText(text="func")], answer=False),
                    QuestionOption(text=[LineText(text="define")], answer=False),
                ],
                score=10,
            ),
            ChoiceQuestion(
                title=[LineText(text="以下哪些是Python的数据类型?")],
                description="int、str、list都是Python的基本数据类型",
                options=[
                    QuestionOption(text=[LineText(text="int")], answer=True),
                    QuestionOption(text=[LineText(text="str")], answer=True),
                    QuestionOption(text=[LineText(text="char")], answer=False),
                    QuestionOption(text=[LineText(text="list")], answer=True),
                    QuestionOption(text=[LineText(text="tuple")], answer=False),
                ],
                score=10,
            ),
            TrueFalseQuestion(
                title=[LineText(text="Python是编译型语言")],
                description="Python是解释型语言",
                answer=False,
                score=10,
            ),
            FillBlankQuestion(
                title=[LineText(text="Python是一种____语言,由____开发")],
                description="Python是解释型语言,由Guido van Rossum在1989年开发。",
                options=[FillBlankAnswer(text="解释型;Guido van Rossum")],
                automatic_type=AutoScoreType.PARTIAL_ORDERED,
                score=10,
            ),
            ShortAnswerQuestion(
                title=[LineText(text="请简述Python的主要特点")],
                description="主要特点：简洁易读、动态类型、丰富的库",
                answer=[LineText(text="Python语法简洁,支持动态类型,拥有丰富的标准库")],
                score=10,
            ),
            AttachmentQuestion(
                title=[LineText(text="请上传在Pycharm中运行的Python项目代码")],
                description="提交在Pycharm中运行的Python项目代码",
                score=10,
            ),
            CodeQuestion(
                title=[LineText(text="请编写一个Python程序")],
                description="编写一个Python程序,输出Hello, World!",
                program_setting=ProgramSettingAllNeed(
                    language=[ProgrammingLanguage.PYTHON3],
                    answer_language=ProgrammingLanguage.PYTHON3,
                    code_answer="print('Hello, World!')",
                    in_cases=[{"in": ""} for _ in range(10)],
                    max_time=1000,
                    max_memory=1024,
                    debug=2,
                    debug_count=9999,
                    runcase=2,
                    runcase_count=100,
                ),
                score=10,
            ),
        ]

        create.batch_create_questions(paper_id, questions_data)
        result = query.query_paper(group_id, paper_id, need_parse=True)
        assert result["success"]
        titles = [
            f"{i}. {''.join(q['title'])}"
            for i, q in enumerate(result["data"]["questions"], 1)
        ]
        print("\n" + "\n".join(titles))
    finally:
        resource_delete.delete_course_resource(group_id, resource_id)


def test_batch_update_sort_and_delete():
    """测试批量操作、选项排序、编程题测试用例、题目排序和删除"""
    paper_id, group_id, resource_id = _create_test_paper("batch_update")
    try:
        questions = [
            ChoiceQuestion(
                title=[LineText(text=f"批量测试单选题{i + 1}")],
                description=f"批量测试描述{i + 1}",
                options=[
                    QuestionOption(text=[LineText(text="选项A")], answer=True),
                    QuestionOption(text=[LineText(text="选项B")], answer=False),
                    QuestionOption(text=[LineText(text="选项C")], answer=False),
                    QuestionOption(text=[LineText(text="选项D")], answer=False),
                ],
                score=10,
            )
            for i in range(8)
        ]
        questions.append(
            CodeQuestion(
                title=[LineText(text="编写程序输出两数之和")],
                description="输入两个整数,输出它们的和",
                program_setting=ProgramSettingAllNeed(
                    language=[ProgrammingLanguage.PYTHON3],
                    answer_language=ProgrammingLanguage.PYTHON3,
                    code_answer="a, b = map(int, input().split())\nprint(a + b)",
                    in_cases=[{"in": "1 2"}],
                    max_time=1000,
                    max_memory=10000,
                    debug=2,
                    debug_count=9999,
                    runcase=2,
                    runcase_count=100,
                ),
                score=20,
            )
        )

        batch_result = create.batch_create_questions(paper_id, questions)
        assert batch_result["success"]
        print(f"\n1. ✓ `批量创建`: {batch_result['message']}")

        # 确保所有题目都成功创建
        paper_data = query.query_paper(group_id, paper_id, need_parse=False)
        assert paper_data["success"]
        all_questions = paper_data["data"]["questions"]
        question_ids = [q["id"] for q in all_questions]
        assert len(question_ids) == len(questions)

        first_question = all_questions[0]
        answer_item_ids = [item["id"] for item in first_question["options"]]
        move_result = update.move_answer_item(
            question_ids[0], list(reversed(answer_item_ids))
        )
        assert move_result["success"]
        print("2. ✓ 选项排序")

        code_question = all_questions[-1]
        update_cases_result = update.update_code_test_cases(
            question_id=code_question["id"],
            program_setting_id=code_question["program_setting"]["id"],
            answer_item_id=code_question["options"][0]["id"],
            answer_language=ProgrammingLanguage.PYTHON3,
            code_answer="a, b = map(int, input().split())\nprint(a + b)",
            in_cases=[{"in": "1 2"}, {"in": "3 5"}],
        )
        assert update_cases_result["success"]
        print("3. ✓ 编程题测试用例")

        updated = update.update_question(
            question_ids[0],
            title=[LineText(text="更新后的题目标题")],
            score=15,
            description="更新后的描述内容",
        )
        assert updated["success"]
        print("4. ✓ 题目更新")

        sort_result = update.update_paper_question_order(
            paper_id, list(reversed(question_ids))
        )
        assert sort_result["success"]
        print("5. ✓ 题目排序")

        rand_result = update.update_paper_randomization(
            paper_id,
            question_shuffle=RandomizationType.DISABLED,
            option_shuffle=RandomizationType.DISABLED,
        )
        assert rand_result["success"]
        print("6. ✓ 随机化设置")

        deleted = delete.delete_questions(paper_id, question_ids[:2])
        assert deleted["success"]
        print("7. ✓ 删除题目")
    finally:
        resource_delete.delete_course_resource(group_id, resource_id)


def test_office_create_questions():
    """测试官方批量导入"""
    paper_id, group_id, resource_id = _create_test_paper("office_import")
    try:
        questions = [
            SingleChoiceQuestionData(
                title="Python是什么类型的语言?",
                standard_answers=[StandardAnswer(seqno="A", standard_answer="A")],
                description="Python是一种解释型、面向对象的高级编程语言",
                score=5,
                answer_items=[
                    AnswerItem(seqno="A", context="解释型语言"),
                    AnswerItem(seqno="B", context="编译型语言"),
                    AnswerItem(seqno="C", context="汇编语言"),
                    AnswerItem(seqno="D", context="机器语言"),
                ],
            ),
            MultipleChoiceQuestionData(
                title="以下哪些是Python的特点?",
                standard_answers=[
                    StandardAnswer(seqno="A", standard_answer="A"),
                    StandardAnswer(seqno="B", standard_answer="B"),
                    StandardAnswer(seqno="D", standard_answer="D"),
                ],
                description="Python具有简洁的语法、丰富的库和跨平台特性",
                score=5,
                answer_items=[
                    AnswerItem(seqno="A", context="语法简洁"),
                    AnswerItem(seqno="B", context="库丰富"),
                    AnswerItem(seqno="C", context="仅支持Windows"),
                    AnswerItem(seqno="D", context="跨平台"),
                ],
            ),
            TrueFalseQuestionData(
                title="Python支持面向对象编程",
                standard_answers=[StandardAnswer(seqno="A", standard_answer="A")],
                description="Python完全支持面向对象编程",
                score=3,
                answer_items=[
                    AnswerItem(seqno="A", context="true"),
                    AnswerItem(seqno="B", context=""),
                ],
            ),
        ]

        result = create.office_create_questions(paper_id, questions)
        assert result["success"]
        print(f"\n✓ 官方批量导入: {result['message']}")

        paper_result = query.query_paper(group_id, paper_id, need_parse=True)
        assert paper_result["success"]
        assert len(paper_result["data"]["questions"]) == 3
        print(f"✓ 验证成功,共{len(paper_result['data']['questions'])}道题目")
    finally:
        resource_delete.delete_course_resource(group_id, resource_id)
