import discord
from discord.ext import commands
import asyncio
import os
from config import TOKEN

# Настройка intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Создание бота
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'╔══════════════════════════════════════╗')
    print(f'║  Бот успешно запущен!                ║')
    print(f'║  Имя: {bot.user.name:<27}║')
    print(f'║  ID: {bot.user.id:<28}               ║')
    print(f'╚══════════════════════════════════════╝')
    
    # Синхронизация slash-команд
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} команд(ы)')
    except Exception as e:
        print(f'❌ Ошибка синхронизации команд: {e}')
    
    # Установка статуса бота
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="за семьёй | /помощь"
        )
    )

@bot.event
async def on_command_error(ctx, error):
    """Обработка ошибок команд"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас недостаточно прав для выполнения этой команды!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Отсутствует обязательный аргумент: {error.param}")
    else:
        print(f'Ошибка: {error}')

async def load_extensions():
    """Загрузка всех модулей (cogs)"""
    extensions = [
        'cogs.applications',
        'cogs.reports',
        'cogs.warns',
        'cogs.members',
        'cogs.utils'
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            print(f'✅ Загружен модуль: {extension}')
        except Exception as e:
            print(f'❌ Ошибка загрузки {extension}: {e}')

async def main():
    """Главная функция запуска"""
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 Бот остановлен')
    except Exception as e:
        print(f'❌ Критическая ошибка: {e}')
