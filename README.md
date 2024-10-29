# investment-report
주식 종목 정보 레포트

KOSPI, KOSDAQ 전종목중 일간 기준 순매수거래대금이 가장 높았던 TOP 15 종목 정보를 이미지로 만들어 텔레그램으로 전달

![image](https://github.com/user-attachments/assets/cf3e321f-28d4-4857-8fb2-97ebd2f56fae)
![image](https://github.com/user-attachments/assets/ec76c682-df3b-4e74-afe7-ecef22043f58)

## 설치 방법
1. 필요한 패키지 설치
```
pip install -r requirements.txt
```

2. wkhtmltopdf 설치
- Windows: [[다운로드 링크]](https://wkhtmltopdf.org/downloads.html)
- Linux: `apt-get install wkhtmltopdf`

3. 환경변수 설정
- `.env.example` 파일을 복사하여 `.env` 파일 생성
- 텔레그램 환경변수 값 설정
