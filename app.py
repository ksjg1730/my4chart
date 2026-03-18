import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="조합선 초집중 분석기", layout="wide")

# 2. 종목 및 기본 설정
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
            # 15분 단위 데이터 로드
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if not df.empty:
                close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
                close = close.copy()
                close.index = close.index.tz_convert('Asia/Seoul')
                
                # --- 🕒 데이터 필터링: 금요일 14:00 이후 ~ 월요일 개장 전 삭제 ---
                day_of_week = close.index.weekday
                hour = close.index.hour
                # 금요일(4) 14시 이후 OR 토요일(5) OR 일요일(6) 데이터 제외
                mask = ((day_of_week == 4) & (hour >= 14)) | (day_of_week >= 5)
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
    st.title("📊 구리 & 은 조합선 (주말 공백 제거 모드)")
    st.markdown("##### ✨ 조합선 4종 강조 | 🌫 배경지표(1등/3등/기초자산) 투명화 | ✂️ -1% 미만 및 주말 타임라인 삭제")

    df = get_clean_data()
    if df is None:
        st.error("데이터를 불러오는 데 실패했습니다.")
        return

    # --- 🧮 4가지 핵심 수익선 계산 ---
    if 'SI=F' in df.columns and 'HG=F' in df.columns:
        s, c = df['SI=F'], df['HG=F']
        df['CU_plus_AG']  = c + s      # 구리 + 은
        df['CU_minus_AG_rev'] = -c - s # -구리 - 은
        df['AG_minus_CU'] = s - c      # 은 - 구리
        df['CU_minus_AG'] = c - s      # 구리 - 은

    # --- 🔍 데이터 필터링 (-1% 미만 수치 제거) ---
    df_filtered = df.copy()
    df_filtered[df_filtered < -1.0] = np.nan

    fig = go.Figure()

    # 1. 🌫 배경: 기초 자산 (매우 투명하게)
    for sym, info in tickers.items():
        if sym in df_filtered.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered.index, y=df_filtered[sym], 
                name=f"{info['name']} (참고)",
                opacity=0.03, line=dict(color='gray', width=1),
                connectgaps=False, hoverinfo='skip'
            ))

    # 2. 🚀 주인공: 4가지 조합선 (굵고 선명하게)
    combos = [
        ('CU_plus_AG', '➕ 구리 + 은', '#27AE60'),
        ('CU_minus_AG_rev', '➖ -구리 - 은', '#C0392B'),
        ('AG_minus_CU', '📊 은 - 구리', '#2980B9'),
        ('CU_minus_AG', '📊 구리 - 은', '#8E44AD')
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

    # 3. 🌫 배경: 슈퍼 1등선 & 3등선 (투명하게)
    if combo_cols:
        # 슈퍼 1등선 (+3%)
        t1_line = df_filtered[combo_cols].max(axis=1) + 3.0
        fig.add_trace(go.Scatter(
            x=df_filtered.index, y=t1_line, name="🌫 슈퍼 1등선 (투명)",
            line=dict(color='red', width=1), 
            opacity=0.05, connectgaps=False, hoverinfo='skip'
        ))
        
        # 3등선 (조합선 중 상위 3위)
        t3_line = df_filtered[combo_cols].apply(
            lambda x: sorted(x.dropna(), reverse=True)[2] if len(x.dropna()) >= 3 else np.nan, axis=1
        )
        fig.add_trace(go.Scatter(
            x=df_filtered.index, y=t3_line, name="🌫 3등선 (투명)",
            line=dict(color='blue', width=1, dash='dot'), 
            opacity=0.05, connectgaps=False, hoverinfo='skip'
        ))

    # 4. 레이아웃 및 X축 타임라인 압축
    fig.update_layout(
        hovermode="x unified",
        height=800,
        template="plotly_white",
        xaxis=dict(
            title="시간 (KST)", 
            tickformat="%m/%d %H:%M",
            # --- ✂️ 주말 공백 삭제 설정 ---
            rangebreaks=[
                dict(bounds=[14, 24], pattern="hour"), # 금요일 14시 ~ 24시 삭제
                dict(bounds=["sat", "mon"]),           # 토요일 ~ 월요일 아침 삭제
            ]
        ),
        yaxis=dict(
            title="수익률 (%)", 
            ticksuffix="%", 
            # -1% 필터링을 반영하여 Y축 범위 설정
            range=[-1.1, df_filtered[combo_cols].max().max() + 5]
        ),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
