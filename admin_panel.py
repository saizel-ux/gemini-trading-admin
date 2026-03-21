import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials
import json
import os

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

# CSS для улучшения внешнего вида
st.markdown("""
<style>
    /* Главный контейнер */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* Карточки метрик */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .metric-delta {
        font-size: 0.9rem;
        margin-top: 5px;
    }
    
    /* Стили для сигналов */
    .signal-card {
        background: #1e1e1e;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid;
    }
    .signal-long {
        border-left-color: #00ff00;
        background: linear-gradient(90deg, rgba(0,255,0,0.1) 0%, rgba(0,255,0,0) 100%);
    }
    .signal-short {
        border-left-color: #ff4444;
        background: linear-gradient(90deg, rgba(255,68,68,0.1) 0%, rgba(255,68,68,0) 100%);
    }
    .signal-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .signal-details {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .signal-detail {
        background: rgba(255,255,255,0.1);
        padding: 5px 10px;
        border-radius: 5px;
    }
    
    /* Кнопки */
    .stButton button {
        background-color: #ff4444;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        transition: all 0.3s;
    }
    .stButton button:hover {
        background-color: #ff6666;
        transform: scale(1.02);
    }
    
    /* Таблица */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Сайдбар */
    .sidebar-content {
        padding: 10px;
    }
    
    /* Загрузка */
    .loading-spinner {
        text-align: center;
        padding: 50px;
    }
</style>
""", unsafe_allow_html=True)

# Функция для подключения к Google Sheets
def get_google_sheets_client():
    """Получение клиента Google Sheets"""
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(base_path, 'service_account.json')
        
        if not os.path.exists(key_path):
            st.error("❌ Файл service_account.json не найден!")
            return None
        
        scope = ["https://spreadsheets.google.com/feeds", 
                 "https://www.googleapis.com/auth/drive"]
        
        creds = Credentials.from_service_account_file(key_path, scopes=scope)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Ошибка подключения: {e}")
        return None

# Функция очистки истории
def clear_history():
    """Очистка истории сделок"""
    try:
        gc = get_google_sheets_client()
        if not gc:
            return False
        
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Очищаем все строки кроме заголовков
        worksheet.clear()
        headers = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        worksheet.append_row(headers)
        
        return True
    except Exception as e:
        st.error(f"Ошибка очистки: {e}")
        return False

# Функция загрузки данных
@st.cache_data(ttl=30, show_spinner=False)
def load_data():
    """Загрузка данных из Google Sheets"""
    try:
        with st.spinner("Загрузка данных..."):
            df = pd.read_csv(CSV_URL)
            
            # Переименовываем колонки
            if len(df.columns) >= 7:
                df.columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
            elif len(df.columns) == 6:
                df.columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP']
                df['Confidence'] = 0
            
            if not df.empty:
                # Преобразование типов
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df['Confidence'] = pd.to_numeric(df['Confidence'], errors='coerce').fillna(0)
                df['Entry'] = pd.to_numeric(df['Entry'], errors='coerce')
                df['SL'] = pd.to_numeric(df['SL'], errors='coerce')
                df['TP'] = pd.to_numeric(df['TP'], errors='coerce')
                
                # Удаляем строки с NaN датами
                df = df.dropna(subset=['Date'])
                
                # Расчет дополнительных метрик
                df['Potential_Profit'] = abs(df['TP'] - df['Entry']) / df['Entry'] * 100
                df['Potential_Risk'] = abs(df['Entry'] - df['SL']) / df['Entry'] * 100
                df['Risk_Reward'] = df['Potential_Profit'] / df['Potential_Risk']
                
                # Заменяем inf на 0
                df['Risk_Reward'] = df['Risk_Reward'].replace([np.inf, -np.inf], 0).fillna(0)
                
                # Добавляем статус (условно)
                df['Status'] = 'Активен'
                
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

# Инициализация состояния сессии
if 'confirm_clear' not in st.session_state:
    st.session_state['confirm_clear'] = False
if 'show_filters' not in st.session_state:
    st.session_state['show_filters'] = True

# Заголовок
st.markdown("""
<div class="main-header">
    <h1>📈 Gemini Trade Bot</h1>
    <p>Аналитическая панель в реальном времени</p>
</div>
""", unsafe_allow_html=True)

# Загрузка данных
df = load_data()

