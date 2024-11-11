import sys
from datetime import datetime, timedelta
import holidays
from reports.volume_report import VolumeReport
from reports.investor_report import InvestorReport
from reports.rs_report import RSReport
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def isTodayHoliday():
    kr_holidays = holidays.KR()
    today = datetime.today().date()
    return today in kr_holidays

def main():
    if isTodayHoliday():
        print('공휴일 종료')
        sys.exit()

    print("\n=== 데이터 수집 시작 ===")
    
    # 날짜 설정
    today_yyyymmdd = datetime.today().strftime('%Y%m%d')
    # today_yyyymmdd = '20241108'  # 테스트용
    today_dt = datetime.strptime(today_yyyymmdd, '%Y%m%d')
    start_date = (today_dt - timedelta(days=15)).strftime('%Y%m%d')
    today_display = today_dt.strftime('%Y-%m-%d')
    print(f"처리 날짜: {today_display}")

    # 1. 거래량 TOP 15 처리
    print("\n1. 전종목 거래량 TOP 15 처리 시작")
    volume_reporter = VolumeReport()
    volume_reporter.create_report(today_yyyymmdd, today_display)
    print("전종목 거래량 TOP 15 처리 완료")

    # 2. 투자자 데이터 처리
    print("\n2. 투자자 데이터 처리 시작")
    investor_reporter = InvestorReport()
    investor_reporter.create_report(today_yyyymmdd, start_date)
    print("투자자 데이터 처리 완료")

    # 3. RS 데이터 처리
    print("\n3. RS 데이터 처리 시작")
    rs_reporter = RSReport()
    rs_reporter.create_report(today_yyyymmdd)
    print("RS 데이터 처리 완료")
    
    print("\n=== 모든 데이터 처리 완료 ===")

if __name__ == "__main__":
    main()
