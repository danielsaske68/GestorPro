import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import threading
import requests
import os
import re
import time
from bs4 import BeautifulSoup
from PIL import Image

# =========================================================
# CONFIGURACIÓN
# =========================================================
USUARIO = "16205"
PASSWORD = "Aventura69."
BASE_URL = "https://www.clientes.homeserve.es/cgi-bin/fccgi.exe?w3exec="
THEME_COLOR = "#0056b3" 


# --- NUEVO: DEFINIR CARPETA DE DATOS ---
# BASE_DIR = carpeta raíz del programa (donde está main.py / el .exe),
# NO el directorio de trabajo actual. Así funciona igual en script y en .exe.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_DATOS = os.path.join(BASE_DIR, "datos_lector")
if not os.path.exists(CARPETA_DATOS):
    os.makedirs(CARPETA_DATOS)


# =========================================================
# APP
# =========================================================
class Lector_de_codigos(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        # ESTRUCTURA
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.parent = parent

        # Sesión HTTP
        self.session = requests.Session()

        

        # PANEL IZQUIERDO
        self.left_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="#1e1e1e")
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # LOGO
        try:
            RUTA_LOGO = os.path.join(BASE_DIR, "assets", "logo.png")
            img = ctk.CTkImage(light_image=Image.open(RUTA_LOGO), dark_image=Image.open(RUTA_LOGO), size=(150, 150))
            ctk.CTkLabel(self.left_frame, image=img, text="").pack(pady=20)
        except:
            ctk.CTkLabel(self.left_frame, text="LOGO", font=("Arial", 20, "bold")).pack(pady=40)

        # BOTONES
        btn_config = {"width": 200, "height": 40, "corner_radius": 8, "fg_color": THEME_COLOR}
        ctk.CTkButton(self.left_frame, text="1. INICIAR SESIÓN", command=self.login, **btn_config).pack(pady=10)
        ctk.CTkButton(self.left_frame, text="2. EXTRAER LISTA", command=lambda: threading.Thread(target=self.listar).start(), **btn_config).pack(pady=10)
        ctk.CTkButton(self.left_frame, text="3. ANALIZAR PENDIENTES", command=lambda: threading.Thread(target=self.pendientes).start(), **btn_config).pack(pady=10)
        ctk.CTkButton(self.left_frame, text="4. LIMPIEZA MASIVA", command=lambda: threading.Thread(target=self.limpiar).start(), **btn_config).pack(pady=10)
        
        # NUEVO BOTÓN PARA IR A LA CARPETA
        ctk.CTkButton(
            self.left_frame, 
            text="📂 Ir a carpeta datos", 
            command=self.abrir_carpeta,
            fg_color="#444444", # Un color distinto para que resalte menos que los de acción
            height=40
        ).pack(pady=20)

        # PANEL DERECHO
        self.right_frame = ctk.CTkFrame(self, corner_radius=15)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # TABLA ESTILIZADA
        style = ttk.Style()
        style.theme_use("clam")

        # Tamaño letras de las filas (ID y ESTADO)
        style.configure(
            "Treeview",
            background="#2a2a2a",
            foreground="white",
            fieldbackground="#2a2a2a",
            borderwidth=0,
            font=("Arial", 16)
        )

        # Tamaño letras de los títulos
        style.configure(
            "Treeview.Heading",
            background=THEME_COLOR,
            foreground="white",
            relief="flat",
            font=("Arial", 16, "bold")
        )

        # Altura de cada fila
        style.configure(
            "Treeview",
            rowheight=35
        )
        
        self.tree = ttk.Treeview(self.right_frame, columns=("id", "estado"), show="headings")
        self.tree.heading("id", text="ID REPARACIÓN")
        self.tree.heading("estado", text="ESTADO")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # LOG
        self.log = ctk.CTkTextbox(self.right_frame, height=120, corner_radius=8, fg_color="#1a1a1a")
        self.log.pack(fill="x", padx=10, pady=10)

    # --- FUNCIONES ---

    def write_log(self, msg):
        self.log.insert("end", f"{msg}\n")
        self.log.see("end")

    def login(self):
        try:
            self.write_log("🔐 Iniciando sesión...")
            self.session.get(BASE_URL + "PROF_PASS")
            res = self.session.post(BASE_URL + "PROF_PASS", data={"CODIGO": USUARIO, "PASSW": PASSWORD, "BTN": "Aceptar"})
            if res.status_code == 200: self.write_log("✅ Sesión iniciada.")
            else: self.write_log("❌ Error login.")
        except Exception as e: self.write_log(f"❌ Error: {e}")

    def listar(self):
        try:
            res = self.session.get(BASE_URL + "recibe_recados&servicio=urgentes")
            servicios = sorted(list(set(re.findall(r"servicio=(\d{6,10})", res.text))))
            self.tree.delete(*self.tree.get_children())
            for s in servicios: self.tree.insert("", "end", values=(s, "CARGADO"))
            with open(os.path.join(CARPETA_DATOS, "pendientes_albaran.txt"), "w", encoding="utf-8") as f: f.write("\n".join(servicios))
            self.write_log(f"✅ Cargados {len(servicios)} servicios.")
        except Exception as e: self.write_log(f"❌ Error listando: {e}")

    def pendientes(self):
        self.write_log("🔍 Analizando estados específicos...")
        self.tree.delete(*self.tree.get_children())
        pendientes_encontrados = [] # Lista para guardar los que fallan
        
        try:
            with open(os.path.join(CARPETA_DATOS, "pendientes_albaran.txt"), "r", encoding="utf-8") as f:
                numeros = [x.strip() for x in f.readlines() if x.strip()]
        except: return

        for num in numeros:
            self.session.post(BASE_URL + "prof_verdatos", data={"SERVICIO": num, "BTNBUSCAR": "Localizar Servicio."})
            detalle = self.session.get(f"{BASE_URL}ver_servicioencurso&Servicio={num}&Pag=1")
            soup = BeautifulSoup(detalle.text, "html.parser")
            
            encontrado = False
            tags = soup.find_all("font")
            for t in tags:
                texto = t.get_text(strip=True).upper()
                if "PENDIENTE DE RECIBIR ALBARÁN" in texto:
                    encontrado = True
                    break
            
            estado = "PENDIENTE ALBARÁN" if encontrado else "OK"
            if encontrado: pendientes_encontrados.append(num) # Guardamos en la lista
            
            self.tree.insert("", "end", values=(num, estado))
            self.write_log(f"{'⚠️' if encontrado else '✅'} {num}: {estado}")
            time.sleep(0.8)
        
        # GUARDAR TXT APARTE
        with open(os.path.join(CARPETA_DATOS, "pendientes_reporte.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(pendientes_encontrados))
            
        self.write_log(f"💾 Reporte guardado en 'pendientes_reporte.txt'")
        self.write_log("🎉 Análisis finalizado.")

    def limpiar(self):
        try:
            res = self.session.get(BASE_URL + "recibe_recados&servicio=urgentes")
            soup = BeautifulSoup(res.text, "html.parser")
            links = [a['href'] for a in soup.find_all("a", href=True) if "servicio=" in a['href']]
            for link in links:
                self.session.get(link)
                time.sleep(0.5)
            self.write_log("🎉 Limpieza finalizada.")
        except Exception as e: self.write_log(f"❌ Error limpieza: {e}")


    def abrir_carpeta(self):
        # Abre la carpeta 'datos_lector' según el sistema operativo
        path = os.path.realpath(CARPETA_DATOS)
        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.uname().sysname == 'Darwin':  # macOS
            import subprocess
            subprocess.call(["open", path])
        else:  # Linux
            import subprocess
            subprocess.call(["xdg-open", path]) 
     