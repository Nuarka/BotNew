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

        # SETTINGS
        "settings_title": "⚙️ Настройки",
        "settings_prompt": (
            "⚙️ <b>Настройки</b>\n\n"
            "Текущий язык: <b>{lang_name}</b>\n"
            "Текущий метод оплаты: <b>{pay_method}</b>\n\n"
            "Выберите метод ниже:"
        ),
        "lang_menu_footer": "↩️ В меню / Menu",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",

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
            "<b>Цена/условия:</b> {price_label}\n"
            "<b>Отправить NFT (покупателю):</b> {target}\n\n"
            "После передачи нажмите «Я перевёл(а) подарки»."
        ),
        "seller_stopped": "⛔️ Продавец остановил ордер. Сделка отменена.",
        "seller_confirmed_wait": "✅ Отправка подарков подтверждена.\n⌛ <b>Ожидайте оплату, не более 15 минут...</b>",
        "seller_final_needed": "💳 Покупатель отметил оплату.\nЕсли получили средства — нажмите «Подтвердить получение оплаты».",
        "seller_final_done": "🎉 Оплата подтверждена. Сделка завершена!",

        # Buyer side
        "buyer_notif_confirmed": "✅ Продавец подтвердил отправку по ордеру <b>{title}</b>.",
        "buyer_pay_prompt_std": (
            "🧾 <b>Детали ордера</b>\n"
            "<b>Название:</b> {title}\n"
            "<b>Описание:</b> {desc}\n"
            "<b>Цена:</b> {price_value} {method}\n"
            "<b>Куда отправить NFT:</b> {target}\n\n"
            "💳 <b>Оплата</b>\n"
            "<b>Кошелёк продавца:</b> <code>{seller_wallet}</code>\n"
            "<b>Комментарий/MEMO:</b> <code>{memo}</code>\n\n"
            "⚠️ <b>Внимание!</b> Укажите <b>комментарий/MEMO</b> при переводе: <code>{memo}</code> — иначе оплата не будет засчитана!"
        ),
        "buyer_pay_prompt_ex": (
            "🧾 <b>Детали ордера</b>\n"
            "<b>Название:</b> {title}\n"
            "<b>Описание:</b> {desc}\n"
            "<b>Обмен:</b> {exchange_desc}\n"
            "<b>Куда отправить NFT:</b> {target}\n\n"
            "💳 <b>Оплата</b>\n"
            "<b>Кошелёк продавца:</b> <code>{seller_wallet}</code>\n"
            "<b>Комментарий/MEMO:</b> <code>{memo}</code>\n\n"
            "⚠️ <b>Внимание!</b> Укажите <b>комментарий/MEMO</b> при переводе: <code>{memo}</code> — иначе оплата не будет засчитана!"
        ),
        "buyer_wait_confirm": "⌛ Ожидайте подтверждения получения оплаты продавцом.",
        "buyer_final_done": "✅ Продавец подтвердил отправку по ордеру <b>{title}</b>.",

        # Create flow prompts (depend on pay method)
        "ask_title": "Введите <b>название</b> ордера.",
        "ask_desc": "Введите <b>описание</b> ордера (содержание подарков).",
        "ask_price_std": "Введите <b>цену</b> в {method} (например: <code>12.5</code>).",
        "ask_price_ex": "Укажите <b>условия обмена</b> в формате: <code>100 STARS -> 12 TON</code>.",
        "ask_user": "Укажите <b>@username</b> покупателя.",
        "bad_price": "⚠️ Нужно число (можно с точкой).",
        "bad_user": "⚠️ Укажите username в формате <code>@username</code>.",

        # Final card (buyer side)
        "final_std": (
            "🧾 <b>Детали ордера</b>\n\n"
            "<b>Название:</b> {title}\n"
            "<b>Описание:</b> {desc}\n"
            "<b>Цена:</b> {price_value} {method}\n"
            "<b>Куда отправить NFT:</b> {target}\n\n"
            "После перехода продавца по ссылке у него будет <b>15 минут</b> на подтверждение отправки.\n\n"
            "<b>Ссылка:</b> {link}"
        ),
        "final_ex": (
            "🧾 <b>Детали ордера</b>\n\n"
            "<b>Название:</b> {title}\n"
            "<b>Описание:</b> {desc}\n"
            "<b>Обмен:</b> {exchange_desc}\n"
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

LANG_NAME = {"ru": "русский", "en": "english"}

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

def get_pay_method(uid: int) -> str:
    # Один из: RUB, USD, KZT, STARS, TON, EXCHANGE
    return memory.users.get(uid, {}).get("pay_method") or "TON"

def set_pay_method(uid: int, method: str):
    memory.users.setdefault(uid, {})["pay_method"] = method

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

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    # ряд RUB / USD / KZT (по клику — выбрать конкретную валюту)
    # ниже STARS
    # ниже TON и ОБМЕН
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="RUB", callback_data="pay:RUB"),
            InlineKeyboardButton(text="USD", callback_data="pay:USD"),
            InlineKeyboardButton(text="KZT", callback_data="pay:KZT"),
        ],
        [InlineKeyboardButton(text="⭐ STARS", callback_data="pay:STARS")],
        [
            InlineKeyboardButton(text="TON", callback_data="pay:TON"),
            InlineKeyboardButton(text="🔁 Обмен", callback_data="pay:EXCHANGE"),
        ],
        [
            InlineKeyboardButton(text=t("ru","lang_ru"), callback_data="lang_ru"),
            InlineKeyboardButton(text=t("ru","lang_en"), callback_data="lang_en"),
        ],
        [InlineKeyboardButton(text=t("ru","lang_menu_footer"), callback_data="menu")]
    ])

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
                    msg = await bot.send_message(d["creator_id"], t(d.get("lang", "ru"), "deal_expired"))
                    memory.all_msgs.setdefault(d["creator_id"], []).append((d["creator_id"], msg.message_id))
                except Exception:
                    pass
                memory.deals.pop(deal_id, None)

