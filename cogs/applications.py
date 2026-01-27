import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from config import APPLICATIONS_CHANNEL_ID, FAMILY_ROLE_ID


class Applications(commands.Cog):
    """Модуль обработки заявок на вступление в семью"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_applications", description="Отправить сообщение с кнопкой подачи заявки")
    @app_commands.default_permissions(administrator=True)
    async def setup_applications(self, interaction: discord.Interaction):
        """Отправляет embed с кнопкой для подачи заявки в текущий канал"""

        embed = discord.Embed(
            title="🏠 Вступление в семью",
            description=(
                "Хотите стать частью нашей семьи? Нажмите на кнопку ниже, "
                "чтобы подать заявку на вступление!\n\n"
                "**Требования:**\n"
                "• Возраст персонажа от 16 лет\n"
                "• Адекватное поведение\n"
                "• Готовность участвовать в жизни семьи\n\n"
                "После подачи заявки она будет рассмотрена администрацией."
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Заявки рассматриваются в течение 24 часов")

        view = ApplicationButtonView()
        await interaction.channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            "✅ Сообщение с кнопкой подачи заявки отправлено!",
            ephemeral=True
        )


class ApplicationButtonView(discord.ui.View):
    """Кнопка для подачи заявки"""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📝 Подать заявку",
        style=discord.ButtonStyle.primary,
        custom_id="open_application_modal"
    )
    async def open_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверка, не состоит ли уже в семье
        family_role = interaction.guild.get_role(FAMILY_ROLE_ID)
        if family_role and family_role in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Вы уже состоите в семье!",
                ephemeral=True
            )
            return

        # Открываем модальное окно заявки
        modal = ApplicationModal()
        await interaction.response.send_modal(modal)


class ApplicationModal(discord.ui.Modal, title='Заявка на вступление в семью'):
    """Модальное окно для подачи заявки"""

    nickname = discord.ui.TextInput(
        label='Никнейм',
        style=discord.TextStyle.short,
        placeholder='Введите ваш ник в игре...',
        required=True,
        max_length=50,
        min_length=2
    )

    static_id = discord.ui.TextInput(
        label='StaticID',
        style=discord.TextStyle.short,
        placeholder='Например: 1337',
        required=True,
        max_length=10,
        min_length=1
    )

    experience = discord.ui.TextInput(
        label='Опыт игры на сервере',
        style=discord.TextStyle.short,
        placeholder='Например: 2 месяца, 100 часов...',
        required=True,
        max_length=100,
        min_length=2
    )

    about = discord.ui.TextInput(
        label='Расскажите о себе',
        style=discord.TextStyle.paragraph,
        placeholder='Почему хотите вступить в семью? Расскажите немного о себе...',
        required=True,
        max_length=1000,
        min_length=1
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Создаём embed для заявки
        embed = discord.Embed(
            title="📝 Новая заявка на вступление в семью",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 Никнейм",
            value=f"`{self.nickname.value}`",
            inline=True
        )
        embed.add_field(
            name="🆔 StaticID",
            value=f"`{self.static_id.value}`",
            inline=True
        )
        embed.add_field(
            name="📊 Опыт на сервере",
            value=f"`{self.experience.value}`",
            inline=False
        )
        embed.add_field(
            name="💭 О себе",
            value=self.about.value,
            inline=False
        )

        embed.set_footer(
            text=f"Discord: {interaction.user.name} • ID: {interaction.user.id}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # Создаём кнопки для обработки заявки
        view = ApplicationDecisionView()

        # Отправляем в канал заявок
        channel = interaction.client.get_channel(APPLICATIONS_CHANNEL_ID)
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


class ApplicationDecisionView(discord.ui.View):
    """Кнопки для обработки заявки (принять/отклонить)"""

    def __init__(self):
        super().__init__(timeout=None)

    def _get_user_id_from_embed(self, embed: discord.Embed) -> int:
        """Извлекает user_id из footer embed'а"""
        if embed.footer and embed.footer.text:
            import re
            match = re.search(r'ID:\s*(\d+)', embed.footer.text)
            if match:
                return int(match.group(1))
        return 0

    def _get_nickname_from_embed(self, embed: discord.Embed) -> str:
        """Извлекает никнейм из embed'а"""
        for field in embed.fields:
            if "Никнейм" in field.name:
                return field.value.strip('`')
        return "Неизвестно"

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.green, custom_id="accept_app")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверка прав
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ У вас недостаточно прав для принятия заявок!",
                ephemeral=True
            )
            return

        # Получаем данные из embed
        embed = interaction.message.embeds[0]
        user_id = self._get_user_id_from_embed(embed)
        nickname = self._get_nickname_from_embed(embed)

        if not user_id:
            await interaction.response.send_message(
                "❌ Не удалось определить пользователя из заявки!",
                ephemeral=True
            )
            return

        # Получаем пользователя
        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message(
                "❌ Пользователь покинул сервер!",
                ephemeral=True
            )
            return

        # Выдаём роль семьи
        family_role = interaction.guild.get_role(FAMILY_ROLE_ID)
        if family_role:
            await member.add_roles(family_role)
        else:
            await interaction.response.send_message(
                "⚠️ Роль семьи не найдена. Проверьте FAMILY_ROLE_ID в .env",
                ephemeral=True
            )
            return

        # Обновляем embed
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
            f"✅ Заявка **{nickname}** принята!\n"
            f"👤 Пользователь: {member.mention}",
            ephemeral=True
        )

        # Отправляем уведомление пользователю
        try:
            welcome_embed = discord.Embed(
                title="🎉 Поздравляем!",
                description="Ваша заявка на вступление в семью **принята**!",
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

        # Получаем данные из embed
        embed = interaction.message.embeds[0]
        user_id = self._get_user_id_from_embed(embed)
        nickname = self._get_nickname_from_embed(embed)

        # Открываем модальное окно для указания причины
        modal = RejectModal(user_id, nickname)
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

    def __init__(self, user_id: int, nickname: str):
        super().__init__()
        self.user_id = user_id
        self.nickname = nickname

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


async def setup(bot):
    await bot.add_cog(Applications(bot))
    # Регистрируем persistent views
    bot.add_view(ApplicationButtonView())
    bot.add_view(ApplicationDecisionView())
