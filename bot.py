import os
import sqlite3
import logging
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv
from gtts import gTTS

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN পাওয়া যায়নি। Render Environment Variables চেক করুন।")

PORT = int(os.getenv("PORT", "10000"))

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "users.db"
DOWNLOAD_DIR = BASE_DIR / "downloads"

DOWNLOAD_DIR.mkdir(exist_ok=True)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

        self.wfile.write(
            b"VoiceGen BD Bot is running!"
        )

    def log_message(self, format, *args):
        return


def start_health_server():
    try:
        server = HTTPServer(
            ("0.0.0.0", PORT),
            HealthHandler
        )

        print(f"Health server running on port {PORT}")

        server.serve_forever()

    except Exception:
        logger.exception("Health server error")


# =========================================================
# DATABASE
# =========================================================

def init_db():

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            selected_language TEXT DEFAULT 'bn',
            selected_voice TEXT DEFAULT 'default'
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.username,
        user.first_name
    ))

    cursor.execute("""
        UPDATE users
        SET username = ?, first_name = ?
        WHERE user_id = ?
    """, (
        user.username,
        user.first_name,
        user.id
    ))

    conn.commit()
    conn.close()


def get_settings(user_id):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT selected_language, selected_voice
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0], row[1]

    return "bn", "default"


def set_language(user_id, language):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET selected_language = ?
        WHERE user_id = ?
    """, (
        language,
        user_id
    ))

    conn.commit()
    conn.close()


def set_voice(user_id, voice):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET selected_voice = ?
        WHERE user_id = ?
    """, (
        voice,
        user_id
    ))

    conn.commit()
    conn.close()


# =========================================================
# LANGUAGE KEYBOARD
# =========================================================

def language_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "🇧🇩 বাংলা",
                callback_data="lang_bn"
            ),
            InlineKeyboardButton(
                "🇬🇧 English",
                callback_data="lang_en"
            ),
        ],
        [
            InlineKeyboardButton(
                "🇮🇳 हिन्दी",
                callback_data="lang_hi"
            ),
            InlineKeyboardButton(
                "🇵🇰 اردو",
                callback_data="lang_ur"
            ),
        ],
        [
            InlineKeyboardButton(
                "🇸🇦 العربية",
                callback_data="lang_ar"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# VOICE KEYBOARD
# =========================================================

def voice_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "🎤 Default Voice",
                callback_data="voice_default"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔊 Standard",
                callback_data="voice_standard"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        user = update.effective_user

        if not user:
            return

        save_user(user)

        text = (
            "🎙️ <b>Welcome to VoiceGen BD!</b>\n\n"
            "আপনি এখানে Text থেকে Voice তৈরি করতে পারবেন।\n\n"
            "🌐 <b>Language নির্বাচন করুন:</b>"
        )

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=language_keyboard()
        )

        logger.info(
            "START received from user %s",
            user.id
        )

    except Exception:
        logger.exception("START handler error")


# =========================================================
# LANGUAGE COMMAND
# =========================================================

async def language_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🌐 Select your language:",
        reply_markup=language_keyboard()
    )


# =========================================================
# VOICE COMMAND
# =========================================================

async def voice_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🎤 Select your voice:",
        reply_markup=voice_keyboard()
    )


# =========================================================
# CHANGE LANGUAGE
# =========================================================

async def change_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🌐 Choose a language:",
        reply_markup=language_keyboard()
    )


# =========================================================
# LANGUAGE SELECTION
# =========================================================

async def language_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    language = query.data.replace(
        "lang_",
        ""
    )

    set_language(
        user_id,
        language
    )

    language_names = {
        "bn": "🇧🇩 বাংলা",
        "en": "🇬🇧 English",
        "hi": "🇮🇳 हिन्दी",
        "ur": "🇵🇰 اردو",
        "ar": "🇸🇦 العربية",
    }

    selected_name = language_names.get(
        language,
        "Unknown"
    )

    await query.edit_message_text(
        f"✅ Language selected: <b>{selected_name}</b>\n\n"
        "এখন আপনার Text পাঠান।\n"
        "আমি সেটিকে Voice/MP3 হিসেবে তৈরি করব।",
        parse_mode="HTML"
    )

    logger.info(
        "Language %s selected by user %s",
        language,
        user_id
    )


