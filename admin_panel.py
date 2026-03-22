import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(
    page_title="Gemini Trade Admin", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Автообновление каждые 30 секунд
st_autorefresh(interval=30000, key="refresh")

# Ссылки и ID
SHEET_ID = os.getenv("SHEET_ID", "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I")
CSV_URL = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vQ8ILWnyjNQrRGXwsBg5twqLHemr9rorb4R_FZqDqnSCpmKyC5ufWazkhC-BA6pMa3uPKA8yKgvW6cn/pub?gid=0&single=true&output=csv"

def get_sheets_client():
    """Подключение к Google Sheets для управления данными"""
    key_path = 'service_account.json'
    if not os.path.exists(key_path):
        return None
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=5)
def load_data(url):
    """Загрузка данных из опубликованного CSV"""
    try:
        data = pd.read_csv(url)
        if data.empty:
            return pd.DataFrame()

        # Ожидаем 8 колонок
        expected_columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence', 'Duration']
        
        # Сопоставляем колонки по факту наличия
        if len(data.columns) >= 8:
            data.columns = expected_columns[:len(data.columns)]
        
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        data['Confidence'] = pd.to_numeric(data['Confidence'], errors='coerce').fillna(0)
        
        return data.dropna(subset=['Date', 'Symbol'])
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

# ИНТЕРФЕЙС
st.title("📈 Gemini Trade - Аналитическая панель")

# Боковая панель
with st.sidebar:
    st.header("⚙️ Управление")
    if st.button("🔄 Обновить данные"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.warning("⚠️ Опасная зона")
    if st.button("🗑️ Очистить всю историю"):
        try:
            gc = get_sheets_client()
            if gc:
                ws = gc.open_by_key(SHEET_ID).get_worksheet(0)
                ws.resize(rows=1) # Оставляем заголовок
                ws.resize(rows=100)
                st.success("История очищена!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Файл ключа не найден!")
        except Exception as e:
            st.error(f"Ошибка при очистке: {e}")

# ОСНОВНОЙ КОНТЕНТ
df = load_data(CSV_URL)

if df.empty:
    st.info("ℹ️ База данных пуста. Отправьте скриншот боту.")
else:
    # Метрики
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Всего сигналов", len(df))
    m2.metric("Ср. уверенность", f"{int(df['Confidence'].mean())}%")
    
    longs = len(df[df['Direction'].str.contains('LONG', na=False)])
    shorts = len(df[df['Direction'].str.contains('SHORT', na=False)])
    m3.metric("🟢 LONG", longs)
    m4.metric("🔴 SHORT", shorts)

    # График точности
    st.subheader("📈 Динамика уверенности ИИ")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Confidence'], 
        mode='lines+markers', 
        line=dict(color='#00ff00', width=2),
        fill='tozeroy'
    ))
    fig.update_layout(template='plotly_dark', height=350, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Таблица данных
    st.subheader("📋 Журнал экспертных сигналов")
    
    st.dataframe(
        df.sort_values('Date', ascending=False),
        use_container_width=True,
        column_config={
            "Date": st.column_config.DatetimeColumn("Время", format="DD.MM HH:mm"),
            "Symbol": "Актив",
            "Direction": "Тип",
            "Duration": "⏳ Срок сделки",
            "Confidence": st.column_config.NumberColumn("Уверенность", format="%d%%"),
            "Entry": "Вход",
            "SL": "Стоп",
            "TP": "Тейк"
        }
    )

st.markdown("---")
st.caption(f"Последнее обновление: {datetime.now().strftime('%H:%M:%S')}")
