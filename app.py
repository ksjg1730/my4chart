import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="글로벌 자산 수익률 대시보드", layout="wide")

# 2. 사이드바 메뉴
st.sidebar.title("📌 기준 선택")
mode = st.sidebar.radio("수익률 리셋 기준:", ["주간 리셋 (월 09:00)", "월간 리셋 (월초 09:00)"])

st.title(f"📊 글로벌 주요 자산 {mode} 분석")

# 3. 종목 설정 (4번에 SOXX 반도체 지수 추가)
tickers = {
    'CL=F': 'WTI 원유 선물',
    'SI=F': '글로벌 은 선물 (2x)',
    'DX-Y.NYB': 'DXY 달러지수 (5x)',
    'SOXX': '필라델피아 반도체(SOXX)' # 4번 항목 교체
}

@st.cache_data(ttl=600)
def load_data(symbol):
    # 월간 데이터를 위해 2개월치 로드
    df = yf.download(symbol, period='2mo', interval='30m', progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert('Asia/Seoul')
    return df

# 4. 차트 및 지표 생성 함수
def draw_dashboard(selection):
    fig = go.Figure()
    cols = st.columns(len(tickers))
    # 각 종목별 고유 색상 (검정, 금색, 빨강, 파랑)
    colors = ['#333333', '#FFD700', '#FF4B4B', '#1A237E']
    all_indices = []

    for i, (symbol, name) in enumerate(tickers.items()):
        df_raw = load_data(symbol)
        if df_raw.empty: continue
        df = df_raw.copy()

        # --- 기준점 설정 로직 ---
        if "주간" in selection:
            # 매주 월요일 09:00 기준
            bases = df[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
            label_format = '%m%d'
        else:
            # 매월 초 첫 데이터 기준
            df['m_val'] = df.index.month
            bases = df[df['m_val'] != df['m_val'].shift(1)]
            label_format = '%m월'

        def get_ref_price(ts):
            past = bases[bases.index <= ts]
            return float(past['Close'].iloc[-1]) if not past.empty else float(df['Close'].iloc[0])

        # 수익률 계산
        df['Base_Price'] = [get_ref_price(ts) for ts in df.index]
        raw_return = ((df['Close'] - df['Base_Price']) / df['Base_Price'] * 100)

        # 가중치 설정 (달러 5배, 은 2배, 나머지는 1배)
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

    # 리셋 수직선 표시
    if all_indices:
        start_ts = min([idx.min() for idx in all_indices])
        for b_ts in bases.index:
            if b_ts >= start_ts:
                fig.add_vline(x=b_ts.timestamp()*1000, line_dash="solid", 
                              line_color="rgba(128, 128, 128, 0.3)", 
                              annotation_text=b_ts.strftime(label_format))

    fig.add_hline(y=0, line_color="black", opacity=0.5)
    fig.update_layout(
        hovermode="x unified", height=650, template='plotly_white',
        xaxis=dict(title="날짜 (KST)", tickformat="%m%d\n%H:%M", dtick=86400000.0),
        yaxis=dict(title="수익률 (%)"),
        legend=dict(orientation="h", y=1.02, x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{selection}")

# 실행
draw_dashboard(mode)

st.caption(f"최근 갱신: {datetime.now().strftime('%m%d %H:%M:%S')} | {mode} 기준 적용됨 | 반도체 지수(SOXX) 추가 완료")
