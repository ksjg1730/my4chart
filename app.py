import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 비교 대시보드", layout="wide")

st.title("📊 주간 단위 수익률 초기화 차트 (월요일 09:00 기준)")

# 2. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물 (2x)',
    'DX-Y.NYB': 'DXY 달러지수 (5x)',
    '233740.KS': 'KODEX 코스닥150레버리지'
}

# 3. 차트 그리기
@st.fragment(run_every=60)
def draw_chart():
    fig = go.Figure()
    cols = st.columns(len(tickers))
    colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96'] 

    all_data_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        # 최근 1개월 데이터 수집
        df = yf.download(symbol, period='1mo', interval='30m', progress=False)
        if df.empty: continue
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.index = df.index.tz_convert('Asia/Seoul')
        all_data_indices.append(df.index)
        
        # --- 주차별 기준가(Base Price) 동적 계산 로직 ---
        # 1. 월요일 09:00 시점들만 추출
        monday_opens = df[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
        
        # 2. 각 데이터 포인트에 대해 해당 시점 '이전'의 가장 가까운 월요일 9시 가격을 기준가로 설정
        def get_weekly_base_price(current_time):
            # 현재 시점보다 이전이거나 같은 월요일 9시 데이터들을 필터링
            past_mondays = monday_opens[monday_opens.index <= current_time]
            if not past_mondays.empty:
                return float(past_mondays['Close'].iloc[-1]) # 가장 최근 월요일 9시 가격
            else:
                return float(df['Close'].iloc[0]) # 데이터 시작점에 월요일이 없으면 첫 가격 사용

        # 3. 모든 행에 대해 기준가 적용 (이 부분은 데이터가 많으면 속도가 느릴 수 있어 벡터화 권장되나 가독성을 위해 명시적 처리)
        # 실제로는 merge_asof 등을 쓰면 빠르지만, 30분봉 한달치이므로 loop로도 충분합니다.
        base_prices = []
        for ts in df.index:
            base_prices.append(get_reference_for_timestamp(ts, monday_opens, df))
        
        df['Base_Price'] = base_prices
        
        # 4. 수익률 및 가중치 계산
        raw_return = ((df['Close'] - df['Base_Price']) / df['Base_Price'] * 100)
        
        if symbol == 'DX-Y.NYB':
            df['Return'] = raw_return * 5
        elif symbol == 'SI=F':
            df['Return'] = raw_return * 2
        else:
            df['Return'] = raw_return
            
        current_return = float(df['Return'].iloc[-1])
        cols[i].metric(label=name, value=f"{current_return:+.2f}%")

        fig.add_trace(go.Scatter(
            x=df.index, y=df['Return'],
            mode='lines', name=name,
            line=dict(width=2, color=colors[i])
        ))

    # 4. 월요일 오전 09:00 수직선 (구분선)
    if all_data_indices:
        start_date = min([idx.min() for idx in all_data_indices])
        end_date = max([idx.max() for idx in all_data_indices])
        curr = start_date.replace(hour=9, minute=0, second=0)
        while curr <= end_date:
            if curr.weekday() == 0:
                fig.add_vline(
                    x=curr.timestamp() * 1000, 
                    line_width=2, 
                    line_dash="solid", 
                    line_color="rgba(200, 0, 0, 0.3)", # 주간 경계선 (붉은색 계열)
                    annotation_text=curr.strftime('%m%d'),
                    annotation_position="top left"
                )
            curr += timedelta(days=1)

    fig.add_hline(y=0, line_color="black", line_width=1, opacity=0.5)
    
    fig.update_layout(
        hovermode="x unified", height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="날짜", tickformat="%m%d\n%H:%M", dtick=86400000.0),
        yaxis=dict(title="주간 수익률 (%)"),
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"갱신: {datetime.now().strftime('%m%d %H:%M:%S')} | 각 주차 월요일 09:00에 수익률이 0%로 리셋됩니다.")

def get_reference_for_timestamp(ts, monday_opens, full_df):
    """특정 시점 ts에 대해 적용할 기준 월요일 가격을 반환"""
    past_mondays = monday_opens[monday_opens.index <= ts]
    if not past_mondays.empty:
        return float(past_mondays['Close'].iloc[-1])
    return float(full_df['Close'].iloc[0])

draw_chart()
