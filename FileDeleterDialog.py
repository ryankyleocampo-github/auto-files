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

class FileDeleterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder = ''
        self.files = []
        
        layout = QVBoxLayout()

        # Browse button
        browse_button = QPushButton('Browse Files')
        browse_button.clicked.connect(self.browse_files)
        layout.addWidget(browse_button)

        # Initialize QTreeWidget
        self.file_tree = QTreeWidget()
        self.file_tree.setColumnCount(3)
        self.file_tree.setHeaderLabels(['Select', 'File Name', 'Size'])

        # Set column resize modes for responsiveness
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Select column
        self.file_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)          # File Name column
        self.file_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Size column

        layout.addWidget(self.file_tree, stretch=1)  # Stretch factor to make tree widget take more space

        # Select all checkbox
        self.select_all_checkbox = QCheckBox('Select All')
        self.select_all_checkbox.stateChanged.connect(self.select_all_files)
        layout.addWidget(self.select_all_checkbox)

        # Buttons at the bottom
        button_layout = QHBoxLayout()

        delete_file_button = QPushButton('Delete File')
        delete_file_button.clicked.connect(self.delete_selected_files)
        button_layout.addWidget(delete_file_button)

        exit_button = QPushButton('Exit')
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)

        layout.addLayout(button_layout)

        # Set the main layout for the dialog
        self.setLayout(layout)
        
        # Set minimum window size
        self.setMinimumSize(600, 400)

    def browse_files(self):
        self.folder = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if self.folder:
            self.populate_file_list()

    def populate_file_list(self):
        self.file_tree.clear()
        if not self.folder:
            return
        for file in os.listdir(self.folder):
            file_path = os.path.join(self.folder, file)
            if os.path.isfile(file_path):  # Ensure that the item is a file
                file_size = os.path.getsize(file_path)
                file_size_str = f"{file_size / (1024*1024):.2f} MB" if file_size > 1024*1024 else f"{file_size / 1024:.2f} KB"

                tree_item = QTreeWidgetItem(['', file, file_size_str])
                checkbox = QCheckBox()
                self.file_tree.addTopLevelItem(tree_item)
                self.file_tree.setItemWidget(tree_item, 0, checkbox)
        self.file_tree.resizeColumnToContents(1)  # Resize the 'File Name' column
        self.file_tree.resizeColumnToContents(2)  # Resize the 'Size' column

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
