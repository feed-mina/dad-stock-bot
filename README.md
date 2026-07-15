# dad-stock-bot

### 아빠 심부름으로 만드는 주식 자동 실시간 구글스프레이드 연동 프로젝트

아버님이 보시기 쉬운 구글 스프레드시트 화면에서 국내 주식 시세를 실시간으로 확인하고,
필요하면 자동 매매까지 확장할 수 있도록 만드는 실전형 프로젝트입니다.

## 핵심 목표

- 실시간 시세를 안정적으로 수신하고 끊김 없이 갱신하기
- 스프레드시트/엑셀 기반의 직관적인 모니터링 환경 만들기
- 모의투자 기반으로 안전하게 자동매매 로직까지 확장하기

## 현재 구현 범위

이 저장소는 이슈 #3의 8단계 로드맵 중, API 키 없이도 검증 가능한 기반 코드를 먼저 제공합니다.

- `.env` 기반 KIS Open API 설정 관리
- OAuth 접근 토큰 및 웹소켓 approval key 발급 클라이언트
- 국내 주식 현재가 REST 조회(`FHKST01010100`)
- 국내 주식 실시간 체결가 웹소켓 구독 메시지 및 `H0STCNT0` 파서
- SQLite 기반 시세/신호 저장소
- 이동평균 돌파 기반 1차 매수/매도/대기 신호
- 텔레그램 알림 전송 어댑터
- 공공데이터포털 금융위원회 주식시세정보 기반 일별/지연 시세 조회
- 관심종목 일괄 동기화, 최근 저장 데이터 조회, CSV 내보내기

실제 주문 전송은 아직 구현하지 않았습니다. 모의투자 환경에서 시세 수신과 전략 신호를 충분히 검증한 뒤 주문 API를 별도 단계로 붙입니다.

## 빠른 시작

```powershell
Copy-Item .env.example .env
```

`.env`에 한국투자증권에서 발급받은 모의투자 AppKey/SecretKey를 입력합니다.

```powershell
python -m dad_stock_bot check-config
python -m dad_stock_bot daily-quote 005930 --base-date 20260708
python -m dad_stock_bot daily-sync --symbols 005930,000660 --base-date 20260708
python -m dad_stock_bot latest --limit 10
python -m dad_stock_bot dedupe
python -m dad_stock_bot export-csv --output data/latest_ticks.csv
python -m dad_stock_bot gui
python -m dad_stock_bot quote 005930
python -m dad_stock_bot listen
```

`daily-quote`는 공공데이터포털 `PUBLIC_DATA_SERVICE_KEY`를 사용합니다. 키가 아직 없다면 `check-config`와 단위 테스트까지 먼저 진행할 수 있고, 키를 받은 뒤 `.env`에 넣으면 됩니다.

`daily-sync`는 같은 종목/기준일의 공공데이터 행을 새 값으로 교체합니다. 기존 버전에서 중복 저장된 행은 `python -m dad_stock_bot dedupe`로 한 번 정리한 뒤 CSV를 다시 내보내면 됩니다.

GUI로 실행하려면 아래 명령을 사용합니다.

```powershell
$env:PYTHONPATH = "src"
python -m dad_stock_bot gui
```

GUI에서는 관심종목 동기화, 저장 데이터 새로고침, 요약 CSV 저장, 중복 정리를 버튼으로 실행할 수 있습니다.
60대 한국인 사용자가 보기 쉽도록 한국어 버튼, 큰 글씨, 상승/하락 색상, 상단 요약 영역을 제공합니다.

403 Forbidden이 나오면 아래를 먼저 확인합니다.

- 공공데이터포털에서 `금융위원회_주식시세정보` 활용신청이 승인되었는지 확인
- `.env`의 `PUBLIC_DATA_SERVICE_KEY`에 값이 들어갔는지 확인
- 가능하면 `일반 인증키 (Decoding)` 값을 사용
- `Encoding` 값을 붙여 넣은 경우 최신 코드에서는 자동으로 한 번 디코딩해서 요청

개발 환경에서 패키지를 설치하지 않고 바로 실행할 때는 `PYTHONPATH=src`를 지정합니다.

```powershell
$env:PYTHONPATH = "src"
python -m dad_stock_bot check-config
```

