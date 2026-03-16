import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="글로벌 자산 수익률 비교", layout="wide")

st.title("📊 글로벌 원유 vs 지표 수익률 비교")

# 2. 종목 설정 (1번을 WTI 원유 선물로 변경)
tickers = {
    'CL=F': 'WTI 원유 선물 (NYMEX)',   # 1번 항목 (석유)
    'SI=F': '글로벌 은 선물 (COMEX)',   # 2배 가중치
    'DX-Y.NYB': 'DXY 달러지수 현물',    # 5배 가중치
    '233740.KS': 'KODEX 코스닥150레버리지'
}

def get_reference_time():
    """가장 최근 월요일 09:00 (KST) 기준 시간을 계산"""
    today = datetime.now()
    # 요일 계산 (0:월, 1:화...)
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday)
    
    # 만약 오늘이 월요일인데 아직 9시 전이면 지난주 월요일로
    if today.weekday() == 0 and today.hour < 9:
        last_monday -= timedelta(days=7)
        
    return pd.Timestamp(last_monday.replace(hour=9, minute=0, second=0)).tz_localize('Asia/Seoul')

ref_time = get_reference_time()

# 3. 차트 그리기
@st.fragment(run_every=60)
def draw_chart():
    fig = go.Figure()
    cols = st.columns(len(tickers))
    # 원유(검정/진회색), 은(금색), 달러(빨강), 코스닥(녹색)
    colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96'] 

    all_data_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        # 데이터 수집 (30분봉)
        df = yf.download(symbol, period='1mo', interval='30m', progress=False)
        if df.empty: continue
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.index = df.index.tz_convert('Asia/Seoul')
        all_data_indices.append(df.index)
        
        # [수익률 기준점 변경: 월요일 09:00]
        base_df = df[df.index <= ref_time]
        base_price = float(base_df['Close'].iloc[-1]) if not base_df.empty else float(df['Close'].iloc[0])
        
        raw_return = ((df['Close'] - base_price) / base_price * 100)
        
        # 가중치 설정
        if symbol == 'DX-Y.NYB':
            df['Return'] = raw_return * 5
            display_name = f"{name} (5x)"
        elif symbol == 'SI=F':
            df['Return'] = raw_return * 2
            display_name = f"{name} (2x)"
        else:
            df['Return'] = raw_return
            display_name = name
            
        current_return = float(df['Return'].iloc[-1])
        cols[i].metric(label=display_name, value=f"{current_return:+.2f}%")

        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['Return'],
            mode='lines',
            name=display_name,
            line=dict(width=2, color=colors[i])
        ))

    # 4. 월요일 오전 09:00 수직 실선
    if all_data_indices:
        start_date = min([idx.min() for idx in all_data_indices])
        end_date = max([idx.max() for idx in all_data_indices])
        curr = start_date.replace(hour=9, minute=0, second=0)
        while curr <= end_date:
            if curr.weekday() == 0:
                fig.add_vline(
                    x=curr.timestamp() * 1000, 
                    line_width=1.5, 
                    line_dash="solid", 
                    line_color="rgba(128, 128, 128, 0.6)",
                    annotation_text=curr.strftime('%m%d'),
                    annotation_position="top left"
                )
            curr += timedelta(days=1)

    # 5. 기준점(월요일 9시) 강조선
    fig.add_vline(x=ref_time.timestamp() * 1000, line_dash="dash", line_color="blue", line_width=2, annotation_text="이번주 시작")
    fig.add_hline(y=0, line_color="black", line_width=1, opacity=0.3)
    
    fig.update_layout(
        hovermode="x unified",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(
            title="날짜",
            showgrid=True,
            tickformat="%m%d\n%H:%M",
            dtick=86400000.0, 
            tickangle=0
        ),
        yaxis=dict(title="수익률 (%)", showgrid=True),
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)
    
    st.caption(f"이번 주 기준(월 09:00): {ref_time.strftime('%m%d %H:%M')} | 갱신: {datetime.now().strftime('%m%d %H:%M:%S')}")

draw_chart()
