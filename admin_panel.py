
4. **Убедитесь что в таблице есть заголовки:**
- Date | Symbol | Direction | Entry | SL | TP | Confidence

5. **Перезапустите админ-панель**
""")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
st.caption(f"🔄 Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with col2:
st.caption("📊 Gemini Trade Bot v8.3")

with col3:
st.caption("⚡ Аналитика в реальном времени")
