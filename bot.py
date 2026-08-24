import os
import asyncio
import logging
import tempfile
from pathlib import Path

import edge_tts
from dotenv import load_dotenv
from aiohttp import web

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

WEBHOOK_URL = os.getenv(
    "WEBHOOK_URL",
    os.getenv("RENDER_EXTERNAL_URL", "")
).rstrip("/")

if not WEBHOOK_URL:
    raise ValueError(
        "WEBHOOK_URL অথবা RENDER_EXTERNAL_URL পাওয়া যায়নি।"
    )

WEBHOOK_PATH = "/telegram"

FULL_WEBHOOK_URL = WEBHOOK_URL + WEBHOOK_PATH

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("VoiceGenBD")


# =========================================================
# USER SETTINGS
# =========================================================

# Render restart/redeploy হলে এই settings reset হবে।
# Permanent storage চাইলে পরে external database যোগ করা যাবে।

user_settings = {}


def get_settings(user_id: int):

    if user_id not in user_settings:

        user_settings[user_id] = {
            "language": "bn",
            "voice": "bn-BD-PradeepNeural",
        }

    return user_settings[user_id]


def set_language(user_id: int, language: str):

    settings = get_settings(user_id)
    settings["language"] = language


def set_voice(user_id: int, voice: str):

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
                "bn-BD-PradeepNeural",
            ),
        ],

        "female": [
            (
                "🇧🇩 বাংলা মহিলা 1",
                "bn-BD-NabanitaNeural",
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
                "en-US-GuyNeural",
            ),
            (
                "🇺🇸 English Male - Davis",
                "en-US-DavisNeural",
            ),
            (
                "🇺🇸 English Male - Jason",
                "en-US-JasonNeural",
            ),
            (
                "🇬🇧 English Male - Ryan",
                "en-GB-RyanNeural",
            ),
        ],

        "female": [
            (
                "🇺🇸 English Female - Jenny",
                "en-US-JennyNeural",
            ),
            (
                "🇺🇸 English Female - Aria",
                "en-US-AriaNeural",
            ),
            (
                "🇺🇸 English Female - Michelle",
                "en-US-MichelleNeural",
            ),
            (
                "🇬🇧 English Female - Sonia",
                "en-GB-SoniaNeural",
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
                "hi-IN-MadhurNeural",
            ),
            (
                "🇮🇳 Hindi Male - Prabhat",
                "hi-IN-PrabhatNeural",
            ),
        ],

        "female": [
            (
                "🇮🇳 Hindi Female - Swara",
                "hi-IN-SwaraNeural",
            ),
            (
                "🇮🇳 Hindi Female - Ananya",
                "hi-IN-AnanyaNeural",
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
                "ur-PK-AsadNeural",
            ),
        ],

        "female": [
            (
                "🇵🇰 Urdu Female - Uzma",
                "ur-PK-UzmaNeural",
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
                "ar-SA-HamedNeural",
            ),
            (
                "🇸🇦 Arabic Male - Khalid",
                "ar-SA-KhalidNeural",
            ),
        ],

        "female": [
            (
                "🇸🇦 Arabic Female - Zariyah",
                "ar-SA-ZariyahNeural",
            ),
            (
                "🇪🇬 Arabic Female - Salma",
                "ar-EG-SalmaNeural",
            ),
        ],
    },
}


# =========================================================
# VOICE VALIDATION
# =========================================================

def is_valid_voice(language: str, voice: str) -> bool:

    language_voices = VOICES.get(language)

    if not language_voices:
        return False

    for category in ("male", "female"):

        for _, voice_id in language_voices[category]:

            if voice_id == voice:
                return True

    return False


# =========================================================
# MAIN MENU
# =========================================================

