import os
import shutil
import zipfile
import asyncio
import re

from config import Config
from bot.helpers.utils import (
    create_apple_zip,
    format_string,
    send_message,
    edit_message,
    zip_handler,
    MAX_SIZE
)
from bot.logger import LOGGER
from mutagen import File
from mutagen.mp4 import MP4
from bot.settings import bot_set
from bot.helpers.progress import ProgressReporter
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..helpers.state import conversation_state


def _get_provider_base_path(user_id: int, path: str) -> str:
    """Determines the base path for rclone uploads based on the provider."""
    user_id_str = str(user_id)
    if "Apple Music" in path:
        return os.path.join(Config.LOCAL_STORAGE, user_id_str, "Apple Music")
    elif "Tidal_NG" in path:
        return os.path.join(Config.LOCAL_STORAGE, user_id_str, "Tidal_NG")
    return Config.LOCAL_STORAGE


async def track_upload(metadata, user, index: int = None, total: int = None):
    """Upload a single track."""
    base_path = _get_provider_base_path(user['user_id'], metadata['filepath'])

    if bot_set.upload_mode == 'Telegram':
        reporter = user.get('progress')
        if reporter:
            await reporter.set_stage("Uploading")

        await send_message(
            user,
            metadata['filepath'],
            'audio',
            caption=await format_string(
                "🎵 **{title}**\n👤 {artist}\n🎧 {provider}",
                {
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', '--')
                }
            ),
            meta={
                'duration': metadata['duration'],
                'artist': metadata['artist'],
                'title': metadata['title'],
                'thumbnail': metadata['thumbnail']
            },
            progress_reporter=reporter,
            progress_label="Uploading",
            file_index=index,
            total_files=total,
            cancel_event=user.get('cancel_event')
        )

    elif bot_set.upload_mode == 'RCLONE':
        rclone_link, index_link, remote_info = await rclone_upload(
            user, metadata['filepath'], base_path
        )
        text = await format_string(
            "🎵 **{title}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', '--'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"

        await send_message(user, text)
        await _post_rclone_manage_button(user, remote_info)

    # Cleanup
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])


async def music_video_upload(metadata, user):
    """Upload a music video."""
    base_path = _get_provider_base_path(user['user_id'], metadata['filepath'])

    if bot_set.upload_mode == 'Telegram':
        reporter = user.get('progress')
        if reporter:
            await reporter.set_stage("Uploading")

        send_type = 'doc' if getattr(bot_set, 'video_as_document', False) else 'video'

        await send_message(
            user,
            metadata['filepath'],
            send_type,
            caption=await format_string(
                "🎬 **{title}**\n👤 {artist}\n🎧 {provider} Music Video",
                {
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', '--')
                }
            ),
            meta=metadata,
            progress_reporter=reporter,
            progress_label="Uploading",
            file_index=1,
            total_files=1,
            cancel_event=user.get('cancel_event')
        )

    elif bot_set.upload_mode == 'RCLONE':
        rclone_link, index_link, remote_info = await rclone_upload(
            user, metadata['filepath'], base_path
        )
        text = await format_string(
            "🎬 **{title}**\n👤 {artist}\n🎧 {provider} Music Video\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', '--'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"

        await send_message(user, text)
        await _post_rclone_manage_button(user, remote_info)

    # Cleanup
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])


def _get_folder_size(folder_path: str) -> int:
    total_size = 0
    for root, _, files in os.walk(folder_path):
        for f in files:
            try:
                total_size += os.path.getsize(os.path.join(root, f))
            except Exception:
                continue
    return total_size


