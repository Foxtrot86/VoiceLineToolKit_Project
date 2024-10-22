""" -----     IMPORTS     -------------------------------------------------------------------------------------------"""
import configparser
import os
import time
import shutil
import librosa
import noisereduce as nr
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt


""" -----     GENERIC FUNCTIONS     ---------------------------------------------------------------------------------"""


def set_debug_status(log: 'Logs'):
    try:
        if log.errors[0] > 0 and log.errors[1] == 0:
            status = "#fa781b"
        elif log.errors[1] > 0:
            status = "#e80505"
        else:
            status = "#498dbf"
    except Exception as e:
        log.write_log(f"WARN: Can't update errors state:  {e}")
        status = "#fa781b"
    return status

def get_subtitles(subtitle_path, separator):
    sub_dict = {}
    try:
        with open(subtitle_path, "r", encoding="utf-8") as f:
            for line in f:
                # Split the line by commas
                parts = line.strip().split(separator)
                # The first part is the key, the rest are the values
                if len(parts) != 0:
                    key = parts[0]
                    value = parts[1:]
                    sub_dict[key] = value
    except Exception as e:
        return e
    return sub_dict


# Delete directory and re-create it
def clear_directory(directory):
    try:
        shutil.rmtree(directory)
        os.makedirs(directory)
        return True
    except Exception as e:
        return e


def adjust_volume(log: 'Logs', l_config: 'Configuration'):
    adjusted_number, scaling, wierd_files = 0, [], 0
    vo_folder = l_config.config["Settings"]["voice_folder"] + "/" + l_config.config["Settings"][
        "character_voice_folder"]
    extension = "." + l_config.config["Static settings"]["audio_format"]
    work_folder = (l_config.config["Settings"]["workspace_folder"] + "/" +
                   l_config.config["Settings"]["character_voice_folder"] +
                   l_config.config["Static settings"]["voice_lines"])
    accurate = False
    if l_config.config["Advanced Settings"]["accurate_volume_adjustment"]:
        accurate = True
    o_folder = FileManagement(path=vo_folder, logs=log, config=l_config)
    o_files = o_folder.get_folder_content(file_filter=extension, raw=False)
    vl_folder = FileManagement(path=work_folder, logs=log, config=l_config)
    vl_files = vl_folder.get_folder_content(file_filter=extension, raw=False)
    o_rms, o_rms_value, vl_rms_value = [], 0, 0
    for vl_file_base in vl_files:
        if vl_file_base in o_files:
            # get original rms
            for o_file in o_files[vl_file_base]:
                audio = Audio(path=vo_folder + "/" + o_file, logs=log, config=l_config)
                o_rms.append(audio.calculate_rms(isolate=accurate))
            if len(o_rms) > 0:
                o_rms_value = sum(o_rms) / len(o_rms)
            # adjust rms for each file
            for vl_file in vl_files[vl_file_base]:
                voice_line = Audio(path=work_folder + "/" + vl_file, logs=log, config=l_config)
                vl_rms_value = voice_line.calculate_rms(isolate=accurate)
                scaling_factor = (o_rms_value / vl_rms_value) * l_config.config["Settings"]["volume_multiplier"]
                print("applying scaling factor ", scaling_factor)
                voice_line.audio *= scaling_factor
                scaling.append(scaling_factor)
                sf.write(voice_line.path, voice_line.audio, voice_line.sr)
                adjusted_number += 1
        else:
            log.write_log(
                f"WARN: {vl_file_base} does not exist in the original voice folder, you may check your folders")
    return adjusted_number


def open_folder(fld_path):
    try:
        if os.path.exists(fld_path):
            os.startfile(fld_path)  # Windows only
    except Exception as e:
        print("Can't open file explorer:  ", e)
    return None

def open_file(file_path):
    return None


