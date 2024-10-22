""" -----     IMPORTS     -------------------------------------------------------------------------------------------"""
import shutil
import time

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from matplotlib.style.core import available

from Class_functions import *
from VoiceLineToolKit import log, config

""" -----     UI FUNCTIONS     --------------------------------------------------------------------------------------"""


def apply_style(app):
    # Set the application icon
    app.setWindowIcon(QIcon("icon.ico"))
    style = ("QWidget { background-color: #3579b5; color: #ffffff; font-family: Arial; } QPushButton { "
             "background-color: #295f8a; border: 1px solid #ffffff; border-radius: 8px; padding: 15px; color: "
             "#ffffff; } QPushButton:hover { background-color: #3b7199; } QLabel { color: #ffffff; padding: 10px; } "
             "QLineEdit { background-color: #276489; color: #ffffff; border: 1px solid #ffffff; border-radius: 5px; "
             "padding: 10px; }")

    app.setStyleSheet(style)


# First window with title and "Next" button
class IntroWindow(QWidget):
    def __init__(self, status="#498dbf"):
        super().__init__()
        self.setWindowTitle("VoiceLineToolKit")
        self.status = status
        self.setGeometry(200, 200, 1280, 720)  # 16:9 aspect ratio
        self.init_ui()

    def init_ui(self):
        # Title and description
        title_label = QLabel("Welcome to VoiceLineToolKit", self)
        title_label.setFont(QFont("Arial", 30))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWindowIcon(QIcon('icon.ico'))

        description_label = QLabel(
            "Easily manage and process audio files for video game dubbing. Let's start by setting up your workspace.",
            self)
        description_label.setFont(QFont("Arial", 14))
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)

        # Next button
        next_button = QPushButton("Next", self)
        next_button.setFont(QFont("Arial", 16))
        next_button.clicked.connect(self.open_folder_window)

        # Debug button
        self.debug_button = QPushButton("debug", self)
        self.debug_button.setFont(QFont("Arial", 10))
        self.debug_button.clicked.connect(self.debug_ui)

        # Change button background color based on status
        self.debug_button.setStyleSheet(f"background-color: {self.status}; color: white")

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(next_button)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        # Debug layout
        debug_layout = QHBoxLayout()
        debug_layout.addStretch(1)  # Espace flexible à gauche
        debug_layout.addWidget(self.debug_button)  # Ajoute le bouton Debug à droite

        # Ajouter le layout du bouton Debug à la fin du layout principal
        layout.addLayout(debug_layout)

    def open_folder_window(self):
        self.folder_window = FolderWindow()
        self.folder_window.show()
        self.close()

    def debug_ui(self, update=False):
        if not update:
            log.debug()
        status = set_debug_status(log)
        self.debug_button.setStyleSheet(f"background-color: {status}; color: white")
        return None


