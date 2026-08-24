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

BOT_TOKEN = os.getenv("BOT_TOKEN")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_LANGUAGE = "bn"
DEFAULT_VOICE_TYPE = "male"

# Word-by-word pause is permanently OFF.
WORD_PAUSE = False

# Default speed shown in your bot.
DEFAULT_SPEED = -30


# ============================================================
# LANGUAGE / VOICE SETTINGS
# ============================================================

LANGUAGES = {
    "bn": "🇧🇩 বাংলা",
    "en": "🇺🇸 English",
}

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


def make_rate(speed: int, extra_rate: int = 0) -> str:
    final_rate = clamp_speed(speed + extra_rate)
    return f"{final_rate:+d}%"


def get_voice_data(settings):
    language = settings["language"]
    voice_type = settings["voice_type"]

    return VOICES[language][voice_type]


def settings_text(settings):
    language_name = LANGUAGES.get(
        settings["language"],
        settings["language"]
    )

    voice_name = VOICES[
        settings["language"]
    ][
        settings["voice_type"]
    ]["name"]

    speed = settings["speed"]

    return (
        "✅ Voice selected successfully!\n\n"
        "প্রথমে আপনার Text পাঠান।\n\n"
        "⏸ Word-by-word pause: OFF\n"
        f"🐢 Speed: {speed:+d}%\n"
        f"🌐 Language: {language_name}\n"
        f"🎙 Voice: {voice_name}"
    )


def main_keyboard(settings):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🌐 Language",
                callback_data="language"
            ),
            InlineKeyboardButton(
                "🎙 Voice",
                callback_data="voice"
            ),
        ],
        [
            InlineKeyboardButton(
                "⚡ Speed",
                callback_data="speed"
            ),
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="help"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Start",
                callback_data="start"
            ),
        ],
    ])


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)

    text = (
        "🎙 *VoiceGen BD*\n\n"
        "আপনার Text পাঠান। আমি সেটাকে Voice-এ convert করব।\n\n"
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
            reply_markup=main_keyboard(settings)
        )

    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(settings)
        )


# ============================================================
# LANGUAGE MENU
# ============================================================

async def language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "🇧🇩 বাংলা",
                callback_data="lang_bn"
            ),
            InlineKeyboardButton(
                "🇺🇸 English",
                callback_data="lang_en"
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back"
            )
        ],
    ]

    await query.edit_message_text(
        "🌐 Select Language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# VOICE MENU
# ============================================================

async def voice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "👨 Male",
                callback_data="voice_male"
            ),
            InlineKeyboardButton(
                "👩 Female",
                callback_data="voice_female"
            ),
        ],
        [
            InlineKeyboardButton(
                "👦 Kids Male",
                callback_data="voice_kid_male"
            ),
            InlineKeyboardButton(
                "👧 Kids Female",
                callback_data="voice_kid_female"
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back"
            )
        ],
    ]

    await query.edit_message_text(
        "🎙 Select Voice:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# SPEED MENU
# ============================================================

async def speed_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "-50%",
                callback_data="speed_-50"
            ),
            InlineKeyboardButton(
                "-40%",
                callback_data="speed_-40"
            ),
            InlineKeyboardButton(
                "-30%",
                callback_data="speed_-30"
            ),
        ],
        [
            InlineKeyboardButton(
                "-20%",
                callback_data="speed_-20"
            ),
            InlineKeyboardButton(
                "0%",
                callback_data="speed_0"
            ),
            InlineKeyboardButton(
                "+20%",
                callback_data="speed_20"
            ),
        ],
        [
            InlineKeyboardButton(
                "+30%",
                callback_data="speed_30"
            ),
            InlineKeyboardButton(
                "+40%",
                callback_data="speed_40"
            ),
            InlineKeyboardButton(
                "+50%",
                callback_data="speed_50"
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back"
            )
        ],
    ]

    await query.edit_message_text(
        "⚡ Select speaking speed:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# HELP
# ============================================================

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "ℹ️ *VoiceGen BD Help*\n\n"
        "1️⃣ Language থেকে বাংলা/English নির্বাচন করুন।\n\n"
        "2️⃣ Voice থেকে Male/Female/Kids voice নির্বাচন করুন।\n\n"
        "3️⃣ Speed থেকে speaking speed নির্বাচন করুন।\n\n"
        "4️⃣ তারপর আপনার Text পাঠান।\n\n"
        "🎵 Bot MP3 তৈরি করবে।\n"
        "🎬 Bot MP4-ও তৈরি করবে।\n\n"
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
                    callback_data="back"
                )
            ]
        ])
    )


# ============================================================
# TTS GENERATION
# ============================================================

async def generate_mp3(
    text: str,
    output_file: str,
    voice: str,
    rate: str,
    pitch: str,
):
    """
    Generate one continuous MP3.

    IMPORTANT:
    No word-by-word splitting is done here.
    Therefore word-by-word pause is OFF.
    """

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume="+0%",
        pitch=pitch,
    )

    await communicate.save(output_file)


# ============================================================
# MP4 GENERATION
# ============================================================

def generate_mp4(mp3_file: str, mp4_file: str):
    """
    Create a simple MP4 video containing the generated audio.

    No system FFmpeg installation is required.
    imageio-ffmpeg supplies the FFmpeg executable.
    """

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    command = [
        ffmpeg,

        "-y",

        # Black video background
        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=720x720:r=1",

        # MP3 audio
        "-i",
        mp3_file,

        # Video encoding
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-tune",
        "stillimage",

        "-pix_fmt",
        "yuv420p",

        # Audio encoding
        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # Stop when audio ends
        "-shortest",

        mp4_file,
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "FFmpeg MP4 conversion failed:\n"
            + result.stderr[-3000:]
        )


