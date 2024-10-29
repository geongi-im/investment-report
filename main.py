import sys
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta, date
import matplotlib.pyplot as plt
from urllib.request import urlopen
import urllib.parse
import requests
import re
import holidays
import os
import imgkit  # 추가된 import

# 결과는 18시 이후 나옴
# 투신, 연기금, 사모 => (금융투자 / 보험 / 투신 / 사모 / 은행 / 기타금융 / 연기금 / 기관합계 / 기타법인 / 개인 / 외국인합계 / 기타외국인 / 전체)
# data : http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020303
# github : https://github.com/sharebook-kr/pykrx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, 'img')

# img 디렉토리가 없으면 생성하도록 추가
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

chat_id = "391698624" #mq_bot
# chat_id = "-4210158716" #MQ_GROUP

# 파일 상단에 상수 정의
INVESTORS = [
    {'name': '투신', 'file_prefix': 'top_investment_trust'},
    {'name': '연기금', 'file_prefix': 'top_pension_fund'},
    {'name': '사모', 'file_prefix': 'top_private_fund'},
    {'name': '외국인', 'file_prefix': 'top_foreign_fund'},
    {'name': '기관합계', 'file_prefix': 'top_institution_fund'}
]

def isTodayHoliday():
    kr_holidays = holidays.KR()
    today = date.today()
    return today in kr_holidays

def sendTelegram(message) :
    message = urllib.parse.quote_plus(message)
    urlopen("https://api.telegram.org/bot7003316340:AAEBx-MW2rEpRJcypv05Iu_mOi-kFUj_tZk/sendMessage?chat_id=${chat_id}&parse_mode=html&text="+message)

def sendTelegramPhoto(photo_path, caption=""):
    url = f"https://api.telegram.org/bot7003316340:AAEBx-MW2rEpRJcypv05Iu_mOi-kFUj_tZk/sendPhoto"

    with open(photo_path, 'rb') as photo:
        payload = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "html"
        }
        files = {
            "photo": photo
        }
        response = requests.post(url, data=payload, files=files)

    return response.json()

def get_top_stocks_by_net_buying(market, start_date, end_date, investor, top_n=15):
    df = stock.get_market_net_purchases_of_equities(start_date, end_date, market, investor)
    top_stocks = df.nlargest(top_n, '순매수거래대금')
    return top_stocks[['종목명', '순매수거래대금']]

def get_stock_trading_value_by_date(ticker, start_date, end_date, investor, detail=True):
    """
    주식 거래 데이터를 가져오는 함수
    Args:
        ticker: 종목 코드
        start_date: 시작일
        end_date: 종료일
        investor: 투자자 유형
        detail: 상세 데이터 여부 (기본값: True)
    Returns:
        int: 연속 매수일 수
        None: 데이터가 없는 경우
    """
    try:
        df = stock.get_market_trading_value_by_date(start_date, end_date, ticker, detail=detail)
        
        # DataFrame이 비어있는 경우 None 반환
        if df.empty:
            print(f"Warning: No data available for ticker {ticker}")
            return None
            
        df_sorted = df.sort_index(ascending=False)
        
        # 외국인의 경우 '외국인합계' 컬럼 사용
        investor_key = '외국인합계' if investor == '외국인' else investor
        consecutive_positive_days = check_consecutive_positive_days(df_sorted[investor_key])
        return consecutive_positive_days
        
    except Exception as e:
        print(f"Error processing ticker {ticker}: {str(e)}")
        return None

def check_consecutive_positive_days(series):
    max_consecutive_days = 0
    current_consecutive_days = 0

    for value in series:
        if value > 0:
            current_consecutive_days += 1
            if current_consecutive_days > max_consecutive_days:
                max_consecutive_days = current_consecutive_days
        else: #음수가 나오면 break
            break

    return max_consecutive_days

