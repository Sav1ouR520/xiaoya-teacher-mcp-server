"""统一响应格式工具"""

from datetime import datetime, timezone
from typing import Any, Dict

TIME_FIELDS = {
    "start_time",
    "end_time",
    "register_time",
    "created_at",
    "updated_at",
    "answer_time",
}


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone()
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_time_value(value: Any) -> Any:
    if value in (None, ""):
        return value

    try:
        if isinstance(value, (int, float)):
            timestamp = float(value)
        elif isinstance(value, str) and value.isdigit():
            timestamp = float(value)
        elif isinstance(value, str):
            iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value
            return _format_datetime(datetime.fromisoformat(iso_value))
        else:
            return value

        if timestamp > 1e11:
            timestamp /= 1000
        return _format_datetime(datetime.fromtimestamp(timestamp, tz=timezone.utc))
    except (OverflowError, TypeError, ValueError):
        return value


def normalize_time_fields(data: Any) -> Any:
    """递归格式化常见时间字段,避免盲目做固定时区偏移。"""
    if isinstance(data, dict):
        return {
            key: _normalize_time_value(value)
            if key in TIME_FIELDS
            else normalize_time_fields(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [normalize_time_fields(item) for item in data]
    return data


class ResponseUtil:
    """用于创建标准化API响应的工具类"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
        """创建成功响应"""

        return {
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": normalize_time_fields(data) if data is not None else data,
            "success": True,
        }

    @staticmethod
    def error(
        message: str = "操作失败",
        exception: Exception = None,
        *,
        data: Any = None,
    ) -> Dict[str, Any]:
        """创建错误响应,仅返回必要错误信息,避免泄露内部堆栈。"""
        if exception is not None and isinstance(exception, Exception):
            detail = str(exception).strip()
            error_type = type(exception).__name__
            if detail:
                message = f"{message}: {error_type}: {detail}"
            else:
                message = f"{message}: {error_type}"

        return {
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": normalize_time_fields(data) if data is not None else data,
            "success": False,
        }
