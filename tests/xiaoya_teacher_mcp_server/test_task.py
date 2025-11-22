from dotenv import load_dotenv, find_dotenv
from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.task import query as task_query

load_dotenv(find_dotenv())


def _latest_group_and_task():
    groups = group_query.query_teacher_groups().get("data") or []
    assert groups, "未找到课程组"
    group_id = groups[0]["group_id"]

    tasks = task_query.query_group_tasks(group_id).get("data") or []
    assert tasks, "未找到任务"
    return group_id, tasks[-1]


def test_query_tasks():
    group_id, _ = _latest_group_and_task()
    result = task_query.query_group_tasks(group_id)
    assert result.get("success")
    print(f"\n✓ 查询任务成功, 共 {len(result.get('data', []))} 个任务")


def test_query_test_result_and_student_paper():
    group_id, task = _latest_group_and_task()
    test_result = task_query.query_test_result(group_id, task["paper_id"], task["publish_id"])
    assert test_result.get("success")
    data = test_result.get("data", {})
    records = data.get("answer_records") or []
    print(f"\n1. ✓ 查询测试结果成功, 共 {len(records)} 条记录")

    if not records:
        return

    record = records[-1]
    paper_result = task_query.query_preview_student_paper(
        group_id,
        task["paper_id"],
        data.get("mark_mode_id"),
        task["publish_id"],
        record["record_id"],
    )
    assert paper_result.get("success")
    print(f"2. ✓ 查询学生答卷成功: {record.get('nickname')} ({record.get('class_name')})")
