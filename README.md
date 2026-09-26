# OpenClaw Korea Air Quality (`korea-air-quality`)

대한민국 지역의 **실시간 대기질(미세먼지, 초미세먼지, 오존, 통합대기) 조회, 위치 기반 측정소 매칭, 날씨 결합 아침 브리핑, 임계치 초과 알림**을 지원하는 **OpenClaw 공식 AgentSkill**입니다.

한국환경공단 에어코리아(AirKorea, ver 1.3) 실측 API와 전 세계 기상 API인 Open-Meteo를 결합하여, API 키 유무와 무관하게 즉시 동작하며 국내 공공데이터의 고정밀 측정소 데이터까지 완벽하게 지원합니다.

---

## 🌟 주요 특징 (Key Features)

- **🇰🇷 대한민국 실시간 대기질 조회 (AirKorea & Open-Meteo 결합)**
  - 한국환경공단 에어코리아(`ArpltnInforInqireSvc`, ver 1.3) 실측 데이터 연동 (1시간 등급, KHAI, O3 등).
  - API 키가 없는 초기 환경에서도 Open-Meteo 기반으로 즉시 조회 가능한 자동 폴백(Fallback) 탑재.
- **📍 4단계 계층형 측정소 정밀 매칭 (Hierarchical Station Matching)**
  - 동 단위 측정소가 없는 경우(`명동`, `을지로동` 등), 엉뚱한 시도 첫 번째 측정소로 튀지 않고 `동/읍/면` ➔ `자치구/시/군(서울 중구)` ➔ `행정동` ➔ `시도 유효 측정소` 순서로 안전하게 자치구 측정소(`중구` 측정소)를 선택.
  - 장비 점검 등으로 인한 결측치(`"-"`) 발생 시 인근 유효 측정소로 지능형 폴백.
- **🔑 공공데이터포털 스마트 인증키 처리 (Smart Key Handling)**
  - 공공데이터포털 특유의 일반 인증키(Encoding vs Decoding) 포맷 차이로 인한 401 오류를 방지하기 위해 원문/인코딩 키 자동 재시도(`fallback retry`) 지원.
  - 포털 표준 에러 XML/JSON(`<cmmMsgHeader>`)을 파싱하여 서비스키 미등록, 승인 대기, 일일 트래픽 초과 등의 명확한 원인 안내.
- **🗺️ 메신저 위치 공유 및 지도 링크 자동 분석**
  - 메신저 JSON 위치 데이터, 위경도 문자열, 네이버 지도/카카오맵 링크 패턴 자동 인식.
  - `(경도, 위도)` 순서로 뒤바뀐 좌표도 대한민국 좌표계 특성을 감지하여 자동 정규화.
- **⏰ OpenClaw Cron 자동화 & 감시 알림**
  - 감시 항목(`pm2_5`, `pm10`, `ozone`, `khai`, `overall`) 임계치 초과 시 알림 규칙 등록 및 중복 알림 방지 상태 관리.
  - 현재 스크립트 실행 경로를 자동 감지하여 OpenClaw에 등록 가능한 `cron-plan` 초안 원클릭 생성.
- **🛡️ 안정성 및 환경 호환성**
  - 복수 지역 비교(`compare`) 시 일부 지역 오타가 있어도 전체 조회가 중단되지 않는 에러 내성 설계.
  - Windows 콘솔 및 OpenClaw 서브프로세스 환경에서 한글 깨짐을 방지하는 UTF-8 자동 입출력 재구성.

---

## 🚀 빠른 시작 (Quick Start)

### 1) 현재 대기질 조회 (`now`)

```bash
# 기본 자연어 지역 조회
python scripts/air_quality.py now "서울 중구"
python scripts/air_quality.py now 홍대
python scripts/air_quality.py now 분당

# 에어코리아 실측 프로바이더 명시
python scripts/air_quality.py now 성동구 --provider airkorea

# JSON 포맷 출력
python scripts/air_quality.py now 서울 --json
```

### 2) 위치 기반 대기질 조회 (`lat/lon` 또는 `location-text`)

```bash
# 위경도 좌표 직접 입력 (부산)
python scripts/air_quality.py now --lat 35.1796 --lon 129.0756 --json

# 메신저 위치공유 텍스트 또는 지도 링크 입력 (경도, 위도 순서도 자동 보정)
python scripts/air_quality.py now --location-text "126.9979, 37.5641"
```

### 3) 사용자 기본 지역 / 위치 관리 (`save-default`, `clear-default`)

사용자 식별자(채널 ID 등)를 키로 기본 지역이나 위치 좌표를 영구 보관합니다.

```bash
# 기본 지역 저장
python scripts/air_quality.py save-default telegram:8209218742 "서울 중구"

# 기본 위치 좌표 저장
python scripts/air_quality.py save-location telegram:8209218742 37.5641 126.9979 --label "서울 중구"

# 저장된 기본 설정 확인
python scripts/air_quality.py show-default telegram:8209218742 --json

# 저장된 기본 지역 기준으로 바로 조회
python scripts/air_quality.py now --user telegram:8209218742

# 기본 설정 초기화 (삭제)
python scripts/air_quality.py clear-default telegram:8209218742
```

### 4) 여러 지역 동시 비교 (`compare`)

여러 도시의 대기질을 한 번에 비교합니다. 일부 지역에 오타가 있어도 유효한 지역의 결과는 중단 없이 출력됩니다.

```bash
python scripts/air_quality.py compare 서울 수원 부산 제주
```

### 5) 대기질 감시 알림 관리 (`alert-add`, `alert-list`, `alert-check`, `alert-remove`)

