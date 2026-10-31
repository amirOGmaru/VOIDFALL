import os
import sqlite3
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

DB = "voidfall.db"

SWORDS = {
    "rusty": ("شمشیر زنگ‌زده", "۱ تا ۱۰", 0),
    "steel": ("شمشیر فولادی", "۵ تا ۱۵", 500),
    "lightning": ("شمشیر آذرخش", "۱۵ تا ۲۵", 2000),
    "cursed": ("شمشیر نفرین‌شده", "۲۰ تا ۳۰", 3000),
    "epic": ("شمشیر حماسی", "۳۰ تا ۴۰", 5000),
}

ARMORS = {
    "iron": ("زره آهنی", "۱۰٪", 3000),
    "steel": ("زره فولادی", "۲۵٪", 8000),
}


def connect():
    return sqlite3.connect(DB)


def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 100,
                coins INTEGER DEFAULT 0,
                sword TEXT DEFAULT 'rusty',
                armor TEXT DEFAULT 'none',
                medkits INTEGER DEFAULT 5
            )
        """)


def get_player(user):
    with connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO players (user_id, name) VALUES (?, ?)",
            (user.id, user.full_name)
        )
        db.execute(
            "UPDATE players SET name=? WHERE user_id=?",
            (user.full_name, user.id)
        )
        return db.execute(
            "SELECT level, xp, hp, coins, sword, armor, medkits "
            "FROM players WHERE user_id=?",
            (user.id,)
        ).fetchone()


def home_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 پروفایل", callback_data="profile"),
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")
        ],
        [
            InlineKeyboardButton("📖 راهنما", callback_data="help")
        ]
    ])


def home_text(name):
    return (
        f"🌑 به دنیای VOIDFALL خوش اومدی، {name}!\n\n"
        "⚔️ آماده‌ای ماجراجویی رو شروع کنی؟\n"
        "از دکمه‌های زیر استفاده کن."
    )


HELP_TEXT = """📖 راهنمای بازی VOIDFALL

👤 پروفایل:
وضعیت شخصیت، لول، XP، سلامتی و تجهیزاتت رو ببین.

🛒 فروشگاه:
شمشیر و زره بخر.

⚔️ مبارزه:
سیستم مبارزه هنوز در حال ساخت است.

🌑 موفق باشی، شکارچی!"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_player(update.effective_user)
    await update.message.reply_text(
        home_text(update.effective_user.first_name),
        reply_markup=home_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def show_profile(query, user):
    row = get_player(user)
    level, xp, hp, coins, sword, armor, medkits = row

    sword_name, sword_damage, _ = SWORDS[sword]
    armor_text = "نداری" if armor == "none" else ARMORS[armor][0]

    text = (
        f"👤 پروفایل {user.full_name}\n\n"
        f"⭐ لول: {level}\n"
        f"✨ XP: {xp}/100\n"
        f"❤️ سلامتی: {hp}/100\n"
        f"🪙 سکه: {coins}\n"
        f"⚔️ شمشیر: {sword_name}\n"
        f"💥 آسیب شمشیر: {sword_damage}\n"
        f"🛡️ زره: {armor_text}\n"
        f"🧪 مدکیت: {medkits}/5"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home")]
    ])

    await query.edit_message_text(text, reply_markup=keyboard)


async def show_shop(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ شمشیرها", callback_data="swords")],
        [InlineKeyboardButton("🛡️ زره‌ها", callback_data="armors")],
        [InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home")]
    ])

    await query.edit_message_text(
        "🛒 فروشگاه VOIDFALL\n\nیک دسته رو انتخاب کن:",
        reply_markup=keyboard
    )


