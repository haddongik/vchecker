from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .database import recreate_tables, engine
from .api.versions import router as versions_router
from .config import settings

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.APP_NAME,
    description="버전 정보를 수신하고 데이터베이스에 저장한 후 Slack에 알림을 보내는 API",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def wait_for_db(max_retries=30, delay=2):
    """데이터베이스 연결을 기다리는 함수"""
    for attempt in range(max_retries):
        try:
            # 데이터베이스 연결 테스트
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logging.info("데이터베이스 연결 성공")
            return True
        except OperationalError as e:
            logging.warning(f"데이터베이스 연결 시도 {attempt + 1}/{max_retries} 실패: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                logging.error("데이터베이스 연결 최대 재시도 횟수 초과")
                return False


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    logging.info("Battle Version Tracker 시작 중...")
    
    # 데이터베이스 연결 대기
    if wait_for_db():
        recreate_tables()  # 테이블 재생성
        logging.info("데이터베이스 테이블 재생성 완료")
    else:
        logging.error("데이터베이스 연결 실패로 애플리케이션을 시작할 수 없습니다.")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트"""
    logging.info("Battle Version Tracker 종료 중...")


# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": settings.DB_HOST
    }


# 루트 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": f"{settings.APP_NAME} API에 오신 것을 환영합니다!",
        "docs": "/docs",
        "health": "/health"
    }


# API 라우터 등록
app.include_router(
    versions_router,
    prefix="/api/versions",
    tags=["versions"]
)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 