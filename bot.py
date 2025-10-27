import asyncio
import secrets
import random
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# ---------- CONFIG ----------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
ADMIN_ID     = int(os.getenv("ADMIN_ID", "0"))  # Укажи свой ID в .env

# ---------- STATES ----------
class SetWallet(StatesGroup):
    waiting_wallet = State()

class CreateDeal(StatesGroup):
    entering = State()

class SellerOnboarding(StatesGroup):
    waiting_wallet = State()

class AdminFlow(StatesGroup):
    waiting_user_for_log   = State()
    waiting_user_for_purge = State()

# ---------- TEXTS ----------
def t(lang: str, key: str) -> str:
    RU = {
        "hello": (
            "👋 <b>MoonGarant</b> — ваш надёжный выбор для сделок с цифровыми подарками и NFT в Telegram.\n\n"
            "• Создавайте ордера за пару шагов\n"
            "• Делитесь безопасной ссылкой для продавца\n"
            "• Авто-таймеры: ссылка — 30 мин, подтверждение — 15 мин\n"
            "• Красивые карточки и удобные кнопки\n\n"
            "Выберите действие ниже:"
        ),
        "menu": "🏠 <b>Меню</b>",
        "settings": "<b>⚙️ Настройки</b>\nВыберите язык интерфейса:",
        "wallet_enter": "👛 <b>Кошелёк</b>\nОтправьте адрес вашего TON-кошелька.",
        "wallet_saved": "✅ Кошелёк сохранён: <code>{addr}</code>",
        "wallet_invalid": "⚠️ Похоже, это не TON-адрес. Попробуйте снова.",
        "deal_expired": "⏳ Срок действия ордера истёк.",

        # Seller onboarding
        "seller_intro": "👋 Вы приглашены к сделке в <b>MoonGarant</b>. Сначала отправьте ваш TON-кошелёк.",
        "seller_wallet_ok": "✅ Адрес кошелька принят.\nНажмите <b>«Принять ордер»</b>, чтобы начать.",
        "accept_btn": "✅ Принять ордер",
        "seller_details": (
            "🧾 <b>Ордер</b>\n"
            "<b>Название:</b> {title}\n"
            "<b>Описание:</b> {desc}\n"
            "<b>Цена:</b> {price} TON\n"
            "<b>Отправить NFT (покупателю):</b> {target}\n\n"
            "После передачи нажмите «Я перевёл(а) подарки»."
        ),
        "seller_stopped": "⛔️ Продавец остановил ордер. Сделка отменена.",
        "seller_confirmed_wait": "✅ Отправка подарков подтверждена.\n⌛ <b>Ожидайте оплату, не более 15 минут...</b>",
        "seller_final_needed": "💳 Покупатель отметил оплату.\nЕсли получили средства — нажмите «Подтвердить получение оплаты».",
        "seller_final_done": "🎉 Оплата подтверждена. Сделка завершена!",

        # Buyer side
        "buyer_notif_confirmed": "✅ Продавец подтвердил отправку по ордеру <b>{title}</b>.",
        "buyer_pay_prompt": (
            "🧾 <b>Детали ордера</b>\n"
            "<b>Название:</b> {title}\n"
            "<b>Описание:</b> {desc}\n"
            "<b>Цена:</b> {price} TON\n"
            "<b>Куда отправить NFT:</b> {target}\n\n"
            "💳 <b>Оплата</b>\n"
            "<b>Кошелёк продавца:</b> <code>{seller_wallet}</code>\n"
            "<b>Комментарий/MEMO:</b> <code>{memo}</code>\n\n"
            "⚠️ <b>Внимание!</b> Укажите <b>комментарий/MEMO</b> при переводе: <code>{memo}</code> — иначе оплата не будет засчитана!"
        ),
        "buyer_wait_confirm": "⌛ Ожидайте подтверждения получения оплаты продавцом.",
        "buyer_final_done": "✅ Продавец подтвердил отправку по ордеру <b>{title}</b>.",

        # Create flow prompts
        "ask_title": "Введите <b>название</b> ордера.",
        "ask_desc": "Введите <b>описание</b> ордера (содержание подарков).",
        "ask_price": "Введите <b>цену</b> в TON (например: <code>12.5</code>).",
        "ask_user": "Укажите <b>@username</b> покупателя.",
        "bad_price": "⚠️ Нужно число (можно с точкой).",
        "bad_user": "⚠️ Укажите username в формате <code>@username</code>.",

        # Final card (buyer side)
        "final": (
            "🧾 <b>Детали ордера</b>\n\n"
            "<b>Название:</b> {title}\n"
            "<b>Описание:</b> {desc}\n"
            "<b>Цена:</b> {price} TON\n"
            "<b>Куда отправить NFT:</b> {target}\n\n"
            "После перехода продавца по ссылке у него будет <b>15 минут</b> на подтверждение отправки.\n\n"
            "<b>Ссылка:</b> {link}"
        ),

        "current_title": "🟡 <b>Текущая сделка</b>",
        "history_title": "🗂 <b>История сделок</b> (последние 10)",
        "no_history": "Пока нет завершённых сделок.",

        # Buttons
        "copy_memo": "📋 Скопировать MEMO",
        "confirm_paid": "✅ Подтвердить оплату",
        "confirm_receive": "✅ Подтвердить получение оплаты",

        # Admin
        "admin_title": "🛡️ <b>Admin Panel</b>\nВыберите действие:",
        "admin_btn_recent": "📊 Последние сделки",
        "admin_btn_chatlog": "🕓 История чата пользователя",
        "admin_btn_purge": "🧹 Удалить сообщения пользователя",
        "admin_back": "↩️ Назад в панель",
        "admin_enter_user": "Отправьте @username или числовой ID пользователя.",
        "admin_no_log": "Нет записей чата для этого пользователя.",
        "admin_purged": "🧹 Удаление завершено. Что смог — удалил.",
        "not_admin": "Доступ ограничен.",
    }
    EN = RU
    return (RU if lang == "ru" else EN)[key]

