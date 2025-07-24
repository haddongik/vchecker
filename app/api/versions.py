from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
import os
import shutil
import subprocess
from datetime import datetime

from ..database import get_db
from ..models import Version
from ..schemas import VersionCreate, VersionResponse, VersionList
from ..services.slack_service import SlackService
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_server_version(version_data: VersionCreate, db: Session = Depends(get_db)):
    """
    새로운 버전 정보를 등록합니다.
    
    - **target**: 대상 플랫폼 (필수)
    - **build_tag**: 빌드 태그 (필수)
    - **repo_root**: 레포지토리 루트 (필수)
    - **script_hash**: 스크립트 해시 (필수)
    - **db_hash**: 데이터베이스 해시 (필수)
    """
    try:
        # 데이터베이스에 버전 정보 저장
        db_version = Version(**version_data.dict())
        db.add(db_version)
        db.commit()
        db.refresh(db_version)
        
        # Slack 알림 전송 (Webhook 우선, 없으면 Bot API 사용)
        version_info = {
            "target": db_version.target,
            "build_tag": db_version.build_tag,
            "repo_root": db_version.repo_root,
            "script_hash": db_version.script_hash,
            "db_hash": db_version.db_hash,
        }
        
        slack_service = SlackService()
        send_success = slack_service.send_version_notification(version_info)
        if send_success:
            logger.info("Slack 알림 전송 성공")
        else:
            logger.warning("Slack 알림 전송에 실패했습니다.")
        
        logger.info(f"새로운 버전 등록: {db_version.target} - {db_version.build_tag}")
        return db_version
        
    except Exception as e:
        db.rollback()
        logger.error(f"버전 등록 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="버전 등록 중 오류가 발생했습니다."
        )


@router.get("/", response_model=VersionList)
async def get_versions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    등록된 버전 목록을 조회합니다.
    
    - **skip**: 건너뛸 레코드 수 (기본값: 0)
    - **limit**: 반환할 최대 레코드 수 (기본값: 100)
    """
    try:
        versions = db.query(Version).offset(skip).limit(limit).all()
        total = db.query(Version).count()
        
        return VersionList(versions=versions, total=total)
        
    except Exception as e:
        logger.error(f"버전 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="버전 목록 조회 중 오류가 발생했습니다."
        )


@router.get("/{version_id}", response_model=VersionResponse)
async def get_version(
    version_id: int,
    db: Session = Depends(get_db)
):
    """
    특정 버전 정보를 조회합니다.
    
    - **version_id**: 조회할 버전의 ID
    """
    try:
        version = db.query(Version).filter(Version.id == version_id).first()
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 버전을 찾을 수 없습니다."
            )
        
        return version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"버전 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="버전 조회 중 오류가 발생했습니다."
        )


@router.get("/latest/", response_model=VersionResponse)
async def get_latest_version(db: Session = Depends(get_db)):
    """
    가장 최근에 등록된 버전 정보를 조회합니다.
    """
    try:
        latest_version = db.query(Version).order_by(Version.created_at.desc()).first()
        
        if not latest_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="등록된 버전이 없습니다."
            )
        
        return latest_version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최신 버전 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="최신 버전 조회 중 오류가 발생했습니다."
        )


@router.post("/cdn", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_client_version(
    branch: str,
    revision: str,
    db: Session = Depends(get_db)
):

    # buildtag = yyyymmdd_revision
    build_tag = f"{datetime.now().strftime('%Y%m%d')}_{revision}"

    svn_urls = {
        "stove_live": settings.SVN_URL1,
        "stove_live_open": settings.SVN_URL2,
        "zlong_live": settings.SVN_URL3,
        "zlong_live_open": settings.SVN_URL4
    }

    if branch not in svn_urls:
        raise HTTPException(status_code=400, detail=f"Invalid branch: {branch}")

    try:
        work_dir = f"./cdn/{branch}"
        
        # 폴더 정리
        shutil.rmtree(work_dir, ignore_errors=True)
        os.makedirs(work_dir, exist_ok=True)
        
        # 파일 복사
        shutil.copy("./exporter", f"{work_dir}/exporter")
        shutil.copy("./config_exporter.json", f"{work_dir}/config.json")
        
        # SVN 체크아웃 (계정 정보 포함)
        svn_url = svn_urls[branch]
        svn_auth = ["--username", settings.SVN_USER, "--password", settings.SVN_PASSWORD, "--non-interactive"]
        
        subprocess.run(["svn", "export", f"{svn_url}/bin64/game.bin", work_dir] + svn_auth, check=True, timeout=300)
        subprocess.run(["svn", "checkout", f"{svn_url}/db", f"{work_dir}/db"] + svn_auth, check=True, timeout=300)
        
        # exporter 실행
        os.chdir(work_dir)
        result = subprocess.run(["./exporter"], capture_output=True, text=True, timeout=300)
        
        logger.info(f"result: {result}")

        # 해시 추출
        script_hash = "unknown"
        db_hash = "unknown"
        
        for line in result.stdout.split('\n'):
            if line.startswith('SCRIPT_HASH='):
                script_hash = line.split('=')[1]
            elif line.startswith('DB_HASH='):
                db_hash = line.split('=')[1]
        
        logger.info(f"script_hash: {script_hash}")
        logger.info(f"db_hash: {db_hash}")

        # DB 저장
        db_version = Version(
            target="client",
            build_tag=build_tag,
            repo_root=branch,
            script_hash=script_hash,
            db_hash=db_hash
        )
        db.add(db_version)
        db.commit()
        db.refresh(db_version)
        
        logger.info(f"클라이언트 버전 생성 완료: {branch}")
        return db_version
        
    except Exception as e:
        db.rollback()
        logger.error(f"클라이언트 버전 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="클라이언트 버전 생성 중 오류가 발생했습니다.")