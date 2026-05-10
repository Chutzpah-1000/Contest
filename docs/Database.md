# Database.md — 유출지하수 매칭 플랫폼

> **데이터 모델 명세**
> 버전: 0.1 | 작성일: 2026-05-10 | 작성자: lala1522@gachon.ac.kr
> 연관: `docs/PRD.md` v0.2, `docs/TSD.md` v0.1

---

## 0. 설계 원칙

1. **MVP는 파일 기반 (Parquet + SQLite)** — 1인 D-3 운영 부담 최소화. Streamlit Cloud 무료 티어에서 RDB 호스팅 부담 없음.
2. **Bronze / Silver / Gold 레이어** — Databricks Medallion 패턴. ETL 재실행과 디버깅이 쉬움.
3. **Phase 2 마이그레이션 비용 최소화** — 스키마는 PostgreSQL + PostGIS 호환 형태로 설계 (좌표는 lat/lng 분리 + WKT geom 컬럼 옵션 보유).
4. **모든 시간은 KST** — 연·월 단위 통합. 일 단위는 Phase 3 IoT.
5. **PII 없음** — 공공데이터만 사용. 시행사 컨설팅(Phase 2)에서 별도 테이블 분리.
6. **출처 추적** — 모든 테이블에 `source` 컬럼 → 라이선스/감사 대응.

---

## 1. 데이터 레이어 구조

```
data/
├── raw/      ← 원본 다운로드 그대로 (gitignore)
├── bronze/   ← 그대로 보관 (스키마 검증만)
├── silver/   ← 정규화·표준화 (분석 가능 상태)
└── gold/     ← 모델 입력·예측·집계 결과
```

| 레이어 | 포맷 | 변경 빈도 | 신뢰도 |
|------|------|---------|--------|
| Bronze | CSV/JSON 그대로 | ETL 시 | 원본 |
| Silver | Parquet (Snappy) | 월 1회 | 정제됨 |
| Gold | Parquet (Snappy) | 모델 학습 시 | 분석용 |

MVP는 추가로 `data/app.db` (SQLite) 하나에 메타 테이블만 보관 (예: 매칭 실행 이력).

---

## 2. 데이터 출처 카탈로그 (Bronze)

| 파일 | 출처 | 갱신 | MVP 사용 |
|------|------|-----|---------|
| `bronze/seoul_groundwater_discharge.csv` | 서울 열린데이터광장 — 유출지하수 발생 현황 | 분기 | ✅ |
| `bronze/seoul_parks.csv` | 서울 열린데이터광장 — 도시공원 현황 | 분기 | ✅ |
| `bronze/seoul_roads.csv` | 서울 열린데이터광장 — 도로 시설 | 반기 | ✅ |
| `bronze/seoul_buildings_register.csv` | 서울 열린데이터광장 — 건축물대장 | 월 | ✅ |
| `bronze/asos_monthly.csv` | 기상청 ASOS Open API — 종관 기상관측 | 월 | ✅ |
| `bronze/spei_monthly.csv` | 기상청·농진청 SPEI 가뭄지수 | 월 | ✅ |
| `bronze/seoul_water_usage.csv` | 서울시 상수도 사용량 통계 (구·동) | 월 | ⏳ (학습용 프록시) |

---

## 3. Silver 레이어 스키마 (전처리 후, MVP 사용)

좌표: 모두 EPSG:4326 (WGS84). 거리 계산은 haversine.

### 3.1 `silver/suppliers.parquet` — 공급처 (신고대상 건물)

| 컬럼 | 타입 | 설명 | 비고 |
|------|------|------|------|
| supplier_id | string | PK. e.g. `SUP-00001` | UUID 대신 가독성 |
| name | string | 건물명 | "광역자원순환센터" |
| address | string | 주소 | |
| latitude | float64 | 위도 | EPSG:4326 |
| longitude | float64 | 경도 | EPSG:4326 |
| total_floor_area_m2 | float64 | 연면적 | |
| floors | int32 | 지상 층수 | |
| daily_avg_supply_ton | float64 | 일평균 발생량 (ton/day) | |
| water_quality_grade | int8 | 수질 등급 1-4 | 참조 §4.1 |
| report_status | string | 신고완료 / 이용계획 미수립 / 하수방류 중 | enum |
| reportable | bool | 21층 ∨ 10만㎡ 충족 | |
| source | string | 데이터 출처 식별자 | |
| ingested_at | timestamp | ETL 실행 시각 | |

인덱스: (latitude, longitude) 공간 인덱스 (Phase 2 PostGIS GIST), MVP는 geopandas R-tree.

### 3.2 `silver/supply_history.parquet` — 발생량 시계열 (월별)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| supplier_id | string | FK → suppliers |
| year_month | string | `YYYY-MM` |
| supply_ton | float64 | 월 누적 발생량 |
| source | string | |

PK: (supplier_id, year_month)

