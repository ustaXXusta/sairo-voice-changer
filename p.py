import tkinter as tk
from tkinter import ttk, messagebox
import sounddevice as sd
import numpy as np
import librosa
import scipy.io.wavfile as wavfile
import parselmouth
import os
import json
from datetime import datetime
from threading import Thread
import time
import logging

# Logging ayarları
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Klasörler ve preset dosyası
BASE_DIR = os.getcwd()
RECORDED_DIR = os.path.join(BASE_DIR, "recorded")
EDITED_DIR = os.path.join(BASE_DIR, "edited")
PRESET_FILE = os.path.join(BASE_DIR, "presets.txt")
os.makedirs(RECORDED_DIR, exist_ok=True)
os.makedirs(EDITED_DIR, exist_ok=True)

class VoiceChangerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Changer")
        self.root.geometry("520x720")
        self.root.resizable(False, False)
        self.padding = 10
        
        self.canvas = tk.Canvas(root, width=520, height=720)
        self.canvas.pack(fill="both", expand=True)
        self.create_gradient()
        
        self.samplerate = 44100
        self.recording = False
        self.paused = False
        self.audio_data = None
        self.editing = False  # Add editing flag
        
        tk.Label(root, text="☁️ Sairo Voice Changer", font=("Arial", 16, "bold"), bg="#2a2a72").place(x=20, y=20)
        
        tk.Label(root, text="Record Duration (seconds):", bg="#2a2a72", fg="white").place(x=20, y=60)
        self.duration_var = tk.StringVar(value="5")
        tk.Entry(root, textvariable=self.duration_var, width=10).place(x=200, y=60)
        
        tk.Button(root, text="Record Audio", command=self.start_recording).place(x=20, y=100)
        tk.Button(root, text="Pause", command=self.pause_recording).place(x=150, y=100)
        tk.Button(root, text="Stop", command=self.stop_recording).place(x=230, y=100)
        
        tk.Label(root, text="Recording Timer:", bg="#2a2a72", fg="white").place(x=20, y=140)
        self.timer_label = tk.Label(root, text="00:00 / 00:05", font=("Arial", 12), bg="#2a2a72", fg="white")
        self.timer_label.place(x=20, y=160)
        
        tk.Label(root, text="Select Recorded Audio:", bg="#2a2a72", fg="white").place(x=20, y=200)
        self.audio_var = tk.StringVar()
        self.audio_dropdown = ttk.Combobox(root, textvariable=self.audio_var, state="readonly", width=30)
        self.audio_dropdown.place(x=20, y=220)
        self.update_audio_list()
        
        tk.Label(root, text="Select/Save Preset:", bg="#2a2a72", fg="white").place(x=20, y=260)
        self.preset_var = tk.StringVar()
        self.preset_dropdown = ttk.Combobox(root, textvariable=self.preset_var, state="readonly", width=25)
        self.preset_dropdown.place(x=20, y=280)
        tk.Button(root, text="X", command=self.delete_preset, width=3).place(x=220, y=280)
        tk.Button(root, text="Save Preset", command=self.save_preset).place(x=260, y=280)
        self.update_preset_list()
        
        settings = [
            ("Pitch Shift (semitones)", -5, 5, 0.5, "Adjusts voice pitch (higher/lower tone)"),
            ("Formant Shift (ratio)", 0.5, 2.0, 0.1, "Modifies vocal tract resonance"),
            ("Tempo (rate)", 0.5, 2.0, 0.1, "Changes speech speed"),
            ("Timbre (distortion)", 0.0, 0.5, 0.05, "Adds roughness to voice"),
            ("Volume (gain)", 0.5, 2.0, 0.1, "Adjusts loudness")
        ]
        self.scales = {}
        for i, (label, min_val, max_val, res, tooltip) in enumerate(settings):
            tk.Label(root, text=label, bg="#2a2a72", fg="white").place(x=20, y=320 + i*60)
            scale = tk.Scale(root, from_=min_val, to=max_val, orient=tk.HORIZONTAL, resolution=res, length=300)
            if label == "Pitch Shift (semitones)":
                scale.set(0)
            else:
                scale.set(1.0 if label != "Timbre (distortion)" else 0.0)
            scale.place(x=20, y=340 + i*60)
            self.create_tooltip(scale, tooltip)
            self.scales[label] = scale
        
        tk.Button(root, text="Edit and Save", command=self.start_editing).place(x=20, y=620)
        
        tk.Label(root, text="Editing Progress:", bg="#2a2a72", fg="white").place(x=20, y=660)
        self.edit_progress = ttk.Progressbar(root, length=300, mode="determinate")
        self.edit_progress.place(x=20, y=680)
    
    def create_gradient(self):
        for i in range(720):
            r = int(42 + (i/720) * (100-42))
            g = int(42 + (i/720) * (100-42))
            b = int(114 + (i/720) * (200-114))
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas.create_line(0, i, 520, i, fill=color)
    
    def create_tooltip(self, widget, text):
        tooltip = tk.Toplevel(self.root)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry("+1000+1000")
        label = tk.Label(tooltip, text=text, background="yellow", relief="solid", borderwidth=1)
        label.pack()
        
        def show(event):
            x, y = event.widget.winfo_rootx() + 20, event.widget.winfo_rooty() + 20
            tooltip.wm_geometry(f"+{x}+{y}")
        
        def hide(event):
            tooltip.wm_geometry("+1000+1000")
        
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)
    
    def update_audio_list(self):
        audio_files = [f for f in os.listdir(RECORDED_DIR) if f.endswith(".wav")]
        self.audio_dropdown["values"] = audio_files
        if audio_files:
            self.audio_var.set(audio_files[0])
    
    def update_preset_list(self):
        if os.path.exists(PRESET_FILE):
            with open(PRESET_FILE, "r") as f:
                presets = [line.split(":")[0] for line in f.readlines()]
            self.preset_dropdown["values"] = presets
            if presets:
                self.preset_var.set(presets[0])
    
    def save_preset(self):
        preset_name = f"preset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        settings = {key: scale.get() for key, scale in self.scales.items()}
        with open(PRESET_FILE, "a") as f:
            f.write(f"{preset_name}:{json.dumps(settings)}\n")
        self.update_preset_list()
        messagebox.showinfo("Success", "Preset saved!")
    
    def delete_preset(self):
        preset_name = self.preset_var.get()
        if not preset_name:
            messagebox.showwarning("Warning", "Select a preset to delete!")
            return
        if os.path.exists(PRESET_FILE):
            with open(PRESET_FILE, "r") as f:
                lines = f.readlines()
            with open(PRESET_FILE, "w") as f:
                for line in lines:
                    if not line.startswith(preset_name + ":"):
                        f.write(line)
            self.update_preset_list()
            messagebox.showinfo("Success", "Preset deleted!")
    
    def start_recording(self):
        try:
            duration = float(self.duration_var.get())
            if duration <= 0:
                raise ValueError("Duration must be positive!")
            self.recording = True
            self.paused = False
            self.audio_data = None
            Thread(target=self.record_audio, args=(duration,)).start()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid duration!")
    
    def record_audio(self, duration):
        logging.debug("Recording started")
        start_time = time.time()
        self.audio_data = sd.rec(int(duration * self.samplerate), samplerate=self.samplerate, channels=1, dtype='float32')
        while self.recording and (time.time() - start_time) < duration:
            if not self.paused:
                elapsed = time.time() - start_time
                self.root.after(10, self.update_timer, elapsed, duration)
            else:
                start_time += 0.01
            time.sleep(0.01)
        sd.wait()
        if self.recording:
            self.stop_recording()
    
    def update_timer(self, elapsed, duration):
        elapsed_secs = int(elapsed)
        total_secs = int(duration)
        elapsed_str = f"{elapsed_secs//60:02d}:{elapsed_secs%60:02d}"
        total_str = f"{total_secs//60:02d}:{total_secs%60:02d}"
        self.timer_label.config(text=f"{elapsed_str} / {total_str}")
    
    def pause_recording(self):
        if self.recording:
            self.paused = not self.paused
            messagebox.showinfo("Info", "Recording paused" if self.paused else "Recording resumed")
    
    def stop_recording(self):
        if self.recording:
            self.recording = False
            if self.audio_data is not None:
                logging.debug("Saving recorded audio")
                recording = np.clip(self.audio_data, -1.0, 1.0)
                recording = (recording * 32767).astype(np.int16)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(RECORDED_DIR, f"record_{timestamp}.wav")
                wavfile.write(filename, self.samplerate, recording)
                self.update_audio_list()
                messagebox.showinfo("Success", "Audio recorded!")
            self.timer_label.config(text=f"00:00 / {int(float(self.duration_var.get()))//60:02d}:{int(float(self.duration_var.get()))%60:02d}")
            self.audio_data = None
    
    def update_progress(self, value):
        """Thread-safe progress update"""
        self.edit_progress["value"] = value
        self.root.update_idletasks()
    
    def start_editing(self):
        if self.editing:
            messagebox.showwarning("Warning", "Editing already in progress!")
            return
            
        selected_file = self.audio_var.get()
        if not selected_file:
            messagebox.showwarning("Warning", "Select an audio file!")
            return
            
        logging.debug(f"Starting edit for file: {selected_file}")
        self.editing = True
        self.edit_progress["value"] = 0
        Thread(target=self.edit_audio).start()
    
    def edit_audio(self):
        try:
            self.root.after(0, lambda: self.update_progress(0))
            self.edit_progress["maximum"] = 6
            selected_file = self.audio_var.get()
            input_path = os.path.join(RECORDED_DIR, selected_file)
            
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Audio file not found: {input_path}")
            
            logging.debug("Loading audio file")
            y, sr = librosa.load(input_path, sr=self.samplerate)
            self.root.after(0, lambda: self.update_progress(1))
            
            # Apply pitch shift
            pitch_shift = self.scales["Pitch Shift (semitones)"].get()
            logging.debug(f"Applying pitch shift: {pitch_shift}")
            if pitch_shift != 0:
                y = librosa.effects.pitch_shift(y, sr=sr, n_steps=pitch_shift)
            self.root.after(0, lambda: self.update_progress(2))
            
            # Apply formant shift using parselmouth (proper implementation)
            formant_shift = self.scales["Formant Shift (ratio)"].get()
            logging.debug(f"Applying formant shift: {formant_shift}")
            if formant_shift != 1.0:
                try:
                    # Convert to parselmouth Sound object
                    snd = parselmouth.Sound(y, sampling_frequency=sr)
                    # Change formant frequencies
                    manipulated = snd.lengthen(formant_shift)
                    y = manipulated.values[0]  # Get the audio data back
                except Exception as e:
                    logging.warning(f"Formant shift failed, skipping: {e}")
            self.root.after(0, lambda: self.update_progress(3))
            
            # Apply tempo change
            tempo_shift = self.scales["Tempo (rate)"].get()
            logging.debug(f"Applying tempo shift: {tempo_shift}")
            if tempo_shift != 1.0:
                y = librosa.effects.time_stretch(y, rate=tempo_shift)
            self.root.after(0, lambda: self.update_progress(4))
            
            # Apply timbre distortion
            distortion = self.scales["Timbre (distortion)"].get()
            logging.debug(f"Applying distortion: {distortion}")
            if distortion > 0:
                # Add controlled distortion
                y_distorted = np.tanh(y * (1 + distortion * 5))  # Soft clipping distortion
                y = y * (1 - distortion) + y_distorted * distortion
            self.root.after(0, lambda: self.update_progress(5))
            
            # Apply volume gain
            volume_gain = self.scales["Volume (gain)"].get()
            logging.debug(f"Applying volume gain: {volume_gain}")
            if volume_gain != 1.0:
                y = y * volume_gain
            
            # Normalize and clip to prevent clipping
            y = np.clip(y, -1.0, 1.0)
            
            # Save the edited audio
            logging.debug("Saving edited audio")
            output_filename = f"edited_{selected_file}"
            output_path = os.path.join(EDITED_DIR, output_filename)
            
            # Convert to int16 for saving
            y_int = (y * 32767).astype(np.int16)
            wavfile.write(output_path, sr, y_int)
            
            self.root.after(0, lambda: self.update_progress(6))
            
            # Show success message
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Edited audio saved as {output_filename}!"))
            logging.debug("Editing completed successfully")
            
        except Exception as e:
            logging.error(f"Editing failed: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Editing failed: {str(e)}"))
        
        finally:
            self.editing = False
            self.root.after(0, lambda: self.update_progress(0))

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceChangerApp(root)
    root.mainloop()