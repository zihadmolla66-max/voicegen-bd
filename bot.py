import os
import asyncio
import tempfile
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

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


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

PORT = int(os.getenv("PORT", "10000"))

# TTS / FFmpeg timeout
TTS_TIMEOUT = int(os.getenv("TTS_TIMEOUT", "120"))
FFMPEG_TIMEOUT = int(os.getenv("FFMPEG_TIMEOUT", "120"))

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing."
    )


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_LANGUAGE = "bn"
DEFAULT_VOICE_TYPE = "male"

# Word-by-word pause permanently OFF
WORD_PAUSE = False

DEFAULT_SPEED = -30


# ============================================================
# LANGUAGES
# ============================================================

LANGUAGES = {
    "bn": "🇧🇩 বাংলা",
    "en": "🇺🇸 English",
}


# ============================================================
# VOICES
# ============================================================

VOICES = {

    "bn": {

        "male": {
            "name": "👨 Male",
            "voice": "bn-BD-PradeepNeural",
            "pitch": "+0Hz",
            "rate_adjust": 0,
        },

        "female": {
            "name": "👩 Female",
            "voice": "bn-BD-NabanitaNeural",
            "pitch": "+0Hz",
            "rate_adjust": 0,
        },

        "kid_male": {
            "name": "👦 Kids Male",
            "voice": "bn-BD-PradeepNeural",
            "pitch": "+35Hz",
            "rate_adjust": 10,
        },

        "kid_female": {
            "name": "👧 Kids Female",
            "voice": "bn-BD-NabanitaNeural",
            "pitch": "+35Hz",
            "rate_adjust": 10,
        },
    },

    "en": {

        "male": {
            "name": "👨 Male",
            "voice": "en-US-GuyNeural",
            "pitch": "+0Hz",
            "rate_adjust": 0,
        },

        "female": {
            "name": "👩 Female",
            "voice": "en-US-JennyNeural",
            "pitch": "+0Hz",
            "rate_adjust": 0,
        },

        "kid_male": {
            "name": "👦 Kids Male",
            "voice": "en-US-GuyNeural",
            "pitch": "+35Hz",
            "rate_adjust": 10,
        },

        "kid_female": {
            "name": "👧 Kids Female",
            "voice": "en-US-JennyNeural",
            "pitch": "+35Hz",
            "rate_adjust": 10,
        },
    },
}


# ============================================================
# USER SETTINGS
# ============================================================

user_settings = {}


def get_user_settings(user_id: int):

    if user_id not in user_settings:

        user_settings[user_id] = {
            "language": DEFAULT_LANGUAGE,
            "voice_type": DEFAULT_VOICE_TYPE,
            "speed": DEFAULT_SPEED,
        }

    return user_settings[user_id]


# ============================================================
# HELPERS
# ============================================================

def clamp_speed(speed: int) -> int:
    return max(-50, min(50, speed))


def make_rate(
    speed: int,
    extra_rate: int = 0,
) -> str:

    final_rate = clamp_speed(
        speed + extra_rate
    )

    return f"{final_rate:+d}%"


def get_voice_data(settings):

    language = settings["language"]
    voice_type = settings["voice_type"]

    return VOICES[language][voice_type]


def settings_text(settings):

    language_name = LANGUAGES[
        settings["language"]
    ]

    voice_name = VOICES[
        settings["language"]
    ][
        settings["voice_type"]
    ]["name"]

    return (
        "✅ Settings saved!\n\n"
        "আপনার Text পাঠান।\n\n"
        "⏸ Word-by-word pause: OFF\n"
        f"🐢 Speed: {settings['speed']:+d}%\n"
        f"🌐 Language: {language_name}\n"
        f"🎙 Voice: {voice_name}"
    )


def main_keyboard(settings):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🌐 Language",
                callback_data="language",
            ),

            InlineKeyboardButton(
                "🎙 Voice",
                callback_data="voice",
            ),
        ],

        [
            InlineKeyboardButton(
                "⚡ Speed",
                callback_data="speed",
            ),
        ],

        [
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="help",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔄 Start",
                callback_data="start",
            ),
        ],
    ])


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    settings = get_user_settings(
        user_id
    )

    text = (
        "🎙 *VoiceGen BD*\n\n"
        "আপনার Text পাঠান। "
        "আমি সেটাকে Voice-এ convert করব।\n\n"
        "🎵 MP3 Download\n"
        "🎬 MP4 Download\n"
        "⏸ Word-by-word pause: OFF\n"
        "👨 Male / 👩 Female\n"
        "👦 Kids Male / 👧 Kids Female"
    )

    if update.message:

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(settings),
        )

    elif update.callback_query:

        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(settings),
        )