### 3.3 `silver/demand_parks.parquet`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| demand_id | string | PK. `PRK-00001` |
| name | string | 공원명 |
| district | string | 자치구 |
| latitude | float64 | |
| longitude | float64 | |
| area_m2 | float64 | 면적 |
| veg_type | string | enum: lawn / shrub / tree / mixed |
| crop_coeff_kc | float32 | 작물계수 (참조 §4.2 join 결과) |
| min_quality_grade | int8 | 허용 가능 최저 수질 등급 |
| source | string | |

### 3.4 `silver/demand_roads.parquet`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| demand_id | string | PK. `RDS-00001` |
| name | string | 도로명 |
| district | string | |
| centroid_lat | float64 | 도로 중심점 위도 |
| centroid_lng | float64 | 도로 중심점 경도 |
| length_m | float64 | 도로 연장 |
| road_type | string | enum: 주간선 / 보조간선 / 집산 / 국지 |
| min_quality_grade | int8 | (살수 용도이므로 보통 3) |
| source | string | |

### 3.5 `silver/demand_history.parquet` — 실측 수요 (학습용, 프록시)

학습용 *실측 비음용 수요*는 직접 데이터가 없으므로 **서울시 상수도 사용량(구·동) × 비음용 비율**로 프록시.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| demand_id | string | FK |
| year_month | string | |
| demand_ton | float64 | 월 사용량 |
| source | string | "proxy:district_water_usage" |
| confidence | float32 | 0~1 신뢰도 |

PK: (demand_id, year_month)

### 3.6 `silver/weather_monthly.parquet`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| station_id | string | 기상관측소 ID |
| station_lat | float64 | |
| station_lng | float64 | |
| year_month | string | |
| tmean_c | float32 | 평균기온 |
| tmin_c | float32 | |
| tmax_c | float32 | |
| precip_mm | float32 | 누적 강수량 |
| rh | float32 | 평균 상대습도 |
| wind_ms | float32 | 평균 풍속 |
| sunshine_hr | float32 | 일조시간 |
| pm10_ugm3 | float32 | 미세먼지 (가능 시) |
| source | string | "kma_asos" |

PK: (station_id, year_month)

### 3.7 `silver/drought_index.parquet`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| region_code | string | 행정구역 코드 |
| year_month | string | |
| spei_3m | float32 | 3개월 SPEI |
| spei_6m | float32 | 6개월 SPEI |
| source | string | |

### 3.8 `silver/water_quality_grades.parquet` — 참조

§4.1 참조.

### 3.9 `silver/crop_coefficients.parquet` — 참조

§4.2 참조.

---

## 4. 참조 테이블 (Reference Data, 정적)

### 4.1 수질 등급 (`water_quality_grades`)

| grade | label | 허용 용도 |
|-----|-------|---------|
| 1 | 음용 가능 | 모든 용도 |
| 2 | 공업용 | 공업·조경·살수·냉각 |
| 3 | 조경용 | 조경·살수·냉각 |
| 4 | 처리 필요 | 처리 후 사용 |

### 4.2 식재 유형별 작물계수 (`crop_coefficients`)

| veg_type | kc | 출처 |
|---------|----|----|
| lawn | 0.85 | FAO-56 turf reference |
| shrub | 0.70 | |
| tree | 0.65 | |
| mixed | 0.75 | |
| road (살수) | 1.00 | 면적당 살수 노멀라이즈 |

---

## 5. Gold 레이어 스키마 (모델 산출물)

### 5.1 `gold/baseline_demand.parquet`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| demand_id | string | |
| year_month | string | |
| et0_mm | float32 | Penman-Monteith ET₀ |
| baseline_demand_ton | float64 | ET₀ × Kc × area / efficiency |

### 5.2 `gold/forecast_monthly.parquet`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| demand_id | string | |
| year_month | string | |
| baseline_ton | float64 | §5.1 |
| residual_ton | float64 | LGB 출력 |
| predicted_ton | float64 | baseline + residual |
| lower_ci_ton | float64 | 90% 신뢰구간 하한 |
| upper_ci_ton | float64 | 90% 신뢰구간 상한 |
| model_version | string | e.g. `lgb_residual_v1` |

PK: (demand_id, year_month, model_version)

### 5.3 `gold/match_solution.parquet` — 솔루션 헤더

| 컬럼 | 타입 | 설명 |
|------|------|------|
| solution_id | string | PK |
| radius_km | float32 | 반경 파라미터 |
| lambda_unmet | float32 | 미충족 페널티 가중 |
| run_at | timestamp | |
| objective_krw | float64 | 목적함수 값 |
| coverage_rate | float32 | 충족 / 전체 수요 |
| solver_status | string | "Optimal", "Time-limited", ... |

MVP는 R∈{500, 1000, 2000} 3종 사전계산 → solution_id 3개.

### 5.4 `gold/match_flows.parquet` — 솔루션 흐름

