# ==========================================================
# PRESUPUESTOS.PY - GESTOR PRO
# INTERFAZ ORIGINAL + PDF PROFESIONAL
# ==========================================================

import base64
import mimetypes
import re
import textwrap
import time
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import os
import requests

def ruta_app(carpeta, archivo=None):
    base = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
    ruta = os.path.join(
        base,
        carpeta
    )
    if archivo:
        ruta = os.path.join(
            ruta,
            archivo
        )
    return ruta
CARPETA_PRESUPUESTOS = ruta_app(
    "presupuestos_pdf"
)
ARCHIVO_BAREMOS = ruta_app(
    "data",
    "baremos_v2.json"
)
import subprocess
import sys
import json
import difflib

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image as RLImage,
    BaseDocTemplate,
    PageTemplate,
    Frame
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================================
# CONFIGURACIÓN DE COLORES
# ==========================================================
THEME_COLOR = "#4a7ec7"
THEME_COLOR_ALT = "#7dd3fc"
PANEL_COLOR = "#181e25"
PANEL_HEAD = "#1d2631"
BG_COLOR = "#0d1218"
SUCCESS_COLOR = "#6fcf8a"
ERROR_COLOR = "#ff7a7a"
ACCENT_GOLD = "#fbbf24"
ACCENT_GREEN = "#34d399"
ACCENT_BLUE = "#60a5fa"