원하는 지역, 지표, 임계 등급을 설정하여 지속적인 감시 규칙을 생성합니다.

```bash
# 알림 규칙 추가 (초미세먼지 나쁨 이상)
python scripts/air_quality.py alert-add telegram:8209218742 "서울 중구" pm2_5 나쁨

# 오존 알림 추가
python scripts/air_quality.py alert-add telegram:8209218742 강남구 ozone 나쁨

# 등록된 알림 규칙 목록 조회
python scripts/air_quality.py alert-list --user telegram:8209218742

# 현재 상태 점검 (중복 알림 방지 탑재)
python scripts/air_quality.py alert-check --user telegram:8209218742

# 알림 규칙 삭제
python scripts/air_quality.py alert-remove --user telegram:8209218742 --id 1
python scripts/air_quality.py alert-remove --user telegram:8209218742 --all
```

### 6) 날씨 결합 아침 브리핑 (`morning-brief`)

기온, 날씨 요약, 강수 확률, 미세먼지 수치, 행동 요령을 한눈에 보기 쉬운 모바일 요약형으로 생성합니다.

```bash
python scripts/air_quality.py morning-brief "서울 중구"
python scripts/air_quality.py morning-brief --user telegram:8209218742
```

### 7) OpenClaw Cron 자동화 스케줄 생성 (`cron-plan`)

OpenClaw의 `cron add`에 즉시 등록할 수 있는 표준 작업 명세를 JSON으로 생성합니다. 현재 실행 환경의 스킬 설치 경로를 동적으로 자동 주입합니다.

```bash
# 매일 아침 7시 30분 아침 브리핑 작업 초안
python scripts/air_quality.py cron-plan morning-brief telegram:8209218742 --region "서울 중구" --hour 7 --minute 30 --json

# 1시간마다 실행하는 대기질 알림 점검 작업 초안
python scripts/air_quality.py cron-plan alert-check telegram:8209218742 --json
```

---

## 🔑 AirKorea OpenAPI 연동 가이드

에어코리아 실시간 측정소 실측값을 사용하려면 공공데이터포털에서 API 키를 발급받아 등록합니다. (키가 없어도 Open-Meteo로 정상 동작합니다.)

1. **공공데이터포털(data.go.kr) 로그인**
2. **`한국환경공단_에어코리아_대기오염정보(ArpltnInforInqireSvc)`** 검색 후 **[활용신청]** 진행
3. 마이페이지 ➔ 개발계정에서 발급된 **일반 인증키(Encoding 또는 Decoding)** 복사
4. 스킬에 프로바이더 및 API 키 저장:

```bash
python scripts/air_quality.py setup-provider airkorea --airkorea-api-key "발급받은서비스키" --json
```

설정 확인:

```bash
python scripts/air_quality.py show-config --json
python scripts/air_quality.py now "서울 중구" --provider airkorea
```

> **Tip:** 공공데이터포털 활용신청 승인 직후에는 게이트웨이 동기화까지 약 10분~1시간가량 소요될 수 있습니다.

---

## 📂 저장소 구조 및 로컬 상태 파일 정책

```text
openclaw-korea-air-quality/
├── SKILL.md                 # OpenClaw 스킬 정의 및 오퍼레이터 가이드
├── README.md                # 저장소 전체 안내 문서
├── scripts/
│   └── air_quality.py       # 하위 호환 CLI 진입점 (구 호출 그대로 동작)
├── src/airquality/          # SOLID 분리 패키지 본체 (constants/paths/store/http/parsing/grading/geo/providers/services/cli/app)
├── tests/
│   └── test_cli_parity.py   # 리팩토링 동등성 테스트
├── references/              # API 기획 및 국내 데이터 규격 문서
│   ├── api-and-product-plan.md
│   ├── domestic-api-notes.md
│   └── alert-and-briefing.md
└── data/                    # 로컬 런타임 상태 (기본 gitignore 대상)
    ├── config.json          # 프로바이더 및 API 키 설정
    ├── user-preferences.json# 사용자별 기본 지역/위치
    ├── alert-rules.json     # 알림 규칙
    ├── alert-state.json     # 알림 중복 방지 상태
    └── station-cache.json   # 측정소 및 지오코딩 캐시
```

> [!NOTE]
> `data/` 내부의 설정 및 상태 파일은 개인화된 런타임 정보이므로 Git 커밋 대상에서 제외(`gitignore`)됩니다. 저장소 코드와 문서는 완전 무상태(Stateless)로 배포 가능합니다.

---

## 🧪 권장 Smoke Test

배포 또는 업데이트 후 아래 테스트로 전체 동작 상태를 빠르게 검증할 수 있습니다.

```bash
python scripts/air_quality.py show-config --json
python scripts/air_quality.py resolve-region "서울 중구" --json
python scripts/air_quality.py now 서울 --json
python scripts/air_quality.py morning-brief "서울 중구"
python scripts/air_quality.py compare 서울 수원 부산
python scripts/air_quality.py cron-plan morning-brief testuser --region "서울 중구" --json
```

리팩토링 동등성 단위 테스트(네트워크 불필요):

```bash
python -m pytest tests/ -q
```

---

## 🤝 OpenClaw 워크스페이스 연동

이 저장소는 OpenClaw 워크스페이스의 스킬 디렉토리에 설치하여 바로 사용할 수 있습니다:

```bash
openclaw skills info korea-air-quality
```

모든 조회, 브리핑, 알림은 OpenClaw 채팅창에서 한국어 자연어 명령으로 자유롭게 호출할 수 있습니다.
