
--
# CHANGELOG 
All notable changes to this project will be documented in this file.




# autoFile ver.[2023-08-17]

# Features

- # AutoFileApp (Main Interface)
    - User can detect drives locally on the main interface.
    - Serves as the main application window, providing centralized access to all features and functionalities.
    - Users can select specific operations like copying, renaming, or deleting.

- # FilePreviewAndRenameDialog function
    - Provides users the capability to preview files from a selected source.
    - Users can easily rename files directly from the preview dialog.

- # FileCopierDialog function
    - Intuitive interface for selecting both source and destination folders.
    - Progress bars offer real-time feedback on the copying process.
    - File paths and current file statuses are clearly displayed to keep users informed.
    - Google Drive Integration:
        - Seamless authentication process with Google Drive.
        - Users can specify a particular Google Drive folder ID for uploads, ensuring proper file placement.
        - Upload files to Google Drive.
  
- # FileDeleterDialog function
    - Allows users to selectively delete files.
    - Users receive a clear list of all files from a selected source, ensuring they have full control over what gets deleted.

- # User Experience Enhancements

    - Comprehensive error handling with detailed messages ensures users are informed about any issues or missteps.
    - The application interface, built with PyQt5, offers a clean and intuitive experience, making operations straightforward even for new users.
    - Progress bars offer real-time feedback on the copying process.

# Bug Fixes

- Many bugs were not documented but were fixed.

# Known Issues

- It crashed when dealing with multiple files or large files.



---



# autoFile ver.[2023-08-22]

# Added
1. A new parameter `selected_drive` in the `__init__` method of the `FilePreviewAndRenameDialog` class.
2. Initialization of new attributes: `self.drive`, `self.folder`, and more, to support the selection of a specific drive.
3. Introduction of a new method `populate_files_list` to list files in a given folder.
4. A new method `delete_current_file` to handle file deletion.
5. Enhanced layout with added functionalities like a "Delete" button.
6. The checkbox `origin_path_checkbox` and the radio button `today_button` are set by default.
7. Functionality to handle the selection of a specific drive before proceeding with file preview and renaming.
8. When user skipped all files, program should show feedback.

# Changed
1. The way layouts are structured and organized has been modified.
2. The way drives are detected and displayed has been altered.
3. The `FilePreviewAndRenameDialog` has been modified to accommodate the new `selected_drive` parameter.

# Removed
1. A few lines related to file skipping and updating the file label have been removed.
2. Some lines related to setting up the drive layout and the drives group box have been removed (but seem to be replaced with a more organized approach).

# Bugs
n/a

# Fixed
n/a

# Security
n/a

...


...


...


...


...


...


...


...


...