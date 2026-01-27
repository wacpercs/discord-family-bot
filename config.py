import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
TOKEN = os.getenv('DISCORD_TOKEN')

# ID сервера
GUILD_ID = int(os.getenv('GUILD_ID', 0))

# ID каналов
APPLICATIONS_CHANNEL_ID = int(os.getenv('APPLICATIONS_CHANNEL_ID', 0))
REPORTS_CHANNEL_ID = int(os.getenv('REPORTS_CHANNEL_ID', 0))
LOGS_CHANNEL_ID = int(os.getenv('LOGS_CHANNEL_ID', 0))

# ID роли семьи
FAMILY_ROLE_ID = int(os.getenv('FAMILY_ROLE_ID', 0))

# Путь к базе данных
DATABASE_PATH = 'database/family.db'
