import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import sys
import os

# Добавляем путь к utils в sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from utils.guild_settings import get_guild_settings
    MULTISERVER_ENABLED = True
except ImportError:
    MULTISERVER_ENABLED = False
    from config import APPLICATIONS_CHANNEL_ID, FAMILY_ROLE_NAME

class Applications(commands.Cog):
    """Модуль обработки заявок на вступление в семью"""
    
    def __init__(self, bot):
        self.bot = bot
        # Регистрируем persistent view при запуске
        self.bot.add_view(ApplicationButton(self.bot))
        
    @app_commands.command(name="заявка", description="Подать заявку на вступление в семью")
    @app_commands.describe(
        nickname="Ваш игровой ник в GTA 5 RP",
        age="Возраст вашего персонажа",
        experience="Ваш опыт игры на сервере (сколько времени играете)",
        about="Расскажите о себе и почему хотите вступить в семью"
    )
    async def submit_application(
        self, 
        interaction: discord.Interaction, 
        nickname: str,
        age: int,
        experience: str,
        about: str
    ):
        # Получаем настройки сервера
        if MULTISERVER_ENABLED:
            settings = await get_guild_settings(interaction.guild.id)
            if not settings:
                await interaction.response.send_message(
                    "⚠️ Бот не настроен на этом сервере!\n\n"
                    "**Администратор должен использовать:**\n"
                    "`/настроить` для первоначальной настройки",
                    ephemeral=True
                )
                return
            applications_channel_id = settings['applications_channel_id']
            family_role_name = settings['family_role_name']
        else:
            applications_channel_id = APPLICATIONS_CHANNEL_ID
            family_role_name = FAMILY_ROLE_NAME
        
        # Проверка возраста
        if age < 16:
            await interaction.response.send_message(
                "❌ К сожалению, минимальный возраст персонажа для вступления - 16 лет.",
                ephemeral=True
            )
            return
        
        # Проверка, не состоит ли уже в семье
        family_role = discord.utils.get(interaction.guild.roles, name=family_role_name)
        if family_role and family_role in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Вы уже состоите в семье!",
                ephemeral=True
            )
            return
        
        # Создаём красивый embed для заявки
        embed = discord.Embed(
            title="📝 Новая заявка на вступление в семью",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Игровой ник", 
            value=f"`{nickname}`", 
            inline=True
        )
        embed.add_field(
            name="🎂 Возраст персонажа", 
            value=f"`{age} лет`", 
            inline=True
        )
        embed.add_field(
            name="📊 Опыт на сервере", 
            value=f"`{experience}`", 
            inline=False
        )
        embed.add_field(
            name="💭 О себе", 
            value=about, 
            inline=False
        )
        
        embed.set_footer(
            text=f"Discord: {interaction.user.name} • ID: {interaction.user.id}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Создаём кнопки для обработки заявки
        view = ApplicationView(interaction.user.id, nickname, interaction.user.name, family_role_name)
        
        # Отправляем в канал заявок
        channel = self.bot.get_channel(applications_channel_id)
        if not channel:
            await interaction.response.send_message(
                "❌ Ошибка: канал для заявок не найден. Обратитесь к администратору.",
                ephemeral=True
            )
            return
            
        await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            "✅ Ваша заявка успешно отправлена на рассмотрение!\n"
            "⏰ Ожидайте ответа от администрации семьи.",
            ephemeral=True
        )
    
    @app_commands.command(name="setup_applications", description="Создать сообщение с кнопкой для подачи заявок (только админы)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_applications_command(self, interaction: discord.Interaction):
        """Создать постоянное сообщение с кнопкой для подачи заявок"""
        
        # Получаем настройки сервера
        if MULTISERVER_ENABLED:
            settings = await get_guild_settings(interaction.guild.id)
            if not settings:
                await interaction.response.send_message(
                    "⚠️ Сначала настройте бота командой `/настроить`",
                    ephemeral=True
                )
                return
            family_role_name = settings['family_role_name']
        else:
            family_role_name = FAMILY_ROLE_NAME
        
        # Создаём embed
        embed = discord.Embed(
            title="📋 Подача заявки на вступление в семью",
            description=(
                "Хотите вступить в нашу семью? Нажмите кнопку ниже!\n\n"
                "**Требования:**\n"
                "• Минимальный возраст персонажа: 16 лет\n"
                "• Активная игра на сервере\n"
                "• Соблюдение правил семьи\n\n"
                "После подачи заявки ожидайте ответа от администрации."
            ),
            color=discord.Color.blue()
        )
        
        embed.set_footer(text=f"Роль семьи: {family_role_name}")
        
        # Создаём view с кнопкой
        view = ApplicationButton(self.bot, family_role_name)
        
        # Отправляем сообщение
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            "✅ Сообщение с кнопкой для подачи заявок создано!",
            ephemeral=True
        )

