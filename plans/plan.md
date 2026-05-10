# Plan: 1인 D-3 개발용 plan.md 생성

## Context

사용자는 2026 서울시 빅데이터 활용 경진대회 _창업 부문_ 출품 (마감 **2026-05-13 18:00**) 1인 프로젝트를 진행 중. 오늘은 **2026-05-10 (D-3)**.

다음 산출물들이 이미 정비되어 있음:

- `docs/PRD.md` v0.2 — Hard Fact 아키타입, 서울시(B2G) wedge, 정보 비대칭 해소 MVP
- `docs/TSD.md` v0.1 — Streamlit + Parquet/DuckDB 단일 스택, ForecastService/MatchingService 시그니처 명시
- `docs/Database.md` v0.1 — Bronze/Silver/Gold 11개 테이블 스키마
- `docs/TEST_CASE.md` v0.1 — 35개 TC, P0 15건 / P1 15건 / P2~3 5건
- `AGENTS.md` — Codex 정본 (Ruff `select=ALL` strict, Pyright strict, uv, pre-commit)
- `pyproject.toml`, `.pre-commit-config.yaml`

남은 빈자리는 **"무엇을 어떤 순서로, 어디에, 어떤 시그니처로 구현할 것인가"** 의 sequenced playbook. Codex 가 이 문서 하나만 들고 즉시 구현에 들어갈 수 있도록 작성한다.

---

## Decision Summary

| 결정          | 선택                                   | 사유                                                 |
| ------------- | -------------------------------------- | ---------------------------------------------------- |
| 산출 위치     | `plans/plan.md`                        | 프로젝트 `plans/` 디렉토리 비어있음. 자연스러운 위치 |
| 시간 분할     | Day 0 (지금) → D-3 → D-2 → D-1 → D-Day | TEST_CASE §11 일정 그대로 채택                       |
| Stretch 처리  | 명시적 Deferred 섹션 분리              | Codex 가 임의 추가하지 않도록                        |
| TC 연결       | 각 Task 마다 acceptance TC ID 명시     | 완료 기준 명확화                                     |
| 함수 시그니처 | TSD §5 그대로 인용                     | 중복 정의·표류 방지                                  |

**Stretch 디폴트 = Deferred** (FR-05 PDF / TC-FCT-04 SHAP / TC-MAP-04 시계열 / TFT / TC-E2E-02 박상무).

이는 explore audit 의 시간 추산 (32h 버퍼) 을 안전 측으로 잡은 결정. 사용자가 stretch 를 in-scope 로 끌어올리고 싶으면 plan.md 작성 후 알려주면 됨.

---

## Critical Files (참조용·이미 존재)

```
docs/PRD.md            — 제품 요구·페르소나·KPI
docs/TSD.md            — 함수 시그니처(§5), 디렉토리(§3), 파이프라인(§4)
docs/Database.md       — 테이블 스키마(§3,5), 참조 데이터(§4)
docs/TEST_CASE.md      — TC 35건, 일정(§11)
AGENTS.md              — Codex 코드 규칙·금지·명령
pyproject.toml         — 의존성·도구 설정
.pre-commit-config.yaml
```

신규 생성:

```
plans/plan.md          — 본 작업의 산출물
```

---

## plan.md 본문 사양 (Codex 가 읽고 실행)

작성할 plan.md 의 정확한 구조와 내용:

### 0. Mandate

한 문단:

- 본 문서는 Codex/구현 에이전트의 **단일 진실 소스**
- 코드 규칙은 `AGENTS.md`, 제품 의도는 `docs/PRD.md`, 함수 시그니처는 `docs/TSD.md §5`, 스키마는 `docs/Database.md`, 합격 기준은 `docs/TEST_CASE.md`
- 본 plan.md 는 **"무엇을 언제 어디에"**, 다른 문서들은 **"어떻게·왜"**

### 1. Day 0 Prereqs (Codex 시작 전 사용자 체크)

- [x] 서울 열린데이터광장 API 키 발급 (data.seoul.go.kr)
- [x] 기상청 ASOS Open API 키 발급 (data.kma.go.kr)
- [x] GitHub repo 생성 (private 권장) 후 main 브랜치
- [x] Streamlit Cloud 계정 → GitHub 연동
- [x] 로컬: `uv` 설치 (`pip install uv` 또는 brew/scoop)
- [ ] `.streamlit/secrets.toml` 템플릿 작성 (gitignore 확인)
- [ ] `git lfs install` (Parquet 1MB+ 대비)

