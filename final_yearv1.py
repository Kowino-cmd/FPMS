import configparser
from tkinter import *
from tkinter import ttk, messagebox, filedialog, simpledialog
from mysql.connector import Error
import mysql.connector
import os
import shutil
from datetime import datetime
import sys
import subprocess
import hashlib


# Establish connection directly with database
conn = mysql.connector.connect(
    user="root",
    host="172.17.99.193",
    password="",       
    #port=3307,         
    database="capstone_db"
)

# Create cursor
c = conn.cursor()

# 1. Students table
c.execute("""
CREATE TABLE IF NOT EXISTS students (
    admission_no VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# 2. Staff (includes supervisors & possibly other roles)
c.execute("""
CREATE TABLE IF NOT EXISTS staff (
    staff_id VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    department VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

# 3. Users (for authentication - students, supervisors, admins)
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,          -- admission_no or staff_id
    password_hash VARCHAR(255) NOT NULL,           -- store hashed passwords (never plain!)
    email VARCHAR(100),
    role ENUM('student', 'staff', 'supervisor', 'admin') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);
""")

# 4. Projects (core table)
c.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    student_admission VARCHAR(20) NOT NULL,
    supervisor_staff_id VARCHAR(20),
    file_path VARCHAR(500) NOT NULL,               -- path or filename in uploads/
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    marks INT DEFAULT NULL,                        -- 0–100 or NULL if not marked
    feedback TEXT,
    status ENUM('pending', 'reviewed', 'approved', 'rejected') DEFAULT 'pending',
    publish_approved TINYINT(1) DEFAULT 0,         -- 0 = not yet, 1 = published by admin
    published_at TIMESTAMP NULL,
    FOREIGN KEY (student_admission) REFERENCES students(admission_no) ON DELETE CASCADE,
    FOREIGN KEY (supervisor_staff_id) REFERENCES staff(staff_id) ON DELETE SET NULL
);
""")

# Optional: 5. Project assignments (if one student can have multiple supervisors or vice versa)
# You can skip this if 1 student = 1 supervisor
c.execute("""
CREATE TABLE IF NOT EXISTS project_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    staff_id VARCHAR(20) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_primary TINYINT(1) DEFAULT 1,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON DELETE CASCADE,
    UNIQUE KEY unique_assignment (project_id, staff_id)
);
""")


# Commit all changes
conn.commit()

upload_dir = "uploads"
os.makedirs(upload_dir, exist_ok=True)

def get_db_connection():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    
    try:
        if not os.path.exists(config_path):
            # Create default config if not exists
            config['Database'] = {
                'host': '172.17.99.188',
                'port': '3306',
                'user': 'root',
                'password': '',
                'database': 'capstone_db'
            }
            with open(config_path, 'w') as f:
                config.write(f)
            
            messagebox.showinfo("First Run", 
                "config.ini file created.\n\n"
                "Please edit the 'host' value with the correct server IP address.")
        
        config.read(config_path)
        db_config = config['Database']

        conn = mysql.connector.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        return conn

    except Error as err:
        messagebox.showerror("Database Connection Failed", 
            f"Could not connect to database.\n\n"
            f"Error: {err}\n\n"
            f"Make sure:\n"
            f"1. XAMPP is running on the server PC\n"
            f"2. The IP in config.ini is correct\n"
            f"3. You are on the same network")
        return None
    except Exception as e:
        messagebox.showerror("Config Error", f"Config file error: {e}")
        return None
    
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def detect_user_type(userid):
        userid = userid.upper().strip()
        if '/' in userid:
            return 'student'
        else:
            return 'staff'
    
