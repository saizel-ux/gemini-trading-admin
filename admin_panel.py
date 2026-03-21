import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# 1. НАСТРОЙКИ СТРАНИЦЫ
st.set_page_config(
    page_title="Gemini Trade Admin", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Автообновление каждые 30 секунд
st_autorefresh(interval=30000, key="refresh")

# ID вашей таблицы (проверьте, что он верный)
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

# 2. ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
@st.cache_data(ttl=30)
def load_data(url):
    try:
        data = pd.read_csv(url)
        
        # Стандартизация колонок
        expected_columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        if len(data.columns) >= 7:
            data.columns = expected_columns[:len(data.columns)]
        
        # Очистка даты
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        
        # Очистка Confidence (убираем % и лишние знаки)
        if 'Confidence' in data.columns:
            data['Confidence'] = data['Confidence'].astype(str).str.replace('%', '').str.strip()
            data['Confidence'] = pd.to_numeric(data['Confidence'], errors='coerce').fillna(0)
            
        # Очистка цен
        for col in ['Entry', 'SL', 'TP']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # Удаление пустых строк
        data = data.dropna(subset=['Date', 'Symbol'])
        return data
    except Exception as e:
        st.error(f"Ошибка при чтении CSV: {e}")
        return pd.DataFrame()

# 3. ОСНОВНОЙ БЛОК
try:
    df = load_data(CSV_URL)
    
    if df.empty:
        st.warning("📭 Данные не найдены. Убедитесь, что в Google Таблице есть записи и доступ открыт 'Всем по ссылке'.")
    else:
        # Расчет дополнительных метрик
        df['Potential_Profit'] = abs(df['TP'] - df['Entry']) / df['Entry'] * 100
        df['Potential_Risk'] = abs(df['Entry'] - df['SL']) / df['Entry'] * 100
        df['Risk_Reward'] = df.apply(
            lambda x: x['Potential_Profit'] / x['Potential_Risk'] if x['Potential_Risk'] > 0 else 0, 
            axis=1
        )

        # ВЕРХНИЕ МЕТРИКИ
        st.subheader("📊 Ключевые показатели")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Всего сигналов", len(df))
        m2.metric("Средняя точность", f"{round(df['Confidence'].mean(), 1)}%")
        m3.metric("LONG", len(df[df['Direction'].str.upper().str.contains('LONG', na=False)]))
        m4.metric("SHORT", len(df[df['Direction'].str.upper().str.contains('SHORT', na=False)]))
        
        st.markdown("---")

        # ГРАФИК УВЕРЕННОСТИ
        st.subheader("📈 Динамика точности")
        daily = df.groupby(df['Date'].dt.date).agg({'Confidence': 'mean', 'Symbol': 'count'}).reset_index()
        daily.columns = ['Date', 'Avg_Conf', 'Count']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily['Date'], y=daily['Avg_Conf'], name="Уверенность %", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Bar(x=daily['Date'], y=daily['Count'], name="Кол-во", yaxis='y2', opacity=0.3))
        
        fig.update_layout(
            template='plotly_dark',
            yaxis=dict(title="Уверенность (%)", range=[0, 101]),
            yaxis2=dict(title="Кол-во сигналов", overlaying='y', side='right'),
            hovermode='x unified', height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        # ТАБЛИЦА СДЕЛОК
        st.subheader("📋 История сделок")
        
        def style_direction(val):
            v = str(val).upper()
            if 'LONG' in v: return 'color: #00ff00'
            if 'SHORT' in v: return 'color: #ff4444'
            return ''

        display_df = df.sort_values('Date', ascending=False).head(50)
        
        # Совместимость версий Pandas (map vs applymap)
        try:
            styled_df = display_df.style.map(style_direction, subset=['Direction'])
        except AttributeError:
            styled_df = display_df.style.applymap(style_direction, subset=['Direction'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=450,
            column_config={
                "Date": st.column_config.DatetimeColumn("Время", format="DD.MM HH:mm"),
                "Confidence": st.column_config.NumberColumn("Уверенность", format="%d%%"),
                "Risk_Reward": st.column_config.NumberColumn("R/R", format="%.2f"),
                "Entry": st.column_config.NumberColumn("Вход", format="%.5f"),
                "TP": st.column_config.NumberColumn("Тейк", format="%.5f"),
                "SL": st.column_config.NumberColumn("Стоп", format="%.5f"),
            }
        )

        if st.button("🔄 Сбросить кэш и обновить"):
            st.cache_data.clear()
            st.rerun()

except Exception as e:
    st.error(f"⚠️ Произошла ошибка: {e}")
