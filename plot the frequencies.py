import numpy as np
import sounddevice as sd
from scipy.signal import firwin, lfilter
from scipy.fft import fft, fftfreq
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import pandas as pd
from datetime import datetime

# Matplotlib Imports for Plotting in Tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Global Constants
fs = 44100  # sampling rate

# ==========================================================
# 	SIGNAL GENERATORS
# ==========================================================

def sine_wave(duration, freq, amp=0.5):
    """Generates a pure sine wave."""
    t = np.linspace(0, duration, int(fs * duration), False)
    return amp * np.sin(2 * np.pi * freq * t)

def white_noise(duration, amp=0.3):
    """Generates White Gaussian Noise (flat power spectrum)."""
    N = int(fs * duration)
    return amp * np.random.randn(N)

def pink_noise(duration, amp=0.3):
    """Generates Pink Noise (power spectral density proportional to 1/f)."""
    N = int(fs * duration)
    # A simple, relatively efficient approximation of pink noise
    rows = 16
    array = np.random.randn(rows, N)
    # Cumulative sum creates the 1/f characteristic (integrated white noise)
    pink = np.sum(np.cumsum(array, axis=1), axis=0)
    pink = pink / np.max(np.abs(pink))
    return amp * pink

def band_limited_noise(duration, low, high, amp=0.3):
    """Generates band-limited white noise using an FIR filter."""
    N = int(fs * duration)
    noise = np.random.randn(N)

    # Use a 1024-tap FIR bandpass filter
    b = firwin(1024, [low, high], pass_zero=False, fs=fs)
    band = lfilter(b, 1, noise)
    band = band / np.max(np.abs(band))

    return amp * band

# ==========================================================
# 	SELECT + CREATE SIGNAL
# ==========================================================

def create_signal(noise_type, duration, freq):
    """Factory function to create the requested signal."""
    if noise_type == "None":
        return np.zeros(int(fs * duration))
    elif noise_type == "Pure Sine Wave":
        return sine_wave(duration, freq)
    elif noise_type == "White Gaussian Noise":
        return white_noise(duration)
    elif noise_type == "Pink Noise":
        return pink_noise(duration)
    elif noise_type == "Band-Limited Noise":
        # Ensure a reasonable bandwidth around the center frequency
        low = max(10, freq - 1000)
        high = freq + 1000
        return band_limited_noise(duration, low, high)
    
    return np.zeros(int(fs * duration))

# ==========================================================
# 	SIGNAL ANALYSIS & PLOTTING
# ==========================================================

def analyze_signal(signal, signal_type, freq):
    """Calculates key statistical and spectral metrics."""
    if np.sum(np.abs(signal)) == 0:
        return {
            'Mean': 0.0,
            'RMS': 0.0,
            'Noise RMS': 0.0,
            'SNR (dB)': 'N/A'
        }

    # 1. Mean
    mean_val = np.mean(signal)
    
    # 2. RMS (Root Mean Square) - Total signal power
    rms_val = np.sqrt(np.mean(signal**2))
    
    # 3. Noise RMS (A simplified approach for generated signals)
    if signal_type == "Pure Sine Wave":
        # Assume negligible noise for a generated pure sine wave
        noise_rms_val = 0.0
        # If we had a measurement, we'd estimate noise by filtering out the fundamental.
    else:
        # For noise signals, the entire signal IS the noise
        noise_rms_val = rms_val

    # 4. SNR (Signal-to-Noise Ratio)
    # For a purely generated signal (sine or noise), defining SNR is tricky.
    # We'll report 'Inf' for the pure sine wave and 'N/A' for pure noise types
    # as the signal and noise are fundamentally the same component.
    if signal_type == "Pure Sine Wave":
        snr_db = 'Inf'
    else:
        # Note: SNR is best calculated when measuring a pure tone against background noise.
        snr_db = 'N/A' 
        
    # 5. FFT (Frequency-Domain)
    N = len(signal)
    yf = fft(signal)
    xf = fftfreq(N, 1 / fs)
    
    # Take the magnitude of the positive frequencies
    positive_freqs_mask = xf > 0
    xf_pos = xf[positive_freqs_mask]
    yf_pos = 2.0/N * np.abs(yf[positive_freqs_mask]) # Scaling for single-sided spectrum
    
    # Convert to dB magnitude (for better observation of noise floor)
    mag_db = 20 * np.log10(yf_pos + 1e-10) # Add epsilon to avoid log(0)

    return {
        'Mean': mean_val,
        'RMS': rms_val,
        'Noise RMS': noise_rms_val,
        'SNR (dB)': snr_db,
        'xf_pos': xf_pos,
        'mag_db': mag_db
    }

