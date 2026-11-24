# Domestic API Notes

## 목표

Open-Meteo 기반 프로토타입 이후, 국내 대기질 API를 붙일 때 필요한 연결 레이어를 정리한다.

## 우선 후보

- 에어코리아 / 공공데이터포털 계열 API
- 국내 측정소/권역 예보 데이터

## 구현 방향

현재 스킬은 `provider` 개념을 도입해 `openmeteo` 와 `airkorea` 같은 공급자를 구분할 수 있게 확장되어 있다.

현재 상태:

1. `AIRKOREA_API_KEY` 또는 `data/config.json`의 `airkorea_api_key` 를 읽는다.
2. AirKorea 시도 단위 실시간 측정 API를 호출한다.
3. JSON 응답을 우선 시도하고, 필요하면 XML도 파싱한다.
4. 지역명과 비슷한 측정소가 있으면 우선 선택하고, 없으면 값이 있는 첫 항목을 사용한다.
5. OpenClaw summary 스키마로 매핑한다.

남은 과제:

- 권역 예보 API 연결 (대기질 예보통보 / 초미세먼지 주간예보 오퍼레이션)
- 시도 단위 fallback보다 더 촘촘한 지역별 정확도 개선

반영 완료 (2026-11-24, 실측 명세 대조):

- 측정소 직접 조회 폴백: 시도 조회가 비어 있거나 전 항목 결측이면
  `getMsrstnAcctoRltmMesureDnsty(stationName + dataTerm=DAILY)` 로 복구
  (`refine_via_station_api`, 최신 유효 레코드 선택)
- 페이지 크기 100 → 200 (경기 등 대형 시도 측정소 누락 방지)
- 응답 변형 흡수: 단일 dict / `{"item": [...]}` 중첩 정규화
- 추가 지표 노출: SO2/CO/NO2 값·등급, 측정망·플래그, 24시간 예측이동농도

## 필요한 설정 예시

- `AIRKOREA_API_KEY`
- 또는 `data/config.json` 내 provider 설정

## 주의점

- 국내 API는 응답 포맷이 XML 기반일 수 있어 파서 추가가 필요하다.
- 측정소 중심 데이터와 행정구역 중심 질의 사이의 매핑 레이어가 중요하다.
- 동일 지표라도 등급 기준/표현이 Open-Meteo와 다를 수 있으니 요약 전에 정규화해야 한다.
