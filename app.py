import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="조합선 집중 분석 모드", layout="wide")

# 2. 종목 설정
tickers = {
    'CL=F': {'name': 'WTI 원유', 'color': '#E67E22'},
    'DX-Y.NYB': {'name': '달러지수', 'color': '#34495E'},
    'SI=F': {'name': '글로벌 은', 'color': '#BDC3C7'},
    'HG=F': {'name': '구리(HG=F)', 'color': '#D35400'}
}

@st.cache_data(ttl=60)
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
                close = close.copy()
                close.index = close.index.tz_convert('Asia/Seoul')
                
                # 금요일 14시 컷오프
                mask = ((close.index.weekday == 4) & (close.index.hour >= 14)) | (close.index.weekday >= 5)
                close.loc[mask] = np.nan
                
                # 주간 수익률 계산
                year, week = close.index.year, close.index.isocalendar().week
                first_price = close.groupby([year, week]).transform('first')
                ret = ((close - first_price) / first_price * 100)
                
                # 가중치 적용 (달러 x5, 구리 x2)
                if sym == 'DX-Y.NYB': ret *= 5
                if sym == 'HG=F': ret *= 2
                
                ret.name = sym
                all_data.append(ret)
        except: continue
    
    return pd.concat(all_data, axis=1) if all_data else None

def run_app():
    st.title("📊 구리 & 은 조합선 (조합선 외 모두 투명화)")
    st.markdown("##### ✨ 4가지 조합선만 강조 | 🌫 슈퍼 1등선 & 3등선 투명화 | ✂️ -1% 미만 절단")

    df = get_clean_data()
    if df is None: return

    # --- 🧮 4가지 핵심 수익선 계산 ---
    if 'SI=F' in df.columns and 'HG=F' in df.columns:
        s, c = df['SI=F'], df['HG=F']
        df['CU_plus_AG']  = c + s
        df['CU_minus_AG_rev'] = -c - s
        df['AG_minus_CU'] = s - c
        df['CU_minus_AG'] = c - s

    # --- 🔍 데이터 필터링 (-1% 미만 제거) ---
    df_filtered = df.copy()
    df_filtered[df_filtered < -1.0] = np.nan

    fig = go.Figure()

    # 1. 🌫 투명 지표군 (배경 처리: 기초자산)
    for sym, info in tickers.items():
        if sym in df_filtered.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered.index, y=df_filtered[sym], 
                name=f"{info['name']} (참고)",
                opacity=0.03, line=dict(color='gray', width=1),
                connectgaps=False, hoverinfo='skip'
            ))

    # 2. 🚀 강조 지표군: 4가지 구리/은 조합선
    combos = [
        ('CU_plus_AG', '➕ 구리 + 은', '#27AE60'),     # 녹색
        ('CU_minus_AG_rev', '➖ -구리 - 은', '#C0392B'), # 빨간색
        ('AG_minus_CU', '📊 은 - 구리', '#2980B9'),     # 파란색
        ('CU_minus_AG', '📊 구리 - 은', '#8E44AD')      # 보라색
    ]
    
    combo_cols = [c[0] for c in combos if c[0] in df_filtered.columns]

    for col, name, color in combos:
        if col in df_filtered.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered.index, y=df_filtered[col], 
                name=name,
                line=dict(color=color, width=4), 
                connectgaps=False,
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 3. 🌫 투명 지표군 (슈퍼 1등선 & 3등선)
    if combo_cols:
        # 슈퍼 1등선 (+3%)
        t1_line = df_filtered[combo_cols].max(axis=1) + 3.0
        fig.add_trace(go.Scatter(
            x=df_filtered.index, y=t1_line, name="🌫 슈퍼 1등선 (투명)",
            line=dict(color='red', width=1), 
            opacity=0.05, connectgaps=False, hoverinfo='skip'
        ))
        
        # 3등선 (현재 조합선들 중 3번째로 높은 수익률)
        # 각 행(시간)별로 정렬하여 3번째 값을 추출
        t3_line = df_filtered[combo_cols].apply(lambda x: sorted(x.dropna(), reverse=True)[2] if len(x.dropna()) >= 3 else np.nan, axis=1)
        fig.add_trace(go.Scatter(
            x=df_filtered.index, y=t3_line, name="🌫 3등선 (투명)",
            line=dict(color='blue', width=1, dash='dot'), 
            opacity=0.05, connectgaps=False, hoverinfo='skip'
        ))

    # 레이아웃 설정
    fig.update_layout(
        hovermode="x unified", height=800, template="plotly_white",
        xaxis=dict(title="시간 (KST)", tickformat="%m/%d %H:%M"),
        yaxis=dict(title="수익률 (%)", ticksuffix="%", range=[-1.1, df_filtered[combo_cols].max().max() + 5]),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