# Second window for selecting directories
class FolderWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoiceLineToolKit - Setup")
        self.setGeometry(200, 200, 1280, 720)  # 16:9 aspect ratio
        self.init_ui()
        self.load_config()

    def init_ui(self):
        # Labels and input fields
        char_label = QLabel('Select Voice Folder (...\\Ready Or Not\\ReadyOrNot\\Content\\VO):', self)
        char_label.setFont(QFont("Arial", 14))
        self.setWindowIcon(QIcon('icon.ico'))

        self.voice_input = QLineEdit(self)
        self.voice_input.setFont(QFont("Arial", 12))

        voice_folder_button = QPushButton("Browse", self)
        voice_folder_button.setFont(QFont("Arial", 12))
        voice_folder_button.clicked.connect(self.browse_voice_folder)

        work_label = QLabel("Select Workspace Folder (Just a folder that you can access easily):", self)
        work_label.setFont(QFont("Arial", 14))

        self.work_input = QLineEdit(self)
        self.work_input.setFont(QFont("Arial", 12))

        work_button = QPushButton("Browse", self)
        work_button.setFont(QFont("Arial", 12))
        work_button.clicked.connect(self.browse_workspace_folder)

        # Next button
        next_button = QPushButton("Next", self)
        next_button.setFont(QFont("Arial", 16))
        next_button.clicked.connect(self.save_config)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(char_label)
        layout.addWidget(self.voice_input)
        layout.addWidget(voice_folder_button)
        layout.addWidget(work_label)
        layout.addWidget(self.work_input)
        layout.addWidget(work_button)
        layout.addWidget(next_button)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def load_config(self):
        # Load existing values from the config file
        self.voice_input.setText(config.VO_folder)
        self.work_input.setText(config.workspace_folder)
        return config

    def browse_voice_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Character Folder")
        if folder:
            self.voice_input.setText(folder)

    def browse_workspace_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Workspace Folder")
        if folder:
            self.work_input.setText(folder)

    def save_config(self):
        config_file_path = config.path
        new_voice_folder = self.voice_input.text()
        new_workspace_folder = self.work_input.text()

        # Read the existing config file content
        with open(config_file_path, 'r') as config_file:
            lines = config_file.readlines()

        # Update the parameters in the existing lines
        for i in range(len(lines)):
            if lines[i].startswith('voice_folder'):
                lines[i] = f'voice_folder = {new_voice_folder}\n'
            elif lines[i].startswith('workspace_folder'):
                lines[i] = f'workspace_folder = {new_workspace_folder}\n'

        # Write the updated lines back to the config file
        with open(config_file_path, 'w') as config_file:
            config_file.writelines(lines)

        # Optionally, you can also show a message box or some feedback to the user
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully.")
        self.show_character_selection()  # Show character selection window after saving

    def show_character_selection(self):
        # Create a new window for character selection
        self.selection_window = QWidget()  # Store the window in an instance variable
        self.selection_window.setWindowTitle("Select Character")
        self.selection_window.setGeometry(300, 300, 600, 400)  # Adjust size as needed

        layout = QVBoxLayout()

        # List widget to display character folders
        char_list = QListWidget(self.selection_window)
        char_list.setFont(QFont("Arial", 12))
        char_list.addItems(["No selection"])

        # Load characters from the voice folder
        voice_folder = self.voice_input.text()
        if os.path.exists(voice_folder):
            characters = [d for d in os.listdir(voice_folder) if os.path.isdir(os.path.join(voice_folder, d))]
            char_list.addItems(characters)

        window_description = QLabel("Select a character to dub:", self.selection_window)
        window_description.setFont(QFont("Arial", 12))
        layout.addWidget(window_description)
        layout.addWidget(char_list)

        # Select button
        select_button = QPushButton("Select", self.selection_window)
        select_button.setFont(QFont("Arial", 16))
        select_button.clicked.connect(lambda: self.select_character(char_list.currentItem()))

        layout.addWidget(select_button)
        self.selection_window.setLayout(layout)  # Set the layout for the selection window
        self.selection_window.show()  # Show the selection window

    def select_character(self, selected_item):
        if selected_item.text() != "No selection":
            selected_character = selected_item.text()
            # Update character_voice_folder in config.ini (optional)
            config.edit('Settings', 'character_voice_folder', selected_character)
            QMessageBox.information(self, "Character Selected", f"You have selected: {selected_character}")
        else:
            selected_character = config.character
            QMessageBox.information(self, "No Character Selected",
                                    f"No character selected: {selected_character} has been selected by default")
        self.selection_window.close()
        config.import_settings()
        self.open_main_window()

    def open_main_window(self):
        workspace_character = config.workspace_folder + "/" + config.character
        workspace = FileManagement(workspace_character, log, config)
        workspace.create_folder_tree()
        self.main_window = MainWindow(self.voice_input.text(), self.work_input.text())
        self.main_window.show()
        self.close()