# ==========================================================
# CLASE PRINCIPAL
# ==========================================================
class AppPresupuestos(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=BG_COLOR)
        self.parent = parent
        self.items_presupuesto = []
        self.cliente_actual = {
            "nombre": "",
            "telefono": "",
            "nif": "",
            "direccion": "",
            "localidad": ""
        }

        self._cargar_variables_entorno_local()
        os.makedirs("data", exist_ok=True)
        self.archivo_clientes = os.path.join("data", "clientes.json")
        self.clientes = self.cargar_clientes()
        self.cliente_seleccionado = None
        self.baremos = self.cargar_baremos()
        self.archivos_ia = []
        self._ultima_llamada_ia = {}
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.local_ai_base_url = os.getenv("LOCAL_AI_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")).strip()
        self.local_ai_model = os.getenv("LOCAL_AI_MODEL", os.getenv("OLLAMA_MODEL", "llama3.2:latest")).strip()
        preferred = str(os.getenv("AI_PREFERRED_PROVIDER", "auto")).strip().lower()
        if preferred not in {"auto", "groq", "openrouter", "local"}:
            preferred = "auto"
        if preferred == "auto":
            preferred = "groq" if self._obtener_clave_groq() else "openrouter" if self._obtener_clave_openrouter() else "local" if self._local_ai_esta_configurado() else "local"
        self.ai_preferred_provider = preferred
        self.openrouter_modelos_fallback = [
            "openrouter/auto",
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "deepseek/deepseek-r1:free",
            "openai/gpt-4o-mini"
        ]

        print("BAREMOS CARGADOS:", len(self.baremos))

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # PANEL IZQUIERDO
        self.left_frame = ctk.CTkScrollableFrame(self, corner_radius=22, fg_color="#121c28", width=500, border_color="#2a3f55", border_width=1)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        panel_cliente = ctk.CTkFrame(self.left_frame, fg_color="#172633", corner_radius=18, border_color="#2f536d", border_width=1)
        panel_cliente.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(panel_cliente, text="📝 DATOS DEL CLIENTE", font=("Arial", 20, "bold"), text_color="#7ec8ff").pack(anchor="w", padx=12, pady=(10, 6))

        cliente_panel = ctk.CTkFrame(panel_cliente, corner_radius=14, fg_color="#0f1a24", border_color="#35546f", border_width=1)
        cliente_panel.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(cliente_panel, text="👤 CLIENTE", font=("Arial",16,"bold"), text_color="#7ec8ff").pack(anchor="w", padx=12, pady=(10, 4))
        self.lbl_cliente_actual = ctk.CTkLabel(
            cliente_panel,
            text="Sin cliente seleccionado",
            font=("Arial",15),
            text_color="#edf7ff"
        )
        self.lbl_cliente_actual.pack(anchor="w", padx=12, pady=(0, 8))
        ctk.CTkButton(
            cliente_panel,
            text="👤 Buscar / Añadir / Editar Cliente",
            height=42,
            fg_color="#2a8cff",
            hover_color="#1d72de",
            corner_radius=12,
            command=self.abrir_gestor_clientes,
            font=("Arial", 13, "bold")
        ).pack(pady=(0, 10), padx=12, fill="x")

        concepto_panel = ctk.CTkFrame(self.left_frame, corner_radius=18, fg_color="#172633", border_color="#2f536d", border_width=1)
        concepto_panel.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(concepto_panel, text="➕ AÑADIR CONCEPTO", font=("Arial", 20, "bold"), text_color="#7ec8ff").pack(anchor="w", padx=12, pady=(10, 5))
        ctk.CTkLabel(concepto_panel, text="Descripción técnica del trabajo", font=("Arial", 13), text_color="#bfd2ea").pack(anchor="w", padx=12, pady=(0, 4))
        self.txt_desc = ctk.CTkTextbox(concepto_panel, height=130, fg_color="#1d2b35", border_color="#4f718c", border_width=1, corner_radius=12, font=("Arial", 15), text_color="#f4f9ff")
        self.txt_desc.pack(pady=(0, 10), padx=12, fill="x")

        self.txt_precio = self.crear_campo_entrada(self.left_frame, "Precio:")
        self.txt_cant = self.crear_campo_entrada(self.left_frame, "Cantidad:")
        self.txt_cant.insert(0, "1")

        self.txt_desc.bind("<KeyRelease>", self.comprobar_campos_item)
        self.txt_desc.bind("<Return>", self.enter_analizar)
        self.txt_desc.bind("<Shift-Return>", self.shift_enter_nueva_linea)
        self.txt_precio.bind("<Return>", lambda e: self.pasar_a_cantidad())
        self.txt_cant.bind("<KeyRelease>", self.comprobar_campos_item)
        self.txt_cant.bind("<Return>", self.enter_cantidad)

        def cambiar_foco(event):
            self.txt_precio.focus()
            return "break"

        self.txt_desc.bind("<Tab>", cambiar_foco)

        self.lbl_ia_rango = ctk.CTkLabel(
            self.left_frame,
            text="IA: Mín. -- € | Recomendado -- € | Máx. -- €",
            font=("Arial", 12, "bold"),
            text_color="#d7f7ff",
            anchor="w"
        )
        self.lbl_ia_rango.pack(anchor="w", padx=16, pady=(0, 6))

        self.btn_add = ctk.CTkButton(
            self.left_frame,
            text="Añadir",
            fg_color="#2a8cff",
            hover_color="#1d72de",
            height=46,
            font=("Arial",15,"bold"),
            corner_radius=12,
            command=self.añadir_item,
            state="disabled"
        )
        self.btn_add.pack(pady=(10, 6), padx=16, fill="x")

        fila_acciones = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        fila_acciones.pack(fill="x", padx=16, pady=(0, 6))
        fila_acciones.grid_columnconfigure((0, 1), weight=1)

        self.btn_analizar = ctk.CTkButton(
            fila_acciones,
            text="🔍 ANALIZAR",
            fg_color="#2a8cff",
            hover_color="#1d72de",
            height=40,
            font=("Arial",13,"bold"),
            corner_radius=12,
            command=self.analizar_trabajo
        )
        self.btn_analizar.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            fila_acciones,
            text="📚 BAREMOS",
            fg_color="#2d4b6d",
            hover_color="#233b56",
            height=40,
            font=("Arial",13,"bold"),
            corner_radius=12,
            command=self.ver_baremos
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self.lbl_adjuntos_ia = ctk.CTkLabel(
            self.left_frame,
            text="0 archivos adjuntos",
            font=("Arial", 12),
            text_color="#d0d0d0"
        )
        self.lbl_adjuntos_ia.pack(pady=(8, 2), padx=16, anchor="w")

        fila_adjuntos = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        fila_adjuntos.pack(fill="x", padx=16, pady=(0, 5))
        fila_adjuntos.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            fila_adjuntos,
            text="📎 Fotos / videos",
            fg_color="#345f8f",
            hover_color="#294f7d",
            height=38,
            font=("Arial", 12, "bold"),
            corner_radius=10,
            command=self.adjuntar_archivos_ia
        ).grid(row=0, column=0, padx=(0, 4), sticky="ew")

        ctk.CTkButton(
            fila_adjuntos,
            text="🧠 RAZONAR PRECIO",
            fg_color="#2b7d59",
            hover_color="#21674b",
            height=38,
            font=("Arial", 12, "bold"),
            corner_radius=10,
            command=self.razonar_precio
        ).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Selector de proveedor IA (Auto / Groq / OpenRouter) y etiqueta de proveedor en uso
        proveedor_frame = ctk.CTkFrame(self.left_frame, fg_color="#172633", corner_radius=12, border_color="#2f536d", border_width=1)
        proveedor_frame.pack(fill="x", padx=16, pady=(6, 6))
        ctk.CTkLabel(proveedor_frame, text="Proveedor IA:", font=("Arial", 12, "bold"), text_color="#edf7ff", anchor="w").grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(10, 6))

        self.var_proveedor = tk.StringVar(value=getattr(self, 'ai_preferred_provider', 'groq'))

        def on_change_proveedor():
            val = self.var_proveedor.get()
            self.ai_preferred_provider = val
            try:
                self._guardar_preferencia_proveedor(val)
            except Exception:
                pass
            if hasattr(self, 'lbl_proveedor_actual'):
                self.lbl_proveedor_actual.configure(text=f"Proveedor preferido: {val}", text_color="#fef3c7")

        opt_auto = ctk.CTkRadioButton(proveedor_frame, text="Auto", variable=self.var_proveedor, value="auto", command=on_change_proveedor, text_color="#ecf6ff", fg_color="#1f2d3d", border_color="#5ca7ff", hover_color="#2d4a69", font=("Arial", 10))
        opt_groq = ctk.CTkRadioButton(proveedor_frame, text="Groq", variable=self.var_proveedor, value="groq", command=on_change_proveedor, text_color="#ecf6ff", fg_color="#1f2d3d", border_color="#5ca7ff", hover_color="#2d4a69", font=("Arial", 10))
        opt_open = ctk.CTkRadioButton(proveedor_frame, text="OpenRouter", variable=self.var_proveedor, value="openrouter", command=on_change_proveedor, text_color="#ecf6ff", fg_color="#1f2d3d", border_color="#5ca7ff", hover_color="#2d4a69", font=("Arial", 10))
        opt_auto.grid(row=0, column=1, padx=6, pady=(10, 6))
        opt_groq.grid(row=0, column=2, padx=6, pady=(10, 6))
        opt_open.grid(row=0, column=3, padx=(6, 12), pady=(10, 6))

        self.lbl_proveedor_actual = ctk.CTkLabel(self.left_frame, text=f"Proveedor preferido: {getattr(self,'ai_preferred_provider','groq')}", font=("Arial", 10), text_color="#fef3c7")
        self.lbl_proveedor_actual.pack(padx=16, anchor='w', pady=(0,6))

        # PANEL DERECHO
        self.right_frame = ctk.CTkScrollableFrame(self, corner_radius=22, fg_color="#121c28", border_color="#2a3f55", border_width=1)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)

        header_right = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        header_right.pack(fill="x", padx=16, pady=(18, 8))
        ctk.CTkLabel(header_right, text="📋 DESGLOSE DEL PRESUPUESTO", font=("Arial", 18, "bold"), text_color="#7ec8ff").pack(anchor="w")

        tabla_panel = ctk.CTkFrame(self.right_frame, corner_radius=18, fg_color="#141f2a", border_color="#36536e", border_width=1, height=580)
        tabla_panel.pack(fill="x", padx=16, pady=(0, 12))
        tabla_panel.pack_propagate(False)

        self.items_container = ctk.CTkScrollableFrame(tabla_panel, fg_color="#101820", corner_radius=0)
        self.items_container.pack(fill="both", expand=True, padx=12, pady=12)
        self.items_container.grid_columnconfigure(0, weight=1)

        self.item_rows = []
        self.selected_item_index = None

        self.header_row = tk.Frame(self.items_container, bg="#101820", height=36)
        self.header_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.header_row.grid_columnconfigure(0, weight=7, minsize=420)
        self.header_row.grid_columnconfigure(1, weight=3, minsize=250)

        tk.Label(self.header_row, text="DESCRIPCIÓN", bg="#1d4b73", fg="#edf7ff", font=("Arial", 11, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=6)

        values_header = tk.Frame(self.header_row, bg="#1d4b73")
        values_header.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=6)
        values_header.grid_columnconfigure(0, weight=1, minsize=70)
        values_header.grid_columnconfigure(1, weight=1, minsize=70)
        values_header.grid_columnconfigure(2, weight=1, minsize=70)

        tk.Label(values_header, text="PRECIO", bg="#1d4b73", fg="#edf7ff", font=("Arial", 11, "bold"), anchor="center").grid(row=0, column=0, sticky="ew", padx=2)
        tk.Label(values_header, text="CANT", bg="#1d4b73", fg="#edf7ff", font=("Arial", 11, "bold"), anchor="center").grid(row=0, column=1, sticky="ew", padx=2)
        tk.Label(values_header, text="TOTAL", bg="#1d4b73", fg="#edf7ff", font=("Arial", 11, "bold"), anchor="center").grid(row=0, column=2, sticky="ew", padx=2)

        self.tree = self.items_container

        btn_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        btn_frame.pack(pady=4, padx=16, fill="x")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame,
            text="❌ Eliminar",
            height=34,
            font=("Arial", 12, "bold"),
            fg_color="#ef4444",
            hover_color="#d93030",
            border_color="#fca5a5",
            border_width=1,
            corner_radius=10,
            command=self.eliminar_item
        ).grid(row=0, column=0, padx=4, sticky="ew")

        ctk.CTkButton(
            btn_frame,
            text="🧹 LIMPIAR TODOS LOS DATOS",
            height=34,
            font=("Arial", 12, "bold"),
            fg_color="#f5b700",
            hover_color="#e29d00",
            text_color="#1a1a1a",
            border_color="#f7d661",
            border_width=1,
            corner_radius=10,
            command=self.limpiar_todo
        ).grid(row=0, column=1, padx=4, sticky="ew")

        ctk.CTkButton(
            self.right_frame,
            text="📂 IR A CARPETA PDF",
            height=36,
            font=("Arial", 13, "bold"),
            fg_color="#1ea6db",
            hover_color="#1387b8",
            text_color="white",
            border_color="#7cd8ff",
            border_width=1,
            corner_radius=10,
            command=self.abrir_carpeta_pdf
        ).pack(pady=(8, 6), padx=16, fill="x")

        self.lbl_totales_ui = ctk.CTkLabel(self.right_frame, text="Subtotal: 0.00 € | IVA: 0.00 € | TOTAL: 0.00 €", font=("Arial", 14, "bold"), text_color="#6fe3a5")
        self.lbl_totales_ui.pack(pady=(10, 8))

        ctk.CTkButton(
            self.right_frame,
            text="📄 GENERAR PDF",
            fg_color="#22d170",
            hover_color="#18af5a",
            text_color="#14251b",
            height=52,
            font=("Arial", 18, "bold"),
            border_color="#9bf0be",
            border_width=1,
            corner_radius=12,
            command=self.generar_pdf_presupuesto
        ).pack(fill="x", padx=16, pady=(0, 10))

    def shift_enter_nueva_linea(self, event=None):
        self.txt_desc.insert("insert", "\n")
        return "break"

    def enter_analizar(self,event=None):
        texto = self.txt_desc.get("1.0", "end-1c").strip()
        if texto:
            self.analizar_trabajo()
        return "break"

    def pasar_a_cantidad(self):

        self.txt_cant.focus()

        self.txt_cant.select_range(
            0,
            "end"
        )

        return "break"

    def enter_cantidad(self,event=None):

        self.añadir_item()

        # preparar siguiente trabajo
        self.txt_desc.focus()

        return "break"

    def guardar_baremos_json(self, mostrar_mensaje=True):
        try:
            os.makedirs(
                os.path.dirname(ARCHIVO_BAREMOS),
                exist_ok=True
            )
            with open(
                ARCHIVO_BAREMOS,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    self.baremos,
                    f,
                    indent=4,
                    ensure_ascii=False
                )
            if mostrar_mensaje:
                messagebox.showinfo(
                    "Guardado",
                    "Baremos guardados correctamente."
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron guardar los baremos:\n\n{e}"
            )

    def cliente_vacio(self):
        return {
            "nombre": "",
            "telefono": "",
            "nif": "",
            "direccion": "",
            "localidad": ""
        }

    def crear_aprendizaje_vacio(self):
        return {
            "usos": 0,
            "palabras_aprendidas": [],
            "frases_aprendidas": [],
            "ultima_fecha": ""
        }

    def _cargar_variables_entorno_local(self):
        ruta_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloud", "env.txt")
        if not os.path.exists(ruta_env):
            return
        claves_permitidas = {
            "BOT_TOKEN", "CHAT_ID", "USUARIO", "INTERVALO_SEGUNDOS", "ADMIN_USER", "ADMIN_PASS",
            "OPENROUTER_API_KEY", "OPENROUTER_KEY", "OPENAI_API_KEY", "OPENROUTER_MODEL",
            "GROQ_API_KEY", "GROQ_KEY", "GROQ_MODEL",
            "LOCAL_AI_BASE_URL", "LOCAL_AI_MODEL", "OLLAMA_BASE_URL", "OLLAMA_MODEL",
            "BRAVE_SEARCH_API_KEY", "BRAVE_API_KEY", "SERPAPI_KEY"
        }
        try:
            with open(ruta_env, "r", encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea or linea.startswith("#") or "=" not in linea:
                        continue
                    clave, valor = [parte.strip() for parte in linea.split("=", 1)]
                    if clave not in claves_permitidas:
                        continue
                    if not clave or not valor or valor in ("******", "*****"):
                        continue
                    if clave in {"LOCAL_AI_BASE_URL", "LOCAL_AI_MODEL", "OLLAMA_BASE_URL", "OLLAMA_MODEL"}:
                        os.environ.setdefault(clave, valor)
                        continue
                    if "http://" in valor.lower() or "https://" in valor.lower():
                        continue
                    os.environ.setdefault(clave, valor)
        except Exception:
            pass

    def _obtener_clave_openrouter(self):
        for nombre in ("OPENROUTER_API_KEY", "OPENROUTER_KEY", "OPENAI_API_KEY"):
            valor = os.getenv(nombre)
            if valor and valor.strip() and valor.strip() not in ("******", "*****"):
                return valor.strip()

        ruta_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloud", "env.txt")
        if os.path.exists(ruta_env):
            try:
                with open(ruta_env, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if not linea or linea.startswith("#") or "=" not in linea:
                            continue
                        clave, valor = [parte.strip() for parte in linea.split("=", 1)]
                        if clave in ("OPENROUTER_API_KEY", "OPENROUTER_KEY", "OPENAI_API_KEY") and valor and valor not in ("******", "*****"):
                            return valor
            except Exception:
                pass
        return ""

    def _obtener_clave_groq(self):
        for nombre in ("GROQ_API_KEY", "GROQ_KEY"):
            valor = os.getenv(nombre)
            if valor and valor.strip() and valor.strip() not in ("******", "*****"):
                return valor.strip()

        ruta_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloud", "env.txt")
        if os.path.exists(ruta_env):
            try:
                with open(ruta_env, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if not linea or linea.startswith("#") or "=" not in linea:
                            continue
                        clave_env, valor = [parte.strip() for parte in linea.split("=", 1)]
                        if clave_env in ("GROQ_API_KEY", "GROQ_KEY") and valor and valor not in ("******", "*****"):
                            return valor
            except Exception:
                pass
        return ""

    def _local_ai_esta_configurado(self):
        cfg = self._obtener_config_local_ai()
        return bool(cfg.get("base_url")) and bool(cfg.get("model"))

    def _obtener_config_local_ai(self):
        base_url = None
        for nombre in ("LOCAL_AI_BASE_URL", "OLLAMA_BASE_URL"):
            valor = os.getenv(nombre)
            if valor and valor.strip() and valor.strip() not in ("******", "*****"):
                base_url = valor.strip()
                break
        if not base_url:
            base_url = getattr(self, "local_ai_base_url", "") or ""
        model = None
        for nombre in ("LOCAL_AI_MODEL", "OLLAMA_MODEL"):
            valor = os.getenv(nombre)
            if valor and valor.strip() and valor.strip() not in ("******", "*****"):
                model = valor.strip()
                break
        if not model:
            model = getattr(self, "local_ai_model", "") or ""
        if not base_url:
            base_url = "http://127.0.0.1:11434/v1"
        if not model:
            model = "llama3.2:latest"
        return {"base_url": base_url, "model": model}

    def _obtener_clave_buscador(self):
        for clave in ("BRAVE_SEARCH_API_KEY", "BRAVE_API_KEY", "SERPAPI_KEY"):
            valor = os.getenv(clave)
            if valor and valor.strip() and valor.strip() not in ("******", "*****"):
                return valor.strip()
        ruta_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloud", "env.txt")
        if os.path.exists(ruta_env):
            try:
                with open(ruta_env, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if not linea or linea.startswith("#") or "=" not in linea:
                            continue
                        clave_env, valor = [parte.strip() for parte in linea.split("=", 1)]
                        if clave_env in ("BRAVE_SEARCH_API_KEY", "BRAVE_API_KEY", "SERPAPI_KEY") and valor and valor not in ("******", "*****"):
                            return valor
            except Exception:
                pass
        return ""

    def _orden_proveedores_ia(self):
        pref = str(getattr(self, "ai_preferred_provider", "auto") or "auto").lower()
        clave_open = self._obtener_clave_openrouter()
        clave_groq = self._obtener_clave_groq()
        cfg_local = self._obtener_config_local_ai() if self._local_ai_esta_configurado() else {"base_url": "", "model": ""}
        orden = []

        if pref == "groq":
            if clave_groq:
                orden.append(("groq", clave_groq, self.groq_model))
            if clave_open:
                orden.append(("openrouter", clave_open, self.openrouter_model))
            if cfg_local.get("base_url") and cfg_local.get("model"):
                orden.append(("local", cfg_local["base_url"], cfg_local["model"]))
        elif pref == "openrouter":
            if clave_open:
                orden.append(("openrouter", clave_open, self.openrouter_model))
            if clave_groq:
                orden.append(("groq", clave_groq, self.groq_model))
            if cfg_local.get("base_url") and cfg_local.get("model"):
                orden.append(("local", cfg_local["base_url"], cfg_local["model"]))
        elif pref == "local":
            if cfg_local.get("base_url") and cfg_local.get("model"):
                orden.append(("local", cfg_local["base_url"], cfg_local["model"]))
            if clave_open:
                orden.append(("openrouter", clave_open, self.openrouter_model))
            if clave_groq:
                orden.append(("groq", clave_groq, self.groq_model))
        else:
            if clave_groq:
                orden.append(("groq", clave_groq, self.groq_model))
            if clave_open:
                orden.append(("openrouter", clave_open, self.openrouter_model))
            if cfg_local.get("base_url") and cfg_local.get("model"):
                orden.append(("local", cfg_local["base_url"], cfg_local["model"]))
        return orden

    def _puede_hacer_llamada_ia(self, provider, cooldown_segundos=8):
        ahora = time.monotonic()
        ultimo = self._ultima_llamada_ia.get(provider, 0)
        if ultimo and (ahora - ultimo) < cooldown_segundos:
            return False
        return True

    def _marcar_llamada_ia(self, provider, cooldown_segundos=8):
        self._ultima_llamada_ia[provider] = time.monotonic() + cooldown_segundos

    def _request_groq(self, clave, model, texto):
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": self._generar_prompt_openrouter(texto)}
            ],
            "temperature": 0.3,
        }
        try:
            headers = {"Content-Type": "application/json"}
            if clave:
                clave_limpia = str(clave).strip()
                headers["Authorization"] = f"Bearer {clave_limpia}" if not clave_limpia.startswith("Bearer ") else clave_limpia
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=90,
            )
            if resp.status_code in (401, 403):
                self._marcar_llamada_ia("groq", cooldown_segundos=30)
            elif resp.status_code == 200:
                self._marcar_llamada_ia("groq", cooldown_segundos=8)
            return resp
        except Exception:
            return None

    def _request_local_ai(self, base_url, model, texto):
        try:
            if not base_url or not model:
                return None
            endpoint = str(base_url).strip().rstrip("/")
            if "/chat/completions" in endpoint:
                url = endpoint
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": self._generar_prompt_openrouter(texto)}
                    ],
                    "temperature": 0.3,
                }
            elif "/api/chat" in endpoint:
                url = endpoint
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": self._generar_prompt_openrouter(texto)}
                    ],
                    "stream": False,
                }
            elif "/v1" in endpoint:
                url = endpoint + "/chat/completions"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": self._generar_prompt_openrouter(texto)}
                    ],
                    "temperature": 0.3,
                }
            else:
                url = endpoint + "/api/chat"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": self._generar_prompt_openrouter(texto)}
                    ],
                    "stream": False,
                }
            headers = {"Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code in (401, 403):
                self._marcar_llamada_ia("local", cooldown_segundos=30)
            elif resp.status_code == 200:
                self._marcar_llamada_ia("local", cooldown_segundos=8)
            return resp
        except Exception:
            return None

    def _buscar_web_referencias(self, texto, max_results=4):
        """Busca referencias web para validar rango de precios. Usa Brave si existe clave; si no, hace fallback a DuckDuckGo HTML."""
        query = str(texto or "").strip()
        if not query:
            return []
        query = re.sub(r"\s+", " ", query)

        clave = self._obtener_clave_buscador()
        if clave:
            try:
                url = "https://api.search.brave.com/res/v1/web/search"
                params = {"q": query, "count": max_results, "search_lang": "es", "country": "ES"}
                headers = {"Accept": "application/json", "Accept-Language": "es-ES", "X-Subscription-Token": clave}
                r = requests.get(url, params=params, headers=headers, timeout=20)
                r.raise_for_status()
                datos = r.json()
                resultados = []
                if isinstance(datos, dict):
                    items = datos.get("web", {}).get("results", []) or datos.get("results", []) or []
                    for item in items[:max_results]:
                        url_item = item.get("url") or item.get("link") or ""
                        title = item.get("title") or item.get("name") or "Resultado web"
                        if url_item:
                            resultados.append({"titulo": title, "url": url_item, "snippet": item.get("description") or item.get("snippet") or ""})
                if resultados:
                    return resultados
            except Exception:
                pass

        try:
            from urllib.parse import quote_plus
            url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            r.raise_for_status()
            html = r.text
            resultados = []
            # Regex simple para extraer títulos y URLs del HTML de DDG Lite
            bloques = re.findall(r'<a rel="nofollow" class="result-link" href="(.*?)".*?>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
            for href, title in bloques[:max_results]:
                clean_title = re.sub(r'<.*?>', '', title)
                clean_title = html.unescape(clean_title.strip()) if hasattr(__import__('html'), 'unescape') else clean_title.strip()
                snippet = ""
                m = re.search(rf'<a rel="nofollow" class="result-link" href="{re.escape(href)}".*?</a>\s*<a class="result-snippet".*?>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
                if m:
                    snippet = re.sub(r'<.*?>', ' ', m.group(1))
                    snippet = " ".join(snippet.split())
                if href:
                    resultados.append({"titulo": clean_title or "Resultado web", "url": href, "snippet": snippet})
            if resultados:
                return resultados
        except Exception:
            pass
        return []

    def _verificar_estimacion(self, texto, precio_recomendado, base_recomendado, categoria=""):
        """Valida si el precio es razonable frente al baremo local y a referencias web."""
        try:
            precio = float(precio_recomendado)
            base = float(base_recomendado)
        except Exception:
            return {"alerta": False, "mensaje": ""}
        if precio > 0 and base > 0 and precio < base * 0.7:
            return {
                "alerta": True,
                "mensaje": "La estimación actual está claramente por debajo del mercado local y merece revisión por material, acceso, horario y complejidad real."
            }
        if texto and "urgente" in str(texto).lower() and precio > 0 and base > 0 and precio < base * 0.8:
            return {
                "alerta": True,
                "mensaje": "El caso incluye urgencia/horario especial y el precio parece muy ajustado; revisa el rango final antes de cerrar."
            }
        return {"alerta": False, "mensaje": ""}

    def _mostrar_dialogo_estimacion(self, titulo, mensaje):
        """Muestra un diálogo modal con campo libre para consulta del asistente y acciones visibles."""
        ventana = ctk.CTkToplevel(self)
        ventana.title(titulo)
        ventana.geometry("720x540")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)
        ventana.configure(fg_color="#0f1723")
        try:
            ventana.update_idletasks()
            sw = ventana.winfo_screenwidth()
            sh = ventana.winfo_screenheight()
            ww = ventana.winfo_width()
            wh = ventana.winfo_height()
            x = int((sw - ww) / 2)
            y = int((sh - wh) / 2)
            ventana.geometry(f"+{x}+{y}")
        except Exception:
            pass

        header = ctk.CTkFrame(ventana, fg_color="#182333", corner_radius=18, border_color="#2e4b66", border_width=1)
        header.pack(fill="x", padx=14, pady=(14, 8))
        ctk.CTkLabel(header, text="Resultado estimado", font=("Arial", 19, "bold"), text_color="#edf6ff", anchor="w").pack(anchor="w", padx=18, pady=(14, 6))

        frame = ctk.CTkFrame(ventana, fg_color="#111922", corner_radius=18, border_color="#22384d", border_width=1)
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        txt = tk.Text(frame, height=9, wrap="word", bg="#0b1220", fg="#edf6ff", relief="flat", borderwidth=0, padx=12, pady=12, insertbackground="#ffffff", font=("Arial", 11))
        txt.insert("1.0", mensaje)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frame, text="Consulta del asistente", font=("Arial", 11, "bold"), text_color="#dfe9f5").pack(anchor="w", padx=12, pady=(0, 4))
        entrada = ctk.CTkEntry(frame, placeholder_text="Ej: investiga más con las fotos, revisa acceso y horario...", height=40, fg_color="#0b1117", border_color="#415c79", border_width=1, text_color="#f8fbff", font=("Arial", 11))
        entrada.pack(fill="x", padx=12, pady=(0, 10))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(0, 12))

        resultado = {"sel": None, "texto": ""}

        def aceptar_accion(sel):
            resultado["sel"] = sel
            resultado["texto"] = entrada.get().strip()
            ventana.destroy()

        def añadir():
            aceptar_accion("tabla")

        def guardar_concepto():
            aceptar_accion("concepto")

        def investigar():
            aceptar_accion("investigar")

        def volver():
            aceptar_accion("volver")

        def cancelar():
            aceptar_accion("cancelar")

        ctk.CTkButton(btns, text="Añadir a la tabla", fg_color="#22a55f", hover_color="#1c9c53", border_color="#95f0bf", border_width=1, width=150, height=42, command=añadir, font=("Arial", 11, "bold")).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Guardar en concepto", fg_color="#1fbf75", hover_color="#17a667", border_color="#8ef1c3", border_width=1, width=180, height=42, command=guardar_concepto, font=("Arial", 11, "bold")).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Investigar / Ajustar", fg_color="#fbbf24", hover_color="#e2a70b", text_color="#1b1b1b", border_color="#ffd66b", border_width=1, width=180, height=42, command=investigar, font=("Arial", 11, "bold")).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Volver", fg_color="#475569", hover_color="#34455e", border_color="#a5b4c8", border_width=1, width=110, height=42, command=volver, font=("Arial", 11, "bold")).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Cancelar", fg_color="#ef4444", hover_color="#d93030", border_color="#fca5a5", border_width=1, width=120, height=42, command=cancelar, font=("Arial", 11, "bold")).pack(side="right")

        entrada.bind("<Return>", lambda event: añadir())
        ventana.bind("<Return>", lambda event: añadir())
        ventana.bind("<Escape>", lambda event: cancelar())
        entrada.bind("<Escape>", lambda event: cancelar())

        ventana.focus_force()
        ventana.wait_window()
        return resultado

    def _feedback_modal(self):
        """Modal para recoger feedback del usuario con botones expert y texto libre natural."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Afinar estimación")
        ventana.geometry("700x370")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)
        ventana.configure(fg_color="#121922")
        try:
            ventana.update_idletasks()
            sw = ventana.winfo_screenwidth()
            sh = ventana.winfo_screenheight()
            ww = ventana.winfo_width()
            wh = ventana.winfo_height()
            x = int((sw - ww) / 2)
            y = int((sh - wh) / 2)
            ventana.geometry(f"+{x}+{y}")
        except Exception:
            pass

        header = ctk.CTkFrame(ventana, fg_color="#1b2633", corner_radius=16)
        header.pack(fill="x", padx=14, pady=(14, 8))
        ctk.CTkLabel(header, text="Ajustar presupuesto", font=("Arial", 18, "bold"), text_color="#eaf7ff", anchor="w").pack(anchor="w", padx=18, pady=(14, 6))

        frame = ctk.CTkFrame(ventana, fg_color="#111922", corner_radius=16)
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        ctk.CTkLabel(frame, text="¿Qué quieres que revise el asistente antes de cerrar el precio?", font=("Arial", 12, "bold"), text_color="#dfe9f5").pack(anchor="w", padx=12, pady=(12, 6))
        texto = ctk.CTkTextbox(frame, height=8, fg_color="#0b1117", border_color="#3d536b", border_width=1, corner_radius=12, font=("Arial", 11))
        texto.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        quick_frame = ctk.CTkFrame(frame, fg_color="transparent")
        quick_frame.pack(fill="x", padx=12, pady=(0, 10))
        quick_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def set_quick(val):
            texto.delete("1.0", "end")
            texto.insert("1.0", val)

        presets = [
            ("Revisa fotos y accesos", "Mira bien las fotos, la zona del trabajo, el acceso, la dificultad real y si hay que mover muebles o abrir pared."),
            ("Horario / urgencia", "Comprueba si es urgente, fuera del horario laboral, nocturno o fin de semana, porque eso afecta al precio final."),
            ("Materiales extra", "Valora si hace falta piezas, latiguillos, juntas, llave de paso, materiales de limpieza o trabajos extra."),
            ("Mercado de Valencia", "Revisa el mercado de Valencia y ajusta por zona, complejidad, mano de obra y condiciones del trabajo."),
        ]

        for i, (label, val) in enumerate(presets):
            button = ctk.CTkButton(
                quick_frame,
                text=label,
                fg_color="#1f2d3d",
                hover_color="#2b3d52",
                text_color="white",
                border_color="#4a6077",
                border_width=1,
                height=42,
                corner_radius=12,
                command=lambda v=val: set_quick(v)
            )
            button.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="ew")

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(0, 12))

        resultado = {"cancel": False, "text": ""}

        def confirmar():
            resultado["text"] = texto.get("1.0", "end-1c").strip()
            ventana.destroy()

        def cancelar():
            resultado["cancel"] = True
            ventana.destroy()

        ctk.CTkButton(btns, text="Enviar feedback", fg_color="#22a55f", hover_color="#1c9c53", width=170, height=42, corner_radius=12, command=confirmar, font=("Arial", 11, "bold")).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Cancelar", fg_color="#ef4444", hover_color="#d93030", width=120, height=42, corner_radius=12, command=cancelar, font=("Arial", 11, "bold")).pack(side="right")

        texto.bind("<Return>", lambda event: confirmar())
        ventana.bind("<Return>", lambda event: confirmar())
        texto.bind("<Escape>", lambda event: cancelar())
        ventana.bind("<Escape>", lambda event: cancelar())

        ventana.focus_force()
        ventana.wait_window()
        if resultado["cancel"]:
            return None
        return resultado["text"]

    def _normalizar_precio(self, valor):
        if valor is None:
            return 0.0
        if isinstance(valor, (int, float)):
            return float(valor)
        texto = str(valor).strip()
        if not texto:
            return 0.0
        texto = texto.replace("€", "").replace("EUR", "").replace(".", "").replace(" ", "")
        texto = texto.replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            numeros = re.findall(r"\d+(?:[.,]\d+)?", texto)
            if not numeros:
                return 0.0
            return float(numeros[0].replace(",", "."))

    def _mostrar_rango_ia(self, minimo=None, recomendado=None, maximo=None):
        return

    def _aplicar_factores_contexto(self, precio, texto, respuestas=None):
        if precio is None:
            return 0.0
        precio = float(precio)
        if precio <= 0:
            return 0.0
        combinacion = " ".join([str(texto or ""), *(str(r) for r in (respuestas or []) if str(r).strip())]).lower()

        # Ajustes normalizados y acumulativos, para que no se multipliquen de forma descontrolada
        # Ejemplo: urgente + nocturno + fin de semana = subida total razonable, pero no multiplicando 1.3 x 1.2 x 1.25
        extra = 0.0
        reduccion = 0.0

        # Horario y urgencia
        if any(k in combinacion for k in ("urgente", "hoy mismo", "ya mismo", "inmediato", "urgencia")):
            extra += 0.18
        if any(k in combinacion for k in ("fuera de horario laboral", "fuera del horario laboral", "fuera horario", "fuera del horario")):
            extra += 0.22
        if any(k in combinacion for k in ("noche", "nocturno", "noche fin de semana", "noche dentro de semana")):
            extra += 0.20
        if any(k in combinacion for k in ("fin de semana", "sábado", "domingo", "weekend")):
            extra += 0.16
        if any(k in combinacion for k in ("dentro de semana", "dentro del horario laboral", "jornada laboral", "horario normal", "horario laboral")):
            extra += 0.00

        # Acceso, distancia, kilometraje y complejidad
        if any(k in combinacion for k in ("acceso difícil", "acceso limitado", "hay que mover muebles", "mover muebles", "abrir pared", "falso techo", "poco acceso", "escalera", "zona complicada", "acceso complicado")):
            extra += 0.12
        if any(k in combinacion for k in ("muy lejos", "lejos", "desplazamiento", "kilómetros", "kilometros", "km", "recorrido extra", "kilometraje", "distancia extra")):
            extra += 0.08
        if any(k in combinacion for k in ("cliente especial", "pide limpieza extra", "requiere desinfección", "desinfección", "desinfectar", "desinfectante", "productos de limpieza", "prevención", "enfermedad", "incapacidad", "baja")):
            extra += 0.10

        # Materiales / piezas / trabajos extra
        if any(k in combinacion for k in ("material extra", "latiguillo", "válvula", "valvula", "junta", "llave de paso", "llave de escuadra", "pieza nueva", "manguera", "racor", "sifón", "sifon", "brida", "válvulas", "juntas")):
            extra += 0.12
        if any(k in combinacion for k in ("llave de paso", "llave de escuadra")):
            extra += 0.06

        # Riesgo o limpieza especial
        if any(k in combinacion for k in ("olor fuerte", "agua estancada", "retorno", "fuga activa", "suciedad", "mantenimiento sanitario", "higiene", "sanitario", "desinfección")):
            extra += 0.08

        # Reducción razonable para casos muy simples y con acceso fácil, sin urgencia ni materiales extra
        if not any(k in combinacion for k in ("urgente", "hoy mismo", "ya mismo", "inmediato", "urgencia", "noche", "nocturno", "fin de semana", "sábado", "domingo", "fuera de horario", "fuera del horario", "acceso difícil", "mover muebles", "abrir pared", "falso techo", "material extra", "latiguillo", "llave de paso", "llave de escuadra", "desinfección", "desinfectar")):
            reduccion += 0.10

        factor = 1.0 + extra - reduccion
        factor = max(0.70, min(factor, 2.20))
        return round(precio * factor, 2)

    def _razonar_precio(self, texto, respuestas=None):
        base_local = self._precio_base_profesional(texto, "", [])
        precio = float(base_local.get("recomendado", 0) or 0)
        precio = self._aplicar_factores_contexto(precio, texto, respuestas)
        if not texto:
            return
        self.txt_precio.delete(0, "end")
        self.txt_precio.insert(0, f"{precio:.2f}")
        detalle = self._descripcion_local_profesional(texto, respuestas or [])
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", detalle)
        self.comprobar_campos_item()

    def _precio_base_profesional(self, texto, categoria="", trabajos=None):
        """Base de mercado realista para Valencia capital. Estima precios profesionales, no precios de desguace."""
        txt = " ".join([str(texto or ""), str(categoria or ""), *(str(x) for x in (trabajos or []))]).lower()

        base = 90.0
        if "desatasc" in txt or "atasc" in txt:
            base += 25.0
        if "fregadero" in txt:
            base += 10.0
        if "lavabo" in txt or "wc" in txt or "baño" in txt:
            base += 15.0
        if "grifo" in txt or "llave" in txt:
            base += 20.0
        if "latiguillo" in txt or "manguera" in txt:
            base += 15.0
        if "termoelectrico" in txt or "termo" in txt:
            base += 20.0
        if "aire" in txt or "presion" in txt or "máquina" in txt:
            base += 20.0
        if "valencia" in txt:
            base += 10.0
        if "acceso" in txt and ("dif" in txt or "dific" in txt or "poco" in txt or "estre" in txt):
            base += 20.0
        if "picado" in txt or "abras" in txt or "retira" in txt or "limpieza" in txt:
            base += 15.0

        # Caso específico: la sustitución de un latiguillo de WC no debe ir a 300 € por defecto.
        # El precio real suele estar alrededor de 120-180 € en Valencia para pieza + mano de obra,
        # subiendo si hay urgencia, acceso difícil, material extra o fin de semana.
        if ("latiguillo" in txt or "manguera" in txt) and ("wc" in txt or "inodoro" in txt or "aseo" in txt):
            base = max(base, 130.0)
            if any(k in txt for k in ("sustituci", "cambio", "reemplaz", "nuevo")):
                base = max(base, 160.0)

        # Precios en horario laboral y sin urgencia: 90-170 € para casos normales.
        return {
            "min": round(max(75.0, base * 0.85), 2),
            "recomendado": round(base, 2),
            "max": round(max(base * 1.30, 150.0), 2),
        }

    def _archivos_ia_a_contenido_multimodal(self, archivos):
        contenido = []
        for path in archivos:
            if not os.path.exists(path):
                continue
            mime, _ = mimetypes.guess_type(path)
            if not mime:
                mime = "application/octet-stream"

            if mime.startswith("image/"):
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                contenido.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"}
                })
            elif mime.startswith("video/"):
                contenido.append({
                    "type": "text",
                    "text": (
                        f"El usuario adjuntó un video para contexto visual del trabajo. "
                        f"Ruta del archivo: {path}. Analiza la secuencia y usa la información del video como referencia visual "
                        f"cuando sea útil para estimar el alcance del trabajo y el precio."
                    )
                })
        return contenido

    def adjuntar_archivos_ia(self):
        rutas = filedialog.askopenfilenames(
            title="Selecciona fotos o vídeos para la IA",
            filetypes=[
                ("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
                ("Videos", "*.mp4;*.mov;*.avi;*.mkv;*.webm"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not rutas:
            return
        self.archivos_ia = list(rutas)
        self.lbl_adjuntos_ia.configure(text=f"{len(self.archivos_ia)} archivo(s) adjunto(s)")
        messagebox.showinfo("Adjuntos", f"Se añadieron {len(self.archivos_ia)} archivo(s) para la IA.")

    def _normalizar_pregunta(self, texto):
        if texto is None:
            return ""
        texto = str(texto).lower().strip()
        texto = texto.replace("¿", "").replace("?", "").replace("¡", "").replace("!", "")
        texto = re.sub(r"\s+", " ", texto)
        texto = texto.strip(" .:-;,_/\\")
        return texto

    def _pregunta_duplicada(self, a, b):
        a_n = self._normalizar_pregunta(a)
        b_n = self._normalizar_pregunta(b)
        if not a_n or not b_n:
            return a_n == b_n
        if a_n == b_n:
            return True
        if a_n in b_n or b_n in a_n:
            return True
        tokens_a = {t for t in re.findall(r"[a-záéíóúüñ]+", a_n) if len(t) > 2 and t not in {"como", "cuando", "donde", "porque", "si", "es", "hay", "necesitas", "quieres", "puedes", "trabajo", "cliente", "tienes", "sobre", "zona", "problema", "hace", "solo", "tambien", "hoy", "mismo", "fuga", "grifo", "pieza", "wc", "respuesta", "pregunta"}}
        tokens_b = {t for t in re.findall(r"[a-záéíóúüñ]+", b_n) if len(t) > 2 and t not in {"como", "cuando", "donde", "porque", "si", "es", "hay", "necesitas", "quieres", "puedes", "trabajo", "cliente", "tienes", "sobre", "zona", "problema", "hace", "solo", "tambien", "hoy", "mismo", "fuga", "grifo", "pieza", "wc", "respuesta", "pregunta"}}
        if not tokens_a or not tokens_b:
            return False
        overlap = len(tokens_a & tokens_b)
        return overlap >= 2

    def _deduplicar_preguntas(self, preguntas):
        lista = []
        for pregunta in preguntas or []:
            texto = str(pregunta).strip()
            if not texto:
                continue
            if any(self._pregunta_duplicada(texto, ya) for ya in lista):
                continue
            lista.append(texto)
        return lista

    def mostrar_resultado_ia(self, titulo, descripcion, precio_min, precio_recomendado, precio_max):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Resultado de IA")
        ventana.geometry("620x420")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)
        ventana.configure(fg_color="#0f1723")

        frame = ctk.CTkFrame(ventana, fg_color="#111922", corner_radius=20, border_color="#29415d", border_width=1)
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        ctk.CTkLabel(frame, text="Resultado de presupuesto", font=("Arial", 22, "bold"), text_color="#edf7ff", anchor="w").pack(anchor="w", padx=18, pady=(18, 8))

        texto = tk.Text(frame, height=10, bg="#0b1220", fg="#edf6ff", relief="flat", borderwidth=0, padx=14, pady=12, insertbackground="#ffffff", font=("Arial", 11))
        texto.insert("1.0", f"Trabajo:\n{titulo}\n\nDescripción:\n{descripcion}\n\nPrecio mínimo: {precio_min:.2f} €\nPrecio recomendado: {precio_recomendado:.2f} €\nPrecio máximo: {precio_max:.2f} €")
        texto.configure(state="disabled")
        texto.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(0, 12))

        def cancelar_resultado():
            self.txt_desc.delete("1.0", "end")
            self.txt_precio.delete(0, "end")
            self.txt_cant.delete(0, "end")
            self.txt_cant.insert(0, "1")
            self.comprobar_campos_item()
            ventana.destroy()

        def editar_resultado():
            self.txt_desc.delete("1.0", "end")
            self.txt_desc.insert("1.0", descripcion)
            self.txt_precio.delete(0, "end")
            self.txt_precio.insert(0, f"{precio_recomendado:.2f}")
            self.txt_cant.delete(0, "end")
            self.txt_cant.insert(0, "1")
            self.comprobar_campos_item()
            self.txt_desc.focus()
            ventana.destroy()

        def aceptar_resultado():
            self.txt_desc.delete("1.0", "end")
            self.txt_desc.insert("1.0", descripcion)
            self.txt_precio.delete(0, "end")
            self.txt_precio.insert(0, f"{precio_recomendado:.2f}")
            self.txt_cant.delete(0, "end")
            self.txt_cant.insert(0, "1")
            self.añadir_item()
            ventana.destroy()

        ctk.CTkButton(btns, text="Cancelar", fg_color="#ef4444", hover_color="#d93030", border_color="#fca5a5", border_width=1, width=120, height=42, corner_radius=12, command=cancelar_resultado, font=("Arial", 11, "bold")).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Editar", fg_color="#f59e0b", hover_color="#d97706", border_color="#fcd34d", border_width=1, width=120, height=42, corner_radius=12, command=editar_resultado, font=("Arial", 11, "bold")).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Aceptar", fg_color="#22a55f", hover_color="#1c9c53", border_color="#8ef1c3", border_width=1, width=120, height=42, corner_radius=12, command=aceptar_resultado, font=("Arial", 11, "bold")).pack(side="right", padx=6)

        ventana.bind("<Escape>", lambda event: cancelar_resultado())
        ventana.bind("<Return>", lambda event: aceptar_resultado())
        ventana.focus_force()
        ventana.wait_window()

    def _preguntas_modal(self, preguntas):
        """Muestra un asistente tipo chat con botones rápidos y fallback seguro."""

        """Muestra un asistente tipo chat con botones r?pidos y fallback seguro."""
        preguntas = self._deduplicar_preguntas(preguntas)
        if not preguntas:
            return []

        ventana = ctk.CTkToplevel(self)
        ventana.title("Asistente de precios")
        ventana.geometry("980x760")
        ventana.minsize(900, 620)
        ventana.resizable(True, True)
        ventana.grab_set()
        ventana.transient(self)
        ventana.configure(fg_color="#0d1722")

        try:
            ventana.update_idletasks()
            sw = ventana.winfo_screenwidth()
            sh = ventana.winfo_screenheight()
            ww = ventana.winfo_width()
            wh = ventana.winfo_height()
            x = int((sw - ww) / 2)
            y = int((sh - wh) / 2)
            ventana.geometry(f"+{x}+{y}")
        except Exception:
            pass

        top = ctk.CTkFrame(ventana, fg_color="#162332", corner_radius=22, border_color="#2a4669", border_width=1)
        top.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(top, text="Asistente consultor de precios", font=("Arial", 24, "bold"), text_color="#eaf7ff", anchor="w").pack(anchor="w", padx=18, pady=(14, 4))
        ctk.CTkLabel(top, text="Necesito validar unos detalles para cerrar un presupuesto más realista y profesional.", font=("Arial", 12), text_color="#bfd2ea", anchor="w").pack(anchor="w", padx=18, pady=(0, 14))

        body = ctk.CTkScrollableFrame(ventana, fg_color="#0f1724", corner_radius=18, border_color="#1d3144", border_width=1)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1)

        panel = ctk.CTkFrame(body, fg_color="#0f1724")
        panel.pack(fill="both", expand=True, padx=12, pady=12)
        panel.grid_columnconfigure(0, weight=1)

        def limpiar_panel():
            for widget in panel.winfo_children():
                widget.destroy()

        respuestas = []
        indice_actual = {"valor": 0}
        resultado = {"cancel": False}

        def opciones_para(pregunta):
            ql = str(pregunta).lower()
            if any(k in ql for k in ("noche", "fin de semana", "fuera de horario", "dentro de semana", "dentro de la jornada", "día laborable", "jornada laboral", "disponibilidad", "horario", "urgente", "hoy mismo", "inmediato")):
                return [
                    ("Dentro del horario laboral", "#34d399"),
                    ("Fuera del horario laboral", "#f59e0b"),
                    ("Dentro de semana", "#60a5fa"),
                    ("Fin de semana", "#f87171"),
                    ("Noche dentro de semana", "#c084fc"),
                    ("Noche fin de semana", "#ec4899")
                ]
            if any(k in ql for k in ("llave de paso", "llave de escuadra", "escuadra", "retención", "pieza / retención")):
                return [("Llave de paso", "#60a5fa"), ("Llave de escuadra", "#f59e0b"), ("Cambio de pieza", "#fbbf24"), ("Fuga / reparación", "#f87171")]
            if any(k in ql for k in ("acceso", "mueble", "falso techo", "difícil", "obstáculo", "movilizar", "llegar", "zona tiene acceso", "espacio reducido", "escalera")):
                return [("Acceso fácil", "#60a5fa"), ("Hay que mover muebles", "#fbbf24"), ("Acceso difícil", "#f87171"), ("Hay que abrir pared / falso techo", "#fb7185")]
            if any(k in ql for k in ("fotos", "fotograf", "imagen", "ver", "video", "vídeo")):
                return [("Sí, hay fotos", "#60a5fa"), ("Sí, hay vídeo", "#60a5fa"), ("No hay fotos", "#f87171"), ("No puedo aportar fotos", "#fbbf24")]
            if any(k in ql for k in ("material", "pieza", "latiguillo", "grifo", "wc", "inodoro", "llave de paso", "sifón", "válvula", "desinfección", "desinfectar", "limpieza")):
                return [("Sí, hace falta material / limpieza", "#60a5fa"), ("No hace falta más material", "#34d399"), ("No lo sé", "#fbbf24")]
            if any(k in ql for k in ("razone", "internet", "investigue", "referencias", "mercado")):
                return [("Sí, razonar y revisar mercado", "#60a5fa"), ("No, cerrar presupuesto", "#f87171"), ("Quiero comparar precios", "#fbbf24")]
            if any(k in ql for k in ("tipo de trabajo", "qué trabajo", "trabajo exacto", "qué tipo", "tipo de incidencia", "problema")):
                return [("Cambio de pieza", "#60a5fa"), ("Fuga / reparación", "#f59e0b"), ("Desatasco", "#fbbf24"), ("Cambio de grifo / WC", "#f87171")]
            if any(k in ql for k in ("distancia", "lejos", "desplazamiento", "kilómetros", "km")):
                return [("Muy cerca", "#60a5fa"), ("Hay desplazamiento", "#fbbf24"), ("Muy lejos", "#f87171"), ("No lo sé", "#c084fc")]
            return [("Sí", "#60a5fa"), ("No", "#f87171"), ("No lo sé", "#fbbf24")]

        def crear_burbuja(texto, derecha=False, color="#1d2d42"):
            item = ctk.CTkFrame(panel, fg_color="transparent")
            item.pack(fill="x", padx=8, pady=6)
            bubble = ctk.CTkFrame(item, corner_radius=16, fg_color=color, border_color="#35506a", border_width=1)
            bubble.pack(fill="x", padx=(18 if not derecha else 60, 18 if not derecha else 18))
            ctk.CTkLabel(bubble, text=texto, justify="left", wraplength=720, font=("Arial", 14), text_color="#f8fbff", padx=16, pady=12).pack(fill="x")

        def responder(valor):
            valor_limpio = str(valor).strip()
            if hasattr(responder_custom, "entry"):
                entry = responder_custom.entry
                entry.delete(0, "end")
                if valor_limpio:
                    entry.insert(0, valor_limpio)
            if valor_limpio:
                respuestas.append(valor_limpio)
                try:
                    texto_trabajo = self.txt_desc.get("1.0", "end-1c").strip()
                    if texto_trabajo:
                        self._recalcular_estimacion_parcial(texto_trabajo, list(respuestas))
                except Exception:
                    pass
            indice_actual["valor"] += 1
            if indice_actual["valor"] < len(preguntas):
                pintar_pregunta()
            else:
                resultado["values"] = list(respuestas)
                ventana.after(50, ventana.destroy)

        def responder_custom():
            if not hasattr(responder_custom, "entry"):
                return
            texto = responder_custom.entry.get().strip()
            if texto:
                responder(texto)

        def volver():
            if indice_actual["valor"] <= 0:
                return
            if respuestas:
                respuestas.pop()
            indice_actual["valor"] = max(0, indice_actual["valor"] - 1)
            pintar_pregunta()

        def pintar_pregunta():
            limpiar_panel()
            crear_burbuja("Hola, soy tu consultor de precios. Voy a razonar cada respuesta, revisar comparables del mercado y confirmar el rango real antes de cerrar nada.")
            crear_burbuja("Puedes responder con un botón o escribirlo tú mismo; así ajustamos precio, accesos, urgencia, materiales y fotos con criterio real.")

            if indice_actual["valor"] >= len(preguntas):
                resultado["values"] = list(respuestas)
                ventana.destroy()
                return

            pregunta = preguntas[indice_actual["valor"]]
            crear_burbuja(pregunta)

            opciones = opciones_para(pregunta)
            btns = ctk.CTkFrame(panel, fg_color="transparent")
            btns.pack(fill="x", padx=12, pady=(12, 8))
            columnas = max(2, min(len(opciones), 4))
            for i in range(columnas):
                btns.grid_columnconfigure(i, weight=1)

            for i in range(3):
                btns.grid_columnconfigure(i, weight=1)
            btns.grid_columnconfigure((0, 1, 2, 3), weight=1)
            for i, (txt, color) in enumerate(opciones):
                row = i // 4
                col = i % 4
                btn = ctk.CTkButton(
                    btns,
                    text=txt,
                    fg_color="#18293b",
                    hover_color="#224366",
                    border_color=color,
                    border_width=2,
                    text_color="white",
                    font=("Arial", 10, "bold"),
                    height=42,
                    corner_radius=12,
                    command=lambda v=txt: responder(v),
                )
                btn.grid(row=row, column=col, padx=6, pady=6, sticky="ew")

            entry = ctk.CTkEntry(
                panel,
                placeholder_text="Escribe aquí tu respuesta...",
                fg_color="#0d1724",
                border_color="#4f6d8d",
                border_width=1,
                text_color="#f8fbff",
                font=("Arial", 13),
                height=46,
                corner_radius=12,
            )
            responder_custom.entry = entry
            entry.pack(fill="x", padx=12, pady=(0, 10))
            entry.bind("<Return>", lambda event: responder_custom())
            ventana.bind("<Return>", lambda event: responder_custom())
            entry.bind("<Escape>", lambda event: cancelar())
            ventana.bind("<Escape>", lambda event: cancelar())

            aceptar = ctk.CTkButton(
                panel,
                text="Aceptar",
                fg_color="#22c55e",
                hover_color="#16a34a",
                border_color="#7ef0af",
                border_width=1,
                corner_radius=12,
                height=48,
                font=("Arial", 12, "bold"),
                command=lambda: responder_custom(),
            )
            aceptar.pack(fill="x", padx=12, pady=(0, 10))

            # Si el usuario presiona una respuesta rápida, se acepta inmediatamente y se avanza.
            # Esto evita que el flujo se quede colgado esperando un segundo clic de Aceptar.
            entry.bind("<Control-Return>", lambda event: responder_custom())

        def cancelar():
            resultado["cancel"] = True
            ventana.destroy()

        footer = ctk.CTkFrame(ventana, fg_color="#121922", corner_radius=16, border_color="#243749", border_width=1)
        footer.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(footer, text="Volver", width=120, command=volver, fg_color="#475569", hover_color="#334155", border_color="#94a3b8", border_width=1, corner_radius=12, font=("Arial", 11, "bold")).pack(side="right", padx=(10, 0), pady=10)
        ctk.CTkButton(footer, text="Cancelar", width=130, command=cancelar, fg_color="#ef4444", hover_color="#d93030", border_color="#fca5a5", border_width=1, corner_radius=12, font=("Arial", 11, "bold")).pack(side="right", padx=(10, 0), pady=10)

        ventana.bind("<Escape>", lambda event: cancelar())

        pintar_pregunta()
        ventana.update_idletasks()
        ventana.focus_force()
        ventana.wait_window()

        if resultado.get("cancel"):
            return None
        return resultado.get("values") or list(respuestas)
    def _contexto_baremo(self, texto):
        if not getattr(self, "baremos", None):
            return "Referencia local: sin baremos cargados."
        resultado = self.buscar_precio_baremo(texto)
        if not resultado:
            return "Referencia local: no hay coincidencia clara en baremos; usa el criterio profesional de Valencia y no bajes por debajo del mercado real."
        item = resultado.get("item", {})
        nombre = item.get("nombre", "Trabajo")
        precio_min = item.get("precio_min", 0)
        precio_max = item.get("precio_max", 0)
        recomendado = item.get("precio_recomendado", (precio_min + precio_max) / 2 if precio_min and precio_max else 0)
        return (
            f"Referencia local del baremo: {nombre}. "
            f"Rango: {precio_min} € - {precio_max} €; recomendado: {recomendado} €. "
            "Usa esta referencia como suelo realista del mercado de Valencia antes de aceptar un precio demasiado bajo."
        )

    def _generar_prompt_openrouter(self, texto_trabajo):
        return (
            "Eres un experto estimador de presupuestos para fontanería, saneamiento y servicios técnicos en España, especialmente en Valencia capital y alrededores. "
            "Tu trabajo es valorar el caso real del cliente con criterio profesional, no usar valores rígidos ni inventar precios fijos, y ajustar siempre según la complejidad real del trabajo. "
            "Haz un razonamiento profesional paso a paso: 1) identifica la familia exacta del trabajo; 2) detecta si es desatasco, llave, latiguillo, tramo de tubería, cambio de pieza, conexión o montaje; 3) analiza la dificultad de acceso, gravedad, materiales, limpieza/desinfección y desplazamiento; 4) valora horario laboral, fuera de horario, noche, fin de semana y urgencia; 5) considera kilometraje, demora, mano de obra extra, y riesgo de deterioro; 6) compara con mercado real de Valencia y justifica el rango. "
            "Tipos de trabajos que debes reconocer exactamente: desatasco de WC/váter, desatasco de lavabo/lavamanos, desatasco de fregadero, desatasco de bidé, desatasco de bañera, sustitución de llaves de escuadra de lavabo, de fregadero, de WC/váter, llave de paso general de vivienda, llave de paso de cuarto de contadores, llave de paso de calentador/termo, latiguillo de WC, latiguillo de fregadero, latiguillo de lavamanos, latiguillo de calentador, latiguillo de termo, tramo de tubería plomo, tramo de tubería cobre, tramo de tubería multicapa, tramo de tubería PEX, tramo de tubería polibutileno, cambio de sifón, cambio de racor, cambio de brida, cambio de válvula, cambio de grifo, reparación de fuga, revisión de presión, conexiones, aislamiento, y trabajos de saneamiento más complejos. "
            "Si existen fotos o vídeos, úsalo como evidencia visual: detecta tipo de material, corrosión, envejecimiento, acceso, paso por pared, falsos techos, espacio reducido, presencia de mueble, piezas rotas, junta gastada, desnivel o gravedad del desagüe. "
            "Si el caso habla de gravedad, la zona está baja, hay retorno, agua estancada, olor, sifón sucio o salida obstruida, debe reflejarse en la complejidad y el precio. "
            "Si es una llave de escuadra de lavabo, fregadero, WC/váter, o una llave de paso general de vivienda o de cuarto de contadores, ten en cuenta si requiere cierre de servicio, tramos, uniones, conexión, prueba de presión y limpieza final. "
            "Si son latiguillos de WC, fregadero, lavamanos, calentador, termo o similar, considera si requieren pieza nueva, acoplamientos, racores, bridas, válvulas, y si la maniobra es rápida o con acceso complicado. "
            "Si son tramos de tubería en plomo, cobre, multicapa, PEX o polibutileno, hay que valorar si se perfora pared, se accede por falso techo, se cambia tramo, se necesita junta, acople, remate o aislamiento; todo eso debe aparecer en observaciones y descripción. "
            "La evaluación debe subir claramente si hay urgencia, noche, fin de semana, trabajo fuera del horario, acceso difícil, piezas extra, limpieza especial, desinfección, trabajo con gravedad, peligro de humedad/olor, o desplazamiento por kilometraje. "
            "También debes incluir hipótesis razonables por incidencias: enfermedad, baja, aislamiento, situación delicada del cliente, necesidad de proteger zona, o cualquier caso donde el operario deba actuar con más tiempo o esfuerzo. "
            "Si el cliente indica urgencia, noche, fin de semana, desplazamiento, enfermedad, material extra, limpieza, desinfección, acceso complicado o varias piezas, el precio debe reflejarlo en precio_min, precio_max y precio_recomendado. "
            "Si el caso es claramente simple, de acceso fácil, sin urgencia, sin materiales extra ni complejidad, revisa si puede mantenerse en el extremo inferior del rango o incluso reducirlo razonablemente. No fuerces un sobreprecio si la operación es pequeña y sin complicaciones. "
            "Usa el baremo local del mercado de Valencia como referencia y no bajes por debajo del rango razonable salvo que el caso sea claramente simple, dentro de horario y sin complejidad. "
            "Nunca uses cifras fijas sin base técnica. Si hay duda, haz preguntas antes de cerrar precio. "
            "Responde SIEMPRE en JSON puro, sin markdown, sin texto fuera del JSON. "
            "La estructura exacta es esta: {\n"
            "  \"titulo\": \"título muy técnico del trabajo\",\n"
            "  \"descripcion\": \"2 o 3 frases profesionales que reflejen exactamente el trabajo solicitado, los trabajos a realizar y la maniobra real. Debe coincidir con el texto del cliente y no inventar tareas que no estén pedidas.\",\n"
            "  \"trabajos\": [\"trabajo 1 real\", \"trabajo 2 real\", \"trabajo 3 real\"],\n"
            "  \"categoria\": \"categoria exacta del trabajo\",\n"
            "  \"precio_min\": 0,\n"
            "  \"precio_max\": 0,\n"
            "  \"precio_recomendado\": 0,\n"
            "  \"cantidad\": 1,\n"
            "  \"materiales\": [\"material 1\", \"material 2\"],\n"
            "  \"observaciones\": \"explica el motivo del precio: urgencia, horario, fin de semana, noche, kilometraje, acceso, material extra, limpieza, desinfección, gravedad, enfermedad, o tipo de tubería/material\",\n"
            "  \"necesita_info\": false,\n"
            "  \"preguntas\": [\"Pregunta 1 breve\", \"Pregunta 2 breve\"]\n"
            "}\n"
            "Si necesitas más datos, devuelve \"necesita_info\": true y añade \"preguntas\" con 2 a 5 preguntas breves. Prioriza: urgencia, horario laboral, fin de semana/nocturno, acceso, materiales extra, kilometraje, limpieza/desinfección, fotos o vídeo, tipo de tubería y gravedad. "
            "Reglas muy importantes: 1) la descripcion y la lista de trabajos deben coincidir exactamente con lo solicitado por el cliente; 2) no inventes tareas ajenas; 3) si se piden materiales, instala esos materiales en 'materiales'; 4) si hay piezas extra, desinfección, plástico/metal, PEX/cobre/plomo/multicapa, latiguillos, racores, válvulas, bridas, sifones, mangueras, grifos o llaves, deben reflejarse en descripcion, trabajos y materiales; 5) si aparece acceso dificultoso, trabajo fuera de horario, fin de semana, noche, gravedad, fotos/vídeo, kilómetros o materiales especiales, explica el ajuste; 6) la respuesta debe estar en español; 7) nunca devuelvas texto fuera del JSON. "
            f"Texto del trabajo del cliente: {texto_trabajo}"
        )

    def _parsear_respuesta_openrouter(self, texto):
        try:
            texto_limpio = texto.strip()
            if texto_limpio.startswith("```"):
                texto_limpio = re.sub(r"^```(?:json)?\s*", "", texto_limpio)
                texto_limpio = re.sub(r"\s*```$", "", texto_limpio)
            inicio = texto_limpio.find("{")
            fin = texto_limpio.rfind("}")
            if inicio != -1 and fin != -1 and fin > inicio:
                texto_limpio = texto_limpio[inicio:fin+1]
            datos = json.loads(texto_limpio)
            if isinstance(datos, dict):
                return datos
        except Exception:
            pass

        # fallback robusto
        match = re.search(r'"precio_recomendado"\s*:\s*(\d+(?:[.,]\d+)?)', texto, re.IGNORECASE)
        if match:
            precio = self._normalizar_precio(match.group(1))
            return {
                "titulo": "Trabajo de fontanería",
                "descripcion": "Trabajo de fontanería profesional",
                "trabajos": ["Trabajo técnico de fontanería"],
                "categoria": "Fontanería",
                "precio_min": precio * 0.9,
                "precio_max": precio * 1.2,
                "precio_recomendado": precio,
                "cantidad": 1,
                "observaciones": texto[:400]
            }
        return None

    def _formatear_descripcion_ia(self, datos):
        if not isinstance(datos, dict):
            return "Trabajo de fontanería profesional"
        titulo = str(datos.get("titulo") or datos.get("categoria") or "Trabajo de fontanería").strip()
        descripcion = str(datos.get("descripcion") or datos.get("observaciones") or titulo).strip()
        trabajos = datos.get("trabajos") or []
        if isinstance(trabajos, str):
            trabajos = [trabajos]
        trabajos_limpios = [str(item).strip() for item in trabajos if str(item).strip()]
        materiales = datos.get("materiales") or []
        if isinstance(materiales, str):
            materiales = [materiales]
        materiales_limpios = [str(item).strip() for item in materiales if str(item).strip()]
        if not descripcion or len(descripcion) < 12:
            descripcion = f"{titulo}: intervención de fontanería profesional."

        texto = descripcion
        if trabajos_limpios:
            texto = f"{texto}\n\nTrabajos a realizar:\n- {'\n- '.join(trabajos_limpios[:5])}"
        if materiales_limpios:
            texto = f"{texto}\n\nMateriales previstos:\n- {'\n- '.join(materiales_limpios[:5])}"
        if datos.get("observaciones"):
            obs = str(datos.get("observaciones")).strip()
            if obs and obs not in texto:
                texto = f"{texto}\n\nObservaciones: {obs}"
        if len(texto) < 30:
            texto = f"{titulo}. Revisión, ajuste y prueba de la instalación con criterio técnico profesional."
        return texto

    def _descripcion_local_profesional(self, texto, respuestas=None):
        texto_l = str(texto or "").strip()
        resp = [str(r).strip() for r in (respuestas or []) if str(r).strip()]
        resp_txt = " ".join(resp).lower()

        if any(k in texto_l.lower() for k in ("desatasc", "atasco", "sifon", "desagüe", "aire comprimido", "máquina de aire")):
            parte = "Desatasco de WC con máquina de aire comprimido"
            detalles = [
                "Revisión de la salida y del sifón para localizar la obstrucción.",
                "Desbloqueo con máquina de aire comprimido o herramientas profesionales.",
                "Limpieza y comprobación del tránsito del agua y del sello de la pieza.",
                "Prueba de presión y cierre para confirmar funcionamiento correcto."
            ]
            if any(k in resp_txt for k in ("urgente", "hoy mismo", "inmediato", "fin de semana", "noche")):
                detalles.insert(0, "Servicio con prioridad por horario especial y posible incidencia puntual.")
            if any(k in resp_txt for k in ("acceso difícil", "mover muebles", "falso techo", "abrir pared")):
                detalles.append("Ajuste por acceso complicado y maniobra extra por espacio limitado.")
            return parte + "\n- " + "\n- ".join(detalles[:4])

        if any(k in texto_l.lower() for k in ("grifo", "latiguillo", "llave de paso", "fuga", "manguera", "válvula", "sustituci", "cambio de pieza")):
            parte = "Reparación o sustitución de grifo / latiguillo / llave de paso"
            detalles = [
                "Diagnóstico de la fuga, desgaste o conexión defectuosa.",
                "Desmontaje y sustitución de pieza necesaria con material compatible.",
                "Comprobación de presión, cierre y estanqueidad final.",
                "Limpieza de la zona y prueba funcional del punto de servicio."
            ]
            if any(k in resp_txt for k in ("material", "pieza", "latiguillo", "válvula")):
                detalles.append("Incluye material adicional por piezas y conexiones necesarias.")
            if any(k in resp_txt for k in ("urgente", "hoy mismo", "fin de semana", "noche")):
                detalles.append("Atención fuera del horario habitual o por urgencia puntual.")
            return parte + "\n- " + "\n- ".join(detalles[:5])

        if any(k in texto_l.lower() for k in ("wc", "inodoro", "aseo", "baño")):
            parte = "Revisión y posible reparación del WC / inodoro"
            detalles = [
                "Comprobación del mecanismo, alimentación y posibles fugas.",
                "Desmontaje parcial si es necesario para localizar la avería.",
                "Revisión de conexiones, sello y ajuste del conjunto.",
                "Prueba final de funcionamiento y limpieza de la zona."
            ]
            if any(k in resp_txt for k in ("dentro del horario laboral", "fuera del horario laboral", "fin de semana", "noche")):
                detalles.append("Se considera el horario y la urgencia para ajustar la ejecución del servicio.")
            return parte + "\n- " + "\n- ".join(detalles[:5])

        base = "Intervención de fontanería profesional"
        detalles = [
            "Diagnóstico de la avería o punto de fuga identificado.",
            "Revisión y preparación del punto de trabajo y acceso.",
            "Intervención técnica con material compatible y prueba final.",
            "Limpieza y entrega del servicio con comprobación funcional."
        ]
        if any(k in resp_txt for k in ("urgente", "fin de semana", "noche", "fuera del horario laboral")):
            detalles.append("Servicio ajustado por urgencia, horario especial o dificultad de ejecución.")
        return base + "\n- " + "\n- ".join(detalles[:4])

    def _request_openrouter(self, clave, model, texto):
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._generar_prompt_openrouter(texto)},
                        *self._archivos_ia_a_contenido_multimodal(self.archivos_ia)
                    ]
                }
            ],
            "temperature": 0.3
        }
        try:
            if not clave:
                return None
            headers = {
                "Authorization": f"Bearer {str(clave).strip()}" if not str(clave).strip().startswith("Bearer ") else str(clave).strip(),
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost",
                "X-Title": "GestorPro"
            }
            respuesta = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=90
            )
            if respuesta.status_code in (401, 403):
                self._marcar_llamada_ia("openrouter", cooldown_segundos=30)
            elif respuesta.status_code == 200:
                self._marcar_llamada_ia("openrouter", cooldown_segundos=8)
            return respuesta
        except Exception:
            return None

    def _request_openrouter_raw(self, clave, model, prompt_text):
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        *self._archivos_ia_a_contenido_multimodal(self.archivos_ia)
                    ]
                }
            ],
            "temperature": 0.2
        }
        try:
            if not clave:
                return None
            clave_limpia = str(clave).strip()
            headers = {
                "Authorization": f"Bearer {clave_limpia}" if not clave_limpia.startswith("Bearer ") else clave_limpia,
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost",
                "X-Title": "GestorPro"
            }
            respuesta = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if respuesta.status_code in (401, 403):
                self._marcar_llamada_ia("openrouter", cooldown_segundos=30)
            elif respuesta.status_code == 200:
                self._marcar_llamada_ia("openrouter", cooldown_segundos=8)
            return respuesta
        except Exception:
            return None

    def _generar_preguntas_con_ia(self, texto):
        # asegurar que la preferencia del UI esté sincronizada
        try:
            ui_pref = getattr(self, 'ai_preferred_provider', None)
            if hasattr(self, 'var_proveedor') and ui_pref and self.var_proveedor.get() != ui_pref:
                self.var_proveedor.set(ui_pref)
        except Exception:
            pass

        """Pide a la IA que genere 2-4 preguntas contextuales y breves para cerrar presupuesto.
        Devuelve lista de preguntas o None si falla (fallback al generador local).
        """
        prompt = (
            "Eres un asistente técnico experto en fontanería y servicios de mantenimiento en Valencia, con criterio realista de mercado. "
            "Genera entre 2 y 4 preguntas MUY concretas para cerrar un presupuesto bien ajustado. "
            "Prioriza exactamente estas variables: urgencia, horario laboral, fuera de horario, noche, fin de semana, acceso difícil, piezas/materiales extra, limpieza/desinfección, desplazamiento, kilometraje, y si hay algún caso especial de enfermedad, incidencia o dependencia del cliente. "
            "Las preguntas deben ser específicas para el tipo de trabajo y no mezclar categorías (si es WC, no preguntes por desatascos de fregadero). "
            "Devuelve solo JSON con la clave 'preguntas', por ejemplo: {\"preguntas\": [\"Pregunta 1\", \"Pregunta 2\"]}. "
            "Añade una pregunta final clara como: '¿Quieres que investigue precios y referencias en internet para validar el rango antes de cerrar?' "
            f"Texto del cliente: {texto}"
        )

        proveedores = self._orden_proveedores_ia()

        if not proveedores:
            return None

        for provider, clave, modelo in proveedores:
            try:
                if provider == "groq":
                    resp = self._request_groq(clave, modelo, prompt)
                elif provider == "local":
                    resp = self._request_local_ai(clave, modelo, prompt)
                else:
                    resp = self._request_openrouter_raw(clave, modelo, prompt)
                if not resp or resp.status_code != 200:
                    continue
                datos = resp.json()
                contenido = None
                try:
                    contenido = datos["choices"][0]["message"]["content"]
                except Exception:
                    contenido = datos
                if isinstance(contenido, list):
                    texto_respuesta = "".join(part.get("text", "") for part in contenido if isinstance(part, dict))
                else:
                    texto_respuesta = str(contenido)
                inicio = texto_respuesta.find('{')
                fin = texto_respuesta.rfind('}')
                if inicio != -1 and fin != -1 and fin > inicio:
                    try:
                        bloque = texto_respuesta[inicio:fin+1]
                        j = json.loads(bloque)
                        preguntas = j.get('preguntas') or j.get('questions')
                        if isinstance(preguntas, list) and preguntas:
                            preguntas_limpias = [str(p).strip() for p in preguntas if str(p).strip()]
                            investigacion = "¿Quieres que investigue precios y referencias en internet y vuelva con fuentes/ejemplos?"
                            if investigacion not in preguntas_limpias:
                                preguntas_limpias.append(investigacion)
                            return preguntas_limpias[:4]
                    except Exception:
                        pass
                lines = [l.strip() for l in re.split(r'[\n\r]+', texto_respuesta) if l.strip()]
                qs = [l for l in lines if l.endswith('?')]
                if qs:
                    return [q.strip() for q in qs][:4]
            except Exception:
                continue
        return None

    def _preguntas_iniciales_por_texto(self, texto):
        texto_l = str(texto).lower()
        preguntas_base = [
            "¿Es urgente o puede hacerse dentro del horario laboral normal?",
            "¿Qué horario te interesa: dentro de la jornada laboral, fuera del horario laboral, dentro de semana, fin de semana, noche dentro de semana o noche fin de semana?",
            "¿La zona tiene acceso fácil o hay que mover muebles, abrir pared / falso techo o llegar por un hueco difícil?",
            "¿Quieres que razone y revise referencias en internet para ajustar mejor el precio?",
        ]

        if any(k in texto_l for k in ("desatasc", "atasco", "desagüe", "sifon", "aire comprimido", "maquina de aire", "máquina de aire", "wc", "váter", "vater", "lavabo", "lavamanos", "fregadero")):
            preguntas = [
                "¿Es un desatasco de WC/váter, lavabo/lavamanos o fregadero?",
                "¿Hay olor fuerte, agua estancada, retorno, gravedad muy lenta o hay que abrir sifón para limpiar?",
                "¿La zona tiene acceso fácil o está detrás de muebles, armario, pared o con poco hueco?",
                "¿Necesitas cambiar sifón, manguera, racor, pieza o hacer una intervención más técnica?",
                "¿Hay fotos o vídeo del desagüe, la salida y la zona de trabajo para detectar la gravedad y el material?"
            ]
            if any(k in texto_l for k in ("urgente", "hoy", "ya")):
                preguntas.insert(0, "¿Necesitas que se haga urgentemente hoy mismo?")
            return (preguntas_base + preguntas)[:6]

        if any(k in texto_l for k in ("llave de paso", "llave escuadra", "escuadra", "retención", "llave de escuadra", "llave de corte", "cuarto de contadores", "contador")):
            preguntas = [
                "¿Es una llave de escuadra de lavabo, fregadero, WC/váter, o una llave de paso general de vivienda / cuarto de contadores?",
                "¿Es urgente y necesitas que se haga hoy mismo o fuera del horario laboral?",
                "¿La instalación está en una zona fácil o hay que mover muebles, abrir pared / falso techo o llegar por un sitio difícil?",
                "¿Hace falta material adicional como llave nueva, latiguillo, junta, racor, válvula, brida o conexión?",
                "¿Hay que usar productos de limpieza o desinfección especiales o hay desplazamiento extra por la zona?",
                "¿Tienes fotos del punto de paso, la conexión y el espacio de trabajo?"
            ]
            return (preguntas_base + preguntas)[:6]

        if any(k in texto_l for k in ("latiguillo", "manguera", "grifo", "fuga", "sustituci", "cambio de pieza", "reemplazo", "conexión", "alimentación", "calentador", "termo")):
            preguntas = [
                "¿Es de WC, fregadero, lavamanos, calentador o termo?",
                "¿Se trata de una fuga activa, cambio de pieza o sustitución del latiguillo/grifo?",
                "¿La zona tiene acceso fácil o hay que mover muebles, abrir un mueble o llegar a un techo o pared?",
                "¿Necesitas cambiar material adicional como latiguillos, juntas, abrazaderas, válvulas, racores o piezas extra?",
                "¿Hay fotos o vídeo de la conexión, la fuga, la zona y el material para valorar bien el trabajo?"
            ]
            return (preguntas_base + preguntas)[:6]

        if any(k in texto_l for k in ("tuberia", "cobre", "multicapa", "pex", "polibutileno", "plomo", "tramo de tubería", "tramo de cobre", "tramo de pex")):
            preguntas = [
                "¿Es un tramo de tubería en plomo, cobre, multicapa, PEX o polibutileno?",
                "¿Se debe abrir pared, foso, falso techo o hay acceso directo?",
                "¿La zona requiere desmantelado, retirada de restos, limpieza, aislamiento o conexión de varias piezas?",
                "¿Hay fotos o vídeo del tramo, unión y material para detectar la corrosión, envejecimiento y el tipo de tubo?",
                "¿Hay urgencia, fin de semana o noche, o es una intervención dentro del horario normal?"
            ]
            return (preguntas_base + preguntas)[:6]

        return [
            "¿Qué tipo de trabajo exacto necesitas: desatasco, llave de paso, llave de escuadra, latiguillo, tramo de tubería, reparación de fuga o cambio de pieza?",
            "¿Es urgente o puede hacerse dentro del horario laboral normal?",
            "¿Qué horario te interesa: dentro de la jornada laboral, fuera del horario laboral, dentro de semana, fin de semana, noche dentro de semana o noche fin de semana?",
            "¿La zona tiene acceso fácil o está difícil de llegar por muebles, pared, falso techo, escaleras o espacio reducido?",
            "¿Necesitas limpieza extra, desinfección, materiales adicionales, desplazamiento extra por kilometraje o trabajos de apertura?",
            "¿Hay fotos o un vídeo del punto exacto para detectar gravedad, material, conexión y complejidad?",
            "¿Quieres que razone y revise referencias en internet para ajustar mejor el precio?"
        ]

    def _preguntas_adicionales_por_contexto(self, texto, respuestas_previas):
        texto_l = str(texto).lower()
        lista = []
        urg = str(respuestas_previas[0]).lower() if len(respuestas_previas) > 0 else ""
        acceso = str(respuestas_previas[1]).lower() if len(respuestas_previas) > 1 else ""
        detalle = str(respuestas_previas[2]).lower() if len(respuestas_previas) > 2 else ""
        fotos = str(respuestas_previas[3]).lower() if len(respuestas_previas) > 3 else ""

        if ("si" in urg or "sí" in urg):
            lista.append("¿Es urgencia inmediata y necesitas que vaya hoy mismo o por la noche?")
        if "no" in acceso or "difícil" in acceso or "poco" in acceso or "escaso" in acceso:
            lista.append("¿Hay que mover muebles, quitar un mueble, abrir un falso techo o es un acceso muy limitado?")
        if "fuga" in texto_l or "llave" in texto_l or "grifo" in texto_l or "latiguillo" in texto_l or "termo" in texto_l:
            if "sí" not in detalle and "si" not in detalle and "cambio" not in detalle and "sustit" not in detalle:
                lista.append("¿Se trata de una fuga activa, un cambio de pieza o solo un desgaste por antigüedad?")
        if ("desatasc" in texto_l or "fregadero" in texto_l or "atasco" in texto_l) and not any(k in texto_l for k in ("latiguillo", "grifo", "fuga", "sustituci", "cambio de pieza", "llave de paso", "manguera")):
            lista.append("¿El agua está totalmente estancada o baja muy lento y con olor?")
        if "no hay fotograf" in fotos or "no fotograf" in fotos or "no hay fotos" in fotos:
            lista.append("¿Puedes describir la zona, el bloqueo, el olor, el retorno de agua o si hay que abrir pared o muebles?")

        # Evitar duplicados y preguntas demasiado repetitivas
        final = []
        visto = set()
        for q in lista:
            clave = q.lower().strip()
            if clave and clave not in visto:
                final.append(q)
                visto.add(clave)
        return final[:3]

    def razonar_precio(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Razonar precio")
        ventana.geometry("520x360")
        ventana.grab_set()
        ventana.transient(self)
        ventana.configure(fg_color="#0d1722")

        ctk.CTkLabel(ventana, text="Revisión de precio", font=("Arial", 22, "bold"), text_color="#edf7ff").pack(anchor="w", padx=18, pady=(18, 10))
        ctk.CTkLabel(ventana, text="Valora si el presupuesto está ajustado y añade contexto antes de cerrar.", font=("Arial", 12), text_color="#bfd2ea").pack(anchor="w", padx=18, pady=(0, 12))

        opciones = [
            ("Me parece muy económico", lambda: self._marcar_razonamiento("muy economico")),
            ("Me parece muy costoso", lambda: self._marcar_razonamiento("muy costoso")),
            ("Adjuntar fotos / vídeos", lambda: (self.adjuntar_archivos_ia(), ventana.destroy())),
            ("Revisar información", lambda: (analizar := self.analizar_con_openrouter(), ventana.destroy())),
        ]

        for idx, (texto, accion) in enumerate(opciones):
            ctk.CTkButton(
                ventana,
                text=texto,
                command=accion,
                fg_color="#1e3a5f" if idx % 2 == 0 else "#2a4f73",
                hover_color="#234a70",
                height=48,
                corner_radius=12,
                font=("Arial", 12, "bold")
            ).pack(fill="x", padx=18, pady=(0, 8))

        ctk.CTkButton(
            ventana,
            text="Cerrar",
            fg_color="#ef4444",
            hover_color="#d93030",
            height=40,
            corner_radius=10,
            command=ventana.destroy,
            font=("Arial", 11, "bold")
        ).pack(fill="x", padx=18, pady=(6, 18))

    def _marcar_razonamiento(self, valor):
        texto = self.txt_desc.get("1.0", "end-1c").strip()
        if not texto:
            messagebox.showwarning("Aviso", "Escribe antes el concepto a revisar.")
            return
        mensaje = f"El precio me parece {valor}. Reviso el alcance real del trabajo, accesos, urgencia, materiales y horario antes de cerrar."
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", f"{texto}\n\n{mensaje}")
        self.comprobar_campos_item()

    def _recalcular_estimacion_parcial(self, texto_trabajo, respuestas_parciales):
        # actualizar etiqueta de proveedor preferido en caso de cambio externo
        try:
            ui_pref = getattr(self, 'ai_preferred_provider', None)
            if ui_pref and hasattr(self, 'lbl_proveedor_actual'):
                self.lbl_proveedor_actual.configure(text=f"Proveedor preferido: {ui_pref}")
        except Exception:
            pass

        """Reconsulta a la IA con la información parcial para ajustar el precio en tiempo real."""
        try:
            texto = str(texto_trabajo).strip()
            if not texto or not respuestas_parciales:
                return
            respuestas = [str(x).strip() for x in respuestas_parciales if str(x).strip()]
            if not respuestas:
                return
            clave_open = self._obtener_clave_openrouter()
            clave_groq = self._obtener_clave_groq()
            if not clave_open and not clave_groq:
                return
            prompt = (
                "Eres un estimador profesional de fontanería para Valencia. "
                "Debes ajustar el presupuesto en tiempo real según la información parcial disponible. "
                "No inventes precios fijos ni valores artificiales. "
                "Analiza el tipo de trabajo, la dificultad de acceso, urgencia/horario, materiales extra, fotos y complejidad. "
                "Si se aportan fotos o video, úsalo como evidencia visual para valorar acceso, piezas, desperfectos, si la zona está oculta, si hay que mover muebles o abrir pared, y si cambia la dificultad real. "
                "Además, interpreta la imagen/vídeo con criterio técnico: si se ve fuga, conexión visible, material antiguo, zona muy ajustada, manguera rota, llave de paso oxidada, falta de acceso, presencia de muebles o pared cerrada, el precio debe subir de forma lógica y justificarlo. "
                "Si se ve una instalación sencilla, con acceso fácil y sin materiales extra, el precio puede mantenerse menor. "
                "Si se trata de latiguillo de WC, usa un rango realista y no uses 300 € por defecto sin base técnica. "
                "Si es un desatasco, llave de escuadra, llave de corte, servicio fuera de horario o fin de semana, ajústalo con criterio real. "
                "Devuelve solo JSON con exactamente: {\"precio_min\": 0, \"precio_max\": 0, \"precio_recomendado\": 0, \"categoria\": \"\", \"observaciones\": \"\"}. "
                f"Trabajo: {texto}\n\nRespuesta parcial del cliente: {respuestas}\n\nFicheros visuales adjuntos: {len(self.archivos_ia) if self.archivos_ia else 0}"
            )
            proveedor = None
            clave = None
            model = None
            pref = str(getattr(self, "ai_preferred_provider", "auto") or "auto").lower()
            if pref == "groq" and clave_groq:
                proveedor = "groq"
                clave = clave_groq
                model = self.groq_model
            elif pref == "local":
                cfg_local = self._obtener_config_local_ai()
                if cfg_local.get("base_url") and cfg_local.get("model"):
                    proveedor = "local"
                    clave = cfg_local["base_url"]
                    model = cfg_local["model"]
            elif clave_open:
                proveedor = "openrouter"
                clave = clave_open
                model = self.openrouter_model
            elif clave_groq:
                proveedor = "groq"
                clave = clave_groq
                model = self.groq_model
            elif self._local_ai_esta_configurado():
                cfg_local = self._obtener_config_local_ai()
                proveedor = "local"
                clave = cfg_local["base_url"]
                model = cfg_local["model"]
            if not proveedor or not clave or not model:
                return
            if proveedor == "groq" and not self._puede_hacer_llamada_ia("groq", cooldown_segundos=8):
                return
            if proveedor == "openrouter" and not self._puede_hacer_llamada_ia("openrouter", cooldown_segundos=8):
                return
            if proveedor == "local" and not self._puede_hacer_llamada_ia("local", cooldown_segundos=8):
                return
            if proveedor == "groq":
                resp = self._request_groq(clave, model, prompt)
            elif proveedor == "local":
                resp = self._request_local_ai(clave, model, prompt)
            else:
                resp = self._request_openrouter(clave, model, prompt)
            if not resp or resp.status_code != 200:
                return
            datos = resp.json()
            contenido = datos.get("choices", [{}])[0].get("message", {}).get("content")
            if isinstance(contenido, list):
                texto_respuesta = "".join(part.get("text", "") for part in contenido if isinstance(part, dict))
            else:
                texto_respuesta = str(contenido)
            parsed = self._parsear_respuesta_openrouter(texto_respuesta)
            if not parsed:
                return
            precio = self._normalizar_precio(parsed.get("precio_recomendado", 0))
            if precio <= 0:
                return

            texto_resumen = " ".join(str(x) for x in respuestas)
            texto_resumen = texto_resumen.lower()
            factor = 1.0
            if any(k in texto_resumen for k in ("urgente", "hoy mismo", "ya mismo", "inmediato")):
                factor *= 1.30
            if any(k in texto_resumen for k in ("fuera de horario laboral", "noche", "nocturno", "fin de semana", "sábado", "domingo")):
                factor *= 1.35
            if any(k in texto_resumen for k in ("acceso difícil", "acceso limitado", "mover muebles", "falso techo", "abrir pared", "poco accesible")):
                factor *= 1.15
            if any(k in texto_resumen for k in ("material extra", "latiguillo", "válvula", "brida", "junta", "llave de paso", "pieza nueva")):
                factor *= 1.15
            if ("latiguillo" in texto_resumen or "manguera" in texto_resumen) and ("wc" in texto_resumen or "inodoro" in texto_resumen or "aseo" in texto_resumen):
                precio = max(precio, 140.0)
            precio *= factor
            self.txt_precio.delete(0, "end")
            self.txt_precio.insert(0, f"{precio:.2f}")
            descripcion_actual = self.txt_desc.get("1.0", "end-1c").strip()
            if descripcion_actual:
                self.txt_desc.delete("1.0", "end")
                titulo = str(parsed.get("categoria") or "Trabajo de fontanería").strip()
                if titulo:
                    self.txt_desc.insert("1.0", f"{titulo}: {descripcion_actual}")
        except Exception:
            pass

    def analizar_con_openrouter(self):
        """Flujo completo del asistente IA con preguntas, proveedor y fallback local."""
        texto = self.txt_desc.get("1.0", "end-1c").strip()
        if not texto:
            messagebox.showwarning("Aviso", "Escribe primero el trabajo que quieres presupuestar.")
            return

        preguntas = self._preguntas_iniciales_por_texto(texto)
        if not preguntas:
            preguntas = [
                "¿Qué tipo de trabajo exacto necesitas: reparación, cambio de pieza, limpieza o desatasco?",
                "¿La zona tiene acceso fácil o está difícil de llegar?",
                "¿Es urgente o puede hacerse dentro del horario laboral normal?",
                "¿Hay fotos o una explicación clara del problema y del material necesario?"
            ]

        # Enriquecer con IA si hay proveedor disponible — evita perder el flujo de preguntas si la API responde bien.
        try:
            preguntas_ia = self._generar_preguntas_con_ia(texto)
            if preguntas_ia:
                preguntas = self._deduplicar_preguntas(preguntas + preguntas_ia)
        except Exception:
            pass

        preguntas = self._deduplicar_preguntas(preguntas)
        if not preguntas:
            preguntas = [
                "¿La zona tiene acceso fácil o está difícil de llegar?",
                "¿Es urgente o puede hacerse dentro del horario laboral normal?",
                "¿Hay fotos o una explicación clara del problema y del material necesario?",
                "¿Necesitas que revise precios y referencias del mercado antes de cerrar?"
            ]

        respuestas = self._preguntas_modal(preguntas)
        if not respuestas:
            # Si el usuario cancela, mantenemos la estimación local para no romper el flujo.
            base_local = self._precio_base_profesional(texto, "", [])
            precio_fallback = float(base_local.get("recomendado", 0) or 0)
            self.txt_precio.delete(0, "end")
            self.txt_precio.insert(0, f"{precio_fallback:.2f}")
            self.comprobar_campos_item()
            return

        respuestas = [str(r).strip() for r in respuestas if str(r).strip()]
        prompt_extra = "\n".join(respuestas)

        # Intento principal con proveedor actual; la lógica local queda separada de la lógica de razonamiento IA.
        claves = self._orden_proveedores_ia()

        referencias_web = self._buscar_web_referencias(f"{texto} presupuesto fontanería Valencia {prompt_extra}", max_results=3)
        contexto_web = ""
        if referencias_web:
            contexto_web = "\nReferencias web verificadas para validar el rango:\n" + "\n".join(
                f"- {r.get('titulo', 'Referencia')}: {r.get('url', '')} | {r.get('snippet', '')[:220]}"
                for r in referencias_web[:3]
            )

        payload = (
            "Eres un consultor técnico profesional de fontanería y precios en Valencia. "
            "Responde solo en JSON con este esquema exacto: {\"titulo\":\"\",\"descripcion\":\"\",\"trabajos\":[\"\"],\"categoria\":\"\",\"precio_min\":0,\"precio_max\":0,\"precio_recomendado\":0,\"cantidad\":1,\"observaciones\":\"\",\"necesita_info\":false,\"preguntas\":[\"\"]}. "
            "Usa el texto del trabajo, la información del cliente y las respuestas del consultor para razonar bien. "
            "Toma muy en cuenta: urgencia, fin de semana, noche dentro de semana, noche fin de semana, fuera del horario laboral, dentro de la jornada laboral, acceso difícil, materiales extra, fotos, piezas, limpieza/desinfección, desplazamiento, kilometraje, trabajo con dificultad añadida o cualquier incidencia por enfermedad/cliente especial. "
            "Si hay urgencia, horario especial, noche o fin de semana, aumenta el precio con criterio real y lo justificas en observaciones y descripción. "
            "Si hay acceso difícil, piezas extra, trabajo sanitario, limpieza especial, distancia, kilometraje o necesidad de desinfectar la zona, debe reflejarse en el precio final. "
            "No uses números fijos ni valores artificiales sin justificar. Revisa el mercado real de Valencia y usa referencias web si están disponibles. "
            f"Trabajo: {texto}\nRespuestas:\n{prompt_extra}{contexto_web}"
        )

        datos_ia = None
        for provider, clave, model in claves:
            if provider == "groq":
                if not self._puede_hacer_llamada_ia("groq", 8):
                    continue
                resp = self._request_groq(clave, model, payload)
            elif provider == "local":
                if not self._puede_hacer_llamada_ia("local", 8):
                    continue
                resp = self._request_local_ai(clave, model, payload)
            else:
                if not self._puede_hacer_llamada_ia("openrouter", 8):
                    continue
                resp = self._request_openrouter(clave, model, payload)
            if not resp or resp.status_code != 200:
                continue
            try:
                datos = resp.json()
                contenido = datos.get("choices", [{}])[0].get("message", {}).get("content")
                if isinstance(contenido, list):
                    texto_resp = "".join(part.get("text", "") for part in contenido if isinstance(part, dict))
                else:
                    texto_resp = str(contenido)
                datos_ia = self._parsear_respuesta_openrouter(texto_resp)
                if datos_ia:
                    break
            except Exception:
                continue

        if datos_ia is None:
            base_local = self._precio_base_profesional(texto, "", [])
            precio_fallback = float(base_local.get("recomendado", 0) or 0)
            precio_fallback = self._aplicar_factores_contexto(precio_fallback, texto, respuestas)
            minimo = max(0.0, float(base_local.get("min", 0) or 0) * 0.9)
            maximo = max(float(base_local.get("max", 0) or 0), precio_fallback)
            descripcion_local = self._descripcion_local_profesional(texto, respuestas)
            self.mostrar_resultado_ia("Trabajo profesional", descripcion_local, minimo, precio_fallback, maximo)
            return

        precio_min = self._normalizar_precio(datos_ia.get("precio_min", 0))
        precio_max = self._normalizar_precio(datos_ia.get("precio_max", 0))
        precio_recomendado = self._normalizar_precio(datos_ia.get("precio_recomendado") or datos_ia.get("precio") or 0)
        if precio_recomendado <= 0:
            precio_recomendado = self._normalizar_precio(precio_min)
        if precio_recomendado <= 0:
            base_local = self._precio_base_profesional(texto, datos_ia.get("categoria", ""), datos_ia.get("trabajos", []))
            precio_recomendado = float(base_local.get("recomendado", 0) or 0)
            precio_min = float(base_local.get("min", 0) or 0)
            precio_max = float(base_local.get("max", 0) or 0)
        precio_min = self._aplicar_factores_contexto(precio_min, texto, respuestas) if precio_min > 0 else precio_min
        precio_max = self._aplicar_factores_contexto(precio_max, texto, respuestas) if precio_max > 0 else precio_max
        precio_recomendado = self._aplicar_factores_contexto(precio_recomendado, texto, respuestas)
        if precio_min <= 0:
            precio_min = min(precio_recomendado, precio_max if precio_max > 0 else precio_recomendado)
        if precio_max <= 0:
            precio_max = max(precio_recomendado, precio_min)
        if precio_max < precio_recomendado:
            precio_max = precio_recomendado
        if precio_min > precio_recomendado:
            precio_min = precio_recomendado * 0.9

        titulo = str(datos_ia.get("titulo") or datos_ia.get("categoria") or "Trabajo de fontanería").strip()
        descripcion = self._formatear_descripcion_ia(datos_ia)
        descripcion = descripcion if descripcion else texto

        self.mostrar_resultado_ia(titulo, descripcion, precio_min, precio_recomendado, precio_max)
        return
    def ver_baremos(self):

        ventana = ctk.CTkToplevel(self)
        ventana.title("📚 Gestor de Baremos PRO")
        ventana.geometry("1400x820")
        ventana.minsize(1200, 700)
        ventana.state("zoomed")
        ventana.grab_set()

        ventana.grid_columnconfigure(0, weight=1)
        ventana.grid_rowconfigure(1, weight=1)
        ventana.grid_rowconfigure(2, weight=0)

        # ==============================
        # BARRA SUPERIOR
        # ==============================

        barra = ctk.CTkFrame(ventana)
        barra.grid(row=0,column=0,padx=10,pady=10,sticky="ew")

        barra.grid_columnconfigure(1,weight=1)

        ctk.CTkLabel(
            barra,
            text="🔍 Buscar:"
        ).grid(row=0,column=0,padx=10)

        buscar = ctk.CTkEntry(
            barra,
            placeholder_text="Nombre, alias, categoría..."
        )

        buscar.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=10
        )

        contador = ctk.CTkLabel(
            barra,
            text=""
        )

        contador.grid(
            row=0,
            column=2,
            padx=10
        )


        # ==============================
        # TABLA
        # ==============================

        columnas=(
            "categoria",
            "nombre",
            "min",
            "max",
            "recomendado",
            "usos"
        )


        frame_tabla=tk.Frame(
            ventana
        )

        frame_tabla.grid(
            row=1,
            column=0,
            padx=10,
            pady=(5, 8),
            sticky="nsew"
        )
        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)


        tree=ttk.Treeview(
            frame_tabla,
            columns=columnas,
            show="headings"
        )


        for col in columnas:

            tree.heading(
                col,
                text=col.capitalize(),
                command=lambda c=col:self.ordenar_baremos(tree,c,False)
            )


        tree.column("categoria",width=150)
        tree.column("nombre",width=400)
        tree.column("min",width=90)
        tree.column("max",width=90)
        tree.column("recomendado",width=120)
        tree.column("usos",width=80)


        scroll=ttk.Scrollbar(
            frame_tabla,
            command=tree.yview
        )

        tree.configure(
            yscrollcommand=scroll.set
        )

        tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scroll.pack(
            side="right",
            fill="y"
        )


        # ==============================
        # DATOS
        # ==============================

        datos_filtrados=[]


        def cargar_tabla(lista):

            tree.delete(*tree.get_children())

            datos_filtrados.clear()

            datos_filtrados.extend(lista)


            for item in lista:

                aprendizaje=item.get(
                    "aprendizaje",
                    {}
                )

                tree.insert(
                    "",
                    "end",
                    values=(

                        item.get("categoria",""),

                        item.get("nombre",""),

                        item.get("precio_min",0),

                        item.get("precio_max",0),

                        item.get(
                            "precio_recomendado",
                            0
                        ),

                        aprendizaje.get(
                            "usos",
                            0
                        )
                    )
                )


            contador.configure(
                text=f"{len(self.baremos)} baremos | {len(lista)} encontrados"
            )



        cargar_tabla(
            self.baremos
        )



        # ==============================
        # BUSCADOR INTELIGENTE
        # ==============================


        def filtrar(event=None):

            texto=buscar.get().lower().strip()


            if not texto:

                cargar_tabla(
                    self.baremos
                )

                return


            resultado=[]


            for item in self.baremos:


                campos=[]

                campos.append(
                    item.get("nombre","")
                )

                campos.append(
                    item.get("categoria","")
                )


                campos+=item.get(
                    "alias",
                    []
                )

                campos+=item.get(
                    "buscar",
                    []
                )


                aprendizaje=item.get(
                    "aprendizaje",
                    {}
                )


                campos+=aprendizaje.get(
                    "palabras_aprendidas",
                    []
                )


                texto_busqueda=" ".join(
                    campos
                ).lower()



                if texto in texto_busqueda:

                    resultado.append(
                        item
                    )


            cargar_tabla(
                resultado
            )


        buscar.bind(
            "<KeyRelease>",
            filtrar
        )


        # ==============================
        # INSPECTOR
        # ==============================


        inspector=ctk.CTkTextbox(
            ventana,
            height=220,
            font=("Consolas",13)
        )

        inspector.grid(
            row=2,
            column=0,
            padx=10,
            pady=(0, 6),
            sticky="ew"
        )

        inspector.configure(
            state="disabled"
        )


        def mostrar_detalle(event=None):

            sel=tree.selection()

            if not sel:
                return


            indice=tree.index(
                sel[0]
            )


            item=datos_filtrados[indice]


            texto=f"""