def check_audio_files(folder_path, l_log: 'Logs', l_config: 'Configuration', auto_del=False):
    # Check if some file have an anormal rms
    l_log.write_log(f"INFO: Checking the file, auto delete: {auto_del}")
    extension = "." + l_config.config["Static settings"]["audio_format"]
    rms_values, wrong_files = [], []
    folder = FileManagement(folder_path, logs=l_log, config=l_config)
    files = list(folder.get_folder_content(raw=True, file_filter=extension))
    for file_name in files:
        audio = Audio(path=folder_path + "/" + file_name, logs=l_log, config=l_config)
        rms_values.append(audio.calculate_rms())
    rms_mean = sum(rms_values) / len(rms_values)
    for i in range(len(rms_values)):
        if rms_values[i] > 100 * rms_mean or rms_values[i] < 0.01 * rms_mean:
            wrong_files.append((files[i], rms_values[i] / rms_mean))
    if auto_del:
        for wrong_file in wrong_files:
            l_log.write_log(f"INFO: Deleting file: {wrong_file[0]}")
            os.remove(folder_path + "/" + wrong_file[0])
    l_log.write_log(f"INFO: Checking files completed, bad files found: {len(wrong_files)}")
    return wrong_files


def check_names(folder_path, l_log: 'Logs', l_config: 'Configuration', auto_correction: bool = True):
    l_log.write_log("INFO: Checking file names")
    missing_files = []
    folder = FileManagement(folder_path, logs=l_log, config=l_config)
    extension = "." + l_config.config["Static settings"]["audio_format"]
    separator = l_config.config["Static settings"]["name_separator"]
    files = folder.get_folder_content(raw=False, file_filter=extension)
    for file_base_name in files:
        numbers, missing_numbers, file_names = [], [], []
        for file_name in files[file_base_name]:
            file_name = file_name.replace(extension, "")
            numbers.append(int(file_name.split(separator)[-1]))
            file_names.append(file_name)
        numbers.sort()
        for i in range(0, numbers[-1] + 1):
            if i not in numbers:
                missing_numbers.append(i)
                missing_files.append(f"{file_base_name}{separator}{i}")
        if auto_correction:
            j = 0
            for i in range(len(numbers)):
                if j < len(missing_numbers) and numbers[i] > missing_numbers[j]:
                    new_file_name = f"{file_base_name}{separator}{missing_numbers[j]}{extension}"
                    os.rename(os.path.join(folder_path, file_names[i] + extension),
                              os.path.join(folder_path, new_file_name))
                    j += 1
    return missing_files


# Compile all voice lines into a single file
def compile_voice_lines(folder_path, l_log: 'Logs', l_config: 'Configuration'):
    # Create the separator
    vl_folder = (l_config.config["Settings"]["workspace_folder"] + "/" +
                 l_config.config["Settings"]["character_voice_folder"] +
                 l_config.config["Static settings"]["voice_lines"])
    sample_rate = l_config.config["Static settings"]["sample_rate"]
    t = np.linspace(0, 0.1, int(sample_rate * 0.1), endpoint=False)  # Time axis
    separator = 0.5 * np.sin(2 * np.pi * 144 * t)
    full_audio = []
    extension = "." + l_config.config["Static settings"]["audio_format"]
    folder = FileManagement(path=folder_path, logs=l_log, config=l_config)
    files = folder.get_folder_content(raw=False, file_filter=extension)
    for file_base_name in files:
        for file_name in files[file_base_name]:
            audio_file = Audio(path=vl_folder + file_name, logs=l_log, config=l_config)
            if audio_file.audio:
                full_audio.append(audio_file.audio)
                full_audio.append(separator)

    return None


""" -----     LOGGER     --------------------------------------------------------------------------------------------"""


