import os
import asyncio
import logging
import tempfile
import shutil
from pathlib import Path

import edge_tts
from dotenv import load_dotenv
from aiohttp import web

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    ""
).strip()


# =========================================================
# VOICE SETTINGS
# =========================================================

VOICE_RATE = "-30%"


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

user_settings = {}


def get_settings(user_id: int):

    if user_id not in user_settings:

        user_settings[user_id] = {
            "language": "bn",
            "voice": "bn_male_1",
        }

    return user_settings[user_id]


def set_language(user_id: int, language: str):

    settings = get_settings(user_id)

    settings["language"] = language


def set_voice(user_id: int, voice_key: str):

    settings = get_settings(user_id)

    settings["voice"] = voice_key


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
#
# Format:
# "voice_key": {
#     "name": "...",
#     "voice": "...",
#     "pitch": "..."
# }
#
# Kids voice = normal voice + higher pitch.
# =========================================================

VOICES = {

    # =====================================================
    # BANGLA
    # =====================================================

    "bn": {

        "male": [

            (
                "👨 বাংলা Male 1",
                "bn_male_1",
            ),

            (
                "👨 বাংলা Male 2",
                "bn_male_2",
            ),
        ],

        "female": [

            (
                "👩 বাংলা Female 1",
                "bn_female_1",
            ),

            (
                "👩 বাংলা Female 2",
                "bn_female_2",
            ),
        ],

        "kids_male": [

            (
                "👦 বাংলা Kids Male 1",
                "bn_kids_male_1",
            ),

            (
                "👦 বাংলা Kids Male 2",
                "bn_kids_male_2",
            ),
        ],

        "kids_female": [

            (
                "👧 বাংলা Kids Female 1",
                "bn_kids_female_1",
            ),

            (
                "👧 বাংলা Kids Female 2",
                "bn_kids_female_2",
            ),
        ],
    },


    # =====================================================
    # ENGLISH
    # =====================================================

    "en": {

        "male": [

            (
                "👨 English Male 1",
                "en_male_1",
            ),

            (
                "👨 English Male 2",
                "en_male_2",
            ),
        ],

        "female": [

            (
                "👩 English Female 1",
                "en_female_1",
            ),

            (
                "👩 English Female 2",
                "en_female_2",
            ),
        ],

        "kids_male": [

            (
                "👦 English Kids Male 1",
                "en_kids_male_1",
            ),

            (
                "👦 English Kids Male 2",
                "en_kids_male_2",
            ),
        ],

        "kids_female": [

            (
                "👧 English Kids Female 1",
                "en_kids_female_1",
            ),

            (
                "👧 English Kids Female 2",
                "en_kids_female_2",
            ),
        ],
    },


    # =====================================================
    # HINDI
    # =====================================================

    "hi": {

        "male": [

            (
                "👨 Hindi Male 1",
                "hi_male_1",
            ),

            (
                "👨 Hindi Male 2",
                "hi_male_2",
            ),
        ],

        "female": [

            (
                "👩 Hindi Female 1",
                "hi_female_1",
            ),

            (
                "👩 Hindi Female 2",
                "hi_female_2",
            ),
        ],

        "kids_male": [

            (
                "👦 Hindi Kids Male 1",
                "hi_kids_male_1",
            ),

            (
                "👦 Hindi Kids Male 2",
                "hi_kids_male_2",
            ),
        ],

        "kids_female": [

            (
                "👧 Hindi Kids Female 1",
                "hi_kids_female_1",
            ),

            (
                "👧 Hindi Kids Female 2",
                "hi_kids_female_2",
            ),
        ],
    },


    # =====================================================
    # URDU
    # =====================================================

    "ur": {

        "male": [

            (
                "👨 Urdu Male 1",
                "ur_male_1",
            ),

            (
                "👨 Urdu Male 2",
                "ur_male_2",
            ),
        ],

        "female": [

            (
                "👩 Urdu Female 1",
                "ur_female_1",
            ),

            (
                "👩 Urdu Female 2",
                "ur_female_2",
            ),
        ],

        "kids_male": [

            (
                "👦 Urdu Kids Male 1",
                "ur_kids_male_1",
            ),

            (
                "👦 Urdu Kids Male 2",
                "ur_kids_male_2",
            ),
        ],

        "kids_female": [

            (
                "👧 Urdu Kids Female 1",
                "ur_kids_female_1",
            ),

            (
                "👧 Urdu Kids Female 2",
                "ur_kids_female_2",
            ),
        ],
    },


    # =====================================================
    # ARABIC
    # =====================================================

    "ar": {

        "male": [

            (
                "👨 Arabic Male 1",
                "ar_male_1",
            ),

            (
                "👨 Arabic Male 2",
                "ar_male_2",
            ),
        ],

        "female": [

            (
                "👩 Arabic Female 1",
                "ar_female_1",
            ),

            (
                "👩 Arabic Female 2",
                "ar_female_2",
            ),
        ],

        "kids_male": [

            (
                "👦 Arabic Kids Male 1",
                "ar_kids_male_1",
            ),

            (
                "👦 Arabic Kids Male 2",
                "ar_kids_male_2",
            ),
        ],

        "kids_female": [

            (
                "👧 Arabic Kids Female 1",
                "ar_kids_female_1",
            ),

            (
                "👧 Arabic Kids Female 2",
                "ar_kids_female_2",
            ),
        ],
    },
}