# ============================================================
# LANGUAGE MENU
# ============================================================

async def language_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    keyboard = [

        [
            InlineKeyboardButton(
                "🇧🇩 বাংলা",
                callback_data="lang_bn",
            ),

            InlineKeyboardButton(
                "🇺🇸 English",
                callback_data="lang_en",
            ),
        ],

        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back",
            )
        ],
    ]

    await query.edit_message_text(
        "🌐 Select Language:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# VOICE MENU
# ============================================================

async def voice_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    keyboard = [

        [
            InlineKeyboardButton(
                "👨 Male",
                callback_data="voice_male",
            ),

            InlineKeyboardButton(
                "👩 Female",
                callback_data="voice_female",
            ),
        ],

        [
            InlineKeyboardButton(
                "👦 Kids Male",
                callback_data="voice_kid_male",
            ),

            InlineKeyboardButton(
                "👧 Kids Female",
                callback_data="voice_kid_female",
            ),
        ],

        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back",
            )
        ],
    ]

    await query.edit_message_text(
        "🎙 Select Voice:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# SPEED MENU
# ============================================================

async def speed_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    keyboard = [

        [
            InlineKeyboardButton(
                "-50%",
                callback_data="speed_-50",
            ),

            InlineKeyboardButton(
                "-40%",
                callback_data="speed_-40",
            ),

            InlineKeyboardButton(
                "-30%",
                callback_data="speed_-30",
            ),
        ],

        [
            InlineKeyboardButton(
                "-20%",
                callback_data="speed_-20",
            ),

            InlineKeyboardButton(
                "0%",
                callback_data="speed_0",
            ),

            InlineKeyboardButton(
                "+20%",
                callback_data="speed_20",
            ),
        ],

        [
            InlineKeyboardButton(
                "+30%",
                callback_data="speed_30",
            ),

            InlineKeyboardButton(
                "+40%",
                callback_data="speed_40",
            ),

            InlineKeyboardButton(
                "+50%",
                callback_data="speed_50",
            ),
        ],

        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back",
            )
        ],
    ]

    await query.edit_message_text(
        "⚡ Select speaking speed:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# HELP
# ============================================================

async def help_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    text = (
        "ℹ️ *VoiceGen BD Help*\n\n"

        "1️⃣ Language থেকে বাংলা/English নির্বাচন করুন।\n\n"

        "2️⃣ Voice থেকে Male/Female/Kids voice নির্বাচন করুন।\n\n"

        "3️⃣ Speed থেকে speaking speed নির্বাচন করুন।\n\n"

        "4️⃣ তারপর আপনার Text পাঠান।\n\n"

        "🎵 MP3 তৈরি হবে।\n"
        "🎬 MP4 তৈরি হবে।\n\n"

        "⏸ Word-by-word pause সম্পূর্ণ OFF।\n"
        "Text একসাথে TTS engine-এ পাঠানো হয়।"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data="back",
                )
            ]
        ]),
    )


# ============================================================
# GENERATE MP3
# ============================================================

async def generate_mp3(
    text: str,
    output_file: str,
    voice: str,
    rate: str,
    pitch: str,
):

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume="+0%",
        pitch=pitch,
    )

    try:

        await asyncio.wait_for(
            communicate.save(output_file),
            timeout=TTS_TIMEOUT,
        )

    except asyncio.TimeoutError:

        raise RuntimeError(
            "TTS timeout. "
            "Text একটু ছোট করে আবার চেষ্টা করুন."
        )

    if not os.path.exists(output_file):

        raise RuntimeError(
            "TTS MP3 file তৈরি হয়নি."
        )

    if os.path.getsize(output_file) <= 0:

        raise RuntimeError(
            "TTS MP3 file empty."
        )


# ============================================================
# RUN FFMPEG
# ============================================================

