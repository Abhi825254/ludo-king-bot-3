import os
import threading
from flask import Flask
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7194958748"))

PRICE = "₹49"

# Content IDs - admin will set these later
PREVIEW_VIDEO = None
PAID_VIDEO = None
PAID_FILE_1 = None
PAID_FILE_2 = None
QR_FILE_ID = None

# Payment requests
payments = {}

# =========================
# FLASK SERVER FOR RENDER
# =========================

app = Flask(__name__)


@app.route("/")
def home():
    return "Ludo King Bot 3 is running!"


def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    name = user.first_name or "Friend"
    telegram_id = user.id
    username = user.username or "N/A"

    welcome_text = (
        f"👋 Hello {name}!\n\n"
        "🎮 Welcome to Ludo King Bot 3\n\n"
        "🆔 Your Telegram ID: "
        f"{telegram_id}\n"
        f"👤 Username: @{username}\n\n"
        "👇 Pehle preview video dekho.\n"
        "Full access ke liye neeche button dabao."
    )

    keyboard = [
        [InlineKeyboardButton(
            "💳 GET FULL ACCESS ₹49",
            callback_data="buy"
        )],
        [InlineKeyboardButton(
            "❌ I DON'T NEED THIS NOW",
            callback_data="cancel"
        )]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    if PREVIEW_VIDEO:
        await update.message.reply_video(
            video=PREVIEW_VIDEO,
            caption=welcome_text,
            reply_markup=markup
        )
    else:
        await update.message.reply_text(
            welcome_text + "\n\n⚠️ Preview video abhi set nahi hai.",
            reply_markup=markup
        )


# =========================
# BUY
# =========================

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(
            "📱 SHARE PHONE NUMBER",
            callback_data="share_phone"
        )],
        [InlineKeyboardButton(
            "💳 PAYMENT DONE",
            callback_data="payment_done"
        )],
        [InlineKeyboardButton(
            "🆘 HELP",
            callback_data="help"
        )]
    ]

    text = (
        "💳 FULL ACCESS\n\n"
        f"💰 Price: {PRICE}\n\n"
        "1️⃣ QR code scan karo\n"
        "2️⃣ ₹49 payment karo\n"
        "3️⃣ Apna phone number share karo\n"
        "4️⃣ PAYMENT DONE dabao\n"
        "5️⃣ Screenshot + UTR submit karo\n\n"
        "⏳ Payment manually verify hogi."
    )

    if QR_FILE_ID:
        await query.message.reply_photo(
            photo=QR_FILE_ID,
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.message.reply_text(
            "⚠️ QR abhi set nahi hai.\n\n" + text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# =========================
# PHONE NUMBER
# =========================

async def share_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    phone_keyboard = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 SHARE MY PHONE NUMBER",
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await query.message.reply_text(
        "📱 Please apna phone number share karo.\n\n"
        "Neeche **SHARE MY PHONE NUMBER** button dabao.",
        reply_markup=phone_keyboard
    )


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    if contact.user_id and contact.user_id != update.effective_user.id:
        await update.message.reply_text(
            "⚠️ Please apna hi Telegram contact share karo."
        )
        return

    phone = contact.phone_number
    user_id = update.effective_user.id

    payments.setdefault(user_id, {})
    payments[user_id]["phone"] = phone

    await update.message.reply_text(
        "✅ Phone number received!\n\n"
        "Ab **PAYMENT DONE** button dabao.",
        reply_markup=ReplyKeyboardRemove()
    )

    keyboard = [
        [InlineKeyboardButton(
            "💳 PAYMENT DONE",
            callback_data="payment_done"
        )]
    ]

    await update.message.reply_text(
        "Payment complete hone ke baad neeche button dabao.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# PAYMENT DONE
# =========================

async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    payments.setdefault(user_id, {})

    context.user_data["payment_step"] = "screenshot"

    await query.message.reply_text(
        "📸 PAYMENT SCREENSHOT BHEJO\n\n"
        "Payment successful hone ka screenshot upload karo."
    )


# =========================
# RECEIVE SCREENSHOT
# =========================

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("payment_step") != "screenshot":
        return

    user_id = update.effective_user.id

    photo = update.message.photo[-1]

    payments.setdefault(user_id, {})
    payments[user_id]["screenshot"] = photo.file_id

    context.user_data["payment_step"] = "utr"

    await update.message.reply_text(
        "✅ Screenshot received!\n\n"
        "🔢 Ab apna **UTR / Transaction ID** bhejo."
    )


# =========================
# RECEIVE UTR
# =========================

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("payment_step") != "utr":
        return

    user = update.effective_user
    user_id = user.id

    utr = update.message.text.strip()

    if len(utr) < 4:
        await update.message.reply_text(
            "⚠️ Please valid UTR / Transaction ID bhejo."
        )
        return

    payments.setdefault(user_id, {})
    payments[user_id]["utr"] = utr

    context.user_data["payment_step"] = "waiting"

    phone = payments[user_id].get("phone", "Not provided")
    screenshot = payments[user_id].get("screenshot")

    username = (
        f"@{user.username}"
        if user.username
        else "N/A"
    )

    admin_text = (
        "💰 NEW PAYMENT REQUEST\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"🔗 Username: {username}\n"
        f"📱 Phone: {phone}\n"
        f"💵 Amount: {PRICE}\n"
        f"🔢 UTR: {utr}\n\n"
        "👇 MANUAL VERIFICATION"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ APPROVE",
                callback_data=f"approve_{user_id}"
            ),
            InlineKeyboardButton(
                "❌ REJECT",
                callback_data=f"reject_{user_id}"
            )
        ]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    if screenshot:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=screenshot,
            caption=f"📸 Payment Screenshot\nUser ID: {user_id}"
        )

    await update.message.reply_text(
        "⏳ PAYMENT SUBMITTED\n\n"
        "Aapka payment request admin ke paas bhej diya gaya hai.\n\n"
        "✅ Manual verification ke baad approved hua "
        "to paid content automatically mil jayega."
    )


# =========================
# ADMIN APPROVE / REJECT
# =========================

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Not authorized.",
            show_alert=True
        )
        return

    await query.answer()

    data = query.data

    # APPROVE
    if data.startswith("approve_"):

        user_id = int(data.split("_")[1])

        if user_id not in payments:
            await query.message.reply_text(
                "⚠️ Payment request data nahi mila."
            )
            return

        if not PAID_VIDEO or not PAID_FILE_1 or not PAID_FILE_2:
            await query.message.reply_text(
                "⚠️ Paid content abhi complete set nahi hai."
            )
            return

        # Prevent duplicate approval
        if payments[user_id].get("status") == "approved":
            await query.message.reply_text(
                "⚠️ Ye payment already approved hai."
            )
            return

        payments[user_id]["status"] = "approved"

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 PAYMENT APPROVED!\n\n"
                    "✅ Full access unlocked.\n"
                    "👇 Aapka paid content:"
                )
            )

            await context.bot.send_video(
                chat_id=user_id,
                video=PAID_VIDEO,
                caption="🎬 Paid Video"
            )

            await context.bot.send_document(
                chat_id=user_id,
                document=PAID_FILE_1,
                caption="📁 File 1"
            )

            await context.bot.send_document(
                chat_id=user_id,
                document=PAID_FILE_2,
                caption="📁 File 2"
            )

            await query.message.edit_text(
                query.message.text +
                "\n\n✅ APPROVED & CONTENT SENT"
            )

        except Exception as e:
            await query.message.reply_text(
                f"⚠️ Delivery error: {e}"
            )

    # REJECT
    elif data.startswith("reject_"):

        user_id = int(data.split("_")[1])

        if user_id in payments:
            payments[user_id]["status"] = "rejected"

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ PAYMENT REJECTED\n\n"
                "Payment verify nahi ho paya.\n\n"
                "Agar aapko lagta hai payment successful hai, "
                "HELP se contact kare."
            )
        )

        await query.message.edit_text(
            query.message.text +
            "\n\n❌ REJECTED"
        )


