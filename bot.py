import os
import asyncio
import logging
import tempfile
import re
import shutil
from pathlib import Path

import edge_tts
from dotenv import load_dotenv
from aiohttp import web
from pydub import AudioSegment

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

WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    ""
).strip()


# =========================================================
# VOICE SETTINGS
# =========================================================

# Overall voice speed
VOICE_RATE = "-30%"

# ---------------------------------------------------------
# Word Pause
# ---------------------------------------------------------

# প্রতিটি word-এর মাঝে pause
WORD_PAUSE_MS = 180

# Sentence শেষ হওয়ার পরে pause
SENTENCE_PAUSE_MS = 350


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

# Render restart/redeploy হলে settings reset হবে।
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

    # =====================================================
    # BANGLA
    # =====================================================

    "bn": {

        "male": [

            (
                "🇧🇩 বাংলা Male 1",
                "bn-BD-PradeepNeural",
            ),

            (
                "🇮🇳 বাংলা Male 2",
                "bn-IN-BashkarNeural",
            ),
        ],

        "female": [

            (
                "🇧🇩 বাংলা Female 1",
                "bn-BD-NabanitaNeural",
            ),

            (
                "🇮🇳 বাংলা Female 2",
                "bn-IN-TanishaaNeural",
            ),
        ],

        "young": [

            (
                "🧒 বাংলা Young/Cute 1",
                "bn-BD-NabanitaNeural",
            ),

            (
                "🧒 বাংলা Young/Cute 2",
                "bn-IN-TanishaaNeural",
            ),
        ],
    },


    # =====================================================
    # ENGLISH
    # =====================================================

    "en": {

        "male": [

            (
                "🇺🇸 English Male 1",
                "en-US-GuyNeural",
            ),

            (
                "🇺🇸 English Male 2",
                "en-US-AndrewNeural",
            ),
        ],

        "female": [

            (
                "🇺🇸 English Female 1",
                "en-US-JennyNeural",
            ),

            (
                "🇺🇸 English Female 2",
                "en-US-AriaNeural",
            ),
        ],

        "young": [

            (
                "🧒 English Young/Cute 1",
                "en-US-AnaNeural",
            ),

            (
                "🧒 English Young/Cute 2",
                "en-US-JennyNeural",
            ),
        ],
    },


    # =====================================================
    # HINDI
    # =====================================================

    "hi": {

        "male": [

            (
                "🇮🇳 Hindi Male 1",
                "hi-IN-MadhurNeural",
            ),

            (
                "🇮🇳 Hindi Male 2",
                "hi-IN-PrabhatNeural",
            ),
        ],

        "female": [

            (
                "🇮🇳 Hindi Female 1",
                "hi-IN-SwaraNeural",
            ),

            (
                "🇮🇳 Hindi Female 2",
                "hi-IN-AnanyaNeural",
            ),
        ],

        "young": [

            (
                "🧒 Hindi Young/Cute 1",
                "hi-IN-SwaraNeural",
            ),

            (
                "🧒 Hindi Young/Cute 2",
                "hi-IN-AnanyaNeural",
            ),
        ],
    },


    # =====================================================
    # URDU
    # =====================================================

    "ur": {

        "male": [

            (
                "🇵🇰 Urdu Male 1",
                "ur-PK-AsadNeural",
            ),

            (
                "🇮🇳 Urdu Male 2",
                "ur-IN-SalmanNeural",
            ),
        ],

        "female": [

            (
                "🇵🇰 Urdu Female 1",
                "ur-PK-UzmaNeural",
            ),

            (
                "🇮🇳 Urdu Female 2",
                "ur-IN-GulNeural",
            ),
        ],

        "young": [

            (
                "🧒 Urdu Young/Cute 1",
                "ur-PK-UzmaNeural",
            ),

            (
                "🧒 Urdu Young/Cute 2",
                "ur-IN-GulNeural",
            ),
        ],
    },


    # =====================================================
    # ARABIC
    # =====================================================

    "ar": {

        "male": [

            (
                "🇸🇦 Arabic Male 1",
                "ar-SA-HamedNeural",
            ),

            (
                "🇦🇪 Arabic Male 2",
                "ar-AE-HamdanNeural",
            ),
        ],

        "female": [

            (
                "🇸🇦 Arabic Female 1",
                "ar-SA-ZariyahNeural",
            ),

            (
                "🇪🇬 Arabic Female 2",
                "ar-EG-SalmaNeural",
            ),
        ],

        "young": [

            (
                "🧒 Arabic Young/Cute 1",
                "ar-EG-SalmaNeural",
            ),

            (
                "🧒 Arabic Young/Cute 2",
                "ar-SA-ZariyahNeural",
            ),
        ],
    },
}


