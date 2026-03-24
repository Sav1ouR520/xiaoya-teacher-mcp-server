from __future__ import annotations

from enum import IntEnum


class ResourceType(IntEnum):
    """资源类型枚举"""

    FOLDER = 1
    NOTE = 2
    MINDMAP = 3
    FILE = 6
    ASSIGNMENT = 7
    VIDEO = 9
    TEACHING_DESIGN = 11

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "文件夹",
            2: "笔记",
            3: "思维导图",
            6: "文件",
            7: "作业",
            9: "视频",
            11: "教学设计",
        }.get(value, default)


class DownloadType(IntEnum):
    """下载属性枚举"""

    DISABLED = 1
    ENABLED = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "不可下载",
            2: "可下载",
        }.get(value, default)


class VisibilityType(IntEnum):
    """资源可见性枚举"""

    HIDDEN = 1
    VISIBLE = 2

    @staticmethod
    def get(value: int, default: str = "unknown") -> str:
        return {
            1: "学生不可见",
            2: "学生可见",
        }.get(value, default)

