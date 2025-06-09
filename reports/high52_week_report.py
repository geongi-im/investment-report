import pandas as pd
import time
from datetime import datetime
import os
import imgkit
import re
import requests
import json
import math

class High52WeekReport:
    def __init__(self):
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img')
        self.wkhtmltoimage_path = os.getenv('WKHTMLTOIMAGE_PATH')

    def fetch_high_52w(self, page=1, page_size=100):
        url = f"https://m.stock.naver.com/api/stocks/high52week/all"
        params = {
            "page": page,
            "pageSize": page_size,
        }
        response = requests.get(url, params=params)
        data = response.json()
        return data

    def get_all_52w_high_stocks(self):
        """데이터 수집"""
        print(f"\n=== 52주 최고가 데이터 네이버 크롤링 시작 ===")

        # 1. 첫 페이지 호출해서 전체 페이지 수 계산
        first_page = self.fetch_high_52w(page=1, page_size=100)
        total_count = first_page['totalCount']
        page_size = 100
        total_pages = math.ceil(total_count / page_size)

        print(f"전체 종목 수: {total_count} / 총 페이지 수: {total_pages}")
        all_stocks = []

        # 2. 모든 페이지 순회해서 종목 수집
        for page in range(1, total_pages + 1):
            data = self.fetch_high_52w(page=page, page_size=page_size)
            stocks = data['stocks']

            filtered_stocks = [s for s in stocks if s.get("stockEndType") == "stock"] #stock 종목만 추출
            all_stocks.extend(filtered_stocks)
            time.sleep(0.2)  # 과도한 요청 방지 (200ms 간격)

        print(f"수집된 종목 수: {len(all_stocks)}")
        return all_stocks[:20]
    
    def process_html(self, stocks):
        # 기본 HTML 구조 생성
        html_pages = []
        items_per_page = 10
        total_pages = (len(stocks) + items_per_page - 1) // items_per_page

        for page in range(total_pages):
            start_idx = page * items_per_page
            end_idx = min((page + 1) * items_per_page, len(stocks))
            current_page_data = stocks[start_idx:end_idx]

            processed_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
                <title>{self.today} 52주 신고가 종목 리포트</title>
                <style>
                    body {{
                        font-family: 'Noto Sans KR', sans-serif;
                        margin: 20px;
                        padding: 0;
                        color: #333;
                        font-size: 14px;
                    }}
                    h1 {{
                        text-align: center;
                        font-size: 28px;
                        margin-bottom: 25px;
                        font-weight: bold;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 15px;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 12px;
                        text-align: center;
                        vertical-align: middle;
                        font-size: 14px;
                        line-height: 1.4;
                    }}
                    th {{
                        background-color: #333;
                        color: white;
                        font-weight: bold;
                        font-size: 15px;
                        padding: 15px;
                    }}
                    tr:nth-child(odd) {{
                        background-color: #f9f9f9;
                    }}
                    .source {{
                        text-align: right;
                        color: #888;
                        font-size: 13px;
                        margin-top: 8px;
                    }}
                    .source-main {{
                        font-size: 13px;
                        margin-bottom: 3px;
                    }}
                    .stock-name {{
                        text-align: center;
                        font-weight: bold;
                        white-space: pre-line;
                        font-size: 15px;
                    }}
                    .price {{
                        color: #e53935;
                        text-align: center;
                        font-size: 14px;
                        white-space: pre-line;
                    }}
                    .content {{
                        text-align: center;
                        font-weight: bold;
                        font-size: 14px;
                    }}
                </style>
            </head>
            <body>
                <h1>{self.today} 52주 신고가 종목 리포트({page + 1}/{total_pages})</h1>
                <table>
                    <tr>
                        <th>종목명</th>
                        <th>현재가</th>
                        <th>시가총액</th>
                        <th>거래대금</th>
                    </tr>
            """

            # 현재 페이지의 종목 데이터 추가
            for stock in current_page_data:
                processed_html += f"""
                    <tr>
                        <td class="stock-name">{stock['stockName']}\n({stock['itemCode']})</td>
                        <td class="price">{stock['closePrice']}원\n(+{stock['fluctuationsRatio']}%)</td>
                        <td class="content">{stock['marketValueHangeul']}</td>
                        <td class="content">{stock['accumulatedTradingValueKrwHangeul']}</td>
                    </tr>
                """

            # HTML 마무리
            processed_html += """
                </table>
                <div class="source">
                    <div class="source-main">※ 출처 : MQ(Money Quotient)</div>
                </div>
            </body>
            </html>
            """
            html_pages.append(processed_html)

        return html_pages

    def save_images_from_html(self, html_pages):
        options = {
            'format': 'png',
            'encoding': "UTF-8",
            'quality': 75,  # 품질을 75%로 낮춰서 파일 크기 감소
            'width': 768,
            'enable-local-file-access': None,
            'minimum-font-size': 12,
            'quiet': None   # 로그 레벨 조정
        }

        if not self.wkhtmltoimage_path:
            message = "오류 발생\n\nWKHTMLTOIMAGE_PATH 환경변수가 설정되지 않았습니다."
            print(message)

            
        # 이전 파일 삭제
        for old_file in os.listdir(self.img_dir):
            if old_file.startswith('high52_week_') and old_file.endswith('.png'):
                os.remove(os.path.join(self.img_dir, old_file))
                print(f"기존 파일 삭제: {old_file}")

        config = imgkit.config(wkhtmltoimage=self.wkhtmltoimage_path)
        
        # HTML을 페이지별로 생성하고 이미지 저장
        image_paths = []
        for page_num, page_html in enumerate(html_pages, 0):
            file_path = os.path.join(self.img_dir, f"high52_week_{self.today}_report_{page_num}p.png")
            imgkit.from_string(page_html, file_path, options=options, config=config)
            print(f"새 파일 저장: {file_path}")
            image_paths.append(file_path)

        return image_paths
    
    def create_report(self):
        stocks = self.get_all_52w_high_stocks()
        html_pages = self.process_html(stocks)
        image_paths = self.save_images_from_html(html_pages)
        return image_paths

if __name__ == "__main__":
    high52_week_report = High52WeekReport()
    stocks = high52_week_report.get_all_52w_high_stocks()
    html_pages = high52_week_report.process_html(stocks)
    image_paths = high52_week_report.save_images_from_html(html_pages)