NOMBRE COMPLETO
-------------------------
{item.get('nombre','')}


CATEGORÍA
-------------------------
{item.get('categoria','')}


ALIAS
-------------------------
{', '.join(item.get('alias',[]))}


PALABRAS BUSQUEDA
-------------------------
{', '.join(item.get('buscar',[]))}


PALABRAS APRENDIDAS
-------------------------
{', '.join(item.get('aprendizaje',{}).get('palabras_aprendidas',[]))}


FECHA APRENDIZAJE
-------------------------
{item.get('aprendizaje',{}).get('ultima_fecha','')}


USOS
-------------------------
{item.get('aprendizaje',{}).get('usos',0)}

"""


            inspector.configure(
                state="normal"
            )

            inspector.delete(
                "1.0",
                "end"
            )

            inspector.insert(
                "1.0",
                texto
            )

            inspector.configure(
                state="disabled"
            )

        tree.bind(
            "<<TreeviewSelect>>",
            mostrar_detalle
        )
        
        tree.bind(
            "<Double-Button-1>",
            lambda e: self.usar_baremo(tree, datos_filtrados, ventana)
        )

        tree.bind(
            "<Return>",
            lambda e: self.usar_baremo(tree, datos_filtrados, ventana)
        )

        tree.bind(
            "<Delete>",
            lambda e: self.eliminar_baremo(tree, datos_filtrados)
        )

        ventana.bind(
            "<Escape>",
            lambda e: ventana.destroy()
        )

        # ==============================
        # BOTONES
        # ==============================
        botones=ctk.CTkFrame(
            ventana
        )
        botones.grid(
            row=3,
            column=0,
            pady=(4, 10)
        )

        ctk.CTkButton(
            botones,
            text="➕ Nuevo baremo",
            height=34,
            font=("Arial", 12, "bold"),
            command=lambda:self.editor_baremo(ventana, None, cargar_tabla)
        ).pack(side="left",padx=5)

        ctk.CTkButton(
            botones,
            text="✏ Editar",
            height=34,
            font=("Arial", 12, "bold"),
            command=lambda:self.editar_desde_tabla(tree, datos_filtrados, ventana, cargar_tabla)
        ).pack(side="left",padx=5)

        ctk.CTkButton(
            botones,
            text="🗑 Eliminar",
            height=34,
            font=("Arial", 12, "bold"),
            fg_color="#aa2222",
            command=lambda:self.eliminar_baremo(tree,datos_filtrados)
        ).pack(side="left",padx=5)

        ctk.CTkButton(
            botones,
            text="📋 Duplicar",
            height=34,
            font=("Arial", 12, "bold"),
            command=lambda: (
                self.duplicar_baremo(datos_filtrados[tree.index(tree.selection()[0])]),
                cargar_tabla(self.baremos),
                self.guardar_baremos_json(False),
                ventana.lift(),
                ventana.focus_force()
            )
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            botones,
            text="❌ Cerrar",
            height=34,
            font=("Arial", 12, "bold"),
            command=ventana.destroy
        ).pack(side="left",padx=5)

    def editar_desde_tabla(self, tree, datos, gestor, actualizar):
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning(
                "Aviso",
                "Selecciona un baremo primero."
            )
            return
        indice = tree.index(
            seleccion[0]
        )
        self.editor_baremo(
            gestor,
            datos[indice],
            actualizar
        )

    def usar_baremo(self, tree, datos_filtrados, ventana):

        sel = tree.selection()

        if not sel:
            return

        indice = tree.index(sel[0])

        item = datos_filtrados[indice]

        precio = item.get(
            "precio_recomendado",
            (item["precio_min"] + item["precio_max"]) / 2
        )

        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", item["nombre"])

        self.txt_precio.delete(0, "end")
        self.txt_precio.insert(0, str(precio))

        self.txt_cant.focus()
        self.txt_cant.select_range(0, "end")

        self.comprobar_campos_item()

        ventana.destroy()
    

    def crear_campo_entrada(self, contenedor, texto):
        ctk.CTkLabel(contenedor, text=texto, font=("Arial", 15, "bold")).pack(pady=(8, 2), padx=20, anchor="w")
        entrada = ctk.CTkEntry(contenedor, height=38, fg_color="#2b2b2b", font=("Arial", 15), border_color="#444444", border_width=1)
        entrada.pack(pady=2, padx=20, fill="x")
        return entrada

    def _guardar_preferencia_proveedor(self, valor):
        """Guarda la preferencia de proveedor en cloud/env.txt como AI_PREFERRED_PROVIDER=valor.
        Si el archivo no existe lo crea. Mantiene otras líneas intactas.
        """
        try:
            base = os.path.dirname(os.path.dirname(__file__))
            ruta_env = os.path.join(base, "cloud", "env.txt")
            os.makedirs(os.path.dirname(ruta_env), exist_ok=True)
            lines = []
            if os.path.exists(ruta_env):
                try:
                    with open(ruta_env, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except Exception:
                    lines = []
            key = "AI_PREFERRED_PROVIDER"
            found = False
            new_lines = []
            for line in lines:
                if not line or "=" not in line:
                    new_lines.append(line)
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                if k == key:
                    new_lines.append(f"{key}={valor}\n")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                if new_lines and not new_lines[-1].endswith("\n"):
                    new_lines[-1] = new_lines[-1] + "\n"
                new_lines.append(f"{key}={valor}\n")
            with open(ruta_env, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception:
            # no fallamos la app por un error al escribir preferencias
            pass

    def cargar_clientes(self):
        if not os.path.exists(self.archivo_clientes):
            return []
        try:
            with open(
                self.archivo_clientes,
                "r",
                encoding="utf-8"
            ) as f:
                return json.load(f)

        except Exception as e:
            messagebox.showerror(
                "Error clientes",
                f"No se pudieron cargar los clientes:\n{e}"
            )
            return []

    def abrir_gestor_clientes(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Gestor de Clientes")
        ventana.geometry("1080x650")
        ventana.minsize(980, 560)
        ventana.configure(fg_color="#0b1117")
        ventana.grab_set()

        ventana.grid_columnconfigure(0, weight=1)
        ventana.grid_columnconfigure(1, weight=1)
        ventana.grid_rowconfigure(1, weight=1)

        campos = {}

        # ==========================
        # FUNCIONES INTERNAS
        # ==========================

        def cargar_lista():
            lista.delete(0, "end")
            for cliente in sorted(self.clientes, key=lambda x: str(x.get("nombre", "")).lower()):
               nombre = str(cliente.get("nombre", "")).strip()
               if nombre:
                   lista.insert("end", nombre)

        def limpiar_campos():
            for campo in campos.values():
               campo.delete(0, "end")
            lista.selection_clear(0, "end")
            self.cliente_actual = self.cliente_vacio()
            self.cliente_seleccionado = None

        def seleccionar_por_nombre(nombre):
            for index, cliente in enumerate(self.clientes):
               if str(cliente.get("nombre", "")).strip().lower() == nombre.lower():
                   self.cliente_actual = cliente
                   self.cliente_seleccionado = cliente
                   for clave in campos:
                       campos[clave].delete(0, "end")
                       campos[clave].insert(0, str(cliente.get(clave, "") or ""))
                   if hasattr(self, "lbl_cliente_actual"):
                       self.lbl_cliente_actual.configure(text=cliente["nombre"])
                   return index
            return None

        def nuevo_cliente():
            limpiar_campos()
            campos["nombre"].focus_set()

        def guardar_cliente(event=None):
            cliente = {
               "nombre": (campos["nombre"].get() or "").strip(),
               "telefono": (campos["telefono"].get() or "").strip(),
               "nif": (campos["nif"].get() or "").strip(),
               "direccion": (campos["direccion"].get() or "").strip(),
               "localidad": (campos["localidad"].get() or "").strip(),
            }

            if not cliente["nombre"]:
               messagebox.showwarning("Aviso", "El nombre es obligatorio")
               campos["nombre"].focus_set()
               return

            indice_existente = None
            for idx, cliente_actual in enumerate(self.clientes):
               if str(cliente_actual.get("nombre", "")).strip().lower() == cliente["nombre"].lower():
                   indice_existente = idx
                   break

            sel = lista.curselection()
            if sel:
               nombre_sel = lista.get(sel)
               for idx, cliente_actual in enumerate(self.clientes):
                   if str(cliente_actual.get("nombre", "")).strip().lower() == nombre_sel.lower():
                       indice_existente = idx
                       break

            if indice_existente is not None:
               self.clientes[indice_existente] = cliente
               accion = "actualizado"
            else:
               self.clientes.append(cliente)
               accion = "guardado"

            try:
               with open(self.archivo_clientes, "w", encoding="utf-8") as f:
                   json.dump(self.clientes, f, indent=4, ensure_ascii=False)
            except Exception as e:
               messagebox.showerror("Error clientes", f"No se pudieron guardar los cambios:\n{e}")
               return

            self.cliente_actual = cliente
            self.cliente_seleccionado = cliente
            if hasattr(self, "lbl_cliente_actual"):
               self.lbl_cliente_actual.configure(text=cliente["nombre"])

            cargar_lista()
            for index, nombre in enumerate([str(c.get("nombre", "")).strip() for c in self.clientes]):
               if str(nombre).lower() == cliente["nombre"].lower():
                   try:
                       lista.selection_clear(0, "end")
                       lista.select_set(index)
                   except Exception:
                       pass
                   break

            messagebox.showinfo("Guardado", f"Cliente {accion} correctamente")
            campos["nombre"].focus_set()

        def seleccionar_cliente(event=None, cerrar_ventana=True):
            sel = lista.curselection()
            if not sel:
               return
            nombre = lista.get(sel)
            seleccionar_por_nombre(nombre)
            if cerrar_ventana:
               ventana.destroy()

        def eliminar_cliente():
            sel = lista.curselection()
            if not sel:
               return

            nombre = lista.get(sel)
            respuesta = messagebox.askyesno("Eliminar", f"¿Eliminar {nombre}?")
            if not respuesta:
               return

            self.clientes = [c for c in self.clientes if str(c.get("nombre", "")).strip().lower() != nombre.lower()]
            try:
               with open(self.archivo_clientes, "w", encoding="utf-8") as f:
                   json.dump(self.clientes, f, indent=4, ensure_ascii=False)
            except Exception as e:
               messagebox.showerror("Error clientes", f"No se pudo eliminar el cliente:\n{e}")
               return

            limpiar_campos()
            cargar_lista()
            messagebox.showinfo("Eliminado", f"Cliente eliminado: {nombre}")

        def cerrar_ventana(event=None):
            ventana.destroy()

        def seleccionar_con_enter(event=None):
            nombre = (campos["nombre"].get() or "").strip()
            if not nombre:
               return
            for cliente in self.clientes:
               if str(cliente.get("nombre", "")).strip().lower() == nombre.lower():
                   self.cliente_actual = cliente
                   self.cliente_seleccionado = cliente
                   if hasattr(self, "lbl_cliente_actual"):
                       self.lbl_cliente_actual.configure(text=cliente["nombre"])
                   ventana.destroy()
                   return
            messagebox.showwarning("Cliente no encontrado", f"No existe el cliente: {nombre}")

        # ==========================
        # INTERFAZ
        # ==========================

        title_bar = ctk.CTkFrame(ventana, fg_color="#0d1720", border_color="#3d7cc2", border_width=2, corner_radius=18)
        title_bar.grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="ew")
        title_bar.grid_columnconfigure(0, weight=1)
        title_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(title_bar, text="👤 Gestor de clientes", font=("Arial", 22, "bold"), text_color="#f5f9ff").grid(row=0, column=0, padx=14, pady=10, sticky="w")
        ctk.CTkLabel(title_bar, text="Datos cliente", font=("Arial", 18, "bold"), text_color="#86d7ff").grid(row=0, column=1, padx=14, pady=10, sticky="e")

        panel_lista = ctk.CTkFrame(ventana, fg_color="#101a22", border_color="#3a5976", border_width=2, corner_radius=18)
        panel_lista.grid(row=1, column=0, padx=(16, 8), pady=(0, 12), sticky="nsew")
        panel_lista.grid_columnconfigure(0, weight=1)
        panel_lista.grid_rowconfigure(1, weight=1)

        lista_header = ctk.CTkFrame(panel_lista, fg_color="#162432", corner_radius=12)
        lista_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        ctk.CTkLabel(lista_header, text="Clientes", font=("Arial", 16, "bold"), text_color="#ecf6ff").pack(padx=12, pady=(8, 6), anchor="w")

        scroll_lista = tk.Scrollbar(panel_lista, orient="vertical", width=12)
        lista = tk.Listbox(
            panel_lista,
            font=("Arial", 13),
            bg="#0f1722",
            fg="#f4fbff",
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            highlightthickness=1,
            highlightcolor="#60a5fa",
            borderwidth=1,
            relief="solid",
            activestyle="none",
            width=34,
            height=14,
            yscrollcommand=scroll_lista.set,
        )
        scroll_lista.config(command=lista.yview)
        lista.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=10)
        scroll_lista.grid(row=1, column=1, sticky="ns", pady=10)
        lista.bind("<Double-Button-1>", lambda e: seleccionar_cliente(cerrar_ventana=True))
        lista.bind("<Return>", lambda e: seleccionar_cliente(cerrar_ventana=True))
        lista.bind("<Escape>", lambda e: cerrar_ventana())

        ventana.bind("<Escape>", cerrar_ventana)

        panel = ctk.CTkFrame(ventana, fg_color="#111a22", border_color="#3a5976", border_width=2, corner_radius=18)
        panel.grid(row=1, column=1, padx=(8, 16), pady=(0, 12), sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)

        form_container = ctk.CTkFrame(panel, fg_color="#111a22")
        form_container.pack(fill="both", expand=True, padx=18, pady=16)

        datos = [
            ("Nombre", "nombre"),
            ("Teléfono", "telefono"),
            ("NIF", "nif"),
            ("Dirección", "direccion"),
            ("Localidad", "localidad")
        ]

        for texto, clave in datos:
            ctk.CTkLabel(form_container, text=texto, font=("Arial", 12, "bold"), text_color="#edf6ff").pack(anchor="w", padx=4, pady=(10, 2))
            entrada = ctk.CTkEntry(
               form_container,
               width=260,
               height=34,
               fg_color="#1b2430",
               border_color="#5f87b2",
               border_width=1,
               text_color="#f8fbff",
               font=("Arial", 13),
               corner_radius=8,
            )
            entrada.pack(fill="x", padx=4, pady=(0, 6))
            entrada.bind("<Return>", guardar_cliente)
            entrada.bind("<Escape>", cerrar_ventana)
            campos[clave] = entrada

        botones = ctk.CTkFrame(panel, fg_color="transparent")
        botones.pack(fill="x", padx=18, pady=(0, 14))
        botones.grid_columnconfigure((0, 1), weight=1)

        buttons_style = dict(height=42, corner_radius=10, border_width=1, font=("Arial", 12, "bold"))
        ctk.CTkButton(botones, text="🆕 Nuevo", command=nuevo_cliente, fg_color="#3b82f6", hover_color="#2563eb", border_color="#bfe1ff", **buttons_style).grid(row=0, column=0, padx=(0, 5), pady=6, sticky="ew")
        ctk.CTkButton(botones, text="💾 Guardar", command=guardar_cliente, fg_color="#16a34a", hover_color="#15803d", border_color="#b7f7c9", **buttons_style).grid(row=0, column=1, padx=(5, 0), pady=6, sticky="ew")
        ctk.CTkButton(botones, text="✔ Seleccionar", command=lambda: seleccionar_cliente(cerrar_ventana=True), fg_color="#2563eb", hover_color="#1d4ed8", border_color="#bfe1ff", **buttons_style).grid(row=1, column=0, padx=(0, 5), pady=6, sticky="ew")
        ctk.CTkButton(botones, text="🗑 Eliminar", command=eliminar_cliente, fg_color="#dc2626", hover_color="#b91c1c", border_color="#fecaca", **buttons_style).grid(row=1, column=1, padx=(5, 0), pady=6, sticky="ew")

        campos["nombre"].focus_set()
        cargar_lista()

    def cargar_baremos(self):
        print("Buscando baremo en:", os.path.abspath(ARCHIVO_BAREMOS))
        if not os.path.exists(ARCHIVO_BAREMOS):
            return []
        try:
            with open(
                ARCHIVO_BAREMOS,
                "r",
                encoding="utf-8"
            ) as f:
                datos = json.load(f)
        except json.JSONDecodeError as e:

            messagebox.showerror(
                "Error en JSON",
                f"El archivo de baremos está roto.\n\nLínea: {e.lineno}\nColumna: {e.colno}"
            )
            return []
        if isinstance(datos,dict):
            datos=list(datos.values())
        print("BAREMOS CARGADOS:",len(datos))
        return datos

    def comprobar_campos_item(self, event=None):

        descripcion = self.txt_desc.get("1.0", "end-1c").strip()
        precio = self.txt_precio.get().strip()
        cantidad = self.txt_cant.get().strip()

        if descripcion and precio and cantidad:
            self.btn_add.configure(state="normal")
        else:
            self.btn_add.configure(state="disabled")

    def buscar_similitud_baremo(self, texto):
        texto = texto.lower().strip()
        mejores = []
        for item in self.baremos:
            palabras_comparar = []
            palabras_comparar.append(
                item.get("nombre","").lower()
            )
            palabras_comparar += [
                x.lower()
                for x in item.get("alias",[])
            ]
            palabras_comparar += [
                x.lower()
                for x in item.get("buscar",[])
            ]
            for palabra in palabras_comparar:
                similitud = difflib.SequenceMatcher(
                    None,
                    texto,
                    palabra
                ).ratio()
                porcentaje = int(similitud * 100)
                if porcentaje >= 55:
                    mejores.append({
                        "item": item,
                        "porcentaje": porcentaje
                    })
        if not mejores:
            return None
        mejores.sort(
            key=lambda x:x["porcentaje"],
            reverse=True
        )
        return mejores[0]

    def buscar_precio_baremo(self, texto):
        def limpiar_texto(valor):
            valor = str(valor or '').lower()
            valor = valor.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ü', 'u').replace('ñ', 'n')
            valor = re.sub(r'[^a-z0-9\s]', ' ', valor)
            valor = re.sub(r'\s+', ' ', valor).strip()
            return valor

        texto_limpio = limpiar_texto(texto)
        palabras_usuario = set(re.findall(r'[a-z0-9]+', texto_limpio))

        resultados = []
        for item in self.baremos:
            puntos = 0
            palabras_detectadas = []
            nombre = limpiar_texto(item.get("nombre", ""))
            alias = [limpiar_texto(v) for v in item.get("alias", [])]
            buscar = [limpiar_texto(v) for v in item.get("buscar", [])]
            palabras = alias + buscar

            for palabra in palabras_usuario:
                if palabra and palabra in nombre:
                    puntos += 15
                    palabras_detectadas.append(palabra)

            for frase in palabras:
                if not frase:
                    continue
                if frase in texto_limpio:
                    puntos += 20
                    palabras_detectadas.append(frase)
                else:
                    for palabra in set(re.findall(r'[a-z0-9]+', frase)):
                        if palabra and palabra in palabras_usuario:
                            puntos += 5
                            palabras_detectadas.append(palabra)

            aprendizaje = item.get("aprendizaje", {})
            for palabra in aprendizaje.get("palabras_aprendidas", []):
                pal = limpiar_texto(palabra)
                if pal and pal in palabras_usuario:
                    puntos += 8
                    palabras_detectadas.append(pal)

            for frase in aprendizaje.get("frases_aprendidas", []):
                frase_clean = limpiar_texto(frase)
                if frase_clean and frase_clean in texto_limpio:
                    puntos += 25
                    palabras_detectadas.append(frase_clean)
                else:
                    for pal in set(re.findall(r'[a-z0-9]+', frase_clean)):
                        if pal and pal in palabras_usuario and len(pal) > 2:
                            puntos += 4
                            palabras_detectadas.append(pal)

            if puntos > 0:
                resultados.append({
                    "item": item,
                    "puntos": puntos,
                    "detectadas": list(set(palabras_detectadas))
                })

        if not resultados:
            parecido = self.buscar_similitud_baremo(texto_limpio)
            if parecido:
                return parecido
            return None

        resultados.sort(key=lambda x: x["puntos"], reverse=True)
        mejor = resultados[0]
        mejor["porcentaje"] = min(mejor["puntos"] * 5, 99)
        return mejor

    def mostrar_sugerencia_precio(self, resultado):
        # 📍 1. Capturamos EL TEXTO ORIGINAL justo al entrar a la función
        texto_original = self.txt_desc.get("1.0", "end-1c").strip()

        sugerencia = resultado["item"]
        porcentaje = resultado["porcentaje"]
        precio = sugerencia.get(
            "precio_recomendado",
            sugerencia.get(
                "precio_sugerido",
                (sugerencia["precio_min"] + sugerencia["precio_max"]) / 2
            )
        )

        ventana = ctk.CTkToplevel(self)
        ventana.title("🤖 Inteligencia Gestor Pro")
        ventana.geometry("620x420")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.transient(self)
        ventana.configure(fg_color="#0f1723")

        try:
            ventana.update_idletasks()
            sw = ventana.winfo_screenwidth()
            sh = ventana.winfo_screenheight()
            ww = ventana.winfo_width()
            wh = ventana.winfo_height()
            x = int((sw - ww) / 2)
            y = int((sh - wh) / 2)
            ventana.geometry(f"+{x}+{y}")
        except Exception:
            pass

        frame = ctk.CTkFrame(ventana, fg_color="#111922", corner_radius=20, border_color="#29415d", border_width=1)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text="Inteligencia Gestor Pro", font=("Arial", 22, "bold"), text_color="#edf7ff", anchor="w").pack(anchor="w", padx=18, pady=(18, 10))

        txt = tk.Text(frame, height=11, bg="#0b1220", fg="#edf6ff", relief="flat", borderwidth=0, padx=14, pady=12, insertbackground="#ffffff", font=("Arial", 11))
        txt.insert("1.0", f"""
