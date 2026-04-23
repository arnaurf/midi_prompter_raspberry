import tkinter as tk
import platform

CURSOR_NAME = "hand2" if platform.system() == "Linux" else "pontinghand"

class OverlayMenu:
    def __init__(self, pdf_files, callback):
        self.pdf_files = pdf_files
        self.callback = callback
        
        # Initialize Tcl engine
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Theme
        self.bg_color = '#121212'
        self.list_bg = '#1e1e1e'
        self.fg_color = '#ffffff'
        self.accent_color = 'cyan'
        
        # State management
        self.current_callback = None
        self.active_hint = None
        
        # Global binding: Catch Enter anywhere in the app
        self.root.bind_all('<Return>', self._global_handle_enter)

    # --- PRIVATE HELPERS ---

    def _global_handle_enter(self, event=None):
        """Internal trigger for the hint window."""
        if self.current_callback:
            # Desactivamos el bind global inmediatamente para liberar la tecla Enter
            self.root.unbind_all('<Return>')
            
            cb = self.current_callback
            self.current_callback = None 
            
            if self.active_hint:
                try:
                    self.active_hint.destroy()
                except:
                    pass
                self.active_hint = None
            
            cb()

    def _prepare_window(self, width, height, borderless=True, position="center"):
        win = tk.Toplevel(self.root)
        win.attributes("-topmost", True)
        
        if borderless:
            win.overrideredirect(True)
            # 'utility' es mejor que 'notification' para recibir teclado
            try:
                win.tk.call('wm', 'attributes', win._w, '-type', 'utility')
            except:
                pass

        win.configure(bg=self.bg_color)

        # 1. Antes de aplicar borderless, calculamos posición
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        if position == "center":
            x, y = (sw - width) // 2, (sh - height) // 2
        elif position == "top-right":
            x, y = sw - width - 20, 40
        elif position == "bottom-right":
            x, y = sw - width - 20, sh - height - 80
        
        win.geometry(f"{width}x{height}+{x}+{y}")
        
        return win

    def _create_list_ui(self, parent, title, items, on_select_callback):
        # Eliminar bordes del contenedor padre si existen
        parent.config(padx=0, pady=0, highlightthickness=0)

        # Título con menos margen superior
        tk.Label(parent, text=title.upper(), fg=self.accent_color, bg=self.bg_color, 
                 font=("Helvetica", 9, "bold")).pack(pady=(8, 2))

        # Listbox sin bordes y con highlight sutil
        listbox = tk.Listbox(parent, 
                              bg=self.list_bg, 
                              fg=self.fg_color, 
                              font=("Helvetica", 11), 
                              borderwidth=0, 
                              highlightthickness=0, # 0 para minimalismo total
                              selectbackground=self.accent_color, 
                              selectforeground="black",
                              activestyle='none')
        
        # fill=tk.BOTH y expand=True para que ocupe toda la ventana sin dejar huecos grises
        listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for item in items:
            listbox.insert(tk.END, f" {item}")

        # --- LÓGICA DE SELECCIÓN ---
        def confirm(e=None):
            selection = listbox.curselection()
            if selection:
                on_select_callback(selection[0])
                parent.grab_release() # <--- LIBERAR AQUÍ
                parent.destroy()

        def on_press(event):
            # Al hacer click, forzamos la selección del elemento bajo el ratón y confirmamos
            index = listbox.nearest(event.y)
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index)
            listbox.activate(index)
            confirm()

        # --- BINDINGS ROBUSTOS ---
        # Enter (Principal y Numérico)
        listbox.bind('<Return>', confirm)
        listbox.bind('<KP_Enter>', confirm)
        
        # Click instantáneo
        listbox.bind('<ButtonPress-1>', on_press)
        
        # Escape para salir
        parent.bind('<Escape>', lambda e: parent.destroy())

        # --- GESTIÓN DE FOCO AGRESIVA ---
        listbox.selection_set(0)
        listbox.activate(0)
        listbox.focus_force()

        # EL TRUCO MAESTRO PARA LINUX:
        # Esperamos un instante a que la ventana exista y forzamos el 'grab'
        def force_input():
            parent.grab_set() # Esto redirige TODO el teclado a esta ventana
            listbox.focus_set()
        
        parent.after(100, force_input)

        return listbox
    # --- PUBLIC METHODS ---

    def prompt_selection(self, title, options):
        """Blocking selection for setup (MIDI). Returns index."""
        win = self._prepare_window(width=450, height=350, borderless=False)
        win.title(title)
        
        res = tk.IntVar(value=-1)
        
        def save_idx(idx):
            res.set(idx)

        self._create_list_ui(win, title, options, save_idx)
        
        win.lift()
        win.focus_force()
        win.wait_variable(res)
        return res.get()

    def show_mini_hint(self, on_enter_callback):
        self.current_callback = on_enter_callback
        if self.active_hint:
            self.active_hint.destroy()

        self.active_hint = self._prepare_window(width=220, height=50, borderless=True, position="top-right")
        
        import platform
        cursor_type = "hand2" if platform.system() == "Linux" else "pointinghand"
        
        label = tk.Label(self.active_hint, text="  [ ENTER ] for Menu  ", 
                         fg=self.accent_color, bg=self.bg_color,
                         font=("Helvetica", 11, "bold"), cursor=cursor_type)
        label.pack(expand=True, fill=tk.BOTH)

        # BINDINGS PARA LINUX (Teclado)
        # Enlazamos a la ventana y al root para máxima seguridad
        self.active_hint.bind('<Return>', lambda e: self._global_handle_enter())
        self.root.bind('<Return>', lambda e: self._global_handle_enter())

        # BINDING PARA CLIC (Mantener lo que ya funciona)
        label.bind('<ButtonPress-1>', lambda e: self._global_handle_enter())
        
        # FORZAR FOCO (Crítico en Raspberry)
        self.active_hint.focus_force()
        self.active_hint.update()

    def show_pdf_selector(self):
        """Shows the minimalist selector at the BOTTOM-RIGHT."""
        num_songs = len(self.pdf_files)
        # Un poco más alto para que quepan bien las canciones abajo
        calculated_height = min(450, (num_songs * 28) + 60)
        
        # Posición: bottom-right
        win = self._prepare_window(width=280, height=calculated_height, borderless=True, position="bottom-right")
        
        sorted_ids = sorted(self.pdf_files.keys())
        names = [f"[{i}] {self.pdf_files[i]}" for i in sorted_ids]

        def on_pdf_chosen(list_idx):
            real_id = sorted_ids[list_idx]
            self.callback(real_id)

        self._create_list_ui(win, "Setlist", names, on_pdf_chosen)
        win.lift()
        win.focus_force()

    def update(self):
        """Process Tkinter events."""
        self.root.update()
