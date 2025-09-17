import os
from pyrogram.types import InlineKeyboardButton

# --- Constants ---
ITEMS_PER_PAGE = 20  # Number of items to show per page

def get_human_readable_size(size_in_bytes: int) -> str:
    """Converts a size in bytes to a human-readable format (KB, MB, GB)."""
    if size_in_bytes is None:
        return "0 B"
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size_in_bytes /= 1024.0
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
    return f"{size_in_bytes:.2f} PB"

async def build_file_browser(path: str, page: int = 0, back_callback: str = None) -> tuple[str, list[list[InlineKeyboardButton]]]:
    """
    Builds the text and button layout for a file browser at a given path.

    Args:
        path (str): The absolute path of the directory to browse.
        page (int): The page number for pagination.
        back_callback (str, optional): The callback data for the 'Back' button.

    Returns:
        A tuple containing:
        - The message text (including the current path).
        - A list of lists of InlineKeyboardButtons for the UI.
    """
    if not os.path.isdir(path):
        return f"❌ **Error:**\nDirectory not found:\n`{path}`", [[InlineKeyboardButton("🔙 Back", callback_data="noop")]]

    try:
        items = sorted(os.listdir(path))
    except OSError as e:
        return f"❌ **Error:**\nCould not access directory:\n`{e}`", [[InlineKeyboardButton("🔙 Back", callback_data="noop")]]

    directories = [d for d in items if os.path.isdir(os.path.join(path, d))]
    files = [f for f in items if os.path.isfile(os.path.join(path, f))]

    # Combine and sort: folders first, then files
    sorted_items = directories + files

    # Pagination
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    paginated_items = sorted_items[start_index:end_index]

    buttons = []
    for item_name in paginated_items:
        item_path = os.path.join(path, item_name)
        if os.path.isdir(item_path):
            buttons.append([InlineKeyboardButton(f"📁 {item_name}", callback_data=f"fm_browse:{item_path}")])
        else:
            try:
                size = os.path.getsize(item_path)
                size_str = get_human_readable_size(size)
                buttons.append([InlineKeyboardButton(f"📄 {item_name} ({size_str})", callback_data=f"fm_select:{item_path}")])
            except OSError:
                buttons.append([InlineKeyboardButton(f"📄 {item_name} (Error)", callback_data=f"fm_select:{item_path}")])

    # --- Navigation Buttons ---
    nav_buttons = []
    total_pages = (len(sorted_items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if total_pages > 1:
        page_nav = []
        if page > 0:
            page_nav.append(InlineKeyboardButton("« Prev", callback_data=f"fm_browse:{path}:{page-1}"))
        page_nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            page_nav.append(InlineKeyboardButton("Next »", callback_data=f"fm_browse:{path}:{page+1}"))
        nav_buttons.append(page_nav)

    control_nav = []
    # Add an "Up" button if not at the root
    if os.path.dirname(path) != path:
        parent_path = os.path.dirname(path)
        control_nav.append(InlineKeyboardButton("⬆️ Up", callback_data=f"fm_browse:{parent_path}"))

    control_nav.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"fm_browse:{path}:{page}"))
    nav_buttons.append(control_nav)

    # Add the contextual back button if provided
    if back_callback:
        nav_buttons.append([InlineKeyboardButton("🔙 Back", callback_data=back_callback)])

    buttons.extend(nav_buttons)

    text = f"**📂 File Manager**\n\n**Current Path:**\n`{path}`"
    return text, buttons
