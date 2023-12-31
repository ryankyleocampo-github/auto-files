from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox, QLabel, QFileDialog, QDialog, QHBoxLayout, QLineEdit, QProgressBar, QInputDialog, QDateEdit, QDialogButtonBox, QRadioButton, QGroupBox, QCheckBox, QListWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QMainWindow, QGridLayout, QFrame, QScrollArea, QSizePolicy, QButtonGroup, QProgressDialog, QComboBox
from PyQt5.QtCore import Qt, QDate, QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QPalette, QColor, QFontMetrics, QFont
from datetime import datetime
import os
import sys
import shutil
import win32api
import win32con
import win32file
import pickle
import time
import os.path
import logging
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from twilio.rest import Client

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'

class BrowseButton(QWidget):

    folderSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        instruction_label = QLabel("Step 1: Select a camera type to detect the drive.")
        instruction_label.setWordWrap(True)  
        font = instruction_label.font()
        font.setPointSize(font.pointSize() + 4)  
        instruction_label.setFont(font)
        instruction_label.setStyleSheet("QLabel { color: blue; font-weight: lightbold }")
        
        # Create the camera type button
        self.browse_button = QPushButton('Camera Type')
        self.browse_button.setStyleSheet("QPushButton { background-color: darkgreen; color: white; } QPushButton:hover { background-color: green; }")
        self.browse_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browse_button.clicked.connect(self.select_camera_type)

        # Create the optional browse button
        self.optional_browse_button = QPushButton('Optional: Choose a Directory')
        self.optional_browse_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.optional_browse_button.clicked.connect(self.optional_browse)

        # Create a QVBoxLayout to add the label on top and buttons side by side below
        main_layout = QVBoxLayout()
        main_layout.addWidget(instruction_label)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.browse_button)
        button_layout.addWidget(self.optional_browse_button)
        
        main_layout.addLayout(button_layout)
        
        # Add a horizontal separator
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Remove margins
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.setLayout(main_layout)

    def select_camera_type(self):
        choices = ['GOPRO11M', 'GOPRO11B', 'INSTA360', 'Window Storage']
        
        dialog = QInputDialog(self)
        dialog.setWindowTitle('Drive')
        dialog.setLabelText('Camera Type:')
        dialog.setComboBoxItems(choices)
        dialog.resize(500, 300)  # Adjust width and height as needed
        
        if dialog.exec_() == QDialog.Accepted:
            camera_type = dialog.textValue()
            if camera_type == 'GOPRO11M':
                self.select_gopro11m_drive()
            elif camera_type == 'GOPRO11B':
                self.select_gopro11b_drive()
            elif camera_type == 'INSTA360':
                self.select_insta360_drive()
            elif camera_type == 'Window Storage':
                self.select_window_storage()

    def select_gopro11m_drive(self):
        drives = self.get_drives_with_volume_name('GoPro11M')
        if not drives:
            QMessageBox.warning(self, 'Warning', 'No GoPro11M drives found!')
            return

        # Construct the path based on the detected drive letter
        target_path = os.path.join(drives[0], 'DCIM', '100GOPRO')

        if os.path.exists(target_path):
            self.folderSelected.emit(target_path)
        else:
            QMessageBox.warning(self, 'Warning', f'No directory found at {target_path}!')

    def select_gopro11b_drive(self):
        drives = self.get_drives_with_volume_name('GoPro11B')
        if not drives:
            QMessageBox.warning(self, 'Warning', 'No GoPro11B drives found!')
            return

        target_path = os.path.join(drives[0], 'DCIM', '100GOPRO')

        if os.path.exists(target_path):
            self.folderSelected.emit(target_path)
        else:
            QMessageBox.warning(self, 'Warning', f'No directory found at {target_path}!')
    
    def select_insta360_drive(self):
        drives = self.get_drives_with_volume_name('InstaX31')
        if not drives:
            QMessageBox.warning(self, 'Warning', 'No INSTA360 drives found!')
            return

        target_path = os.path.join(drives[0], 'DCIM', 'Camera01')

        if os.path.exists(target_path):
            self.folderSelected.emit(target_path)
        else:
            QMessageBox.warning(self, 'Warning', f'No directory found at {target_path}!')

    def select_window_storage(self):  
        drives = self.get_drives_with_volume_name('Windows-SSD')
        if not drives:
            QMessageBox.warning(self, 'Warning', 'No Windows-SSD drives found!')
            return
        
        target_path = os.path.join(drives[0], 'Test', 'TEST')
        
        if os.path.exists(target_path):
            self.folderSelected.emit(target_path)
        else:
            QMessageBox.warning(self, 'Warning', f'No directory found at {target_path}!')
    
    def get_drives_with_volume_name(self, keyword):
        drives = [drive for drive in win32api.GetLogicalDriveStrings().split('\x00') if drive]
        matched_drives = []
        for drive in drives:
            try:
                if keyword in win32api.GetVolumeInformation(drive)[0]:
                    matched_drives.append(drive)
            except Exception as e:
                pass  
        return matched_drives
    
    def optional_browse(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder_path:  
            self.folderSelected.emit(folder_path)

class FilePreviewAndRenameDialog(QWidget):
    datedFolderCreated = pyqtSignal(str)
    folderCreated = pyqtSignal(str)
    def __init__(self, browse_button_widget=None, parent=None):
        super().__init__(parent)

        self.folder = ''  
        self.files = []
        self.current_file_index = 0

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  
        layout.setSpacing(10)  

        # Use the passed browse_button_widget
        self.browse_button_widget = browse_button_widget
        layout.addWidget(self.browse_button_widget)

        instruction_label = QLabel("Step 2: Preview and rename the files.")
        instruction_label.setWordWrap(True)  
        font = instruction_label.font()
        font.setPointSize(font.pointSize() + 4)  
        instruction_label.setFont(font)
        instruction_label.setStyleSheet("QLabel { color: blue; }")
        layout.addWidget(instruction_label)

        file_label_buttons_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        file_label_buttons_layout.addWidget(self.file_label)

        # Create a QGridLayout for the buttons and labels
        grid_layout = QGridLayout()

        # Add the existing file label
        self.file_label = QLabel("No file selected")
        grid_layout.addWidget(self.file_label, 0, 0)

        # Add existing 'Preview File' and 'Delete' buttons
        preview_button = QPushButton('Preview File')
        preview_button.clicked.connect(self.preview_file)
        grid_layout.addWidget(preview_button, 0, 1)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_current_file)
        self.delete_button.setStyleSheet("QPushButton { background-color: darkred; color: white; } QPushButton:hover { background-color: red; }")
        grid_layout.addWidget(self.delete_button, 0, 2)

        # Add new 'Rename File' and 'Skip File' buttons on the next row, but in the same columns as the existing buttons
        rename_button = QPushButton('Rename File')
        rename_button.clicked.connect(self.rename_file)
        rename_button.setStyleSheet("QPushButton { background-color: darkgreen; color: white; } QPushButton:hover { background-color: green; }")
        grid_layout.addWidget(rename_button, 1, 1)

        skip_button = QPushButton('Skip File')
        skip_button.clicked.connect(self.skip_file)
        grid_layout.addWidget(skip_button, 1, 2)

        # Add the grid layout to the main layout
        layout.addLayout(grid_layout)

        # Create a horizontal layout to contain the "Origin Storage" and "Current Path" labels
        info_layout = QHBoxLayout()

        self.origin_label = QLabel("Origin Storage: Not selected")
        self.origin_label.setStyleSheet("QLabel { font-weight: bold; }")  # Set text to bold
        info_layout.addWidget(self.origin_label)  # Add to the horizontal layout

        # Add a spacer to create some space between the labels
        info_layout.addSpacing(20)

        self.path_label = QLabel("Current Path: Not initialized")
        self.path_label.setStyleSheet("QLabel { font-weight: bold; }")  # Set text to bold
        info_layout.addWidget(self.path_label)  # Add to the horizontal layout

        # Add the horizontal layout to the main layout
        layout.addLayout(info_layout)

        self.modified_date_label = QLabel("Date Modified: Not initialized")
        layout.addWidget(self.modified_date_label)

        self.browse_button_widget.folderSelected.connect(self.on_folder_selected)

        category_group = QGroupBox("Step 3: Select Category for File Rename Format")
        category_group.setStyleSheet("QGroupBox { font-size: 22px; font-weight: lightbold; color: blue; }")
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

        additional_info_layout = QHBoxLayout()

        self.origin_path_checkbox = QCheckBox('Origin Storage')
        self.origin_path_checkbox.setChecked(True)  
        additional_info_layout.addWidget(self.origin_path_checkbox)

        additional_info_label = QLabel("Additional Information:")
        additional_info_layout.addWidget(additional_info_label)

        self.additional_info_input = QLineEdit()
        additional_info_layout.addWidget(self.additional_info_input)

        layout.addLayout(additional_info_layout)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        date_group = QGroupBox("Step 4: Select a date")
        date_group.setStyleSheet("QGroupBox { font-size: 22px; font-weight: lightbold; color: blue; }")
        date_layout = QHBoxLayout()
        self.date_picker = QDateEdit()
        self.date_picker.setDisplayFormat("yyyy-MM-dd") 
        self.date_picker.setDate(QDate.currentDate())  
        self.today_button = QRadioButton("Today's Date")
        self.today_button.setChecked(True)
        self.today_button.toggled.connect(self.date_option_toggled)
        date_layout.addWidget(self.date_picker)
        date_layout.addWidget(self.today_button)

        self.create_dir_button = QPushButton('Create date directory on SD card?')
        self.create_dir_button.clicked.connect(self.create_directory)
        self.create_dir_button.setEnabled(False)
        self.create_dir_button.setToolTip("Browse a folder and select a date to enable this option.")
        date_layout.addWidget(self.create_dir_button)

        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        instruction_label = QLabel("Step 5: Create a directory on the SD card with the selected date and camera type.")
        instruction_label.setWordWrap(True)  
        font = instruction_label.font()
        font.setPointSize(font.pointSize() + 4)  
        instruction_label.setFont(font)
        instruction_label.setStyleSheet("QLabel { color: blue; }")
        layout.addWidget(instruction_label)

        self.camera_radio_group = QButtonGroup(self)  
        self.gopro_radio = QRadioButton('GOPRO')
        self.insta360_radio = QRadioButton('INSTA360')
        self.gopro_radio.setChecked(True)  

        self.camera_radio_group.addButton(self.gopro_radio)
        self.camera_radio_group.addButton(self.insta360_radio)

        camera_radio_layout = QHBoxLayout()
        camera_radio_layout.addWidget(self.gopro_radio)
        camera_radio_layout.addWidget(self.insta360_radio)
        layout.addLayout(camera_radio_layout)
        
        create_dir_button_layout = QHBoxLayout()
        create_dir_button_layout.addWidget(self.create_dir_button)
        create_dir_button_layout.addStretch(1) 
        layout.addLayout(create_dir_button_layout)

        self.setLayout(layout)

        self.renamed_files_count = 0
        self.skipped_files_count = 0

        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

    def has_subfolders(self, dir_path, subfolder_names):
        return all(os.path.exists(os.path.join(dir_path, name)) for name in subfolder_names)
    
    def populate_files_list(self):
        try:
            self.files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
            self.update_file_label()
        except OSError:
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

    def check_create_dir_button_status(self):
        if self.folder and (self.date_picker.isEnabled() or self.today_button.isChecked()):
            selected_date = self.date_picker.date().toString("yyyy-MM-dd") if not self.today_button.isChecked() else datetime.today().date().strftime("%Y-%m-%d")
            new_dir_path = os.path.join(self.folder, selected_date)
            if os.path.exists(new_dir_path) and self.has_subfolders(new_dir_path, ['GOPRO', 'INSTA360']):
                self.create_dir_button.setEnabled(False)
            else:
                self.create_dir_button.setEnabled(True)
        else:
            self.create_dir_button.setEnabled(False)

    def on_folder_selected(self, folder):
        self.folder = folder
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
            self.origin_label.setText(f"Origin Storage: {volume_name}")
        else:
            self.origin_label.setText("Origin Storage: Unknown")
        self.check_create_dir_button_status()

    def date_option_toggled(self, checked):
        self.date_picker.setEnabled(not checked)
        self.check_create_dir_button_status()

    def create_directory(self):
        selected_camera = 'GOPRO' if self.gopro_radio.isChecked() else 'INSTA360' if self.insta360_radio.isChecked() else None

        if selected_camera is None:
            QMessageBox.warning(self, "No Selection", "Please select a camera type.")
            return

        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        if self.today_button.isChecked():
            selected_date = datetime.today().date().strftime("%Y-%m-%d")

        if self.folder:
            dated_folder_path = os.path.join(self.folder, selected_date)
            
            if not os.path.exists(dated_folder_path):
                try:
                    os.makedirs(dated_folder_path)
                    self.latest_camera_folder = dated_folder_path 
                    self.datedFolderCreated.emit(dated_folder_path)  # Emit the signal with the path of the created dated folder
                except OSError:
                    QMessageBox.critical(self, 'Error', 'Failed to create the dated folder.', QMessageBox.Ok)
                    return

            camera_folder_path = os.path.join(dated_folder_path, selected_camera)
            if not os.path.exists(camera_folder_path):
                try:
                    os.makedirs(camera_folder_path)
                    self.latest_camera_folder = camera_folder_path
                    self.folderCreated.emit(camera_folder_path)  # Emit the signal with the path of the created camera folder
                except OSError:
                    QMessageBox.critical(self, 'Error', 'Failed to create the camera folder.', QMessageBox.Ok)
                    return

            QMessageBox.information(self, "Directory Creation", f"Dated Folder: {dated_folder_path}\nCamera Folder: {camera_folder_path}", QMessageBox.Ok)
        else:
            QMessageBox.warning(self, "No Folder Selected", "Please select a folder first.", QMessageBox.Ok)

    def rename_file(self):
        if self.files:
            selected_category = next((key for key, button in self.category_buttons.items() if button.isChecked()), None)
            if selected_category == 'other':
                selected_category = self.other_input.text()
            
            origin_path = self.origin_label.text().replace("Origin Storage: ", "") if self.origin_path_checkbox.isChecked() else ""
            
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
                QMessageBox.information(self, "All Files Skipped", "You have skipped all files inside the folder.")

    def update_file_label(self):
        if self.current_file_index < len(self.files):
            self.file_label.setText(f'Current File: <b>{self.files[self.current_file_index]}</b>')
            self.path_label.setText(f'Current Path: {os.path.join(self.folder, self.files[self.current_file_index])}')
            self.update_modified_date_label()  
        else:
            QMessageBox.information(self, 'Process Finished',
                                    f'All files processed. Renamed: {self.renamed_files_count}. Skipped: {self.skipped_files_count}.',
                                    QMessageBox.Ok)
            self.file_label.setText("No files left to process")
            self.path_label.setText("No path selected")
            self.reset()

    def update_modified_date_label(self):
        if self.current_file_index < len(self.files):
            file_path = os.path.join(self.folder, self.files[self.current_file_index])
            timestamp = os.path.getmtime(file_path)
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            self.modified_date_label.setText(f"Date Modified: {date_str}")
        else:
            self.modified_date_label.setText("Date Modified: Not available")

    def reset(self):
        self.folder = ''
        self.files = []
        self.current_file_index = 0
        self.renamed_files_count = 0
        self.skipped_files_count = 0
        self.other_input.clear()
        self.gopro_radio.setChecked(True)
        
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

