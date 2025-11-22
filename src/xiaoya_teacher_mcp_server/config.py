"""
MCP服务器配置模块

此模块包含API调用的基础配置.
支持两种认证方式:直接设置token或通过账号密码登录.
"""

import os
import random
import string
from contextlib import contextmanager
from contextvars import ContextVar
from threading import RLock
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP


# 认证相关状态统一管理
class AuthState:
    def __init__(self):
        self.request_token: ContextVar[Optional[str]] = ContextVar(
            "request_token", default=None
        )
        self.request_transport: ContextVar[str] = ContextVar(
            "request_transport", default="stdio"
        )
        self.request_account: ContextVar[Optional[str]] = ContextVar(
            "request_account", default=None
        )
        self.request_password: ContextVar[Optional[str]] = ContextVar(
            "request_password", default=None
        )
        self.account_tokens: dict[str, str] = {}
        self.account_tokens_lock = RLock()
        self.cached_token: Optional[str] = None
        self.is_initialized: bool = False


auth_state = AuthState()


# API基础配置
MAIN_URL = "https://fzrjxy.ai-augmented.com/api/jx-iresource"
DOWNLOAD_URL = "https://fzrjxy.ai-augmented.com/api/jx-oresource"

# 全局MCP服务器实例 - 所有模块共享
MCP = FastMCP("xiaoya-teacher-mcp-server")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Content-Type": "application/json;charset=UTF-8",
}


def _normalize_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    token = token.strip()
    return token and (token if token.startswith("Bearer ") else "Bearer " + token)


def resolve_request_token(
    authorization: Optional[str] = None,
    account: Optional[str] = None,
    password: Optional[str] = None,
) -> Optional[str]:
    if authorization:
        return _normalize_token(authorization)
    if account:
        with auth_state.account_tokens_lock:
            cached = auth_state.account_tokens.get(account)
        if cached:
            return cached
        if not password:
            return None
        token = login(account, password)
        norm = _normalize_token(token)
        if norm:
            with auth_state.account_tokens_lock:
                auth_state.account_tokens[account] = norm
        return norm
    return None


@contextmanager
def request_context(
    *,
    transport: str = "stdio",
    authorization: Optional[str] = None,
    account: Optional[str] = None,
    password: Optional[str] = None,
):
    token = (
        None
        if transport == "stdio"
        else resolve_request_token(authorization, account, password)
    )
    ts_scope = auth_state.request_transport.set(transport)
    tk_scope = auth_state.request_token.set(token)
    acc_scope = auth_state.request_account.set(account)
    pwd_scope = auth_state.request_password.set(password)
    try:
        yield
    finally:
        auth_state.request_transport.reset(ts_scope)
        auth_state.request_token.reset(tk_scope)
        auth_state.request_account.reset(acc_scope)
        auth_state.request_password.reset(pwd_scope)


def generate_random_state(length: int = 6) -> str:
    """生成随机state字符串,由数字和字母组成"""
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def headers() -> dict:
    transport = auth_state.request_transport.get()
    if transport == "stdio":
        if not auth_state.is_initialized:
            initialize_auth()
        if auth_state.cached_token:
            return HEADERS | {"Authorization": auth_state.cached_token}
        raise ValueError("stdio 认证未初始化")
    token = auth_state.request_token.get()
    if token:
        return HEADERS | {"Authorization": token}
    raise ValueError(
        f"{transport} 缺少认证(Authorization 或 x-xiaoya-account/x-xiaoya-password)"
    )


def initialize_auth() -> None:
    if auth_state.cached_token:
        return
    token = os.getenv("XIAOYA_AUTH_TOKEN")
    if not token:
        acc, pwd = os.getenv("XIAOYA_ACCOUNT"), os.getenv("XIAOYA_PASSWORD")
        if not (acc and pwd):
            raise ValueError(
                "缺少 stdio 认证环境变量: 设置 XIAOYA_AUTH_TOKEN 或 (XIAOYA_ACCOUNT + XIAOYA_PASSWORD)"
            )
        token = login(acc, pwd)
    auth_state.cached_token = _normalize_token(token)
    if not auth_state.cached_token:
        raise ValueError("认证初始化失败, 无效 token")
    auth_state.is_initialized = True
    print("认证初始化成功")


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