# Main Menu window
class MainWindow(QWidget):
    def __init__(self, char_folder, work_folder):
        super().__init__()
        self.dubbing_window = None
        self.voice_folder = config.config["Settings"]["voice_folder"]
        self.work_folder = config.config["Settings"]["workspace_folder"]
        self.character = config.config["Settings"]["character_voice_folder"]
        self.workspace_char_folder = self.work_folder + "/" + self.character
        self.dubbed_tracks = config.config["Static settings"]["dubbed_tracks"]
        self.voice_lines = config.config["Static settings"]["voice_lines"]
        self.extension = "." + config.config["Static settings"]["audio_format"]
        self.setWindowTitle("VoiceLineToolKit - Main Menu")
        self.setGeometry(200, 200, 1280, 720)  # 16:9 aspect ratio
        self.vo_fld_content = None
        self.selected_tracks = []
        self.init_ui()

    def init_ui(self):
        # Title and description labels
        title_label = QLabel("VoiceLineToolKit - V1.4", self)
        title_label.setFont(QFont("Arial", 30))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWindowIcon(QIcon('icon.ico'))

        description_label = QLabel(
            "Manage and process audio files for video game dubbing. Select an action below to proceed.", self)
        description_label.setFont(QFont("Arial", 14))
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)

        # Buttons with descriptions
        import_button = QPushButton("1: Import Audio Files", self)
        import_button.setFont(QFont("Arial", 16))
        #import_button.clicked.connect(self.import_audio_files)
        import_button.clicked.connect(self.import_original_vl)

        import_desc = QLabel("Import the original voice lines into the workspace for dubbing.", self)
        import_desc.setFont(QFont("Arial", 12))
        import_desc.setWordWrap(True)

        dubassist_button = QPushButton("2: Dubbing assist", self)
        dubassist_button.setFont(QFont("Arial", 16))
        dubassist_button.clicked.connect(self.dubbing_assist)

        dubassist_desc = QLabel("Let you see some advices on how to dub a specific line group (optional)", self)
        dubassist_desc.setFont(QFont("Arial", 12))
        dubassist_desc.setWordWrap(True)

        split_button = QPushButton("3: Split Audio Files", self)
        split_button.setFont(QFont("Arial", 16))
        split_button.clicked.connect(self.split_audio_files)

        split_desc = QLabel("Split your dubbed tracks into multiple audio files", self)
        split_desc.setFont(QFont("Arial", 12))
        split_desc.setWordWrap(True)

        enhance_button = QPushButton("4: Enhance Audio Files", self)
        enhance_button.setFont(QFont("Arial", 16))
        enhance_button.clicked.connect(self.enhance_audio)

        enhance_desc = QLabel("Enhance your voice lines with multiple effect (optional)", self)
        enhance_desc.setFont(QFont("Arial", 12))
        enhance_desc.setWordWrap(True)

        volume_button = QPushButton("5: Adjust volumes", self)
        volume_button.setFont(QFont("Arial", 16))
        volume_button.clicked.connect(self.adjust_volume)

        volume_desc = QLabel("Adjust the volume of your voice based on the original voice volume", self)
        volume_desc.setFont(QFont("Arial", 12))
        volume_desc.setWordWrap(True)

        push_button = QPushButton("6: Push Audio Files", self)
        push_button.setFont(QFont("Arial", 16))
        push_button.clicked.connect(self.push_interface)

        push_desc = QLabel("Replace the original voice files with the newly dubbed voices.", self)
        push_desc.setFont(QFont("Arial", 12))
        push_desc.setWordWrap(True)

        # Settings button
        settings_button = QPushButton("Settings", self)
        settings_button.setFont(QFont("Arial", 12))
        settings_button.clicked.connect(self.open_settings)

        # subtitle button
        log_button = QPushButton("Log file", self)
        log_button.setFont(QFont("Arial", 12))
        log_button.clicked.connect(self.open_logs)

        # Debug button
        self.debug_button = QPushButton("  ", self)
        self.debug_button.setFont(QFont("Arial", 10))
        self.debug_button.clicked.connect(self.debug_ui)
        # Change button background color based on status
        self.debug_button.setStyleSheet(f"background-color: {set_debug_status(log)}; color: white")

        # Layout for buttons and descriptions
        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(description_label)

        button_layout1 = QHBoxLayout()
        button_layout1.addWidget(import_button)
        button_layout1.addWidget(import_desc)

        button_layout2 = QHBoxLayout()
        button_layout2.addWidget(volume_button)
        button_layout2.addWidget(volume_desc)

        button_layout3 = QHBoxLayout()
        button_layout3.addWidget(split_button)
        button_layout3.addWidget(split_desc)

        button_layout4 = QHBoxLayout()
        button_layout4.addWidget(enhance_button)
        button_layout4.addWidget(enhance_desc)

        button_layout5 = QHBoxLayout()
        button_layout5.addWidget(push_button)
        button_layout5.addWidget(push_desc)

        button_layout6 = QHBoxLayout()
        button_layout6.addWidget(dubassist_button)
        button_layout6.addWidget(dubassist_desc)

        layout.addLayout(button_layout1)
        layout.addLayout(button_layout6)
        layout.addLayout(button_layout3)
        layout.addLayout(button_layout4)
        layout.addLayout(button_layout2)
        layout.addLayout(button_layout5)

        # Add the settings button to the top-right corner
        button_layout5 = QHBoxLayout()
        button_layout5.addStretch()
        button_layout5.addWidget(settings_button)
        layout.addLayout(button_layout5)

        # Add the Subtitle button
        button_layout5 = QHBoxLayout()
        button_layout5.addStretch()
        button_layout5.addWidget(log_button)
        layout.addLayout(button_layout5)
        self.debug_ui(update=True)
        self.setLayout(layout)

    def push_interface(self):
        log.write_log("\n\nINFO: Called function: Push interface")
        self.update_config()
        dialog = QDialog(self)
        dialog.setWindowTitle("Push settings")
        font = QFont("Arial", 14)
        dialog.setFont(font)
        dialog.setGeometry(300, 300, 650, 400)
        # ComboBox for character selection
        character_selection = QComboBox(dialog)
        character_selection.addItems([self.character])
        # Load characters from the voice folder
        try:
            if os.path.exists(self.voice_folder):
                characters = [d for d in os.listdir(self.voice_folder) if
                              os.path.isdir(os.path.join(self.voice_folder, d))]
                character_selection.addItems(characters)
        except Exception as e:
            log.write_log(f"WARN: Can't get characters from game files: {e}")
        # Checkbox in the secondary window
        pa_checkbox = QCheckBox("Push all *", dialog)
        da_checkbox = QCheckBox("Delete all **", dialog)
        # Button to confirm and close the dialog
        confirm_button = QPushButton("Confirm", dialog)
        # Label to show checkbox status
        status_label = QLabel("* Disabled: Code will push only the files that are existing in the game files\n"
                              "** Disabled: Code will delete only the dubbed voice lines in the game's folder",
                              dialog)

        # Function to update label when checkbox is toggled
        def on_checkbox_toggled():
            if pa_checkbox.isChecked() and da_checkbox.isChecked():
                status_label.setText("* Enabled: Code will push all your voice lines that are in your "
                                     "character voice lines folder\n"
                                     "** Enabled: Code will delete all original voicelines from the character\n "
                                     "            in the game's folder before pushing the new ones")
            elif not pa_checkbox.isChecked() and da_checkbox.isChecked():
                status_label.setText("* Disabled: Code will push only the files that are existing in the game files\n"
                                     "** Enabled: Code will delete all original voicelines from the character\n "
                                     "            in the game's folder before pushing the new ones")
            elif pa_checkbox.isChecked() and not da_checkbox.isChecked():
                status_label.setText("* Enabled: Code will push all your voice lines that are in your "
                                     "character voice lines folder\n"
                                     "** Disabled: Code will delete only the dubbed voice lines in the game's folder")
            else:
                status_label.setText("* Disabled: Code will push only the files that are existing in the game files\n"
                                     "** Disabled: Code will delete only the dubbed voice lines in the game's folder")

        pa_checkbox.toggled.connect(on_checkbox_toggled)
        da_checkbox.toggled.connect(on_checkbox_toggled)

        # Confirm button functionality
        def confirm_selection():
            selected_character = character_selection.currentText()
            push_all = pa_checkbox.isChecked()
            delete_all = da_checkbox.isChecked()
            # PUSH THE VOICE LINES
            self.push_audio_files(character=selected_character, push_all=push_all, delete_all=delete_all)
            dialog.accept()  # Close the dialog
            return None

        confirm_button.clicked.connect(confirm_selection)
        # Layout for the dialog
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a character where to push:", dialog))
        layout.addWidget(character_selection)
        layout.addWidget(pa_checkbox)
        layout.addWidget(da_checkbox)
        layout.addWidget(confirm_button)
        layout.addWidget(status_label)
        dialog.setLayout(layout)
        # Execute the dialog modal (blocks interaction with main window)
        dialog.exec()

    def update_config(self):
        config.import_settings()
        self.voice_folder = config.config["Settings"]["voice_folder"]
        self.work_folder = config.config["Settings"]["workspace_folder"]
        self.character = config.config["Settings"]["character_voice_folder"]
        self.workspace_char_folder = self.work_folder + "/" + self.character
        self.dubbed_tracks = config.config["Static settings"]["dubbed_tracks"]
        self.voice_lines = config.config["Static settings"]["voice_lines"]
        self.extension = "." + config.config["Static settings"]["audio_format"]
        log.write_log(f"INFO: Config values have been updated")

    def debug_ui(self, update=False):
        if not update:
            log.debug()
        status = set_debug_status(log)
        self.debug_button.setStyleSheet(f"background-color: {status}; color: white")
        return None

    def import_original_vl(self):
        log.write_log("\n\nINFO: Called function: Import Audio files")
        try:
            # Get voice lines groups from the game files
            path_vo = config.VO_folder + "/" + config.character
            vo_files = FileManagement(path_vo, logs=log, config=config)
            extension = "." + config.config["Static settings"]["audio_format"]
            self.vo_fld_content = vo_files.get_folder_content(file_filter=extension, raw=False)
            file_list = list(self.vo_fld_content.keys())
            # Check if original voice lines can be found and stop import if not
            if len(file_list) == 0:
                log.write_log(f"WARN: Folder '{path_vo}' seems empty, import has been stopped")
                QMessageBox.information(self, "Warning",
                                        f"Import can't start: check logs for more details."
                                        f"\nMake sure you have selected the right voice line folder in the game files")
                return None
            self.dubbing_window = SelectionWindow(items=file_list)
            if self.dubbing_window.exec():
                self.selected_tracks = self.dubbing_window.selected_items
            start_ = time.time()
            if len(self.selected_tracks) == 0:
                log.write_log(f"INFO: No selected items for import")
                return None
                # Clear blank tracks folder
            try:
                clear_directory(config.workspace_folder + "/" + config.character + config.blank_tracks)
            except Exception as e:
                log.write_log(f"WARN: Can't clear blank tracks directory: {e}")
            blank_tracks_folder = config.workspace_folder + "/" + config.character + config.blank_tracks
            saved_file, bad_file = 0, 0
            for file_name in self.selected_tracks:
                file = Audio(path="None", logs=log, config=config)
                success = file.save(output_folder=blank_tracks_folder, segments='empty', name=file_name)
                saved_file += 1 if success > 0 else 0
                bad_file += 1 if success == 0 else 0
            end_ = time.time()
            message = f'Import completed, {saved_file} files imported in {round(end_ - start_, 3)} seconds.'
            if bad_file > 0:
                message += f"\n{bad_file} files could not be imported. Check logs for more details."
            log.write_log(f"INFO: {message}")
            QMessageBox.information(self, "Information", f"{message}."
                                                         f"\nYou may now import the blank tracks from "
                                                         f"\n{blank_tracks_folder} to your favorite record software !")
            open_folder(blank_tracks_folder)
            self.debug_ui(update=True)
        except Exception as e:
            log.write_log("WARN: Exception occurred while importing files: ", e)
            QMessageBox.information(self, "Warning",
                                    f"import couldn't finish: check logs")
        return None

    def dubbing_assist(self):
        log.write_log(f"\n\nINFO: Function called: Dubbing assist")
        # Create the audio dict
        audio_dict = {}
        if len(self.selected_tracks) == 0:
            try:
                blank_tracks_folder_path = config.workspace_folder + "/" + config.character + config.blank_tracks
                blank_tracks_folder = FileManagement(blank_tracks_folder_path, logs=log, config=config)
                files_extension = "." + config.config["Static settings"]["audio_format"]
                blank_tracks_list = list(blank_tracks_folder.get_folder_content(raw=True, file_filter=files_extension))
                if len(blank_tracks_list) == 0:
                    log.write_log(f"WARN: Folder '{blank_tracks_folder_path}' seems empty, dub assistant can't start")
                    QMessageBox.information(self, "Warning",
                                            f"Dubbing assistant can't start: check logs for more details."
                                            f"\nMake sure you have imported files first")
                    self.debug_ui(update=True)
                    return None
                else:
                    for track in blank_tracks_list:
                        self.selected_tracks.append("".join(track.split(".")[:-1]))
            except Exception as e:
                log.write_log("WARN: Exception occurred while launching dub assistant files: ", e)
        if self.vo_fld_content is None:
            log.write_log(f"INFO: Retrieving files from the game files")
            try:
                vo_fld_path = config.VO_folder + "/" + config.character
                vo_fld = FileManagement(vo_fld_path, logs=log, config=config)
                files_extension = "." + config.config["Static settings"]["audio_format"]
                vo_file_dict = vo_fld.get_folder_content(raw=False, file_filter=files_extension)
                vo_file_list = list(vo_file_dict.keys())
                if len(vo_file_list) == 0:
                    log.write_log(f"WARN: Folder '{vo_fld_path}' seems empty, dub assistant can't start")
                    QMessageBox.information(self, "Warning",
                                            f"Dubbing assistant can't start: check logs for more details."
                                            f"\nMake sure you have selected the right voice line folder in the game "
                                            f"files")
                    self.debug_ui(update=True)
                    return None
                else:
                    self.vo_fld_content = vo_file_dict
            except Exception as e:
                log.write_log("WARN: Exception occurred while launching dub assistant files: ", e)
        try:
            for blank_track in self.selected_tracks:
                if blank_track in self.vo_fld_content:
                    audio_dict[blank_track] = self.vo_fld_content[blank_track]
            self.audio_window = AudioWindow(audio_dict)
            self.audio_window.show()
        except Exception as e:
            log.write_log("WARN: Exception occurred while launching dub assistant: ", e)
        self.debug_ui(update=True)

    def split_audio_files(self):
        log.write_log("\n\nINFO: Called function: splitting")
        try:
            self.update_config()
            stime = time.time()
            saved_number, pre_effect, pre_effect_scale = (0, config.config["Advanced Settings"]["pre_effect"],
                                                          config.config["Advanced Settings"]["pre_effect_scale"])
            workspace = FileManagement(self.workspace_char_folder + self.dubbed_tracks, logs=log, config=config)
            files = workspace.get_folder_content(file_filter='.ogg', raw=True)
            if len(files) == 0:
                log.write_log(f"WARN: Folder '{self.workspace_char_folder + self.dubbed_tracks}' seems empty, "
                              f"split function has been stopped."
                              f"\n     Make sure you exported the dubbed tracks in the right folder.")
                QMessageBox.information(self, "Warning",
                                        f"Split can't start: check logs for more details."
                                        f"\nMake sure you exported the dubbed tracks in the right folder.")
                return None
            for file in files:
                try:
                    audio_track = Audio(path=f'{self.workspace_char_folder}{self.dubbed_tracks}/{file}', logs=log,
                                        config=config)
                    ok = True
                    if len(audio_track.audio) < audio_track.sr * 0.5:
                        log.write_log(
                            f"WARN: file '{file}' seems empty ({len(audio_track.audio) / audio_track.sr}). File "
                            f"skipped. ")
                        ok = False
                    if len(pre_effect) > 1 and ok:
                        audio_track.apply_effect(effect=pre_effect, scale=pre_effect_scale)
                    if ok:
                        segments = audio_track.split_audio()
                        saved_number += audio_track.save(output_folder=self.workspace_char_folder + self.voice_lines,
                                                         segments=segments,
                                                         name='auto')
                except Exception as e:
                    log.write_log(f"WARN: Can't read {file}: ", e)
                    pass
            etime = time.time()
            message = f"Splitting completed in {round(etime - stime, 1)}s, {saved_number} files saved"
            log.write_log(f"INFO: {message}")
            QMessageBox.information(self, "Information", message)
            self.debug_ui(update=True)
        except Exception as e:
            log.write_log("WARN: Exception occurred while splitting files: ", e)
            QMessageBox.information(self, "Warning",
                                    f"Splitting couldn't finish: check log")
        return

    def adjust_volume(self):
        log.write_log("\n\nINFO: Called function: Adjust volumes")
        try:
            self.update_config()
            start_ = time.time()
            double_check = config.config["Advanced Settings"]["double_check_files"]
            work_folder = (self.work_folder + "/" +
                           self.character +
                           config.config["Static settings"]["voice_lines"])
            folder = FileManagement(path=work_folder, logs=log, config=config)
            files = folder.get_folder_content(raw=True, file_filter=None)
            if len(files) == 0:
                log.write_log(f"WARN: Folder '{self.workspace_char_folder + self.voice_lines}' seems empty, "
                              f"volume adjustment has been stopped."
                              f"\n     Make sure you used the split function before.")
                QMessageBox.information(self, "Warning",
                                        f"Volume adjustment can't start: check logs for more details."
                                        f"\nMake sure you clicked on the split function before trying to adjust the "
                                        f"volumes.")
                return None
            if double_check:
                check_audio_files(work_folder, l_log=log, l_config=config, auto_del=True)
            num = adjust_volume(log=log, l_config=config)
            end_ = time.time()
            message = f"{num} adjusted volume in {round(end_ - start_)} seconds"
            log.write_log(f"INFO: {message}")
            QMessageBox.information(self, "Information", message)
            self.debug_ui(update=True)
        except Exception as e:
            log.write_log("WARN: Exception occurred while adjusting volumes: ", e)
            QMessageBox.warning(self, "Error", "Exception occurred !")
        return

    def enhance_audio(self):
        log.write_log("\n\nINFO: Called function: Enhance audio")
        try:
            self.update_config()
            num = 0
            # Get dubbed voice lines
            folder = FileManagement(path=self.workspace_char_folder + "/" + self.voice_lines, logs=log,
                                    config=config)
            file_list = list(folder.get_folder_content(raw=True, file_filter=self.extension))
            if len(file_list) == 0:
                log.write_log(f"WARN: Folder '{self.workspace_char_folder + self.voice_lines}' seems empty, "
                              f"enhancement has been stopped."
                              f"\n     Make sure you used the split function before.")
                QMessageBox.information(self, "Error",
                                        f"Enhancement can't start: check logs for more details."
                                        f"\nMake sure you clicked on the split function before trying to enhance audio "
                                        f"files.")
                self.debug_ui(update=True)
                return None
            # open effect selection window
            available_settings = config.config["Static settings"]["all_effect"].split(" ")
            txt = ("Tips: the stable effect are:"
                   "\n          -Noise reduction"
                   "\n          -Band pass"
                   "\n          -Retrim"
                   "\n          -Sinus"
                   "\n          -Gain"
                   "\n          -Fade"
                   "\nYou can get additional information about the effects in the guides\n\n")
            selection_window = SelectionWindow(items=available_settings, additional_text=txt)
            if selection_window.exec() == QDialog.DialogCode.Accepted:
                selected_effects = selection_window.selected_items
                start_ = time.time()
                if not selected_effects or len(selected_effects) == 0:
                    QMessageBox.information(self, "Information", "No effects selected. Enhancement canceled.")
                    self.debug_ui(update=True)
                    return None
                for file_name in file_list:
                    file_path = self.workspace_char_folder + self.voice_lines + "/" + file_name
                    file = Audio(path=file_path, logs=log, config=config)
                    # Apply effect
                    for effect in selected_effects:
                        file.apply_effect(effect=effect)
                    file.save(output_folder=file.folder, name=file.name)
                    num += 1
                end_ = time.time()
                message = f"{num} files enhanced in {round(end_ - start_, 1)} seconds"
                log.write_log(f"INFO: {message}: ")
                QMessageBox.information(self, "Information", message)
                self.debug_ui(update=True)
            else:
                log.write_log("INFO: Enhancement process was canceled by the user.")
        except Exception as e:
            log.write_log("WARN: Exception occurred while enhancing audio files: ", e)
            QMessageBox.warning(self, "Error", "Exception occurred !")
        self.debug_ui(update=True)
        return

    def push_audio_files(self, character="Default", push_all=True, delete_all=False):
        log.write_log("\n\nINFO: Called function: Push audio files")
        try:
            missing_files = check_names(folder_path=self.workspace_char_folder + self.voice_lines,
                                        l_config=config, l_log=log)
            if len(missing_files) == 0:
                log.write_log(f"INFO: File naming complete, everything looks good.")
            else:
                log.write_log(f"INFO: Some files were missing, naming corrected\n"
                              f"      Missing files: {", ".join(missing_files)}")
        except Exception as e:
            log.write_log(f"WARN: Can't check file names: {e}")
        try:
            self.update_config()
            start_ = time.time()
            if character == "Default":
                character = self.character
            vl_folder_path = self.workspace_char_folder + self.voice_lines
            vo_folder_path = self.voice_folder + "/" + character
            check_names(folder_path=vl_folder_path, l_config=config, l_log=log)
            vl_fld = FileManagement(path=vl_folder_path, logs=log, config=config)
            vo_fld = FileManagement(path=vo_folder_path, logs=log, config=config)
            vl_files = vl_fld.get_folder_content(raw=False, file_filter=self.extension)
            if len(vl_files) == 0:
                log.write_log(f"WARN: {vl_folder_path} seems empty, stopping push"
                              f"\n     Make sure you have split the dubbed tracks before trying to push")
                QMessageBox.warning(self, "Error", f"Push can't start, "
                                                   f"check logs for more details"
                                                   f"\nMake sure you clicked on the split function before trying to "
                                                   f"push your voice lines.")
                return None
            vo_files = vo_fld.get_folder_content(raw=False, file_filter=self.extension)
            num, wrong, done = 0, [], False
            if delete_all:
                done = clear_directory(vo_folder_path)
                if done is not True:
                    log.write_log(f"WARN: {vo_folder_path} can't be cleared: {done}")
            for vl_base_name in vl_files:
                if vl_base_name in vo_files:
                    if not delete_all and done != True:
                        for file_name in vo_files[vl_base_name]:  # Remove the original files
                            os.remove(vo_folder_path + "/" + file_name)
                    for file_name in vl_files[vl_base_name]:  # Add the new files
                        shutil.copy(vl_folder_path + "/" + file_name, vo_folder_path + "/" + file_name)
                        num += 1
                else:
                    for file_name in vl_files[vl_base_name]:  # count number of wrong files
                        wrong.append(file_name)
                        if push_all:
                            shutil.copy(vl_folder_path + "/" + file_name, vo_folder_path + "/" + file_name)
                            num += 1
            end_ = time.time()
            add = ""
            if num == len(vl_files):
                add = "(all) "
            message = f'{num} {add}files were pushed in the game files in {round(end_ - start_, 2)} seconds.'
            if len(wrong) > 0:
                message += f' {len(wrong)} files seem to not exist in the game files, check log for more details.'
            log.write_log(f"INFO: {message}.\n "
                          f"      Not original files: {', '.join(wrong)}")
            QMessageBox.information(self, "Information", message)
            self.debug_ui(update=True)
        except Exception as e:
            log.write_log(f"WARN: could not push, ", e)
            QMessageBox.warning(self, "Error", f"Exception occurred ! {e}")
        return

    def open_settings(self):
        log.write_log("INFO: Called function: Open Settings")
        # Open the config.ini file with the default application
        try:
            os.startfile(config.path)  # For Windows
            log.write_log("INFO: Settings opened successfully")
            self.debug_ui(update=True)
        except Exception as e:
            log.write_log("WARN: Settings couldn't open, ", e)
            QMessageBox.warning(self, "Error", f"Can't open settings. {e}")
        return

    def open_logs(self):
        self.update_config()
        log.write_log("INFO: Called function: Open log file")
        try:
            os.startfile(log.path)
            log.write_log("INFO: log file opened")
            self.debug_ui(update=True)
        except Exception as e:
            log.write_log(f"WARN: Errors while opening log file: {e}")
            QMessageBox.warning(self, "Error", f"Errors while opening log file: {e}")
        return


