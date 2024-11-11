import pandas as pd
from pykrx import stock
import time
from datetime import datetime, timedelta
from utils.telegram_util import TelegramUtil
import os
import imgkit
import re

class InvestorReport:
    def __init__(self):
        self.telegram = TelegramUtil()
        self.img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img')
        self.wkhtmltoimage_path = os.getenv('WKHTMLTOIMAGE_PATH')
        
        # 투자자 그룹 정의
        self.investors = [
            {'name': '투신', 'file_prefix': 'top_investment_trust'},
            {'name': '연기금', 'file_prefix': 'top_pension_fund'},
            {'name': '사모', 'file_prefix': 'top_private_fund'},
            {'name': '외국인', 'file_prefix': 'top_foreign_fund'},
            {'name': '기관합계', 'file_prefix': 'top_institution_fund'}
        ]

    def save_combined_df_as_image(self, dfs, file_name, today_display, market_type):
        """여러 DataFrame을 하나의 이미지로 저장"""
        if not file_name.endswith('.png'):
            file_name = file_name + '.png'
            
        file_name, file_extension = os.path.splitext(file_name)
        current_date = datetime.now().strftime('%Y%m%d')
        new_file_path = os.path.join(self.img_dir, f"{file_name}_{current_date}{file_extension}")
        
        # 이전 파일 삭제
        for old_file in os.listdir(self.img_dir):
            if old_file.startswith(file_name) and old_file.endswith(file_extension):
                os.remove(os.path.join(self.img_dir, old_file))
                print(f"기존 파일 삭제: {old_file}")

        # DataFrame 데이터 준비
        columns = []
        for i, df in enumerate(dfs):
            investor_name = self.investors[i if len(dfs) == 3 else i+3]['name']
            columns.extend([
                (investor_name, '종목명'),
                (investor_name, '순매수대금')
            ])
        
        columns = pd.MultiIndex.from_tuples(columns)
        
        combined_data = []
        for i in range(len(dfs[0])):
            row = []
            for df in dfs:
                row.extend([df['종목명'].iloc[i], df['순매수거래대금'].iloc[i]])
            combined_data.append(row)
        
        df = pd.DataFrame(combined_data, columns=columns)

        # 캡션 설정
        if len(dfs) == 3:
            caption = f"{today_display} {market_type} 투신/연기금/사모 순매수대금 TOP 15"
        else:
            caption = f"{today_display} {market_type} 외국인/기관 순매수대금 TOP 15"

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
            <div class="caption">{caption}</div>
        '''

        # DataFrame을 HTML로 변환
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

        options = {
            'format': 'png',
            'encoding': "UTF-8",
            'quality': 100,
            'width': 1200 if len(dfs) == 3 else 800,
            'enable-local-file-access': None,
            'minimum-font-size': 12
        }

        try:
            if not self.wkhtmltoimage_path:
                error_message = "❌ 오류 발생\n\nWKHTMLTOIMAGE_PATH 환경변수가 설정되지 않았습니다."
                self.telegram.send_test_message(error_message)
                raise ValueError("WKHTMLTOIMAGE_PATH 환경변수가 필요합니다.")
                
            config = imgkit.config(wkhtmltoimage=self.wkhtmltoimage_path)
            imgkit.from_string(html_str, new_file_path, options=options, config=config)
            print(f"새 파일 저장: {new_file_path}")
            
            # 텔레그램으로 이미지 전송
            self.telegram.send_photo(new_file_path, caption)
            
            return new_file_path
            
        except Exception as e:
            error_message = f"❌ 오류 발생\n\n함수: save_combined_df_as_image\n파일: {file_name}\n오류: {str(e)}"
            self.telegram.send_test_message(error_message)
            print(f"이미지 생성 중 오류 발생: {str(e)}")
            return None

    def get_top_stocks_by_net_buying(self, market, start_date, end_date, investor, top_n=15):
        """투자자별 순매수 상위 종목 추출"""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                df = stock.get_market_net_purchases_of_equities(start_date, end_date, market, investor)
                if not df.empty:
                    top_stocks = df.nlargest(top_n, '순매수거래대금')
                    return top_stocks[['종목명', '순매수거래대금']]
            except Exception as e:
                print(f"데이터 조회 시도 {attempt + 1}/{max_attempts} 실패: {str(e)}")
            
            attempt += 1
            if attempt < max_attempts:
                print(f"20초 후 재시도합니다...")
                time.sleep(20)
        
        error_message = f"❌ 오류 발생\n\n함수: get_top_stocks_by_net_buying\n시장: {market}\n투자자: {investor}\n기간: {start_date}~{end_date}"
        self.telegram.send_test_message(error_message)
        return None

    def get_stock_trading_value_by_date(self, ticker, start_date, end_date, investor, detail=True):
        """종목별 투자자 거래 데이터 조회"""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                df = stock.get_market_trading_value_by_date(start_date, end_date, ticker, detail=detail)
                if not df.empty:
                    df_sorted = df.sort_index(ascending=False)
                    investor_key = '외국인합계' if investor == '외국인' else investor
                    consecutive_positive_days = self._check_consecutive_positive_days(df_sorted[investor_key])
                    return consecutive_positive_days
            except Exception as e:
                print(f"데이터 조회 시도 {attempt + 1}/{max_attempts} 실패: {str(e)}")
            
            attempt += 1
            if attempt < max_attempts:
                print(f"20초 후 재시도합니다...")
                time.sleep(20)
        
        error_message = f"❌ 오류 발생\n\n함수: get_stock_trading_value_by_date\n종목: {ticker}\n투자자: {investor}"
        self.telegram.send_test_message(error_message)
        return None

    def _check_consecutive_positive_days(self, series):
        """연속 순매수일 계산"""
        max_consecutive_days = 0
        current_consecutive_days = 0

        for value in series:
            if value > 0:
                current_consecutive_days += 1
                if current_consecutive_days > max_consecutive_days:
                    max_consecutive_days = current_consecutive_days
            else:
                break

        return max_consecutive_days

    def transform_df(self, df):
        """DataFrame 변환"""
        df = df.reset_index(drop=True)
        df['종목명'] = df.apply(lambda x: x['종목명'] + f"({int(x['연속매수일'])})" if x['연속매수일'] > 1 else x['종목명'], axis=1)
        df['순매수거래대금'] = (df['순매수거래대금'] / 100000000).round(2).map('{:,}'.format)
        return df[['종목명', '순매수거래대금']]

    def create_report(self, date, start_date):
        """투자자별 보고서 생성"""
        markets = ["KOSPI", "KOSDAQ"]
        
        for market in markets:
            print(f"\n=== {market} 시장 투자자 데이터 처리 시작 ===")
            investor_groups = [
                self.investors[:3],  # 투신/연기금/사모
                self.investors[3:]   # 외국인/기관
            ]
            
            for group_index, investor_group in enumerate(investor_groups, 1):
                combined_dfs = []
                for investor_info in investor_group:
                    investor_name = investor_info['name']
                    print(f"- {investor_name} 데이터 수집 중...")
                    
                    top_stocks = self.get_top_stocks_by_net_buying(
                        market, date, date, investor_name
                    )
                    
                    if top_stocks is not None:
                        for ticker in top_stocks.index:
                            consecutive_days = self.get_stock_trading_value_by_date(
                                ticker, start_date, date, investor_name,
                                detail=(group_index == 1)
                            )
                            
                            if consecutive_days is not None:
                                top_stocks.at[ticker, '연속매수일'] = consecutive_days
                        
                        transformed_df = self.transform_df(top_stocks)
                        combined_dfs.append(transformed_df)
                        print(f"- {investor_name} 처리 완료")
                
                if combined_dfs:
                    today_display = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')
                    file_name = f'combined_investors_{group_index}_{market.lower()}.png'
                    self.save_combined_df_as_image(combined_dfs, file_name, today_display, market)
            
            print(f"=== {market} 시장 투자자 데이터 처리 완료 ===")