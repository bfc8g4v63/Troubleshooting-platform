import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import sqlite3
import os
import shutil
import hashlib
import subprocess
import sys
import tempfile

from account_management_tab import build_user_management_tab

# 設定原始資料庫與本機暫存資料庫位置
ORIGINAL_DB = r"C:\Users\user\Desktop\Nelson\Dev\GitHub\Troubleshooting platform\troubleshooting.db"
LOCAL_DB = os.path.join(tempfile.gettempdir(), "troubleshooting.db")
shutil.copy(ORIGINAL_DB, LOCAL_DB)

DB_NAME = LOCAL_DB

DIP_SOP_PATH = r"\\192.120.100.177\工程部\生產管理\上齊SOP大禮包\DIP_SOP"
ASSEMBLY_SOP_PATH = r"\\192.120.100.177\工程部\生產管理\上齊SOP大禮包\組裝SOP"
TEST_SOP_PATH = r"\\192.120.100.177\工程部\生產管理\上齊SOP大禮包\測試SOP"
PACKAGING_SOP_PATH = r"\\192.120.100.177\工程部\生產管理\上齊SOP大禮包\包裝SOP"
OQC_PATH = r"\\192.120.100.177\工程部\生產管理\上齊SOP大禮包\檢查表OQC"

LOG_TABLE = "activity_logs"

def init_db():
    if not os.access(DB_NAME, os.R_OK | os.W_OK):
        raise IOError(f"無法讀寫資料庫檔案：{DB_NAME}")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("PRAGMA journal_mode=WAL")

def sync_back_to_server():
    try:
        shutil.copy(DB_NAME, ORIGINAL_DB)
        print("✅ 已同步本機資料庫回網路磁碟")
    except Exception as e:
        print(f"⚠️ 資料回寫失敗: {e}")

def logout_and_exit(root):
    sync_back_to_server()
    root.destroy()

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def log_activity(user, action, filename):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {LOG_TABLE} (username, action, filename, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user, action, filename, datetime.now().isoformat()))
        conn.commit()

def open_file(filepath):
    try:
        if sys.platform == "win32":
            os.startfile(filepath)
        elif sys.platform == "darwin":
            subprocess.call(["open", filepath])
        else:
            subprocess.call(["xdg-open", filepath])
    except Exception as e:
        messagebox.showerror("錯誤", f"無法開啟檔案: {e}")

def build_log_view_tab(tab, db_name):
    frame = tk.Frame(tab)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    tk.Label(frame, text="操作紀錄查詢（僅限管理者）").pack(anchor="w")

    columns = ("使用者", "動作", "檔案名稱", "時間")
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150)
    tree.pack(fill="both", expand=True)

    def refresh_logs():
        for row in tree.get_children():
            tree.delete(row)
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, username, action, filename, timestamp FROM {LOG_TABLE} ORDER BY timestamp DESC")
            for row in cursor.fetchall():
                tree.insert("", "end", iid=row[0], values=row[1:])

    refresh_button = tk.Button(frame, text="重新整理", command=refresh_logs)
    refresh_button.pack(anchor="e", pady=5)

    def delete_selected_log():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("提醒", "請先選取一筆操作紀錄")
            return
        if messagebox.askyesno("確認", "確定要刪除所選操作紀錄？"):
            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                for iid in selected:
                    cursor.execute(f"DELETE FROM {LOG_TABLE} WHERE id=?", (iid,))
                conn.commit()
            refresh_logs()
    def delete_all_logs():
        if messagebox.askyesno("確認", "⚠️ 確定要刪除所有操作紀錄？此操作無法復原。"):
            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {LOG_TABLE}")
                conn.commit()
            refresh_logs()

    button_frame = tk.Frame(frame)
    button_frame.pack(anchor="e", pady=5)

    tk.Button(button_frame, text="刪除所選", command=delete_selected_log).pack(side="left", padx=5)
    tk.Button(button_frame, text="刪除全部", command=delete_all_logs).pack(side="left", padx=5)
    refresh_logs()
                
