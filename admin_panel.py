import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Gemini Admin Panel", layout="wide")
st_autorefresh(interval=20000, key="refresh")

# Публичная ссылка Google Sheets → File → Share → Publish to web → CSV
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ8ILWnyjNQrRGXwsBg5twqLHemr9rorb4R_FZqDqnSCpmKyC5ufWazkhC-BA6pMa3uPKA8yKgvW6cn/pub?gid=0&single=true&output=csv"

st.title("📈 Gemini Trading Bot — Live Stats")
st.markdown("---")

@st.cache_data(ttl=20)
def load_data() -> pd.DataFrame:
    return pd.read_csv(CSV_URL)

try:
    df = load_data()

    if df.empty:
        st.info("Данных пока нет. Бот готов к первой записи!")
        st.stop()

    # Нормализация имён колонок (на случай разных вариантов написания)
    df.columns = [c.strip() for c in df.columns]
    rename_map = {
        "direction": "Dir", "symbol": "Symbol",
        "confidence": "Conf", "duration": "Duration",
        "entry": "Entry", "sl": "SL", "tp": "TP",
    }
    df.rename(columns=rename_map, inplace=True)

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Conf'] = pd.to_numeric(df['Conf'], errors='coerce').fillna(0)
    df = df[df['Symbol'] != 'NONE'].sort_values('Date')

    # ── Метрики ───────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Всего сигналов", len(df))
    m2.metric("Средняя уверенность", f"{round(df['Conf'].mean(), 1)}%")
    m3.metric("Последний тикер", str(df['Symbol'].iloc[-1]))
    calls = len(df[df['Dir'].isin(['CALL', 'BUY', 'LONG'])])
    puts  = len(df[df['Dir'].isin(['PUT', 'SELL', 'SHORT'])])
    m4.metric("CALL / PUT", f"{calls} / {puts}")

    st.markdown("---")

    # ── Графики ───────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("Активы")
        fig_pie = px.pie(df, names='Symbol', hole=0.3, template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Динамика уверенности")
        fig_line = px.area(
            df, x='Date', y='Conf', color='Symbol',
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_line.add_hline(y=70, line_dash="dash", line_color="orange",
                           annotation_text="Порог 70%")
        st.plotly_chart(fig_line, use_container_width=True)

    with c3:
        st.subheader("CALL vs PUT")
        dir_df = df['Dir'].value_counts().reset_index()
        dir_df.columns = ['Направление', 'Количество']
        fig_bar = px.bar(
            dir_df, x='Направление', y='Количество',
            color='Направление', template="plotly_dark",
            color_discrete_map={
                'CALL': '#00c853', 'BUY': '#00c853', 'LONG': '#00c853',
                'PUT': '#d50000', 'SELL': '#d50000', 'SHORT': '#d50000',
            }
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Таблица ───────────────────────────────────────────────
    st.subheader("📋 История сделок")

    def highlight_dir(row):
        color = '#1b5e2030' if row.get('Dir') in ('CALL', 'BUY', 'LONG') else '#b71c1c30'
        return [f'background-color: {color}'] * len(row)

    styled = df.sort_values('Date', ascending=False).style.apply(highlight_dir, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── Боковая панель ────────────────────────────────────────
    st.sidebar.header("⚙️ Управление")

    if st.sidebar.button("🔄 Обновить данные"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    # Очистка истории — только если в Streamlit Cloud настроены secrets
    if "gcp_service_account" in st.secrets and "SHEET_ID" in st.secrets:
        st.sidebar.warning("Это удалит все записи из Google Sheets!")
        if st.sidebar.button("🗑 Очистить историю", type="primary"):
            try:
                import gspread
                from google.oauth2.service_account import Credentials
                creds = Credentials.from_service_account_info(
                    dict(st.secrets["gcp_service_account"]),
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive",
                    ]
                )
                gc = gspread.authorize(creds)
                ws = gc.open_by_key(st.secrets["SHEET_ID"]).get_worksheet(0)
                ws.clear()
                ws.append_row(["Date", "Symbol", "Dir", "Entry", "SL", "TP", "Conf", "Duration"])
                st.cache_data.clear()
                st.sidebar.success("✅ История очищена!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Ошибка: {e}")
    else:
        st.sidebar.info("💡 Для очистки прямо из панели добавьте `gcp_service_account` и `SHEET_ID` в Streamlit Cloud Secrets.\n\nИли используйте команду `/clear` в Telegram-боте.")

except Exception as e:
    st.error(f"Ошибка загрузки данных: {e}")
    st.exception(e)