def run_ffmpeg(
    command,
    timeout=FFMPEG_TIMEOUT,
):

    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

    except subprocess.TimeoutExpired:

        raise RuntimeError(
            "FFmpeg timeout. "
            "অনুগ্রহ করে আবার চেষ্টা করুন."
        )

    if result.returncode != 0:

        error = result.stderr.strip()

        if len(error) > 4000:
            error = error[-4000:]

        raise RuntimeError(
            "FFmpeg error:\n\n"
            + error
        )

    return result


# ============================================================
# GET MEDIA DURATION
# ============================================================

def get_media_duration(
    media_file: str,
) -> float:

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    command = [

        ffmpeg,

        "-hide_banner",

        "-i",
        media_file,

        "-f",
        "null",

        "-",
    ]

    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

    except subprocess.TimeoutExpired:

        raise RuntimeError(
            "Media duration detection timeout."
        )

    # FFmpeg normally prints Duration to stderr
    output = result.stderr

    # Example:
    # Duration: 00:00:02.450000
    import re

    match = re.search(
        r"Duration:\s*"
        r"(\d+):(\d+):"
        r"(\d+(?:\.\d+)?)",
        output,
    )

    if not match:

        raise RuntimeError(
            "Media duration detect করা যায়নি."
        )

    hours = int(
        match.group(1)
    )

    minutes = int(
        match.group(2)
    )

    seconds = float(
        match.group(3)
    )

    duration = (
        hours * 3600
        + minutes * 60
        + seconds
    )

    if duration <= 0:

        raise RuntimeError(
            "Invalid media duration."
        )

    return duration


# ============================================================
# CREATE MP4
# ============================================================

def generate_mp4(
    mp3_file: str,
    mp4_file: str,
):

    """
    MP3 audio-এর duration অনুসরণ করে MP4 তৈরি করে।

    গুরুত্বপূর্ণ:
    আগের code-এর fixed frame_count logic ব্যবহার করা হয়নি।
    FFmpeg audio শেষ হলেই video শেষ করবে।
    """

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    duration = get_media_duration(
        mp3_file
    )

    print(
        f"[MP4] Audio duration: "
        f"{duration:.3f}s"
    )

    # --------------------------------------------------------
    # Slight safety margin
    #
    # AAC encoding-এর কারণে tiny padding হতে পারে।
    # তাই audio duration-এর চেয়ে সামান্য কম video limit
    # ব্যবহার করা হচ্ছে না; বরং shortest + exact output limit
    # ব্যবহার করা হচ্ছে।
    # --------------------------------------------------------

    output_duration = max(
        0.1,
        duration,
    )

    command = [

        ffmpeg,

        "-y",

        "-hide_banner",

        "-loglevel",
        "error",

        # ----------------------------------------------------
        # Black video source
        # ----------------------------------------------------

        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=720x720:r=25",

        # ----------------------------------------------------
        # Audio
        # ----------------------------------------------------

        "-i",
        mp3_file,

        # ----------------------------------------------------
        # Stream mapping
        # ----------------------------------------------------

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        # ----------------------------------------------------
        # Output duration
        # ----------------------------------------------------

        "-t",
        f"{output_duration:.3f}",

        "-shortest",

        # ----------------------------------------------------
        # Video
        # ----------------------------------------------------

        "-c:v",
        "libx264",

        "-preset",
        "ultrafast",

        "-tune",
        "stillimage",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "25",

        # ----------------------------------------------------
        # Audio
        # ----------------------------------------------------

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # ----------------------------------------------------
        # MP4
        # ----------------------------------------------------

        "-movflags",
        "+faststart",

        "-avoid_negative_ts",
        "make_zero",

        mp4_file,
    ]

    print("[MP4] Starting FFmpeg...")

    run_ffmpeg(
        command,
        timeout=FFMPEG_TIMEOUT,
    )

    if not os.path.exists(mp4_file):

        raise RuntimeError(
            "MP4 file তৈরি হয়নি."
        )

    if os.path.getsize(mp4_file) <= 0:

        raise RuntimeError(
            "MP4 file empty."
        )

    print(
        "[MP4] Created:",
        os.path.getsize(mp4_file),
        "bytes",
    )

    # --------------------------------------------------------
    # Verify duration
    # --------------------------------------------------------

    try:

        final_duration = get_media_duration(
            mp4_file
        )

        print(
            f"[MP4] Final duration: "
            f"{final_duration:.3f}s"
        )

    except Exception as e:

        print(
            "[MP4] Duration verification warning:",
            repr(e),
        )


