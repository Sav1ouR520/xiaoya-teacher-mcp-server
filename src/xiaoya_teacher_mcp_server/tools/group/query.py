"""课程组查询 MCP 工具"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ... import field_descriptions as desc
from ...config import MAIN_URL, MCP
from ...types.task_models import AttendanceStatus
from ...utils.client import APIRequestError, expect_success, get_json, post_json
from ...utils.response import ResponseUtil
from ..resources import query as resource_query
from ..task import query as task_query


@MCP.tool()
def query_teacher_groups() -> dict:
    """查询教师的课程组"""
    try:
        data = expect_success(get_json(f"{MAIN_URL}/group/teacher/groups"))
        courses = [
            {
                **{key: item[key] for key in ["name", "teacher_names", "term_name", "department_name", "member_count", "start_time", "end_time"] if key in item},
                "group_id": item["id"],
            }
            for item in data
        ]
        return ResponseUtil.success(courses, "查询成功")
    except APIRequestError as e:
        return ResponseUtil.error("查询教师的课程组失败", e)


@MCP.tool()
def query_group_snapshot(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
) -> dict:
    """查询课程组总览快照"""
    try:
        groups_result = query_teacher_groups()
        if not groups_result["success"]:
            return groups_result
        group_data = next(
            (group for group in groups_result["data"] if group["group_id"] == str(group_id)),
            None,
        )
        if group_data is None:
            return ResponseUtil.error(f"未找到课程组: {group_id}")

        classes_result = query_group_classes(group_id)
        if not classes_result["success"]:
            return classes_result
        tasks_result = task_query.query_group_tasks(group_id, detail_level="summary")
        if not tasks_result["success"]:
            return tasks_result
        resources_result = resource_query.query_course_resources(group_id, detail_level="summary")
        if not resources_result["success"]:
            return resources_result
        attendance_result = query_attendance_records(group_id)
        if not attendance_result["success"]:
            return attendance_result

        recent_attendances = sorted(
            attendance_result["data"],
            key=lambda record: record.get("start_time", ""),
            reverse=True,
        )[:5]
        return ResponseUtil.success(
            {
                **group_data,
                "class_count": len(classes_result["data"]),
                "task_count": len(tasks_result["data"]),
                "resource_count": len(resources_result["data"]),
                "recent_attendance_count": len(recent_attendances),
                "recent_attendances": recent_attendances,
            },
            "课程组总览查询成功",
        )
    except (APIRequestError, ValueError) as e:
        return ResponseUtil.error("查询课程组总览失败", e)


@MCP.tool()
def query_attendance_records(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
) -> dict:
    """查询课程组的全部签到记录情况"""
    try:
        page_size = 50
        classes_result = query_group_classes(group_id)
        if not classes_result["success"]:
            return classes_result
        class_map = {
            course_class["class_id"]: course_class["class_name"]
            for course_class in classes_result["data"]
        }

        all_data = []
        current_page = 1
        while True:
            page_data = expect_success(post_json(
                f"{MAIN_URL}/register/group",
                payload={"group_id": str(group_id), "page": current_page, "page_size": page_size},
            ))
            registers = page_data["result"]["registers"]
            for record in registers:
                filtered_record = {
                    key: record[key]
                    for key in ["id", "start_time", "end_time", "class_id", "course_id", "register_count"]
                    if key in record
                }
                filtered_record["class_name"] = class_map.get(record["class_id"], "未知班级")
                all_data.append(filtered_record)

            if not registers:
                break
            total_register = page_data["total_register"]
            if total_register:
                total_pages = (total_register + page_size - 1) // page_size
                if current_page >= total_pages:
                    break
            elif len(registers) < page_size:
                break
            current_page += 1

        return ResponseUtil.success(all_data, "签到记录查询成功")
    except APIRequestError as e:
        return ResponseUtil.error("查询课程组的签到记录失败", e)


@MCP.tool()
def query_group_classes(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
) -> dict:
    """查询课程组的班级列表"""
    try:
        data = expect_success(get_json(f"{MAIN_URL}/group/class/list/{group_id}"))
        class_list = [
            {
                "class_id": course_class["class_id"],
                "class_name": course_class["class_name"],
                "member_count": course_class["member_count"],
            }
            for course_class in data
        ]
        return ResponseUtil.success(class_list, "班级列表查询成功")
    except APIRequestError as e:
        return ResponseUtil.error("查询课程组的班级列表失败", e)


@MCP.tool()
def query_single_attendance_students(
    group_id: Annotated[str, Field(description=desc.GROUP_ID_DESC)],
    register_id: Annotated[str, Field(description=desc.REGISTER_ID_DESC)],
    course_id: Annotated[str, Field(description=desc.COURSE_ID_FROM_ATTENDANCE_DESC)],
) -> dict:
    """查询单次签到的学生列表"""
    try:
        data = expect_success(post_json(
            f"{MAIN_URL}/register/one/student",
            payload={
                "register_id": str(register_id),
                "group_id": str(group_id),
                "course_id": str(course_id),
            },
        ))
        students = [
            {
                **{key: student[key] for key in ["nickname", "register_status", "register_time", "student_number", "user_id"]},
                "register_status": AttendanceStatus.get(student["register_status"], "未知"),
            }
            for student in data["result"]
        ]
        return ResponseUtil.success(students, "学生列表查询成功")
    except APIRequestError as e:
        return ResponseUtil.error("查询单次签到的学生列表失败", e)
