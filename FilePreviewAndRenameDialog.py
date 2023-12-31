from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox, QLabel, QFileDialog, QDialog, QHBoxLayout, QLineEdit, QProgressBar, QInputDialog, QDateEdit, QDialogButtonBox, QRadioButton, QGroupBox, QCheckBox, QListWidget, QTreeWidget, QTreeWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QDate, QObject, pyqtSignal, QThread
from PyQt5.QtGui import QPalette, QColor
from datetime import datetime
import os
import shutil
import win32api
import win32file
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'

class FilePreviewAndRenameDialog(QDialog):

    def __init__(self, selected_drive, parent=None):
        super().__init__(parent)

        # 1. Initialize attributes
        self.drive = selected_drive
        self.folder = self.drive
        self.files = []
        self.current_file_index = 0

        self.file_label = QLabel("Initializing...")  
        self.path_label = QLabel(f"Current Path: {selected_drive}")

        self.populate_files_list()

        layout = QVBoxLayout()

        # File label, delete button, and path label setup
        file_path_layout = QVBoxLayout()

        file_button_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        file_button_layout.addWidget(self.file_label)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_current_file)
        file_button_layout.addWidget(self.delete_button)
        
        browse_path_layout = QHBoxLayout()
        self.path_label = QLabel(f"Current Path: {self.drive}")
        browse_path_layout.addWidget(self.path_label)
        
        browse_button = QPushButton('Browse')
        browse_button.clicked.connect(self.browse_files)
        browse_path_layout.addWidget(browse_button)

        file_path_layout.addLayout(file_button_layout)
        file_path_layout.addLayout(browse_path_layout)

        layout.addLayout(file_path_layout)

        self.origin_label = QLabel("Origin Path: Not selected")
        layout.addWidget(self.origin_label)

        preview_button = QPushButton('Preview File')
        preview_button.clicked.connect(self.preview_file)
        layout.addWidget(preview_button)

        category_group = QGroupBox("Select Category:")
        category_layout = QHBoxLayout()
        self.category_buttons = {'car': QRadioButton('car'), 'beach': QRadioButton('beach'), 'water': QRadioButton('water'), 'other': QRadioButton('other')}
        for button in self.category_buttons.values():
            button.toggled.connect(self.category_button_toggled)
            category_layout.addWidget(button)
        self.other_input = QLineEdit()
        self.other_input.setEnabled(False)
        category_layout.addWidget(self.other_input)
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)

        additional_info_group = QGroupBox("Additional Information:")
        additional_info_layout = QHBoxLayout()

        self.origin_path_checkbox = QCheckBox('Origin Path')
        self.origin_path_checkbox.setChecked(True)  # Set the checkbox to be checked by default
        additional_info_layout.addWidget(self.origin_path_checkbox)

        self.additional_info_input = QLineEdit()
        additional_info_layout.addWidget(self.additional_info_input)
        additional_info_group.setLayout(additional_info_layout)
        layout.addWidget(additional_info_group)

        date_group = QGroupBox("Select Date:")
        date_layout = QHBoxLayout()
        self.date_picker = QDateEdit()
        self.today_button = QRadioButton("Today's Date")
        self.today_button.setChecked(True)  # Set the radio button to be checked by default
        self.today_button.toggled.connect(self.date_option_toggled)
        date_layout.addWidget(self.date_picker)
        date_layout.addWidget(self.today_button)

        self.create_dir_button = QPushButton('Create a directory?')
        self.create_dir_button.clicked.connect(self.create_directory)
        self.create_dir_button.setEnabled(False)
        self.create_dir_button.setToolTip("Browse a folder and select a date to enable this option.")
        date_layout.addWidget(self.create_dir_button)

        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        button_layout = QHBoxLayout()

        rename_button = QPushButton('Rename File')
        rename_button.clicked.connect(self.rename_file)
        rename_button.setStyleSheet("QPushButton { background-color: darkgreen; color: white; } QPushButton:hover { background-color: green; }")
        layout.addWidget(rename_button)

        skip_button = QPushButton('Skip File')
        skip_button.clicked.connect(self.skip_file)
        button_layout.addWidget(skip_button)

        exit_button = QPushButton('Exit')
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    
        self.renamed_files_count = 0
        self.skipped_files_count = 0
    def populate_files_list(self):
        # Use os.listdir to obtain a list of files in the initial folder
        try:
            self.files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
            self.update_file_label()
        except OSError:
            # Handle any potential errors
            self.files = []
            self.file_label.setText("No files found or error reading directory")
            self.path_label.setText(f"Current Path: {self.folder}")

    def preview_file(self):
        if self.files and self.current_file_index < len(self.files):
            file_path = os.path.join(self.folder, self.files[self.current_file_index])
            os.startfile(file_path)

    def delete_current_file(self):
        if self.files and 0 <= self.current_file_index < len(self.files):
            file_to_delete = os.path.join(self.folder, self.files[self.current_file_index])

            confirmation = QMessageBox.question(self, 'Confirm Deletion', 'Are you sure you want to delete this file?', QMessageBox.Yes | QMessageBox.No)
            if confirmation == QMessageBox.Yes:
                try:
                    os.remove(file_to_delete)
                    del self.files[self.current_file_index]
                    if self.current_file_index == len(self.files):
                        self.current_file_index -= 1
                    self.update_file_label()
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Failed to delete the file due to: {str(e)}', QMessageBox.Ok)

    def category_button_toggled(self):
        self.other_input.setEnabled(self.category_buttons['other'].isChecked())

    def date_option_toggled(self, checked):
        self.date_picker.setEnabled(not checked)

    def check_create_dir_button_status(self):
        if self.folder and (self.date_picker.isEnabled() or self.today_button.isChecked()):
            self.create_dir_button.setEnabled(True)
        else:
            self.create_dir_button.setEnabled(False)

    def browse_files(self):
        self.folder = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if self.folder:
            self.files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
            self.current_file_index = 0
            self.update_file_label()
        else:
            self.file_label.setText("No files in the selected folder")
            self.path_label.setText("No path selected")

        drive_letter = os.path.splitdrive(self.folder)[0] + '\\'
        volume_name = win32api.GetVolumeInformation(drive_letter)[0]
        if volume_name:
            self.origin_label.setText(f"Origin Path: {volume_name}")
        else:
            self.origin_label.setText("Origin Path: Unknown")
        self.check_create_dir_button_status()

    def date_option_toggled(self, checked):
        self.date_picker.setEnabled(not checked)
        self.check_create_dir_button_status()

    def create_directory(self):
        selected_date = self.date_picker.date().toString("yyyy-MM-dd") if not self.today_button.isChecked() else datetime.today().date().strftime("%Y-%m-%d")
        new_dir_path = os.path.join(self.folder, selected_date)
    
        if not os.path.exists(new_dir_path):
            os.mkdir(new_dir_path)
            QMessageBox.information(self, 'Directory Created', f'Directory named {selected_date} created successfully.', QMessageBox.Ok)
        else:
            QMessageBox.warning(self, 'Directory Exists', f'Directory named {selected_date} already exists.', QMessageBox.Ok)

    def rename_file(self):
        if self.files:
            selected_category = next((key for key, button in self.category_buttons.items() if button.isChecked()), None)
            if selected_category == 'other':
                selected_category = self.other_input.text()
            
            origin_path = self.origin_label.text().replace("Origin Path: ", "") if self.origin_path_checkbox.isChecked() else ""
            
            selected_date = self.date_picker.date().toString("yyyy-MM-dd") if not self.today_button.isChecked() else datetime.today().date().strftime("%Y-%m-%d")
            old_filename = self.files[self.current_file_index]
            additional_information = self.additional_info_input.text()
            
            new_filename_parts = [selected_date, selected_category, origin_path, additional_information, old_filename]
            new_filename = ' '.join(part for part in new_filename_parts if part)
            
            confirmation = QMessageBox.question(self, 'Confirm Rename', 'Are you sure you want to rename the file?', QMessageBox.Yes | QMessageBox.No)
            if confirmation == QMessageBox.No:
                return

            self.worker2 = RenameWorker2(self.folder, old_filename, new_filename)
            self.thread = QThread()
            self.worker2.moveToThread(self.thread)

            self.worker2.rename_error.connect(lambda e: QMessageBox.critical(self, 'Error', e, QMessageBox.Ok))
            self.worker2.rename_success.connect(self.on_rename_success)

            self.thread.started.connect(self.worker2.run)
            self.thread.start()

    def on_rename_success(self):
        self.renamed_files_count += 1
        self.files[self.current_file_index] = self.worker2.new_filename
        if self.files and self.current_file_index < len(self.files) - 1:
            self.current_file_index += 1
        self.update_file_label()
        self.thread.quit()
        self.thread.wait()
        self.worker2.deleteLater()
        self.thread.deleteLater()

    def skip_file(self):
        if self.files:
            if self.current_file_index < len(self.files) - 1:
                self.skipped_files_count += 1
                self.current_file_index += 1
                self.update_file_label()
            else:
                # Display feedback to the user if all files have been skipped
                QMessageBox.information(self, "All Files Skipped", "You have skipped all files inside the folder.")

    def update_file_label(self):
        if self.current_file_index < len(self.files):
            self.file_label.setText(f'Current File: <b>{self.files[self.current_file_index]}</b>')
            self.path_label.setText(f'Current Path: {os.path.join(self.folder, self.files[self.current_file_index])}')
        else:
            QMessageBox.information(self, 'Process Finished',
                                    f'All files processed. Renamed: {self.renamed_files_count}. Skipped: {self.skipped_files_count}.',
                                    QMessageBox.Ok)
            self.file_label.setText("No files left to process")
            self.path_label.setText("No path selected")
            self.reset()

    def reset(self):
        self.folder = ''
        self.files = []
        self.current_file_index = 0
        self.renamed_files_count = 0
        self.skipped_files_count = 0
        self.other_input.clear()

