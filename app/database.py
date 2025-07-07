from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings

# PostgreSQL 데이터베이스 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=300     # 5분마다 연결 재생성
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """데이터베이스 세션을 제공하는 의존성 함수"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """데이터베이스 테이블 삭제 (개발용)"""
    Base.metadata.drop_all(bind=engine)


def recreate_tables():
    """데이터베이스 테이블 재생성 (개발용)"""
    drop_tables()
    create_tables() 