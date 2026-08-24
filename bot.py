import os
import asyncio
import logging
import tempfile
import subprocess
import json
from pathlib import Path

import aiohttp
from aiohttp import web
import edge_tts


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

PORT = int(os.getenv("PORT", "10000"))

RENDER_URL = os.getenv(
    "RENDER_URL",
    "https://voicegen-bd.onrender.com"
).rstrip("/")

WEBHOOK_PATH = "/telegram"
WEBHOOK_URL = RENDER_URL + WEBHOOK_PATH

WORD_PAUSE = False
SPEED_RATE = "-30%"

TEMP_DIR = Path(tempfile.gettempdir()) / "voicegen_bd"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - VoiceGenBD - %(levelname)s - %(message)s"
)

logger = logging.getLogger("VoiceGenBD")


# ============================================================
# TELEGRAM API
# ============================================================

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def telegram_api(method, data=None, files=None):

    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        if files:

            form = aiohttp.FormData()

            if data:
                for key, value in data.items():
                    form.add_field(key, str(value))

            opened_files = []

            try:

                for key, file_info in files.items():

                    filename, file_path, content_type = file_info

                    file_handle = open(file_path, "rb")
                    opened_files.append(file_handle)

                    form.add_field(
                        key,
                        file_handle,
                        filename=filename,
                        content_type=content_type
                    )

                async with session.post(
                    f"{TELEGRAM_API}/{method}",
                    data=form
                ) as response:

                    return await response.json()

            finally:

                for file_handle in opened_files:

                    try:
                        file_handle.close()
                    except Exception:
                        pass

        else:

            async with session.post(
                f"{TELEGRAM_API}/{method}",
                data=data or {}
            ) as response:

                return await response.json()


# ============================================================
# TELEGRAM SEND FUNCTIONS
# ============================================================

