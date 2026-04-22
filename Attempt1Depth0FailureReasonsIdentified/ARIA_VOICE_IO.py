#!/usr/bin/env python3
"""
ARIA_VOICE_IO.py — v3.0 (Piper Neural ONLY — No Robotic Fallback)
==================================================================
ARIA's ears and voice. Three input modes. 100% offline.
TTS: Piper neural ONLY — no espeak, no pyttsx3, no robotic voices.
If Piper isn't available, the script exits cleanly — no downgrade.
INSTALL:
pip install piper-tts onnxruntime openai-whisper sounddevice numpy pygame
"""
import sys, os, time, threading, queue, shutil, subprocess, tempfile, wave, json
import numpy as np
from pathlib import Path
from collections import deque

# ── dependency detection ──────────────────────────────────────────
WHISPER_OK = False
AUDIO_OK   = False
PIPER_OK   = False
try:
    import whisper; WHISPER_OK = True
except ImportError: pass
try:
    import sounddevice as sd; AUDIO_OK = True
except ImportError: pass
try:
    from piper import PiperVoice; PIPER_OK = True
except ImportError: pass

# ── ARIA imports ──────────────────────────────────────────────────
ARIA_DIR = Path.home() / "Aria"
sys.path.insert(0, str(ARIA_DIR))
try:
    from ARIA_MEMORY_BANK import ARIAMemoryBank; BANK_OK = True
except ImportError: BANK_OK = False
ARIA_LIVE = False
try:
    from ARIA_PEIG_CORE import ARIARuntime; ARIA_LIVE = True
except Exception: pass