미충족 항목이 있으면 Codex 가 시작 전 사용자에게 알린다.

### 2. Day 1 — D-3 (2026-05-10): Bootstrap + ETL Silver

**산출 목표**: `data/silver/*.parquet` 모두 생성, ETL 단위 테스트 통과.

| Task  | 산출                                              | 함수·파일                                                                                                            | TC                 | 추정 |
| ----- | ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------ | ---- |
| T1.1  | uv 환경 동기화                                    | `uv sync` 실행, `.venv/`, `uv.lock`                                                                                  | —                  | 0.3h |
| T1.2  | 디렉토리 골격                                     | `app/`, `etl/extract/`, `etl/transform/`, `models/forecast/`, `models/matching/`, `tests/` 빈 패키지 + `__init__.py` | —                  | 0.2h |
| T1.3  | `.gitignore` + `.streamlit/secrets.toml.template` | secrets·data/raw·data/bronze·.venv 제외                                                                              | TC-SEC-01          | 0.2h |
| T1.4  | 서울 데이터 추출                                  | `etl/extract/seoul_data.py` — 4종 CSV 다운로드 (groundwater, parks, roads, buildings)                                | TC-DATA-01         | 1.5h |
| T1.5  | 기상청 추출                                       | `etl/extract/kma_asos.py` — 월별 종관관측 + SPEI                                                                     | TC-DATA-01         | 1.0h |
| T1.6  | bronze→silver transform                           | `etl/transform/normalize.py` — EPSG:4326 통일, 결측치 처리                                                           | TC-DATA-02, 04, 05 | 1.5h |
| T1.7  | 신고대상 식별                                     | `etl/transform/suppliers.py` — 21층 ∨ 10만㎡ 필터, 광역자원순환센터·창동 식별 검증                                   | TC-DATA-03         | 1.0h |
| T1.8  | 수요처 정제                                       | `etl/transform/demand.py` — 공원·도로 좌표·면적·작물계수 join                                                        | —                  | 1.0h |
| T1.9  | 파이프라인 진입점                                 | `etl/pipelines.py` — `extract` / `transform` 서브커맨드                                                              | —                  | 0.5h |
| T1.10 | 테스트 작성                                       | `tests/test_etl.py` — Bronze→Silver 픽스처 5개                                                                       | TC-DATA-01~05      | 1.5h |
| T1.11 | 전 도구 통과                                      | `ruff check --fix && ruff format && pyright && pytest` 모두 0                                                        | AGENTS §8          | 0.5h |

**Day 1 합격선**: `data/silver/{suppliers, supply_history, demand_parks, demand_roads, weather_monthly, drought_index}.parquet` 6개 생성. 모든 TC-DATA P0 통과.

### 3. Day 2 — D-2 (2026-05-11): 모델 + Gold 사전계산

| Task  | 산출               | 함수·파일                                                                       | TC               | 추정 |
| ----- | ------------------ | ------------------------------------------------------------------------------- | ---------------- | ---- |
| T2.1  | ET₀ 베이스라인     | `models/forecast/baseline.py::et0_penman_monteith()` — TSD §5.1 시그니처 그대로 | TC-FCT-01        | 1.5h |
| T2.2  | 베이스라인 수요    | `models/forecast/baseline.py::baseline_demand_monthly()`                        | TC-FCT-02        | 0.5h |
| T2.3  | LightGBM 잔차 모델 | `models/forecast/lightgbm.py::ResidualForecaster` (fit/predict/explain)         | TC-FCT-03        | 2.5h |
| T2.4  | walk-forward CV    | `models/forecast/eval.py` — train≤2024-12 / valid 2025 월별                     | TC-FCT-03        | 1.5h |
| T2.5  | 데이터 부족 폴백   | `predict_demand` 가 빈 학습데이터에서 baseline 만 반환                          | TC-FCT-05        | 0.5h |
| T2.6  | PuLP ILP 매칭      | `models/matching/ilp.py::solve()` — TSD §5.2 시그니처                           | TC-MTC-01, 03~07 | 2.5h |
| T2.7  | Greedy 베이스라인  | `models/matching/greedy.py`                                                     | TC-MTC-02        | 0.8h |
| T2.8  | Gold 사전계산      | `etl/pipelines.py train` + `match` — R∈{500,1k,2k}m 솔루션 3종                  | TC-MTC-08        | 1.0h |
| T2.9  | Epiphany 집계      | `models/aggregate.py` — 카운터 4종 계산 → `epiphany_metrics.parquet`            | TC-DSH-02        | 0.8h |
| T2.10 | 모델 테스트        | `tests/test_models.py` — TC-FCT-01~03, TC-MTC-01~07                             | 위 TC            | 2.0h |
| T2.11 | 전 도구 통과       | 동일                                                                            | AGENTS §8        | 0.5h |