# =========================================================
# VOICE VALIDATION
# =========================================================

def is_valid_voice(
    language: str,
    voice: str,
) -> bool:

    language_voices = VOICES.get(language)

    if not language_voices:
        return False

    for category in (
        "male",
        "female",
        "young",
    ):

        for _, voice_id in language_voices.get(
            category,
            [],
        ):

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

    return InlineKeyboardMarkup(
        keyboard
    )


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

    return InlineKeyboardMarkup(
        keyboard
    )


# =========================================================
# VOICE KEYBOARD
# =========================================================

def voice_keyboard(
    language: str,
):

    voices = VOICES.get(
        language,
        VOICES["bn"],
    )

    keyboard = []

    # -----------------------------------------------------
    # Male
    # -----------------------------------------------------

    keyboard.append([

        InlineKeyboardButton(
            "👨 Male Voices",
            callback_data="voice_title_male",
        )

    ])

    for name, voice_id in voices.get(
        "male",
        [],
    ):

        keyboard.append([

            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_id}",
            )

        ])

    # -----------------------------------------------------
    # Female
    # -----------------------------------------------------

    keyboard.append([

        InlineKeyboardButton(
            "👩 Female Voices",
            callback_data="voice_title_female",
        )

    ])

    for name, voice_id in voices.get(
        "female",
        [],
    ):

        keyboard.append([

            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_id}",
            )

        ])

    # -----------------------------------------------------
    # Young / Cute
    # -----------------------------------------------------

    keyboard.append([

        InlineKeyboardButton(
            "🧒 Young / Cute Voices",
            callback_data="voice_title_young",
        )

    ])

    for name, voice_id in voices.get(
        "young",
        [],
    ):

        keyboard.append([

            InlineKeyboardButton(
                name,
                callback_data=f"voice_select|{voice_id}",
            )

        ])

    # -----------------------------------------------------
    # Back
    # -----------------------------------------------------

    keyboard.append([

        InlineKeyboardButton(
            "🔙 Back",
            callback_data="menu_start",
        )

    ])

    return InlineKeyboardMarkup(
        keyboard
    )


# =========================================================
# TEXT PROCESSING
# =========================================================

def split_text_into_words(
    text: str,
):

    """
    Text-কে word অনুযায়ী ভাগ করে।

    Example:

    আমি ভালো আছি।

    Result:

    আমি
    ভালো
    আছি।
    """

    parts = re.findall(
        r"\S+",
        text,
        flags=re.UNICODE,
    )

    return parts


def has_sentence_end(
    word: str,
):

    return bool(
        re.search(
            r"[.!?।！？]+$",
            word,
            flags=re.UNICODE,
        )
    )


# =========================================================
# CREATE WORD PAUSE AUDIO
# =========================================================

