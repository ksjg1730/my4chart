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

@st.cache_data(ttl=300) # 캐시 시간을 조금 늘려 성능 최적화
def get_clean_data():
    all_data = []
    for sym, info in tickers.items():
        try:
            # 15분 단위 데이터 로드 (최근 1개월)
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            # MultiIndex 대응 및 Close 데이터 추출
            if isinstance(df.columns, pd.MultiIndex):
                close = df['Close'][sym].copy()
            else:
                close = df['Close'].copy()
            
            # 시간대 변환 (UTC -> Asia/Seoul)
            close.index = close.index.tz_convert('Asia/Seoul')
            
            # --- 🕒 데이터 필터링: 금요일 14:00 이후 ~ 월요일 개장 전 (주말 공백) ---
            day_of_week = close.index.weekday
            hour = close.index.hour
            # 금요일(4) 14시 이후 ~ 일요일(6) 전체 데이터 제외
            mask = ((day_of_week == 4) & (hour >= 14)) | (day_of_week >= 5)
            close.loc[mask] = np.nan
            
            # 주간 수익률 계산 (매주 월요일 시가 기준 0% 시작)
            year_week = close.index.strftime('%Y-%U')
            first_prices = close.groupby(year_week).transform('first')
            ret = ((close - first_prices) / first_prices * 100)
            
            # 가중치 적용 (현실적인 변동성 보정)
            if sym == 'DX-Y.NYB': ret *= 5
            if sym == 'HG=F': ret *= 2
            
            ret.name = sym
            all_data.append(ret)
        except Exception as e:
            st.warning(f"{sym} 데이터를 가져오는 중 오류 발생: {e}")
            continue
    
    return pd.concat(all_data, axis=1) if all_data else None

def run_app():
    st.title("📊 구리 & 은 조합선 (전략 분석 모드)")
    st.markdown("##### ✨ 조합선 4종 강조 | 🌫 배경지표 투명화 | ✂️ -1% 미만 및 주말 공백 제거")

    df = get_clean_data()
    if df is None or df.empty:
        st.error("데이터를 불러오지 못했습니다. 시장 휴장 여부를 확인하세요.")
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
    # 조합선 컬럼들에 대해서만 필터링 적용 (가시성 확보)
    combo_names = ['CU_plus_AG', 'CU_minus_AG_rev', 'AG_minus_CU', 'CU_minus_AG']
    for col in combo_names:
        if col in df_filtered.columns:
            df_filtered.loc[df_filtered[col] < -1.0, col] = np.nan

    fig = go.Figure()

    # 1. 🌫 배경: 기초 자산 (매우 투명하게)
    for sym, info in tickers.items():
        if sym in df_filtered.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered.index, y=df_filtered[sym], 
                name=f"{info['name']}",
                opacity=0.1, line=dict(color='gray', width=1),
                connectgaps=False, hoverinfo='skip'
            ))

    # 2. 🚀 주인공: 4가지 조합선 (굵고 선명하게)
    combos = [
        ('CU_plus_AG', '➕ 구리 + 은', '#27AE60'),
        ('CU_minus_AG_rev', '➖ -구리 - 은', '#C0392B'),
        ('AG_minus_CU', '📊 은 - 구리', '#2980B9'),
        ('CU_minus_AG', '📊 구리 - 은', '#8E44AD')
    ]

    for col, name, color in combos:
        if col in df_filtered.columns:
            fig.add_trace(go.Scatter(
                x=df_filtered.index, y=df_filtered[col], 
                name=name,
                line=dict(color=color, width=3.5), 
                connectgaps=False, # -1% 미만 끊김 유지
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 3. 🌫 배경: 상위권 가이드라인 (동적 계산)
    existing_combos = [c[0] for c in combos if c[0] in df_filtered.columns]
    if existing_combos:
        # 슈퍼 1등선 (+3% 오프셋)
        t1_line = df_filtered[existing_combos].max(axis=1) + 1.5
        fig.add_trace(go.Scatter(
            x=df_filtered.index, y=t1_line, name="🌫 상단 가이드",
            line=dict(color='red', width=1, dash='dash'), 
            opacity=0.2, connectgaps=False, hoverinfo='skip'
        ))

    # 4. 레이아웃 및 X축 타임라인 설정
    fig.update_layout(
        hovermode="x unified",
        height=750,
        template="plotly_white",
        xaxis=dict(
            title="시간 (KST)", 
            tickformat="%m/%d %H:%M",
            # 핵심: 거래가 없는 주말 시간대를 차트에서 완전히 삭제
            rangebreaks=[
                dict(bounds=[14, 24], pattern="hour"), # 금요일 오후 2시 이후
                dict(bounds=["sat", "mon"]),           # 토/일요일
                dict(bounds=[0, 7], pattern="hour")    # (선택) 새벽 휴장 시간
            ]
        ),
        yaxis=dict(
            title="상대적 수익률 (%)", 
            ticksuffix="%",
            zeroline=True, zerolinewidth=2, zerolinecolor='LightGray'
        ),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=50, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
