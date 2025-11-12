from dotenv import load_dotenv, find_dotenv
from xiaoya_teacher_mcp_server.tools.group import query

load_dotenv(find_dotenv())


def test_query_groups_and_classes():
    """测试查询教师课程组和班级"""
    groups_result = query.query_teacher_groups()
    assert groups_result["success"]
    print(f"\n1. ✓ 查询课程组成功,共{len(groups_result['data'])}个")

    group_id = groups_result["data"][0]["group_id"]
    classes_result = query.query_group_classes(group_id)
    assert classes_result["success"]
    print(f"2. ✓ 查询班级成功,共{len(classes_result['data'])}个")


def test_query_attendance():
    """测试查询签到记录"""
    groups_result = query.query_teacher_groups()
    assert groups_result["success"]
    group_id = groups_result["data"][0]["group_id"]

    records_result = query.query_attendance_records(group_id)
    assert records_result["success"]
    print(f"\n1. ✓ 查询签到记录成功,共{len(records_result['data'])}条")

    if records_result["data"]:
        record = records_result["data"][-1]
        students_result = query.query_single_attendance_students(
            group_id, record["id"], record["course_id"]
        )
        assert students_result["success"]
        print(f"2. ✓ 查询单次签到学生成功,共{len(students_result['data'])}人")