# ---------- START ----------
@dp.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    memory.all_msgs.setdefault(m.from_user.id, []).append((m.chat.id, m.message_id))
    remember_username(m.from_user)
    set_lang(m.from_user.id, get_lang(m.from_user.id))
    # дефолт метода оплаты — TON
    if "pay_method" not in memory.users.get(m.from_user.id, {}):
        set_pay_method(m.from_user.id, "TON")

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
            price_label = d.get("exchange_desc") or f"{d.get('price','-')} {d.get('method','')}"
            rows.append(
                f"<b>#{d.get('id')}</b> — {d.get('status','-')} — {price_label}\n"
                f"🏷 {d.get('title','-')}\n"
                f"👤 buyer: {cuser} • seller: {suser}\n"
            )
        text = "📊 <b>Последние сделки</b>\n\n" + "\n".join(rows)
    await show_panel(c.message.chat.id, text, reply_markup=admin_back_only_kb()); await c.answer()

@dp.callback_query(F.data=="admin_chatlog")
async def admin_chatlog(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer(t("ru","not_admin"), show_alert=True); return
    await state.set_state(AdminFlow.waiting_user_for_log)
    await show_panel(c.message.chat.id, "🕓 <b>История чата</b>\n" + t("ru","admin_enter_user"), reply_markup=admin_back_only_kb()); await c.answer()

@dp.message(AdminFlow.waiting_user_for_log)
async def admin_get_log(m: Message, state: FSMContext):
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
    try: await bot.delete_message(m.chat.id, to_delete)
    except Exception: pass

@dp.callback_query(F.data=="admin_purge")
async def admin_purge(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        await c.answer(t("ru","not_admin"), show_alert=True); return
    await state.set_state(AdminFlow.waiting_user_for_purge)
    await show_panel(c.message.chat.id, "🧹 <b>Удаление сообщений</b>\n" + t("ru","admin_enter_user"), reply_markup=admin_back_only_kb()); await c.answer()

@dp.message(AdminFlow.waiting_user_for_purge)
async def admin_do_purge(m: Message, state: FSMContext):
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
    for (chat_id, mid) in list(memory.all_msgs.get(uid, [])):
        try:
            await bot.delete_message(chat_id, mid)
            removed += 1
        except Exception:
            pass
    memory.all_msgs[uid] = []

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

def settings_text(uid: int) -> str:
    lang = get_lang(uid)
    lang_name = LANG_NAME.get(lang, lang)
    method = get_pay_method(uid)
    return t(lang, "settings_prompt").format(lang_name=lang_name, pay_method=method)

@dp.callback_query(F.data == "settings")
async def cb_settings(c: CallbackQuery):
    uid = c.from_user.id
    lang = get_lang(uid)
    await show_panel(c.message.chat.id, settings_text(uid), reply_markup=settings_kb(lang))
    await c.answer()

@dp.callback_query(F.data.in_(["lang_ru", "lang_en"]))
async def cb_set_lang(c: CallbackQuery):
    uid = c.from_user.id
    new_lang = "ru" if c.data.endswith("ru") else "en"
    set_lang(uid, new_lang)
    await show_panel(c.message.chat.id, settings_text(uid), reply_markup=settings_kb(new_lang))
    await c.answer()

@dp.callback_query(F.data.startswith("pay:"))
async def cb_set_pay(c: CallbackQuery):
    uid = c.from_user.id
    method = c.data.split(":",1)[1]
    # one of RUB/USD/KZT/STARS/TON/EXCHANGE
    set_pay_method(uid, method)
    lang = get_lang(uid)
    await show_panel(c.message.chat.id, settings_text(uid), reply_markup=settings_kb(lang))
    await c.answer("Метод оплаты обновлён")

# ---------- CREATE FLOW ----------
def wip(uid: int) -> dict:
    # price_value: float|None (для всех кроме EXCHANGE)
    # exchange_desc: str|None (для EXCHANGE)
    return memory.wip.setdefault(uid, {"step": 1, "title": "", "desc": "", "price_value": None, "exchange_desc": None, "username": ""})

def prompt_for_step(uid: int, draft: dict) -> str:
    lang = get_lang(uid)
    s = draft.get("step", 1)
    if s == 1:
        return t(lang, "ask_title")
    if s == 2:
        return t(lang, "ask_desc")
    if s == 3:
        method = get_pay_method(uid)
        if method == "EXCHANGE":
            return t(lang, "ask_price_ex")
        else:
            return t(lang, "ask_price_std").format(method=method)
    if s == 4:
        return t(lang, "ask_user")
    return "..."

def final_text(uid: int, snap: dict) -> str:
    lang = get_lang(uid)
    if snap.get("exchange_desc"):
        return t(lang, "final_ex").format(
            title=snap["title"], desc=snap["desc"], exchange_desc=snap["exchange_desc"], target=snap["target_user"], link=snap["deep_link"]
        )
    else:
        return t(lang, "final_std").format(
            title=snap["title"], desc=snap["desc"], price_value=snap["price_value"], method=snap["method"], target=snap["target_user"], link=snap["deep_link"]
        )

@dp.callback_query(F.data == "create")
async def cb_create(c: CallbackQuery, state: FSMContext):
    remember_username(c.from_user)
    uid = c.from_user.id
    lang = get_lang(uid)
    memory.user_msgs[c.message.chat.id] = []
    draft = wip(uid)
    draft.update({"step": 1, "title": "", "desc": "", "price_value": None, "exchange_desc": None, "username": ""})
    await state.set_state(CreateDeal.entering)
    await show_panel(c.message.chat.id, prompt_for_step(uid, draft), reply_markup=create_nav_prev_only(lang, draft["step"]))
    await c.answer()

@dp.callback_query(F.data == "create_prev")
async def cb_prev(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    lang = get_lang(uid)
    draft = wip(uid)
    if draft["step"] > 1:
        draft["step"] -= 1
    await show_panel(c.message.chat.id, prompt_for_step(uid, draft), reply_markup=create_nav_prev_only(lang, draft["step"]))
    await c.answer()

@dp.callback_query(F.data == "create_cancel")
async def cb_cancel(c: CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    lang = get_lang(uid)
    memory.wip[uid] = {"step": 1, "title": "", "desc": "", "price_value": None, "exchange_desc": None, "username": ""}
    await clear_flow_messages(c.message.chat.id)
    await show_panel(
        c.message.chat.id,
        t(lang, "hello"),
        reply_markup=main_menu(lang, has_active_deal(uid), has_history(uid), uid=uid),
    )
    await state.clear()
    await c.answer()

@dp.message(CreateDeal.entering)
async def create_input(m: Message, state: FSMContext):
    remember_username(m.from_user)
    uid  = m.from_user.id
    lang = get_lang(uid)
    method = get_pay_method(uid)
    draft = wip(uid)
    await add_user_msg(m)
    text = (m.text or "").strip()

    if draft["step"] == 1:
        draft["title"] = text
        draft["step"] = 2
    elif draft["step"] == 2:
        draft["desc"] = text
        draft["step"] = 3
    elif draft["step"] == 3:
        if method == "EXCHANGE":
            # просто принимаем строку-описание обмена
            draft["exchange_desc"] = text
            draft["price_value"] = None
            draft["step"] = 4
        else:
            try:
                price = float(text.replace(",", "."))
                draft["price_value"] = price
                draft["exchange_desc"] = None
                draft["step"] = 4
            except Exception:
                warn = await m.answer(t(lang, "bad_price"))
                set_warning(uid, warn.message_id)
                return
    elif draft["step"] == 4:
        if not (text.startswith("@") and len(text) > 1):
            warn = await m.answer(t(lang, "bad_user"))
            set_warning(uid, warn.message_id)
            return
        draft["username"] = text

        deal_id = secrets.token_urlsafe(8)
        url = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
        snapshot = {
            "id": deal_id,
            "creator_id": uid,
            "creator_username": memory.usernames.get(uid, f"id{uid}"),
            "title": draft["title"],
            "desc": draft["desc"],
            "price_value": draft["price_value"],   # float или None
            "exchange_desc": draft["exchange_desc"],  # str или None
            "method": method,                      # RUB/USD/KZT/STARS/TON/EXCHANGE
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
        await show_panel(m.chat.id, final_text(uid, snapshot), reply_markup=final_actions(lang, deal_id))

        memory.wip[uid] = {"step": 1, "title": "", "desc": "", "price_value": None, "exchange_desc": None, "username": ""}
        await state.clear()
        return

    await show_panel(m.chat.id, prompt_for_step(uid, draft), reply_markup=create_nav_prev_only(lang, draft["step"]))

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

    price_label = d.get("exchange_desc") or (f"{d['price_value']} {d['method']}" if d.get("price_value") is not None else d.get("method"))
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
        price_label = d.get("exchange_desc") or (f"{d['price_value']} {d['method']}" if d.get("price_value") is not None else d.get("method"))
        await show_panel(
            c.message.chat.id,
            t(lang, "seller_details").format(title=d["title"], desc=d["desc"], price_label=price_label, target=d["target_user"]),
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
        if d.get("exchange_desc"):
            buyer_text = (
                t(buyer_lang, "buyer_notif_confirmed").format(title=d["title"]) + "\n\n" +
                t(buyer_lang, "buyer_pay_prompt_ex").format(
                    title=d["title"], desc=d["desc"], exchange_desc=d["exchange_desc"],
                    target=d["target_user"], seller_wallet=d["seller_wallet"], memo=memo
                )
            )
        else:
            buyer_text = (
                t(buyer_lang, "buyer_notif_confirmed").format(title=d["title"]) + "\n\n" +
                t(buyer_lang, "buyer_pay_prompt_std").format(
                    title=d["title"], desc=d["desc"], price_value=d["price_value"], method=d["method"],
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
    txt = final_text(c.from_user.id, d)
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
        price_label = d.get("exchange_desc") or (f"{d['price_value']} {d['method']}" if d.get("price_value") is not None else d.get("method"))
        lines.append(f"{i}. <b>{d.get('title') or '[title]'}</b> — {price_label} — {d.get('status','done')} — {when}")

    await show_panel(c.message.chat.id, t(lang, "history_title") + "\n\n" + "\n".join(lines), reply_markup=back_to_menu(lang))
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
                    description=(d.get("exchange_desc") or f"{d.get('price_value')} {d.get('method')}") + f" • {d['target_user']}",
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
