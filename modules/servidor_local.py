import customtkinter as ctk
import threading
import subprocess
import time

from cloud.railway_app import (
    iniciar_servidor,
    loop,
    monitor_webhook,
    volver_a_railway,
    obtener_usuarios
)
from cloud.control import estado
import cloud.control as control


class ServidorLocalFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        titulo = ctk.CTkLabel(
            self,
            text="☁️ SERVIDOR LOCAL",
            font=("Arial",28,"bold")
        )
        titulo.pack(pady=20)

        self.estado_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.estado_frame.pack(pady=10)


        self.luz_estado = ctk.CTkLabel(
            self.estado_frame,
            text="●",
            font=("Arial",30),
            text_color="red"
        )

        self.luz_estado.pack(
            side="left",
            padx=10
        )


        self.estado = ctk.CTkLabel(
            self.estado_frame,
            text="Estado general: Apagado",
            font=("Arial",18),
            text_color="white"
        )

        self.estado.pack(
            side="left"
        )

        # ==========================
        # PILOTOS DE ESTADO
        # ==========================

        def crear_piloto(parent, texto):
            frame = ctk.CTkFrame(parent, fg_color="transparent")

            luz = ctk.CTkLabel(
                frame,
                text="●",
                font=("Arial", 30),
                text_color="gray"
            )
            luz.pack(side="left", padx=10)

            label = ctk.CTkLabel(
                frame,
                text=texto,
                font=("Arial",18)
            )
            label.pack(side="left")

            frame.pack(pady=5)

            return luz, label


        self.luz_flask, self.piloto_flask = crear_piloto(
            self,
            "Servidor Flask"
        )


        self.luz_ngrok, self.piloto_ngrok = crear_piloto(
            self,
            "Ngrok"
        )


        self.luz_telegram, self.piloto_telegram = crear_piloto(
            self,
            "Telegram Local"
        )


        self.luz_railway, self.piloto_railway = crear_piloto(
            self,
            "Railway"
        )

        self.luz_railway.configure(
            text_color="green"
        )

        self.btn_iniciar = ctk.CTkButton(
            self,
            text="▶ Iniciar servidor",
            command=self.iniciar
        )

        self.btn_iniciar.pack(pady=10)



        self.btn_railway = ctk.CTkButton(
            self,
            text="☁️ Volver a Railway",
            command=self.railway
        )

        self.btn_railway.pack(pady=10)



        self.btn_detener = ctk.CTkButton(
            self,
            text="⛔ Detener",
            command=self.detener
        )

        self.btn_detener.pack(pady=10)


        self.actualizar_pilotos()

        


    def iniciar(self):

        if control.servidor_activo:
            return

        control.servidor_activo = True
        estado["servidor"] = True


        control.ngrok_proceso = subprocess.Popen(
            [
                "ngrok",
                "http",
                "10000"
            ],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        estado["ngrok"] = True
        estado["telegram"] = True
        estado["railway"] = False

        self.luz_railway.configure(
            text_color="red"
        )

        self.piloto_railway.configure(
            text="Railway desconectado"
        )

        def iniciar_loop_local():

            from cloud.railway_app import homeserve

            print("LOGIN INICIAL LOCAL")

            resultado = homeserve.login()

            print("LOGIN RESULTADO:", resultado)

            loop()


        threading.Thread(
            target=iniciar_loop_local,
            daemon=True
        ).start()

        threading.Thread(
            target=iniciar_servidor,
            daemon=True
        ).start()


        threading.Thread(
            target=monitor_webhook,
            daemon=True
        ).start()


        self.actualizar_pilotos()



    def actualizar_pilotos(self):

        if estado["servidor"]:

            self.luz_flask.configure(
                text_color="green"
            )

            self.piloto_flask.configure(
                text="Servidor Flask activo"
            )

            self.luz_ngrok.configure(
                text_color="green"
            )

            self.piloto_ngrok.configure(
                text="Ngrok conectado"
            )

            self.luz_telegram.configure(
                text_color="green"
            )

            self.piloto_telegram.configure(
                text="Telegram Local activo"
            )

            self.luz_estado.configure(
                text_color="green"
            )

            self.estado.configure(
                text="Estado general: Servidor Local funcionando"
            )

        else:

            self.luz_flask.configure(
                text_color="red"
            )

            self.piloto_flask.configure(
                text="Servidor Flask apagado"
            )

            self.luz_ngrok.configure(
                text_color="red"
            )

            self.piloto_ngrok.configure(
                text="Ngrok cerrado"
            )

            self.luz_telegram.configure(
                text_color="red"
            
            )
            self.piloto_telegram.configure(
                text="Telegram sin conexión"
            )


            self.luz_estado.configure(
                text_color="red"
            )

            self.estado.configure(
                text="Estado general: Apagado"
            )


        self.after(
            1000,
            self.actualizar_pilotos
        )


    def railway(self):

        volver_a_railway()

        estado["railway"] = True
        estado["telegram"] = False

        control.servidor_activo = False

        self.luz_railway.configure(
            text_color="green"
        )

        self.piloto_railway.configure(
            text="Railway activo"
        )

        self.actualizar_pilotos()


    def detener(self):

        if control.ngrok_proceso:
            control.ngrok_proceso.kill()
            control.ngrok_proceso = None

        control.servidor_activo = False

        estado["servidor"] = False
        estado["ngrok"] = False
        estado["telegram"] = False
        estado["railway"] = True

        self.actualizar_pilotos()