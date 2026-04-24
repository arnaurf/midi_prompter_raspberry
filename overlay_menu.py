import tkinter as tk
import platform
import queue
import os
from pynput import keyboard

class OverlayMenu:
    def __init__(self, pdf_root, callback):
        self.pdf_root = pdf_root
        self.callback = callback
        self.current_subpath = ""
        
        self.root = tk.Tk()
        self.root.geometry("1x1-1000-1000")
        self.root.title("OverlayMaster")
        
        self.bg_color = '#121212'
        self.list_bg = '#1e1e1e'
        self.fg_color = '#ffffff'
        self.accent_color = 'cyan'
        self.folder_color = '#f1c40f'
        
        self.current_callback = None
        self.active_hint = None
        self.active_window = None
        self.current_listbox = None
        self.is_midi_setup = False
        
        self.key_queue = queue.Queue()
        self.cursor_type = "hand2" if platform.system() == "Linux" else "pointinghand"

        self._check_queue()
        self.listener = keyboard.Listener(on_press=self._on_pynput_press)
        self.listener.daemon = True
        self.listener.start()

    def _on_pynput_press(self, key):
        try:
            is_enter = key == keyboard.Key.enter or getattr(key, 'vk', None) in [13, 36, 104]
            if is_enter:
                self.key_queue.put("Return")
            elif hasattr(key, 'char'):
                if key.char == 'w': self.key_queue.put("Up")
                elif key.char == 's': self.key_queue.put("Down")
            elif key == keyboard.Key.esc:
                self.key_queue.put("Escape")
        except Exception: pass

    def _check_queue(self):
        try:
            while True:
                key_name = self.key_queue.get_nowait()
                self._handle_logic(key_name)
        except queue.Empty: pass
        self.root.after(20, self._check_queue)

    def _handle_logic(self, key_name):
        if self.active_hint and self.active_hint.winfo_exists() and not self.active_window:
            if key_name == "Return":
                self._global_handle_enter()
                return

        if self.active_window and self.active_window.winfo_exists():
            if key_name == "Escape":
                self._close_current_window()
            elif self.current_listbox:
                if key_name == "Up": self._move_selection(-1)
                elif key_name == "Down": self._move_selection(1)
                elif key_name == "Return": self._confirm_selection_logic()

    def _move_selection(self, delta):
        lb = self.current_listbox
        idx = lb.curselection()
        curr = idx[0] if idx else 0
        new = max(0, min(lb.size() - 1, curr + delta))
        lb.selection_clear(0, tk.END)
        lb.selection_set(new)
        lb.activate(new)
        lb.see(new)

    def _confirm_selection_logic(self):
        if not self.current_listbox: return
        idx_list = self.current_listbox.curselection()
        if not idx_list: return
        
        idx = idx_list[0]
        item_text = self.current_listbox.get(idx).strip()

        if self.is_midi_setup:
            self.midi_res.set(idx)
            self._close_current_window()
            return

        if item_text == "../":
            self.current_subpath = os.path.dirname(self.current_subpath)
            self.show_pdf_selector()
        elif item_text.endswith("/"):
            self.current_subpath = os.path.join(self.current_subpath, item_text[:-1])
            self.show_pdf_selector()
        else:
            full_rel_path = os.path.join(self.current_subpath, item_text)
            self._close_current_window()
            self.callback(full_rel_path)

    def _prepare_window(self, width, height, borderless=True, position="center"):
        win = tk.Toplevel(self.root)
        win.attributes("-topmost", True)
        win.configure(bg=self.bg_color)
        if borderless: win.overrideredirect(True)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        if position == "bottom-right": x, y = sw - width - 20, sh - height - 80
        elif position == "top-right": x, y = sw - width - 20, 40
        else: x, y = (sw - width) // 2, (sh - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.focus_force()
        return win

    def prompt_selection(self, title, options):
        self.is_midi_setup = True
        self.midi_res = tk.IntVar(value=-1)
        win = self._prepare_window(width=400, height=300, borderless=False)
        win.title(title)
        self._create_list_ui(win, title, [(o, "file") for o in options])
        win.wait_window(win)
        self.is_midi_setup = False
        return self.midi_res.get()

    def _create_list_ui(self, parent, title, items):
        tk.Label(parent, text=title.upper(), fg=self.accent_color, bg=self.bg_color, font=("Helvetica", 9, "bold")).pack(pady=5)
        lb = tk.Listbox(parent, bg=self.list_bg, fg=self.fg_color, borderwidth=0, highlightthickness=0, selectbackground=self.accent_color, selectforeground="black", activestyle='none', font=("Helvetica", 11))
        lb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for text, kind in items:
            lb.insert(tk.END, f" {text}")
            if kind == "folder": lb.itemconfig(tk.END, fg=self.folder_color)
            elif kind == "back": lb.itemconfig(tk.END, fg=self.accent_color)
        lb.selection_set(0)
        self.current_listbox = lb
        self.active_window = parent

    def show_mini_hint(self, on_enter_callback):
        self.current_callback = on_enter_callback
        if self.active_hint: self.active_hint.destroy()
        self.active_hint = self._prepare_window(200, 45, position="top-right")
        tk.Label(self.active_hint, text="  [ ENTER ] for Menu  ", fg=self.accent_color, bg=self.bg_color, font=("Helvetica", 10, "bold")).pack(expand=True, fill=tk.BOTH)

    def show_pdf_selector(self):
        """Navegador de archivos con mensaje de ayuda en inglés."""
        abs_path = os.path.abspath(os.path.join(self.pdf_root, self.current_subpath))
        items = []
        
        if self.current_subpath and self.current_subpath != ".":
            items.append(("../", "back"))
            
        try:
            for e in sorted(os.listdir(abs_path)):
                full = os.path.join(abs_path, e)
                if os.path.isdir(full):
                    items.append((f"{e}/", "folder"))
                elif e.lower().endswith(".pdf"):
                    items.append((e, "file"))
        except:
            pass

        if self.active_window: 
            self.active_window.destroy()

        # Aumentamos un poco el alto (h) para que quepa el mensaje de ayuda
        h = min(550, (len(items) * 28) + 100) 
        win = self._prepare_window(300, h, position="bottom-right")
        
        # Título de la ventana
        title = f"/{self.current_subpath}" if self.current_subpath else "BROWSER"
        self._create_list_ui(win, title, items)

        # --- MENSAJE DE AYUDA EN INGLÉS ---
        help_text = "Use [W/S] to Navigate\n[ENTER] to Select / [ESC] to Exit"
        help_label = tk.Label(
            win, 
            text=help_text, 
            fg="#777777", # Gris suave para que no distraiga demasiado
            bg=self.bg_color, 
            font=("Helvetica", 8, "italic"),
            justify=tk.CENTER
        )
        help_label.pack(side=tk.BOTTOM, pady=(0, 10))

    def _global_handle_enter(self):
        """Maneja el Enter cuando solo está el Mini Hint visible."""
        if self.current_callback:
            cb = self.current_callback
            self.current_callback = None
            if self.active_hint:
                self.active_hint.destroy()
                self.active_hint = None
            cb()

    def _close_current_window(self):
        """Cierra la ventana activa y restaura el Hint si es necesario."""
        if self.active_window:
            self.active_window.destroy()
            self.active_window = None
            self.current_listbox = None
            
        # Si no estamos en el setup inicial de MIDI, restauramos el hint
        # para que el usuario pueda volver a abrir el menú.
        if not self.is_midi_setup:
            # Importante: pasamos el callback que abre el selector
            self.show_mini_hint(self.show_pdf_selector)

    def update(self):
        self.root.update()