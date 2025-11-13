# Investment Report - 주식 시장 분석 자동화 시스템

한국 주식시장(KOSPI/KOSDAQ)의 일간 데이터를 자동으로 수집하여 시각화된 리포트를 생성하고, 텔레그램과 웹 API를 통해 배포하는 자동화 시스템입니다.

![거래량 TOP15](https://github.com/user-attachments/assets/cf3e321f-28d4-4857-8fb2-97ebd2f56fae)
![순매수대금 TOP15](https://github.com/user-attachments/assets/ec76c682-df3b-4e74-afe7-ecef22043f58)

## 주요 기능

### 1. 거래량 분석 리포트
- KOSPI/KOSDAQ 전종목 중 일간 거래량 TOP 15 종목 분석
- 시가/고가/저가/종가/거래량 정보 제공

### 2. 투자자별 순매수대금 리포트
- 투자주체별(투신/연기금/사모/외국인) 순매수대금 TOP 15
- 연속 순매수 일수 추적 (괄호 안 표시)
- KOSPI/KOSDAQ 시장별 분리 제공

### 3. RS(Relative Strength) 랭킹 리포트
- 시장 대비 상대 강도 지수 계산 및 순위 제공
- 20일 기준 RS 점수 (0~100 정규화)
- KOSPI/KOSDAQ 별도 분석

### 4. 52주 신고가 종목 리포트
- 52주 신고가를 경신한 종목 리스트
- 현재가, 시가총액, 거래량 정보 포함
- 네이버 금융 API 연동

## 기술 스택

### 핵심 라이브러리
- **pykrx** (1.0.47): 한국 주식시장 데이터 수집 API
- **pandas** (2.2.2): 데이터 분석 및 가공
- **requests** (2.32.3): HTTP 통신 (네이버 API, 웹 API 연동)

### 이미지 처리
- **imgkit** (1.2.3): HTML → PNG 이미지 변환
- **Pillow** (≥10.0.0): 이미지 압축 및 리사이징
- **wkhtmltopdf**: HTML 렌더링 엔진 (별도 설치 필요)

### 유틸리티
- **python-dotenv** (1.0.1): 환경변수 관리
- **holidays** (0.54): 한국 공휴일 체크

## 프로젝트 구조

```
investment-report/
├── main.py                          # 메인 실행 스크립트
├── requirements.txt                 # Python 패키지 의존성
├── .env                            # 환경변수 설정 (git 제외)
├── .env.example                    # 환경변수 템플릿
├── .gitignore
│
├── reports/                        # 리포트 생성 모듈
│   ├── volume_report.py           # 거래량 리포트
│   ├── investor_report.py         # 투자자별 순매수 리포트
│   ├── rs_report.py               # RS 랭킹 리포트
│   ├── high52_week_report.py      # 52주 신고가 리포트
│   └── img/                       # 생성된 리포트 이미지
│
├── utils/                         # 유틸리티 모듈
│   ├── api_util.py               # 웹 API 연동
│   ├── telegram_util.py          # 텔레그램 봇 연동
│   └── logger_util.py            # 로깅 시스템
│
├── thumbnail/                    # 웹용 썸네일 이미지
│   ├── thumbnail_volume_top15.png
│   ├── thumbnail_investor_top15.png
│   ├── thumbnail_rs_top15.png
│   └── thumbnail_high52_week.png
│
└── logs/                         # 일별 로그 파일
```

## 설치 및 실행

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. wkhtmltopdf 설치

HTML을 이미지로 변환하기 위해 필요합니다.

- **Windows**: [다운로드 링크](https://wkhtmltopdf.org/downloads.html)에서 설치 파일 다운로드
- **Linux**:
  ```bash
  sudo apt-get install wkhtmltopdf
  ```

### 3. 환경변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 다음 값들을 설정합니다:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
TELEGRAM_CHAT_TEST_ID=your_telegram_chat_test_id_here
WKHTMLTOIMAGE_PATH=your_wkhtmltoimage_path_here
DART_API_KEY=your_dart_api_key_here# BASE URL
BASE_URL=http://example.com
```

#### 환경변수 설명
- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰 (BotFather에서 발급)
- `TELEGRAM_CHAT_ID`: 메인 리포트 전송 채널 ID
- `TELEGRAM_CHAT_TEST_ID`: 테스트/에러 메시지 전송 채널 ID
- `WKHTMLTOIMAGE_PATH`: wkhtmltoimage 실행 파일의 절대 경로
- `DART_API_KEY`: DART API 키 (현재 미사용)

### 4. 실행

```bash
python main.py
```

## 데이터 흐름

```
┌─────────────────┐
│  pykrx API      │ ← 거래량, 투자자 데이터, 지수 데이터
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
┌────────▼────────┐ ┌─────▼──────────┐
│ Naver 금융 API  │ │  데이터 가공    │
│ (52주 신고가)   │ │  (pandas)      │
└────────┬────────┘ └─────┬──────────┘
         │                 │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ HTML 생성 + CSS │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │ wkhtmltoimage   │
         │ (PNG 변환)      │
         └────────┬────────┘
                  │
         ┌────────▼────────────────┐
         │  이미지 압축 및 최적화   │
         └────────┬────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
┌────────▼────────┐ ┌─────▼──────────┐
│ 텔레그램 전송   │ │ 웹 API 전송    │
│ (media group)   │ │ (게시글 생성)  │
└─────────────────┘ └────────────────┘
```

## 주요 모듈 설명

### main.py
- 전체 리포트 생성 프로세스 오케스트레이션
- 공휴일 체크 (거래일이 아니면 실행 종료)
- 4개 리포트 순차 생성 및 배포
- 에러 핸들링 및 텔레그램 알림

### reports/volume_report.py
- pykrx API로 OHLCV 데이터 수집
- 거래량 기준 상위 15종목 필터링
- 5회 재시도 로직 (20초 간격)
- HTML 테이블 → PNG 이미지 변환

### reports/investor_report.py
- 투자주체별(투신/연기금/사모/외국인/총합) 순매수 데이터 수집
- 연속 순매수 일수 계산
- 시장별(KOSPI/KOSDAQ), 투자자 그룹별 4개 이미지 생성
- 연속 매수 종목 강조 표시 (빨간색 텍스트)

### reports/rs_report.py
- Relative Strength 지수 계산
  - 공식: RS = (개별 주식 수익률) / (시장 지수 수익률)
- 로그 스케일 정규화 (0~100)
- 20일 기준 RS 순위 제공
- KOSPI/KOSDAQ 별도 분석

### reports/high52_week_report.py
- 네이버 금융 API 크롤링
- 페이지네이션으로 전체 52주 신고가 종목 수집
- 상위 20개 종목 선별
- 10개 종목당 1페이지로 분할하여 이미지 생성

### utils/telegram_util.py
- 텔레그램 Bot API 연동
- 단일/다중 이미지 전송
- 메인 채널 + 테스트 채널 분리 운영
- Media Group API 활용 (최대 10개 이미지)

### utils/api_util.py
- 웹 백엔드 API 연동 (`/api/board-research`)
- 이미지 자동 압축 (최대 800px, 1MB 이하)
- multipart/form-data 방식 업로드
- 썸네일 이미지 별도 전송
- 게시글 생성 및 URL 응답 처리

### utils/logger_util.py
- 싱글톤 패턴 로거
- 콘솔 + 파일 동시 출력
- 일별 로그 파일 생성 (`logs/YYYY-MM-DD_log.log`)
- 로그 레벨: DEBUG, INFO, WARNING, ERROR

## 이미지 생성 프로세스

### HTML 템플릿 특징
- **폰트**: Noto Sans KR (Google Fonts) - 한글 지원
- **테이블 디자인**:
  - 다크 헤더 (#333333)
  - 교대 행 색상 (가독성 향상)
  - 호버 효과
  - 중앙 정렬
- **출처 표기**: "출처 : MQ(Money Quotient)"

### 이미지 최적화
1. HTML → PNG 변환 (wkhtmltoimage)
2. 최대 너비 800px로 리사이징
3. 1MB 이하로 압축 (품질 자동 조정)
4. EXIF 메타데이터 제거

## 자동화 스케줄링 (권장)

현재는 수동 실행이지만, 다음과 같이 자동화할 수 있습니다:

### Windows (작업 스케줄러)
1. "작업 스케줄러" 실행
2. "기본 작업 만들기"
3. 트리거: 매일 오후 4시 (장 마감 후)
4. 동작: `python C:\path\to\investment-report\main.py`

### Linux (cron)
```bash
# 매일 오후 4시 실행
0 16 * * 1-5 cd /path/to/investment-report && python main.py
```

## 보안 및 에러 처리

### 재시도 로직
- pykrx API 호출: 5회 재시도 (20초 간격)
- 네트워크 타임아웃 처리

### 에러 알림
- 모든 에러를 테스트 텔레그램 채널로 전송
- 에러 메시지에 함수명, 파라미터, 상세 정보 포함
- API 에러: 상태 코드 + 응답 본문

### 로깅
- 일별 로그 파일 자동 생성
- 로그 레벨별 필터링 가능
- 콘솔과 파일 동시 출력

## 향후 개선 계획

- [ ] APScheduler를 활용한 자동 스케줄링 기능 추가
- [ ] 데이터베이스 연동으로 히스토리 관리
- [ ] 임계값 기반 알림 시스템
- [ ] 실시간 모니터링 대시보드
- [ ] 병렬 처리를 통한 성능 최적화
- [ ] 단위 테스트 및 통합 테스트 확대

## 라이선스

본 프로젝트는 개인 포트폴리오 목적으로 제작되었습니다.

## 문의

프로젝트 관련 문의사항이나 이슈는 GitHub Issues를 통해 등록해주세요.

---

**최종 업데이트**: 2025년 10월
**개발자**: MQ(Money Quotient)
