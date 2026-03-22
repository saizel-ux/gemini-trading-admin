import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(
    page_title="Gemini Trade Admin", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Автообновление каждые 30 секунд
st_autorefresh(interval=30000, key="refresh")

# Ссылки и ID
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"
CSV_URL = f"https://docs.google.com/spreadsheets/d/e/2PACX-1vQ8ILWnyjNQrRGXwsBg5twqLHemr9rorb4R_FZqDqnSCpmKyC5ufWazkhC-BA6pMa3uPKA8yKgvW6cn/pub?gid=0&single=true&output=csv"

# Функция для подключения к Google Sheets для записи/удаления
def get_sheets_client():
    key_path = 'service_account.json'
    if not os.path.exists(key_path):
        return None
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(key_path, scopes=scopes)
    return gspread.authorize(creds)

# Функция очистки
def clear_google_sheets():
    try:
        gc = get_sheets_client()
        if gc:
            sh = gc.open_by_key(SHEET_ID)
            ws = sh.get_worksheet(0)
            # Оставляем только заголовок (первую строку)
            ws.resize(rows=1) 
            ws.resize(rows=100) # Возвращаем запас строк
            st.success("✅ История успешно очищена в Google Sheets!")
            st.cache_data.clear()
        else:
            st.error("❌ Файл service_account.json не найден. Очистка невозможна.")
    except Exception as e:
        st.error(f"❌ Ошибка при очистке: {e}")

st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

# 2. ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
@st.cache_data(ttl=5)
def load_data(url):
    try:
        data = pd.read_csv(url)
        if data.empty or len(data.columns) < 7:
            return pd.DataFrame()

        expected_columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        data.columns = expected_columns[:len(data.columns)]
        
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
        return pd.DataFrame()

# 3. ОСНОВНОЙ ИНТЕРФЕЙС
try:
    df = load_data(CSV_URL)
    
    # Боковая панель управления
    with st.sidebar:
        st.header("⚙️ Управление")
        if st.button("🔄 Обновить данные"):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        st.warning("⚠️ Опасная зона")
        # Подтверждение очистки
        if st.button("🗑️ Очистить всю историю"):
            clear_google_sheets()
            st.rerun()

    if df.empty:
        st.info("ℹ️ **Данных о сделках пока нет.**")
    else:
        # Расчет метрик
        df['Potential_Profit'] = abs(df['TP'] - df['Entry']) / df['Entry'] * 100
        df['Potential_Risk'] = abs(df['Entry'] - df['SL']) / df['Entry'] * 100
        df['Risk_Reward'] = df.apply(lambda x: x['Potential_Profit'] / x['Potential_Risk'] if x['Potential_Risk'] > 0 else 0, axis=1)

        # МЕТРИКИ
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
        daily = df.groupby(df['Date'].dt.date).agg({'Confidence': 'mean', 'Symbol': 'count'}).reset_index()
        daily.columns = ['Date', 'Avg_Conf', 'Count']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily['Date'], y=daily['Avg_Conf'], name="Уверенность %", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Bar(x=daily['Date'], y=daily['Count'], name="Кол-во", yaxis='y2', opacity=0.3))
        fig.update_layout(template='plotly_dark', height=400, yaxis=dict(range=[0, 101]), yaxis2=dict(overlaying='y', side='right'))
        st.plotly_chart(fig, use_container_width=True)

        # ТАБЛИЦА
        st.subheader("📋 Последние сигналы")
        def style_direction(val):
            v = str(val).upper()
            if 'LONG' in v: return 'color: #00ff00; font-weight: bold'
            if 'SHORT' in v: return 'color: #ff4444; font-weight: bold'
            return ''

        display_df = df.sort_values('Date', ascending=False).head(50)
        try:
            styled_df = display_df.style.map(style_direction, subset=['Direction'])
        except:
            styled_df = display_df.style.applymap(style_direction, subset=['Direction'])
        
        st.dataframe(styled_df, use_container_width=True, height=450)

except Exception as e:
    st.error(f"⚠️ Системная ошибка: {e}")