세부 실행 계획은 `docs/issue-3-development-plan.md`에 정리되어 있습니다.

## 개발 진행 절차 (8단계)

완전한 실시간 국내 주가를 안정적으로 받아오고, 자동매매까지 확장하기 위한 표준 개발 프로세스입니다.

### 1단계. 증권사 선정 및 API 서비스 신청

가장 먼저 어떤 증권사 API를 사용할지 정하고 권한을 획득해야 합니다.

- 추천 증권사: 한국투자증권(KIS Developers), 키움증권(Open API+)
- 팁: Mac 환경이거나 Python으로 가볍게 시작하려면 REST API/웹소켓을 지원하는 한국투자증권이 유리합니다.
- 참고: 키움증권은 OCX 방식이라 Windows 환경 및 32비트 Python 제약이 있습니다.

수행 작업:
- 증권사 홈페이지에서 개발자 계정 신청
- 모의투자 계좌 개설(필수)
- AppKey/SecretKey 발급

### 2단계. 개발 환경 세팅 및 GitHub 연동

수행 작업:
- 로컬 컴퓨터에 개발 환경(Python, VS Code 등) 구축
- GitHub 레포지토리 생성 및 로컬 연동(`git clone`)

보안 주의:
- AppKey, SecretKey, 계좌번호를 코드 파일에 직접 작성해 업로드하지 않습니다.
- 민감정보는 `.env`에 저장하고, `.gitignore`에 `.env`를 반드시 등록합니다.

### 3단계. REST API 로그인 및 토큰 발급 구현

증권사 서버 접근을 위한 인증 단계입니다.

개발 내용:
- Python `requests` 라이브러리로 인증 서버에 AppKey/SecretKey 전송
- 실시간 데이터 요청에 필요한 Access Token 발급
- 발급 토큰을 메모리 또는 안전한 저장소에 관리

### 4단계. 웹소켓(WebSocket) 실시간 시세 수신 구현 (핵심)

구글 시트처럼 주기적 호출(Polling)이 아니라, 시세가 변할 때마다 즉시 데이터를 받기 위해 웹소켓을 사용합니다.

수행 작업:
- Python `websockets` 라이브러리 활용
- 실시간 시세 서버 연결
- 원하는 종목코드(예: 삼성전자 005930) 실시간 체결가 등록 패킷 전송
- 서버가 전달하는 실시간 JSON 데이터 파싱

필수 라이브러리:
- `requests` (인증)
- `websockets` (실시간 데이터)

### 5단계. 엑셀(Excel) 또는 데이터베이스(DB) 연동

받아온 실시간 데이터를 화면에 보여주거나 저장하는 단계입니다.

엑셀 연동:
- `openpyxl` 또는 `xlwings`로 시세 데이터를 특정 셀에 실시간 반영

DB 연동:
- 초당 다수 업데이트를 고려해 SQLite 또는 Redis 기반 임시 저장(캐싱) 구조 권장

### 6단계. 매매 로직(알고리즘) 및 주문 기능 구현

시세 조회에서 나아가 자동 매매로 확장하는 단계입니다.

수행 작업:
- 간단한 매매 조건 정의(예: 5일 이동평균선 돌파 시 매수)
- 아버님이 원하는 매수/매도 규칙을 코드로 구현
- 조건 충족 시 증권사 주문 API 호출로 매수/매도 주문 전송

### 7단계. 대시보드 연동 (엑셀/텔레그램)

엑셀 연동:
- 실시간 시세를 아버님이 보기 쉬운 엑셀 화면에 반영

알림 연동:
- 매매 체결 또는 급등락 발생 시 텔레그램 리포트 전송

### 8단계. 시스템 구축 및 예외 처리

프로젝트를 안정적으로 장시간 운영하기 위한 최종 마무리 단계입니다.

수행 작업:
- 네트워크 끊김, 토큰 만료, 서버 점검 시간 등 오류 상황 대비
- `try-except` 기반 재시도/재연결 로직 구현
- `logging` 라이브러리로 실행 이력 및 에러 로그 파일 저장

안전 장치:
- 반드시 모의투자(Paper Trading) 계좌에서 먼저 충분히 테스트한 뒤 실계좌로 확장합니다.
