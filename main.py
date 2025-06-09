import sys
from datetime import datetime, timedelta
import holidays
from reports.high52_week_report import High52WeekReport
from reports.volume_report import VolumeReport
from reports.investor_report import InvestorReport
from reports.rs_report import RSReport
from dotenv import load_dotenv
from utils.telegram_util import TelegramUtil
from utils.api_util import ApiUtil, ApiError
from utils.logger_util import LoggerUtil

load_dotenv()

def isTodayHoliday():
    kr_holidays = holidays.KR()
    today = datetime.today().date()
    return today in kr_holidays

def main():
    logger = LoggerUtil().get_logger()
    
    if isTodayHoliday():
        logger.info('공휴일 종료')
        sys.exit()

    logger.info("\n=== 데이터 수집 시작 ===")
    
    telegram = TelegramUtil()
    api_util = ApiUtil()
    
    # 날짜 설정
    today_yyyymmdd = datetime.today().strftime('%Y%m%d')
    # today_yyyymmdd = '20250217'  # 테스트용
    today_dt = datetime.strptime(today_yyyymmdd, '%Y%m%d')
    start_date = (today_dt - timedelta(days=15)).strftime('%Y%m%d')
    today_display = today_dt.strftime('%Y-%m-%d')
    logger.info(f"처리 날짜: {today_display}")

    # 1. 거래량 TOP 15 처리
    logger.info("\n1. 전종목 거래량 TOP 15 처리 시작")
    volume_reporter = VolumeReport()
    volume_images = volume_reporter.create_report(today_yyyymmdd, today_display)
    if volume_images:
        image_paths = [img_path for img_path, _ in volume_images]
        caption = f"{today_display} 전종목 거래량 TOP 15"
        telegram.send_multiple_photo(image_paths, caption)
        try:
            api_util.create_post(
                title=caption,
                content="전종목 거래량 상위 15개 종목 분석 결과",
                category="거래량",
                writer="admin",
                image_paths=image_paths
            )
        except ApiError as e:
            error_message = f"❌ API 오류 발생\n\n{e.message}"
            telegram.send_test_message(error_message)
    logger.info("전종목 거래량 TOP 15 처리 완료")

    # 2. 투자자 데이터 처리
    logger.info("\n2. 투자자 데이터 처리 시작")
    investor_reporter = InvestorReport()
    investor_images = investor_reporter.create_report(today_yyyymmdd, start_date)
    if investor_images:
        caption = f"{today_display} 시장별 순매수대금 TOP 15"
        telegram.send_multiple_photo(investor_images, caption)
        try:
            api_util.create_post(
                title=caption,
                content="시장별 투자자 순매수대금 상위 15개 종목 분석 결과",
                category="순매수대금",
                writer="admin",
                image_paths=investor_images
            )
        except ApiError as e:
            error_message = f"❌ API 오류 발생\n\n{e.message}"
            telegram.send_test_message(error_message)
    logger.info("투자자 데이터 처리 완료")

    # 3. RS 데이터 처리
    logger.info("\n3. RS 데이터 처리 시작")
    rs_reporter = RSReport()
    rs_images = rs_reporter.create_report(today_yyyymmdd)
    if rs_images:
        caption = f"{today_display} 시장별 RS 랭킹 TOP 15"
        telegram.send_multiple_photo(rs_images, caption)
        try:
            api_util.create_post(
                title=caption,
                content="시장별 RS(Relative Strength) 상위 15개 종목 분석 결과",
                category="RS랭킹",
                writer="admin",
                image_paths=rs_images
            )
        except ApiError as e:
            error_message = f"❌ API 오류 발생\n\n{e.message}"
            telegram.send_test_message(error_message)
    logger.info("RS 데이터 처리 완료")

    # 4. 52주 신고가 종목 데이터 처리
    logger.info("\n4. 52주 신고가 종목 데이터 처리 시작")
    high52_week_reporter = High52WeekReport()
    high52_week_images = high52_week_reporter.create_report()
    if high52_week_images:
        caption = f"{today_display} 52주 신고가 종목 리포트"
        telegram.send_multiple_photo(high52_week_images, caption)
        try:
            api_util.create_post(
                title=caption,
                content="52주 신고가 종목 리포트",
                category="52주 신고가",
                writer="admin",
                image_paths=high52_week_images
            )
        except ApiError as e:
            error_message = f"❌ API 오류 발생\n\n{e.message}"
            telegram.send_test_message(error_message)
    logger.info("52주 신고가 종목 데이터 처리 완료")
    
    logger.info("\n=== 모든 데이터 처리 완료 ===")

if __name__ == "__main__":
    main()