class ApplicationView(discord.ui.View):
    """Кнопки для обработки заявки"""
    
    def __init__(self, user_id: int, nickname: str, username: str, family_role_name: str = None):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.nickname = nickname
        self.username = username
        self.family_role_name = family_role_name or "🏠 Семья"
        
    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.green, custom_id="accept_app")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверка прав
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ У вас недостаточно прав для принятия заявок!",
                ephemeral=True
            )
            return
        
        # Получаем пользователя
        member = interaction.guild.get_member(self.user_id)
        if not member:
            await interaction.response.send_message(
                "❌ Пользователь покинул сервер!",
                ephemeral=True
            )
            return
        
        # Выдаём роль семьи
        family_role = discord.utils.get(interaction.guild.roles, name=self.family_role_name)
        if family_role:
            await member.add_roles(family_role)
        else:
            await interaction.response.send_message(
                f"⚠️ Роль '{self.family_role_name}' не найдена. Создайте её или используйте /настроить для изменения",
                ephemeral=True
            )
            return
        
        # Обновляем embed
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ Заявка принята"
        embed.add_field(
            name="Принял заявку", 
            value=f"{interaction.user.mention} ({interaction.user.name})", 
            inline=False
        )
        embed.timestamp = datetime.now()
        
        # Убираем кнопки
        await interaction.message.edit(embed=embed, view=None)
        
        await interaction.response.send_message(
            f"✅ Заявка **{self.nickname}** принята!\n"
            f"👤 Пользователь: {member.mention}",
            ephemeral=True
        )
        
        # Отправляем уведомление пользователю
        try:
            welcome_embed = discord.Embed(
                title="🎉 Поздравляем!",
                description=f"Ваша заявка на вступление в семью **принята**!",
                color=discord.Color.green()
            )
            welcome_embed.add_field(
                name="Принял вашу заявку",
                value=f"{interaction.user.name}",
                inline=False
            )
            welcome_embed.add_field(
                name="Добро пожаловать!",
                value="Ознакомьтесь с правилами семьи и начинайте участвовать в мероприятиях!",
                inline=False
            )
            await member.send(embed=welcome_embed)
        except discord.Forbidden:
            pass  # У пользователя закрыты ЛС
    
    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.red, custom_id="reject_app")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверка прав
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ У вас недостаточно прав для отклонения заявок!",
                ephemeral=True
            )
            return
        
        # Открываем модальное окно для указания причины
        modal = RejectModal(self.user_id, self.nickname, self.username)
        await interaction.response.send_modal(modal)

class RejectModal(discord.ui.Modal, title='Причина отклонения заявки'):
    """Модальное окно для указания причины отклонения"""
    
    reason = discord.ui.TextInput(
        label='Укажите причину отклонения',
        style=discord.TextStyle.paragraph,
        placeholder='Например: не соответствуете требованиям по возрасту/опыту...',
        required=True,
        max_length=500,
        min_length=10
    )
    
    def __init__(self, user_id: int, nickname: str, username: str):
        super().__init__()
        self.user_id = user_id
        self.nickname = nickname
        self.username = username
    
    async def on_submit(self, interaction: discord.Interaction):
        # Обновляем embed
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ Заявка отклонена"
        embed.add_field(
            name="Отклонил заявку", 
            value=f"{interaction.user.mention} ({interaction.user.name})", 
            inline=False
        )
        embed.add_field(
            name="Причина отклонения", 
            value=self.reason.value, 
            inline=False
        )
        embed.timestamp = datetime.now()
        
        # Убираем кнопки
        await interaction.message.edit(embed=embed, view=None)
        
        await interaction.response.send_message(
            f"❌ Заявка **{self.nickname}** отклонена.\n"
            f"📝 Причина: {self.reason.value}",
            ephemeral=True
        )
        
        # Отправляем уведомление пользователю
        member = interaction.guild.get_member(self.user_id)
        if member:
            try:
                reject_embed = discord.Embed(
                    title="❌ Заявка отклонена",
                    description="К сожалению, ваша заявка на вступление в семью была отклонена.",
                    color=discord.Color.red()
                )
                reject_embed.add_field(
                    name="Причина отклонения",
                    value=self.reason.value,
                    inline=False
                )
                reject_embed.add_field(
                    name="Что делать?",
                    value="Вы можете подать заявку повторно после устранения недочётов.",
                    inline=False
                )
                await member.send(embed=reject_embed)
            except discord.Forbidden:
                pass  # У пользователя закрыты ЛС


