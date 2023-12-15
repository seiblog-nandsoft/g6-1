from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi.params import Depends, Form
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from common.database import get_db
from lib.common import TEMPLATES_DIR, theme_asset, datetime_format, get_member_image, AlertException
from ..models import AttendanceHistory, AttendanceConfig
from ..plugin_config import module_name

router = APIRouter()

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])
templates.env.globals["theme_asset"] = theme_asset
templates.env.filters["datetime_format"] = datetime_format
templates.env.globals["get_member_image"] = get_member_image


@router.get("/show/{attendance_id}")  # date 없을때
@router.get("/show/{attendance_id}/{date}")
def show_attendance_check(
        request: Request,
        db: Session = Depends(get_db),
        date: str = '',
        attendance_id: Optional[int] = None
):
    if not attendance_id:
        raise AlertException("사용하지 않는 출석부 입니다", url='/')

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        date = datetime.strftime(datetime.now(), "%Y-%m-%d")

    attendance_config = db.scalar(select(AttendanceConfig)
                                  .where(AttendanceConfig.id == attendance_id,
                                         AttendanceConfig.end_date >= datetime.now().strftime(
                                             "%Y-%m-%d %H:%M:%S")))
    if not attendance_config:
        raise AlertException("출석기간이 아닙니다.")

    comments = db.scalars(select(AttendanceHistory).where(
        AttendanceHistory.attendance_config_id == attendance_config.id,
        AttendanceHistory.created_at.between(f'{date} 00:00:00', f'{date} 23:59:59'))).all()

    if not comments:
        comments = []
    db.commit()

    return templates.TemplateResponse(
        "attendance.html",
        {
            "request": request,
            "title": f"Hello plugin!",
            "content": f"Hello {module_name}!",
            "comments": comments,
        }
    )


@router.get("/{attendance_id}/check")
def save_attendance_check(
        request: Request,
        attendance_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    if not attendance_id:
        raise AlertException("유효한 요청이 아닙니다.", url='/', status_code=400)

    today_attendance = db.scalar(
        select(AttendanceHistory).where(
            AttendanceHistory.mb_id == request.state.login_member.mb_id,
            AttendanceHistory.attendance_config_id == attendance_id,
            AttendanceHistory.created_at.between(
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 00:00:00',
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 23:59:59'))
    )

    if today_attendance:
        raise AlertException("이미 출석하셨습니다.")

    db.add(AttendanceHistory(mb_id=request.state.login_member.mb_id))
    db.commit()

    return RedirectResponse(url='/attendance/show')


@router.post("/save_comment")
def save_adttendance_comment(
        request: Request,
        db: Session = Depends(get_db),
        attendance_id: Optional[int] = None,
        comment: str = Form(...)
):
    if not attendance_id:
        raise AlertException("유효한 요청이 아닙니다.", url='/', status_code=400)

    if not comment:
        return RedirectResponse(url='/attendance_check/check')

    today_attendance = db.scalar(
        select(AttendanceHistory).where(
            AttendanceHistory.mb_id == request.state.login_member.mb_id,
            AttendanceHistory.created_at.between(
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 00:00:00',
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 23:59:59'))
    )
    if today_attendance:
        today_attendance.comment = comment

    else:
        db.add(AttendanceHistory(mb_id=request.state.login_member.mb_id, comment=comment))

    db.commit()

    return RedirectResponse(url='/attendance/check')


@router.post("/delete_comment")
def delete_adttendance_comment(
        request: Request,
        attendance_id: Optional[int] = None,

        db: Session = Depends(get_db)
):
    """
    출석기록은 그대로 두고 코멘트만 지우기
    """
    if not attendance_id:
        raise AlertException("유효한 요청이 아닙니다.", url='/', status_code=400)

    today_attendance = db.scalar(
        select(AttendanceHistory).where(
            AttendanceHistory.mb_id == request.state.login_member.mb_id,
            AttendanceHistory.created_at.between(
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 00:00:00',
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 23:59:59'))
    )
    if today_attendance:
        today_attendance.comment = ''

    db.commit()

    return RedirectResponse(url='/attendance/check')