class FileList(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder = ''
        
        layout = QVBoxLayout()

        # Button layout for the Browse and Select Destination buttons
        button_layout = QHBoxLayout()

        instruction_label = QLabel("Step 6: Move files to 'camera type' directory on SD card.")
        instruction_label.setWordWrap(True)  
        font = instruction_label.font()
        font.setPointSize(font.pointSize() + 4)  
        instruction_label.setFont(font)
        instruction_label.setStyleSheet("QLabel { color: blue; }")
        layout.addWidget(instruction_label)

        # Browse button
        browse_button = QPushButton('Browse Files')
        browse_button.clicked.connect(self.browse_files)
        button_layout.addWidget(browse_button)

        # Create a refresh button
        refresh_button = QPushButton('Refresh List')
        refresh_button.clicked.connect(self.refresh_file_list)
        button_layout.addWidget(refresh_button)

        # Destination button
        destination_button = QPushButton('Select Destination')
        destination_button.clicked.connect(self.select_destination_folder)
        button_layout.addWidget(destination_button)

        layout.addLayout(button_layout)

        self.current_path_label = QLabel("Current Path: Not selected")
        layout.addWidget(self.current_path_label)

        self.destination_path_label = QLabel("Destination Path: Not selected")
        layout.addWidget(self.destination_path_label)

        # Initialize QTreeWidget
        self.file_tree = QTreeWidget()
        self.file_tree.setColumnCount(5)  # Updated column count to include Date Modified and Type
        self.file_tree.setHeaderLabels(['Select', 'File Name', 'Size', 'Date Modified', 'Type'])

        # Set column resize modes for responsiveness
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Select column
        self.file_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)          # File Name column
        self.file_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Size column
        self.file_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Date Modified column
        self.file_tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Type column

        # Set the size policy to allow expansion in both directions
        self.file_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Optionally, you can set a minimum size to ensure it doesn't get too small
        self.file_tree.setMinimumSize(150, 150)

        layout.addWidget(self.file_tree, stretch=1)  # Stretch factor to make tree widget take more space

        # Select all checkbox
        self.select_all_checkbox = QCheckBox('Select All')
        self.select_all_checkbox.stateChanged.connect(self.select_all_files)
        layout.addWidget(self.select_all_checkbox)

        # Buttons at the bottom
        button_layout = QHBoxLayout()

        # Add this beside the delete file button
        move_file_button = QPushButton('Move Files')
        move_file_button.setStyleSheet("QPushButton { background-color: darkgreen; color: white; } QPushButton:hover { background-color: green; }")
        move_file_button.clicked.connect(self.move_selected_files)
        button_layout.addWidget(move_file_button)

        delete_file_button = QPushButton('Delete File')
        delete_file_button.clicked.connect(self.delete_selected_files)
        button_layout.addWidget(delete_file_button)

        exit_button = QPushButton('Exit')
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)

        layout.addLayout(button_layout)

        parent.folderSelected.connect(self.set_and_populate_folder)

        # Set the main layout for the dialog
        self.setLayout(layout)

    def refresh_file_list(self):
        if self.folder:
            self.populate_file_list()
        else:
            QMessageBox.warning(self, "Warning", "No folder selected. Please select a folder first.")

    def select_destination_folder(self):
        if hasattr(self.parent(), 'latest_camera_folder') and self.parent().latest_camera_folder:
            self.destination_folder = self.parent().latest_camera_folder
            self.destination_path_label.setText(f"Destination Path: {self.destination_folder}")
        else:
            self.destination_folder = QFileDialog.getExistingDirectory(self, 'Select Destination Folder')
            if self.destination_folder:
                self.destination_path_label.setText(f"Destination Path: {self.destination_folder}")
            else:
                QMessageBox.warning(self, "Warning", "No destination folder selected. Please select a valid destination folder.")

    def set_file_preview_and_rename_dialog(self, dialog_instance):
        self.file_preview_and_rename_dialog = dialog_instance
    
    def move_selected_files(self):
        if not hasattr(self, 'destination_folder') or not self.destination_folder:
            QMessageBox.warning(self, "Warning", "Please select a destination folder first.")
            return

        files_to_move = []
        # Gather all files to move
        for index in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(index)
            checkbox = self.file_tree.itemWidget(item, 0)
            if checkbox.isChecked():
                files_to_move.append((index, item.text(1)))

        # Move the files
        for index, file in reversed(files_to_move):
            src_path = os.path.join(self.folder, file)
            dst_path = os.path.join(self.destination_folder, file)
            try:
                shutil.move(src_path, dst_path)
                self.file_tree.takeTopLevelItem(index)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Unable to move the file: {file}. Error: {e}")

    def set_and_populate_folder(self, folder_path):
        """ Set the folder and populate file list. """
        self.folder = folder_path
        self.current_path_label.setText(f"Current Path: {self.folder}")
        self.populate_file_list()

        # Connect the folderCreated signal to a new method to update the destination folder
        self.file_preview_and_rename_dialog.folderCreated.connect(self.update_destination_folder)

    def update_destination_folder(self, folder_path):
        # Method to update the destination folder when the folderCreated signal is emitted
        self.destination_folder = folder_path
        self.destination_path_label.setText(f"Destination Path: {self.destination_folder}")

    def browse_files(self):
        self.folder = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if self.folder:
            self.current_path_label.setText(f"Current Path: {self.folder}")
            self.populate_file_list()

    def populate_file_list(self):
        self.file_tree.clear()
        if not self.folder:
            return
        
        file_items = []
        for file in os.listdir(self.folder):
            file_path = os.path.join(self.folder, file)
            if os.path.isfile(file_path):  # Ensure that the item is a file
                file_size = os.path.getsize(file_path)
                file_size_str = f"{file_size / (1024*1024):.2f} MB" if file_size > 1024*1024 else f"{file_size / 1024:.2f} KB"

                # Get the last modified date and time
                modified_time = os.path.getmtime(file_path)
                date_modified_str = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
                
                # Get the file type (extension)
                file_type = os.path.splitext(file)[1]
                
                tree_item = QTreeWidgetItem(['', file, file_size_str, date_modified_str, file_type])
                checkbox = QCheckBox()
                
                file_items.append(tree_item)
                
                # Add a small delay before setting the checkbox widget to the tree item
                QTimer.singleShot(100, lambda item=tree_item, checkbox=checkbox: self.file_tree.setItemWidget(item, 0, checkbox))
        
        # Sort the files by type
        self.file_tree.addTopLevelItems(file_items)
        self.file_tree.sortItems(4, Qt.AscendingOrder)
        
        self.file_tree.resizeColumnToContents(1)  # Resize the 'File Name' column
        self.file_tree.resizeColumnToContents(2)  # Resize the 'Size' column
        self.file_tree.resizeColumnToContents(3)  # Resize the 'Date Modified' column
        self.file_tree.resizeColumnToContents(4)  # Resize the 'Type' column

    def select_all_files(self, state):
        for index in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(index)
            checkbox = self.file_tree.itemWidget(item, 0)
            checkbox.setChecked(state == Qt.Checked)

    def delete_selected_files(self):
        # Create a list of files to delete, so that we don't modify the tree while iterating through it
        files_to_delete = []
        
        # Gather all files to delete
        for index in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(index)
            checkbox = self.file_tree.itemWidget(item, 0)
            if checkbox.isChecked():
                files_to_delete.append((index, item.text(1)))
        
        # Delete the files
        for index, file in reversed(files_to_delete):
            try:
                os.remove(os.path.join(self.folder, file))
                self.file_tree.takeTopLevelItem(index)
            except FileNotFoundError:
                QMessageBox.warning(self, "Error", f"Unable to delete the file: {file}")

