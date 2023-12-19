from sqlalchemy import inspect

from common.database import engine, DB_TABLE_PREFIX
from main import app
from .. import models
from ..admin.admin_router import admin_router
from ..plugin_config import module_name
from plugin.demo_todo import plugin_config

# install
if not inspect(engine).has_table(DB_TABLE_PREFIX + "todos"):
    models.Base.metadata.create_all(bind=engine)


# 플러그인의 admin 라우터를 등록한다.
# 관리자는 /admin 으로 시작해야 접근권한이 보호된다.
def register_admin_router():
    app.include_router(admin_router, prefix="/admin", tags=[module_name])


def register_admin_menu():
    """관리자 메뉴 등록
    plugin_config.py 에서 관리자메뉴 설정
    """
    return getattr(plugin_config, "admin_menu", [])
