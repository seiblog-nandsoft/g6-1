import os


# module_name - 플러그인 폴더 이름과 동일
module_name = os.path.basename(os.path.dirname(os.path.realpath(__file__)))

router_prefix = "attendance"
admin_router_prefix = router_prefix
