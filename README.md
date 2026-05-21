====================================
CAPSTONE PROJECTS MANAGEMENT SYSTEM
====================================

Version: 1.0
Developed for: CISKM Department

DESCRIPTION
-----------
A complete system for managing capstone projects - submission, supervision, marking, and publication.

SERVER INFORMATION
------------------
• Server PC: Your Device (must remain ON and XAMPP running)
• Database User: capstone_user
• Default Admin Login:
   Username: ADMIN_001
   Password: admin123

HOW TO USE (For All Users)
--------------------------
1. Download the FPMS folder from GitHub.
2. Extract the folder to any location on your computer.
3. Open the file `config.ini` with Notepad.
4. Change the `host` value to the IP address of the Server PC.

   Example:
   host = 192.168.1.105     ← Replace with the actual server IP

5. Save the file.
6. Navigate to dist/ folder.
7. Double-click `FPMS.exe` to launch the system.

CONFIG.INI EXAMPLE
------------------
[Database]
host = 192.168.1.105        ; ← CHANGE THIS to Server PC IP Address
port = 3306
user = capstone_user
password = password123
database = capstone_db

DEFAULT ADMIN ACCOUNT
---------------------
Username : ADMIN_001
Password : admin123
Role     : Administrator

TROUBLESHOOTING
---------------
• "Connection Failed" → 
   - Make sure XAMPP (Apache + MySQL) is running on the Server PC.
   - Confirm you are on the same Wi-Fi network.
   - Check that the IP address in config.ini is correct.

• IP Address keeps changing → Ask the server owner for the new IP.

• Uploads not saving → Make sure the "uploads" folder exists.

IMPORTANT NOTES
---------------
• The Server PC must be powered on and XAMPP must be running whenever users want to access the system.
• All users must be connected to the same local network (Wi-Fi).
• Do not change the username and password in config.ini unless instructed.

For any issues, contact the System Administrator.

Thank you for using the Capstone Projects Management System!
