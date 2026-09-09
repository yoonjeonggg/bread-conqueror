# Bread Conqueror — Backend

FastAPI · SQLAlchemy 2.0 (async) · MySQL 8 · Redis · Alembic

## 구조

```
app/
├── main.py                FastAPI 앱 (CORS, 라우터 등록, /health)
├── core/                  config · security(JWT/bcrypt) · dependencies(RBAC) · redis
├── db/                    async 세션, DeclarativeBase, Alembic import 타깃
├── models/                15개 ORM 모델 (enums.py에 ENUM 일괄 정의)
├── schemas/               Pydantic v2 요청/응답
├── api/v1/routers/        auth · users · stores · flags · ranking · posts · admin
├── services/              flag_service(트랜잭션 코어) · geo · tier · abuse_detection
│                          · ranking(Redis ZSET) · policy(정책값 로더)
├── tasks/                 APScheduler 스텁 (랭킹 재빌드 등)
├── utils/exif.py          실버 깃발 EXIF 검증
└── tests/                 unit(geo·tier) + integration(정복 플로우) — SQLite
alembic/versions/0001      initial schema (metadata에서 생성)
scripts/seed.py            정책·티어·데모 매장·데모 계정
```

## 명령

```bash
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload

pytest          # DB 불필요 (SQLite in-memory)
ruff check .
```

## 환경변수 (`.env`)

| 키 | 예시 | 필수 |
| --- | --- | --- |
| `DATABASE_URL` | `mysql+aiomysql://root:password@localhost:3306/bread_conqueror` | ✅ |
| `JWT_SECRET_KEY` | 임의 문자열 | ✅ |
| `REDIS_URL` | `redis://localhost:6379/0` | (기본값 있음) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | (기본값 있음) |
| `KAKAO_MAP_API_KEY` 등 | 매장 수집 배치용 | ✕ |

> Alembic·동기 도구는 `settings.sync_database_url` 로 `+aiomysql` → `+pymysql` 자동 치환.

## 데모 계정 (seed 후)

- 관리자: `admin@bread.dev` / `admin1234`
- 일반: `demo@bread.dev` / `demo1234`
