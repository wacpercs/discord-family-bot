"""
Вспомогательные функции для получения настроек серверов
"""
import aiosqlite
from config import DATABASE_PATH
import discord

async def get_guild_settings(guild_id: int):
    """
    Получить настройки сервера из БД
    
    Возвращает dict с ключами:
    - applications_channel_id
    - reports_channel_id
    - logs_channel_id
    - family_role_name
    
    Возвращает None если настройки не найдены
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            'SELECT applications_channel_id, reports_channel_id, logs_channel_id, family_role_name FROM guild_settings WHERE guild_id = ?',
            (guild_id,)
        )
        result = await cursor.fetchone()
    
    if not result:
        return None
    
    return {
        'applications_channel_id': result[0],
        'reports_channel_id': result[1],
        'logs_channel_id': result[2],
        'family_role_name': result[3]
    }

async def check_guild_setup(interaction: discord.Interaction) -> tuple[bool, dict]:
    """
    Проверить настроен ли сервер
    
    Возвращает (настроен: bool, настройки: dict или None)
    """
    settings = await get_guild_settings(interaction.guild.id)
    
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
        return False, None
    
    return True, settings

# Для обратной совместимости с существующим кодом
# Если настройки сервера не найдены - используем из config.py
async def get_channel_or_default(guild_id: int, channel_type: str):
    """
    Получить ID канала из настроек сервера или из config.py
    
    channel_type: 'applications', 'reports', 'logs'
    """
    settings = await get_guild_settings(guild_id)
    
    if settings:
        if channel_type == 'applications':
            return settings['applications_channel_id']
        elif channel_type == 'reports':
            return settings['reports_channel_id']
        elif channel_type == 'logs':
            return settings['logs_channel_id']
    
    # Fallback на config.py если настройки не найдены
    from config import APPLICATIONS_CHANNEL_ID, REPORTS_CHANNEL_ID, LOGS_CHANNEL_ID
    
    if channel_type == 'applications':
        return APPLICATIONS_CHANNEL_ID
    elif channel_type == 'reports':
        return REPORTS_CHANNEL_ID
    elif channel_type == 'logs':
        return LOGS_CHANNEL_ID
    
    return None

async def get_family_role_or_default(guild_id: int):
    """Получить название роли семьи из настроек сервера или из config.py"""
    settings = await get_guild_settings(guild_id)
    
    if settings and settings['family_role_name']:
        return settings['family_role_name']
    
    # Fallback на config.py
    from config import FAMILY_ROLE_NAME
    return FAMILY_ROLE_NAME
