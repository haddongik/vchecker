import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Settings:
    """애플리케이션 설정 클래스"""
    
    # 데이터베이스 설정
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: str = os.getenv("DB_PORT", "")
    DB_USER: str = os.getenv("DB_USER", "dev")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "dev")
    DB_NAME: str = os.getenv("DB_NAME", "battle_versions")
    
    # 데이터베이스 URL 생성
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Slack 설정
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    
    # 애플리케이션 설정
    APP_NAME: str = "Battle Version Tracker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# 전역 설정 인스턴스
settings = Settings() 