import json
import os
import uuid

import pytest
from dotenv import find_dotenv, load_dotenv

from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.questions import create, delete, query, update
from xiaoya_teacher_mcp_server.tools.questions.normalize import parse_question
from xiaoya_teacher_mcp_server.tools.resources import (
    create as resource_create,
    delete as resource_delete,
    query as resource_query,
)
from xiaoya_teacher_mcp_server.types import (
    AnswerItem,
    AttachmentQuestion,
    AutoScoreType,
    ChoiceQuestion,
    CodeQuestion,
    FillBlankAnswer,
    FillBlankQuestion,
    MultipleChoiceQuestionData,
    ProgramSetting,
    ProgramSettingAllNeed,
    ProgrammingLanguage,
    QuestionOption,
    RandomizationType,
    ResourceType,
    ShortAnswerQuestion,
    SingleChoiceQuestionData,
    StandardAnswer,
    TrueFalseQuestion,
    TrueFalseQuestionData,
)

load_dotenv(find_dotenv())

requires_live_auth = pytest.mark.skipif(
    not (
        os.getenv("XIAOYA_AUTH_TOKEN")
        or (os.getenv("XIAOYA_ACCOUNT") and os.getenv("XIAOYA_PASSWORD"))
    ),
    reason="需要配置小雅认证环境变量",
)


def _find_root_resource(resource_tree):
    """递归查找名为 'root' 的资源"""
    for resource in resource_tree:
        if resource.get("name") == "root":
            return resource
        if "children" in resource and resource["children"]:
            found = _find_root_resource(resource["children"])
            if found:
                return found
    return None


def _create_test_paper(test_name: str) -> tuple:
    group_id = group_query.query_teacher_groups()["data"][0]["group_id"]
    summary_result = resource_query.query_course_resources_summary(group_id)
    assert summary_result["success"], f"查询资源失败: {summary_result}"

    root = _find_root_resource(summary_result["data"])
    assert root is not None, "找不到root资源"

    root_attr = resource_query.query_resource_attributes(group_id, root["id"])
    assert root_attr["success"], f"查询root资源属性失败: {root_attr}"
    root_id = root_attr["data"]["id"]

    resource_name = f"test_{test_name}_{uuid.uuid4().hex[:8]}"
    result = resource_create.create_course_resource(
        group_id, ResourceType.ASSIGNMENT, root_id, resource_name
    )
    assert result["success"], f"创建测试试卷失败: {result}"
    return result["data"]["paper_id"], group_id, result["data"]["id"]