def get_top_15_stocks_by_volume(date):
    ohlcv_data = stock.get_market_ohlcv(date=date, market="ALL") # 특정 날짜의 모든 종목의 OHLCV 데이터를 가져옵니다.
    ohlcv_data['거래량'] = ohlcv_data['거래량'].astype(int) # '거래량' 열을 정수형으로 변환합니다.
    sorted_data = ohlcv_data.sort_values(by="거래량", ascending=False) # DataFrame을 거래량 기준으로 내림차순으로 정렬합니다.
    top_15_stocks = sorted_data.head(15) # 상위 15개 종목을 선택합니다.
    return top_15_stocks

def transform_df(df):
    df = df.reset_index(drop=True)  # 인덱스 제거
    df['종목명'] = df.apply(lambda x: x['종목명'] + f"({int(x['연속매수일'])})" if x['연속매수일'] > 1 else x['종목명'], axis=1)
    df['순매수거래대금'] = (df['순매수거래대금'] / 100000000).round(2).map('{:,}'.format)
    return df[['종목명', '순매수거래대금', 'EPS']]  # EPS 컬럼 추가

def transform_df_volume(df):
    df['종목명'] = df.index.map(stock.get_market_ticker_name)
    df['거래량'] = df['거래량'].apply(lambda x: f"{x:,}")
    df = df.reset_index(drop=True)  # 인덱스 제거
    return df[['종목명', '거래량']]

def process_investor_data(investor_info, market, today_yyyymmdd, start_date, today_display, detail=True):
    """투자자별 데이터를 처리하는 함수"""
    investor_name = investor_info['name']
    file_path = f"{investor_info['file_prefix']}.png"
    
    title = f"{today_display} {investor_name} 순매수거래대금 TOP 15"
    print(title)
    
    top_stocks = get_top_stocks_by_net_buying(market, today_yyyymmdd, today_yyyymmdd, investor_name)
    
    for ticker in top_stocks.index:
        row = top_stocks.loc[ticker]
        consecutive_days = get_stock_trading_value_by_date(
            ticker, start_date, today_yyyymmdd, investor_name, detail=detail
        )
        top_stocks.at[ticker, '연속매수일'] = consecutive_days
        print(f"{row['종목명']}: {row['순매수거래대금']} (Consecutive Days: {consecutive_days})")

    transformed_df = transform_df(top_stocks)
    new_file_path = save_df_as_image(transformed_df, file_path, title)
    sendTelegramPhoto(new_file_path, title)

def process_volume_data(today_yyyymmdd, today_display):
    """거래량 TOP 15 데이터를 처리하는 함수"""
    title = f"{today_display} 전종목 거래량 TOP 15"
    file_path = 'top_volume.png'
    print(title)
    
    top_15_stocks = get_top_15_stocks_by_volume(today_yyyymmdd)
    transformed_df = transform_df_volume(top_15_stocks)
    new_file_path = save_df_as_image(transformed_df, file_path, title)
    sendTelegramPhoto(new_file_path, title)

