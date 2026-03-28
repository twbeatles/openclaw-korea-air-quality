# OpenClaw Skill: Korea Air Quality

`openclaw-korea-air-quality`는 대한민국 지역의 **미세먼지 / 초미세먼지 / 오존 / 대기질 요약 / 지역 저장 / 위치 기반 조회**를 다루기 위한 **OpenClaw AgentSkill 저장소**입니다.

이 저장소는 OpenClaw에서 다음 같은 요청을 처리하는 것을 목표로 합니다.

- `지금 서울 미세먼지 어때?`
- `성동구 초미세먼지 알려줘`
- `내 기본 지역을 분당으로 저장해줘`
- `내 위치 기준으로 공기질 알려줘`
- `서울, 수원, 인천 비교해줘`
- `초미세먼지 나쁨 이상이면 알려줘`

## OpenClaw 스킬로서의 포지션

이 프로젝트는 일반 파이썬 스크립트 저장소가 아니라, **OpenClaw에서 설치/호출/자동화하기 위한 스킬 저장소**라는 점이 중요합니다.

- 권장 저장소명: `openclaw-korea-air-quality`
- 스킬 엔트리: `SKILL.md`
- 로컬 실행용 CLI: `scripts/air_quality.py`
- 패키지 결과물: `korea-air-quality.skill`

## 현재 구현 상태

현재 버전에는 아래가 포함됩니다.

- Open-Meteo 기반 대한민국 대기질 조회
- 지역 alias 확장 지원 (`서울`, `성동구`, `동대문구`, `답십리동`, `장안동`, `분당`, `판교`, `영통`, `잠실` 등)
- 사용자 기본 지역 저장/조회
- 여러 지역 비교 CLI
- 위치 좌표 입력 시 캐시된 지역 후보 기준 nearest 해석 구조
- 대기질 알림 규칙 추가/목록/점검 (`alert-add`, `alert-list`, `alert-check`)
- 중복 알림 방지 상태 저장 (`alert-state.json`)
- OpenClaw cron 초안 생성 (`cron-plan`)
- 날씨 + 대기질 결합 아침 브리핑 (`morning-brief`)
- 국내 API 확장용 provider 레이어 (`--provider openmeteo|airkorea`)

## 빠른 예시

### 현재 대기질 조회

```bash
python scripts/air_quality.py now 서울
python scripts/air_quality.py now 성동구 --json
```

### 기본 지역 저장

```bash
python scripts/air_quality.py save-default telegram:8209218742 성동구
python scripts/air_quality.py show-default telegram:8209218742 --json
python scripts/air_quality.py now --user telegram:8209218742
```

### 여러 지역 비교

```bash
python scripts/air_quality.py compare 서울 수원 인천
```

### 알림 규칙 추가 / 점검

```bash
python scripts/air_quality.py alert-add telegram:8209218742 성동구 pm2_5 나쁨
python scripts/air_quality.py alert-list --user telegram:8209218742
python scripts/air_quality.py alert-check --user telegram:8209218742
```

### 아침 브리핑

```bash
python scripts/air_quality.py morning-brief 답십리동
python scripts/air_quality.py morning-brief --user telegram:8209218742
```

### OpenClaw cron 초안 생성

```bash
python scripts/air_quality.py cron-plan morning-brief telegram:8209218742 --region 답십리동 --hour 7 --minute 30 --json
python scripts/air_quality.py cron-plan alert-check telegram:8209218742 --json
```

### 지역명 해석

```bash
python scripts/air_quality.py resolve-region 답십리동 --json
python scripts/air_quality.py resolve-region 판교 --json
```

## 다음 단계

이 저장소를 더 OpenClaw답게 완성하려면 다음이 이어지면 좋습니다.

1. 공공/국내 대기질 API 추가 연결
2. 위치 공유 메시지에서 위경도 직접 반영
3. 나쁨 이상 alert rule 저장/점검
4. 아침 브리핑 / cron 연동
5. weather 스킬과 결합한 생활형 브리핑
