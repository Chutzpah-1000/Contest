# Autonomous Improvement Log

## 초기 상태 파악 (2026-05-18)

### 레포지토리 구조
- **앱**: `app/main.py` (Streamlit entry), `app/components/` (cards, kakao_map, sidebar), `app/services/` (data, matching, roi)
- **ETL**: `etl/pipelines.py`, `etl/transform/`, `etl/sample_data.py`
- **모델**: `models/forecast/`, `models/matching/`
- **테스트**: `tests/` — 28개 통과, 커버리지 64.78% (>60% 기준 통과)

### 실행/검증 명령
```bash
uv run ruff check --fix .    # 린트 (현재: All checks passed!)
uv run ruff format .          # 포매팅
uv run pyright                # 타입체크 (0 errors, 138 warnings)
uv run pytest                 # 28 passed, 64.78% coverage
uv run streamlit run app/main.py  # 앱 실행
```

### 현재 심사점수 (Round 0 기준)
| 영역 | 점수 | 근거 |
|------|------|------|
| 기능 완성도 | 7 | KPI 카드·지도·사이드바 완성, 매칭 흐름 표시, 검색 작동 |
| 사용자 경험 | 5 | 지도가 단순 마커+InfoWindow, 좌패널 없음, 마커가 원형 |
| 안정성/버그 | 7 | 28 테스트 통과, Kakao SDK 오류 핸들링 존재 |
| 성능 | 7 | 캐시된 솔루션 3종, 데이터 로딩 빠름 |
| 코드 품질 | 8 | ruff clean, pyright 0 errors, 타입힌트 100% |
| 완성도/폴리시 | 6 | 기본 디자인 토큰 적용, 마커 스타일 단순 |

---

## Round 1

- **Lowest area**: 사용자 경험 (5점)
- **Planned improvement**: 네이버지도 스타일 UI — 지도 좌측 공급처 목록 패널 + 핀 마커 + 클릭 시 상세 패널 + 줌 컨트롤 + 범례

### Files changed
- `app/components/kakao_map.py` — `_HTML_TEMPLATE` 전면 재설계

### 변경 내용
1. **레이아웃**: 좌측 280px 패널 + 우측 지도(flex:1) — 네이버지도 분할 구조
2. **공급처 목록**: 발생량 순 정렬 리스트, 매칭/미매칭 뱃지, 클릭 시 지도 이동
3. **핀 마커**: 공급처 → 테어드롭(핀) 형태 SVG. 수요처 → 원형 유지
4. **상세 패널**: 마커/목록 클릭 시 좌패널에 상세정보(발생량·수질등급·신고상태) 표시
5. **줌 컨트롤**: 우상단 +/- 버튼 (네이버지도 스타일)
6. **범례**: 우하단 마커 유형 범례

### Verification
- Ruff: All checks passed
- Pyright: 0 errors
- Pytest: 28 passed, coverage 64.78%

### Commit
- `polish: 네이버지도 스타일 지도 UI — 좌측 목록 패널·핀 마커·상세 패널·범례`

---

## Round 2 — KPI 카드·Streamlit 폴리시
- **Branch**: `agent/round-2-page-polish`
- KPI 카드 캡션·섹션 레이블·수요 충족률 data 색·Streamlit 크롬 숨김

## Round 3 — 사이드바 브랜딩
- **Branch**: `agent/round-3-sidebar-polish`
- 브랜딩 헤더 (💧)·컨트롤 라벨 통일·데이터 출처 푸터

## Round 4 — 안정성 개선
- **Branch**: `agent/round-4-stability`
- `_filter_by_solution_id` pandas native 필터·`main.py` FileNotFoundError 오류 경계

## Round 5 — metric_value 개선
- **Branch**: `agent/round-5-metric-value`
- pandas native 필터·불필요한 normalize 임포트 제거

## Round 6 — 지도 필터 탭
- **Branch**: `agent/round-6-map-section-header`
- 지도 패널에 "전체/매칭됨" 필터 탭 추가

## Round 7 — 섹션 레이블
- **Branch**: `agent/round-7-map-header-label`
- 지도 섹션 레이블 추가·H1 인라인 스타일 정리

## Round 8 — 테스트 커버리지
- **Branch**: `agent/round-8-test-coverage`
- 8개 테스트 추가 (커버리지 63.8% → 65.1%)

## Round 9 — 통계 바
- **Branch**: `agent/round-9-panel-stats`
- 지도 패널에 발생량 합계·매칭 건수 통계 바 추가

## Round 10 — Kakao 지도 검색·줌 성능 (2026-05-18)