def initialize_database():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        # 建立 issues 表（僅新 DB 建立用）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                product_code TEXT PRIMARY KEY,
                product_name TEXT,
                dip_sop TEXT,
                assembly_sop TEXT,
                test_sop TEXT,
                packaging_sop TEXT,
                oqc_checklist TEXT,
                created_by TEXT,
                created_at TEXT
            )
        """)

        # 🔧 自動補欄位 dip_sop（防止舊 DB 出錯）
        cursor.execute("PRAGMA table_info(issues)")
        columns = [row[1] for row in cursor.fetchall()]
        if "dip_sop" not in columns:
            cursor.execute("ALTER TABLE issues ADD COLUMN dip_sop TEXT")
            print("✅ 已自動新增 dip_sop 欄位至 issues 表")

        # 建立使用者表（如不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                role TEXT DEFAULT 'user',
                can_add INTEGER DEFAULT 1,
                can_delete INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1
            )
        """)

        # 建立操作紀錄表（如不存在）
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {LOG_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                action TEXT,
                filename TEXT,
                timestamp TEXT
            )
        """)

        # 新增預設管理者帳號
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='Nelson'")
        if cursor.fetchone()[0] == 0:
            hashed_pw = hash_password("8463")
            cursor.execute("""
                INSERT INTO users (username, password, role, can_add, can_delete, active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("Nelson", hashed_pw, "admin", 1, 1, 1))

        conn.commit()

def save_file(file_path, target_folder, username):
    if not os.path.exists(file_path):
        return ""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{os.path.basename(file_path)}"
    target_path = os.path.join(target_folder, filename)
    try:
        shutil.copy(file_path, target_path)
        log_activity(username, "upload", filename)
        return filename
    except Exception as e:
        messagebox.showerror("錯誤", f"檔案儲存失敗: {e}")
        return ""

def update_sop_field(cursor, product_code, field_name, new_file_path):
    cursor.execute(f"UPDATE issues SET {field_name}=?, created_at=? WHERE product_code=?",
                   (new_file_path, datetime.now().isoformat(), product_code))


def handle_sop_update(product_code, sop_path, field_name, entry_widget, current_user):
    path = entry_widget.get().strip()
    if not path:
        return None
    filename = save_file(path, sop_path, current_user)
    if not filename:
        return None
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        update_sop_field(cursor, product_code, field_name, os.path.join(sop_path, filename))
        conn.commit()
    return filename


def create_sop_update_button(frame, row, label, sop_path, field_name, product_code_entry, entry_widget, current_user):
    def update_action():
        product_code = product_code_entry.get().strip()
        if not product_code:
            messagebox.showwarning("警告", "請先輸入產品編號")
            return
        updated_filename = handle_sop_update(product_code, sop_path, field_name, entry_widget, current_user)
        if updated_filename:
            messagebox.showinfo("成功", f"已更新 {label} 檔案")
    btn = tk.Button(frame, text="更新", command=update_action)
    btn.grid(row=row, column=3, padx=5)
    return btn


def create_upload_field_with_update(row, label, folder, field_name, form, product_code_entry, current_user):
    tk.Label(form, text=label).grid(row=row, column=0, sticky="e")
    entry = tk.Entry(form, width=50)
    entry.grid(row=row, column=1)
    def browse():
        path = filedialog.askopenfilename()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)
    tk.Button(form, text="選擇檔案", command=browse).grid(row=row, column=2)
    create_sop_update_button(form, row, label, folder, field_name, product_code_entry, entry, current_user)
    return entry


