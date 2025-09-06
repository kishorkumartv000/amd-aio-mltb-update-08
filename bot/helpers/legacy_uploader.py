import os
from config import Config

from ..settings import bot_set
from .message import send_message, edit_message
from .utils import *
from .uploader import rclone_upload as modern_rclone_upload, _post_rclone_manage_button

#
#
#  TASK HANDLER
#
#

async def track_upload(metadata, user, disable_link=False):
    if bot_set.upload_mode == 'Local':
        await local_upload(metadata, user)
    elif bot_set.upload_mode == 'Telegram':
        await telegram_upload(metadata, user)
    else:
        rclone_link, index_link, remote_info = await rclone_upload(user, metadata['filepath'])
        if not disable_link:
            await post_simple_message(user, metadata, rclone_link, index_link)
        if remote_info:
            await _post_rclone_manage_button(user, remote_info)

    try:
        os.remove(metadata['filepath'])
    except FileNotFoundError:
        pass



async def album_upload(metadata, user):
    if bot_set.upload_mode == 'Local':
        await local_upload(metadata, user)
    elif bot_set.upload_mode == 'Telegram':
        if bot_set.album_zip:
            for item in metadata['folderpath']:
                await send_message(user,item,'doc',
                    caption=await create_simple_text(metadata, user)
                )
        else:
            await batch_telegram_upload(metadata, user)
    else:
        rclone_link, index_link, remote_info = await rclone_upload(user, metadata['folderpath'])
        if metadata['poster_msg']:
            try:
                await edit_art_poster(metadata, user, rclone_link, index_link, await format_string(lang.s.ALBUM_TEMPLATE, metadata, user))
            except MessageNotModified:
                pass
        else:
            await post_simple_message(user, metadata, rclone_link, index_link)
        if remote_info:
            await _post_rclone_manage_button(user, remote_info)

    await cleanup(None, metadata)


async def artist_upload(metadata, user):
    if bot_set.upload_mode == 'Local':
        await local_upload(metadata, user)
    elif bot_set.upload_mode == 'Telegram':
        if bot_set.artist_zip:
            for item in metadata['folderpath']:
                await send_message(user,item,'doc',
                    caption=await create_simple_text(metadata, user)
                )
        else:
            pass # artist telegram uploads are handled by album fucntion
    else:
        rclone_link, index_link, remote_info = await rclone_upload(user, metadata['folderpath'])
        if metadata['poster_msg']:
            try:
                await edit_art_poster(metadata, user, rclone_link, index_link, await format_string(lang.s.ARTIST_TEMPLATE, metadata, user))
            except MessageNotModified:
                pass
        else:
            await post_simple_message(user, metadata, rclone_link, index_link)
        if remote_info:
            await _post_rclone_manage_button(user, remote_info)

    await cleanup(None, metadata)



async def playlist_upload(metadata, user):
    if bot_set.upload_mode == 'Local':
        await local_upload(metadata, user)
    elif bot_set.upload_mode == 'Telegram':
        if bot_set.playlist_zip:
            for item in metadata['folderpath']:
                await send_message(user,item,'doc',
                    caption=await create_simple_text(metadata, user)
                )
        else:
            await batch_telegram_upload(metadata, user)
    else:
        if bot_set.playlist_sort and not bot_set.playlist_zip:
            if bot_set.disable_sort_link:
                # Upload the whole base folder; ignore returned links
                try:
                    _, _, remote_info = await rclone_upload(user, f"{Config.DOWNLOAD_BASE_DIR}/{user['r_id']}/")
                    if remote_info:
                        await _post_rclone_manage_button(user, remote_info)
                except Exception:
                    pass
            else:
                for track in metadata['tracks']:
                    try:
                        rclone_link, index_link, remote_info = await rclone_upload(user, track['filepath'])
                        if not bot_set.disable_sort_link:
                            await post_simple_message(user, track, rclone_link, index_link)
                        if remote_info:
                            await _post_rclone_manage_button(user, remote_info)
                    except ValueError: # might try to upload track which is not available
                        pass
        else:
            rclone_link, index_link, remote_info = await rclone_upload(user, metadata['folderpath'])
            if metadata['poster_msg']:
                try:
                    await edit_art_poster(metadata, user, rclone_link, index_link, await format_string(lang.s.PLAYLIST_TEMPLATE, metadata, user))
                except MessageNotModified:
                    pass
            else:
                await post_simple_message(user, metadata, rclone_link, index_link)
            if remote_info:
                await _post_rclone_manage_button(user, remote_info)

#
#
#  CORE
#
#

async def rclone_upload(user, realpath):
    """
    Delegate Rclone upload to the modern uploader with copy scope support and manage button context.
    Returns: (rclone_link, index_link, remote_info)
    """
    base_path = f"{Config.LEGACY_DOWNLOAD_BASE_DIR}/{user['r_id']}/"
    return await modern_rclone_upload(user, realpath, base_path)


async def local_upload(metadata, user):
    """
    Copies directory to local storage and merges contents if the destination exists.
    Args:
        metadata: metadata dict of item
        user: user details
    """
    to_move = f"{Config.DOWNLOAD_BASE_DIR}/{user['r_id']}/{metadata['provider']}"
    destination = os.path.join(Config.LOCAL_STORAGE, os.path.basename(to_move))

    # If the destination directory exists, merge contents
    if os.path.exists(destination):
        for item in os.listdir(to_move):
            src_item = os.path.join(to_move, item)
            dest_item = os.path.join(destination, item)

            # If it's a file, copy it; if it's a directory, use copytree
            if os.path.isdir(src_item):
                if not os.path.exists(dest_item):
                    shutil.copytree(src_item, dest_item)
            else:
                shutil.copy2(src_item, dest_item)
    else:
        shutil.copytree(to_move, destination)

    shutil.rmtree(to_move)


async def telegram_upload(track, user):
    """
    Only upload a single track
    Args:
        track: track metadata
        """
    await send_message(user, track['filepath'], 'audio', meta=track)


async def batch_telegram_upload(metadata, user):
    """
    Args:
        metadata: full metadata
        user: user details
    """
    if metadata['type'] == 'album' or metadata['type'] == 'playlist':
        for track in metadata['tracks']:
            try:
                await telegram_upload(track, user)
            except FileNotFoundError:
                pass
    elif metadata['type'] == 'artist':
        for album in metadata['albums']:
            for track in album['tracks']:
                await telegram_upload(track, user)
