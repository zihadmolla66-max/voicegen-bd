import os
import sqlite3
import edge_tts

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from database import init_db


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


# =========================
# Language & Voice Settings
# =========================

LANGUAGES = {
    "bn": {
        "name": "🇧🇩 বাংলা",
        "voices": {
            "female": "bn-BD-NabanitaNeural",
            "male": "bn-BD-PradeepNeural",
        },
    },

    "en_us": {
        "name": "🇺🇸 English (US)",
        "voices": {
            "female": "en-US-JennyNeural",
            "male": "en-US-GuyNeural",
        },
    },

    "hi": {
        "name": "🇮🇳 Hindi",
        "voices": {
            "female": "hi-IN-SwaraNeural",
            "male": "hi-IN-MadhurNeural",
        },
    },

    "ur": {
        "name": "🇵🇰 Urdu",
        "voices": {
            "female": "ur-PK-UzmaNeural",
            "male": "ur-PK-AsadNeural",
        },
    },

    "ar": {
        "name": "🇸🇦 Arabic",
        "voices": {
            "female": "ar-SA-ZariyahNeural",
            "male": "ar-SA-HamedNeural",
        },
    },

    "es": {
        "name": "🇪🇸 Spanish",
        "voices": {
            "female": "es-ES-ElviraNeural",
            "male": "es-ES-AlvaroNeural",
        },
    },

    "fr": {
        "name": "🇫🇷 French",
        "voices": {
            "female": "fr-FR-DeniseNeural",
            "male": "fr-FR-HenriNeural",
        },
    },

    "ja": {
        "name": "🇯🇵 Japanese",
        "voices": {
            "female": "ja-JP-NanamiNeural",
            "male": "ja-JP-KeitaNeural",
        },
    },
}


# =========================
# Database
# =========================

def ensure_columns():

    conn = sqlite3.connect("voicegen.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    if "selected_voice" not in columns:
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN selected_voice TEXT DEFAULT 'female'
            """
        )

    if "selected_language" not in columns:
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN selected_language TEXT DEFAULT 'bn'
            """
        )

    conn.commit()
    conn.close()


def save_user(user):

    conn = sqlite3.connect("voicegen.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username)
        VALUES (?, ?)
        """,
        (user.id, user.username),
    )

    conn.commit()
    conn.close()


def get_settings(user_id):

    conn = sqlite3.connect("voicegen.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT selected_language, selected_voice
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    result = cursor.fetchone()

    conn.close()

    if result:
        language = result[0] or "bn"
        voice = result[1] or "female"

        if language not in LANGUAGES:
            language = "bn"

        if voice not in ["female", "male"]:
            voice = "female"

        return language, voice

    return "bn", "female"


def set_language(user_id, language):

    conn = sqlite3.connect("voicegen.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET selected_language = ?
        WHERE user_id = ?
        """,
        (language, user_id),
    )

    conn.commit()
    conn.close()


