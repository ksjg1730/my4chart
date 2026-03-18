import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="상위 1-2등 합산 수익률", layout="wide")

# 2. 종목 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},
    'DX-Y.NYB': {'name': '달러지수(x5)', 'color': '#2C3E50'},
    'SOXX': {'name': '반도체(SOXX)', 'color': '#3498DB'}
}

@st.cache_data(ttl=300)
def get_clean_data():
    all_data = []
    success_list = []
    for sym, info in tickers.items():
        try:
            # 1시간봉, 1개월 데이터
            df = yf.download(sym, period='1mo', interval='1h', progress=False)
            if df.empty: continue
            
            # Multi-index 처리
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            
            # KST 변환
            if close.index.tz is None: close = close.tz_localize('UTC')
            close = close.index.tz_convert('Asia/Seoul')

            # 주간 리셋 수익률
            first_price = close.groupby([close.index.year, close.index.isocalendar().week]).transform('first')
            weight = 5 if sym == 'DX-Y.NYB' else 1
            ret = ((close - first_price) / first_price * 100) * weight
            ret.name = sym
            all_data.append(ret)
            success_list.append(sym)
        except: continue
    
    if not all_data: return None, []
    return pd.concat(all_data, axis=1).ffill().dropna(), success_list

def run_app():
    st.title("🏆 상위 1-2등 주도주 합산선 (1시간봉)")
    st.markdown("##### ⚫ **검정 굵은선**: 실시간 1등 + 2등 수익률 합계 | ❌ **적색 십자가**: 주도주 교체")

    df, success_list = get_clean_data()
    if df is None:
        st.error("데이터 로드 실패. yfinance 연결을 확인하세요.")
        return

    # --- 🧮 상위 1-2등 합산 계산 ---
    # 각 행(시간)별로 상위 2개 값만 골라 더함
    df['상위합산'] = df[success_list].apply(lambda x: x.nlargest(2).sum(), axis=1)

    fig = go.Figure()

    # 1. ⚫ 상위 1-2등 합산선
    fig.add_trace(go.Scatter(
        x=df.index, y=df['상위합산'], 
        name="<b>Σ 상위 1-2등 합산</b>",
        line=dict(color='black', width=5),
        hovertemplate="<b>[1+2등 합계]</b>: %{y:.2f}%<extra></extra>"
    ))

    # 2. 개별 종목 선 (참고용)
    for sym in success_list:
        info = tickers[sym]
        fig.add_trace(go.Scatter(
            x=df.index, y=df[sym], 
            name=info['name'],
            line=dict(color=info['color'], width=1.5),
            opacity=0.4,
            hovertemplate=f"{info['name']}: %{{y:.2f}}