async def send_message(chat_id, text, reply_markup=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    return await telegram_api(
        "sendMessage",
        data=data
    )


async def answer_callback(callback_id, text=""):

    return await telegram_api(
        "answerCallbackQuery",
        data={
            "callback_query_id": callback_id,
            "text": text
        }
    )


async def send_audio(chat_id, file_path, caption=None):

    data = {
        "chat_id": chat_id
    }

    if caption:
        data["caption"] = caption

    files = {
        "audio": (
            Path(file_path).name,
            file_path,
            "audio/mpeg"
        )
    }

    return await telegram_api(
        "sendAudio",
        data=data,
        files=files
    )


async def send_video(chat_id, file_path, caption=None):

    data = {
        "chat_id": chat_id,
        "supports_streaming": "true"
    }

    if caption:
        data["caption"] = caption

    files = {
        "video": (
            Path(file_path).name,
            file_path,
            "video/mp4"
        )
    }

    return await telegram_api(
        "sendVideo",
        data=data,
        files=files
    )


# ============================================================
# USER SETTINGS
# ============================================================

USER_SETTINGS = {}


def get_user_settings(user_id):

    if user_id not in USER_SETTINGS:

        USER_SETTINGS[user_id] = {
            "language": "bn",
            "voice": "male",
            "speed": "-30%",
            "word_pause": False
        }

    return USER_SETTINGS[user_id]


# ============================================================
# VOICES
# ============================================================

VOICE_CONFIG = {

    # --------------------------------------------------------
    # BANGLA
    # --------------------------------------------------------

    "bn_male": {
        "name": "বাংলা Male",
        "voice": "bn-BD-PradeepNeural",
        "pitch": "+0Hz",
        "rate": "-30%"
    },

    "bn_female": {
        "name": "বাংলা Female",
        "voice": "bn-BD-NabanitaNeural",
        "pitch": "+0Hz",
        "rate": "-30%"
    },

    "bn_kid_male_1": {
        "name": "Kids Male 1",
        "voice": "bn-BD-PradeepNeural",
        "pitch": "+20Hz",
        "rate": "-30%"
    },

    "bn_kid_male_2": {
        "name": "Kids Male 2",
        "voice": "bn-BD-PradeepNeural",
        "pitch": "+35Hz",
        "rate": "-30%"
    },

    "bn_kid_female_1": {
        "name": "Kids Female 1",
        "voice": "bn-BD-NabanitaNeural",
        "pitch": "+20Hz",
        "rate": "-30%"
    },

    "bn_kid_female_2": {
        "name": "Kids Female 2",
        "voice": "bn-BD-NabanitaNeural",
        "pitch": "+35Hz",
        "rate": "-30%"
    },


    # --------------------------------------------------------
    # ENGLISH
    # --------------------------------------------------------

    "en_male": {
        "name": "English Male",
        "voice": "en-US-AndrewMultilingualNeural",
        "pitch": "+0Hz",
        "rate": "-30%"
    },

    "en_female": {
        "name": "English Female",
        "voice": "en-US-AvaMultilingualNeural",
        "pitch": "+0Hz",
        "rate": "-30%"
    },

    "en_kid_male_1": {
        "name": "Kids Male 1",
        "voice": "en-US-ChristopherNeural",
        "pitch": "+20Hz",
        "rate": "-30%"
    },

    "en_kid_male_2": {
        "name": "Kids Male 2",
        "voice": "en-US-ChristopherNeural",
        "pitch": "+35Hz",
        "rate": "-30%"
    },

    "en_kid_female_1": {
        "name": "Kids Female 1",
        "voice": "en-US-AnaNeural",
        "pitch": "+10Hz",
        "rate": "-30%"
    },

    "en_kid_female_2": {
        "name": "Kids Female 2",
        "voice": "en-US-AnaNeural",
        "pitch": "+25Hz",
        "rate": "-30%"
    }
}


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard():

    return {
        "keyboard": [
            [
                {
                    "text": "🌐 Language",
                    "callback_data": "language"
                },
                {
                    "text": "🎤 Voice",
                    "callback_data": "voice"
                }
            ],
            [
                {
                    "text": "ℹ️ Help",
                    "callback_data": "help"
                }
            ],
            [
                {
                    "text": "🔄 Start",
                    "callback_data": "start"
                }
            ]
        ],
        "resize_keyboard": True
    }


def language_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🇧🇩 বাংলা",
                    "callback_data": "lang_bn"
                },
                {
                    "text": "🇺🇸 English",
                    "callback_data": "lang_en"
                }
            ],
            [
                {
                    "text": "🔙 Back",
                    "callback_data": "back"
                }
            ]
        ]
    }


def bangla_voice_keyboard():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "👨 বাংলা Male",
                    "callback_data": "voice_bn_male"
                }
            ],

            [
                {
                    "text": "👩 বাংলা Female",
                    "callback_data": "voice_bn_female"
                }
            ],

            [
                {
                    "text": "👦 Kids Male 1",
                    "callback_data": "voice_bn_kid_male_1"
                },
                {
                    "text": "👦 Kids Male 2",
                    "callback_data": "voice_bn_kid_male_2"
                }
            ],

            [
                {
                    "text": "👧 Kids Female 1",
                    "callback_data": "voice_bn_kid_female_1"
                },
                {
                    "text": "👧 Kids Female 2",
                    "callback_data": "voice_bn_kid_female_2"
                }
            ],

            [
                {
                    "text": "🔙 Back",
                    "callback_data": "back"
                }
            ]
        ]
    }


def english_voice_keyboard():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "👨 English Male",
                    "callback_data": "voice_en_male"
                }
            ],

            [
                {
                    "text": "👩 English Female",
                    "callback_data": "voice_en_female"
                }
            ],

            [
                {
                    "text": "👦 Kids Male 1",
                    "callback_data": "voice_en_kid_male_1"
                },
                {
                    "text": "👦 Kids Male 2",
                    "callback_data": "voice_en_kid_male_2"
                }
            ],

            [
                {
                    "text": "👧 Kids Female 1",
                    "callback_data": "voice_en_kid_female_1"
                },
                {
                    "text": "👧 Kids Female 2",
                    "callback_data": "voice_en_kid_female_2"
                }
            ],

            [
                {
                    "text": "🔙 Back",
                    "callback_data": "back"
                }
            ]
        ]
    }


