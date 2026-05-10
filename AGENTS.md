# AGENTS.md

> 이 파일은 모든 AI 코딩 에이전트(Codex CLI · Cursor · Copilot · Gemini CLI 등)가 읽는 표준 컨텍스트 파일입니다.
> Claude Code 는 별도로 `CLAUDE.md` 를 참조하지만, 본 파일을 정본으로 두고 CLAUDE.md 는 stub 으로 유지합니다.

---

## 1. 프로젝트 개요

**유출지하수 공급-수요 매칭 플랫폼** — 2026 서울시 빅데이터 활용 경진대회 *창업 부문* 출품작.
서울시 공공데이터 + AI 수요예측·매칭 최적화로 미사용 유출지하수와 비음용수 수요처를 매칭하는 B2G 분석 SaaS.

**진행 단계**: MVP / 1인 / 마감 2026-05-13 18:00.

### 정본 문서 (수정·기능 추가 전 반드시 일독)

- `docs/PRD.md` — 제품 요구사항 (Arc Hard Fact 프레임)
- `docs/TSD.md` — 기술 설계
- `docs/Database.md` — 스키마
- `docs/TEST_CASE.md` — 테스트 케이스 35건

---

## 2. 기술 스택 (절대 임의 변경 금지)

- 언어: **Python 3.11** (`>=3.11,<3.12`)
- 패키지·환경: **uv**
- 프론트: **Streamlit** + **Folium**
- 데이터: pandas + DuckDB + Parquet, geopandas
- ML: **LightGBM** (잔차 보정) + scikit-learn + shap + refet (ET₀)
- 최적화: **PuLP** + CBC
- 배포: **Streamlit Cloud**
- 린터·포매터: **Ruff**
- 타입체커: **Pyright (strict)**
- 테스트: pytest

기술 스택 변경이 필요하면 사용자에게 먼저 제안하고 확인받을 것. 임의 추가·교체 금지.

---

## 3. 명령 (이 명령들이 작업 정의)

### 3.1 환경 셋업

```bash
uv sync                      # 의존성 설치 + .venv 생성
uv run pre-commit install    # git hook 설치 (최초 1회)
```

### 3.2 작업 완료 전 *반드시* 통과해야 하는 명령

```bash
uv run ruff check --fix .    # 린트 + 자동수정
uv run ruff format .         # 포매팅
uv run pyright               # strict 타입체크
uv run pytest                # 테스트 + 커버리지 60% 이상
```

위 4개가 모두 0 exit code 가 아니면 작업이 끝난 것이 아니다. 절대 "lint 무시하고 일단 커밋" 하지 말 것.

### 3.3 앱 실행

```bash
uv run streamlit run app/main.py
```

### 3.4 ETL 일괄 실행

```bash
uv run python -m etl.pipelines extract
uv run python -m etl.pipelines transform
uv run python -m etl.pipelines train
uv run python -m etl.pipelines match
```

---

## 4. 코드 스타일 — 강제 규칙

### 4.1 Ruff (`pyproject.toml [tool.ruff]`) 가 정의

`select = ["ALL"]` + 실용 예외만 ignore. 자세한 내용은 `pyproject.toml` 의 `[tool.ruff.lint]` 섹션 주석 참고.

### 4.2 절대 규칙

- **타입 힌트 100%** — 모든 public 함수/메서드의 인자·반환에 타입 힌트. Pyright strict 통과는 타협 없음.
- **`from __future__ import annotations`** — 모든 `.py` 파일 최상단에 자동 삽입됨 (Ruff `required-imports`).
- **상대 import 금지** — `from app.foo import bar` ✅ / `from .foo import bar` ❌ (Ruff TID).
- **docstring 스타일: Google** — public 함수·클래스 (private 면제).
- **라인 길이 100자** — 포매터가 자동 처리.
- **따옴표: double quote** — 포매터가 자동.
- **들여쓰기: 4 spaces**.
- **`print` 금지 (`etl/` 제외)** — `logging` 사용. ETL 스크립트만 print 허용.
- **pdb·breakpoint 금지** — pre-commit 에서 차단됨.
- **assert 는 테스트에서만** — 프로덕션 코드는 `if not X: raise ValueError(...)`.
- **매직 넘버 금지** — 상수로 추출 (단, `0`/`1`/임계값은 ignore 처리됨).
- **Pydantic / dataclass 우선** — 자유 dict 보다 typed model.