def create_main_interface(root, db_name, login_info):
    current_user = login_info['user']
    current_role = login_info['role']
    can_add = login_info['can_add']
    can_delete = login_info['can_delete']



    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    tabs = {
        "生產資訊": tk.Frame(notebook),
        "治具管理": tk.Frame(notebook),
        "測試BOM": tk.Frame(notebook),
        "SOP套用": tk.Frame(notebook),
        "帳號管理": tk.Frame(notebook) if current_role == "admin" else None,
        "操作紀錄": tk.Frame(notebook) if current_role == "admin" else None
    }

    for name, frame in tabs.items():
        if frame:
            notebook.add(frame, text=name)

    if current_role == "admin":
        build_log_view_tab(tabs["操作紀錄"], db_name)
        build_user_management_tab(tabs["帳號管理"], db_name, current_user)

    frame = tabs["生產資訊"]
    form = tk.LabelFrame(frame, text="新增紀錄")
    form.pack(fill="x", padx=10, pady=5)

    tk.Label(form, text="產品編號:").grid(row=0, column=0, sticky="e")
    entry_code = tk.Entry(form, width=50)
    entry_code.grid(row=0, column=1)

    tk.Label(form, text="品名:").grid(row=1, column=0, sticky="e")
    entry_name = tk.Entry(form, width=50)
    entry_name.grid(row=1, column=1)

    entry_dip = create_upload_field_with_update(2, "DIP SOP", DIP_SOP_PATH, "dip_sop", form, entry_code, current_user)
    entry_assembly = create_upload_field_with_update(3, "組裝SOP", ASSEMBLY_SOP_PATH, "assembly_sop", form, entry_code, current_user)
    entry_test = create_upload_field_with_update(4, "測試SOP", TEST_SOP_PATH, "test_sop", form, entry_code, current_user)
    entry_packaging = create_upload_field_with_update(5, "包裝SOP", PACKAGING_SOP_PATH, "packaging_sop", form, entry_code, current_user)
    entry_oqc = create_upload_field_with_update(6, "檢查表OQC", OQC_PATH, "oqc_checklist", form, entry_code, current_user)

    def save_data():
        code = entry_code.get().strip()
        name = entry_name.get().strip()

        if len(code) not in (8, 10, 12) or not code.isdigit():
            messagebox.showerror("錯誤", "產品編號必須為 8/10/12 碼數字")
            return

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT product_code FROM issues WHERE product_code=?", (code,))
            if cursor.fetchone():
                messagebox.showerror("錯誤", "產品編號已存在，請重新確認過。")
                return

            d_path = save_file(entry_dip.get().strip(), DIP_SOP_PATH, current_user)
            a_path = save_file(entry_assembly.get().strip(), ASSEMBLY_SOP_PATH, current_user)
            t_path = save_file(entry_test.get().strip(), TEST_SOP_PATH, current_user)
            p_path = save_file(entry_packaging.get().strip(), PACKAGING_SOP_PATH, current_user)
            o_path = save_file(entry_oqc.get().strip(), OQC_PATH, current_user)

            cursor.execute("""
                INSERT INTO issues (product_code, product_name, dip_sop, assembly_sop, test_sop, packaging_sop, oqc_checklist, created_by, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name, os.path.join(DIP_SOP_PATH, d_path), os.path.join(ASSEMBLY_SOP_PATH, a_path),
                os.path.join(TEST_SOP_PATH, t_path), os.path.join(PACKAGING_SOP_PATH, p_path),
                os.path.join(OQC_PATH, o_path), current_user, datetime.now().isoformat()))
            conn.commit()

        messagebox.showinfo("成功", "已新增紀錄")
        for e in [entry_code, entry_name, entry_dip, entry_assembly, entry_test, entry_packaging, entry_oqc]:
            e.delete(0, tk.END)
        query_data()

    tk.Button(form, text="新增紀錄", command=save_data, bg="lightblue", state="normal" if can_add else "disabled").grid(row=7, column=1, pady=10)

    query_frame = tk.Frame(frame)
    query_frame.pack(fill="x", padx=10, pady=5)
    tk.Label(query_frame, text="查詢關鍵字: ").pack(side="left")
    entry_query = tk.Entry(query_frame)
    entry_query.pack(side="left")
    sort_desc = tk.BooleanVar(value=True)

    def toggle_sort():
        sort_desc.set(not sort_desc.get())
        query_data()

    tk.Button(query_frame, text="↕排序", command=toggle_sort).pack(side="left", padx=5)
    tk.Button(query_frame, text="查詢", command=lambda: query_data()).pack(side="left")

    columns = ("產品編號", "品名", "DIP SOP", "組裝SOP", "測試SOP", "包裝SOP", "檢查表OQC", "使用者", "建立時間")
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120)
    tree.pack(fill="both", expand=True, padx=10, pady=5)

    if current_role == "admin":
        def delete_selected():
            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("提醒", "請先選取要刪除的資料")
                return
            if messagebox.askyesno("確認", "確定要刪除選取的資料？此操作無法復原。"):
                deleted_items = [] 
                with sqlite3.connect(db_name) as conn:
                    cursor = conn.cursor()
                    for item in selected_items:
                        product_code = tree.item(item)['values'][0]
                        cursor.execute("DELETE FROM issues WHERE product_code=?", (product_code,))
                        deleted_items.append(product_code)
                    conn.commit()
                for code in deleted_items:
                    log_activity(current_user, "delete", code)

                query_data()

        delete_frame = tk.Frame(frame)
        delete_frame.pack(fill="x", padx=10, pady=(0, 5), anchor="e")

        tk.Button(delete_frame, text="刪除選取資料", command=delete_selected,
                bg="lightcoral", fg="white").pack(side="right")

    def query_data():
        keyword = entry_query.get().strip()
        for row in tree.get_children():
            tree.delete(row)
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT product_code, product_name, dip_sop, assembly_sop, test_sop, packaging_sop, oqc_checklist, created_by, created_at
                FROM issues
                WHERE product_code LIKE ? OR product_name LIKE ?
                ORDER BY created_at {'DESC' if sort_desc.get() else 'ASC'}
            """, ('%' + keyword + '%', '%' + keyword + '%'))
            for row in cursor.fetchall():
                row_display = list(row)
                for i in range(2, 6):
                    row_display[i] = os.path.basename(row_display[i]) if row_display[i] else ""
                tree.insert('', tk.END, values=row_display)

    def on_double_click(event):
        item = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not item or not col:
            return
        col_index = int(col[1:]) - 1
        if col_index in range(2, 7):  # 支援 DIP SOP + 4種
            filename = tree.item(item)['values'][col_index]
            base_paths = [DIP_SOP_PATH, ASSEMBLY_SOP_PATH, TEST_SOP_PATH, PACKAGING_SOP_PATH, OQC_PATH]
            full_path = os.path.join(base_paths[col_index - 2], filename)
            if os.path.exists(full_path):
                open_file(full_path)

    def on_copy(event):
        focus = tree.focus()
        if not focus:
            return
        col = tree.identify_column(event.x)
        col_index = int(col[1:]) - 1
        value = tree.item(focus)['values'][col_index]
        root.clipboard_clear()
        root.clipboard_append(str(value))
        root.update()

    tree.bind("<Double-1>", on_double_click)
    tree.bind("<Control-c>", on_copy)

