# TSD — 유출지하수 매칭 플랫폼

> **Technical Specification Document**
> 버전: 0.1 | 작성일: 2026-05-10 | 작성자: lala1522@gachon.ac.kr
> 연관 문서: `docs/PRD.md` v0.2, `docs/Database.md` v0.1

---

## 0. 목적·범위

PRD v0.2 §6 (MVP — 정보 비대칭 해소) 기능을 **1인 D-3 (마감 2026-05-13)** 안에 구현·배포하기 위한 기술 명세. Phase 2~3 확장 시 마이그레이션 비용을 줄이는 설계 결정도 함께 명시.

---

## 1. 시스템 아키텍처

### 1.1 MVP 아키텍처

```
┌─────────────────────────────────────────────────────┐
│  Browser (Chrome/Edge 최신 2버전)                    │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────┐
│  Streamlit Cloud (단일 인스턴스, 무료 티어)            │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Streamlit App (app/main.py)                     │ │
│ │   ─ Map (Folium / streamlit-folium)             │ │
│ │   ─ Sidebar (반경/수질 슬라이더, 모델 토글)         │ │
│ │   ─ Epiphany Cards (FR-04)                      │ │
│ └────────────────────┬────────────────────────────┘ │
│                      │ in-process call              │
│ ┌────────────────────▼────────────────────────────┐ │
│ │ Core Services                                   │ │
│ │   ─ ForecastService  (LightGBM + ET₀ baseline)  │ │
│ │   ─ MatchingService  (PuLP CBC ILP)             │ │
│ │   ─ GeoService       (geopandas, haversine)     │ │
│ └────────────────────┬────────────────────────────┘ │
│                      │ DuckDB / pandas              │
│ ┌────────────────────▼────────────────────────────┐ │
│ │ Data Layer (read-only)                          │ │
│ │   data/silver/*.parquet  (전처리)                │ │
│ │   data/gold/*.parquet    (예측·최적해 캐시)        │ │
│ │   data/app.db (SQLite, 가벼운 메타데이터)          │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘

[ ETL — offline, 로컬 1회 또는 GitHub Actions cron ]
서울 열린데이터광장 ─┐
기상청 ASOS API     ─┼─▶ bronze/ ─▶ silver/ ─▶ gold/
가뭄지수 (SPEI)     ─┘
```

### 1.2 Phase 2~3 로드맵 (참고 — 현재 구현 X)

- DB: PostgreSQL 16 + PostGIS 3.4 (다중 지자체 테넌트)
- API: FastAPI + Pydantic v2 + SQLAlchemy 2.x
- 작업큐: Celery + Redis (예측 일배치)
- 프론트: Next.js 14 + 카카오맵 SDK
- IoT: MQTT → TimescaleDB (실시간 유량계, Phase 3)
- 인프라: NHN Cloud 또는 AWS ap-northeast-2 + Terraform

---

## 2. 기술 스택

### 2.1 MVP

| 레이어 | 선택 | 사유 |
|------|------|------|
| 언어 | Python 3.11 | ML/지오 라이브러리 즉시 사용, 1인 단일 언어 |
| 프론트 | **Streamlit** 1.32+ | 1인 D-3 최단경로. UI 인력 불필요 |
| 지도 | **Folium** + streamlit-folium | 토큰 불필요, 안정 |
| 데이터 처리 | pandas, **DuckDB** 0.10+ | SQL on Parquet, 1인 친화 |
| 지오 처리 | geopandas, shapely, pyproj | 좌표계 변환·반경 쿼리 |
| ML | **LightGBM** 4.x, scikit-learn, shap | LightGBM 1개로 축소 |
| 도메인 모델 | refet (Penman-Monteith ET₀) | 기준증발산량 산출 |
| 최적화 | **PuLP** + CBC | 오픈소스 ILP, N<1000 충분 |
| 차트 | plotly, altair | Streamlit 네이티브 |
| 배포 | **Streamlit Cloud** | 무료, GitHub 자동 배포 |
| Secrets | Streamlit Cloud Secrets | API 키 보관 |
| 패키지 | uv 또는 pip + requirements.txt | Streamlit Cloud 호환 |