def download_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🎵 Download MP3",
                    "callback_data": "download_mp3"
                }
            ],
            [
                {
                    "text": "🎬 Download MP4",
                    "callback_data": "download_mp4"
                }
            ],
            [
                {
                    "text": "🔙 Back",
                    "callback_data": "back"
                }
            ]
        ]
    }


# ============================================================
# STATUS
# ============================================================

def status_text(user_id):

    settings = get_user_settings(user_id)

    language = settings["language"]

    if language == "bn":
        language_text = "🇧🇩 বাংলা"
    else:
        language_text = "🇺🇸 English"

    voice_key = settings["voice"]

    full_key = f"{language}_{voice_key}"

    voice_info = VOICE_CONFIG.get(
        full_key,
        VOICE_CONFIG["bn_male"]
    )

    return (
        f"🎙️ VoiceGen BD\n\n"
        f"🌐 Language: {language_text}\n"
        f"🎤 Voice: {voice_info['name']}\n"
        f"⏸️ Word-by-word pause: OFF\n"
        f"🐢 Speed: -30%\n\n"
        f"প্রধান আপনার Text পাঠান।"
    )


# ============================================================
# TEXT TO SPEECH
# ============================================================

async def generate_audio(text, user_id, output_path):

    settings = get_user_settings(user_id)

    language = settings["language"]
    voice_type = settings["voice"]

    voice_key = f"{language}_{voice_type}"

    if voice_key not in VOICE_CONFIG:

        voice_key = (
            "bn_male"
            if language == "bn"
            else "en_male"
        )

    config = VOICE_CONFIG[voice_key]

    communicate = edge_tts.Communicate(
        text=text,
        voice=config["voice"],
        rate=SPEED_RATE,
        pitch=config["pitch"]
    )

    await communicate.save(str(output_path))

    return output_path


# ============================================================
# GET MEDIA DURATION
# ============================================================

def get_media_duration(file_path):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        logger.error(
            "ffprobe error: %s",
            result.stderr
        )

        raise RuntimeError(
            "Could not determine media duration."
        )

    output = result.stdout.strip()

    if not output:
        raise RuntimeError("ffprobe returned empty duration.")

    return float(output)


# ============================================================
# GET STREAM DURATION
# ============================================================

def get_stream_duration(file_path, stream_type):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        stream_type,
        "-show_entries",
        "stream=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    value = result.stdout.strip()

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


# ============================================================
# CREATE MP4 - EXACT AUDIO LENGTH
# ============================================================

