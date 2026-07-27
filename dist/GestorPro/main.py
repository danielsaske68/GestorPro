import customtkinter as ctk
from PIL import Image
import time
import json
import sys
import os

# --- AJUSTE DE RUTA PARA SCRIPT O .EXE ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from modules.liquidaciones import LiquidacionesFrame
from tkinter import messagebox
import threading
import subprocess

from cloud.railway_app import iniciar_servidor
from cloud.railway_app import loop
from cloud.railway_app import monitor_webhook

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class GestorPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GESTOR PRO")
        # Tamaño inicial pequeño
        self.geometry("400x500") 
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ... (resto de tu código de botones del menú)
        # ==========================
        # MENÚ IZQUIERDO
        # ==========================
        self.menu = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu.grid(row=0, column=0, sticky="ns")
        try:
            RUTA_LOGO = os.path.join(
                BASE_DIR,
                "assets",
                "logo.png"
            )
            logo = ctk.CTkImage(
                light_image=Image.open(RUTA_LOGO),
                dark_image=Image.open(RUTA_LOGO),
                size=(120, 120)
            )

            ctk.CTkLabel(
                self.menu,
                image=logo,
                text=""
            ).pack(pady=20)

        except:
            ctk.CTkLabel(
                self.menu,
                text="GESTOR PRO",
                font=("Arial", 24, "bold")
            ).pack(pady=30)

        ctk.CTkButton(
            self.menu,
            text="🏠 Inicio",
            command=self.inicio
        ).pack(fill="x", padx=15, pady=5)

        ctk.CTkButton(
            self.menu,
            text="💰 Liquidaciones",
            command=self.abrir_liquidaciones
        ).pack(fill="x", padx=15, pady=5)

        ctk.CTkButton(
            self.menu,
            text="🛠 Lector de códigos", 
            command=self.abrir_lector_codigos
        ).pack(fill="x", padx=15, pady=5)

        ctk.CTkButton(
            self.menu,
            text="📝 Presupuestos",
            command=self.abrir_presupuestos
        ).pack(fill="x", padx=15, pady=5)

        self.boton_cloud = ctk.CTkButton(
            self.menu,
            text="☁️ Servidor Local",
            command=self.iniciar_cloud
        )
        self.boton_cloud.pack(fill="x", padx=15, pady=5)


        ctk.CTkButton(
            self.menu,
            text="🏠 Ejecutar HomeServe",
            command=self.ejecutar_homeserve
        ).pack(fill="x", padx=15, pady=5)


        ctk.CTkButton(
            self.menu,
            text="🔄 Actualizar Gestor PRO",
            command=self.abrir_actualizador
        ).pack(
            fill="x",
            padx=15,
            pady=5
        )

        ctk.CTkButton(
            self.menu,
            text="❌ Salir",
            command=self.destroy
        ).pack(side="bottom", fill="x", padx=15, pady=20)

        # ==========================
        # PANEL DERECHO
        # ==========================
        self.contenido = ctk.CTkFrame(self, corner_radius=0)
        self.contenido.grid(row=0, column=1, sticky="nsew")
        self.frame_actual = None
        self.inicio()

    # ==========================
    # NUEVAS FUNCIONES DE CONTROL
    # ==========================
    def pantalla_pequena(self):
        self.state('normal')
        self.geometry("400x500")
        
    def pantalla_completa(self):
        self.state('zoomed')

    # ==========================
    # CAMBIAR MÓDULO
    # ==========================
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

    def abrir_actualizador(self):
        from modules.actualizador import ActualizadorFrame
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = ActualizadorFrame(
            self.contenido
        )
        self.frame_actual.pack(
            fill="both",
            expand=True
        )

    def inicio(self):
        self.pantalla_pequena()
        self.limpiar()
        self.frame_actual = ctk.CTkFrame(self.contenido, fg_color="transparent")
        self.frame_actual.pack(fill="both", expand=True)

        # --- RELOJ ---
        lbl_hora = ctk.CTkLabel(self.frame_actual, text="", font=("Arial", 26, "bold"), text_color="#ffffff")
        lbl_hora.place(relx=0.95, rely=0.05, anchor="ne")
        lbl_fecha = ctk.CTkLabel(self.frame_actual, text="", font=("Arial", 14), text_color="#aaaaaa")
        lbl_fecha.place(relx=0.95, rely=0.13, anchor="ne")
        
        def actualizar_reloj_loop():
            # VERIFICACIÓN DE SEGURIDAD
            if lbl_hora.winfo_exists(): 
                lbl_hora.configure(text=time.strftime("%H:%M:%S"))
                lbl_fecha.configure(text=time.strftime("%d/%m/%Y"))
                self.after(1000, actualizar_reloj_loop)
        actualizar_reloj_loop()
        
        # ... resto de tu código de inicio

        # --- CONTENIDO CENTRAL ---
        center_frame = ctk.CTkFrame(self.frame_actual, fg_color="transparent")
        center_frame.place(relx=0.52, rely=0.50, anchor="center")
        ctk.CTkLabel(center_frame, text=self.obtener_saludo(), font=("Arial", 16, "italic"), text_color="gray").pack(pady=5)
        
        ctk.CTkLabel(
            center_frame,
            text="GESTOR PRO",
            font=("Arial", 32, "bold"), 
            text_color=("#0056b3", "#3b8ed0")
        ).pack(pady=5)

        ctk.CTkLabel(
            center_frame,
            text="Selecciona un módulo\npara comenzar.",
            font=("Arial", 14),
            text_color="white",
            justify="center"
        ).pack(pady=5)

    def abrir_lector_codigos(self):
        self.pantalla_completa()
        self.limpiar()
        from modules.Lector_de_codigos import Lector_de_codigos 
        self.frame_actual = Lector_de_codigos(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def abrir_liquidaciones(self):
        self.pantalla_completa()
        self.limpiar()
        self.frame_actual = LiquidacionesFrame(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def abrir_presupuestos(self):
        self.pantalla_completa()
        self.limpiar()
        from modules.presupuestos import AppPresupuestos 
        self.frame_actual = AppPresupuestos(self.contenido)
        self.frame_actual.pack(fill="both", expand=True)

    def iniciar_cloud(self):
        self.pantalla_completa()
        self.limpiar()
        from modules.servidor_local import ServidorLocalFrame
        self.frame_actual=ServidorLocalFrame(
            self.contenido
        )
        self.frame_actual.pack(
            fill="both",
            expand=True
        )

    def ir_a_railway(self):
        volver_a_railway()
        messagebox.showinfo(
            "Railway",
            "El bot vuelve a funcionar desde Railway."
        )

    def ejecutar_homeserve(self):

        ventana = ctk.CTkToplevel(self)
        ventana.title("HomeServe")
        ventana.geometry("320x350")
        ventana.resizable(False, False)
        ventana.grab_set()

        ctk.CTkLabel(
            ventana,
            text="HomeServe",
            font=("Arial", 22, "bold")
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            ventana,
            text="¿Qué deseas hacer?",
            font=("Arial", 14)
        ).pack(pady=(0, 20))

        def abrir_scrcpy():
            ventana.destroy()
            self.iconify()

            BASE_HOME = os.path.join(
                BASE_DIR,
                "Homeserve"
            )

            SCRCPY = os.path.join(
                BASE_HOME,
                "scrcpy.exe"
            )
            proceso = subprocess.Popen(SCRCPY)

            def esperar():
                proceso.wait()
                self.after(
                    0,
                    self.deiconify
                )

            threading.Thread(
                target=esperar,
                daemon=True
            ).start()

        def ejecutar_bot():

            ventana.withdraw()

            self.iconify()

            import modules.homeserve as bot

            def ejecutar():

                bot.iniciar_homeserve()

                self.after(0, self.deiconify)
                self.after(0, ventana.deiconify)

            threading.Thread(
                target=ejecutar,
                daemon=True
            ).start()

        ctk.CTkButton(
            ventana,
            text="📱 Abrir scrcpy",
            command=abrir_scrcpy,
            height=40
        ).pack(fill="x", padx=25, pady=5)

        ctk.CTkButton(
            ventana,
            text="🤖 Ejecutar BOT",
            command=ejecutar_bot,
            height=40
        ).pack(fill="x", padx=25, pady=5)

        ctk.CTkButton(
            ventana,
            text="Cancelar",
            fg_color="gray40",
            command=ventana.destroy
        ).pack(fill="x", padx=25, pady=(15,10))

        def pausar_bot():
            import modules.homeserve as bot
            bot.BOT_PAUSADO = True



        def continuar_bot():
            import modules.homeserve as bot
            bot.BOT_PAUSADO = False



        def detener_bot():
            import modules.homeserve as bot
            bot.BOT_DETENIDO = True

        ctk.CTkButton(
            ventana,
            text="⏸ Pausar BOT",
            command=pausar_bot,
            height=35
        ).pack(fill="x", padx=25, pady=5)


        ctk.CTkButton(
            ventana,
            text="▶ Continuar BOT",
            command=continuar_bot,
            height=35
        ).pack(fill="x", padx=25, pady=5)


        ctk.CTkButton(
            ventana,
            text="⛔ Detener BOT",
            command=detener_bot,
            height=35,
            fg_color="red"
        ).pack(fill="x", padx=25, pady=5)

if __name__ == "__main__":
    app = GestorPro()
    app.mainloop()