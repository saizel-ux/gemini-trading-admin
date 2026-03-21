import streamlit as st
import pandas as pd
import plotly.express as px
import os
from streamlit_autorefresh import st_autorefresh

# Настройки страницы
st.set_page_config(page_title="Gemini Admin Panel", layout="wide")

# Автообновление каждые 10 секунд
st_autorefresh(interval=10000, key="panel_refresh")

st.title("📈 Gemini DeepMind Live Stats")
st.markdown("---")

LOG_FILE = "trade_log.csv"

if os.path.exists(LOG_FILE):
    try:
        df = pd.read_csv(LOG_FILE)
        
        # ИСПРАВЛЕНИЕ ОШИБКИ ДАТЫ: format='mixed' автоматически поймет секунды
        df['Date'] = pd.to_datetime(df['Date'], format='mixed')
        
        # Преобразование уверенности в число
        df['Conf'] = pd.to_numeric(df['Conf'], errors='coerce').fillna(0)
        
        # Сортировка для графиков
        df = df.sort_values(by='Date')

        # Метрики
        m1, m2, m3 = st.columns(3)
        m1.metric("Всего сигналов", len(df))
        m2.metric("Средняя точность", f"{round(df['Conf'].mean(), 1)}%")
        m3.metric("Последний тикер", str(df['Symbol'].iloc[-1]))

        st.markdown("---")

        # Графики
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Активы")
            fig_pie = px.pie(df, names='Symbol', hole=0.3)
            st.plotly_chart(fig_pie, width='stretch')
        
        with c2:
            st.subheader("Динамика точности")
            fig_line = px.line(df, x='Date', y='Conf', markers=True)
            st.plotly_chart(fig_line, width='stretch')

        # Таблица
        st.subheader("📋 Журнал логов")
        st.dataframe(df.sort_values('Date', ascending=False), width='stretch', hide_index=True)

        # Очистка
        if st.sidebar.button("🗑 Очистить историю"):
            os.remove(LOG_FILE)
            st.rerun()

    except Exception as e:
        st.error(f"Ошибка чтения данных: {e}")
else:
    st.info("👋 Жду данных от бота... Отправьте тикер в Telegram.")