import requests
import json
import logging
from ..config import settings

logger = logging.getLogger(__name__)


class SlackService:
    """Slack 알림 서비스"""
    
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL
    
    def send_version_notification(self, version_info: dict):
        """새로운 버전 등록 시 Slack 알림 전송"""
        try:
            if not self.webhook_url:
                logger.warning("Webhook URL이 설정되지 않았습니다.")
                return False
            
            # Slack 메시지 구성
            message = self._create_version_message(version_info)
            
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
    
    def _create_version_message(self, version_info: dict) -> str:
        """버전 정보를 포함한 텍스트 메시지 생성"""
        return (
            f"🎮 *새로운 버전이 등록되었습니다!*\n"
            f"• 대상: {version_info['target']}\n"
            f"• 빌드 태그: {version_info['build_tag']}\n"
            f"• 레포지토리 루트: {version_info['repo_root']}\n"
            f"• 스크립트 해시: {version_info['script_hash']}\n"
            f"• 데이터베이스 해시: {version_info['db_hash']}"
        ) 