# =========================
# HELP
# =========================

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "🆘 HELP\n\n"
        "Payment ya access se related problem ho to "
        "admin se Telegram par contact kare."
    )


# =========================
# CANCEL
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "👍 Theek hai!\n\n"
        "Jab bhi full access chahiye ho, /start bhej dena."
    )


# =========================
# ADMIN CONTENT COMMANDS
# =========================

async def set_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PREVIEW_VIDEO

    if update.effective_user.id != ADMIN_ID:
        return

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.video
    ):
        PREVIEW_VIDEO = update.message.reply_to_message.video.file_id

        await update.message.reply_text(
            "✅ Preview video saved!"
        )
    else:
        await update.message.reply_text(
            "Pehle preview video bhejo, "
            "phir us video ko reply karke /setpreview bhejo."
        )


async def set_paid_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PAID_VIDEO

    if update.effective_user.id != ADMIN_ID:
        return

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.video
    ):
        PAID_VIDEO = update.message.reply_to_message.video.file_id

        await update.message.reply_text(
            "✅ Paid video saved!"
        )
    else:
        await update.message.reply_text(
            "Paid video ko reply karke /setpaidvideo bhejo."
        )


async def set_file1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PAID_FILE_1

    if update.effective_user.id != ADMIN_ID:
        return

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.document
    ):
        PAID_FILE_1 = (
            update.message.reply_to_message.document.file_id
        )

        await update.message.reply_text(
            "✅ File 1 saved!"
        )
    else:
        await update.message.reply_text(
            "File 1 ko reply karke /setfile1 bhejo."
        )


async def set_file2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PAID_FILE_2

    if update.effective_user.id != ADMIN_ID:
        return

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.document
    ):
        PAID_FILE_2 = (
            update.message.reply_to_message.document.file_id
        )

        await update.message.reply_text(
            "✅ File 2 saved!"
        )
    else:
        await update.message.reply_text(
            "File 2 ko reply karke /setfile2 bhejo."
        )


async def set_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QR_FILE_ID

    if update.effective_user.id != ADMIN_ID:
        return

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.photo
    ):
        QR_FILE_ID = (
            update.message.reply_to_message.photo[-1].file_id
        )

        await update.message.reply_text(
            "✅ QR saved!"
        )
    else:
        await update.message.reply_text(
            "QR photo ko reply karke /setqr bhejo."
        )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN environment variable missing"
        )

    # Render web server
    threading.Thread(
        target=run_server,
        daemon=True
    ).start()

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # User commands
    application.add_handler(
        CommandHandler("start", start)
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(
            buy,
            pattern="^buy$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            share_phone,
            pattern="^share_phone$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            payment_done,
            pattern="^payment_done$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            help_button,
            pattern="^help$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            cancel,
            pattern="^cancel$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            admin_action,
            pattern="^(approve|reject)_"
        )
    )

    # Admin content commands
    application.add_handler(
        CommandHandler(
            "setpreview",
            set_preview
        )
    )

    application.add_handler(
        CommandHandler(
            "setpaidvideo",
            set_paid_video
        )
    )

    application.add_handler(
        CommandHandler(
            "setfile1",
            set_file1
        )
    )

    application.add_handler(
        CommandHandler(
            "setfile2",
            set_file2
        )
    )

    application.add_handler(
        CommandHandler(
            "setqr",
            set_qr
        )
    )

    # Contact / screenshot / text
    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            receive_contact
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_photo
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_text
        )
    )

    print("Ludo King Bot 3 started...")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()