- **Branch**: `agent/round-10-map-perf`
- **Scores (before → after)**:
  - 기능 완성도: 8 → 8
  - 사용자 경험: 8 → 9
  - 안정성: 8 → 8
  - 성능: 8 → 9
  - 코드 품질: 9 → 9
  - 완성도: 8 → 8
- **Lowest area**: 성능 — 사이드바 검색 키스트로크 단위 Streamlit rerun + iframe 통째 재주입, 지도 줌/팬 시 모든 마커·폴리라인 상시 렌더링.

### Planned improvement
사용자가 명시한 두 가지 카카오지도 UX 문제(검색 딜레이, 줌/팬 렉)를 풀기 위한 점진 개선.

### Files changed
- `app/components/sidebar.py` — 검색 입력을 `st.form` 으로 감싸 명시적 제출(`검색`/`초기화` 버튼)에만 rerun 발생. 순수 상태 전이 함수 `resolve_search_state()` 분리.
- `app/components/kakao_map.py`
  - `@st.cache_data(show_spinner=False, max_entries=16)` 로 `build_kakao_map_html` 결과 캐싱 → 동일 (suppliers/parks/roads/flows/search_term/js_key) 입력에 대해 JSON 직렬화·HTML 빌드 스킵.
  - `kakao.maps.event.addListener(_map, 'idle', ...)` 에 100ms `setTimeout` 쓰로틀 부착, `_map.getBounds()` 밖의 park/road 마커와 flow 폴리라인을 `setMap(null)` 토글 → 줌·팬 시 DOM 부하 감소.
  - `level >= 8` 일 때 flow 폴리라인 일괄 숨김 → 시 전체 줌아웃에서 폴리라인 클러터 제거.
  - `nameLower[]` 사전 캐시로 검색 시 `(s.name||'').toLowerCase()` 매 반복 제거.
  - `_applyFilter()` DOM display 변경을 `requestAnimationFrame` 으로 묶어 layout thrash 완화.
- `tests/test_sidebar_search.py` — `resolve_search_state()` 상태 전이 5건 테스트 추가 (idle/submit/clear/clear-over-submit/empty).

### Verification
- `uv run ruff check .` → All checks passed
- `uv run ruff format --check .` → 41 files already formatted
- `uv run pyright` → 0 errors, 136 warnings (baseline 그대로)
- `uv run pytest` → 41 passed (36 → 41), coverage 64.68% → **65.00%**

### Manual UX 측정 (수동, 사용자 환경에서 검증 필요)
- 검색: 종전 키스트로크마다 iframe 재주입 → form 도입 후 제출 시 1회만. 캐시 적중 시 동일 검색어 재제출은 HTML 빌드 0회.
- 줌/팬: idle 100ms 후 bounds 밖 마커 setMap(null). 시 전체 줌아웃 시 flow 폴리라인 0개 표시.
- 필터 탭 토글: rAF로 DOM display 배치 → 클러스터 rebuild 1회.

### Commit
- `improve(map): 검색 폼 디바운스·HTML 캐싱·idle 뷰포트 컬링으로 Kakao 지도 체감 성능 개선`

### Notes (다음 라운드 후보)
- 사이드바에 자동완성 드롭다운 (form 도입으로 한 스텝 미스가 됨 — Phase 2 가치).
- ⓘ 출처 popover (Design.md §5 1급 UX 미적용 영역).
- FR-02 LightGBM 30-day 예측 데모 스텁 (Phase 2 우선이지만 시연 와우 포인트 가능).
- KPI 카드 hover 시 dataset 출처·formula 표시 (Design.md §5).

---

## Round 11 — 사이드바 검색 폼 폴리시 (2026-05-18)

- **Branch**: `agent/round-11-sidebar-polish`
- **Scores (before → after)**:
  - 기능 완성도: 8 → 8
  - 사용자 경험: 9 → 9
  - 안정성: 8 → 8
  - 성능: 9 → 9
  - 코드 품질: 9 → 9
  - 완성도: 8 → 9
- **Lowest area**: 완성도 — `st.form_submit_button` 두 개가 Streamlit 기본 빨강 톤이라 Design.md §3 monochrome 톤과 어색. placeholder 도 프롬프트 명시 문구 미반영.

### Planned improvement
프롬프트 §76-78 "먼저 할 일" 잔여 항목(검색·초기화 버튼 디자인, placeholder Heliocity 변경, 한국어 검색 가능) 흡수.

