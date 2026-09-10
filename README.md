# 🥐 Bread Conqueror

전국 베이커리를 방문하며 **깃발(Flag)** 을 꽂고 정복하는 게임형(Gamification) 빵 커뮤니티 서비스.
방문 인증 → 경험치 → 티어 → 랭킹으로 이어지는 성장 루프를 중심으로 설계했습니다.

> 포트폴리오 / 기술 연습 프로젝트. 기획·요구사항·DB·기술 스택 명세는 Notion 문서 기준.

---

## 아키텍처

```
bread-conqueror/
├── backend/      FastAPI · SQLAlchemy 2.0(async) · MySQL 8 · Redis · Alembic
├── frontend/     Next.js 14 (App Router) · React 18 · TypeScript  (모바일 우선)
└── docker-compose.yml   backend + frontend + mysql + redis
```

| 레이어 | 스택 | 비고 |
| --- | --- | --- |
| API | FastAPI, Pydantic v2 | 자동 OpenAPI 문서 (`/docs`) |
| ORM | SQLAlchemy 2.0 async, Alembic | 15개 테이블, FK 촘촘한 관계형 스키마 |
| DB | MySQL 8 (utf8mb4) | 로컬은 Docker, 테스트는 SQLite |
| 캐시/랭킹 | Redis Sorted Set | 전국/지역 랭킹, 쿨다운 (best-effort, DB가 SoT) |
| 인증 | JWT (access/refresh), passlib bcrypt | RBAC 의존성으로 관리자 API 보호 |
| 프론트 | Next.js App Router | 홈·지도·검색·매장상세(리뷰)·매장등록·정복·QR정복·소유권신청/관리·게시판·랭킹·알림·미션·프로필·관리자 |

---

## 빠른 시작 (Docker)

```bash
cp backend/.env.example backend/.env      # 필요 시 값 조정
docker compose up --build
```

- 프론트: http://localhost:3000
- API 문서: http://localhost:8000/docs
- 컨테이너 기동 시 `alembic upgrade head` + `scripts/seed.py` 자동 실행
  (정책값·티어·데모 매장 6곳·계정 `admin@bread.dev / admin1234`, `demo@bread.dev / demo1234`)

## 로컬 개발 (Docker 없이)

**백엔드** — MySQL·Redis는 `docker compose up mysql redis`로 띄운 뒤:

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # win: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

**프론트**

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

## 테스트 / 린트

```bash
cd backend
pytest            # 단위(geo·tier) + 통합(정복 플로우) — SQLite, DB 불필요
ruff check .
```

---

## 정복(인증) 시스템 — 핵심 로직

`app/services/flag_service.py` 의 `create_flag()` 한 번이 **하나의 트랜잭션**으로
`Flag` · `UserStat` · `StoreStat` · 티어를 함께 갱신합니다. (라우터가 커밋 소유)

- **골드 깃발** (F-CONQ-01~03): GPS 좌표와 매장 좌표를 haversine으로 계산, 반경
  `CONQUEST_RADIUS_M`(기본 50m) 이내일 때만 발급. 경험치 100%.
- **실버 깃발** (F-CONQ-04~05): 과거 방문 수동 등록. 경험치 50%, 일 5건 / 누적 30건 제한.
- **실버 → 골드 업그레이드** (F-CONQ-06): 실버가 꽂힌 매장을 실시간 재인증하면 승격 + 연출.
- **쿨다운** (F-CONQ-07): 동일 (user, store) 24시간.
- **이상 탐지** (F-CONQ-09): 직전 깃발과의 이동 속도가 `ABUSE_SPEED_KMH` 초과 시
  `is_flagged=True` 로 관리자 검토 큐(F-ADMIN-01/02)에 올림. (`abuse_detection.py`)

정책값은 전부 `policy_configs` / `tier_policies` 테이블에서 읽어 하드코딩을 피했습니다
(`policy_service.py`, 미시드 시 안전한 기본값).

---

## 요구사항 → 구현 매핑

