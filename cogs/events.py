import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import aiosqlite
from config import DATABASE_PATH
from typing import Optional

class EventView(discord.ui.View):
    """Кнопки и меню для управления мероприятием"""
    
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id
    
    @discord.ui.button(label="✅ Записаться в основной состав", style=discord.ButtonStyle.green, custom_id="join_main")
    async def join_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Записаться в основной состав"""
        result = await self.register_user(interaction, "main")
        await interaction.response.send_message(result, ephemeral=True)
    
    @discord.ui.button(label="📋 Записаться в запасной состав", style=discord.ButtonStyle.gray, custom_id="join_reserve")
    async def join_reserve(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Записаться в запасной состав"""
        result = await self.register_user(interaction, "reserve")
        await interaction.response.send_message(result, ephemeral=True)
    
    @discord.ui.button(label="❌ Отменить запись", style=discord.ButtonStyle.red, custom_id="cancel_registration")
    async def cancel_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отменить свою регистрацию"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                'DELETE FROM event_participants WHERE event_id = ? AND user_id = ?',
                (self.event_id, interaction.user.id)
            )
            await db.commit()
        
        await self.update_event_message(interaction.message)
        await interaction.response.send_message("✅ Вы отменили запись на мероприятие", ephemeral=True)
    
    @discord.ui.select(
        placeholder="Взаимодействие со списками",
        options=[
            discord.SelectOption(label="Тег основного состава", description="Упомянуть всех из основного состава", value="tag_main", emoji="📢"),
            discord.SelectOption(label="Тег запасного состава", description="Упомянуть всех из запасного состава", value="tag_reserve", emoji="📢"),
            discord.SelectOption(label="Завершить мероприятие", description="Закрыть регистрацию и архивировать", value="finish", emoji="✅"),
            discord.SelectOption(label="Отменить мероприятие", description="Отменить и удалить мероприятие", value="cancel", emoji="🗑️"),
        ]
    )
    async def manage_menu(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Меню управления мероприятием"""
        
        # Проверка прав (только создатель или администратор)
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT creator_id FROM events WHERE id = ?',
                (self.event_id,)
            )
            result = await cursor.fetchone()
            
        if not result:
            await interaction.response.send_message("❌ Мероприятие не найдено!", ephemeral=True)
            return
        
        creator_id = result[0]
        
        if interaction.user.id != creator_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Только создатель мероприятия или администратор может управлять им!",
                ephemeral=True
            )
            return
        
        choice = select.values[0]
        
        if choice == "tag_main":
            await self.tag_participants(interaction, "main")
        elif choice == "tag_reserve":
            await self.tag_participants(interaction, "reserve")
        elif choice == "finish":
            await self.finish_event(interaction)
        elif choice == "cancel":
            await self.cancel_event(interaction)
    
    async def register_user(self, interaction: discord.Interaction, roster_type: str):
        """Зарегистрировать пользователя на мероприятие"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Получаем информацию о мероприятии
            cursor = await db.execute(
                'SELECT max_participants, current_participants FROM events WHERE id = ?',
                (self.event_id,)
            )
            event_info = await cursor.fetchone()
            
            if not event_info:
                return "❌ Мероприятие не найдено!"
            
            max_participants, current_participants = event_info
            
            # Проверяем, не записан ли уже
            cursor = await db.execute(
                'SELECT roster_type FROM event_participants WHERE event_id = ? AND user_id = ?',
                (self.event_id, interaction.user.id)
            )
            existing = await cursor.fetchone()
            
            if existing:
                old_type = existing[0]
                if old_type == roster_type:
                    return f"⚠️ Вы уже записаны в {'основной' if roster_type == 'main' else 'запасной'} состав!"
                
                # Переместить из одного списка в другой
                await db.execute(
                    'UPDATE event_participants SET roster_type = ? WHERE event_id = ? AND user_id = ?',
                    (roster_type, self.event_id, interaction.user.id)
                )
                await db.commit()
                await self.update_event_message(interaction.message)
                return f"✅ Вы перемещены в {'основной' if roster_type == 'main' else 'запасной'} состав!"
            
            # Проверяем лимит для основного состава
            if roster_type == "main" and current_participants >= max_participants:
                return f"❌ Основной состав полон ({max_participants}/{max_participants})! Запишитесь в запасной."
            
            # Регистрируем
            await db.execute(
                'INSERT INTO event_participants (event_id, user_id, roster_type, joined_at) VALUES (?, ?, ?, ?)',
                (self.event_id, interaction.user.id, roster_type, datetime.now().isoformat())
            )
            
            # Обновляем счётчик участников
            if roster_type == "main":
                await db.execute(
                    'UPDATE events SET current_participants = current_participants + 1 WHERE id = ?',
                    (self.event_id,)
                )
            
            await db.commit()
        
        await self.update_event_message(interaction.message)
        return f"✅ Вы записаны в {'основной' if roster_type == 'main' else 'запасной'} состав!"
    
    async def update_event_message(self, message: discord.Message):
        """Обновить сообщение с мероприятием"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Получаем информацию о мероприятии
            cursor = await db.execute(
                'SELECT * FROM events WHERE id = ?',
                (self.event_id,)
            )
            event = await cursor.fetchone()
            
            # Получаем участников
            cursor = await db.execute(
                'SELECT user_id, roster_type FROM event_participants WHERE event_id = ? ORDER BY joined_at',
                (self.event_id,)
            )
            participants = await cursor.fetchall()
        
        if not event:
            return
        
        # Распаковываем данные мероприятия
        event_id, guild_id, creator_id, title, server, color, map_name, time, max_participants, current_participants, priority_roles, created_at = event
        
        # Создаём embed
        embed = discord.Embed(
            title=f"📋 Регистрация на мероприятие",
            color=discord.Color.from_str(color) if color else discord.Color.blue()
        )
        
        # Информация о мероприятии
        info = f"**• Название:** {title}\n"
        info += f"**• Сервер:** {server}\n"
        info += f"**• Лимит участников:** {max_participants}\n"
        if color:
            info += f"**• Цвет:** {color}\n"
        if map_name:
            info += f"**• Карта:** {map_name}\n"
        
        creator = message.guild.get_member(creator_id)
        info += f"**• Создатель:** {creator.mention if creator else 'Неизвестен'}\n"
        
        if priority_roles:
            info += f"**• Приоритетные роли:** {priority_roles}\n"
        
        info += f"**• Время:** {time}\n"
        info += f"**• ID мероприятия:** {event_id}\n"
        
        embed.add_field(name="ℹ️ Информация", value=info, inline=False)
        
        # Основной состав
        main_roster = [p for p in participants if p[1] == "main"]
        main_list = ""
        for i, (user_id, _) in enumerate(main_roster, 1):
            member = message.guild.get_member(user_id)
            main_list += f"{i}. {member.mention if member else f'ID:{user_id}'}\n"
        
        if not main_list:
            main_list = "*Пусто*"
        
        embed.add_field(
            name=f"👥 Основной состав | {len(main_roster)}/{max_participants} человек",
            value=main_list,
            inline=False
        )
        
        # Запасной состав
        reserve_roster = [p for p in participants if p[1] == "reserve"]
        reserve_list = ""
        for i, (user_id, _) in enumerate(reserve_roster, 1):
            member = message.guild.get_member(user_id)
            reserve_list += f"{i}. {member.mention if member else f'ID:{user_id}'}\n"
        
        if not reserve_list:
            reserve_list = "*Пусто*"
        
        embed.add_field(
            name=f"📋 Запасной состав | {len(reserve_roster)} человек",
            value=reserve_list,
            inline=False
        )
        
        embed.set_footer(text=f"Создано: {created_at[:16]}")
        
        await message.edit(embed=embed, view=self)
    
    async def tag_participants(self, interaction: discord.Interaction, roster_type: str):
        """Упомянуть всех участников"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT user_id FROM event_participants WHERE event_id = ? AND roster_type = ?',
                (self.event_id, roster_type)
            )
            participants = await cursor.fetchall()
        
        if not participants:
            await interaction.response.send_message(
                f"❌ {'Основной' if roster_type == 'main' else 'Запасной'} состав пуст!",
                ephemeral=True
            )
            return
        
        mentions = " ".join([f"<@{p[0]}>" for p in participants])
        roster_name = "основного" if roster_type == "main" else "запасного"
        
        await interaction.response.send_message(
            f"📢 **Участники {roster_name} состава:**\n{mentions}"
        )
    
    async def finish_event(self, interaction: discord.Interaction):
        """Завершить мероприятие"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                'UPDATE events SET status = ? WHERE id = ?',
                ("finished", self.event_id)
            )
            await db.commit()
        
        embed = interaction.message.embeds[0]
        embed.title = "✅ Мероприятие завершено"
        embed.color = discord.Color.green()
        
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Мероприятие завершено!", ephemeral=True)
    
    async def cancel_event(self, interaction: discord.Interaction):
        """Отменить мероприятие"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('DELETE FROM event_participants WHERE event_id = ?', (self.event_id,))
            await db.execute('DELETE FROM events WHERE id = ?', (self.event_id,))
            await db.commit()
        
        await interaction.message.delete()
        await interaction.response.send_message("🗑️ Мероприятие отменено и удалено!", ephemeral=True)


