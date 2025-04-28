import os
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

DB_NAME = "troubleshooting.db"

# === 資料庫初始化 ===
with sqlite3.connect(DB_NAME) as conn:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL,
            product_name TEXT,
            status TEXT,
            change TEXT,
            file_path TEXT,
            created_by TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='Nelson'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       ("Nelson", "8463", "admin"))
    conn.commit()

# === 登入視窗 ===
def login(root):
    login_success = {"user": None, "role": None}

    def attempt_login():
        username = entry_user.get().strip()
        password = entry_pass.get().strip()
        if not username or not password:
            messagebox.showerror("錯誤", "請輸入帳號與密碼")
            return
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
            result = cursor.fetchone()
            if result:
                login_success["user"] = username
                login_success["role"] = result[0]
                login_window.destroy()
            else:
                messagebox.showerror("錯誤", "帳號或密碼錯誤")

    login_window = tk.Toplevel(root)
    login_window.title("登入系統")
    login_window.geometry("300x180")
    login_window.resizable(False, False)
    login_window.grab_set()

    tk.Label(login_window, text="請輸入使用者名稱：").pack(pady=(15, 5))
    entry_user = tk.Entry(login_window)
    entry_user.pack()

    tk.Label(login_window, text="請輸入密碼：").pack(pady=(10, 5))
    entry_pass = tk.Entry(login_window, show="*")
    entry_pass.pack()

    tk.Button(login_window, text="登入", command=attempt_login).pack(pady=15)
    login_window.protocol("WM_DELETE_WINDOW", root.destroy)

    root.wait_window(login_window)
    return login_success["user"], login_success["role"]

# === 主程式 ===
root = tk.Tk()
root.withdraw()

current_user, current_role = login(root)

if not current_user:
    root.destroy()
    exit()

root.deiconify()
root.title("異常排除資訊平台")
root.geometry("1000x750")
tk.Label(root, text=f"登入者：{current_user} ({current_role})", anchor="e").pack(fill="x", padx=10, pady=5)

# === 表單區塊 ===
frame_form = tk.Frame(root)
frame_form.pack(pady=10)

tk.Label(frame_form, text="產品編號:").grid(row=0, column=0, sticky="e")
entry_product = tk.Entry(frame_form, width=30)
entry_product.grid(row=0, column=1)

tk.Label(frame_form, text="品名:").grid(row=1, column=0, sticky="e")
entry_name = tk.Entry(frame_form, width=30)
entry_name.grid(row=1, column=1)

tk.Label(frame_form, text="狀況描述:").grid(row=2, column=0, sticky="e")
entry_status = tk.Entry(frame_form, width=60)
entry_status.grid(row=2, column=1)

tk.Label(frame_form, text="變更內容:").grid(row=3, column=0, sticky="e")
entry_change = tk.Entry(frame_form, width=60)
entry_change.grid(row=3, column=1)

tk.Label(frame_form, text="相關檔案:").grid(row=4, column=0, sticky="e")
entry_file = tk.Entry(frame_form, width=50)
entry_file.grid(row=4, column=1)

def browse_file():
    path = filedialog.askopenfilename()
    if path:
        entry_file.delete(0, tk.END)
        entry_file.insert(0, path)

btn_file = tk.Button(frame_form, text="選擇檔案", command=browse_file)
btn_file.grid(row=4, column=2)

# === 儲存資料 ===
def save_data():
    code = entry_product.get().strip()
    name = entry_name.get().strip()
    status = entry_status.get().strip()
    change = entry_change.get().strip()
    filepath = entry_file.get().strip()
    if len(code) not in (8, 10, 12) or not code.isdigit():
        messagebox.showerror("錯誤", "產品編號必須為 8 / 10 / 12 碼數字")
        return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO issues (product_code, product_name, status, change, file_path, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (code, name, status, change, filepath, current_user, datetime.now().isoformat()))
    messagebox.showinfo("成功", "資料已儲存")
    for e in [entry_product, entry_name, entry_status, entry_change, entry_file]:
        e.delete(0, tk.END)
    query_data()

btn_add = tk.Button(frame_form, text="新增紀錄", command=save_data, bg="lightblue",
                    state="normal" if current_role == "admin" else "disabled")
btn_add.grid(row=5, column=1, pady=10)

# === 查詢區塊 ===
frame_query = tk.Frame(root)
frame_query.pack()
tk.Label(frame_query, text="查詢關鍵字 (產品編號/描述/品名):").pack(side="left")
entry_query = tk.Entry(frame_query)
entry_query.pack(side="left")

sort_desc = tk.BooleanVar(value=True)

def toggle_sort():
    sort_desc.set(not sort_desc.get())
    query_data()

btn_sort = tk.Button(frame_query, text="↕排序", command=toggle_sort)
btn_sort.pack(side="left", padx=10)

def query_data():
    for row in tree.get_children():
        tree.delete(row)
    keyword = entry_query.get().strip()
    query = """
        SELECT id, product_code, product_name, status, change, file_path, created_by, created_at
        FROM issues
        WHERE product_code LIKE ? OR status LIKE ? OR change LIKE ? OR product_name LIKE ?
        ORDER BY created_at {}
    """.format("DESC" if sort_desc.get() else "ASC")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple('%' + keyword + '%' for _ in range(4)))
        for row in cursor.fetchall():
            tree.insert('', tk.END, values=row)

btn_query = tk.Button(frame_query, text="查詢", command=query_data)
btn_query.pack(side="left")

# === 表格 ===
columns = ("工單", "產品編號", "品名", "狀況", "變更", "檔案", "使用者", "建立時間")
tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=120 if col != "變更" else 180)
tree.pack(fill="both", expand=True)

# === 刪除紀錄 ===
def delete_record():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("未選擇", "請選取要刪除的紀錄")
        return
    if messagebox.askyesno("確認", "確定要刪除這些紀錄嗎？"):
        ids = [tree.item(i)['values'][0] for i in selected]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.executemany("DELETE FROM issues WHERE id=?", [(i,) for i in ids])
        query_data()

if current_role == "admin":
    btn_del = tk.Button(root, text="刪除選取紀錄", command=delete_record, bg="#ff9999")
    btn_del.pack(pady=5)

# === 啟動介面 ===
query_data()
root.mainloop()