def plot_signal(signal, analysis_results, fig, axes, title):
    """Plots the time-domain waveform and the frequency spectrum."""
    t = np.linspace(0, len(signal)/fs, len(signal), endpoint=False)
    
    # Clear previous plots
    for ax in axes:
        ax.clear()

    # --- Plot 1: Time Domain ---
    axes[0].plot(t, signal, color='#3498db')
    axes[0].set_title(f'Time Domain Waveform: {title}', fontsize=10)
    axes[0].set_xlabel('Time (s)', fontsize=8)
    axes[0].set_ylabel('Amplitude', fontsize=8)
    axes[0].grid(True, linestyle='--', alpha=0.6)
    axes[0].tick_params(axis='both', which='major', labelsize=7)
    axes[0].set_xlim(0, 0.02) # Zoom into the first 20ms for visibility

    # --- Plot 2: Frequency Domain (FFT) ---
    axes[1].plot(analysis_results['xf_pos'], analysis_results['mag_db'], color='#e74c3c', linewidth=1)
    axes[1].set_title(f'Frequency Spectrum (FFT): {title}', fontsize=10)
    axes[1].set_xlabel('Frequency (Hz)', fontsize=8)
    axes[1].set_ylabel('Magnitude (dB)', fontsize=8)
    axes[1].grid(True, linestyle='--', alpha=0.6)
    axes[1].tick_params(axis='both', which='major', labelsize=7)
    axes[1].set_xlim(0, fs/2)
    axes[1].set_ylim(-120, 0) # Set a consistent dB range

    fig.tight_layout()
    canvas.draw()
    
# ==========================================================
# 	PLAY TWO SIGNALS TOGETHER (WITH ANALYSIS)
# ==========================================================

def play_both():
    """Generates both signals, analyzes the first one, plots, and plays the mix."""
    try:
        duration = float(entry_duration.get())
        freq1 = float(entry_freq1.get())
        freq2 = float(entry_freq2.get())
        type1 = combo_noise1.get()
        type2 = combo_noise2.get()

        # 1. Generate Signals
        s1 = create_signal(type1, duration, freq1)
        s2 = create_signal(type2, duration, freq2)

        # 2. Analyze Signal 1 (The primary one for plotting)
        analysis1 = analyze_signal(s1, type1, freq1)
        
        # 3. Update Analysis Display for Signal 1
        update_analysis_display(analysis1, type1, freq1)

        # 4. Plot Signal 1
        if np.sum(np.abs(s1)) > 0:
            plot_signal(s1, analysis1, fig, axes, f"{type1} ({freq1} Hz)")
        else:
            # Clear plots if no signal is selected
            for ax in axes:
                ax.clear()
            fig.canvas.draw()


        # 5. Mix and Play
        final_signal = s1 + s2
        
        sd.stop()
        # Scale the signal to prevent clipping after mixing
        max_amp = np.max(np.abs(final_signal))
        if max_amp > 1.0:
            final_signal /= max_amp
            
        sd.play(final_signal, fs)
        
    except ValueError:
        messagebox.showerror("Input Error", "Please ensure all frequency and duration fields contain valid numbers.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during playback/analysis: {str(e)}")


