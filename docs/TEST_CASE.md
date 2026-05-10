# TEST_CASE.md — 유출지하수 매칭 플랫폼

> **테스트 케이스 명세**
> 버전: 0.1 | 작성일: 2026-05-10 | 작성자: lala1522@gachon.ac.kr
> 연관: `docs/PRD.md` v0.2, `docs/TSD.md` v0.1, `docs/Database.md` v0.1

---

## 0. 테스트 정책

- **우선순위**: P0 (Demo 차단) > P1 (필수 기능) > P2 (정확도/UX) > P3 (Stretch)
- **D-3 1인 운영 기준**: P0+P1만 Demo 전 모두 통과해야 함. P2는 가능한 만큼.
- **테스트 ID 체계**: `TC-<카테고리>-<번호>`
  - DATA (ETL) / MAP (지도) / FCT (수요예측) / MTC (매칭) / DSH (대시보드) / PDF (리포트) / NFR (비기능) / SEC (보안) / E2E (시나리오) / REG (회귀)
- **합격 기준**: 각 TC의 *기대 결과 체크박스 100% 통과* + 합격 기준 충족.

---

## 1. 데이터 ETL (PRD §7.3, TSD §4)

### TC-DATA-01 — 서울 열린데이터광장 4종 데이터 수집 (P0)

**목적**: 창업 부문 필수 요건(서울 공공데이터 1건 이상) 충족 및 silver 레이어 생성.

- 사전조건
  - [ ] Streamlit Secrets에 `seoul_api_key` 저장됨
  - [ ] `data/raw/` 디렉토리 존재
- 절차
  - [ ] `python -m etl.pipelines extract` 실행
  - [ ] 유출지하수 발생 현황 CSV 다운로드 성공
  - [ ] 도시공원 현황 CSV 다운로드 성공
  - [ ] 도로 시설 CSV 다운로드 성공
  - [ ] 건축물대장 CSV 다운로드 성공
- 기대 결과
  - [ ] `data/bronze/seoul_groundwater_discharge.csv` 행 ≥ 50
  - [ ] `data/bronze/seoul_parks.csv` 행 ≥ 100
  - [ ] `data/bronze/seoul_roads.csv` 존재
  - [ ] `data/bronze/seoul_buildings_register.csv` 존재
- 합격 기준: 4개 CSV 모두 행 수 > 0 + 헤더 검증 통과.

---

### TC-DATA-02 — 좌표계 통일 (EPSG:4326) (P0)

**목적**: 거리 계산·지도 렌더링 오류 방지.

- 절차
  - [ ] silver 변환 후 모든 lat/lng 컬럼 검사
- 기대 결과
  - [ ] suppliers·demand_parks·demand_roads 모두 latitude ∈ [33, 39], longitude ∈ [124, 132]
  - [ ] 위경도 swap 없음 (서울이라 lat ≈ 37.5)
- 합격 기준: 범위 위반 0건. 단위 테스트 `tests/test_geo.py::test_seoul_bbox` 통과.

---

### TC-DATA-03 — 신고대상 건물 식별 (P1)

**목적**: PRD §1 신고 기준(21층 ∨ 10만㎡)에 부합하는 공급처만 추출.

- 절차
  - [ ] 건축물대장에서 `floors >= 21 OR total_floor_area_m2 >= 100000` 필터
- 기대 결과
  - [ ] `suppliers.reportable == True` 인 건물만 후속 매칭에 진입
  - [ ] 광역자원순환센터·창동 문화산업단지가 reportable=True 로 식별됨 (PRD 명시 사례)
- 합격 기준: PRD 명시 2개 사례 식별률 100%.

---

### TC-DATA-04 — 결측치·이상치 처리 (P1)

**목적**: 모델 학습·매칭에서 NaN으로 인한 실패 방지.

- 절차
  - [ ] silver 변환 후 `daily_avg_supply_ton`, `area_m2`, `latitude` NaN 검사
- 기대 결과
  - [ ] 핵심 컬럼 NaN 비율 0%
  - [ ] 음수·0 발생량은 수질 등급 4(처리 필요) 또는 폐기
  - [ ] 면적 0인 공원은 demand_parks에서 제외
- 합격 기준: 단위 테스트 `tests/test_etl.py::test_no_nan_in_keys` 통과.

---

### TC-DATA-05 — 시간 정렬 (월 단위 KST) (P2)

**목적**: 시계열 모델 학습 시 시점 혼선 방지.

- 절차
  - [ ] supply_history·weather_monthly·spei 의 `year_month` 형식 검사
