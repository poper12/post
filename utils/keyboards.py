from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✍️ Create Post", callback_data="menu:create")],
            [
                InlineKeyboardButton("🗓 Scheduled Posts", callback_data="menu:scheduled"),
                InlineKeyboardButton("✏️ Edit Post", callback_data="menu:edit"),
            ],
            [
                InlineKeyboardButton("📊 Channel Stats", callback_data="menu:stats"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
            ],
            [InlineKeyboardButton("📡 Channels", callback_data="menu:channels")],
        ]
    )


def back_button(target="menu:root"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Back", callback_data=target)]])


def channel_list_kb(channels, callback_prefix, extra_row=None):
    rows = []
    for ch in channels:
        label = ch.get("title") or str(ch["chat_id"])
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"{callback_prefix}:{ch['chat_id']}")]
        )
    if extra_row:
        rows.append(extra_row)
    rows.append([InlineKeyboardButton("« Back", callback_data="menu:root")])
    return InlineKeyboardMarkup(rows)


def channels_menu_kb(channels):
    rows = [
        [InlineKeyboardButton(ch.get("title") or str(ch["chat_id"]), callback_data=f"ch:view:{ch['chat_id']}")]
        for ch in channels
    ]
    rows.append([InlineKeyboardButton("➕ Add Channel", callback_data="ch:add")])
    rows.append([InlineKeyboardButton("« Back", callback_data="menu:root")])
    return InlineKeyboardMarkup(rows)


def channel_view_kb(chat_id):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑 Remove Channel", callback_data=f"ch:remove:{chat_id}")],
            [InlineKeyboardButton("« Back", callback_data="menu:channels")],
        ]
    )


def post_preview_kb(post_id, is_scheduled=False):
    rows = [
        [
            InlineKeyboardButton("✅ Send Now", callback_data=f"post:send:{post_id}"),
            InlineKeyboardButton("🗓 Schedule", callback_data=f"post:schedule:{post_id}"),
        ],
        [
            InlineKeyboardButton("🔘 Add Button", callback_data=f"post:addbtn:{post_id}"),
            InlineKeyboardButton("♻️ Clear Buttons", callback_data=f"post:clearbtn:{post_id}"),
        ],
        [
            InlineKeyboardButton("✏️ Re-edit Content", callback_data=f"post:reedit:{post_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"post:cancel:{post_id}"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def sent_kb(view_url):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("View Post in Channel ↗", url=view_url)]]
    )


def settings_kb(settings):
    pm = settings.get("parse_mode", "HTML")
    silent = "ON" if settings.get("silent") else "OFF"
    preview = "ON" if settings.get("link_preview") else "OFF"
    reactions = "ON" if settings.get("default_reactions") else "OFF"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Auto Formatting: {pm}", callback_data="set:parse_mode")],
            [InlineKeyboardButton(f"Silent Broadcast: {silent}", callback_data="set:silent")],
            [InlineKeyboardButton(f"Link Previews: {preview}", callback_data="set:link_preview")],
            [InlineKeyboardButton(f"Default Reactions: {reactions}", callback_data="set:default_reactions")],
            [InlineKeyboardButton("« Back", callback_data="menu:root")],
        ]
    )


def scheduled_list_kb(posts):
    rows = []
    for p in posts:
        snippet = (p["content"].get("text") or "(media)")[:30]
        rows.append(
            [InlineKeyboardButton(f"🗓 {snippet}", callback_data=f"sched:view:{p['post_id']}")]
        )
    rows.append([InlineKeyboardButton("« Back", callback_data="menu:root")])
    return InlineKeyboardMarkup(rows)


def scheduled_view_kb(post_id):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❌ Cancel Schedule", callback_data=f"sched:cancel:{post_id}")],
            [InlineKeyboardButton("« Back", callback_data="menu:scheduled")],
        ]
    )


def sent_posts_kb(posts):
    rows = []
    for p in posts:
        snippet = (p["content"].get("text") or "(media)")[:30]
        rows.append(
            [InlineKeyboardButton(f"✏️ {snippet}", callback_data=f"edit:view:{p['post_id']}")]
        )
    rows.append([InlineKeyboardButton("« Back", callback_data="menu:root")])
    return InlineKeyboardMarkup(rows)


def edit_view_kb(post_id):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✏️ Edit Text/Caption", callback_data=f"edit:text:{post_id}")],
            [InlineKeyboardButton("🗑 Delete From Channel", callback_data=f"edit:delete:{post_id}")],
            [InlineKeyboardButton("« Back", callback_data="menu:edit")],
        ]
    )


def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="op:cancel")]])