**Day 2 합격선**: `data/gold/{baseline_demand, forecast_monthly, match_solution, match_flows, epiphany_metrics}.parquet` 5개 생성. ILP 절감액 ≥ Greedy 절감액 (단조성). LGB MAPE ≤ 35%.

### 4. Day 3 — D-1 (2026-05-12): Streamlit + 통합 + 배포

| Task  | 산출                 | 함수·파일                                                    | TC                    | 추정 |
| ----- | -------------------- | ------------------------------------------------------------ | --------------------- | ---- |
| T3.1  | 데이터 로더          | `app/services/data.py` — `@st.cache_data` Parquet 로더       | —                     | 0.5h |
| T3.2  | 매칭 서비스 래퍼     | `app/services/matching.py` — gold 캐시 인덱싱                | —                     | 0.5h |
| T3.3  | 지도 컴포넌트        | `app/components/map.py` — Folium + 4계층 마커 (PRD §8 FR-01) | TC-MAP-01, 02         | 2.5h |
| T3.4  | Epiphany 카드        | `app/components/cards.py` — 카운터 4종 (PRD §8 FR-04)        | TC-DSH-01, 02         | 1.0h |
| T3.5  | 사이드바             | `app/components/sidebar.py` — 반경 슬라이더, 솔루션 선택     | TC-MAP-03, DSH-03     | 0.5h |
| T3.6  | 진입점               | `app/main.py` — 페이지 레이아웃 + 위 컴포넌트 조립           | —                     | 0.8h |
| T3.7  | 라이선스 푸터        | 데이터 출처 표시 (서울 열린데이터·기상청)                    | TC-SEC-03             | 0.2h |
| T3.8  | smoke 테스트         | `tests/test_app.py` — Streamlit AppTest 또는 임포트 검증     | TC-MAP-01             | 1.0h |
| T3.9  | GitHub push          | repo 생성·main push                                          | —                     | 0.5h |
| T3.10 | Streamlit Cloud 배포 | secrets 입력, 빌드 확인                                      | TC-NFR-01, 04, SEC-02 | 1.0h |
| T3.11 | 성능 측정            | 지도 ≤ 5s / 매칭 ≤ 2s                                        | TC-NFR-01, 02         | 0.5h |
| T3.12 | E2E 리허설           | 5분 시연 시나리오 3회                                        | TC-E2E-01             | 1.5h |
| T3.13 | 전 도구 통과 + 커밋  | 동일                                                         | AGENTS §8             | 0.5h |

**Day 3 합격선**: 공개 URL 접속 정상. TC-E2E-01 3회 모두 5분 이내. P0 P1 TC 모두 통과.

### 5. Day 4 — D-Day (2026-05-13, 마감 18:00): 폴리시 + 출품

| Task | 산출                                    | TC              | 추정 |
| ---- | --------------------------------------- | --------------- | ---- |
| T4.1 | Streamlit Cloud wake-up + 안정성 (오전) | TC-NFR-04       | 0.3h |
| T4.2 | 발표 슬라이드 10p                       | —               | 4.0h |
| T4.3 | 사업계획서 요약 (PRD 압축)              | —               | 1.5h |
| T4.4 | QR 코드 + 시연 영상 백업                | —               | 0.5h |
| T4.5 | 출품 (마감 18:00 이전)                  | TEST_CASE §11.4 | 0.5h |

**Day 4 합격선**: 18:00 이전 제출 완료. 발표 자료에 SHAP 또는 모델 비교 챠트 1장 포함 (선택).

### 6. Deferred (시간 남으면)

