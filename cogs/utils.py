import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from database.db import Database

class Utils(commands.Cog):
    """Модуль вспомогательных команд"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Инициализация базы данных при запуске"""
        await Database.init()
    
    @app_commands.command(name="помощь", description="Показать список всех команд бота")
    async def help_command(self, interaction: discord.Interaction):
        """Показывает список всех доступных команд"""
        
        embed = discord.Embed(
            title="📚 Помощь по командам бота",
            description="Список всех доступных команд для управления семьёй",
            color=discord.Color.blue()
        )
        
        # Заявки
        embed.add_field(
            name="📝 Заявки",
            value=(
                "`/заявка` - Подать заявку на вступление в семью\n"
            ),
            inline=False
        )
        
        # Предупреждения
        embed.add_field(
            name="⚠️ Предупреждения (Варны)",
            value=(
                "`/warn` - Выдать предупреждение участнику 🔒\n"
                "`/warns` - Посмотреть предупреждения\n"
                "`/unwarn` - Снять предупреждение 🔒\n"
                "`/clearwarns` - Очистить все предупреждения 🔒\n"
            ),
            inline=False
        )
        
        # Отчёты
        embed.add_field(
            name="📋 Отчёты о мероприятиях",
            value=(
                "`/отчёт` - Отправить отчёт о мероприятии\n"
                "`/мои_отчёты` - Посмотреть свои отчёты\n"
                "`/топ_организаторов` - Топ организаторов\n"
            ),
            inline=False
        )
        
        # Участники
        embed.add_field(
            name="👥 Управление участниками",
            value=(
                "`/профиль` - Посмотреть профиль участника\n"
                "`/список_семьи` - Список всех участников\n"
                "`/исключить` - Исключить участника 🔒\n"
                "`/установить_ник` - Установить игровой ник 🔒\n"
            ),
            inline=False
        )
        
        # Прочее
        embed.add_field(
            name="🛠️ Прочее",
            value=(
                "`/помощь` - Показать это сообщение\n"
                "`/инфо` - Информация о боте\n"
                "`/пинг` - Проверить задержку бота\n"
            ),
            inline=False
        )
        
        embed.set_footer(text="🔒 - Требуются права администратора/модератора")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="инфо", description="Информация о боте")
    async def info_command(self, interaction: discord.Interaction):
        """Показывает информацию о боте"""
        
        embed = discord.Embed(
            title="ℹ️ Информация о боте",
            description="Бот для управления семьёй на GTA 5 RP сервере",
            color=discord.Color.blue()
        )
        
        # Статистика бота
        guild_count = len(self.bot.guilds)
        total_members = sum(guild.member_count for guild in self.bot.guilds)
        
        embed.add_field(
            name="📊 Статистика",
            value=f"Серверов: **{guild_count}**\n"
                  f"Пользователей: **{total_members}**\n"
                  f"Команд: **15+**",
            inline=True
        )
        
        # Версия и технологии
        embed.add_field(
            name="🛠️ Технологии",
            value=f"Discord.py {discord.__version__}\n"
                  f"Python 3.10+\n"
                  f"SQLite",
            inline=True
        )
        
        # Возможности
        embed.add_field(
            name="✨ Возможности",
            value=(
                "• Приём заявок на вступление\n"
                "• Система предупреждений\n"
                "• Отчёты о мероприятиях\n"
                "• Управление участниками\n"
                "• База данных\n"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Бот запущен: {self.bot.user.name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="пинг", description="Проверить задержку бота")
    async def ping_command(self, interaction: discord.Interaction):
        """Показывает задержку бота"""
        
        # API Latency
        api_latency = round(self.bot.latency * 1000)
        
        embed = discord.Embed(
            title="🏓 Понг!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="⏱️ Задержка API",
            value=f"`{api_latency}ms`",
            inline=True
        )
        
        # Определяем качество связи
        if api_latency < 100:
            status = "🟢 Отлично"
        elif api_latency < 200:
            status = "🟡 Хорошо"
        elif api_latency < 300:
            status = "🟠 Средне"
        else:
            status = "🔴 Плохо"
        
        embed.add_field(
            name="📶 Качество связи",
            value=status,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="статистика", description="Общая статистика семьи")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stats_command(self, interaction: discord.Interaction):
        """Показывает общую статистику семьи"""
        
        await interaction.response.defer()
        
        # Получаем данные из БД
        import aiosqlite
        from config import DATABASE_PATH, FAMILY_ROLE_ID

        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Количество участников
            family_role = interaction.guild.get_role(FAMILY_ROLE_ID)
            member_count = len([m for m in interaction.guild.members if family_role in m.roles]) if family_role else 0
            
            # Всего предупреждений
            cursor = await db.execute('SELECT COUNT(*) FROM warns')
            total_warns = (await cursor.fetchone())[0]
            
            # Всего отчётов
            cursor = await db.execute('SELECT COUNT(*) FROM reports')
            total_reports = (await cursor.fetchone())[0]
            
            # Всего участников мероприятий
            cursor = await db.execute('SELECT SUM(participants) FROM reports')
            result = await cursor.fetchone()
            total_participants = result[0] if result[0] else 0
            
            # Активных участников (те, кто отправлял отчёты)
            cursor = await db.execute('SELECT COUNT(DISTINCT user_id) FROM reports')
            active_members = (await cursor.fetchone())[0]
        
        embed = discord.Embed(
            title="📊 Статистика семьи",
            description=f"Общая статистика семьи на сервере **{interaction.guild.name}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👥 Участники",
            value=f"Всего: **{member_count}**\n"
                  f"Активных: **{active_members}**",
            inline=True
        )
        
        embed.add_field(
            name="📋 Мероприятия",
            value=f"Отчётов: **{total_reports}**\n"
                  f"Участников: **{total_participants}**",
            inline=True
        )
        
        embed.add_field(
            name="⚠️ Дисциплина",
            value=f"Предупреждений: **{total_warns}**",
            inline=True
        )
        
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utils(bot))