def save_df_as_image(df, file_name, title):
    """DataFrame을 이미지로 저장하는 함수"""

    file_name, file_extension = os.path.splitext(file_name)
    current_date = datetime.now().strftime('%Y%m%d')
    new_file_path = os.path.join(IMG_DIR, f"{file_name}_{current_date}{file_extension}")
    
    # 이전 파일 삭제
    for old_file in os.listdir(IMG_DIR):
        if old_file.startswith(file_name) and old_file.endswith(file_extension):
            os.remove(os.path.join(IMG_DIR, old_file))
            print(f"기존 파일 삭제: {old_file}")

    html_str = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Noto Sans KR', sans-serif;
                margin: 20px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px auto;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            th, td {{
                border: 1px solid #e0e0e0;
                padding: 12px 15px;
                text-align: center;
            }}
            th {{
                background-color: #333333;
                color: white;
                font-weight: 700;
                font-size: 15px;
                white-space: nowrap;
            }}
            td {{
                font-size: 14px;
                font-weight: 500;
            }}
            tr:nth-child(even) td {{
                background-color: #f9f9f9;
            }}
            tr:hover td {{
                background-color: #f5f5f5;
            }}
            .caption {{
                text-align: center;
                font-size: 22px;
                font-weight: 700;
                margin: 20px 0;
                color: #333333;
            }}
            .source {{
                text-align: right;
                font-size: 12px;
                color: #666666;
                margin-top: 15px;
                font-weight: 400;
            }}
            .consecutive {{
                color: #d32f2f;
                font-weight: 700;
            }}
        </style>
    </head>
    <body>
        <div class="caption">{title}</div>
    '''

    # DataFrame을 HTML로 변환
    df_html = df.to_html(index=False, classes='styled-table')

    # 연속매수일 표시된 종목 강조 (종목명 컬럼이 있는 경우)
    if '종목명' in df.columns:
        for i, row in df.iterrows():
            value = row['종목명']
            if re.search(r'\((\d+)\)', str(value)) and int(re.search(r'\((\d+)\)', str(value)).group(1)) > 1:
                df_html = df_html.replace(f'>{value}<', f' class="consecutive">{value}<')

    html_str += df_html
    html_str += '''
        <div class="source">※ 출처 : MQ(Money Quotient)</div>
    </body>
    </html>
    '''

    # imgkit 설정
    options = {
        'format': 'png',
        'encoding': "UTF-8",
        'quality': 100,
        'width': 600,
        'enable-local-file-access': None,
        'minimum-font-size': 12,
        'zoom': 1.2,  # 전체적인 크기 조정
    }

    try:
        # wkhtmltoimage 경로 설정 (필요한 경우)
        config = imgkit.config(wkhtmltoimage='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltoimage.exe') #for windows
        # config = imgkit.config(wkhtmltoimage='/usr/local/bin/wkhtmltoimage') #for centos
        
        # HTML을 이미지로 변환
        imgkit.from_string(html_str, new_file_path, options=options, config=config)
        print(f"새 파일 저장: {new_file_path}")
        return new_file_path
    except Exception as e:
        print(f"이미지 생성 중 오류 발생: {str(e)}")
        return None


def save_combined_df_as_image(dfs, file_name, today_display, market_type):
    """dataframe데이터를 하나의 이미지로 저장"""
    if not file_name.endswith('.png'):
        file_name = file_name + '.png'
        
    file_name, file_extension = os.path.splitext(file_name)
    current_date = datetime.now().strftime('%Y%m%d')
    new_file_path = os.path.join(IMG_DIR, f"{file_name}_{current_date}{file_extension}")
    
    # 이전 파일 삭제
    for old_file in os.listdir(IMG_DIR):
        if old_file.startswith(file_name) and old_file.endswith(file_extension):
            os.remove(os.path.join(IMG_DIR, old_file))
            print(f"기존 파일 삭제: {old_file}")

    # DataFrame 데이터 준비
    columns = []
    for i, df in enumerate(dfs):
        investor_name = INVESTORS[i if len(dfs) == 3 else i+3]['name']
        columns.extend([
            (investor_name, '종목명'),
            (investor_name, '순매수대금'),
            (investor_name, 'EPS')
        ])
    
    columns = pd.MultiIndex.from_tuples(columns)
    
    combined_data = []
    for i in range(len(dfs[0])):
        row = []
        for df in dfs:
            row.extend([df['종목명'].iloc[i], df['순매수거래대금'].iloc[i], df['EPS'].iloc[i]])
        combined_data.append(row)
    
    df = pd.DataFrame(combined_data, columns=columns)

    # 캡션 설정
    if len(dfs) == 3:
        caption = f"{today_display} {market_type} 투신/연기금/사모 순매수대금 TOP 15"
    else:
        caption = f"{today_display} {market_type} 외국인/기관 순매수대금 TOP 15"

    # HTML 문자열 생성
    html_str = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Noto Sans KR', sans-serif;
                margin: 20px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px auto;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            th, td {{
                border: 1px solid #e0e0e0;
                padding: 12px 15px;
                text-align: center;
            }}
            th {{
                background-color: #333333;  /* 변경: 푸른색에서 검정색으로 */
                color: white;
                font-weight: 700;
                font-size: 15px;
                white-space: nowrap;
            }}
            td {{
                font-size: 14px;
                font-weight: 500;
            }}
            tr:nth-child(even) td {{
                background-color: #f9f9f9;  /* 변경: 짝수 행 배경색 */
            }}
            tr:hover td {{
                background-color: #f5f5f5;  /* 변경: 호버 시 배경색 */
            }}
            .caption {{
                text-align: center;
                font-size: 22px;
                font-weight: 700;
                margin: 20px 0;
                color: #333333;  /* 변경: 캡션 색상 */
            }}
            .source {{
                text-align: right;
                font-size: 12px;
                color: #666666;  /* 변경: 출처 텍스트 색상 */
                margin-top: 15px;
                font-weight: 400;
            }}
            .consecutive {{
                color: #d32f2f;  /* 변경: 연속매수일 강조 색상 */
                font-weight: 700;
            }}
        </style>
    </head>
    <body>
        <div class="caption">{caption}</div>
    '''

    # DataFrame을 HTML로 변환하고 헤더 텍스트 수정
    df_html = df.to_html(index=False, classes='styled-table')
    
    # '순매수대금' 헤더를 '순매수대금<br>(억원)'으로 변경
    df_html = df_html.replace('>순매수대금<', '>순매수대금<br>(억원)<')

    # '기관합계' 헤더를 '기관'으로 변경
    df_html = df_html.replace('>기관합계<', '>기관<')

    # 연속매수일 표시된 종목 강조
    for i in range(len(df)):
        for col in df.columns:
            if '종목명' in str(col[1]):
                value = df.iloc[i][col]
                if re.search(r'\((\d+)\)', str(value)) and int(re.search(r'\((\d+)\)', str(value)).group(1)) > 1:
                    df_html = df_html.replace(f'>{value}<', f' class="consecutive">{value}<')

    html_str += df_html
    html_str += '''
        <div class="source">※ 출처 : MQ(Money Quotient)</div>
    </body>
    </html>
    '''

    # imgkit 설정
    options = {
        'format': 'png',
        'encoding': "UTF-8",
        'quality': 100,
        'width': 1200 if len(dfs) == 3 else 800,  # 투신/연기금/사모일 때는 1200, 외국인/기관일 때는 900
        'enable-local-file-access': None,
        'minimum-font-size': 12
    }

    try:
        # wkhtmltoimage 경로 설정 (필요한 경우)
        config = imgkit.config(wkhtmltoimage='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltoimage.exe') #for windows
        # config = imgkit.config(wkhtmltoimage='/usr/local/bin/wkhtmltoimage') #for centos
        
        # HTML을 이미지로 변환
        imgkit.from_string(html_str, new_file_path, options=options, config=config)
        print(f"새 파일 저장: {new_file_path}")
        return new_file_path
    except Exception as e:
        print(f"이미지 생성 중 오류 발생: {str(e)}")
        return None

