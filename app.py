import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정 및 레이아웃 중앙 박제 CSS
st.set_page_config(page_title="Fixed Central Dashboard", layout="wide")

st.markdown(
    """
    <style>
    /* 배경 및 가로 스크롤 허용 */
    .main { background-color: #ffffff; overflow-x: auto !important; }

    /* 메인 컨테이너 1100px 중앙 고정 */
    .main .block-container {
        width: 1100px !important;
        max-width: 1100px !important;
        min-width: 1100px !important;
        margin: 0 auto !important;
        padding: 2rem 0 !important;
        text-align: center;
    }

    /* 텍스트 요소 중앙 정렬 */
    h1, h2, h3, .stMarkdown { text-align: center !important; }

    /* 옵션 컬럼 너비 및 위치 고정 */
    [data-testid="column"] {
        width: 300px !important;
        flex: none !important;
        margin: 0 auto !important;
        text-align: left;
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
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    base_currency = st.selectbox("기준 통화 (1단위)", all_currencies, index=0)

with c2:
    filtered_currencies = [c for c in all_currencies if c != base_currency]
    target_currencies = st.multiselect(
        "비교할 통화들",
        options=filtered_currencies,
        default=["KRW"]
    )

with c3:
    current_year = datetime.now().year
    year_range = st.slider("조회 연도 범위", 1999, current_year, (2015, current_year))

st.write("---")

# --- 데이터 로드 함수 (Frankfurter API) ---
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
        # 1. 상단 증감 현황 (Metric)
        st.subheader("🔔 전날 대비 실시간 환율 증감 현황")
        m_cols = st.columns(len(target_currencies))
        
        for i, target in enumerate(target_currencies):
            series = df_rates[target].dropna()
            current_val = series.iloc[-1]
            prev_val = series.iloc[-2] if len(series) > 1 else current_val
            delta = current_val - prev_val
            val_format = ".4f" if base_currency == "KRW" or current_val < 1 else ".2f"
            
            with m_cols[i]:
                st.metric(label=f"1 {base_currency} ➔ {target}", value=f"{current_val:{val_format}}", delta=f"{delta:{val_format}}")
        
        st.write("---")

        # 2. 연도별 환율 변동 추이 (Plotly 고정 모드)
        st.subheader(f"📈 {year_range[0]}년~{year_range[1]}년 환율 변동 추이")
        
        fig = go.Figure()
        for target in target_currencies:
            fig.add_trace(go.Scatter(
                x=df_rates.index, 
                y=df_rates[target], 
                mode='lines', 
                name=target,
                line=dict(width=2.5),
                hovertemplate='%{x|%Y-%m-%d}<br>환율: %{y:,.4f}'
            ))

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode="x unified",
            # X축 설정: 연도 고정 및 드래그 방지
            xaxis=dict(
                title="연도 (Year)",
                tickformat="%Y", 
                dtick="M12", 
                fixedrange=True, # 드래그/줌 방지
                gridcolor='#f0f0f0'
            ),
            # Y축 설정: 드래그 방지
            yaxis=dict(
                title="환율 가치",
                fixedrange=True, # 드래그/줌 방지
                gridcolor='#f0f0f0'
            ),
            margin=dict(l=50, r=50, t=30, b=50),
            height=500,
            dragmode=False, # 마우스 드래그 기능 비활성화
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # 툴바 숨기기 및 줌 방지 설정 적용하여 출력
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
        
    else:
        st.error("데이터를 불러오지 못했습니다.")