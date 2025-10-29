"""
课程组查询MCP工具

此模块为课程管理系统中查询教学课程组、课程签到情况、课程班级信息等提供MCP工具.
"""

import requests
from typing import Annotated
from pydantic import Field

from ...types.types import AttendanceStatus
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, create_headers, MCP


@MCP.tool()
def query_teacher_groups() -> dict:
    """查询教师的课程组"""
    try:
        response = requests.get(
            f"{MAIN_URL}/group/teacher/groups", headers=create_headers()
        ).json()

        if response.get("success"):
            courses = [
                {
                    **{
                        key: item[key]
                        for key in [
                            "name",
                            "teacher_names",
                            "term_name",
                            "department_name",
                            "member_count",
                            "start_time",
                            "end_time",
                        ]
                        if key in item
                    },
                    "group_id": item["id"],
                }
                for item in response["data"]
            ]
            return ResponseUtil.success(courses, "查询成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("查询教师的课程组失败", e)


@MCP.tool()
def query_attendance_records(
    group_id: Annotated[str, Field(description="课程组id")],
) -> dict:
    """查询课程组的全部签到记录情况"""
    try:
        page, page_size = 1, 50

        classes_result = query_group_classes(group_id)
        class_map = {
            cls["class_id"]: cls["class_name"] for cls in classes_result["data"]
        }

        all_data = []
        current_page = page

        while True:
            response = requests.post(
                f"{MAIN_URL}/register/group",
                headers=create_headers(),
                json={
                    "group_id": str(group_id),
                    "page": current_page,
                    "page_size": page_size,
                },
            ).json()

            if not response.get("success"):
                return ResponseUtil.error(
                    response.get("msg") or response.get("message") or "未知错误"
                )

            keep_keys = [
                "id",
                "start_time",
                "end_time",
                "class_id",
                "course_id",
                "register_count",
            ]
            for record in response["data"]["result"]["registers"]:
                filtered_record = {
                    key: record[key] for key in keep_keys if key in record
                }
                filtered_record["class_name"] = class_map.get(
                    record["class_id"], "未知班级"
                )
                all_data.append(filtered_record)
            total_register = response["data"]["total_register"]
            if total_register:
                total_pages = (total_register + page_size - 1) // page_size
                if current_page >= total_pages:
                    break
            elif len(response["data"]["result"]["register"]) < page_size:
                break

            current_page += 1

        return ResponseUtil.success(all_data, "签到记录查询成功")
    except Exception as e:
        return ResponseUtil.error("查询课程组的签到记录失败", e)


@MCP.tool()
def query_group_classes(
    group_id: Annotated[str, Field(description="课程组id")],
) -> dict:
    """查询课程组的班级列表"""
    try:
        response = requests.get(
            f"{MAIN_URL}/group/class/list/{group_id}", headers=create_headers()
        ).json()
        if response.get("success"):
            class_list = [
                {
                    "class_id": c["class_id"],
                    "class_name": c["class_name"],
                    "member_count": c["member_count"],
                }
                for c in response["data"]
            ]
            return ResponseUtil.success(class_list, "班级列表查询成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("查询课程组的班级列表失败", e)


@MCP.tool()
def query_single_attendance_students(
    group_id: Annotated[str, Field(description="课程组id")],
    register_id: Annotated[str, Field(description="签到id")],
    course_id: Annotated[
        str,
        Field(description="课程id[query_attendance_records的course_id]"),
    ],
) -> dict:
    """查询单次签到的学生列表"""
    try:
        response = requests.post(
            f"{MAIN_URL}/register/one/student",
            headers=create_headers(),
            json={
                "register_id": str(register_id),
                "group_id": str(group_id),
                "course_id": str(course_id),
            },
        ).json()
        if response.get("success"):
            keep_keys = [
                "nickname",
                "register_status",
                "register_time",
                "student_number",
                "user_id",
            ]
            students = []
            for s in response["data"]["result"]:
                student = {key: s[key] for key in keep_keys}
                student["register_status"] = AttendanceStatus.get(
                    student["register_status"], "未知"
                )
                students.append(student)
            return ResponseUtil.success(students, "学生列表查询成功")
        else:
            return ResponseUtil.error(
                response.get("msg") or response.get("message") or "未知错误"
            )
    except Exception as e:
        return ResponseUtil.error("查询单次签到的学生列表失败", e)
