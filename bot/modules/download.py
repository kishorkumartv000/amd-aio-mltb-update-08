import asyncio
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client, filters

from bot import CMD
from bot.logger import LOGGER

import bot.helpers.translations as lang

from ..helpers.utils import cleanup
from ..helpers.qobuz.handler import start_qobuz
from ..helpers.tidal.handler import start_tidal
from ..helpers.tidal_ng.handler import start_tidal_ng
from ..helpers.deezer.handler import start_deezer
from ..providers.apple import start_apple
# IMPORT EDIT_MESSAGE HERE:
from ..helpers.message import send_message, antiSpam, check_user, fetch_user_details, edit_message
from ..helpers.state import conversation_state


@Client.on_message(filters.command(CMD.DOWNLOAD))
async def download_track(c, msg: Message):
    if await check_user(msg=msg):
        try:
            if msg.reply_to_message:
                # Get options from message text and URL from reply
                parts = msg.text.split()
                options = parse_options(parts[1:]) if len(parts) > 1 else {}
                link = msg.reply_to_message.text
                reply = True
            else:
                # Parse options and URL from message text
                parts = msg.text.split()[1:]
                options = parse_options(parts)
                # Last part is URL
                link = parts[-1] if parts else None
                reply = False
        except Exception as e:
            LOGGER.error(f"Error parsing command: {e}")
            return await send_message(msg, lang.s.ERR_NO_LINK)

        if not link:
            return await send_message(msg, lang.s.ERR_LINK_RECOGNITION)
        
        # Apple-only: optional flags popup before starting, unless flags already provided
        try:
            apple_music = ["https://music.apple.com"]
            from bot.settings import bot_set
            popup_on = bool(getattr(bot_set, 'apple_flags_popup', False))
            has_flags = bool(options.get('song')) or bool(options.get('atmos'))
            is_apple_link = link.startswith(tuple(apple_music))
        except Exception:
            popup_on = False
            has_flags = False
            is_apple_link = False

        if is_apple_link and popup_on and not has_flags:
            # Store minimal context and show selection UI, then exit handler.
            user_ctx = await fetch_user_details(msg, reply)
            await conversation_state.start(
                msg.from_user.id,
                'apple_flags_select',
                {
                    'link': link,
                    'options': options or {},
                    'reply': bool(reply)
                }
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 Single track  —song", callback_data="appleFlag|song")],
                [InlineKeyboardButton("💿 Atmos album  —atmos", callback_data="appleFlag|atmos")],
                [InlineKeyboardButton("🎬 Atmos track  —song —atmos", callback_data="appleFlag|song_atmos")],
                [InlineKeyboardButton("❌ Cancel", callback_data="appleFlagCancel")]
            ])
            await send_message(user_ctx, "Select Apple Music download mode:", markup=kb)
            return

        spam = await antiSpam(msg.from_user.id, msg.chat.id)
        if not spam:
            user = await fetch_user_details(msg, reply)
            user['link'] = link
            from bot.helpers.tasks import task_manager
            from bot.settings import bot_set
            # If queue mode is ON, enqueue the job to run one-by-one
            if getattr(bot_set, 'queue_mode', False):
                # Build a small function that will create its own task state when executed
                async def _job():
                    state = await task_manager.create(user, label="Download")
                    u = dict(user)
                    u['task_id'] = state.task_id
                    u['cancel_event'] = state.cancel_event
                    u['bot_msg'] = await send_message(msg, f"Starting download…\nUse /cancel <code>{state.task_id}</code> to stop.")
                    await send_message(u, f"Task ID:\n<code>{state.task_id}</code>")
                    try:
                        await start_link(link, u, options)
                        await send_message(u, lang.s.TASK_COMPLETED)
                    except asyncio.CancelledError:
                        await send_message(u, "⏹️ Task cancelled")
                    except Exception as e:
                        LOGGER.error(f"Download failed: {e}")
                        error_msg = f"Download failed: {str(e)}"
                        await send_message(u, error_msg)
                    try:
                        await c.delete_messages(msg.chat.id, u['bot_msg'].id)
                    except Exception:
                        pass
                    await cleanup(u)
                    await task_manager.finish(state.task_id, status="cancelled" if state.cancel_event.is_set() else "done")
                    await antiSpam(msg.from_user.id, msg.chat.id, True)

                qid, pos = await task_manager.enqueue(user['user_id'], link, options, _job)
                await send_message(user, f"✅ Added to queue. ID: <code>{qid}</code>\nPosition: {pos}")
                return

            # Otherwise, run immediately as before
            state = await task_manager.create(user, label="Download")
            user['task_id'] = state.task_id
            user['cancel_event'] = state.cancel_event
            user['bot_msg'] = await send_message(msg, f"Starting download…\nUse /cancel <code>{state.task_id}</code> to stop.")
            await send_message(user, f"Task ID:\n<code>{state.task_id}</code>")
            try:
                await start_link(link, user, options)
                await send_message(user, lang.s.TASK_COMPLETED)
            except asyncio.CancelledError:
                await send_message(user, "⏹️ Task cancelled")
            except Exception as e:
                LOGGER.error(f"Download failed: {e}")
                error_msg = f"Download failed: {str(e)}"
                await send_message(user, error_msg)
            await c.delete_messages(msg.chat.id, user['bot_msg'].id)
            await cleanup(user)  # deletes uploaded files
            await task_manager.finish(state.task_id, status="cancelled" if state.cancel_event.is_set() else "done")
            await antiSpam(msg.from_user.id, msg.chat.id, True)