# ============================================================
# TEXT HANDLER
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    text = update.message.text.strip()

    if not text:

        await update.message.reply_text(
            "❌ Please send some text."
        )

        return

    # Avoid extremely large requests
    if len(text) > 5000:

        await update.message.reply_text(
            "❌ Text অনেক বড়।\n\n"
            "একবারে সর্বোচ্চ 5000 characters পাঠান."
        )

        return

    user_id = update.effective_user.id

    settings = get_user_settings(
        user_id
    )

    voice_data = get_voice_data(
        settings
    )

    voice = voice_data["voice"]

    pitch = voice_data["pitch"]

    speed = settings["speed"]

    extra_rate = voice_data["rate_adjust"]

    rate = make_rate(
        speed,
        extra_rate,
    )

    status = await update.message.reply_text(
        "⏳ Voice তৈরি হচ্ছে...\n\n"
        "⏸ Word-by-word pause: OFF"
    )

    temp_dir = tempfile.mkdtemp(
        prefix="voicegen_"
    )

    mp3_file = os.path.join(
        temp_dir,
        "voice.mp3",
    )

    mp4_file = os.path.join(
        temp_dir,
        "voice.mp4",
    )

    try:

        # ====================================================
        # GENERATE MP3
        # ====================================================

        await generate_mp3(
            text=text,
            output_file=mp3_file,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

        # ====================================================
        # MP3 -> MP4
        # ====================================================

        await status.edit_text(
            "🎬 MP4 তৈরি হচ্ছে...\n\n"
            "⏸ Word-by-word pause: OFF"
        )

        await asyncio.to_thread(
            generate_mp4,
            mp3_file,
            mp4_file,
        )

        # ====================================================
        # SEND MP3
        # ====================================================

        await status.edit_text(
            "📤 MP3 পাঠানো হচ্ছে..."
        )

        language_name = LANGUAGES[
            settings["language"]
        ]

        voice_name = voice_data["name"]

        caption = (
            "🎙 VoiceGen BD\n\n"
            f"🌐 Language: {language_name}\n"
            f"🎙 Voice: {voice_name}\n"
            "⏸ Word pause: OFF\n"
            f"🐢 Speed: {settings['speed']:+d}%"
        )

        with open(
            mp3_file,
            "rb",
        ) as audio:

            await update.message.reply_audio(
                audio=audio,
                title="VoiceGen BD",
                performer="VoiceGen BD",
                caption=caption,
                read_timeout=120,
                write_timeout=120,
                connect_timeout=30,
                pool_timeout=30,
            )

        # ====================================================
        # SEND MP4
        # ====================================================

        await status.edit_text(
            "📤 MP4 পাঠানো হচ্ছে..."
        )

        with open(
            mp4_file,
            "rb",
        ) as video:

            await update.message.reply_video(
                video=video,
                caption=(
                    "🎬 VoiceGen BD MP4\n\n"
                    f"🌐 Language: {language_name}\n"
                    f"🎙 Voice: {voice_name}\n"
                    "⏸ Word pause: OFF\n"
                    f"🐢 Speed: {settings['speed']:+d}%"
                ),
                supports_streaming=True,
                read_timeout=180,
                write_timeout=180,
                connect_timeout=30,
                pool_timeout=30,
            )

        # ====================================================
        # DELETE STATUS
        # ====================================================

        try:

            await status.delete()

        except Exception:
            pass

        # ====================================================
        # SETTINGS
        # ====================================================

        await update.message.reply_text(
            settings_text(settings),
            reply_markup=main_keyboard(
                settings
            ),
        )

    except Exception as e:

        print(
            "================================"
        )

        print(
            "TTS / MP4 ERROR:"
        )

        print(
            repr(e)
        )

        print(
            "================================"
        )

        try:

            error_text = str(e)

            if len(error_text) > 1000:
                error_text = error_text[:1000]

            await status.edit_text(
                "❌ Voice তৈরি করতে সমস্যা হয়েছে।\n\n"
                "কিছুক্ষণ পরে আবার চেষ্টা করুন.\n\n"
                f"Error: {error_text}"
            )

        except Exception:
            pass

    finally:

        # ====================================================
        # CLEAN TEMP DIRECTORY
        # ====================================================

        try:

            temp_path = Path(
                temp_dir
            )

            if temp_path.exists():

                for file in temp_path.iterdir():

                    try:
                        file.unlink()
                    except Exception:
                        pass

                try:
                    temp_path.rmdir()
                except Exception:
                    pass

        except Exception:
            pass


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    settings = get_user_settings(
        user_id
    )

    data = query.data

    # ========================================================
    # START
    # ========================================================

    if data == "start":

        await start(
            update,
            context,
        )

        return

    # ========================================================
    # LANGUAGE
    # ========================================================

    if data == "language":

        await language_menu(
            update,
            context,
        )

        return

    # ========================================================
    # BANGLA
    # ========================================================

    if data == "lang_bn":

        settings["language"] = "bn"

        if settings["voice_type"] not in VOICES["bn"]:

            settings["voice_type"] = "male"

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(
                settings
            ),
        )

        return

    # ========================================================
    # ENGLISH
    # ========================================================

    if data == "lang_en":

        settings["language"] = "en"

        if settings["voice_type"] not in VOICES["en"]:

            settings["voice_type"] = "male"

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(
                settings
            ),
        )

        return

    # ========================================================
    # VOICE MENU
    # ========================================================

    if data == "voice":

        await voice_menu(
            update,
            context,
        )

        return

    # ========================================================
    # VOICE SELECT
    # ========================================================

    if data.startswith("voice_"):

        voice_type = data.replace(
            "voice_",
            "",
            1,
        )

        if voice_type in VOICES[
            settings["language"]
        ]:

            settings["voice_type"] = voice_type

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(
                settings
            ),
        )

        return

    # ========================================================
    # SPEED MENU
    # ========================================================

    if data == "speed":

        await speed_menu(
            update,
            context,
        )

        return

    # ========================================================
    # SPEED SELECT
    # ========================================================

    if data.startswith("speed_"):

        try:

            speed = int(
                data.replace(
                    "speed_",
                    "",
                    1,
                )
            )

            settings["speed"] = clamp_speed(
                speed
            )

        except ValueError:
            pass

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(
                settings
            ),
        )

        return

    # ========================================================
    # HELP
    # ========================================================

    if data == "help":

        await help_menu(
            update,
            context,
        )

        return

    # ========================================================
    # BACK
    # ========================================================

    if data == "back":

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(
                settings
            ),
        )

        return


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    print(
        "BOT ERROR:",
        repr(context.error)
    )


