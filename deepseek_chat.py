import tkinter as tk
from tkinter import scrolledtext, messagebox, font
import threading
import json
import requests
from pynput import keyboard
from pynput.keyboard import Key, Controller
import sys
import os
import queue
import datetime
import textwrap
import pyperclip
from dataclasses import dataclass
from typing import Optional

# Конфигурация API (ваш вариант)
API_KEY = "sk-2mppQStx-Jd403pZtIAYbQ"  # Замените на ваш API ключ
API_BASE_URL = "https://llm.globalapi.ru/v1"  # Базовый URL из вашего примера
API_CHAT_ENDPOINT = f"{API_BASE_URL}/chat/completions"
HOTKEY = {Key.ctrl_l, Key.alt_l, Key.space}
MODEL = "deepseek-chat"


@dataclass
class MessageStyle:
    """Стиль для сообщений"""
    bg_color: str
    text_color: str
    border_color: str
    align: str  # 'left' или 'right'
    avatar: str
    name: str
    name_color: str
    copy_btn_color: str


class ChatBubble(tk.Frame):
    """Виджет сообщения в виде облачка с кнопкой копирования"""

    def __init__(self, parent, text, style: MessageStyle, max_width=400, message_id=None, **kwargs):
        super().__init__(parent, bg='#1a1a1a', **kwargs)

        self.style = style
        self.text = text
        self.max_width = max_width
        self.message_id = message_id or datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

        self.create_widgets()

        # Для анимации копирования
        self.copy_animation_id = None

    def create_widgets(self):
        """Создание виджетов сообщения"""
        # Основной контейнер
        main_container = tk.Frame(self, bg='#1a1a1a')

        if self.style.align == 'right':
            main_container.pack(anchor='e')
            avatar_side = 'right'
            text_side = 'left'
            btn_align = 'w'
        else:
            main_container.pack(anchor='w')
            avatar_side = 'left'
            text_side = 'right'
            btn_align = 'e'

        # Аватарка
        avatar_frame = tk.Frame(main_container, bg='#1a1a1a')
        avatar_frame.pack(side=avatar_side, padx=(0 if self.style.align == 'right' else 5,
                                                  5 if self.style.align == 'right' else 0))

        avatar_label = tk.Label(
            avatar_frame,
            text=self.style.avatar,
            font=("Segoe UI Emoji", 14),
            bg='#2a2a2a',
            fg=self.style.name_color,
            width=2,
            height=1,
            relief='flat',
            padx=5,
            pady=5
        )
        avatar_label.pack()

        # Контейнер для текста и кнопок
        text_container = tk.Frame(main_container, bg='#1a1a1a')
        text_container.pack(side=text_side)

        # Имя отправителя
        if self.style.name:
            name_frame = tk.Frame(text_container, bg='#1a1a1a')
            name_frame.pack(fill='x', pady=(0, 2))

            name_label = tk.Label(
                name_frame,
                text=self.style.name,
                font=("Segoe UI", 9, "bold"),
                fg=self.style.name_color,
                bg='#1a1a1a',
                anchor='w' if self.style.align == 'left' else 'e'
            )
            name_label.pack(side='left' if self.style.align == 'left' else 'right')

        # Облачко с текстом
        bubble_frame = tk.Frame(text_container, bg=self.style.bg_color,
                                relief='flat', bd=0)
        bubble_frame.pack()

        # Текст сообщения с переносами
        wrapped_text = self.wrap_text(self.text)

        # ВСЕГДА используем Label с динамической высотой
        message_label = tk.Label(
            bubble_frame,
            text=wrapped_text,
            font=("Segoe UI", 10),
            fg=self.style.text_color,
            bg=self.style.bg_color,
            justify='center',
            wraplength=self.max_width - 20,  # Максимальная ширина с учетом отступов
            padx=12,
            pady=8
        )
        message_label.pack()

        # Фрейм для времени и кнопок
        bottom_frame = tk.Frame(text_container, bg='#1a1a1a')
        bottom_frame.pack(fill='x', pady=(2, 0))

        # Время
        time_label = tk.Label(
            bottom_frame,
            text=datetime.datetime.now().strftime("%H:%M"),
            font=("Segoe UI", 8),
            fg='#666666',
            bg='#1a1a1a'
        )

        # Кнопка копирования
        self.copy_btn = tk.Label(
            bottom_frame,
            text="📋 Копировать",
            font=("Segoe UI", 8),
            fg=self.style.copy_btn_color,
            bg='#1a1a1a',
            cursor="hand2"
        )

        # Располагаем элементы в зависимости от выравнивания
        if self.style.align == 'right':
            time_label.pack(side='right')
            self.copy_btn.pack(side='right', padx=5)
        else:
            time_label.pack(side='left')
            self.copy_btn.pack(side='left', padx=5)

        # Привязываем события к кнопке копирования
        self.copy_btn.bind("<Button-1>", lambda e: self.copy_text())
        self.copy_btn.bind("<Enter>", lambda e: self.on_copy_btn_enter())
        self.copy_btn.bind("<Leave>", lambda e: self.on_copy_btn_leave())

    def wrap_text(self, text):
        """Форматирование текста с переносами"""
        # Автоматическое определение максимальной длины строки
        max_line_length = 60

        # Разбиваем текст на абзацы
        paragraphs = text.split('\n')
        wrapped_paragraphs = []

        for paragraph in paragraphs:
            if len(paragraph) <= max_line_length:
                wrapped_paragraphs.append(paragraph)
            else:
                # Используем textwrap для переноса длинных строк
                words = paragraph.split()
                lines = []
                current_line = []
                current_length = 0

                for word in words:
                    word_length = len(word)
                    if current_length + word_length + (1 if current_line else 0) <= max_line_length:
                        current_line.append(word)
                        current_length += word_length + (1 if current_line else 0)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = word_length

                if current_line:
                    lines.append(' '.join(current_line))

                wrapped_paragraphs.append('\n'.join(lines))

        return '\n'.join(wrapped_paragraphs)

    def copy_text(self):
        """Копирование текста сообщения в буфер обмена"""
        try:
            # Копируем текст
            pyperclip.copy(self.text)

            # Анимация копирования
            self.show_copy_animation()

        except Exception as e:
            print(f"Ошибка при копировании: {e}")

    def show_copy_animation(self):
        """Анимация успешного копирования"""
        original_text = self.copy_btn.cget("text")
        original_color = self.copy_btn.cget("fg")

        # Меняем текст и цвет
        self.copy_btn.config(text="✓ Скопировано!", fg="#4CAF50")

        # Возвращаем обратно через 2 секунды
        if self.copy_animation_id:
            self.copy_btn.after_cancel(self.copy_animation_id)

        self.copy_animation_id = self.copy_btn.after(2000,
                                                     lambda: self.reset_copy_button(original_text, original_color))

    def reset_copy_button(self, original_text, original_color):
        """Восстановление кнопки копирования"""
        self.copy_btn.config(text=original_text, fg=original_color)
        self.copy_animation_id = None

    def on_copy_btn_enter(self):
        """При наведении на кнопку копирования"""
        if self.copy_btn.cget("text") == "📋 Копировать":
            self.copy_btn.config(fg="#ffffff")

    def on_copy_btn_leave(self):
        """При уходе с кнопки копирования"""
        if self.copy_btn.cget("text") == "📋 Копировать":
            self.copy_btn.config(fg=self.style.copy_btn_color)


class DeepSeekChatApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("DeepSeek Assistant")

        # Настройки стилей
        self.setup_styles()

        self.chat_window = None
        self.is_window_visible = False
        self.current_keys = set()
        self.keyboard_controller = Controller()

        self.gui_queue = queue.Queue()

        # История диалога с системным промптом
        self.system_prompt = "Ты портативный помощник, который может проконсультировать по любому вопросу. Ориентация текста в твоих ответах - по середине, по этому подстраивай свои ответы под этот параметр "
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Счетчик сообщений
        self.message_counter = 0

        # Запуск
        self.root.after(100, self.process_gui_queue)
        self.start_hotkey_listener()

        print("✨ DeepSeek Assistant запущен")
        print(f"📡 API: {API_BASE_URL}")
        print("📌 Горячие клавиши: Ctrl+Alt+Space")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """Настройка стилей сообщений"""
        self.styles = {
            'user': MessageStyle(
                bg_color='#2d7df6',
                text_color='#ffffff',
                border_color='#1e6bd8',
                align='right',
                avatar='👤',
                name='Вы',
                name_color='#4CAF50',
                copy_btn_color='#90CAF9'
            ),
            'assistant': MessageStyle(
                bg_color='#2a2a2a',
                text_color='#e0e0e0',
                border_color='#3a3a3a',
                align='left',
                avatar='🤖',
                name='DeepSeek',
                name_color='#2196F3',
                copy_btn_color='#B0BEC5'
            ),
            'system': MessageStyle(
                bg_color='#333333',
                text_color='#aaaaaa',
                border_color='#444444',
                align='center',
                avatar='⚙️',
                name='Система',
                name_color='#FF9800',
                copy_btn_color='#FFCC80'
            ),
            'welcome': MessageStyle(
                bg_color='#1E88E5',
                text_color='#ffffff',
                border_color='#1976D2',
                align='left',
                avatar='🌟',
                name='Добро пожаловать!',
                name_color='#FFD700',
                copy_btn_color='#BBDEFB'
            ),
            'api_info': MessageStyle(
                bg_color='#37474F',
                text_color='#ffffff',
                border_color='#455A64',
                align='center',
                avatar='📡',
                name='API Информация',
                name_color='#80DEEA',
                copy_btn_color='#B0BEC5'
            )
        }

    def start_hotkey_listener(self):
        listener_thread = threading.Thread(target=self.run_keyboard_listener, daemon=True)
        listener_thread.start()

    def run_keyboard_listener(self):
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()

    def on_press(self, key):
        if key in HOTKEY:
            self.current_keys.add(key)
            if self.current_keys == HOTKEY:
                self.gui_queue.put(("toggle_window", None))

    def on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)

    def process_gui_queue(self):
        try:
            while True:
                cmd, data = self.gui_queue.get_nowait()
                if cmd == "toggle_window":
                    self.toggle_chat_window_safe()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_gui_queue)

    def toggle_chat_window_safe(self):
        if not self.is_window_visible:
            self.show_chat_window_safe()
        else:
            self.hide_chat_window_safe()

    def show_chat_window_safe(self):
        if self.chat_window is None:
            self.create_chat_window()

        self.chat_window.deiconify()
        self.chat_window.lift()
        self.input_text.focus_set()
        self.is_window_visible = True

    def hide_chat_window_safe(self):
        if self.chat_window:
            self.chat_window.withdraw()
            self.is_window_visible = False

    def create_chat_window(self):
        """Создание основного окна чата"""
        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("DeepSeek Chat")

        # Стиль окна
        self.chat_window.configure(bg='#1a1a1a')
        self.chat_window.overrideredirect(True)

        # Размер и позиция
        window_width = 500
        window_height = 700

        screen_width = self.chat_window.winfo_screenwidth()
        screen_height = self.chat_window.winfo_screenheight()

        x = screen_width - window_width - 20
        y = (screen_height - window_height) // 2

        self.chat_window.geometry(f'{window_width}x{window_height}+{x}+{y}')
        self.chat_window.resizable(False, False)
        self.chat_window.withdraw()

        self.create_widgets()

        # Горячие клавиши
        self.chat_window.bind('<Escape>', lambda e: self.hide_chat_window_safe())
        self.chat_window.bind('<Control-Return>', lambda e: self.send_message())
        self.chat_window.bind('<Control-w>', lambda e: self.hide_chat_window_safe())

        # Эффекты
        self.chat_window.attributes('-alpha', 0.98)

    def create_widgets(self):
        """Создание всех виджетов интерфейса"""
        # Основной контейнер
        main_container = tk.Frame(self.chat_window, bg='#1a1a1a', padx=0, pady=0)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Шапка
        header = tk.Frame(main_container, bg='#1a1a1a', height=60)
        header.pack(fill='x', pady=(0, 1))
        header.pack_propagate(False)

        # Градиентная линия
        gradient_line = tk.Canvas(header, height=3, bg='#1a1a1a', highlightthickness=0)
        gradient_line.pack(fill='x', side='top')

        # Создаем градиент
        width = 500
        for i in range(width):
            r = int(41 + (66 - 41) * i / width)
            g = int(168 + (195 - 168) * i / width)
            b = int(185 + (250 - 185) * i / width)
            color = f'#{r:02x}{g:02x}{b:02x}'
            gradient_line.create_line(i, 0, i, 3, fill=color)

        # Заголовок и кнопки
        title_frame = tk.Frame(header, bg='#1a1a1a')
        title_frame.place(relx=0.5, rely=0.5, anchor='center')

        tk.Label(
            title_frame,
            text="💬 DeepSeek Assistant",
            font=("Segoe UI", 13, "bold"),
            fg='#ffffff',
            bg='#1a1a1a'
        ).pack(side='left', padx=(0, 20))

        # Кнопка копирования всего чата
        copy_all_btn = tk.Label(
            title_frame,
            text="📄",
            font=("Segoe UI", 12),
            fg='#888888',
            bg='#1a1a1a',
            cursor="hand2"
        )
        copy_all_btn.pack(side='left', padx=(0, 10))
        copy_all_btn.bind("<Button-1>", lambda e: self.copy_all_chat())
        copy_all_btn.bind("<Enter>", lambda e: copy_all_btn.config(fg='#ffffff', text="📋"))
        copy_all_btn.bind("<Leave>", lambda e: copy_all_btn.config(fg='#888888', text="📄"))

        # Кнопка закрытия
        close_btn = tk.Label(
            title_frame,
            text="✕",
            font=("Segoe UI", 14),
            fg='#888888',
            bg='#1a1a1a',
            cursor="hand2"
        )
        close_btn.pack(side='right')
        close_btn.bind("<Button-1>", lambda e: self.hide_chat_window_safe())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg='#ffffff'))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg='#888888'))

        # Контейнер для чата с прокруткой
        chat_container = tk.Frame(main_container, bg='#1a1a1a')
        chat_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 15))

        # Canvas для сообщений с прокруткой
        self.chat_canvas = tk.Canvas(chat_container, bg='#1a1a1a', highlightthickness=0)
        scrollbar = tk.Scrollbar(chat_container, orient="vertical",
                                 command=self.chat_canvas.yview)

        self.chat_frame = tk.Frame(self.chat_canvas, bg='#1a1a1a')

        # Настройка прокрутки
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        # Упаковка элементов
        scrollbar.pack(side="right", fill="y")
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        # Создаем окно в canvas для фрейма
        self.canvas_window = self.chat_canvas.create_window(
            (0, 0), window=self.chat_frame, anchor="nw", width=460
        )

        # Привязка событий
        self.chat_frame.bind("<Configure>", self.on_frame_configure)
        self.chat_canvas.bind("<Configure>", self.on_canvas_configure)

        # Плавная прокрутка колесиком мыши
        self.chat_canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # Приветственное сообщение
        self.add_welcome_message()

        # Панель ввода
        input_container = tk.Frame(main_container, bg='#1a1a1a', height=120)
        input_container.pack(fill='x', padx=15, pady=(0, 15))
        input_container.pack_propagate(False)

        # Рамка для поля ввода
        input_frame = tk.Frame(input_container, bg='#2a2a2a', relief='flat')
        input_frame.pack(fill='both', expand=True, padx=1, pady=1)

        # Поле ввода с подсказкой
        self.input_text = tk.Text(
            input_frame,
            height=3,
            font=("Segoe UI", 11),
            bg='#2a2a2a',
            fg='#ffffff',
            insertbackground='#ffffff',
            relief='flat',
            wrap=tk.WORD,
            padx=12,
            pady=10
        )
        self.input_text.pack(side='left', fill='both', expand=True)
        self.input_text.bind('<Return>', self.on_enter_pressed)

        # Подсказка в поле ввода
        self.placeholder = ""
        self.input_text.insert('1.0', self.placeholder)
        self.input_text.tag_add('placeholder', '1.0', 'end')
        self.input_text.tag_config('placeholder', foreground='#666666')

        self.input_text.bind('<FocusIn>', self.on_input_focus_in)
        self.input_text.bind('<FocusOut>', self.on_input_focus_out)

        # Фрейм для кнопок отправки
        btn_frame = tk.Frame(input_frame, bg='#2a2a2a', width=80)
        btn_frame.pack(side='right', fill='y')
        btn_frame.pack_propagate(False)

        # Кнопка отправки
        send_btn = tk.Label(
            btn_frame,
            text="➤",
            font=("Segoe UI", 16, "bold"),
            fg='#4CAF50',
            bg='#2a2a2a',
            cursor="hand2"
        )
        send_btn.place(relx=0.5, rely=0.3, anchor='center')
        send_btn.bind("<Button-1>", lambda e: self.send_message())
        send_btn.bind("<Enter>", lambda e: send_btn.config(fg='#66BB6A'))
        send_btn.bind("<Leave>", lambda e: send_btn.config(fg='#4CAF50'))

        # Кнопка очистки чата
        clear_btn = tk.Label(
            btn_frame,
            text="🗑️",
            font=("Segoe UI", 12),
            fg='#FF5252',
            bg='#2a2a2a',
            cursor="hand2"
        )
        clear_btn.place(relx=0.5, rely=0.7, anchor='center')
        clear_btn.bind("<Button-1>", lambda e: self.clear_chat())
        clear_btn.bind("<Enter>", lambda e: clear_btn.config(fg='#FF8A80'))
        clear_btn.bind("<Leave>", lambda e: clear_btn.config(fg='#FF5252'))

    def add_welcome_message(self):
        """Добавление приветственного сообщения"""
        welcome_text = f"""Привет! Я DeepSeek Assistant 🤖

📡 Используется API: {API_BASE_URL}
💬 Системный промпт: "{self.system_prompt}"

Я здесь, чтобы помочь вам с:
• Ответами на вопросы
• Решением задач
• Объяснением сложных тем
• Написанием кода
• И многим другим!

💡 Под каждым сообщением есть кнопка "Копировать" - нажмите её, чтобы скопировать текст в буфер обмена.

Просто напишите ваш вопрос, и я постараюсь помочь! ✨"""

        self.add_message(welcome_text, 'welcome')

    def on_input_focus_in(self, event):
        """Обработка фокуса на поле ввода"""
        if self.input_text.get('1.0', 'end-1c') == self.placeholder:
            self.input_text.delete('1.0', 'end')
            self.input_text.config(fg='#ffffff')

    def on_input_focus_out(self, event):
        """Обработка потери фокуса полем ввода"""
        if not self.input_text.get('1.0', 'end-1c').strip():
            self.input_text.insert('1.0', self.placeholder)
            self.input_text.tag_add('placeholder', '1.0', 'end')
            self.input_text.config(fg='#666666')

    def on_frame_configure(self, event=None):
        """Обновление скроллбара при изменении размера фрейма"""
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Изменение размера окна в canvas"""
        self.chat_canvas.itemconfig(self.canvas_window, width=event.width)

    def on_mousewheel(self, event):
        """Прокрутка колесиком мыши"""
        self.chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_enter_pressed(self, event):
        """Обработка нажатия Enter"""
        if event.state == 4:  # Ctrl нажат
            self.send_message()
            return "break"
        elif event.state == 0:  # Ctrl не нажат
            # Shift+Enter для новой строки
            if event.state & 1:  # Shift нажат
                return None
            else:
                self.send_message()
                return "break"
        return None

    def add_message(self, text, sender_type='user'):
        """Добавление нового сообщения в чат"""
        style = self.styles.get(sender_type, self.styles['user'])

        # Увеличиваем счетчик сообщений
        self.message_counter += 1
        message_id = f"{sender_type}_{self.message_counter}"

        # Создаем bubble сообщения
        bubble = ChatBubble(
            self.chat_frame,
            text,
            style,
            max_width=400,
            message_id=message_id
        )

        # Добавляем отступы в зависимости от типа сообщения
        if sender_type == 'user':
            bubble.pack(fill='x', padx=(40, 5), pady=8, anchor='e')
        elif sender_type in ['welcome', 'api_info', 'system']:
            bubble.pack(fill='x', padx=5, pady=8, anchor='center')
        else:
            bubble.pack(fill='x', padx=(5, 40), pady=8, anchor='w')

        # Сохраняем ссылку на сообщение
        if not hasattr(self, 'messages'):
            self.messages = []
        self.messages.append(bubble)

        # Обновляем прокрутку
        self.chat_frame.update_idletasks()
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

        # Автопрокрутка вниз
        self.chat_canvas.yview_moveto(1.0)

        return bubble

    def add_typing_indicator(self):
        """Добавление индикатора набора текста - УПРОЩЕННАЯ ВЕРСИЯ"""
        typing_frame = tk.Frame(self.chat_frame, bg='#1a1a1a')
        typing_frame.pack(fill='x', padx=(5, 40), pady=12, anchor='w')

        # Простой индикатор без точек
        indicator_container = tk.Frame(typing_frame, bg='#2a2a2a', relief='flat')
        indicator_container.pack(anchor='w')

        # Аватар
        tk.Label(
            indicator_container,
            text="🤖",
            font=("Segoe UI Emoji", 12),
            bg='#2a2a2a',
            fg='#2196F3',
            padx=8,
            pady=8
        ).pack(side='left')

        # Текст без дополнительных параметров padx
        tk.Label(
            indicator_container,
            text="Печатает...",
            font=("Segoe UI", 9),
            fg='#aaaaaa',
            bg='#2a2a2a'
        ).pack(side='left', padx=5)

        return typing_frame

    def send_message(self):
        """Отправка сообщения через API"""
        message = self.input_text.get("1.0", tk.END).strip()

        if not message or message == self.placeholder:
            return

        # Очищаем поле ввода
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert('1.0', self.placeholder)
        self.input_text.tag_add('placeholder', '1.0', 'end')
        self.input_text.config(fg='#666666')

        # Добавляем сообщение пользователя
        self.add_message(message, 'user')
        self.conversation_history.append({"role": "user", "content": message})

        # Добавляем УПРОЩЕННЫЙ индикатор набора текста
        self.typing_indicator = self.add_typing_indicator()

        # Отправляем запрос в отдельном потоке
        threading.Thread(target=self.get_ai_response, args=(message,), daemon=True).start()

    def get_ai_response(self, user_message):
        """Получение ответа от API"""
        try:
            # Подготавливаем данные для запроса
            request_data = {
                "model": MODEL,
                "messages": self.conversation_history,
                "stream": False
            }

            # Отправляем запрос к API (ваш вариант)
            response = requests.post(
                API_CHAT_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json=request_data,
                timeout=100
            )

            # Проверяем ответ
            response.raise_for_status()

            # Парсим JSON ответ
            result = response.json()

            # Извлекаем текст ответа (в зависимости от структуры API)
            if 'choices' in result and len(result['choices']) > 0:
                ai_response = result['choices'][0]['message']['content']
            elif 'text' in result:
                ai_response = result['text']
            else:
                # Пробуем разные возможные структуры
                if 'response' in result:
                    ai_response = result['response']
                elif 'output' in result:
                    ai_response = result['output']
                elif 'content' in result:
                    ai_response = result['content']
                else:
                    # Если непонятная структура, показываем весь ответ для отладки
                    ai_response = f"Ответ API: {json.dumps(result, ensure_ascii=False, indent=2)}"
                    self.root.after(0, self.add_message,
                                    f"⚠️ Нестандартная структура ответа API:\n{ai_response}", 'api_info')
                    return

            # Добавляем ответ в историю
            self.conversation_history.append({"role": "assistant", "content": ai_response})

            # Удаляем индикатор и добавляем ответ
            self.root.after(0, self.show_ai_response, ai_response)

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка соединения с API: {str(e)}"
            self.root.after(0, self.show_error, error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Ошибка разбора JSON ответа: {str(e)}"
            self.root.after(0, self.show_error, error_msg)
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            self.root.after(0, self.show_error, error_msg)

    def show_ai_response(self, response_text):
        """Отображение ответа AI"""
        # Удаляем индикатор набора
        if hasattr(self, 'typing_indicator'):
            self.typing_indicator.destroy()

        # Добавляем ответ
        self.add_message(response_text, 'assistant')

    def show_error(self, error_msg):
        """Отображение ошибки"""
        # Удаляем индикатор набора
        if hasattr(self, 'typing_indicator'):
            self.typing_indicator.destroy()

        # Добавляем сообщение об ошибке
        self.add_message(f"⚠️ {error_msg}", 'system')

    def copy_all_chat(self):
        """Копирование всего чата"""
        try:
            chat_text = f"DeepSeek Assistant Chat\nAPI: {API_BASE_URL}\n{'=' * 40}\n\n"

            # Собираем текст всех сообщений
            if hasattr(self, 'messages'):
                for msg in self.messages:
                    # Добавляем отправителя и текст
                    if hasattr(msg, 'style'):
                        sender = msg.style.name
                        chat_text += f"{sender}:\n{msg.text}\n\n"

            if chat_text:
                pyperclip.copy(chat_text.strip())

                # Показываем уведомление
                self.show_copy_all_notification()
            else:
                self.show_error("Чат пуст")

        except Exception as e:
            print(f"Ошибка при копировании чата: {e}")

    def show_copy_all_notification(self):
        """Показ уведомления о копировании всего чата"""
        # Создаем всплывающее уведомление
        notification = tk.Toplevel(self.chat_window)
        notification.overrideredirect(True)
        notification.configure(bg='#4CAF50')

        # Позиционируем
        notification.geometry("+%d+%d" % (
            self.chat_window.winfo_rootx() + 100,
            self.chat_window.winfo_rooty() + 50
        ))

        # Текст уведомления
        tk.Label(
            notification,
            text="✓ Весь чат скопирован в буфер!",
            font=("Segoe UI", 10, "bold"),
            fg='white',
            bg='#4CAF50',
            padx=15,
            pady=10
        ).pack()

        # Автоматическое закрытие через 2 секунды
        notification.after(2000, notification.destroy)

    def clear_chat(self):
        """Очистка чата (только визуальная)"""
        if messagebox.askyesno("Очистка чата",
                               "Очистить историю сообщений?\n(Диалог с AI продолжится)"):
            # Удаляем все сообщения из интерфейса
            for widget in self.chat_frame.winfo_children():
                widget.destroy()

            # Очищаем список сообщений
            if hasattr(self, 'messages'):
                self.messages.clear()

            # Восстанавливаем системный промпт в истории
            self.conversation_history = [
                {"role": "system", "content": self.system_prompt}
            ]

            # Добавляем приветственное сообщение заново
            self.add_welcome_message()

    def test_api_connection(self):
        """Тестирование соединения с API"""
        try:
            test_data = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "Hello, test message"}
                ],
                "stream": False
            }

            response = requests.post(
                API_CHAT_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json=test_data,
                timeout=10
            )

            if response.status_code == 200:
                self.add_message("✅ Соединение с API успешно установлено", 'api_info')
                return True
            else:
                self.add_message(f"❌ Ошибка API: {response.status_code}", 'system')
                return False

        except Exception as e:
            self.add_message(f"❌ Ошибка соединения: {str(e)}", 'system')
            return False

    def on_closing(self):
        """Обработка закрытия приложения"""
        if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
            self.root.quit()
            self.root.destroy()
            os._exit(0)

    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


def main():
    """Точка входа"""
    app = DeepSeekChatApp()
    app.run()


if __name__ == "__main__":
    main()