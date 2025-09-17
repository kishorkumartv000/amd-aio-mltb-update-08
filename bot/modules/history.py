# bot/modules/history.py
from pyrogram import Client, filters
from bot.helpers.database.pg_impl import download_history
from bot.helpers.message import send_message

@Client.on_message(filters.command(["history", "downloads"]))
async def download_history_handler(client, message):
    user_id = message.from_user.id
    history = download_history.get_user_history(user_id)
    
    if not history:
        await send_message(message, "You haven't downloaded anything yet!")
        return
    
    response = "📝 **Your Download History:**\n\n"
    for item in history:
        response += (
            f"• **{item['title']}** by {item['artist']}\n"
            f"  - Type: {item['content_type'].title()}\n"
            f"  - Quality: {item['quality']}\n"
            f"  - Date: {item['download_time'].strftime('%Y-%m-%d %H:%M')}\n\n"
        )
    
    await send_message(message, response)
