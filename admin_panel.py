import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Настройки страницы
st.set_page_config(page_title="Cloud Trade Admin", layout="wide")
# Автообновление каждые 20 секунд
st_autorefresh(interval=20000, key="refresh")

# ВАША НОВАЯ ССЫЛКА ИЗ GOOGLE
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ8ILWnyjNQrRGXwsBg5twqLHemr9rorb4R_FZqDqnSCpmKyC5ufWazkhC-BA6pMa3uPKA8yKgvW6cn/pub?gid=0&single=true&output=csv"

st.title("📈 Gemini Cloud Trading Stats")

try:
    # Загружаем данные напрямую
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        # Приводим типы данных в порядок
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Conf'] = pd.to_numeric(df['Conf'], errors='coerce').fillna(0)
        
        # Основные показатели
        m1, m2 = st.columns(2)
        m1.metric("Всего сигналов", len(df))
        m2.metric("Средняя точность", f"{round(df['Conf'].mean(), 1)}%")

        # График динамики
        fig = px.line(df.sort_values('Date'), x='Date', y='Conf', 
                     markers=True, title="Точность сигналов ИИ во времени",
                     template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        # Таблица последних сделок
        st.subheader("Журнал сигналов")
        st.dataframe(df.sort_values('Date', ascending=False), 
                     use_container_width=True, hide_index=True)
    else:
        st.info("Таблица пока пуста. Бот еще не отправил ни одного сигнала.")

except Exception as e:
    st.error(f"Не удалось прочитать данные. Проверьте публикацию таблицы! Ошибка: {e}")