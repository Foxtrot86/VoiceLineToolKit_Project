import configparser
import time
from venv import create

import numpy as np
from numpy.random import sample
from scipy.ndimage import gaussian_filter1d

from Class_functions import *
import matplotlib.pyplot as plt
import sys

# INIT
log = Logs()
log.create_instance()
config = Configuration(logs=log)
config.import_settings()
try:
    if config.config["Settings"]["reset_logs"]:
        log.clear_logs()
        log.create_instance()
except Exception as e:
    log.write_log(f"WARN: Checking reset_logs settings:  {e}")

config.check_config()

config.edit(section="Advanced Settings", parameter="gain", value=1)


def apply_gain_to_max(audio, target_max_amplitude):
    """
    Adjust the gain of the audio so that the maximum amplitude reaches the target_max_amplitude.
    :param target_max_amplitude: The desired maximum amplitude (e.g., 0.9 for 90% of the possible amplitude range).
    """
    try:
        # Calculate the current max amplitude of the audio
        current_max_amplitude = np.max(np.abs(audio))

        # Calculate the gain factor needed to scale the audio to the desired max amplitude
        gain_factor = target_max_amplitude / current_max_amplitude if current_max_amplitude > 0 else 1

        # Apply the gain to the audio
        audio = audio * gain_factor

        # Log the applied gain (optional)
        # print("Gain factor: ", gain_factor)

    except Exception as e:
        print(e)
    return audio


def show_audio(audio, sr, name=None):
    # Calcul du RMS (Root Mean Square)
    rms_value = np.sqrt(np.mean(np.square(audio)))

    length_audio = len(audio)/sr

    # 1. Tracer la forme d'onde (amplitude dans le temps)
    plt.figure(figsize=(21, 18))
    plt.subplot(3, 1, 1)
    librosa.display.waveshow(audio, sr=sr)
    plt.title(f'Waveform (Amplitude) - {name} | RMS: {rms_value:.6f}')
    plt.xlabel('Time (seconds)')
    plt.xticks(np.arange(0, length_audio, 0.25))
    plt.ylabel('Amplitude')

    # 2. Calculer et tracer le spectrogramme (fréquences)
    plt.subplot(3, 1, 2)
    D = np.abs(librosa.stft(audio))
    DB = librosa.amplitude_to_db(D, ref=np.max)
    img = librosa.display.specshow(DB, sr=sr, x_axis='time', y_axis='log')
    cbar = plt.colorbar(img, format='%+2.0f dB', location='bottom')
    cbar.set_label('Amplitude (dB)')
    plt.title('Spectrogram (Frequencies)')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Frequency (Hz)')

    # 3. Calculer et tracer la série de Fourier
    fft = np.fft.fft(audio)
    frequencies = np.fft.fftfreq(len(fft), 1 / sr)
    magnitude = np.abs(fft)[:len(fft) // 2]
    frequencies = frequencies[:len(fft) // 2]

    plt.subplot(3, 1, 3)
    plt.plot(frequencies, magnitude)
    plt.yscale('log')
    plt.title('Fourier Transform')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.grid()

    # Ajuster l'affichage global
    plt.tight_layout()
    plt.show()


def interpolate_pops(audio_data, threshold=0.2, min_duration=10):
    """
    Detects pops and replaces the pop region by interpolation between surrounding quiet zones.

    - threshold: amplitude value considered as a pop (relative to max amplitude)
    - min_duration: minimum number of samples considered as a pop (short bursts)
    """
    max_amplitude = np.max(np.abs(audio_data))
    pop_threshold = max_amplitude * threshold

    pop_indices = []

    for i in range(1, len(audio_data) - 1):
        if np.abs(audio_data[i]) > pop_threshold:
            pop_indices.append(i)

    for idx in pop_indices:
        # Replace the pop region with the average of its surrounding values
        start = max(0, idx - min_duration)
        end = min(len(audio_data), idx + min_duration)
        audio_data[start:end] = np.interp(np.arange(start, end), [start, end], [audio_data[start], audio_data[end]])

    return audio_data


def gaussian_smooth_audio(audio_data, sigma: "float" = 1):
    """
    Applies a Gaussian smoothing to the audio signal to reduce sudden pops.

    - audio_data: The audio signal as a 1D numpy array.
    - sigma: The standard deviation of the Gaussian kernel. Higher values result in more smoothing.
    """
    # Apply a Gaussian filter with the given sigma to smooth the audio data
    smoothed_audio = gaussian_filter1d(audio_data, sigma=sigma)

    return smoothed_audio


def remove_pops(audio_data, scale=7, window_size=5, reduction_factor=0.5):
    start_ = time.time()
    """
    Detects and reduces microphone pops in an audio signal.

    - audio_data: The audio signal as a 1D numpy array.
    - threshold: The amplitude threshold above which pops are detected.
    - window_size: The size of the window (in samples) over which to check for amplitude spikes.
    - reduction_factor: The factor by which to reduce the amplitude in detected pop areas.

    Returns:
        A modified version of the audio signal with pops reduced.
    """
    r = 80
    # Create a copy of the audio data to modify
    cleaned_audio = np.copy(audio_data)
    mean_scale_list = []
    # Traverse the audio data and detect areas with pops
    for i in range(window_size, len(audio_data) - window_size, int(window_size / r)):
        # Create windows
        #low_window = audio_data[i - window_size:i + int(window_size/r)]
        #high_window = audio_data[i - int(window_size/r):i + window_size]
        out_window = audio_data[i - window_size:i - int(window_size / r)] + audio_data[
                                                                            i + int(window_size / r):i + window_size]
        in_window = audio_data[i - int(window_size / r):i + int(window_size / r)]
        # get means
        #mean_low = np.mean(low_window)
        #mean_high = np.mean(high_window)
        mean_out = np.mean(np.abs(out_window))
        mean_in = np.mean(np.abs(in_window))
        # max i
        #max_i = np.abs(audio_data[i])

        """# Look at a small window around the current sample
        local_window = audio_data[i - window_size:i + window_size]
        local_up = audio_data[i:i + window_size]
        local_down = audio_data[i - window_size:i]
        mean_window = np.mean(local_window)
        mean_up = np.mean(local_up)
        mean_down = np.mean(local_down)"""
        # Detect if a pop is present: large amplitude surrounded by quiet areas
        #if max_i > 20*mean_up and max_i > 20*mean_down:
        if mean_in > 0 and mean_out > 0:
            mean_scale_list.append((f"{round(i / 44100,3)} s",round(mean_in / mean_out,3)))
        if mean_in > scale * mean_out:
            print("pops ",round(i/44100,3), "s  ",round(mean_in / mean_out,3))
            # If a pop is detected, reduce the amplitude at this point
            print((i - int(20*window_size / r))/44100)
            print((i + int(20*window_size / r)) / 44100)
            print((2*int(20*window_size / r)) / 44100)
            for j in range(i - int(20*window_size / r), i + int(20*window_size / r)):
                cleaned_audio[j] /= reduction_factor

    print("time  ", time.time() - start_, "  seconds")
    max_tuple = max(mean_scale_list, key=lambda x: x[1])
    min_tuple = min(mean_scale_list, key=lambda x: x[1])
    print("max ", max_tuple)
    print("min ", min_tuple)
    for tuples in mean_scale_list:
        if tuples[1] > 2:
            print(tuples)
    return cleaned_audio


w = 1.1
t = 20


def f(x):
    y = np.sign(x) * abs((np.tanh(x * np.pi))) ** 4
    return y


def f(x):
    return np.sin(x*np.pi/2)/np.pi*2

def g(x):
    return np.sign(x)*(abs(x))**2

tot = f(1) + g(1)
# Générer des valeurs
x = np.linspace(-w, w, 1000)
f = f(x)
g = g(x)

# Borne les valeurs entre -3 et 3
f_b = np.clip(f, -t, t)
g_b = np.clip(g, -t, t)

# Tracer les résultats

#plt.plot(x, y, label='f(x)')
plt.plot(x, f_b, label='f(x)')
plt.plot(x, x, label='x=y')
plt.xlabel('x')
plt.ylabel('f(x)')
plt.legend()
plt.grid()
plt.show()

plt.plot(x, g_b, label='g(x)')
plt.plot(x, x, label='x=y')
plt.xlabel('x')
plt.ylabel('g(x)')
plt.legend()
plt.grid()
plt.show()


audio_path = r"E:\Documents\RON voices\testbisb\[CALL]OrderMoveS.ogg"
audio_folder = r"E:\Documents\RON voices\testbisb"

audio = Audio(path=audio_path, config=config, logs=log)
target_amp = np.max(np.abs(audio.audio))
show_audio(audio.audio, 44100, "Original")
audio.save(audio_folder, name="Original")

audio.apply_effect(effect="compression")
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "Compressed")
audio.save(audio_folder, name="compressed")

audio = Audio(path=audio_path, config=config, logs=log)
audio.apply_effect(effect="fade")
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "fade")
audio.save(audio_folder, name="fade")

