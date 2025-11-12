"""
MCP服务器配置模块

此模块包含API调用的基础配置.
支持两种认证方式:直接设置token或通过账号密码登录.
"""

import os
import random
import string
from typing import Optional
from mcp.server.fastmcp import FastMCP
import requests

# 全局缓存变量
_cached_token: Optional[str] = None

# 是否为初始化完成
_is_initialized: bool = False


# API基础配置
MAIN_URL = "https://fzrjxy.ai-augmented.com/api/jx-iresource"
DOWNLOAD_URL = "https://fzrjxy.ai-augmented.com/api/jx-oresource"

# 全局MCP服务器实例 - 所有模块共享
MCP = FastMCP("xiaoya-teacher-mcp-server")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Content-Type": "application/json;charset=UTF-8",
}


def generate_random_state(length: int = 6) -> str:
    """生成随机state字符串,由数字和字母组成"""
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def headers() -> dict:
    """创建HTTP请求头,仅使用已初始化的认证信息"""
    global _cached_token, _is_initialized
    if not _is_initialized:
        initialize_auth()
        _is_initialized = True
    if _cached_token:
        return HEADERS | {"Authorization": _cached_token}
    raise ValueError("认证未初始化")


def initialize_auth() -> None:
    """在服务器启动阶段初始化认证信息"""
    global _cached_token, _is_initialized
    if _cached_token:
        return

    _is_initialized = True

    token = os.getenv("XIAOYA_AUTH_TOKEN")
    if token:
        _cached_token = token if token.startswith("Bearer ") else "Bearer " + token
    else:
        account, password = (
            os.getenv("XIAOYA_ACCOUNT"),
            os.getenv("XIAOYA_PASSWORD"),
        )
        if account and password:
            _cached_token = login(account, password)
        else:
            raise ValueError(
                "未配置认证信息. 请设置环境变量:\n"
                "1. XIAOYA_AUTH_TOKEN 或\n"
                "2. XIAOYA_ACCOUNT 和 XIAOYA_PASSWORD"
            )

    if _cached_token:
        print(f"认证初始化成功: {_cached_token}")
    else:
        raise ValueError("认证初始化失败: 未获取到有效的认证令牌")


def login(account: str, password: str) -> Optional[str]:
    """通过账号密码登录获取认证令牌"""
    try:
        session = requests.session()

        # 登录数据
        login_data = {
            "account": account,
            "password": password,
            "schoolId": "ed965396-cdeb-4d5c-8ff6-dc1f92fe5e2c",
            "clientId": "xy_client_fzrjxy",
            "state": generate_random_state(),
            "redirectUri": "https://fzrjxy.ai-augmented.com/api/jw-starcmooc/user/authorCallback",
            "weekNoLoginStatus": False,
        }

        # 执行登录流程
        urls = [
            (
                "https://infra.ai-augmented.com/api/auth/login/loginByMobileOrAccount",
                "post",
                login_data,
            ),
            ("https://infra.ai-augmented.com/api/auth/login/listAccounts", "get", None),
        ]

        accounts_response = None
        for url, method, data in urls:
            response = getattr(session, method)(
                url, **({"json": data} if data else {}), headers=HEADERS
            )
            response.raise_for_status()
            if "listAccounts" in url:
                accounts_response = response.json()

        # 选择第一个账号
        accounts = accounts_response.get("data", {}).get("accounts", [])
        if not accounts:
            raise ValueError("未找到可用的账号")

        account_id = accounts[0]["id"]

        # 完成认证流程
        final_urls = [
            (
                "https://infra.ai-augmented.com/api/auth/login/bySelectAccount",
                {"xyAccountId": account_id},
            ),
            (
                "https://infra.ai-augmented.com/api/auth/oauth/onAccountAuthRedirect",
                None,
            ),
        ]

        for url, data in final_urls:
            method = "post" if data else "get"
            getattr(session, method)(
                url, **({"json": data} if data else {}), headers=HEADERS
            ).raise_for_status()

        return "Bearer " + session.cookies.get("FS-prd-access-token")

    except Exception as e:
        print(f"登录失败: {str(e)}")
        return None
