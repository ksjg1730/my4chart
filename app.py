import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="글로벌 자산 수익률 비교", layout="wide")

st.title("📊 글로벌 지표 vs 국내 ETF 수익률 비교 (가중치 적용)")

# 2. 종목 설정
tickers = {
    'DX=F': '달러 인덱스 선물',        # 5배 가중치 적용 대상
    'SI=F': '글로벌 은 선물 (COMEX)',  # 2배 가중치 유지
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

# 3. 차트 그리기
@st.fragment(run_every=60)
def draw_chart():
    fig = go.Figure()
    cols = st.columns(len(tickers))
    colors = ['#1F77B4', '#FFD700', '#EF553B', '#00CC96'] 

    all_data_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        df = yf.download(symbol, period='1mo', interval='30m', progress=False)
        if df.empty: continue
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.index = df.index.tz_convert('Asia/Seoul')
        all_data_indices.append(df.index)
        
        base_df = df[df.index <= ref_time]
        base_price = float(base_df['Close'].iloc[-1]) if not base_df.empty else float(df['Close'].iloc[0])
        
        raw_return = ((df['Close'] - base_price) / base_price * 100)
        
        # [가중치 적용 로직]
        if symbol == 'DX=F':
            df['Return'] = raw_return * 5  # 달러 인덱스 5배 가중치
            display_name = f"{name} (5x)"
        elif symbol == 'SI=F':
            df['Return'] = raw_return * 2  # 글로벌 은 선물 2배 가중치
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

    # 4. 월요일 오전 09:00 수직 실선 추가
    if all_data_indices:
        start_date = min([idx.min() for idx in all_data_indices])
        end_date = max([idx.max() for idx in all_data_indices])
        curr = start_date.replace(hour=9, minute=0, second=0)
        while curr <= end_date:
            if curr.weekday() == 0:
                fig.add_vline(
                    x=curr.timestamp() * 1000, 
                    line_width=1, 
                    line_dash="solid", 
                    line_color="rgba(128, 128, 128, 0.4)",
                    annotation_text="Mon 09:00",
                    annotation_position="top left"
                )
            curr += timedelta(days=1)

    fig.add_vline(x=ref_time.timestamp() * 1000, line_dash="dash", line_color="green", line_width=2, annotation_text="기준점")
    fig.add_hline(y=0, line_color="black", line_width=1, opacity=0.3)
    
    fig.update_layout(
        hovermode="x unified",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="날짜 (KST)", showgrid=True),
        yaxis=dict(title="수익률 (%)", showgrid=True),
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"기준: {ref_time.strftime('%Y-%m-%d %H:%M')} | 갱신: {datetime.now().strftime('%H:%M:%S')}")

draw_chart()
