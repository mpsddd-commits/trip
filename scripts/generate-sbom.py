#!/usr/bin/env python3
"""SBOM 생성 (ID-18 / SEC-10).

SEC-10 요건: "프로덕션 배포용 Software Bill of Materials 를 생성할 것"

외부 도구 설치 없이 표준 라이브러리만으로 CycloneDX 1.5 형식의 최소 SBOM 을
만든다. 구성 요소는 다음에서 읽는다.
  - Python : backend/requirements.txt (정확한 버전 고정 — SEC-10)
  - Node   : web/package-lock.json    (u2 가 있을 때만)

사용법:  python scripts/generate-sbom.py [출력경로]
기본 출력: sbom.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_PIN = re.compile(r"^\s*([A-Za-z0-9._-]+)(?:\[[^\]]*\])?\s*==\s*([^\s#]+)")


def python_components() -> list[dict]:
    path = ROOT / "backend" / "requirements.txt"
    if not path.is_file():
        return []
    components = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#") or not line.strip():
            continue
        match = _PIN.match(line)
        if match is None:
            # SEC-10 — 버전이 고정되지 않은 항목은 그냥 넘기지 않고 드러낸다.
            print(f"[warn] 버전이 고정되지 않은 의존성: {line.strip()}", file=sys.stderr)
            continue
        name, version = match.group(1), match.group(2)
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name.lower()}@{version}",
                "scope": "required",
            }
        )
    return components


def node_components() -> list[dict]:
    path = ROOT / "web" / "package-lock.json"
    if not path.is_file():
        print("[info] web/package-lock.json 없음 (u2 미생성). Node 구성 요소를 건너뜁니다.")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    components = []
    for key, meta in (data.get("packages") or {}).items():
        if not key.startswith("node_modules/"):
            continue
        name = key.removeprefix("node_modules/")
        version = meta.get("version")
        if not version:
            continue
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:npm/{name}@{version}",
                "scope": "optional" if meta.get("dev") else "required",
            }
        )
    return components


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sbom.json"
    components = python_components() + node_components()

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "trip",
                "version": "0.1.0",
                "description": "여행 일정 생성 + 시간표 + 네이버지도 연동",
            },
            # ⚠️ 타임스탬프는 생성 시점에 셸에서 주입하는 편이 재현성에 유리하다.
            #    여기서는 의도적으로 넣지 않는다 (동일 입력 → 동일 산출물).
            "tools": [{"name": "generate-sbom.py", "version": "1.0"}],
        },
        "components": sorted(components, key=lambda c: (c["type"], c["name"])),
    }

    output.write_text(json.dumps(sbom, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SBOM 생성 완료: {output} (구성 요소 {len(components)}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
