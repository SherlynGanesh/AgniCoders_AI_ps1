import io
import math
import wave
import logging
from typing import Dict, Any, Tuple, Optional
import speech_recognition as sr

try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
    except ImportError:
        audioop = None

logger = logging.getLogger("dukaanmitra.voice_service")


class VoiceService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def analyze_audio_volume(self, wav_bytes: bytes) -> Tuple[float, float, bool]:
        """
        Analyzes audio volume from WAV bytes.
        Returns: (rms, db, is_audible)
        """
        try:
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                sampwidth = wf.getsampwidth()
                nframes = wf.getnframes()
                if nframes == 0:
                    return 0.0, -100.0, False
                frames = wf.readframes(nframes)

                if audioop and sampwidth in (1, 2, 4):
                    rms = audioop.rms(frames, sampwidth)
                else:
                    # Fallback RMS calculation
                    import struct
                    fmt = f"<{nframes}h" if sampwidth == 2 else f"<{nframes}b"
                    samples = struct.unpack(fmt, frames[:nframes * sampwidth])
                    rms = math.sqrt(sum(s * s for s in samples) / len(samples)) if samples else 0.0

                db = 20 * math.log10(rms) if rms > 0 else -100.0
                is_audible = rms > 250
                return float(rms), float(round(db, 1)), is_audible
        except Exception as e:
            logger.warning(f"Error analyzing audio volume: {e}")
            return 500.0, -20.0, True

    def transcribe_wav(self, wav_bytes: bytes) -> Dict[str, Any]:
        """
        Transcribes 16-bit PCM WAV audio.
        Returns transcript, audible status, and diagnostic flags.
        """
        rms, db, is_audible = self.analyze_audio_volume(wav_bytes)

        if not is_audible:
            return {
                "success": False,
                "transcript": "",
                "rms": rms,
                "db": db,
                "error": "not_audible",
                "message": "⚠️ You are not audible. Mic input volume is too low. Please speak louder or bring mic closer."
            }

        try:
            wav_file = io.BytesIO(wav_bytes)
            with sr.AudioFile(wav_file) as source:
                # Adjust for ambient noise briefly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = self.recognizer.record(source)

            # Try Hindi (hi-IN) first which best captures Hinglish / Indian store terms
            transcript = ""
            for lang_code in ["hi-IN", "mr-IN", "en-IN"]:
                try:
                    transcript = self.recognizer.recognize_google(audio_data, language=lang_code)
                    if transcript and transcript.strip():
                        break
                except sr.UnknownValueError:
                    continue
                except Exception as ex:
                    logger.debug(f"Recognition attempt for {lang_code} failed: {ex}")
                    continue

            if not transcript or not transcript.strip():
                return {
                    "success": False,
                    "transcript": "",
                    "rms": rms,
                    "db": db,
                    "error": "unclear_speech",
                    "message": "⚠️ Context is not clear. Speech was detected but could not be recognized as grocery/store words."
                }

            return {
                "success": True,
                "transcript": transcript.strip(),
                "rms": rms,
                "db": db,
                "error": None,
                "message": None
            }

        except sr.RequestError as e:
            logger.error(f"Speech recognition service request error: {e}")
            return {
                "success": False,
                "transcript": "",
                "rms": rms,
                "db": db,
                "error": "service_unavailable",
                "message": "⚠️ Backend speech recognition cloud service unreachable. Please type your order or try again."
            }
        except Exception as e:
            logger.error(f"Unexpected error in transcribe_wav: {e}")
            return {
                "success": False,
                "transcript": "",
                "rms": rms,
                "db": db,
                "error": "transcription_failed",
                "message": f"⚠️ Audio processing error: {str(e)}"
            }


voice_service = VoiceService()
