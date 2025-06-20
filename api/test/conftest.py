import pytest
from app.http.app import app as _app
from internal.extension.database_extension import db as _db
from sqlalchemy.orm import sessionmaker,scoped_session
@pytest.fixture
def app():
    """获取Flask应用并返回"""
    _app.config["TESTING"] = True
    return _app

@pytest.fixture
def client(app):
    """获取Flask应用的测试应用，并返回"""
    with app.test_client() as client:
        yield client

@pytest.fixture
def db(app):
    """创建一个临时的数据库会话 当测试结束的时候回滚整个事务 从而实现测试与数据实际隔离"""
    with app.app_context():
        # 1.获取数据库链接并创建事务
        connection = _db.engine.connect()
        transaction = connection.begin()

        # 2.创建一个临时数据库会话
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)
        _db.session = session

        # 3.抛出数据库实例
        yield _db

        # 4.回退数据库并关闭链接 随后清除会话
        transaction.rollback()
        connection.close()
        session.remove()

