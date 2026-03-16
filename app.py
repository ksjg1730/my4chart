import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="통합 수익률 대시보드", layout="wide")

st.title("📊 자산별 주간/월간 수익률 통합 분석")
st.info("💡 차트는 **이번 주(월요일 09:00 기준)** 수익률이며, 상단 지표에서 **이번 달(월초 기준)** 성적을 함께 확인하세요.")

# 2. 종목 설정
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물 (2x)',
    'DX-Y.NYB': 'DXY 달러지수 (5x)',
    '233740.KS': 'KODEX 코스닥150레버리지'
}

@st.cache_data(ttl=600)
def load_data(symbol):
    # 월간 계산을 위해 2개월치 데이터 로드
    df = yf.download(symbol, period='2mo', interval='30m', progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert('Asia/Seoul')
    return df

# 3. 데이터 처리 및 차트 생성
def draw_integrated_dashboard():
    fig = go.Figure()
    cols = st.columns(len(tickers))
    colors = ['#333333', '#FFD700', '#FF4B4B', '#00CC96']
    all_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        df_raw = load_data(symbol)
        if df_raw.empty: continue
        df = df_raw.copy()

        # --- A. 주간 기준가 계산 (이번 주 월요일 09:00) ---
        monday_bases = df[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
        
        # --- B. 월간 기준가 계산 (이번 달 초 개장) ---
        df['month_val'] = df.index.month
        month_bases = df[df['month_val'] != df['month_val'].shift(1)]

        def get_ref_price(ts, base_df):
            past = base_df[base_df.index <= ts]
            return float(past['Close'].iloc[-1]) if not past.empty else float(df['Close'].iloc[0])

        # 주간/월간 수익률 계산
        df['Weekly_Base'] = [get_ref_price(ts, monday_bases) for ts in df.index]
        df['Monthly_Base'] = [get_ref_price(ts, month_bases) for ts in df.index]
        
        week_raw = ((df['Close'] - df['Weekly_Base']) / df['Weekly_Base'] * 100)
        month_raw = ((df['Close'] - df['Monthly_Base']) / df['Monthly_Base'] * 100)

        # 가중치 설정
        weight = 5 if symbol == 'DX-Y.NYB' else (2 if symbol == 'SI=F' else 1)
        df['Weekly_Ret'] = week_raw * weight
        df['Monthly_Ret'] = month_raw * weight
        
        curr_week = float(df['Weekly_Ret'].iloc[-1])
        curr_month = float(df['Monthly_Ret'].iloc[-1])

        # --- 상단 지표 표시 ---
        with cols[i]:
            st.markdown(f"**{name}**")
            st.metric(label="이번주(가중)", value=f"{curr_week:+.2f}%")
            st.metric(label="이번달(가중)", value=f"{curr_month:+.2f}%")

        # --- 차트 추가 ---
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Weekly_Ret'],
            mode='lines', name=name,
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
    
    st.plotly_chart(fig, use_container_width=True, key="integrated_chart")

draw_integrated_dashboard()

# 마지막 줄 수정됨
st.caption(f"최근 갱신: {datetime.now().strftime('%m%d %H:%M:%S')} | 데이터: yfinance 30분봉 | 가중치(2x, 5x) 반영됨")