### Files changed
- `app/components/sidebar.py`
  - 사이드바 폼 버튼 톤 CSS 추가: 흰 배경·1px border·`#0071E3` hover/focus·focus ring (사이드바 스코프 `[data-testid="stSidebar"] [data-testid="stForm"] button`)
  - placeholder `"예: 서울 광역자원순환센터"` → `"건물명으로 검색 (예: Heliocity)"`
- `tests/test_sidebar_search.py`
  - `_find_building()` 한국어 부분일치 회귀 테스트 추가 (`"헬리오"` → "강남 헬리오시티")
  - import: `pandas`, `_find_building`

### Verification
- `uv run ruff check --fix .` → All checks passed
- `uv run ruff format .` → 41 files left unchanged
- `uv run pyright` → 0 errors, 136 warnings (baseline 그대로)
- `uv run pytest` → **42 passed** (41 → 42), coverage 65.00% → **65.72%**

### Commit
- `polish(sidebar): 검색 폼 버튼 톤·placeholder + 한국어 검색 테스트`

### Notes (다음 라운드 후보 풀)
- 안정성 후보 A1·A2·A3 (kakao_map 회귀 테스트, sidebar 빈 DF 가드, load_app_data FNF 가드)
- 기능 완성도 B1 (ⓘ 출처 popover) — Design.md §5 1급 UX
- 완성도 C1·C2·C3 (모바일 KPI 가독성, H1 spacing 토큰, footer GitHub 링크)
- 코드 품질 D1·D2 (kakao_map 매직상수·sidebar CSS 모듈상수)
- 다음 라운드 후보 1순위: **A1 kakao_map 회귀 테스트** (안정성·코드품질 동시 영향)

---

## Round 12 — Kakao 지도 Round 10 성능 회귀 가드 (2026-05-18)

- **Branch**: `agent/round-12-map-regression-test`
- **Scores (before → after)**:
  - 기능 완성도: 8 → 8
  - 사용자 경험: 9 → 9
  - 안정성: 8 → 9
  - 성능: 9 → 9
  - 코드 품질: 9 → 9
  - 완성도: 9 → 9
- **Lowest area**: 안정성 — Round 10 의 idle 뷰포트 컬링·rAF DOM 배치·플로우 줌 컷오프가 HTML 템플릿 문자열에 들어가 있는데, 누가 실수로 제거하면 검증 없이 통과. 회귀 가드 0건.

### Planned improvement (후보 풀 A1 소진)
`tests/test_app.py` 에 `test_kakao_map_html_includes_round10_perf_tokens` 추가 — `build_kakao_map_html()` 결과에 `FLOW_HIDE_LEVEL=8`, `_scheduleCull`, `_cullDemand`, `requestAnimationFrame`, `'idle'` 5개 토큰이 모두 포함되는지 검증.

### Files changed
- `tests/test_app.py` — 회귀 테스트 1건 추가

### Verification
- `uv run ruff check --fix .` → All checks passed
- `uv run ruff format .` → 41 files left unchanged
- `uv run pyright` → 0 errors, 136 warnings
- `uv run pytest` → **43 passed** (42 → 43), coverage 65.72% 유지

### Commit
- `test(kakao_map): Round 10 성능 토큰 회귀 가드 (idle·rAF·flow level cutoff)`

### Notes (다음 라운드 후보 풀 잔여)
- 안정성 A2·A3 (sidebar 빈 DF, load_app_data FNF — 기존 가드의 회귀 테스트)
- 기능 완성도 B1·B2·B3 (ⓘ 출처 popover, 라디우스 메타, ETL mtime)
- 완성도 C1·C2·C3 (모바일 KPI, H1 spacing 토큰, footer)
- 코드 품질 D1·D2, 성능 E1
- 다음 라운드 1순위: **B1 ⓘ 출처 popover** (Design.md §5 1급 UX, 기능 완성도 8 → 9 기대)

---

## Round 13 — KPI 카드 ⓘ 출처 popover (2026-05-18)

- **Branch**: `agent/round-13-kpi-source-popover`
- **Scores (before → after)**:
  - 기능 완성도: 8 → 9
  - 사용자 경험: 9 → 9
  - 안정성: 9 → 9
  - 성능: 9 → 9
  - 코드 품질: 9 → 9
  - 완성도: 9 → 9
- **Lowest area**: 기능 완성도 — KPI 4종 숫자만 노출, 데이터셋·계산식·갱신주기가 caption 한 줄로만 표현. Design.md §5 "모든 숫자는 단위+출처를 1급 UX" 미충족.

### Planned improvement (후보 풀 B1 소진)
4개 epiphany KPI 카드 caption 영역을 `<details><summary>` 디스클로저로 교체. summary 에 ⓘ 아이콘 + 기존 caption 표시, 펼치면 데이터셋 · 계산식 · 갱신주기 3행이 노출.