if not df.empty:
    # ==================== БОКОВАЯ ПАНЕЛЬ ====================
    with st.sidebar:
        st.header("🔍 Управление")
        
        # Кнопка очистки истории
        st.markdown("---")
        st.subheader("🗑️ Управление данными")
        
        if st.button("🧹 Очистить историю", type="secondary", use_container_width=True):
            st.session_state['confirm_clear'] = True
        
        if st.session_state['confirm_clear']:
            st.warning("⚠️ Вы уверены? Это действие необратимо!")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Да, очистить", use_container_width=True):
                    if clear_history():
                        st.success("✅ История очищена!")
                        st.session_state['confirm_clear'] = False
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Ошибка очистки")
            with col2:
                if st.button("❌ Нет, отмена", use_container_width=True):
                    st.session_state['confirm_clear'] = False
                    st.rerun()
        
        st.markdown("---")
        
        # Фильтры
        st.subheader("📊 Фильтры")
        
        # Фильтр по символу
        symbols = ['Все'] + sorted(df['Symbol'].unique().tolist())
        selected_symbol = st.selectbox("Валютная пара", symbols, key="symbol_filter")
        
        # Фильтр по направлению
        directions = ['Все', 'LONG', 'SHORT']
        selected_direction = st.selectbox("Направление", directions, key="direction_filter")
        
        # Фильтр по дате
        st.subheader("📅 Период")
        col1, col2 = st.columns(2)
        with col1:
            min_date = df['Date'].min().date() if not df.empty else datetime.now().date()
            date_from = st.date_input("С", min_date, key="date_from")
        with col2:
            max_date = df['Date'].max().date() if not df.empty else datetime.now().date()
            date_to = st.date_input("По", max_date, key="date_to")
        
        # Фильтр по уверенности
        st.subheader("📈 Уверенность")
        min_confidence = st.slider("Минимальная уверенность (%)", 0, 100, 50, key="confidence_filter")
        
        # Фильтр по Risk/Reward
        st.subheader("⚖️ Risk/Reward")
        min_rr = st.slider("Минимальный RR", 0.0, 5.0, 1.0, 0.1, key="rr_filter")
        
        # Количество записей для отображения
        st.subheader("📄 Отображение")
        n_records = st.selectbox("Количество записей", [50, 100, 200, 500, 1000], index=1, key="records_filter")
        
        st.markdown("---")
        st.caption("🔄 Данные обновляются каждые 30 секунд")

    # ==================== ПРИМЕНЕНИЕ ФИЛЬТРОВ ====================
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
    filtered_df = filtered_df[filtered_df['Risk_Reward'] >= min_rr]
    
    # Ограничиваем количество записей
    filtered_df = filtered_df.head(n_records)
    
    # ==================== КЛЮЧЕВЫЕ МЕТРИКИ ====================
    st.subheader("📊 Ключевые показатели")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_signals = len(filtered_df)
        st.metric(
            "Всего сигналов", 
            total_signals,
            delta=None,
            help="Общее количество торговых сигналов"
        )
    
    with col2:
        avg_confidence = filtered_df['Confidence'].mean()
        delta_conf = avg_confidence - df['Confidence'].mean() if not df.empty else 0
        st.metric(
            "Средняя уверенность", 
            f"{avg_confidence:.1f}%",
            delta=f"{delta_conf:+.1f}%",
            help="Средний уровень уверенности ИИ"
        )
    
    with col3:
        long_count = len(filtered_df[filtered_df['Direction'] == 'LONG'])
        long_pct = (long_count / total_signals * 100) if total_signals > 0 else 0
        st.metric(
            "LONG сигналы", 
            f"{long_count}",
            delta=f"{long_pct:.0f}%",
            help="Количество сигналов на покупку"
        )
    
    with col4:
        short_count = len(filtered_df[filtered_df['Direction'] == 'SHORT'])
        short_pct = (short_count / total_signals * 100) if total_signals > 0 else 0
        st.metric(
            "SHORT сигналы", 
            f"{short_count}",
            delta=f"{short_pct:.0f}%",
            help="Количество сигналов на продажу"
        )
    
    # Дополнительные метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_rr = filtered_df['Risk_Reward'].mean()
        st.metric(
            "Средний RR", 
            f"{avg_rr:.2f}",
            delta=None,
            help="Среднее соотношение риск/прибыль"
        )
    
    with col2:
        avg_profit = filtered_df['Potential_Profit'].mean()
        st.metric(
            "Средний потенциал", 
            f"{avg_profit:.2f}%",
            delta=None,
            help="Средний потенциальный профит"
        )
    
    with col3:
        best_symbol = filtered_df.groupby('Symbol')['Confidence'].mean().idxmax() if not filtered_df.empty else "N/A"
        st.metric(
            "Лучший инструмент", 
            best_symbol,
            delta=None,
            help="Инструмент с максимальной средней уверенностью"
        )
    
    with col4:
        today_signals = len(filtered_df[filtered_df['Date'].dt.date == datetime.now().date()])
        st.metric(
            "Сегодня", 
            today_signals,
            delta=None,
            help="Количество сигналов за сегодня"
        )
    
    st.markdown("---")
    
    # ==================== ГРАФИКИ ====================
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Динамика", "🎯 Аналитика", "📊 Статистика", "📋 История"])
    
    with tab1:
        st.subheader("Динамика точности прогнозов")
        
        # Группировка по дате
        daily_stats = filtered_df.groupby(filtered_df['Date'].dt.date).agg({
            'Confidence': ['mean', 'count', 'std'],
            'Risk_Reward': 'mean'
        }).reset_index()
        daily_stats.columns = ['Date', 'Avg_Confidence', 'Signal_Count', 'Conf_Std', 'Avg_RR']
        daily_stats['Conf_Std'] = daily_stats['Conf_Std'].fillna(0)
        
        # График с двумя осями
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_stats['Date'],
            y=daily_stats['Avg_Confidence'],
            mode='lines+markers',
            name='Средняя уверенность',
            line=dict(color='#00ff00', width=3),
            marker=dict(size=8, symbol='circle'),
            error_y=dict(
                type='data',
                array=daily_stats['Conf_Std'],
                visible=True,
                color='rgba(255,255,255,0.3)'
            )
        ))
        
        fig.add_trace(go.Bar(
            x=daily_stats['Date'],
            y=daily_stats['Signal_Count'],
            name='Количество сигналов',
            yaxis='y2',
            marker=dict(color='rgba(0, 100, 255, 0.5)', line=dict(color='#0066ff', width=1)),
            opacity=0.7
        ))
        
        fig.update_layout(
            title="Динамика качества сигналов",
            xaxis_title="Дата",
            yaxis_title="Средняя уверенность (%)",
            yaxis=dict(range=[0, 100]),
            yaxis2=dict(
                title="Количество сигналов",
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=500,
            template='plotly_dark',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Тренд уверенности
        if len(daily_stats) > 1:
            st.subheader("Тренд уверенности")
            trend = daily_stats['Avg_Confidence'].iloc[-1] - daily_stats['Avg_Confidence'].iloc[0]
            trend_color = "🟢" if trend > 0 else "🔴"
            st.info(f"{trend_color} Изменение уверенности за период: {trend:+.1f}%")
    
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
                color_discrete_sequence=['#667eea'],
                labels={'Confidence': 'Уверенность (%)', 'count': 'Количество сигналов'}
            )
            fig_hist.update_layout(
                showlegend=False,
                bargap=0.1,
                xaxis_range=[0, 100]
            )
            # Добавляем среднюю линию
            fig_hist.add_vline(x=avg_confidence, line_dash="dash", line_color="red", 
                               annotation_text=f"Средняя: {avg_confidence:.1f}%")
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Box plot по символам
            top_symbols = filtered_df['Symbol'].value_counts().head(10).index
            top_df = filtered_df[filtered_df['Symbol'].isin(top_symbols)]
            
            fig_box = px.box(
                top_df,
                x='Symbol',
                y='Confidence',
                title="Разброс уверенности по инструментам",
                color='Symbol',
                labels={'Confidence': 'Уверенность (%)', 'Symbol': 'Инструмент'}
            )
            fig_box.update_layout(showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)
        
        # Risk/Reward анализ
        st.subheader("⚖️ Risk/Reward анализ")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Распределение RR
            fig_rr = px.histogram(
                filtered_df,
                x='Risk_Reward',
                nbins=30,
                title="Распределение Risk/Reward",
                color_discrete_sequence=['#ffaa00'],
                labels={'Risk_Reward': 'Risk/Reward', 'count': 'Количество сигналов'}
            )
            fig_rr.add_vline(x=1, line_dash="dash", line_color="red", 
                             annotation_text="Минимальный RR (1:1)")
            fig_rr.add_vline(x=2, line_dash="dash", line_color="green",
                             annotation_text="Хороший RR (2:1)")
            st.plotly_chart(fig_rr, use_container_width=True)
        
        with col2:
            # Топ по RR
            rr_stats = filtered_df.groupby('Symbol').agg({
                'Risk_Reward': ['mean', 'count'],
                'Confidence': 'mean'
            }).round(2)
            rr_stats.columns = ['Средний RR', 'Кол-во', 'Средняя уверенность']
            rr_stats = rr_stats.sort_values('Средний RR', ascending=False).head(10)
            
            fig_rr_top = px.bar(
                rr_stats.reset_index(),
                x='Symbol',
                y='Средний RR',
                title="Топ-10 инструментов по RR",
                color='Средний RR',
                color_continuous_scale='Viridis',
                text='Средний RR'
            )
            fig_rr_top.update_traces(textposition='outside')
            st.plotly_chart(fig_rr_top, use_container_width=True)
    
    with tab3:
        st.subheader("Статистика по инструментам")
        
        # Сводная таблица
        summary = filtered_df.groupby('Symbol').agg({
            'Confidence': ['mean', 'count', 'std'],
            'Risk_Reward': 'mean',
            'Direction': lambda x: (x == 'LONG').sum()
        }).round(2)
        
        summary.columns = ['Средняя уверенность', 'Количество', 'Стд отклонение', 'Средний RR', 'LONG сигналы']
        summary['SHORT сигналы'] = summary['Количество'] - summary['LONG сигналы']
        summary['Процент LONG'] = (summary['LONG сигналы'] / summary['Количество'] * 100).round(1)
        
        # Сортировка по количеству
        summary = summary.sort_values('Количество', ascending=False)
        
        st.dataframe(
            summary,
            use_container_width=True,
            column_config={
                "Средняя уверенность": st.column_config.NumberColumn("Уверенность", format="%.1f%%"),
                "Количество": "Всего сигналов",
                "Стд отклонение": st.column_config.NumberColumn("Разброс", format="%.1f"),
                "Средний RR": st.column_config.NumberColumn("RR", format="%.2f"),
                "LONG сигналы": "LONG",
                "SHORT сигналы": "SHORT",
                "Процент LONG": st.column_config.NumberColumn("LONG %", format="%.1f%%")
            }
        )
        
        # Тепловая карта корреляции
        st.subheader("Корреляция метрик")
        corr_matrix = filtered_df[['Confidence', 'Risk_Reward', 'Potential_Profit', 'Potential_Risk']].corr()
        
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=True,
            title="Корреляционная матрица",
            color_continuous_scale='RdBu',
            aspect="auto"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    
    with tab4:
        st.subheader("История сделок")
        
        # Поиск
        search = st.text_input("🔍 Поиск по символу", placeholder="Например: SBER, EURUSD", key="search")
        
        if search:
            display_df = filtered_df[filtered_df['Symbol'].str.contains(search.upper(), na=False)]
        else:
            display_df = filtered_df
        
        # Сортировка
        col1, col2 = st.columns(2)
        with col1:
            sort_col = st.selectbox(
                "Сортировать по", 
                ['Date', 'Confidence', 'Symbol', 'Risk_Reward', 'Potential_Profit'],
                key="sort_col"
            )
        with col2:
            sort_order = st.selectbox("Порядок", ['По убыванию', 'По возрастанию'], key="sort_order")
        
        ascending = (sort_order == 'По возрастанию')
        display_df = display_df.sort_values(sort_col, ascending=ascending)
        
        # Стилизация таблицы
        def color_direction(val):
            if val == 'LONG':
                return 'background-color: #00ff0022; color: #00ff00; font-weight: bold'
            elif val == 'SHORT':
                return 'background-color: #ff000022; color: #ff4444; font-weight: bold'
            return ''
        
        def color_confidence(val):
            if val >= 80:
                return 'color: #00ff00; font-weight: bold'
            elif val >= 60:
                return 'color: #ffff00'
            elif val >= 40:
                return 'color: #ffaa00'
            else:
                return 'color: #ff4444'
        
        def color_rr(val):
            if val >= 2:
                return 'color: #00ff00; font-weight: bold'
            elif val >= 1:
                return 'color: #ffff00'
            else:
                return 'color: #ff4444'
        
        styled_df = display_df.style.applymap(color_direction, subset=['Direction'])
        styled_df = styled_df.applymap(color_confidence, subset=['Confidence'])
        styled_df = styled_df.applymap(color_rr, subset=['Risk_Reward'])
        
        # Форматирование чисел
        styled_df = styled_df.format({
            'Entry': '{:.5f}',
            'SL': '{:.5f}',
            'TP': '{:.5f}',
            'Confidence': '{:.0f}%',
            'Potential_Profit': '{:.2f}%',
            'Potential_Risk': '{:.2f}%',
            'Risk_Reward': '{:.2f}'
        })
        
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
                "Potential_Profit": st.column_config.NumberColumn("Потенциал", format="%.2f%%"),
                "Potential_Risk": st.column_config.NumberColumn("Риск", format="%.2f%%"),
                "Risk_Reward": st.column_config.NumberColumn("Risk/Reward", format="%.2f"),
                "Status": "Статус"
            }
        )
        
        # Экспорт данных
        st.markdown("---")
        st.subheader("💾 Экспорт данных")
        
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
    # Отображение при отсутствии данных
    st.info("📭 Нет данных для отображения")
    
    st.markdown("""
    ### 🚀 Начало работы:
    
    1. **Настройте Google Sheets:**
       - Создайте таблицу в Google Sheets
       - Добавьте заголовки: Date, Symbol, Direction, Entry, SL, TP, Confidence
       - Откройте доступ для сервисного аккаунта
       - Вставьте ID таблицы в .env файл
    
    2. **Запустите бота:**
       ```bash
       python main.py
