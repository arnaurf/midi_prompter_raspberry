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
        print(f"DEBUG: Triggered _global_handle_enter. Callback exists: {self.current_callback is not None}")
        
        if self.current_callback:
            cb = self.current_callback
            self.current_callback = None 
            if self.active_hint:
                try:
                    self.active_hint.destroy()
                except:
                    pass
                self.active_hint = None
            
            print("DEBUG: Executing Callback...")
            cb()

    def _prepare_window(self, width, height, borderless=True, position="center"):
        win = tk.Toplevel(self.root)
        win.attributes("-topmost", True)
        win.configure(bg=self.bg_color)
        
        win.update_idletasks()
        if borderless:
            win.overrideredirect(True)

        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        if position == "center":
            x, y = (sw - width) // 2, (sh - height) // 2
        elif position == "top-right":
            # Margen de 20px desde la derecha y 40px desde arriba (bajo la barra de Mac)
            x = sw - width - 20
            y = 40
        elif position == "bottom-right":
            # Margen de 20px desde la derecha y 80px desde abajo (sobre el Dock)
            x = sw - width - 20
            y = sh - height - 80
        
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.update_idletasks()
        
        return win

    def _create_list_ui(self, parent, title, items, on_select_callback):
        """
        Reusable UI for lists with minimalist styling.
        Optimized for instant 'ButtonPress' selection on macOS/Linux.
        """
        # Título minimalista
        tk.Label(parent, text=title.upper(), fg=self.accent_color, bg=self.bg_color, 
                 font=("Helvetica", 10, "bold")).pack(pady=(10, 5))

        # Configuración de la Listbox
        listbox = tk.Listbox(parent, 
                              bg=self.list_bg, 
                              fg=self.fg_color, 
                              font=("Helvetica", 11), 
                              borderwidth=0, 
                              highlightthickness=0, 
                              selectbackground="#333333", 
                              selectforeground=self.accent_color,
                              activestyle='none', # Elimina el subrayado feo del item activo
                              cursor=CURSOR_NAME)
        
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Insertar elementos
        for item in items:
            listbox.insert(tk.END, f" {item}")

        # Foco inicial
        listbox.focus_set()
        listbox.selection_set(0)

        # --- Lógica de Selección ---
        def confirm(e=None):
            selection = listbox.curselection()
            if selection:
                # Debug opcional para verificar la rapidez
                # print(f"DEBUG: Instant selection of index {selection[0]}")
                on_select_callback(selection[0])
                parent.destroy()

        def on_press(event):
            """
            Selecciona el elemento bajo el ratón e inmediatamente confirma.
            Esto ocurre en el momento exacto de bajar el dedo (Down).
            """
            # Obtener el índice basado en la posición Y del click
            index = listbox.nearest(event.y)
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index)
            confirm()

        # --- Bindings ---
        # 1. Teclado (Enter)
        listbox.bind('<Return>', confirm)
        
        # 2. Ratón: Instantáneo al presionar (Down)
        listbox.bind('<ButtonPress-1>', on_press)
        
        # 3. Escape para cancelar y cerrar
        parent.bind('<Escape>', lambda e: parent.destroy())

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

        self.active_hint = self._prepare_window(width=220, height=50, borderless=True, position="bottom-right")
        
        label = tk.Label(self.active_hint, text="  [ CLICK ] for Menu  ", 
                         fg=self.accent_color, bg=self.bg_color,
                         font=("Helvetica", 11, "bold"), cursor=CURSOR_NAME)
        label.pack(expand=True, fill=tk.BOTH)

        # USAMOS ButtonPress-1 para que sea instantáneo al bajar el dedo
        label.bind('<ButtonPress-1>', lambda e: self._global_handle_enter())
        
        self.active_hint.lift()
        self.active_hint.focus_force()

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
