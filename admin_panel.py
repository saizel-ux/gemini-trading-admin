import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
import os

st.set_page_config(page_title="Gemini Admin", layout="wide")
st_autorefresh(interval=30000, key="refresh")

# Ссылки (Замените SHEET_ID на ваш)
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"
CSV_URL = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vQ8ILWnyjNQrRGXwsBg5twqLHemr9rorb4R_FZqDqnSCpmKyC5ufWazkhC-BA6pMa3uPKA8yKgvW6cn/pub?gid=0&single=true&output=csv"

def get_sheets_client():
    if not os.path.exists('service_account.json'): return None
    creds = Credentials.from_service_account_file('service_account.json', 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_data(ttl=10)
def load_data(url):
    try:
        data = pd.read_csv(url)
        # Названия для 8 колонок
        expected = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence', 'Duration']
        data.columns = expected[:len(data.columns)]
        data['Date'] = pd.to_datetime(data['Date'])
        return data
    except:
        return pd.DataFrame()

# ИНТЕРФЕЙС
st.title("📈 Аналитика Gemini Trade")

with st.sidebar:
    st.header("⚙️ Управление")
    if st.button("🗑️ Очистить всю историю"):
        gc = get_sheets_client()
        if gc:
            ws = gc.open_by_key(SHEET_ID).get_worksheet(0)
            ws.resize(rows=1)
            ws.resize(rows=100)
            st.success("Таблица очищена!")
            st.rerun()

df = load_data(CSV_URL)

if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Всего сигналов", len(df))
    m2.metric("Средняя уверенность", f"{int(df['Confidence'].mean())}%")
    m3.metric("Последний актив", df.iloc[-1]['Symbol'])

    # График уверенности
    fig = go.Figure(go.Scatter(x=df['Date'], y=df['Confidence'], mode='lines+markers', name="Confidence", line=dict(color='#00ff00')))
    fig.update_layout(template='plotly_dark', title="Точность предсказаний", height=300)
    st.plotly_chart(fig, use_container_width=True)

    # Таблица с новой колонкой Срок (Duration)
    st.subheader("📋 Журнал сделок")
    st.dataframe(
        df.sort_values('Date', ascending=False),
        column_config={
            "Date": st.column_config.DatetimeColumn("Время", format="DD.MM HH:mm"),
            "Duration": "⏳ Срок",
            "Confidence": st.column_config.NumberColumn("Уверенность", format="%d%%"),
        },
        use_container_width=True
    )
else:
    st.info("Данных пока нет. Отправьте скриншот боту.")