Coincidencia:
{porcentaje}%
Trabajo:
{sugerencia['nombre']}
Categoría:
{sugerencia.get('categoria','')}
Precio mínimo:
{sugerencia['precio_min']} €
Precio máximo:
{sugerencia['precio_max']} €
Precio recomendado:
{precio} €

¿Es este trabajo?
""")
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(0, 14))

        decision = {"respuesta": False}

        def cerrar(valor):
            decision["respuesta"] = valor
            ventana.destroy()

        ctk.CTkButton(btns, text="Sí, es este", fg_color="#22a55f", hover_color="#1c9c53", border_color="#8ef1c3", border_width=1, width=170, height=42, corner_radius=12, command=lambda: cerrar(True), font=("Arial", 11, "bold")).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="No", fg_color="#ef4444", hover_color="#d93030", border_color="#fca5a5", border_width=1, width=110, height=42, corner_radius=12, command=lambda: cerrar(False), font=("Arial", 11, "bold")).pack(side="right")

        ventana.bind("<Return>", lambda event: cerrar(True))
        ventana.bind("<Escape>", lambda event: cerrar(False))
        ventana.focus_force()
        ventana.wait_window()

        respuesta = decision["respuesta"]

        if respuesta:
            frases_aprendidas = [texto_original] + (resultado.get("detectadas", []) if isinstance(resultado, dict) else [])
            self.aprender_confirmacion(
                sugerencia,
                frases_aprendidas
            )
            self.txt_desc.delete("1.0", "end")
            self.txt_desc.insert("1.0", sugerencia["nombre"])

            self.txt_precio.delete(0, "end")
            self.txt_precio.insert(0, str(precio))

            self.comprobar_campos_item()
            return True

        # -------------------------------------------------------------------
        # SI DICE QUE NO
        # -------------------------------------------------------------------
        nueva_descripcion = ctk.CTkInputDialog(
            text="No parece correcto.\nEscribe el trabajo correcto:",
            title="Corregir trabajo"
        ).get_input()

        if nueva_descripcion:
            # Volver a analizar la corrección
            resultado_nuevo = self.buscar_precio_baremo(nueva_descripcion)

            if resultado_nuevo:
                trabajo = resultado_nuevo["item"]
                precio_corr = trabajo.get(
                    "precio_recomendado",
                    (trabajo["precio_min"] + trabajo["precio_max"]) / 2
                )

                aceptar = messagebox.askyesno(
                    "Corrección encontrada",
    f"""
    He encontrado este trabajo:
    {trabajo['nombre']}
    Precio recomendado:
    {precio_corr} €

    ¿Es este?
    """
                )
                if aceptar:
                    self.txt_desc.delete("1.0", "end")
                    self.txt_desc.insert("1.0", trabajo["nombre"])

                    self.txt_precio.delete(0, "end")
                    self.txt_precio.insert(0, str(precio_corr))

                    # Guardamos el texto original erróneo + la búsqueda corregida
                    self.aprender_confirmacion(
                        trabajo,
                        [texto_original, nueva_descripcion]
                    )
                    self.comprobar_campos_item()
                    return True # 👈 CAMBIO 2: Retornamos True porque se completó con éxito la corrección

        self.comprobar_campos_item()
        return False

    def _formatear_descripcion_tabla(self, descripcion):
        texto = descripcion.strip()
        if not texto:
            return ""

        lineas = []
        for bloque in texto.splitlines():
            if not bloque.strip():
                continue
            lineas.extend(textwrap.wrap(
                bloque.strip(),
                width=28,
                break_long_words=False,
                break_on_hyphens=False
            ))

        return "\n".join(lineas) if lineas else ""

    def _seleccionar_fila(self, index):
        self.selected_item_index = index
        for row_index, row in enumerate(self.item_rows):
            row.configure(bg="#1e5a8a" if row_index == index else "#2b6da8")
            for child in row.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg="#1e5a8a" if row_index == index else "#2b6da8")

    def _ajustar_ancho_fila(self, row, desc_label):
        try:
            row.update_idletasks()
            ancho_total = max(300, row.winfo_width())
            ancho_valores = max(150, int(ancho_total * 0.30))
            ancho_desc = max(220, ancho_total - ancho_valores - 30)
            desc_label.configure(wraplength=max(220, ancho_desc))
        except Exception:
            pass

    def _agregar_fila_presupuesto(self, descripcion, precio, cantidad, total):
        row_index = len(self.item_rows)
        row = tk.Frame(self.items_container, bg="#101820", padx=0, pady=0, highlightthickness=0)
        row.grid(row=row_index + 1, column=0, sticky="ew", pady=(0, 6))
        row.grid_columnconfigure(0, weight=7, minsize=420)
        row.grid_columnconfigure(1, weight=3, minsize=250)

        lineas_desc = max(2, len(textwrap.wrap(descripcion.strip(), width=34, break_long_words=False, break_on_hyphens=False)))
        altura_fila = min(240, max(120, lineas_desc * 22 + 36))

        desc_box = tk.Frame(row, bg="#2b6da8", padx=0, pady=0, highlightbackground="#9ed7ff", highlightthickness=2, bd=0, height=altura_fila)
        desc_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        desc_box.grid_propagate(False)
        desc_label = tk.Label(
            desc_box,
            text=descripcion,
            bg="#2b6da8",
            fg="#edf7ff",
            justify="left",
            anchor="w",
            wraplength=430,
            font=("Arial", 11, "normal"),
            padx=10,
            pady=10,
            compound="left"
        )
        desc_label.pack(fill="both", expand=True)

        values_box = tk.Frame(row, bg="#2b6da8", highlightbackground="#9ed7ff", highlightthickness=2, height=altura_fila)
        values_box.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        values_box.grid_propagate(False)
        values_box.grid_columnconfigure(0, weight=1, minsize=70)
        values_box.grid_columnconfigure(1, weight=1, minsize=70)
        values_box.grid_columnconfigure(2, weight=1, minsize=70)
        values_box.grid_rowconfigure(0, weight=1)

        def crear_celda(parent, col, valor):
            cell = tk.Frame(parent, bg="#2b6da8", highlightbackground="#a8deff", highlightthickness=1)
            cell.grid(row=0, column=col, sticky="nsew", padx=(0, 2), pady=0)
            cell.grid_propagate(False)
            label = tk.Label(
                cell,
                text=valor,
                bg="#2b6da8",
                fg="#edf7ff",
                font=("Arial", 11, "bold"),
                anchor="center",
                justify="center",
                pady=8,
            )
            label.pack(fill="both", expand=True, padx=0, pady=0)
            return label

        precio_label = crear_celda(values_box, 0, f"{precio:.2f}")
        cant_label = crear_celda(values_box, 1, str(cantidad))
        total_label = crear_celda(values_box, 2, f"{total:.2f}")

        row.bind("<Button-1>", lambda event, idx=row_index: self._seleccionar_fila(idx))
        desc_label.bind("<Button-1>", lambda event, idx=row_index: self._seleccionar_fila(idx))
        precio_label.bind("<Button-1>", lambda event, idx=row_index: self._seleccionar_fila(idx))
        cant_label.bind("<Button-1>", lambda event, idx=row_index: self._seleccionar_fila(idx))
        total_label.bind("<Button-1>", lambda event, idx=row_index: self._seleccionar_fila(idx))

        self.item_rows.append(row)

    def añadir_item(self):
        descripcion = self.txt_desc.get("1.0", "end-1c").strip()
        if not descripcion:
            messagebox.showwarning(
                "Aviso",
                "Escribe una descripción del trabajo."
            )
            return

        try:

            precio_texto = self.txt_precio.get().strip()

            # SI NO HAY PRECIO BUSCAMOS EN BAREMO
            if not precio_texto:

                sugerencia = self.buscar_precio_baremo(descripcion)

                if sugerencia:

                    aceptado = self.mostrar_sugerencia_precio(sugerencia)

                    if aceptado:
                        precio = sugerencia.get("precio_recomendado")
                        if precio is None:
                            precio = (
                                sugerencia.get("precio_min", 0) +
                                sugerencia.get("precio_max", 0)
                            ) / 2
                        precio = float(precio)

                        # usar la descripción oficial
                        descripcion = sugerencia["nombre"]

                        # actualizar el cuadro de texto para que el usuario lo vea
                        self.txt_desc.delete("1.0", "end")
                        self.txt_desc.insert("1.0", descripcion)

                    else:
                        # dejamos al usuario corregir manualmente
                        self.txt_precio.focus()
                        return

                else:
                    messagebox.showwarning(
                        "Sin coincidencia",
                        "No se encontró ningún trabajo en el baremo."
                    )
                    return

            else:
                # PRECIO MANUAL
                precio = float(
                    precio_texto.replace(",", ".")
                )

            cantidad = int(self.txt_cant.get())
            total = precio * cantidad

            self.items_presupuesto.append({
                "desc": descripcion,
                "precio": precio,
                "cant": cantidad,
                "total": total
            })

            descripcion_visible = self._formatear_descripcion_tabla(descripcion)
            self._agregar_fila_presupuesto(descripcion_visible, precio, cantidad, total)
            self.actualizar_totales_ui()

            self.txt_desc.delete("1.0", "end")
            self.txt_precio.delete(0, "end")
            self.txt_cant.delete(0, "end")
            self.txt_cant.insert(0, "1")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Revisa los valores.\n\n{e}"
            )

        self.comprobar_campos_item()
    def analizar_trabajo(self):
        texto = self.txt_desc.get("1.0", "end-1c").strip()
        if not texto:
            messagebox.showwarning("Aviso", "Escribe primero el trabajo a analizar.")
            return

        resultado = self.buscar_precio_baremo(texto)
        if resultado:
            aceptado = self.mostrar_sugerencia_precio(resultado)
            if aceptado:
                self.añadir_item()
                return
        else:
            messagebox.showinfo("Sin resultado", "No encuentro este trabajo todavía.")
            self.aprender_nuevo_trabajo(texto)


    def aprender_nuevo_trabajo(self, texto):
        respuesta = messagebox.askyesno(
            "Nuevo trabajo",
            f"No conozco:\n\n{texto}\n\n¿Quieres añadirlo al aprendizaje?"
        )
        if not respuesta:
            correccion = ctk.CTkInputDialog(
                text="Escribe la palabra correcta:",
                title="Corregir aprendizaje"
            ).get_input()
            if correccion:
                resultado = self.buscar_precio_baremo(
                    correccion
                )
                if resultado:
                    aceptar = messagebox.askyesno(
                        "Trabajo encontrado",
                        f"""
        He encontrado:
        {resultado['item']['nombre']}
        ¿Es este el trabajo correcto?
        """
                    )
                    if aceptar:
                        trabajo = resultado["item"]
                        if not trabajo.get("aprendizaje"):
                            trabajo["aprendizaje"] = self.crear_aprendizaje_vacio()
                        if "palabras_aprendidas" not in trabajo["aprendizaje"]:
                            trabajo["aprendizaje"]["palabras_aprendidas"] = []
                        palabra = texto.lower().strip()
                        if palabra not in trabajo["aprendizaje"]["palabras_aprendidas"]:
                            trabajo["aprendizaje"]["palabras_aprendidas"].append(
                                palabra
                            )
                        trabajo["aprendizaje"]["usos"] += 1
                        self.guardar_baremos_json(False)
                        print(
                            "NUEVO APRENDIZAJE GUARDADO",
                            texto,
                            "->",
                            trabajo["nombre"]
                        )
                        messagebox.showinfo(
                            "Aprendido",
                            f"Ahora reconoceré:\n\n{texto}\n\ncomo:\n{trabajo['nombre']}"
                        )
                else:
                    messagebox.showinfo(
                        "Sin coincidencia",
                        "No encontré esa corrección en el baremo."
                    )
            return

        ventana = ctk.CTkToplevel(self)
        ventana.title("🤖 Aprender nuevo trabajo")
        ventana.geometry("500x650")

        ventana.grab_set()


        campos = {}


        def crear_campo(nombre, clave):

            ctk.CTkLabel(
                ventana,
                text=nombre,
                font=("Arial",15,"bold")
            ).pack(
                anchor="w",
                padx=30,
                pady=(10,0)
            )


            entrada = ctk.CTkEntry(
                ventana,
                height=35,
                font=("Arial",14)
            )

            entrada.pack(
                fill="x",
                padx=30,
                pady=5
            )

            campos[clave] = entrada
        # -----------------------------
        # CAMPOS
        # -----------------------------
        crear_campo(
            "Nombre correcto del trabajo:",
            "nombre"
        )

        campos["nombre"].insert(
            0,
            texto
        )


        crear_campo(
            "Categoría:",
            "categoria"
        )


        crear_campo(
            "Precio mínimo:",
            "precio_min"
        )


        crear_campo(
            "Precio máximo:",
            "precio_max"
        )


        crear_campo(
            "Precio recomendado:",
            "precio_recomendado"
        )


        crear_campo(
            "Palabras alternativas (separadas por comas):",
            "alias"
        )


        # -----------------------------
        # GUARDAR
        # -----------------------------


        def guardar():

            nombre = campos["nombre"].get().strip()


            if not nombre:

                messagebox.showwarning(
                    "Aviso",
                    "El nombre del trabajo es obligatorio."
                )

                return


            try:

                precio_min = float(
                    campos["precio_min"].get()
                    .replace(",", ".")
                    or 0
                )

                precio_max = float(
                    campos["precio_max"].get()
                    .replace(",", ".")
                    or 0
                )

                precio_recomendado = float(
                    campos["precio_recomendado"].get()
                    .replace(",", ".")
                    or ((precio_min + precio_max)/2)
                )

            except:
                messagebox.showerror(
                    "Error",
                    "Revisa los precios."
                )

                return
            alias_texto = campos["alias"].get().strip()
            alias = []
            if alias_texto:
                alias = [
                    palabra.strip().lower()
                    for palabra in alias_texto.split(",")
                    if palabra.strip()
                ]
            nuevo = {
                "categoria":
                    campos["categoria"].get().strip()
                    or "Aprendido automáticamente",
                "nombre":
                    nombre,
                "alias":
                    alias,
                "buscar":
                    [],
                "precio_min":
                    precio_min,
                "precio_max":
                    precio_max,
                "precio_recomendado":
                    precio_recomendado,
                "aprendizaje":{
                    "usos":1,
                    "palabras_aprendidas":
                        [texto.lower()],
                    "frases_aprendidas":[],
                    "ultima_fecha":
                        datetime.now().strftime("%d/%m/%Y")
                }
            }
            self.baremos.append(
                nuevo
            )
            with open(
                ARCHIVO_BAREMOS,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    self.baremos,
                    f,
                    indent=4,
                    ensure_ascii=False
                )
            messagebox.showinfo(
                "Aprendido",
                f"Nuevo trabajo guardado:\n\n{nombre}"
            )
            ventana.destroy()

        ctk.CTkButton(
            ventana,
            text="💾 Guardar aprendizaje",
            height=45,
            fg_color="#00aa66",
            font=("Arial",16,"bold"),
            command=guardar
        ).pack(
            fill="x",
            padx=30,
            pady=25
        )

    def aprender_confirmacion(self, trabajo, palabras):
        if "aprendizaje" not in trabajo:
            trabajo["aprendizaje"] = self.crear_aprendizaje_vacio()
        aprendizaje = trabajo["aprendizaje"]
        if "palabras_aprendidas" not in aprendizaje:
            aprendizaje["palabras_aprendidas"] = []
        if "frases_aprendidas" not in aprendizaje:
            aprendizaje["frases_aprendidas"] = []
        if "usos" not in aprendizaje:
            aprendizaje["usos"] = 0
        for texto in palabras:
            texto = texto.lower().strip()
            if not texto:
                continue
            # FRASES DE DOS O MÁS PALABRAS
            if len(texto.split()) > 1:
                if texto not in aprendizaje["frases_aprendidas"]:
                    aprendizaje["frases_aprendidas"].append(texto)
            # PALABRAS SUELTAS
            else:
                if texto not in aprendizaje["palabras_aprendidas"]:
                    aprendizaje["palabras_aprendidas"].append(texto)
        aprendizaje["usos"] += 1
        aprendizaje["ultima_fecha"] = datetime.now().strftime("%d/%m/%Y")
        self.guardar_baremos_json(False)
        print(
            "APRENDIZAJE GUARDADO:",
            trabajo["nombre"],
            aprendizaje
        )

    def editor_baremo(self, gestor=None, baremo=None, actualizar=None):
        if gestor:
            ventana = ctk.CTkToplevel(gestor)
        else:
            ventana = ctk.CTkToplevel(self)
        ventana.title("Editor de baremo")
        ventana.geometry("900x720")
        ventana.minsize(760, 620)
        ventana.grab_set()
        campos = {}
        datos = [
            ("Nombre", "nombre"),
            ("Categoría", "categoria"),
            ("Precio mínimo", "precio_min"),
            ("Precio máximo", "precio_max"),
            ("Precio recomendado", "precio_recomendado"),
            ("Alias separados por comas", "alias")
        ]
        for texto, clave in datos:

            ctk.CTkLabel(
                ventana,
                text=texto,
                font=("Arial",14,"bold")
            ).pack(
                anchor="w",
                padx=30,
                pady=(10,0)
            )

            entrada = ctk.CTkEntry(
                ventana,
                height=35
            )

            entrada.pack(
                fill="x",
                padx=30,
                pady=5
            )

            campos[clave]=entrada
        # cargar datos si es editar
        if baremo:
            for clave in campos:
                valor = baremo.get(clave,"")
                if clave == "alias":
                    valor = ", ".join(
                        baremo.get("alias",[])
                    )
                campos[clave].insert(
                    0,
                    str(valor)
                )

        def guardar():
            try:
                nuevo = {
                    "categoria":
                        campos["categoria"].get(),
                    "nombre":
                        campos["nombre"].get(),
                    "alias":
                        [
                            x.strip().lower()
                            for x in campos["alias"].get().split(",")
                            if x.strip()
                        ],
                    "buscar": [],
                    "precio_min":
                        float(
                            campos["precio_min"].get()
                            .replace(",", ".")
                        ),

                    "precio_max":
                        float(
                            campos["precio_max"].get()
                            .replace(",", ".")
                        ),

                    "precio_recomendado":
                        float(
                            campos["precio_recomendado"].get()
                            .replace(",", ".")
                        ),

                    "aprendizaje":
                        baremo.get(
                            "aprendizaje",
                            self.crear_aprendizaje_vacio()
                        )
                        if baremo
                        else self.crear_aprendizaje_vacio()
                }

                if baremo is not None:
                    indice = self.baremos.index(baremo)
                    self.baremos[indice] = nuevo
                else:
                    self.baremos.append(nuevo)
                self.guardar_baremos_json(False)
                if actualizar:
                    actualizar(self.baremos)
                ventana.destroy()
                if gestor:
                    gestor.lift()
                    gestor.focus_force()

            except Exception as e:

                messagebox.showerror(
                    "Error",
                    str(e)
                )


        ctk.CTkButton(
            ventana,
            text="💾 Guardar",
            fg_color="#008844",
            height=45,
            command=guardar
        ).pack(
            fill="x",
            padx=30,
            pady=20
        )


    def duplicar_baremo(self, baremo):

        copia = json.loads(json.dumps(baremo))

        copia["nombre"] += " (copia)"

        self.baremos.append(copia)

        messagebox.showinfo(
            "Duplicado",
            "Baremo duplicado correctamente."
        )


    def eliminar_baremo(self, tree, datos_filtrados):

        seleccion = tree.selection()

        if not seleccion:
            return


        indice = tree.index(
            seleccion[0]
        )

        baremo = datos_filtrados[indice]


        confirmar = messagebox.askyesno(
            "Eliminar",
            f"¿Eliminar {baremo['nombre']}?"
        )


        if confirmar:

            self.baremos.remove(
                baremo
            )

            self.guardar_baremos_json(False)
            tree.delete(
                seleccion[0]
            )
            tree.winfo_toplevel().lift()
            tree.winfo_toplevel().focus_force()

    def eliminar_item(self):
        if self.selected_item_index is None:
            if self.item_rows:
                self.selected_item_index = len(self.item_rows) - 1
            else:
                return

        indice = self.selected_item_index
        if 0 <= indice < len(self.items_presupuesto):
            self.items_presupuesto.pop(indice)
        if 0 <= indice < len(self.item_rows):
            row = self.item_rows.pop(indice)
            row.destroy()
            for i in range(indice, len(self.item_rows)):
                self.item_rows[i].configure(bg="#2b6da8")
                for child in self.item_rows[i].winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg="#2b6da8")
            self.selected_item_index = None if not self.item_rows else max(0, indice - 1)
        self.actualizar_totales_ui()

    def actualizar_totales_ui(self):
        subtotal = sum(item["total"] for item in self.items_presupuesto)
        iva = subtotal * 0.21
        total = subtotal + iva
        self.lbl_totales_ui.configure(text=f"Subtotal: {subtotal:.2f} € | IVA: {iva:.2f} € | TOTAL: {total:.2f} €")

    def limpiar_todo(self):

        # Limpiar cliente seleccionado
        self.cliente_actual = self.cliente_vacio()

        self.cliente_seleccionado = None

        self.lbl_cliente_actual.configure(
            text="Sin cliente seleccionado"
        )

        # Limpiar concepto
        self.txt_desc.delete("1.0", "end")
        self.txt_precio.delete(0, "end")
        self.txt_cant.delete(0, "end")
        self.txt_cant.insert(0, "1")

        # Vaciar presupuesto
        self.items_presupuesto.clear()
        self.selected_item_index = None

        for row in list(self.item_rows):
            row.destroy()
        self.item_rows.clear()

        # Reiniciar interfaz
        self.actualizar_totales_ui()

        messagebox.showinfo(
            "Limpieza",
            "Todos los datos han sido borrados."
        )

    def abrir_carpeta_pdf(self):
        """Crea la carpeta 'presupuestos_pdf' en la raíz del proyecto si no existe y la abre."""
        # 1. Obtener la ruta del directorio raíz (donde se ejecuta la app)
        # Usamos os.getcwd() para asegurar que apunte a la carpeta base del ejecutable/script
        ruta_raiz = os.getcwd() 
        carpeta_pdf = os.path.join(ruta_raiz, "presupuestos_pdf")

        # 2. Si la carpeta no existe, la crea automáticamente
        if not os.path.exists(carpeta_pdf):
            os.makedirs(carpeta_pdf, exist_ok=True)

        # 3. Abrir la carpeta en el explorador de archivos
        try:
            if os.name == 'nt':  # Windows
                os.startfile(carpeta_pdf)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', carpeta_pdf])
            else:  # Linux
                subprocess.run(['xdg-open', carpeta_pdf])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{e}")

    def generar_pdf_presupuesto(self):
        numero = datetime.now().strftime("%Y%m%d-%H%M%S") 
        ruta_pdf = os.path.join(CARPETA_PRESUPUESTOS, f"Presupuesto_{numero}.pdf")
        NARANJA = colors.HexColor("#FF9900")
        NEGRO = colors.HexColor("#424242")
        estilos = getSampleStyleSheet()

        # Función para dibujar el pie de página fijo al fondo
        def footer(canvas, doc):
            canvas.saveState()
            
            # --- POSICIÓN BASE DEL BLOQUE ---
            y_base = 80 
            
            # 1. Título de Instrucciones
            canvas.setFont("Helvetica-Bold", 10)
            canvas.setFillColor(NARANJA)
            canvas.drawString(30, y_base, "INSTRUCCIONES PARA ACEPTAR TRABAJO:")
            
            # 2. Instrucciones (Texto compacto)
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(NEGRO)
            canvas.drawString(30, y_base - 13, "Contacte al 663675275 - 641087348 o escriba a tatan4676@gmail.com")
            canvas.drawString(30, y_base - 24, "indicando su nombre y el trabajo a realizar.")
            
            # 3. Garantía (Justo debajo y alineado)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(30, y_base - 40, "GARANTÍA:")
            canvas.setFont("Helvetica", 9)
            canvas.drawString(85, y_base - 40, "6 meses en mano de obra.")
            # -------------------------------------------------------------

            # Elementos decorativos (Barra y Eslogan)
            canvas.setStrokeColor(NARANJA)
            canvas.setLineWidth(3)
            canvas.line(30, 25, 565, 25)

            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(NEGRO)
            canvas.drawCentredString(297.5, 10, "Profesionalidad y calidad garantizada en cada proyecto.")

            canvas.restoreState()

        # Configuración del documento
        doc = BaseDocTemplate(ruta_pdf, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=120)
        frame = Frame(30, 200, 540, 600, showBoundary=0)
        doc.addPageTemplates([PageTemplate(id='base', frames=frame, onPage=footer)])
        
        el = []
        
        logo = ""

        if os.path.exists("assets/logo.png"):
            logo = RLImage("assets/logo.png", width=95, height=95)
        cabecera_der = Paragraph(f"""
        <para alignment="right" leading="20">
            <font size="24" color="{NARANJA}"><b>PRESUPUESTO</b></font><br/>
            <font size="11" color="black">
            Nº {numero}<br/>
            Fecha: {datetime.now().strftime('%d/%m/%Y')}
            </font>
        </para>
        """, estilos["Normal"])

        cabecera = Table(
            [[logo, cabecera_der]],
            colWidths=[90, 450]
        )

        cabecera.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
        ]))

        el.append(cabecera)

        el.append(
            Table(
                [[""]],
                colWidths=[540],
                style=[
                    ("LINEBELOW",(0,0),(-1,-1),2.5,NARANJA)
                ]
            )
        )

        el.append(Spacer(1,12))

        # 2. DATOS
        emp_text = f"<b>DE NUESTRA EMPRESA:</b><br/>Jhonatan Mauricio Giraldo Alzate<br/>NIF: Y8168681S<br/>Avda Blasco Ibáñez 86, Valencia 46021<br/>Tel: 663675275 - 641087348<br/>tatan4676@gmail.com"
        
        # Aquí construimos el bloque del cliente con la localidad debajo de la dirección
        cli_text = (
            f"<b>PRESUPUESTO PARA:</b><br/>"
            f"<b>Nombre:</b> {self.cliente_actual.get('nombre', '')}<br/>"
            f"<b>Teléfono:</b> {self.cliente_actual.get('telefono', '')}<br/>"
            f"<b>DNI / NIE / NIF:</b> {self.cliente_actual.get('nif', '')}<br/>"
            f"<b>Dirección:</b> {self.cliente_actual.get('direccion', '')}<br/>"
            f"<b>Localidad:</b> {self.cliente_actual.get('localidad', '')}"
        )
        
        el.append(Table([[Paragraph(emp_text, estilos["Normal"]), Paragraph(cli_text, estilos["Normal"])]], colWidths=[270, 270], style=[('VALIGN', (0,0), (-1,-1), 'TOP')]))
        el.append(Spacer(1, 15))

        # ==========================================================
        # TABLA DE CONCEPTOS
        # ==========================================================

        datos = [["DESCRIPCIÓN", "PRECIO", "CANT.", "TOTAL"]]

        for i in self.items_presupuesto:
            texto_formateado = i["desc"].replace("\n", "<br/>")
            desc_parrafo = Paragraph(texto_formateado, estilos["Normal"])
            datos.append([
                desc_parrafo,
                f"{i['precio']:.2f} €",
                str(i["cant"]),
                f"{i['total']:.2f} €"
            ])

        # --- AQUÍ AÑADIMOS LOS TOTALES COMO FILAS DE LA MISMA TABLA ---
        sub = sum(i["total"] for i in self.items_presupuesto)
        iva = sub * 0.21
        total = sub + iva

        datos.append(["", "", "Subtotal:", f"{sub:.2f} €"])
        datos.append(["", "", "IVA (21%):", f"{iva:.2f} €"])
        datos.append(["", "", "TOTAL:", f"{total:.2f} €"])

        # Crear tabla (el mismo tamaño de columnas)
        t = Table(datos, colWidths=[255, 85, 55, 145])

        estilo_tabla = TableStyle([
            # 1. Cabecera (Gris #3F3F46, letra blanca)
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3F3F46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            
            # 2. Datos (Bordes #696969)
            ("GRID", (0, 0), (-1, -4), 0.5, colors.HexColor("#696969")),
            ("FONTNAME", (0, 1), (-1, -4), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -4), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            
            # 3. Bloque de totales alineado
            ("FONTNAME", (2, -3), (3, -1), "Helvetica-Bold"),
            ("ALIGN", (2, -3), (2, -1), "RIGHT"),
            ("ALIGN", (3, -3), (3, -1), "RIGHT"),

            # Separación entre etiqueta e importe
            ("RIGHTPADDING", (2, -3), (2, -1), 8),
            ("LEFTPADDING", (3, -3), (3, -1), 8),

            # TOTAL resaltado
            ("BACKGROUND", (2, -1), (3, -1), colors.HexColor("#FF9900")),
            ("TEXTCOLOR", (2, -1), (3, -1), colors.white),
        ])

        t.setStyle(estilo_tabla)

        # Añadimos la tabla directamente al documento
        el.append(t)

        doc.build(el)
        messagebox.showinfo("Éxito", "Presupuesto generado.")
