import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Настройки страницы
st.set_page_config(page_title="Cloud Trade Admin", layout="wide")
st_autorefresh(interval=20000, key="refresh")

# ID вашей таблицы
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"
# Ссылка для прямого экспорта данных в CSV
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

st.title("📈 Gemini Cloud Trading Stats")

try:
    # Загружаем данные из Google Таблицы (она должна быть открыта по ссылке)
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], format='mixed')
        df['Conf'] = pd.to_numeric(df['Conf'], errors='coerce').fillna(0)
        
        # Метрики
        m1, m2 = st.columns(2)
        m1.metric("Всего сигналов", len(df))
        m2.metric("Средняя точность", f"{round(df['Conf'].mean(), 1)}%")

        # График
        fig = px.line(df.sort_values('Date'), x='Date', y='Conf', markers=True, title="Динамика точности ИИ")
        st.plotly_chart(fig, use_container_width=True)

        # Таблица
        st.subheader("Журнал сделок")
        st.dataframe(df.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.warning("Таблица пуста. Отправьте первый сигнал через бота!")

except Exception as e:
    st.error(f"Ошибка подключения к Google Таблице. Проверьте права доступа! ({e})")