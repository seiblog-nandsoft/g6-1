from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi.params import Depends, Form
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.templating import Jinja2Templates

from common.database import get_db
from common.models import Member
from lib.common import TEMPLATES_DIR, theme_asset, datetime_format, get_member_image, AlertException, validate_token, \
    number_format
from ..models import AttendanceHistory, AttendanceConfig
from ..plugin_config import module_name
import calendar

router = APIRouter()

PLUGIN_TEMPLATES_DIR = f"plugin/{module_name}/templates"
templates = Jinja2Templates(directory=[TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])
templates.env.globals["theme_asset"] = theme_asset
templates.env.globals["get_member_image"] = get_member_image
templates.env.filters["datetime_format"] = datetime_format
templates.env.filters["number_format"] = number_format

@router.get("/show/{attendance_id}")  # date 없을때
@router.get("/show/{attendance_id}/{date}")
async def show_attendance_check(
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

    comments = db.scalars(select(AttendanceHistory, Member.mb_nick)
    .join(Member, AttendanceHistory.mb_id == Member.mb_id)
    .where(
        AttendanceHistory.attendance_config_id == attendance_config.id,

        AttendanceHistory.comment != '',
        AttendanceHistory.created_at.between(f'{date} 00:00:00', f'{date} 23:59:59'))

    ).all()

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


@router.post("/ajax/{attendance_id}/check")
async def save_attendance_check(
        request: Request,
        attendance_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    """
    출석체크 api
    """
    if not attendance_id:
        raise AlertException("유효한 요청이 아닙니다.", url='/', status_code=400)

    today_attendance = db.scalar(
        select(AttendanceHistory).where(
            AttendanceHistory.mb_id == request.state.login_member.mb_id,
            AttendanceHistory.attendance_config_id == attendance_id,
            AttendanceHistory.created_at.between(
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 00:00:00',
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 23:59:59')
        )
    )

    if today_attendance:
        return JSONResponse({"status": "error", "message": "이미 출석체크를 하셨습니다."}, status_code=400)

    db.add(AttendanceHistory(mb_id=request.state.login_member.mb_id, attendance_config_id=attendance_id))
    db.commit()

    return JSONResponse({"status": "success", "message": "출석체크 완료."}, status_code=200)


@router.post("/ajax/{attendance_id}/info")
async def save_attendance_check(
        request: Request,
        attendance_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    """
    출석체크 한달목록 출력 api
    """

    if not attendance_id:
        raise AlertException("유효한 요청이 아닙니다.", url='/', status_code=400)

    today = datetime.today()

    first_date_of_month = today.replace(day=1)
    res = calendar.monthrange(today.year, today.month)
    last_date_of_month = datetime(today.year, today.month, res[1])

    attendance_histories = db.scalars(
        select(AttendanceHistory).where(
            AttendanceHistory.mb_id == request.state.login_member.mb_id,
            AttendanceHistory.attendance_config_id == attendance_id,
            AttendanceHistory.created_at.between(
                f'{datetime.strftime(first_date_of_month, "%Y-%m-%d")} 00:00:00',
                f'{datetime.strftime(last_date_of_month, "%Y-%m-%d")} 23:59:59')
        )
    ).all()

    attendace_list = {
        'attendance': [],
    }
    for data in attendance_histories:
        item = {
            'check_time': data.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        attendace_list['attendance'].append(item)

    return JSONResponse({"status": "success", "data": attendace_list}, status_code=200)


@router.post("/save_comment/{attendance_id}", dependencies=[Depends(validate_token)])
async def save_adttendance_comment(
        request: Request,
        db: Session = Depends(get_db),
        attendance_id: Optional[int] = None,
        comment: str = Form(...)
):
    if not attendance_id:
        raise AlertException("유효한 요청이 아닙니다.", url='/', status_code=400)

    if not comment:
        return AlertException("댓글이 없습니다.", url='/', status_code=400)

    config = request.state.config
    if comment in config.cf_filter:
        return AlertException("금지어가 포함되어 있습니다.", url='/', status_code=400)

    # 유효성검사 끝

    today_attendance = db.scalar(
        select(AttendanceHistory).where(
            AttendanceHistory.mb_id == request.state.login_member.mb_id,
            AttendanceHistory.created_at.between(
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 00:00:00',
                f'{datetime.strftime(datetime.now(), "%Y-%m-%d")} 23:59:59'))
    )

    # 출석체크만 하고 댓글 없을 경우
    if today_attendance:
        if not today_attendance.comment:
            today_attendance.comment = comment
            db.commit()
        return RedirectResponse(url=f'/attendance/show/{attendance_id}', status_code=302)

    # 출석체크
    attendance_history = AttendanceHistory(
        attendance_config_id=attendance_id,
        mb_id=request.state.login_member.mb_id,
        comment=comment
    )

    db.add(attendance_history)
    db.commit()

    return RedirectResponse(url=f'/attendance/show/{attendance_id}', status_code=302)


@router.get("/{attendance_id}/delete_comment/{comment_id}", dependencies=[Depends(validate_token)])
async def delete_adttendance_comment(
        request: Request,
        attendance_id: Optional[int] = None,
        comment_id: Optional[int] = None,

        db: Session = Depends(get_db)
):
    """
    출석기록은 그대로 두고 코멘트만 지우기
    """
    if not attendance_id or not comment_id:
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

    return RedirectResponse(url=f'/attendance/show/{attendance_id}', status_code=302)
