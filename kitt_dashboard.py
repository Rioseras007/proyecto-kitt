import tkinter as tk
import customtkinter as ctk
import sounddevice as sd
import numpy as np
import threading
import time
import math
import os
import sys
import ctypes
import miniaudio
import webbrowser
from pathlib import Path
from tkinter import filedialog

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Native Windows Audio Engine (MCI) for MP3 Background Music
class MciPlayer:
    def __init__(self):
        self.mci = ctypes.windll.winmm
        # Define types to prevent crashes/errors in some environments
        self.mci.mciSendStringW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        self.mci.mciSendStringW.restype = ctypes.c_uint
        
        self.alias = "kitt_music"
        self.is_opened = False

    def play(self, filepath):
        if not os.path.exists(filepath): return 1 # File not found code
        
        # 1. ALWAYS force a clean close first to avoid "alias already in use"
        self.stop()
        time.sleep(0.1) # Vital delay for Windows driver to reset
        
        abs_path = os.path.abspath(filepath)
        # 2. Open with a fresh command
        # Note: We use MCI 'open' which returns a non-zero code on failure
        res_open = self.mci.mciSendStringW(f'open "{abs_path}" type mpegvideo alias {self.alias}', None, 0, None)
        if res_open == 0:
            self.is_opened = True
            res_play = self.mci.mciSendStringW(f'play {self.alias} from 0', None, 0, None)
            return res_play
        return res_open

    def stop(self):
        # We try to stop and close even if we think it's not opened, just in case
        self.mci.mciSendStringW(f'stop {self.alias}', None, 0, None)
        self.mci.mciSendStringW(f'close {self.alias}', None, 0, None)
        self.is_opened = False

# Digital Audio Synthesizer (KittSynth) - Generates waveforms on the fly
class KittSynth:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate

    def _play(self, data):
        try:
            # sd.play is non-blocking and handles mixing on most Windows systems
            sd.play(data, self.sample_rate)
        except Exception as e:
            print(f"Synth error: {e}")

    def generate_sine(self, freq, duration, volume=0.3):
        t = np.linspace(0, duration, int(self.sample_rate * duration), False, dtype=np.float32)
        wave = np.sin(2 * np.pi * freq * t).astype(np.float32)
        decay = np.exp(-10 * t)
        return wave * decay * volume

    def generate_triangle(self, freq, duration, volume=0.3):
        t = np.linspace(0, duration, int(self.sample_rate * duration), False, dtype=np.float32)
        wave = (2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1).astype(np.float32)
        return wave * np.exp(-5 * t) * volume

    def play_click(self):
        s1 = self.generate_sine(2000, 0.05, 0.4)
        s2 = self.generate_sine(4000, 0.03, 0.2)
        data = s1.copy()
        data[:len(s2)] += s2
        self._play(data)

    def play_mode(self):
        # Dual 1200Hz/1800Hz confirm tones
        s1 = self.generate_sine(1200, 0.12, 0.3) 
        s2 = np.zeros_like(s1)
        # delayed harmonic
        start_idx = int(0.04 * self.sample_rate)
        h = self.generate_sine(1800, 0.08, 0.2)
        s2[start_idx:start_idx+len(h)] = h
        self._play(s1 + s2)

    def play_init(self):
        try:
            full_data = np.array([], dtype=np.float32)
            for i in range(6):
                ping = self.generate_triangle(3000 - (i * 400), 0.15, 0.15)
                full_data = np.concatenate([full_data, ping])
            self._play(full_data)
        except Exception as e:
            print(f"Neural Boot Init error: {e}")

    def play_pursuit(self):
        duration = 0.5
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        freqs = np.geomspace(100, 1200, len(t))
        phases = 2 * np.pi * np.cumsum(freqs) / self.sample_rate
        wave = np.sin(phases)
        env = np.ones_like(t)
        env[:int(0.1*len(t))] = np.linspace(0, 1, int(0.1*len(t)))
        env[-int(0.1*len(t)):] = np.linspace(1, 0, int(0.1*len(t)))
        self._play(wave * env * 0.4)

