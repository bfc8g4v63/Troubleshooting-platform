import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def build_user_management_tab(tab_frame, db_name, current_user):
    tk.Label(tab_frame, text="帳號管理", font=("Arial", 16)).pack(pady=10)

    form = tk.Frame(tab_frame)
    form.pack(pady=5)

    tk.Label(form, text="帳號:").grid(row=0, column=0)
    entry_user = tk.Entry(form)
    entry_user.grid(row=0, column=1)

    tk.Label(form, text="密碼:").grid(row=1, column=0)
    entry_pass = tk.Entry(form, show="*")
    entry_pass.grid(row=1, column=1)

    var_add = tk.IntVar(value=1)
    var_delete = tk.IntVar(value=0)
    var_active = tk.IntVar(value=1)

    tk.Checkbutton(form, text="可新增", variable=var_add).grid(row=2, column=1, sticky="w")
    tk.Checkbutton(form, text="可刪除", variable=var_delete).grid(row=3, column=1, sticky="w")
    tk.Checkbutton(form, text="啟用帳號", variable=var_active).grid(row=4, column=1, sticky="w")

    def add_user():
        u = entry_user.get().strip()
        p = entry_pass.get().strip()
        if not u or not p:
            messagebox.showwarning("錯誤", "請輸入帳號與密碼")
            return
        hashed_pw = hash_password(p)
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO users (username, password, role, can_add, can_delete, active)
                    VALUES (?, ?, 'user', ?, ?, ?)
                """, (u, hashed_pw, var_add.get(), var_delete.get(), var_active.get()))
                messagebox.showinfo("成功", "使用者已新增")
                entry_user.delete(0, tk.END)
                entry_pass.delete(0, tk.END)
                refresh_users()
            except sqlite3.IntegrityError:
                messagebox.showerror("錯誤", "帳號已存在")

    tk.Button(form, text="新增使用者", command=add_user).grid(row=5, column=1, pady=5)

    tree = ttk.Treeview(tab_frame, columns=("帳號", "角色", "可新增", "可刪除", "啟用"), show="headings", height=10)
    for col in tree["columns"]:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    tree.pack(padx=10, pady=10, fill="both", expand=True)

    tk.Label(tab_frame, text="選取使用者後可修改權限 ↓").pack()

    edit_frame = tk.Frame(tab_frame)
    edit_frame.pack(pady=5)

    tk.Label(edit_frame, text="新密碼（可留空）:").grid(row=0, column=0)
    entry_edit_pass = tk.Entry(edit_frame, show="*")
    entry_edit_pass.grid(row=0, column=1)

    role_var = tk.StringVar()
    combo_role = ttk.Combobox(edit_frame, textvariable=role_var, values=["admin", "user"], state="readonly")
    combo_role.grid(row=1, column=1)
    tk.Label(edit_frame, text="角色:").grid(row=1, column=0)

    edit_add = tk.IntVar()
    edit_delete = tk.IntVar()
    edit_active = tk.IntVar()
    tk.Checkbutton(edit_frame, text="可新增", variable=edit_add).grid(row=2, column=1, sticky="w")
    tk.Checkbutton(edit_frame, text="可刪除", variable=edit_delete).grid(row=3, column=1, sticky="w")
    tk.Checkbutton(edit_frame, text="啟用", variable=edit_active).grid(row=4, column=1, sticky="w")

    def on_select_user(event):
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])["values"]
        role_var.set(item[1])
        edit_add.set(item[2])
        edit_delete.set(item[3])
        edit_active.set(item[4])

    tree.bind("<<TreeviewSelect>>", on_select_user)

    def update_user():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("未選擇", "請選擇帳號")
            return
        username = tree.item(selected[0])["values"][0]
        if username == current_user:
            messagebox.showerror("錯誤", "無法修改當前登入帳號")
            return
        new_pass = entry_edit_pass.get().strip()
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            if new_pass:
                hashed_pw = hash_password(new_pass)
                cursor.execute("""
                    UPDATE users SET password=?, role=?, can_add=?, can_delete=?, active=?
                    WHERE username=?
                """, (hashed_pw, role_var.get(), edit_add.get(), edit_delete.get(), edit_active.get(), username))
            else:
                cursor.execute("""
                    UPDATE users SET role=?, can_add=?, can_delete=?, active=?
                    WHERE username=?
                """, (role_var.get(), edit_add.get(), edit_delete.get(), edit_active.get(), username))
        messagebox.showinfo("成功", "已更新")
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
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username=?", (username,))
        messagebox.showinfo("成功", "使用者已刪除")
        refresh_users()

    tk.Button(tab_frame, text="刪除使用者", command=delete_user, bg="#ff9999").pack(pady=5)

    def refresh_users():
        for i in tree.get_children():
            tree.delete(i)
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, role, can_add, can_delete, active FROM users")
            for user in cursor.fetchall():
                tree.insert('', tk.END, values=user)

    refresh_users()