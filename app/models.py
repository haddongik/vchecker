from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Version(Base):
    """버전 정보를 저장하는 모델"""
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    target = Column(String(100), nullable=False, index=True)
    build_tag = Column(String(100), nullable=False, index=True)
    repo_root = Column(String(500), nullable=False)
    script_hash = Column(String(255), nullable=False)
    db_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Version(target='{self.target}', build_tag='{self.build_tag}')>" 