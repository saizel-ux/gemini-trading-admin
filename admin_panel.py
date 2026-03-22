import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(
    page_title="Gemini Trade Admin", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Автообновление каждые 30 секунд
st_autorefresh(interval=30000, key="refresh")

# ID таблицы и ссылка
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

st.title("📈 Gemini Trade Bot - Аналитическая панель")
st.markdown("---")

# 2. ФУНКЦИЯ ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS
def get_google_sheets_client():
    """Получение клиента Google Sheets для записи/очистки"""
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(base_path, 'service_account.json')
        
        if not os.path.exists(key_path):
            return None
        
        scope = ["https://spreadsheets.google.com/feeds", 
                 "https://www.googleapis.com/auth/drive"]
        
        creds = Credentials.from_service_account_file(key_path, scopes=scope)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Ошибка подключения: {e}")
        return None

# 3. ФУНКЦИЯ ОЧИСТКИ ИСТОРИИ
def clear_history():
    """Очистка истории сделок"""
    try:
        gc = get_google_sheets_client()
        if not gc:
            st.error("❌ Файл service_account.json не найден!")
            st.info("""
            **Как получить service_account.json:**
            1. Перейдите в Google Cloud Console
            2. Создайте сервисный аккаунт
            3. Скачайте JSON ключ
            4. Переименуйте в service_account.json
            5. Поместите в папку с приложением
            """)
            return False
        
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0)
        
        # Очищаем все строки кроме заголовков
        worksheet.clear()
        headers = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        worksheet.append_row(headers)
        
        return True
    except Exception as e:
        st.error(f"❌ Ошибка очистки: {e}")
        return False

# 4. ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
@st.cache_data(ttl=30)
def load_data(url):
    try:
        data = pd.read_csv(url)
        
        if data.empty:
            return pd.DataFrame()

        # Принудительно называем колонки
        expected_columns = ['Date', 'Symbol', 'Direction', 'Entry', 'SL', 'TP', 'Confidence']
        
        if len(data) < 1:
            return pd.DataFrame()

        # Маппинг колонок
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

