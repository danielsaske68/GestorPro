import os
import sys
import time
import json
import threading
import subprocess
from PIL import Image
import customtkinter as ctk
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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class GestorPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 📍 Título de la pestaña/ventana con la versión leída del JSON
        self.title(f"GESTOR PRO {VERSION}")
        self.geometry("400x500")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================
        # MENÚ IZQUIERDO
        # ==========================
        self.menu = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu.grid(row=0, column=0, sticky="ns")

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
        ctk.CTkButton(self.menu, text="🏠 Inicio", command=self.inicio).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(self.menu, text="💰 Liquidaciones", command=self.abrir_liquidaciones).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(self.menu, text="🛠 Lector de códigos", command=self.abrir_lector_codigos).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(self.menu, text="📝 Presupuestos", command=self.abrir_presupuestos).pack(fill="x", padx=15, pady=5)

        self.boton_cloud = ctk.CTkButton(self.menu, text="☁️ Servidor Local", command=self.iniciar_cloud)
        self.boton_cloud.pack(fill="x", padx=15, pady=5)

        ctk.CTkButton(self.menu, text="🏠 Ejecutar HomeServe", command=self.ejecutar_homeserve).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(self.menu, text="🔄 Actualizar Gestor PRO", command=self.abrir_actualizador).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(self.menu, text="❌ Salir", command=self.destroy).pack(side="bottom", fill="x", padx=15, pady=20)

        # ==========================
        # PANEL DERECHO (CONTENIDO)
        # ==========================
        self.contenido = ctk.CTkFrame(self, corner_radius=0)
        self.contenido.grid(row=0, column=1, sticky="nsew")
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
        self.state('normal')
        self.geometry("400x500")

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
        self.frame_actual = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self.frame_actual.pack(fill="both", expand=True)

        lbl_hora = ctk.CTkLabel(self.frame_actual, text="", font=("Arial", 26, "bold"), text_color="#ffffff")
        lbl_hora.place(relx=0.95, rely=0.05, anchor="ne")
        lbl_fecha = ctk.CTkLabel(self.frame_actual, text="", font=("Arial", 14), text_color="#aaaaaa")
        lbl_fecha.place(relx=0.95, rely=0.13, anchor="ne")

        def actualizar_reloj_loop():
            if lbl_hora.winfo_exists():
                lbl_hora.configure(text=time.strftime("%H:%M:%S"))
                lbl_fecha.configure(text=time.strftime("%d/%m/%Y"))
                self.after(1000, actualizar_reloj_loop)

        actualizar_reloj_loop()

        center_frame = ctk.CTkFrame(self.frame_actual, fg_color="transparent")
        center_frame.place(relx=0.52, rely=0.50, anchor="center")
        ctk.CTkLabel(center_frame, text=self.obtener_saludo(), font=("Arial", 16, "italic"), text_color="gray").pack(pady=5)
        ctk.CTkLabel(center_frame, text="GESTOR PRO", font=("Arial", 32, "bold"), text_color=("#0056b3", "#3b8ed0")).pack(pady=5)
        ctk.CTkLabel(center_frame, text="Selecciona un módulo\npara comenzar.", font=("Arial", 14), text_color="white", justify="center").pack(pady=5)

        # 📍 Número de versión limpio abajo a la derecha
        lbl_version = ctk.CTkLabel(
            self.frame_actual,
            text=f"v{VERSION}" if not VERSION.startswith("v") else VERSION,
            font=("Arial", 11),
            text_color="gray50"
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

        ctk.CTkLabel(ventana, text="HomeServe", font=("Arial", 20, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(ventana, text="¿Qué deseas hacer?", font=("Arial", 13)).pack(pady=(0, 10))

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