### 2.2 Phase 2~3 후보

PostgreSQL 16 + PostGIS, FastAPI, SQLAlchemy 2, Celery, Redis, Next.js 14, 카카오맵 SDK, TimescaleDB, Sentry, Terraform.

---

## 3. 저장소 디렉토리 구조

```
Contest/
├── docs/
│   ├── PRD.md
│   ├── TSD.md            ← 본 문서
│   └── Database.md
├── references/
├── data/
│   ├── raw/              ← 원본 다운로드 (gitignore)
│   ├── bronze/           ← 그대로 보관
│   ├── silver/           ← 클리닝·표준화 Parquet
│   └── gold/             ← 모델 입력·예측 결과
├── etl/
│   ├── extract/          ← API/CSV 수집
│   ├── transform/        ← 정규화·feature engineering
│   └── pipelines.py      ← 일괄 실행 진입
├── models/
│   ├── forecast/
│   │   ├── baseline.py   ← ET₀ 베이스라인
│   │   ├── lightgbm.py   ← 잔차 보정
│   │   └── eval.py       ← walk-forward CV
│   └── matching/
│       ├── ilp.py        ← PuLP 최적화
│       └── greedy.py     ← 베이스라인
├── app/
│   ├── main.py           ← Streamlit 진입
│   ├── pages/
│   ├── components/       ← 지도·카드·사이드바
│   └── services/         ← forecast/matching wrapper
├── tests/
├── notebooks/            ← EDA·실험
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml      ← gitignore
├── requirements.txt
└── README.md
```

---

## 4. 데이터 파이프라인

전처리·학습은 **오프라인 1회 실행**, Streamlit은 read-only Parquet 만 소비.

```
Step 1 — Extract (etl/extract/)
  서울 열린데이터광장 (4 datasets) ──▶ data/bronze/*.csv
  기상청 ASOS API                  ──▶ data/bronze/asos_monthly.csv
  기상청·농진청 SPEI               ──▶ data/bronze/spei.csv

Step 2 — Transform (etl/transform/)
  ─ 좌표계 통일 → EPSG:4326
  ─ 결측치 처리 (수질·발생량)
  ─ 신고대상 식별 (21층 ∨ 10만㎡)
  ─ 수요처 (공원·도로) 정제
  ─ 시간 정렬 (월 단위)
  ─ Output: data/silver/{suppliers, demand_parks, demand_roads, weather, drought}.parquet

Step 3 — Feature Engineering (models/forecast/baseline.py)
  ─ ET₀ Penman-Monteith 월별
  ─ 베이스라인 = ET₀ × Kc × area / 효율
  ─ Output: data/gold/baseline_demand.parquet

Step 4 — Train (models/forecast/lightgbm.py)
  ─ X: 면적, 식재유형, 월, 강수, 기온, 토양수분, SPEI, 미세먼지
  ─ y: 잔차 (실측 − 베이스라인)
  ─ 검증: walk-forward CV (월 시차)
  ─ Save: models/artifacts/lgb_residual_v1.pkl

Step 5 — Predict & Match
  ─ data/gold/forecast_monthly.parquet
  ─ data/gold/match_solution.parquet (R∈{500,1000,2000m} 사전계산)
  ─ data/gold/epiphany_metrics.parquet

Step 6 — Serve (app/main.py)
  Streamlit이 data/gold/ 만 로드, DuckDB로 인터랙티브 필터.
```

**1인 D-3 권장 운영**: 로컬에서 1회 실행 → Parquet 결과를 git LFS 또는 직접 커밋 → Streamlit Cloud 자동 빌드.

---

