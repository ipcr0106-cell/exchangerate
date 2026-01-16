import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Fixed Exchange Dashboard", layout="wide")

# 2. CSS 강화: 브라우저 줌 조절 시에도 레이아웃 보호
st.markdown(
    """
    <style>
    /* 1. 전체 컨테이너 너비를 고정하여 줌 아웃 시 요소가 퍼지지 않게 함 */
    .main .block-container {
        max-width: 1200px; /* 최대 너비 제한 */
        min-width: 1000px; /* 최소 너비 고정 */
        margin: 0 auto;    /* 중앙 정렬 */
        padding-top: 2rem;
    }

    /* 2. 상단 옵션 컬럼들(selectbox, slider)의 크기가 변하지 않게 고정 */
    [data-testid="column"] {
        min-width: 250px !important;
        flex: 1 1 250px !important;
    }

    /* 3. 메트릭(증감 수치) 카드 크기 고정 */
    [data-testid="stMetric"] {
        width: fit-content;
        min-width: 150px;
    }
    
    /* 4. 가로 스크롤 허용 (브라우저를 아주 작게 줄였을 때 깨짐 방지) */
    .main {
        overflow-x: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("💰 글로벌 환율 변동 분석 대시보드")

# 전체 통화 리스트
all_currencies = ["USD", "EUR", "KRW", "JPY", "GBP", "CAD", "CNY", "HKD"]

# --- 상단 옵션 배치 ---
st.write("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    base_currency = st.selectbox("기준 통화 (1단위)", all_currencies, index=0)

with col2:
    filtered_currencies = [c for c in all_currencies if c != base_currency]
    target_currencies = st.multiselect(
        "비교할 통화들",
        options=filtered_currencies,
        default=["KRW"]
    )

with col3:
    current_year = datetime.now().year
    year_range = st.slider("조회 연도 범위", 1999, current_year, (2015, current_year))

st.write("---")

# --- 데이터 로드 함수 ---
@st.cache_data(ttl=3600)
def get_exchange_data(base, targets, start_y, end_y):
    if not targets: return None
    start_date = f"{start_y}-01-04"
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = f"{end_y}-12-31" if end_y < current_year else today
    
    url = f"https://api.frankfurter.app/{start_date}..{end_date}?from={base}&to={','.join(targets)}"
    try:
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data['rates']).T
        df.index = pd.to_datetime(df.index)
        return df
    except:
        return None

# --- 결과 출력 섹션 ---
if target_currencies:
    df_rates = get_exchange_data(base_currency, target_currencies, year_range[0], year_range[1])

    if df_rates is not None and not df_rates.empty:
        # 1. 전날 대비 환율 증감 추이
        st.subheader("🔔 전날 대비 실시간 환율 증감 현황")
        m_cols = st.columns(len(target_currencies))
        
        for i, target in enumerate(target_currencies):
            if target in df_rates.columns:
                series = df_rates[target].dropna()
                current_val = series.iloc[-1]
                prev_val = series.iloc[-2] if len(series) > 1 else current_val
                delta = current_val - prev_val
                
                val_format = ".4f" if base_currency == "KRW" or current_val < 1 else ".2f"
                
                with m_cols[i]:
                    st.metric(
                        label=f"1 {base_currency} ➔ {target}", 
                        value=f"{current_val:{val_format}}", 
                        delta=f"{delta:{val_format}}"
                    )
        
        st.write("---")

        # 2. 연도별 환율 변동 추이 (그래프 섹션)
        target_names = ", ".join(target_currencies)
        st.subheader(f"📈 {year_range[0]}년~{year_range[1]}년 {base_currency} 대비 {target_names} 환율 변동 추이")
        
        fig = go.Figure()
        for target in target_currencies:
            if target in df_rates.columns:
                fig.add_trace(go.Scatter(
                    x=df_rates.index, y=df_rates[target], 
                    mode='lines', name=target,
                    line=dict(width=2),
                    hovertemplate='%{x|%Y-%m-%d}<br>환율: %{y:,.4f}'
                ))

        fig.update_layout(
            hovermode="x unified",
            xaxis=dict(tickformat="%Y", dtick="M12", fixedrange=True, title="연도"),
            yaxis=dict(fixedrange=True, title="환율"),
            dragmode=False,
            height=500,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
    else:
        st.error("데이터를 불러오지 못했습니다.")
else:
    st.info("상단에서 비교할 통화를 선택해 주세요.")