- 기대 결과
  - [ ] 모두 `YYYY-MM` 형식
  - [ ] 시간대 KST 일관 (UTC 변환 흔적 없음)
- 합격 기준: 정규식 `^\d{4}-\d{2}$` 100% 매치.

---

## 2. 지도 시각화 — FR-01 (PRD §8 FR-01)

### TC-MAP-01 — 4계층 마커 정상 렌더링 (P0)

**목적**: 핵심 시각자료가 정상 렌더링됨을 보장.

- 절차
  - [ ] Streamlit 앱 진입
  - [ ] 지도 초기 로딩
- 기대 결과
  - [ ] 파란 마커(공급처) 표시, 크기 = 일발생량에 비례
  - [ ] 주황 마커(수요처) 표시, 크기 = 예측수요에 비례
  - [ ] 녹색 선(매칭 경로) 표시
  - [ ] 빨간 마커(미사용 공급) 표시
- 합격 기준: 4종 모두 화면에 보이고 시각적으로 구별됨.

---

### TC-MAP-02 — 마커 클릭 → 상세 사이드패널 (P1)

**목적**: 의사결정자가 개별 공급/수요처 상세를 확인할 수 있어야 함.

- 절차
  - [ ] 임의 공급처 마커 클릭
  - [ ] 임의 수요처 마커 클릭
- 기대 결과
  - [ ] 공급처 패널: 건물명·톤/일·수질 등급·신고 상태 노출
  - [ ] 수요처 패널: 유형·예측 일수요량·면적 노출
  - [ ] 월별 그래프(plotly/altair) 표시
- 합격 기준: 패널 항목 누락 0건.

---

### TC-MAP-03 — 반경 슬라이더 동작 (P0)

**목적**: 반경 변경 시 매칭 가시화가 즉시 갱신됨.

- 절차
  - [ ] 슬라이더 값 500m / 1km / 2km 순차 전환
- 기대 결과
  - [ ] 매칭 라인 개수가 반경에 따라 단조 증가 (500 ≤ 1000 ≤ 2000)
  - [ ] 사전계산된 결과를 사용해 응답 ≤ 2초
- 합격 기준: 반경 ↑ → 매칭 ↑ 단조성 위반 0건.

---

### TC-MAP-04 — 시계열 슬라이더 (P3, Stretch)

**목적**: 월별 공급·수요 변화 가시화.

- 절차
  - [ ] 슬라이더로 1~12월 전환
- 기대 결과
  - [ ] 마커 크기·매칭 라인이 월별 데이터로 갱신
- 합격 기준: Stretch — 시간 부족 시 생략 허용.

---

## 3. AI 수요예측 — §7.1 (TSD §5.1)

### TC-FCT-01 — ET₀ 베이스라인 단위 정확성 (P0)

**목적**: Penman-Monteith 산식이 FAO-56 reference 값과 일치.

- 절차
  - [ ] FAO-56 Annex 6 reference 케이스 입력
  - [ ] `et0_penman_monteith()` 호출
- 기대 결과
  - [ ] 산출 ET₀ vs reference 오차 ≤ 0.1 mm/day
- 합격 기준: `tests/test_models.py::test_et0_fao56` 통과.

---

### TC-FCT-02 — 수요예측 출력 시그니처 (P0)

**목적**: ForecastService 가 PRD §7.1·TSD §5.1 인터페이스를 준수.

- 절차
  - [ ] `predict_demand(input_df)` 호출
- 기대 결과
  - [ ] 반환 DataFrame 컬럼: `[demand_id, year_month, baseline_ton, residual_ton, predicted_ton, lower_ci_ton, upper_ci_ton]`
  - [ ] 예측값 ≥ 0
  - [ ] lower_ci ≤ predicted ≤ upper_ci
- 합격 기준: 컬럼·범위 검증 100% 통과.

---

### TC-FCT-03 — Walk-forward CV MAPE (P1)

**목적**: PRD §7.1 현실 목표(MAPE 20~30%) 충족 + naive 베이스라인 대비 개선.

- 절차
  - [ ] train ≤ 2024-12, valid 2025 월별 split
  - [ ] LGB 잔차 모델 학습·예측
  - [ ] naive (전년 동월) 베이스라인 비교
- 기대 결과
  - [ ] LGB MAPE ≤ 35% (Demo 단계 KPI)
  - [ ] **LGB MAPE ≤ naive MAPE − 5%p** (개선 합격 기준)
- 합격 기준: 두 조건 모두 충족.

---

### TC-FCT-04 — SHAP 변수 중요도 시각화 (P2)

**목적**: 발표 시 모델 설명력 확보.