### 4.3 import 순서 (Ruff isort 자동)

```
# 1. __future__
from __future__ import annotations

# 2. stdlib
import os
from pathlib import Path

# 3. third-party
import pandas as pd
import streamlit as st

# 4. first-party
from app.services import ForecastService
from etl.transform import normalize_supplier
```

### 4.4 파일·디렉토리 규칙

`docs/TSD.md §3` 준수. 새 모듈은 반드시 다음 위치 중 하나:

- `app/` — Streamlit UI, 컴포넌트, 서비스 wrapper
- `etl/` — extract / transform / pipelines
- `models/forecast/` — 수요예측
- `models/matching/` — 매칭 최적화
- `tests/` — pytest

루트에 `.py` 파일 추가 금지.

---

## 5. 테스트 규칙

- 새 함수·메서드 작성 시 `tests/` 에 대응 테스트 추가. 커버리지 60% 미만이면 `uv run pytest` 가 실패.
- 테스트 파일명: `tests/test_*.py` (pre-commit `name-tests-test` 강제).
- ML/매칭 핵심 로직은 `docs/TEST_CASE.md` 의 TC-FCT-*, TC-MTC-* 와 매핑되는 테스트 작성.
- 외부 API (서울 열린데이터광장, 기상청) 호출은 fixture 로 mock — 네트워크 의존 테스트 금지.

---

## 6. 데이터 다루기

- 원본 데이터는 `data/raw/`, `data/bronze/` (gitignore 됨). 절대 git 에 평문 커밋 금지.
- 가공 결과는 `data/silver/`, `data/gold/` Parquet. 1MB 이상이면 `.gitignore` 예외 추가 후 git LFS.
- 좌표계는 모두 **EPSG:4326** (WGS84). EPSG:5179 등으로 들어오면 ETL Step 2 에서 변환 후 저장.
- 결측치 처리는 `etl/transform/` 에서 일괄 — 모델 코드 안에서 NaN 처리 금지.

---

## 7. 보안 (절대 위반 금지)

- API 키 / 토큰 / secret 평문 금지. 모두 `.streamlit/secrets.toml` 또는 환경변수.
- `.env`, `.streamlit/secrets.toml`, `data/raw/` 는 `.gitignore` 에 포함.
- pre-commit `gitleaks` 가 차단하지만, 그 전에 사람이 한 번 더 확인.
- `SQL` / 파일 경로에 사용자 입력을 직접 끼워넣기 금지 (parametrize 또는 `Path()` 사용).

---

## 8. 작업 워크플로우 (커밋 전 체크리스트)

1. [ ] 작업 파일을 ruff check + ruff format 통과
2. [ ] pyright strict 통과
3. [ ] 새 함수에 대응 테스트 추가 + pytest 통과 (커버리지 60%+)
4. [ ] `docs/TEST_CASE.md` 의 관련 TC 가 영향받았다면 본문 업데이트
5. [ ] 커밋 메시지: `<type>: <한 줄 요약>` (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`)
6. [ ] `git commit` — pre-commit 자동 실행
7. [ ] pre-commit 실패 시 fix → 재커밋. **`--no-verify` 절대 금지**.

---

## 9. 안 하는 것 (Don'ts)

- 린트·타입체크·테스트 우회 (`# noqa` 남발, `# type: ignore` 무근거 추가, `--no-verify`).
- PRD/TSD/Database/TEST_CASE 에 없는 기능 임의 추가. 필요하면 사용자에게 먼저 제안.
- 새 의존성 임의 추가. `pyproject.toml [project] dependencies` 에 적히지 않은 패키지 import 시 사용자 컨펌 필수.
- 공공 데이터 라이선스 표시 누락.
- "임시" 또는 "일단" 코드 — 작성하면 커밋 전에 정리하고 들어갈 것.
- README/CHANGELOG/문서 자동 생성 — 사용자 명시 요청 시에만.

---

## 10. 변경 이력

| 버전 | 날짜       | 변경                                                         |
| ---- | ---------- | ------------------------------------------------------------ |
| 0.1  | 2026-05-10 | 초안. Ruff(strictest) + Pyright(strict) + uv + pre-commit 정의 |
