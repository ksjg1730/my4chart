import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="삼성전자 실시간 분석기", layout="wide")

# 2. 종목 및 기본 설정
tickers_info = {
    '005930.KS': {'name': '삼성전자', 'color': '#0057D8', 'width': 6},
    'CL=F': {'name': 'WTI 원유', 'color': '#E67E22', 'width': 2},
    'DX-Y.NYB': {'name': '달러지수(x5)', 'color': '#34495E', 'width': 2},
    'SI=F': {'name': '글로벌 은', 'color': '#BDC3C7', 'width': 2}
}

@st.cache_data(ttl=30) # 실시간성을 위해 캐시를 30초로 단축
def get_data_with_current():
    combined_df = []
    current_stats = {}
    
    for sym, info in tickers_info.items():
        try:
            # 데이터 로드
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            close = df['Close'][sym] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            close = close.copy()
            
            # KST 변환
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC').tz_convert('Asia/Seoul')
            else:
                close.index = close.index.tz_convert('Asia/Seoul')

            # --- 실시간 수치 추출 ---
            latest_price = close.dropna().iloc[-1]
            prev_close = close.dropna().iloc[-2] if len(close) > 1 else latest_price
            chg_pct = ((latest_price - prev_close) / prev_close) * 100
            current_stats[sym] = {'price': latest_price, 'chg': chg_pct}

            # 주간 수익률 (월요일 시작점 기준)
            year_week = close.index.strftime('%Y-%U')
            first_prices = close.groupby(year_week).transform(lambda x: x.dropna().iloc[0] if not x.dropna().empty else np.nan)
            ret = ((close - first_prices) / first_prices * 100)
            
            if sym == 'DX-Y.NYB': ret *= 5
            
            ret.name = sym
            combined_df.append(ret)
        except: continue
        
    return pd.concat(combined_df, axis=1) if combined_df else None, current_stats

def run_app():
    st.title("🚀 삼성전자 & 글로벌 지표 실시간 분석")
    
    df, stats = get_data_with_current()
    if df is None:
        st.error("데이터 로드 실패")
        return

    fig = go.Figure()

    # 그리기 순서 (삼성전자가 맨 위)
    plot_order = ['CL=F', 'DX-Y.NYB', 'SI=F', '005930.KS']
    
    for sym in plot_order:
        if sym in df.columns:
            info = tickers_info[sym]
            curr = stats.get(sym, {'price': 0, 'chg': 0})
            
            # 종목 이름에 현재가와 등락률 추가
            display_name = f"{info['name']} [{curr['price']:,.1f} | {curr['chg']:+.2f}%]"
            
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym],
                name=display_name,
                line=dict(color=info['color'], width=info['width']),
                connectgaps=True,
                hovertemplate=f"<b>{info['name']}</b><br>주간수익률: %{{y:.2f}}%<br>현재가: {curr['price']:,.1f}<extra></extra>"
            ))

    # 월요일 개장선
    monday_starts = df.index[(df.index.weekday == 0) & (df.index.hour == 9) & (df.index.minute == 0)]
    for m_start in monday_starts:
        fig.add_vline(x=m_start, line_width=1, line_color="black")

    fig.update_layout(
        hovermode="x unified",
        height=800,
        xaxis=dict(
            tickformat="%m/%d %H:%M",
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[15.5, 9], pattern="hour"),
            ]
        ),
        yaxis=dict(
            title="주간 수익률 (%)",
            range=[-20, 20],
            zeroline=True, zerolinewidth=2, zerolinecolor='black'
        ),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center", font=dict(size=12))
    )

    st.plotly_chart(fig, use_container_width=True)
    st.write(f"⏱️ 마지막 업데이트: {df.index[-1].strftime('%Y-%m-%d %H:%M:%S')} (KST)")

if __name__ == "__main__":
    run_app()