# ---------- MEMORY ----------
class Memory:
    def __init__(self):
        self.users: Dict[int, dict] = {}
        self.usernames: Dict[int, str] = {}
        self.deals: Dict[str, dict] = {}
        self.history: Dict[int, List[dict]] = {}

        self.user_msgs: Dict[int, List[int]] = {}      # per-chat: messages to clean on menu
        self.panel_id: Dict[int, int] = {}             # per-chat panel message id

        self.chatlog: Dict[int, List[Tuple[datetime, str, str]]] = {}  # user_id -> [(ts, who, text)]
        self.all_msgs: Dict[int, List[Tuple[int, int]]] = {}           # user_id -> [(chat_id, msg_id)]

        self.wip: Dict[int, dict] = {}

memory = Memory()

def now() -> datetime:
    return datetime.now(timezone.utc)

def get_lang(uid: int) -> str:
    return memory.users.get(uid, {}).get("lang") or "ru"

def set_lang(uid: int, lang: str):
    memory.users.setdefault(uid, {})["lang"] = lang

def set_wallet(uid: int, w: str):
    memory.users.setdefault(uid, {})["wallet"] = w

def get_wallet(uid: int) -> Optional[str]:
    return memory.users.get(uid, {}).get("wallet")

def set_warning(uid: int, mid: Optional[int]):
    memory.users.setdefault(uid, {})["warn_id"] = mid

def pop_warning(uid: int) -> Optional[int]:
    d = memory.users.get(uid, {})
    mid = d.get("warn_id")
    if "warn_id" in d:
        del d["warn_id"]
    return mid

def is_ton_address(text: str) -> bool:
    if not text:
        return False
    s = text.strip()
    if s.lower().startswith("ton://"):
        return True
    return 48 <= len(s) <= 66 and all(c.isalnum() or c in "-_:" for c in s)

def has_active_deal(uid: int) -> bool:
    for d in memory.deals.values():
        if d.get("creator_id") == uid and d.get("status") in {"new", "await_payment", "await_seller_final"} and now() < d.get("expires_at", now()):
            return True
    return False

def has_history(uid: int) -> bool:
    return bool(memory.history.get(uid))

def is_admin(uid: int) -> bool:
    return ADMIN_ID and uid == ADMIN_ID

def remember_username(u) -> None:
    if u:
        if getattr(u, "username", None):
            memory.usernames[u.id] = f"@{u.username}"
        else:
            memory.usernames.setdefault(u.id, f"id{u.id}")

# ---------- KEYBOARDS ----------
def main_menu(lang: str, has_active: bool = False, has_history_: bool = False, uid: Optional[int] = None) -> InlineKeyboardMarkup:
    t_ru = ("⚙️ Настройки", "👛 Кошелёк", "📦 Создать сделку", "🟡 Текущая сделка", "🗂 История сделок")
    t_en = ("⚙️ Settings", "👛 Wallet", "📦 Create deal", "🟡 Current deal", "🗂 Deal history")
    t_local = t_ru if lang == "ru" else t_en
    rows = [
        [InlineKeyboardButton(text=t_local[0], callback_data="settings")],
        [InlineKeyboardButton(text=t_local[1], callback_data="wallet")],
        [InlineKeyboardButton(text=t_local[2], callback_data="create")],
    ]
    if has_active:
        rows.append([InlineKeyboardButton(text=t_local[3], callback_data="current")])
    if has_history_:
        rows.append([InlineKeyboardButton(text=t_local[4], callback_data="history")])
    if uid and is_admin(uid):
        rows.append([InlineKeyboardButton(text="🛡️ Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_to_menu(lang: str) -> InlineKeyboardMarkup:
    txt = "↩️ В меню" if lang == "ru" else "↩️ Menu"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=txt, callback_data="menu")]])

def lang_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            ],
            [InlineKeyboardButton(text="↩️ В меню / Menu", callback_data="menu")],
        ]
    )