def update_analysis_display(results, sig_type, freq):
    """Updates the Tkinter labels with the computed metrics."""
    analysis_frame_title.config(text=f"Analysis for Signal 1: {sig_type} @ {freq} Hz")
    
    # Format float results to 4 decimal places, keep strings as-is
    mean_text = f"{results['Mean']:.4f}"
    rms_text = f"{results['RMS']:.4f}"
    noise_rms_text = f"{results['Noise RMS']:.4f}"
    snr_text = str(results['SNR (dB)'])

    label_mean.config(text=f"Mean: {mean_text}")
    label_rms.config(text=f"RMS: {rms_text}")
    label_noise_rms.config(text=f"Noise RMS: {noise_rms_text}")
    label_snr.config(text=f"SNR (dB): {snr_text}")

def stop_sound():
    """Stops any currently playing audio."""
    sd.stop()

# ==========================================================
# 	READ FROM ARDUINO (5 SECONDS)
# ==========================================================

def record_from_arduino():
    """Records serial data from Arduino and saves it to a CSV file."""
    try:
        port = entry_port.get()
        baud = 115200

        ser = serial.Serial(port, baud, timeout=1)
        print("Waiting for START...")
        
        # wait for Arduino START signal
        while True:
            line = ser.readline().decode().strip()
            if line == "START":
                break

        samples = []
        
        # read until END signal
        while True:
            line = ser.readline().decode().strip()
            if line == "END":
                break

            if line.isdigit():
                samples.append(int(line))

        ser.close()

        # Save CSV
        filename = "capture_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
        pd.DataFrame(samples, columns=["ADC Value"]).to_csv(filename, index=False)

        messagebox.showinfo("Saved", f"Data capture saved as: {filename}")

    except serial.SerialException as e:
        messagebox.showerror("Serial Error", f"Could not connect or read from COM port {port}. Please check the port and baud rate.\nDetails: {str(e)}")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred during recording: {str(e)}")


# ==========================================================
# 	BUILD GUI
# ==========================================================

root = tk.Tk()
root.title("Acoustic Signal Analyzer & Arduino Recorder")
# Increase initial size to accommodate the plots
root.geometry("1000x800")
root.resizable(True, True)

# Main Container using PanedWindow for adjustable separation
main_pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
main_pane.pack(fill=tk.BOTH, expand=1, padx=10, pady=10)

# -------------------------
# Control Panel Frame (Left Side)
# -------------------------
control_frame = ttk.Frame(main_pane, padding="10 10 10 10")
main_pane.add(control_frame, weight=0)

# Title
tk.Label(control_frame, text="Signal Generation Controls", font=("Arial", 14, "bold")).pack(pady=10)

# --- Signal 1 Controls ---
ttk.Label(control_frame, text="--- Signal 1 ---", font=("Arial", 11, "underline")).pack(pady=(5, 0))
tk.Label(control_frame, text="Noise Type 1", font=("Arial", 10)).pack()
noise_options = ["None", "Pure Sine Wave", "White Gaussian Noise",
                 "Pink Noise", "Band-Limited Noise"]

combo_noise1 = ttk.Combobox(control_frame, values=noise_options, state="readonly", width=30)
combo_noise1.current(2) # Default to White Noise for easy comparison
combo_noise1.pack(pady=5)

tk.Label(control_frame, text="Frequency 1 (Hz) [Used for Sine/Band-Limited]", font=("Arial", 10)).pack()
entry_freq1 = tk.Entry(control_frame, width=33)
entry_freq1.insert(0, "1000")
entry_freq1.pack(pady=5)