def main_menu_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "🌐 Language",
                callback_data="menu_language",
            ),
            InlineKeyboardButton(
                "🎤 Voice",
                callback_data="menu_voice",
            ),
        ],

        [
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="menu_help",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔄 Start",
                callback_data="menu_start",
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
                callback_data="lang_bn",
            ),
            InlineKeyboardButton(
                "🇬🇧 English",
                callback_data="lang_en",
            ),
        ],

        [
            InlineKeyboardButton(
                "🇮🇳 हिन्दी",
                callback_data="lang_hi",
            ),
            InlineKeyboardButton(
                "🇵🇰 اردو",
                callback_data="lang_ur",
            ),
        ],

        [
            InlineKeyboardButton(
                "🇸🇦 العربية",
                callback_data="lang_ar",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="menu_start",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# VOICE KEYBOARD
# =========================================================

def voice_keyboard(language: str):

    voices = VOICES.get(
        language,
        VOICES["bn"],
    )

    keyboard = []

    # Male title
    keyboard.append([
        InlineKeyboardButton(
            "👨 পুরুষের Voice",
            callback_data="voice_title_male",
        )
    ])

    # Male voices
    for name, voice_id in voices["male"]:

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_id}",
            )
        ])

    # Female title
    keyboard.append([
        InlineKeyboardButton(
            "👩 মহিলার Voice",
            callback_data="voice_title_female",
        )
    ])

    # Female voices
    for name, voice_id in voices["female"]:

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_id}",
            )
        ])

    # Back
    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back",
            callback_data="menu_start",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
                reply_markup=main_menu_keyboard(),
            )

        elif update.callback_query:

            await update.callback_query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )

        logger.info(
            "START received from user %s",
            user.id,
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
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    await update.message.reply_text(
        "🌐 <b>Language নির্বাচন করুন:</b>",
        parse_mode="HTML",
        reply_markup=language_keyboard(),
    )


# =========================================================
# VOICE COMMAND
# =========================================================

async def voice_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    user = update.effective_user

    if not user:
        return

    settings = get_settings(user.id)

    language = settings["language"]

    await update.message.reply_text(
        "🎤 <b>আপনার Voice নির্বাচন করুন:</b>",
        parse_mode="HTML",
        reply_markup=voice_keyboard(language),
    )


# =========================================================
# CHANGE LANGUAGE
# =========================================================

async def change_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    await update.message.reply_text(
        "🌐 <b>Choose a language:</b>",
        parse_mode="HTML",
        reply_markup=language_keyboard(),
    )


# =========================================================
# HELP COMMAND
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    await update.message.reply_text(
        "ℹ️ <b>VoiceGen BD</b>\n\n"
        "🌐 /language - Language নির্বাচন\n"
        "🎤 /voice - Voice নির্বাচন\n"
        "🔄 /start - Main menu\n"
        "ℹ️ /help - Help\n\n"
        "Text পাঠালেই MP3 তৈরি হবে।\n\n"
        "🐢 Speed: -30%\n"
        "🎵 Output: MP3",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


# =========================================================
# TEXT TO VOICE
# =========================================================

async def text_to_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
        text[:100],
    )

    # Character limit
    if len(text) > 3000:

        await update.message.reply_text(
            "❌ Text অনেক বড়।\n\n"
            "সর্বোচ্চ <b>3000 characters</b> পাঠান।",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )

        return

    # User settings
    settings = get_settings(user.id)

    language = settings["language"]

    voice = settings["voice"]

    # Check voice
    if not is_valid_voice(
        language,
        voice,
    ):

        voice = VOICES[language]["male"][0][1]

        set_voice(
            user.id,
            voice,
        )

    # Processing message
    processing_message = await update.message.reply_text(
        "⏳ <b>Voice তৈরি হচ্ছে...</b>\n\n"
        "🐢 Speed: -30%\n"
        "🎤 Voice প্রস্তুত করা হচ্ছে...",
        parse_mode="HTML",
    )

    output_file = None

    try:

        logger.info(
            "Creating TTS: user=%s language=%s voice=%s",
            user.id,
            language,
            voice,
        )

        # Temporary MP3
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False,
        )

        output_file = temp_file.name

        temp_file.close()

        # Edge TTS
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate="-30%",
        )

        await communicate.save(
            output_file
        )

        # Check file
        output_path = Path(output_file)

        if not output_path.exists():

            raise RuntimeError(
                "MP3 file তৈরি হয়নি।"
            )

        if output_path.stat().st_size <= 0:

            raise RuntimeError(
                "MP3 file empty হয়েছে।"
            )

        logger.info(
            "MP3 created successfully: %s",
            output_file,
        )

        # Delete processing message
        try:

            await processing_message.delete()

        except Exception:

            pass

        # Send MP3
        with open(
            output_file,
            "rb",
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
                reply_markup=main_menu_keyboard(),
            )

        logger.info(
            "MP3 sent successfully to user %s",
            user.id,
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
                reply_markup=main_menu_keyboard(),
            )

        except Exception:

            try:

                await update.message.reply_text(
                    "❌ Voice তৈরি করা যায়নি।\n\n"
                    "দয়া করে আবার চেষ্টা করুন।",
                    reply_markup=main_menu_keyboard(),
                )

            except Exception:

                pass

        logger.error(
            "TTS Error details: %s",
            str(e),
        )

    finally:

        # Delete temporary MP3
        if output_file:

            try:

                path = Path(output_file)

                if path.exists():

                    path.unlink()

                    logger.info(
                        "Temporary MP3 deleted: %s",
                        output_file,
                    )

            except Exception:

                logger.exception(
                    "Could not delete temporary MP3"
                )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    user_id = query.from_user.id

    data = query.data or ""

    logger.info(
        "Callback received: user=%s data=%s",
        user_id,
        data,
    )

    # =====================================================
    # MAIN MENU
    # =====================================================

    if data == "menu_start":

        await start(
            update,
            context,
        )

        return

    # =====================================================
    # LANGUAGE MENU
    # =====================================================

    if data == "menu_language":

        await query.edit_message_text(
            "🌐 <b>Language নির্বাচন করুন:</b>",
            parse_mode="HTML",
            reply_markup=language_keyboard(),
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
            reply_markup=voice_keyboard(language),
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
            reply_markup=main_menu_keyboard(),
        )

        return

    # =====================================================
    # LANGUAGE SELECTION
    # =====================================================

    if data.startswith("lang_"):

        language = data.replace(
            "lang_",
            "",
            1,
        )

        if language not in VOICES:

            logger.warning(
                "Invalid language: %s",
                language,
            )

            return

        set_language(
            user_id,
            language,
        )

        # Default male voice
        default_voice = VOICES[language]["male"][0][1]

        set_voice(
            user_id,
            default_voice,
        )

        selected_name = LANGUAGE_NAMES.get(
            language,
            language,
        )

        await query.edit_message_text(
            f"✅ <b>Language selected:</b> "
            f"{selected_name}\n\n"
            "এখন আপনার পছন্দের Voice নির্বাচন করুন।",
            parse_mode="HTML",
            reply_markup=voice_keyboard(language),
        )

        logger.info(
            "Language %s selected by user %s",
            language,
            user_id,
        )

        return

    # =====================================================
    # VOICE SELECT
    # =====================================================

    if data.startswith("voice_select|"):

        voice = data.split(
            "|",
            1,
        )[1]

        settings = get_settings(user_id)

        language = settings["language"]

        # Validate voice
        if not is_valid_voice(
            language,
            voice,
        ):

            await query.edit_message_text(
                "❌ এই Voice বর্তমানে available নয়।\n\n"
                "দয়া করে অন্য Voice নির্বাচন করুন।",
                parse_mode="HTML",
                reply_markup=voice_keyboard(language),
            )

            logger.warning(
                "Invalid voice selected: user=%s voice=%s",
                user_id,
                voice,
            )

            return

        set_voice(
            user_id,
            voice,
        )

        await query.edit_message_text(
            "✅ <b>Voice selected successfully!</b>\n\n"
            "এখন আপনার Text পাঠান।\n\n"
            "🐢 Speed: -30%",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )

        logger.info(
            "Voice %s selected by user %s",
            voice,
            user_id,
        )

        return

    # =====================================================
    # VOICE CATEGORY
    # =====================================================

    if data == "voice_title_male":

        await query.answer(
            "👨 নিচে Male voices দেওয়া আছে।",
            show_alert=False,
        )

        return

    if data == "voice_title_female":

        await query.answer(
            "👩 নিচে Female voices দেওয়া আছে।",
            show_alert=False,
        )

        return

    # =====================================================
    # UNKNOWN CALLBACK
    # =====================================================

    logger.warning(
        "Unknown callback data: %s",
        data,
    )


