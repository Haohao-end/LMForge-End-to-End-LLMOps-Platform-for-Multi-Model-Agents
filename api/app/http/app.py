import logging
import os

from flask_migrate import Migrate
from flask_mail import Mail
from config import Config
from internal.router import Router
from internal.server import Http
from internal.service import AppService, SkillService
from pkg.sqlalchemy import SQLAlchemy
from pkg.env_loader import load_project_env
from flask_weaviate import FlaskWeaviate
from .module import injector
from flask_login import LoginManager
from internal.middleware import Middleware

load_project_env()


conf = Config()

app = Http(
    __name__,
    conf=conf,
    db=injector.get(SQLAlchemy),
    weaviate=injector.get(FlaskWeaviate),
    migrate=injector.get(Migrate),
    login_manager=injector.get(LoginManager),
    mail=injector.get(Mail),
    middleware=injector.get(Middleware),
    router=injector.get(Router),
)


def _should_sync_skill_catalog_on_startup() -> bool:
    mode = os.getenv("MODE", "api")
    enabled = os.getenv("SKILL_CATALOG_SYNC_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    return mode != "celery" and enabled


with app.app_context():
    if _should_sync_skill_catalog_on_startup():
        try:
            synced_count = injector.get(SkillService).ensure_local_catalog_synced()
            logging.info("启动时同步技能目录完成，共同步 %s 个技能包", synced_count)
        except Exception:
            logging.exception("启动时同步技能目录失败")

    assistant_mcp_bindings = app.config.get("ASSISTANT_MCP_BINDINGS", [])
    if isinstance(assistant_mcp_bindings, list) and assistant_mcp_bindings:
        try:
            injector.get(AppService).prewarm_assistant_mcp_tool_snapshots()
        except Exception:
            logging.exception("启动时预热首页助手 MCP 快照失败")

celery = app.extensions['celery']

if __name__ == "__main__":
    app.run(debug=True, port=5001)
