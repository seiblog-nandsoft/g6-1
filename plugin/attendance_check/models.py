from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

from common.database import DB_TABLE_PREFIX

Base = declarative_base()


class AttendanceConfig(Base):
    """출석부 설정"""
    __tablename__ = DB_TABLE_PREFIX + "attendance_config"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(length=50), index=True)
    point = Column(Integer, default=0)
    start_date = Column(DateTime, nullable=False, default=datetime.now)
    end_date = Column(DateTime, nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)


class AttendanceHistory(Base):
    """회원들 출석기록, 댓글"""
    __tablename__ = DB_TABLE_PREFIX + "attendance_history"
    id = Column(Integer, primary_key=True, index=True)
    mb_id = Column(String(length=50), index=True)
    comment = Column(Text(length=300))
    created_at = Column(DateTime, default=datetime.now)
