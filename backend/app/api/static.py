"""L7 StaticAssetHandler — 웹 정적 자산 서빙 + SPA catch-all.

근거:
    UD-8 / Q8=A   단일 컨테이너에서 FastAPI 가 `web/dist` 를 서빙한다
    ND-8 / PP-3   해시 자산은 `immutable` 영구 캐시, `index.html` 은 `no-cache`
    SEC-09        디렉터리 리스팅 없음. 경로 이탈 차단
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

IMMUTABLE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"
_HASHED_DIRS = ("assets",)  # Vite 기본 산출 경로


class CachingStaticFiles(StaticFiles):
    """PP-3 — 해시 파일명 자산과 진입점에 서로 다른 캐시 정책을 적용한다."""

    def file_response(self, full_path, stat_result, scope, status_code: int = 200):  # type: ignore[no-untyped-def]
        response = super().file_response(full_path, stat_result, scope, status_code)
        name = Path(full_path).name
        parent = Path(full_path).parent.name
        if parent in _HASHED_DIRS and "." in name:
            response.headers["Cache-Control"] = IMMUTABLE
        else:
            response.headers["Cache-Control"] = NO_CACHE
        return response


def build_spa_router(static_dir: Path) -> APIRouter:
    """SPA catch-all. `/api/*` 를 가로채지 않도록 마지막에 등록한다."""
    router = APIRouter()
    index_file = static_dir / "index.html"

    @router.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str, request: Request):  # type: ignore[no-untyped-def]
        # /api 경로가 여기까지 왔다면 라우트가 없는 것이다 — 404 를 JSON 으로 돌려준다.
        if full_path.startswith("api/") or full_path.startswith("api"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if not index_file.is_file():
            return JSONResponse(
                {
                    "detail": (
                        "웹 자산이 빌드되지 않았습니다. "
                        "개발 중에는 Vite dev 서버(5273)를 사용하세요."
                    )
                },
                status_code=404,
            )
        return FileResponse(index_file, headers={"Cache-Control": NO_CACHE})

    return router
