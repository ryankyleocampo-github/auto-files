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

class FileCopierDialog(QDialog):
    update_progress_signal = pyqtSignal(int)
    update_start_time_signal = pyqtSignal(str)
    update_end_time_signal = pyqtSignal(str)
    file_copied_signal = pyqtSignal(str)
    upload_error_signal = pyqtSignal(str)
    upload_info_signal = pyqtSignal(str)
    copying_done_signal = pyqtSignal()
    show_progress_bar_signal = pyqtSignal()
    hide_progress_bar_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.connect_signals()
        self.upload_error_signal.connect(self.show_upload_error)
        self.upload_info_signal.connect(self.show_upload_info)

    def init_ui(self):
        self.from_folder = ''
        self.to_folder = ''
        self.files = []
        self.moved_files = 0
        self.skipped_files = 0
        self.total_files = 0
        self.current_file_index = 0

        layout = QVBoxLayout()

        browse_layout = QHBoxLayout()
        browse_from_button = QPushButton('Select Source Folder')
        browse_from_button.clicked.connect(self.browse_from_folder)
        browse_layout.addWidget(browse_from_button)

        browse_to_button = QPushButton('Select Destination Folder')
        browse_to_button.clicked.connect(self.browse_to_folder)
        browse_layout.addWidget(browse_to_button)

        layout.addLayout(browse_layout)

        self.from_folder_label = QLabel("Source Folder: Not selected")
        layout.addWidget(self.from_folder_label)

        self.to_folder_label = QLabel("Destination Folder: Not selected")
        layout.addWidget(self.to_folder_label)

        self.file_label = QLabel("No file selected")
        layout.addWidget(self.file_label)

        button_layout = QHBoxLayout()
        move_all_button = QPushButton('Copy All Files')
        move_all_button.clicked.connect(self.copy_all_files)
        button_layout.addWidget(move_all_button)

        copy_file_button = QPushButton('Copy File')
        copy_file_button.clicked.connect(self.copy_file)
        button_layout.addWidget(copy_file_button)

        skip_file_button = QPushButton('Skip File')
        skip_file_button.clicked.connect(self.skip_file)
        button_layout.addWidget(skip_file_button)

        exit_button = QPushButton('Exit')
        exit_button.clicked.connect(self.exit_program)
        button_layout.addWidget(exit_button)

        layout.addLayout(button_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.start_time_label = QLabel("Start Time: Not started")
        layout.addWidget(self.start_time_label)

        self.end_time_label = QLabel("End Time: Not completed")
        layout.addWidget(self.end_time_label)

        self.copied_files_tree = QTreeWidget(self)
        self.copied_files_tree.setFixedHeight(100)
        self.copied_files_tree.setColumnCount(2)
        self.copied_files_tree.setHeaderLabels(['File Name', 'Selected'])
        self.copied_files_tree.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.copied_files_tree)

        self.summary_label = QLabel("Moved Files: 0, Selected: 0")
        layout.addWidget(self.summary_label)

        self.upload_button = QPushButton("Upload to Google Drive")
        self.upload_button.clicked.connect(self.start_upload)
        layout.addWidget(self.upload_button)

        self.setLayout(layout)

    def show_upload_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_upload_info(self, message):
        QMessageBox.information(self, "Info", message)

    def start_upload(self):
        folder_id = self.get_google_drive_folder_id()
        if not folder_id:
            return
        self.upload_thread = UploadThread(lambda: self.upload_to_drive(folder_id))
        self.upload_thread.upload_done_signal.connect(self.on_upload_done)  
        self.upload_thread.start()

    def on_upload_done(self):
        QMessageBox.information(self, "Upload Complete", "Files have been uploaded to Google Drive successfully!")
    
    def upload_to_drive(self, folder_id):
        # Authenticate to Google Drive
        service = self.authenticate_to_drive()
        if not service:
            self.upload_error_signal.emit("Failed to authenticate with Google Drive.")
            return

        selected_files = self.get_selected_files()

        if not selected_files:
            self.upload_info_signal.emit("No files have been selected for upload.")
            return

        self.upload_info_signal.emit("Starting to upload files to Google Drive...")

        for file_name in selected_files:
            full_path = os.path.join(self.to_folder, file_name)
            self.upload_file_to_drive(service, file_name, full_path, folder_id)
        
        self.upload_info_signal.emit("Files uploaded to Google Drive successfully!")

    def get_google_drive_folder_id(self):
        folder_id, ok = QInputDialog.getText(self, "Google Drive", "Enter the Folder ID where you want to upload the files:")
        if ok and folder_id:
            return folder_id
        return None
    
    def authenticate_to_drive(self):
        creds = None
        # The token.pickle file stores the user's access and refresh tokens.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no valid credentials available, authenticate the user.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        try:
            return build('drive', 'v3', credentials=creds)
        except HttpError as e:
            print(f"Error: {e}")
            return None

    def get_selected_files(self):
        selected_files = []
        for i in range(self.copied_files_tree.topLevelItemCount()):
            item = self.copied_files_tree.topLevelItem(i)
            if item.checkState(1) == Qt.Checked:
                selected_files.append(item.text(0))
        return selected_files

    def upload_file_to_drive(self, service, file_name, file_path, folder_id):
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]  # The key addition to place the file inside the desired folder
        }
        media = MediaFileUpload(file_path)
        try:
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"File {file_name} uploaded with ID {file.get('id')}")
        except HttpError as error:
            print(f"Error uploading {file_name}: {error}")

    def connect_signals(self):
        self.update_progress_signal.connect(self.update_progress_bar)
        self.update_start_time_signal.connect(self.update_start_time)
        self.update_end_time_signal.connect(self.update_end_time)
        self.copying_done_signal.connect(self.show_copying_done_message)
        self.show_progress_bar_signal.connect(self.show_progress_bar)
        self.hide_progress_bar_signal.connect(self.hide_progress_bar)
        self.file_copied_signal.connect(self.post_file_copy)

    def browse_from_folder(self):
        self.from_folder = QFileDialog.getExistingDirectory(self, 'Select Source Folder')
        if not os.path.exists(self.from_folder):
            QMessageBox.critical(self, 'Error', 'Invalid source folder selected')
            return
        self.from_folder_label.setText(f'Source Folder: {self.from_folder}')
        self.load_files()

    def browse_to_folder(self):
        self.to_folder = QFileDialog.getExistingDirectory(self, 'Select Destination Folder')
        if not os.path.exists(self.to_folder):
            QMessageBox.critical(self, 'Error', 'Invalid destination folder selected')
            return
        self.to_folder_label.setText(f'Destination Folder: {self.to_folder}')

    def load_files(self):
        file_list = [f for f in os.listdir(self.from_folder) if os.path.isfile(os.path.join(self.from_folder, f))]
        self.total_files = len(file_list)
        self.files = iter(file_list)  
        self.current_file = next(self.files, None)
        self.current_file_index = 0
        self.moved_files = 0
        self.skipped_files = 0

        self.progress_bar.setValue(0)
        self.update_file_label()

    def update_file_label(self):
        if self.current_file:
            self.file_label.setText(f'Current File: {self.current_file}')
        else:
            self.file_label.setText("No files in the selected folder")

    def copy_all_files(self):
        self.copy_thread = CopyThread(parent=self)
        self.copy_thread.start()

    def show_copying_done_message(self):
        QMessageBox.information(self, 'Done', 'Copying process has been completed!')  

    def copy_file(self):
        self.show_progress_bar()

        if not self.current_file:
            return

        try:
            src_path = os.path.join(self.from_folder, self.current_file)
            dest_path = os.path.join(self.to_folder, self.current_file)
            self.copy_with_progress(src_path, dest_path)
            self.file_copied_signal.emit(self.current_file)

        except (FileNotFoundError, PermissionError, OSError) as e:
            QMessageBox.critical(self, 'Error', f'An error occurred while copying the file: {e}')
        
        self.hide_progress_bar()

    def post_file_copy(self, file_name):
        item = QTreeWidgetItem(self.copied_files_tree)
        item.setText(0, file_name)
        item.setCheckState(1, Qt.Unchecked)
        self.current_file = next(self.files, None)
        self.moved_files += 1
        self.current_file_index = 0
        selected_count = sum([self.copied_files_tree.topLevelItem(i).checkState(1) == Qt.Checked for i in range(self.copied_files_tree.topLevelItemCount())])
        self.summary_label.setText(f"Moved Files: {self.moved_files}, Selected: {selected_count}")
        self.update_file_label()

    def on_item_changed(self, item, column):
        if column == 1:
            selected_count = sum([self.copied_files_tree.topLevelItem(i).checkState(1) == Qt.Checked for i in range(self.copied_files_tree.topLevelItemCount())])
            self.summary_label.setText(f"Moved Files: {self.moved_files}, Selected: {selected_count}")

    def show_progress_bar(self):
        self.progress_bar.setVisible(True)

    def hide_progress_bar(self):
        self.progress_bar.setVisible(False)

    def copy_with_progress(self, src, dest):
        buffer_size = 1024 * 1024 
        with open(src, 'rb') as src_file, open(dest, 'wb') as dest_file:
            while True:
                data = src_file.read(buffer_size)
                if not data:
                    break
                dest_file.write(data)
                copied_size = os.path.getsize(dest)
                total_size = os.path.getsize(src)
                percentage = (copied_size / total_size) * 100
                self.update_progress_signal.emit(int(percentage))

    def skip_file(self):
        if self.current_file:
            self.current_file = next(self.files, None)
            self.skipped_files += 1
            self.update_file_label()

    def exit_program(self):
        self.close()

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: gray; border: 2px solid gray; border-radius: 5px; text-align: center; } QProgressBar::chunk { background-color: green; }")

    def update_start_time(self, value):
        self.start_time_label.setText(f"Start Time: {value}")

    def update_end_time(self, value):
        self.end_time_label.setText(f"End Time: {value}")

class UploadThread(QThread):
    upload_done_signal = pyqtSignal()

    def __init__(self, upload_method):
        super().__init__()
        self.upload_method = upload_method
    
    def run(self):
        self.upload_method()
        self.upload_done_signal.emit()

class CopyThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    def run(self):
        self.parent.show_progress_bar_signal.emit()
        self.parent.update_start_time_signal.emit(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        while self.parent.current_file:
            self.parent.copy_file()
        self.parent.update_end_time_signal.emit(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.parent.hide_progress_bar_signal.emit()
        self.parent.copying_done_signal.emit()

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

            self.drive_group_box.show()  # Show the drives group box
            self.update()

    def on_button_clicked(self, button_num):
        if button_num == 1:
            self.file_preview_and_rename_dialog = FilePreviewAndRenameDialog(self)
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
