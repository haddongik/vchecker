from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
import os
import shutil
import subprocess
import threading
from datetime import datetime

from ..database import get_db
from ..models import Version
from ..schemas import VersionCreate, VersionResponse, VersionList
from ..services.slack_service import SlackService
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def _send_version_notification(version):
    slack_service = SlackService()
    send_success = slack_service.send_version_notification(version)
    if send_success:
        logger.info(f"Slack({version.target}) 알림 전송 성공")
    else:
        logger.warning(f"Slack({version.target}) 알림 전송에 실패했습니다.")

# 전역 변수로 original_dir 설정 (한 번만 세팅)
_root_dir = None

def process_client_version_background(branch: str, revision: str, build_tag: str, version_id: int):

    from ..database import SessionLocal
    
    svn_urls = {
        "stove_live": settings.SVN_URL1,
        "stove_live_open": settings.SVN_URL2,
        "zlong_live": settings.SVN_URL3,
        "zlong_live_open": settings.SVN_URL4
    }
    
    db = SessionLocal()
    try:
        # 절대 경로로 작업 디렉토리 설정
        work_dir = os.path.join(_root_dir, "cdn", branch)
        
        # SVN 인증 정보
        svn_url = svn_urls[branch]
        svn_auth = ["--username", settings.SVN_USER, "--password", settings.SVN_PASSWORD, "--non-interactive"]
        
        # 폴더가 없으면 새로 생성하고 체크아웃
        if not os.path.exists(work_dir):
            os.makedirs(work_dir, exist_ok=True)
            
            # 파일 복사 (절대 경로 사용)
            exporter_path = os.path.join(_root_dir, "exporter")
            config_path = os.path.join(_root_dir, "config_exporter.json")
            shutil.copy(exporter_path, os.path.join(work_dir, "exporter"))
            shutil.copy(config_path, os.path.join(work_dir, "config.json"))
            
            # SVN 체크아웃 (계정 정보 포함)
            subprocess.run(["svn", "export", f"{svn_url}/bin64/game.bin", work_dir] + svn_auth, check=True, timeout=300)
            subprocess.run(["svn", "checkout", f"{svn_url}/db", os.path.join(work_dir, "db")] + svn_auth, check=True, timeout=300)
        else:
            # 최신으로 강제 업데이트
            subprocess.run(["svn", "update", "--accept", "theirs-full", "--force", os.path.join(work_dir, "db")] + svn_auth, check=True, timeout=300)
            
            # game.bin 파일 강제 업데이트
            subprocess.run(["svn", "export", "--force", f"{svn_url}/bin64/game.bin", work_dir] + svn_auth, check=True, timeout=300)
    
        # exporter 실행 (절대 경로 사용)
        exporter_work_path = os.path.join(work_dir, "exporter")
        result = subprocess.run([exporter_work_path], capture_output=True, text=True, timeout=300, cwd=work_dir)
        
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

        # DB 업데이트
        version = db.query(Version).filter(Version.id == version_id).first()
        if version:
            version.script_hash = script_hash
            version.db_hash = db_hash
            db.commit()
            logger.info(f"클라이언트 버전 처리 완료: {branch} (ID: {version_id})")
        else:
            logger.error(f"버전을 찾을 수 없음: {version_id}")

        _send_version_notification(version)
            
    except Exception as e:
        logger.error(f"클라이언트 버전 처리 실패: {str(e)}")
        # 실패 시 DB 업데이트
        try:
            version = db.query(Version).filter(Version.id == version_id).first()
            if version:
                version.script_hash = "error"
                version.db_hash = "error"
                db.commit()
        except:
            pass
    finally:
        db.close()


@router.post("/", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_server_version(version_data: VersionCreate, db: Session = Depends(get_db)):

    try:
        # 데이터베이스에 버전 정보 저장
        version = Version(**version_data.dict())
        
        # build_tag에 'z'가 포함되어 있으면 repo_root를 'zlong_live'로 설정
        if "z" in version.build_tag.lower():
            version.repo_root = "zlong_live"
        else:
            version.repo_root = "stove_live"
        
        db.add(version)
        db.commit()
        db.refresh(version)
        
        # Slack 알림 전송 (Webhook 우선, 없으면 Bot API 사용)
        _send_version_notification(version)
        
        logger.info(f"새로운 버전 등록: {version.target} - {version.build_tag}")
        return version
        
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
    # 루트 디렉토리 경로 설정
    global _root_dir
    if _root_dir is None:
        _root_dir = os.getcwd()
        
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

    # 즉시 응답할 버전 정보 생성
    db_version = Version(
        target="client",
        build_tag=build_tag,
        repo_root=branch,
        script_hash="processing",  # 처리 중임을 나타내는 값
        db_hash="processing"
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    
    # 별도 스레드에서 실제 작업 수행
    thread = threading.Thread(
        target=process_client_version_background,
        args=(branch, revision, build_tag, db_version.id)
    )
    thread.daemon = True  # 메인 프로세스 종료 시 함께 종료
    thread.start()
    
    logger.info(f"클라이언트 버전 생성 요청 완료: {branch} (ID: {db_version.id})")
    return db_version