import requests
from typing import Annotated, List
from pydantic import Field

from ...types.types import AttendanceStatus, AttendanceUser
from ...utils.response import ResponseUtil
from ...config import MAIN_URL, headers


# @MCP.tool()
def change_attendance_status(
    group_id: Annotated[str, Field(description="课程组id")],
    attendance_list: Annotated[
        List[AttendanceUser],
        Field(description="签到用户列表"),
    ],
    course_id: Annotated[str, Field(description="课程id")],
    register_id: Annotated[str, Field(description="签到id")],
) -> dict:
    """批量修改签到状态"""
    try:
        success_list, failed_list = [], []
        for item in attendance_list:
            try:
                resp = requests.post(
                    f"{MAIN_URL}/status/change",
                    headers=headers(),
                    json={
                        "group_id": str(group_id),
                        "register_user_id": str(item["register_user_id"]),
                        "status": str(item["status"]),
                        "course_id": str(course_id),
                        "register_id": str(register_id),
                    },
                ).json()
                if resp.get("success"):
                    item.update(
                        {
                            k: resp["data"][k]
                            for k in [
                                "user_id",
                                "register_status",
                                "created_at",
                                "update_at",
                            ]
                            if k in resp["data"]
                        }
                    )
                    item["status"] = AttendanceStatus.get(
                        resp["data"].get("register_status"), "未知"
                    )
                    success_list.append(item)
                else:
                    failed_list.append(
                        {
                            "register_user_id": item["register_user_id"],
                            "error": resp.get("msg")
                            or resp.get("message")
                            or "未知错误",
                        }
                    )
            except Exception as e:
                failed_list.append(
                    {
                        "register_user_id": item.get("register_user_id", "unknown"),
                        "error": str(e),
                    }
                )
        return ResponseUtil.success(
            {"success_list": success_list, "failed_list": failed_list},
            f"批量修改完成,成功: {len(success_list)} 个,失败: {len(failed_list)} 个",
        )
    except Exception as e:
        return ResponseUtil.error("批量修改签到状态失败", e)