# --- Signal 2 Controls ---
ttk.Label(control_frame, text="--- Signal 2 ---", font=("Arial", 11, "underline")).pack(pady=(15, 0))
tk.Label(control_frame, text="Noise Type 2", font=("Arial", 10)).pack()
combo_noise2 = ttk.Combobox(control_frame, values=noise_options, state="readonly", width=30)
combo_noise2.current(0)
combo_noise2.pack(pady=5)

tk.Label(control_frame, text="Frequency 2 (Hz) [Used for Sine/Band-Limited]", font=("Arial", 10)).pack()
entry_freq2 = tk.Entry(control_frame, width=33)
entry_freq2.insert(0, "500")
entry_freq2.pack(pady=5)


# --- Global Duration ---
tk.Label(control_frame, text="Duration (seconds)", font=("Arial", 11)).pack(pady=(15, 0))
entry_duration = tk.Entry(control_frame, width=33)
entry_duration.insert(0, "2")
entry_duration.pack(pady=5)


# --- Play/Stop Buttons ---
tk.Button(control_frame, text="ANALYZE & PLAY MIXED SIGNAL",
          command=play_both, width=30, bg='#2ecc71', fg='white', font=('Arial', 10, 'bold')).pack(pady=15)

tk.Button(control_frame, text="STOP SOUND", command=stop_sound,
          width=30, bg='#e74c3c', fg='white').pack(pady=5)


# --- Arduino Recorder Section ---
ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)
tk.Label(control_frame, text="Arduino Data Recorder", font=("Arial", 14, "bold")).pack(pady=5)
tk.Label(control_frame, text="COM Port (e.g., COM5 or /dev/ttyACM0)", font=("Arial", 10)).pack()
entry_port = tk.Entry(control_frame, width=33)
entry_port.insert(0, "COM3")    # default placeholder
entry_port.pack(pady=5)

tk.Button(control_frame, text="RECORD DATA FROM ARDUINO",
          command=record_from_arduino, width=30, bg='#3498db', fg='white', font=('Arial', 10, 'bold')).pack(pady=20)


# -------------------------
# Plotting and Analysis Frame (Right Side)
# -------------------------
plot_analysis_frame = ttk.Frame(main_pane, padding="10 10 10 10")
main_pane.add(plot_analysis_frame, weight=1)

# Analysis Metrics Display
analysis_frame = ttk.LabelFrame(plot_analysis_frame, text="Signal 1 Metrics", padding="10")
analysis_frame.pack(fill='x', pady=5)

analysis_frame_title = tk.Label(analysis_frame, text="Analysis for Signal 1: Not yet analyzed", font=("Arial", 12, "bold"))
analysis_frame_title.pack(anchor='w')

label_mean = tk.Label(analysis_frame, text="Mean: 0.0", anchor='w')
label_mean.pack(fill='x')
label_rms = tk.Label(analysis_frame, text="RMS: 0.0", anchor='w')
label_rms.pack(fill='x')
label_noise_rms = tk.Label(analysis_frame, text="Noise RMS: 0.0", anchor='w')
label_noise_rms.pack(fill='x')
label_snr = tk.Label(analysis_frame, text="SNR (dB): N/A", anchor='w')
label_snr.pack(fill='x')

# Matplotlib Figure Setup
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(6, 6))
plt.subplots_adjust(hspace=0.4)
fig.set_facecolor('#f0f0f0') # Match Tkinter background

# Initial plot display setup
for ax in axes:
    ax.set_title("Ready for Analysis", fontsize=10)
    ax.set_xlabel('Time/Frequency', fontsize=8)
    ax.set_ylabel('Amplitude/dB', fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.grid(True, linestyle='--', alpha=0.6)

canvas = FigureCanvasTkAgg(fig, master=plot_analysis_frame)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=1, pady=10)


# ==========================================================
# 	MAIN LOOP
# ==========================================================
root.mainloop()

# Note on serial: You must have the 'pyserial' library installed (`pip install pyserial`) 
# and your Arduino must be sending "START", data lines (as integers), and "END" 
# signals to match the recording logic.
