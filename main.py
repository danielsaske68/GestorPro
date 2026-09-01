import os
import sys
import time
import json
import threading
import subprocess
from PIL import Image, ImageTk, ImageSequence
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

# ==========================================
# CONFIGURACIÓN DE RUTAS BASE Y MÓDULOS
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Aseguramos que Python encuentre la raíz y la carpeta 'modules'
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ==========================================
# LECTURA DINÁMICA DE VERSIÓN DESDE VERSION.JSON
# ==========================================
def obtener_version():
    ruta_version = os.path.join(BASE_DIR, "version.json")
    try:
        if os.path.exists(ruta_version):
            with open(ruta_version, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "v1.0.0")
    except Exception as e:
        print(f"Error al leer version.json: {e}")
    return "v1.0.0"

VERSION = obtener_version()

# ==========================================
# IMPORTACIONES DE TUS MÓDULOS
# ==========================================
import modules.homeserve as bot
from modules.liquidaciones import LiquidacionesFrame
from modules.servidor_local import ServidorLocalFrame
from cloud.railway_app import volver_a_railway

ctk.deactivate_automatic_dpi_awareness()
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
ctk.set_window_scaling(1.0)
ctk.set_widget_scaling(1.15)


class GestorPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 📍 Título de la pestaña/ventana con la versión leída del JSON
        self.title(f"GESTOR PRO {VERSION}")
        self.configure(fg_color="#0b0f14")
        self.geometry("1100x760")
        self.minsize(1040, 720)
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================
        # MENÚ IZQUIERDO
        # ==========================
        self.menu = ctk.CTkFrame(self, width=300, corner_radius=28, fg_color="#0b1220", border_color="#223248", border_width=1)
        self.menu.grid(row=0, column=0, sticky="ns", padx=(10, 0), pady=10)
        self.menu.grid_propagate(False)
        self.menu.grid_rowconfigure(0, weight=0)

        # Cargar Logo de assets
        try:
            RUTA_LOGO = os.path.join(BASE_DIR, "assets", "logo.png")
            logo = ctk.CTkImage(
                light_image=Image.open(RUTA_LOGO),
                dark_image=Image.open(RUTA_LOGO),
                size=(120, 120)
            )
            ctk.CTkLabel(self.menu, image=logo, text="").pack(pady=20)
        except Exception:
            ctk.CTkLabel(
                self.menu, 
                text="GESTOR PRO", 
                font=("Arial", 24, "bold")
            ).pack(pady=30)

        # Botones del Menú
        # Tamaño de botón ajustado para mejor encaje en pantallas pequeñas
        menu_style = dict(height=48, corner_radius=12, fg_color="#3b6fa8", hover_color="#2a5e8a", font=("Arial", 14, "bold"), text_color="#ffffff", border_width=1, border_color="#2f5376")
        ctk.CTkButton(self.menu, text="🏠 Inicio", command=self.inicio, **menu_style).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(self.menu, text="💰 Liquidaciones", command=self.abrir_liquidaciones, **menu_style).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(self.menu, text="🛠 Lector de códigos", command=self.abrir_lector_codigos, **menu_style).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(self.menu, text="📝 Presupuestos", command=self.abrir_presupuestos, **menu_style).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(self.menu, text="📑 Verificador de Pagos", command=self.abrir_verificador_pagos, **menu_style).pack(fill="x", padx=12, pady=5)

        self.boton_cloud = ctk.CTkButton(self.menu, text="☁️ Servidor Local", command=self.iniciar_cloud, **menu_style)
        self.boton_cloud.pack(fill="x", padx=12, pady=5)

        ctk.CTkButton(self.menu, text="🏠 Ejecutar HomeServe", command=self.ejecutar_homeserve, **menu_style).pack(fill="x", padx=14, pady=(8, 6))
        ctk.CTkButton(self.menu, text="🔄 Actualizar Gestor PRO", command=self.abrir_actualizador, **menu_style).pack(fill="x", padx=14, pady=(8, 6))
        # Botón Salir ligeramente más compacto para armonizar con el menú
        ctk.CTkButton(self.menu, text="❌ Salir", command=self.destroy, fg_color="#b44343", hover_color="#9b3535", height=52, corner_radius=14, font=("Arial", 15, "bold"), border_width=1, border_color="#7a2b2b").pack(side="bottom", fill="x", padx=14, pady=18)

        # ==========================
        # PANEL DERECHO (CONTENIDO)
        # ==========================
        self.contenido = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1218")
        self.contenido.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.frame_actual = None
        self.inicio()

    def restaurar_interfaz(self):
        """Método de instancia para restaurar la ventana de Gestor PRO limpia"""
        try:
            self.deiconify()
            self.state('normal')
            self.focus_force()
        except Exception as e:
            print(f"Error al restaurar interfaz: {e}")

    def pantalla_pequena(self):
        # Mantener un tamaño que garantice visibilidad de todos los botones del menú
        self.state('normal')
        # Usar el tamaño inicial de la ventana para evitar ocultar botones
        self.geometry("1100x760")

    def pantalla_completa(self):
        self.state('zoomed')

    def limpiar(self):
        if self.frame_actual is not None:
            self.frame_actual.destroy()

    def obtener_saludo(self):
        hora = int(time.strftime("%H"))
        if 6 <= hora < 12:
            return "¡Buenos días!"
        elif 12 <= hora < 20:
            return "¡Buenas tardes!"
        else:
            return "¡Buenas noches!"

    def inicio(self):
        self.pantalla_pequena()
        self.limpiar()
        self.frame_actual = ctk.CTkFrame(self.contenido, fg_color="#11181f")
        self.frame_actual.pack(fill="both", expand=True)

        panel = ctk.CTkFrame(self.frame_actual, fg_color="#101821", corner_radius=18, border_color="#2b3d4d", border_width=1)
        panel.pack(fill="both", expand=True, padx=0, pady=0)

        background = tk.Canvas(panel, bg="#101d2d", highlightthickness=0, bd=0)
        background.pack(fill="both", expand=True)

        def animar_fondo(offset=0):
            if not panel.winfo_exists():
                return
            w = max(1, background.winfo_width())
            h = max(1, background.winfo_height())
            background.delete("all")
            for i in range(-60, w + 120, 90):
                x0 = (i + offset) % (w + 120) - 60
                background.create_rectangle(x0, 0, x0 + 70, h, fill="#142a42", outline="", tags="bg")
            band_x = (offset * 2) % (w + 220) - 110
            background.create_rectangle(band_x, h * 0.14, band_x + 320, h * 0.86, fill="#173d64", stipple="gray50", outline="", tags="glow")
            background.create_rectangle(w * 0.38, h * 0.18, w * 0.62, h * 0.82, outline="#56c0ff", width=1, tags="pulse")
            background.lower("bg")
            self.after(40, lambda: animar_fondo((offset + 5) % (w + 200)))

        # Si hay GIF disponible, usa solo ese GIF como fondo (el primero que encuentre en assets/)
        gif_anim_started = False
        try:
            import glob
            assets_folder = os.path.join(BASE_DIR, "assets")
            gif_candidates = []
            if os.path.isdir(assets_folder):
                for ext in (".gif", ".GIF", ".gift", ".GIFT"):
                    gif_candidates.extend(glob.glob(os.path.join(assets_folder, f"*{ext}")))
            if gif_candidates:
                gif_path = sorted(gif_candidates)[0]
                gif_frames = []
                gif_durations = []
                for frame in ImageSequence.Iterator(Image.open(gif_path)):
                    gif_frames.append(frame.convert("RGBA"))
                    gif_durations.append(frame.info.get("duration", 100))
                if gif_frames:
                    self._gif_frames = gif_frames
                    self._gif_durations = gif_durations
                    self._gif_index = 0

                    gif_label = tk.Label(panel, bg="#101d2d", bd=0, highlightthickness=0)
                    gif_label.place(relx=0, rely=0, relwidth=1, relheight=1)

                    def mostrar_un_gif():
                        if not panel.winfo_exists() or not hasattr(self, "_gif_frames"):
                            return
                        idx = self._gif_index % len(self._gif_frames)
                        frame = self._gif_frames[idx].copy()
                        w = max(1, panel.winfo_width())
                        h = max(1, panel.winfo_height())
                        try:
                            frame = frame.resize((w, h), Image.LANCZOS)
                        except Exception:
                            frame = frame.resize((w, h))
                        photo = ImageTk.PhotoImage(frame)
                        gif_label.configure(image=photo)
                        gif_label.image = photo
                        self._gif_index += 1
                        panel.after(max(20, self._gif_durations[idx] if idx < len(self._gif_durations) else 100), mostrar_un_gif)

                    panel.bind("<Configure>", lambda e: (background.configure(width=e.width, height=e.height), mostrar_un_gif()))
                    mostrar_un_gif()
                    gif_anim_started = True
        except Exception:
            gif_anim_started = False

        if not gif_anim_started:
            panel.bind("<Configure>", lambda e: (background.configure(width=e.width, height=e.height), animar_fondo(0)))
            animar_fondo(0)

        clock_panel = ctk.CTkFrame(self.frame_actual, fg_color="#0b1621", corner_radius=26, border_color="#3a5e7c", border_width=1)
        clock_panel.place(relx=0.96, rely=0.10, anchor="ne")

        lbl_hora = ctk.CTkLabel(clock_panel, text="", font=("Arial", 25, "bold"), text_color="#f2f7ff")
        lbl_hora.pack(padx=20, pady=(12, 2))
        lbl_fecha = ctk.CTkLabel(clock_panel, text="", font=("Arial", 12), text_color="#b7c9d9")
        lbl_fecha.pack(padx=20, pady=(0, 12))

        def actualizar_reloj_loop():
            if lbl_hora.winfo_exists():
                lbl_hora.configure(text=time.strftime("%H:%M:%S"))
                lbl_fecha.configure(text=time.strftime("%d/%m/%Y"))
                self.after(1000, actualizar_reloj_loop)

        actualizar_reloj_loop()

        # sombra simulada detrás del panel central para efecto "premium"
        # CTkFrame requiere width/height en el constructor cuando se usa customtkinter en Windows; pasar aquí evita ValueError en .place()
        shadow = ctk.CTkFrame(self.frame_actual, fg_color="#05121a", corner_radius=30, border_width=0, width=460, height=300)
        # tamaño estimado para dar profundidad; se mantiene centrado y detrás del center_frame
        shadow.place(relx=0.52, rely=0.52, anchor="center")

        center_frame = ctk.CTkFrame(self.frame_actual, fg_color="transparent")
        center_frame.place(relx=0.52, rely=0.52, anchor="center")

        badge = ctk.CTkFrame(center_frame, fg_color="#0a1824", corner_radius=18, border_color="#4d7ca8", border_width=1)
        badge.pack(pady=(0, 10), padx=20)
        ctk.CTkLabel(badge, text="PANEL DE CONTROL", font=("Arial", 12, "bold"), text_color="#dfeeff").pack(padx=20, pady=(7, 6))

        content_panel = ctk.CTkFrame(center_frame, fg_color="#091923", corner_radius=28, border_color="#3f6d98", border_width=1)
        content_panel.pack(padx=12, pady=0)

        inner_panel = ctk.CTkFrame(content_panel, fg_color="#0b1a2a", corner_radius=22, border_color="#2f5376", border_width=1)
        inner_panel.pack(padx=28, pady=(16, 16))

        ctk.CTkLabel(inner_panel, text=self.obtener_saludo(), font=("Arial", 17, "italic"), text_color="#eaf4ff").pack(pady=(14, 4))
        ctk.CTkLabel(inner_panel, text="GESTOR PRO", font=("Arial", 40, "bold"), text_color="#f9fbff").pack(pady=(2, 6))
        ctk.CTkLabel(inner_panel, text="Selecciona un módulo\npara comenzar.", font=("Arial", 17), text_color="#edf5ff", justify="center").pack(pady=(2, 14), padx=24)

        # Asegurarse de que la sombra quede detrás (si el framework permite levantar elementos, se podría usar lower)
        try:
            shadow.lower()
        except Exception:
            pass

        lbl_version = ctk.CTkLabel(
            self.frame_actual,
            text=f"v{VERSION}" if not VERSION.startswith("v") else VERSION,
            font=("Arial", 11),
            text_color="#dfeaf7",
            fg_color="#101a29",
            corner_radius=12,
            border_color="#355c7d",
            border_width=1
        )
        lbl_version.place(relx=1.0, rely=1.0, anchor="se", x=-15, y=-10)

    def abrir_actualizador(self):
        from modules.actualizador import ActualizadorFrame
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = ActualizadorFrame(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def abrir_lector_codigos(self):
        from modules.Lector_de_codigos import Lector_de_codigos
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = Lector_de_codigos(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def abrir_verificador_pagos(self):
        from modules.VerificadorPagos import VerificadorPagosFrame
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = VerificadorPagosFrame(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def abrir_liquidaciones(self):
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = LiquidacionesFrame(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def abrir_presupuestos(self):
        from modules.presupuestos import AppPresupuestos
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = AppPresupuestos(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def iniciar_cloud(self):
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = ServidorLocalFrame(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def ir_a_railway(self):
        try:
            volver_a_railway()
            messagebox.showinfo("Railway", "El bot vuelve a funcionar desde Railway.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar con Railway: {e}")

    def ejecutar_homeserve(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("HomeServe")
        ventana.geometry("340x580")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.configure(fg_color="#101820")

        header = ctk.CTkFrame(ventana, fg_color="#121b29", corner_radius=18, border_color="#2d435d", border_width=1)
        header.pack(fill="x", padx=12, pady=(12, 10))

        ctk.CTkLabel(header, text="HomeServe", font=("Arial", 22, "bold"), text_color="#4ea3ff").pack(pady=(16, 6))
        ctk.CTkLabel(header, text="¿Qué deseas hacer?", font=("Arial", 13), text_color="#dfeaff").pack(pady=(0, 16))

        panel = ctk.CTkFrame(ventana, fg_color="#171f2a", corner_radius=16, border_color="#2d435d", border_width=1)
        panel.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        btn_style = dict(height=40, corner_radius=10, fg_color="#0f6cbd", hover_color="#0d5ea8", font=("Arial", 12, "bold"))
        ctk.CTkButton(panel, text="▶ Iniciar sesión", command=lambda: None, **btn_style).pack(fill="x", padx=16, pady=(18, 10))
        ctk.CTkButton(panel, text="🧭 Ejecutar bot", command=lambda: None, **btn_style).pack(fill="x", padx=16, pady=10)
        ctk.CTkButton(panel, text="📋 Ver servicios", command=lambda: None, **btn_style).pack(fill="x", padx=16, pady=10)
        ctk.CTkButton(panel, text="🛑 Detener", command=lambda: None, fg_color="#c2410c", hover_color="#9a3609", height=40, corner_radius=10, font=("Arial", 12, "bold")).pack(fill="x", padx=16, pady=(10, 18))

        app_main = self

        def cerrar_adb():
            """Cierra los procesos en segundo plano de ADB para evitar que queden colgados"""
            BASE_HOME = os.path.join(BASE_DIR, "Homeserve")
            ADB_EXE = os.path.join(BASE_HOME, "adb.exe")
            try:
                if os.path.exists(ADB_EXE):
                    subprocess.run([ADB_EXE, "kill-server"], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.run(["adb", "kill-server"], creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass

        def abrir_scrcpy():
            ventana.destroy()
            app_main.iconify()
            BASE_HOME = os.path.join(BASE_DIR, "Homeserve")
            SCRCPY = os.path.join(BASE_HOME, "scrcpy.exe")
            
            try:
                proceso = subprocess.Popen(SCRCPY)

                def esperar():
                    proceso.wait()
                    cerrar_adb()  # Limpia los procesos ADB al cerrar la ventana de scrcpy
                    app_main.after(0, lambda: app_main.restaurar_interfaz())

                threading.Thread(target=esperar, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir scrcpy: {e}")
                app_main.restaurar_interfaz()

        def ingresar_servicios():
            """Abre una subventana para escribir/pegar servicios y guardarlos en servicios.txt"""
            BASE_HOME = os.path.join(BASE_DIR, "Homeserve")
            ruta_servicios = os.path.join(BASE_HOME, "servicios.txt")
            
            v_servicios = ctk.CTkToplevel(ventana)
            v_servicios.title("Ingresar Servicios")
            v_servicios.geometry("320x420")
            v_servicios.resizable(False, False)
            v_servicios.grab_set()

            ctk.CTkLabel(v_servicios, text="Lista de Servicios", font=("Arial", 16, "bold")).pack(pady=(12, 2))
            ctk.CTkLabel(v_servicios, text="Ingresa un servicio por línea:", font=("Arial", 11), text_color="gray70").pack(pady=(0, 8))

            txt_servicios = ctk.CTkTextbox(v_servicios, width=280, height=270, font=("Consolas", 12))
            txt_servicios.pack(padx=15, pady=5)

            # Si el archivo existe, cargamos su contenido
            if os.path.exists(ruta_servicios):
                try:
                    with open(ruta_servicios, "r", encoding="utf-8") as f:
                        contenido = f.read()
                        txt_servicios.insert("1.0", contenido)
                except Exception as e:
                    print(f"Error al leer servicios.txt: {e}")

            def guardar():
                texto_raw = txt_servicios.get("1.0", "end-1c")
                lineas = [linea.strip() for linea in texto_raw.splitlines() if linea.strip()]
                
                try:
                    os.makedirs(BASE_HOME, exist_ok=True)
                    with open(ruta_servicios, "w", encoding="utf-8") as f:
                        f.write("\n".join(lineas) + ("\n" if lineas else ""))
                    
                    messagebox.showinfo("Éxito", f"Se han guardado {len(lineas)} servicio(s) correctamente.")
                    v_servicios.destroy()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

            ctk.CTkButton(v_servicios, text="💾 Guardar Servicios", command=guardar, height=35, fg_color="#2b8a3e", hover_color="#237032").pack(pady=12)

        def ejecutar_bot():
            ventana.withdraw()
            app_main.iconify()

            def ejecutar():
                import ctypes

                # 1. Creamos la ventana de consola limpia
                try:
                    ctypes.windll.kernel32.AllocConsole()
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8")
                    print("==================================================", flush=True)
                    print("        CONSOLA DE LOGS - BOT HOMESERVE", flush=True)
                    print("==================================================", flush=True)
                except Exception:
                    pass

                try:
                    # 2. Ejecutamos el bot
                    bot.iniciar_homeserve()
                except Exception as err:
                    print(f"\n[!] Bot finalizado/detenido: {err}", flush=True)
                finally:
                    # 3. Forzamos el cierre y ocultación inmediata de la consola
                    try:
                        # Obtenemos el identificador de la ventana de consola actual
                        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                        if hwnd != 0:
                            # Ocultamos la ventana en pantalla inmediatamente
                            ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
                        
                        sys.stdout.close()
                        sys.stderr.close()
                        sys.stdout = sys.__stdout__
                        sys.stderr = sys.__stderr__
                        ctypes.windll.kernel32.FreeConsole()
                    except Exception:
                        pass
                    
                    cerrar_adb()  # Limpia los procesos ADB
                    app_main.after(0, lambda: app_main.restaurar_interfaz())
                    app_main.after(0, lambda: ventana.deiconify() if ventana.winfo_exists() else None)

            threading.Thread(target=ejecutar, daemon=True).start()

        def pausar_bot():
            bot.BOT_PAUSADO = True

        def continuar_bot():
            bot.BOT_PAUSADO = False

        def detener_bot():
            bot.BOT_DETENIDO = True

        # --- OPCIONES SUPERIORES ---
        ctk.CTkButton(ventana, text="📱 Abrir scrcpy", command=abrir_scrcpy, height=35).pack(fill="x", padx=25, pady=4)
        ctk.CTkButton(ventana, text="📝 Ingresar servicios", command=ingresar_servicios, height=35, fg_color="#1f6aa5").pack(fill="x", padx=25, pady=4)
        ctk.CTkButton(ventana, text="🤖 Ejecutar BOT", command=ejecutar_bot, height=35, fg_color="#2b8a3e", hover_color="#237032").pack(fill="x", padx=25, pady=4)

        # --- SEPARADOR VISUAL Y ACCIONES DE CONTROL ---
        ctk.CTkFrame(ventana, height=2, fg_color="gray30").pack(fill="x", padx=25, pady=10)

        ctk.CTkButton(ventana, text="⏸ Pausar BOT", command=pausar_bot, height=35, fg_color="gray30", hover_color="gray40").pack(fill="x", padx=25, pady=4)
        ctk.CTkButton(ventana, text="▶ Continuar BOT", command=continuar_bot, height=35, fg_color="gray30", hover_color="gray40").pack(fill="x", padx=25, pady=4)
        ctk.CTkButton(ventana, text="⛔ Detener BOT", command=detener_bot, height=35, fg_color="#c92a2a", hover_color="#a61e1e").pack(fill="x", padx=25, pady=4)

        ctk.CTkButton(ventana, text="Cancelar", fg_color="gray20", hover_color="gray30", command=ventana.destroy, height=35).pack(fill="x", padx=25, pady=(15, 10))


if __name__ == "__main__":
    app = GestorPro()
    app.mainloop()