class Logs:
    def __init__(self):
        self.name = "logs"
        self.errors = [0, 0]
        self.extension = ".txt"
        self.folder = ""
        self.path = self.name+self.extension
        self.check_logs()

    # Check if the log file exist or create one if not
    def check_logs(self):
        if not os.path.exists(self.path):
            with open(self.path, 'w') as f:
                f.write("")
            print(f"File '{self.path}' created.")
        else:
            print(f"File '{self.path}' already exists.")
        return None

    def debug(self):
        self.errors = [0, 0]
        return None

    # Create an instance in the log file
    def create_instance(self):
        message = "\n\n --- App launched, at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " ---\n\n"
        self.write_log(message)
        return None

    # Write a message in the log file
    def write_log(self, message):
        print("Log message: ", message)
        if "WARN" in message:
            self.errors[0] += 1
        if "FATAL" in message:
            self.errors[1] += 1
        with open(self.path, 'a') as f:
            f.write(message + '\n')
        return None

    # Clear the log file
    def clear_logs(self):
        print("Clearing logs...")
        with open(self.path, 'w') as f:
            pass
        return None


""" -----     CONFIG     --------------------------------------------------------------------------------------------"""


class Configuration:
    def __init__(self, logs=None):
        self.name = "config"
        self.extension = ".ini"
        self.folder = ""
        self.path = self.name + self.extension
        if logs:
            self.log = logs
        else:
            self.log = Logs()
        # Default Settings
        self.config = {
            "DEFAULT": [],
            "INFO": ["Info message"],
            "Settings":
                {
                    "voice_folder": "C:/programefiles/Steam/steamapps/common/Ready Or Not/ReadyOrNot/Content/VO",
                    "character_voice_folder": "/SWATJudge",
                    "workspace_folder": "...Document/Workspace",
                    "silent_duration_threshold": 0.7,
                    "silent_volume_threshold": -30.0,
                    "silence_padding": 0.2,
                    "minimal_audio_duration": 3,
                    "minimal_segment_duration": 1,
                    "volume_multiplier": 1,
                    "open_files": False,
                    "reset_logs": False,
                    "combine_s_files": False
                },
            "Advanced Settings":
                {
                    "pre_effect": 'noisereduction',
                    "pre_effect_scale": 0.8,
                    "accurate_volume_adjustment": True,
                    "gain": 1,
                    "sinus_pass" : 1,
                    "noise_reduction": 0.6,
                    "noise_reduction_stationary_thresh": 0,
                    "compression_threshold": -45,
                    "compression_ratio": 4,
                    "compression_fade": 0.02,
                    "desaturation_threshold": 0.8,
                    "desaturation_reduction": 2,
                    "bandpass_order": 4,
                    "bandpass_low": 20,
                    "bandpass_high": 20000,
                    "fading_duration": 0.1,
                    "double_check_files": True

                },
            "Static settings":
                {
                    "all_effect": 'noisereduction bandpass compression retrim gain desaturation fade',
                    "audio_format": "ogg",
                    "sample_rate": 44100,
                    "sub_file_name": "sub_en.csv",
                    "blank_tracks": "/BlankTracks",
                    "dubbed_tracks": "/DubbedTracks",
                    "voice_lines": "/VoiceLines",
                    "split_thread": "auto",
                    "name_separator": "_"
                }

        }
        # create main variables
        self.VO_folder = self.config["Settings"]["voice_folder"]
        self.character = self.config["Settings"]["character_voice_folder"]
        self.workspace_folder = self.config["Settings"]["workspace_folder"]
        self.blank_tracks = self.config["Static settings"]["blank_tracks"]
        self.dubbed_tracks = self.config["Static settings"]["dubbed_tracks"]
        self.check_config()

    def edit(self, section, parameter, value):
        try:
            self.config[section][parameter] = value
            parser = configparser.ConfigParser()
            parser.read(self.path)
            parser.set(section, parameter, str(value))
            with open(self.path, 'w') as f:
                parser.write(f)
            self.log.write_log(f"INFO: Config data edited by the code")
        except Exception as e:
            self.log.write_log(f"WARN: Can't update config file:  {e}")
        return None

    def check_config(self):
        try:
            if not os.path.exists(self.path):
                self.log.write_log(f"FATAL: Config file does not exist: {self.path}")
            config_file = configparser.ConfigParser()
            config_file.read(self.path)
            conf_dict = dict(config_file)
            default_config = self.config
            self.log.write_log(f"INFO: Config file readable: {self.path}")
            if len(conf_dict) != len(default_config):
                self.log.write_log(message="FATAL: Config file contains different section number:\n"
                                           f"   config:   {len(conf_dict)} sections; {conf_dict.keys()} \n"
                                           f"   expected: {len(default_config)} sections; {default_config.keys()} \n")
            for key in conf_dict.keys():
                if len(conf_dict[key]) != len(default_config[key]):
                    self.log.write_log(f"FATAL: Section '{key}' has different variable number: \n"
                                       f"    config: {len(conf_dict[key])}, expected: {len(default_config[key])}")
        except Exception as e:
            self.log.write_log(f"FATAL: reading / checking config file:  {e}")

    # Convert a str into a value (if possible)
    def convert_value(self, value):
        # Try to convert to an integer
        if value.isdigit():
            return int(value)
        # Try to convert to a float
        try:
            return float(value)
        except ValueError:
            pass
        # Try to convert to a boolean
        lower_value = value.lower()
        if lower_value in ['true', 'false']:
            return lower_value == 'true'
        # If all conversions fail, return the value as a string
        return value

    # Update the config
    def import_settings(self):
        try:
            read_config = configparser.ConfigParser()
            read_config.read(self.path)
            config_dict = {section: {key: self.convert_value(value) for key, value in read_config.items(section)} for
                           section in read_config.sections()}
            self.config["Settings"] = dict(config_dict["Settings"])
            self.config["Advanced Settings"] = dict(config_dict["Advanced Settings"])
            self.config["Static settings"] = dict(config_dict["Static settings"])
            # Update main variables
            self.VO_folder = self.config["Settings"]["voice_folder"]
            self.character = self.config["Settings"]["character_voice_folder"]
            self.workspace_folder = self.config["Settings"]["workspace_folder"]
            self.blank_tracks = self.config["Static settings"]["blank_tracks"]
            self.dubbed_tracks = self.config["Static settings"]["dubbed_tracks"]
            self.voice_lines = self.config["Static settings"]["voice_lines"]
        except Exception as e:
            self.log.write_log(f"WARN: Importing / Updating config:  {e}")
        return self.config

    # Write data in the config file
    def write_config(self, section, key, value):
        try:
            config = configparser.ConfigParser()
            config.read(self.path)
            # Update the value
            config[section][key] = str(value)  # Convert value to string
            # Write the changes back to the config file
            with open(self.path, 'w') as config_file:
                config.write(config_file)
        except Exception as e:
            self.log.write_log(f"WARN: Writing new value in config file:  {e}")
        return None


