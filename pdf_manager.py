import subprocess
import time
import os
import platform

# Check system OS to avoid crashing on macOS
IS_LINUX = platform.system() == "Linux"

HAS_PYDBUS = False
if IS_LINUX:
    try:
        from pydbus import SessionBus
        HAS_PYDBUS = True
    except (ImportError, Exception):
        HAS_PYDBUS = False

class pdfManager:
    """
    Manage PDF playback in Zathura via D-Bus.
    """
    def __init__(self, pdf_folder):
        self.pdf_folder = pdf_folder
        self.dbus = None
        self.zathura_ps = None
        self.current_pdf = None
        self.current_page = 1

    def clear_zathura_sessions(self):
        """
        Delete Zathura session and history files to ensure a clean start.
        """
        home = os.path.expanduser("~")
        sessions_path = os.path.join(home, ".local", "share", "zathura", "sessions")
        history_path = os.path.join(home, ".local", "share", "zathura", "history")

        if os.path.exists(sessions_path):
            for f in os.listdir(sessions_path):
                try:
                    os.remove(os.path.join(sessions_path, f))
                except Exception as e:
                    print(f"Error removing session {f}: {e}")

        if os.path.exists(history_path):
            try:
                os.remove(history_path)
            except Exception as e:
                print(f"Error removing history: {e}")

    def start_zathura(self, initial_pdf_rel=None):
        """
        Launch Zathura in presentation mode.
        """
        if not HAS_PYDBUS:
            return
        
        self.clear_zathura_sessions()
        cmd = ['zathura', '--mode=presentation', '--page=1']
        
        if initial_pdf_rel:
            full_path = os.path.join(self.pdf_folder, initial_pdf_rel)
            cmd.append(full_path)
        
        self.zathura_ps = subprocess.Popen(cmd)
        time.sleep(4) # Tiempo para que el servicio D-Bus se registre

        # Buscamos el servicio D-Bus por PID como en tu versión original
        try:
            bus = SessionBus()
            service_name = None
            for name in bus.get("org.freedesktop.DBus").ListNames():
                if name.startswith("org.pwmt.zathura.PID"):
                    service_name = name
                    break
            
            if service_name:
                self.dbus = bus.get(service_name, "/org/pwmt/zathura")
                self.current_page = 1
                self.dbus.GotoPage(self.current_page)
        except Exception as e:
            print(f"D-Bus connection error: {e}")

    def is_dbus_active(self):
        if not self.dbus: return False
        try:
            self.dbus.Ping()
            return True
        except:
            return False

    def open_pdf(self, relative_path):
        """
        Open a new PDF via D-Bus if running, or restart Zathura.
        """
        file_path = os.path.abspath(os.path.join(self.pdf_folder, relative_path))
        self.current_pdf = relative_path

        if not self.is_dbus_active():
            self.start_zathura(relative_path)
        else:
            try:
                self.current_page = 0
                self.dbus.OpenDocument(file_path, "", self.current_page)
            except Exception as e:
                print(f"Error opening PDF: {e}")
                # Si falla, intentamos reiniciar
                self.start_zathura(relative_path)

    def turn_page(self):
        if self.is_dbus_active():
            self.current_page += 1
            self.dbus.GotoPage(self.current_page)

    def close(self):
        if self.zathura_ps:
            self.zathura_ps.terminate()