# Window with checkboxes list
class SelectionWindow(QDialog):
    def __init__(self, items, additional_text=None):
        super().__init__()
        self.setWindowTitle("Select elements")
        self.setGeometry(200, 200, 400, 700)
        self.items = items
        self.additional_text = additional_text
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # additional text
        add_text = QLabel(self.additional_text, self)
        add_text.setFont(QFont("Arial", 12))
        #add_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_text.setWordWrap(True)
        if self.additional_text is not None:
            layout.addWidget(add_text)

        # "Select All" checkbox
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.setFont(QFont("Arial", 10))
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        layout.addWidget(self.select_all_checkbox)

        # Scrollable area for checkboxes
        scroll_area = QScrollArea(self)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.checkboxes = []
        for item in self.items:
            checkbox = QCheckBox(item)
            checkbox.setFont(QFont("Arial", 10))
            checkbox.stateChanged.connect(self.update_select_all_state)
            scroll_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # butons
        button_layout = QHBoxLayout()
        validate_button = QPushButton("Continue")
        #cancel_button = QPushButton("Cancel")
        validate_button.clicked.connect(self.validate)
        #cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(validate_button)
        #button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def toggle_select_all(self):
        is_checked = self.select_all_checkbox.isChecked()
        for checkbox in self.checkboxes:
            checkbox.blockSignals(True)  # Disable all signals to avoid infinite loop
            checkbox.setChecked(is_checked)
            checkbox.blockSignals(False)  # enable back the signals

    def update_select_all_state(self):
        checked_count = sum(checkbox.isChecked() for checkbox in self.checkboxes)
        # Lock other signal to avoid interference
        self.select_all_checkbox.blockSignals(True)
        # Update 'Select All' state
        if checked_count == len(self.checkboxes):
            self.select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        elif checked_count == 0:
            self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        # Reactivate all signal
        self.select_all_checkbox.blockSignals(False)

    def validate(self):
        self.selected_items = [checkbox.text() for checkbox in self.checkboxes if checkbox.isChecked()]
        self.accept()