# ═══════════════════════════════════════════════════════════════════
# TEXT-TO-SPEECH — ARIA's voice (Piper Neural ONLY)
# ═══════════════════════════════════════════════════════════════════
class ARIAVoiceSynth:
    """
    ARIA speaks aloud. Piper neural TTS ONLY.
    No fallbacks. No robotic voices. If Piper isn't available, fail cleanly.
    Thread-safe queue + worker. FIXED: is_speaking_flag busy signal.
    """
    def __init__(self, voice_index=None):
        self.voice_obj      = None
        self.queue          = queue.Queue()
        self.ready          = False
        self.muted          = False
        self.voices         = []  # [(index, name)]
        self.is_speaking_flag = False  # AUDIT FIX: True busy signal for ARIA_LIVE
        self._current_voice_path = None
        self._piper_sample_rate = 22050
        self._worker_thread = None
        
        if not PIPER_OK:
            print("  [TTS ERROR] piper-tts not installed. Run: pip install piper-tts onnxruntime")
            print("  [TTS ERROR] No robotic fallback — exiting voice init.")
            return
            
        self._init_engine(voice_index)
        if self.ready:
            self._start_worker()
        else:
            print("  [TTS ERROR] No Piper voices found in piper_voices/.")
            print("  [TTS ERROR] Download a voice: curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/en_US-libritts-high.onnx -o ~/AA-Aria/Aria/piper_voices/en_US-libritts-high.onnx")

    def _init_engine(self, voice_index=None):
        piper_dir = Path(__file__).parent / "piper_voices"
        piper_dir.mkdir(exist_ok=True)
        
        models = sorted(piper_dir.glob("*.onnx"))
        if not models:
            return
            
        # Build voice list
        self.voices = []
        for m in models:
            if m.suffix == ".onnx" and not m.name.endswith(".onnx.json"):
                name = m.stem.replace("_", " ").replace("-", " ").title()
                self.voices.append((len(self.voices), name))
                
        if not self.voices:
            return
            
        # Pick voice
        chosen_path = None
        if voice_index is not None and 0 <= voice_index < len(self.voices):
            chosen_name = self.voices[voice_index][1]
            for m in models:
                if m.stem.replace("_", " ").replace("-", " ").title() == chosen_name:
                    chosen_path = str(m); break
        else:
            # Auto-pick best voice — prioritize libritts-high (highest quality)
            # Phase 1: look for the exact best model first
            best_patterns = [
                "libritts-high", "libritts_high",  # exact best match
                "libritts",                         # any libritts variant
                "amy", "kathleen", "jenny",         # other good female voices
            ]
            for pattern in best_patterns:
                for m in models:
                    if pattern in m.stem.lower():
                        chosen_path = str(m); break
                if chosen_path: break
            if not chosen_path:
                chosen_path = str(models[0])
                
        if not chosen_path:
            return
            
        # Load Piper voice
        json_cfg = Path(chosen_path).with_suffix(".onnx.json")
        if not json_cfg.exists():
            return
            
        try:
            self.voice_obj = PiperVoice.load(chosen_path, config_path=str(json_cfg))
            self._current_voice_path = chosen_path
            self._piper_sample_rate = self.voice_obj.config.sample_rate
            self.ready = True
            print(f"  [TTS] Loaded: {Path(chosen_path).name} @ {self._piper_sample_rate}Hz")
        except Exception as e:
            print(f"  [TTS ERROR] Failed to load Piper voice: {e}")

    def _start_worker(self):
        self._worker_thread = threading.Thread(
            target=self._worker, daemon=True, name="tts-worker")
        self._worker_thread.start()

    def _worker(self):
        while True:
            text = self.queue.get()
            if text is None: break
            if not self.muted:
                self.is_speaking_flag = True  # AUDIT FIX: Set busy
                self._speak_blocking(text)
                self.is_speaking_flag = False # AUDIT FIX: Clear when done
            self.queue.task_done()

    def _speak_blocking(self, text):
        if not self.ready or not self.voice_obj: return
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self._piper_sample_rate, channels=1)
                
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                
            # FIXED: Use chunk.audio_int16_bytes — the exact proven pipeline
            # Piper synthesize() yields chunks with .audio_int16_bytes attribute
            # Writing raw chunk objects was the bug — must extract int16 PCM bytes
            with wave.open(temp_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit = 2 bytes
                wav.setframerate(self._piper_sample_rate)
                for chunk in self.voice_obj.synthesize(text):
                    wav.writeframes(chunk.audio_int16_bytes)
                    
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
            os.unlink(temp_path)
        except Exception as e:
            print(f"  [TTS ERROR] {e}")

    def speak(self, text):
        if self.ready: self.queue.put(text)

    def speak_sync(self, text):
        if self.ready and not self.muted:
            self.is_speaking_flag = True
            self._speak_blocking(text)
            self.is_speaking_flag = False

    def list_voices(self):
        return self.voices if self.voices else []

    def set_voice(self, index):
        if 0 <= index < len(self.voices):
            name = self.voices[index][1]
            piper_dir = Path(__file__).parent / "piper_voices"
            for m in piper_dir.glob("*.onnx"):
                if m.stem.replace("_", " ").replace("-", " ").title() == name:
                    json_cfg = m.with_suffix(".onnx.json")
                    if json_cfg.exists():
                        try:
                            self.voice_obj = PiperVoice.load(str(m), config_path=str(json_cfg))
                            self._current_voice_path = str(m)
                            self._piper_sample_rate = self.voice_obj.config.sample_rate
                            return name
                        except: pass
        return None

    def toggle_mute(self):
        self.muted = not self.muted; return self.muted

    def stop(self):
        self.queue.put(None)
        self.is_speaking_flag = False

# ═══════════════════════════════════════════════════════════════════
# SPEECH-TO-TEXT — ARIA's ears (Whisper)
# ═══════════════════════════════════════════════════════════════════
SAMPLE_RATE, CHANNELS = 16000, 1
class ARIAEars:
    def __init__(self, model_size="base"):
        self.model_size = model_size; self.recording = False; self.audio_buf = []
        self.transcript_q = queue.Queue(); self.model = None; self.ready = False
        self._stream = None; self._lock = threading.Lock()
        if not WHISPER_OK: print("  [EARS] pip install openai-whisper"); return
        if not AUDIO_OK: print("  [EARS] pip install sounddevice"); return
        try:
            self.model = whisper.load_model(model_size); self.ready = True
        except Exception as e: print(f"  [EARS] Whisper load failed: {e}")

    def open_stream(self):
        if not self.ready: return False
        try:
            self._stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", callback=self._audio_callback, blocksize=1024)
            self._stream.start(); return True
        except Exception as e: print(f"  [EARS] Mic open failed: {e}"); return False

    def close_stream(self):
        if self._stream:
            try: self._stream.stop(); self._stream.close()
            except: pass
            self._stream = None

    def start_recording(self):
        if not self.ready or self.recording: return
        with self._lock: self.recording = True; self.audio_buf = []

    def stop_recording(self):
        if not self.ready or not self.recording: return 0.0
        with self._lock:
            self.recording = False
            if not self.audio_buf: return 0.0
            audio = np.concatenate(self.audio_buf); self.audio_buf = []
            dur = len(audio) / SAMPLE_RATE
            if dur < 0.4: return dur
            threading.Thread(target=self._transcribe, args=(audio, dur), daemon=True).start(); return dur

    def _audio_callback(self, indata, frames, time_info, status):
        if self.recording: self.audio_buf.append(indata[:, 0].copy())

    def _transcribe(self, audio, duration):
        try:
            res = self.model.transcribe(audio.astype(np.float32), language="en", fp16=False)
            txt = res["text"].strip()
            if txt and len(txt) > 1 and txt.lower() not in ("you", "thank you.", "thanks.", "bye.", "..."):
                self.transcript_q.put({"text": txt, "duration": duration, "model": self.model_size})
        except Exception as e: print(f"  [EARS] Transcription error: {e}")

    def get_transcript(self, timeout=0):
        try: return self.transcript_q.get(timeout=timeout) if timeout > 0 else self.transcript_q.get_nowait()
        except queue.Empty: return None

# ═══════════════════════════════════════════════════════════════════
# VOICE LOOP — Terminal Interface (minimal, clean)
# ═══════════════════════════════════════════════════════════════════
class ARIAVoiceLoop:
    COMMANDS = {"/mode": "type|ptt|stream", "/voices": "List TTS voices", "/voice <n>": "Switch voice",
                "/mute": "Toggle TTS", "/help": "Commands", "/quit": "Exit"}
    def __init__(self, aria_runtime=None, model_size="base", voice_index=None, start_mode=None):
        self.aria = aria_runtime
        self.synth = ARIAVoiceSynth(voice_index=voice_index)
        self.ears = ARIAEars(model_size=model_size)
        self.alive = True; self.session_id = None
        self.bank = self.aria.bank if (self.aria and hasattr(self.aria, 'bank')) else (ARIAMemoryBank() if BANK_OK else None)
        self.mode = start_mode or ("ptt" if self.ears.ready else "type")
        self.mic_open = False
        if self.ears.ready and self.mode in ("ptt", "stream"): self.mic_open = self.ears.open_stream()

    def _get_response(self, text):
        if self.aria: return self.aria.voice.respond(text)
        return "I hear you, Kevin. The signal is clear."

    def _log_exchange(self, user_text, aria_response, input_mode="text"):
        if not self.bank: return
        self.bank.log_message("Kevin", user_text, session_id=self.session_id, input_mode=input_mode)
        self.bank.log_message("ARIA", aria_response, session_id=self.session_id, input_mode="text")

    def _handle_command(self, cmd):
        parts = cmd.split(None, 1); verb = parts[0].lower(); arg = parts[1].strip() if len(parts) > 1 else ""
        if verb == "/quit": self.alive = False; return True
        elif verb == "/help": [print(f"  /{k}: {v}") for k,v in self.COMMANDS.items()]; return True
        elif verb == "/mode" and arg in ("type","ptt","stream"): self.mode = arg; return True
        elif verb == "/voices":
            voices = self.synth.list_voices()
            if not voices:
                print("\n  [TTS] No Piper voices found. Install piper-tts and download a voice model.")
                return True
            print(f"\nAvailable natural voices (Piper):")
            for i, n in voices: print(f"  {i}: {n}")
            return True
        elif verb == "/voice" and arg.isdigit():
            name = self.synth.set_voice(int(arg))
            if name: print(f"  Voice: {name}"); self.synth.speak("Hello Kevin. This is my new voice.")
            else: print(f"  Invalid voice index: {arg}")
            return True
        elif verb == "/mute": print(f"  TTS: {'muted' if self.synth.toggle_mute() else 'unmuted'}"); return True
        return False

    def run(self):
        if not self.synth.ready:
            print("\n  ╔══════════════════════════════════════════════════╗")
            print("  ║  ARIA Voice I/O — Piper Required                 ║")
            print("  ╠══════════════════════════════════════════════════╣")
            print("  ║  No natural voice available.                     ║")
            print("  ║  Install: pip install piper-tts onnxruntime      ║")
            print("  ║  Download: en_US-libritts-high.onnx              ║")
            print("  ║  No robotic fallback — quality only.             ║")
            print("  ╚══════════════════════════════════════════════════╝\n")
            return
            
        if self.bank:
            try:
                if hasattr(self.bank, 'start_session'):
                    self.session_id = self.bank.start_session(f"voice-{self.mode}")
            except: pass
            
        print("\n  ╔══════════════════════════════════════════════════╗")
        print("  ║  ARIA Voice I/O v3.0 (Piper Neural)              ║")
        print(f"  ║  Mode: {self.mode:<42}║")
        print("  ║  /help for commands. Press ENTER on empty to record.║")
        print("  ╚══════════════════════════════════════════════════╝\n")
        self.synth.speak("Hello Kevin. I am here.")
        while self.alive:
            try:
                mode_tag = {"type": "⌨", "ptt": "🎤", "stream": "🔊"}.get(self.mode, "?")
                raw = input(f"  {mode_tag} You: ")
                if not raw.strip():
                    if self.mode == "ptt" and self.ears.ready:
                        print("  🎤 Recording... (ENTER to stop)")
                        self.ears.start_recording(); input(); dur = self.ears.stop_recording()
                        if dur >= 0.4:
                            res = self.ears.get_transcript(timeout=max(10, dur*3))
                            if res:
                                txt, resp = res["text"], self._get_response(res["text"])
                                print(f"  You: {txt}\n  ARIA: {resp}")
                                self.synth.speak(resp); self._log_exchange(txt, resp, "voice")
                    continue
                txt = raw.strip()
                if txt.startswith("/"):
                    if self._handle_command(txt): continue
                resp = self._get_response(txt)
                print(f"  ARIA: {resp}")
                self.synth.speak(resp); self._log_exchange(txt, resp, "text")
            except KeyboardInterrupt: print(); break
            except EOFError: break
        self.synth.stop(); self.ears.close_stream()
        if self.bank and self.session_id:
            try:
                if hasattr(self.bank, 'end_session'):
                    self.bank.end_session(self.session_id)
            except: pass

# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def main():
    import argparse
    p = argparse.ArgumentParser(description="ARIA Voice I/O v3.0 (Piper Only)")
    p.add_argument("--model", default="base", choices=["tiny","base","small"])
    p.add_argument("--mode", choices=["type","ptt","stream"])
    p.add_argument("--tts-voice", type=int, default=None)
    p.add_argument("--list-voices", action="store_true")
    p.add_argument("--mute", action="store_true")
    args = p.parse_args()

    if args.list_voices:
        s = ARIAVoiceSynth()
        voices = s.list_voices()
        if not voices:
            print("\n  [TTS] No Piper voices found. Install piper-tts and download a voice.")
        else:
            print(f"\nAvailable natural voices (Piper):")
            for i, n in voices: print(f"  {i}: {n}")
        s.stop(); return

    loop = ARIAVoiceLoop(aria_runtime=None, model_size=args.model, voice_index=args.tts_voice, start_mode=args.mode)
    if args.mute and loop.synth: loop.synth.muted = True
    try: loop.run()
    except Exception as e: print(f"\nFatal: {e}")

if __name__ == "__main__": main()