def get_drive_label(drive_path):
    try:
        drive_info = win32api.GetVolumeInformation(drive_path)
        return drive_info[0]  # The label is the first item in the tuple returned by GetVolumeInformation
    except Exception as e:
        return None

class MoveFolderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.client = Client("ACbafddfb2596e8129c895aaece07d72f9", "19c2c85a1e552946ba54969aa1b7b216")
        
        # Create a vertical layout to hold the UI elements
        layout = QVBoxLayout()
        
        # Create a horizontal layout to hold the folder selection buttons
        folder_selection_layout = QHBoxLayout()

        instruction_label = QLabel("Step 7: Copy dated folder to QNAP Data.")
        instruction_label.setWordWrap(True)  
        font = instruction_label.font()
        font.setPointSize(font.pointSize() + 4)  
        instruction_label.setFont(font)
        instruction_label.setStyleSheet("QLabel { color: blue; }")
        layout.addWidget(instruction_label)
        
        # Create a button to open the folder selection dialog
        self.select_folder_button = QPushButton("Select Dated Folder")
        self.select_folder_button.clicked.connect(self.select_dated_folder)
        
        # Create a button to open the destination folder selection dialog
        self.select_destination_button = QPushButton("Select Destination Folder")
        self.select_destination_button.clicked.connect(self.select_destination_folder)
        
        # Add the folder selection buttons to the horizontal layout
        folder_selection_layout.addWidget(self.select_folder_button)
        folder_selection_layout.addWidget(self.select_destination_button)
        
        # Create a button to initiate the folder copy process
        self.copy_folder_button = QPushButton("Copy Folder")
        self.copy_folder_button.setStyleSheet("QPushButton { background-color: darkgreen; color: white; } QPushButton:hover { background-color: green; }")
        self.copy_folder_button.clicked.connect(self.copy_folder)

        # Create labels to display the selected folder paths
        self.source_folder_label = QLabel("Source Folder: None")
        self.destination_folder_label = QLabel("Destination Folder: None")
        
        # Create a progress bar to display the progress of the copy operation
        self.progress_bar = QProgressBar()
        self.progress_bar.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.progress_bar.setStyleSheet("QProgressBar { border: 2px solid grey; border-radius: 5px; background-color: #F0F0F0; } QProgressBar::chunk { background-color: #76C7C0; }")
        
        # Create a label to display the completion message
        self.completion_label = QLabel()

        self.upload_to_drive_button = QPushButton("Upload to Google Drive")
        self.upload_to_drive_button.clicked.connect(self.upload_to_google_drive)
        
        # Add the UI elements to the layout
        layout.addLayout(folder_selection_layout)
        layout.addWidget(self.copy_folder_button)
        layout.addWidget(self.source_folder_label)
        layout.addWidget(self.destination_folder_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.completion_label)
        layout.addWidget(self.upload_to_drive_button)
        
        # Set the layout for this widget
        self.setLayout(layout)
        
        # Class variables to store the selected folder paths
        self.selected_dated_folder = ""
        self.destination_folder = ""

        # Set default destination folder
        self.set_default_destination_folder()
    
    def handle_upload_completion(self, uploaded_files, start_time, message):
        # Change the button label back to its original state
        self.upload_to_drive_button.setText("Upload to Google Drive")

        formatted_message = f"Upload started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        formatted_message += message
        formatted_message += "\nUploaded files:\n"
        formatted_message += "\n".join(uploaded_files)

        QMessageBox.information(self, "Information", formatted_message)
        self.send_sms_message(formatted_message)

    def send_sms_message(self, message):
        self.client.messages.create(
            body=message,
            from_='+12569527301',
            to='+639560642329'
        )
    
    def upload_to_google_drive(self):
        self.upload_to_drive_button.setText("Uploading to Google Drive...")
        # Initialize the OAuth2 flow
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes=['https://www.googleapis.com/auth/drive'])
        
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive'])
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds = flow.run_local_server(port=0)  
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        # Build the Google Drive API client
        self.drive_service = build('drive', 'v3', credentials=creds)

        # Open a dialog to select the destination folder on Google Drive
        self.select_google_drive_folder()

    def select_google_drive_folder(self):
        # List shared drives
        results = self.drive_service.drives().list(pageSize=10).execute()
        items = results.get('drives', [])
        
        if items:
            # Display a dialog to select a drive
            item_names = [item['name'] for item in items]
            item, okPressed = QInputDialog.getItem(self, "Select Google Drive","Drive:", item_names, 0, False)
            if okPressed and item:
                # Find the selected drive's ID
                for i in items:
                    if i['name'] == item:
                        self.selected_google_drive_folder_id = i['id']
                        break
                
                # Start the upload process
                self.upload_folder_to_google_drive()
        else:
            QMessageBox.information(self, "Information", "No shared drives found")

    def upload_folder_to_google_drive(self):
        if self.selected_dated_folder and self.selected_google_drive_folder_id:
            # Create a folder in the selected shared drive
            file_metadata = {
                'name': os.path.basename(self.selected_dated_folder),
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.selected_google_drive_folder_id]
            }
            folder = self.drive_service.files().create(body=file_metadata, supportsAllDrives=True).execute()
            
            # Initialize the GoogleDriveUploadThread and connect its signals
            self.google_drive_upload_thread = GoogleDriveUploadThread(self.drive_service, folder['id'], self.selected_dated_folder)
            self.google_drive_upload_thread.completion_signal.connect(self.handle_upload_completion)  # Assuming you have defined this method to handle completion signal
            self.google_drive_upload_thread.error_signal.connect(self.display_error_message)
            
            # Show a message indicating that the upload has started
            QMessageBox.information(self, "Information", "The upload has started. Please wait for an SMS to know if the upload was successful.")
            
            # Start the Google Drive upload thread
            self.google_drive_upload_thread.start()

        else:
            QMessageBox.information(self, "Information", "Please select a dated folder and a Google Drive folder")
    
    def set_default_destination_folder(self):
        drive_label = "5TBHD"
        folder_name = "Shared Videos 5TB"
        for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = f"{drive_letter}:\\"
            if os.path.exists(drive_path) and os.path.isdir(drive_path):
                if get_drive_label(drive_path) == drive_label:  # Changed os.get_label to get_drive_label
                    destination_folder_path = os.path.join(drive_path, folder_name)
                    if os.path.exists(destination_folder_path):
                        self.destination_folder = destination_folder_path
                        self.destination_folder_label.setText(f"Destination Folder: {destination_folder_path}")
                    break
    
    def select_dated_folder(self):
        options = QFileDialog.Options()
        folder_path = QFileDialog.getExistingDirectory(self, "Select Dated Folder", "", options=options)
        if folder_path:
            self.selected_dated_folder = folder_path
            self.source_folder_label.setText(f"Source Folder: {folder_path}")

    def update_source_folder(self, folder_path):
        self.selected_dated_folder = folder_path
        self.source_folder_label.setText(f"Source Folder: {folder_path}")

    def select_destination_folder(self):
        options = QFileDialog.Options()
        folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder", "", options=options)
        if folder_path:
            self.destination_folder = folder_path
            self.destination_folder_label.setText(f"Destination Folder: {folder_path}")

    def copy_folder(self):
        # Change the button label to indicate the copying process has started
        self.copy_folder_button.setText("Copying Folder...")

        # Initialize the CopyFolderThread and connect its signals
        self.copy_thread = CopyFolderThread(self.selected_dated_folder, self.destination_folder)
        self.copy_thread.progress_signal.connect(self.update_progress_bar)
        self.copy_thread.completion_signal.connect(self.display_completion_message)
        self.copy_thread.error_signal.connect(self.display_error_message)
        
        # Start the copy thread
        self.copy_thread.start()
        
    def update_progress_bar(self, progress):
        # Update the progress bar with the current progress value
        self.progress_bar.setValue(progress)
        
    def display_completion_message(self, skipped_files):
        # Change the button label back to its original state
        self.copy_folder_button.setText("Copy Folder")
        
        # Display a message indicating the completion of the copy operation
        self.completion_label.setText(f"Copy operation completed. {skipped_files} files skipped.")
        
    def display_error_message(self, error_message):
        # Display the error message
        self.completion_label.setText(f"Error: {error_message}")

