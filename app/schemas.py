from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class VersionBase(BaseModel):
    """버전 정보 기본 스키마"""
    target: str = Field(..., description="대상 플랫폼")
    build_tag: str = Field(..., description="빌드 태그")
    repo_root: str = Field(..., description="레포지토리 루트")
    git_branch: str = Field(..., description="Git 브랜치")
    script_hash: str = Field(..., description="스크립트 해시")
    db_hash: str = Field(..., description="데이터베이스 해시")


class VersionCreate(VersionBase):
    """버전 생성 요청 스키마"""
    pass


class VersionResponse(VersionBase):
    """버전 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VersionList(BaseModel):
    """버전 목록 응답 스키마"""
    versions: list[VersionResponse]
    total: int 