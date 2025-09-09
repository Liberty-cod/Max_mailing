import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import csv
import requests
import threading
import os


API_BASE = "https://botapi.max.ru"


def upload_file(file_path, token):
    """Загрузка файла в Max API и получение attachment_id"""
    url = f"{API_BASE}/upload?access_token={token}"
    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(url, files=files)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("attachment_id")
    else:
        print("Ошибка загрузки:", resp.text)
        return None


def send_max_message(user_id, text, token, attachments=None):
    """Отправка сообщения с текстом и (опционально) вложениями"""
    url = f"{API_BASE}/messages?access_token={token}"
    payload = {
        "user_id": int(user_id),
        "text": text
    }
    if attachments:
        payload["attachments"] = attachments

    resp = requests.post(url, json=payload)
    return resp.status_code == 200


class MessengerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MAX Рассылка")

        self.attachments = []

        # Токен
        tk.Label(root, text="Access Token:").pack(anchor="w")
        self.token_entry = tk.Entry(root, width=60, show="*")
        self.token_entry.pack(padx=5, pady=5)

        # IDs
        tk.Label(root, text="Список User IDs (через запятую):").pack(anchor="w")
        self.ids_entry = tk.Text(root, height=6, width=50)
        self.ids_entry.pack(padx=5, pady=5)

        self.load_btn = tk.Button(root, text="Загрузить IDs из файла", command=self.load_from_file)
        self.load_btn.pack(pady=5)

        # Сообщение
        tk.Label(root, text="Текст сообщения:").pack(anchor="w")
        self.msg_entry = tk.Text(root, height=6, width=50)
        self.msg_entry.pack(padx=5, pady=5)

        # Вложения
        self.attach_btn = tk.Button(root, text="Прикрепить файлы", command=self.attach_files)
        self.attach_btn.pack(pady=5)
        self.attach_label = tk.Label(root, text="Файлы не выбраны", fg="gray", justify="left")
        self.attach_label.pack()

        # Прогресс-бар
        tk.Label(root, text="Прогресс рассылки:").pack(anchor="w", pady=(10, 0))
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=5)
        self.progress_label = tk.Label(root, text="Ожидание...")
        self.progress_label.pack()

        # Отправка
        self.send_btn = tk.Button(root, text="Отправить", command=self.send_bulk_thread)
        self.send_btn.pack(pady=10)

    def get_token(self):
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showerror("Ошибка", "Введите Access Token!")
            return None
        return token

    def load_from_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл с User IDs",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        ids = []
        try:
            if path.endswith(".txt"):
                with open(path, "r", encoding="utf-8") as f:
                    ids = [line.strip() for line in f if line.strip()]
            elif path.endswith(".csv"):
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    ids = [row[0].strip() for row in reader if row and row[0].strip()]
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")
            return

        if ids:
            self.ids_entry.delete("1.0", tk.END)
            self.ids_entry.insert("1.0", ", ".join(ids))
            messagebox.showinfo("Готово", f"Загружено {len(ids)} ID")

    def attach_files(self):
        token = self.get_token()
        if not token:
            return

        paths = filedialog.askopenfilenames(title="Выберите файлы для отправки")
        if not paths:
            return

        uploaded = []
        for path in paths:
            attach_id = upload_file(path, token)
            if attach_id:
                self.attachments.append(attach_id)
                uploaded.append(os.path.basename(path))

        if uploaded:
            self.attach_label.config(
                text="Выбраны файлы:\n" + "\n".join(uploaded), fg="green", justify="left"
            )
            messagebox.showinfo("Успех", f"Загружено {len(uploaded)} файлов")
        else:
            messagebox.showerror("Ошибка", "Не удалось загрузить файлы")

    def send_bulk_thread(self):
        threading.Thread(target=self.send_bulk).start()

    def send_bulk(self):
        token = self.get_token()
        if not token:
            return

        ids_text = self.ids_entry.get("1.0", tk.END).strip()
        message = self.msg_entry.get("1.0", tk.END).strip()
        if not ids_text or not message:
            messagebox.showerror("Ошибка", "Введите User IDs и текст сообщения!")
            return

        ids = [i.strip() for i in ids_text.split(",") if i.strip()]
        total = len(ids)
        self.progress["maximum"] = total
        self.progress["value"] = 0
        self.progress_label.config(text=f"0 из {total}")

        success = fail = 0
        for idx, uid in enumerate(ids, start=1):
            try:
                if send_max_message(uid, message, token, self.attachments):
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                print(f"[ERROR] {uid}: {e}")
                fail += 1

            # обновляем прогресс
            self.progress["value"] = idx
            self.progress_label.config(text=f"{idx} из {total}")
            self.root.update_idletasks()

        messagebox.showinfo("Результат", f"Отправлено: {success}, Ошибок: {fail}")
        self.progress_label.config(text="Готово ✅")


if __name__ == "__main__":
    root = tk.Tk()
    app = MessengerApp(root)
    root.mainloop()