class Events(commands.Cog):
    """Модуль управления игровыми мероприятиями"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Инициализация таблиц при запуске"""
        await self.init_db()
    
    async def init_db(self):
        """Создать таблицы для мероприятий"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Таблица мероприятий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    creator_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    server TEXT NOT NULL,
                    color TEXT,
                    map_name TEXT,
                    time TEXT NOT NULL,
                    max_participants INTEGER DEFAULT 20,
                    current_participants INTEGER DEFAULT 0,
                    priority_roles TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Таблица участников
            await db.execute('''
                CREATE TABLE IF NOT EXISTS event_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    roster_type TEXT NOT NULL,
                    joined_at TEXT NOT NULL,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    UNIQUE(event_id, user_id)
                )
            ''')
            
            await db.commit()
    
    @app_commands.command(name="создать_мероприятие", description="Создать игровое мероприятие")
    @app_commands.describe(
        title="Название мероприятия",
        server="Игровой сервер (например: Miami)",
        time="Время проведения (например: 18:50)",
        max_participants="Максимум участников в основном составе",
        color="Цвет embed (например: #FF0000)",
        map_name="Название карты/локации",
        priority_roles="Приоритетные роли (через запятую)"
    )
    async def create_event(
        self,
        interaction: discord.Interaction,
        title: str,
        server: str,
        time: str,
        max_participants: int = 20,
        color: Optional[str] = None,
        map_name: Optional[str] = None,
        priority_roles: Optional[str] = None
    ):
        """Создать новое мероприятие"""
        
        # Проверка прав
        if not interaction.user.guild_permissions.manage_events:
            # Можно добавить проверку на определенную роль
            pass
        
        # Сохраняем в БД
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute('''
                INSERT INTO events 
                (guild_id, creator_id, title, server, color, map_name, time, max_participants, priority_roles, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                interaction.guild.id,
                interaction.user.id,
                title,
                server,
                color,
                map_name,
                time,
                max_participants,
                priority_roles,
                datetime.now().isoformat()
            ))
            await db.commit()
            event_id = cursor.lastrowid
        
        # Создаём embed
        embed = discord.Embed(
            title=f"📋 Регистрация на мероприятие",
            color=discord.Color.from_str(color) if color else discord.Color.blue()
        )
        
        # Информация о мероприятии
        info = f"**• Название:** {title}\n"
        info += f"**• Сервер:** {server}\n"
        info += f"**• Лимит участников:** {max_participants}\n"
        if color:
            info += f"**• Цвет:** {color}\n"
        if map_name:
            info += f"**• Карта:** {map_name}\n"
        
        info += f"**• Создатель:** {interaction.user.mention}\n"
        
        if priority_roles:
            info += f"**• Приоритетные роли:** {priority_roles}\n"
        
        info += f"**• Время:** {time}\n"
        info += f"**• ID мероприятия:** {event_id}\n"
        
        embed.add_field(name="ℹ️ Информация", value=info, inline=False)
        embed.add_field(
            name=f"👥 Основной состав | 0/{max_participants} человек",
            value="*Пусто*",
            inline=False
        )
        embed.add_field(
            name=f"📋 Запасной состав | 0 человек",
            value="*Пусто*",
            inline=False
        )
        
        embed.set_footer(text=f"Создано: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        # Создаём view с кнопками
        view = EventView(event_id)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="мои_мероприятия", description="Посмотреть свои созданные мероприятия")
    async def my_events(self, interaction: discord.Interaction):
        """Список мероприятий пользователя"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                'SELECT id, title, time, current_participants, max_participants, status FROM events WHERE creator_id = ? AND guild_id = ? ORDER BY created_at DESC LIMIT 10',
                (interaction.user.id, interaction.guild.id)
            )
            events = await cursor.fetchall()
        
        if not events:
            await interaction.response.send_message(
                "📋 У вас нет созданных мероприятий",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Ваши мероприятия",
            color=discord.Color.blue()
        )
        
        for event_id, title, time, current, max_p, status in events:
            status_emoji = "✅" if status == "finished" else "🟢" if status == "active" else "❌"
            embed.add_field(
                name=f"{status_emoji} {title}",
                value=f"**ID:** {event_id}\n**Время:** {time}\n**Участников:** {current}/{max_p}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Events(bot))