class AudioWindow(QWidget):
    def __init__(self, audio_dict):
        super().__init__()
        # get the subtitle data
        sub_path = config.VO_folder + "/" + config.character + "/" + config.config["Static settings"]["sub_file_name"]
        self.subtitles = get_subtitles(sub_path, ",")
        self.audio_ext = "." + config.config["Static settings"]["audio_format"]

        self.setWindowTitle("Audio Player")
        self.setGeometry(300, 300, 400, 200)

        # Store audio dictionary
        self.audio_dict = audio_dict
        self.current_key_index = 0  # Index for current key in the dictionary
        self.current_audio_index = 0  # Index for current audio in the list of the key
        self.keys = list(audio_dict.keys())  # List of dictionary keys

        # Labels and buttons
        font = QFont("Arial", 14)
        self.text_label = QLabel(self)
        self.text_label.setFont(font)
        self.update_text_label()
        self.info_label = QLabel("Additional Info", self)
        self.listen_button = QPushButton("Listen", self)
        self.listen_button.clicked.connect(self.play_audio)
        self.next_button = QPushButton("Next", self)
        self.next_button.clicked.connect(self.next_key)
        self.previous_button = QPushButton("Previous", self)
        self.previous_button.clicked.connect(self.previous_key)
        self.cycle_button = QPushButton("Cycle", self)
        self.cycle_button.clicked.connect(self.cycle_audio)

        # Layout setup
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.previous_button)
        button_layout.addWidget(self.cycle_button)
        button_layout.addWidget(self.next_button)

        layout = QVBoxLayout()
        layout.addWidget(self.text_label)
        layout.addWidget(self.info_label)
        layout.addWidget(self.listen_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_text_label(self):
        try:
            current_key = self.keys[self.current_key_index]
            current_audio = self.audio_dict[current_key][self.current_audio_index][:-len(self.audio_ext)]
            add = ""
            if isinstance(self.subtitles, dict):
                if current_audio in self.subtitles:
                    print(self.subtitles[current_audio])
                    add = (f'\nLine: {"".join(self.subtitles[current_audio][0:-1])}'
                           f'\nContext: {self.subtitles[current_audio][-1]}')
                else:
                    add = "\nNo info for this line"
            self.text_label.setText(f"Line: {current_key}\nAudio: {current_audio}\n" + add)
        except Exception as e:
            log.write_log("WARN: Dub assist, can't update text label: ", e)

    def play_audio(self):
        try:
            current_key = self.keys[self.current_key_index]
            current_audio = self.audio_dict[current_key][self.current_audio_index]
            current_path = config.VO_folder + "/" + config.character + "/" + current_audio
            log.write_log(f"INFO: Request for playing audio file: {current_path}")

            if os.path.exists(current_path):  # Ensure the file exists
                try:
                    # Open the audio file using the default player (e.g., Windows Media Player)
                    os.startfile(current_path)
                except Exception as e:
                    self.info_label.setText(f"Error playing audio: {e}")
            else:
                self.info_label.setText(f"Audio file {current_audio} not found.")
        except Exception as e:
            log.write_log("WARN: Can't play audio file: ", e)

    def next_key(self):
        try:
            if self.current_key_index < len(self.keys) - 1:
                self.current_key_index += 1
            else:
                self.current_key_index = 0  # Loop back to the first key

            self.current_audio_index = 0  # Reset audio index when switching keys
            self.update_text_label()
        except Exception as e:
            log.write_log("WARN: Can't get to the next track group: ", e)

    def previous_key(self):
        try:
            if self.current_key_index > 0:
                self.current_key_index -= 1
            else:
                self.current_key_index = len(self.keys) - 1  # Loop to the last key

            self.current_audio_index = 0  # Reset audio index when switching keys
            self.update_text_label()
        except Exception as e:
            log.write_log("WARN: Can't get to the previous track group: ", e)

    def cycle_audio(self):
        try:
            current_key = self.keys[self.current_key_index]
            if self.current_audio_index < len(self.audio_dict[current_key]) - 1:
                self.current_audio_index += 1
            else:
                self.current_audio_index = 0  # Loop back to the first audio

            self.update_text_label()
        except Exception as e:
            log.write_log("WARN: Can't cycle through the line names: ", e)