# =========================================================
# VOICE SELECTION
# =========================================================

async def voice_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    voice = query.data.replace(
        "voice_",
        ""
    )

    set_voice(
        user_id,
        voice
    )

    await query.edit_message_text(
        f"✅ Voice selected: {voice}\n\n"
        "এখন আপনার Text পাঠান।"
    )

    logger.info(
        "Voice %s selected by user %s",
        voice,
        user_id
    )


# =========================================================
# TEXT TO VOICE
# =========================================================

async def text_to_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    user = update.effective_user

    if not user:
        return

    save_user(user)

    text = update.message.text.strip()

    if not text:
        return

    logger.info(
        "Text received from user %s: %s",
        user.id,
        text[:100]
    )

    if len(text) > 3000:

        await update.message.reply_text(
            "❌ Text অনেক বড়।\n"
            "সর্বোচ্চ 3000 characters পাঠান।"
        )

        return

    language, voice = get_settings(
        user.id
    )

    await update.message.reply_text(
        "⏳ Voice তৈরি হচ্ছে...\n"
        "একটু অপেক্ষা করুন।"
    )

    language_map = {
        "bn": "bn",
        "en": "en",
        "hi": "hi",
        "ur": "ur",
        "ar": "ar",
    }

    lang_code = language_map.get(
        language,
        "bn"
    )

    output_file = (
        DOWNLOAD_DIR /
        f"{user.id}_{update.message.message_id}.mp3"
    )

    try:

        logger.info(
            "Creating TTS for user %s, language=%s",
            user.id,
            lang_code
        )

        tts = gTTS(
            text=text,
            lang=lang_code,
            slow=False
        )

        tts.save(
            str(output_file)
        )

        logger.info(
            "MP3 created: %s",
            output_file
        )

        await download_mp3(
            update,
            output_file
        )

        logger.info(
            "MP3 sent successfully to user %s",
            user.id
        )

    except Exception as e:

        logger.exception(
            "TTS Error"
        )

        await update.message.reply_text(
            "❌ Voice তৈরি করা যায়নি।\n\n"
            "দয়া করে আবার চেষ্টা করুন।\n\n"
            f"Error: {str(e)[:500]}"
        )

    finally:

        if output_file.exists():

            try:
                output_file.unlink()

            except Exception:
                logger.exception(
                    "Could not delete temporary MP3"
                )


# =========================================================
# SEND MP3
# =========================================================

async def download_mp3(
    update: Update,
    file_path
):

    with open(
        file_path,
        "rb"
    ) as audio_file:

        await update.message.reply_audio(
            audio=audio_file,
            title="VoiceGen BD",
            performer="VoiceGen BD Bot",
            caption="🎙️ Generated by VoiceGen BD"
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Exception while handling update:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("====================================")
    print("          VoiceGen BD Bot")
    print("====================================")
    print(f"Render PORT: {PORT}")
    print("Starting health server...")

    # Database
    init_db()

    # Render health server
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    print("Health server started.")

    # Telegram Application
    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =====================================================
    # HANDLERS
    # =====================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "language",
            language_command
        )
    )

    app.add_handler(
        CommandHandler(
            "voice",
            voice_command
        )
    )

    app.add_handler(
        CommandHandler(
            "changelanguage",
            change_language
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            language_selection,
            pattern=r"^lang_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            voice_selection,
            pattern=r"^voice_"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_voice
        )
    )

    app.add_error_handler(
        error_handler
    )

    # =====================================================
    # START
    # =====================================================

    print("====================================")
    print("VoiceGen BD Bot is running...")
    print("Waiting for Telegram messages...")
    print("====================================")

    # Important:
    # Remove old Telegram webhook before polling.
    # This prevents webhook/polling conflict.

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