# =========================================================
# ACTUAL EDGE-TTS VOICE PROFILES
# =========================================================

VOICE_PROFILES = {

    # -----------------------------------------------------
    # BANGLA
    # -----------------------------------------------------

    "bn_male_1": {
        "voice": "bn-BD-PradeepNeural",
        "pitch": "0Hz",
    },

    "bn_male_2": {
        "voice": "bn-IN-BashkarNeural",
        "pitch": "0Hz",
    },

    "bn_female_1": {
        "voice": "bn-BD-NabanitaNeural",
        "pitch": "0Hz",
    },

    "bn_female_2": {
        "voice": "bn-IN-TanishaaNeural",
        "pitch": "0Hz",
    },

    "bn_kids_male_1": {
        "voice": "bn-BD-PradeepNeural",
        "pitch": "+35Hz",
    },

    "bn_kids_male_2": {
        "voice": "bn-IN-BashkarNeural",
        "pitch": "+45Hz",
    },

    "bn_kids_female_1": {
        "voice": "bn-BD-NabanitaNeural",
        "pitch": "+30Hz",
    },

    "bn_kids_female_2": {
        "voice": "bn-IN-TanishaaNeural",
        "pitch": "+40Hz",
    },


    # -----------------------------------------------------
    # ENGLISH
    # -----------------------------------------------------

    "en_male_1": {
        "voice": "en-US-GuyNeural",
        "pitch": "0Hz",
    },

    "en_male_2": {
        "voice": "en-US-AndrewNeural",
        "pitch": "0Hz",
    },

    "en_female_1": {
        "voice": "en-US-JennyNeural",
        "pitch": "0Hz",
    },

    "en_female_2": {
        "voice": "en-US-AriaNeural",
        "pitch": "0Hz",
    },

    "en_kids_male_1": {
        "voice": "en-US-GuyNeural",
        "pitch": "+45Hz",
    },

    "en_kids_male_2": {
        "voice": "en-US-AndrewNeural",
        "pitch": "+55Hz",
    },

    "en_kids_female_1": {
        "voice": "en-US-AnaNeural",
        "pitch": "+15Hz",
    },

    "en_kids_female_2": {
        "voice": "en-GB-MaisieNeural",
        "pitch": "+15Hz",
    },


    # -----------------------------------------------------
    # HINDI
    # -----------------------------------------------------

    "hi_male_1": {
        "voice": "hi-IN-MadhurNeural",
        "pitch": "0Hz",
    },

    "hi_male_2": {
        "voice": "hi-IN-PrabhatNeural",
        "pitch": "0Hz",
    },

    "hi_female_1": {
        "voice": "hi-IN-SwaraNeural",
        "pitch": "0Hz",
    },

    "hi_female_2": {
        "voice": "hi-IN-AnanyaNeural",
        "pitch": "0Hz",
    },

    "hi_kids_male_1": {
        "voice": "hi-IN-MadhurNeural",
        "pitch": "+40Hz",
    },

    "hi_kids_male_2": {
        "voice": "hi-IN-PrabhatNeural",
        "pitch": "+50Hz",
    },

    "hi_kids_female_1": {
        "voice": "hi-IN-SwaraNeural",
        "pitch": "+30Hz",
    },

    "hi_kids_female_2": {
        "voice": "hi-IN-AnanyaNeural",
        "pitch": "+40Hz",
    },


    # -----------------------------------------------------
    # URDU
    # -----------------------------------------------------

    "ur_male_1": {
        "voice": "ur-PK-AsadNeural",
        "pitch": "0Hz",
    },

    "ur_male_2": {
        "voice": "ur-IN-SalmanNeural",
        "pitch": "0Hz",
    },

    "ur_female_1": {
        "voice": "ur-PK-UzmaNeural",
        "pitch": "0Hz",
    },

    "ur_female_2": {
        "voice": "ur-IN-GulNeural",
        "pitch": "0Hz",
    },

    "ur_kids_male_1": {
        "voice": "ur-PK-AsadNeural",
        "pitch": "+40Hz",
    },

    "ur_kids_male_2": {
        "voice": "ur-IN-SalmanNeural",
        "pitch": "+50Hz",
    },

    "ur_kids_female_1": {
        "voice": "ur-PK-UzmaNeural",
        "pitch": "+30Hz",
    },

    "ur_kids_female_2": {
        "voice": "ur-IN-GulNeural",
        "pitch": "+40Hz",
    },


    # -----------------------------------------------------
    # ARABIC
    # -----------------------------------------------------

    "ar_male_1": {
        "voice": "ar-SA-HamedNeural",
        "pitch": "0Hz",
    },

    "ar_male_2": {
        "voice": "ar-AE-HamdanNeural",
        "pitch": "0Hz",
    },

    "ar_female_1": {
        "voice": "ar-SA-ZariyahNeural",
        "pitch": "0Hz",
    },

    "ar_female_2": {
        "voice": "ar-EG-SalmaNeural",
        "pitch": "0Hz",
    },

    "ar_kids_male_1": {
        "voice": "ar-SA-HamedNeural",
        "pitch": "+40Hz",
    },

    "ar_kids_male_2": {
        "voice": "ar-AE-HamdanNeural",
        "pitch": "+50Hz",
    },

    "ar_kids_female_1": {
        "voice": "ar-SA-ZariyahNeural",
        "pitch": "+30Hz",
    },

    "ar_kids_female_2": {
        "voice": "ar-EG-SalmaNeural",
        "pitch": "+40Hz",
    },
}