- 절차
  - [ ] `forecaster.explain(X)` 호출, SHAP summary plot 저장
- 기대 결과
  - [ ] PNG 파일 생성, 상위 5개 feature 식별 가능
  - [ ] 강수·기온·SPEI·면적 중 최소 2개가 상위 5에 포함
- 합격 기준: 도메인 상식과 일치하는 feature가 최상위.

---

### TC-FCT-05 — 데이터 부족 시 베이스라인 폴백 (P1)

**목적**: 실측 수요 데이터가 부족한 demand_id에서도 예측 출력.

- 절차
  - [ ] demand_history 가 비어있는 demand_id 입력
- 기대 결과
  - [ ] residual = 0, predicted = baseline
  - [ ] lower/upper CI 는 베이스라인 ±25% 휴리스틱
- 합격 기준: 예외 없이 정상 반환.

---

## 4. 매칭 최적화 — §7.2 (TSD §5.2)

### TC-MTC-01 — ILP 작은 사례 정답 일치 (P0)

**목적**: PuLP CBC 모델이 수동 최적해와 일치함을 검증.

- 절차
  - [ ] 3 공급(각 100t/일) × 3 수요(각 80t/일) 픽스처
  - [ ] 수동 계산한 최적 절감액과 비교
- 기대 결과
  - [ ] solver_status == "Optimal"
  - [ ] objective_krw 가 수동 정답과 일치 (오차 ≤ 1원)
- 합격 기준: `tests/test_matching.py::test_small_ilp` 통과.

---

### TC-MTC-02 — 그리디 ≤ ILP 단조성 (P0)

**목적**: ILP 가 그리디 베이스라인보다 약하지 않음.

- 절차
  - [ ] 동일 입력으로 그리디·ILP 양쪽 실행
- 기대 결과
  - [ ] `ilp.objective_krw >= greedy.objective_krw - ε` (ε=1원)
- 합격 기준: 100건 랜덤 시드에서 위반 0건.

---

### TC-MTC-03 — 반경 제약 적용 (P0)

**목적**: 반경 R 초과 거리 페어가 매칭에 들어가지 않음.

- 절차
  - [ ] R = 1km 로 solve
  - [ ] flows 의 distance_km 검사
- 기대 결과
  - [ ] 모든 flow 의 `distance_km <= 1.0` (haversine)
- 합격 기준: 위반 0건.

---

### TC-MTC-04 — 수질 등급 제약 적용 (P1)

**목적**: 음용 등급 미달 공급처가 음용 수요처에 매칭되지 않음.

- 절차
  - [ ] grade 4(처리 필요) 공급처 + grade 1만 받는 수요처 입력
- 기대 결과
  - [ ] 해당 페어 `x_ij == 0`
- 합격 기준: 부적합 페어 매칭 0건.

---

### TC-MTC-05 — 용량 제약 (P0)

**목적**: 공급/수요 한도를 초과하는 흐름 없음.

- 절차
  - [ ] solve 후 공급처별·수요처별 합계 검증
- 기대 결과
  - [ ] `Σ_j x_ij <= S_i` ∀i
  - [ ] `Σ_i x_ij <= D_j` ∀j
- 합격 기준: 위반 0건.

---

### TC-MTC-06 — Solver 타임아웃 페일오버 (P1)

**목적**: 30초 내 ILP 미수렴 시 그리디로 폴백.

- 절차
  - [ ] `solver_time_limit_s=1` 로 강제 타임아웃 시뮬
- 기대 결과
  - [ ] solver_status ∈ {"Time-limited", "Optimal"}
  - [ ] 어느 쪽이든 빈 해가 아닌 결과 반환
- 합격 기준: 사용자에게 친절한 메시지 + greedy 결과 표시.

---

### TC-MTC-07 — 빈 입력 방어 (P1)

**목적**: 반경 0 또는 수질 호환 페어 0인 경우 크래시 없이 처리.

- 절차
  - [ ] R=0 으로 호출
- 기대 결과
  - [ ] 빈 flows DataFrame + objective=0 + 안내 메시지
  - [ ] Streamlit 화면에 "현재 조건에서 매칭 가능한 페어가 없습니다" 표출
- 합격 기준: 예외 throw 0건.

---

### TC-MTC-08 — 사전계산 매칭 캐시 (P0)

**목적**: R∈{500,1000,2000m} 사전계산이 gold 레이어에 정확히 저장됨.

- 절차
  - [ ] `data/gold/match_solution.parquet` 로드
- 기대 결과
  - [ ] solution_id 3종 존재
  - [ ] 각 solution 의 flows 가 비어있지 않음 (단 정상 데이터일 때)
