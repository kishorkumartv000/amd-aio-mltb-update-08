import os
import shutil
import asyncio
import re
from config import Config
from bot.logger import LOGGER
from bot.settings import bot_set
from bot.helpers.utils import format_string, send_message, edit_message, MAX_SIZE
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..state import conversation_state


async def _get_tidal_ng_base_path(user_id: int) -> str:
    return os.path.join(Config.LOCAL_STORAGE, str(user_id), "Tidal_NG")


def _get_folder_size(folder_path: str) -> int:
    total_size = 0
    for root, _, files in os.walk(folder_path):
        for f in files:
            try:
                total_size += os.path.getsize(os.path.join(root, f))
            except Exception:
                continue
    return total_size


async def create_tidal_ng_zip(directory: str, user_id: int, metadata: dict) -> str:
    """Create a zip file for Tidal NG content with provider-aware naming.

    Examples:
    - Album:     [Tidal NG] The_Album_Name.zip
    - Playlist:  [Tidal NG] My_Playlist (Playlist).zip
    - Artist:    [Tidal NG] Some_Artist (Artist).zip
    - Video:     [Tidal NG] Some_Video (Video).zip
    """
    title = (metadata.get('title') or 'Tidal NG').strip()
    # sanitize and convert spaces to underscores similar to Apple helper
    safe_title = re.sub(r'[\\/*?:"<>|]', '', title).replace(' ', '_')
    provider = 'Tidal NG'
    ctype = (metadata.get('type') or 'album').strip().lower()

    if ctype == 'album':
        base = f"[{provider}] {safe_title}"
    elif ctype == 'playlist':
        base = f"[{provider}] {safe_title} (Playlist)"
    elif ctype == 'artist':
        base = f"[{provider}] {safe_title} (Artist)"
    elif ctype == 'video':
        base = f"[{provider}] {safe_title} (Video)"
    else:
        base = f"[{provider}] {safe_title}"

    zip_dir = os.path.dirname(directory)
    zip_path = os.path.join(zip_dir, f"{base}.zip")
    idx = 1
    while os.path.exists(zip_path):
        zip_path = os.path.join(zip_dir, f"{base}_{idx}.zip")
        idx += 1
    # Simple synchronous zipping (folder small enough or split handled elsewhere)
    import zipfile
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for f in files:
                fp = os.path.join(root, f)
                arc = os.path.relpath(fp, directory)
                zipf.write(fp, arc)
    LOGGER.info(f"Created Tidal NG zip: {zip_path}")
    return zip_path


async def _rclone_upload(user, path, base_path):
    dest_root = (getattr(bot_set, 'rclone_dest', None) or Config.RCLONE_DEST)
    if not dest_root:
        return None, None, None

    abs_path = os.path.abspath(path)
    is_dir = os.path.isdir(abs_path)
    # Relative path relative to final download base (Tidal NG root under LOCAL_STORAGE)
    try:
        base_abs = os.path.abspath(base_path)
        rel = os.path.relpath(abs_path, base_abs) if abs_path.startswith(base_abs) else os.path.basename(abs_path)
    except Exception:
        rel = os.path.basename(abs_path)

    # For files, upload to parent dir in remote; for directories, keep directory name
    if is_dir:
        dest_path = f"{dest_root}/{rel}".rstrip('/')
        source = abs_path
    else:
        parent_rel = os.path.dirname(rel)
        dest_path = f"{dest_root}/{parent_rel}".rstrip('/')
        source = abs_path

    copy_cmd = f'rclone copy --config ./rclone.conf "{source}" "{dest_path}"'
    proc = await asyncio.create_subprocess_shell(
        copy_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        try:
            LOGGER.debug(f"Rclone copy failed: {err.decode().strip()}")
        except Exception:
            pass
        return None, None, None

    rclone_link = None
    index_link = None
    if bot_set.link_options in ['RCLONE', 'Both']:
        link_target = f"{dest_root}/{rel}".rstrip('/')
        link_cmd = f'rclone link --config ./rclone.conf "{link_target}"'
        t2 = await asyncio.create_subprocess_shell(
            link_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        so, se = await t2.communicate()
        if t2.returncode == 0:
            try:
                rclone_link = so.decode().strip()
            except Exception:
                rclone_link = None
    if bot_set.link_options in ['Index', 'Both'] and Config.INDEX_LINK:
        index_link = f"{Config.INDEX_LINK}/{rel}".replace(' ', '%20')

    remote = ''
    base = ''
    try:
        if dest_root and ':' in dest_root:
            remote, base = dest_root.split(':', 1)
            base = base.strip('/')
        else:
            remote = (getattr(bot_set, 'rclone_remote', '') or dest_root or '').rstrip(':')
            base = ''
    except Exception:
        remote = (getattr(bot_set, 'rclone_remote', '') or (Config.RCLONE_DEST.split(':',1)[0] if Config.RCLONE_DEST and ':' in Config.RCLONE_DEST else '')).rstrip(':')
        base = ''

    info = {
        'remote': remote,
        'base': base,
        'path': rel,
        'is_dir': is_dir
    }
    return rclone_link, index_link, info


async def _post_manage(user, remote_info: dict):
    try:
        import uuid
        token = uuid.uuid4().hex[:10]
        rel = remote_info.get('path') or ''
        is_dir = bool(remote_info.get('is_dir'))
        if is_dir:
            src_path = rel
            src_file = None
        else:
            src_path = os.path.dirname(rel)
            src_file = rel
        state = await conversation_state.get(user['user_id']) or {"stage": None, "data": {}}
        ctx = state.get('data', {})
        manage_map = dict(ctx.get('rclone_manage_map') or {})
        manage_map[token] = {
            'src_remote': remote_info.get('remote'),
            'base': remote_info.get('base'),
            'src_path': src_path,
            'src_file': src_file,
            'dst_remote': None,
            'dst_path': '',
            'cc_mode': 'copy',
            'src_page': 0
        }
        await conversation_state.update(user['user_id'], rclone_manage_map=manage_map)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📂 Browse uploaded (Copy/Move)", callback_data=f"rcloneManageStart|{token}")]])
        await send_message(user, "Manage the uploaded item:", markup=kb)
    except Exception:
        pass


async def track_upload(metadata, user, index: int = None, total: int = None):
    base_path = await _get_tidal_ng_base_path(user['user_id'])
    if bot_set.upload_mode == 'Telegram':
        reporter = user.get('progress')
        if reporter:
            try:
                await reporter.set_stage("Uploading")
            except Exception:
                pass
        await send_message(
            user,
            metadata['filepath'],
            'audio',
            caption=await format_string(
                "🎵 **{title}**\n👤 {artist}\n🎧 {provider}",
                {
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Tidal NG')
                }
            ),
            meta={
                'duration': metadata.get('duration', 0),
                'artist': metadata.get('artist', 'Unknown Artist'),
                'title': metadata.get('title', 'Unknown'),
                'thumbnail': metadata.get('thumbnail')
            },
            file_index=index,
            total_files=total,
        )
    else:
        r_link, i_link, info = await _rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Tidal NG'),
                'r_link': r_link
            }
        )
        if i_link:
            text += f"\n📁 [Index Link]({i_link})"
        await send_message(user, text)
        await _post_manage(user, info)
    # Cleanup
    try:
        os.remove(metadata['filepath'])
    except Exception:
        pass
    if metadata.get('thumbnail'):
        try:
            os.remove(metadata['thumbnail'])
        except Exception:
            pass