audio = Audio(path=audio_path, config=config, logs=log)
audio.apply_effect(effect="bandpass")
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "Passband")
audio.save(audio_folder, name="Passband")

"""audio = Audio(path=audio_path, config=config, logs=log)
audio.apply_effect(effect="desaturation")
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "desaturation")
audio.save(audio_folder, name="desatration")
audio.audio = np.sin(audio.audio / target_amp * (np.pi / 2))
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "desaturation + sin")
audio.save(audio_folder, name="desatration + sin")"""

audio = Audio(path=audio_path, config=config, logs=log)
audio.apply_effect(effect="noisereduction")
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "noisereduction")
audio.save(audio_folder, name="noisereduction")

audio = Audio(path=audio_path, config=config, logs=log)
audio.apply_effect(effect="retrim")
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "re-trimmed")
audio.save(audio_folder, name="re-trimmed")

audio = Audio(path=audio_path, config=config, logs=log)
audio.audio = gaussian_smooth_audio(audio.audio, sigma=0.5)
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "gaussian")
audio.save(audio_folder, name="gaussian")

audio = Audio(path=audio_path, config=config, logs=log)
audio.audio = np.sin(audio.audio / target_amp * (np.pi / 2))/np.pi*2
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "sinus")
audio.save(audio_folder, name="sinus")


"""audio = Audio(path=audio_path, config=config, logs=log)
audio.audio = remove_pops(audio.audio, scale=6, window_size=8000, reduction_factor=100)
audio.audio = apply_gain_to_max(audio.audio, target_amp)
show_audio(audio.audio, 44100, "remove pops")
audio.save(audio_folder, name="remove pops")"""

plt.rcParams["figure.figsize"] = [20, 30]
plt.rcParams["figure.autolayout"] = True
