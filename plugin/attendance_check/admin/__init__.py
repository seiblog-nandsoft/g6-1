from common.database import engine
from main import app
from .. import models
from ..admin.admin_router import admin_router
from ..plugin_config import module_name, admin_router_prefix

# install
models.Base.metadata.create_all(bind=engine)


# 플러그인의 admin 라우터를 등록한다.
# 관리자는 /admin 으로 시작해야 접근권한이 보호된다.
def register_admin_router():
    app.include_router(admin_router, prefix="/admin", tags=[module_name])


def register_admin_menu():
    admin_menu = {
        f"{module_name}": [
            {
                "name": "플러그인 데모",
                "url": "",
                "permission": ""
            },
            {
                "id": module_name + "1",  # 메뉴 아이디
                "name": "출석부 추가",
                "url": f"{admin_router_prefix}/create",
            },
            {
                "id": module_name + "2",  # 메뉴 아이디
                "name": "출석부 보기",
                "url": f"{admin_router_prefix}/index",
            },
            {
                "id": module_name + "3",
                "name": "출석기록",
                "url": f"{admin_router_prefix}/history",
            }
        ]
    }
    return admin_menu