## 5. AI/ML 구현 명세 (PRD §7 구체화)

### 5.1 수요예측 (Forecast Service)

```python
# models/forecast/baseline.py
def et0_penman_monteith(
    tmean_c, tmin_c, tmax_c, rh, wind_ms, rs_mj_m2,
    lat_rad, doy
) -> float:  # mm/day
    ...

def baseline_demand_monthly(
    area_m2: float,
    crop_coeff: float,         # Kc, 식재유형별 (참조 테이블)
    et0_monthly_mm: float,
    irrigation_efficiency: float = 0.7,
) -> float:                    # ton/month
    return area_m2 * et0_monthly_mm * crop_coeff / irrigation_efficiency / 1000
```

```python
# models/forecast/lightgbm.py
@dataclass
class ForecastInput:
    demand_id: str
    year: int; month: int
    area_m2: float
    veg_type: Literal["lawn","shrub","tree","road"]
    precip_mm: float; tmean_c: float
    soil_moisture: float
    spei: float; pm10: float
    is_event: int

class ResidualForecaster:
    def fit(self, X: pd.DataFrame, y_residual: pd.Series): ...
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...
    def explain(self, X: pd.DataFrame) -> shap.Explanation: ...

def predict_demand(input_df: pd.DataFrame) -> pd.DataFrame:
    base = baseline_demand_monthly(...)
    residual = ResidualForecaster.predict(input_df)
    return base + residual
```

**검증** (`models/forecast/eval.py`)
- Walk-forward split: train ≤ 2024-12, valid 2025 월별
- 메트릭: MAPE, RMSE, sMAPE
- Naive 베이스라인: 전년 동월. **합격 기준: LGB가 naive 대비 MAPE 5%p 개선**.
- SHAP plot: 발표 슬라이드 첨부.

### 5.2 매칭 최적화 (Matching Service)

```python
# models/matching/ilp.py
@dataclass
class Supplier:
    id: str; lat: float; lng: float
    daily_supply_ton: float
    quality_grade: int           # 1=best ... 4=worst

@dataclass
class Demand:
    id: str; lat: float; lng: float
    daily_demand_ton: float
    min_quality_grade: int

@dataclass
class MatchSolution:
    flows: pd.DataFrame          # supplier_id, demand_id, ton_per_day, savings_krw
    objective_krw: float
    coverage_rate: float
    solver_status: str

def solve(
    suppliers: list[Supplier],
    demands: list[Demand],
    radius_km: float = 1.0,
    transport_cost_per_ton_km: float = 500,    # KRW
    tap_water_price_per_ton: float = 1200,     # KRW (서울시 비음용 단가)
    unmet_penalty: float = 5000,
    solver_time_limit_s: int = 30,
) -> MatchSolution: ...
```

PuLP 모델 (의사코드):
```
maximize  Σ x_ij × (tap_water_price − transport_cost × dist_ij)
        − λ × Σ (D_j − Σ_i x_ij)
s.t.      Σ_j x_ij ≤ S_i           ∀i
          Σ_i x_ij ≤ D_j           ∀j
          x_ij = 0 if dist_ij > R or quality_i ∉ allowed(j)
          x_ij ≥ 0
solver = pulp.PULP_CBC_CMD(timeLimit=30)
```

**Greedy 베이스라인** (`greedy.py`) — 거리 오름차순으로 공급량을 수요에 채움. ILP와 절감액 차이를 발표에서 시각화.

### 5.3 자동 검증

`tests/test_models.py`:
- ET₀ 산식 단위테스트 (FAO-56 reference 값 비교)
- 매칭 ILP — 작은 사례 (3공급 × 3수요)에서 수동 정답과 일치
- Greedy 절감액 ≤ ILP 절감액 (단조성 검증)

---

## 6. 외부 통합

