import pandas as pd
from pykrx import stock
import time
from datetime import datetime
from utils.telegram_util import TelegramUtil
import os
import imgkit

class VolumeReport:
    def __init__(self):
        self.telegram = TelegramUtil()
        self.img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img')
        self.wkhtmltoimage_path = os.getenv('WKHTMLTOIMAGE_PATH')
        
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)

    def save_df_as_image(self, df, title, file_name='top_volume.png'):
        """DataFrame을 이미지로 저장"""
        if df is None or df.empty:
            return None

        file_name, file_extension = os.path.splitext(file_name)
        current_date = datetime.now().strftime('%Y%m%d')
        new_file_path = os.path.join(self.img_dir, f"{file_name}_{current_date}{file_extension}")
        
        # 이전 파일 삭제
        for old_file in os.listdir(self.img_dir):
            if old_file.startswith(file_name) and old_file.endswith(file_extension):
                os.remove(os.path.join(self.img_dir, old_file))
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
            'enable-local-file-access': None
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
            error_message = f"❌ 오류 발생\n\n함수: save_df_as_image\n파일: {file_name}\n오류: {str(e)}"
            self.telegram.send_test_message(error_message)
            print(f"이미지 생성 중 오류 발생: {str(e)}")
            return None

    def get_top_15_stocks_by_volume(self, date):
        """거래량 기준 상위 15개 종목 추출"""
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                ohlcv_data = stock.get_market_ohlcv(date=date, market="ALL")
                if not ohlcv_data.empty and {'거래량'}.issubset(ohlcv_data.columns):
                    ohlcv_data['거래량'] = ohlcv_data['거래량'].astype(int)
                    sorted_data = ohlcv_data.sort_values(by="거래량", ascending=False)
                    return sorted_data.head(15)
            except Exception as e:
                print(f"데이터 조회 시도 {attempt + 1}/{max_attempts} 실패: {str(e)}")
            
            attempt += 1
            if attempt < max_attempts:
                print(f"20초 후 재시도합니다...")
                time.sleep(20)
        
        error_message = f"❌ 오류 발생\n\n함수: get_top_15_stocks_by_volume\n날짜: {date}\n\n5회 재시도 모두 실패"
        self.telegram.send_test_message(error_message)
        return None

    def transform_df(self, df):
        """DataFrame 변환"""
        df['종목명'] = df.index.map(stock.get_market_ticker_name)
        df['거래량'] = df['거래량'].apply(lambda x: f"{x:,}")
        df = df.reset_index(drop=True)
        return df[['종목명', '거래량']]

    def create_report(self, date, today_display):
        """거래량 보고서 생성"""
        print("\n1. 전종목 거래량 TOP 15 처리 시작")
        top_stocks = self.get_top_15_stocks_by_volume(date)
        
        if top_stocks is not None:
            transformed_df = self.transform_df(top_stocks)
            title = f"{today_display} 전종목 거래량 TOP 15"
            self.save_df_as_image(transformed_df, title)
            print("전종목 거래량 TOP 15 처리 완료")
            return transformed_df
        return None 