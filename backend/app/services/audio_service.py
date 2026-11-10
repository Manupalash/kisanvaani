import asyncio
import os
import re
import shutil
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_DURATION_SECONDS = 30
SUPPORTED_FORMATS = {"wav", "mp3", "ogg", "flac", "aac", "m4a"}
MIME_TO_FORMAT = {
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
    "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/ogg": "ogg",
    "audio/flac": "flac", "audio/aac": "aac", "audio/mp4": "m4a",
    "audio/x-m4a": "m4a", "audio/webm": "webm", "video/webm": "webm",
}


@dataclass
class PreparedAudio:
    path: str
    filename: str
    content_type: str
    duration: float
    temporary_directory: str | None = None

    def cleanup(self) -> None:
        if self.temporary_directory:
            shutil.rmtree(self.temporary_directory, ignore_errors=True)


async def _read_limited(upload) -> bytes:
    content = bytearray()
    while chunk := await upload.read(64 * 1024):
        content.extend(chunk)
        if len(content) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Audio exceeds the 10 MB upload limit")
    if not content:
        raise HTTPException(status_code=400, detail="Audio recording is empty")
    return bytes(content)


def _container(data: bytes) -> str | None:
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE": return "wav"
    if data.startswith(b"OggS"): return "ogg"
    if data.startswith(b"fLaC"): return "flac"
    if data.startswith(b"ID3") or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"): return "mp3"
    if data.startswith(b"\x1aE\xdf\xa3"): return "webm"
    if len(data) > 12 and data[4:8] == b"ftyp": return "m4a"
    if data.startswith(b"ADIF") or (len(data) > 2 and data[0] == 0xFF and (data[1] & 0xF6) == 0xF0): return "aac"
    return None


async def prepare_audio(upload, *, ffmpeg_binary: str = "ffmpeg") -> PreparedAudio:
    try:
        data = await _read_limited(upload)
    except HTTPException:
        await upload.close()
        raise
    claimed = MIME_TO_FORMAT.get((upload.content_type or "").lower())
    extension = Path(upload.filename or "").suffix.lower().lstrip(".")
    if extension == "webm": claimed = "webm"
    actual = _container(data)
    if not claimed or claimed not in SUPPORTED_FORMATS | {"webm"}:
        raise HTTPException(status_code=415, detail="Unsupported audio format. Use WAV, MP3, OGG, FLAC, AAC, or M4A.")
    if not actual or actual != claimed:
        raise HTTPException(status_code=400, detail="Audio content is invalid or does not match the declared format")
    source_dir = tempfile.mkdtemp(prefix="kisanvaani-audio-")
    suffix = ".webm" if claimed == "webm" else f".{claimed}"
    source_path = os.path.join(source_dir, f"input{suffix}")
    try:
        with open(source_path, "wb") as target:
            target.write(data)
        probe = await asyncio.create_subprocess_exec(ffmpeg_binary, "-v", "error", "-i", source_path, "-f", "null", "-", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        try: _, decode_error = await asyncio.wait_for(probe.communicate(), timeout=20)
        except asyncio.TimeoutError:
            probe.kill(); await probe.wait(); raise HTTPException(status_code=400, detail="Audio could not be decoded within the validation time limit")
        if probe.returncode != 0:
            raise HTTPException(status_code=400, detail="Audio recording is not decodable")
        duration_probe = await asyncio.create_subprocess_exec(ffmpeg_binary, "-i", source_path, "-f", "null", "-", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        try:
            _, stderr = await asyncio.wait_for(duration_probe.communicate(), timeout=20)
        except asyncio.TimeoutError:
            duration_probe.kill(); await duration_probe.wait()
            raise HTTPException(status_code=400, detail="Audio duration could not be checked")
        found = re.search(rb"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
        if not found: raise HTTPException(status_code=400, detail="Could not determine audio duration")
        duration = int(found.group(1))*3600 + int(found.group(2))*60 + float(found.group(3))
        if duration <= 0: raise HTTPException(status_code=400, detail="Audio recording is empty")
        if duration > MAX_DURATION_SECONDS: raise HTTPException(status_code=413, detail="Audio exceeds the 30 second duration limit")
        if claimed == "webm":
            converted_path = os.path.join(source_dir, "converted.wav")
            process = await asyncio.create_subprocess_exec(ffmpeg_binary, "-v", "error", "-i", source_path, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "wav", converted_path, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()
            if process.returncode != 0: raise HTTPException(status_code=400, detail="WebM audio could not be converted to WAV")
            if os.path.getsize(converted_path) > MAX_AUDIO_BYTES: raise HTTPException(status_code=413, detail="Converted audio exceeds the 10 MB upload limit")
            try:
                with wave.open(converted_path, "rb") as converted:
                    if converted.getnchannels() != 1 or converted.getframerate() != 16000 or converted.getsampwidth() != 2:
                        raise HTTPException(status_code=400, detail="WebM conversion did not produce mono 16 kHz PCM WAV")
            except (wave.Error, EOFError) as exc: raise HTTPException(status_code=400, detail="Converted audio WAV is invalid") from exc
            return PreparedAudio(converted_path, "recording.wav", "audio/wav", duration, source_dir)
        return PreparedAudio(source_path, f"recording.{claimed}", {
            "wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg", "flac": "audio/flac", "aac": "audio/aac", "m4a": "audio/mp4"
        }[claimed], duration, source_dir)
    except Exception:
        shutil.rmtree(source_dir, ignore_errors=True)
        raise
