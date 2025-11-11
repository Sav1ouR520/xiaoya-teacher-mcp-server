from dotenv import load_dotenv, find_dotenv
from xiaoya_teacher_mcp_server.tools.group import query as group_query
from xiaoya_teacher_mcp_server.tools.task import query as task_query

load_dotenv(find_dotenv())


def _get_group_and_task() -> tuple:
    """获取group_id和最新任务信息"""
    group_id = group_query.query_teacher_groups()["data"][0]["group_id"]
    tasks = task_query.query_group_tasks(group_id)["data"]
    assert tasks, "未找到任务"
    return group_id, tasks[-1]


def test_query_tasks():
    """测试查询课程组任务"""
    group_id, task = _get_group_and_task()
    result = task_query.query_group_tasks(group_id)
    assert result["success"]
    print(f"\n✓ 查询任务成功,共{len(result['data'])}个任务")


def test_query_test_result_and_student_paper():
    """测试查询测试结果和学生答卷"""
    group_id, task = _get_group_and_task()
    test_result = task_query.query_test_result(
        group_id, task["paper_id"], task["publish_id"]
    )
    assert test_result["success"]
    print(
        f"\n1. ✓ 查询测试结果成功,共{len(test_result['data']['answer_records'])}条记录"
    )

    if test_result["data"]["answer_records"]:
        record = test_result["data"]["answer_records"][-1]
        paper_result = task_query.query_preview_student_paper(
            group_id,
            task["paper_id"],
            test_result["data"]["mark_mode_id"],
            task["publish_id"],
            record["record_id"],
        )
        assert paper_result["success"]
        print(f"2. ✓ 查询学生答卷成功: {record['nickname']} ({record['class_name']})")
