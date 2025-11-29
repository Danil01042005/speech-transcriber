from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox

import grpc  # type: ignore
import pyaudio  # type: ignore

# Обеспечиваем доступ к сгенерированным protobuf-модулям (папка output).
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
if str(OUTPUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUTPUT_DIR))

from yandex.cloud.ai.stt.v3 import stt_pb2, stt_service_pb2_grpc  # type: ignore


# Настройки аудио и распознавания.
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 4096


@dataclass
class SpeechEvent:
    kind: str
    payload: str | None = None


class SpeechSession(threading.Thread):
    def __init__(self, api_key: str, events: "queue.Queue[SpeechEvent]") -> None:
        super().__init__(daemon=True)
        self.api_key = api_key
        self.events = events
        self._stop_event = threading.Event()
        self._pyaudio = pyaudio.PyAudio()
        self._stream: pyaudio.Stream | None = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._stream and self._stream.is_active():
            try:
                self._stream.stop_stream()
            except Exception:
                pass

    def run(self) -> None:
        try:
            cred = grpc.ssl_channel_credentials()
            channel = grpc.secure_channel("stt.api.cloud.yandex.net:443", cred)
            stub = stt_service_pb2_grpc.RecognizerStub(channel)

            self.events.put(SpeechEvent("status", "Подключение к сервису..."))
            responses = stub.RecognizeStreaming(
                self._request_iterator(),
                metadata=(("authorization", f"Api-Key {self.api_key}"),),
            )

            last_partial = ""
            last_final = ""
            last_normalized = ""
            pending_final: str | None = None
            for response in responses:
                event_type = response.WhichOneof("Event")
                if event_type == "partial" and response.partial.alternatives:
                    text = response.partial.alternatives[0].text.strip()
                    if text and text != last_partial:
                        last_partial = text
                        self.events.put(SpeechEvent("partial", text))
                elif event_type == "final" and response.final.alternatives:
                    text = response.final.alternatives[0].text.strip()
                    if text:
                        pending_final = text
                        last_partial = ""
                elif (
                    event_type == "final_refinement"
                    and response.final_refinement.normalized_text.alternatives
                ):
                    refined_alt = response.final_refinement.normalized_text.alternatives[0]
                    refined = getattr(refined_alt, "text", refined_alt)
                    refined = str(refined).strip()
                    if refined and refined != last_normalized:
                        last_final = refined
                        last_normalized = refined
                        last_partial = ""
                        self.events.put(SpeechEvent("final", refined))
                        pending_final = None

                if self._stop_event.is_set():
                    break

            if pending_final and pending_final != last_normalized:
                self.events.put(SpeechEvent("final", pending_final))

            self.events.put(SpeechEvent("finished"))
        except Exception as exc:  # noqa: BLE001
            self.events.put(SpeechEvent("error", f"Ошибка распознавания: {exc}"))
        finally:
            if self._stream is not None:
                try:
                    self._stream.close()
                except Exception:
                    pass
            self._pyaudio.terminate()

    def _request_iterator(self):
        options = stt_pb2.StreamingOptions(
            recognition_model=stt_pb2.RecognitionModelOptions(
                audio_format=stt_pb2.AudioFormatOptions(
                    raw_audio=stt_pb2.RawAudio(
                        audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                        sample_rate_hertz=RATE,
                        audio_channel_count=CHANNELS,
                    )
                ),
                text_normalization=stt_pb2.TextNormalizationOptions(
                    text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                    profanity_filter=False,
                    literature_text=False,
                ),
                language_restriction=stt_pb2.LanguageRestrictionOptions(
                    restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                    language_code=["ru-RU"],
                ),
                audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME,
            )
        )

        yield stt_pb2.StreamingRequest(session_options=options)

        self._stream = self._pyaudio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        self.events.put(SpeechEvent("status", "Запись началась — говорите в микрофон"))

        while not self._stop_event.is_set():
            try:
                data = self._stream.read(CHUNK, exception_on_overflow=False)
            except Exception:
                break
            yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
API_KEY_FILE = PROJECT_ROOT / "api_key.txt"


def _load_api_key() -> str:
    env_key = os.getenv("SPEECHKIT_API_KEY", "").strip()
    if env_key:
        return env_key
    if API_KEY_FILE.exists():
        try:
            return API_KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return ""


class AnimatedMic:
    def __init__(self, parent: tk.Frame) -> None:
        self.canvas = tk.Canvas(parent, width=140, height=140, bg="#1a1733", highlightthickness=0, bd=0)
        self.canvas.pack(side=tk.LEFT, padx=(0, 16))
        self._base_radius = 45
        self._pulse = 0
        self._active = False
        self._animation_job: int | None = None
        self.draw(initial=True)

    def start(self) -> None:
        self._active = True
        if self._animation_job is None:
            self._animate()

    def stop(self) -> None:
        self._active = False
        if self._animation_job is not None:
            self.canvas.after_cancel(self._animation_job)
            self._animation_job = None
        self.draw(initial=True)

    def draw(self, *, initial: bool = False) -> None:
        self.canvas.delete("all")
        center = 70
        radius = self._base_radius + (0 if initial else self._pulse)
        self.canvas.create_oval(
            center - radius,
            center - radius,
            center + radius,
            center + radius,
            outline="#4b3df6",
            width=4,
            stipple="gray12",
        )
        self.canvas.create_oval(
            center - (radius - 16),
            center - (radius - 16),
            center + (radius - 16),
            center + (radius - 16),
            outline="#9f7aff",
            width=3,
        )
        self.canvas.create_oval(
            center - (radius - 32),
            center - (radius - 32),
            center + (radius - 32),
            center + (radius - 32),
            fill="#735bff",
            outline="",
        )
        self.canvas.create_rectangle(center - 8, center - 30, center + 8, center + 15, fill="#1a1733", outline="")
        self.canvas.create_rectangle(center - 18, center + 12, center + 18, center + 20, fill="#1a1733", outline="")

    def _animate(self) -> None:
        if not self._active:
            return
        self._pulse = (self._pulse + 3) % 20
        self.draw()
        self._animation_job = self.canvas.after(80, self._animate)


class SpeechkitApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Live Speech Transcriber")
        self.root.geometry("760x540")
        self.root.configure(bg="#0d0b1a")
        self.root.minsize(640, 480)

        self.api_key = _load_api_key()
        self.status_var = tk.StringVar(value="Готово к записи")

        self._build_ui()

        self.events: "queue.Queue[SpeechEvent]" = queue.Queue()
        self.session: SpeechSession | None = None
        self.transcript_parts: list[str] = []
        self.last_partial = ""

        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        header = tk.Canvas(self.root, height=120, highlightthickness=0, bd=0)
        header.pack(fill=tk.X)
        for i in range(0, 760):
            color = "#2f1d8c" if i < 250 else "#4528b8" if i < 500 else "#6135f5"
            header.create_line(i, 0, i, 120, fill=color)
        header.create_text(
            26,
            36,
            anchor="w",
            text="Live Speech Transcriber",
            font=("Segoe UI", 26, "bold"),
            fill="#f7f4ff",
        )

        shell = tk.Frame(self.root, bg="#15122a", bd=0, relief=tk.FLAT)
        shell.pack(fill=tk.BOTH, expand=True, padx=20, pady=(6, 20))

        top_section = tk.Frame(shell, bg="#15122a")
        top_section.pack(fill=tk.X, padx=18, pady=(18, 10))

        self.mic = AnimatedMic(top_section)

        control_frame = tk.Frame(top_section, bg="#15122a")
        control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        button_frame = tk.Frame(control_frame, bg="#15122a")
        button_frame.pack(fill=tk.X, pady=(6, 12))

        self.start_button = tk.Button(button_frame, text="Начать запись", command=self.start)
        self._style_button(self.start_button, "#50f5c1", "#161231")
        self.start_button.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_button = tk.Button(button_frame, text="Остановить", command=self.stop, state=tk.DISABLED)
        self._style_button(self.stop_button, "#ff6b9a", "#2c1d3f")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 8))

        clear_button = tk.Button(button_frame, text="Очистить текст", command=self.clear_transcript)
        self._style_button(clear_button, "#7f89ff", "#2c1d3f")
        clear_button.pack(side=tk.LEFT)

        status_label = tk.Label(
            control_frame,
            textvariable=self.status_var,
            anchor="w",
            bg="#15122a",
            fg="#aea6ff",
            font=("Segoe UI", 11),
        )
        status_label.pack(fill=tk.X, pady=(4, 0))

        text_frame = tk.Frame(shell, bg="#15122a", bd=0)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))

        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            height=16,
            state=tk.DISABLED,
            bg="#0f0d24",
            fg="#f7f4ff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=16,
            font=("Segoe UI", 13),
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.text_widget, command=self.text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.config(yscrollcommand=scrollbar.set)

    def _style_button(self, button: tk.Button, color: str, hover_bg: str) -> None:
        base_bg = "#231b3f"
        button.configure(
            bg=base_bg,
            fg="#f4f1ff",
            activebackground=hover_bg,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            font=("Segoe UI Semibold", 12),
            padx=18,
            pady=10,
            highlightthickness=0,
        )
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=base_bg))

    def start(self) -> None:
        if not self.api_key:
            messagebox.showwarning(
                "API ключ",
                "API ключ SpeechKit не задан. Установите переменную SPEECHKIT_API_KEY или обновите код.",
            )
            return

        if self.session and self.session.is_alive():
            return

        self.transcript_parts.clear()
        self.status_var.set("Подготовка...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.mic.start()

        self.session = SpeechSession(self.api_key, self.events)
        self.session.start()

    def stop(self) -> None:
        if self.session:
            self.session.stop()
        self.stop_button.config(state=tk.DISABLED)
        self.mic.stop()

    def clear_transcript(self) -> None:
        self.transcript_parts.clear()
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.config(state=tk.DISABLED)
        self.status_var.set("Текст очищен")

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event.kind == "status" and event.payload:
                    self.status_var.set(event.payload)
                elif event.kind == "partial" and event.payload:
                    text = " ".join(self.transcript_parts + [event.payload])
                    self._set_text(text, append=False)
                elif event.kind == "final" and event.payload:
                    self.transcript_parts.append(event.payload)
                    self._set_text(" ".join(self.transcript_parts), append=False)
                elif event.kind == "error" and event.payload:
                    messagebox.showerror("Ошибка", event.payload)
                    self.status_var.set("Ошибка распознавания")
                    self.start_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    self.mic.stop()
                elif event.kind == "finished":
                    self.status_var.set("Запись остановлена")
                    self.start_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    self.mic.stop()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)

    def _set_text(self, text: str, append: bool = False) -> None:
        self.text_widget.config(state=tk.NORMAL)
        if append:
            self.text_widget.insert(tk.END, text)
        else:
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert(tk.END, text)
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = SpeechkitApp()
    app.run()


if __name__ == "__main__":
    main()

