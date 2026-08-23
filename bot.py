import os
import sqlite3
import logging
import threading
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

        logger.info(
            "Health server running on port %s",
            PORT
        )

        server.serve_forever()

    except Exception:

        logger.exception(
            "Health server error"
        )


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
        (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.username,
        user.first_name
    ))

    cursor.execute("""
        UPDATE users
        SET username = ?,
            first_name = ?
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
# VOICE LIST
# =========================================================

VOICE_LIST = {

    # -------------------------
    # BANGLA
    # -------------------------

    "bn": {

        "male": [
            (
                "🇧🇩 বাংলা পুরুষ 1",
                "bn-BD-PradeepNeural"
            ),
        ],

        "female": [
            (
                "🇧🇩 বাংলা মহিলা 1",
                "bn-BD-NabanitaNeural"
            ),
        ],
    },


    # -------------------------
    # ENGLISH
    # -------------------------

    "en": {

        "male": [
            (
                "🇺🇸 English Male - Guy",
                "en-US-GuyNeural"
            ),
            (
                "🇺🇸 English Male - Christopher",
                "en-US-ChristopherNeural"
            ),
            (
                "🇺🇸 English Male - Eric",
                "en-US-EricNeural"
            ),
            (
                "🇬🇧 English Male - Ryan",
                "en-GB-RyanNeural"
            ),
        ],

        "female": [
            (
                "🇺🇸 English Female - Jenny",
                "en-US-JennyNeural"
            ),
            (
                "🇺🇸 English Female - Aria",
                "en-US-AriaNeural"
            ),
            (
                "🇺🇸 English Female - Michelle",
                "en-US-MichelleNeural"
            ),
            (
                "🇬🇧 English Female - Sonia",
                "en-GB-SoniaNeural"
            ),
        ],
    },


    # -------------------------
    # HINDI
    # -------------------------

    "hi": {

        "male": [
            (
                "🇮🇳 Hindi Male - Madhur",
                "hi-IN-MadhurNeural"
            ),
        ],

        "female": [
            (
                "🇮🇳 Hindi Female - Swara",
                "hi-IN-SwaraNeural"
            ),
        ],
    },


    # -------------------------
    # URDU
    # -------------------------

    "ur": {

        "male": [
            (
                "🇵🇰 Urdu Male - Asad",
                "ur-PK-AsadNeural"
            ),
        ],

        "female": [
            (
                "🇵🇰 Urdu Female - Uzma",
                "ur-PK-UzmaNeural"
            ),
        ],
    },


    # -------------------------
    # ARABIC
    # -------------------------

    "ar": {

        "male": [
            (
                "🇸🇦 Arabic Male - Hamed",
                "ar-SA-HamedNeural"
            ),
        ],

        "female": [
            (
                "🇸🇦 Arabic Female - Zariyah",
                "ar-SA-ZariyahNeural"
            ),
        ],
    },

}


# =========================================================
# VOICE MENU
# =========================================================

def voice_keyboard(language):

    voices = VOICE_LIST.get(
        language,
        VOICE_LIST["bn"]
    )

    keyboard = []

    keyboard.append([
        InlineKeyboardButton(
            "👨 পুরুষের Voice",
            callback_data="voice_menu_male"
        ),
        InlineKeyboardButton(
            "👩 মহিলার Voice",
            callback_data="voice_menu_female"
        ),
    ])

    return InlineKeyboardMarkup(keyboard)


def gender_voice_keyboard(language, gender):

    voices = VOICE_LIST.get(
        language,
        VOICE_LIST["bn"]
    ).get(
        gender,
        []
    )

    keyboard = []

    for name, voice_id in voices:

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"selectvoice_{voice_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ Back",
            callback_data="voice_back"
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

    if update.message:

        await update.message.reply_text(
            "🌐 Language নির্বাচন করুন:",
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

    if not user or not update.message:
        return

    language, voice = get_settings(
        user.id
    )

    await update.message.reply_text(
        "🎤 Voice নির্বাচন করুন:",
        reply_markup=voice_keyboard(language)
    )


# =========================================================
# CHANGE LANGUAGE
# =========================================================

async def change_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.message:

        await update.message.reply_text(
            "🌐 Language নির্বাচন করুন:",
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
        "🎤 এখন Voice নির্বাচন করুন:",
        parse_mode="HTML",
        reply_markup=voice_keyboard(language)
    )

    logger.info(
        "Language %s selected by user %s",
        language,
        user_id
    )


# =========================================================
# VOICE MENU - MALE
# =========================================================

async def male_voice_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    language, voice = get_settings(
        query.from_user.id
    )

    await query.edit_message_text(
        "👨 <b>পুরুষের Voice নির্বাচন করুন:</b>",
        parse_mode="HTML",
        reply_markup=gender_voice_keyboard(
            language,
            "male"
        )
    )


# =========================================================
# VOICE MENU - FEMALE
# =========================================================

async def female_voice_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    language, voice = get_settings(
        query.from_user.id
    )

    await query.edit_message_text(
        "👩 <b>মহিলার Voice নির্বাচন করুন:</b>",
        parse_mode="HTML",
        reply_markup=gender_voice_keyboard(
            language,
            "female"
        )
    )


# =========================================================
# VOICE BACK
# =========================================================

async def voice_back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    language, voice = get_settings(
        query.from_user.id
    )

    await query.edit_message_text(
        "🎤 Voice নির্বাচন করুন:",
        reply_markup=voice_keyboard(language)
    )


# =========================================================
# SELECT VOICE
# =========================================================

async def select_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    voice = query.data.replace(
        "selectvoice_",
        ""
    )

    set_voice(
        user_id,
        voice
    )

    await query.edit_message_text(
        "✅ <b>Voice selected!</b>\n\n"
        "এখন আপনার Text পাঠান।\n"
        "আমি সেটিকে ধীরে Voice/MP3 করে দেব।",
        parse_mode="HTML"
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
        "⏳ <b>Voice তৈরি হচ্ছে...</b>\n\n"
        "🐢 Speed: <b>30% Slow</b>\n"
        "একটু অপেক্ষা করুন।",
        parse_mode="HTML"
    )

    output_file = (
        DOWNLOAD_DIR /
        f"{user.id}_{update.message.message_id}.mp3"
    )

    try:

        logger.info(
            "Creating TTS: user=%s voice=%s rate=-30%%",
            user.id,
            voice
        )

        # =================================================
        # EDGE TTS
        # 30% SLOW
        # =================================================

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate="-30%"
        )

        await communicate.save(
            str(output_file)
        )

        logger.info(
            "MP3 created: %s",
            output_file
        )

        if not output_file.exists():

            raise FileNotFoundError(
                "MP3 file তৈরি হয়নি।"
            )

        # =================================================
        # SEND MP3
        # =================================================

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬇️ Download MP3",
                    callback_data=f"download_{output_file.name}"
                )
            ]
        ])

        with open(
            output_file,
            "rb"
        ) as audio_file:

            await update.message.reply_audio(
                audio=audio_file,
                title="VoiceGen BD",
                performer="VoiceGen BD Bot",
                caption=(
                    "🎙️ Voice তৈরি হয়েছে!\n"
                    "🐢 Speed: 30% Slow"
                ),
                reply_markup=keyboard
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
# DOWNLOAD BUTTON
# =========================================================

async def download_mp3(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer(
        "MP3 প্রস্তুত করা হচ্ছে..."
    )

    filename = query.data.replace(
        "download_",
        ""
    )

    file_path = DOWNLOAD_DIR / filename

    # Security check
    if file_path.parent != DOWNLOAD_DIR:

        await query.message.reply_text(
            "❌ Invalid file."
        )

        return

    if not file_path.exists():

        await query.message.reply_text(
            "❌ এই MP3 file আর available নেই।\n"
            "নতুন করে Text পাঠিয়ে Voice তৈরি করুন।"
        )

        return

    try:

        with open(
            file_path,
            "rb"
        ) as audio_file:

            await query.message.reply_document(
                document=audio_file,
                filename=filename,
                caption="⬇️ আপনার MP3 Download করুন।"
            )

    except Exception:

        logger.exception(
            "Download error"
        )

        await query.message.reply_text(
            "❌ MP3 পাঠানো যায়নি।"
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

    # Health server
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
    # COMMANDS
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

    # =====================================================
    # LANGUAGE
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            language_selection,
            pattern=r"^lang_"
        )
    )

    # =====================================================
    # VOICE MENU
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            male_voice_menu,
            pattern=r"^voice_menu_male$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            female_voice_menu,
            pattern=r"^voice_menu_female$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            voice_back,
            pattern=r"^voice_back$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            select_voice,
            pattern=r"^selectvoice_"
        )
    )

    # =====================================================
    # DOWNLOAD
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            download_mp3,
            pattern=r"^download_"
        )
    )

    # =====================================================
    # TEXT
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_voice
        )
    )

    # =====================================================
    # ERROR
    # =====================================================

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

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
