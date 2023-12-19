from datetime import datetime

from fastapi import APIRouter
from fastapi.params import Depends, Form
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from admin.admin_config import get_admin_plugin_menus
from common.database import db_session
from lib.common import ADMIN_TEMPLATES_DIR, get_member_id_select, get_skin_select, get_editor_select, get_selected, \
    get_member_level_select, option_array_checked, get_admin_menus, generate_token, get_client_ip, AlertException, \
    default_if_none, validate_token, get_paging, subject_sort_link
from lib.plugin.service import get_all_plugin_module_names, PLUGIN_DIR
from ..models import AttendanceConfig, AttendanceHistory
from ..plugin_config import module_name, router_prefix, admin_router_prefix

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[PLUGIN_DIR, PLUGIN_TEMPLATES_DIR, ADMIN_TEMPLATES_DIR])
templates.env.globals["getattr"] = getattr
templates.env.globals["get_member_id_select"] = get_member_id_select
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_editor_select"] = get_editor_select
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals["option_array_checked"] = option_array_checked
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["generate_token"] = generate_token
templates.env.globals["get_client_ip"] = get_client_ip
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["subject_sort_link"] = subject_sort_link

admin_router = APIRouter(prefix=f'/{admin_router_prefix}', tags=[f'{router_prefix}_admin'])


@admin_router.get("/index")
async def set_config(
        request: Request,
        db: db_session
):
    request.session["menu_key"] = module_name

    attendance_configs = db.scalars(select(AttendanceConfig)).all()
    total_count = db.scalar(select(func.count(AttendanceConfig.id)))

    return templates.TemplateResponse(
        "admin/config.html", {
            "request": request,
            "total_count": total_count,
            "attendance_configs": attendance_configs,
            "paging": get_paging(request, request.state.page, total_count),
        })


@admin_router.get("/edit/{id}")
async def edit_attendance_config(
        request: Request,
        id: int,
        db: db_session
):
    """출석판 설정 수정"""
    request.session["menu_key"] = module_name

    attendance_config = db.scalar(select(AttendanceConfig).where(AttendanceConfig.id == id))

    if attendance_config is None:
        raise AlertException("출석판 설정이 없습니다")

    return templates.TemplateResponse(
        "admin/create.html", {
            "request": request,
            "attendance_config": attendance_config,
        })


@admin_router.post("/edit/{id}", dependencies=[Depends(validate_token)])
async def edit_attendance_config(
        request: Request,
        id: int,
        db: db_session,
        title: str = Form(default=""),
        start_date: str = Form(...),
        end_date: str = Form(...),
        point: int = Form(...),
):
    """출석판 설정 수정"""
    request.session["menu_key"] = module_name

    attendance_config = db.scalar(select(AttendanceConfig).where(AttendanceConfig.id == id))

    if attendance_config is None:
        raise AlertException("출석판가 없습니다")

    try:
        start_date = datetime.fromisoformat(start_date)
    except ValueError:
        start_date = datetime.now()

    try:
        end_date = datetime.fromisoformat(end_date)
    except ValueError:
        raise AlertException("종료일 날짜 형식이 잘못되었습니다")

    if start_date > end_date:
        raise AlertException("종료일이 시작일보다 빠릅니다")

    # 유효성 검사 끝

    attendance_config.title = title
    attendance_config.start_date = start_date
    attendance_config.end_date = end_date
    attendance_config.point = point

    db.commit()

    return RedirectResponse(f"/admin/attendance/{id}", status_code=302)


@admin_router.get("/create")
async def edit_attendance_config(
        request: Request,
):
    """출석판 설정 수정"""
    request.session["menu_key"] = module_name

    return templates.TemplateResponse(
        "admin/create.html", {
            "request": request,
            "attendance_config": AttendanceConfig()
        })


@admin_router.post("/create", dependencies=[Depends(validate_token)])
async def save_attendance_config(
        request: Request,
        db: db_session,
        title: str = Form(default=""),
        start_date: str = Form(...),
        end_date: str = Form(...),
        point: int = Form(...),
):
    """출석판 설정 저장"""
    try:
        start_date = datetime.fromisoformat(start_date)
    except ValueError:
        start_date = datetime.now()

    try:
        end_date = datetime.fromisoformat(end_date)
    except ValueError:
        raise AlertException("종료일 날짜 형식이 잘못되었습니다")

    if start_date > end_date:
        raise AlertException("종료일이 시작일보다 빠릅니다")

    # 유효성 검사 끝

    attendance_config = AttendanceConfig(
        title=title,
        start_date=start_date,
        end_date=end_date,
        point=point
    )

    db.add(attendance_config)
    db.commit()

    return RedirectResponse("/admin/attendance/index", status_code=302)


@admin_router.get("/history")
async def show_attendance_history(
        request: Request,
        db: db_session,
        page: int = 1,
):
    request.session["menu_key"] = module_name
    request.state.page = request.state.page if request.state.page else 1

    page_per_rows = request.state.config.cf_page_rows
    offset = (request.state.page - 1) * page_per_rows

    request.state.sfl = request.state.sfl if request.state.sfl else ''
    column = getattr(AttendanceHistory, request.state.sfl, None) or getattr(AttendanceConfig, request.state.sfl, None)

    filters = []
    if request.state.stx:
        filters.append(column == f'{request.state.stx}')

    attendance_histories = (db.scalars(select(AttendanceHistory, AttendanceConfig)
                                       .join(AttendanceHistory)
                                       .where(*filters)
                                       .offset(offset)
                                       .limit(page_per_rows)).all())

    total_count = db.scalar(select(func.count(AttendanceHistory.id))
                            .select_from(AttendanceHistory)
                            .join(AttendanceConfig)
                            .where(*filters))

    return templates.TemplateResponse(
        "admin/history.html", {
            "request": request,
            "total_count": total_count,
            "attendance_histories": attendance_histories,
            "paging": get_paging(request, page, total_count),
        })


@admin_router.get("/{id}")
async def show_attendance_config(
        request: Request,
        db: db_session,
        id: int,
):
    request.session["menu_key"] = module_name

    attendance_config = db.scalar(select(AttendanceConfig).where(AttendanceConfig.id == id))
    if attendance_config is None:
        raise AlertException("출석판 설정이 없습니다")

    return templates.TemplateResponse(
        "admin/show.html", {
            "request": request,
            "attendance_config": attendance_config,
        })


@admin_router.post("/delete", dependencies=[Depends(validate_token)])
async def delete_attendance(
        request: Request,
        db: db_session,
        ids: list = Form(..., alias='chk[]')
):
    delete_query = delete(AttendanceConfig).where(AttendanceConfig.id.in_(ids))
    db.execute(delete_query)
    db.commit()

    return RedirectResponse("/admin/attendance/index", status_code=302)