def create_nav_prev_only(lang: str, step: int) -> InlineKeyboardMarkup:
    prev_txt = "⬅️ Пред" if lang == "ru" else "⬅️ Prev"
    cancel_txt = "⛔️ Отменить" if lang == "ru" else "⛔️ Cancel"
    menu_txt = "↩️ В меню" if lang == "ru" else "↩️ Menu"
    rows = []
    if step > 1:
        rows.append([InlineKeyboardButton(text=prev_txt, callback_data="create_prev")])
    rows.append([InlineKeyboardButton(text=cancel_txt, callback_data="create_cancel")])
    rows.append([InlineKeyboardButton(text=menu_txt, callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def final_actions(lang: str, deal_id: str) -> InlineKeyboardMarkup:
    send_txt = "📩 Отправить продавцу" if lang == "ru" else "📩 Send to seller"
    cancel_txt = "⛔️ Отменить ордер" if lang == "ru" else "⛔️ Cancel order"
    menu_txt = "↩️ В меню" if lang == "ru" else "↩️ Menu"
    btn_send = InlineKeyboardButton(
        text=send_txt,
        switch_inline_query_chosen_chat={"query": f"deal_{deal_id}", "allow_user_chats": True,
                                         "allow_bot_chats": False, "allow_group_chats": True,
                                         "allow_channel_chats": False}
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn_send],
        [InlineKeyboardButton(text=cancel_txt, callback_data=f"deal:{deal_id}:stop")],
        [InlineKeyboardButton(text=menu_txt, callback_data="menu")],
    ])

def seller_controls(lang: str, deal_id: str) -> InlineKeyboardMarkup:
    texts = ("⛔️ Остановить ордер", "✅ Я перевёл(а) подарки") if lang == "ru" else ("⛔️ Stop order", "✅ I sent the gifts")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[0], callback_data=f"deal:{deal_id}:stop")],
        [InlineKeyboardButton(text=texts[1], callback_data=f"deal:{deal_id}:confirm")],
    ])

def accept_order_kb(lang: str, deal_id: str) -> InlineKeyboardMarkup:
    txt = t(lang, "accept_btn")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=txt, callback_data=f"deal:{deal_id}:accept")],
        [InlineKeyboardButton(text=("↩️ В меню" if lang == "ru" else "↩️ Menu"), callback_data="menu")]
    ])

def buyer_pay_kb(lang: str, deal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "copy_memo"), callback_data=f"memo:{deal_id}")],
        [InlineKeyboardButton(text=t(lang, "confirm_paid"), callback_data=f"paid:{deal_id}")],
        [InlineKeyboardButton(text=("↩️ В меню" if lang == "ru" else "↩️ Menu"), callback_data="menu")],
    ])

def seller_final_kb(lang: str, deal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "confirm_receive"), callback_data=f"finish:{deal_id}")],
        [InlineKeyboardButton(text=("↩️ В меню" if lang == "ru" else "↩️ Menu"), callback_data="menu")],
    ])

def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("ru","admin_btn_recent"), callback_data="admin_recent")],
        [InlineKeyboardButton(text=t("ru","admin_btn_chatlog"), callback_data="admin_chatlog")],
        [InlineKeyboardButton(text=t("ru","admin_btn_purge"), callback_data="admin_purge")],
        [InlineKeyboardButton(text=t("ru","admin_back"), callback_data="admin_back_menu")]
    ])

def admin_back_only_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("ru","admin_back"), callback_data="admin_back")]
    ])

