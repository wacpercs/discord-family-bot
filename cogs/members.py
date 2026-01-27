import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from database.db import Database
from config import FAMILY_ROLE_ID

class Members(commands.Cog):
    """Модуль управления участниками семьи"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="профиль", description="Посмотреть профиль участника семьи")
    @app_commands.describe(member="Выберите участника (оставьте пустым для своего профиля)")
    async def profile(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None
    ):
        if member is None:
            member = interaction.user
        
        # Проверяем, состоит ли в семье
        family_role = interaction.guild.get_role(FAMILY_ROLE_ID)
        if family_role and family_role not in member.roles:
            await interaction.response.send_message(
                "❌ Этот пользователь не состоит в семье!",
                ephemeral=True
            )
            return
        
        # Получаем данные из БД
        member_data = await Database.get_member(member.id)
        warns = await Database.get_warns(member.id)
        reports = await Database.get_user_reports(member.id, limit=100)
        
        # Создаём embed
        embed = discord.Embed(
            title=f"👤 Профиль участника семьи",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Основная информация
        embed.add_field(
            name="📋 Discord",
            value=f"{member.mention}\n`{member.name}`",
            inline=True
        )
        
        if member_data:
            nickname, join_date, rank, activity = member_data[1], member_data[2], member_data[3], member_data[4]
            
            try:
                join_date_obj = datetime.fromisoformat(join_date)
                days_in_family = (datetime.now() - join_date_obj).days
                formatted_date = join_date_obj.strftime("%d.%m.%Y")
            except:
                formatted_date = "Неизвестно"
                days_in_family = 0
            
            embed.add_field(
                name="🎮 Игровой ник",
                value=f"`{nickname}`",
                inline=True
            )
            embed.add_field(
                name="📅 В семье с",
                value=f"{formatted_date}\n({days_in_family} дн.)",
                inline=True
            )
            embed.add_field(
                name="⭐ Звание",
                value=f"`{rank}`",
                inline=True
            )
            embed.add_field(
                name="📊 Активность",
                value=f"`{activity} очков`",
                inline=True
            )
        
        # Статистика
        warn_count = len(warns)
        report_count = len(reports)
        
        total_participants = sum(r[3] for r in reports) if reports else 0
        
        embed.add_field(
            name="📈 Статистика",
            value=f"⚠️ Предупреждений: **{warn_count}/3**\n"
                  f"📋 Отчётов: **{report_count}**\n"
                  f"👥 Участников мероприятий: **{total_participants}**",
            inline=False
        )
        
        # Дата присоединения к Discord
        account_created = member.created_at.strftime("%d.%m.%Y")
        embed.set_footer(text=f"Аккаунт создан: {account_created}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="список_семьи", description="Показать всех участников семьи")
    async def family_list(self, interaction: discord.Interaction):
        """Показывает список всех участников семьи"""
        
        family_role = interaction.guild.get_role(FAMILY_ROLE_ID)
        
        if not family_role:
            await interaction.response.send_message(
                "❌ Роль семьи не найдена на сервере! Проверьте FAMILY_ROLE_ID в .env",
                ephemeral=True
            )
            return
        
        # Получаем всех участников с ролью семьи
        family_members = [member for member in interaction.guild.members if family_role in member.roles]
        
        if not family_members:
            await interaction.response.send_message(
                "❌ В семье пока нет участников!",
                ephemeral=True
            )
            return
        
        # Сортируем по дате присоединения к серверу
        family_members.sort(key=lambda m: m.joined_at if m.joined_at else datetime.now())
        
        embed = discord.Embed(
            title=f"👥 Список участников семьи",
            description=f"Всего участников: **{len(family_members)}**",
            color=discord.Color.blue()
        )
        
        # Разбиваем на страницы по 25 участников
        for i in range(0, len(family_members), 25):
            members_chunk = family_members[i:i+25]
            member_list = []
            
            for j, member in enumerate(members_chunk, i+1):
                # Получаем данные из БД
                member_data = await Database.get_member(member.id)
                nickname = member_data[1] if member_data else "Не указан"
                
                member_list.append(f"**{j}.** {member.mention} - `{nickname}`")
            
            # Добавляем поле с участниками
            field_name = f"Участники {i+1}-{min(i+25, len(family_members))}"
            embed.add_field(
                name=field_name,
                value="\n".join(member_list),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="исключить", description="Исключить участника из семьи")
    @app_commands.describe(
        member="Выберите участника для исключения",
        reason="Причина исключения"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        # Проверка, что нельзя кикнуть себя
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Вы не можете исключить сами себя!",
                ephemeral=True
            )
            return
        
        # Проверка иерархии ролей
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ Вы не можете исключить этого участника (у него выше или равная роль)!",
                ephemeral=True
            )
            return
        
        family_role = interaction.guild.get_role(FAMILY_ROLE_ID)
        
        if not family_role or family_role not in member.roles:
            await interaction.response.send_message(
                "❌ Этот пользователь не состоит в семье!",
                ephemeral=True
            )
            return
        
        # Убираем роль
        await member.remove_roles(family_role)
        
        # Создаём embed
        embed = discord.Embed(
            title="🚫 Участник исключён из семьи",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Исключён", value=member.mention, inline=True)
        embed.add_field(name="👮 Модератор", value=interaction.user.mention, inline=True)
        embed.add_field(name="📋 Причина", value=reason, inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
        # Уведомляем пользователя
        try:
            user_embed = discord.Embed(
                title="🚫 Вы исключены из семьи",
                description=f"Вы были исключены из семьи на сервере **{interaction.guild.name}**",
                color=discord.Color.red()
            )
            user_embed.add_field(name="📋 Причина", value=reason, inline=False)
            user_embed.add_field(name="👮 Модератор", value=interaction.user.name, inline=False)
            await member.send(embed=user_embed)
        except discord.Forbidden:
            pass
    
    @app_commands.command(name="установить_ник", description="Установить игровой ник участнику")
    @app_commands.describe(
        member="Выберите участника",
        nickname="Игровой ник в GTA 5 RP"
    )
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def set_nickname(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        nickname: str
    ):
        # Проверяем длину ника
        if len(nickname) > 50:
            await interaction.response.send_message(
                "❌ Ник слишком длинный (максимум 50 символов)!",
                ephemeral=True
            )
            return
        
        # Сохраняем в БД
        await Database.add_member(
            user_id=member.id,
            nickname=nickname,
            join_date=datetime.now().isoformat()
        )
        
        embed = discord.Embed(
            title="✅ Игровой ник установлен",
            description=f"Игровой ник для {member.mention} установлен: `{nickname}`",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Members(bot))
