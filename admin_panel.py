import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(
    page_title="Gemini Trade Admin", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Автообновление каждые 30 секунд
st_autorefresh(interval=30000, key="refresh")

# Ссылка на вашу публикацию (CSV)
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ8ILWnyjNQrRGXwsBg5twqLHemr9rorb4R_FZqDqnSCpmKyC5ufWazkhC-BA6pMa3uPKA8yKgvW6cn/pub?gid=0&single=true&output=csv"

st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

# 2. ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
@st.cache_data(ttl=5) # Уменьшил время кэша до 5 секунд для тестов
def load_data(url):
    try:
        data = pd.read_csv(url)
        
        if data.empty:
            return pd.DataFrame()

        # Принудительно называем колонки (если в CSV их меньше или больше)
        expected_columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        
        # Если загрузилось пустое поле или только заголовки
        if len(data) < 1:
            return pd.DataFrame()

        # Маппинг колонок (на случай, если в CSV другой порядок)
        if len(data.columns) >= 7:
            data.columns = expected_columns[:len(data.columns)]
        
        # Очистка данных
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        
        if 'Confidence' in data.columns:
            data['Confidence'] = data['Confidence'].astype(str).str.replace('%', '').str.strip()
            data['Confidence'] = pd.to_numeric(data['Confidence'], errors='coerce').fillna(0)
            
        for col in ['Entry', 'SL', 'TP']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        data = data.dropna(subset=['Date', 'Symbol'])
        return data
    except Exception as e:
        st.error(f"❌ Ошибка доступа к CSV: {e}")
        return pd.DataFrame()

# 3. ОСНОВНОЙ ИНТЕРФЕЙС
try:
    df = load_data(CSV_URL)
    
    if df.empty or len(df) == 0:
        st.info("ℹ️ **Таблица подключена, но данных о сделках пока нет.**")
        st.write("Как только вы отправите график боту в Telegram, здесь появится статистика.")
        if st.button("🔄 Проверить данные снова"):
            st.cache_data.clear()
            st.rerun()
    else:
        # Расчет Risk/Reward
        df['Potential_Profit'] = abs(df['TP'] - df['Entry']) / df['Entry'] * 100
        df['Potential_Risk'] = abs(df['Entry'] - df['SL']) / df['Entry'] * 100
        df['Risk_Reward'] = df.apply(
            lambda x: x['Potential_Profit'] / x['Potential_Risk'] if x['Potential_Risk'] > 0 else 0, 
            axis=1
        )

        # МЕТРИКИ
        st.subheader("📊 Ключевые показатели")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Всего сигналов", len(df))
        m2.metric("Ср. уверенность", f"{round(df['Confidence'].mean(), 1)}%")
        
        longs = len(df[df['Direction'].astype(str).str.upper().str.contains('LONG', na=False)])
        shorts = len(df[df['Direction'].astype(str).str.upper().str.contains('SHORT', na=False)])
        
        m3.metric("🟢 LONG", longs)
        m4.metric("🔴 SHORT", shorts)
        
        st.markdown("---")

        # ГРАФИК
        st.subheader("📈 Динамика точности ИИ")
        # Группировка по дням
        daily = df.groupby(df['Date'].dt.date).agg({'Confidence': 'mean', 'Symbol': 'count'}).reset_index()
        daily.columns = ['Date', 'Avg_Conf', 'Count']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily['Date'], y=daily['Avg_Conf'], name="Уверенность %", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Bar(x=daily['Date'], y=daily['Count'], name="Кол-во", yaxis='y2', opacity=0.3))
        
        fig.update_layout(
            template='plotly_dark',
            yaxis=dict(title="Уверенность (%)", range=[0, 101]),
            yaxis2=dict(title="Кол-во сигналов", overlaying='y', side='right'),
            hovermode='x unified', height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # ИСТОРИЯ СДЕЛАК
        st.subheader("📋 Последние сигналы")
        
        def style_direction(val):
            v = str(val).upper()
            if 'LONG' in v: return 'color: #00ff00; font-weight: bold'
            if 'SHORT' in v: return 'color: #ff4444; font-weight: bold'
            return ''

        display_df = df.sort_values('Date', ascending=False).head(50)
        
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
                "Entry": st.column_config.NumberColumn("Вход", format="%.4f"),
                "TP": st.column_config.NumberColumn("Тейк", format="%.4f"),
                "SL": st.column_config.NumberColumn("Стоп", format="%.4f"),
            }
        )

        if st.button("🔄 Обновить принудительно"):
            st.cache_data.clear()
            st.rerun()

except Exception as e:
    st.error(f"⚠️ Системная ошибка: {e}")
