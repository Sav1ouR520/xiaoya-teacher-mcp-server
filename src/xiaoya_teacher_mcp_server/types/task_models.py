from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, Field

from .. import field_descriptions as desc


class AttendanceStatus(IntEnum):
    """签到状态枚举"""

    ATTENDANCE = 1
    ABSENT = 2
    LATE = 3
    EARLY_LEAVE = 4
    PERSONAL_LEAVE = 5
    SICK_LEAVE = 6
    OFFICIAL_LEAVE = 7
    OTHER = 8

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "签到",
            2: "旷课",
            3: "迟到",
            4: "早退",
            5: "事假",
            6: "病假",
            7: "公假",
            8: "其他",
        }.get(value, default)


class AttendanceUser(BaseModel):
    """签到用户信息"""

    register_user_id: str = Field(description=desc.REGISTER_USER_ID_DESC)
    status: AttendanceStatus = Field(description="签到状态")


class AnswerStatus(IntEnum):
    """答题状态枚举"""

    IN_PROGRESS = 1
    SUBMITTED = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "答题中",
            2: "已提交",
        }.get(value, default)