def create_mp4(audio_path, output_path):

    """
    Create black MP4 with duration matching the audio.

    Important:
    - No imageio-ffmpeg
    - Uses system ffmpeg
    - Uses system ffprobe
    - Video is generated from audio duration
    - Audio/video are cut at the exact target duration
    - Extra silent video is removed
    """

    audio_duration = get_media_duration(audio_path)

    logger.info(
        "Original audio duration: %.3f sec",
        audio_duration
    )

    # Keep precision but avoid tiny floating point issues.
    target_duration = max(0.10, audio_duration)

    duration_text = f"{target_duration:.3f}"

    # --------------------------------------------------------
    # First pass
    # --------------------------------------------------------

    command = [
        "ffmpeg",
        "-y",

        # Black video
        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=1280x720:r=25",

        # Original audio
        "-i",
        str(audio_path),

        # Exact target
        "-t",
        duration_text,

        # Video
        "-map",
        "0:v:0",

        # Audio
        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-tune",
        "stillimage",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "25",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # Make timestamps start at zero
        "-avoid_negative_ts",
        "make_zero",

        # Stop when shortest stream finishes
        "-shortest",

        # MP4 streaming
        "-movflags",
        "+faststart",

        str(output_path)
    ]

    logger.info(
        "Creating MP4..."
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        logger.error(
            "FFmpeg error:\n%s",
            result.stderr
        )

        raise RuntimeError(
            "FFmpeg could not create MP4."
        )

    # --------------------------------------------------------
    # Check generated MP4
    # --------------------------------------------------------

    mp4_duration = get_media_duration(output_path)

    logger.info(
        "First MP4 duration: %.3f sec",
        mp4_duration
    )

    # --------------------------------------------------------
    # If FFmpeg created extra duration, trim again.
    # --------------------------------------------------------

    tolerance = 0.08

    if mp4_duration > target_duration + tolerance:

        logger.warning(
            "MP4 is longer than audio. Trimming again..."
        )

        trimmed_path = output_path.with_name(
            output_path.stem + "_trimmed.mp4"
        )

        trim_command = [
            "ffmpeg",
            "-y",

            "-i",
            str(output_path),

            "-t",
            duration_text,

            "-map",
            "0:v:0",

            "-map",
            "0:a:0",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-pix_fmt",
            "yuv420p",

            "-r",
            "25",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-avoid_negative_ts",
            "make_zero",

            "-movflags",
            "+faststart",

            str(trimmed_path)
        ]

        trim_result = subprocess.run(
            trim_command,
            capture_output=True,
            text=True
        )

        if trim_result.returncode != 0:

            logger.error(
                "Second FFmpeg trim failed:\n%s",
                trim_result.stderr
            )

            raise RuntimeError(
                "Could not trim MP4."
            )

        try:
            output_path.unlink()
        except Exception:
            pass

        trimmed_path.replace(output_path)

        mp4_duration = get_media_duration(
            output_path
        )

        logger.info(
            "Trimmed MP4 duration: %.3f sec",
            mp4_duration
        )

    # --------------------------------------------------------
    # Final verification
    # --------------------------------------------------------

    video_duration = get_stream_duration(
        output_path,
        "v:0"
    )

    audio_stream_duration = get_stream_duration(
        output_path,
        "a:0"
    )

    logger.info(
        "FINAL MP4 format duration: %.3f sec",
        mp4_duration
    )

    logger.info(
        "FINAL video stream duration: %s",
        video_duration
    )

    logger.info(
        "FINAL audio stream duration: %s",
        audio_stream_duration
    )

    # We allow a very small codec/container difference.
    if mp4_duration > target_duration + 0.15:

        raise RuntimeError(
            f"MP4 duration mismatch: "
            f"audio={target_duration:.2f}s, "
            f"mp4={mp4_duration:.2f}s"
        )

    logger.info(
        "MP4 duration check OK: audio=%.3f sec, mp4=%.3f sec",
        target_duration,
        mp4_duration
    )

    return output_path


# ============================================================
# PROCESS TEXT
# ============================================================

async def process_text(chat_id, user_id, text):

    text = text.strip()

    if not text:

        await send_message(
            chat_id,
            "❌ Text খালি। আবার Text পাঠান।"
        )

        return

    if len(text) > 4000:

        await send_message(
            chat_id,
            "❌ Text অনেক বড়। সর্বোচ্চ 4000 characters ব্যবহার করুন।"
        )

        return

    await send_message(
        chat_id,
        "⏳ Voice তৈরি হচ্ছে..."
    )

    unique_id = f"{user_id}_{os.getpid()}_{int(asyncio.get_running_loop().time() * 1000)}"

    audio_path = TEMP_DIR / f"voice_{unique_id}.mp3"
    mp4_path = TEMP_DIR / f"voice_{unique_id}.mp4"

    try:

        # ----------------------------------------------------
        # Generate MP3
        # ----------------------------------------------------

        await generate_audio(
            text,
            user_id,
            audio_path
        )

        audio_duration = get_media_duration(
            audio_path
        )

        logger.info(
            "Generated MP3 duration: %.3f sec",
            audio_duration
        )

        # ----------------------------------------------------
        # Generate MP4
        # ----------------------------------------------------

        create_mp4(
            audio_path,
            mp4_path
        )

        mp4_duration = get_media_duration(
            mp4_path
        )

        logger.info(
            "Generated MP4 duration: %.3f sec",
            mp4_duration
        )

        # ----------------------------------------------------
        # Save last generated files
        # ----------------------------------------------------

        USER_SETTINGS[user_id]["last_mp3"] = str(
            audio_path
        )

        USER_SETTINGS[user_id]["last_mp4"] = str(
            mp4_path
        )

        await send_message(
            chat_id,
            (
                f"✅ Voice তৈরি হয়েছে!\n\n"
                f"⏱️ Audio: {audio_duration:.2f} sec\n"
                f"🎬 MP4: {mp4_duration:.2f} sec\n"
                f"⏸️ Word-by-word pause: OFF\n"
                f"🐢 Speed: -30%\n\n"
                f"নিচের option থেকে download করুন:"
            ),
            reply_markup=download_keyboard()
        )

    except Exception as e:

        logger.exception(
            "Audio/video generation failed"
        )

        await send_message(
            chat_id,
            (
                "❌ Voice তৈরি করতে সমস্যা হয়েছে।\n\n"
                f"Error: {str(e)[:500]}"
            )
        )


# ============================================================
# HANDLE MESSAGE
# ============================================================

async def handle_message(message):

    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = user.get("id")

    if not chat_id or not user_id:
        return

    text = message.get("text", "")

    # --------------------------------------------------------
    # /start
    # --------------------------------------------------------

    if text.startswith("/start"):

        get_user_settings(user_id)

        await send_message(
            chat_id,
            status_text(user_id),
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # /help
    # --------------------------------------------------------

    if text.startswith("/help"):

        help_text = (
            "ℹ️ VoiceGen BD Help\n\n"
            "1️⃣ Language থেকে বাংলা অথবা English নির্বাচন করুন।\n"
            "2️⃣ Voice থেকে আপনার পছন্দের voice নির্বাচন করুন।\n"
            "3️⃣ Text পাঠান।\n"
            "4️⃣ Voice তৈরি হলে MP3 অথবা MP4 download করুন।\n\n"
            "⏸️ Word-by-word pause: OFF\n"
            "🐢 Speed: -30%\n\n"
            "🎬 MP4-এর duration audio-এর duration-এর সাথে মিলিয়ে তৈরি হবে।"
        )

        await send_message(
            chat_id,
            help_text,
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # Normal text
    # --------------------------------------------------------

    if text:

        await process_text(
            chat_id,
            user_id,
            text
        )

        return


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def handle_callback(callback):

    callback_id = callback.get("id")
    data = callback.get("data", "")

    message = callback.get("message", {})

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    user = callback.get("from", {})
    user_id = user.get("id")

    if not chat_id or not user_id:
        return

    settings = get_user_settings(user_id)

    # --------------------------------------------------------
    # Answer callback
    # --------------------------------------------------------

    await answer_callback(callback_id)

    # --------------------------------------------------------
    # Start
    # --------------------------------------------------------

    if data == "start":

        await send_message(
            chat_id,
            status_text(user_id),
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # Back
    # --------------------------------------------------------

    if data == "back":

        await send_message(
            chat_id,
            status_text(user_id),
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # Language
    # --------------------------------------------------------

    if data == "language":

        await send_message(
            chat_id,
            "🌐 Language নির্বাচন করুন:",
            reply_markup=language_keyboard()
        )

        return

    # --------------------------------------------------------
    # Bangla
    # --------------------------------------------------------

    if data == "lang_bn":

        settings["language"] = "bn"

        await send_message(
            chat_id,
            (
                "🇧🇩 বাংলা language selected.\n\n"
                "🎤 Voice নির্বাচন করুন:"
            ),
            reply_markup=bangla_voice_keyboard()
        )

        return

    # --------------------------------------------------------
    # English
    # --------------------------------------------------------

    if data == "lang_en":

        settings["language"] = "en"

        await send_message(
            chat_id,
            (
                "🇺🇸 English language selected.\n\n"
                "🎤 Select voice:"
            ),
            reply_markup=english_voice_keyboard()
        )

        return

    # --------------------------------------------------------
    # Voice menu
    # --------------------------------------------------------

    if data == "voice":

        if settings["language"] == "bn":

            await send_message(
                chat_id,
                "🎤 বাংলা Voice নির্বাচন করুন:",
                reply_markup=bangla_voice_keyboard()
            )

        else:

            await send_message(
                chat_id,
                "🎤 Select English Voice:",
                reply_markup=english_voice_keyboard()
            )

        return

    # --------------------------------------------------------
    # Voice selection
    # --------------------------------------------------------

    if data.startswith("voice_"):

        voice_key = data.replace(
            "voice_",
            "",
            1
        )

        language = settings["language"]

        expected_prefix = language + "_"

        if not voice_key.startswith(expected_prefix):

            await send_message(
                chat_id,
                "❌ এই voice এই language-এর জন্য নয়।"
            )

            return

        voice_config = VOICE_CONFIG.get(
            voice_key
        )

        if not voice_config:

            await send_message(
                chat_id,
                "❌ Voice পাওয়া যায়নি।"
            )

            return

        settings["voice"] = voice_key.replace(
            language + "_",
            "",
            1
        )

        await send_message(
            chat_id,
            (
                f"✅ Voice selected successfully:\n\n"
                f"🎤 {voice_config['name']}\n"
                f"⏸️ Word-by-word pause: OFF\n"
                f"🐢 Speed: -30%\n\n"
                f"এখন Text পাঠান।"
            ),
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # Help
    # --------------------------------------------------------

    if data == "help":

        help_text = (
            "ℹ️ VoiceGen BD\n\n"
            "🎤 Voice নির্বাচন করুন\n"
            "🌐 Language নির্বাচন করুন\n"
            "📝 তারপর Text পাঠান\n\n"
            "⏸️ Word-by-word pause: OFF\n"
            "🐢 Speed: -30%\n\n"
            "🎵 MP3 এবং 🎬 MP4 দুই option থাকবে।\n"
            "MP4-এর duration audio-এর কাছাকাছি থাকবে।"
        )

        await send_message(
            chat_id,
            help_text,
            reply_markup=main_keyboard()
        )

        return

    # --------------------------------------------------------
    # MP3 Download
    # --------------------------------------------------------

    if data == "download_mp3":

        file_path = settings.get(
            "last_mp3"
        )

        if not file_path or not Path(file_path).exists():

            await send_message(
                chat_id,
                "❌ MP3 পাওয়া যায়নি। আগে একটি Text পাঠিয়ে Voice তৈরি করুন।"
            )

            return

        await send_message(
            chat_id,
            "📤 MP3 পাঠানো হচ্ছে..."
        )

        try:

            await send_audio(
                chat_id,
                file_path,
                caption="🎵 VoiceGen BD - MP3"
            )

        except Exception as e:

            logger.exception(
                "MP3 send failed"
            )

            await send_message(
                chat_id,
                f"❌ MP3 পাঠাতে সমস্যা হয়েছে: {str(e)[:300]}"
            )

        return

    # --------------------------------------------------------
    # MP4 Download
    # --------------------------------------------------------

    if data == "download_mp4":

        file_path = settings.get(
            "last_mp4"
        )

        if not file_path or not Path(file_path).exists():

            await send_message(
                chat_id,
                "❌ MP4 পাওয়া যায়নি। আগে একটি Text পাঠিয়ে Voice তৈরি করুন।"
            )

            return

        await send_message(
            chat_id,
            "📤 MP4 পাঠানো হচ্ছে..."
        )

        try:

            await send_video(
                chat_id,
                file_path,
                caption="🎬 VoiceGen BD - MP4"
            )

        except Exception as e:

            logger.exception(
                "MP4 send failed"
            )

            await send_message(
                chat_id,
                f"❌ MP4 পাঠাতে সমস্যা হয়েছে: {str(e)[:300]}"
            )

        return


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

async def telegram_webhook(request):

    try:

        update = await request.json()

        logger.info(
            "Telegram update received"
        )

        if "message" in update:

            await handle_message(
                update["message"]
            )

        elif "callback_query" in update:

            await handle_callback(
                update["callback_query"]
            )

        return web.json_response(
            {"ok": True}
        )

    except Exception as e:

        logger.exception(
            "Webhook error"
        )

        return web.json_response(
            {
                "ok": False,
                "error": str(e)
            },
            status=200
        )


# ============================================================
# HEALTH CHECK
# ============================================================

async def health(request):

    return web.json_response(
        {
            "status": "ok",
            "service": "VoiceGen BD",
            "word_pause": False,
            "speed": "-30%",
            "mp3": True,
            "mp4": True,
            "video": "exact_audio_duration"
        }
    )


# ============================================================
# SET WEBHOOK
# ============================================================

async def set_webhook():

    logger.info(
        "Setting Telegram webhook..."
    )

    result = await telegram_api(
        "setWebhook",
        data={
            "url": WEBHOOK_URL,
            "drop_pending_updates": "true"
        }
    )

    logger.info(
        "Webhook result: %s",
        result
    )

    if result.get("ok"):

        logger.info(
            "Telegram webhook set successfully: %s",
            WEBHOOK_URL
        )

    else:

        logger.error(
            "Webhook setup failed: %s",
            result
        )


# ============================================================
# GET WEBHOOK INFO
# ============================================================

async def get_webhook_info():

    result = await telegram_api(
        "getWebhookInfo"
    )

    logger.info(
        "Webhook info: %s",
        result
    )


# ============================================================
# STARTUP
# ============================================================

async def on_startup(app):

    logger.info(
        "Starting VoiceGen BD..."
    )

    logger.info(
        "Render URL: %s",
        RENDER_URL
    )

    logger.info(
        "Webhook URL: %s",
        WEBHOOK_URL
    )

    logger.info(
        "Word-by-word pause: OFF"
    )

    logger.info(
        "Speed: -30%%"
    )

    # --------------------------------------------------------
    # Check FFmpeg
    # --------------------------------------------------------

    try:

        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:

            first_line = result.stdout.splitlines()[0]

            logger.info(
                "FFmpeg available: %s",
                first_line
            )

        else:

            logger.error(
                "FFmpeg is not working."
            )

    except Exception:

        logger.exception(
            "FFmpeg check failed."
        )

    # --------------------------------------------------------
    # Check FFprobe
    # --------------------------------------------------------

    try:

        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:

            first_line = result.stdout.splitlines()[0]

            logger.info(
                "FFprobe available: %s",
                first_line
            )

        else:

            logger.error(
                "FFprobe is not working."
            )

    except Exception:

        logger.exception(
            "FFprobe check failed."
        )

    # --------------------------------------------------------
    # Telegram webhook
    # --------------------------------------------------------

    await set_webhook()

    await get_webhook_info()


# ============================================================
# CLEANUP
# ============================================================

async def on_cleanup(app):

    logger.info(
        "VoiceGen BD shutting down..."
    )

    try:

        await telegram_api(
            "deleteWebhook"
        )

    except Exception:

        logger.exception(
            "Could not delete webhook."
        )


# ============================================================
# APPLICATION
# ============================================================

app = web.Application(
    client_max_size=20 * 1024 * 1024
)

app.router.add_get(
    "/",
    health
)

app.router.add_get(
    "/health",
    health
)

app.router.add_post(
    WEBHOOK_PATH,
    telegram_webhook
)

app.on_startup.append(
    on_startup
)

app.on_cleanup.append(
    on_cleanup
)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    logger.info(
        "=========================================="
    )

    logger.info(
        "VoiceGen BD is starting..."
    )

    logger.info(
        "Port: %s",
        PORT
    )

    logger.info(
        "=========================================="
    )

    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
