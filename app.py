import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="ETF 수익률 비교 대시보드", layout="wide")

st.title("📊 ETF 실시간 수익률 비교")
st.sidebar.header("설정")

# 1. 종목 설정
tickers = {
    '144600.KS': 'KODEX 은선물(H)',
    '261250.KS': 'KODEX 달러레버리지',
    '233740.KS': 'KODEX 코스닥150레버리지',
    '494310.KS': 'KODEX 반도체레버리지'
}

# 2. 기준 시간 계산 함수
def get_reference_time():
    today = datetime.now()
    days_since_friday = (today.weekday() - 4) % 7
    last_friday = today - timedelta(days=days_since_friday)
    if today.weekday() < 4 or (today.weekday() == 4 and today.hour < 12):
        last_friday -= timedelta(days=7)
    return pd.Timestamp(last_friday.replace(hour=12, minute=0, second=0)).tz_localize('Asia/Seoul')

ref_time = get_reference_time()

# 사이드바 정보
st.sidebar.write(f"**기준 시간:** \n{ref_time.strftime('%Y-%m-%d %H:%M')}")
st.sidebar.write("*(최근 금요일 12:00 기준)*")
update_interval = st.sidebar.selectbox("갱신 주기", [60, 300, 600], index=0, format_func=lambda x: f"{x}초")

# 3. 데이터 로드 및 시각화
@st.fragment(run_every=update_interval) # 지정된 초마다 이 부분만 다시 실행
def draw_chart():
    fig = go.Figure()
    cols = st.columns(4) # 상단에 현재 수익률 표시용
    
    colors = ['#EF553B', '#00CC96', '#636EFA', '#AB63FA']

    for i, (symbol, name) in enumerate(tickers.items()):
        # 최근 1개월 데이터
        df = yf.download(symbol, period='1mo', interval='30m', progress=False)
        if df.empty: continue
        
        df.index = df.index.tz_convert('Asia/Seoul')
        
        # 수익률 계산
        base_df = df[df.index <= ref_time]
        base_price = base_df['Close'].iloc[-1] if not base_df.empty else df['Close'].iloc[0]
        df['Return'] = ((df['Close'] - base_price) / base_price * 100)
        current_return = df['Return'].iloc[-1].values[0]

        # 상단 지표(Metric) 표시
        cols[i].metric(label=name, value=f"{current_return:+.2f}%")

        # 메인 그래프 추가
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['Return'],
            mode='lines',
            name=name,
            line=dict(width=2, color=colors[i])
        ))

    # 그래프 레이아웃
    fig.update_layout(
        hovermode="x unified",
        height=600,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="날짜/시간"),
        yaxis=dict(title="수익률 (%)", zeroline=True, zerolinewidth=2, zerolinecolor='Black'),
        template='plotly_white'
    )
    
    # 기준선 세로줄
    fig.add_vline(x=ref_time.timestamp() * 1000, line_dash="dot", line_color="green", 
                  annotation_text="기준점")

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"최근 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

draw_chart()