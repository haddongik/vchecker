import requests
import json
import logging
from ..config import settings

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
    
    def _create_version_message(self, version_data) -> str:
        """버전 정보를 포함한 텍스트 메시지 생성"""
        return (
            f"🎮 *battle hash info*\n"
            f"• build: {version_data.get('repo_root', 'unknown')}\n"
            f"• target: {version_data.get('target', 'unknown')}\n"
            f"• git branch: {version_data.get('git_branch', 'unknown')}\n"
            f"• build tag: {version_data.get('build_tag', 'unknown')}\n"
            f"• script hash: *{version_data.get('script_hash', 'unknown')}*\n"
            f"• db hash: *{version_data.get('db_hash', 'unknown')}*"
        ) 
    
    def _get_last_send_hashinfo(self, target_region):
        """마지막으로 전송된 target_region 별 해시 정보 조회(client, arena_server 둘다)"""
        # DB 사용 안함 - 빈 정보 반환
        logger.warning("DB 사용 안함 - 해시 정보 조회 불가")
        return {
            "client_script_hash": None,
            "client_db_hash": None,
            "arena_server_script_hash": None,
            "arena_server_db_hash": None
        }