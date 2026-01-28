import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from config import DATABASE_PATH

class Setup(commands.Cog):
    """Модуль настройки бота для каждого сервера"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Инициализация таблицы настроек"""
        await self.init_db()
    
    async def init_db(self):
        """Создать таблицу настроек серверов"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    applications_channel_id INTEGER,
                    reports_channel_id INTEGER,
                    logs_channel_id INTEGER,
                    family_role_name TEXT DEFAULT '🏠 Семья'
                )
            ''')
            await db.commit()
    
    @app_commands.command(name="настроить", description="Настроить бота для этого сервера")
    @app_commands.describe(
        applications_channel="Канал для заявок",
        reports_channel="Канал для отчётов",
        logs_channel="Канал для логов (необязательно)",
        family_role="Название роли семьи (по умолчанию: 🏠 Семья)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        applications_channel: discord.TextChannel,
        reports_channel: discord.TextChannel,
        logs_channel: discord.TextChannel = None,
        family_role: str = "🏠 Семья"
    ):
        """Настроить бота для сервера"""
        
        # Сохраняем настройки в БД
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO guild_settings 
                (guild_id, applications_channel_id, reports_channel_id, logs_channel_id, family_role_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                interaction.guild.id,
                applications_channel.id,
                reports_channel.id,
                logs_channel.id if logs_channel else None,
                family_role
            ))
            await db.commit()
        
        embed = discord.Embed(
            title="✅ Бот настроен!",
            description="Настройки успешно сохранены для этого сервера",
            color=discord.Color.green()
        )
        
        embed.add_field(name="📝 Канал заявок", value=applications_channel.mention, inline=False)
        embed.add_field(name="📋 Канал отчётов", value=reports_channel.mention, inline=False)
        if logs_channel:
            embed.add_field(name="📊 Канал логов", value=logs_channel.mention, inline=False)
        embed.add_field(name="🏠 Роль семьи", value=f"`{family_role}`", inline=False)
        
        embed.set_footer(text=f"Сервер: {interaction.guild.name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="настройки", description="Показать текущие настройки")
    async def settings(self, interaction: discord.Interaction):
        """Посмотреть настройки сервера"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT * FROM guild_settings WHERE guild_id = ?',
                (interaction.guild.id,)
            )
            settings = await cursor.fetchone()
        
        if not settings:
            embed = discord.Embed(
                title="⚠️ Бот не настроен",
                description=(
                    "Этот бот ещё не настроен на этом сервере!\n\n"
                    "**Администратор должен использовать:**\n"
                    "`/настроить` для первоначальной настройки"
                ),
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id, apps_ch, reports_ch, logs_ch, role = settings
        
        embed = discord.Embed(
            title="⚙️ Настройки бота",
            description=f"Настройки для сервера **{interaction.guild.name}**",
            color=discord.Color.blue()
        )
        
        apps_channel = interaction.guild.get_channel(apps_ch)
        reports_channel = interaction.guild.get_channel(reports_ch)
        logs_channel = interaction.guild.get_channel(logs_ch) if logs_ch else None
        
        embed.add_field(
            name="📝 Канал заявок",
            value=apps_channel.mention if apps_channel else "❌ Не найден",
            inline=False
        )
        embed.add_field(
            name="📋 Канал отчётов",
            value=reports_channel.mention if reports_channel else "❌ Не найден",
            inline=False
        )
        if logs_channel:
            embed.add_field(
                name="📊 Канал логов",
                value=logs_channel.mention,
                inline=False
            )
        embed.add_field(name="🏠 Роль семьи", value=f"`{role}`", inline=False)
        
        embed.set_footer(text=f"ID сервера: {interaction.guild.id}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Setup(bot))
