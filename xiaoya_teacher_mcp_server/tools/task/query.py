"""
任务查询模块

本模块为课程管理系统提供任务相关的查询功能,包括课程组任务列表、任务详情、学生答题情况等,供 MCP 工具调用.
"""

import json
import requests
from typing import Annotated
from pydantic import Field

from ..resources.query import query_course_resources
from ...types.types import AnswerChecked, AnswerStatus
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, create_headers, MCP


@MCP.tool()
def query_group_tasks(
    group_id: Annotated[str, Field(description="课程组id")],
) -> dict:
    """查询课程组发布的全部测试/考试/任务"""
    result = query_course_resources(group_id, "flat")
    if not result.get("success"):
        result["message"] = f"课程测试/考试/任务查询失败: {result['message']}"
        return result

    tasks = [resource for resource in result["data"] if resource.get("type") == 7]

    flattened_tasks = [
        {
            "name": task_folder["name"],
            "paper_id": task_folder["quote_id"],
            "start_time": link_task["start_time"],
            "end_time": link_task["end_time"],
            "publish_id": link_task["publish_id"],
        }
        for task_folder in tasks
        for link_task in task_folder["link_tasks"]
    ]

    return ResponseUtil.success(
        flattened_tasks, f"课程测试/考试/任务查询成功,共{len(flattened_tasks)}项"
    )


@MCP.tool()
def query_test_result(
    group_id: Annotated[str, Field(description="课程组id")],
    paper_id: Annotated[str, Field(description="试卷paper_id")],
    publish_id: Annotated[str, Field(description="发布id")],
) -> dict:
    """查询学生的测试/考试/任务的答题情况(包含mark_mode_id)"""
    try:
        response = requests.get(
            f"{MAIN_URL}/survey/course/queryStuAnswerList/v2",
            headers=create_headers(),
            params={
                "group_id": str(group_id),
                "paper_id": str(paper_id),
                "publish_id": str(publish_id),
            },
        ).json()

        if response.get("success"):
            processed_data = {}

            if "lost_members" in response["data"]:
                keep_keys_lost = [
                    "class_id",
                    "class_name",
                    "nickname",
                    "student_number",
                ]
                processed_data["lost_members"] = [
                    {key: member[key] for key in keep_keys_lost if key in member}
                    for member in response["data"]["lost_members"]
                ]

            if "answer_records" in response["data"]:
                processed_data["answer_records"] = [
                    {
                        "record_id": record["id"],
                        "actual_score": record["actual_score"],
                        "answer_time": record["answer_time"],
                        "created_at": record["created_at"],
                        "nickname": record["nickname"],
                        "student_number": record["student_number"],
                        "class_id": record["class_id"],
                        "class_name": record["class_name"],
                        "status": AnswerStatus.get(record["status"]),
                        "answer_rate": record.get("answer_rate", 0),
                    }
                    for record in response["data"]["answer_records"]
                ]
                processed_data["mark_mode_id"] = response["data"]["mark_mode"][
                    "mark_mode_id"
                ]
            return ResponseUtil.success(processed_data, "小测答题情况查询成功")
        else:
            return ResponseUtil.error(
                f"查询任务详情失败: {response.get('msg') or response.get('message', '未知错误')}"
            )
    except Exception as e:
        return ResponseUtil.error("查询任务详情时发生异常", e)


@MCP.tool()
def query_preview_student_paper(
    group_id: Annotated[str, Field(description="课程组id")],
    paper_id: Annotated[str, Field(description="试卷paper_id")],
    mark_mode_id: Annotated[str, Field(description="修改模式id")],
    publish_id: Annotated[str, Field(description="发布id")],
    record_id: Annotated[str, Field(description="答题记录id")],
) -> dict:
    """查询学生答题信息(部分id通过query_test_result获取)"""
    try:
        response = requests.get(
            f"{MAIN_URL}/survey/course/queryMarkRecord",
            headers=create_headers(),
            params={
                "group_id": str(group_id),
                "paper_id": str(paper_id),
                "publish_id": str(publish_id),
                "mark_mode_id": str(mark_mode_id),
                "answer_record_id": str(record_id),
            },
        ).json()
        if response.get("success"):

            def parse_text(text):
                try:
                    blocks = json.loads(text).get("blocks", [])
                    return (
                        "\n".join(block.get("text", "") for block in blocks)
                        if blocks
                        else text
                    )
                except Exception:
                    return text

            def parse_answer_items(answer_items, question_type):
                if question_type in [1, 2]:
                    return [
                        {
                            "id": item["id"],
                            "value": parse_text(item["value"]),
                            "answer": AnswerChecked.get(item["answer_checked"]),
                        }
                        for item in answer_items
                    ]
                elif question_type == 5:
                    return [
                        {
                            "id": item["id"],
                            "answer": AnswerChecked.get(item["answer_checked"]),
                        }
                        for item in answer_items
                    ]
                elif question_type == 4:
                    return [
                        {"id": item["id"], "answer": item["answer"]}
                        for item in answer_items
                    ]
                elif question_type == 10:
                    return [
                        {"id": item["id"], "answer": json.loads(item["answer"])}
                        for item in answer_items
                    ]

            record = response["data"]["answer_record"]
            questions = response["data"]["questions"]
            answer_map = {ans["question_id"]: ans for ans in record["answers"]}

            integrated_questions = []
            for q in questions:
                user_ans = answer_map[q["id"]]
                integrated_questions.append(
                    {
                        "id": q["id"],
                        "title": parse_text(q["title"]),
                        "description": parse_text(q["description"]),
                        "score": q["score"],
                        "options": parse_answer_items(
                            q["answer_items"], q.get("type", 1)
                        ),
                        "user_answer": parse_text(user_ans["answer"]),
                        "user_score": user_ans["score"],
                        "program_setting": q.get("program_setting", None),
                    }
                )

            return ResponseUtil.success(integrated_questions, "学生答题预览查询成功")
        else:
            return ResponseUtil.error(
                f"查询学生答题预览失败: {response.get('msg') or response.get('message', '未知错误')}"
            )
    except Exception as e:
        return ResponseUtil.error("查询学生答题预览时发生异常", e)
