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
            role TEXT DEFAULT 'user',
            can_add INTEGER DEFAULT 1,
            can_delete INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='Nelson'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role, can_add, can_delete, active) VALUES (?, ?, ?, ?, ?, ?)",
                       ("Nelson", "8463", "admin", 1, 1, 1))
    conn.commit()

# === 登入視窗 ===
def login(root):
    login_success = {"user": None, "role": None, "can_add": 0, "can_delete": 0}

    def attempt_login():
        username = entry_user.get().strip()
        password = entry_pass.get().strip()
        if not username or not password:
            messagebox.showerror("錯誤", "請輸入帳號與密碼")
            return
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, can_add, can_delete FROM users WHERE username=? AND password=? AND active=1", (username, password))
            result = cursor.fetchone()
            if result:
                login_success["user"] = username
                login_success["role"] = result[0]
                login_success["can_add"] = result[1]
                login_success["can_delete"] = result[2]
                login_window.destroy()
            else:
                messagebox.showerror("錯誤", "帳號或密碼錯誤或帳號已停用")

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
    return login_success

# === 刪除紀錄功能 ===
def delete_record(tree):
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("未選擇", "請選取要刪除的紀錄")
        return
    if messagebox.askyesno("確認", "確定要刪除這些紀錄嗎？"):
        ids = [tree.item(i)['values'][0] for i in selected]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.executemany("DELETE FROM issues WHERE id=?", [(i,) for i in ids])
        messagebox.showinfo("成功", "已刪除選取的紀錄")
        return True
    return False

# === 使用者管理 ===
def manage_users():
    win = tk.Toplevel(root)
    win.title("帳號管理")
    win.geometry("700x500")

    tk.Label(win, text="帳號:").grid(row=0, column=0)
    entry_new_user = tk.Entry(win)
    entry_new_user.grid(row=0, column=1)

    tk.Label(win, text="密碼:").grid(row=1, column=0)
    entry_new_pass = tk.Entry(win, show="*")
    entry_new_pass.grid(row=1, column=1)

    var_add = tk.IntVar(value=1)
    var_delete = tk.IntVar(value=0)
    var_active = tk.IntVar(value=1)
    tk.Checkbutton(win, text="允許新增", variable=var_add).grid(row=2, column=1, sticky="w")
    tk.Checkbutton(win, text="允許刪除", variable=var_delete).grid(row=3, column=1, sticky="w")
    tk.Checkbutton(win, text="啟用帳號", variable=var_active).grid(row=4, column=1, sticky="w")

    def add_user():
        u = entry_new_user.get().strip()
        p = entry_new_pass.get().strip()
        if not u or not p:
            messagebox.showwarning("錯誤", "請輸入帳號與密碼")
            return
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO users (username, password, role, can_add, can_delete, active)
                    VALUES (?, ?, 'user', ?, ?, ?)
                """, (u, p, var_add.get(), var_delete.get(), var_active.get()))
                messagebox.showinfo("成功", "使用者已新增")
                entry_new_user.delete(0, tk.END)
                entry_new_pass.delete(0, tk.END)
                refresh_user_list()
            except sqlite3.IntegrityError:
                messagebox.showerror("錯誤", "帳號已存在")

    tk.Button(win, text="新增使用者", command=add_user).grid(row=5, column=1, pady=10)

    frame_list = tk.LabelFrame(win, text="現有使用者")
    frame_list.grid(row=6, column=0, columnspan=3, pady=10, padx=10, sticky="nsew")
    frame_list.columnconfigure(0, weight=1)

    tree_users = ttk.Treeview(frame_list, columns=("帳號", "角色", "可新增", "可刪除", "啟用"), show="headings", height=10)
    for col in ("帳號", "角色", "可新增", "可刪除", "啟用"):
        tree_users.heading(col, text=col)
        tree_users.column(col, width=100 if col != "帳號" else 150)
    tree_users.pack(fill="both", expand=True)

    tk.Label(win, text="選取帳號後可修改 ↓").grid(row=7, column=0, columnspan=2)

    entry_edit_pass = tk.Entry(win, show="*")
    entry_edit_pass.grid(row=8, column=1)
    tk.Label(win, text="新密碼（選填）:").grid(row=8, column=0)

    edit_add = tk.IntVar()
    edit_delete = tk.IntVar()
    edit_active = tk.IntVar()
    tk.Checkbutton(win, text="允許新增", variable=edit_add).grid(row=9, column=1, sticky="w")
    tk.Checkbutton(win, text="允許刪除", variable=edit_delete).grid(row=10, column=1, sticky="w")
    tk.Checkbutton(win, text="啟用帳號", variable=edit_active).grid(row=11, column=1, sticky="w")

    def on_user_select(event):
        selected = tree_users.selection()
        if not selected:
            return
        item = tree_users.item(selected[0])["values"]
        edit_add.set(1 if item[2] else 0)
        edit_delete.set(1 if item[3] else 0)
        edit_active.set(1 if item[4] else 0)

    def update_permissions():
        selected = tree_users.selection()
        if not selected:
            messagebox.showwarning("未選擇", "請選擇帳號")
            return
        username = tree_users.item(selected[0])["values"][0]
        new_pass = entry_edit_pass.get().strip()
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            if new_pass:
                cursor.execute("""
                    UPDATE users SET password=?, can_add=?, can_delete=?, active=? WHERE username=?
                """, (new_pass, edit_add.get(), edit_delete.get(), edit_active.get(), username))
            else:
                cursor.execute("""
                    UPDATE users SET can_add=?, can_delete=?, active=? WHERE username=?
                """, (edit_add.get(), edit_delete.get(), edit_active.get(), username))
        messagebox.showinfo("成功", "使用者權限已更新")
        entry_edit_pass.delete(0, tk.END)
        refresh_user_list()

    tk.Button(win, text="更新權限/密碼", command=update_permissions).grid(row=12, column=1, pady=10)

    def refresh_user_list():
        for row in tree_users.get_children():
            tree_users.delete(row)
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role, can_add, can_delete, active FROM users")
            for user in cursor.fetchall():
                tree_users.insert('', tk.END, values=user)

    tree_users.bind("<<TreeviewSelect>>", on_user_select)
    refresh_user_list()

# === 主程式 ===
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    login_info = login(root)
    if not login_info["user"]:
        root.destroy()
        exit()

    current_user = login_info["user"]
    current_role = login_info["role"]
    can_add = login_info["can_add"]
    can_delete = login_info["can_delete"]

    root.deiconify()
    root.title("生產資訊平台")
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
                        state="normal" if can_add else "disabled")
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

    # === 刪除功能按鈕（需權限）===
    if can_delete:
        btn_del = tk.Button(root, text="刪除選取紀錄", command=lambda: delete_record(tree), bg="#ff9999")
        btn_del.pack(pady=5)

    if current_role == "admin":
        tk.Button(root, text="帳號管理", command=manage_users).pack(pady=5)

    root.mainloop()