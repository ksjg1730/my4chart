import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="주간 수익률 대시보드", layout="wide")

st.title("📊 자산별 주간 수익률 분석 (월요일 09:00 리셋)")

# 2. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물 (2x)',
    'DX-Y.NYB': 'DXY 달러지수 (5x)',
    '233740.KS': 'KODEX 코스닥150레버리지'
}

@st.cache_data(ttl=600)
def load_data(symbol):
    # 주간 데이터 확인을 위해 1개월치 로드
    df = yf.download(symbol, period='1mo', interval='30m', progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert('Asia/Seoul')
    return df

# 3. 차트 생성 함수
def draw_dashboard():
    fig = go.Figure()
    cols = st.columns(len(tickers))
    colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96']
    all_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        df_raw = load_data(symbol)
        if df_raw.empty: continue
        df = df_raw.copy()

        # 월요일 09:00 기준가 찾기
        monday_bases = df[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
        
        def get_ref_price(ts):
            past = monday_bases[monday_bases.index <= ts]
            return float(past['Close'].iloc[-1]) if not past.empty else float(df['Close'].iloc[0])

        # 수익률 계산
        df['Base_Price'] = [get_ref_price(ts) for ts in df.index]
        raw_return = ((df['Close'] - df['Base_Price']) / df['Base_Price'] * 100)

        # 가중치 설정
        weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
        df['Return'] = raw_return * weight
        
        curr_ret = float(df['Return'].iloc[-1])
        display_name = f"{name} (5x)" if symbol == 'DX-Y.NYB' else (f"{name} (2x)" if symbol == 'SI=F' else name)

        # 상단 지표 표시
        cols[i].metric(label=display_name, value=f"{curr_ret:+.2f}%")

        # 차트 선 추가
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Return'],
            mode='lines', name=display_name,
            line=dict(width=2, color=colors[i])
        ))
        all_indices.append(df.index)

    # 월요일 리셋 실선 표시
    if all_indices:
        start_date = min([idx.min() for idx in all_indices])
        end_date = max([idx.max() for idx in all_indices])
        curr = start_date.replace(hour=9, minute=0, second=0)
        while curr <= end_date:
            if curr.weekday() == 0:
                fig.add_vline(x=curr.timestamp()*1000, line_dash="solid", 
                              line_color="rgba(200,0,0,0.2)", annotation_text=curr.strftime('%m%d'))
            curr += timedelta(days=1)

    fig.add_hline(y=0, line_color="black", opacity=0.5)
    fig.update_layout(
        hovermode="x unified", height=600, template='plotly_white',
        xaxis=dict(title="날짜", tickformat="%m%d\n%H:%M", dtick=86400000.0),
        yaxis=dict(title="주간 수익률 (%)"),
        legend=dict(orientation="h", y=1.02, x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# 실행
draw_dashboard()

st.caption(f"최근 갱신: {datetime.now().strftime('%m%d %H:%M:%S')} | 기준: 매주 월요일 09:00 리셋 | 데이터: yfinance 30분봉")
