import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib

def build_user_management_tab(tab, db_name, current_user):
    frame = tk.Frame(tab)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    tk.Label(frame, text="帳號管理（僅限管理者）").pack(anchor="w")

    # 篩選與排序區塊
    control_frame = tk.Frame(frame)
    control_frame.pack(anchor="w", pady=(0, 5))

    tk.Label(control_frame, text="顯示帳號：").pack(side="left")
    filter_var = tk.StringVar(value="全部")
    filter_combo = ttk.Combobox(control_frame, textvariable=filter_var, values=["全部", "僅啟用", "僅停用"], width=10, state="readonly")
    filter_combo.pack(side="left", padx=(0, 10))

    sort_asc = tk.BooleanVar(value=True)
    def toggle_sort():
        sort_asc.set(not sort_asc.get())
        refresh_users()

    tk.Button(control_frame, text="↕排序帳號", command=toggle_sort).pack(side="left")

    columns = ("帳號", "角色", "可新增", "可刪除", "啟用")
    tree = ttk.Treeview(frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    tree.pack(fill="both", expand=True, pady=5)

    def refresh_users():
        for row in tree.get_children():
            tree.delete(row)
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT username, role, can_add, can_delete, active FROM users"
            condition = filter_var.get()
            if condition == "僅啟用":
                sql += " WHERE active=1"
            elif condition == "僅停用":
                sql += " WHERE active=0"
            sql += f" ORDER BY username {'ASC' if sort_asc.get() else 'DESC'}"
            cursor.execute(sql)
            for row in cursor.fetchall():
                tags = ("disabled",) if row[4] == 0 else ()
                tree.insert("", "end", values=row, tags=tags)

        tree.tag_configure("disabled", foreground="gray")

    filter_combo.bind("<<ComboboxSelected>>", lambda e: refresh_users())

    # === 新增帳號表單 ===
    form = tk.LabelFrame(frame, text="新增使用者")
    form.pack(fill="x", pady=10)

    tk.Label(form, text="帳號：").grid(row=0, column=0, sticky="e")
    entry_user = tk.Entry(form, width=30)
    entry_user.grid(row=0, column=1)

    tk.Label(form, text="密碼：").grid(row=1, column=0, sticky="e")
    entry_pass = tk.Entry(form, width=30, show="*")
    entry_pass.grid(row=1, column=1)

    tk.Label(form, text="角色：").grid(row=2, column=0, sticky="e")
    role_var = tk.StringVar(value="user")
    role_menu = ttk.Combobox(form, textvariable=role_var, values=["admin", "user"], state="readonly", width=28)
    role_menu.grid(row=2, column=1)

    var_add = tk.IntVar(value=1)
    var_delete = tk.IntVar(value=0)
    var_active = tk.IntVar(value=1)
    tk.Checkbutton(form, text="可新增", variable=var_add).grid(row=3, column=0)
    tk.Checkbutton(form, text="可刪除", variable=var_delete).grid(row=3, column=1, sticky="w")
    tk.Checkbutton(form, text="啟用", variable=var_active).grid(row=4, column=0)

    def hash_password(password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def add_user():
        new_user = entry_user.get().strip()
        new_pw = entry_pass.get().strip()
        role = role_var.get()
        can_add = var_add.get()
        can_delete = var_delete.get()
        active = var_active.get()

        if not new_user or not new_pw:
            messagebox.showwarning("警告", "請填寫帳號與密碼")
            return

        hashed_pw = hash_password(new_pw)

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username=?", (new_user,))
            if cursor.fetchone():
                messagebox.showerror("錯誤", "該使用者已存在")
                return

            cursor.execute("""
                INSERT INTO users (username, password, role, can_add, can_delete, active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_user, hashed_pw, role, can_add, can_delete, active))
            conn.commit()

        messagebox.showinfo("成功", "使用者已新增")
        entry_user.delete(0, tk.END)
        entry_pass.delete(0, tk.END)
        refresh_users()

    tk.Button(form, text="新增使用者", command=add_user, bg="lightblue").grid(row=5, column=1, pady=10)

    # === 權限修改區塊 ===
    edit_frame = tk.LabelFrame(frame, text="修改權限 / 狀態 / 帳號名稱")
    edit_frame.pack(fill="x", pady=10)

    tk.Label(edit_frame, text="新帳號（可留空）:").grid(row=0, column=0)
    entry_edit_user = tk.Entry(edit_frame)
    entry_edit_user.grid(row=0, column=1)

    tk.Label(edit_frame, text="新密碼（可留空）:").grid(row=1, column=0)
    entry_edit_pass = tk.Entry(edit_frame, show="*")
    entry_edit_pass.grid(row=1, column=1)

    tk.Label(edit_frame, text="角色:").grid(row=2, column=0)
    role_edit = tk.StringVar()
    combo_role = ttk.Combobox(edit_frame, textvariable=role_edit, values=["admin", "user"], state="readonly")
    combo_role.grid(row=2, column=1)

    edit_add = tk.IntVar()
    edit_delete = tk.IntVar()
    edit_active = tk.IntVar()
    tk.Checkbutton(edit_frame, text="可新增", variable=edit_add).grid(row=3, column=0)
    tk.Checkbutton(edit_frame, text="可刪除", variable=edit_delete).grid(row=3, column=1, sticky="w")
    tk.Checkbutton(edit_frame, text="啟用", variable=edit_active).grid(row=4, column=0)

    def on_select_user(event):
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])["values"]
        entry_edit_user.delete(0, tk.END)
        entry_edit_user.insert(0, item[0])
        role_edit.set(item[1])
        edit_add.set(item[2])
        edit_delete.set(item[3])
        edit_active.set(item[4])

    tree.bind("<<TreeviewSelect>>", on_select_user)

    def update_user():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("未選擇", "請選擇帳號")
            return
        original_username = tree.item(selected[0])["values"][0]
        if original_username == current_user:
            messagebox.showerror("錯誤", "無法修改當前登入帳號")
            return

        new_username = entry_edit_user.get().strip()
        new_pass = entry_edit_pass.get().strip()

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            if new_username and new_username != original_username:
                cursor.execute("SELECT username FROM users WHERE username=?", (new_username,))
                if cursor.fetchone():
                    messagebox.showerror("錯誤", "新帳號名稱已存在")
                    return
                cursor.execute("UPDATE users SET username=? WHERE username=?", (new_username, original_username))
                original_username = new_username

            if new_pass:
                hashed_pw = hash_password(new_pass)
                cursor.execute("""
                    UPDATE users SET password=?, role=?, can_add=?, can_delete=?, active=?
                    WHERE username=?
                """, (hashed_pw, role_edit.get(), edit_add.get(), edit_delete.get(), edit_active.get(), original_username))
            else:
                cursor.execute("""
                    UPDATE users SET role=?, can_add=?, can_delete=?, active=?
                    WHERE username=?
                """, (role_edit.get(), edit_add.get(), edit_delete.get(), edit_active.get(), original_username))
            conn.commit()

        messagebox.showinfo("成功", "已更新")
        entry_edit_user.delete(0, tk.END)
        entry_edit_pass.delete(0, tk.END)
        refresh_users()

    tk.Button(edit_frame, text="更新權限", command=update_user).grid(row=5, column=1, pady=5)

    def delete_user():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("未選擇", "請選擇帳號")
            return
        username = tree.item(selected[0])["values"][0]
        if username == current_user:
            messagebox.showerror("錯誤", "無法刪除自己")
            return
        if messagebox.askyesno("確認", f"是否確定要刪除帳號「{username}」？"):
            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username=?", (username,))
                conn.commit()
            messagebox.showinfo("成功", "使用者已刪除")
            refresh_users()

    tk.Button(frame, text="刪除選取帳號", command=delete_user, bg="#ff9999").pack(pady=5, ipady=5)

    refresh_users()
    return tree, refresh_users