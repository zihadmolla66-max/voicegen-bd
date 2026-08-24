import os
import asyncio
import logging
import tempfile
from pathlib import Path

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
    raise ValueError("BOT_TOKEN পাওয়া যায়নি। Render Environment Variables চেক করুন।")

PORT = int(os.getenv("PORT", "10000"))

# Render automatically provides RENDER_EXTERNAL_URL.
# চাইলে Render Environment Variables-এ WEBHOOK_URL-ও দিতে পারো।
WEBHOOK_URL = os.getenv(
    "WEBHOOK_URL",
    os.getenv("RENDER_EXTERNAL_URL", "")
).rstrip("/")

if not WEBHOOK_URL:
    raise ValueError(
        "WEBHOOK_URL বা RENDER_EXTERNAL_URL পাওয়া যায়নি।"
    )

WEBHOOK_PATH = "/telegram"


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# USER SETTINGS
# =========================================================

# Free Render-এর জন্য settings memory-তে রাখা হচ্ছে।
# Service restart হলে আবার default হবে।
user_settings = {}


def get_settings(user_id):

    if user_id not in user_settings:
        user_settings[user_id] = {
            "language": "bn",
            "voice": "bn-BD-PradeepNeural",
        }

    return user_settings[user_id]


def set_language(user_id, language):

    settings = get_settings(user_id)
    settings["language"] = language


def set_voice(user_id, voice):

    settings = get_settings(user_id)
    settings["voice"] = voice


# =========================================================
# LANGUAGE NAMES
# =========================================================

LANGUAGE_NAMES = {
    "bn": "🇧🇩 বাংলা",
    "en": "🇬🇧 English",
    "hi": "🇮🇳 हिन्दी",
    "ur": "🇵🇰 اردو",
    "ar": "🇸🇦 العربية",
}


# =========================================================
# VOICE LIST
# =========================================================

