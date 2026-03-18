import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="자산 통합 수익률 대시보드", layout="wide")

# 2. 종목 설정 (달러지수 심볼이 불안정할 경우를 대비해 처리)
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#FF9900'},
    'SI=F': {'name': '글로벌 은', 'color': '#95A5A6'},
    'DX-Y.NYB': {'name': '달러지수(x5)', 'color': '#2C3E50'},
    'SOXX': {'name': '반도체(SOXX)', 'color': '#3498DB'}
}

@st.cache_data(ttl=300)
def get_clean_data():
    all_data = []
    success_tickers = []
    
    for sym, info in tickers.items():
        try:
            # interval='1h'로 1개월치 데이터 다운로드
            df = yf.download(sym, period='1mo', interval='1h', progress=False)
            
            if df.empty or len(df) < 5:
                st.warning(f"⚠️ {info['name']}({sym}) 데이터를 가져올 수 없습니다.")
                continue
            
            # 컬럼 정리 (Multi-index 방지)
            if isinstance(df.columns, pd.MultiIndex):
                close = df['Close'][sym].copy()
            else:
                close = df['Close'].copy()

            # 타임존 처리 (KST)
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC')
            close.index = close.index.tz_convert('Asia/Seoul')

            # 주간 수익률 리셋 계산
            years = close.index.year
            weeks = close.index.isocalendar().week
            first_price = close.groupby([years, weeks]).transform('first')
            
            weight = 5 if sym == 'DX-Y.NYB' else 1
            ret = ((close - first_price) / first_price * 100) * weight
            ret.name = sym
            all_data.append(ret)
            success_tickers.append(sym)
            
        except Exception as e:
            st.error(f"❌ {sym} 로드 중 에러: {e}")
            continue
    
    if not all_data:
        return None, []
    
    combined_df = pd.concat(all_data, axis=1).ffill().dropna()
    return combined_df, success_tickers

def run_app():
    st.title("📊 전 종목 합산 통합 수익선 (1시간봉)")
    
    df, success_list = get_clean_data()
    
    if df is None or df.empty:
        st.error("🚨 모든 데이터 로드에 실패했습니다. 잠시 후 다시 시도하거나 인터넷 연결을 확인하세요.")
        return

    # --- 🧮 통합선 계산 (로드 성공한 종목들만 합산) ---
    df['통합'] = df[success_list].sum(axis=1)

    fig = go.Figure()

    # 1. ⚫ 통합 합산선
    fig.add_trace(go.Scatter(
        x=df.index, y=df['통합'], 
        name="<b>Σ 통합 합산선</b>",
        line=dict(color='black', width=5),
        hovertemplate="<b>[통합 합계]</b>: %{y:.2f}%<extra></extra>"
    ))

    # 2. 개별 종목 수익선
    for sym in success_list:
        info = tickers[sym]
        fig.add_trace(go.Scatter(
            x=df.index, y=df[sym], 
            name=info['name'],
            line=dict(color=info['color'], width=1.5),
            opacity=0.5,
            hovertemplate=f"{info['name']}: %{{y:.2f}}%<extra></extra>"
        ))

    # 3. ❌ 주도주 교체 지점 (X 표시)
    leader_series = df[success_list].idxmax(axis=1)
    change_mask = leader_series != leader_series.shift(1)
    change_mask.iloc[0] = False
    cross_points = df[change_mask]
    
    if not cross_points.empty:
        fig.add_trace(go.Scatter(
            x=cross_points.index,
            y=[df.loc[t, leader_series[t]] for t in cross_points.index],
            mode='markers',
            marker=dict(symbol='x', size=18, color='red', line=dict(width=2, color='white')),
            name="주도주 교체"
        ))

    # 레이아웃 설정
    fig.update_layout(
        hovermode="x unified", height=750, template="plotly_white",
        xaxis=dict(tickformat="%m/%d %H:%M"),
        yaxis=dict(ticksuffix="%"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

    # 상태 요약
    st.info(f"✅ 현재 로드된 종목: {', '.join([tickers[s]['name'] for s in success_list])}")

if __name__ == "__main__":
    run_app()