@requires_live_auth
def test_create_and_query_paper():
    """测试创建7种题型并查询"""
    paper_id, group_id, resource_id = _create_test_paper("query")
    try:
        questions_data = [
            ChoiceQuestion(
                title="Python中哪个关键字用于定义函数?",
                description="函数定义使用def关键字。Python使用def关键字定义函数,这是Python的基本语法之一。",
                options=[
                    QuestionOption(text="def", answer=True),
                    QuestionOption(text="function", answer=False),
                    QuestionOption(text="func", answer=False),
                    QuestionOption(text="define", answer=False),
                ],
                score=10,
            ),
            ChoiceQuestion(
                title="以下哪些是Python的数据类型?",
                description="int、str、list都是Python的基本数据类型",
                options=[
                    QuestionOption(text="int", answer=True),
                    QuestionOption(text="str", answer=True),
                    QuestionOption(text="char", answer=False),
                    QuestionOption(text="list", answer=True),
                    QuestionOption(text="tuple", answer=False),
                ],
                score=10,
            ),
            TrueFalseQuestion(
                title="Python是编译型语言",
                description="Python是解释型语言",
                answer=False,
                score=10,
            ),
            FillBlankQuestion(
                title="Python是一种____语言,由____开发",
                description="Python是解释型语言,由Guido van Rossum在1989年开发。",
                options=[FillBlankAnswer(text="解释型;Guido van Rossum")],
                automatic_type=AutoScoreType.PARTIAL_ORDERED,
                score=10,
            ),
            ShortAnswerQuestion(
                title="请简述Python的主要特点",
                description="主要特点: 简洁易读、动态类型、丰富的库",
                answer="Python语法简洁,支持动态类型,拥有丰富的标准库",
                score=10,
            ),
            AttachmentQuestion(
                title="请上传在Pycharm中运行的Python项目代码",
                description="提交在Pycharm中运行的Python项目代码",
                score=10,
            ),
            CodeQuestion(
                title="请编写一个Python程序",
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
        result = query.query_paper(group_id, paper_id, parse_mode="plain")
        assert result["success"]
        titles = [
            f"{index}. {question['title']}"
            for index, question in enumerate(result["data"]["questions"], 1)
        ]
        print("\n" + "\n".join(titles))
    finally:
        resource_delete.delete_course_resource(group_id, resource_id)


@requires_live_auth
def test_batch_update_sort_and_delete():
    """测试批量操作、选项排序、编程题测试用例、题目排序和删除"""
    paper_id, group_id, resource_id = _create_test_paper("batch_update")
    try:
        questions = [
            ChoiceQuestion(
                title=f"批量测试单选题{i + 1}",
                description=f"批量测试描述{i + 1}",
                options=[
                    QuestionOption(text="选项A", answer=True),
                    QuestionOption(text="选项B", answer=False),
                    QuestionOption(text="选项C", answer=False),
                    QuestionOption(text="选项D", answer=False),
                ],
                score=10,
            )
            for i in range(8)
        ]
        questions.append(
            CodeQuestion(
                title="编写程序输出两数之和",
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

        paper_data = query.query_paper(
            group_id, paper_id, detail_level="full", parse_mode="raw"
        )
        assert paper_data["success"]
        all_questions = paper_data["data"]["questions"]
        question_ids = [question["id"] for question in all_questions]
        assert len(question_ids) == len(questions)

        first_question = all_questions[0]
        answer_item_ids = [item["answer_item_id"] for item in first_question["options"]]
        move_result = update.move_answer_item(
            question_ids[0], list(reversed(answer_item_ids))
        )
        assert move_result["success"]
        print("2. ✓ 选项排序")

        code_question = all_questions[-1]
        update_cases_result = update.update_code_test_cases(
            question_id=code_question["id"],
            program_setting_id=code_question["program_setting"]["id"],
            answer_item_id=code_question["options"][0]["answer_item_id"],
            answer_language=ProgrammingLanguage.PYTHON3,
            code_answer="a, b = map(int, input().split())\nprint(a + b)",
            in_cases=[{"in": "1 2"}, {"in": "3 5"}],
        )
        assert update_cases_result["success"]
        print("3. ✓ 编程题测试用例")

        updated = update.update_question(
            question_ids[0],
            title="更新后的题目标题",
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


@requires_live_auth
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

        paper_result = query.query_paper(group_id, paper_id, parse_mode="plain")
        assert paper_result["success"]
        assert len(paper_result["data"]["questions"]) == 3
        print(f"✓ 验证成功,共{len(paper_result['data']['questions'])}道题目")
    finally:
        resource_delete.delete_course_resource(group_id, resource_id)


def test_update_question_options_accepts_string_id_and_text(monkeypatch):
    captured = {}

    def fake_post(url, *, payload=None, timeout=20, allow_http_error=False):
        captured["url"] = url
        captured["payload"] = payload
        return {
            "success": True,
            "data": [
                {
                    "id": "answer-1",
                    "value": captured["payload"]["value"],
                    "answer_checked": 2,
                }
            ],
        }

    monkeypatch.setattr(update, "post_json", fake_post)

    result = update.update_question_options(
        question_id="question-1",
        answer_item_id="answer-1",
        option_text="更新后的选项",
        is_answer=True,
    )

    assert result["success"]
    assert captured["payload"]["answer_item_id"] == "answer-1"
    assert captured["payload"]["answer_checked"] == 2
    assert json.loads(captured["payload"]["value"])["blocks"][0]["text"] == "更新后的选项"


def test_update_question_validates_code_cases_before_remote_update(monkeypatch):
    called = False

    def fake_post_update_question(**payload):
        nonlocal called
        called = True
        return payload

    monkeypatch.setattr(update, "_post_update_question", fake_post_update_question)

    result = update.update_question(
        question_id="question-1",
        program_setting=ProgramSetting(
            code_answer="print(input())",
            answer_language=ProgrammingLanguage.PYTHON3,
            in_cases=[{"in": "hello"}],
        ),
    )

    assert not result["success"]
    assert called is False
    assert "answer_item_id" in result["message"]


def test_batch_create_questions_marks_partial_failure(monkeypatch):
    questions = [
        ChoiceQuestion(
            title="成功题",
            description="desc",
            options=[
                QuestionOption(text="A", answer=True),
                QuestionOption(text="B", answer=False),
                QuestionOption(text="C", answer=False),
                QuestionOption(text="D", answer=False),
            ],
            score=5,
        ),
        ChoiceQuestion(
            title="失败题",
            description="desc",
            options=[
                QuestionOption(text="A", answer=True),
                QuestionOption(text="B", answer=False),
                QuestionOption(text="C", answer=False),
                QuestionOption(text="D", answer=False),
            ],
            score=5,
        ),
    ]

    calls = {"count": 0}

    def fake_create_choice_question(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"success": True, "data": {"id": "question-1"}}
        return {"success": False, "message": "模拟失败"}

    monkeypatch.setattr(create, "_create_choice_question", fake_create_choice_question)

    result = create.batch_create_questions("paper-1", questions)

    assert not result["success"]
    assert result["data"]["success_count"] == 1
    assert result["data"]["failed_count"] == 1
    assert result["data"]["partial_success"] is True
    assert result["data"]["failed_items"] == [
        {"index": 2, "type": "单选题", "title": "失败题", "message": "模拟失败"}
    ]


def test_delete_questions_returns_failed_items(monkeypatch):
    def fake_post_json(url, *, payload=None, timeout=20, allow_http_error=False):
        if payload["question_id"] == "q1":
            return {"success": True, "data": None}
        return {"success": False, "message": "不存在"}

    monkeypatch.setattr(delete, "post_json", fake_post_json)

    result = delete.delete_questions("paper-1", ["q1", "q2"])

    assert not result["success"]
    assert result["data"]["success_count"] == 1
    assert result["data"]["failed_count"] == 1
    assert result["data"]["partial_success"] is True
    assert result["data"]["success_ids"] == ["q1"]
    assert result["data"]["failed_items"] == [{"question_id": "q2", "message": "不存在"}]


def test_parse_question_fill_blank_fields_are_mapped_correctly():
    result = parse_question(
        {
            "id": "question-1",
            "title": "title",
            "description": "desc",
            "type": 4,
            "score": 5,
            "required": 2,
            "answer_items_sort": "",
            "answer_items": [],
            "is_split_answer": False,
            "automatic_type": 1,
            "automatic_stat": 2,
        },
        parse_mode="raw",
    )

    assert result["automatic_type"] == "精确匹配+有序"
    assert result["automatic_stat"] == "开启"


def test_office_create_questions_detects_answer_mismatch(monkeypatch):
    monkeypatch.setattr(
        create,
        "post_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": [
                {
                    "id": "question-1",
                    "type": 1,
                    "answer_items": [
                        {"id": "a1", "answer_checked": 2},
                        {"id": "a2", "answer_checked": 1},
                        {"id": "a3", "answer_checked": 1},
                        {"id": "a4", "answer_checked": 1},
                    ],
                }
            ],
        },
    )

    result = create.office_create_questions(
        "paper-1",
        [
            SingleChoiceQuestionData(
                title="测试题",
                standard_answers=[StandardAnswer(seqno="A", standard_answer="B")],
                description="desc",
                score=5,
                answer_items=[
                    AnswerItem(seqno="A", context="选项A"),
                    AnswerItem(seqno="B", context="选项B"),
                    AnswerItem(seqno="C", context="选项C"),
                    AnswerItem(seqno="D", context="选项D"),
                ],
            )
        ],
    )

    assert not result["success"]
    assert "结果校验失败" in str(result["message"])


def test_query_paper_defaults_to_summary(monkeypatch):
    monkeypatch.setattr(
        query,
        "get_json",
        lambda *args, **kwargs: {
            "success": True,
            "data": {
                "random": 1,
                "question_random": 1,
                "id": "paper-id",
                "paper_id": "paper-id",
                "title": "Linux基础练习",
                "updated_at": "2026-03-09T00:00:00Z",
                "questions": [
                    {
                        "id": "question-1",
                        "title": '{"blocks":[{"text":"题目1"}],"entityMap":{}}',
                        "description": "desc",
                        "type": 1,
                        "score": 5,
                        "required": 2,
                        "answer_items_sort": "",
                        "answer_items": [
                            {"id": "a1", "value": "A", "answer_checked": 2},
                            {"id": "a2", "value": "B", "answer_checked": 1},
                        ],
                    }
                ],
            },
        },
    )

    result = query.query_paper("group-1", "paper-1")

    assert result["success"]
    assert result["message"] == "试卷摘要查询成功"
    assert result["data"]["question_count"] == 1
    assert result["data"]["total_score"] == 5
    assert result["data"]["type_counts"] == {"单选题": 1}
    assert result["data"]["questions"][0] == {
        "id": "question-1",
        "title": "题目1",
        "type": "单选题",
        "score": 5,
        "required": "是",
        "option_count": 2,
    }


def test_configure_paper_basics_updates_required_and_randomization(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        update,
        "_fetch_paper_edit_buffer",
        lambda group_id, paper_id: {
            "questions": [{"id": "q1"}, {"id": "q2"}],
        },
    )
    monkeypatch.setattr(
        update,
        "_update_question_required",
        lambda question_id, required: None,
    )
    monkeypatch.setattr(
        update,
        "_update_paper_settings",
        lambda **kwargs: captured.update(kwargs),
    )

    result = update.configure_paper_basics(
        group_id="group-1",
        paper_id="paper-1",
        required=2,
        question_shuffle=1,
        option_shuffle=2,
        question_score_type=1,
    )

    assert result["success"]
    assert result["data"]["required_updated"] == 2
    assert result["data"]["required_failed_question_ids"] == []
    assert result["data"]["randomization_updated"] is True
    assert result["data"]["required"] == "是"
    assert result["data"]["question_shuffle"] == "关闭"
    assert result["data"]["option_shuffle"] == "开启"
    assert result["data"]["question_score_type"] == "严格计分"
    assert captured == {
        "paper_id": "paper-1",
        "question_shuffle": 1,
        "option_shuffle": 2,
        "question_score_type": 1,
    }