async def album_upload(metadata, user):
    """Upload an album."""
    base_path = _get_provider_base_path(user['user_id'], metadata['folderpath'])

    if bot_set.upload_mode == 'Telegram':
        reporter = user.get('progress')

        if bot_set.album_zip:
            total_size = _get_folder_size(metadata['folderpath'])
            zip_paths = []

            if total_size > MAX_SIZE:
                z = await zip_handler(metadata['folderpath'])
                zip_paths = z if isinstance(z, list) else [z]
            else:
                zip_path = await create_apple_zip(
                    metadata['folderpath'],
                    user['user_id'],
                    metadata,
                    progress=reporter,
                    cancel_event=user.get('cancel_event')
                )
                zip_paths = [zip_path]

            caption = await format_string(
                "💿 **{album}**\n👤 {artist}\n🎧 {provider}",
                {
                    'album': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', '--')
                }
            )

            total_parts = len(zip_paths)
            for idx, zp in enumerate(zip_paths, start=1):
                await send_message(
                    user,
                    zp,
                    'doc',
                    caption=caption,
                    progress_reporter=reporter,
                    progress_label="Uploading",
                    file_index=idx,
                    total_files=total_parts
                )
                try:
                    os.remove(zp)
                except Exception:
                    pass

        else:
            tracks = metadata.get('tracks') or metadata.get('items', [])
            total_tracks = len(tracks)
            for idx, track in enumerate(tracks, start=1):
                await track_upload(track, user, index=idx, total=total_tracks)

    elif bot_set.upload_mode == 'RCLONE':
        rclone_link, index_link, remote_info = await rclone_upload(
            user, metadata['folderpath'], base_path
        )
        text = await format_string(
            "💿 **{album}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'album': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', '--'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"

        if metadata.get('poster_msg'):
            await edit_message(metadata['poster_msg'], text)
        else:
            await send_message(user, text)

        await _post_rclone_manage_button(user, remote_info)

    shutil.rmtree(metadata['folderpath'])


async def artist_upload(metadata, user):
    """Upload an artist's content."""
    base_path = _get_provider_base_path(user['user_id'], metadata['folderpath'])

    if bot_set.upload_mode == 'Telegram':
        reporter = user.get('progress')

        if bot_set.artist_zip:
            total_size = _get_folder_size(metadata['folderpath'])
            zip_paths = []

            if total_size > MAX_SIZE:
                z = await zip_handler(metadata['folderpath'])
                zip_paths = z if isinstance(z, list) else [z]
            else:
                zip_path = await create_apple_zip(
                    metadata['folderpath'],
                    user['user_id'],
                    metadata,
                    progress=reporter,
                    cancel_event=user.get('cancel_event')
                )
                zip_paths = [zip_path]

            caption = await format_string(
                "🎤 **{artist}**\n🎧 {provider} Discography",
                {
                    'artist': metadata['title'],
                    'provider': metadata.get('provider', '--')
                }
            )

            total_parts = len(zip_paths)
            for idx, zp in enumerate(zip_paths, start=1):
                await send_message(
                    user,
                    zp,
                    'doc',
                    caption=caption,
                    progress_reporter=reporter,
                    progress_label="Uploading",
                    file_index=idx,
                    total_files=total_parts
                )
                try:
                    os.remove(zp)
                except Exception:
                    pass

        else:
            if 'albums' in metadata:
                for album in metadata['albums']:
                    await album_upload(album, user)
            else:
                tracks = metadata.get('tracks') or metadata.get('items', [])
                total_tracks = len(tracks)
                for idx, track in enumerate(tracks, start=1):
                    await track_upload(track, user, index=idx, total=total_tracks)

    elif bot_set.upload_mode == 'RCLONE':
        rclone_link, index_link, remote_info = await rclone_upload(
            user, metadata['folderpath'], base_path
        )
        text = await format_string(
            "🎤 **{artist}**\n🎧 {provider} Discography\n🔗 [Direct Link]({r_link})",
            {
                'artist': metadata['title'],
                'provider': metadata.get('provider', '--'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"

        await send_message(user, text)
        await _post_rclone_manage_button(user, remote_info)

    shutil.rmtree(metadata['folderpath'])


async def playlist_upload(metadata, user):
    """Upload a playlist."""
    base_path = _get_provider_base_path(user['user_id'], metadata['folderpath'])

    if bot_set.upload_mode == 'Telegram':
        reporter = user.get('progress')

        if bot_set.playlist_zip:
            total_size = _get_folder_size(metadata['folderpath'])
            zip_paths = []

            if total_size > MAX_SIZE:
                z = await zip_handler(metadata['folderpath'])
                zip_paths = z if isinstance(z, list) else [z]
            else:
                zip_path = await create_apple_zip(
                    metadata['folderpath'],
                    user['user_id'],
                    metadata,
                    progress=reporter,
                    cancel_event=user.get('cancel_event')
                )
                zip_paths = [zip_path]

            caption = await format_string(
                "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist",
                {
                    'title': metadata['title'],
                    'artist': metadata.get('artist', 'Various Artists'),
                    'provider': metadata.get('provider', '--')
                }
            )

            total_parts = len(zip_paths)
            for idx, zp in enumerate(zip_paths, start=1):
                await send_message(
                    user,
                    zp,
                    'doc',
                    caption=caption,
                    progress_reporter=reporter,
                    progress_label="Uploading",
                    file_index=idx,
                    total_files=total_parts
                )
                try:
                    os.remove(zp)
                except Exception:
                    pass

        else:
            tracks = metadata.get('tracks') or metadata.get('items', [])
            total_tracks = len(tracks)
            for idx, track in enumerate(tracks, start=1):
                await track_upload(track, user, index=idx, total=total_tracks)

    elif bot_set.upload_mode == 'RCLONE':
        rclone_link, index_link, remote_info = await rclone_upload(
            user, metadata['folderpath'], base_path
        )
        text = await format_string(
            "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata.get('artist', 'Various Artists'),
                'provider': metadata.get('provider', '--'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"

        await send_message(user, text)
        await _post_rclone_manage_button(user, remote_info)

    shutil.rmtree(metadata['folderpath'])


async def rclone_upload(user, path, base_path):
    """Upload files via Rclone."""
    dest_root = (getattr(bot_set, 'rclone_dest', None) or Config.RCLONE_DEST)
    if not dest_root:
        return None, None, None

    abs_path = os.path.abspath(path)

    def _compute_relative(p: str, base: str | None) -> str:
        try:
            p_abs = os.path.abspath(p)
            if base:
                base_abs = os.path.abspath(base)
                if p_abs.startswith(base_abs):
                    return os.path.relpath(p_abs, base_abs)
        except Exception:
            pass

        if "Apple Music" in abs_path:
            try:
                parts = p_abs.split(os.sep)
                if "Apple Music" in parts:
                    idx = parts.index("Apple Music")
                    root = os.sep.join(parts[:idx + 1])
                    return os.path.relpath(p_abs, root)
            except Exception:
                pass

        return os.path.basename(p_abs) if os.path.isfile(p_abs) else os.path.basename(os.path.normpath(p_abs))

    scope = getattr(bot_set, 'rclone_copy_scope', 'FILE').upper()
    is_directory = os.path.isdir(abs_path)

    if scope == 'FOLDER':
        if is_directory:
            source_for_copy = abs_path
            relative_path = _compute_relative(abs_path, base_path)
            dest_path = f"{dest_root}/{relative_path}".rstrip("/")
        else:
            parent_dir_abs = os.path.dirname(abs_path)
            source_for_copy = parent_dir_abs
            relative_path = _compute_relative(parent_dir_abs, base_path)
            dest_path = f"{dest_root}/{relative_path}".rstrip("/")
            is_directory = True
    else:
        relative_path = _compute_relative(abs_path, base_path)
        if is_directory:
            source_for_copy = abs_path
            dest_path = f"{dest_root}/{relative_path}".rstrip("/")
        else:
            parent_dir = os.path.dirname(relative_path)
            source_for_copy = abs_path
            dest_path = f"{dest_root}/{parent_dir}".rstrip("/")

    copy_cmd = f'rclone copy --config ./rclone.conf "{source_for_copy}" "{dest_path}"'
    copy_task = await asyncio.create_subprocess_shell(
        copy_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    copy_stdout, copy_stderr = await copy_task.communicate()
    if copy_task.returncode != 0:
        try:
            LOGGER.debug(f"Rclone copy failed: {copy_stderr.decode().strip()}")
        except Exception:
            pass
        return None, None, None

    rclone_link = None
    index_link = None

    if bot_set.link_options in ['RCLONE', 'Both']:
        link_target = f"{dest_root}/{relative_path}".rstrip("/")
        link_cmd = f'rclone link --config ./rclone.conf "{link_target}"'
        link_task = await asyncio.create_subprocess_shell(
            link_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await link_task.communicate()
        if link_task.returncode == 0:
            try:
                rclone_link = stdout.decode().strip()
            except Exception:
                rclone_link = None
        else:
            try:
                LOGGER.debug(f"Failed to get Rclone link: {stderr.decode().strip()}")
            except Exception:
                pass

    if bot_set.link_options in ['Index', 'Both'] and Config.INDEX_LINK:
        index_link = f"{Config.INDEX_LINK}/{relative_path}".replace(" ", "%20")

    remote_name = ''
    remote_base = ''
    try:
        if dest_root and ':' in dest_root:
            remote_name, remote_base = dest_root.split(':', 1)
            remote_base = remote_base.strip('/')
        else:
            remote_name = (getattr(bot_set, 'rclone_remote', '') or dest_root or '').rstrip(':')
            remote_base = ''
    except Exception:
        remote_name = (getattr(bot_set, 'rclone_remote', '') or (
            Config.RCLONE_DEST.split(':', 1)[0] if Config.RCLONE_DEST and ':' in Config.RCLONE_DEST else ''
        )).rstrip(':')
        remote_base = ''

    remote_info = {
        'remote': remote_name,
        'base': remote_base,
        'path': relative_path,
        'is_dir': is_directory
    }

    return rclone_link, index_link, remote_info


async def _post_rclone_manage_button(user, remote_info: dict):
    """Post manage button after Rclone upload."""
    try:
        import uuid
        token = uuid.uuid4().hex[:10]
        src_remote = remote_info.get('remote')
        rel_path = remote_info.get('path') or ''
        is_dir = bool(remote_info.get('is_dir'))

        if is_dir:
            src_path = rel_path
            src_file = None
        else:
            src_path = os.path.dirname(rel_path)
            src_file = rel_path

        state = await conversation_state.get(user['user_id']) or {"stage": None, "data": {}}
        ctx = state.get('data', {})
        manage_map = dict(ctx.get('rclone_manage_map') or {})
        manage_map[token] = {
            'src_remote': src_remote,
            'base': remote_info.get('base') if isinstance(remote_info, dict) else None,
            'src_path': src_path,
            'src_file': src_file,
            'dst_remote': None,
            'dst_path': '',
            'cc_mode': 'copy',
            'src_page': 0
        }
        await conversation_state.update(user['user_id'], rclone_manage_map=manage_map)

        # Use rcloneManageStart|<token> to open the Cloud-to-Cloud manage flow
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Manage uploaded files", callback_data=f"rcloneManageStart|{token}")]
        ])
        await send_message(user, "✅ Uploaded via Rclone.", reply_markup=kb)
    except Exception as e:
        LOGGER.error(f"Error posting Rclone manage button: {e}")