- 합격 기준: 3 솔루션 모두 존재.

---

## 5. Epiphany 대시보드 — FR-04 (PRD §8)

### TC-DSH-01 — 카운터 4종 표시 (P0)

**목적**: PRD 핵심 epiphany 메시지가 화면 상단에 노출.

- 절차
  - [ ] 앱 진입, 상단 카드 영역 확인
- 기대 결과
  - [ ] "오늘 ___톤 하수도행" 카드
  - [ ] "절감 가능 수도요금 연 ___억원" 카드
  - [ ] "탄소 절감 ___t-CO₂eq/년" 카드
  - [ ] "현재 활용률 0% → 시스템 ___%" 카드
- 합격 기준: 4종 모두 표시 + 값이 실제 데이터 기반.

---

### TC-DSH-02 — 카운터 값 정합성 (P1)

**목적**: 표시 값이 §7.2 매칭 솔루션과 일치.

- 절차
  - [ ] 카드 값 vs `epiphany_metrics.parquet` 비교
- 기대 결과
  - [ ] 절감액 == sum(flows.savings_krw) × 365일
  - [ ] 활용률 == coverage_rate × 100
- 합격 기준: 오차 ≤ 0.5%.

---

### TC-DSH-03 — 반경 변경 시 카운터 갱신 (P1)

**목적**: 슬라이더 인터랙션이 카운터에 반영.

- 절차
  - [ ] 반경 500m → 2km 전환
- 기대 결과
  - [ ] 절감액·활용률 카운터 값이 갱신됨
  - [ ] 갱신 응답 ≤ 2초
- 합격 기준: 갱신 누락 0건.

---

## 6. 매칭 리포트 PDF — FR-05 (Stretch)

### TC-PDF-01 — 매칭 리포트 PDF 생성 (P3)

**목적**: B2G 영업·심사용 산출물.

- 절차
  - [ ] "리포트 다운로드" 클릭
- 기대 결과
  - [ ] PDF 파일 다운로드, 1MB 이하
  - [ ] 페이지 1: 요약 카운터 / 페이지 2: 지도 캡처 / 페이지 3: 매칭 표
- 합격 기준: Stretch — 시간 부족 시 생략.

---

## 7. 비기능 — PRD §9

### TC-NFR-01 — 지도 초기 로딩 ≤ 5초 (P1)

**목적**: PRD §9 응답속도 KPI.

- 절차
  - [ ] 시크릿 모드 / 캐시 비움 상태에서 첫 진입
  - [ ] DevTools Network 탭 또는 lighthouse 로 측정
- 기대 결과
  - [ ] First Contentful Paint ≤ 5초 (Streamlit 한계 감안)
- 합격 기준: 3회 측정 평균 ≤ 5초.

---

### TC-NFR-02 — 매칭 갱신 ≤ 2초 (P1)

**목적**: PRD §9 매칭 추천 응답 KPI.

- 절차
  - [ ] 사전계산된 R 값 슬라이더 전환
- 기대 결과
  - [ ] UI 응답 ≤ 2초
- 합격 기준: 3회 측정 모두 ≤ 2초.

---

### TC-NFR-03 — 브라우저 호환 (P2)

**목적**: PRD §9 접근성 (Chrome/Edge 최신 2버전).

- 절차
  - [ ] Chrome 최신·Edge 최신에서 진입
- 기대 결과
  - [ ] 양쪽에서 지도·카운터 정상 표시
- 합격 기준: 시각적 회귀 없음.

---

### TC-NFR-04 — Streamlit Cloud 콜드 스타트 (P0)

**목적**: 시연 직전 sleep 상태 방지.

- 절차
  - [ ] 시상식 전날(2026-07-05) 앱 URL 접속
- 기대 결과
  - [ ] 깨우기(슬립 해제) 후 30초 이내 첫 페이지 렌더
- 합격 기준: 발표 당일 sleep 상태가 아님.

---

## 8. 보안 — PRD §9 + TSD §9

### TC-SEC-01 — API 키 노출 점검 (P0)

**목적**: API 키가 코드·git·로그·클라이언트에 노출되지 않음.

- 절차
  - [ ] `git grep -i "api_key\|secret\|token"` 실행
  - [ ] `requirements.txt`·`.streamlit/config.toml` 점검
  - [ ] 브라우저 DevTools 네트워크 응답에서 키 검색
- 기대 결과
  - [ ] 평문 키 노출 0건
  - [ ] `.streamlit/secrets.toml` 이 .gitignore 됨
- 합격 기준: 모든 점검 통과.

---