class RegisterWindow:
    def __init__(self, parent):
        self.top = Toplevel(parent)
        self.top.title("Register - Final-Year PMS")
        self.top.geometry("560x620")
        self.top.resizable(False, False)
        self.top.configure(bg="#f8fafc")

        style = ttk.Style(self.top)
        style.theme_use('clam')

        container = ttk.Frame(self.top, padding=40)
        container.pack(fill=BOTH, expand=True)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=3)

        row = 0

        ttk.Label(container, text="Create Your Account", font=("Segoe UI", 18, "bold")).grid(
            row=row, column=0, columnspan=2, pady=(0,25), sticky=W)
        row += 1

        # Email
        ttk.Label(container, text="Email *").grid(row=row, column=0, sticky=W, pady=8)
        self.email_entry = ttk.Entry(container, width=40, font=("Segoe UI", 11))
        self.email_entry.grid(row=row, column=1, sticky=EW, pady=8)
        row += 1

        # ID Field (Admission or Staff ID)
        ttk.Label(container, text="Admission No / Staff ID *").grid(row=row, column=0, sticky=W, pady=8)
        self.id_entry = ttk.Entry(container, width=40, font=("Segoe UI", 11))
        self.id_entry.grid(row=row, column=1, sticky=EW, pady=8)
        row += 1

        ttk.Label(container, text="(Student IDs contain '/' e.g. BCS/M/1234/2025)", 
                  font=("Segoe UI", 9), foreground="gray").grid(row=row, column=1, sticky=W)
        row += 1

        # Full Name
        ttk.Label(container, text="Full Name *").grid(row=row, column=0, sticky=W, pady=8)
        self.name_entry = ttk.Entry(container, width=40, font=("Segoe UI", 11))
        self.name_entry.grid(row=row, column=1, sticky=EW, pady=8)
        row += 1

        # Password
        ttk.Label(container, text="Password *").grid(row=row, column=0, sticky=W, pady=8)
        self.pass_entry = ttk.Entry(container, width=40, show="•", font=("Segoe UI", 11))
        self.pass_entry.grid(row=row, column=1, sticky=EW, pady=8)
        row += 1

        ttk.Label(container, text="Confirm Password *").grid(row=row, column=0, sticky=W, pady=8)
        self.confirm_entry = ttk.Entry(container, width=40, show="•", font=("Segoe UI", 11))
        self.confirm_entry.grid(row=row, column=1, sticky=EW, pady=8)
        row += 1

        # Register Button
        ttk.Button(container, text="Register Account", command=self.register_user).grid(
            row=row, column=0, columnspan=2, pady=30, sticky=EW)

        ttk.Button(container, text="Cancel", command=self.top.destroy).grid(
            row=row+1, column=0, columnspan=2, sticky=EW)

        self.email_entry.focus_set()

    def register_user(self):
        email = self.email_entry.get().strip()
        userid = self.id_entry.get().strip().upper()
        fullname = self.name_entry.get().strip()
        password = self.pass_entry.get()
        confirm = self.confirm_entry.get()

        if not email or not userid or not fullname or not password:
            messagebox.showwarning("Missing Fields", "All fields are required.")
            return

        if password != confirm:
            messagebox.showwarning("Mismatch", "Passwords do not match.")
            return

        if len(password) < 6:
            messagebox.showwarning("Weak Password", "Password must be at least 6 characters.")
            return

        user_type = detect_user_type(userid)

        conn = get_db_connection()
        if not conn: return
        cursor = conn.cursor()

        try:
            # Check if ID or email already exists
            cursor.execute("SELECT username FROM users WHERE username = %s OR email = %s", (userid, email))
            if cursor.fetchone():
                messagebox.showerror("Exists", "This ID or email is already registered.")
                return

            now = datetime.now()
            hashed=hash_password(password)

            # Insert into reference table + users
            if user_type == 'student':
                cursor.execute("""
                    INSERT INTO students (admission_no, full_name, email, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (userid, fullname, email, now))

                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role, created_at)
                    VALUES (%s, %s, %s, 'student', %s)
                """, (userid, email, hashed, now))

            else:  # staff
                cursor.execute("""
                    INSERT INTO staff (staff_id, full_name, email, department, created_at)
                    VALUES (%s, %s, %s, 'CISK', %s)
                """, (userid, fullname, email, now))

                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role, created_at)
                    VALUES (%s, %s, %s, 'staff', %s)
                """, (userid, email, hashed, now))

            conn.commit()
            messagebox.showinfo("Success", 
                f"Account created successfully!\n\n"
                f"ID: {userid}\n"
                f"Role: {user_type.capitalize()}\n\n"
                f"You can now login.\n\n"
                f"Note: Only admin can promote staff to Supervisor.")
            self.top.destroy()

        except mysql.connector.Error as err:
            conn.rollback()
            messagebox.showerror("Error", f"Registration failed:\n{err}")
        finally:
            cursor.close()
            conn.close() 

class AdminDashboard:
    def __init__(self, root, current_user):
        self.root = root
        self.user = current_user

        self.root.title("Admin Dashboard – Final-Year PMS")
        self.root.geometry("1200x680")
        self.root.minsize(1050, 640)
        self.root.configure(bg="#f8fafc")

        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=10, font=("Segoe UI", 11))
        style.configure("Danger.TButton", background="#dc2626", foreground="white", font=("Segoe UI", 11, "bold"))
        style.map("Danger.TButton", background=[("active", "#b91c1c")])

        # Header
        header = Frame(self.root, bg="#1e40af", height=80)
        header.pack(fill=X)

        Label(header, text="Admin Dashboard", fg="white", bg="#1e40af",
              font=("Segoe UI", 22, "bold")).pack(side=LEFT, padx=30, pady=20)

        # Logout / Back button
        ttk.Button(header, text="Back to Login", style="Danger.TButton",
                   command=self.back_to_main).pack(side=RIGHT, padx=30, pady=20)

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=20, pady=15)

        # ── Tab 1: All Projects ────────────────────────────────
        self.projects_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.projects_tab, text="All Projects")
        self.build_projects_tab()

        # ── Tab 2: All Students ────────────────────────────────
        self.students_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.students_tab, text="All Students")
        self.build_students_tab()

        # ── Tab 3: Staff & Supervisors ─────────────────────────
        self.staff_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.staff_tab, text="Staff & Supervisors")
        self.build_staff_tab()

        # ── Tab 4: assign supervisor ─────────────────────────
        self.build_assign_supervisor_tab()

        #Tab 5: perform functions
        self.build_publish_tab()
    

    # ──────────────────────────────────────────────────────────
    # Tab: All Projects
    # ──────────────────────────────────────────────────────────
    def build_projects_tab(self):
        frame = ttk.Frame(self.projects_tab, padding=20)
        frame.pack(fill=BOTH, expand=True)

        Label(frame, text="All Submitted Projects", font=("Segoe UI", 18, "bold")).pack(anchor=W, pady=(0,15))

        ttk.Button(frame, text="Refresh", command=self.load_all_projects).pack(anchor=W, pady=(0,10))

        columns = ("id", "title", "student", "supervisor", "submitted", "status", "marks")
        self.projects_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)

        self.projects_tree.heading("id", text="ID")
        self.projects_tree.heading("title", text="Title")
        self.projects_tree.heading("student", text="Student")
        self.projects_tree.heading("supervisor", text="Supervisor")
        self.projects_tree.heading("submitted", text="Submitted")
        self.projects_tree.heading("status", text="Status")
        self.projects_tree.heading("marks", text="Marks")

        self.projects_tree.column("id", width=60, anchor="center")
        self.projects_tree.column("title", width=280)
        self.projects_tree.column("student", width=140)
        self.projects_tree.column("supervisor", width=140)
        self.projects_tree.column("submitted", width=140)
        self.projects_tree.column("status", width=110, anchor="center")
        self.projects_tree.column("marks", width=80, anchor="center")

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self.projects_tree.yview)
        self.projects_tree.configure(yscroll=vsb.set)

        self.projects_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self.load_all_projects()

    def load_all_projects(self):
        for item in self.projects_tree.get_children():
            self.projects_tree.delete(item)

        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    p.id, p.title, p.student_admission, 
                    COALESCE(p.supervisor_staff_id, '-') AS supervisor,
                    p.submitted_at, p.status, p.marks
                FROM projects p
                ORDER BY p.submitted_at DESC
            """)
            for row in cursor.fetchall():
                self.projects_tree.insert("", END, values=(
                    row['id'],
                    row['title'],
                    row['student_admission'],
                    row['supervisor'],
                    row['submitted_at'].strftime("%Y-%m-%d %H:%M"),
                    row['status'].capitalize(),
                    row['marks'] if row['marks'] is not None else "-"
                ))
        finally:
            cursor.close()
            conn.close()

    # ──────────────────────────────────────────────────────────
    # Back to main screen (login)
    # ──────────────────────────────────────────────────────────
    def back_to_main(self):
        if messagebox.askyesno("Confirm", "Log out and return to login screen?"):
            self.root.destroy()
            win =Tk()
            MainInterface(win)
            win.mainloop()

    # ──────────────────────────────────────────────────────────
    # Tab: All Students
    # ──────────────────────────────────────────────────────────
    def build_students_tab(self):
        frame = ttk.Frame(self.students_tab, padding=20)
        frame.pack(fill=BOTH, expand=True)

        Label(frame, text="All Registered Students", font=("Segoe UI", 18, "bold")).pack(anchor=W, pady=(0,15))

        ttk.Button(frame, text="Refresh", command=self.load_all_students).pack(anchor=W, pady=(0,10))

        columns = ("adm_no", "name", "email", "created")
        self.students_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)

        self.students_tree.heading("adm_no", text="Admission No")
        self.students_tree.heading("name", text="Full Name")
        self.students_tree.heading("email", text="Email")
        self.students_tree.heading("created", text="Registered")

        self.students_tree.column("adm_no", width=140, anchor="center")
        self.students_tree.column("name", width=260)
        self.students_tree.column("email", width=260)
        self.students_tree.column("created", width=160)

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self.students_tree.yview)
        self.students_tree.configure(yscroll=vsb.set)

        self.students_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self.load_all_students()

    def load_all_students(self):
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)

        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT admission_no, full_name, email, created_at
                FROM students
                ORDER BY created_at DESC
            """)
            for row in cursor.fetchall():
                self.students_tree.insert("", END, values=(
                    row['admission_no'],
                    row['full_name'],
                    row['email'] or "-",
                    row['created_at'].strftime("%Y-%m-%d %H:%M")
                ))
        finally:
            cursor.close()
            conn.close()

    # ──────────────────────────────────────────────────────────
    # Tab: Staff & Supervisors (with promotion)
    # ──────────────────────────────────────────────────────────
    def build_staff_tab(self):
        frame = ttk.Frame(self.staff_tab, padding=20)
        frame.pack(fill=BOTH, expand=True)

        Label(frame, text="Staff & Supervisors Management", font=("Segoe UI", 18, "bold")).pack(anchor=W, pady=(0,15))

        btn_frame = Frame(frame)
        btn_frame.pack(fill=X, pady=8)

        ttk.Button(btn_frame, text="Refresh", command=self.load_staff_list).pack(side=LEFT, padx=5)
        self.promote_btn = ttk.Button(btn_frame, text="Promote to Supervisor",
                                      command=self.promote_to_supervisor, state="disabled")
        self.promote_btn.pack(side=LEFT, padx=5)

        columns = ("staff_id", "name", "email", "department", "role")
        self.staff_tree = ttk.Treeview(frame, columns=columns, show="headings", height=18)

        self.staff_tree.heading("staff_id", text="Staff ID")
        self.staff_tree.heading("name", text="Full Name")
        self.staff_tree.heading("email", text="Email")
        self.staff_tree.heading("department", text="Department")
        self.staff_tree.heading("role", text="Role")

        self.staff_tree.column("staff_id", width=120, anchor="center")
        self.staff_tree.column("name", width=220)
        self.staff_tree.column("email", width=220)
        self.staff_tree.column("department", width=180)
        self.staff_tree.column("role", width=100, anchor="center")

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self.staff_tree.yview)
        self.staff_tree.configure(yscroll=vsb.set)

        self.staff_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self.staff_tree.bind("<<TreeviewSelect>>", self.on_staff_select)
        self.load_staff_list()

    def load_staff_list(self):
        for item in self.staff_tree.get_children():
            self.staff_tree.delete(item)

        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT s.staff_id, s.full_name, s.email, s.department, u.role
                FROM staff s
                LEFT JOIN users u ON s.staff_id = u.username
                ORDER BY s.full_name
            """)
            for row in cursor.fetchall():
                role = row['role'] if row['role'] else "—"
                self.staff_tree.insert("", END, values=(
                    row['staff_id'],
                    row['full_name'],
                    row['email'] or "—",
                    row['department'] or "—",
                    role
                ))
        finally:
            cursor.close()
            conn.close()

    def on_staff_select(self, event):
        selected = self.staff_tree.selection()
        if selected:
            values = self.staff_tree.item(selected[0])['values']
            current_role = values[4]
            self.promote_btn.config(state="normal" if current_role == "staff" else "disabled")

    def promote_to_supervisor(self):
        selected = self.staff_tree.selection()
        if not selected:
            return

        values = self.staff_tree.item(selected[0])['values']
        staff_id = values[0]
        name = values[1]

        if messagebox.askyesno("Confirm", f"Promote {name} ({staff_id}) to Supervisor?"):
            conn = get_db_connection()
            if not conn: return

            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE users SET role = 'supervisor' WHERE username = %s AND role = 'staff'", (staff_id,))
                if cursor.rowcount == 1:
                    conn.commit()
                    messagebox.showinfo("Success", f"{name} is now a Supervisor.")
                    self.load_staff_list()
                else:
                    messagebox.showwarning("No change", "User was not in 'staff' role or already updated.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                cursor.close()
                conn.close()

    # ──────────────────────────────────────────────────────────
    # Tab: Assign Supervisors
    # ──────────────────────────────────────────────────────────
    def build_assign_supervisor_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Assign Supervisors")

        frame = ttk.Frame(tab, padding=25)
        frame.pack(fill=BOTH, expand=True)

        Label(frame, text="Assign / Change Supervisor for Students", 
            font=("Segoe UI", 18, "bold")).pack(anchor=W, pady=(0,20))

        # ── Top: Select Student ───────────────────────────────
        select_frame = ttk.LabelFrame(frame, text="Select Student Project")
        select_frame.pack(fill=X, pady=10)

        Label(select_frame, text="Student:").pack(side=LEFT, padx=10, pady=10)
        self.student_combo = ttk.Combobox(select_frame, width=40, state="readonly")
        self.student_combo.pack(side=LEFT, padx=10, pady=10)

        ttk.Button(select_frame, text="Load Students", command=self.load_students_for_assignment).pack(side=LEFT, padx=10)

        # ── Supervisor selection ──────────────────────────────
        assign_frame = ttk.LabelFrame(frame, text="Assign Supervisor")
        assign_frame.pack(fill=X, pady=15)

        Label(assign_frame, text="Supervisor:").pack(side=LEFT, padx=10, pady=10)
        self.supervisor_combo = ttk.Combobox(assign_frame, width=40, state="readonly")
        self.supervisor_combo.pack(side=LEFT, padx=10, pady=10)

        ttk.Button(assign_frame, text="Load Supervisors", command=self.load_supervisors).pack(side=LEFT, padx=10)

        # ── Current assignment display ────────────────────────
        self.current_assignment_label = Label(frame, text="Current supervisor: —", font=("Segoe UI", 11), fg="#4b5563")
        self.current_assignment_label.pack(anchor=W, pady=10)

        # ── Action buttons ────────────────────────────────────
        btn_frame = Frame(frame)
        btn_frame.pack(fill=X, pady=20)

        ttk.Button(btn_frame, text="Assign / Update Supervisor", command=self.assign_supervisor).pack(side=LEFT, padx=10)
        ttk.Button(btn_frame, text="Clear Assignment", command=self.clear_assignment).pack(side=LEFT, padx=10)

        # Load initial data
        self.load_students_for_assignment()
        self.load_supervisors()

    def load_students_for_assignment(self):
        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT DISTINCT p.student_admission, s.full_name
                FROM projects p
                JOIN students s ON p.student_admission = s.admission_no
                ORDER BY s.full_name
            """)
            students = cursor.fetchall()

            self.student_combo['values'] = [f"{s['student_admission']} - {s['full_name']}" for s in students]
            if students:
                self.student_combo.current(0)
                self.show_current_assignment()
        finally:
            cursor.close()
            conn.close()

    def load_supervisors(self):
        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT staff_id, full_name 
                FROM staff s
                JOIN users u ON s.staff_id = u.username
                WHERE u.role IN ('supervisor', 'staff')
                ORDER BY full_name
            """)
            supervisors = cursor.fetchall()

            self.supervisor_combo['values'] = [f"{s['staff_id']} - {s['full_name']}" for s in supervisors]
            if supervisors:
                self.supervisor_combo.current(0)
        finally:
            cursor.close()
            conn.close()

    def show_current_assignment(self):
        selected = self.student_combo.get()
        if not selected:
            self.current_assignment_label.config(text="Current supervisor: —")
            return

        student_id = selected.split(" - ")[0].strip()

        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT supervisor_staff_id, s.full_name
                FROM projects p
                LEFT JOIN staff s ON p.supervisor_staff_id = s.staff_id
                WHERE p.student_admission = %s
                LIMIT 1
            """, (student_id,))
            row = cursor.fetchone()

            if row and row['supervisor_staff_id']:
                text = f"Current supervisor: {row['supervisor_staff_id']} - {row['full_name'] or 'Unknown'}"
            else:
                text = "Current supervisor: — (not assigned)"
            self.current_assignment_label.config(text=text)
        finally:
            cursor.close()
            conn.close()

    def assign_supervisor(self):
        student_str = self.student_combo.get()
        supervisor_str = self.supervisor_combo.get()

        if not student_str or not supervisor_str:
            messagebox.showwarning("Incomplete", "Please select both student and supervisor.")
            return

        student_id = student_str.split(" - ")[0].strip()
        supervisor_id = supervisor_str.split(" - ")[0].strip()

        if messagebox.askyesno("Confirm", 
            f"Assign {supervisor_str}\nto student {student_str}?"):
            
            conn = get_db_connection()
            if not conn: return

            cursor = conn.cursor()
            try:
                # Update all projects of this student (or just future ones — your choice)
                cursor.execute("""
                    UPDATE projects 
                    SET supervisor_staff_id = %s
                    WHERE student_admission = %s
                """, (supervisor_id, student_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    messagebox.showinfo("Success", f"Supervisor assigned to {cursor.rowcount} project(s).")
                    self.show_current_assignment()
                else:
                    messagebox.showinfo("No change", "No projects found for this student.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                cursor.close()
                conn.close()

    def clear_assignment(self):
        student_str = self.student_combo.get()
        if not student_str:
            return

        student_id = student_str.split(" - ")[0].strip()

        if messagebox.askyesno("Confirm Clear", 
            f"Remove supervisor assignment from student {student_str}?"):
            
            conn = get_db_connection()
            if not conn: return

            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE projects 
                    SET supervisor_staff_id = NULL
                    WHERE student_admission = %s
                """, (student_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    messagebox.showinfo("Success", "Supervisor assignment cleared.")
                    self.show_current_assignment()
                else:
                    messagebox.showinfo("No change", "No projects had a supervisor.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                cursor.close()
                conn.close()
    
    # publish, unpublish, delete tab
    def build_publish_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Publish Projects")

        frame = ttk.Frame(tab, padding=20)
        frame.pack(fill=BOTH, expand=True)

        # Title + search
        top = Frame(frame)
        top.pack(fill=X, pady=(0, 15))

        Label(top, text="Publish Reviewed Projects (≥ 40 marks)", 
            font=("Segoe UI", 18, "bold")).pack(side=LEFT)

        search_frame = Frame(top)
        search_frame.pack(side=RIGHT)

        Label(search_frame, text="Search:").pack(side=LEFT, padx=(0, 8))
        self.publish_search_var = StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.publish_search_var, width=35)
        search_entry.pack(side=LEFT, padx=8)
        search_entry.bind("<KeyRelease>", lambda e: self.filter_publish_list())

        # Table
        columns = ("id", "title", "student", "marks", "published")
        self.publish_tree = ttk.Treeview(frame, columns=columns, show="headings", height=18)

        self.publish_tree.heading("id", text="ID")
        self.publish_tree.heading("title", text="Project Title")
        self.publish_tree.heading("student", text="Student")
        self.publish_tree.heading("marks", text="Marks")
        #self.publish_tree.heading("feedback_short", text="Feedback")
        self.publish_tree.heading("published", text="Published")

        self.publish_tree.column("id", width=40, anchor="center")
        self.publish_tree.column("title", width=280)
        self.publish_tree.column("student", width=140)
        self.publish_tree.column("marks", width=60, anchor="center")
        #self.publish_tree.column("feedback_short", width=220)
        self.publish_tree.column("published", width=100, anchor="center")

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self.publish_tree.yview)
        self.publish_tree.configure(yscroll=vsb.set)

        self.publish_tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        # Buttons
        btn_frame = Frame(frame)
        btn_frame.pack(fill=X, pady=15)

        ttk.Button(btn_frame, text="Refresh", command=self.load_publish_list).pack(side=LEFT, padx=5)
        self.publish_btn   = ttk.Button(btn_frame, text="Publish",   command=self.publish_selected, state="disabled")
        self.unpublish_btn = ttk.Button(btn_frame, text="Unpublish", command=self.unpublish_selected, state="disabled")
        self.delete_btn    = ttk.Button(btn_frame, text="Delete",    command=self.delete_selected, style="Danger.TButton", state="disabled")

        self.publish_btn.pack(side=LEFT, padx=5)
        self.unpublish_btn.pack(side=LEFT, padx=5)
        self.delete_btn.pack(side=LEFT, padx=5)

        # Bind selection → enable/disable buttons
        self.publish_tree.bind("<<TreeviewSelect>>", self.on_publish_select)

        # Initial load
        self.load_publish_list()

    def load_publish_list(self, filter_text=""):
        for item in self.publish_tree.get_children():
            self.publish_tree.delete(item)

        conn = get_db_connection()
        if not conn: return

        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT 
                    p.id, p.title, p.student_admission, 
                    s.full_name AS student_name,
                    p.marks, p.feedback, p.publish_approved
                FROM projects p
                JOIN students s ON p.student_admission = s.admission_no
                WHERE p.status = 'reviewed'
            """
            params = []

            if filter_text:
                query += " AND (p.title LIKE %s OR p.student_admission LIKE %s OR s.full_name LIKE %s)"
                like = f"%{filter_text}%"
                params.extend([like, like, like])

            query += " ORDER BY p.marks DESC, p.submitted_at DESC"

            cursor.execute(query, params)

            for row in cursor.fetchall():
                #feedback_short = (row['feedback'] or "")[:60] + ("..." if row['feedback'] and len(row['feedback']) > 60 else "")
                published = "Yes" if row['publish_approved'] else "No"

                iid = self.publish_tree.insert("", "end", values=(
                    row['id'],
                    row['title'],
                    f"{row['student_admission']} - {row['student_name']}",
                    row['marks'],
                    #feedback_short,
                    published
                ))

                # Visual cue: green if >=40 and published, orange if >=40 but not published
                if row['marks'] is not None and row['marks'] >= 40:
                    if row['publish_approved']:
                        self.publish_tree.item(iid, tags=('published',))
                    else:
                        self.publish_tree.item(iid, tags=('can_publish',))
                else:
                    self.publish_tree.item(iid, tags=('low_marks',))

            # Apply tag colors
            self.publish_tree.tag_configure('published',   foreground="#166534", background="#f0fdf4")
            self.publish_tree.tag_configure('can_publish', foreground="#b45309", background="#fffbeb")
            self.publish_tree.tag_configure('low_marks',   foreground="#991b1b", background="#fef2f2")

        finally:
            cursor.close()
            conn.close()

    def filter_publish_list(self):
        self.load_publish_list(self.publish_search_var.get().strip())

    def on_publish_select(self, event):
        selected = self.publish_tree.selection()
        if not selected:
            self.publish_btn.config(state="disabled")
            self.unpublish_btn.config(state="disabled")
            self.delete_btn.config(state="disabled")
            return

        item = self.publish_tree.item(selected[0])
        values = item['values']
        marks = values[3]
        published = values[4]

        # Enable delete always
        self.delete_btn.config(state="normal")

        # Publish / Unpublish logic
        if marks == "-" or marks < 40:
            self.publish_btn.config(state="disabled")
            self.unpublish_btn.config(state="disabled")
        else:
            if published == "Yes":
                self.publish_btn.config(state="disabled")
                self.unpublish_btn.config(state="normal")
            else:
                self.publish_btn.config(state="normal")
                self.unpublish_btn.config(state="disabled")

    def publish_selected(self):
        selected = self.publish_tree.selection()
        if not selected: return

        item = self.publish_tree.item(selected[0])
        pid = item['values'][0]

        if messagebox.askyesno("Publish", "Publish this project to public gallery?"):
            conn = get_db_connection()
            if not conn: return
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE projects SET publish_approved = 1 WHERE id = %s", (pid,))
                conn.commit()
                messagebox.showinfo("Done", "Project published.")
                self.load_publish_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                cursor.close()
                conn.close()

    def unpublish_selected(self):
        selected = self.publish_tree.selection()
        if not selected: return

        item = self.publish_tree.item(selected[0])
        pid = item['values'][0]

        if messagebox.askyesno("Unpublish", "Remove this project from public gallery?"):
            conn = get_db_connection()
            if not conn: return
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE projects SET publish_approved = 0 WHERE id = %s", (pid,))
                conn.commit()
                messagebox.showinfo("Done", "Project unpublished.")
                self.load_publish_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                cursor.close()
                conn.close()

    def delete_selected(self):
        selected = self.publish_tree.selection()
        if not selected: return

        item = self.publish_tree.item(selected[0])
        pid = item['values'][0]
        title = item['values'][1]

        if messagebox.askyesno("Delete", f"Delete project '{title}' permanently?\nThis cannot be undone."):
            conn = get_db_connection()
            if not conn: return
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM projects WHERE id = %s", (pid,))
                conn.commit()
                messagebox.showinfo("Done", "Project deleted.")
                self.load_publish_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                cursor.close()
                conn.close()

# Student Dashboard Window
# ────────────────────────────────────────────────
class StudentDashboard:
    def __init__(self, root, current_user):
        """
        current_user: dict with at least {'username': str, 'role': 'student', 'email': str, ...}
        """
        self.root = root
        self.user = current_user

        self.root.title("Student Dashboard – Final-Year PMS")
        self.root.geometry("1200x680")
        self.root.minsize(1050, 640)
        self.root.configure(bg="#f9fafb")

        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=10, font=("Segoe UI", 11))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), background="#2563eb", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])

        # ── Header ─────────────────────────────────────────────────────
        header = Frame(self.root, bg="#1e40af", height=80)
        header.pack(fill=X)

        Label(header, text="Student Dashboard", fg="white", bg="#1e40af",
              font=("Segoe UI", 20, "bold")).pack(side=LEFT, padx=40, pady=20)
        
        # Right side container for user info + button
        right_container = Frame(header, bg="#1e40af")
        right_container.pack(side=RIGHT, padx=30, pady=15)

        Label(header, text=f"{self.user.get('username', 'Student')}  •  {self.user.get('email', '')}",
              fg="white", bg="#1e40af", font=("Segoe UI", 12)).pack(side=LEFT, padx=(0, 30))
        
        ttk.Button(header, text="Back to Login", style="Danger.TButton",
                   command=self.back_to_main).pack(side=RIGHT)

        # ── Main content area ──────────────────────────────────────────
        main = ttk.Frame(self.root, padding=25)
        main.pack(fill=BOTH, expand=True)

        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        # Status / summary card
        status_frame = ttk.LabelFrame(main, text="Project Status & Information")
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0,20), padx=10)

        self.status_text = StringVar(value="Loading your project information...")
        ttk.Label(status_frame, textvariable=self.status_text, font=("Segoe UI", 11),
                  wraplength=900, justify="left").pack(pady=15, padx=20, anchor="w")

        # Upload button
        ttk.Button(main, text="Upload New Project (PDF / DOCX)", 
                   command=self.upload_new_project, style="Accent.TButton").grid(
            row=0, column=0, pady=12, sticky="e", padx=20)

        # Projects list
        projects_frame = ttk.LabelFrame(main, text="My Submitted Projects")
        projects_frame.grid(row=1, column=0, sticky="nsew", pady=10, padx=10)

        columns = ("title", "submitted", "status", "marks", "feedback", "supervisor")
        self.tree = ttk.Treeview(projects_frame, columns=columns, show="headings", height=16)

        self.tree.heading("title", text="Project Title")
        self.tree.heading("submitted", text="Submitted On")
        self.tree.heading("status", text="Status")
        self.tree.heading("marks", text="Marks")
        self.tree.heading("feedback", text="Supervisor Feedback")
        self.tree.heading("supervisor", text="Supervisor")

        self.tree.column("title", width=340, anchor="w")
        self.tree.column("submitted", width=120, anchor="center")
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("marks", width=50, anchor="center")
        self.tree.column("feedback", width=320, anchor="w")
        self.tree.column("supervisor", width=220, anchor="w")

        vsb = ttk.Scrollbar(projects_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        style.configure("Danger.TButton", background="#dc2626", foreground="white", font=("Segoe UI", 11, "bold"))
        style.map("Danger.TButton", background=[("active", "#b91c1c")])

        # Footer
        self.footer_var = StringVar(value=f"Logged in as {self.user.get('username')} • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        footer = Label(self.root, textvariable=self.footer_var, bd=1, relief=SUNKEN,
                       anchor=W, font=("Segoe UI", 9), bg="#e5e7eb")
        footer.pack(side=BOTTOM, fill=X)

        # Load data immediately
        self.refresh_projects()     

    # ──────────────────────────────────────────────────────────
    # Back to main screen (login)
    # ──────────────────────────────────────────────────────────
    def back_to_main(self):
        if messagebox.askyesno("Confirm", "Log out and return to login screen?"):
            self.root.destroy()
            win =Tk()
            MainInterface(win)
            win.mainloop()

    def refresh_projects(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = get_db_connection()
        if not conn:
            self.status_text.set("Cannot connect to database.")
            return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    p.title, 
                    p.submitted_at, 
                    p.status, 
                    p.marks, 
                    p.feedback,
                    s.full_name AS supervisor_name
                FROM projects p
                LEFT JOIN staff s ON p.supervisor_staff_id = s.staff_id
                WHERE p.student_admission = %s
                ORDER BY p.submitted_at DESC
            """, (self.user['username'],))

            rows = cursor.fetchall()

            if not rows:
                self.status_text.set(
                    "You have not submitted any project yet.\n"
                    "Click the button above to upload your capstone project."
                )
            else:
                pending_count = sum(1 for r in rows if r['status'] == 'pending')
                reviewed_count = len(rows) - pending_count

                msg = f"You have submitted {len(rows)} project(s).\n"
                if pending_count > 0:
                    msg += f"{pending_count} awaiting supervisor review.\n"
                if reviewed_count > 0:
                    msg += f"{reviewed_count} already reviewed."
                
                # ← Add supervisor info here (for the latest project, or most relevant)
                latest_sup = rows[0].get('supervisor_name')
                if latest_sup:
                    msg += f"\nYour supervisor: {latest_sup}"
                else:
                    msg += "\nYour supervisor: Not assigned yet"

                self.status_text.set(msg)

            # Insert rows into Treeview — include supervisor
            for row in rows:
                fb_short = (row['feedback'] or "-")[:80] + ("..." if row['feedback'] and len(row['feedback']) > 80 else "")
                supervisor_display = row['supervisor_name'] or "Not assigned"

                self.tree.insert("", END, values=(
                    row['title'],
                    row['submitted_at'].strftime("%Y-%m-%d %H:%M"),
                    row['status'].capitalize(),
                    row['marks'] if row['marks'] is not None else "-",
                    fb_short,
                    supervisor_display                     # ← this goes into the supervisor column
                ))

        except Exception as e:
            messagebox.showerror("Query Error", f"Failed to load projects:\n{e}")
        finally:
            cursor.close()
            conn.close()


    def upload_new_project(self):
        file_path = filedialog.askopenfilename(
            title="Select your project file",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
        )
        if not file_path:
            return

        title = simpledialog.askstring("Project Title", "Enter the title of your project:")
        if not title or not title.strip():
            messagebox.showwarning("Title required", "Please enter your project title.")
            return

        # Sanitize username by replacing slashes
        safe_username = self.user['username'].replace("/", "_")
        safe_filename = f"{safe_username}_{os.path.basename(file_path)}"
        destination = os.path.join(upload_dir, safe_filename)

        try:
            #shutil.copy(file_path, destination)
            os.rename(file_path, destination)  # moves file

        except Exception as e:
            messagebox.showerror("File Copy Error", f"Could not save file:\n{e}")
            return

        conn = get_db_connection()
        if not conn:
            return

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO projects 
                (title, student_admission, file_path, submitted_at, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """, (title.strip(), self.user['username'], destination, datetime.now()))

            conn.commit()
            messagebox.showinfo("Upload Successful", 
                f"Project '{title}' has been submitted.\n"
                "It is now pending review by your supervisor.")
            
            self.refresh_projects()

        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", str(err))
        finally:
            cursor.close()
            conn.close()

#supervision dashboard

class SupervisorDashboard:
    def __init__(self, root, current_user):
        """
        current_user: dict with at least {'username': str, 'role': 'supervisor', ...}
        """
        self.root = root
        self.user = current_user
        self.staff_id = current_user['username']

        self.root.title("Supervisor Dashboard – Final-Year PMS")
        self.root.geometry("1200x680")
        self.root.minsize(1050, 640)
        self.root.configure(bg="#f8fafc")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=10, font=("Segoe UI", 11))
        style.configure("Danger.TButton", background="#dc2626", foreground="white", font=("Segoe UI", 11, "bold"))
        style.map("Danger.TButton", background=[("active", "#b91c1c")])

        # Header
        header = Frame(self.root, bg="#1e40af", height=80)
        header.pack(fill=X)

        Label(header, text="Supervisor Dashboard", fg="white", bg="#1e40af",
              font=("Segoe UI", 22, "bold")).pack(side=LEFT, padx=30, pady=20)

        ttk.Button(header, text="Back to Login", style="Danger.TButton",
                   command=self.back_to_main).pack(side=RIGHT, padx=30, pady=20)

        # Main content
        main = ttk.Frame(self.root, padding=25)
        main.pack(fill=BOTH, expand=True)

        Label(main, text=f"Welcome, {self.user.get('username', 'Supervisor')}", 
              font=("Segoe UI", 16, "bold")).pack(anchor=W, pady=(0,20))

        # Action buttons
        btn_frame = Frame(main)
        btn_frame.pack(fill=X, pady=10, padx=10)

        ttk.Button(btn_frame, text="Refresh List", command=self.load_projects).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Review Selected Project", command=self.review_selected).pack(side=LEFT, padx=5)

        # Projects list
        frame = ttk.LabelFrame(main, text="Projects Assigned to You")
        frame.pack(fill=BOTH, expand=True, pady=10, padx=10)

        columns = ("id", "title", "student", "submitted", "status", "marks")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)

        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Project Title")
        self.tree.heading("student", text="Student")
        self.tree.heading("submitted", text="Submitted")
        self.tree.heading("status", text="Status")
        self.tree.heading("marks", text="Marks")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("title", width=340)
        self.tree.column("student", width=140)
        self.tree.column("submitted", width=140)
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("marks", width=80, anchor="center")

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        # Load data
        self.load_projects()

    def load_projects(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        conn = get_db_connection()
        if not conn:
            return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    p.id, p.title, p.student_admission, 
                    s.full_name AS student_name,
                    p.submitted_at, p.status, p.marks
                FROM projects p
                JOIN students s ON p.student_admission = s.admission_no
                WHERE p.supervisor_staff_id = %s
                ORDER BY p.submitted_at DESC
            """, (self.staff_id,))

            for row in cursor.fetchall():
                self.tree.insert("", END, values=(
                    row['id'],
                    row['title'],
                    f"{row['student_admission']} - {row['student_name']}",
                    row['submitted_at'].strftime("%Y-%m-%d %H:%M"),
                    row['status'].capitalize(),
                    row['marks'] if row['marks'] is not None else "—"
                ))
        finally:
            cursor.close()
            conn.close()

    def review_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a project first.")
            return

        values = self.tree.item(selected[0])['values']
        project_id = values[0]
        title = values[1]
        student = values[2]

        # Fetch project data from database (including file_path)
        conn = get_db_connection()
        if not conn:
            return

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT id, title, file_path, student_admission
                FROM projects
                WHERE id = %s AND supervisor_staff_id = %s
            """, (project_id, self.staff_id))

            project = cursor.fetchone()
            if not project:
                messagebox.showwarning("Not found", "Project not found or not assigned to you.")
                return

        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return
        finally:
            cursor.close()
            conn.close()

        # Now project is defined — open the file
        file_path = project["file_path"]
        if os.path.exists(file_path):
            try:
                if os.name == "nt":          # Windows
                    os.startfile(file_path)
                elif os.name == "posix":
                    if sys.platform == "darwin":  # macOS
                        subprocess.call(["open", file_path])
                    else:                         # Linux
                        subprocess.call(["xdg-open", file_path])
                # Optional: messagebox.showinfo("File Opened", "Opened in default viewer.")
            except Exception as e:
                messagebox.showwarning("Open Failed", f"Could not open file:\n{e}")
        else:
            messagebox.showwarning("File Not Found", f"Path does not exist:\n{file_path}")

        # Open the marking form
        self.open_marking_form(project, project_id, title, student)


    # ────────────────────────────────────────────────
    # This MUST be OUTSIDE review_selected — at class level
    # ────────────────────────────────────────────────
    def open_marking_form(self, project, project_id, title, student):
        dialog = Toplevel(self.root)
        dialog.title(f"Review: {title}")
        dialog.geometry("620x580")
        dialog.transient(self.root)
        dialog.grab_set()

        Label(dialog, text=f"Project: {title}", font=("Segoe UI", 14, "bold")).pack(pady=10)
        Label(dialog, text=f"Student: {student}").pack(pady=5)

        ttk.Label(dialog, text="Marks (0–100):").pack(anchor="w", padx=20, pady=(20,5))
        marks_var = IntVar(value=project.get('marks', 0))   # pre-fill if exists
        ttk.Entry(dialog, textvariable=marks_var, width=10).pack(anchor="w", padx=20)

        ttk.Label(dialog, text="Feedback / Comments:").pack(anchor="w", padx=20, pady=(15,5))
        feedback_text = Text(dialog, height=12, width=70, wrap="word")
        feedback_text.pack(padx=20, pady=5, fill=BOTH, expand=True)

        # Pre-fill existing feedback
        if project.get('feedback'):
            feedback_text.insert("1.0", project['feedback'])

        def submit_review():
            marks = marks_var.get()
            feedback = feedback_text.get("1.0", END).strip()

            if not (0 <= marks <= 100):
                messagebox.showwarning("Invalid", "Marks must be between 0 and 100.")
                return

            conn = get_db_connection()
            if not conn:
                return

            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE projects 
                    SET marks = %s, feedback = %s, status = 'reviewed'
                    WHERE id = %s AND supervisor_staff_id = %s
                """, (marks, feedback, project_id, self.staff_id))

                if cursor.rowcount == 1:
                    conn.commit()
                    messagebox.showinfo("Success", "Review submitted successfully.")
                    dialog.destroy()
                    self.load_projects()
                else:
                    messagebox.showwarning("No update", "Project not found or not assigned to you.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                cursor.close()
                conn.close()

        ttk.Button(dialog, text="Submit Review", command=submit_review).pack(pady=25)

    def back_to_main(self):
        if messagebox.askyesno("Logout", "Return to login screen?"):
            self.root.destroy()
            win =Tk()
            MainInterface(win)
            win.mainloop()


class MainInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("Final-Year Projects Management System")
        self.root.geometry("1200x680")          # Smaller default size
        self.root.minsize(1000, 640)
        self.root.configure(bg="#f8fafc")

        # ── Style ───────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("TLabel", background="#f8fafc", font=("Segoe UI", 11))
        style.configure("Hero.TLabel", font=("Segoe UI", 32, "bold"), foreground="#1e40af")
        style.configure("Tagline.TLabel", font=("Segoe UI", 14), foreground="#475569")
        style.configure("TButton", padding=10, font=("Segoe UI", 11))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=12,
                        background="#2563eb", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])

        style.configure("Stat.TLabel", font=("Segoe UI", 22, "bold"), foreground="#1e40af")
        style.configure("StatTitle.TLabel", font=("Segoe UI", 11), foreground="#64748b")

        # ── Header / Hero ───────────────────────────────────────────────
        hero = Frame(self.root, bg="#1e40af", height=120)  # Reduced height
        hero.pack(fill=X)

        Label(hero, text="FPMS", fg="white", bg="#1e40af",
              font=("Segoe UI", 36, "bold")).pack(pady=(30, 5))

        Label(hero, text="Discover, submit, supervise, monitor & Manage All Final-Year Projects", fg="#dbeafe", bg="#1e40af",
              font=("Segoe UI", 14)).pack()

        # ── Main container ──────────────────────────────────────────────
        main = Frame(self.root, bg="#f8fafc")
        main.pack(fill=BOTH, expand=True, padx=50, pady=10)

        # Search section
        search_container = Frame(main, bg="white", bd=1, relief="flat", height=120)
        search_container.pack(fill=X, pady=20, ipady=15, padx=20)
        search_container.configure(highlightbackground="#e2e8f0", highlightthickness=1)

        ttk.Label(search_container, text="Search for Posted Projects", font=("Segoe UI", 14, "bold")).pack(pady=(15, 8))

        search_frame = Frame(search_container, bg="white")
        search_frame.pack(fill=X, padx=30)

        self.search_var = StringVar()
        entry = ttk.Entry(search_frame, textvariable=self.search_var, width=60, font=("Segoe UI", 12))
        entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10), ipady=4)
        entry.insert(0, "e.g. AI in Agriculture, 2025, Jane Cheptoo...")
        entry.bind("<FocusIn>", lambda e: entry.delete(0, END) if entry.get().startswith("e.g.") else None)

        entry.focus_set()
        ttk.Button(search_frame, text="Search", style="Accent.TButton",
                   command=self.perform_search).pack(side=LEFT)

        # Results area (initially hidden message)
        self.results_frame = Frame(main, bg="#f8fafc", bd=1, relief="flat")
        self.results_frame.pack(fill=BOTH, expand=True, pady=5, padx=20)
        self.results_frame.configure(highlightbackground="#e2e8f0", highlightthickness=1)

        self.results_label = ttk.Label(self.results_frame,
                                       text="Enter a keyword above to see published Final-Year Projects",
                                       font=("Segoe UI", 12), foreground="#6b7280",
                                       background="#f8fafc", wraplength=900, justify="center")
        self.results_label.pack(expand=True, pady=30)

        # ── Bottom row: Auth buttons + Stats ────────────────────────────
        bottom_row = Frame(main, bg="#f8fafc", height=90)
        bottom_row.pack(fill=X, pady=20)

        # Left: Login/Register buttons
        auth_frame = Frame(bottom_row, bg="#f8fafc")
        auth_frame.pack(side=LEFT)

        ttk.Button(auth_frame, text="Login", command=self.open_login).pack(side=LEFT, padx=8)
        ttk.Button(auth_frame, text="Register", command=lambda: RegisterWindow(self.root)).pack(side=LEFT, padx=8)

        # Right: Stats cards
        stats_frame = Frame(bottom_row, bg="#f8fafc")
        stats_frame.pack(side=RIGHT)

        stats = [
            ("Published Projects", "200+", "#1e40af"),
            ("Students", "700+", "#059669"),
            ("Supervisors", "15+", "#7c3aed")
        ]

        for title, value, color in stats:
            card = Frame(stats_frame, bg="white", bd=1, relief="flat", height=70)
            card.pack(side=LEFT, padx=12, fill=Y)
            card.configure(highlightbackground="#e2e8f0", highlightthickness=1)

            Label(card, text=value, font=("Segoe UI", 20, "bold"), fg=color, bg="white").pack(pady=(10, 2))
            Label(card, text=title, font=("Segoe UI", 10), fg="#475569", bg="white").pack(pady=(0, 10))

        # ── Footer ──────────────────────────────────────────────────────
        footer = Frame(self.root, bg="#1e293b", height=30)
        footer.pack(side=BOTTOM, fill=X)

        Label(footer, text="© 2026 Final-Year Projects' Management System • Built By kowino for Academic Excellence",
              fg="#94a3b8", bg="#1e293b", font=("Segoe UI", 9)).pack(pady=10)

    def perform_search(self):
        query = self.search_var.get().strip()
        if not query or query.startswith("e.g."):
            messagebox.showinfo("Search", "Please enter a keyword, title, author name or year.")
            return

        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.results_frame,
                text=f"Searching for: \"{query}\"",
                font=("Segoe UI", 14, "bold"), background="#f8fafc").pack(anchor="w", pady=10, padx=20)

        conn = get_db_connection()
        if not conn:
            ttk.Label(self.results_frame,
                    text="Database connection failed.",
                    font=("Segoe UI", 12), foreground="red", background="#f8fafc").pack(pady=40)
            return

        cursor = conn.cursor(dictionary=True)  # ← important: dictionary=True so rows are dicts

        try:
            like_term = f"%{query}%"

            cursor.execute("""
                SELECT 
                    p.id,
                    p.title,
                    s.full_name          AS student_name,
                    s.admission_no,
                    sup.full_name        AS supervisor_name,
                    p.marks,
                    LEFT(p.feedback, 120) AS feedback_short,
                    p.file_path,
                    DATE_FORMAT(p.submitted_at, '%%Y-%%m-%%d') AS submitted_date
                FROM projects p
                JOIN students s ON p.student_admission = s.admission_no
                LEFT JOIN staff sup ON p.supervisor_staff_id = sup.staff_id
                WHERE p.publish_approved = 1
                AND p.status = 'reviewed'
                AND (
                    p.title               LIKE %s
                    OR s.full_name        LIKE %s
                    OR COALESCE(sup.full_name, '') LIKE %s
                    OR COALESCE(p.feedback, '')    LIKE %s
                )
                ORDER BY p.marks DESC, p.submitted_at DESC
                LIMIT 50
            """, [like_term] * 4)  # ← pass the parameters here!

            results = cursor.fetchall()

            if not results:
                ttk.Label(self.results_frame,
                        text="No matching published projects found.",
                        font=("Segoe UI", 12), foreground="#6b7280", background="#f8fafc").pack(pady=60)
                return

            # Show header
            ttk.Label(self.results_frame,
                    text=f"Found {len(results)} project(s)",
                    font=("Segoe UI", 13, "bold"), background="#f8fafc").pack(anchor="w", pady=10, padx=20)

            # Display results as cards
            for row in results:
                card = Frame(self.results_frame, bg="white", bd=1, relief="flat")
                card.pack(fill=X, pady=(5, 0), padx=20, ipady=10)
                card.configure(highlightbackground="#e2e8f0", highlightthickness=1)

                ttk.Label(card, text=row['title'], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=15, pady=(10, 2))
                ttk.Label(card, text=f"By {row['student_name']} ({row['admission_no']})", foreground="#64748b").pack(anchor="w", padx=15)

                sup = row['supervisor_name'] or "Not assigned"
                ttk.Label(card, text=f"Supervisor: {sup}", foreground="#4b5563").pack(anchor="w", padx=15, pady=(2, 0))

                ttk.Label(card, text=f"Marks: {row['marks'] if row['marks'] is not None else '—'}", 
                        foreground="#1e40af", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(6, 0))

                ttk.Label(card, text=f"Submitted: {row['submitted_date']}", foreground="#6b7280").pack(anchor="w", padx=15)

                # Make card clickable to open file
                card.bind("<Button-1>", lambda e, fp=row['file_path']: self.open_project_file(fp))
                for child in card.winfo_children():
                    child.bind("<Button-1>", lambda e, fp=row['file_path']: self.open_project_file(fp))

        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Query failed:\n{err}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            cursor.close()
            conn.close()

        clear_btn = ttk.Button(self.results_frame, text="clear", command=self.clear_search_results, width=10)
        clear_btn.pack(pady=(5, 0), ipady=3, anchor="e")


    
    def clear_search_results(self):
        """Reset search results and show original placeholder"""
        self.search_var.set("")
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.results_frame,
                text="Enter a search term above to see published projects",
                font=("Segoe UI", 12), foreground="#6b7280", background="#f8fafc", wraplength=900, justify="center").pack(expand=True, pady=80)

    #open file on click
    def open_project_file(self, file_path):
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("File Not Found", "The project file is missing or was not saved correctly.")
            return

        try:
            import subprocess
            import sys
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", file_path])
            else:
                subprocess.call(["xdg-open", file_path])
            # Optional: messagebox.showinfo("Opened", "File opened in default viewer.")
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open the file:\n{e}")

    def open_login(self):
        # Create login popup (modal style)
        login_win = Toplevel(self.root)
        login_win.title("Login")
        login_win.geometry("480x420")           # nice compact size
        login_win.resizable(False, False)

        # Center it on the main window
        login_win.transient(self.root)          # stays on top of main window
        login_win.grab_set()                    # blocks interaction with main window

        # Center calculation
        x = self.root.winfo_x() + (self.root.winfo_width() - 480) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 420) // 2
        login_win.geometry(f"480x420+{x}+{y}")

        # Inside the window
        frame = ttk.Frame(login_win, padding=30)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="Login", font=("Segoe UI", 20, "bold")).pack(pady=20)

        ttk.Label(frame, text="Username / Admission / Staff ID").pack(anchor="w")
        username_entry = ttk.Entry(frame, width=40)
        username_entry.pack(pady=8, fill=X)

        ttk.Label(frame, text="Password").pack(anchor="w", pady=(15,0))
        password_entry = ttk.Entry(frame, width=40, show="*")
        password_entry.pack(pady=8, fill=X)

        def handle_login():
            username = username_entry.get().strip().upper()
            password = password_entry.get().strip()

            if not username or not password:
                messagebox.showwarning("Required", "Please enter username and password")
                return

            conn = get_db_connection()   # Make sure this function exists and works
            if not conn:
                return

            c = conn.cursor(dictionary=True)
            
            try:
                c.execute("""
                    SELECT username, role, email 
                    FROM users 
                    WHERE username = %s AND password_hash = %s
                """, (username, hash_password(password)))   # ← Change to hashed password later

                user = c.fetchone()

                #if user is None:
                    #messagebox.showerror("Login Failed", "Invalid username or password")
                    #return

                # Clear current login window content
                for widget in self.root.winfo_children():
                    widget.destroy()

                if user['role'] == 'student':
                    open_student_dashboard_after_login(self.root, user)   # Note: you may need to create new root

                elif user['role'] == 'admin':
                    launch_admin_dashboard(self.root, user)

                elif user['role'] == 'supervisor':
                    launch_supervisor_dashboard(self.root, user)

                elif user['role'] == 'staff':
                    messagebox.showinfo("Access Restricted", 
                        "Sorry, you're not yet eligible to access the system.\nContact the admin to be promoted to supervisor.")
                    MainInterface(self.root)

                else:
                    messagebox.showerror("Error", "Unknown user role.")

            except Exception as e:
                messagebox.showerror("Database Error", f"An error occurred:\n{e}")
            finally:
                c.close()

        ttk.Button(frame, text="Login", command=handle_login).pack(pady=20, fill=X)

        ttk.Button(frame, text="Cancel", command=login_win.destroy).pack(pady=(0, 5))

        username_entry.focus_set() 

# ────────────────────────────────────────────────
# Example launch (after login)
# ────────────────────────────────────────────────
def launch_admin_dashboard(root, user_dict):
    root.destroy()
    win = Tk()
    AdminDashboard(win, user_dict)
    win.mainloop()

def launch_supervisor_dashboard(root, user_dict):
    root.destroy()
    win = Tk()
    SupervisorDashboard(win, user_dict)
    win.mainloop()

# ────────────────────────────────────────────────
# Example: how to launch after login
# ────────────────────────────────────────────────
def open_student_dashboard_after_login(root, user_dict):
    root.destroy()
    dashboard_root = Tk()
    StudentDashboard(dashboard_root, user_dict)
    dashboard_root.mainloop()

# ── Application entry point ───────────────────────────────────────────
if __name__ == "__main__":
    root = Tk()
    app = MainInterface(root)
    root.mainloop()