| 시스템 | 용도 | 인증 | 호출 |
|--------|------|------|------|
| 서울 열린데이터광장 (data.seoul.go.kr) | 유출지하수·공원·도로·건축물대장 | API key (Secrets) | ETL 시 1회/월 |
| 기상청 ASOS Open API | 종관 기상관측 | API key | ETL 시 1회/월 |
| 기상청·농진청 SPEI | 가뭄지수 | (확인 필요) | ETL 시 1회/월 |
| (Phase 2) 카카오맵 | 지오코딩·길찾기 | API key | 사용자 인터랙션 |

API 키는 Streamlit Cloud Secrets 에서만 보관, 코드·git·로그 노출 절대 금지.

---

## 7. 배포

1. GitHub repo 생성 (main 브랜치만)
2. Streamlit Cloud ↔ GitHub 연동 → main 푸시 시 자동 배포
3. Secrets는 Streamlit Cloud 대시보드에서 입력
4. `requirements.txt` + `runtime.txt` (Python 3.11)
5. Entry point: `app/main.py`
6. 시연 URL: `https://<app>.streamlit.app/` → 슬라이드에 QR 코드
7. 롤백: GitHub revert → 자동 재배포

---

## 8. 성능 고려사항

| 영역 | 전략 |
|------|------|
| 지도 마커 | 50 공급 + 100 수요 = 150 → Folium 부담 없음. 광역 확장 시 MarkerCluster |
| ILP 풀이 | 1000×1000 이하 CBC <2초. timeout=30s, fallback=greedy |
| 모델 호출 | 사전계산 후 Parquet 캐시. Streamlit은 학습 안 함 |
| Streamlit 캐시 | `@st.cache_data` Parquet 로드, `@st.cache_resource` 모델 |
| 콜드 스타트 | 무료 티어 7일 sleep — 시상식 전날 wake-up |
| 슬라이더 변경 | 반경별 사전계산 (R∈{500,1000,2000m}) — 클릭당 매칭 재실행 X |

---

## 9. 보안

| 영역 | 조치 |
|------|------|
| API 키 | Streamlit Secrets, 코드/git/로그 노출 금지 |
| HTTPS | Streamlit Cloud 기본 |
| PII | 공공데이터만 사용. 시행사 컨설팅(Phase 2)에서 NDA |
| 데이터 라이선스 | 서울 열린데이터광장 이용약관 준수, 출처 명시 |
| 의존성 취약점 | `pip-audit` 주 1회 (Phase 2부터 dependabot) |

---

## 10. 테스트 전략 (1인 D-3)

| 레벨 | 우선순위 | 도구 |
|------|---------|------|
| 단위 (ET₀, ILP 작은케이스) | **필수** | pytest |
| 통합 (ETL 1주기 e2e) | **필수** | pytest + sample fixtures |
| UI smoke (페이지 200) | 권장 | playwright (stretch) |
| 부하 | 생략 | — |

---

## 11. 위험 & 기술부채

| 항목 | 영향 | 대응 |
|------|------|------|
| Streamlit Cloud sleep | 시연 직전 down | 시상식 전날 wake-up |
| 실측 수요량 데이터 부족 | LGB 학습 불가 | 베이스라인만으로도 demo 가능. 발표에서 "데이터 수집 로드맵" 명시 |
| 좌표계 혼선 (5179 vs 4326) | 거리 계산 오류 | ETL Step 2에서 4326 통일, haversine |
| ILP 비실행 가능 케이스 | 빈 해 | UI 메시지 + greedy fallback |
| 광역 확장 시 SQLite 한계 | 다중 테넌트 부적합 | Phase 2에서 Postgres 마이그레이션 (Database.md §6) |
| `git` 1MB 이상 Parquet | 푸시 거부 | git LFS 또는 데이터를 리포 외부(S3-like)로 분리 |

---

## 12. 변경 이력

| 버전 | 날짜 | 변경 |
|------|------|------|
| 0.1 | 2026-05-10 | 초안 작성 (PRD v0.2 기반) |