# =========================================================
# BOT COMMAND MENU
# =========================================================

async def post_init(
    application: Application,
):

    await application.bot.set_my_commands([

        (
            "start",
            "🚀 Start VoiceGen BD",
        ),

        (
            "language",
            "🌐 Change language",
        ),

        (
            "voice",
            "🎤 Select voice",
        ),

        (
            "changelanguage",
            "🌐 Change language",
        ),

        (
            "help",
            "ℹ️ Help",
        ),
    ])

    logger.info(
        "Bot commands registered successfully."
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Exception while handling update:",
        exc_info=context.error,
    )


# =========================================================
# HEALTH ENDPOINT
# =========================================================

async def health(request):

    return web.Response(
        text="VoiceGen BD Bot is running!",
        status=200,
    )


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

async def telegram_webhook(request):

    # Optional secret verification
    if WEBHOOK_SECRET:

        incoming_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token",
            "",
        )

        if incoming_secret != WEBHOOK_SECRET:

            logger.warning(
                "Invalid Telegram webhook secret."
            )

            return web.Response(
                text="Unauthorized",
                status=401,
            )

    # Read JSON
    try:

        data = await request.json()

    except Exception:

        logger.warning(
            "Invalid JSON received by webhook."
        )

        return web.Response(
            text="Bad Request",
            status=400,
        )

    # Convert JSON to Telegram Update
    try:

        application = request.app[
            "telegram_application"
        ]

        update = Update.de_json(
            data,
            application.bot,
        )

    except Exception:

        logger.exception(
            "Could not parse Telegram update."
        )

        return web.Response(
            text="Bad Request",
            status=400,
        )

    # Put update into Telegram queue
    try:

        await request.app[
            "telegram_application"
        ].update_queue.put(update)

    except Exception:

        logger.exception(
            "Could not put update into queue."
        )

        return web.Response(
            text="Server Error",
            status=500,
        )

    return web.Response(
        text="OK",
        status=200,
    )