# ============================================================
# TEXT MESSAGE
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    text = update.message.text.strip()

    if not text:
        await update.message.reply_text(
            "❌ Please send some text."
        )
        return

    user_id = update.effective_user.id
    settings = get_user_settings(user_id)

    voice_data = get_voice_data(settings)

    voice = voice_data["voice"]
    pitch = voice_data["pitch"]

    speed = settings["speed"]
    extra_rate = voice_data["rate_adjust"]

    rate = make_rate(
        speed,
        extra_rate
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
        "voice.mp3"
    )

    mp4_file = os.path.join(
        temp_dir,
        "voice.mp4"
    )

    try:

        # ----------------------------------------------------
        # Generate MP3
        # ----------------------------------------------------

        await generate_mp3(
            text=text,
            output_file=mp3_file,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )

        # ----------------------------------------------------
        # Generate MP4
        # ----------------------------------------------------

        await status.edit_text(
            "🎬 MP4 তৈরি হচ্ছে...\n\n"
            "⏸ Word-by-word pause: OFF"
        )

        await asyncio.to_thread(
            generate_mp4,
            mp3_file,
            mp4_file,
        )

        # ----------------------------------------------------
        # Send MP3
        # ----------------------------------------------------

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

        with open(mp3_file, "rb") as audio:

            await update.message.reply_audio(
                audio=audio,
                title="VoiceGen BD",
                performer="VoiceGen BD",
                caption=caption,
            )

        # ----------------------------------------------------
        # Send MP4
        # ----------------------------------------------------

        await status.edit_text(
            "📤 MP4 পাঠানো হচ্ছে..."
        )

        with open(mp4_file, "rb") as video:

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
            )

        await status.delete()

        # ----------------------------------------------------
        # Show controls again
        # ----------------------------------------------------

        await update.message.reply_text(
            settings_text(settings),
            reply_markup=main_keyboard(settings)
        )

    except Exception as e:

        print(
            "TTS/MP4 ERROR:",
            repr(e)
        )

        try:
            await status.edit_text(
                "❌ Voice তৈরি করা যায়নি।\n\n"
                "কিছুক্ষণ পরে আবার চেষ্টা করুন।\n\n"
                f"Error: {str(e)[:500]}"
            )
        except Exception:
            pass

    finally:

        # ----------------------------------------------------
        # Cleanup temporary files
        # ----------------------------------------------------

        try:
            for file in Path(temp_dir).glob("*"):
                try:
                    file.unlink()
                except Exception:
                    pass

            try:
                Path(temp_dir).rmdir()
            except Exception:
                pass

        except Exception:
            pass


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    settings = get_user_settings(user_id)

    data = query.data

    # --------------------------------------------------------
    # Start
    # --------------------------------------------------------

    if data == "start":
        await start(update, context)
        return

    # --------------------------------------------------------
    # Language
    # --------------------------------------------------------

    if data == "language":
        await language_menu(update, context)
        return

    if data == "lang_bn":

        settings["language"] = "bn"

        # Keep current voice type if available
        if settings["voice_type"] not in VOICES["bn"]:
            settings["voice_type"] = "male"

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(settings)
        )

        return

    if data == "lang_en":

        settings["language"] = "en"

        if settings["voice_type"] not in VOICES["en"]:
            settings["voice_type"] = "male"

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(settings)
        )

        return

    # --------------------------------------------------------
    # Voice
    # --------------------------------------------------------

    if data == "voice":
        await voice_menu(update, context)
        return

    if data.startswith("voice_"):

        voice_type = data.replace(
            "voice_",
            "",
            1
        )

        if voice_type in VOICES[
            settings["language"]
        ]:

            settings["voice_type"] = voice_type

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(settings)
        )

        return

    # --------------------------------------------------------
    # Speed
    # --------------------------------------------------------

    if data == "speed":
        await speed_menu(update, context)
        return

    if data.startswith("speed_"):

        try:
            speed = int(
                data.replace(
                    "speed_",
                    "",
                    1
                )
            )

            settings["speed"] = clamp_speed(
                speed
            )

        except ValueError:
            pass

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(settings)
        )

        return

    # --------------------------------------------------------
    # Help
    # --------------------------------------------------------

    if data == "help":
        await help_menu(update, context)
        return

    # --------------------------------------------------------
    # Back
    # --------------------------------------------------------

    if data == "back":

        await query.edit_message_text(
            settings_text(settings),
            reply_markup=main_keyboard(settings)
        )

        return


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    print(
        "BOT ERROR:",
        repr(context.error)
    )


# ============================================================
# APPLICATION
# ============================================================

def create_application():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
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

    # --------------------------------------------------------
    # WEBHOOK MODE
    # --------------------------------------------------------

    if WEBHOOK_URL:

        webhook_url = WEBHOOK_URL.rstrip("/")

        if not webhook_url.endswith("/telegram"):
            webhook_url += "/telegram"

        print(
            "Starting VoiceGen BD webhook..."
        )

        print(
            "Webhook URL:",
            webhook_url
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

    # --------------------------------------------------------
    # FALLBACK POLLING
    # --------------------------------------------------------

    else:

        print(
            "WEBHOOK_URL not found."
        )

        print(
            "Starting polling mode..."
        )

        application.run_polling()


if __name__ == "__main__":
    main()