logging.basicConfig(level=logging.INFO)

class GoogleDriveUploadThread(QThread):
    progress_signal = pyqtSignal(int, str)
    completion_signal = pyqtSignal(list, datetime, str)  # Modified to include a list of uploaded files and start time
    error_signal = pyqtSignal(str)

    def __init__(self, drive_service, folder_id, local_folder_path):
        super().__init__()
        self.drive_service = drive_service
        self.folder_id = folder_id
        self.local_folder_path = local_folder_path
        self.total_files = sum([len(files) for r, d, files in os.walk(self.local_folder_path)])
        self.uploaded_files = 0
        self.failed_uploads = []
        self.successful_uploads = []  # List to keep track of successfully uploaded files
        self.start_time = datetime.now()  # Record the start time of the upload
        self.log_file_name = f"files_uploaded_{self.start_time.strftime('%Y%m%d_%H%M%S')}.txt"

    def run(self):
        try:
            # Clear or create the log file
            with open(self.log_file_name, 'w') as log_file:
                log_file.write(f"Upload log started at {self.start_time}\n")
            
            self.upload_folder(self.local_folder_path, self.folder_id)
            self.completion_signal.emit(self.successful_uploads, self.start_time, f"Upload completed successfully. {self.uploaded_files} files uploaded. {len(self.failed_uploads)} files failed to upload: {', '.join(self.failed_uploads)}")
        except Exception as e:
            logging.exception("An error occurred during the upload process")
            self.error_signal.emit(str(e))

    def upload_folder(self, local_folder, drive_folder_id):
        for item in os.listdir(local_folder):
            item_path = os.path.join(local_folder, item)
            if os.path.isfile(item_path):
                self.upload_file(item_path, drive_folder_id)
            elif os.path.isdir(item_path):
                new_folder_metadata = {
                    'name': os.path.basename(item_path),
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [drive_folder_id]
                }
                try:
                    new_folder = self.drive_service.files().create(body=new_folder_metadata, supportsAllDrives=True).execute()
                    self.write_to_log(f"Uploaded folder: {item_path}")  # Log the folder upload
                    self.upload_folder(item_path, new_folder['id'])
                except Exception as e:
                    logging.exception(f"Error uploading folder {item_path}")
                    self.error_signal.emit(f"Error uploading folder {item_path}: {str(e)}")

    def write_to_log(self, text):
        with open(self.log_file_name, 'a') as log_file:  # 'a' for appending to the file
            log_file.write(f"{text}\n")
    
    def upload_file(self, file_path, folder_id):
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        request = self.drive_service.files().create(media_body=media, body=file_metadata, supportsAllDrives=True)
        
        response = None
        retry_count = 0
        max_retries = 5
        while response is None and retry_count < max_retries: 
            try:
                print(f"Attempting to upload {file_path}, Retry Count: {retry_count}")  # Debug print
                status, response = request.next_chunk()
                print(f"Successfully uploaded {file_path}")  # Debug print

                self.uploaded_files += 1
                self.successful_uploads.append(file_path)
                
                # Log the file upload only when it is successful
                self.write_to_log(f"Successfully uploaded file: {file_path}")  

                self.progress_signal.emit(int((self.uploaded_files / self.total_files) * 100), file_path)
            except Exception as e:
                retry_count += 1
                response = None  # Reset response to None to ensure the loop works correctly
                time.sleep(2**retry_count)  # Exponential backoff
                logging.exception(f"Error uploading file {file_path}, Retrying ({retry_count})...")
                if retry_count == max_retries:
                    self.failed_uploads.append(file_path)
                    try:
                        self.successful_uploads.remove(file_path)  # Remove the file from the successful uploads list if it ultimately fails
                    except ValueError:
                        print("File not found in successful uploads list")  # Debug print
                    self.error_signal.emit(f"Error uploading file {file_path}: {str(e)}. Maximum retries reached.")

