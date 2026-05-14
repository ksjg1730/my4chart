import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="24H 수익률 분석기", layout="wide")

# 2. 종목 및 기본 설정
tickers_info = {
    '005930.KS': {'name': '삼성전자', 'color': '#0057D8', 'width': 5},
    'CL=F': {'name': 'WTI 원유', 'color': '#E67E22', 'width': 1.5},
    'DX-Y.NYB': {'name': '달러지수(x5)', 'color': '#34495E', 'width': 1.5},
    'SI=F': {'name': '글로벌 은', 'color': '#BDC3C7', 'width': 1.5}
}

@st.cache_data(ttl=30)
def get_performance_data():
    combined_df = []
    current_stats = {}
    
    for sym, info in tickers_info.items():
        try:
            # 데이터 로드 (1개월치, 15분봉)
            df = yf.download(sym, period='1mo', interval='15m', progress=False)
            if df.empty: continue
            
            if isinstance(df.columns, pd.MultiIndex):
                close = df['Close'][sym]
            else:
                close = df['Close']
            
            close = close.dropna()
            
            # 시간대 KST 변환
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC').tz_convert('Asia/Seoul')
            else:
                close.index = close.index.tz_convert('Asia/Seoul')

            # --- [핵심 수정] 기준 가격: 매주 금요일 13:00 ---
            # ISO 주차 기준으로 그룹화
            year_week = close.index.strftime('%G-%V')
            
            def get_friday_1pm_price(series):
                # 해당 주차 내에서 금요일(4) 13시 데이터를 찾음
                target = series[(series.index.weekday == 4) & (series.index.hour == 13)]
                if not target.empty:
                    return target.iloc[0]
                else:
                    # 금요일 13시 데이터가 없으면 해당 주의 첫 데이터로 대체
                    return series.iloc[0]

            base_price = close.groupby(year_week).transform(get_friday_1pm_price)
            
            # 수익률 계산
            ret = ((close - base_price) / base_price * 100)
            
            if sym == 'DX-Y.NYB': ret *= 5
            
            current_stats[sym] = {'price': close.iloc[-1], 'ret': ret.iloc[-1]}
            ret.name = sym
            combined_df.append(ret)
        except: continue
        
    return pd.concat(combined_df, axis=1) if combined_df else (None, {})

def run_app():
    st.title("📊 24H 국제 시세 및 수익률 비교")
    st.markdown("##### 🟦 삼성전자 강조 | ⬛ 기준: 매주 금요일 13:00 (0%) | 🌙 밤 시간 포함 24시간")

    df, stats = get_performance_data()
    if df is None:
        st.error("데이터 로딩 실패")
        return

    fig = go.Figure()
    plot_order = ['CL=F', 'DX-Y.NYB', 'SI=F', '005930.KS']
    
    for sym in plot_order:
        if sym in df.columns:
            info = tickers_info[sym]
            curr = stats.get(sym, {'price': 0, 'ret': 0})
            display_name = f"{info['name']} ({curr['ret']:+.2f}%)"
            
            fig.add_trace(go.Scatter(
                x=df.index, y=df[sym],
                name=display_name,
                line=dict(color=info['color'], width=info['width']),
                connectgaps=True,
                hovertemplate=f"<b>{info['name']}</b>: %{{y:.2f}}%<extra></extra>"
            ))

    # 기준선 (매주 금요일 13시 세로선 표시)
    friday_lines = df.index[(df.index.weekday == 4) & (df.index.hour == 13) & (df.index.minute == 0)]
    for f_line in friday_lines:
        fig.add_vline(x=f_line, line_width=1, line_dash="dot", line_color="red")

    fig.update_layout(
        hovermode="x unified",
        height=750,
        template="plotly_white",
        xaxis=dict(
            title="시간 (KST)",
            tickformat="%m/%d %H:%M",
            # rangebreaks에서 시간대 제한 삭제 (24시간 표시)
            rangebreaks=[dict(bounds=["sat", "mon"])] # 주말만 삭제 (필요시 이 줄도 삭제 가능)
        ),
        yaxis=dict(
            title="수익률 (기준: 금요일 13:00 = 0%)",
            range=[-15, 15],
            ticksuffix="%",
            zeroline=True, zerolinewidth=2, zerolinecolor='black'
        ),
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right")
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # 지표 카드 표시
    cols = st.columns(4)
    for i, sym in enumerate(plot_order):
        if sym in stats:
            cols[i].metric(tickers_info[sym]['name'], f"{stats[sym]['price']:,.2f}", f"{stats[sym]['ret']:.2f}%")

if __name__ == "__main__":
    run_app()