async def music_video_upload(metadata, user):
    base_path = await _get_tidal_ng_base_path(user['user_id'])
    if bot_set.upload_mode == 'Telegram':
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
                    'provider': metadata.get('provider', 'Tidal NG')
                }
            ),
            meta=metadata,
        )
    else:
        r_link, i_link, info = await _rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎬 **{title}**\n👤 {artist}\n🎧 {provider} Music Video\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Tidal NG'),
                'r_link': r_link
            }
        )
        if i_link:
            text += f"\n📁 [Index Link]({i_link})"
        await send_message(user, text)
        await _post_manage(user, info)
    # Cleanup
    try:
        os.remove(metadata['filepath'])
    except Exception:
        pass
    if metadata.get('thumbnail'):
        try:
            os.remove(metadata['thumbnail'])
        except Exception:
            pass


async def album_upload(metadata, user):
    base_path = await _get_tidal_ng_base_path(user['user_id'])
    if bot_set.upload_mode == 'Telegram':
        if getattr(bot_set, 'album_zip', False):
            # Always create a single descriptive zip for Telegram mode
            zp = await create_tidal_ng_zip(metadata['folderpath'], user['user_id'], metadata)
            zip_paths = [zp]
            caption = await format_string(
                "💿 **{album}**\n👤 {artist}\n🎧 {provider}",
                {
                    'album': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Tidal NG')
                }
            )
            for idx, zp in enumerate(zip_paths, start=1):
                await send_message(user, zp, 'doc', caption=caption)
                try:
                    os.remove(zp)
                except Exception:
                    pass
        else:
            tracks = metadata.get('tracks') or metadata.get('items', [])
            total_tracks = len(tracks)
            for idx, track in enumerate(tracks, start=1):
                await track_upload(track, user, index=idx, total=total_tracks)
    else:
        r_link, i_link, info = await _rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "💿 **{album}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'album': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Tidal NG'),
                'r_link': r_link
            }
        )
        if i_link:
            text += f"\n📁 [Index Link]({i_link})"
        if metadata.get('poster_msg'):
            await edit_message(metadata['poster_msg'], text)
        else:
            await send_message(user, text)
        await _post_manage(user, info)
    # Cleanup
    shutil.rmtree(metadata['folderpath'])


async def playlist_upload(metadata, user):
    base_path = await _get_tidal_ng_base_path(user['user_id'])
    if bot_set.upload_mode == 'Telegram':
        if getattr(bot_set, 'playlist_zip', False):
            zp = await create_tidal_ng_zip(metadata['folderpath'], user['user_id'], metadata)
            caption = await format_string(
                "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist",
                {
                    'title': metadata['title'],
                    'artist': metadata.get('artist', 'Various Artists'),
                    'provider': metadata.get('provider', 'Tidal NG')
                }
            )
            await send_message(user, zp, 'doc', caption=caption)
            try:
                os.remove(zp)
            except Exception:
                pass
        else:
            tracks = metadata.get('tracks') or metadata.get('items', [])
            total_tracks = len(tracks)
            for idx, track in enumerate(tracks, start=1):
                await track_upload(track, user, index=idx, total=total_tracks)
    else:
        r_link, i_link, info = await _rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata.get('artist', 'Various Artists'),
                'provider': metadata.get('provider', 'Tidal NG'),
                'r_link': r_link
            }
        )
        if i_link:
            text += f"\n📁 [Index Link]({i_link})"
        await send_message(user, text)
        await _post_manage(user, info)
    # Cleanup
    shutil.rmtree(metadata['folderpath'])