# 5. ОСНОВНОЙ ИНТЕРФЕЙС
try:
    # Инициализация состояния для подтверждения очистки
    if 'confirm_clear' not in st.session_state:
        st.session_state['confirm_clear'] = False
    
    df = load_data(CSV_URL)
    
    if df.empty or len(df) == 0:
        st.info("ℹ️ **Таблица подключена, но данных о сделках пока нет.**")
        st.write("Как только вы отправите график боту в Telegram, здесь появится статистика.")
        
        # Показываем инструкцию
        with st.expander("📖 Инструкция по настройке"):
            st.markdown("""
            **1. Проверьте доступ к таблице:**
            - Откройте [Google Таблицу](https://docs.google.com/spreadsheets/d/1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I/edit)
            - Нажмите "Поделиться"
            - Выберите "Все, у кого есть ссылка" → "Читатель"
            
            **2. Проверьте структуру таблицы:**
            - Заголовки должны быть: Date, Symbol, Direction, Entry, SL, TP, Confidence
            
            **3. Отправьте тестовый сигнал:**
            - Сделайте скриншот графика
            - Отправьте боту @Geminiants_bot
            - Данные появятся здесь через 30 секунд
            """)
        
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
        df['Risk_Reward'] = df['Risk_Reward'].replace([float('inf'), -float('inf')], 0).fillna(0)

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
        fig.add_trace(go.Scatter(
            x=daily['Date'], 
            y=daily['Avg_Conf'], 
            name="Уверенность %", 
            line=dict(color='#00ff00', width=3),
            mode='lines+markers',
            marker=dict(size=8)
        ))
        fig.add_trace(go.Bar(
            x=daily['Date'], 
            y=daily['Count'], 
            name="Кол-во", 
            yaxis='y2', 
            opacity=0.5,
            marker=dict(color='rgba(102, 126, 234, 0.7)')
        ))
        
        fig.update_layout(
            template='plotly_dark',
            title="Динамика качества сигналов",
            xaxis_title="Дата",
            yaxis=dict(title="Уверенность (%)", range=[0, 101]),
            yaxis2=dict(title="Кол-во сигналов", overlaying='y', side='right'),
            hovermode='x unified', 
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Распределение по символам
        st.subheader("🎯 Распределение сигналов")
        col1, col2 = st.columns(2)
        
        with col1:
            symbol_counts = df['Symbol'].value_counts().head(10)
            if len(symbol_counts) > 0:
                fig_pie = px.pie(
                    values=symbol_counts.values,
                    names=symbol_counts.index,
                    title="Топ-10 инструментов",
                    template='plotly_dark'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Распределение LONG/SHORT
            direction_data = pd.DataFrame({
                'Направление': ['LONG', 'SHORT'],
                'Количество': [longs, shorts]
            })
            fig_bar = px.bar(
                direction_data,
                x='Направление',
                y='Количество',
                title="LONG vs SHORT",
                color='Направление',
                color_discrete_map={'LONG': '#00ff00', 'SHORT': '#ff4444'},
                template='plotly_dark'
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ИСТОРИЯ СДЕЛАК
        st.subheader("📋 Последние сигналы")
        
        def style_direction(val):
            v = str(val).upper()
            if 'LONG' in v: 
                return 'background-color: #00ff0022; color: #00ff00; font-weight: bold'
            if 'SHORT' in v: 
                return 'background-color: #ff000022; color: #ff4444; font-weight: bold'
            return ''

        display_df = df.sort_values('Date', ascending=False).head(50)
        
        styled_df = display_df.style.applymap(style_direction, subset=['Direction'])
        styled_df = styled_df.format({
            'Entry': '{:.5f}',
            'SL': '{:.5f}',
            'TP': '{:.5f}',
            'Confidence': '{:.0f}%',
            'Risk_Reward': '{:.2f}'
        })
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=450,
            column_config={
                "Date": st.column_config.DatetimeColumn("Время", format="DD.MM.YYYY HH:mm"),
                "Symbol": "Инструмент",
                "Direction": "Направление",
                "Entry": st.column_config.NumberColumn("Вход", format="%.5f"),
                "SL": st.column_config.NumberColumn("Стоп", format="%.5f"),
                "TP": st.column_config.NumberColumn("Тейк", format="%.5f"),
                "Confidence": st.column_config.NumberColumn("Уверенность", format="%.0f%%"),
                "Risk_Reward": st.column_config.NumberColumn("R/R", format="%.2f")
            }
        )
        
        # КНОПКИ УПРАВЛЕНИЯ
        st.markdown("---")
        st.subheader("⚙️ Управление данными")
        
        col1, col2, col3 = st.columns(3)
        
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
        
        with col3:
            if st.button("🗑️ Очистить историю", type="secondary", use_container_width=True):
                st.session_state['confirm_clear'] = True
        
        # Подтверждение очистки
        if st.session_state['confirm_clear']:
            st.warning("⚠️ **Вы уверены?** Это действие необратимо и удалит все сделки из таблицы!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Да, очистить всё", use_container_width=True):
                    with st.spinner("Очистка истории..."):
                        if clear_history():
                            st.success("✅ История успешно очищена!")
                            st.session_state['confirm_clear'] = False
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Ошибка при очистке. Проверьте service_account.json")
            with col2:
                if st.button("❌ Нет, отмена", use_container_width=True):
                    st.session_state['confirm_clear'] = False
                    st.rerun()

except Exception as e:
    st.error(f"⚠️ Системная ошибка: {e}")
    st.info("""
    ### 🔧 Решение:
    1. Убедитесь что Google Таблица открыта для публичного доступа
    2. Проверьте ID таблицы
    3. Убедитесь что в таблице есть заголовки: Date, Symbol, Direction, Entry, SL, TP, Confidence
    4. Перезапустите админ-панель
    """)

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.caption(f"🔄 Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with col2:
    st.caption("📊 Gemini Trade Bot v8.4")

with col3:
    st.caption("⚡ Аналитика в реальном времени")