def parse_options(parts: list) -> dict:
    """Parse command-line options from message parts
    
    Args:
        parts: List of command arguments
    
    Returns:
        dict: Parsed options in {key: value} format
    """
    options = {}
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith('--'):
            key = part[2:]
            # Check if next part is a value (not another option)
            if i + 1 < len(parts) and not parts[i+1].startswith('--'):
                options[key] = parts[i+1]
                i += 1  # Skip value
            else:
                options[key] = True
        i += 1
    return options


async def start_link(link: str, user: dict, options: dict = None):
    """
    Route download request to appropriate provider handler
    
    Args:
        link: URL to download
        user: User details dictionary
        options: Command-line options passed by user
    """
    tidal = ["https://tidal.com", "https://listen.tidal.com", "tidal.com", "listen.tidal.com"]
    deezer = ["https://link.deezer.com", "https://deezer.com", "deezer.com", "https://www.deezer.com", "link.deezer.com"]
    qobuz = ["https://play.qobuz.com", "https://open.qobuz.com", "https://www.qobuz.com"]
    spotify = ["https://open.spotify.com"]
    apple_music = ["https://music.apple.com"]

    from bot.settings import bot_set
    if link.startswith(tuple(tidal)):
        if bot_set.tidal_legacy_enabled:
            await start_tidal(link, user)
        else:
            await start_tidal_ng(link, user)
    elif link.startswith(tuple(deezer)):
        await start_deezer(link, user)
    elif link.startswith(tuple(qobuz)):
        user['provider'] = 'Qobuz'
        await start_qobuz(link, user)
    elif link.startswith(tuple(spotify)):
        return 'spotify'
    elif link.startswith(tuple(apple_music)):
        user['provider'] = 'Apple'
        # USE IMPORTED EDIT_MESSAGE FUNCTION
        await edit_message(user['bot_msg'], "Starting Apple Music download...")
        await start_apple(link, user, options)
    else:
        await send_message(user, lang.s.ERR_UNSUPPORTED_LINK)
        return None


