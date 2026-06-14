import os
import ipaddress
import socket
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.orm import scoped_session, sessionmaker

# 在导入应用前关闭外部 tracing，避免初始化阶段产生联网副作用。
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ.pop("LANGCHAIN_API_KEY", None)
os.environ.pop("LANGSMITH_API_KEY", None)


@pytest.fixture(autouse=True)
def _disable_external_tracing(monkeypatch):
    """关闭外部 tracing，上报链路会干扰离线测试且没有业务价值。"""
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    yield


def _build_fake_getaddrinfo_result(ip: str, port: int | None):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    if family == socket.AF_INET6:
        sockaddr = (ip, port or 0, 0, 0)
    else:
        sockaddr = (ip, port or 0)
    return [(family, socket.SOCK_STREAM, 6, "", sockaddr)]


@pytest.fixture(autouse=True)
def _stable_safe_http_dns(monkeypatch):
    """
    为安全 HTTP 校验提供稳定的离线 DNS 行为。

    说明：
    - 已知的测试域名固定到公网 IP，避免依赖真实 DNS。
    - localhost / loopback 保持为回环地址，便于相关拦截测试。
    - 未知域名默认解析到公网 IP，避免 CI 因外网 DNS 抖动失败。
    """

    public_ip = "93.184.216.34"
    loopback_ip = "127.0.0.1"
    private_ip = "10.0.0.1"

    def _fake_getaddrinfo(host, port, *args, **kwargs):
        normalized = str(host or "").strip().lower().rstrip(".")
        mapping = {
            "localhost": loopback_ip,
            "private.example.com": private_ip,
            "rebound.example.com": public_ip,
            "api.example.com": public_ip,
            "example.com": public_ip,
            "a.com": public_ip,
            "baidu.com": public_ip,
            "kolors.example": public_ip,
            "qwen.example": public_ip,
            "cos.example.com": public_ip,
            "mcp.example.com": public_ip,
            "img.example.com": public_ip,
            "temporary.example.com": public_ip,
            "sandbox.example.com": public_ip,
            "ui.example.com": public_ip,
        }

        if normalized.endswith(".localhost"):
            ip = loopback_ip
        elif normalized in mapping:
            ip = mapping[normalized]
        else:
            try:
                ip = str(ipaddress.ip_address(normalized))
            except ValueError:
                ip = public_ip

        return _build_fake_getaddrinfo_result(ip, port)

    monkeypatch.setattr("internal.lib.safe_http_client.socket.getaddrinfo", _fake_getaddrinfo)
    yield


@pytest.fixture(autouse=True)
def _reset_socketio_state():
    """每个测试都从干净的 Socket.IO 全局状态开始，避免模块级单例串扰。"""
    from internal.extension import socketio_extension

    socketio_extension.socketio = None
    yield
    socketio_extension.socketio = None


@pytest.fixture
def app():
    """返回 Flask 应用，并开启测试模式。"""
    from app.http.app import app as _app

    _app.config["TESTING"] = True
    # 测试阶段关闭鉴权，聚焦参数校验与 handler/service 逻辑。
    _app.config["LOGIN_DISABLED"] = True
    _app.config["WTF_CSRF_ENABLED"] = False
    return _app


@pytest.fixture
def client(app):
    """返回 Flask 测试客户端。"""
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def db(app):
    """每个测试使用独立事务，结束后统一回滚，确保不污染真实数据。"""
    from internal.extension.database_extension import db as _db

    with app.app_context():
        # 1) 基于原始连接开启事务；2) 复用该连接构造测试会话。
        connection = _db.engine.connect()
        transaction = connection.begin()
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)
        _db.session = session

        yield _db

        # 无论测试成功/失败都回滚，保证数据库状态不被测试持久化。
        transaction.rollback()
        connection.close()
        session.remove()


@pytest.fixture(autouse=True)
def _rollback_http_tests(request):
    """所有使用 `client` 夹具的 HTTP 测试自动绑定事务回滚。"""
    # 说明：部分矩阵测试使用自定义 http_client 且完整 mock service，不依赖数据库连接。
    if "client" in request.fixturenames:
        request.getfixturevalue("db")
    yield


@pytest.fixture
def login_account(monkeypatch):
    """兼容旧测试的登录态夹具，提供稳定 current_user 桩。"""
    account = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        is_authenticated=True,
        email="tester@example.com",
        name="tester",
    )
    monkeypatch.setattr("internal.handler.app_handler.current_user", account)
    return account
