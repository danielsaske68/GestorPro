import os
import sys
import subprocess
from datetime import datetime
import fitz  # PyMuPDF: pip install PyMuPDF
import customtkinter as ctk
from tkinter import filedialog, messagebox

def ruta_app(carpeta, archivo=None):
    base = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
    ruta = os.path.join(base, carpeta)
    if archivo:
        ruta = os.path.join(ruta, archivo)
    return ruta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_RESULTADOS = ruta_app("resultados_pagos")
os.makedirs(CARPETA_RESULTADOS, exist_ok=True)

class VerificadorPagosFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Título del módulo
        titulo = ctk.CTkLabel(self, text="🔍 Verificador de Pagos por PDF", font=("Arial", 22, "bold"))
        titulo.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Controles superiores (Selección de PDF)
        controles_frame = ctk.CTkFrame(self, fg_color="transparent")
        controles_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        controles_frame.grid_columnconfigure(1, weight=1)

        self.btn_pdf = ctk.CTkButton(controles_frame, text="📄 Seleccionar PDF de Liquidación", command=self.seleccionar_pdf, fg_color="#1f6aa5", height=35)
        self.btn_pdf.grid(row=0, column=0, padx=(0, 10), pady=5)

        self.lbl_pdf_path = ctk.CTkLabel(controles_frame, text="Ningún PDF seleccionado", text_color="gray70")
        self.lbl_pdf_path.grid(row=0, column=1, sticky="w", pady=5)

        # Cuerpo principal (Entrada y Resultados)
        cuerpo_frame = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        cuerpo_frame.grid_columnconfigure(0, weight=1)
        cuerpo_frame.grid_columnconfigure(1, weight=1)
        cuerpo_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(cuerpo_frame, text="Códigos a verificar (uno por línea):", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkLabel(cuerpo_frame, text="Resultados de la verificación:", font=("Arial", 14, "bold")).grid(row=0, column=1, sticky="w", padx=(15, 0), pady=5)

        # Textbox de códigos con placeholder dinámico
        self.txt_codigos = ctk.CTkTextbox(cuerpo_frame, font=("Consolas", 12))
        self.txt_codigos.grid(row=1, column=0, sticky="nsew", pady=5)
        
        self.placeholder_codigos = "INSERTE NUEVOS SERVICIOS PARA REVISAR"
        self.txt_codigos.insert("1.0", self.placeholder_codigos)
        self.txt_codigos.configure(text_color="gray")
        
        self.txt_codigos.bind("<FocusIn>", self.on_focus_in_codigos)
        self.txt_codigos.bind("<FocusOut>", self.on_focus_out_codigos)

        # Textbox de resultados con placeholder dinámico
        self.txt_resultados = ctk.CTkTextbox(cuerpo_frame, font=("Consolas", 12))
        self.txt_resultados.grid(row=1, column=1, sticky="nsew", padx=(15, 0), pady=5)
        
        self.placeholder_resultados = "Resultado una vez termine ya"
        self.txt_resultados.insert("1.0", self.placeholder_resultados)
        self.txt_resultados.configure(text_color="gray", state="disabled")

        # Frame inferior para botones de acción
        acciones_frame = ctk.CTkFrame(self, fg_color="transparent")
        acciones_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        acciones_frame.grid_columnconfigure(0, weight=1)
        acciones_frame.grid_columnconfigure(1, weight=1)

        # Botón principal de ejecución
        btn_verificar = ctk.CTkButton(acciones_frame, text="🚀 Verificar y Generar TXT Separado", command=self.ejecutar_verificacion, height=42, fg_color="#2b8a3e", hover_color="#237032", font=("Arial", 14, "bold"))
        btn_verificar.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        # Botón para abrir la carpeta interna de resultados
        self.btn_abrir_carpeta = ctk.CTkButton(acciones_frame, text="📂 Abrir Carpeta de Resultados", command=self.abrir_carpeta_destino, height=42, fg_color="#343a40", hover_color="#495057", font=("Arial", 14, "bold"), state="disabled")
        self.btn_abrir_carpeta.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        self.ruta_pdf_seleccionado = ""
        self.ultima_ruta_salida = ""
        self.es_placeholder_activo = True

    def on_focus_in_codigos(self, event):
        if self.es_placeholder_activo:
            self.txt_codigos.delete("1.0", "end")
            self.txt_codigos.configure(text_color=("black", "white")) # Se adapta a modo claro/oscuro de CTk
            self.es_placeholder_activo = False

    def on_focus_out_codigos(self, event):
        contenido = self.txt_codigos.get("1.0", "end-1c").strip()
        if not contenido:
            self.es_placeholder_activo = True
            self.txt_codigos.delete("1.0", "end")
            self.txt_codigos.insert("1.0", self.placeholder_codigos)
            self.txt_codigos.configure(text_color="gray")

    def seleccionar_pdf(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo PDF de liquidación",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )
        if archivo:
            self.ruta_pdf_seleccionado = archivo
            self.lbl_pdf_path.configure(text=os.path.basename(archivo), text_color="#3b8ed0")

    def ejecutar_verificacion(self):
        if not self.ruta_pdf_seleccionado or not os.path.exists(self.ruta_pdf_seleccionado):
            messagebox.showwarning("Advertencia", "Selecciona un archivo PDF válido primero.")
            return

        if self.es_placeholder_activo:
            messagebox.showwarning("Advertencia", "Ingresa al menos un código válido para verificar.")
            return

        raw_text_codigos = self.txt_codigos.get("1.0", "end-1c")
        lista_codigos = [c.strip() for c in raw_text_codigos.splitlines() if c.strip() and c.strip() != self.placeholder_codigos]

        if not lista_codigos:
            messagebox.showwarning("Advertencia", "Ingresa al menos un código para verificar.")
            return

        try:
            doc = fitz.open(self.ruta_pdf_seleccionado)
            texto_pdf = ""
            for pagina in doc:
                texto_pdf += pagina.get_text()

            pagados = []
            no_pagados = []

            for codigo in lista_codigos:
                if codigo in texto_pdf:
                    pagados.append(codigo)
                else:
                    no_pagados.append(codigo)

            os.makedirs(CARPETA_RESULTADOS, exist_ok=True)

            # Generación de nomenclatura correlativa por fecha (ej: 05/Agost_001)
            fecha_actual = datetime.now()
            meses_es = {
                1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
                7: "Jul", 8: "Agost", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
            }
            dia_str = fecha_actual.strftime("%d")
            mes_str = meses_es.get(fecha_actual.month, fecha_actual.strftime("%b"))
            prefijo_fecha = f"{dia_str}_{mes_str}"

            # Buscar cuántos archivos existen hoy para calcular el correlativo (001, 002...)
            archivos_existentes = os.listdir(CARPETA_RESULTADOS)
            contador = 1
            for archivo_ex in archivos_existentes:
                if archivo_ex.startswith(prefijo_fecha) and archivo_ex.endswith(".txt"):
                    contador += 1

            sufijo_correlativo = f"{contador:03d}"
            nombre_archivo_salida = f"{prefijo_fecha}_{sufijo_correlativo}.txt"
            self.ultima_ruta_salida = os.path.join(CARPETA_RESULTADOS, nombre_archivo_salida)
            
            with open(self.ultima_ruta_salida, "w", encoding="utf-8") as f:
                f.write("==================================================\n")
                f.write("      INFORME DE VERIFICACIÓN DE PAGOS SEPARADO   \n")
                f.write("==================================================\n\n")
                
                f.write(f"--- [✔] PAGADOS ({len(pagados)}) ---\n")
                if pagados:
                    for cod in pagados:
                        f.write(f"  {cod}\n")
                else:
                    f.write("  (Ninguno)\n")
                
                f.write("\n")
                
                f.write(f"--- [❌] AÚN NO PAGADOS ({len(no_pagados)}) ---\n")
                if no_pagados:
                    for cod in no_pagados:
                        f.write(f"  {cod}\n")
                else:
                    f.write("  (Ninguno)\n")

            # Mostrar resumen visual en pantalla habilitando temporalmente el textbox
            texto_pantalla = f"=== [✔] PAGADOS ({len(pagados)}) ===\n" + ("\n".join(pagados) if pagados else "(Ninguno)")
            texto_pantalla += f"\n\n=== [❌] AÚN NO PAGADOS ({len(no_pagados)}) ===\n" + ("\n".join(no_pagados) if no_pagados else "(Ninguno)")
            texto_pantalla += f"\n\n[✔] Archivo TXT guardado:\n{nombre_archivo_salida}"

            self.txt_resultados.configure(state="normal")
            self.txt_resultados.delete("1.0", "end")
            self.txt_resultados.insert("1.0", texto_pantalla)
            self.txt_resultados.configure(text_color=("black", "white"))
            
            # Habilitar botón para abrir la carpeta interna
            self.btn_abrir_carpeta.configure(state="normal", fg_color="#1f6aa5", hover_color="#144875")
            
            messagebox.showinfo("Éxito", f"Verificación completada. Guardado como: {nombre_archivo_salida}")

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    def abrir_carpeta_destino(self):
        if os.path.exists(CARPETA_RESULTADOS):
            os.startfile(CARPETA_RESULTADOS)
        else:
            messagebox.showwarning("Aviso", "La carpeta de resultados aún no ha sido creada.")