class ApplicationModal(discord.ui.Modal, title="Заявка на вступление в семью"):
    """Модальное окно для подачи заявки"""
    
    nickname = discord.ui.TextInput(
        label="Игровой ник",
        placeholder="Ваш ник в GTA 5 RP",
        required=True,
        max_length=50
    )
    
    age = discord.ui.TextInput(
        label="Возраст персонажа",
        placeholder="Например: 25",
        required=True,
        max_length=3
    )
    
    experience = discord.ui.TextInput(
        label="Опыт на сервере",
        placeholder="Например: Играю 2 месяца",
        required=True,
        max_length=100
    )
    
    about = discord.ui.TextInput(
        label="О себе",
        placeholder="Расскажите почему хотите вступить в семью",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    def __init__(self, bot, family_role_name: str):
        super().__init__()
        self.bot = bot
        self.family_role_name = family_role_name
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверка возраста
        try:
            age_int = int(self.age.value)
        except ValueError:
            await interaction.response.send_message(
                "❌ Возраст должен быть числом!",
                ephemeral=True
            )
            return
        
        if age_int < 16:
            await interaction.response.send_message(
                "❌ Минимальный возраст персонажа для вступления - 16 лет.",
                ephemeral=True
            )
            return
        
        # Проверка, не состоит ли уже в семье
        family_role = discord.utils.get(interaction.guild.roles, name=self.family_role_name)
        if family_role and family_role in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Вы уже состоите в семье!",
                ephemeral=True
            )
            return
        
        # Получаем настройки сервера
        if MULTISERVER_ENABLED:
            settings = await get_guild_settings(interaction.guild.id)
            if not settings:
                await interaction.response.send_message(
                    "⚠️ Бот не настроен на этом сервере!",
                    ephemeral=True
                )
                return
            applications_channel_id = settings['applications_channel_id']
        else:
            applications_channel_id = APPLICATIONS_CHANNEL_ID
        
        # Создаём embed для заявки
        embed = discord.Embed(
            title="📝 Новая заявка на вступление в семью",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Игровой ник", value=f"`{self.nickname.value}`", inline=True)
        embed.add_field(name="🎂 Возраст персонажа", value=f"`{age_int} лет`", inline=True)
        embed.add_field(name="📊 Опыт на сервере", value=f"`{self.experience.value}`", inline=False)
        embed.add_field(name="💭 О себе", value=self.about.value, inline=False)
        
        embed.set_footer(
            text=f"Discord: {interaction.user.name} • ID: {interaction.user.id}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Создаём кнопки
        view = ApplicationView(
            interaction.user.id,
            self.nickname.value,
            interaction.user.name,
            self.family_role_name
        )
        
        # Отправляем в канал заявок
        channel = self.bot.get_channel(applications_channel_id)
        if channel:
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                "✅ Ваша заявка успешно отправлена!\n⏰ Ожидайте ответа от администрации.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Ошибка: канал для заявок не найден.",
                ephemeral=True
            )


class ApplicationButton(discord.ui.View):
    """Постоянная кнопка для подачи заявок"""
    
    def __init__(self, bot, family_role_name: str = "🏠 Семья"):
        super().__init__(timeout=None)
        self.bot = bot
        self.family_role_name = family_role_name
    
    @discord.ui.button(
        label="📝 Подать заявку",
        style=discord.ButtonStyle.green,
        custom_id="application_button",
        emoji="📝"
    )
    async def application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Получаем настройки сервера для определения роли
        if MULTISERVER_ENABLED:
            settings = await get_guild_settings(interaction.guild.id)
            if settings:
                family_role_name = settings['family_role_name']
            else:
                family_role_name = self.family_role_name
        else:
            family_role_name = self.family_role_name
        
        # Открываем модальное окно
        modal = ApplicationModal(self.bot, family_role_name)
        await interaction.response.send_modal(modal)


async def setup(bot):
    await bot.add_cog(Applications(bot))