""" -----     FILEMANAGEMENT     ------------------------------------------------------------------------------------"""


class FileManagement:
    def __init__(self, path, logs: 'Logs', config: 'Configuration'):
        self.log = logs
        self.config = config
        self.path = path
        if os.path.isfile(self.path):
            self.type = 'file'
            self.filename = os.path.basename(self.path)
            self.folder = os.path.dirname(self.path)
            self.extension = os.path.splitext(self.filename)[1]
        elif os.path.isdir(self.path):
            self.type = 'folder'
            self.filename = None
            self.extension = None
            self.folder = os.path.dirname(self.path)
        else:
            self.create(path)

    # Create the file or the folder
    def create(self, path=None):
        self.log.write_log("Create request from FileManagement class")
        try:
            if path is None:
                path = self.path
            if os.path.splitext(path)[1]:  # It's a file
                dir_name = os.path.dirname(path)
                if dir_name and not os.path.exists(dir_name):
                    os.makedirs(dir_name)
                if os.path.splitext(path)[1] == '.' + self.config.config["Static settings"]["audio_format"]:
                    sample_rate = self.config.config["Static settings"]["sample_rate"]
                    audio_format = self.config.config["Static settings"]["audio_format"]
                    num_samples = 0.01 * sample_rate
                    # Write the empty audio
                    sf.write(path, np.zeros(int(num_samples)), sample_rate, format=audio_format)
                else:
                    with open(path, 'a'):
                        os.utime(path, None)
            else:  # It's a folder
                if not os.path.exists(path):
                    os.makedirs(path)
            self.log.write_log(f"INFO: New file created: {path}")
        except Exception as e:
            self.log.write_log(f"FATAL: Can't create new file '{self.path}': {e}")
        return None

    # Create the workspace structure from the workspace folder
    def create_folder_tree(self):
        blank_tracks = self.config.blank_tracks
        dubbed_tracks = self.config.dubbed_tracks
        voice_lines = self.config.voice_lines
        path_workspace = self.config.workspace_folder + "/" + self.config.character
        if not os.path.exists(path_workspace + blank_tracks):
            self.create(path_workspace + blank_tracks)
        if not os.path.exists(path_workspace + dubbed_tracks):
            self.create(path_workspace + dubbed_tracks)
        if not os.path.exists(path_workspace + voice_lines):
            self.create(path_workspace + voice_lines)
        return None

    def check(self, args):  # args is a list or argument
        log_list = []
        try:
            if 'exist' in args:  # Check if the folder exist
                pass
            if 'VO' in args:  # Check if the VO folder looks like a real one
                pass
            if 'voicelines' in args:  # Check if the voice lines folder is not empty
                pass
            for message in log_list:
                self.log.write_log(message)
        except Exception as e:
            self.log.write_log(fr"WARN: Can't Check the folder {self.path}: {e}")
        return

    # Get the file names (can do it without the variation) in a specified folder
    def get_folder_content(self, raw=True, file_filter=None):
        try:
            content = os.listdir(self.path)
            files = {}
            name_separator = self.config.config["Static settings"]["name_separator"]
            if file_filter is not None:
                for f in content:
                    if f.endswith(file_filter) and raw:
                        files[f] = file_filter
                    elif f.endswith(file_filter) and not raw:
                        key = ''.join(f.split(name_separator)[:-1])
                        files.setdefault(key, []).append(f)
            else:
                for f in content:
                    files[f] = ''
            if '' in files.keys():
                del files['']
            return files
        except Exception as e:
            self.log.write_log(fr"WARN: Can't get the folder content properly: {e}")
            return None