### Files changed
- `app/components/cards.py`
  - `NamedTuple _KpiSource(caption, dataset, formula, refresh)` 도입.
  - `_KPI_CAPTIONS` 4개 문자열을 `_KPI_SOURCES: tuple[_KpiSource, ...]` 로 확장 (서울 열린데이터광장·KEPCO 배출계수·하수도사용조례·PuLP 최적해 출처 명시).
  - `_kpi_source_html(src)` 헬퍼: `<details class="kpi-source">` + summary(ⓘ + caption) + body(3행) 마크업.
  - `_DESIGN_CSS` 에 `.kpi-source*` CSS 추가 — 닫힘/열림 상태 색상, focus ring, info-icon 원형 border.

### Verification
- `uv run ruff check .` → All checks passed (`×` → `*` 로 RUF001 회피)
- `uv run ruff format .` → 1 file reformatted (cards.py), 40 unchanged
- `uv run pyright` → 0 errors, 136 warnings
- `uv run pytest` → **43 passed** 유지, coverage 65.35%

### Commit
- `improve(cards): KPI 4종 카드에 데이터셋·계산식·갱신주기 ⓘ 출처 disclosure`

### Notes (다음 라운드 후보 풀 잔여)
- 안정성 A2·A3 (sidebar 빈 DF, load_app_data FNF 회귀 가드)
- 기능 완성도 B2·B3 (라디우스 메타, ETL mtime)
- 완성도 C1·C2·C3, 코드 품질 D1·D2, 성능 E1
- 동률 영역 모두 9점. 다음 라운드는 사용자 핵심 플로우(검색·매칭) 영향이 큰 **B2 라디우스 메타**(매칭 솔루션 요약 카드) 또는 **A2 sidebar 빈 DF 회귀 테스트**.

---

## Round 14 — 매칭 솔루션 카드 라디우스 메타 (2026-05-18)

- **Branch**: `agent/round-14-match-radius-meta`
- **Scores (before → after)**:
  - 기능 완성도: 9 → 9
  - 사용자 경험: 9 → 9
  - 안정성: 9 → 9
  - 성능: 9 → 9
  - 코드 품질: 9 → 9
  - 완성도: 9 → 9 (내부 신뢰도 ↑)
- **Lowest area**: 동률 9. 사용자 핵심 플로우(라디우스 슬라이더 변경 → 솔루션 갱신)의 가시성이 약했음 — 현재 어떤 반경의 솔루션을 보고 있는지/매칭 라인이 몇 건인지 카드에 표시 0건.

### Planned improvement (후보 풀 B2 소진)
`render_solution_summary` 시그니처에 `radius_m: int | None = None` 추가. 섹션 헤더에 `반경 1km · 매칭 N건` 메타를 우측 정렬로 표시. `main.py` 호출부에서 사이드바 radius_m 전달.

### Files changed
- `app/components/cards.py`
  - `.section-header` flex 레이아웃 CSS 추가 (label 좌측 · meta 우측).
  - `.section-meta` 톤 (muted 11px) 추가.
  - `render_solution_summary` 시그니처에 `radius_m` 옵션 추가, 메타 HTML 분기 렌더.
- `app/main.py`
  - `render_solution_summary(selected.solution, selected.flows, radius_m=radius_m)` 로 호출 갱신.

### Verification
- `uv run ruff check --fix .` → 1 error fixed (자동), 0 remaining
- `uv run ruff format .` → 1 file reformatted, 40 unchanged
- `uv run pyright` → 0 errors, 136 warnings
- `uv run pytest` → **43 passed** 유지, coverage 64.99%

### Commit
- `improve(cards): 매칭 솔루션 요약 카드에 선택 반경·매칭 건수 메타 표시`

### Notes (다음 라운드 후보 풀 잔여)
- 안정성 A2·A3 (sidebar 빈 DF, load_app_data FNF 회귀 가드)
- 기능 완성도 B3 (ETL mtime)
- 완성도 C1·C2·C3, 코드 품질 D1·D2, 성능 E1
- 다음 라운드 후보: **A2 sidebar 빈 DF 회귀 테스트** (안정성 회귀 가드) — 코드 변경 없이 테스트만 추가, 안전.

---

## 최종 점수 (Round 14 기준)
| 영역 | 점수 |
|------|------|
| 기능 완성도 | 9 |
| 사용자 경험 | 9 |
| 안정성/버그 | 9 |
| 성능 | 9 |
| 코드 품질 | 9 |
| 완성도/폴리시 | 9 |
