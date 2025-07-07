# Battle Version Tracker

버전 정보를 수신하고 데이터베이스에 저장한 후 Slack에 알림을 보내는 Python 백엔드 애플리케이션입니다.

## 🚀 주요 기능

- **API 엔드포인트**: 버전 정보를 받는 REST API
- **데이터베이스 저장**: SQLAlchemy를 사용한 MySQL 저장
- **Slack 알림**: 새로운 버전 등록 시 자동 알림
- **API 문서**: 자동 생성되는 Swagger UI

## 🛠 기술 스택

- **FastAPI**: 현대적이고 빠른 Python 웹 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **MySQL**: 메인 데이터베이스
- **Pydantic**: 데이터 검증
- **slack-sdk**: Slack API 연동

## 📦 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`config.env` 파일을 확인하고 필요시 수정하세요:
```
# 데이터베이스 설정
DB_HOST=10.10.20.96
DB_PORT=5432
DB_USER=dev
DB_PASSWORD=dev
DB_NAME=battle_versions

# 애플리케이션 설정
DEBUG=True
LOG_LEVEL=INFO
```

### 3. 데이터베이스 준비
MySQL에서 `battle_versions` 데이터베이스를 생성하세요:
```sql
CREATE DATABASE battle_versions CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 애플리케이션 실행
```bash
uvicorn app.main:app --reload
```

### 5. API 문서 확인
브라우저에서 `http://localhost:8000/docs` 접속

## 📡 API 사용법

### 버전 정보 등록
```bash
curl -X POST "http://localhost:8000/api/versions" \
     -H "Content-Type: application/json" \
     -d '{
       "version": "1.2.3",
       "description": "새로운 기능 추가",
       "release_date": "2024-01-15T10:30:00",
       "author": "개발팀"
     }'
```

## 🗄 데이터베이스 스키마

- `version`: 버전 번호
- `description`: 버전 설명
- `release_date`: 출시 날짜
- `author`: 작성자
- `created_at`: 등록 시간
- `updated_at`: 수정 시간

## 🔧 개발

### 테스트 실행
```bash
pytest
```

### 코드 포맷팅
```bash
black .
```

## 📝 라이선스

MIT License 