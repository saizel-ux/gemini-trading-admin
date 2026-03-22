import gspread
from google.oauth2.service_account import Credentials
import os
import json

# Настройки (те же, что в твоем проекте)
SERVICE_ACCOUNT_FILE = 'service_account.json'
# Твой ID таблицы из .env или напрямую
SHEET_ID = "1dxBmcTGmH9kHMOlwM2o1b_3LZ18ofXHA9Lqo4913R6I"

def check_system():
    print("🔍 Начинаю проверку системы...\n")

    # 1. Проверка физического наличия файла
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ ОШИБКА: Файл '{SERVICE_ACCOUNT_FILE}' не найден в папке с ботом!")
        return
    print(f"✅ Файл '{SERVICE_ACCOUNT_FILE}' обнаружен.")

    # 2. Проверка содержимого JSON
    try:
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            data = json.load(f)
            client_email = data.get("client_email")
            if not client_email:
                print("❌ ОШИБКА: В JSON-файле не найден 'client_email'. Это не тот файл!")
                return
            print(f"✅ Файл корректен. Почта сервисного аккаунта:\n   👉 {client_email}")
            print("\n⚠️ ВНИМАНИЕ: Проверь, что ТЫ ДОБАВИЛ ЭТУ ПОЧТУ в настройки доступа таблицы (кнопка 'Поделиться')!")
    except Exception as e:
        print(f"❌ ОШИБКА: Не удалось прочитать JSON: {e}")
        return

    # 3. Попытка авторизации и подключения к таблице
    print("\n🚀 Пробую подключиться к Google Sheets...")
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        gc = gspread.authorize(creds)
        
        # Пробуем открыть таблицу
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.get_worksheet(0)
        
        print(f"✅ УСПЕХ! Таблица '{sh.title}' открыта.")
        print(f"📊 Всего строк в таблице: {ws.row_count}")
        print("\n🔥 Система полностью готова к работе!")
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ ОШИБКА: Таблица с ID {SHEET_ID} не найдена. Проверь ID или доступ по почте.")
    except Exception as e:
        print(f"❌ ОШИБКА подключения: {e}")

if __name__ == "__main__":
    check_system()
