import os
import sqlite3
import logging
import threading
import asyncio
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

import edge_tts
from dotenv import load_dotenv

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
    raise ValueError(
        "BOT_TOKEN পাওয়া যায়নি। Render Environment Variables চেক করুন।"
    )

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
# VOICE LIST
# =========================================================

VOICES = {

    # -------------------------
    # BANGLA
    # -------------------------
    "bn": {
        "🇧🇩 বাংলা পুরুষ 1": "bn-BD-PradeepNeural",
        "🇧🇩 বাংলা মহিলা 1": "bn-BD-NabanitaNeural",
    },

    # -------------------------
    # ENGLISH
    # -------------------------
    "en": {
        "🇺🇸 English Male - Guy": "en-US-GuyNeural",
        "🇺🇸 English Male - Christopher": "en-US-ChristopherNeural",
        "🇺🇸 English Male - Eric": "en-US-EricNeural",
        "🇺🇸 English Female - Jenny": "en-US-JennyNeural",
        "🇺🇸 English Female - Aria": "en-US-AriaNeural",
        "🇺🇸 English Female - Michelle": "en-US-MichelleNeural",
    },

    # -------------------------
    # HINDI
    # -------------------------
    "hi": {
        "🇮🇳 हिन्दी Male - Madhur": "hi-IN-MadhurNeural",
        "🇮🇳 हिन्दी Female - Swara": "hi-IN-SwaraNeural",
    },

    # -------------------------
    # URDU
    # -------------------------
    "ur": {
        "🇵🇰 اردو Male - Asad": "ur-PK-AsadNeural",
        "🇵🇰 اردو Female - Uzma": "ur-PK-UzmaNeural",
    },

    # -------------------------
    # ARABIC
    # -------------------------
    "ar": {
        "🇸🇦 العربية Male - Hamed": "ar-SA-HamedNeural",
        "🇸🇦 العربية Female - Zariyah": "ar-SA-ZariyahNeural",
    },
}


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
            selected_voice TEXT DEFAULT 'bn-BD-PradeepNeural'
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name, selected_language, selected_voice)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user.id,
        user.username,
        user.first_name,
        "bn",
        "bn-BD-PradeepNeural"
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

    return "bn", "bn-BD-PradeepNeural"


def set_language(user_id, language):

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    default_voice = list(
        VOICES.get(language, VOICES["bn"]).values()
    )[0]

    cursor.execute("""
        UPDATE users
        SET selected_language = ?,
            selected_voice = ?
        WHERE user_id = ?
    """, (
        language,
        default_voice,
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
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

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

        print(
            f"Health server running on port {PORT}"
        )

        server.serve_forever()

    except Exception:

        logger.exception(
            "Health server error"
        )


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

def voice_keyboard(language):

    voices = VOICES.get(
        language,
        VOICES["bn"]
    )

    keyboard = []

    for name, voice_id in voices.items():

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice:{voice_id}"
            )
        ])

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
            "আপনি এখানে Text থেকে Voice/MP3 তৈরি করতে পারবেন।\n\n"
            "🌐 <b>প্রথমে Language নির্বাচন করুন:</b>"
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

        logger.exception(
            "START handler error"
        )


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

    user = update.effective_user

    if not user:
        return

    save_user(user)

    language, voice = get_settings(
        user.id
    )

    await update.message.reply_text(
        "🎤 <b>Voice নির্বাচন করুন:</b>",
        parse_mode="HTML",
        reply_markup=voice_keyboard(language)
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

        f"✅ Language selected: "
        f"<b>{selected_name}</b>\n\n"

        "🎤 এখন আপনার Voice নির্বাচন করুন:",

        parse_mode="HTML",

        reply_markup=voice_keyboard(language)

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

    voice_id = query.data.replace(
        "voice:",
        ""
    )

    set_voice(
        user_id,
        voice_id
    )

    await query.edit_message_text(

        "✅ <b>Voice selected!</b>\n\n"
        "📝 এখন আপনার Text পাঠান।\n\n"
        "🎙️ আমি সেটিকে MP3 Voice-এ তৈরি করে দেব।",

        parse_mode="HTML"

    )

    logger.info(
        "Voice %s selected by user %s",
        voice_id,
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
        "⏳ <b>Voice তৈরি হচ্ছে...</b>\n\n"
        "একটু অপেক্ষা করুন।",
        parse_mode="HTML"
    )

    message_id = update.message.message_id

    output_file = (
        DOWNLOAD_DIR /
        f"{user.id}_{message_id}.mp3"
    )

    try:

        logger.info(
            "Creating TTS for user %s, voice=%s",
            user.id,
            voice
        )

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice
        )

        await communicate.save(
            str(output_file)
        )

        logger.info(
            "MP3 created: %s",
            output_file
        )

        # ---------------------------------------------
        # SEND AUDIO
        # ---------------------------------------------

        with open(
            output_file,
            "rb"
        ) as audio_file:

            await update.message.reply_audio(

                audio=audio_file,

                title="VoiceGen BD",

                performer="VoiceGen BD Bot",

                caption=(
                    "🎙️ Voice তৈরি হয়েছে!\n\n"
                    "⬇️ নিচের Download MP3 button "
                    "চাপলে MP3 ফাইল পাবেন।"
                ),

                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "⬇️ Download MP3",
                            callback_data=(
                                f"download:{user.id}:"
                                f"{message_id}"
                            )
                        )
                    ]
                ])

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

            "❌ <b>Voice তৈরি করা যায়নি।</b>\n\n"
            "দয়া করে আবার চেষ্টা করুন।\n\n"
            f"Error: {str(e)[:500]}",

            parse_mode="HTML"
        )


