from fastapi import APIRouter, HTTPException, status
from typing import List
import logging
import os
import shutil
import subprocess
import threading
from datetime import datetime

from ..services.slack_service import SlackService
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def _send_version_notification(version_data):
    slack_service = SlackService()
    send_success = slack_service.send_version_notification(version_data)
    if send_success:
        logger.info(f"Slack({version_data.get('target', 'unknown')}) 알림 전송 성공")
    else:
        logger.warning(f"Slack({version_data.get('target', 'unknown')}) 알림 전송에 실패했습니다.")

# 전역 변수로 original_dir 설정 (한 번만 세팅)
_root_dir = None

def process_client_version_background(branch: str, revision: str, build_tag: str):

    svn_urls = {
        "stove_live": settings.SVN_URL1,
        "stove_live_open": settings.SVN_URL2,
        "zlong_live": settings.SVN_URL3,
        "zlong_live_open": settings.SVN_URL4
    }

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

        # 버전 데이터 생성
        version_data = {
            "target": "client",
            "build_tag": build_tag,
            "repo_root": branch,
            "script_hash": script_hash,
            "db_hash": db_hash
        }

        logger.info(f"클라이언트 버전 처리 완료: {branch}")

        _send_version_notification(version_data)
            
    except Exception as e:
        logger.error(f"클라이언트 버전 처리 실패: {str(e)}")
        # 실패 시 에러 버전 데이터 생성
        error_version_data = {
            "target": "client",
            "build_tag": build_tag,
            "repo_root": branch,
            "script_hash": "error",
            "db_hash": "error"
        }
        _send_version_notification(error_version_data)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_server_version(version_data: dict):

    try:
        # Slack 알림 전송
        _send_version_notification(version_data)

        logger.info(f"새로운 버전 등록: {version_data.get('target')} - {version_data.get('build_tag')}")
        return version_data

    except Exception as e:
        logger.error(f"버전 등록 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="버전 등록 중 오류가 발생했습니다."
        )


@router.get("/")
async def get_versions(
    skip: int = 0,
    limit: int = 100
):
    try:
        # DB 사용 안함 - 빈 응답 반환
        return {"versions": [], "total": 0}

    except Exception as e:
        logger.error(f"버전 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="버전 목록 조회 중 오류가 발생했습니다."
        )


@router.get("/{version_id}")
async def get_version(
    version_id: int
):
    try:
        # DB 사용 안함 - 404 반환
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 버전을 찾을 수 없습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"버전 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="버전 조회 중 오류가 발생했습니다."
        )


@router.get("/latest/")
async def get_latest_version():
    """
    가장 최근에 등록된 버전 정보를 조회합니다.
    """
    try:
        # DB 사용 안함 - 404 반환
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="등록된 버전이 없습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최신 버전 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="최신 버전 조회 중 오류가 발생했습니다."
        )


@router.post("/cdn", status_code=status.HTTP_201_CREATED)
async def create_client_version(
    branch: str,
    revision: str
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
    version_data = {
        "target": "client",
        "build_tag": build_tag,
        "repo_root": branch,
        "script_hash": "processing",
        "db_hash": "processing"
    }

    # 별도 스레드에서 실제 작업 수행
    thread = threading.Thread(
        target=process_client_version_background,
        args=(branch, revision, build_tag)
    )
    thread.daemon = True  # 메인 프로세스 종료 시 함께 종료
    thread.start()

    logger.info(f"클라이언트 버전 생성 요청 완료: {branch}")
    return version_data