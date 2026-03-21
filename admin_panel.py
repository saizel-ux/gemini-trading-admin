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

# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ ИЗ "ОПУБЛИКОВАТЬ В ИНТЕРНЕТЕ"
# Это решит ошибку 401 Unauthorized
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQoRp0BklBBdrhBpdmPvBsYltqfplATjad2l_oVWs_pGhSAHIzGExkdG9kPhS-jbWSotBO0WaQ21uX6/pub?gid=0&single=true&output=csv"

st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

# 2. ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
@st.cache_data(ttl=30)
def load_data(url):
    try:
        # Читаем данные напрямую по публичной ссылке
        data = pd.read_csv(url)
        
        # Переименовываем колонки для надежности
        expected_columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        if len(data.columns) >= 7:
            data.columns = expected_columns[:len(data.columns)]
        
        # Приведение типов
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        
        # Очистка колонки уверенности от знаков %
        if 'Confidence' in data.columns:
            data['Confidence'] = data['Confidence'].astype(str).str.replace('%', '').str.strip()
            data['Confidence'] = pd.to_numeric(data['Confidence'], errors='coerce').fillna(0)
            
        # Очистка цен
        for col in ['Entry', 'SL', 'TP']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # Убираем пустые строки
        data = data.dropna(subset=['Date', 'Symbol'])
        return data
    except Exception as e:
        st.error(f"❌ Ошибка доступа: {e}")
        st.info("💡 Убедитесь, что вы сделали: Файл -> Поделиться -> Опубликовать в интернете -> CSV")
        return pd.DataFrame()

# 3. ОСНОВНОЙ ИНТЕРФЕЙС
try:
    df = load_data(CSV_URL)
    
    if df.empty:
        st.warning("📭 Данные пока не загружены. Если вы уже опубликовали таблицу, подождите 1-2 минуты, пока Google обновит ссылку.")
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
        
        # Фильтр направлений (игнорируем регистр)
        longs = len(df[df['Direction'].astype(str).str.upper().str.contains('LONG', na=False)])
        shorts = len(df[df['Direction'].astype(str).str.upper().str.contains('SHORT', na=False)])
        
        m3.metric("🟢 LONG", longs)
        m4.metric("🔴 SHORT", shorts)
        
        st.markdown("---")

        # ГРАФИК
        st.subheader("📈 Динамика точности ИИ")
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
        
        # Авто-выбор метода стилизации в зависимости от версии Pandas
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
                "Symbol": "Монета",
                "Direction": "Тип",
                "Confidence": st.column_config.NumberColumn("Уверенность", format="%d%%"),
                "Risk_Reward": st.column_config.NumberColumn("R/R", format="%.2f"),
                "Entry": st.column_config.NumberColumn("Вход", format="%.4f"),
                "TP": st.column_config.NumberColumn("Тейк", format="%.4f"),
                "SL": st.column_config.NumberColumn("Стоп", format="%.4f"),
            }
        )

        if st.button("🔄 Обновить данные принудительно"):
            st.cache_data.clear()
            st.rerun()

except Exception as e:
    st.error(f"⚠️ Системная ошибка: {e}")
