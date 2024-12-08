import OpenDartReader
import pandas as pd
from datetime import datetime
import imgkit
import os
from pykrx import stock
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class OperationProfitReport:
    def __init__(self):
        self.quarter_codes = {
            1: '11013',  # 1분기
            2: '11012',  # 반기
            3: '11014',  # 3분기
            4: '11011'   # 사업보고서
        }
        self.min_operating_profit_margin = 30  # 최소 평균 영업이익률 (%)
        self.img_dir = 'img'
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)
        
        # API 초기화
        self.api_key = os.getenv('DART_API_KEY')
        self.dart = OpenDartReader(self.api_key)

    def get_stock_market_list(self):
        """
        pykrx를 사용하여 코스피, 코스닥 종목 리스트를 가져옵니다.
        """
        today = datetime.now().strftime('%Y%m%d')
        
        try:
            kospi_fundamental = stock.get_market_fundamental_by_ticker(today, market="KOSPI", alternative=True)
            kosdaq_fundamental = stock.get_market_fundamental_by_ticker(today, market="KOSDAQ", alternative=True)
            
            kospi_list = [
                {'code': ticker, 'name': stock.get_market_ticker_name(ticker)}
                for ticker in kospi_fundamental.index
                if kospi_fundamental.loc[ticker, 'PER'] > 0
            ]
            
            kosdaq_list = [
                {'code': ticker, 'name': stock.get_market_ticker_name(ticker)}
                for ticker in kosdaq_fundamental.index
                if kosdaq_fundamental.loc[ticker, 'PER'] > 0
            ]
            
            print(f"KOSPI 종목 수: {len(kospi_list)}")
            print(f"KOSDAQ 종목 수: {len(kosdaq_list)}")
            
            return kospi_list, kosdaq_list
            
        except Exception as e:
            print(f"종목 리스트 가져오기 실패: {e}")
            return None, None

    def get_revenue(self, data, quarter, prev_quarter_data=None):
        """매출액을 조회합니다."""
        revenue_data = data[data['account_nm'] == '매출액']
        
        if not revenue_data.empty:
            if quarter in [1, 3]:  # 1분기, 3분기는 당기금액 사용
                amount = revenue_data['thstrm_amount'].iloc[0].replace(',', '')
            elif quarter == 2:  # 2분기는 당기누적금액 - 1분기 당기금액
                current_amount = revenue_data['thstrm_add_amount'].iloc[0].replace(',', '')
                if prev_quarter_data is not None:
                    prev_revenue = prev_quarter_data[prev_quarter_data['account_nm'] == '매출액']
                    if not prev_revenue.empty:
                        prev_amount = prev_revenue['thstrm_amount'].iloc[0].replace(',', '')
                        amount = str(int(current_amount) - int(prev_amount))
                else:
                    amount = current_amount
            elif quarter == 4:  # 4분기는 당기금액 - 3분기 누적금액
                current_amount = revenue_data['thstrm_amount'].iloc[0].replace(',', '')
                if prev_quarter_data is not None:
                    prev_revenue = prev_quarter_data[prev_quarter_data['account_nm'] == '매출액']
                    if not prev_revenue.empty:
                        prev_amount = prev_revenue['thstrm_add_amount'].iloc[0].replace(',', '')
                        amount = str(int(current_amount) - int(prev_amount))
                else:
                    amount = current_amount
            
            return int(amount)
        
        return None  # 매출액이 없는 경우 None 반환

    def get_operating_profit(self, data, quarter, prev_quarter_data=None):
        """영업이익을 조회합니다."""
        op_data = data[data['account_nm'] == '영업이익']
        
        if op_data.empty:
            op_data = data[data['account_nm'] == '영업이익(손실)']
        
        if not op_data.empty:
            if quarter in [1, 3]:  # 1분기, 3분기는 당기금액 사용
                amount = op_data['thstrm_amount'].iloc[0].replace(',', '')
            elif quarter == 2:  # 2분기는 당기누적금액 - 1분기 당기금액
                current_amount = op_data['thstrm_add_amount'].iloc[0].replace(',', '')
                if prev_quarter_data is not None:
                    prev_op = prev_quarter_data[prev_quarter_data['account_nm'].isin(['영업이익', '영업이익(손실)'])]
                    if not prev_op.empty:
                        prev_amount = prev_op['thstrm_amount'].iloc[0].replace(',', '')
                        amount = str(int(current_amount) - int(prev_amount))
                else:
                    amount = current_amount
            elif quarter == 4:  # 4분기는 당기금액 - 3분기 누적금액
                current_amount = op_data['thstrm_amount'].iloc[0].replace(',', '')
                if prev_quarter_data is not None:
                    prev_op = prev_quarter_data[prev_quarter_data['account_nm'].isin(['영업이익', '영업이익(손실)'])]
                    if not prev_op.empty:
                        prev_amount = prev_op['thstrm_add_amount'].iloc[0].replace(',', '')
                        amount = str(int(current_amount) - int(prev_amount))
                else:
                    amount = current_amount
                
            return int(amount)
        
        return None  # 영업이익이 없는 경우 None 반환

    def get_company_metrics(self, company_code, company_name):
        """기업의 재무 지표를 계산합니다."""
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # 공시 지연을 고려한 분기 설정
        if current_month < 3:  # 1-2월
            base_year = current_year - 1
            base_quarter = 3  # 3분기까지의 데이터만 확실
        elif current_month < 5:  # 3-4월
            base_year = current_year - 1
            base_quarter = 4  # 4분기 데이터 사용 가능
        elif current_month < 8:  # 5-7월
            base_year = current_year
            base_quarter = 1  # 1분기 데이터 사용 가능
        elif current_month < 11:  # 8-10월
            base_year = current_year
            base_quarter = 2  # 2분기 데이터 사용 가능
        else:  # 11-12월
            base_year = current_year
            base_quarter = 3  # 3분기 데이터 사용 가능

        try:
            quarters_data = []
            year = base_year
            quarter = base_quarter
            prev_quarter_data = None
            
            for _ in range(4):  # 4개 분기 데이터 수집
                try:
                    quarter_data = self.dart.finstate(company_code, year, reprt_code=self.quarter_codes[quarter])
                    
                    if quarter_data is not None and not quarter_data.empty and not isinstance(quarter_data, dict):
                        cfs_data = quarter_data[quarter_data['fs_div'] == 'CFS']
                        
                        if not cfs_data.empty:
                            # 이전 분기 데이터가 필요한 경우 가져오기
                            if quarter in [2, 4]:
                                prev_quarter = quarter - 1
                                prev_year = year
                                if prev_quarter < 1:
                                    prev_quarter = 4
                                    prev_year -= 1
                                prev_data = self.dart.finstate(company_code, prev_year, reprt_code=self.quarter_codes[prev_quarter])
                                if prev_data is not None and not prev_data.empty:
                                    prev_quarter_data = prev_data[prev_data['fs_div'] == 'CFS']
                        
                        revenue = self.get_revenue(cfs_data, quarter, prev_quarter_data)
                        op = self.get_operating_profit(cfs_data, quarter, prev_quarter_data)
                        
                        if revenue and op and revenue > 0:
                            opm = (op / revenue) * 100
                            quarters_data.append({
                                'year': year,
                                'quarter': quarter,
                                'opm': opm
                            })
                
                    # 이전 분기로 이동
                    quarter -= 1
                    if quarter < 1:
                        quarter = 4
                        year -= 1
                    
                except Exception as e:
                    print(f"Error processing {company_name} for {year} Q{quarter}: {e}")
                    continue
            
            if len(quarters_data) == 4:  # 4개 분기 데이터가 모두 있는 경우만 처리
                avg_opm = sum(q['opm'] for q in quarters_data) / 4
                return {
                    'name': company_name,
                    'code': company_code,
                    'quarters_data': quarters_data,
                    'avg_opm': avg_opm
                }
                                
        except Exception as e:
            print(f"\n{company_name}({company_code}) 처리 중 오류 발생: {str(e)}")
        
        return None

    def create_comparison_html(self, companies_data, market_type):
        """기업 비교 데이터를 HTML 형식으로 변환합니다."""
        # 첫 번째 데이터에서 가장 최근 분기 정보 가져오기
        current_quarter_info = ""
        quarters_info = []
        if companies_data and len(companies_data) > 0:
            first_data = companies_data[0]
            for q_data in first_data['quarters_data']:
                quarters_info.append(f"{q_data['year']}.{q_data['quarter']}Q")
            
            # 가장 최근 분기 정보 (quarters_data[0]이 가장 최근)
            latest_quarter = first_data['quarters_data'][0]
            current_quarter_info = f"{latest_quarter['year']}년 {latest_quarter['quarter']}분기"
        
        html = f"""
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
                .company-name {{
                    text-align: left;
                }}
                .change-rate {{
                    font-size: 12px;
                    margin-left: 5px;
                }}
                .positive {{
                    color: #d32f2f;
                }}
                .negative {{
                    color: #1976d2;
                }}
                .avg-column {{
                    background-color: #ffebee !important;  /* 연한 빨간색 배경 */
                    font-weight: 700 !important;  /* 글자 굵게 */
                    color: #d32f2f !important;  /* 빨간색 글자 */
                }}
                
                /* hover 시에도 배경색 유지 */
                tr:hover td.avg-column {{
                    background-color: #ffcdd2 !important;  /* hover 시 약간 더 진한 빨간색 */
                }}
            </style>
        </head>
        <body>
            <div class="caption">{current_quarter_info} {market_type} 영업이익률 상위 종목</div>
            <table>
                <tr>
                    <th>No</th>
                    <th>종목명</th>
                    <th style="background-color: #d32f2f; font-weight: 700;">평균 영업이익</th>
                    <th>{quarters_info[0]}</th>
                    <th>{quarters_info[1]}</th>
                    <th>{quarters_info[2]}</th>
                    <th>{quarters_info[3]}</th>
                </tr>
        """
        
        for idx, data in enumerate(companies_data, 1):
            if data:
                # 각 분기별 증감률 계산 (현재 분기 - 이전 분기)
                changes = []
                for i in range(len(data['quarters_data']) - 1):  # 0,1,2 인덱스에 대해
                    current_opm = data['quarters_data'][i]['opm']
                    prev_opm = data['quarters_data'][i + 1]['opm']
                    change = current_opm - prev_opm
                    change_class = 'positive' if change >= 0 else 'negative'
                    if change >= 0:
                        change_html = f'<span class="change-rate {change_class}"><br/>(+{change:.2f}%)'
                    else:
                        change_html = f'<span class="change-rate {change_class}"><br/>({change:.2f}%)'

                    changes.append(change_html)
                changes.append('')  # 마지막 분기는 증감률 표시 안함

                html += f"""
                    <tr>
                        <td>{idx}</td>
                        <td class="company-name">{data['name']}({data['code']})</td>
                        <td class="avg-column">{data['avg_opm']:.2f}%</td>
                        <td>{data['quarters_data'][0]['opm']:.2f}%{changes[0]}</span></td>
                        <td>{data['quarters_data'][1]['opm']:.2f}%{changes[1]}</span></td>
                        <td>{data['quarters_data'][2]['opm']:.2f}%{changes[2]}</span></td>
                        <td>{data['quarters_data'][3]['opm']:.2f}%{changes[3]}</td>
                    </tr>
                """
        
        html += """
            </table>
            <div class="source">※ 출처 : MQ(Money Quotient)</div>
        </body>
        </html>
        """
        
        return html

    def generate_image(self, html_content, output_path):
        """HTML을 이미지로 변환합니다."""
        wkhtmltoimage_path = os.getenv('WKHTMLTOIMAGE_PATH')
        config = imgkit.config(wkhtmltoimage=wkhtmltoimage_path)
        options = {
            'width': 800,
            'enable-local-file-access': None,
            'encoding': 'UTF-8',
            'custom-header': [
                ('Content-Type', 'text/html; charset=UTF-8'),
            ]
        }

        try:
            imgkit.from_string(html_content, output_path, options=options, config=config)
            print(f"이미지가 {output_path}로 저장되었습니다.")
        except Exception as e:
            print(f"이미지 변환 중 오류 발생: {e}")

    def process_market_data(self, market_list, market_type):
        """특정 시장(코스피/코스닥)의 데이터를 처리합니다."""
        if not market_list:
            print(f"{market_type} 종목 리스트를 가져오는데 실패했습니다.")
            return
            
        total_companies = len(market_list)
        companies_data = []
        success_count = 0
        error_count = 0
        high_opm_count = 0
        
        for idx, company in enumerate(market_list, 1):
            print(f"[{idx}/{total_companies}] {company['name']} 조회 중... (성공: {success_count}, 실패: {error_count})")
            
            data = self.get_company_metrics(company['code'], company['name'])
            if data:
                success_count += 1
                if data['avg_opm'] >= self.min_operating_profit_margin:
                    companies_data.append(data)
                    high_opm_count += 1
            else:
                error_count += 1
        
        print(f"\n{market_type} 데이터 조회 완료!")
        print(f"전체 종목 수: {total_companies}")
        print(f"성공: {success_count}, 실패: {error_count}")
        print(f"영업이익률 {self.min_operating_profit_margin}% 이상 기업 수: {high_opm_count}개")

        companies_data.sort(key=lambda x: x['avg_opm'], reverse=True)

        if companies_data:
            html_content = self.create_comparison_html(companies_data, market_type)
            today = datetime.now().strftime('%Y%m%d')
            output_path = os.path.join(self.img_dir, f"opm_{market_type.lower()}_{today}.jpg")
            self.generate_image(html_content, output_path)

    def run(self):
        """보고서 생성을 실행합니다."""
        kospi_list, kosdaq_list = self.get_stock_market_list()
        self.process_market_data(kospi_list, "KOSPI")
        self.process_market_data(kosdaq_list, "KOSDAQ")

# 메인 실행 코드는 그대로 유지
def main():
    report = OperationProfitReport()
    report.run()

if __name__ == "__main__":
    main()


