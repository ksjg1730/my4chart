import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="글로벌 자산 수익률 비교", layout="wide")

st.title("📊 글로벌 은 선물 vs 국내 ETF 수익률 비교")

# 1. 종목 설정 (반도체 레버리지 -> 글로벌 은 선물로 변경)
tickers = {
    'SI=F': '글로벌 은 선물 (COMEX)',  # 글로벌 데이터로 변경
    '144600.KS': 'KODEX 은선물(H)',
    '261250.KS': 'KODEX 달러레버리지',
    '233740.KS': 'KODEX 코스닥150레버리지'
}

def get_reference_time():
    """최근 금요일 12:00 (KST) 계산"""
    today = datetime.now()
    days_since_friday = (today.weekday() - 4) % 7
    last_friday = today - timedelta(days=days_since_friday)
    if today.weekday() < 4 or (today.weekday() == 4 and today.hour < 12):
        last_friday -= timedelta(days=7)
    return pd.Timestamp(last_friday.replace(hour=12, minute=0, second=0)).tz_localize('Asia/Seoul')

ref_time = get_reference_time()

# 3. 데이터 로드 및 시각화
@st.fragment(run_every=60)
def draw_chart():
    fig = go.Figure()
    cols = st.columns(4)
    colors = ['#FFD700', '#EF553B', '#00CC96', '#636EFA'] # 은색/금색 느낌을 위해 첫번째 색상 변경

    for i, (symbol, name) in enumerate(tickers.items()):
        # 최근 1개월 데이터 (30분봉)
        df = yf.download(symbol, period='1mo', interval='30m', progress=False)
        if df.empty: continue
        
        # 중요: yfinance의 글로벌 데이터는 UTC 기준이므로 한국 시간(KST)으로 변환
        df.index = df.index.tz_convert('Asia/Seoul')
        
        # 수익률 계산
        base_df = df[df.index <= ref_time]
        # 기준 시점 데이터가 없을 경우 가장 가까운 과거 데이터 사용
        base_price = base_df['Close'].iloc[-1] if not base_df.empty else df['Close'].iloc[0]
        
        df['Return'] = ((df['Close'] - base_price) / base_price * 100)
        current_return = df['Return'].iloc[-1].values[0]

        # 상단 지표 표시
        cols[i].metric(label=name, value=f"{current_return:+.2f}%")

        # 메인 그래프 추가
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['Return'],
            mode='lines',
            name=name,
            line=dict(width=2, color=colors[i])
        ))

    fig.update_layout(
        hovermode="x unified",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="시간 (KST)"),
        yaxis=dict(title="수익률 (%)", zeroline=True, zerolinewidth=2, zerolinecolor='Black'),
        template='plotly_white'
    )
    
    fig.add_vline(x=ref_time.timestamp() * 1000, line_dash="dot", line_color="green")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"기준 시간: {ref_time.strftime('%Y-%m-%d %H:%M')} | 마지막 갱신: {datetime.now().strftime('%H:%M:%S')}")

draw_chart()