- **FR-05 PDF 리포트** — TC-PDF-01. WeasyPrint 의존성 추가 비용 ≥ 2h.
- **TC-FCT-04 SHAP 시각화** — 발표용 가치는 있으나, 잔차 모델 학습이 우선.
- **TC-MAP-04 시계열 애니메이션** — Stretch.
- **Temporal Fusion Transformer** — TFT 학습 ≥ 4h, MAPE 이득 불확실.
- **TC-E2E-02 박상무 페르소나** — Phase 2 명시.

각 항목은 plan.md §6 에 동일 형식으로 기재하되 "Deferred" 라벨.

### 7. Acceptance Gates 요약

| 단계     | P0 TC 통과 필요                                             |
| -------- | ----------------------------------------------------------- |
| D-3 종료 | DATA-01,02,03,04 (4건) + SEC-01                             |
| D-2 종료 | + FCT-01,02 + MTC-01,02,03,05,08 (8건)                      |
| D-1 종료 | + MAP-01,03 + DSH-01 + NFR-01,02,04 + SEC-02 + E2E-01 (8건) |
| D-Day    | 0 (감수성 점검만)                                           |

총 P0 16건 (TEST_CASE §11.4 누락분 포함) — 4 + 8 + 8 = 20 (중복 제거 후 P0 15 + 2 P1 보강).

### 8. Verification

#### 일별 self-check (각 Day 종료 시 실행)

```bash
uv run ruff check .            # 0 문제
uv run ruff format --check .   # 변경 없음
uv run pyright                 # 0 error
uv run pytest                  # 100% pass, coverage ≥ 60%
```

#### Day 3 종료 시 추가 (배포 검증)

```bash
# 로컬
uv run streamlit run app/main.py
# 브라우저: 지도 5s 이내 로딩, 반경 슬라이더 2s 이내 갱신, 카운터 4종 표출

# 원격
curl -sSL https://<app>.streamlit.app/ | head -20  # 200 OK
```

#### Day 4 최종 (제출 전)

- [ ] Streamlit Cloud URL 시크릿 모드 접속 → 첫 페이지 5초 이내
- [ ] 시연 시나리오 5분 이내 3회 성공
- [ ] 발표 슬라이드에 라이브 QR 코드 + 출처(서울·기상청) 명시
- [ ] 출품 마감 (2026-05-13 18:00) 이전 제출 완료

### 9. Codex 사용 가이드 (plan.md 말미)

- 작업은 위 Day 순서로 진행. Day 내 Task 는 의존성 따라 가능하면 병렬.
- 각 Task 시작 시: `docs/TSD.md §5` 의 시그니처를 먼저 확인 후 코드 작성.
- 각 Task 종료 시: AGENTS.md §8 워크플로우 — ruff·pyright·pytest 순.
- 외부 데이터 호출은 **반드시** mock fixture 로 테스트. 네트워크 의존 테스트 금지.
- 의문이 들면 사용자에게 질문. 임의 추가 금지 (AGENTS.md §9).

---

## Verification of this plan

본 plan.md 가 잘 작성되었는지의 검증:

1. **Codex 가 첫 문장만 읽고 시작 위치를 안다** — Day 0 prereq → Day 1 T1.1 순서로 명확.
2. **각 Task 가 단일 결과물·단일 TC 와 매핑** — 추적 가능.
3. **시간 합계가 가용 시간 안에 들어옴** — Day 1: 9.2h / Day 2: 14.1h / Day 3: 11.0h / Day 4: 6.8h ≈ **41h**. 가용 ~72h 대비 안전 마진 31h.
4. **Stretch 가 명시적으로 Deferred** — 에이전트의 시간 폭주 차단.
5. **검증 명령이 자동화** — Codex 가 self-check 가능.

---

## Out of Scope of this plan file

- plan.md 의 텍스트 자체를 plan 파일에 모두 복제하지 않음 (분량 비효율). 위 §"plan.md 본문 사양" 의 구조를 그대로 plan.md 로 옮긴다.
- 발표 슬라이드 디자인 가이드는 별도. (Design.md 가 iOS HIG 라 본 프로젝트 무관, 사용자 확인 필요.)

---

## 변경 이력

| 버전 | 날짜       | 변경                                    |
| ---- | ---------- | --------------------------------------- |
| 0.1  | 2026-05-10 | 초안. Day 0~4 + Deferred + Verification |