def main():
    if isTodayHoliday():
        print('공휴일 종료')
        sys.exit()

    print("\n=== 데이터 수집 시작 ===")
    
    # 날짜 설정
    today_yyyymmdd = datetime.today().strftime('%Y%m%d')
    # today_yyyymmdd = '20241024'
    today_dt = datetime.strptime(today_yyyymmdd, '%Y%m%d')
    start_date = (today_dt - timedelta(days=15)).strftime('%Y%m%d')
    today_display = today_dt.strftime('%Y-%m-%d')
    print(f"처리 날짜: {today_display}")

    # 전종목 거래량 상위 TOP 15 추출 및 전송
    print("\n1. 전종목 거래량 TOP 15 처리 시작")
    process_volume_data(today_yyyymmdd, today_display)
    print("전종목 거래량 TOP 15 처리 완료")
    
    # 각 시장별로 처리
    for market in ["KOSPI", "KOSDAQ"]:
        print(f"\n=== {market} 시장 처리 시작 ===")
        
        # 1. 투신, 연기금, 사모 데이터 수집 (detail=True)
        print(f"\n2. {market} 투신/연기금/사모 데이터 수집 시작")
        combined_dfs_1 = []
        for investor_info in INVESTORS[:3]:
            investor_name = investor_info['name']
            print(f"- {investor_name} 데이터 수집 중...")
            top_stocks = get_top_stocks_by_net_buying(market, today_yyyymmdd, today_yyyymmdd, investor_name)
            
            print(f"- {investor_name} 연속매수일 및 EPS 계산 중...")
            for ticker in top_stocks.index:
                # 연속매수일 계산
                consecutive_days = get_stock_trading_value_by_date(
                    ticker, start_date, today_yyyymmdd, investor_name, detail=True
                )
                
                # 데이터가 없는 경우 해당 종목 건너뛰기
                if consecutive_days is None:
                    print(f"Skipping ticker {ticker} due to missing data")
                    continue
                
                top_stocks.at[ticker, '연속매수일'] = consecutive_days
                
                # EPS 정보 가져오기
                fundamental_df = stock.get_market_fundamental(today_yyyymmdd, today_yyyymmdd, ticker)
                if not fundamental_df.empty:
                    eps = fundamental_df.iloc[0]['EPS']
                    top_stocks.at[ticker, 'EPS'] = f"{eps:,.0f}"
                else:
                    top_stocks.at[ticker, 'EPS'] = "N/A"
            
            transformed_df = transform_df(top_stocks)
            combined_dfs_1.append(transformed_df)
            print(f"- {investor_name} 처리 완료")
        
        print(f"\n3. {market} 투신/연기금/사모 이미지 생성 및 전송")
        new_file_path = save_combined_df_as_image(
            combined_dfs_1, 
            f'combined_investors_1_{market.lower()}.png', 
            today_display,
            market
        )
        sendTelegramPhoto(
            new_file_path, 
            f"{today_display} {market} 투신/연기금/사모 순매수대금 TOP 15"
        )
        print(f"{market} 투신/연기금/사모 처리 완료")
        
        # 2. 외국인, 기관합계 데이터 수집 (detail=False)
        print(f"\n4. {market} 외국인/기관 데이터 수집 시작")
        combined_dfs_2 = []
        for investor_info in INVESTORS[3:]:
            investor_name = investor_info['name']
            print(f"- {investor_name} 데이터 수집 중...")
            top_stocks = get_top_stocks_by_net_buying(market, today_yyyymmdd, today_yyyymmdd, investor_name)
            
            print(f"- {investor_name} 연속매수일 및 EPS 계산 중...")
            for ticker in top_stocks.index:
                consecutive_days = get_stock_trading_value_by_date(
                    ticker, start_date, today_yyyymmdd, investor_name, detail=False
                )
                
                # 데이터가 없는 경우 해당 종목 건너뛰기
                if consecutive_days is None:
                    print(f"Skipping ticker {ticker} due to missing data")
                    continue
                
                top_stocks.at[ticker, '연속매수일'] = consecutive_days
                
                # EPS 정보 가져오기
                fundamental_df = stock.get_market_fundamental(today_yyyymmdd, today_yyyymmdd, ticker)
                if not fundamental_df.empty:
                    eps = fundamental_df.iloc[0]['EPS']
                    top_stocks.at[ticker, 'EPS'] = f"{eps:,.0f}"
                else:
                    top_stocks.at[ticker, 'EPS'] = "N/A"
            
            transformed_df = transform_df(top_stocks)
            combined_dfs_2.append(transformed_df)
            print(f"- {investor_name} 처리 완료")
        
        print(f"\n5. {market} 외국인/기관 이미지 생성 및 전송")
        new_file_path = save_combined_df_as_image(
            combined_dfs_2, 
            f'combined_investors_2_{market.lower()}.png', 
            today_display,
            market
        )
        sendTelegramPhoto(
            new_file_path, 
            f"{today_display} {market} 외국인/기관 순매수대금 TOP 15"
        )
        print(f"{market} 외국인/기관 처리 완료")
        
        print(f"\n=== {market} 시장 처리 완료 ===")
    
    print("\n=== 모든 데이터 처리 완료 ===")

if __name__ == "__main__":
    main()
