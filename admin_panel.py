import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# Настройки страницы
st.set_page_config(
    page_title="Gemini Trade Admin", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Обновление раз в 30 секунд
st_autorefresh(interval=30000, key="refresh")

# ID вашей таблицы
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"
# Используем экспорт в CSV
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

@st.cache_data(ttl=30)  # Кешируем данные на 30 секунд
def load_data(url):
    # Читаем CSV, принудительно считая первую строку заголовками
    data = pd.read_csv(url)
    
    # Ожидаемые колонки
    expected_columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
    
    # Если загрузилось не то количество колонок, пробуем переназначить
    if len(data.columns) >= 7:
        data.columns = expected_columns[:len(data.columns)]
    
    # --- ОЧИСТКА ДАННЫХ ---
    # Убираем лишние пробелы и знаки % из колонки уверенности
    if 'Confidence' in data.columns:
        data['Confidence'] = data['Confidence'].astype(str).str.replace('%', '').str.strip()
        data['Confidence'] = pd.to_numeric(data['Confidence'], errors='coerce').fillna(0)
    
    # Преобразование даты
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
    
    # Преобразование цен в числа (удаляем возможные пробелы)
    for col in ['Entry', 'SL', 'TP']:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
            
    # Удаляем строки, где нет даты или символа
    data = data.dropna(subset=['Date', 'Symbol'])
    return data

try:
    df = load_data(CSV_URL)
    
    if df.empty:
        st.warning("📭 Таблица пуста или недоступна. Проверьте права доступа 'Доступ по ссылке' в Google Таблице.")
    else:
        # Расчет Risk/Reward (с защитой от деления на ноль)
        df['Potential_Profit'] = abs(df['TP'] - df['Entry']) / df['Entry'] * 100
        df['Potential_Risk'] = abs(df['Entry'] - df['SL']) / df['Entry'] * 100
        
        # Защита: если риск 0, ставим RR = 0, чтобы не было ошибки
        df['Risk_Reward'] = df.apply(
            lambda x: x['Potential_Profit'] / x['Potential_Risk'] if x['Potential_Risk'] > 0 else 0, 
            axis=1
        )
        
        # --- МЕТРИКИ ---
        st.subheader("📊 Ключевые показатели")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Всего сигналов", len(df))
        m2.metric("Средняя точность", f"{round(df['Confidence'].mean(), 1)}%")
        m3.metric("LONG", len(df[df['Direction'].str.upper() == 'LONG']))
        m4.metric("SHORT", len(df[df['Direction'].str.upper() == 'SHORT']))
        
        st.markdown("---")
        
        # --- ГРАФИК УВЕРЕННОСТИ ---
        st.subheader("📈 Динамика точности сигналов")
        daily = df.groupby(df['Date'].dt.date).agg({'Confidence': 'mean', 'Symbol': 'count'}).reset_index()
        daily.columns = ['Date', 'Avg_Conf', 'Count']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily['Date'], y=daily['Avg_Conf'], name="Уверенность %", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Bar(x=daily['Date'], y=daily['Count'], name="Кол-во", yaxis='y2', opacity=0.3))
        
        fig.update_layout(
            template='plotly_dark',
            yaxis=dict(title="Уверенность (%)", range=[0, 100]),
            yaxis2=dict(title="Кол-во сигналов", overlaying='y', side='right'),
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # --- РАСПРЕДЕЛЕНИЕ ---
        c1, c2 = st.columns(2)
        with c1:
            sym_fig = px.pie(df, names='Symbol', title="Топ инструментов", hole=0.4, template='plotly_dark')
            st.plotly_chart(sym_fig, use_container_width=True)
        with c2:
            dir_fig = px.bar(df['Direction'].value_counts(), title="Направления", 
                             color=df['Direction'].value_counts().index,
                             color_discrete_map={'LONG': '#00ff00', 'SHORT': '#ff4444'}, template='plotly_dark')
            st.plotly_chart(dir_fig, use_container_width=True)

        # --- ТАБЛИЦА ---
        st.subheader("📋 История сделок")
        
        # Настройка стилей для таблицы
        def style_direction(val):
            if str(val).upper() == 'LONG': return 'color: #00ff00'
            if str(val).upper() == 'SHORT': return 'color: #ff4444'
            return ''

        # В новых версиях pandas/streamlit используется .map вместо .applymap
        display_df = df.sort_values('Date', ascending=False).head(50)
        styled_df = display_df.style.map(style_direction, subset=['Direction'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            column_config={
                "Date": st.column_config.DatetimeColumn("Время", format="DD.MM HH:mm"),
                "Confidence": st.column_config.NumberColumn("Уверенность", format="%d%%"),
                "Risk_Reward": st.column_config.NumberColumn("R/R", format="%.2f"),
                "Entry": st.column_config.NumberColumn("Вход", format="%.5f"),
                "TP": st.column_config.NumberColumn("Тейк", format="%.5f"),
                "SL": st.column_config.NumberColumn("Стоп", format="%.5f"),
            }
        )

        # Кнопки под таблицей
        if st.button("🔄 Очистить кэш и обновить"):
            st.cache_data.clear()
            st.rerun()

except Exception as e:
    st.error(f"⚠️ Критическая ошибка: {e}")
    st.info("💡 Проверьте, что в Google Таблице ровно 7 колонок и доступ открыт 'Всем, у кого есть ссылка'.")