# Color Palette (Canonical KITT)
COLOR_BG = "#0b0b0b"
COLOR_PANEL_BG = "#171818"
COLOR_RED_ON = "#B40522"
COLOR_RED_GLOW = "#FF0000"
COLOR_RED_OFF = "#220000"
COLOR_GREEN = "#A9D739"
COLOR_AMBER = "#FFCC00"
COLOR_PURSUIT_OFF = "#9D1926"
COLOR_GREY_BLOCK = "#9b9c98"
LED_COUNT = 20
COLUMNS = 3

class KittDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KITT Dashboard - Stable Audio")
        self.geometry("1100x950")
        self.configure(fg_color=COLOR_BG)

        # Initialize Engines
        self.audio_player = MciPlayer()
        self.synth = KittSynth()
        self.audio_file = resource_path("Knight Rider.mp3")
        self.current_mode = "off"
        
        self.stream = None
        self.mic_gain = 2.0
        self.mic_level = 0
        self.v_smooth = 0 # Tracks smooth decay for speech
        self.playback_data = None # Real waveform data for v3.0
        self.playback_idx = 0
        self.scanner_pos = 0
        self.scanner_dir = 1
        
        self.setup_ui()
        
        # Set Window Icon (ICO file required for Windows)
        try:
            icon_ico = resource_path("kitt.ico")
            if os.path.exists(icon_ico):
                self.iconbitmap(icon_ico)
        except:
            pass
            
        self.animate_all()
        
        # Neural Boot Sound
        self.after(500, self.synth.play_init)

    def setup_ui(self):
        # 1. SCANNER TOP COMPONENT
        self.scanner_frame = ctk.CTkFrame(self, fg_color="black", height=80, corner_radius=10)
        self.scanner_frame.pack(fill="x", padx=100, pady=20)
        
        self.canvas_scanner = tk.Canvas(self.scanner_frame, width=600, height=50, bg="black", highlightthickness=0)
        self.canvas_scanner.pack(expand=True, pady=10)
        
        self.scanner_segments = []
        for i in range(12): 
            rect = self.canvas_scanner.create_rectangle(i*50 + 5, 10, i*50 + 45, 40, fill="#330000", outline="#111")
            self.scanner_segments.append(rect)

        # 2. MAIN LAYOUT
        self.main_layout = ctk.CTkFrame(self, fg_color="transparent")
        self.main_layout.pack(fill="both", expand=True, padx=20)

        # Left Panel (System Status)
        self.left_panel = self.create_lateral_panel(self.main_layout, "LEFT", ["ALT", "OIL PRESS", "OIL TEMP", "EGT", "FUEL"], COLOR_GREEN)
        self.left_panel.pack(side="left", fill="y", padx=5)

        # Center Console
        self.center_console = ctk.CTkFrame(self.main_layout, fg_color="transparent")
        self.center_console.pack(side="left", fill="both", expand=True)

        # VOICE MODULE
        self.voice_frame = ctk.CTkFrame(self.center_console, fg_color=COLOR_PANEL_BG, border_color="#330000", border_width=2)
        self.voice_frame.pack(pady=20, padx=5)
        
        self.canvas_voice = tk.Canvas(self.voice_frame, width=320, height=450, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.canvas_voice.pack(padx=20, pady=20)
        
        self.led_rects = []
        self.led_glows = [] 
        
        spacing_x = 55
        led_h = 14
        led_w = 40
        
        for c in range(COLUMNS):
            col_rects = []
            col_glows = []
            x_start = 80 + (c * spacing_x)
            for i in range(LED_COUNT):
                y_start = 10 + (i * (led_h + 5))
                glow = self.canvas_voice.create_rectangle(x_start-4, y_start-2, x_start + led_w+4, y_start + led_h+2, 
                                                         fill=COLOR_PANEL_BG, outline="")
                rect = self.canvas_voice.create_rectangle(x_start, y_start, x_start + led_w, y_start + led_h, 
                                                         fill=COLOR_RED_OFF, outline="#111")
                col_rects.append(rect)
                col_glows.append(glow)
            self.led_rects.append(col_rects)
            self.led_glows.append(col_glows)

        # 3x3 CRUISE MODES (AUTHENTIC GRID)
        self.cruise_container = ctk.CTkFrame(self.center_console, fg_color="transparent")
        self.cruise_container.pack(pady=10, padx=5)
        
        # Grid Configuration
        for i in range(3): self.cruise_container.grid_rowconfigure(i, weight=1)
        for i in range(3): self.cruise_container.grid_columnconfigure(i, weight=0)

        # Row 0: NORMAL CRUISE
        self.btn_normal = self.create_cruise_row(self.cruise_container, 0, "NORMAL CRUISE", COLOR_GREY_BLOCK)
        # Row 1: AUTO CRUISE
        self.btn_auto = self.create_cruise_row(self.cruise_container, 1, "AUTO CRUISE", COLOR_GREY_BLOCK)
        # Row 2: PURSUIT
        self.btn_pursuit = self.create_cruise_row(self.cruise_container, 2, "PURSUIT", "green", bg_off=COLOR_PURSUIT_OFF)

        # Right Panel (Advanced Comms)
        self.right_panel = self.create_lateral_panel(self.main_layout, "RIGHT", ["AUX", "SAT COMM", "ACC", "RADAR", "MAI"], "#FF5555")
        self.right_panel.pack(side="right", fill="y", padx=5)

        # Footer Status - Using 2x2 Grid + Status Row
        self.footer = ctk.CTkFrame(self, fg_color="#050505", border_color="#222", border_width=2)
        self.footer.pack(fill="x", side="bottom", pady=20, padx=20)
        self.footer.columnconfigure(0, weight=1)
        self.footer.columnconfigure(1, weight=1)
        
        self.btn_music = ctk.CTkButton(self.footer, text="🎵 MUSIC", command=self.start_music, 
                                       fg_color="#222", hover_color="#333", font=("Courier", 16, "bold"), width=150, height=45)
        self.btn_music.grid(row=0, column=0, padx=5, pady=10, sticky="e")
        
        self.btn_mic = ctk.CTkButton(self.footer, text="🎤 MIC", command=self.start_mic, 
                                     fg_color="#222", hover_color="#333", font=("Courier", 16, "bold"), width=150, height=45)
        self.btn_mic.grid(row=0, column=1, padx=5, pady=10)
        
        self.btn_load = ctk.CTkButton(self.footer, text="📂 LOAD FILE", command=self.start_analyzer, 
                                     fg_color="#113311", hover_color="#224422", font=("Courier", 14, "bold"), width=150, height=45)
        self.btn_load.grid(row=0, column=2, padx=5, pady=10, sticky="w")
        
        self.btn_lock = ctk.CTkButton(self.footer, text="🔓 LOCK SIZE", command=self.toggle_window_lock, 
                                     fg_color="#111", border_color="#555", border_width=1, font=("Courier", 14, "bold"), width=160, height=45)
        self.btn_lock.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        
        self.btn_off = ctk.CTkButton(self.footer, text="⛔ STANDBY", command=self.stop_all, 
                                     fg_color="#440000", hover_color="#660000", font=("Courier", 16, "bold"), width=160, height=45)
        self.btn_off.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        self.btn_db = ctk.CTkButton(self.footer, text="💾 DATABASE", command=self.open_database, 
                                     fg_color="#CC8800", text_color="black", hover_color="#EEAA00", 
                                     font=("Courier", 14, "bold"), width=150, height=45)
        self.btn_db.grid(row=1, column=2, padx=5, pady=10, sticky="w")
        
        # Row 2: Sensitivity Control
        self.gain_lbl = ctk.CTkLabel(self.footer, text="VOICE SENSITIVITY:", font=("Courier", 12, "bold"), text_color="#777")
        self.gain_lbl.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="e")
        
        self.slider_gain = ctk.CTkSlider(self.footer, from_=0.1, to=10.0, number_of_steps=100, 
                                        command=self.update_gain, width=160, button_color=COLOR_RED_ON, progress_color="#440000")
        self.slider_gain.set(self.mic_gain)
        self.slider_gain.grid(row=2, column=1, padx=10, pady=(10, 0), sticky="w")
        
        self.status_lbl = ctk.CTkLabel(self.footer, text="SYSTEM STATUS: ONLINE", font=("Courier", 12), text_color="#555")
        self.status_lbl.grid(row=3, column=0, columnspan=2, pady=10)

    def update_gain(self, value):
        self.mic_gain = float(value)

    def create_lateral_panel(self, parent, side, labels, color):
        panel = ctk.CTkFrame(parent, fg_color=COLOR_PANEL_BG, corner_radius=10, border_color="#333", border_width=1)
        panel.columnconfigure(0, weight=1)
        for i, text in enumerate(labels):
            panel.rowconfigure(i, weight=1)
            formatted_text = text.replace(" ", "\n")
            btn = ctk.CTkButton(panel, text=formatted_text, fg_color="#111", border_color=color, border_width=1,
                               hover_color="#222", text_color=color, width=120, height=75, 
                               font=("Courier", 22, "bold"), anchor="center", command=self.synth.play_click)
            btn.grid(row=i, column=0, pady=25, padx=15, sticky="nsew")
        return panel

    def create_cruise_row(self, parent, row, text, color_indicator, bg_off="#333"):
        indicator = ctk.CTkLabel(parent, text="", width=25, height=60, fg_color=color_indicator, corner_radius=2)
        indicator.grid(row=row, column=0, padx=5, pady=5)
        spacer = ctk.CTkLabel(parent, text="", width=35, height=60, fg_color="black", corner_radius=2)
        spacer.grid(row=row, column=1, padx=5, pady=5)
        btn = ctk.CTkButton(parent, text=text, fg_color=bg_off, text_color="#777",
                           font=("Courier", 16, "bold"), width=150, height=60, corner_radius=5,
                           command=lambda: self.select_cruise_mode(row))
        btn.grid(row=row, column=2, padx=5, pady=5)
        btn._bg_off = bg_off
        return btn

    def select_cruise_mode(self, idx):
        if idx == 2: self.synth.play_pursuit()
        else: self.synth.play_click()
        btns = [self.btn_normal, self.btn_auto, self.btn_pursuit]
        for i, b in enumerate(btns):
            if i == idx:
                if i == 2: b.configure(fg_color=COLOR_RED_GLOW, text_color="white", border_color="white", border_width=2)
                else: b.configure(fg_color="white", text_color="black", border_color="white", border_width=2)
            else:
                b.configure(fg_color=b._bg_off, text_color="#777", border_width=0)

    def toggle_window_lock(self):
        self.synth.play_mode()
        is_resizable = self.resizable()
        if is_resizable[0]:
            self.resizable(False, False)
            self.btn_lock.configure(text="🔒 UNLOCK SIZE", fg_color="#330000")
        else:
            self.resizable(True, True)
            self.btn_lock.configure(text="🔓 LOCK SIZE", fg_color="#111")

    def animate_all(self):
        def loop():
            while True:
                self.scanner_pos += self.scanner_dir
                if self.scanner_pos >= 11 or self.scanner_pos <= 0: self.scanner_dir *= -1
                bands = [0, 0, 0]
                if self.current_mode == "music":
                    # Advanced "Heartbeat" Pulsator synced with theme BPM
                    t = time.time()
                    pulse1 = abs(math.sin(t * 7.7)) # Primary beat ~116 BPM
                    pulse2 = abs(math.sin(t * 15.4)) * 0.4 # Secondary syncopation
                    val = (pulse1 + pulse2) * 8
                    bands = [val * 0.6, val, val * 0.6]
                elif self.current_mode == "analyzer":
                    # Real Sync from v3.0 Voice Analyzer
                    target = self.mic_level # Driven by playback_callback
                    if target > self.v_smooth: self.v_smooth = target
                    else: self.v_smooth *= 0.8
                    val = self.v_smooth
                    bands = [val * 0.7, val, val * 0.7]
                elif self.current_mode == "mic":
                    # Smoothing / Decay logic for natural speech
                    target = self.mic_level
                    if target > self.v_smooth:
                        self.v_smooth = target # Fast attack
                    else:
                        self.v_smooth *= 0.85 # Slow decay (Fall-off)
                    
                    val = self.v_smooth
                    bands = [val * 0.7, val, val * 0.7]
                self.after(0, self.render_update, self.scanner_pos, bands)
                time.sleep(0.04)
        threading.Thread(target=loop, daemon=True).start()

    def render_update(self, scan_idx, voice_bands):
        for i, seg in enumerate(self.scanner_segments):
            if i == scan_idx: self.canvas_scanner.itemconfig(seg, fill=COLOR_RED_GLOW, outline=COLOR_RED_GLOW)
            elif abs(i - scan_idx) == 1: self.canvas_scanner.itemconfig(seg, fill="#B40522", outline="#440000")
            elif abs(i - scan_idx) == 2: self.canvas_scanner.itemconfig(seg, fill="#440000", outline="#220000")
            else: self.canvas_scanner.itemconfig(seg, fill="#110000", outline="#000")
        for i, val in enumerate(voice_bands):
            level = min(int(val), LED_COUNT)
            center = 9.5
            half = level / 2
            for j in range(LED_COUNT):
                rect = self.led_rects[i][j]
                glow = self.led_glows[i][j]
                if abs(j - center) < half:
                    self.canvas_voice.itemconfig(rect, fill=COLOR_RED_GLOW, outline=COLOR_RED_GLOW)
                    self.canvas_voice.itemconfig(glow, fill="#440000")
                else:
                    self.canvas_voice.itemconfig(rect, fill=COLOR_RED_OFF, outline="#111")
                    self.canvas_voice.itemconfig(glow, fill=COLOR_PANEL_BG)

    def stop_all(self, play_sound=True):
        if play_sound: self.synth.play_mode()
        self.current_mode = "off"
        self.audio_player.stop()
        if self.stream: self.stream.stop(); self.stream.close(); self.stream = None
        self.status_lbl.configure(text="SYSTEM: STANDBY", text_color="#777")
        self.btn_music.configure(fg_color="#222")
        self.btn_mic.configure(fg_color="#222")

    def start_music(self):
        try:
            self.synth.play_mode()
            self.stop_all(play_sound=False) # Prevent double beep
            self.current_mode = "music"
            res = self.audio_player.play(self.audio_file)
            if res == 0:
                self.status_lbl.configure(text="SYSTEM: MUSIC ENGINE ONLINE", text_color=COLOR_AMBER)
                self.btn_music.configure(fg_color="#CC8800")
            else:
                self.status_lbl.configure(text=f"MCI ERROR: {res}", text_color="red")
                self.current_mode = "off"
        except Exception as e:
            self.status_lbl.configure(text=f"SYS ERROR: {str(e)[:20]}", text_color="red")
            print(f"Error in start_music: {e}")

    def start_mic(self):
        self.synth.play_mode()
        self.stop_all(play_sound=False)
        try:
            self.stream = sd.InputStream(callback=self.audio_callback)
            self.stream.start()
            self.current_mode = "mic"
            self.status_lbl.configure(text="SYSTEM: VOICE SENSOR ONLINE", text_color=COLOR_GREEN)
            self.btn_mic.configure(fg_color="#006600")
        except:
            self.status_lbl.configure(text="ERROR: MICROPHONE NOT FOUND", text_color="red")

    def start_analyzer(self):
        self.stop_all()
        # Clean file path handling (Native Windows dialog)
        file_path_raw = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
        if not file_path_raw: return
        
        # v3.2: Path Normalization (Solves accents and special characters)
        file_path = Path(file_path_raw).resolve()
        
        try:
            self.status_lbl.configure(text=f"ANALYZING: {file_path.name[:20]}...", text_color=COLOR_AMBER)
            
            # v3.2 Multi-Engine Strategy:
            # 1. Primary Decode (Standard)
            try:
                decoded = miniaudio.decode_file(str(file_path), sample_rate=44100, nchannels=1)
            except:
                # 2. Rescue Engine (Binary stream)
                # This bypasses path-encoding bugs in underlying C libraries
                with open(file_path, "rb") as f:
                    bin_data = f.read()
                decoded = miniaudio.decode(bin_data, sample_rate=44100, nchannels=1)
                self.status_lbl.configure(text="RECOVERY: BINARY STREAM OK", text_color="cyan")
            
            # Convert to float32 normalized buffer
            self.playback_data = np.frombuffer(decoded.samples, dtype=np.int16).astype(np.float32) / 32768.0
            
            self.playback_idx = 0
            self.current_mode = "analyzer"
            self.btn_load.configure(fg_color="#006600")
            
            # Use Fixed 44100Hz for maximum stability on all Windows drivers
            self.stream = sd.OutputStream(samplerate=44100, channels=1, callback=self.analyzer_callback)
            self.stream.start()
        except MemoryError:
            self.status_lbl.configure(text="ERR: FILE TOO LARGE", text_color="red")
        except Exception as e:
            full_err = str(e)
            print(f"Detailed Analyzer Error: {full_err}")
            self.status_lbl.configure(text=f"ERR: {full_err[:25]}...", text_color="red")
            self.current_mode = "off"

    def analyzer_callback(self, outdata, frames, time, status):
        if self.playback_idx < len(self.playback_data):
            chunk = self.playback_data[self.playback_idx : self.playback_idx + frames]
            if len(chunk) < frames: chunk = np.pad(chunk, (0, frames - len(chunk)))
            
            # 1. Output sound
            outdata[:] = chunk.reshape(-1, 1)
            # 2. Extract Volume with Neural Compression (Perfect Sync)
            # We use the same logarithmic scaling as the mic for consistency
            rms = np.linalg.norm(chunk) * 25 * self.mic_gain
            compressed = np.log1p(rms * 40) / np.log1p(40)
            self.mic_level = min(compressed * 18, LED_COUNT)
            
            self.playback_idx += frames
        else:
            self.current_mode = "off"
            raise sd.CallbackStop

    def audio_callback(self, indata, frames, time, status):
        # Neural Speech Filter: 
        # 1. Root-Mean-Square (Volume)
        rms = np.linalg.norm(indata) * self.mic_gain
        # 2. Logarithmic Compression (Makes quiet speech very visible)
        # v = log1p(rms * weight) / log1p(weight) 
        compressed = np.log1p(rms * 40) / np.log1p(40)
        # 3. Output Scale (to LED count)
        self.mic_level = min(compressed * 18, LED_COUNT)

    def open_database(self):
        self.synth.play_mode()
        db_path = os.path.abspath("personajes.html")
        if os.path.exists(db_path):
            webbrowser.open(f"file:///{db_path}")
        else:
            self.status_lbl.configure(text="ERR: DATABASE NOT FOUND", text_color="red")

if __name__ == "__main__":
    app = KittDashboard()
    app.mainloop()