| 요구사항 | 위치 |
| --- | --- |
| F-MAP-01 주변 베이커리 탐색 | `GET /stores?lat&lng&radius_m` — bounding box 1차 필터 + haversine |
| F-SEARCH 검색/필터 | `GET /stores/search` (키워드·지역·종류·인증·정렬), `GET /stores/filters`, `GET /posts?q&store_id&sort` |
| F-MISSION 주간 미션 | `GET /missions/weekly` (이번 주 진행도), `POST /missions/{code}/claim` (보상 1회) — `services/mission_service.py` |
| F-MAP-04 / F-STORE-02 신규 매장 등록 | `POST /stores` — 반경 30m 중복 검사, 프론트 `/stores/new` |
| F-DETAIL-01/02 리뷰·평점 | `GET/POST /stores/{id}/reviews` — upsert 시 StoreStat·UserStat 재집계 |
| F-CONQ-01~09 정복/이상탐지 | `POST /flags`, `services/flag_service.py`, `geo_service.py` |
| F-CONQ-05 실버 증빙 신뢰도 | `POST /flags/exif-preview` — `utils/exif.py`, EXIF 촬영시각/GPS → trust |
| F-CONQ-10 신고 | `POST /reports` → 관리자 큐 |
| F-TIER-01~03 티어 산정 | `services/tier_service.py` — exp + 골드비율 게이트 |
| F-RANK-01~03 랭킹 | `GET /rankings/{national,regional,friends}` (Redis ZSET, DB fallback) |
| F-PROF-01 프로필 | `GET /users/me`, `GET /users/{id}`, 팔로우 카운트 |
| F-BOARD-01~03 추천 게시판 | `GET/POST /posts`, 댓글·좋아요, 신고→관리자 모더레이션 |
| F-STORE-05 매장 소유권 Claim | `POST /stores/{id}/claims` → 관리자 승인 시 `store.owner_id` 연결 |
| F-CONQ-11 QR 정복 | 소유자가 `POST /stores/{id}/qr-tokens` 발급 → 손님 `POST /flags/qr` (GPS 없이 골드) |
| F-ADMIN-01/02 | `GET /admin/flags/review-queue`, `POST .../approve\|invalidate` |
| F-ADMIN-04 매장 병합 | `POST /admin/stores/{target}/merge` — 참조 이관·집계 재계산·source 폐점 (`services/store_service.py`) |
| F-ADMIN-05 CSV 대량 등록 | `POST /admin/stores/bulk-upload` — 행별 검증·반경 30m 중복 스킵·dry-run·행별 리포트 (`services/store_import_service.py`) |
| F-ADMIN-06 Claim 심사 | `GET /admin/claims`, `POST /admin/claims/{id}/approve\|reject` |
| F-NOTI-01~03 인앱 알림 | `GET /notifications`, `/unread-count`, `POST /notifications/read` — 팔로우·댓글·좋아요·Claim 심사·티어 상승·QR 정복 시 생성 (`services/notification_service.py`) |
| F-ADMIN-07 계정 정지 | `POST /admin/users/{id}/suspend\|reactivate` |
| F-ADMIN-08 경험치·티어 조정 | `POST /admin/users/{id}/adjust-exp` — 티어 자동 재계산 |
| F-ADMIN-09 콘텐츠 모더레이션 | `POST /admin/{posts,comments}/{id}/moderate`, `/admin/reports/{id}/resolve` |
| F-ADMIN-10/11 | `GET /admin/stats/dashboard` — RBAC 의존성으로 전 라우트 보호 |

모든 관리자 행위는 `admin_action_logs` 에 기록됩니다.

### 로드맵 단계별 상태

- **1단계 (매장/지도/기본 인증)** — ✅ 동작
- **2단계 (골드/실버, 티어)** — ✅ 동작
- **3단계 (랭킹, 게시판)** — ✅ 동작 (전국/친구 랭킹, 게시글·댓글·좋아요·신고)
- **4단계 (관리자)** — ✅ 검토 큐·대시보드·계정 제재·경험치 조정·신고/콘텐츠 처리·Claim 심사·매장 병합·CSV 대량 등록
- **5단계 (매장 Claim/QR)** — ✅ 소유권 신청→관리자 승인→소유자 연결, 정복용 QR 토큰 발급/검증
  (`/stores/{id}/claim`, `/stores/{id}/manage`, `/qr?t=`) · 제휴/포인트는 스텁
- **6단계 (인앱 알림)** — ✅ 팔로우·댓글·좋아요·Claim 심사·티어 상승·QR 정복 알림,
  읽음 처리, 하단 네비 배지 (`/notifications`)
- **7단계 (검색/필터)** — ✅ 매장 키워드·지역·종류·인증·정렬 검색(`/search`), 게시판 검색·인기순
- **8단계 (주간 미션)** — ✅ 이번 주 골드/깃발/리뷰/탐험/원정 미션, 진행도 계산·보상 수령 (`/missions`)

---

## API 문서

기동 후 `http://localhost:8000/docs` (Swagger) / `/redoc`.