### TC-SEC-02 — HTTPS 강제 (P0)

**목적**: PRD §9 보안 — HTTPS 강제.

- 절차
  - [ ] http:// 로 접속 시도
- 기대 결과
  - [ ] Streamlit Cloud 가 자동 https:// 리다이렉트
- 합격 기준: HTTP 노출 0건.

---

### TC-SEC-03 — 데이터 라이선스 출처 표시 (P1)

**목적**: 서울 열린데이터광장 이용약관 준수.

- 절차
  - [ ] 앱 푸터·README·발표 슬라이드 확인
- 기대 결과
  - [ ] 4개 데이터셋 출처 명시
  - [ ] 기상청 API 출처 명시
- 합격 기준: 출처 누락 0건.

---

## 9. End-to-End 시나리오

### TC-E2E-01 — 김주무관 페르소나 시연 (P0)

**목적**: PRD §5 Primary 페르소나 JTBD 충족.

- 시나리오: "이번 분기 보고에 쓸 근거 있는 매칭 가능량과 절감액 시뮬레이션을 얻고 싶다."
- 절차
  - [ ] 앱 진입 → Epiphany 카운터 4종 즉시 인지
  - [ ] 광역자원순환센터 마커 클릭 → 일 1,326톤 표출
  - [ ] 반경 1km 슬라이더 → 매칭 라인 생성
  - [ ] 절감액 카운터 자동 갱신
  - [ ] (Stretch) PDF 리포트 다운로드
- 기대 결과
  - [ ] 5분 안에 모든 단계 완료
  - [ ] 발표 시연 시나리오 그대로 재현 가능
- 합격 기준: 사전 리허설 3회 모두 5분 이내.

---

### TC-E2E-02 — 박상무 페르소나 (P2, Phase 2)

**목적**: PRD §5 Secondary — 신축 신고대상 시행사용 매칭표.

- 절차
  - [ ] 신규 건물 좌표 입력 → 반경 1km 수요처 매칭표 출력
- 기대 결과
  - [ ] CSV/PDF 다운로드 가능
- 합격 기준: Phase 2 범위 — Demo 제외.

---

## 10. 회귀·체크리스트 — Phase 2 진입 전

### TC-REG-01 — 광역시 데이터 추가 시 파라미터 교체로 동작 (P3)

**목적**: PRD §9 확장성 — 부산·인천 등 추가 시 코드 수정 최소화.

- 절차
  - [ ] `config/region.yaml` 의 region_code, bbox, station_id 만 변경
- 기대 결과
  - [ ] 코드 변경 없이 부산 데이터로 앱 동작
- 합격 기준: Phase 2 진입 전 점검 항목.

---

### TC-REG-02 — Postgres+PostGIS 마이그레이션 동등성 (P3)

**목적**: SQLite/Parquet → Postgres 이전 후 결과 동일성.

- 절차
  - [ ] 동일 입력으로 양쪽 ILP 실행
- 기대 결과
  - [ ] objective_krw 차이 ≤ 1%
- 합격 기준: Phase 2 진입 시 필수.

---

## 11. Demo 전 최종 체크리스트 (D-3 → D-Day)

### 11.1 D-3 (오늘, 2026-05-10)

- [ ] TC-DATA-01~04 통과
- [ ] TC-MAP-01, TC-MAP-03 통과
- [ ] TC-FCT-01, TC-FCT-02 통과
- [ ] TC-MTC-01~03, TC-MTC-05, TC-MTC-08 통과
- [ ] TC-DSH-01 통과

### 11.2 D-2

- [ ] TC-FCT-03 통과 (MAPE 35% 이하)
- [ ] TC-MTC-04, TC-MTC-06, TC-MTC-07 통과
- [ ] TC-DSH-02, TC-DSH-03 통과
- [ ] TC-NFR-01, TC-NFR-02 통과
- [ ] TC-SEC-01~03 통과

### 11.3 D-1

- [ ] TC-E2E-01 리허설 3회 (5분 이내)
- [ ] TC-NFR-04 (Cloud wake-up)
- [ ] 발표 슬라이드 10p 완성
- [ ] PRD 요약본 사업계획서 출력

### 11.4 D-Day (2026-05-13 18:00 마감)

- [ ] Demo URL 접속 정상
- [ ] 발표 슬라이드 + QR 코드 노출
- [ ] 사업계획서 제출

---

## 12. 변경 이력

| 버전 | 날짜 | 변경 |
|------|------|------|
| 0.1 | 2026-05-10 | 초안 작성. 10개 카테고리 / 약 35개 TC / 4단계 우선순위 |
