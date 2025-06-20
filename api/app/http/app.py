import dotenv
from flask_migrate import Migrate
from config import Config
from internal.router import Router
from internal.server import Http
from pkg.sqlalchemy import SQLAlchemy
from flask_weaviate import FlaskWeaviate
from .module import injector
from flask_login import LoginManager
from internal.middleware import Middleware
# 将env加载到环境变量中
dotenv.load_dotenv()

conf = Config()

app = Http(
    __name__,
    conf=conf,
    db=injector.get(SQLAlchemy),
    weaviate=injector.get(FlaskWeaviate),
    migrate=injector.get(Migrate),
    login_manager=injector.get(LoginManager),
    middleware=injector.get(Middleware),
    router=injector.get(Router),
)
celery = app.extensions['celery']

if __name__ == "__main__":
    app.run(debug=True, port=5001)

