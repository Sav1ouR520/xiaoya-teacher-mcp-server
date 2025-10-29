"""
响应工具模块

此模块为所有MCP工具提供统一的响应格式.
所有API响应都遵循标准格式:{message, timestamp, data, success}
"""

from datetime import datetime, timedelta
from typing import Any, Dict


def adjust_time_fields(data: Any) -> Any:
    """递归调整数据中的时间字段,直接转换时区+8小时"""
    time_fields = {
        "start_time",
        "end_time",
        "register_time",
        "created_at",
        "updated_at",
        "answer_time",
    }

    def adjust_time(value):
        if not value:
            return value
        try:
            if isinstance(value, str) and value.isdigit():
                timestamp_seconds = int(value) / 1000
                parsed_time = datetime.fromtimestamp(timestamp_seconds)
            else:
                parsed_time = datetime.fromisoformat(value.rstrip("Z"))
            adjusted_time = parsed_time + timedelta(hours=8)
            return adjusted_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return value

    if isinstance(data, dict):
        return {
            key: adjust_time(value) if key in time_fields else adjust_time_fields(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [adjust_time_fields(item) for item in data]
    else:
        return data


class ResponseUtil:
    """用于创建标准化API响应的工具类"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
        """创建成功响应"""

        return {
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": adjust_time_fields(data) if data is not None else data,
            "success": True,
        }

    @staticmethod
    def error(message: str = "操作失败", exception: Exception = None) -> Dict[str, Any]:
        """创建错误响应 - 支持多个traceback"""
        if exception is not None and isinstance(exception, Exception):
            import traceback

            error_chain = []
            current = exception
            while current is not None:
                tb_lines = traceback.format_exception(
                    type(current), current, current.__traceback__
                )
                simplified_tb = []
                for line in tb_lines:
                    for split_line in line.split("\n"):
                        if not split_line:
                            continue
                        if "xiaoya_teacher_mcp_server" in split_line:
                            idx = split_line.find("xiaoya_teacher_mcp_server")
                            simplified_tb.append(split_line[idx:])
                        else:
                            simplified_tb.append(split_line)

                error_chain.append(
                    {
                        "type": type(current).__name__,
                        "message": str(current),
                        "traceback": simplified_tb,
                    }
                )
                current = getattr(current, "__cause__", None) or getattr(
                    current, "__context__", None
                )

            message = {
                "type": type(exception).__name__,
                "message": str(exception),
                "exception": error_chain,
            }

        return {
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": None,
            "success": False,
        }