class RenameWorker2(QObject):
    rename_error = pyqtSignal(str)
    rename_success = pyqtSignal()

    def __init__(self, folder, old_filename, new_filename):
        super().__init__()
        self.folder = folder
        self.old_filename = old_filename
        self.new_filename = new_filename

    def run(self):
        try:
            os.rename(os.path.join(self.folder, self.old_filename), os.path.join(self.folder, self.new_filename))
            self.rename_success.emit()
        except Exception as e:
            self.rename_error.emit(str(e))

class AutoFileApp(QWidget):
    def __init__(self):
        super().__init__()

        # Increase the size of the interface
        self.resize(600, 200)

        # Add window title
        self.setWindowTitle('autoFile')

        # Create a QVBoxLayout instance for the entire window
        self.main_layout = QVBoxLayout()

        # Add the modified welcome message
        self.welcome_label = QLabel("Search for drives?")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.welcome_label)

        # Add the "Search Drives" button below the welcome message
        self.search_button = QPushButton("Search Drives")
        self.search_button.setStyleSheet("QPushButton { background-color: darkgreen; color: white; } QPushButton:hover { background-color: green; }")
        self.search_button.clicked.connect(self.safe_wrapper(self.on_search_button_clicked))
        self.main_layout.addWidget(self.search_button)

        # Placeholder for the drives group
        self.drive_group_box = QGroupBox("Available Drives")
        self.drive_layout = QVBoxLayout()
        self.drive_group_box.setLayout(self.drive_layout)
        self.main_layout.addWidget(self.drive_group_box)
        self.drive_group_box.hide()  # Hide initially

        # Add buttons with custom names for Main Interface
        main_button_names = ['Preview and Rename Files', 'Copy Files', 'Delete Files']
        for i in range(3):
            button = QPushButton(main_button_names[i])
            button.setStyleSheet("QPushButton { background-color: darkgreen; color: white; } QPushButton:hover { background-color: green; }")
            button.clicked.connect(self.safe_wrapper(lambda checked, i=i: self.on_button_clicked(i + 1)))
            self.main_layout.addWidget(button)

        # Set the layout
        self.setLayout(self.main_layout)

        # Connect the close event to the custom exit method
        self.closeEvent = self.on_exit_clicked

    def safe_wrapper(self, func):
        """ Wrap slots to catch and display exceptions. """
        def wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

        return wrapped

    def get_selected_drive(self):
        for i in range(self.drive_layout.count()):
            widget = self.drive_layout.itemAt(i).widget()
            if widget is not None and isinstance(widget, QRadioButton) and widget.isChecked():
                return widget.text().split(' ')[0]  # Extracting the drive letter from the text
        return None

    def on_search_button_clicked(self, _=None):  # Add an extra argument here
        # Clear any previous radio buttons
        for _ in range(self.drive_layout.count()):
            widget = self.drive_layout.itemAt(0).widget()
            if widget is not None:
                widget.deleteLater()

        # Detect available drives
        drives = self.detect_drives()

        # Display detected drives as radio buttons
        self.display_drive_radios(drives)
        self.selected_drive = self.get_selected_drive()

    def detect_drives(self):
        drives = [f"{d}:\\" for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f"{d}:\\")]
        drive_names = []

        for drive in drives:
            if win32file.GetDriveType(drive) in [win32file.DRIVE_REMOVABLE, win32file.DRIVE_FIXED]:
                try:
                    # Fetch volume name
                    volume_name, _, _, _, _ = win32api.GetVolumeInformation(drive)
                    if not volume_name:
                        volume_name = "No Label"
                    drive_names.append(f"{drive} ({volume_name})")
                except Exception as e:
                    if "The device is not ready" in str(e):
                        drive_names.append(f"{drive} (Device Not Ready)")
                    else:
                        drive_names.append(drive)

        return drive_names

    def display_drive_radios(self, drives):
      """Display detected drives as radio buttons."""
      if drives:
          for drive in drives:
              radio = QRadioButton(drive)
              self.drive_layout.addWidget(radio)

          # Assuming the first radio button is selected by default
          self.drive_layout.itemAt(0).widget().setChecked(True)
          self.selected_drive = self.get_selected_drive()

          self.drive_group_box.show()  # Show the drives group box
          self.update()

    def on_button_clicked(self, button_num):
        selected_drive = self.get_selected_drive()
        if not selected_drive:
            QMessageBox.critical(self, "Error", "Please select a drive first.")
            return

        if button_num == 1:
            self.file_preview_and_rename_dialog = FilePreviewAndRenameDialog(selected_drive, self)
            self.file_preview_and_rename_dialog.show()
        elif button_num == 2:
            self.file_mover_dialog = FileCopierDialog(self)
            self.file_mover_dialog.show()
        elif button_num == 3:
            self.file_mover_dialog = FileDeleterDialog(self)
            self.file_mover_dialog.show()

    def on_exit_clicked(self, event=None):
        QApplication.instance().quit()
        
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = AutoFileApp()
    window.show()
    sys.exit(app.exec_())
    