from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.switch_inline_query_chosen_chat import SwitchInlineQueryChosenChat

def main_menu(lang: str, has_active: bool=False, has_history: bool=False) -> InlineKeyboardMarkup:
    t = {"ru": ("⚙️ Настройки", "👛 Кошелёк", "📦 Создать сделку", "🟡 Текущая сделка", "🗂 История сделок"), "en": ("⚙️ Settings", "👛 Wallet", "📦 Create deal", "🟡 Current deal", "🗂 Deal history")}[lang]
    rows = [[InlineKeyboardButton(text=t[0], callback_data="settings")],[InlineKeyboardButton(text=t[1], callback_data="wallet")],[InlineKeyboardButton(text=t[2], callback_data="create")]]
    if has_active:
        rows.append([InlineKeyboardButton(text=t[3], callback_data="current")])
    if has_history:
        rows.append([InlineKeyboardButton(text=t[4], callback_data="history")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_to_menu(lang: str) -> InlineKeyboardMarkup:
    txt = "↩️ В меню" if lang == "ru" else "↩️ Menu"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=txt, callback_data="menu")]])

def lang_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],[InlineKeyboardButton(text="↩️ В меню / Menu", callback_data="menu")]])

def create_nav(lang: str, step: int) -> InlineKeyboardMarkup:
    prev_txt = "⬅️ Пред" if lang=="ru" else "⬅️ Prev"
    next_txt = "➡️ След" if lang=="ru" else "➡️ Next"
    cancel_txt = "⛔️ Отменить" if lang=="ru" else "⛔️ Cancel"
    menu_txt = "↩️ В меню" if lang=="ru" else "↩️ Menu"
    rows = []
    if step > 1:
        rows.append([InlineKeyboardButton(text=prev_txt, callback_data="create_prev")])
    rows.append([InlineKeyboardButton(text=next_txt, callback_data="create_next")])
    rows.append([InlineKeyboardButton(text=cancel_txt, callback_data="create_cancel")])
    rows.append([InlineKeyboardButton(text=menu_txt, callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def final_actions(lang: str, deal_id: str) -> InlineKeyboardMarkup:
    send_txt = "📩 Отправить продавцу" if lang=="ru" else "📩 Send to seller"
    cancel_txt = "⛔️ Отменить ордер" if lang=="ru" else "⛔️ Cancel order"
    menu_txt = "↩️ В меню" if lang=="ru" else "↩️ Menu"
    sic = SwitchInlineQueryChosenChat(query=f"deal_{deal_id}", allow_user_chats=True, allow_bot_chats=False, allow_group_chats=True, allow_channel_chats=False)
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=send_txt, switch_inline_query_chosen_chat=sic)],[InlineKeyboardButton(text=cancel_txt, callback_data=f"deal:{deal_id}:stop")],[InlineKeyboardButton(text=menu_txt, callback_data="menu")]])

def seller_controls(lang: str, deal_id: str) -> InlineKeyboardMarkup:
    texts = {"ru": ("⛔️ Остановить ордер", "✅ Я перевёл(а) подарки"), "en": ("⛔️ Stop order", "✅ I sent the gifts")}[lang]
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=texts[0], callback_data=f"deal:{deal_id}:stop")],[InlineKeyboardButton(text=texts[1], callback_data=f"deal:{deal_id}:confirm")]])
