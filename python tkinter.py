import numpy as np
import sounddevice as sd
from scipy.signal import firwin, lfilter
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import pandas as pd
from datetime import datetime

fs = 44100  # sampling rate


# ==========================================================
#                SIGNAL GENERATORS
# ==========================================================

def sine_wave(duration, freq, amp=0.5):
    t = np.linspace(0, duration, int(fs * duration), False)
    return amp * np.sin(2 * np.pi * freq * t)


def white_noise(duration, amp=0.3):
    N = int(fs * duration)
    return amp * np.random.randn(N)


def pink_noise(duration, amp=0.3):
    N = int(fs * duration)
    rows = 16
    array = np.random.randn(rows, N)
    pink = np.sum(np.cumsum(array, axis=1), axis=0)
    pink = pink / np.max(np.abs(pink))
    return amp * pink


def band_limited_noise(duration, low, high, amp=0.3):
    N = int(fs * duration)
    noise = np.random.randn(N)

    b = firwin(1024, [low, high], pass_zero=False, fs=fs)
    band = lfilter(b, 1, noise)
    band = band / np.max(np.abs(band))

    return amp * band


# ==========================================================
#                SELECT + CREATE SIGNAL
# ==========================================================

def create_signal(noise_type, duration, freq):
    if noise_type == "None":
        return np.zeros(int(fs * duration))

    elif noise_type == "Pure Sine Wave":
        return sine_wave(duration, freq)

    elif noise_type == "White Gaussian Noise":
        return white_noise(duration)

    elif noise_type == "Pink Noise":
        return pink_noise(duration)

    elif noise_type == "Band-Limited Noise":
        low = max(10, freq - 1000)
        high = freq + 1000
        return band_limited_noise(duration, low, high)

    return np.zeros(int(fs * duration))


# ==========================================================
#                PLAY TWO SIGNALS TOGETHER
# ==========================================================

def play_both():
    duration = float(entry_duration.get())
    freq1 = float(entry_freq1.get())
    freq2 = float(entry_freq2.get())
    type1 = combo_noise1.get()
    type2 = combo_noise2.get()

    s1 = create_signal(type1, duration, freq1)
    s2 = create_signal(type2, duration, freq2)

    final_signal = s1 + s2

    sd.stop()
    sd.play(final_signal, fs)


def stop_sound():
    sd.stop()


# ==========================================================
#                READ FROM ARDUINO (5 SECONDS)
# ==========================================================

def record_from_arduino():
    try:
        port = entry_port.get()
        baud = 115200

        ser = serial.Serial(port, baud, timeout=1)
        print("Waiting for START...")

        # wait for Arduino START
        while True:
            line = ser.readline().decode().strip()
            if line == "START":
                break

        samples = []

        # read until END
        while True:
            line = ser.readline().decode().strip()
            if line == "END":
                break

            if line.isdigit():
                samples.append(int(line))

        ser.close()

        # Save CSV
        filename = "capture_" + datetime.now().strftime("%H%M%S") + ".csv"
        pd.DataFrame(samples, columns=["ADC"]).to_csv(filename, index=False)

        messagebox.showinfo("Saved", f"Saved as: {filename}")

    except Exception as e:
        messagebox.showerror("Error", str(e))


# ==========================================================
#                BUILD GUI
# ==========================================================

root = tk.Tk()
root.title("Noise Producer + Arduino Recorder")
root.geometry("480x550")


# -------------------------
# Noise Type 1
# -------------------------
tk.Label(root, text="Noise Type 1", font=("Arial", 12)).pack()
noise_options = ["None", "Pure Sine Wave", "White Gaussian Noise",
                 "Pink Noise", "Band-Limited Noise"]

combo_noise1 = ttk.Combobox(root, values=noise_options, state="readonly")
combo_noise1.current(0)
combo_noise1.pack(pady=5)

tk.Label(root, text="Frequency 1 (Hz)", font=("Arial", 12)).pack()
entry_freq1 = tk.Entry(root)
entry_freq1.insert(0, "1000")
entry_freq1.pack(pady=5)


# -------------------------
# Noise Type 2
# -------------------------
tk.Label(root, text="Noise Type 2", font=("Arial", 12)).pack()
combo_noise2 = ttk.Combobox(root, values=noise_options, state="readonly")
combo_noise2.current(0)
combo_noise2.pack(pady=5)

tk.Label(root, text="Frequency 2 (Hz)", font=("Arial", 12)).pack()
entry_freq2 = tk.Entry(root)
entry_freq2.insert(0, "500")
entry_freq2.pack(pady=5)


# -------------------------
# Duration
# -------------------------
tk.Label(root, text="Duration (seconds)", font=("Arial", 12)).pack()
entry_duration = tk.Entry(root)
entry_duration.insert(0, "2")
entry_duration.pack(pady=5)


# -------------------------
# PLAY BUTTONS
# -------------------------
tk.Button(root, text="PLAY MIXED SIGNAL",
          command=play_both, width=25).pack(pady=10)

tk.Button(root, text="STOP", command=stop_sound,
          width=15).pack(pady=5)


# -------------------------
# Arduino Recorder
# -------------------------
tk.Label(root, text="\nArduino COM Port", font=("Arial", 12)).pack()
entry_port = tk.Entry(root)
entry_port.insert(0, "COM5")   # default
entry_port.pack(pady=5)

tk.Button(root, text="RECORD FROM ARDUINO (5 sec)",
          command=record_from_arduino, width=30).pack(pady=20)


root.mainloop()