# ---------- PANEL / LOG ----------
async def show_panel(chat_id: int, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None):
    # лог переписки бота
    memory.chatlog.setdefault(chat_id, []).append((now(), "bot", text))
    mid = memory.panel_id.get(chat_id)
    try:
        if mid:
            msg = await bot.edit_message_text(
                chat_id=chat_id,
                message_id=mid,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            # учтём обновлённую панель в all_msgs (чтобы можно было удалить)
            memory.panel_id[chat_id] = msg.message_id
            memory.all_msgs.setdefault(chat_id, []).append((chat_id, msg.message_id))
            return
    except Exception:
        pass
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    memory.panel_id[chat_id] = msg.message_id
    memory.all_msgs.setdefault(chat_id, []).append((chat_id, msg.message_id))

async def add_user_msg(m: Message):
    memory.user_msgs.setdefault(m.chat.id, []).append(m.message_id)
    memory.all_msgs.setdefault(m.from_user.id, []).append((m.chat.id, m.message_id))
    memory.chatlog.setdefault(m.from_user.id, []).append((now(), "user", m.text or ""))

async def clear_flow_messages(chat_id: int):
    for mid in memory.user_msgs.get(chat_id, []):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass
    memory.user_msgs[chat_id] = []

# ---------- BOT ----------
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

async def clear_warn_if_any(uid: int, cid: int):
    wid = pop_warning(uid)
    if wid:
        try:
            await bot.delete_message(cid, wid)
        except Exception:
            pass

# ---------- EXPIRY WORKER ----------
async def expiry_worker():
    while True:
        await asyncio.sleep(5)
        for deal_id, d in list(memory.deals.items()):
            if d.get("status") in ("done", "stopped"):
                continue
            if d.get("expires_at") and now() > d["expires_at"]:
                try:
                    # трекаем уведомление, чтобы админ-пурж мог удалить
                    msg = await bot.send_message(d["creator_id"], t(d.get("lang", "ru"), "deal_expired"))
                    memory.all_msgs.setdefault(d["creator_id"], []).append((d["creator_id"], msg.message_id))
                except Exception:
                    pass
                memory.deals.pop(deal_id, None)

# ---------- START ----------
@dp.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    # Сохраняем и /start тоже, чтобы потом можно было удалить при тотальной чистке
    memory.all_msgs.setdefault(m.from_user.id, []).append((m.chat.id, m.message_id))

    remember_username(m.from_user)
    set_lang(m.from_user.id, get_lang(m.from_user.id))
    lang = get_lang(m.from_user.id)

    args = (m.text or "").split(maxsplit=1)
    if len(args) == 2 and args[1].startswith("deal_"):
        deal_id = args[1].split("_", 1)[1]
        d = memory.deals.get(deal_id)
        if not d or now() > d["expires_at"]:
            await show_panel(m.chat.id, t(lang, "deal_expired"), reply_markup=back_to_menu(lang))
            return
        await show_panel(m.chat.id, t(lang, "seller_intro"))
        await state.update_data(deal_id=deal_id)
        await state.set_state(SellerOnboarding.waiting_wallet)
        return

    await show_panel(
        m.chat.id,
        t(lang, "hello"),
        reply_markup=main_menu(lang, has_active_deal(m.from_user.id), has_history(m.from_user.id), uid=m.from_user.id),
    )

# ---------- /admin ----------
@dp.message(Command("admin"))
async def cmd_admin(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        await m.answer(t("ru","not_admin"))
        return
    await state.clear()
    await show_panel(m.chat.id, t("ru","admin_title"), reply_markup=admin_panel_kb())

@dp.callback_query(F.data=="admin_panel")
async def cb_admin_panel(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer(t("ru","not_admin"), show_alert=True); return
    await state.clear()
    await show_panel(c.message.chat.id, t("ru","admin_title"), reply_markup=admin_panel_kb()); await c.answer()

# --- Admin: последние сделки
@dp.callback_query(F.data=="admin_recent")
async def admin_recent(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer(t("ru","not_admin"), show_alert=True); return
    items = list(memory.deals.values()) + [d for hs in memory.history.values() for d in hs]
    items = sorted(items, key=lambda x: x.get("created_at", now()), reverse=True)[:20]
    if not items:
        text = "📊 <b>Последние сделки</b>\nНет данных."
    else:
        rows = []
        for d in items:
            cid = d.get("creator_id")
            sid = d.get("seller_id")
            cuser = memory.usernames.get(cid, f"id{cid}") if cid else "-"
            suser = memory.usernames.get(sid, f"id{sid}") if sid else "-"
            rows.append(
                f"<b>#{d.get('id')}</b> — {d.get('status','-')} — {d.get('price','-')} TON\n"
                f"🏷 {d.get('title','-')}\n"
                f"👤 buyer: {cuser} • seller: {suser}\n"
            )
        text = "📊 <b>Последние сделки</b>\n\n" + "\n".join(rows)
    await show_panel(c.message.chat.id, text, reply_markup=admin_back_only_kb()); await c.answer()

# --- Admin: история чата пользователя
@dp.callback_query(F.data=="admin_chatlog")
async def admin_chatlog(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer(t("ru","not_admin"), show_alert=True); return
    await state.set_state(AdminFlow.waiting_user_for_log)
    await show_panel(c.message.chat.id, "🕓 <b>История чата</b>\n" + t("ru","admin_enter_user"), reply_markup=admin_back_only_kb()); await c.answer()

@dp.message(AdminFlow.waiting_user_for_log)
async def admin_get_log(m: Message, state: FSMContext):
    # всегда удаляем ввод админа после обработки
    to_delete = m.message_id

    if not is_admin(m.from_user.id):
        await m.answer(t("ru","not_admin"))
        try: await bot.delete_message(m.chat.id, to_delete)
        except Exception: pass
        return

    query = (m.text or "").strip()
    uid = None
    if query.startswith("@"):
        for _uid, uname in memory.usernames.items():
            if uname.lower() == query.lower():
                uid = _uid; break
    else:
        try: uid = int(query)
        except: uid = None

    if not uid:
        # сообщаем и удаляем ввод
        await m.reply("Не нашёл пользователя. Введите @username или ID ещё раз.")
        try: await bot.delete_message(m.chat.id, to_delete)
        except Exception: pass
        return

    logs = memory.chatlog.get(uid, [])
    if not logs:
        await show_panel(m.chat.id, "🕓 <b>История чата</b>\n" + t("ru","admin_no_log"), reply_markup=admin_back_only_kb())
        await state.clear()
        try: await bot.delete_message(m.chat.id, to_delete)
        except Exception: pass
        return

    logs = logs[-50:]
    lines = []
    for ts, who, text in logs:
        ts_local = ts.astimezone().strftime("%d.%m %H:%M:%S")
        prefix = "👤" if who == "user" else "🤖"
        text = (text or "").strip()
        if len(text) > 500:
            text = text[:500] + "…"
        lines.append(f"{ts_local} {prefix} {text}")
    out = "🕓 <b>История чата</b>\n\n" + "\n".join(lines)
    await show_panel(m.chat.id, out, reply_markup=admin_back_only_kb())
    await state.clear()

    # удалить ввод админа
    try: await bot.delete_message(m.chat.id, to_delete)
    except Exception: pass

# --- Admin: удаление сообщений пользователя
@dp.callback_query(F.data=="admin_purge")
async def admin_purge(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer(t("ru","not_admin"), show_alert=True); return
    await state.set_state(AdminFlow.waiting_user_for_purge)
    await show_panel(c.message.chat.id, "🧹 <b>Удаление сообщений</b>\n" + t("ru","admin_enter_user"), reply_markup=admin_back_only_kb()); await c.answer()

@dp.message(AdminFlow.waiting_user_for_purge)
async def admin_do_purge(m: Message, state: FSMContext):
    # удалим ввод админа после обработки
    to_delete = m.message_id

    if not is_admin(m.from_user.id):
        await m.answer(t("ru","not_admin"))
        try: await bot.delete_message(m.chat.id, to_delete)
        except Exception: pass
        return

    query = (m.text or "").strip()
    uid = None
    if query.startswith("@"):
        for _uid, uname in memory.usernames.items():
            if uname.lower() == query.lower():
                uid = _uid; break
    else:
        try: uid = int(query)
        except: uid = None
    if not uid:
        await m.reply("Не нашёл пользователя. Введите @username или ID ещё раз.")
        try: await bot.delete_message(m.chat.id, to_delete)
        except Exception: pass
        return

    removed = 0
    # удалить все известные сообщения (включая /start, так как он тоже трекается)
    for (chat_id, mid) in list(memory.all_msgs.get(uid, [])):
        try:
            await bot.delete_message(chat_id, mid)
            removed += 1
        except Exception:
            pass
    memory.all_msgs[uid] = []

    # удалить «панель» (если есть)
    try:
        pid = memory.panel_id.get(uid)
        if pid:
            await bot.delete_message(uid, pid)
            removed += 1
            memory.panel_id.pop(uid, None)
    except Exception:
        pass

    await show_panel(m.chat.id, f"🧹 Удалено сообщений: <b>{removed}</b>\n\n" + t("ru","admin_purged"), reply_markup=admin_back_only_kb())
    await state.clear()

    # удалить ввод админа
    try: await bot.delete_message(m.chat.id, to_delete)
    except Exception: pass

@dp.callback_query(F.data.in_(["admin_back","admin_back_menu"]))
async def admin_back(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer(t("ru","not_admin"), show_alert=True); return
    if c.data == "admin_back_menu":
        lang = get_lang(c.from_user.id)
        await show_panel(
            c.message.chat.id,
            t(lang, "hello"),
            reply_markup=main_menu(lang, has_active_deal(c.from_user.id), has_history(c.from_user.id), uid=c.from_user.id),
        )
    else:
        await show_panel(c.message.chat.id, t("ru","admin_title"), reply_markup=admin_panel_kb())
    await state.clear(); await c.answer()

# ---------- WALLET / SETTINGS ----------
@dp.callback_query(F.data == "wallet")
async def cb_wallet(c: CallbackQuery, state: FSMContext):
    lang = get_lang(c.from_user.id)
    await show_panel(c.message.chat.id, t(lang, "wallet_enter"), reply_markup=back_to_menu(lang))
    await state.set_state(SetWallet.waiting_wallet)
    await c.answer()

@dp.message(SetWallet.waiting_wallet, F.chat.type == ChatType.PRIVATE)
async def wallet_set(m: Message, state: FSMContext):
    remember_username(m.from_user)
    lang = get_lang(m.from_user.id)
    await add_user_msg(m)
    txt = (m.text or "").strip()
    if is_ton_address(txt):
        set_wallet(m.from_user.id, txt)
        await show_panel(m.chat.id, t(lang, "wallet_saved").format(addr=txt), reply_markup=back_to_menu(lang))
    else:
        warn = await m.answer(t(lang, "wallet_invalid"))
        set_warning(m.from_user.id, warn.message_id)

# ---------- CREATE FLOW ----------
def wip(uid: int) -> dict:
    return memory.wip.setdefault(uid, {"step": 1, "title": "", "desc": "", "price": None, "username": ""})

def prompt_for_step(lang: str, draft: dict) -> str:
    s = draft.get("step", 1)
    return {1: t(lang, "ask_title"), 2: t(lang, "ask_desc"), 3: t(lang, "ask_price"), 4: t(lang, "ask_user")}[s]

def final_text(lang: str, snap: dict) -> str:
    return t(lang, "final").format(
        title=snap["title"], desc=snap["desc"], price=snap["price"], target=snap["target_user"], link=snap["deep_link"]
    )

@dp.callback_query(F.data == "create")
async def cb_create(c: CallbackQuery, state: FSMContext):
    remember_username(c.from_user)
    lang = get_lang(c.from_user.id)
    memory.user_msgs[c.message.chat.id] = []
    draft = wip(c.from_user.id)
    draft.update({"step": 1, "title": "", "desc": "", "price": None, "username": ""})
    await state.set_state(CreateDeal.entering)
    await show_panel(c.message.chat.id, prompt_for_step(lang, draft), reply_markup=create_nav_prev_only(lang, draft["step"]))
    await c.answer()

@dp.callback_query(F.data == "create_prev")
async def cb_prev(c: CallbackQuery, state: FSMContext):
    lang = get_lang(c.from_user.id)
    draft = wip(c.from_user.id)
    if draft["step"] > 1:
        draft["step"] -= 1
    await show_panel(c.message.chat.id, prompt_for_step(lang, draft), reply_markup=create_nav_prev_only(lang, draft["step"]))
    await c.answer()

@dp.callback_query(F.data == "create_cancel")
async def cb_cancel(c: CallbackQuery, state: FSMContext):
    lang = get_lang(c.from_user.id)
    memory.wip[c.from_user.id] = {"step": 1, "title": "", "desc": "", "price": None, "username": ""}
    await clear_flow_messages(c.message.chat.id)
    await show_panel(
        c.message.chat.id,
        t(lang, "hello"),
        reply_markup=main_menu(lang, has_active_deal(c.from_user.id), has_history(c.from_user.id), uid=c.from_user.id),
    )
    await state.clear()
    await c.answer()

@dp.message(CreateDeal.entering)
async def create_input(m: Message, state: FSMContext):
    remember_username(m.from_user)
    lang = get_lang(m.from_user.id)
    draft = wip(m.from_user.id)
    await add_user_msg(m)
    text = (m.text or "").strip()

    if draft["step"] == 1:
        draft["title"] = text
        draft["step"] = 2
    elif draft["step"] == 2:
        draft["desc"] = text
        draft["step"] = 3
    elif draft["step"] == 3:
        try:
            draft["price"] = float(text.replace(",", "."))
            draft["step"] = 4
        except Exception:
            warn = await m.answer(t(lang, "bad_price"))
            set_warning(m.from_user.id, warn.message_id)
            return
    elif draft["step"] == 4:
        if not (text.startswith("@") and len(text) > 1):
            warn = await m.answer(t(lang, "bad_user"))
            set_warning(m.from_user.id, warn.message_id)
            return
        draft["username"] = text

        deal_id = secrets.token_urlsafe(8)
        url = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
        snapshot = {
            "id": deal_id,
            "creator_id": m.from_user.id,
            "creator_username": memory.usernames.get(m.from_user.id, f"id{m.from_user.id}"),
            "title": draft["title"],
            "desc": draft["desc"],
            "price": draft["price"],
            "target_user": draft["username"],
            "lang": lang,
            "status": "new",
            "created_at": now(),
            "expires_at": now() + timedelta(minutes=30),
            "seller_id": None,
            "seller_deadline": None,
            "deep_link": url,
            "seller_wallet": None,
            "memo": None,
        }
        memory.deals[deal_id] = snapshot

        await clear_flow_messages(m.chat.id)
        await show_panel(m.chat.id, final_text(lang, snapshot), reply_markup=final_actions(lang, deal_id))

        memory.wip[m.from_user.id] = {"step": 1, "title": "", "desc": "", "price": None, "username": ""}
        await state.clear()
        return

    await show_panel(m.chat.id, prompt_for_step(lang, draft), reply_markup=create_nav_prev_only(lang, draft["step"]))

# ---------- SELLER ONBOARDING ----------
@dp.message(SellerOnboarding.waiting_wallet)
async def seller_wallet(m: Message, state: FSMContext):
    remember_username(m.from_user)
    lang = get_lang(m.from_user.id)
    await add_user_msg(m)
    txt = (m.text or "").strip()
    if not is_ton_address(txt):
        warn = await m.answer(t(lang, "wallet_invalid"))
        set_warning(m.from_user.id, warn.message_id)
        return

    data = await state.get_data()
    deal_id = data.get("deal_id")
    d = memory.deals.get(deal_id)
    if not d:
        await show_panel(m.chat.id, t(lang, "deal_expired"), reply_markup=back_to_menu(lang))
        await state.clear()
        return

    set_wallet(m.from_user.id, txt)
    d["seller_id"] = m.from_user.id
    d["seller_username"] = memory.usernames.get(m.from_user.id, f"id{m.from_user.id}")
    d["seller_wallet"] = txt
    memory.deals[deal_id] = d

    try:
        await bot.delete_message(m.chat.id, m.message_id)  # удалить сообщение с кошельком
    except Exception:
        pass
    await clear_flow_messages(m.chat.id)

    await show_panel(
        m.chat.id,
        t(lang, "seller_wallet_ok"),
        reply_markup=accept_order_kb(lang, deal_id),
    )
    await state.clear()

# ---------- SELLER/BUYER ACTIONS ----------
@dp.callback_query(F.data.startswith("deal:"))
async def seller_action(c: CallbackQuery):
    remember_username(c.from_user)
    parts = c.data.split(":")
    _, deal_id, action = parts
    d = memory.deals.get(deal_id)
    lang = get_lang(c.from_user.id)

    if not d:
        await show_panel(c.message.chat.id, t(lang, "deal_expired"), reply_markup=back_to_menu(lang))
        await c.answer()
        return

    if action == "accept":
        await show_panel(
            c.message.chat.id,
            t(lang, "seller_details").format(title=d["title"], desc=d["desc"], price=d["price"], target=d["target_user"]),
            reply_markup=seller_controls(lang, deal_id),
        )
        await c.answer(); return

    if action == "stop":
        d["status"] = "stopped"
        await show_panel(c.message.chat.id, t(lang, "seller_stopped"), reply_markup=back_to_menu(lang))
        try:
            msg = await bot.send_message(d["creator_id"], f"⛔️ Продавец остановил ордер <b>{d['title']}</b>.")
            memory.all_msgs.setdefault(d["creator_id"], []).append((d["creator_id"], msg.message_id))
        except Exception:
            pass
        memory.history.setdefault(d["creator_id"], []).insert(0, d.copy())
        memory.deals.pop(deal_id, None)
        await c.answer(); return

    if action == "confirm":
        if not d.get("seller_wallet"):
            await c.answer("Сначала укажите кошелёк.", show_alert=True); return

        delay = random.randint(4, 7)
        await show_panel(c.message.chat.id, "⏳ Обработка подтверждения...", reply_markup=None)
        await asyncio.sleep(delay)

        d["status"] = "await_payment"
        d["seller_deadline"] = now() + timedelta(minutes=15)
        memo = "MG-" + secrets.token_urlsafe(4).upper().replace("_", "").replace("-", "")
        d["memo"] = memo
        memory.deals[deal_id] = d

        await show_panel(c.message.chat.id, t(lang, "seller_confirmed_wait"), reply_markup=back_to_menu(lang))

        buyer_lang = get_lang(d["creator_id"])
        buyer_text = (
            t(buyer_lang, "buyer_notif_confirmed").format(title=d["title"]) + "\n\n" +
            t(buyer_lang, "buyer_pay_prompt").format(
                title=d["title"], desc=d["desc"], price=d["price"],
                target=d["target_user"], seller_wallet=d["seller_wallet"], memo=memo
            )
        )
        await show_panel(d["creator_id"], buyer_text, reply_markup=buyer_pay_kb(buyer_lang, deal_id))
        await c.answer(); return

@dp.callback_query(F.data.startswith("memo:"))
async def copy_memo(c: CallbackQuery):
    deal_id = c.data.split(":", 1)[1]
    d = memory.deals.get(deal_id)
    if not d or not d.get("memo"):
        await c.answer("MEMO недоступен.", show_alert=True); return
    await c.answer(f"MEMO: {d['memo']}", show_alert=True)

@dp.callback_query(F.data.startswith("paid:"))
async def buyer_paid(c: CallbackQuery):
    deal_id = c.data.split(":", 1)[1]
    d = memory.deals.get(deal_id)
    lang = get_lang(c.from_user.id)
    if not d:
        await c.answer("Ордер недоступен.", show_alert=True); return
    if c.from_user.id != d["creator_id"]:
        await c.answer("Недоступно.", show_alert=True); return

    d["status"] = "await_seller_final"
    memory.deals[deal_id] = d

    await show_panel(c.message.chat.id, t(lang, "buyer_wait_confirm"), reply_markup=back_to_menu(lang))

    seller_lang = get_lang(d.get("seller_id") or c.from_user.id)
    await show_panel(
        d["seller_id"],
        t(seller_lang, "seller_final_needed"),
        reply_markup=seller_final_kb(seller_lang, deal_id)
    )
    await c.answer("Отмечено. Ожидаем подтверждения продавца.")

@dp.callback_query(F.data.startswith("finish:"))
async def seller_finish(c: CallbackQuery):
    deal_id = c.data.split(":", 1)[1]
    d = memory.deals.get(deal_id)
    lang = get_lang(c.from_user.id)
    if not d:
        await c.answer("Ордер недоступен.", show_alert=True); return
    if c.from_user.id != d.get("seller_id"):
        await c.answer("Недоступно.", show_alert=True); return

    d["status"] = "done"
    memory.history.setdefault(d["creator_id"], []).insert(0, d.copy())

    await show_panel(c.message.chat.id, t(lang, "seller_final_done"), reply_markup=back_to_menu(lang))

    buyer_lang = get_lang(d["creator_id"])
    await show_panel(d["creator_id"], t(buyer_lang, "buyer_final_done").format(title=d["title"]), reply_markup=back_to_menu(buyer_lang))

    memory.deals.pop(deal_id, None)
    await c.answer("Готово.")

# ---------- CURRENT / HISTORY ----------
@dp.callback_query(F.data == "current")
async def cb_current(c: CallbackQuery):
    lang = get_lang(c.from_user.id)
    active = [
        d for d in memory.deals.values()
        if d.get("creator_id") == c.from_user.id
        and d.get("status") in {"new", "await_payment", "await_seller_final"}
        and now() < d.get("expires_at", now())
    ]
    if not active:
        await show_panel(
            c.message.chat.id,
            t(lang, "hello"),
            reply_markup=main_menu(lang, False, has_history(c.from_user.id), uid=c.from_user.id),
        )
        await c.answer(); return

    d = sorted(active, key=lambda x: x["created_at"], reverse=True)[0]
    txt = final_text(lang, d)
    await show_panel(
        c.message.chat.id,
        t(lang, "current_title") + "\n\n" + txt,
        reply_markup=final_actions(lang, d["id"]),
    )
    await c.answer()

@dp.callback_query(F.data == "history")
async def cb_history(c: CallbackQuery):
    lang = get_lang(c.from_user.id)
    items = memory.history.get(c.from_user.id, [])[:10]
    if not items:
        await show_panel(c.message.chat.id, t(lang, "history_title") + "\n" + t(lang, "no_history"), reply_markup=back_to_menu(lang))
        await c.answer(); return

    lines = []
    for i, d in enumerate(items, 1):
        when = d.get("created_at")
        if when:
            try: when = when.astimezone().strftime("%d.%m %H:%M")
            except Exception: when = "-"
        else:
            when = "-"
        lines.append(f"{i}. <b>{d.get('title') or '[title]'}</b> — {d.get('price','-')} TON — {d.get('status','done')} — {when}")

    await show_panel(c.message.chat.id, t(lang, "history_title") + "\n\n" + "\n".join(lines), reply_markup=back_to_menu(lang))
    await c.answer()

# ---------- SETTINGS / LANG ----------
@dp.callback_query(F.data == "settings")
async def cb_settings(c: CallbackQuery):
    lang = get_lang(c.from_user.id)
    await show_panel(c.message.chat.id, t(lang, "settings"), reply_markup=lang_menu())
    await c.answer()

@dp.callback_query(F.data.in_(["lang_ru", "lang_en"]))
async def cb_set_lang(c: CallbackQuery):
    new_lang = "ru" if c.data.endswith("ru") else "en"
    set_lang(c.from_user.id, new_lang)
    await show_panel(
        c.message.chat.id,
        t(new_lang, "hello"),
        reply_markup=main_menu(new_lang, has_active_deal(c.from_user.id), has_history(c.from_user.id), uid=c.from_user.id),
    )
    await c.answer()

# ---------- MENU ----------
@dp.callback_query(F.data == "menu")
async def cb_menu(c: CallbackQuery):
    lang = get_lang(c.from_user.id)
    await clear_warn_if_any(c.from_user.id, c.message.chat.id)
    await clear_flow_messages(c.message.chat.id)
    await show_panel(
        c.message.chat.id,
        t(lang, "hello"),
        reply_markup=main_menu(lang, has_active_deal(c.from_user.id), has_history(c.from_user.id), uid=c.from_user.id),
    )
    await c.answer()

# ---------- INLINE SHARE ----------
@dp.inline_query()
async def inline_share(iq: InlineQuery):
    q = (iq.query or "").strip()
    results = []
    if q.startswith("deal_"):
        deal_id = q.split("_", 1)[1]
        d = memory.deals.get(deal_id)
        if d:
            url = d["deep_link"]
            text = f"{url}\n\nMoonGarant - ваш выбор в проведении сделок!"
            results.append(
                InlineQueryResultArticle(
                    id=deal_id,
                    title="MoonGarant • Ссылка на сделку",
                    description=f"{d['price']} TON • {d['target_user']}",
                    input_message_content=InputTextMessageContent(message_text=text, parse_mode=ParseMode.HTML),
                )
            )
    await iq.answer(results=results, cache_time=0, is_personal=True)

# ---------- GUARD ----------
@dp.message(F.chat.type == ChatType.PRIVATE)
async def guard_delete_noise(m: Message, state: FSMContext):
    remember_username(m.from_user)
    current = await state.get_state()
    txt = (m.text or "").strip()
    if current is None and txt != "/start" and not txt.startswith("/admin"):
        try:
            await m.delete()
        except Exception:
            pass
    else:
        memory.chatlog.setdefault(m.from_user.id, []).append((now(), "user", m.text or ""))

# ---------- MAIN ----------
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Put it into .env")
    asyncio.create_task(expiry_worker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