def set_voice(user_id, voice):

    conn = sqlite3.connect("voicegen.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET selected_voice = ?
        WHERE user_id = ?
        """,
        (voice, user_id),
    )

    conn.commit()
    conn.close()


# =========================
# Language Keyboard
# =========================

def language_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "🇧🇩 বাংলা",
                callback_data="lang:bn"
            ),
            InlineKeyboardButton(
                "🇺🇸 English",
                callback_data="lang:en_us"
            ),
        ],
        [
            InlineKeyboardButton(
                "🇮🇳 Hindi",
                callback_data="lang:hi"
            ),
            InlineKeyboardButton(
                "🇵🇰 Urdu",
                callback_data="lang:ur"
            ),
        ],
        [
            InlineKeyboardButton(
                "🇸🇦 Arabic",
                callback_data="lang:ar"
            ),
            InlineKeyboardButton(
                "🇪🇸 Spanish",
                callback_data="lang:es"
            ),
        ],
        [
            InlineKeyboardButton(
                "🇫🇷 French",
                callback_data="lang:fr"
            ),
            InlineKeyboardButton(
                "🇯🇵 Japanese",
                callback_data="lang:ja"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# Voice Keyboard
# =========================

def voice_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "👩 Female",
                callback_data="voice:female"
            ),
            InlineKeyboardButton(
                "👨 Male",
                callback_data="voice:male"
            ),
        ],
        [
            InlineKeyboardButton(
                "🌐 Change Language",
                callback_data="change_language"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    save_user(user)

    language, voice = get_settings(user.id)

    await update.message.reply_text(
        "🎙️ Welcome to VoiceGen BD!\n\n"
        "🌐 Language এবং 🎤 Voice নির্বাচন করো:",
        reply_markup=language_keyboard()
    )


# =========================
# /language
# =========================

async def language_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🌐 Select Language:",
        reply_markup=language_keyboard()
    )


# =========================
# /voice
# =========================

async def voice_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    language, voice = get_settings(user.id)

    language_name = LANGUAGES[language]["name"]

    await update.message.reply_text(
        f"🌐 Language: {language_name}\n"
        f"🎤 Voice: {voice.title()}\n\n"
        "Voice নির্বাচন করো:",
        reply_markup=voice_keyboard()
    )


# =========================
# Language Selection
# =========================

async def language_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    language = query.data.replace("lang:", "")

    if language not in LANGUAGES:
        return

    save_user(user)

    set_language(user.id, language)

    language_name = LANGUAGES[language]["name"]

    await query.edit_message_text(
        f"✅ Language selected!\n\n"
        f"🌐 {language_name}\n\n"
        "এখন Voice নির্বাচন করো:",
        reply_markup=voice_keyboard()
    )


# =========================
# Voice Selection
# =========================

async def voice_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    voice = query.data.replace("voice:", "")

    if voice not in ["female", "male"]:
        return

    save_user(user)

    language, old_voice = get_settings(user.id)

    set_voice(user.id, voice)

    language_name = LANGUAGES[language]["name"]

    await query.edit_message_text(
        "✅ Settings saved!\n\n"
        f"🌐 Language: {language_name}\n"
        f"🎤 Voice: {voice.title()}\n\n"
        "এখন Text পাঠাও। আমি Voice তৈরি করে দেব।"
    )


# =========================
# Change Language
# =========================

async def change_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(
        "🌐 Select Language:",
        reply_markup=language_keyboard()
    )


# =========================
# Text → Voice
# =========================

async def text_to_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    text = update.message.text

    if not text:
        return

    save_user(user)

    language, voice_type = get_settings(user.id)

    voice = LANGUAGES[language]["voices"][voice_type]

    await update.message.reply_text(
        "🎙️ Voice তৈরি হচ্ছে..."
    )

    output_file = (
        f"voice_{user.id}_"
        f"{update.message.message_id}.mp3"
    )

    try:

        communicate = edge_tts.Communicate(
            text,
            voice
        )

        await communicate.save(output_file)

        # Voice message
        with open(output_file, "rb") as audio:

            await update.message.reply_voice(
                voice=audio
            )

        # Download button
        keyboard = [
            [
                InlineKeyboardButton(
                    "⬇️ Download MP3",
                    callback_data=f"download:{output_file}"
                )
            ]
        ]

        await update.message.reply_text(
            "🎧 Voice তৈরি হয়েছে!\n\n"
            "MP3 download করতে নিচের button চাপো:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:

        print("Error:", e)

        await update.message.reply_text(
            "❌ Voice তৈরি করতে সমস্যা হয়েছে।"
        )

        if os.path.exists(output_file):
            os.remove(output_file)


# =========================
# Download MP3
# =========================

async def download_mp3(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    file_name = query.data.replace(
        "download:",
        "",
        1
    )

    # Security check
    if os.path.basename(file_name) != file_name:

        await query.message.reply_text(
            "❌ Invalid file."
        )

        return

    if not os.path.exists(file_name):

        await query.message.reply_text(
            "❌ MP3 file আর available নেই।\n"
            "আবার Text পাঠিয়ে Voice তৈরি করো।"
        )

        return

    try:

        with open(file_name, "rb") as audio:

            await query.message.reply_document(
                document=audio,
                filename=file_name,
                caption="⬇️ VoiceGen BD MP3"
            )

    except Exception as e:

        print("Download Error:", e)

        await query.message.reply_text(
            "❌ MP3 পাঠাতে সমস্যা হয়েছে।"
        )

    finally:

        if os.path.exists(file_name):
            os.remove(file_name)


# =========================
# Main
# =========================

def main():

    init_db()

    ensure_columns()

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # /language
    app.add_handler(
        CommandHandler(
            "language",
            language_command
        )
    )

    # /voice
    app.add_handler(
        CommandHandler(
            "voice",
            voice_command
        )
    )

    # Language selection
    app.add_handler(
        CallbackQueryHandler(
            language_selection,
            pattern=r"^lang:"
        )
    )

    # Voice selection
    app.add_handler(
        CallbackQueryHandler(
            voice_selection,
            pattern=r"^voice:"
        )
    )

    # Change language
    app.add_handler(
        CallbackQueryHandler(
            change_language,
            pattern=r"^change_language$"
        )
    )

    # Download MP3
    app.add_handler(
        CallbackQueryHandler(
            download_mp3,
            pattern=r"^download:"
        )
    )

    # Text → Voice
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_voice
        )
    )

    print("VoiceGen BD Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()