# ============================================================
# CREATE APPLICATION
# ============================================================

def create_application():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(180)
        .write_timeout(180)
        .pool_timeout(30)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    application.add_error_handler(
        error_handler
    )

    return application


# ============================================================
# MAIN
# ============================================================

def main():

    application = create_application()

    # ========================================================
    # WEBHOOK MODE
    # ========================================================

    if WEBHOOK_URL:

        webhook_url = WEBHOOK_URL.rstrip("/")

        if not webhook_url.endswith("/telegram"):

            webhook_url += "/telegram"

        print(
            "================================"
        )

        print(
            "VoiceGen BD"
        )

        print(
            "Starting webhook mode..."
        )

        print(
            "Webhook URL:",
            webhook_url
        )

        print(
            "Port:",
            PORT
        )

        print(
            "================================"
        )

        webhook_kwargs = {

            "listen": "0.0.0.0",

            "port": PORT,

            "url_path": "telegram",

            "webhook_url": webhook_url,
        }

        if WEBHOOK_SECRET:

            webhook_kwargs[
                "secret_token"
            ] = WEBHOOK_SECRET

        application.run_webhook(
            **webhook_kwargs
        )

    # ========================================================
    # POLLING MODE
    # ========================================================

    else:

        print(
            "================================"
        )

        print(
            "WEBHOOK_URL not found."
        )

        print(
            "Starting polling mode..."
        )

        print(
            "================================"
        )

        application.run_polling(
            drop_pending_updates=True
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