| 컬럼 | 타입 | 설명 |
|------|------|------|
| solution_id | string | FK → match_solution |
| supplier_id | string | FK → suppliers |
| demand_id | string | FK (parks/roads 통합) |
| ton_per_day | float64 | 배분량 |
| distance_km | float32 | haversine 거리 |
| transport_cost_krw | float64 | 운반비 추정 |
| savings_krw | float64 | 상수도 대비 절감액 |

PK: (solution_id, supplier_id, demand_id)

### 5.5 `gold/epiphany_metrics.parquet` — 대시보드 카운터

| 컬럼 | 타입 | 설명 |
|------|------|------|
| metric_name | string | enum: total_discharge_ton_day / savings_krw_year / co2_eq_year / utilization_rate |
| metric_value | float64 | |
| unit | string | |
| solution_id | string | 어느 솔루션 기반인지 |
| computed_at | timestamp | |

---

## 6. SQLite 메타 테이블 (`data/app.db`)

매칭 실행 이력·사용자 인터랙션 추적 정도로만 사용. MVP에서는 사실상 비워둠.

```sql
CREATE TABLE match_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    solution_id TEXT NOT NULL,
    user_session TEXT,
    radius_km REAL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    status TEXT
);

CREATE INDEX idx_match_runs_started ON match_runs(started_at);
```

---

## 7. 관계 다이어그램 (논리)

```
suppliers ──< supply_history
   │
   │  (supplier_id)
   │
   └─< match_flows >─ demand (parks ∪ roads)
                         │
                         ├─< demand_history
                         └─< forecast_monthly

weather_monthly ──┐
drought_index   ──┼──▶ baseline_demand ──▶ forecast_monthly ──▶ match_flows
crop_coefficients ┘                                                 │
                                                                    ▼
                                                            epiphany_metrics
```

---

## 8. Phase 2 PostgreSQL + PostGIS 마이그레이션

### 8.1 변경 사항

- `latitude/longitude` 컬럼 → `geom GEOMETRY(Point, 4326)` 보강 (양쪽 유지하다 점진 이동)
- 공간 인덱스: `CREATE INDEX ON suppliers USING GIST(geom);`
- 시계열 테이블 (supply_history, forecast_monthly, weather_monthly) → TimescaleDB hypertable
- 다중 테넌트: `tenant_id` 컬럼 추가 (서울/부산/인천...)
- Row-level security 로 지자체별 격리

### 8.2 마이그레이션 코드 골격

```python
# etl/migrate_to_postgres.py
import duckdb, sqlalchemy

eng = sqlalchemy.create_engine("postgresql+psycopg://...")
for table in ["suppliers", "demand_parks", "demand_roads",
              "supply_history", "weather_monthly", ...]:
    df = duckdb.sql(f"SELECT * FROM 'data/silver/{table}.parquet'").df()
    df.to_sql(table, eng, if_exists="append", index=False, chunksize=10_000)

# geom 보강
with eng.connect() as c:
    c.execute("""
        ALTER TABLE suppliers ADD COLUMN geom geometry(Point, 4326);
        UPDATE suppliers SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);
        CREATE INDEX ON suppliers USING GIST(geom);
    """)
```

---

## 9. 데이터 거버넌스

| 영역 | 정책 |
|------|------|
| 라이선스 | 서울 열린데이터광장 이용약관 (출처 명시·재배포 조건 준수) |
| PII | 없음. Phase 2 시행사 정보 추가 시 PII 분리 테이블 + 암호화 |
| 보존기간 | Bronze 영구 / Silver 영구 / Gold 모델 버전별 보존 |
| 백업 | MVP: GitHub 리포가 사실상 백업. Phase 2: pg_dump 일배치 |
| 변경 이력 | `ingested_at` + `source` 컬럼으로 추적. Phase 2 SCD Type 2 검토 |

---

## 10. 위험 & 미정 항목

| 항목 | 영향 | 대응 |
|------|------|------|
| 실측 수요량 데이터 부재 | LGB 학습 정확도 저하 | demand_history를 상수도 사용량 프록시로 채움. Phase 2에서 빅데이터캠퍼스 협조 요청 |
| 신고대상 건물 식별 누락 | 공급처 누락 | 21층·10만㎡ 두 조건 OR 적용 + 수동 검증 |
| 좌표계 혼선 | 거리 오류 | ETL Step 2에서 4326 강제, 단위 테스트로 보호 |
| 도로 데이터의 폴리라인 → 점화 | 살수 수요 추정 오차 | 일단 centroid + length 사용, Phase 2에서 세그먼트 단위 |
| Parquet 파일 git 1MB 초과 | 푸시 거부 | git LFS 또는 데이터 외부 저장 (S3-호환) |

---

## 11. 변경 이력

| 버전 | 날짜 | 변경 |
|------|------|------|
| 0.1 | 2026-05-10 | 초안 (PRD v0.2 / TSD v0.1 기반). Bronze/Silver/Gold 3계층, 11개 핵심 테이블 정의 |
