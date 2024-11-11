import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pykrx import stock
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
from utils.telegram_util import TelegramUtil
import os
import time
import imgkit

class RSReport:
    def __init__(self):
        self.telegram = TelegramUtil()
        self.img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img')
        self.wkhtmltoimage_path = os.getenv('WKHTMLTOIMAGE_PATH')
        self.kospi_benchmark = '1001'  # KOSPI 지수
        self.kosdaq_benchmark = '2001'  # KOSDAQ 지수
        self.update_market_lists()

    def update_market_lists(self):
        """KOSPI와 KOSDAQ 종목 리스트를 업데이트합니다."""
        self.kospi_tickers = set(stock.get_market_ticker_list(market="KOSPI"))
        self.kosdaq_tickers = set(stock.get_market_ticker_list(market="KOSDAQ"))

    def _get_market_type(self, ticker):
        """주어진 티커의 시장 유형(KOSPI/KOSDAQ)을 판단합니다."""
        if ticker in self.kospi_tickers:
            return 'KOSPI', self.kospi_benchmark
        elif ticker in self.kosdaq_tickers:
            return 'KOSDAQ', self.kosdaq_benchmark
        else:
            print(f"경고: {ticker}에 대한 시장을 찾을 수 없습니다. KOSPI를 기본값으로 사용합니다.")
            return 'UNKNOWN', self.kospi_benchmark

    def _get_data(self, ticker, start_date, end_date):
        """주어진 기간 동안의 종목 가격 데이터를 가져옵니다."""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
                if not df.empty:
                    return df['종가']
            except Exception as e:
                print(f"데이터 조회 시도 {attempt + 1}/{max_attempts} 실패: {str(e)}")
            
            attempt += 1
            if attempt < max_attempts:
                print(f"20초 후 재시도합니다...")
                time.sleep(20)
        
        error_message = f"❌ 오류 발생\n\n함수: _get_data\n종목: {ticker}\n기간: {start_date}~{end_date}\n\n5회 재시도 모두 실패"
        self.telegram.send_test_message(error_message)
        return None

    def _get_index_data(self, index_code, start_date, end_date):
        """주어진 기간 동안의 지수 데이터를 가져옵니다."""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                df = stock.get_index_ohlcv_by_date(start_date, end_date, index_code)
                if not df.empty:
                    return df['종가']
            except Exception as e:
                print(f"데이터 조회 시도 {attempt + 1}/{max_attempts} 실패: {str(e)}")
            
            attempt += 1
            if attempt < max_attempts:
                print(f"20초 후 재시도합니다...")
                time.sleep(20)
        
        error_message = f"❌ 오류 발생\n\n함수: _get_index_data\n지수: {index_code}\n기간: {start_date}~{end_date}\n\n5회 재시도 모두 실패"
        self.telegram.send_test_message(error_message)
        return None

    def get_stock_name(self, ticker):
        """주식 코드에 해당하는 종목명을 반환합니다."""
        try:
            return stock.get_market_ticker_name(ticker)
        except:
            return "알 수 없음"

    def _calculate_single_rs(self, stock_data, benchmark_data, period):
        """단일 기간에 대한 RS 값을 계산합니다."""
        common_dates = stock_data.index.intersection(benchmark_data.index)
        stock_data = stock_data[common_dates][-period:]
        benchmark_data = benchmark_data[common_dates][-period:]

        # 수익률 계산
        stock_returns = (stock_data.pct_change() + 1).cumprod() - 1
        benchmark_returns = (benchmark_data.pct_change() + 1).cumprod() - 1

        # 최종 누적 수익률로 RS 계산
        rs = (1 + stock_returns.iloc[-1]) / (1 + benchmark_returns.iloc[-1])
        return rs

    def normalize_rs(self, rs_value, base=2, scale=50):
        """RS 값을 0-100 스케일로 정규화합니다."""
        log_rs = np.log(rs_value) / np.log(base)
        normalized_score = 50 + (log_rs * scale)
        return max(0, min(100, normalized_score))  # 0-100 범위로 클리핑

    def calculate_rs(self, ticker, periods=[20, 60, 120]):
        """주어진 기간들에 대해 RS 값을 계산합니다."""
        end_date = datetime.today().strftime('%Y%m%d')
        max_period = max(periods)
        start_date = (datetime.today() - timedelta(days=max_period * 2)).strftime('%Y%m%d')

        market_type, benchmark_ticker = self._get_market_type(ticker)
        
        stock_data = self._get_data(ticker, start_date, end_date)
        benchmark_data = self._get_index_data(benchmark_ticker, start_date, end_date)

        if stock_data is None or benchmark_data is None:
            return None, market_type

        rs_values = {}
        for period in periods:
            rs = self._calculate_single_rs(stock_data, benchmark_data, period)
            rs_values[period] = rs

        return rs_values, market_type

    def calculate_rs_with_score(self, ticker, periods=[20, 60, 120]):
        """RS 값을 계산하고 정규화된 점수도 함께 반환합니다."""
        rs_values, market_type = self.calculate_rs(ticker, periods)
        if rs_values:
            rs_scores = {period: self.normalize_rs(rs) for period, rs in rs_values.items()}
            return rs_scores, market_type
        return None, market_type

    def get_market_rs_ranking(self, market, period=20, top_n=15):
        """특정 시장의 RS 랭킹을 계산합니다."""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                print(f"\n{market} 시장 {period}일 RS 점수 계산 시작...")
                
                # 해당 시장의 모든 종목 코드 가져오기
                tickers = stock.get_market_ticker_list(market=market)
                if not tickers:
                    raise Exception("종목 리스트를 가져오는데 실패했습니다.")
                
                results = []
                for i, ticker in enumerate(tickers, 1):
                    try:
                        if i % 50 == 0:
                            print(f"진행중... {i}/{len(tickers)} 종목 처리완료")
                        
                        rs_scores, _ = self.calculate_rs_with_score(ticker, [period])
                        if rs_scores:
                            stock_name = self.get_stock_name(ticker)
                            results.append({
                                '종목코드': ticker,
                                '종목명': stock_name,
                                'RS점수': rs_scores[period]
                            })
                        
                        time.sleep(0.1)  # API 호출 제한 방지
                        
                    except Exception as e:
                        print(f"종목 {ticker} 처리 중 오류 발생: {str(e)}")
                        continue
                
                df = pd.DataFrame(results)
                if not df.empty:
                    df = df.sort_values('RS점수', ascending=False)
                    df['RS점수'] = df['RS점수'].round(2)
                    return df.head(top_n)
                
                return pd.DataFrame()
                
            except Exception as e:
                print(f"데이터 조회 시도 {attempt + 1}/{max_attempts} 실패: {str(e)}")
                
            attempt += 1
            if attempt < max_attempts:
                print(f"20초 후 재시도합니다...")
                time.sleep(20)
        
        error_message = f"❌ 오류 발생\n\n함수: get_market_rs_ranking\n시장: {market}\n기간: {period}\n\n5회 재시도 모두 실패"
        self.telegram.send_test_message(error_message)
        return None

    def save_rs_ranking_as_image(self, df, market, period, today_display):
        """RS 랭킹 데이터를 이미지로 저장"""
        if df is None or df.empty:
            return None

        file_name = f'rs_ranking_{market.lower()}_{period}'
        current_date = datetime.now().strftime('%Y%m%d')
        new_file_path = os.path.join(self.img_dir, f"{file_name}_{current_date}.png")
        
        # 이전 파일 삭제
        for old_file in os.listdir(self.img_dir):
            if old_file.startswith(file_name) and old_file.endswith('.png'):
                os.remove(os.path.join(self.img_dir, old_file))
                print(f"기존 파일 삭제: {old_file}")

        title = f"{today_display} {market} {period}일 RS 랭킹 TOP 15"

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
            </style>
        </head>
        <body>
            <div class="caption">{title}</div>
            {df.to_html(index=False, classes='styled-table')}
            <div class="source">※ 출처 : MQ(Money Quotient)</div>
        </body>
        </html>
        '''

        options = {
            'format': 'png',
            'encoding': "UTF-8",
            'quality': 100,
            'width': 600,
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
            self.telegram.send_photo(new_file_path, title)
            
            return new_file_path
            
        except Exception as e:
            error_message = f"❌ 오류 발생\n\n함수: save_rs_ranking_as_image\n파일: {file_name}\n오류: {str(e)}"
            self.telegram.send_test_message(error_message)
            print(f"이미지 생성 중 오류 발생: {str(e)}")
            return None

    def create_report(self, date_str, period=20):
        """RS 보고서를 생성합니다."""
        markets = ["KOSPI", "KOSDAQ"]
        results = {}
        today_display = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        
        for market in markets:
            print(f"\n=== {market} 시장 RS 데이터 처리 시작 ===")
            results[market] = {}
            
            print(f"{market} {period}일 RS 랭킹 계산 중...")
            ranking_df = self.get_market_rs_ranking(market, period)
            
            if ranking_df is not None and not ranking_df.empty:
                results[market][period] = ranking_df
                transformed_df = self.transform_df(ranking_df)
                if transformed_df is not None:
                    self.save_rs_ranking_as_image(transformed_df, market, period, today_display)
                print(f"{market} {period}일 RS 랭킹 계산 완료")
            
            time.sleep(1)  # API 호출 제한 방지
            print(f"=== {market} 시장 RS 데이터 처리 완료 ===")
        
        return results

    def transform_df(self, df):
        """DataFrame 형식을 변환합니다."""
        if df is None or df.empty:
            return None
            
        df = df.copy()
        df = df.reset_index(drop=True)
        return df[['종목명', 'RS점수']]