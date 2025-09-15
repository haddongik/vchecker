import requests
import json
import logging
from sqlalchemy import desc
from ..config import settings
from ..models import Version
from ..database import SessionLocal

logger = logging.getLogger(__name__)


class SlackService:
    """Slack 알림 서비스"""
    
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL
    
    def send_version_notification(self, version):
        """새로운 버전 등록 시 Slack 알림 전송"""
        try:
            if not self.webhook_url:
                logger.warning("Webhook URL이 설정되지 않았습니다.")
                return False
            
            # Slack 메시지 구성
            message = self._create_version_message(version)
            
            # Webhook으로 메시지 전송
            response = requests.post(
                self.webhook_url,
                json={"text": message},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("Slack 알림 전송 성공")
                return True
            else:
                logger.error(f"Slack 전송 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Slack 알림 전송 실패: {str(e)}")
            return False
    
    def _create_version_message(self, version) -> str:
        """버전 정보를 포함한 텍스트 메시지 생성"""
        return (
            f"🎮 *battle hash info*\n" 
            f"• build: {version.repo_root}\n"
            f"• target: {version.target}\n"
            f"• git branch: {version.git_branch}\n"
            f"• build tag: {version.build_tag}\n"
            f"• script hash: *{version.script_hash}*\n"
            f"• db hash: *{version.db_hash}*"
        ) 
    
    def _get_last_send_hashinfo(self, target_region):
        """마지막으로 전송된 target_region 별 해시 정보 조회(client, arena_server 둘다)"""
        try:
            with SessionLocal() as session:
                # 클라이언트 버전 조회 (target_region에 따라 필터링)
                client_version = session.query(Version).filter(
                    Version.target == "client",
                    Version.repo_root == "zlong_live" if target_region == "Zlong" else "stove_live"
                ).order_by(desc(Version.created_at)).first()

                # 아레나 서버 버전 조회
                arena_server_version = session.query(Version).filter(
                    Version.target == "arena_server",
                    Version.build_tag.like("%z%" if target_region == "Zlong" else "%")
                ).order_by(desc(Version.created_at)).first()
            
            return {
                "client_script_hash": client_version.script_hash if client_version else None,
                "client_db_hash": client_version.db_hash if client_version else None,
                "arena_server_script_hash": arena_server_version.script_hash if arena_server_version else None,
                "arena_server_db_hash": arena_server_version.db_hash if arena_server_version else None
            }
        except Exception as e:
            logger.error(f"해시 정보 조회 실패: {str(e)}")
            return None