# =========================================================
# VOICE VALIDATION
# =========================================================

def is_valid_voice(language: str, voice_key: str) -> bool:

    language_voices = VOICES.get(language)

    if not language_voices:
        return False

    for category in (
        "male",
        "female",
        "kids_male",
        "kids_female",
    ):

        for _, key in language_voices.get(category, []):

            if key == voice_key:
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


    # =====================================================
    # MALE
    # =====================================================

    keyboard.append([
        InlineKeyboardButton(
            "👨 Male Voices",
            callback_data="voice_title_male",
        )
    ])

    for name, voice_key in voices.get(
        "male",
        [],
    ):

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_key}",
            )
        ])


    # =====================================================
    # FEMALE
    # =====================================================

    keyboard.append([
        InlineKeyboardButton(
            "👩 Female Voices",
            callback_data="voice_title_female",
        )
    ])

    for name, voice_key in voices.get(
        "female",
        [],
    ):

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_key}",
            )
        ])


    # =====================================================
    # KIDS MALE
    # =====================================================

    keyboard.append([
        InlineKeyboardButton(
            "👦 Kids Male Voices",
            callback_data="voice_title_kids_male",
        )
    ])

    for name, voice_key in voices.get(
        "kids_male",
        [],
    ):

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_key}",
            )
        ])


    # =====================================================
    # KIDS FEMALE
    # =====================================================

    keyboard.append([
        InlineKeyboardButton(
            "👧 Kids Female Voices",
            callback_data="voice_title_kids_female",
        )
    ])

    for name, voice_key in voices.get(
        "kids_female",
        [],
    ):

        keyboard.append([
            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_key}",
            )
        ])


    keyboard.append([
        InlineKeyboardButton(
            "🔙 Back",
            callback_data="menu_start",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# TEXT TO MP3
#
# IMPORTANT:
# No word splitting.
# No word pause.
# No pydub.
# Entire text is generated in ONE TTS request.
# =========================================================

async def create_voice_audio(
    text: str,
    voice_key: str,
    output_file: str,
):

    profile = VOICE_PROFILES.get(
        voice_key
    )

    if not profile:

        raise RuntimeError(
            "Voice profile পাওয়া যায়নি।"
        )

    voice = profile["voice"]

    pitch = profile.get(
        "pitch",
        "0Hz",
    )

    logger.info(
        "Generating full text TTS: voice=%s pitch=%s",
        voice,
        pitch,
    )


    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=VOICE_RATE,
        pitch=pitch,
    )


    await communicate.save(
        output_file
    )


    output_path = Path(
        output_file
    )


    if not output_path.exists():

        raise RuntimeError(
            "MP3 file তৈরি হয়নি।"
        )


    if output_path.stat().st_size <= 0:

        raise RuntimeError(
            "MP3 file empty হয়েছে।"
        )


    logger.info(
        "Full text MP3 generated successfully."
    )


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

        get_settings(
            user.id
        )


        text = (
            "🎙️ <b>Welcome to VoiceGen BD!</b>\n\n"

            "আপনি Text থেকে Voice / MP3 তৈরি করতে পারবেন।\n\n"

            "🌐 <b>Language</b> নির্বাচন করুন।\n"

            "🎤 <b>Voice</b> নির্বাচন করুন।\n\n"

            "👨 2 Male Voice\n"
            "👩 2 Female Voice\n"
            "👦 2 Kids Male Voice\n"
            "👧 2 Kids Female Voice\n\n"

            "⏸️ <b>Word-by-word pause OFF</b>\n"
            "পুরো Text একসাথে natural voice-এ তৈরি হবে।\n\n"

            "🐢 Speed: <b>-30%</b>\n"
            "🎵 Output: <b>MP3</b>"
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

    settings = get_settings(
        user.id
    )

    language = settings[
        "language"
    ]


    await update.message.reply_text(

        "🎤 <b>আপনার Voice নির্বাচন করুন:</b>\n\n"

        "👨 2 Male\n"
        "👩 2 Female\n"
        "👦 2 Kids Male\n"
        "👧 2 Kids Female",

        parse_mode="HTML",

        reply_markup=voice_keyboard(
            language
        ),
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
# HELP
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

        "👨 2 Male Voice\n"
        "👩 2 Female Voice\n"
        "👦 2 Kids Male Voice\n"
        "👧 2 Kids Female Voice\n\n"

        "⏸️ Word-by-word pause: <b>OFF</b>\n"
        "🎙️ পুরো Text একসাথে generate হবে\n\n"

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


    # =====================================================
    # TEXT LENGTH
    # =====================================================

    if len(text) > 3000:

        await update.message.reply_text(

            "❌ Text অনেক বড়।\n\n"
            "সর্বোচ্চ <b>3000 characters</b> পাঠান।",

            parse_mode="HTML",

            reply_markup=main_menu_keyboard(),
        )

        return


    # =====================================================
    # USER SETTINGS
    # =====================================================

    settings = get_settings(
        user.id
    )

    language = settings[
        "language"
    ]

    voice_key = settings[
        "voice"
    ]


    # =====================================================
    # VALIDATE VOICE
    # =====================================================

    if not is_valid_voice(
        language,
        voice_key,
    ):

        voice_key = VOICES[
            language
        ][
            "male"
        ][
            0
        ][
            1
        ]

        set_voice(
            user.id,
            voice_key,
        )


    # =====================================================
    # PROCESSING MESSAGE
    # =====================================================

    processing_message = (
        await update.message.reply_text(

            "⏳ <b>Voice তৈরি হচ্ছে...</b>\n\n"

            "🎤 Voice প্রস্তুত করা হচ্ছে...\n"
            "🎙️ পুরো Text একসাথে generate হচ্ছে...\n"
            "⏸️ Word-by-word pause: <b>OFF</b>\n"
            "🐢 Speed: -30%",

            parse_mode="HTML",
        )
    )


    output_file = None


    try:

        # =================================================
        # TEMP MP3
        # =================================================

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False,
        )

        output_file = temp_file.name

        temp_file.close()


        # =================================================
        # CREATE FULL AUDIO
        # =================================================

        await create_voice_audio(

            text=text,

            voice_key=voice_key,

            output_file=output_file,
        )


        output_path = Path(
            output_file
        )


        if not output_path.exists():

            raise RuntimeError(
                "Final MP3 file তৈরি হয়নি।"
            )


        if output_path.stat().st_size <= 0:

            raise RuntimeError(
                "Final MP3 file empty হয়েছে।"
            )


        # =================================================
        # DELETE PROCESSING MESSAGE
        # =================================================

        try:

            await processing_message.delete()

        except Exception:

            pass


        # =================================================
        # SEND AUDIO
        # =================================================

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

                    f"🌐 Language: "
                    f"{LANGUAGE_NAMES.get(language, language)}\n"

                    "⏸️ Word pause: OFF\n"

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

        # =================================================
        # DELETE TEMP FILE
        # =================================================

        if output_file:

            try:

                path = Path(
                    output_file
                )

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
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return


    await query.answer()


    user_id = query.from_user.id

    data = query.data or ""


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

        settings = get_settings(
            user_id
        )

        language = settings[
            "language"
        ]


        await query.edit_message_text(

            "🎤 <b>Voice নির্বাচন করুন:</b>\n\n"

            "👨 2 Male\n"
            "👩 2 Female\n"
            "👦 2 Kids Male\n"
            "👧 2 Kids Female",

            parse_mode="HTML",

            reply_markup=voice_keyboard(
                language
            ),
        )

        return


    # =====================================================
    # HELP MENU
    # =====================================================

    if data == "menu_help":

        await query.edit_message_text(

            "ℹ️ <b>VoiceGen BD Help</b>\n\n"

            "1️⃣ Language নির্বাচন করুন\n"
            "2️⃣ Voice নির্বাচন করুন\n"
            "3️⃣ Text পাঠান\n"
            "4️⃣ Bot MP3 তৈরি করবে\n\n"

            "👨 2 Male Voice\n"
            "👩 2 Female Voice\n"
            "👦 2 Kids Male Voice\n"
            "👧 2 Kids Female Voice\n\n"

            "⏸️ Word-by-word pause: <b>OFF</b>\n"
            "🎙️ পুরো Text একসাথে generate হবে\n\n"

            "🐢 Speed: -30%\n"
            "🎵 Output: MP3",

            parse_mode="HTML",

            reply_markup=main_menu_keyboard(),
        )

        return


    # =====================================================
    # LANGUAGE SELECT
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


        default_voice = VOICES[
            language
        ][
            "male"
        ][
            0
        ][
            1
        ]


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

            reply_markup=voice_keyboard(
                language
            ),
        )

        return


    # =====================================================
    # VOICE SELECT
    # =====================================================

    if data.startswith("voice_select|"):

        voice_key = data.split(
            "|",
            1,
        )[1]


        settings = get_settings(
            user_id
        )

        language = settings[
            "language"
        ]


        if not is_valid_voice(
            language,
            voice_key,
        ):

            await query.edit_message_text(

                "❌ এই Voice বর্তমানে available নয়।\n\n"
                "দয়া করে অন্য Voice নির্বাচন করুন।",

                parse_mode="HTML",

                reply_markup=voice_keyboard(
                    language
                ),
            )

            return


        set_voice(
            user_id,
            voice_key,
        )


        await query.edit_message_text(

            "✅ <b>Voice selected successfully!</b>\n\n"

            "এখন আপনার Text পাঠান।\n\n"

            "⏸️ Word-by-word pause: <b>OFF</b>\n"
            "🐢 Speed: -30%",

            parse_mode="HTML",

            reply_markup=main_menu_keyboard(),
        )

        return


    # =====================================================
    # VOICE CATEGORY TITLES
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


    if data == "voice_title_kids_male":

        await query.answer(
            "👦 নিচে Kids Male voices দেওয়া আছে।",
            show_alert=False,
        )

        return


    if data == "voice_title_kids_female":

        await query.answer(
            "👧 নিচে Kids Female voices দেওয়া আছে।",
            show_alert=False,
        )

        return


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


    try:

        await request.app[
            "telegram_application"
        ].update_queue.put(
            update
        )


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


    web_app[
        "telegram_application"
    ] = application


    web_app.router.add_get(
        "/",
        health,
    )


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

    print(
        f"Render PORT : {PORT}"
    )

    print(
        f"Webhook URL : {FULL_WEBHOOK_URL}"
    )

    print(
        f"Health URL  : {WEBHOOK_URL}/"
    )

    print(
        "Word Pause  : OFF"
    )

    print(
        f"Voice Rate  : {VOICE_RATE}"
    )

    print("========================================")
    print()


    # =====================================================
    # CHECK FFMPEG
    #
    # FFmpeg is NOT required for TTS generation now.
    # This is only an informational check.
    # =====================================================

    ffmpeg_path = shutil.which(
        "ffmpeg"
    )


    if ffmpeg_path:

        logger.info(
            "FFmpeg found: %s",
            ffmpeg_path,
        )

    else:

        logger.info(
            "FFmpeg not required for current TTS mode."
        )


    # =====================================================
    # TELEGRAM APPLICATION
    # =====================================================

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )


    # =====================================================
    # COMMANDS
    # =====================================================

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


    # =====================================================
    # CALLBACK BUTTONS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )


    # =====================================================
    # TEXT MESSAGES
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_voice,
        )
    )


    # =====================================================
    # ERROR HANDLER
    # =====================================================

    application.add_error_handler(
        error_handler
    )


    # =====================================================
    # INITIALIZE
    # =====================================================

    await application.initialize()


    # =====================================================
    # START TELEGRAM APPLICATION
    # =====================================================

    await application.start()


    # =====================================================
    # DELETE OLD WEBHOOK
    # =====================================================

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


    # =====================================================
    # SET NEW WEBHOOK
    # =====================================================

    webhook_kwargs = {

        "url": FULL_WEBHOOK_URL,

        "allowed_updates": Update.ALL_TYPES,

        "drop_pending_updates": False,

        "max_connections": 40,
    }


    if WEBHOOK_SECRET:

        webhook_kwargs[
            "secret_token"
        ] = WEBHOOK_SECRET


    await application.bot.set_webhook(
        **webhook_kwargs
    )


    logger.info(
        "Telegram webhook set successfully: %s",
        FULL_WEBHOOK_URL,
    )


    # =====================================================
    # WEBHOOK INFORMATION
    # =====================================================

    try:

        webhook_info = (
            await application.bot.get_webhook_info()
        )


        logger.info(

            "Webhook info: url=%s pending=%s",

            webhook_info.url,

            webhook_info.pending_update_count,
        )


    except Exception:

        logger.exception(
            "Could not get webhook information."
        )


    # =====================================================
    # CREATE WEB APPLICATION
    # =====================================================

    web_app = await create_web_app(
        application
    )


    # =====================================================
    # START HTTP SERVER
    # =====================================================

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

    print(
        "========================================"
    )

    print(
        "       VoiceGen BD Bot is RUNNING"
    )

    print(
        "========================================"
    )

    print(
        f"Health : {WEBHOOK_URL}/"
    )

    print(
        f"Webhook: {FULL_WEBHOOK_URL}"
    )

    print(
        "Word Pause: OFF"
    )

    print(
        f"Voice Speed: {VOICE_RATE}"
    )

    print(
        "========================================"
    )

    print()


    # =====================================================
    # KEEP SERVER RUNNING
    # =====================================================

    try:

        await asyncio.Event().wait()


    finally:

        logger.info(
            "Stopping VoiceGen BD Bot..."
        )


        try:

            await application.bot.delete_webhook(
                drop_pending_updates=False,
            )

        except Exception:

            logger.exception(
                "Could not delete webhook."
            )


        try:

            await application.stop()

        except Exception:

            logger.exception(
                "Could not stop Telegram application."
            )


        try:

            await application.shutdown()

        except Exception:

            logger.exception(
                "Could not shutdown Telegram application."
            )


        try:

            await runner.cleanup()

        except Exception:

            logger.exception(
                "Could not cleanup web server."
            )


# =========================================================
# START PROGRAM
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
