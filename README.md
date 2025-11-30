
1)Noise Generator & Recorder UI (Python)
-----------------------------------
This Python application provides a simple UI to generate signals, record 5-second audio samples, and save them as CSV files.
It’s designed for easy data collection for noise analysis, machine learning, or signal processing experiments.

✨ Features

🎤 Record audio for 5 seconds per signal

💾 Save recorded signal as CSV (timestamp + amplitude)

🎚️ UI controls for selecting signal type

📈 Real-time signal display (if enabled)

🔌 Uses sounddevice for audio capture

🧮 Uses scipy, numpy, and pandas for processing
#########################################


2)Noise Producer + Arduino ADC Recorder
------------------------------------
A Python + Arduino project for generating audio signals and recording 5-second ADC samples at 10 kS/s, saved automatically as CSV.

This tool is useful for signal processing, noise analysis, audio experiments, machine-learning datasets, and sensor testing.

✨ Features
🔊 Noise Generator (Python)

Pure Sine Wave

White Gaussian Noise

Pink Noise

Band-Limited Noise

Mix two signals together

Adjustable frequency and duration

Play through speakers using sounddevice

🔌 Arduino 5-Second Recorder

Samples A0 at 10,000 samples per second

Sends exactly 50,000 samples over Serial

Uses "START" and "END" markers for sync

Python saves the recording automatically as CSV