# =========================================================
# CREATE WEB APP
# =========================================================

async def create_web_app(
    application: Application,
):

    web_app = web.Application()

    web_app["telegram_application"] = application

    # Health
    web_app.router.add_get(
        "/",
        health,
    )

    # Telegram webhook
    web_app.router.add_post(
        WEBHOOK_PATH,
        telegram_webhook,
    )

    return web_app


# =========================================================
# RUN BOT
# =========================================================

async def run_bot():

    print()
    print("========================================")
    print("          VoiceGen BD Bot")
    print("========================================")
    print(f"Render PORT : {PORT}")
    print(f"Webhook URL : {FULL_WEBHOOK_URL}")
    print(f"Health URL  : {WEBHOOK_URL}/")
    print("========================================")
    print()

    # -----------------------------------------------------
    # Telegram Application
    # -----------------------------------------------------

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # -----------------------------------------------------
    # Commands
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "language",
            language_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "voice",
            voice_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "changelanguage",
            change_language,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    # -----------------------------------------------------
    # Callback buttons
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )

    # -----------------------------------------------------
    # Text messages
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_voice,
        )
    )

    # -----------------------------------------------------
    # Error handler
    # -----------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    # -----------------------------------------------------
    # Initialize
    # -----------------------------------------------------

    await application.initialize()

    # -----------------------------------------------------
    # Start Telegram application
    # -----------------------------------------------------

    await application.start()

    # -----------------------------------------------------
    # Delete old webhook
    # -----------------------------------------------------

    try:

        await application.bot.delete_webhook(
            drop_pending_updates=False,
        )

        logger.info(
            "Old webhook removed."
        )

    except Exception:

        logger.exception(
            "Could not delete old webhook."
        )

    # -----------------------------------------------------
    # Set new webhook
    # -----------------------------------------------------

    webhook_kwargs = {
        "url": FULL_WEBHOOK_URL,
        "allowed_updates": Update.ALL_TYPES,
        "drop_pending_updates": False,
        "max_connections": 40,
    }

    if WEBHOOK_SECRET:

        webhook_kwargs["secret_token"] = WEBHOOK_SECRET

    await application.bot.set_webhook(
        **webhook_kwargs
    )

    logger.info(
        "Telegram webhook set successfully: %s",
        FULL_WEBHOOK_URL,
    )

    # -----------------------------------------------------
    # Webhook information
    # -----------------------------------------------------

    try:

        webhook_info = await application.bot.get_webhook_info()

        logger.info(
            "Webhook info: url=%s pending=%s",
            webhook_info.url,
            webhook_info.pending_update_count,
        )

    except Exception:

        logger.exception(
            "Could not get webhook information."
        )

    # -----------------------------------------------------
    # Create web application
    # -----------------------------------------------------

    web_app = await create_web_app(
        application
    )

    # -----------------------------------------------------
    # Start HTTP server
    # -----------------------------------------------------

    runner = web.AppRunner(
        web_app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    print()
    print("========================================")
    print("       VoiceGen BD Bot is RUNNING")
    print("========================================")
    print(f"Health : {WEBHOOK_URL}/")
    print(f"Webhook: {FULL_WEBHOOK_URL}")
    print("========================================")
    print()

    # -----------------------------------------------------
    # Keep server running
    # -----------------------------------------------------

    try:

        await asyncio.Event().wait()

    finally:

        logger.info(
            "Stopping VoiceGen BD Bot..."
        )

        # Delete webhook
        try:

            await application.bot.delete_webhook(
                drop_pending_updates=False,
            )

        except Exception:

            logger.exception(
                "Could not delete webhook."
            )

        # Stop Telegram application
        try:

            await application.stop()

        except Exception:

            logger.exception(
                "Could not stop Telegram application."
            )

        # Shutdown Telegram application
        try:

            await application.shutdown()

        except Exception:

            logger.exception(
                "Could not shutdown Telegram application."
            )

        # Cleanup HTTP server
        try:

            await runner.cleanup()

        except Exception:

            logger.exception(
                "Could not cleanup web server."
            )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            run_bot()
        )

    except KeyboardInterrupt:

        print(
            "\nVoiceGen BD Bot stopped."
        )