class CopyFolderThread(QThread):
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    completion_signal = pyqtSignal(int)

    def __init__(self, source_folder, destination_folder):
        super().__init__()
        self.source_folder = source_folder
        self.destination_folder = destination_folder

    # Modified to emit the completion signal with the number of skipped files
    def run(self):
        try:
            total_files = sum([len(files) for r, d, files in os.walk(self.source_folder)])
            copied_files = 0
            skipped_files = 0

            for root, dirs, files in os.walk(self.source_folder):
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(self.destination_folder, os.path.basename(self.source_folder), os.path.relpath(src_file, self.source_folder))
                    
                    # Create the destination folder if it does not exist
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    
                    # Try to copy the file and handle errors (like file already exists)
                    try:
                        shutil.copy2(src_file, dst_file)
                        copied_files += 1
                        self.progress_signal.emit(int((copied_files / total_files) * 100))
                    except Exception as e:
                        skipped_files += 1
                        # You can log the error message here if needed

            # Emit signal indicating completion with the number of skipped files
            self.completion_signal.emit(skipped_files)
        except Exception as e:
            self.error_signal.emit(str(e))

class DriveEjectWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        instruction_label = QLabel("Step 9: Eject Selected Drive")
        instruction_label.setWordWrap(True)
        font = instruction_label.font()
        font.setPointSize(font.pointSize() + 4)
        instruction_label.setFont(font)
        instruction_label.setStyleSheet("QLabel { color: blue; }")
        layout.addWidget(instruction_label)

        self.drive_combo_box = QComboBox()
        self.update_drive_list()
        layout.addWidget(self.drive_combo_box)

        self.eject_button = QPushButton("Eject Drive")
        self.eject_button.clicked.connect(self.eject_selected_drive)
        layout.addWidget(self.eject_button)

        self.setLayout(layout)

    def update_drive_list(self):
        drives = win32api.GetLogicalDriveStrings()
        drives = drives.split('\000')[:-1]

        drive_with_volume_names = []
        for drive in drives:
            try:
                volume_name, _, _, _, _ = win32api.GetVolumeInformation(drive)
                drive_with_volume_names.append(f"{drive} ({volume_name})")
            except Exception as e:
                drive_with_volume_names.append(f"{drive} (Unknown Volume)")

        self.drive_combo_box.clear()
        self.drive_combo_box.addItems(drive_with_volume_names)

    def eject_drive(self):
        selected_drive = self.drive_combo_box.currentText()
        if selected_drive:
            drive_letter = selected_drive[0]
            volume_name = selected_drive[4:-1]

            reply = QMessageBox.question(self, 'Eject Drive',
                                        f'Are you sure you want to eject the drive "{volume_name}" ({drive_letter}:)?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                try:
                    win32api.GetLogicalDriveStrings()
                    win32file.DefineDosDevice(win32con.DDD_REMOVE_DEFINITION, drive_letter, None)
                    self.update_drive_list()
                    QMessageBox.information(self, "Success", f"The drive {drive_letter}: has been ejected successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"An error occurred while ejecting the drive {drive_letter}: - {str(e)}")
            else:
                # User decided not to eject the drive
                pass
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a drive to eject.")

    def eject_selected_drive(self):
        selected_drive = self.drive_combo_box.currentText()
        if selected_drive:
            try:
                win32api.DefineDosDevice(win32con.DDD_REMOVE_DEFINITION, selected_drive, selected_drive)
                QMessageBox.information(self, "Success", f"The drive {selected_drive} has been ejected successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while ejecting the drive: {str(e)}")
        else:
            QMessageBox.warning(self, "Warning", "No drive selected.")

class MainInterface(QMainWindow):
    def __init__(self): 
        super().__init__()
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        scroll_area = QScrollArea()
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(scroll_area)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)  # Use QVBoxLayout for content

        widget1 = BrowseButton()
        widget2 = FilePreviewAndRenameDialog(browse_button_widget=widget1)
        widget3 = FileList(widget1)  
        widget3.set_file_preview_and_rename_dialog(widget2)

        # Create an instance of MoveFolderWidget and add it to the layout
        move_folder_widget = MoveFolderWidget()
        
        # Connect the folderCreated signal to the update_source_folder slot
        widget2.datedFolderCreated.connect(move_folder_widget.update_source_folder)

        layout.addWidget(widget1)
        layout.addWidget(widget2)
        layout.addWidget(widget3)

        # Add horizontal lines using QFrame
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)

        layout.addWidget(line1)

        # Add the instance of MoveFolderWidget to the layout
        layout.addWidget(move_folder_widget)

        # Create an instance of DriveEjectWidget and add it to the layout
        drive_eject_widget = DriveEjectWidget()
        layout.addWidget(drive_eject_widget)

        layout.addStretch(1)  # Add stretchable space below the horizontal line

        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.setWindowTitle("autoFile")
        self.setGeometry(100, 100, 1000, 1000)

        # Allow scrolling
        scroll_area.setWidgetResizable(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainInterface()
    window.show()
    sys.exit(app.exec_())