# =========================================================
# DOWNLOAD MP3 BUTTON
# =========================================================

async def download_mp3(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer(
        "⏳ MP3 প্রস্তুত হচ্ছে..."
    )

    try:

        parts = query.data.split(":")

        if len(parts) != 3:
            return

        user_id = int(parts[1])
        message_id = int(parts[2])

        # Security check
        if query.from_user.id != user_id:

            await query.answer(
                "❌ এই ফাইল আপনার জন্য নয়।",
                show_alert=True
            )

            return

        file_path = (
            DOWNLOAD_DIR /
            f"{user_id}_{message_id}.mp3"
        )

        if not file_path.exists():

            await query.message.reply_text(
                "❌ MP3 ফাইলটি আর পাওয়া যাচ্ছে না।\n"
                "নতুন করে Text পাঠিয়ে Voice তৈরি করুন।"
            )

            return

        with open(
            file_path,
            "rb"
        ) as audio_file:

            await query.message.reply_document(

                document=audio_file,

                filename="VoiceGen-BD.mp3",

                caption=(
                    "⬇️ আপনার MP3 Download করুন।\n"
                    "🎙️ VoiceGen BD"
                )

            )

        logger.info(
            "MP3 downloaded by user %s",
            user_id
        )

        # Delete after sending
        try:
            file_path.unlink()
        except Exception:
            pass

    except Exception:

        logger.exception(
            "Download error"
        )

        await query.message.reply_text(
            "❌ MP3 পাঠাতে সমস্যা হয়েছে।"
        )


# =========================================================
# CLEAN OLD FILES
# =========================================================

def cleanup_old_files():

    try:

        now = time.time()

        for file in DOWNLOAD_DIR.glob("*.mp3"):

            try:

                age = now - file.stat().st_mtime

                # Delete files older than 2 hours
                if age > 7200:

                    file.unlink()

            except Exception:
                pass

    except Exception:

        logger.exception(
            "Cleanup error"
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

    print(
        f"Render PORT: {PORT}"
    )

    # ---------------------------------------------
    # DATABASE
    # ---------------------------------------------

    init_db()

    # ---------------------------------------------
    # CLEAN OLD MP3
    # ---------------------------------------------

    cleanup_old_files()

    # ---------------------------------------------
    # HEALTH SERVER
    # ---------------------------------------------

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    print(
        "Health server started."
    )

    # ---------------------------------------------
    # TELEGRAM APPLICATION
    # ---------------------------------------------

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # ---------------------------------------------
    # COMMANDS
    # ---------------------------------------------

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

    # ---------------------------------------------
    # LANGUAGE BUTTON
    # ---------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            language_selection,
            pattern=r"^lang_"
        )
    )

    # ---------------------------------------------
    # VOICE BUTTON
    # ---------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            voice_selection,
            pattern=r"^voice:"
        )
    )

    # ---------------------------------------------
    # DOWNLOAD BUTTON
    # ---------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            download_mp3,
            pattern=r"^download:"
        )
    )

    # ---------------------------------------------
    # TEXT MESSAGE
    # ---------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_voice
        )
    )

    # ---------------------------------------------
    # ERROR HANDLER
    # ---------------------------------------------

    app.add_error_handler(
        error_handler
    )

    # ---------------------------------------------
    # START BOT
    # ---------------------------------------------

    print("====================================")
    print("VoiceGen BD Bot is running...")
    print("Waiting for Telegram messages...")
    print("====================================")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
