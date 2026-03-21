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

# ID вашей таблицы (из .env)
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

try:
    # Загрузка данных
    df = pd.read_csv(CSV_URL)
    
    if not df.empty:
        # Правильные имена колонок (как в вашей таблице)
        if len(df.columns) >= 7:
            df.columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        
        # Преобразование типов
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Confidence'] = pd.to_numeric(df['Confidence'], errors='coerce').fillna(0)
        df['Entry'] = pd.to_numeric(df['Entry'], errors='coerce')
        df['SL'] = pd.to_numeric(df['SL'], errors='coerce')
        df['TP'] = pd.to_numeric(df['TP'], errors='coerce')
        
        # Удаляем пустые строки
        df = df.dropna(subset=['Date', 'Symbol'])
        
        # Расчет Risk/Reward
        df['Potential_Profit'] = abs(df['TP'] - df['Entry']) / df['Entry'] * 100
        df['Potential_Risk'] = abs(df['Entry'] - df['SL']) / df['Entry'] * 100
        df['Risk_Reward'] = df['Potential_Profit'] / df['Potential_Risk']
        df['Risk_Reward'] = df['Risk_Reward'].replace([float('inf'), -float('inf')], 0).fillna(0)
        
        # Метрики
        st.subheader("📊 Ключевые показатели")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Всего сигналов", len(df))
        
        with col2:
            avg_conf = round(df['Confidence'].mean(), 1)
            st.metric("Средняя уверенность", f"{avg_conf}%")
        
        with col3:
            long_count = len(df[df['Direction'] == 'LONG'])
            st.metric("LONG сигналы", long_count)
        
        with col4:
            short_count = len(df[df['Direction'] == 'SHORT'])
            st.metric("SHORT сигналы", short_count)
        
        st.markdown("---")
        
        # График динамики уверенности
        st.subheader("📈 Динамика точности сигналов")
        
        # Группировка по дате
        daily_stats = df.groupby(df['Date'].dt.date).agg({
            'Confidence': 'mean',
            'Direction': 'count'
        }).reset_index()
        daily_stats.columns = ['Date', 'Avg_Confidence', 'Signal_Count']
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_stats['Date'],
            y=daily_stats['Avg_Confidence'],
            mode='lines+markers',
            name='Средняя уверенность',
            line=dict(color='#00ff00', width=3),
            marker=dict(size=6, color='#00ff00')
        ))
        
        fig.add_trace(go.Bar(
            x=daily_stats['Date'],
            y=daily_stats['Signal_Count'],
            name='Количество сигналов',
            yaxis='y2',
            marker=dict(color='rgba(102, 126, 234, 0.5)')
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
            height=500,
            template='plotly_dark',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение по символам
        st.subheader("🎯 Распределение сигналов")
        col1, col2 = st.columns(2)
        
        with col1:
            symbol_counts = df['Symbol'].value_counts().head(10)
            fig_pie = px.pie(
                values=symbol_counts.values,
                names=symbol_counts.index,
                title="Топ-10 инструментов",
                template='plotly_dark'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Распределение LONG/SHORT
            direction_counts = df['Direction'].value_counts()
            fig_bar = px.bar(
                x=direction_counts.index,
                y=direction_counts.values,
                title="LONG vs SHORT",
                color=direction_counts.index,
                color_discrete_map={'LONG': '#00ff00', 'SHORT': '#ff4444'},
                template='plotly_dark'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Risk/Reward анализ
        st.subheader("⚖️ Risk/Reward анализ")
        col1, col2 = st.columns(2)
        
        with col1:
            fig_rr = px.histogram(
                df,
                x='Risk_Reward',
                nbins=30,
                title="Распределение Risk/Reward",
                color_discrete_sequence=['#ffaa00'],
                template='plotly_dark'
            )
            fig_rr.add_vline(x=1, line_dash="dash", line_color="red", annotation_text="1:1")
            fig_rr.add_vline(x=2, line_dash="dash", line_color="green", annotation_text="2:1")
            st.plotly_chart(fig_rr, use_container_width=True)
        
        with col2:
            avg_rr_by_symbol = df.groupby('Symbol')['Risk_Reward'].mean().sort_values(ascending=False).head(10)
            fig_rr_bar = px.bar(
                x=avg_rr_by_symbol.index,
                y=avg_rr_by_symbol.values,
                title="Топ-10 по Risk/Reward",
                color=avg_rr_by_symbol.values,
                color_continuous_scale='Viridis',
                template='plotly_dark'
            )
            st.plotly_chart(fig_rr_bar, use_container_width=True)
        
        # Таблица данных
        st.subheader("📋 История сделок")
        
        # Стилизация таблицы
        def color_direction(val):
            if val == 'LONG':
                return 'background-color: #00ff0022; color: #00ff00'
            elif val == 'SHORT':
                return 'background-color: #ff000022; color: #ff4444'
            return ''
        
        styled_df = df.sort_values('Date', ascending=False).head(100).style
        styled_df = styled_df.applymap(color_direction, subset=['Direction'])
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
                "Risk_Reward": st.column_config.NumberColumn("Risk/Reward", format="%.2f")
            }
        )
        
        # Экспорт
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df.to_csv(index=False)
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
        
    else:
        st.info("📭 Данных пока нет. Отправьте первый сигнал боту!")
        
        st.markdown("""
        ### 🚀 Как начать:
        1. Запустите бота: `python main.py`
        2. Отправьте скриншот графика в Telegram
        3. Данные автоматически появятся здесь
        """)

except Exception as e:
    st.error(f"❌ Ошибка загрузки данных: {e}")
    st.info("💡 Убедитесь, что Google Таблица открыта для публичного доступа")

# Footer
st.markdown("---")
st.caption(f"🔄 Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("📊 Gemini Trade Bot v8.3 | Аналитика в реальном времени")