async def create_word_pause_audio(
    text: str,
    voice: str,
    output_file: str,
):

    """
    প্রতিটি word আলাদা করে Edge TTS-এ convert করে।

    তারপর:

    Word 1
    ↓
    Pause
    ↓
    Word 2
    ↓
    Pause
    ↓
    Word 3

    এভাবে final MP3 তৈরি করে।
    """

    words = split_text_into_words(
        text
    )

    if not words:

        raise RuntimeError(
            "Text-এ কোনো word পাওয়া যায়নি।"
        )

    combined_audio = AudioSegment.empty()

    temp_files = []

    try:

        for index, word in enumerate(
            words
        ):

            # -------------------------------------------------
            # Temporary word MP3
            # -------------------------------------------------

            word_file = tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
            )

            word_path = word_file.name

            word_file.close()

            temp_files.append(
                word_path
            )

            logger.info(
                "Generating word %s/%s: %s",
                index + 1,
                len(words),
                word,
            )

            # -------------------------------------------------
            # Edge TTS
            # -------------------------------------------------

            communicate = edge_tts.Communicate(
                text=word,
                voice=voice,
                rate=VOICE_RATE,
            )

            await communicate.save(
                word_path
            )

            # -------------------------------------------------
            # Check word file
            # -------------------------------------------------

            word_file_path = Path(
                word_path
            )

            if not word_file_path.exists():

                raise RuntimeError(
                    f"Word audio তৈরি হয়নি: {word}"
                )

            if word_file_path.stat().st_size <= 0:

                raise RuntimeError(
                    f"Word audio empty হয়েছে: {word}"
                )

            # -------------------------------------------------
            # Load MP3
            # -------------------------------------------------

            word_audio = AudioSegment.from_file(
                word_path,
                format="mp3",
            )

            # -------------------------------------------------
            # Add word audio
            # -------------------------------------------------

            combined_audio += word_audio

            # -------------------------------------------------
            # Add pause
            # -------------------------------------------------

            if index < len(words) - 1:

                if has_sentence_end(
                    word
                ):

                    pause = AudioSegment.silent(
                        duration=SENTENCE_PAUSE_MS
                    )

                else:

                    pause = AudioSegment.silent(
                        duration=WORD_PAUSE_MS
                    )

                combined_audio += pause

        # -----------------------------------------------------
        # Export final MP3
        # -----------------------------------------------------

        combined_audio.export(
            output_file,
            format="mp3",
            bitrate="128k",
        )

        logger.info(
            "Final word-pause MP3 exported."
        )

    finally:

        # -----------------------------------------------------
        # Delete individual word MP3 files
        # -----------------------------------------------------

        for temp_file in temp_files:

            try:

                path = Path(
                    temp_file
                )

                if path.exists():

                    path.unlink()

            except Exception:

                logger.exception(
                    "Could not delete temporary word file."
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

            "🌐 Language নির্বাচন করুন।\n"
            "🎤 Male / Female Voice নির্বাচন করুন।\n"
            "🧒 Young / Cute Voice-ও available।\n\n"

            "তারপর আপনার Text পাঠান।\n\n"

            "👨 2 Male Voice\n"
            "👩 2 Female Voice\n"
            "🧒 2 Young/Cute Voice\n"
            "⏸️ Word-এর মাঝে Pause\n\n"

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
        "🧒 2 Young/Cute",

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
        "🧒 2 Young/Cute Voice\n\n"

        "⏸️ প্রতিটি word-এর মাঝে pause\n"
        f"⏱️ Word pause: {WORD_PAUSE_MS}ms\n"
        f"⏱️ Sentence pause: {SENTENCE_PAUSE_MS}ms\n\n"

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

    # -----------------------------------------------------
    # Character limit
    # -----------------------------------------------------

    if len(text) > 3000:

        await update.message.reply_text(

            "❌ Text অনেক বড়।\n\n"
            "সর্বোচ্চ <b>3000 characters</b> পাঠান।",

            parse_mode="HTML",

            reply_markup=main_menu_keyboard(),

        )

        return

    # -----------------------------------------------------
    # Settings
    # -----------------------------------------------------

    settings = get_settings(
        user.id
    )

    language = settings[
        "language"
    ]

    voice = settings[
        "voice"
    ]

    # -----------------------------------------------------
    # Validate voice
    # -----------------------------------------------------

    if not is_valid_voice(
        language,
        voice,
    ):

        voice = VOICES[
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
            voice,
        )

    # -----------------------------------------------------
    # Processing message
    # -----------------------------------------------------

    processing_message = await update.message.reply_text(

        "⏳ <b>Voice তৈরি হচ্ছে...</b>\n\n"

        "🎤 Voice প্রস্তুত করা হচ্ছে...\n"
        "⏸️ Word-এর মাঝে pause যোগ করা হচ্ছে...\n"
        "🐢 Speed: -30%",

        parse_mode="HTML",

    )

    output_file = None

    try:

        logger.info(
            "Creating word-pause TTS: "
            "user=%s language=%s voice=%s",
            user.id,
            language,
            voice,
        )

        # -------------------------------------------------
        # Temporary final MP3
        # -------------------------------------------------

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False,
        )

        output_file = temp_file.name

        temp_file.close()

        # -------------------------------------------------
        # Create final audio
        # -------------------------------------------------

        await create_word_pause_audio(

            text=text,

            voice=voice,

            output_file=output_file,

        )

        # -------------------------------------------------
        # Check final file
        # -------------------------------------------------

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

        logger.info(
            "Final MP3 created successfully: %s",
            output_file,
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
            "rb",
        ) as audio_file:

            await update.message.reply_audio(

                audio=audio_file,

                title="VoiceGen BD",

                performer="VoiceGen BD",

                caption=(

                    "🎙️ <b>VoiceGen BD</b>\n"

                    "🐢 Speed: -30%\n"

                    f"⏸️ Word pause: {WORD_PAUSE_MS}ms\n"

                    f"⏸️ Sentence pause: {SENTENCE_PAUSE_MS}ms"

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

        # -------------------------------------------------
        # Delete final temporary MP3
        # -------------------------------------------------

        if output_file:

            try:

                path = Path(
                    output_file
                )

                if path.exists():

                    path.unlink()

                    logger.info(
                        "Temporary final MP3 deleted: %s",
                        output_file,
                    )

            except Exception:

                logger.exception(
                    "Could not delete final temporary MP3"
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
            "🧒 2 Young/Cute",

            parse_mode="HTML",

            reply_markup=voice_keyboard(
                language
            ),

        )

        return

    # =====================================================
    # HELP
    # =====================================================

    if data == "menu_help":

        await query.edit_message_text(

            "ℹ️ <b>VoiceGen BD Help</b>\n\n"

            "1️⃣ Language নির্বাচন করুন\n"
            "2️⃣ Male/Female/Young Voice নির্বাচন করুন\n"
            "3️⃣ Text পাঠান\n"
            "4️⃣ Bot MP3 তৈরি করবে\n\n"

            "👨 2 Male Voice\n"
            "👩 2 Female Voice\n"
            "🧒 2 Young/Cute Voice\n"

            "⏸️ Word-এর মাঝে pause\n"
            f"⏱️ Word pause: {WORD_PAUSE_MS}ms\n"
            f"⏱️ Sentence pause: {SENTENCE_PAUSE_MS}ms\n\n"

            "🐢 Speed: -30%\n"
            "🎵 Output: MP3",

            parse_mode="HTML",

            reply_markup=main_menu_keyboard(),

        )

        return

    # =====================================================
    # LANGUAGE SELECTION
    # =====================================================

    if data.startswith(
        "lang_"
    ):

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

        logger.info(
            "Language %s selected by user %s",
            language,
            user_id,
        )

        return

    # =====================================================
    # VOICE SELECT
    # =====================================================

    if data.startswith(
        "voice_select|"
    ):

        voice = data.split(
            "|",
            1,
        )[1]

        settings = get_settings(
            user_id
        )

        language = settings[
            "language"
        ]

        # -------------------------------------------------
        # Validate
        # -------------------------------------------------

        if not is_valid_voice(
            language,
            voice,
        ):

            await query.edit_message_text(

                "❌ এই Voice বর্তমানে available নয়।\n\n"

                "দয়া করে অন্য Voice নির্বাচন করুন।",

                parse_mode="HTML",

                reply_markup=voice_keyboard(
                    language
                ),

            )

            logger.warning(
                "Invalid voice selected: "
                "user=%s voice=%s",
                user_id,
                voice,
            )

            return

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        set_voice(
            user_id,
            voice,
        )

        await query.edit_message_text(

            "✅ <b>Voice selected successfully!</b>\n\n"

            "এখন আপনার Text পাঠান।\n\n"

            f"⏸️ Word pause: {WORD_PAUSE_MS}ms\n"
            f"⏸️ Sentence pause: {SENTENCE_PAUSE_MS}ms\n"
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
    # MALE CATEGORY
    # =====================================================

    if data == "voice_title_male":

        await query.answer(

            "👨 নিচে Male voices দেওয়া আছে।",

            show_alert=False,

        )

        return

    # =====================================================
    # FEMALE CATEGORY
    # =====================================================

    if data == "voice_title_female":

        await query.answer(

            "👩 নিচে Female voices দেওয়া আছে।",

            show_alert=False,

        )

        return

    # =====================================================
    # YOUNG CATEGORY
    # =====================================================

    if data == "voice_title_young":

        await query.answer(

            "🧒 নিচে Young/Cute voices দেওয়া আছে।",

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

async def health(
    request,
):

    return web.Response(

        text="VoiceGen BD Bot is running!",

        status=200,

    )


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

async def telegram_webhook(
    request,
):

    # -----------------------------------------------------
    # Secret verification
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Read JSON
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Convert to Update
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Queue update
    # -----------------------------------------------------

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

    print(
        "========================================"
    )

    print(
        "          VoiceGen BD Bot"
    )

    print(
        "========================================"
    )

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
        f"Word Pause  : {WORD_PAUSE_MS}ms"
    )

    print(
        f"Sentence Pause : {SENTENCE_PAUSE_MS}ms"
    )

    print(
        f"Voice Rate  : {VOICE_RATE}"
    )

    print(
        "========================================"
    )

    print()

    # =====================================================
    # Check FFmpeg
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

        logger.warning(
            "FFmpeg not found. "
            "Pydub MP3 processing may fail."
        )

    # =====================================================
    # Telegram Application
    # =====================================================

    application = (

        Application

        .builder()

        .token(
            BOT_TOKEN
        )

        .post_init(
            post_init
        )

        .build()

    )

    # =====================================================
    # Commands
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
    # Callback buttons
    # =====================================================

    application.add_handler(

        CallbackQueryHandler(
            callback_handler,
        )

    )

    # =====================================================
    # Text messages
    # =====================================================

    application.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_to_voice,

        )

    )

    # =====================================================
    # Error handler
    # =====================================================

    application.add_error_handler(
        error_handler
    )

    # =====================================================
    # Initialize
    # =====================================================

    await application.initialize()

    # =====================================================
    # Start Telegram application
    # =====================================================

    await application.start()

    # =====================================================
    # Delete old webhook
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
    # Set new webhook
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
    # Webhook information
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
    # Create web application
    # =====================================================

    web_app = await create_web_app(
        application
    )

    # =====================================================
    # Start HTTP server
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
        f"Pause  : {WORD_PAUSE_MS}ms"
    )

    print(
        f"Sentence Pause : {SENTENCE_PAUSE_MS}ms"
    )

    print(
        "========================================"
    )

    print()

    # =====================================================
    # Keep server running
    # =====================================================

    try:

        await asyncio.Event().wait()

    finally:

        logger.info(
            "Stopping VoiceGen BD Bot..."
        )

        # -------------------------------------------------
        # Delete webhook
        # -------------------------------------------------

        try:

            await application.bot.delete_webhook(

                drop_pending_updates=False,

            )

        except Exception:

            logger.exception(
                "Could not delete webhook."
            )

        # -------------------------------------------------
        # Stop Telegram application
        # -------------------------------------------------

        try:

            await application.stop()

        except Exception:

            logger.exception(
                "Could not stop Telegram application."
            )

        # -------------------------------------------------
        # Shutdown Telegram application
        # -------------------------------------------------

        try:

            await application.shutdown()

        except Exception:

            logger.exception(
                "Could not shutdown Telegram application."
            )

        # -------------------------------------------------
        # Cleanup HTTP server
        # -------------------------------------------------

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
