import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Настройки страницы
st.set_page_config(page_title="Cloud Trade Admin", layout="wide")
# Обновление раз в 20 секунд
st_autorefresh(interval=20000, key="refresh")

# ВАША ПУБЛИЧНАЯ ССЫЛКА (Уже исправлена)
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ8ILWnyjNQrRGXwsBg5twqLHemr9rorb4R_FZqDqnSCpmKyC5ufWazkhC-BA6pMa3uPKA8yKgvW6cn/pub?gid=0&single=true&output=csv"

st.title("📈 Gemini Cloud Trading Stats")

try:
    # Загрузка данных
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Conf'] = pd.to_numeric(df['Conf'], errors='coerce').fillna(0)
        
        # Метрики
        m1, m2 = st.columns(2)
        m1.metric("Всего сигналов", len(df))
        m2.metric("Средняя точность", f"{round(df['Conf'].mean(), 1)}%")

        # Красивый темный график
        fig = px.area(df.sort_values('Date'), x='Date', y='Conf', 
                     title="Точность сигналов (Real-time)",
                     template="plotly_dark", color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig, use_container_width=True)

        # Таблица данных
        st.subheader("История сделок")
        st.dataframe(df.sort_values('Date', ascending=False), 
                     use_container_width=True, hide_index=True)
    else:
        st.info("Данных пока нет. Бот готов к первой записи!")

except Exception as e:
    st.error(f"Ошибка загрузки данных: {e}")