def login():
    result = {"user": None, "role": None, "can_add": 0, "can_delete": 0}

    def try_login():
        u = entry_user.get().strip()
        p = entry_pass.get().strip()
        if not u or not p:
            messagebox.showerror("錯誤", "請輸入帳號與密碼")
            return

        hashed_pw = hash_password(p)

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            c = conn.cursor()
            c.execute("SELECT role, can_add, can_delete FROM users WHERE username=? AND password=? AND active=1", (u, hashed_pw))
            r = c.fetchone()
            if r:
                result["user"] = u
                result["role"] = r[0]
                result["can_add"] = r[1]
                result["can_delete"] = r[2]
                login_window.destroy()
            else:
                messagebox.showerror("錯誤", "帳號或密碼錯誤或帳號已停用")

    login_window = tk.Tk()
    login_window.title("登入系統")
    login_window.geometry("300x180")
    try:
        login_window.iconbitmap("Ted64.ico")
    except:
        pass
    tk.Label(login_window, text="使用者名稱：").pack(pady=(15, 5))
    entry_user = tk.Entry(login_window)
    entry_user.pack()
    tk.Label(login_window, text="密碼：").pack(pady=(10, 5))
    entry_pass = tk.Entry(login_window, show="*")
    entry_pass.pack()
    tk.Button(login_window, text="登入", command=try_login).pack(pady=15)

    def on_close():
        login_window.destroy()

    login_window.protocol("WM_DELETE_WINDOW", on_close)
    login_window.mainloop()

    return result

if __name__ == "__main__":
    init_db()
    initialize_database()
    login_info = login()

    if login_info and login_info.get("user"):
        root = tk.Tk()
        root.title("生產資訊平台")
        root.geometry("1000x750")
        try:
            root.iconbitmap("Ted64.ico")
        except:
            pass
        import tkinter.font as tkFont
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=10, family="Microsoft Calibri")

        # 建立頂部工具列（含登出按鈕）
        top_bar = tk.Frame(root)
        top_bar.pack(fill="x", side="top")
        logout_btn = tk.Button(top_bar, text="登出並關閉", command=lambda: logout_and_exit(root), bg="orange")
        logout_btn.pack(side="right", padx=10, pady=5)

        # 主內容區域
        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True)
        create_main_interface(main_frame, DB_NAME, login_info)

        def on_close():
            logout_and_exit(root)
        root.protocol("WM_DELETE_WINDOW", on_close)

        root.mainloop()
    else:
        print("⚠️ 使用者未登入或登入失敗，系統結束。")