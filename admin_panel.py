import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
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
st.title("📈 Gemini Trade Bot - Административная панель")
st.markdown("---")

# Функция загрузки данных с кэшированием
@st.cache_data(ttl=30)
def load_data():
    """Загрузка данных из Google Sheets"""
    try:
        df = pd.read_csv(CSV_URL)
        
        # Переименовываем колонки для удобства
        if len(df.columns) >= 7:
            df.columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        
        # Преобразование типов
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Confidence'] = pd.to_numeric(df['Confidence'], errors='coerce').fillna(0)
            df['Entry'] = pd.to_numeric(df['Entry'], errors='coerce')
            df['SL'] = pd.to_numeric(df['SL'], errors='coerce')
            df['TP'] = pd.to_numeric(df['TP'], errors='coerce')
            
            # Добавляем колонку с результатом (условно)
            df['Status'] = 'Pending'
            
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

# Загружаем данные
df = load_data()

if not df.empty:
    # Фильтры в сайдбаре
    st.sidebar.header("🔍 Фильтры")
    
    # Фильтр по символу
    symbols = ['All'] + sorted(df['Symbol'].unique().tolist())
    selected_symbol = st.sidebar.selectbox("Валютная пара", symbols)
    
    # Фильтр по направлению
    directions = ['All', 'LONG', 'SHORT']
    selected_direction = st.sidebar.selectbox("Направление", directions)
    
    # Фильтр по дате
    col1, col2 = st.sidebar.columns(2)
    with col1:
        date_from = st.date_input("С", df['Date'].min().date() if not df.empty else datetime.now())
    with col2:
        date_to = st.date_input("По", df['Date'].max().date() if not df.empty else datetime.now())
    
    # Применяем фильтры
    filtered_df = df.copy()
    
    if selected_symbol != 'All':
        filtered_df = filtered_df[filtered_df['Symbol'] == selected_symbol]
    
    if selected_direction != 'All':
        filtered_df = filtered_df[filtered_df['Direction'] == selected_direction]
    
    filtered_df = filtered_df[
        (filtered_df['Date'].dt.date >= date_from) & 
        (filtered_df['Date'].dt.date <= date_to)
    ]
    
    # Метрики
    st.subheader("📊 Ключевые метрики")
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
        st.metric("LONG сигналы", long_count, 
                  delta=f"{(long_count/total_signals*100):.0f}%" if total_signals > 0 else "0%")
    
    with col4:
        short_count = len(filtered_df[filtered_df['Direction'] == 'SHORT'])
        st.metric("SHORT сигналы", short_count,
                  delta=f"{(short_count/total_signals*100):.0f}%" if total_signals > 0 else "0%")
    
    st.markdown("---")
    
    # График динамики уверенности
    st.subheader("📈 Динамика точности прогнозов")
    
    # Группировка по дате
    daily_stats = filtered_df.groupby(filtered_df['Date'].dt.date).agg({
        'Confidence': ['mean', 'count']
    }).reset_index()
    daily_stats.columns = ['Date', 'Avg_Confidence', 'Signal_Count']
    
    # Создаем график с двумя осями
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_stats['Date'],
        y=daily_stats['Avg_Confidence'],
        mode='lines+markers',
        name='Средняя уверенность',
        line=dict(color='#00ff00', width=2),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Bar(
        x=daily_stats['Date'],
        y=daily_stats['Signal_Count'],
        name='Количество сигналов',
        yaxis='y2',
        marker=dict(color='rgba(0, 100, 255, 0.3)')
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
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Распределение по символам
    st.subheader("🎯 Распределение сигналов по инструментам")
    col1, col2 = st.columns(2)
    
    with col1:
        symbol_counts = filtered_df['Symbol'].value_counts().head(10)
        fig_pie = px.pie(
            values=symbol_counts.values,
            names=symbol_counts.index,
            title="Топ-10 инструментов по количеству сигналов"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Сводка по направлениям
        direction_stats = filtered_df.groupby(['Symbol', 'Direction']).size().unstack(fill_value=0)
        fig_bar = px.bar(
            direction_stats,
            title="Распределение LONG/SHORT по инструментам",
            barmode='group'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Таблица с последними сигналами
    st.subheader("📋 Последние сигналы")
    
    # Добавляем цветовое выделение
    def color_direction(val):
        color = '#00ff00' if val == 'LONG' else '#ff4444'
        return f'color: {color}'
    
    def color_confidence(val):
        if val >= 80:
            return 'color: #00ff00; font-weight: bold'
        elif val >= 60:
            return 'color: #ffff00'
        else:
            return 'color: #ff4444'
    
    # Отображаем таблицу
    display_df = filtered_df.sort_values('Date', ascending=False).head(100)
    
    styled_df = display_df.style.applymap(
        color_direction, subset=['Direction']
    ).applymap(
        color_confidence, subset=['Confidence']
    )
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=400,
        column_config={
            "Date": st.column_config.DatetimeColumn("Дата и время", format="DD.MM.YYYY HH:mm"),
            "Symbol": "Инструмент",
            "Direction": "Направление",
            "Entry": st.column_config.NumberColumn("Вход", format="%.5f"),
            "SL": st.column_config.NumberColumn("Stop Loss", format="%.5f"),
            "TP": st.column_config.NumberColumn("Take Profit", format="%.5f"),
            "Confidence": st.column_config.NumberColumn("Уверенность", format="%.0f%%"),
            "Status": "Статус"
        }
    )
    
    # Экспорт данных
    st.markdown("---")
    st.subheader("💾 Экспорт данных")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Скачать CSV", use_container_width=True):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Подтвердить скачивание",
                data=csv,
                file_name=f"trade_signals_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        # Статистика по периодам
        today_stats = filtered_df[filtered_df['Date'].dt.date == datetime.now().date()]
        if not today_stats.empty:
            st.success(f"Сегодня: {len(today_stats)} сигналов, "
                      f"средняя уверенность: {today_stats['Confidence'].mean():.1f}%")
    
else:
    st.warning("📭 Нет данных для отображения. Отправьте первый сигнал через бота!")
    
    # Инструкция
    st.info("""
    **Как начать:**
    1. Убедитесь, что бот запущен
    2. Отправьте боту скриншот графика
    3. Данные автоматически появятся здесь
    4. Таблица должна быть открыта для публичного доступа
    """)

# Footer
st.markdown("---")
st.caption(f"🔄 Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
