import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from database.db import Database
from config import FAMILY_ROLE_ID

class Warns(commands.Cog):
    """Модуль системы предупреждений (варнов)"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="warn", description="Выдать предупреждение участнику семьи")
    @app_commands.describe(
        member="Выберите участника семьи",
        reason="Причина выдачи предупреждения"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def warn_member(
        self, 
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        # Проверка, что нельзя варнить себя
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Вы не можете выдать предупреждение самому себе!",
                ephemeral=True
            )
            return
        
        # Проверка, что пользователь в семье
        family_role = interaction.guild.get_role(FAMILY_ROLE_ID)
        if family_role and family_role not in member.roles:
            await interaction.response.send_message(
                "❌ Этот пользователь не состоит в семье!",
                ephemeral=True
            )
            return
        
        # Добавляем предупреждение в БД
        current_date = datetime.now().isoformat()
        await Database.add_warn(member.id, interaction.user.id, reason, current_date)
        
        # Получаем количество предупреждений
        warn_count = await Database.get_warn_count(member.id)
        
        # Создаём embed
        embed = discord.Embed(
            title="⚠️ Выдано предупреждение",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Нарушитель", 
            value=f"{member.mention} (`{member.name}`)", 
            inline=True
        )
        embed.add_field(
            name="👮 Модератор", 
            value=f"{interaction.user.mention}", 
            inline=True
        )
        embed.add_field(
            name="📋 Причина", 
            value=reason, 
            inline=False
        )
        embed.add_field(
            name="📊 Всего предупреждений", 
            value=f"**{warn_count}/3**", 
            inline=False
        )
        
        if warn_count >= 3:
            embed.add_field(
                name="🚨 КРИТИЧНО", 
                value="Участник достиг лимита предупреждений и будет исключён!", 
                inline=False
            )
            embed.color = discord.Color.red()
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
        # Отправляем уведомление пользователю
        try:
            user_embed = discord.Embed(
                title="⚠️ Вы получили предупреждение",
                description=f"Вам выдано предупреждение в семье **{interaction.guild.name}**",
                color=discord.Color.orange()
            )
            user_embed.add_field(name="📋 Причина", value=reason, inline=False)
            user_embed.add_field(name="👮 Модератор", value=interaction.user.name, inline=False)
            user_embed.add_field(name="📊 Предупреждений", value=f"**{warn_count}/3**", inline=False)
            
            if warn_count >= 3:
                user_embed.add_field(
                    name="🚨 Внимание!",
                    value="Вы достигли лимита предупреждений и будете исключены из семьи!",
                    inline=False
                )
                user_embed.color = discord.Color.red()
            else:
                user_embed.add_field(
                    name="ℹ️ Важно",
                    value="При накоплении 3 предупреждений вы будете исключены из семьи.",
                    inline=False
                )
            
            await member.send(embed=user_embed)
        except discord.Forbidden:
            pass  # У пользователя закрыты ЛС
        
        # Если 3 варна - исключаем из семьи
        if warn_count >= 3:
            if family_role:
                await member.remove_roles(family_role)
                
            kick_embed = discord.Embed(
                title="🚫 Участник исключён из семьи",
                description=f"{member.mention} исключён за накопление 3 предупреждений!",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            kick_embed.add_field(name="Участник", value=member.mention, inline=True)
            kick_embed.add_field(name="Причина", value="3 предупреждения", inline=True)
            
            await interaction.followup.send(embed=kick_embed)
    
    @app_commands.command(name="warns", description="Посмотреть предупреждения участника")
    @app_commands.describe(member="Выберите участника (оставьте пустым, чтобы посмотреть свои)")
    async def check_warns(
        self, 
        interaction: discord.Interaction,
        member: discord.Member = None
    ):
        # Если участник не указан - показываем свои
        if member is None:
            member = interaction.user
        
        # Получаем предупреждения из БД
        warns = await Database.get_warns(member.id)
        
        embed = discord.Embed(
            title=f"⚠️ Предупреждения пользователя {member.display_name}",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if not warns:
            embed.description = "✅ Предупреждений нет"
            embed.color = discord.Color.green()
        else:
            embed.description = f"**Всего предупреждений:** {len(warns)}/3"
            
            for i, (warn_id, reason, date, mod_id) in enumerate(warns, 1):
                moderator = interaction.guild.get_member(mod_id)
                mod_name = moderator.display_name if moderator else "Неизвестен"
                
                # Форматируем дату
                try:
                    date_obj = datetime.fromisoformat(date)
                    formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
                except:
                    formatted_date = date[:10]
                
                embed.add_field(
                    name=f"Предупреждение #{i}",
                    value=f"**Причина:** {reason}\n"
                          f"**Модератор:** {mod_name}\n"
                          f"**Дата:** {formatted_date}\n"
                          f"**ID:** `{warn_id}`",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unwarn", description="Снять предупреждение с участника")
    @app_commands.describe(
        member="Выберите участника",
        warn_id="ID предупреждения (посмотрите через /warns)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        warn_id: int
    ):
        # Получаем все варны участника
        warns = await Database.get_warns(member.id)
        
        # Проверяем, существует ли варн с таким ID у этого пользователя
        warn_exists = any(w[0] == warn_id for w in warns)
        
        if not warn_exists:
            await interaction.response.send_message(
                f"❌ Предупреждение с ID `{warn_id}` не найдено у пользователя {member.mention}",
                ephemeral=True
            )
            return
        
        # Удаляем предупреждение
        await Database.remove_warn(warn_id)
        
        # Получаем обновлённое количество варнов
        new_warn_count = await Database.get_warn_count(member.id)
        
        embed = discord.Embed(
            title="✅ Предупреждение снято",
            description=f"Предупреждение с ID `{warn_id}` снято с {member.mention}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="👤 Участник",
            value=member.mention,
            inline=True
        )
        embed.add_field(
            name="👮 Снял",
            value=interaction.user.mention,
            inline=True
        )
        embed.add_field(
            name="📊 Осталось предупреждений",
            value=f"{new_warn_count}/3",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Уведомляем пользователя
        try:
            user_embed = discord.Embed(
                title="✅ Предупреждение снято",
                description=f"С вас снято предупреждение в семье **{interaction.guild.name}**",
                color=discord.Color.green()
            )
            user_embed.add_field(
                name="👮 Снял",
                value=interaction.user.name,
                inline=False
            )
            user_embed.add_field(
                name="📊 Осталось предупреждений",
                value=f"{new_warn_count}/3",
                inline=False
            )
            await member.send(embed=user_embed)
        except discord.Forbidden:
            pass
    
    @app_commands.command(name="clearwarns", description="Очистить все предупреждения участника")
    @app_commands.describe(member="Выберите участника")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_warns(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        # Получаем все варны
        warns = await Database.get_warns(member.id)
        
        if not warns:
            await interaction.response.send_message(
                f"❌ У {member.mention} нет предупреждений",
                ephemeral=True
            )
            return
        
        # Удаляем все варны
        for warn in warns:
            await Database.remove_warn(warn[0])
        
        embed = discord.Embed(
            title="✅ Предупреждения очищены",
            description=f"Все предупреждения ({len(warns)}) сняты с {member.mention}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="👮 Очистил", value=interaction.user.mention, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        # Уведомляем пользователя
        try:
            await member.send(
                f"✅ Все ваши предупреждения в семье **{interaction.guild.name}** были сняты!\n"
                f"Администратор: {interaction.user.name}"
            )
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(Warns(bot))