# --- Apple flags popup callbacks ---
@Client.on_callback_query(filters.regex(pattern=r"^appleFlag\|"))
async def apple_flag_select_cb(c, cb):
    try:
        state = await conversation_state.get(cb.from_user.id) or {}
        if state.get('stage') != 'apple_flags_select':
            return
        data = state.get('data') or {}
        link = data.get('link')
        options = dict(data.get('options') or {})
        choice = (cb.data.split('|', 1)[1] or '').strip()
        if choice == 'song':
            options['song'] = True
        elif choice == 'atmos':
            options['atmos'] = True
        elif choice == 'song_atmos':
            options['song'] = True
            options['atmos'] = True
        else:
            return
        # Acknowledge and close the selection message
        try:
            await c.answer_callback_query(cb.id)
        except Exception:
            pass
        try:
            await c.delete_messages(cb.message.chat.id, cb.message.id)
        except Exception:
            pass
        # Clear state
        await conversation_state.clear(cb.from_user.id)

        # Anti-spam check
        if await antiSpam(cb.from_user.id, cb.message.chat.id):
            return

        # Build user context
        user = await fetch_user_details(cb.message, reply=False)
        user['link'] = link

        from bot.helpers.tasks import task_manager
        from bot.settings import bot_set
        if getattr(bot_set, 'queue_mode', False):
            async def _job():
                state = await task_manager.create(user, label="Download")
                u = dict(user)
                u['task_id'] = state.task_id
                u['cancel_event'] = state.cancel_event
                u['bot_msg'] = await send_message(cb.message, f"Starting download…\nUse /cancel <code>{state.task_id}</code> to stop.")
                await send_message(u, f"Task ID:\n<code>{state.task_id}</code>")
                try:
                    await start_link(link, u, options)
                    await send_message(u, lang.s.TASK_COMPLETED)
                except asyncio.CancelledError:
                    await send_message(u, "⏹️ Task cancelled")
                except Exception as e:
                    LOGGER.error(f"Download failed: {e}")
                    await send_message(u, f"Download failed: {str(e)}")
                try:
                    await c.delete_messages(cb.message.chat.id, u['bot_msg'].id)
                except Exception:
                    pass
                await cleanup(u)
                await task_manager.finish(state.task_id, status="cancelled" if state.cancel_event.is_set() else "done")
                await antiSpam(cb.from_user.id, cb.message.chat.id, True)

            qid, pos = await task_manager.enqueue(user['user_id'], link, options, _job)
            await send_message(cb.message, f"✅ Added to queue. ID: <code>{qid}</code>\nPosition: {pos}")
            return

        # Immediate run
        state = await task_manager.create(user, label="Download")
        user['task_id'] = state.task_id
        user['cancel_event'] = state.cancel_event
        user['bot_msg'] = await send_message(cb.message, f"Starting download…\nUse /cancel <code>{state.task_id}</code> to stop.")
        await send_message(user, f"Task ID:\n<code>{state.task_id}</code>")
        try:
            await start_link(link, user, options)
            await send_message(user, lang.s.TASK_COMPLETED)
        except asyncio.CancelledError:
            await send_message(user, "⏹️ Task cancelled")
        except Exception as e:
            LOGGER.error(f"Download failed: {e}")
            await send_message(user, f"Download failed: {str(e)}")
        await c.delete_messages(cb.message.chat.id, user['bot_msg'].id)
        await cleanup(user)
        await task_manager.finish(state.task_id, status="cancelled" if state.cancel_event.is_set() else "done")
        await antiSpam(cb.from_user.id, cb.message.chat.id, True)
    except Exception:
        try:
            await conversation_state.clear(cb.from_user.id)
        except Exception:
            pass


@Client.on_callback_query(filters.regex(pattern=r"^appleFlagCancel$"))
async def apple_flag_cancel_cb(c, cb):
    try:
        await conversation_state.clear(cb.from_user.id)
    except Exception:
        pass
    try:
        await c.answer_callback_query(cb.id, "Cancelled", show_alert=False)
    except Exception:
        pass
    try:
        await c.delete_messages(cb.message.chat.id, cb.message.id)
    except Exception:
        pass