async def show_swords(query):
    buttons = []

    for key, (name, damage, price) in SWORDS.items():
        buttons.append([
            InlineKeyboardButton(
                f"{name} | آسیب {damage} | {price} سکه",
                callback_data=f"sword:{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="shop")
    ])

    await query.edit_message_text(
        "⚔️ بخش شمشیرها\n\nشمشیر موردنظرت رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_armors(query):
    buttons = []

    for key, (name, reduction, price) in ARMORS.items():
        buttons.append([
            InlineKeyboardButton(
                f"{name} | کاهش آسیب {reduction} | {price} سکه",
                callback_data=f"armor:{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="shop")
    ])

    await query.edit_message_text(
        "🛡️ بخش زره‌ها\n\nزره موردنظرت رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_item(query, category, key):
    items = SWORDS if category == "sword" else ARMORS

    if key not in items:
        await query.answer("این وسیله پیدا نشد.", show_alert=True)
        return

    name, stat, price = items[key]
    label = "آسیب" if category == "sword" else "کاهش آسیب"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🛒 خرید",
            callback_data=f"buy:{category}:{key}"
        )],
        [InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="swords" if category == "sword" else "armors"
        )]
    ])

    await query.edit_message_text(
        f"📦 {name}\n\n{label}: {stat}\nقیمت: {price} سکه",
        reply_markup=keyboard
    )


async def buy_item(query, user, category, key):
    items = SWORDS if category == "sword" else ARMORS

    if key not in items:
        await query.answer("این وسیله پیدا نشد.", show_alert=True)
        return

    name, stat, price = items[key]
    column = "sword" if category == "sword" else "armor"

    with connect() as db:
        row = db.execute(
            "SELECT coins FROM players WHERE user_id=?",
            (user.id,)
        ).fetchone()

        if row is None or row[0] < price:
            await query.answer("سکه کافی نداری!", show_alert=True)
            return

        db.execute(
            f"UPDATE players SET coins=coins-?, {column}=? WHERE user_id=?",
            (price, key, user.id)
        )

    await query.edit_message_text(
        f"✅ خرید موفق!\n\n{name} به تجهیزاتت اضافه شد.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🛒 بازگشت به فروشگاه",
                callback_data="shop"
            )],
            [InlineKeyboardButton(
                "🏠 صفحه اصلی",
                callback_data="home"
            )]
        ])
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    if data == "home":
        await query.edit_message_text(
            home_text(user.first_name),
            reply_markup=home_keyboard()
        )

    elif data == "profile":
        await show_profile(query, user)

    elif data == "help":
        await query.edit_message_text(
            HELP_TEXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🏠 صفحه اصلی",
                    callback_data="home"
                )]
            ])
        )

    elif data == "shop":
        await show_shop(query)

    elif data == "swords":
        await show_swords(query)

    elif data == "armors":
        await show_armors(query)

    elif data.startswith("sword:"):
        await show_item(query, "sword", data.split(":")[1])

    elif data.startswith("armor:"):
        await show_item(query, "armor", data.split(":")[1])

    elif data.startswith("buy:"):
        _, category, key = data.split(":")
        await buy_item(query, user, category, key)


async def text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "راهنما":
        await update.message.reply_text(HELP_TEXT)

    elif text == "پروفایل":
        row = get_player(update.effective_user)
        level, xp, hp, coins, sword, armor, medkits = row

        await update.message.reply_text(
            f"👤 پروفایل {update.effective_user.full_name}\n"
            f"⭐ لول: {level}\n"
            f"✨ XP: {xp}/100\n"
            f"❤️ HP: {hp}/100\n"
            f"🪙 سکه: {coins}\n"
            f"⚔️ شمشیر: {SWORDS[sword][0]}\n"
            f"🛡️ زره: {'نداری' if armor == 'none' else ARMORS[armor][0]}\n"
            f"🧪 مدکیت: {medkits}/5"
        )

    elif text in ("شاپ", "فروشگاه"):
        await update.message.reply_text(
            "🛒 فروشگاه VOIDFALL",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ شمشیرها", callback_data="swords")],
                [InlineKeyboardButton("🛡️ زره‌ها", callback_data="armors")]
            ])
        )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")

    if not RENDER_URL:
        raise RuntimeError("RENDER_EXTERNAL_URL تنظیم نشده است.")

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_commands)
    )

    print("VOIDFALL is starting with webhook...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{RENDER_URL}/{TOKEN}",
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