""" -----     AUDIO     ---------------------------------------------------------------------------------------------"""


class Audio:
    def __init__(self, path, config: 'Configuration', logs: 'Logs'):
        self.path = path
        self.folder, temp_name = os.path.split(path)
        self.name, self.original_extension = os.path.splitext(temp_name)
        self.path = path
        self.log = logs
        self.config = config
        if os.path.exists(self.path):
            print(f"Reading audio {self.name} from {self.path}")
            self.audio = self.read()
        self.sr = config.config["Static settings"]["sample_rate"]
        self.format = '.' + config.config["Static settings"]["audio_format"]
        self.split_thread = int(0.01 * self.sr)  # default split precision at 10ms

    def init_sr(self):
        try:
            # Open the audio file and retrieve its sample rate
            with sf.SoundFile(self.path) as audio_file:
                sample_rate = audio_file.samplerate
            self.config.write_config("Static settings", "sample_rate", sample_rate)
            self.sr = sample_rate
            self.log.write_log(f"INFO: Sample rate updated at {sample_rate} Hz from file '{self.path}'")
        except Exception as e:
            self.log.write_log(f"WARN: Can't Update the sample Rate: {e}")
        return None

    def get_split_thread(self):
        try:
            config_value = self.config.config["Static settings"]["split_thread"]
            if config_value == 'auto':
                self.split_thread = int(0.01 * self.sr)
            else:
                self.split_thread = int(float(config_value) * self.sr)
        except Exception as e:
            self.log.write_log(f"WARN: Can't get the split_thread: {e}")

    # Return the audio
    def read(self):
        try:
            read_audio, sr = librosa.load(self.path, sr=self.config.config["Static settings"]["sample_rate"])
        except Exception as e:
            self.log.write_log(fr"WARN: Can't Read the audio file: {e}")
            read_audio = None
        return read_audio

    # Calculate the rms of the audio
    def calculate_rms(self, isolate=False):
        try:
            if isolate:
                audio = self.isolate_high_amp()
            else:
                audio = self.audio
            rms = np.mean(librosa.feature.rms(y=audio))
            return rms
        except Exception as e:
            self.log.write_log(f"WARN: RMS calculation for {self.name}: {e}")

    def apply_effect(self, effect="", scale=1.0):
        applied = False
        try:
            advanced_settings = self.config.config["Advanced Settings"]
        except Exception as e:
            self.log.write_log(f"WARN: Can't load settings for audio effects. {e}")
            advanced_settings = {}
        # Check if audio data is loaded
        if self.audio is None:
            self.log.write_log(f"WARN: No audio data loaded for {self.name}.")
            return
        if effect is not None:
            effect = effect.split(" ")
        if "noisereduction" in effect:
            try:
                # Get noise reduction values
                strength, s_threshold = (advanced_settings[key] for key in ["noise_reduction",
                                                                           "noise_reduction_stationary_thresh"])
                # Apply noise reduction using the noisereduce library
                reduced_audio = nr.reduce_noise(y=self.audio,
                                                sr=self.sr,
                                                prop_decrease=strength * scale,
                                                stationary=s_threshold)
                # Update self.audio with the noise-reduced version
                self.audio = reduced_audio
                # print("nr applied")
                applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to apply noise reduction on {self.name}: {e}")
        if "bandpass" in effect:
            try:
                # Get bandpass values
                order, low, high = advanced_settings["bandpass_order"], advanced_settings["bandpass_low"], \
                    advanced_settings["bandpass_high"]
                # Design a bandpass filter
                sos = butter(N=order, Wn=[low, high], btype='band', fs=self.sr, output='sos')
                # Apply the bandpass filter to the audio
                self.audio = sosfilt(sos, self.audio)
                # print("bandpass applied")
                applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to apply bandpass filter on {self.name}: {e}")
        if "compression" in effect:
            try:
                # Get compression settings
                threshold, fade, ratio = (advanced_settings[key] for key in ["compression_threshold",
                                                                             "compression_fade",
                                                                             "compression_ratio"])
                # Normalize the audio to range [0, 1]
                audio_normalized = self.audio / np.max(np.abs(self.audio))
                # Convert threshold from dB to linear scale
                threshold_linear = 10 ** (threshold / 20)
                # Initialize output array
                compressed_audio = np.zeros_like(audio_normalized)
                # Variables for attack and release
                env = 0.0
                for i in range(len(audio_normalized)):
                    # Calculate the envelope (attack)
                    env = (1 - fade) * env + fade * np.abs(audio_normalized[i])
                    # Apply compression if the envelope exceeds the threshold
                    if env > threshold_linear:
                        # Calculate gain based on the ratio
                        gain = threshold_linear + (env - threshold_linear) / (ratio * scale)
                    else:
                        gain = 1.0  # No compression
                    # Apply gain to the audio sample
                    compressed_audio[i] = audio_normalized[i] * gain
                # Scale back to the original range
                self.audio = compressed_audio * np.max(np.abs(self.audio))
                # print("compression applied")
                applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to apply compression on {self.name}: {e}")
        if "retrim" in effect:
            print("aa")
            try:
                silence_threshold = self.config.config["Settings"]["silent_volume_threshold"]
                buffer_seconds = self.config.config["Settings"]["silence_padding"]
                # Find start index
                start_index = 0
                amplitude = librosa.amplitude_to_db(np.abs(self.audio), ref=np.max)
                while start_index < len(self.audio) and amplitude[start_index] < silence_threshold:
                    start_index += 1
                # Find end index
                end_index = len(self.audio) - 1
                while end_index > 0 and amplitude[end_index] < silence_threshold:
                    end_index -= 1
                # Calculate the buffer in samples
                buffer_samples = int(buffer_seconds * self.sr)
                # Adjust the start and end indices to include the buffer
                start_index = max(start_index - buffer_samples, 0)
                end_index = min(end_index + buffer_samples, len(self.audio))
                # Update the audio to include the buffer
                self.audio = self.audio[start_index:end_index]
                applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to retrim {self.name}: {e}")
        if "sinus" in effect:
            try:
                for p in range(self.config.config["Advanced Settings"]["sinus_pass"]):
                    max_amp = np.max(np.abs(self.audio))
                    self.audio = np.sin(self.audio / max_amp * (np.pi / 2))
                    applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to apply sinus function on {self.name}: {e}")
        if "gain" in effect:
            try:
                gain = scale * advanced_settings["gain"]
                self.audio *= gain
                # print("gain applied")
                applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to apply gain on {self.name}: {e}")
        if "desaturation" in effect:
            try:
                threshold, reduction_factor = (advanced_settings[key] for key in ["desaturation_threshold",
                                                                                  "desaturation_reduction"])
                # Trouver la valeur absolue maximale dans l'audio
                max_val = np.max(np.abs(self.audio))
                # S'assurer que le max_val n'est pas nul pour éviter la division par zéro
                if max_val > 0:
                    normalized_audio = self.audio / max_val
                else:
                    normalized_audio = self.audio  # Si l'audio est déjà complètement silencieux
                # Identify where the audio exceeds the threshold
                saturated_indices = np.where(np.abs(normalized_audio) > threshold)[0]
                # Reduce the gain of the saturated parts
                self.audio[saturated_indices] /= (reduction_factor * scale)
                # print("desaturation applied")
                applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to apply desaturation on {self.name}: {e}")
        if "fade" in effect:
            try:
                fade_duration = advanced_settings["fade_duration"]
                # Calculate the number of samples for the fade duration
                fade_samples = int(fade_duration * self.sr)
                # Create a linear fade-in and fade-out window
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                # Ensure the audio length is greater than fade_samples
                if len(self.audio) > fade_samples:
                    # Apply fade-in at the start
                    self.audio[:fade_samples] *= fade_in
                    # Apply fade-out at the end
                    self.audio[-fade_samples:] *= fade_out
                # print("fade applied")
                applied = True
            except Exception as e:
                self.log.write_log(f"WARN: Failed to apply fade on {self.name}: {e}")
        print("At least an effect has been applied ? ", applied)
        return self.audio

    # Isolate the audio segments that are above a given threshold
    def isolate_high_amp(self):
        try:
            # Convert the silent_volume_threshold to amplitude
            threshold = librosa.db_to_amplitude(self.config.config["Settings"]["silent_volume_threshold"])

            # Create an empty list to store non-silent audio segments
            filtered_audio_segments = []

            # Initialize start and end indices for non-silent segments
            start = None
            end = None

            # Iterate through the audio samples
            for i, sample in enumerate(self.audio):
                # If the absolute amplitude is above the threshold
                if abs(sample) > threshold:
                    # Start a new segment if not already started
                    if start is None:
                        start = i
                    end = i  # Update the end index of the segment
                else:
                    # If the sample is below the threshold and we have a started segment, close the segment
                    if start is not None:
                        filtered_audio_segments.append(self.audio[start:end + 1])
                        start = None  # Reset start to begin detecting a new segment

            # Handle any remaining segment at the end of the audio
            if start is not None:
                filtered_audio_segments.append(self.audio[start:end + 1])

            # Concatenate all non-silent segments into a single audio array
            if filtered_audio_segments:
                return np.concatenate(filtered_audio_segments)
            else:
                print(f"WARN: Can't find any silent segments in {self.path}")
                return self.audio

        except Exception as e:
            self.log.write_log(f"WARN: Isolate high amplitude sound segment in {self.path}: {e}")
            return self.audio

    # Main function to split audio tracks in multiple lines
    def split_audio(self):
        try:
            # Variables
            threshold_db = self.config.config["Settings"]["silent_volume_threshold"]
            threshold_duration = self.config.config["Settings"]["silent_duration_threshold"]
            silence_padding = self.config.config["Settings"]["silence_padding"]
            minimal_segment_duration = self.config.config["Settings"]["minimal_segment_duration"]
            # Calculate amplitude in dB
            amplitude = librosa.amplitude_to_db(np.abs(self.audio), ref=np.max)
            segments = []
            if amplitude[0] > threshold_db:
                segments = [(0, True)]
            # Mark switch between up and down state
            for i in range(1, len(amplitude), self.split_thread):
                if amplitude[i] > threshold_db >= amplitude[i - self.split_thread]:
                    segments.append((i / self.sr, True))  # Entering audible segment
                elif amplitude[i] < threshold_db <= amplitude[i - self.split_thread]:
                    segments.append((i / self.sr, False))  # leaving audible segment
            if segments[-1][1]:
                segments.append((len(amplitude), False))
            index_list = []
            # Merging short silence to audio
            for i in range(len(segments) - 1):
                if not segments[i][1]:
                    silence_duration = segments[i + 1][0] - segments[i][0]
                    if silence_duration <= threshold_duration:
                        index_list += (i, i + 1)
            segments = [v for i, v in enumerate(segments) if i not in index_list]
            index_list = []
            # Merging short audio to silence
            for i in range(len(segments) - 1):
                if segments[i][1]:
                    audible_duration = segments[i + 1][0] - segments[i][0]
                    if audible_duration <= minimal_segment_duration:
                        index_list += (i, i + 1)
            segments = [v for i, v in enumerate(segments) if i not in index_list]
            # Add silence padding
            for i in range(len(segments)):
                if segments[i][1]:
                    segments[i] = (max(0, segments[i][0] - silence_padding), True)
                else:
                    segments[i] = (min((len(amplitude) - 1) / self.sr, segments[i][0] + silence_padding), False)
            if not segments[0][1]:  # Make sure that the segments list doesn't start with a False
                segments.pop(0)
            segment_iterations = [(int(segments[i][0] * self.sr), int(segments[i + 1][0] * self.sr)) for i in
                                  range(0, len(segments), 2)]
            return segment_iterations
        except Exception as e:
            self.log.write_log(f"WARN: Can't split audio '{self.name}': {e}")
            return [(0, 1)]

    def save(self, output_folder, segments=None, name='auto', time_limit=True):
        audio_type = "audio"
        saved_number = 0
        try:
            if name == 'auto':
                name = self.name
            path = f'{output_folder}/{name}'
            if isinstance(segments, list):
                audio_type = "segment"
                for i, (start, end) in enumerate(segments):
                    if abs(start - end) < 0.2 * self.sr and time_limit:
                        self.log.write_log(
                            f"WARN: a segment of '{self.name}' will not be saved because it's too short "
                            f"({(end - start) / self.sr} second)")
                        pass
                    segment = self.audio[start:end]
                    segment_path = f"{path}_{i}{self.format}"
                    sf.write(segment_path, segment, self.sr, format=self.format[1:])
                    saved_number += 1
            elif segments == 'empty':
                audio_type = "empty file"
                num_samples = int(0.01 * self.sr)
                empty_audio_data = np.zeros(num_samples)
                sf.write(path+self.format, empty_audio_data, self.sr, format=self.format[1:])
                saved_number += 1
            else:
                sf.write(path + self.format, self.audio, self.sr, format=self.format[1:])
                saved_number += 1
        except Exception as e:
            self.log.write_log(f"WARN: Can't save {audio_type} from '{self.name}': {e}")
        return saved_number


""" -----     RECORDER     ------------------------------------------------------------------------------------------"""
