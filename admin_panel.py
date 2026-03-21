import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from streamlit_autorefresh import st_autorefresh

# Настройки страницы
st.set_page_config(
    page_title="Gemini Trade Admin",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Автообновление каждые 30 секунд
st_autorefresh(interval=30000, key="refresh")

# ID вашей таблицы
SHEET_ID = st.secrets.get("SHEET_ID", "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# Заголовок
st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

# CSS для улучшения внешнего вида
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px;
    }
    .signal-long {
        background-color: #00ff0022;
        border-left: 4px solid #00ff00;
        padding: 10px;
        margin: 5px 0;
    }
    .signal-short {
        background-color: #ff000022;
        border-left: 4px solid #ff0000;
        padding: 10px;
        margin: 5px 0;
    }
    .stButton button {
        background-color: #ff4444;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Функция загрузки данных
@st.cache_data(ttl=30)
def load_data():
    """Загрузка данных из Google Sheets"""
    try:
        df = pd.read_csv(CSV_URL)
        
        if len(df.columns) >= 7:
            df.columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Confidence'] = pd.to_numeric(df['Confidence'], errors='coerce').fillna(0)
            df['Entry'] = pd.to_numeric(df['Entry'], errors='coerce')
            df['SL'] = pd.to_numeric(df['SL'], errors='coerce')
            df['TP'] = pd.to_numeric(df['TP'], errors='coerce')
            
            # Расчет потенциальной прибыли
            df['Potential_Profit'] = abs(df['TP'] - df['Entry']) / df['Entry'] * 100
            df['Potential_Risk'] = abs(df['Entry'] - df['SL']) / df['Entry'] * 100
            df['Risk_Reward'] = df['Potential_Profit'] / df['Potential_Risk']
            
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

# Боковая панель с фильтрами
with st.sidebar:
    st.header("🔍 Фильтры")
    
    # Кнопка очистки истории
    st.markdown("---")
    st.subheader("🗑️ Управление данными")
    
    if st.button("🧹 Очистить историю сделок", type="secondary", use_container_width=True):
        st.session_state['confirm_clear'] = True
    
    if st.session_state.get('confirm_clear', False):
        st.warning("⚠️ Вы уверены? Это действие необратимо!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Да, очистить", use_container_width=True):
                try:
                    import gspread
                    from google.oauth2.service_account import Credentials
                    import json
                    
                    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                    creds = Credentials.from_service_account_file('service_account.json', scopes=scope)
                    gc = gspread.authorize(creds)
                    sh = gc.open_by_key(SHEET_ID)
                    worksheet = sh.get_worksheet(0)
                    
                    # Очищаем все строки кроме заголовков
                    worksheet.clear()
                    headers = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
                    worksheet.append_row(headers)
                    
                    st.success("✅ История очищена!")
                    st.session_state['confirm_clear'] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка очистки: {e}")
        with col2:
            if st.button("❌ Нет, отмена", use_container_width=True):
                st.session_state['confirm_clear'] = False
                st.rerun()
    
    st.markdown("---")
    
    # Фильтр по символу
    df = load_data()
    if not df.empty:
        symbols = ['Все'] + sorted(df['Symbol'].unique().tolist())
        selected_symbol = st.selectbox("📊 Валютная пара", symbols)
        
        # Фильтр по направлению
        directions = ['Все', 'LONG', 'SHORT']
        selected_direction = st.selectbox("🎯 Направление", directions)
        
        # Фильтр по дате
        st.subheader("📅 Период")
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("С", df['Date'].min().date() if not df.empty else datetime.now())
        with col2:
            date_to = st.date_input("По", df['Date'].max().date() if not df.empty else datetime.now())
        
        # Фильтр по уверенности
        min_confidence = st.slider("📈 Минимальная уверенность", 0, 100, 50)

# Загрузка данных
df = load_data()

if not df.empty:
    # Применяем фильтры
    filtered_df = df.copy()
    
    if selected_symbol != 'Все':
        filtered_df = filtered_df[filtered_df['Symbol'] == selected_symbol]
    
    if selected_direction != 'Все':
        filtered_df = filtered_df[filtered_df['Direction'] == selected_direction]
    
    filtered_df = filtered_df[
        (filtered_df['Date'].dt.date >= date_from) & 
        (filtered_df['Date'].dt.date <= date_to)
    ]
    
    filtered_df = filtered_df[filtered_df['Confidence'] >= min_confidence]
    
    # Основные метрики
    st.subheader("📊 Ключевые показатели")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_signals = len(filtered_df)
        st.metric("Всего сигналов", total_signals, delta=None)
    
    with col2:
        avg_confidence = filtered_df['Confidence'].mean()
        st.metric("Средняя уверенность", f"{avg_confidence:.1f}%", 
                  delta=f"{avg_confidence - df['Confidence'].mean():+.1f}%" if not df.empty else None)
    
    with col3:
        long_count = len(filtered_df[filtered_df['Direction'] == 'LONG'])
        long_pct = (long_count / total_signals * 100) if total_signals > 0 else 0
        st.metric("LONG сигналы", f"{long_count} ({long_pct:.0f}%)")
    
    with col4:
        short_count = len(filtered_df[filtered_df['Direction'] == 'SHORT'])
        short_pct = (short_count / total_signals * 100) if total_signals > 0 else 0
        st.metric("SHORT сигналы", f"{short_count} ({short_pct:.0f}%)")
    
    st.markdown("---")
    
    # Графики
    tab1, tab2, tab3 = st.tabs(["📈 Динамика", "🎯 Аналитика", "📋 История"])
    
    with tab1:
        st.subheader("Динамика точности прогнозов")
        
        # Группировка по дате
        daily_stats = filtered_df.groupby(filtered_df['Date'].dt.date).agg({
            'Confidence': ['mean', 'count'],
            'Risk_Reward': 'mean'
        }).reset_index()
        daily_stats.columns = ['Date', 'Avg_Confidence', 'Signal_Count', 'Avg_RR']
        
        # Создаем график с двумя осями
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_stats['Date'],
            y=daily_stats['Avg_Confidence'],
            mode='lines+markers',
            name='Средняя уверенность',
            line=dict(color='#00ff00', width=3),
            marker=dict(size=8, symbol='circle')
        ))
        
        fig.add_trace(go.Bar(
            x=daily_stats['Date'],
            y=daily_stats['Signal_Count'],
            name='Количество сигналов',
            yaxis='y2',
            marker=dict(color='rgba(0, 100, 255, 0.3)', line=dict(color='blue', width=1))
        ))
        
        fig.update_layout(
            title="Динамика качества сигналов",
            xaxis_title="Дата",
            yaxis_title="Средняя уверенность (%)",
            yaxis2=dict(
                title="Количество сигналов",
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=500,
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение по символам
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Топ-10 инструментов")
            symbol_counts = filtered_df['Symbol'].value_counts().head(10)
            fig_pie = px.pie(
                values=symbol_counts.values,
                names=symbol_counts.index,
                title="Распределение сигналов",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("Соотношение LONG/SHORT")
            direction_stats = filtered_df.groupby(['Symbol', 'Direction']).size().unstack(fill_value=0)
            fig_bar = px.bar(
                direction_stats,
                title="LONG vs SHORT по инструментам",
                barmode='group',
                color_discrete_map={'LONG': '#00ff00', 'SHORT': '#ff4444'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with tab2:
        st.subheader("Аналитика сигналов")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Распределение уверенности
            fig_hist = px.histogram(
                filtered_df, 
                x='Confidence',
                nbins=20,
                title="Распределение уверенности сигналов",
                color_discrete_sequence=['#667eea']
            )
            fig_hist.update_layout(bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Box plot по символам
            fig_box = px.box(
                filtered_df,
                x='Symbol',
                y='Confidence',
                title="Разброс уверенности по инструментам",
                color='Symbol'
            )
            st.plotly_chart(fig_box, use_container_width=True)
        
        # Risk/Reward анализ
        st.subheader("Risk/Reward анализ")
        rr_stats = filtered_df.groupby('Symbol').agg({
            'Risk_Reward': ['mean', 'min', 'max', 'count']
        }).round(2)
        rr_stats.columns = ['Средний RR', 'Min RR', 'Max RR', 'Кол-во']
        st.dataframe(rr_stats, use_container_width=True)
    
    with tab3:
        st.subheader("История сделок")
        
        # Поиск
        search = st.text_input("🔍 Поиск по символу", placeholder="Например: SBER")
        if search:
            display_df = filtered_df[filtered_df['Symbol'].str.contains(search.upper(), na=False)]
        else:
            display_df = filtered_df
        
        # Сортировка
        sort_col = st.selectbox("Сортировать по", ['Date', 'Confidence', 'Symbol', 'Risk_Reward'])
        display_df = display_df.sort_values(sort_col, ascending=False)
        
        # Стилизация таблицы
        def style_dataframe(val):
            if 'Direction' in str(val):
                if val == 'LONG':
                    return 'background-color: #00ff0022; color: #00ff00'
                elif val == 'SHORT':
                    return 'background-color: #ff000022; color: #ff4444'
            return ''
        
        styled_df = display_df.style.applymap(style_dataframe, subset=['Direction'])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=500,
            column_config={
                "Date": st.column_config.DatetimeColumn("Дата и время", format="DD.MM.YYYY HH:mm"),
                "Symbol": "Инструмент",
                "Direction": "Направление",
                "Entry": st.column_config.NumberColumn("Вход", format="%.5f"),
                "SL": st.column_config.NumberColumn("Stop Loss", format="%.5f"),
                "TP": st.column_config.NumberColumn("Take Profit", format="%.5f"),
                "Confidence": st.column_config.NumberColumn("Уверенность", format="%.0f%%"),
                "Potential_Profit": st.column_config.NumberColumn("Потенциал %", format="%.2f%%"),
                "Potential_Risk": st.column_config.NumberColumn("Риск %", format="%.2f%%"),
                "Risk_Reward": st.column_config.NumberColumn("Risk/Reward", format="%.2f")
            }
        )
        
        # Экспорт
        col1, col2, col3 = st.columns(3)
        with col1:
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Скачать CSV",
                data=csv,
                file_name=f"trade_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            if st.button("🔄 Обновить данные", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        
        with col3:
            st.info(f"📊 Отображается {len(display_df)} из {len(filtered_df)} сигналов")

else:
    st.info("📭 Нет данных для отображения")
    
    st.markdown("""
    ### 🚀 Начало работы:
    1. **Настройте Google Sheets:**
       - Создайте таблицу и откройте доступ
       - Добавьте email сервисного аккаунта
       - Вставьте ID таблицы в .env
    
    2. **Запустите бота:**
       ```bash
       python main.py