VOICES = {

    # -----------------------------------------------------
    # BANGLA
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # ENGLISH
    # -----------------------------------------------------

    "en": {
        "male": [
            (
                "🇺🇸 English Male - Guy",
                "en-US-GuyNeural"
            ),
            (
                "🇺🇸 English Male - Davis",
                "en-US-DavisNeural"
            ),
            (
                "🇺🇸 English Male - Jason",
                "en-US-JasonNeural"
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


    # -----------------------------------------------------
    # HINDI
    # -----------------------------------------------------

    "hi": {
        "male": [
            (
                "🇮🇳 Hindi Male - Madhur",
                "hi-IN-MadhurNeural"
            ),
            (
                "🇮🇳 Hindi Male - Prabhat",
                "hi-IN-PrabhatNeural"
            ),
        ],

        "female": [
            (
                "🇮🇳 Hindi Female - Swara",
                "hi-IN-SwaraNeural"
            ),
            (
                "🇮🇳 Hindi Female - Ananya",
                "hi-IN-AnanyaNeural"
            ),
        ],
    },


    # -----------------------------------------------------
    # URDU
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # ARABIC
    # -----------------------------------------------------

    "ar": {
        "male": [
            (
                "🇸🇦 Arabic Male - Hamed",
                "ar-SA-HamedNeural"
            ),
            (
                "🇸🇦 Arabic Male - Khalid",
                "ar-SA-KhalidNeural"
            ),
        ],

        "female": [
            (
                "🇸🇦 Arabic Female - Zariyah",
                "ar-SA-ZariyahNeural"
            ),
            (
                "🇸🇦 Arabic Female - Amany",
                "ar-EG-SalmaNeural"
            ),
        ],
    },
}


# =========================================================
# START / MAIN MENU KEYBOARD
# =========================================================

def main_menu_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "🌐 Language",
                callback_data="menu_language"
            ),
            InlineKeyboardButton(
                "🎤 Voice",
                callback_data="menu_voice"
            ),
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="menu_help"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Start",
                callback_data="menu_start"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


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
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="menu_start"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# VOICE KEYBOARD
# =========================================================

def voice_keyboard(language):

    voices = VOICES.get(language, VOICES["bn"])

    keyboard = []

    # Male voices
    keyboard.append([
        InlineKeyboardButton(
            "👨 পুরুষের Voice",
            callback_data="voice_title_male"
        )
    ])

    for name, voice_id in voices["male"]:

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_id}"
            )
        ])

    # Female voices
    keyboard.append([
        InlineKeyboardButton(
            "👩 মহিলার Voice",
            callback_data="voice_title_female"
        )
    ])

    for name, voice_id in voices["female"]:

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back",
            callback_data="menu_start"
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

        get_settings(user.id)

        text = (
            "🎙️ <b>Welcome to VoiceGen BD!</b>\n\n"
            "আপনি Text থেকে Voice / MP3 তৈরি করতে পারবেন।\n\n"
            "🌐 প্রথমে Language নির্বাচন করুন অথবা\n"
            "🎤 Voice নির্বাচন করুন।\n\n"
            "তারপর শুধু আপনার Text পাঠান।\n\n"
            "🐢 Voice speed: <b>-30%</b>"
        )

        if update.message:

            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        elif update.callback_query:

            await update.callback_query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
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
        "🌐 <b>Language নির্বাচন করুন:</b>",
        parse_mode="HTML",
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

    settings = get_settings(user.id)

    language = settings["language"]

    await update.message.reply_text(
        "🎤 <b>আপনার Voice নির্বাচন করুন:</b>",
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
        "🌐 <b>Choose a language:</b>",
        parse_mode="HTML",
        reply_markup=language_keyboard()
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

    text = update.message.text.strip()

    if not text:
        return

    logger.info(
        "Text received from user %s: %s",
        user.id,
        text[:100]
    )

    # Character limit
    if len(text) > 3000:

        await update.message.reply_text(
            "❌ Text অনেক বড়।\n\n"
            "সর্বোচ্চ <b>3000 characters</b> পাঠান।",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

        return

    settings = get_settings(user.id)

    language = settings["language"]
    voice = settings["voice"]

    # -----------------------------------------------------
    # Processing message
    # -----------------------------------------------------

    processing_message = await update.message.reply_text(
        "⏳ <b>Voice তৈরি হচ্ছে...</b>\n\n"
        "🐢 Speed: -30%\n"
        "🎤 Voice প্রস্তুত করা হচ্ছে...",
        parse_mode="HTML"
    )

    output_file = None

    try:

        logger.info(
            "Creating TTS: user=%s language=%s voice=%s",
            user.id,
            language,
            voice
        )

        # -------------------------------------------------
        # Temporary MP3 file
        # -------------------------------------------------

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        )

        output_file = temp_file.name

        temp_file.close()

        # -------------------------------------------------
        # Edge TTS
        # -------------------------------------------------

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate="-30%"
        )

        await communicate.save(output_file)

        logger.info(
            "MP3 created successfully: %s",
            output_file
        )

        # -------------------------------------------------
        # Delete processing message
        # -------------------------------------------------

        try:
            await processing_message.delete()
        except Exception:
            pass

        # -------------------------------------------------
        # Send MP3
        # -------------------------------------------------

        with open(
            output_file,
            "rb"
        ) as audio_file:

            await update.message.reply_audio(
                audio=audio_file,
                title="VoiceGen BD",
                performer="VoiceGen BD",
                caption=(
                    "🎙️ <b>VoiceGen BD</b>\n"
                    "🐢 Speed: -30%"
                ),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

        logger.info(
            "MP3 sent successfully to user %s",
            user.id
        )

    except Exception as e:

        logger.exception(
            "TTS Error"
        )

        try:
            await processing_message.edit_text(
                "❌ <b>Voice তৈরি করা যায়নি।</b>\n\n"
                "দয়া করে আবার চেষ্টা করুন।",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            await update.message.reply_text(
                "❌ Voice তৈরি করা যায়নি।\n\n"
                "দয়া করে আবার চেষ্টা করুন।",
                reply_markup=main_menu_keyboard()
            )

        logger.error(
            "TTS Error details: %s",
            str(e)
        )

    finally:

        # -------------------------------------------------
        # Delete temporary MP3
        # -------------------------------------------------

        if output_file:

            try:

                path = Path(output_file)

                if path.exists():
                    path.unlink()

            except Exception:

                logger.exception(
                    "Could not delete temporary MP3"
                )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    user_id = query.from_user.id

    data = query.data

    # =====================================================
    # MAIN MENU
    # =====================================================

    if data == "menu_start":

        await start(
            update,
            context
        )

        return


    # =====================================================
    # LANGUAGE MENU
    # =====================================================

    if data == "menu_language":

        await query.edit_message_text(
            "🌐 <b>Language নির্বাচন করুন:</b>",
            parse_mode="HTML",
            reply_markup=language_keyboard()
        )

        return


    # =====================================================
    # VOICE MENU
    # =====================================================

    if data == "menu_voice":

        settings = get_settings(user_id)

        language = settings["language"]

        await query.edit_message_text(
            "🎤 <b>Voice নির্বাচন করুন:</b>",
            parse_mode="HTML",
            reply_markup=voice_keyboard(language)
        )

        return


    # =====================================================
    # HELP
    # =====================================================

    if data == "menu_help":

        await query.edit_message_text(
            "ℹ️ <b>VoiceGen BD Help</b>\n\n"
            "1️⃣ Language নির্বাচন করুন\n"
            "2️⃣ Male/Female Voice নির্বাচন করুন\n"
            "3️⃣ Text পাঠান\n"
            "4️⃣ Bot MP3 Voice তৈরি করে দেবে\n\n"
            "🐢 Voice speed: -30%\n"
            "🎵 Output: MP3",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

        return


    # =====================================================
    # LANGUAGE SELECTION
    # =====================================================

    if data.startswith("lang_"):

        language = data.replace(
            "lang_",
            "",
            1
        )

        if language not in LANGUAGE_NAMES:
            return

        set_language(
            user_id,
            language
        )

        # Language change হলে সেই language-এর default
        # male voice automatically select হবে।

        default_voice = VOICES[language]["male"][0][1]

        set_voice(
            user_id,
            default_voice
        )

        selected_name = LANGUAGE_NAMES[language]

        await query.edit_message_text(
            f"✅ <b>Language selected:</b> {selected_name}\n\n"
            "এখন আপনার পছন্দের Voice নির্বাচন করুন।",
            parse_mode="HTML",
            reply_markup=voice_keyboard(language)
        )

        logger.info(
            "Language %s selected by user %s",
            language,
            user_id
        )

        return


    # =====================================================
    # VOICE SELECT
    # =====================================================

    if data.startswith("voice_select|"):

        voice = data.split(
            "|",
            1
        )[1]

        set_voice(
            user_id,
            voice
        )

        await query.edit_message_text(
            "✅ <b>Voice selected successfully!</b>\n\n"
            "এখন আপনার Text পাঠান।\n\n"
            "🐢 Speed: -30%",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

        logger.info(
            "Voice %s selected by user %s",
            voice,
            user_id
        )

        return


    # =====================================================
    # VOICE CATEGORY BUTTONS
    # =====================================================

    if data == "voice_title_male":

        await query.answer(
            "👨 নিচে Male voices দেওয়া আছে।",
            show_alert=False
        )

        return


    if data == "voice_title_female":

        await query.answer(
            "👩 নিচে Female voices দেওয়া আছে।",
            show_alert=False
        )

        return


# =========================================================
# BOT COMMAND MENU
# =========================================================

async def post_init(
    application: Application
):

    await application.bot.set_my_commands([
        ("start", "🚀 Start VoiceGen BD"),
        ("language", "🌐 Change language"),
        ("voice", "🎤 Select voice"),
        ("changelanguage", "🌐 Change language"),
        ("help", "ℹ️ Help"),
    ])

    logger.info(
        "Bot commands registered successfully."
    )


# =========================================================
# HELP COMMAND
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "ℹ️ <b>VoiceGen BD</b>\n\n"
        "🌐 /language - Language নির্বাচন\n"
        "🎤 /voice - Voice নির্বাচন\n"
        "🔄 /start - Main menu\n\n"
        "Text পাঠালেই MP3 তৈরি হবে।\n"
        "🐢 Speed: -30%",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
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
    print(f"Webhook URL: {WEBHOOK_URL}{WEBHOOK_PATH}")
    print("Starting Telegram Webhook...")
    print("====================================")

    # -----------------------------------------------------
    # Application
    # -----------------------------------------------------

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # -----------------------------------------------------
    # Commands
    # -----------------------------------------------------

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
        CommandHandler(
            "help",
            help_command
        )
    )

    # -----------------------------------------------------
    # Callback buttons
    # -----------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # -----------------------------------------------------
    # Text messages
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_voice
        )
    )

    # -----------------------------------------------------
    # Error
    # -----------------------------------------------------

    app.add_error_handler(
        error_handler
    )

    # -----------------------------------------------------
    # WEBHOOK
    # -----------------------------------------------------

    webhook_url = (
        WEBHOOK_URL +
        WEBHOOK_PATH
    )

    print("====================================")
    print("VoiceGen BD Bot is starting...")
    print(f"Webhook: {webhook_url}")
    print("====================================")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH.lstrip("/"),
        webhook_url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
        max_connections=40,
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
