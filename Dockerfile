# trip — 멀티스테이지 이미지 (UD-8: 단일 컨테이너가 API + 웹 정적 자산 서빙)
#
# 근거:
#   ID-2   베이스 이미지는 버전 태그 + 다이제스트로 고정 (SEC-10, latest 금지)
#   ID-19  읽기 전용 루트 FS 대응 — PYTHONDONTWRITEBYTECODE + 사전 compileall
#   ID-4   🔴 uvicorn 워커는 1개 고정 (아래 CMD 주석 참조)
#   UD-9   런타임은 python:3.12-slim (로컬 3.14 는 비보증)
#
# ⚠️ 이 Dockerfile 은 `web/` (u2-trip-web) 가 있어야 빌드된다.
#    u1 만 생성된 상태에서는 stage 1 이 실패한다 — 정상이다.
#    이미지 빌드는 u2·u3 생성 후 Build & Test 스테이지에서 수행한다.

# ---------------------------------------------------------------------------
# stage 1: 웹 정적 자산 빌드
# ---------------------------------------------------------------------------
# ID-20 / SEC-10 — 베이스 이미지를 **다이제스트로 고정**한다 (Build & Test I-2 에서 실측).
#   태그는 같은 이름으로 다른 내용이 올 수 있다. 다이제스트는 그럴 수 없다.
#   갱신 절차: docker buildx imagetools inspect node:24-alpine --format '{{.Manifest.Digest}}'
FROM node:26-alpine@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019 AS web-build

WORKDIR /build

# 락파일 기반 재현 가능 설치 (SEC-10)
COPY web/package.json web/package-lock.json ./
RUN npm ci

# UD-3: 생성된 API 타입이 저장소에 커밋되어 있으므로
#       이 스테이지는 백엔드를 기동하지 않고 독립적으로 빌드된다.
COPY web/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# stage 2: 런타임
# ---------------------------------------------------------------------------
# ID-20 / SEC-10 — 다이제스트 고정 (위와 같은 이유).
#   갱신 절차: docker buildx imagetools inspect python:3.12-slim --format '{{.Manifest.Digest}}'
FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS runtime

# ID-19 — 읽기 전용 루트 FS 에서 .pyc 쓰기 시도를 없앤다
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Seoul

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
# pip 자체에도 알려진 취약점이 있다 (Build & Test I-12 에서 확인).
# 의존성을 설치하기 전에 먼저 올린다.
RUN pip install --no-cache-dir --upgrade pip  && pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=web-build /build/dist ./static

# ID-19 — 기동 속도 확보를 위해 미리 바이트코드를 만들어 둔다
RUN python -m compileall -q ./app

# ID-6 — 비루트 실행. 볼륨 마운트 지점만 소유권을 넘긴다.
RUN groupadd --gid 10001 appuser \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin appuser \
 && mkdir -p /app/data /app/logs \
 && chown -R 10001:10001 /app/data /app/logs

USER 10001:10001

ENV DATABASE_PATH=/app/data/trip.db \
    LOG_DIR=/app/logs \
    STATIC_DIR=/app/static \
    PORT=8200

EXPOSE 8200

# ---------------------------------------------------------------------------
# 🔴 --workers 1 은 의도적으로 하드코딩되어 있다 (ID-4 / SP-5).
#
#    서킷 브레이커(L1) · IP 레이트 리밋(C4) · job 동시 실행 세마포어(L3) 가
#    전부 **프로세스 내 상태**다. 워커를 2개 이상으로 늘리면 각 워커가 따로
#    세기 시작해 이 통제들이 **오류 없이 조용히 무력화**된다.
#    (레이트 리밋이 사실상 워커 수만큼 곱해진다.)
#
#    늘리려면 Redis(공유 상태) + PostgreSQL 전환이 선행되어야 한다.
#    자세한 내용: aidlc-docs/construction/u1-trip-backend/nfr-design/
#                nfr-design-patterns.md §2 SP-5
# ---------------------------------------------------------------------------
#
# `--factory` 를 쓰는 이유: 모듈 수준 `app = create_app()` 은 import 만으로
# DB 생성·마이그레이션·클라이언트 풀 생성을 일으키는 부작용이 있어 제거했다.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8200", "--workers", "1"]
