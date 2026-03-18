
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ... (페이지 설정 및 tickers 설정은 동일)

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            # interval='15m'은 최근 60일 데이터까지만 제공됨에 유의
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                # MultiIndex 대응 및 Close 컬럼 추출
                if isinstance(df.columns, pd.MultiIndex):
                    close = df['Close'][sym].copy()
                else:
                    close = df['Close'].copy()
                
                close.index = close.index.tz_convert('Asia/Seoul')
                
                # 주간 수익률 계산: 해당 주의 첫 번째 가격 기준
                weeks = close.index.isocalendar().week
                years = close.index.year
                first_prices = close.groupby([years, weeks]).transform('first')
                
                # 달러지수 가중치 5배 적용 (사용자 로직 유지)
                weight = 5 if sym == 'DX-Y.NYB' else 1
                ret = ((close - first_prices) / first_prices * 100) * weight
                ret.name = sym
                all_data.append(ret)
        except Exception as e:
            st.warning(f"{sym} 데이터 로드 중 오류: {e}")
            continue
    
    if not all_data: return None
    # 결측치는 이전 값으로 채움 (장 시작 전후 공백 대비)
    return pd.concat(all_data, axis=1).ffill().dropna()

def run_app():
    # ... (상단 타이틀 및 지표 로직 동일)

    # --- 📈 그래프 그리기 ---
    fig = go.Figure()

    # 1. 종목별 선
    for sym, info in tickers.items():
        if sym in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym], name=info['name'],
                line=dict(color=info['color'], width=2),
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 2. 🔥 슈퍼 1등선 (가시성 위해 대시선 추천)
    t1_line = df.max(axis=1) + 3.0
    fig.add_trace(go.Scatter(
        x=df.index, y=t1_line, name="🔥 슈퍼 1등선 (+3%)",
        line=dict(color='red', width=3, dash='dot'), # 점선으로 변경 시 더 세련됨
        hovertemplate="<b>슈퍼 1등선</b>: %{y:.2f}%<extra></extra>"
    ))

    # 3. 🔵 월요일 리셋 수직선 (로직 보강)
    # 데이터셋 내에서 주(Week)가 바뀌는 지점을 찾음
    df['week'] = df.index.isocalendar().week
    reset_points = df.index[df['week'] != df['week'].shift(1)]
    
    for rp in reset_points:
        if rp != df.index[0]: # 첫 번째 데이터 제외
            fig.add_vline(x=rp, line_width=1.5, line_color="blue", line_dash="dash", opacity=0.6)

    # 레이아웃 및 렌더링...
