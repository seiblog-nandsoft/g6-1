from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from common.database import DB_TABLE_PREFIX
from common.models import Member, Base


class AttendanceConfig(Base):
    """출석부 설정"""
    __tablename__ = DB_TABLE_PREFIX + "attendance_config"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(length=50), index=True)
    point = Column(Integer, nullable=False, default=0, comment='출석 포인트')
    start_date = Column(DateTime, nullable=False, default=datetime.now)
    end_date = Column(DateTime, nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.now)


class AttendanceHistory(Base):
    """회원들 출석기록, 댓글"""
    __tablename__ = DB_TABLE_PREFIX + "attendance_history"
    id = Column(Integer, primary_key=True, index=True)
    mb_id = Column(String(length=50), index=True)
    attendance_config_id = Column(Integer, ForeignKey(AttendanceConfig.id), index=True)
    comment = Column(Text(length=300))
    created_at = Column(DateTime, default=datetime.now)

    attendance_config = relationship('AttendanceConfig')
    member = relationship(Member, innerjoin=True, primaryjoin='Member.mb_id==AttendanceHistory.mb_id',
                          foreign_keys=Member.mb_id)
