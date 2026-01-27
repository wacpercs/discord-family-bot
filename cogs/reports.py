import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from database.db import Database
from config import REPORTS_CHANNEL_ID

class Reports(commands.Cog):
    """Модуль отчётов о внутриигровых мероприятиях"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="отчёт", description="Отправить отчёт о проведённом мероприятии")
    @app_commands.describe(
        event_type="Тип мероприятия (например: Рейд, Гонки, Вечеринка)",
        participants="Количество участников мероприятия",
        description="Подробное описание мероприятия",
        screenshot="Прикрепите скриншот мероприятия (необязательно)"
    )
    async def submit_report(
        self,
        interaction: discord.Interaction,
        event_type: str,
        participants: int,
        description: str,
        screenshot: discord.Attachment = None
    ):
        # Проверка количества участников
        if participants < 1:
            await interaction.response.send_message(
                "❌ Количество участников должно быть больше 0!",
                ephemeral=True
            )
            return
        
        # Создаём embed для отчёта
        embed = discord.Embed(
            title=f"📋 Отчёт о мероприятии: {event_type}",
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📊 Тип мероприятия", 
            value=f"`{event_type}`", 
            inline=True
        )
        embed.add_field(
            name="👥 Количество участников", 
            value=f"`{participants} чел.`", 
            inline=True
        )
        embed.add_field(
            name="👤 Организатор", 
            value=interaction.user.mention, 
            inline=False
        )
        
        embed.set_footer(
            text=f"Discord: {interaction.user.name} • ID: {interaction.user.id}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Если есть скриншот - добавляем его
        screenshot_url = None
        if screenshot:
            if screenshot.content_type and screenshot.content_type.startswith('image/'):
                embed.set_image(url=screenshot.url)
                screenshot_url = screenshot.url
            else:
                await interaction.response.send_message(
                    "⚠️ Прикреплённый файл не является изображением!",
                    ephemeral=True
                )
                return
        
        # Сохраняем отчёт в БД
        await Database.add_report(
            user_id=interaction.user.id,
            event_type=event_type,
            participants=participants,
            description=description,
            date=datetime.now().isoformat(),
            screenshot_url=screenshot_url
        )
        
        # Отправляем в канал отчётов
        channel = self.bot.get_channel(REPORTS_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message(
                "❌ Ошибка: канал для отчётов не найден. Обратитесь к администратору.",
                ephemeral=True
            )
            return
        
        # Добавляем реакции для оценки отчёта
        message = await channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("❤️")
        await message.add_reaction("🔥")
        
        await interaction.response.send_message(
            "✅ Отчёт успешно отправлен!\n"
            "📊 Ваш отчёт сохранён в базе данных.",
            ephemeral=True
        )
    
    @app_commands.command(name="мои_отчёты", description="Посмотреть свои отчёты о мероприятиях")
    @app_commands.describe(limit="Количество последних отчётов (по умолчанию 5)")
    async def my_reports(
        self,
        interaction: discord.Interaction,
        limit: int = 5
    ):
        # Ограничиваем лимит
        if limit > 10:
            limit = 10
        if limit < 1:
            limit = 1
        
        # Получаем отчёты из БД
        reports = await Database.get_user_reports(interaction.user.id, limit)
        
        embed = discord.Embed(
            title=f"📋 Мои отчёты о мероприятиях",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        if not reports:
            embed.description = "❌ У вас пока нет отчётов о мероприятиях"
        else:
            embed.description = f"Показано последних отчётов: **{len(reports)}**"
            
            for i, report in enumerate(reports, 1):
                report_id, user_id, event_type, participants, description, date, screenshot_url = report
                
                # Форматируем дату
                try:
                    date_obj = datetime.fromisoformat(date)
                    formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
                except:
                    formatted_date = date[:10]
                
                # Обрезаем описание если слишком длинное
                short_desc = description[:100] + "..." if len(description) > 100 else description
                
                embed.add_field(
                    name=f"{i}. {event_type}",
                    value=f"**Участников:** {participants} чел.\n"
                          f"**Описание:** {short_desc}\n"
                          f"**Дата:** {formatted_date}",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="топ_организаторов", description="Топ организаторов мероприятий")
    async def top_organizers(self, interaction: discord.Interaction):
        """Показывает топ-10 организаторов по количеству проведённых мероприятий"""
        
        await interaction.response.defer()
        
        # Получаем статистику из БД
        import aiosqlite
        from config import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute('''
                SELECT user_id, COUNT(*) as report_count, SUM(participants) as total_participants
                FROM reports
                GROUP BY user_id
                ORDER BY report_count DESC
                LIMIT 10
            ''')
            stats = await cursor.fetchall()
        
        embed = discord.Embed(
            title="🏆 Топ организаторов мероприятий",
            description="Рейтинг участников по количеству проведённых мероприятий",
            color=discord.Color.gold()
        )
        
        if not stats:
            embed.description = "❌ Пока нет данных о мероприятиях"
        else:
            medals = ["🥇", "🥈", "🥉"]
            
            for i, (user_id, report_count, total_participants) in enumerate(stats, 1):
                member = interaction.guild.get_member(user_id)
                member_name = member.display_name if member else f"ID: {user_id}"
                
                medal = medals[i-1] if i <= 3 else f"**{i}.**"
                
                embed.add_field(
                    name=f"{medal} {member_name}",
                    value=f"📋 Мероприятий: **{report_count}**\n"
                          f"👥 Всего участников: **{total_participants}**",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Reports(bot))
