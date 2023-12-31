

---

# autoFile

# Overview

The tool is a Python-based GUI application designed for users who work well with video files. The application assists users in sorting, copying, deleting and renaming files. It also provides the ability to upload these files seamlessly to Google Drive. Created by _RK_.

Automating these tasks in the future will save significant time, especially when dealing with large numbers of media files and repetitive tasks.

# Features

   1. File Selection and Copying: Users can select a source folder and a destination folder. Files from the source folder can be copied to the destination folder either individually or all at once.
   2. Google Drive Integration: Users can upload selected files from the destination folder to a specified Google Drive folder.
   3. Progress Tracking: The application provides real-time feedback through progress bars and labels, showing the current file being processed and the overall progress.
   4. Error Handling: In case of issues (like selecting an invalid folder or encountering a copying error), the application displays relevant error messages to the user.
   5. Delete files: In case of user wanted to delete files, this tool can let user select and delete files inside folders.

# Getting Started

   1. Prerequisites: Ensure you have Python installed, along with the following libraries:
      - PyQt5
      - win32api
      - win32file
      - google-auth, google-auth-oauthlib, google-auth-httplib2, google-api-python-client (for Google Drive integration)

   2. Setup:
      - Clone the repository.
      - Install the required libraries using pip: ```pip install PyQt5 pywin32 google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client```

   3. Google Drive Configuration:
      - Go to Google Developers Console: https://console.developers.google.com/
      - Create a new project.
      - Enable the Google Drive API for the project.
      - Create OAuth 2.0 Client IDs.
      - Download the `credentials.json` file and place it in the application's directory.

   4. Running the Application:
      - Navigate to the application directory.
      - Run the main test script: ```python main_test.py```

# Contributing

If you'd like to contribute to this project, please review the `CONTRIBUTING.md` file for guidelines.

# License

This project is licensed under the MIT License.

# Acknowledgments

- Special thanks to the developers behind the PyQt5 and Google Drive API libraries.
- openAI and GitHub Copilot was instrumental in reading the entire codebase, double-checking for potential issues, and providing recommendations.
- Main developer signature ____RK_____


---
 