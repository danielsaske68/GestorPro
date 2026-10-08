import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from tkcalendar import DateEntry
import os
import sys
import json
import subprocess
import locale
import re
from datetime import datetime

from modules.modelos_aeat import get_model_config, get_current_year, SUPPORTED_YEARS

from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ==============================================================
# PALETA
# ==============================================================
COLOR_BG        = "#101820"
COLOR_CARD      = "#171f2a"
COLOR_CARD_ALT  = "#1d2733"
COLOR_BORDER    = "#2d435d"
COLOR_ROW       = "#1d2733"
COLOR_BLUE      = "#0f6cbd"
COLOR_BLUE_HOV  = "#0d5ea8"
COLOR_RED       = "#d63031"
COLOR_RED_HOV   = "#b71c1c"
COLOR_GRAY_BTN  = "#3d4b59"
COLOR_GRAY_HOV  = "#4f5e70"
COLOR_GREEN     = "#2dd881"
COLOR_TEXT      = "#edf4ff"
COLOR_MUTED     = "#9bb7d3"


class ReadOnlyDropdown:
    def __init__(self, master, values, command=None, width=200, height=34, fg_color="#1d2f44", button_color=COLOR_BLUE, text_color="#edf4ff", border_color=COLOR_BORDER, placeholder=None):
        self.values = list(values)
        self.command = command
        self.placeholder = placeholder
        self.current = self.placeholder if self.placeholder is not None else (self.values[0] if self.values else "")

        self.frame = ctk.CTkFrame(master, width=width, height=height, corner_radius=10, fg_color=fg_color, border_width=1, border_color=border_color)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)

        self.label = ctk.CTkLabel(self.frame, text=self.current, text_color=text_color, font=("Segoe UI", 12, "bold"), anchor="w", justify="left")
        self.label.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=6)

        self.btn = ctk.CTkButton(self.frame, text="▾", width=28, height=20, corner_radius=8, fg_color=button_color, hover_color=button_color, text_color="#edf4ff", font=("Segoe UI", 12, "bold"), border_width=0)
        self.btn.grid(row=0, column=1, sticky="e", padx=(0, 8), pady=6)

        self.menu = tk.Menu(self.frame, tearoff=0, bg="#0d1b2a", fg="#edf4ff", activebackground="#1d3047", activeforeground="#edf4ff", bd=0, font=("Segoe UI", 11))
        for item in self.values:
            self.menu.add_command(label=item, command=lambda v=item: self.set(v))

        def abrir(event=None):
            self.menu.post(self.frame.winfo_rootx(), self.frame.winfo_rooty() + self.frame.winfo_height())

        self.frame.bind("<Button-1>", abrir)
        self.label.bind("<Button-1>", abrir)
        self.btn.bind("<Button-1>", abrir)
        self.frame.bind("<Enter>", lambda event: self.frame.configure(border_color="#5c7ca2"))
        self.frame.bind("<Leave>", lambda event: self.frame.configure(border_color=border_color))

    def set(self, value):
        self.current = str(value)
        self.label.configure(text=self.current)
        if self.command is not None:
            self.command(self.current)

    def get(self):
        return self.current

    def configure(self, *args, **kwargs):
        pass

    def grid(self, *args, **kwargs):
        self.frame.grid(*args, **kwargs)

    def grid_remove(self):
        self.frame.grid_remove()


class LiquidacionesFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLOR_BG)
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.PDFS_DIR = os.path.join(self.BASE_DIR, "PDFS")
        self.anio_actual = str(get_current_year())
        os.makedirs(self.PDFS_DIR, exist_ok=True)
        self._actualizar_ruta_exportacion(self.anio_actual)
        self.pack(fill="both", expand=True)

        self._cargando = False           # evita autosave durante load
        self._mes_actual = None          # mes cargado actualmente

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ================= HEADER =================
        self.header = ctk.CTkFrame(
            self, fg_color="#121b29", corner_radius=18,
            border_width=1, border_color=COLOR_BORDER,
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        self.header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.header, text="💰 LIQUIDACIÓN MENSUAL",
            font=("Segoe UI", 28, "bold"), text_color="#4ea3ff",
        ).grid(row=0, column=0, pady=(18, 10))

        selector_row = ctk.CTkFrame(self.header, fg_color="transparent")
        selector_row.grid(row=1, column=0, pady=(0, 18))
        selector_row.grid_columnconfigure(0, weight=0)
        selector_row.grid_columnconfigure(1, weight=0)

        self.mes_seleccionado = ReadOnlyDropdown(
            selector_row,
            values=["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
                    "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"],
            command=self._on_cambio_mes,
            width=220,
            height=34,
            fg_color="#1d2f44",
            button_color=COLOR_BLUE,
            text_color="#edf4ff",
            border_color=COLOR_BORDER,
            placeholder="SELECCIONA UN MES",
        )
        self.mes_seleccionado.grid(row=0, column=0, padx=(0, 8))

        self.anio_seleccionado = ReadOnlyDropdown(
            selector_row,
            values=SUPPORTED_YEARS,
            command=self._on_cambio_anio,
            width=120,
            height=34,
            fg_color="#1d2f44",
            button_color=COLOR_BLUE,
            text_color="#edf4ff",
            border_color=COLOR_BORDER,
        )
        self.anio_seleccionado.set(self.anio_actual)
        self.anio_seleccionado.grid(row=0, column=1)

        # ================= BODY (3 columnas) =================
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        for i in range(3):
            self.body.grid_columnconfigure(i, weight=1, uniform="cols")
        self.body.grid_rowconfigure(0, weight=1)

        # ---------- COLUMNA 1 ----------
        self.col1 = ctk.CTkFrame(self.body, fg_color="transparent")
        self.col1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.col1.grid_columnconfigure(0, weight=1)
        self.col1.grid_rowconfigure(1, weight=1)   # gastos fijos crece

        # --- Tarjeta FIJA: Datos principales + Recibo ---
        card_datos = ctk.CTkFrame(
            self.col1, fg_color="#1b2530", corner_radius=18,
            border_width=1, border_color=COLOR_BORDER,
        )
        card_datos.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            card_datos, text="📊 DATOS PRINCIPALES",
            font=("Segoe UI", 15, "bold"), text_color="#4ea3ff", anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 6))

        inner = ctk.CTkFrame(
            card_datos, fg_color=COLOR_CARD, corner_radius=12,
            border_width=1, border_color=COLOR_BORDER,
        )
        inner.pack(fill="x", padx=10, pady=(0, 10))

        self._label(inner, "Base Factura").pack(anchor="w", padx=12, pady=(12, 4))
        self.e_base = self._entry(inner); self.e_base.pack(fill="x", padx=12)
        self.e_base.bind("<KeyRelease>", self._on_edit)

        self._label(inner, "Transferencia").pack(anchor="w", padx=12, pady=(12, 4))
        self.e_trans = self._entry(inner); self.e_trans.pack(fill="x", padx=12, pady=(0, 12))
        self.e_trans.bind("<KeyRelease>", self._on_edit)

        recibo_box = ctk.CTkFrame(
            card_datos, fg_color="#0f2540", corner_radius=12,
            border_width=1, border_color="#1e3a5f",
        )
        recibo_box.pack(fill="x", padx=10, pady=(0, 12))
        self.lbl_recibo = ctk.CTkLabel(
            recibo_box, text="💸 RECIBO: 0.00",
            font=("Segoe UI", 18, "bold"), text_color="#4ea3ff",
        )
        self.lbl_recibo.pack(pady=14)

        # --- Tarjeta SEPARADA con scroll: Gastos fijos ---
        card_fijos = ctk.CTkFrame(
            self.col1, fg_color="#1b2530", corner_radius=18,
            border_width=1, border_color=COLOR_BORDER,
        )
        card_fijos.grid(row=1, column=0, sticky="nsew")
        card_fijos.grid_rowconfigure(1, weight=1)
        card_fijos.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card_fijos, text="  💸  GASTOS FIJOS",
            font=("Segoe UI", 14, "bold"), text_color="#4ea3ff", anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        scroll_fijos = ctk.CTkScrollableFrame(
            card_fijos, fg_color=COLOR_CARD, corner_radius=12,
            border_color=COLOR_BORDER,
        )
        scroll_fijos.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.cont_fijos = scroll_fijos  # las filas se crean aquí dentro

        self._btn_azul(
            card_fijos, "➕ Añadir gasto fijo",
            lambda: self.ventana_nuevo_registro("fijo")
        ).grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        # ---------- COLUMNA 2: VARIABLES (3 tarjetas independientes) ----------
        self.col2 = ctk.CTkFrame(self.body, fg_color="transparent")
        self.col2.grid(row=0, column=1, sticky="nsew", padx=6)
        self.col2.grid_columnconfigure(0, weight=1)
        for r in range(3):
            self.col2.grid_rowconfigure(r, weight=1, uniform="v")

        self.cont_mat = self._card_scroll(
            self.col2, "🧱 MATERIAL", "➕ Añadir material",
            lambda: self.ventana_nuevo_registro("material"), row=0,
        )
        self.cont_comb = self._card_scroll(
            self.col2, "⛽ COMBUSTIBLE", "➕ Añadir combustible",
            lambda: self.ventana_nuevo_registro("combustible"), row=1,
        )
        self.cont_ajustes = self._card_scroll(
            self.col2, "🔧 AJUSTES MES ANTERIOR", "➕ Añadir ajustes",
            lambda: self.ventana_nuevo_registro("ajuste"), row=2,
        )

        # ---------- COLUMNA 3: EXTRAS ----------
        self.col3 = ctk.CTkScrollableFrame(
            self.body,
            label_text="  ✨  EXTRAS",
            label_font=("Segoe UI", 15, "bold"),
            label_text_color="#4ea3ff",
            label_fg_color="#1b2530",
            corner_radius=18, fg_color="#1b2530",
            border_width=1, border_color=COLOR_BORDER,
        )
        self.col3.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        self._btn_azul(self.col3, "➕ TF / Bizum",
                       lambda: self.add_extra("Bizum")).pack(fill="x", padx=6, pady=(6, 4))
        self._btn_azul(self.col3, "➕ Efectivo",
                       lambda: self.add_extra("Efectivo")).pack(fill="x", padx=6, pady=(6, 4))
        self.cont_ext = self._contenedor_rows(self.col3)

        # ================= FOOTER =================
        self.footer = ctk.CTkFrame(
            self, fg_color="#121b29", corner_radius=18,
            border_width=1, border_color=COLOR_BORDER, height=90,
        )
        self.footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(6, 18))
        self.footer.grid_columnconfigure(0, weight=1)

        self.lbl_mio = ctk.CTkLabel(
            self.footer, text="💰 MIO: 0.00 €",
            font=("Segoe UI", 28, "bold"), text_color=COLOR_GREEN,
        )
        self.lbl_mio.grid(row=0, column=0, sticky="w", padx=20, pady=18)

        ctk.CTkButton(
            self.footer, text="📄 DECLARACIÓN TRIMESTRAL / ANUAL",
            command=self.mostrar_resumen_renta,
            width=280, height=44, corner_radius=10,
            fg_color=COLOR_BLUE, hover_color=COLOR_BLUE_HOV,
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=1, padx=(10, 8), pady=18)

        ctk.CTkButton(
            self.footer, text="📄 GENERAR PDF", command=self.generar_pdf,
            width=170, height=44, corner_radius=10,
            fg_color=COLOR_BLUE, hover_color=COLOR_BLUE_HOV,
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=2, padx=(10, 8), pady=18)

        ctk.CTkButton(
            self.footer, text="📂 ABRIR LIQUIDACIONES", command=self.abrir_carpeta_declaracion,
            width=200, height=44, corner_radius=10,
            fg_color=COLOR_GRAY_BTN, hover_color=COLOR_GRAY_HOV,
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=3, padx=(0, 20), pady=18)
       

    # ==============================================================
    # HELPERS UI
    # ==============================================================
    def _label(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=("Segoe UI", 13),
                            text_color=COLOR_MUTED, anchor="w")

    def _entry(self, parent):
        return ctk.CTkEntry(parent, height=38, corner_radius=8,
                            fg_color="#151515", border_color=COLOR_BORDER,
                            text_color=COLOR_TEXT, font=("Segoe UI", 13))

    def _btn_azul(self, parent, text, command):
        return ctk.CTkButton(parent, text=text, command=command,
                             height=40, corner_radius=10,
                             fg_color=COLOR_BLUE, hover_color=COLOR_BLUE_HOV,
                             font=("Segoe UI", 13, "bold"))

    def formato_fecha(self, fecha):
        try:
            if isinstance(fecha, str):
                fecha = fecha.strip()

                formatos = [
                    "%d/%m/%Y",
                    "%d/%b/%Y",
                    "%d/%B/%Y"
                ]

                fecha_obj = None

                for f in formatos:
                    try:
                        fecha_obj = datetime.strptime(fecha, f)
                        break
                    except:
                        pass

                if not fecha_obj:
                    return fecha

            else:
                fecha_obj = fecha


            meses = [
                "Ene", "Feb", "Mar", "Abr",
                "May", "Jun", "Jul", "Ago",
                "Sep", "Oct", "Nov", "Dic"
            ]

            return f"{fecha_obj.day}/{meses[fecha_obj.month-1]}/{fecha_obj.year}"

        except:
            return fecha


    def ventana_nuevo_registro(self, tipo):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Añadir")
        ventana.geometry("320x260")
        ventana.resizable(False, False)


        # CENTRAR VENTANA EN PANTALLA
        ventana.update_idletasks()

        ancho = 320
        alto = 260

        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2) + 250
        y = (ventana.winfo_screenheight() // 2) - (alto // 2) + 100


        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

        ventana.grab_set()
        ventana.lift()
        ventana.focus_force()


        if tipo == "fijo":

            ctk.CTkLabel(
                ventana,
                text="Nombre"
            ).pack(anchor="w", padx=30)

            e_nombre = ctk.CTkEntry(ventana)
            e_nombre.pack(fill="x", padx=30, pady=5)


            ctk.CTkLabel(
                ventana,
                text="Importe"
            ).pack(anchor="w", padx=30)

            e_importe = ctk.CTkEntry(ventana)
            e_importe.pack(fill="x", padx=30, pady=5)


        elif tipo in ("material", "combustible"):

            ctk.CTkLabel(
                ventana,
                text="Importe"
            ).pack(anchor="w", padx=30)

            e_importe = ctk.CTkEntry(ventana)
            e_importe.pack(fill="x", padx=30, pady=5)


        elif tipo == "ajuste":

            ctk.CTkLabel(
                ventana,
                text="Concepto"
            ).pack(anchor="w", padx=30)

            e_nombre = ctk.CTkEntry(ventana)
            e_nombre.insert(0, "Mes anterior")
            e_nombre.configure(state="disabled")
            e_nombre.pack(fill="x", padx=30, pady=5)


            ctk.CTkLabel(
                ventana,
                text="Importe"
            ).pack(anchor="w", padx=30)

            e_importe = ctk.CTkEntry(ventana)
            e_importe.pack(fill="x", padx=30, pady=5)



        def guardar():

            importe = e_importe.get()

            if tipo == "fijo":
                self.crear_fila_fijo(
                    e_nombre.get(),
                    importe
                )

            elif tipo == "material":
                e = self.add_fila_doble(self.cont_mat)
                e.insert(0, importe)


            elif tipo == "combustible":
                e = self.add_fila_doble(self.cont_comb)
                e.insert(0, importe)


            elif tipo == "ajuste":
                self.add_ajuste_mes(
                    "Mes anterior",
                    importe
                )


            self.calcular()
            self._autosave()
            ventana.destroy()



        botones = ctk.CTkFrame(
            ventana,
            fg_color="transparent"
        )
        botones.pack(pady=20)


        ctk.CTkButton(
            botones,
            text="GUARDAR",
            command=guardar,
            fg_color=COLOR_BLUE
        ).pack(side="left", padx=10)


        ctk.CTkButton(
            botones,
            text="CANCELAR",
            fg_color=COLOR_RED,
            command=ventana.destroy
        ).pack(side="left", padx=10)

        # ----- Comportamiento teclado: Enter avanza, Esc cierra -----
        try:
            widgets = []
            if tipo == 'fijo':
                widgets = [e_nombre, e_importe]
            elif tipo in ('material', 'combustible'):
                widgets = [e_importe]
            elif tipo == 'ajuste':
                widgets = [e_importe]

            for i, w in enumerate(widgets):
                # Avanzar o guardar al pulsar Enter
                w.bind('<Return>', (lambda idx: (lambda ev: (widgets[idx+1].focus_set() if idx+1 < len(widgets) else guardar())))(i))
                # Esc cierra
                w.bind('<Escape>', lambda ev: ventana.destroy())

            # poner foco en el primer widget
            if widgets:
                ventana.after(50, lambda: widgets[0].focus_set())
        except Exception:
            pass

    def _contenedor_rows(self, parent):
        cont = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10,
                            border_width=1, border_color=COLOR_BORDER)
        cont.pack(fill="x", padx=6, pady=(0, 6))
        return cont

    def _card_scroll(self, parent, titulo, btn_txt, btn_cmd, row):
        """Tarjeta con título + scroll interno + botón añadir. Devuelve el scroll."""
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_ALT, corner_radius=18,
                            border_width=1, border_color=COLOR_BORDER)
        card.grid(row=row, column=0, sticky="nsew", pady=(0, 8) if row < 2 else 0)
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 14, "bold"),
                     text_color="#4ea3ff", anchor="w"
                     ).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        scroll = ctk.CTkScrollableFrame(card, fg_color=COLOR_CARD,
                                        corner_radius=12, border_color=COLOR_BORDER)
        scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 6))

        self._btn_azul(card, btn_txt, btn_cmd).grid(
            row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        return scroll

    # ==============================================================
    # LÓGICA (sin cambios funcionales)
    # ==============================================================
    def _on_edit(self, *a):
        self.calcular()
        self._autosave()

    def limpiar(self, val):
        texto = str(val.get() if hasattr(val, 'get') else val).replace(',', '.').strip()
        try: return float(texto)
        except ValueError: return 0.0

    def add_fila_doble(self, p):
        # Si el contenedor es material o combustible, usar una rejilla de 3 columnas
        is_price_grid = p in (getattr(self, 'cont_mat', None), getattr(self, 'cont_comb', None))

        f = ctk.CTkFrame(p, fg_color=COLOR_ROW, corner_radius=8)
        # contenedor normal (gastos fijos / ajustes)
        if not is_price_grid:
            f.pack(fill="x", pady=3, padx=4)
            e = ctk.CTkEntry(f, height=30, corner_radius=6, fg_color="#151515",
                             border_color=COLOR_BORDER)
            e.pack(side="left", fill="x", expand=True, padx=6, pady=6)
            e.bind("<KeyRelease>", self._on_edit)
            ctk.CTkButton(f, text="✖", fg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
                          width=30, corner_radius=8,
                          command=lambda: [f.destroy(), self._on_edit()]
                          ).pack(side="right", padx=6, pady=6)
            return e

        # Inicializar rejilla de 3 columnas en el contenedor si no se hizo antes
        try:
            if not getattr(p, '_grid_init', False):
                for col in range(3):
                    try: p.grid_columnconfigure(col, weight=1)
                    except Exception: pass
                p._grid_init = True
        except Exception:
            pass

        # Celda compacta: entrada centrada y botón eliminar pequeño
        e = ctk.CTkEntry(f, height=28, corner_radius=6, fg_color="#151515",
                 border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                 font=("Segoe UI", 11), justify="left", width=80)
        e.bind("<KeyRelease>", self._on_edit)

        del_btn = ctk.CTkButton(f, text="✖", fg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
                    width=22, height=22, corner_radius=6)

        # usar grid dentro de la celda: entrada expandible a la izquierda, botón a la derecha
        try:
            f.grid_columnconfigure(0, weight=1)
            e.grid(row=0, column=0, sticky='ew', padx=(8, 4), pady=6)
            del_btn.grid(row=0, column=1, sticky='e', padx=(4, 8), pady=6)
        except Exception:
            # fallback a pack si grid falla
            e.pack(fill="both", expand=True, padx=6, pady=6)
            del_btn.place(relx=0.92, rely=0.12)

        # comando eliminar: destruir y reordenar
        del_btn.configure(command=lambda: [f.destroy(), self._on_edit(), self._reflow_grid(p)])

        # colocar la nueva celda al final
        count = len([w for w in p.winfo_children()])
        r = count // 3; ccol = count % 3
        f.grid(row=r, column=ccol, padx=6, pady=6, sticky='nsew')

        # asegurar reflow para forzar 3 columnas consistentes
        try:
            self._reflow_grid(p)
        except Exception:
            pass

        # botón eliminado: no usar place para evitar sobreposiciones

        return e

    def _reflow_grid(self, p):
        """Reorganiza los children del contenedor `p` en una rejilla de 3 columnas."""
        try:
            children = [w for w in p.winfo_children()]
            for idx, child in enumerate(children):
                try:
                    child.pack_forget()
                except Exception:
                    pass
                try:
                    child.grid_forget()
                except Exception:
                    pass
                r = idx // 3; ccol = idx % 3
                try:
                    # dar un ancho fijo a las celdas para que quepan 3 por fila
                    try:
                        # solo ajustar ancho para material/combustible contenedores
                        if p in (getattr(self, 'cont_mat', None), getattr(self, 'cont_comb', None)):
                            child.configure(width=120)
                    except Exception:
                        pass
                    child.grid(row=r, column=ccol, padx=6, pady=6, sticky='w')
                except Exception:
                    pass
        except Exception:
            pass

    def add_ajuste_mes(self, nombre="Mes anterior", valor="0"):
        f = ctk.CTkFrame(self.cont_ajustes, fg_color=COLOR_ROW, corner_radius=8)
        f.pack(fill="x", pady=3, padx=4)
        e_n = ctk.CTkEntry(f, width=140, height=30, corner_radius=6,
                           fg_color="#151515", border_color=COLOR_BORDER)
        e_n.insert(0, nombre); e_n.pack(side="left", padx=6, pady=6)
        e_n.bind("<KeyRelease>", self._on_edit)
        e = ctk.CTkEntry(f, width=70, height=30, corner_radius=6,
                         fg_color="#151515", border_color=COLOR_BORDER)
        e.insert(0, valor); e.pack(side="left", padx=4, pady=6)
        e.bind("<KeyRelease>", self._on_edit)
        ctk.CTkButton(f, text="✖", fg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
                      width=32, corner_radius=8,
                      command=lambda: [f.destroy(), self._on_edit()]
                      ).pack(side="right", padx=6, pady=6)

    def add_extra(self, t, neto="", iva="", irpf="", res="", fecha=None):
        f = ctk.CTkFrame(self.cont_ext, fg_color=COLOR_ROW, corner_radius=8)
        f.pack(fill="x", pady=4, padx=4)
        cab = ctk.CTkFrame(f, fg_color="transparent"); cab.pack(fill="x", padx=4, pady=(4, 0))
        for txt in ["NETO", "IVA", "IRPF", "RESULTADO"]:
            ctk.CTkLabel(cab, text=txt, width=65, text_color=COLOR_MUTED,
                         font=("Segoe UI", 10, "bold")).pack(side="left", padx=2)
        fila = ctk.CTkFrame(f, fg_color="transparent"); fila.pack(fill="x", padx=4, pady=(0, 4))
        c = {"n": ctk.CTkEntry(fila, width=65), "iva": ctk.CTkEntry(fila, width=65),
             "irpf": ctk.CTkEntry(fila, width=65), "res": ctk.CTkEntry(fila, width=70)}
        for v, k in zip([neto, iva, irpf, res], ["n", "iva", "irpf", "res"]):
            if v != "": c[k].insert(0, str(v))
            c[k].pack(side="left", padx=2)

        de = DateEntry(
            fila,
            width=12,
            date_pattern="d/mm/yyyy"
        )

        if fecha:
            try: de.set_date(fecha)
            except Exception: pass
        de.pack(side="left", padx=4)
        ctk.CTkButton(fila, text="✖", width=30, fg_color=COLOR_RED,
                      hover_color=COLOR_RED_HOV,
                      command=lambda: [f.destroy(), self._on_edit()]).pack(side="right")
        c["n"].bind("<KeyRelease>", lambda e: [self.calc_extra(t, c), self._autosave()])
        f.c = c; f.t = t

        # poner foco en neto y bindings: Enter -> siguiente campo, Esc -> cerrar fila (elimina)
        try:
            entradas = [c['n'], c['iva'], c['irpf'], c['res']]
            for i, w in enumerate(entradas):
                def _make_enter(i):
                    def _on_enter(ev):
                        if i+1 < len(entradas):
                            entradas[i+1].focus_set()
                        else:
                            # al final, recalcular y autosave
                            self.calc_extra(t, c); self._autosave()
                    return _on_enter
                w.bind('<Return>', _make_enter(i))
                w.bind('<Escape>', lambda ev, ff=f: ff.destroy())
            # foco inicial
            f.after(50, lambda: entradas[0].focus_set())
        except Exception:
            pass

    def crear_fila_fijo(self, nombre="", importe=""):
        f = ctk.CTkFrame(self.cont_fijos, fg_color=COLOR_ROW, corner_radius=8)
        f.pack(fill="x", pady=3, padx=4)
        e_n = ctk.CTkEntry(f, height=30, corner_radius=6, fg_color="#151515",
                           border_color=COLOR_BORDER, font=("Segoe UI", 11))
        e_n.insert(0, nombre)
        e_n.pack(side="left", fill="x", expand=True, padx=(6, 4), pady=6)
        e_n.bind("<KeyRelease>", self._on_edit)
        e_v = ctk.CTkEntry(f, width=70, height=30, corner_radius=6, justify="center",
                           fg_color="#151515", border_color=COLOR_BORDER,
                           font=("Segoe UI", 11, "bold"))
        e_v.insert(0, importe)
        e_v.pack(side="left", padx=4, pady=6)
        e_v.bind("<KeyRelease>", self._on_edit)
        ctk.CTkButton(f, text="✖", width=32, corner_radius=8,
                      fg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
                      command=lambda: [f.destroy(), self._on_edit()]
                      ).pack(side="right", padx=6, pady=6)
        self.calcular()

    def calc_extra(self, t, c):
        n = self.limpiar(c["n"])
        res = (n - (n * 0.20)) if t == "Bizum" else (n * 0.21 + n * 0.20) * -1
        for k, v in zip(["iva", "irpf", "res"], [n * 0.21, n * 0.20, res]):
            c[k].delete(0, tk.END); c[k].insert(0, f"{v:.2f}")
        self.calcular()

    def calcular(self, *args):
        try:
            bs, tr = self.limpiar(self.e_base), self.limpiar(self.e_trans)
            def s(p, idx): return sum(self.limpiar(w.winfo_children()[idx]) for w in p.winfo_children())
            f = s(self.cont_fijos, 1); a = s(self.cont_ajustes, 1)
            mat = s(self.cont_mat, 0); comb = s(self.cont_comb, 0) / 2
            rec = tr - (bs * 0.21 + (bs - (mat + comb)) * 0.20)
            ex = sum(self.limpiar(w.c["res"]) for w in self.cont_ext.winfo_children() if hasattr(w, "c"))
            self.lbl_recibo.configure(text=f"💸 RECIBO: {rec:.2f}")
            self.lbl_mio.configure(text=f"💰 MIO: {rec - f + ex + a:.2f} €")
        except: pass

    def numero(self, w):
        try:
            val = w.get() if hasattr(w, 'get') else w
            return float(str(val).replace('€', '').replace(',', '.').strip())
        except: return 0.0

    # ==============================================================
    # PERSISTENCIA POR MES
    # ==============================================================
    def _ruta_mes(self, mes):
        return os.path.join(self.CARPETA_DATA, f"{mes.upper()}.json")

    def _on_cambio_mes(self, nuevo_mes):
        placeholder = self.mes_seleccionado.placeholder.upper() if self.mes_seleccionado.placeholder else ""
        nuevo_mes = str(nuevo_mes or "").strip()

        if not nuevo_mes or nuevo_mes.upper() == placeholder:
            return

        if self._mes_actual and self._mes_actual != nuevo_mes:
            self._guardar_mes(self._mes_actual)

        self._cargar_mes(nuevo_mes)

    def _on_cambio_anio(self, nuevo_anio):
        if not nuevo_anio:
            return
        if self._mes_actual:
            self._guardar_mes(self._mes_actual)
        self._actualizar_ruta_exportacion(nuevo_anio)
        if self._mes_actual:
            self._cargar_mes(self._mes_actual)

    def _autosave(self):
        if self._cargando or not self._mes_actual: return
        try: self._guardar_mes(self._mes_actual)
        except Exception: pass

    def _snapshot(self):
        def rows_doble(p):
            out = []
            for w in p.winfo_children():
                hijos = w.winfo_children()
                if hijos: out.append(hijos[0].get())
            return out
        fijos = [(w.winfo_children()[0].get(), w.winfo_children()[1].get())
                 for w in self.cont_fijos.winfo_children()]
        ajustes = [(w.winfo_children()[0].get(), w.winfo_children()[1].get())
                   for w in self.cont_ajustes.winfo_children()]
        extras = []
        for w in self.cont_ext.winfo_children():
            if not hasattr(w, "c"): continue
            fecha = ""
            for x in w.winfo_children():
                for y in x.winfo_children() if hasattr(x, "winfo_children") else []:
                    if isinstance(y, DateEntry):
                        try:
                            d = y.get_date()
                            try:
                                fecha = d.isoformat()
                            except Exception:
                                fecha = d.strftime("%Y-%m-%d")
                        except Exception:
                            fecha = ""
            extras.append({
                "tipo": w.t,
                "neto": w.c["n"].get(), "iva": w.c["iva"].get(),
                "irpf": w.c["irpf"].get(), "res": w.c["res"].get(),
                "fecha": fecha,
            })
        return {
            "base": self.e_base.get(),
            "transferencia": self.e_trans.get(),
            "material": rows_doble(self.cont_mat),
            "combustible": rows_doble(self.cont_comb),
            "fijos": fijos, "ajustes": ajustes, "extras": extras,
        }

    def _guardar_mes(self, mes):
        with open(self._ruta_mes(mes), "w", encoding="utf-8") as fh:
            json.dump(self._snapshot(), fh, ensure_ascii=False, indent=2)

    def _limpiar_contenedor(self, cont):
        for w in list(cont.winfo_children()): w.destroy()

    def _cargar_mes(self, mes):
        self._cargando = True
        try:
            self._limpiar_contenedor(self.cont_fijos)
            self._limpiar_contenedor(self.cont_mat)
            self._limpiar_contenedor(self.cont_comb)
            self._limpiar_contenedor(self.cont_ajustes)
            self._limpiar_contenedor(self.cont_ext)
            self.e_base.delete(0, tk.END); self.e_trans.delete(0, tk.END)

            ruta = self._ruta_mes(mes)
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as fh:
                    d = json.load(fh)
                self.e_base.insert(0, d.get("base", ""))
                self.e_trans.insert(0, d.get("transferencia", ""))
                for n, v in d.get("fijos", []): self.crear_fila_fijo(n, v)
                for v in d.get("material", []):
                    e = self.add_fila_doble(self.cont_mat); e.insert(0, v)
                for v in d.get("combustible", []):
                    e = self.add_fila_doble(self.cont_comb); e.insert(0, v)
                for n, v in d.get("ajustes", []): self.add_ajuste_mes(n, v)
                for ex in d.get("extras", []):
                    fecha = None
                    if ex.get("fecha"):
                        from datetime import date
                        f = ex["fecha"]
                        # Intentar ISO primero, luego formatos antiguos
                        try:
                            fecha = date.fromisoformat(f)
                        except Exception:
                            try:
                                # aceptar dd/Mon/YYYY o d/Mon/YYYY, y d/mm/YYYY
                                for fmt in ("%d/%b/%Y", "%d/%B/%Y", "%d/%m/%Y"):
                                    try:
                                        fecha = datetime.strptime(f, fmt).date()
                                        break
                                    except Exception:
                                        continue
                            except Exception:
                                fecha = None
                    self.add_extra(ex.get("tipo", "Bizum"),
                                   ex.get("neto", ""), ex.get("iva", ""),
                                   ex.get("irpf", ""), ex.get("res", ""), fecha)

                # Forzar reordenación de la rejilla tras cargar datos
                try:
                    self._reflow_grid(self.cont_mat)
                    self._reflow_grid(self.cont_comb)
                except Exception:
                    pass
            else:
                # defaults primera vez
                for n, imp in [("Internet", "20"), ("Autónomo", "120"),
                               ("Gestor", "80"), ("Vuelo", "102")]:
                    self.crear_fila_fijo(n, imp)

            self._mes_actual = mes
            self.calcular()
        finally:
            self._cargando = False

    def _meses_del_trimestre(self, mes):
        meses = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
                 "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
        idx = meses.index(mes.upper()) if mes.upper() in meses else -1
        if idx == -1:
            return []
        inicio = (idx // 3) * 3
        return meses[inicio:inicio + 3]

    def _meses_del_anio(self):
        return ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
                "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

    def _sumar_periodo(self, meses):
        total = {
            "base": 0.0,
            "material": 0.0,
            "combustible": 0.0,
            "extras": 0.0,
            "fijos": 0.0,
            "ajustes": 0.0,
            "iva_facturas": 0.0,
            "iva_extras": 0.0,
            "gastos_deducibles": 0.0,
            "base_imponible": 0.0,
            "iva_estimado": 0.0,
            "irpf_estimado": 0.0,
            "resultado_neto": 0.0,
        }

        def parse_number(value):
            try:
                if value is None or value == "":
                    return 0.0
                if isinstance(value, (int, float)):
                    return float(value)

                s = str(value).strip().replace(" ", "").replace("€", "")
                if s in {"", "-"}:
                    return 0.0

                if "," in s and "." in s:
                    if s.rfind(",") > s.rfind("."):
                        s = s.replace(".", "").replace(",", ".")
                    else:
                        s = s.replace(",", "")
                elif "," in s:
                    if s.count(",") > 1:
                        s = s.replace(",", "")
                    else:
                        s = s.replace(",", ".")
                elif "." in s and s.count(".") > 1:
                    s = s.replace(".", "")

                return float(s)
            except Exception:
                return 0.0

        def sum_values(items):
            if not items:
                return 0.0
            total_items = 0.0
            for item in items:
                if isinstance(item, (int, float, str)):
                    total_items += parse_number(item)
                elif isinstance(item, list):
                    if len(item) >= 2:
                        total_items += parse_number(item[-1])
                elif isinstance(item, dict):
                    total_items += parse_number(item.get("neto", item.get("importe", item.get("res", item.get("valor", 0)))))
            return total_items

        for mes in meses:
            path = os.path.join(self.CARPETA_DATA, f"{mes}.json")
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    datos = json.load(fh)
            except Exception:
                continue

            base_mes = parse_number(datos.get("base", 0))
            material_mes = parse_number(datos.get("total_material", 0))
            if material_mes == 0:
                material_mes = sum_values(datos.get("material", []))
            combustible_mes = parse_number(datos.get("total_combustible", 0))
            if combustible_mes == 0:
                combustible_mes = sum_values(datos.get("combustible", []))
            extras_neto = 0.0
            extras_iva = 0.0
            for extra in datos.get("extras", []) or []:
                if isinstance(extra, dict):
                    extras_neto += parse_number(extra.get("neto", extra.get("res", 0)))
                    extras_iva += parse_number(extra.get("iva", 0))

            if base_mes == 0 and material_mes == 0 and combustible_mes == 0 and extras_neto == 0:
                continue

            total["base"] += base_mes
            total["material"] += material_mes
            total["combustible"] += combustible_mes
            total["iva_facturas"] += base_mes * 0.21
            total["extras"] += extras_neto
            total["iva_extras"] += extras_iva

        total["base"] = total["base"] + total["extras"]
        total["combustible"] = total["combustible"] * 0.5
        total["gastos_deducibles"] = total["material"] + total["combustible"]
        total["base_imponible"] = max(0.0, total["base"] - total["gastos_deducibles"])
        total["iva_estimado"] = total["iva_facturas"] + total["iva_extras"]
        total["irpf_estimado"] = total["base_imponible"] * 0.20
        total["resultado_neto"] = total["base"] - total["gastos_deducibles"] - total["irpf_estimado"]
        return total

    def _casillas_periodo(self, meses, nombre_periodo, exercise_year=None):
        resumen = self._sumar_periodo(meses)
        iva_cob = resumen["base"] * 0.21
        iva_ded = resumen["gastos_deducibles"] * 0.21
        rendimiento = max(0.0, resumen["base"] - resumen["gastos_deducibles"])
        irpf = max(0.0, rendimiento * 0.20)
        year = str(exercise_year or get_current_year())

        modelo_303 = get_model_config(year, "303")
        modelo_130 = get_model_config(year, "130")

        def valor_casilla_303(code):
            map_values = {
                "07": resumen["base"],
                "09": iva_cob,
                "28": resumen["gastos_deducibles"],
                "29": iva_ded,
                "71": iva_cob - iva_ded,
            }
            return map_values.get(str(code), 0.0)

        def valor_casilla_130(code):
            map_values = {
                "01": resumen["base"],
                "02": resumen["gastos_deducibles"],
                "03": rendimiento,
                "04": irpf,
                "05": 0.0,
                "A ingresar": irpf,
            }
            return map_values.get(str(code), 0.0)

        return {
            "periodo": nombre_periodo,
            "modelo_303": [
                (f"Casilla {item['code']}", item['label'], valor_casilla_303(item['code']))
                for item in modelo_303
            ],
            "modelo_130": [
                (f"Casilla {item['code']}", item['label'], valor_casilla_130(item['code']))
                for item in modelo_130
            ],
        }

    def _casillas_modelo_100(self, resumen_obj, exercise_year=None):
        year = str(exercise_year or get_current_year())
        modelo_100 = get_model_config(year, "100")

        base_general = max(0.0, resumen_obj["base_imponible"])
        base_ahorro = 0.0
        base_liquidable_general = base_general
        base_liquidable_ahorro = 0.0
        cuota_estatal = max(0.0, resumen_obj["irpf_estimado"] * 0.60)
        cuota_autonomica = max(0.0, resumen_obj["irpf_estimado"] * 0.40)
        cuota_total = cuota_estatal + cuota_autonomica
        pagos_cuenta = max(0.0, resumen_obj["iva_estimado"] + resumen_obj["irpf_estimado"])
        resultado = pagos_cuenta - cuota_total

        def valor_casilla(code):
            map_values = {
                "0435": base_general,
                "0460": base_ahorro,
                "0500": base_liquidable_general,
                "0510": base_liquidable_ahorro,
                "0545": cuota_estatal,
                "0546": cuota_autonomica,
                "0609": pagos_cuenta,
                "0610": resultado,
                "0700": resultado,
            }
            return map_values.get(str(code), 0.0)

        return {
            "periodo": "ANUAL",
            "modelo_100": [
                (f"Casilla {item['code']}", item['label'], valor_casilla(item['code']))
                for item in modelo_100
            ],
            "texto": (
                "Este bloque corresponde al Modelo 100 anual. Los valores son un resumen anual de la renta y no deben mezclarse con los resultados del 303/130 trimestral."
            ),
        }

    def _estado_declaracion(self, resumen_obj):
        iva = max(0.0, resumen_obj["base"] * 0.21 - resumen_obj["gastos_deducibles"] * 0.21)
        irpf = max(0.0, (max(0.0, resumen_obj["base"] - resumen_obj["gastos_deducibles"])) * 0.20)

        if resumen_obj["base"] * 0.21 - resumen_obj["gastos_deducibles"] * 0.21 > 0:
            estado_303 = "A ingresar"
        elif resumen_obj["base"] * 0.21 - resumen_obj["gastos_deducibles"] * 0.21 < 0:
            estado_303 = "A compensar / devolver"
        else:
            estado_303 = "Sin cuota"

        estado_130 = "A ingresar" if irpf > 0 else "Sin cuota"
        return {
            "iva": iva,
            "irpf": irpf,
            "estado_303": estado_303,
            "estado_130": estado_130,
            "texto": (
                "Este resumen prepara 303 y 130. El modelo 100 es anual y se rellena en la Declaración de la Renta, "
                "no en el trimestre."
            ),
        }

    def _generar_nombre_archivo_declaracion(self, periodo_label: str, year: str, extension: str = "pdf"):
        year = str(year).strip()
        etiqueta = str(periodo_label).strip().upper()

        if "ANUAL" in etiqueta:
            base_name = f"anual_{year}"
        elif "TRIMESTRE" in etiqueta or "1ER" in etiqueta or "2º" in etiqueta or "2O" in etiqueta or "3ER" in etiqueta or "4º" in etiqueta or "4O" in etiqueta:
            match = re.search(r"(\d)", etiqueta)
            trimestre = match.group(1) if match else "1"
            base_name = f"trimestre_{trimestre}_{year}"
        else:
            base_name = f"declaracion_{year}"

        candidate = os.path.join(self.CARPETA_DECLARACION, f"{base_name}.{extension}")
        index = 1
        while os.path.exists(candidate):
            candidate = os.path.join(self.CARPETA_DECLARACION, f"{base_name}_{index}.{extension}")
            index += 1
        return candidate

    def _resolver_periodo_export(self, periodo_label: str | None = None):
        label = str(periodo_label or "ANUAL").strip().upper()
        if "ANUAL" in label:
            return "ANUAL", self._meses_del_anio()

        mapping = {
            "1ER TRIMESTRE": ["ENERO", "FEBRERO", "MARZO"],
            "TRIMESTRE 1": ["ENERO", "FEBRERO", "MARZO"],
            "2º TRIMESTRE": ["ABRIL", "MAYO", "JUNIO"],
            "2O TRIMESTRE": ["ABRIL", "MAYO", "JUNIO"],
            "TRIMESTRE 2": ["ABRIL", "MAYO", "JUNIO"],
            "3ER TRIMESTRE": ["JULIO", "AGOSTO", "SEPTIEMBRE"],
            "TRIMESTRE 3": ["JULIO", "AGOSTO", "SEPTIEMBRE"],
            "4º TRIMESTRE": ["OCTUBRE", "NOVIEMBRE", "DICIEMBRE"],
            "4O TRIMESTRE": ["OCTUBRE", "NOVIEMBRE", "DICIEMBRE"],
            "TRIMESTRE 4": ["OCTUBRE", "NOVIEMBRE", "DICIEMBRE"],
        }
        return label, mapping.get(label, self._meses_del_anio())

    def _exportar_archivo_renta(self, year: str, periodo_label: str | None = None, months: list[str] | None = None):
        os.makedirs(self.CARPETA_DECLARACION, exist_ok=True)
        periodo = str(periodo_label or "ANUAL").strip() or "ANUAL"
        if "ANUAL" in periodo.upper():
            selected_periodo = "ANUAL"
            selected_months = self._meses_del_anio()
            resumen = self._sumar_periodo(selected_months)
            casillas = self._casillas_modelo_100(resumen, year)["modelo_100"]
            modelos = [("100", casillas)]
        else:
            selected_periodo = periodo.upper()
            selected_months = months or self._resolver_periodo_export(periodo)[1]
            resumen = self._sumar_periodo(selected_months)
            periodo_data = self._casillas_periodo(selected_months, selected_periodo, year)
            modelos = [("303", periodo_data["modelo_303"]), ("130", periodo_data["modelo_130"])]

        rows = []
        for model_name, casillas in modelos:
            for casilla, texto, valor in casillas:
                rows.append({
                    "modelo": model_name,
                    "casilla": str(casilla).replace("Casilla ", ""),
                    "etiqueta": texto,
                    "valor": float(valor or 0.0),
                })

        json_path = self._generar_nombre_archivo_declaracion(selected_periodo, year, "json")
        txt_path = self._generar_nombre_archivo_declaracion(selected_periodo, year, "txt")

        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump({"year": year, "periodo": selected_periodo, "casillas": rows}, fh, ensure_ascii=False, indent=2)

        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(f"DECLARACION RENTA - EJERCICIO {year} - {selected_periodo.upper()}\n")
            fh.write("========================================\n")
            for row in rows:
                fh.write(f"Modelo {row['modelo']} | Casilla {row['casilla']} | {row['etiqueta']} | {row['valor']:.2f} €\n")

        return json_path, txt_path

    def exportar_periodo_actual(self, year: str | None = None, tab_name: str | None = None, periodo_label: str | None = None):
        year_value = str(year or get_current_year())
        if (tab_name or "").upper() == "ANUAL":
            periodo = "ANUAL"
            meses = self._meses_del_anio()
        else:
            periodo = str(periodo_label or "1ER TRIMESTRE").strip() or "1ER TRIMESTRE"
            _, meses = self._resolver_periodo_export(periodo)

        json_path, txt_path = self._exportar_archivo_renta(year_value, periodo_label=periodo, months=meses)
        messagebox.showinfo("Archivo generado", f"Se ha creado la declaración para {periodo.upper()}:\n\nJSON: {json_path}\nTXT: {txt_path}")
        return json_path, txt_path

    def _get_current_quarter_label(self, month_number=None):
        current_month = int(month_number if month_number is not None else datetime.now().month)
        mapping = {
            1: "1er Trimestre",
            2: "1er Trimestre",
            3: "1er Trimestre",
            4: "2º Trimestre",
            5: "2º Trimestre",
            6: "2º Trimestre",
            7: "3er Trimestre",
            8: "3er Trimestre",
            9: "3er Trimestre",
            10: "4º Trimestre",
            11: "4º Trimestre",
            12: "4º Trimestre",
        }
        return mapping.get(current_month, "1er Trimestre")

    def _get_quarter_label_for_month(self, month_name=None):
        monthly_map = {
            "ENERO": "1er Trimestre",
            "FEBRERO": "1er Trimestre",
            "MARZO": "1er Trimestre",
            "ABRIL": "2º Trimestre",
            "MAYO": "2º Trimestre",
            "JUNIO": "2º Trimestre",
            "JULIO": "3er Trimestre",
            "AGOSTO": "3er Trimestre",
            "SEPTIEMBRE": "3er Trimestre",
            "OCTUBRE": "4º Trimestre",
            "NOVIEMBRE": "4º Trimestre",
            "DICIEMBRE": "4º Trimestre",
        }
        month_key = str(month_name or "").upper().strip()
        if month_key in monthly_map:
            return monthly_map[month_key]
        return self._get_current_quarter_label(datetime.now().month)

    def _get_quarter_months_for_label(self, label):
        mapping = {
            "1er Trimestre": ["ENERO", "FEBRERO", "MARZO"],
            "2º Trimestre": ["ABRIL", "MAYO", "JUNIO"],
            "3er Trimestre": ["JULIO", "AGOSTO", "SEPTIEMBRE"],
            "4º Trimestre": ["OCTUBRE", "NOVIEMBRE", "DICIEMBRE"],
        }
        return mapping.get(label, ["ENERO", "FEBRERO", "MARZO"])

    def _ruta_recordatorios(self):
        return os.path.join(self.CARPETA_DATA, "recordatorios_renta.json")

    def _cargar_recordatorios(self):
        path = self._ruta_recordatorios()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _guardar_recordatorios(self, data):
        path = self._ruta_recordatorios()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def _obtener_estado_recordatorio(self, year_key: str, tipo: str):
        data = self._cargar_recordatorios()
        bucket = data.setdefault(str(year_key), {})
        estado = bucket.setdefault(tipo, {})
        estado.setdefault("status", "active")
        return estado

    def _guardar_estado_recordatorio(self, year_key: str, tipo: str, status: str):
        data = self._cargar_recordatorios()
        bucket = data.setdefault(str(year_key), {})
        bucket[tipo] = {"status": status}
        self._guardar_recordatorios(data)
        return bucket[tipo]

    def mostrar_resumen_renta(self):
        mes_actual = self.mes_seleccionado.get().upper().strip()
        placeholder = self.mes_seleccionado.placeholder.upper() if self.mes_seleccionado.placeholder else ""
        if not mes_actual or mes_actual == placeholder:
            mes_actual = datetime.now().strftime("%B").upper()

        selected_year = str(get_current_year())
        selected_quarter = self._get_quarter_label_for_month(mes_actual)
        quarter_choice = {
            "label": selected_quarter,
            "months": self._get_quarter_months_for_label(selected_quarter),
        }
        resumen_trim = self._sumar_periodo(quarter_choice["months"])
        resumen_anual = self._sumar_periodo(self._meses_del_anio())

        ventana = ctk.CTkToplevel(self)
        ventana.title("Resumen de renta autónomo")
        ventana.configure(fg_color="#081722")
        ventana.minsize(1500, 900)
        ventana.geometry("1700x1000")
        ventana.resizable(True, True)
        ventana.grab_set()
        ventana.focus_force()
        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)
        ventana.bind("<Escape>", lambda event: ventana.destroy())

        try:
            ventana.update_idletasks()
            ventana.state("zoomed")
        except Exception:
            try:
                ventana.attributes("-fullscreen", True)
            except Exception:
                pass

        ventana.grid_columnconfigure(0, weight=1)
        ventana.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(ventana, fg_color="#0d1b2a", corner_radius=20, border_width=1, border_color="#2f4869")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        header.grid_columnconfigure(2, weight=0)

        title_wrap = ctk.CTkFrame(header, fg_color="transparent")
        title_wrap.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 0))
        ctk.CTkLabel(title_wrap, text="📊",
                     font=("Segoe UI", 28, "bold"), text_color="#5bc0ff").pack(side="left")
        ctk.CTkLabel(title_wrap, text="RESUMEN DE RENTA AUTÓNOMO",
                     font=("Segoe UI", 28, "bold"), text_color="#5bc0ff",
                     anchor="w").pack(side="left", padx=(10, 0))
        ctk.CTkLabel(header, text="Periodo activo: 303/130 trimestrales · 100 anual · 390 en cierre de IVA",
                     font=("Segoe UI", 12), text_color="#bfd2ea").grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))

        class DropdownField:
            def __init__(self, master, values, width, height, fg_color, button_color, text_color, border_color="#2f4869", command=None):
                self.values = list(values)
                self.command = command
                self.current = self.values[0] if self.values else ""
                self.frame = ctk.CTkFrame(master, width=width, height=height, corner_radius=10, fg_color=fg_color, border_width=1, border_color=border_color)
                self.frame.grid_columnconfigure(0, weight=1)
                self.frame.grid_columnconfigure(1, weight=0)
                self.label = ctk.CTkLabel(self.frame, text=self.current, text_color=text_color, font=("Segoe UI", 12, "bold"), anchor="w", justify="left")
                self.label.grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=6)
                self.arrow = ctk.CTkButton(self.frame, text="▾", width=26, height=20, corner_radius=8, fg_color=button_color, hover_color=button_color, text_color="#edf4ff", font=("Segoe UI", 12, "bold"), border_width=0)
                self.arrow.grid(row=0, column=1, sticky="e", padx=(0, 8), pady=6)
                self.menu = tk.Menu(self.frame, tearoff=0, bg="#0d1b2a", fg="#edf4ff", activebackground="#1d3047", activeforeground="#edf4ff", bd=0, font=("Segoe UI", 11))
                for item in self.values:
                    self.menu.add_command(label=item, command=lambda v=item: self.set(v, trigger=True))
                self._open_menu = lambda event=None: self.menu.post(self.frame.winfo_rootx(), self.frame.winfo_rooty() + self.frame.winfo_height())
                self.frame.bind("<Button-1>", self._open_menu)
                self.label.bind("<Button-1>", self._open_menu)
                self.arrow.bind("<Button-1>", self._open_menu)
                self.frame.bind("<Enter>", lambda event: self.frame.configure(border_color="#5c7ca2"))
                self.frame.bind("<Leave>", lambda event: self.frame.configure(border_color=border_color))

            def set(self, value, trigger=False):
                self.current = str(value)
                self.label.configure(text=self.current)
                if trigger and self.command is not None:
                    self.command(self.current)

            def configure(self, command=None, **kwargs):
                if command is not None:
                    self.command = command

            def grid(self, *args, **kwargs):
                self.frame.grid(*args, **kwargs)

            def grid_remove(self):
                self.frame.grid_remove()

            def get(self):
                return self.current

        selector_trimestre = DropdownField(
            header,
            values=["1er Trimestre", "2º Trimestre", "3er Trimestre", "4º Trimestre"],
            width=200,
            height=34,
            fg_color="#122438",
            button_color="#0f6cbd",
            text_color="#edf4ff",
            border_color="#2f4869",
        )
        selector_trimestre.set(selected_quarter, trigger=False)
        selector_trimestre.grid(row=0, column=1, sticky="e", padx=(0, 10), pady=(18, 6))

        def sync_header_for_active_tab():
            current_tab = active_tab.upper()
            if current_tab == "ANUAL":
                selector_trimestre.grid_remove()
            else:
                selector_trimestre.grid()
                selector_trimestre.set(selected_quarter, trigger=False)

        selector_anio = DropdownField(
            header,
            values=SUPPORTED_YEARS,
            width=120,
            height=34,
            fg_color="#112437",
            button_color="#0f6cbd",
            text_color="#edf4ff",
            border_color="#2f4869",
        )
        selector_anio.set(selected_year, trigger=False)
        selector_anio.grid(row=0, column=2, sticky="e", padx=(0, 18), pady=(18, 6))

        active_tab = "TRIMESTRE"
        tabs_container = ctk.CTkFrame(ventana, fg_color="#0d1b2a", corner_radius=18, border_width=1, border_color="#2f4869")
        tabs_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        tabs_container.grid_columnconfigure(0, weight=1)
        tabs_container.grid_rowconfigure(1, weight=1)

        tab_selector = ctk.CTkSegmentedButton(
            tabs_container,
            values=["TRIMESTRE", "ANUAL"],
            width=260,
            height=32,
            corner_radius=10,
            fg_color="#16293d",
            selected_color="#0f6cbd",
            unselected_color="#1d3047",
            border_width=0,
            font=("Segoe UI", 12, "bold"),
            command=lambda value: on_tab_changed(value),
            dynamic_resizing=False,
        )
        tab_selector.grid(row=0, column=0, sticky="n", pady=(12, 10))
        tab_selector.set("TRIMESTRE")

        content_area = ctk.CTkFrame(tabs_container, fg_color="#0a1622", corner_radius=16, border_width=1, border_color="#2f4869")
        content_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        content_area.grid_columnconfigure(0, weight=1)
        content_area.grid_rowconfigure(0, weight=1)

        tabs = {
            "TRIMESTRE": ctk.CTkFrame(content_area, fg_color="#0d1726"),
            "ANUAL": ctk.CTkFrame(content_area, fg_color="#0d1726"),
        }
        for name in ["TRIMESTRE", "ANUAL"]:
            tabs[name].grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            if name != "TRIMESTRE":
                tabs[name].grid_remove()

        estado_label = None

        def update_estado(resumen_obj):
            nonlocal estado_label
            total = resumen_obj["iva_estimado"] + resumen_obj["irpf_estimado"]
            estado = "Sin cuota a pagar" if total <= 0 else "Con cuota a pagar"
            if estado_label is not None:
                estado_label.configure(
                    text=(
                        f"Estado fiscal: {estado} | Cuota estimada: {total:.2f} €\n"
                        f"Bs - IRPF/IVA: {resumen_obj['base_imponible']:.2f} € | IVA + IRPF: {total:.2f} € | Resultado neto: {resumen_obj['resultado_neto']:.2f} €"
                    )
                )

        def render_tab(tab_name, resumen_obj, exercise_year=None):
            nonlocal selected_year
            year_value = str(exercise_year or selected_year)
            frame = tabs[str(tab_name).upper()]
            for child in frame.winfo_children():
                child.destroy()
            update_estado(resumen_obj)

            frame.grid_columnconfigure(0, weight=2)
            frame.grid_columnconfigure(1, weight=3)
            frame.grid_columnconfigure(2, weight=5)
            frame.grid_rowconfigure(0, weight=1)
            frame.configure(fg_color="#0a1622")

            def actualizar_trimestre_desde_selector(valor=None):
                nonlocal selected_quarter
                opt = str(valor or selected_quarter or "1er Trimestre").strip()
                selected_quarter = opt
                quarter_choice["label"] = opt
                quarter_choice["months"] = self._get_quarter_months_for_label(opt)
                resumen_actual = self._sumar_periodo(quarter_choice["months"])
                selector_trimestre.set(opt, trigger=False)
                render_tab("TRIMESTRE", resumen_actual)
                actualizar_recordatorio_ui()
                sync_header_for_active_tab()

            if tab_name == "TRIMESTRE":
                try:
                    selector_trimestre.configure(command=actualizar_trimestre_desde_selector)
                except Exception:
                    pass

            left = ctk.CTkFrame(frame, fg_color="#101f2d", corner_radius=18, border_width=1, border_color="#2f4869")
            left.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=(10, 12))
            left.grid_propagate(False)
            left.configure(width=300)
            left.grid_columnconfigure(0, weight=1)
            left.grid_rowconfigure(0, weight=1)

            middle = ctk.CTkFrame(frame, fg_color="#101f2d", corner_radius=18, border_width=1, border_color="#2f4869")
            middle.grid(row=0, column=1, sticky="nsew", padx=8, pady=(10, 12))
            middle.grid_propagate(False)
            middle.configure(width=340)
            middle.grid_columnconfigure(0, weight=1)
            middle.grid_rowconfigure(0, weight=1)

            right = ctk.CTkFrame(frame, fg_color="#101f2d", corner_radius=18, border_width=1, border_color="#2f4869")
            right.grid(row=0, column=2, sticky="nsew", padx=(8, 12), pady=(10, 12))
            right.grid_propagate(False)
            right.configure(width=560)
            right.grid_columnconfigure(0, weight=1)
            right.grid_rowconfigure(0, weight=1)

            resumen_scroll = ctk.CTkScrollableFrame(left, fg_color="#0e1a2a", corner_radius=14, border_width=1, border_color="#2f4869")
            resumen_scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
            resumen_scroll.grid_columnconfigure(0, weight=1)
            resumen_scroll.grid_rowconfigure(0, weight=1)
            resumen_scroll.configure(width=360)

            chart_panel = ctk.CTkFrame(middle, fg_color="#0d1726", corner_radius=14, border_width=1, border_color="#2f4869")
            chart_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
            chart_panel.grid_columnconfigure(0, weight=1)
            chart_panel.grid_rowconfigure(0, weight=1)

            modelos_scroll = ctk.CTkScrollableFrame(right, fg_color="#0e1a2a", corner_radius=14, border_width=1, border_color="#2f4869")
            modelos_scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
            modelos_scroll.grid_columnconfigure(0, weight=1)
            modelos_scroll.grid_rowconfigure(0, weight=1)
            modelos_scroll.configure(width=600)

            total_iva_irpf = resumen_obj["iva_estimado"] + resumen_obj["irpf_estimado"]
            datos = [
                ("Base imponible", resumen_obj["base"], "#dfeeff"),
                ("Gastos deducibles", resumen_obj["gastos_deducibles"], "#bfd3eb"),
                ("Bs - IRPF/IVA", resumen_obj["base_imponible"], "#a9d8c7"),
                ("IVA estimado", resumen_obj["iva_estimado"], "#cbd7e8"),
                ("IRPF estimado", resumen_obj["irpf_estimado"], "#cbd7e8"),
                ("IVA + IRPF", total_iva_irpf, "#cbd7e8"),
                ("Resultado neto", resumen_obj["resultado_neto"], "#a9d8c7"),
            ]

            for i, (label, valor, color_text) in enumerate(datos):
                fila = ctk.CTkFrame(resumen_scroll, fg_color="#132638", corner_radius=12, border_width=1, border_color="#2a466b")
                fila.grid(row=i, column=0, sticky="ew", padx=10, pady=(10 if i == 0 else 6, 6))
                ctk.CTkLabel(fila, text=label, font=("Segoe UI", 14, "bold"), text_color="#dfeeff", anchor="w").pack(side="left", padx=16, pady=12, expand=True)
                ctk.CTkLabel(fila, text=f"{valor:.2f} €", font=("Segoe UI", 14, "bold"), text_color=color_text, anchor="e").pack(side="right", padx=16, pady=12)

            if tab_name == "TRIMESTRE":
                casillas = self._casillas_periodo(quarter_choice["months"], tab_name, year_value)
                modelo_box = ctk.CTkFrame(modelos_scroll, fg_color="#0d1726", corner_radius=14, border_width=1, border_color="#2f4869")
                modelo_box.pack(fill="x", padx=10, pady=(10, 8))
                ctk.CTkLabel(modelo_box, text="Modelo 303 - IVA trimestral", font=("Segoe UI", 15, "bold"), text_color="#dfeeff").pack(anchor="w", padx=12, pady=(12, 8))
                for casilla, texto, valor in casillas["modelo_303"]:
                    fila_casilla = ctk.CTkFrame(modelo_box, fg_color="#132638", corner_radius=10, border_width=1, border_color="#2a466b")
                    fila_casilla.pack(fill="x", padx=12, pady=4)
                    ctk.CTkLabel(fila_casilla, text=f"{casilla} - {texto}", font=("Segoe UI", 11, "bold"), text_color="#dfeeff", anchor="w", justify="left", wraplength=240).pack(side="left", padx=10, pady=9, expand=True)
                    ctk.CTkLabel(fila_casilla, text=f"{valor:.2f} €", font=("Segoe UI", 11, "bold"), text_color="#7cc8ff", anchor="e").pack(side="right", padx=10, pady=9)

                modelo_130_box = ctk.CTkFrame(modelos_scroll, fg_color="#0d1726", corner_radius=14, border_width=1, border_color="#2f4869")
                modelo_130_box.pack(fill="x", padx=10, pady=(0, 8))
                ctk.CTkLabel(modelo_130_box, text="Modelo 130 - IRPF trimestral", font=("Segoe UI", 15, "bold"), text_color="#dfeeff").pack(anchor="w", padx=12, pady=(12, 8))
                for casilla, texto, valor in casillas["modelo_130"]:
                    fila_casilla = ctk.CTkFrame(modelo_130_box, fg_color="#132638", corner_radius=10, border_width=1, border_color="#2a466b")
                    fila_casilla.pack(fill="x", padx=12, pady=4)
                    ctk.CTkLabel(fila_casilla, text=f"{casilla} - {texto}", font=("Segoe UI", 11, "bold"), text_color="#dfeeff", anchor="w", justify="left", wraplength=240).pack(side="left", padx=10, pady=9, expand=True)
                    ctk.CTkLabel(fila_casilla, text=f"{valor:.2f} €", font=("Segoe UI", 11, "bold"), text_color="#7cc8ff", anchor="e").pack(side="right", padx=10, pady=9)

                estado = self._estado_declaracion(resumen_obj)
                validacion = ctk.CTkFrame(modelos_scroll, fg_color="#0d1726", corner_radius=14, border_width=1, border_color="#2f4869")
                validacion.pack(fill="x", padx=10, pady=(0, 10))
                ctk.CTkLabel(validacion, text="Validación de modelos", font=("Segoe UI", 14, "bold"), text_color="#dfeeff").pack(anchor="w", padx=12, pady=(12, 4))
                ctk.CTkLabel(
                    validacion,
                    text=(
                        f"303: {estado['estado_303']} · {estado['iva']:.2f} €\n"
                        f"130: {estado['estado_130']} · {estado['irpf']:.2f} €\n\n"
                        "Obligaciones trimestrales: 303 + 130.\n"
                        "Cierre anual de IVA (si aplica): 390.\n"
                        "La declaración anual de IRPF corresponde al Modelo 100."
                    ),
                    justify="left",
                    text_color="#dfeeff",
                    font=("Segoe UI", 11, "bold"),
                    wraplength=440,
                    anchor="w",
                ).pack(anchor="w", padx=12, pady=(0, 12))
            else:
                casillas = self._casillas_modelo_100(resumen_obj, year_value)
                modelo_box = ctk.CTkFrame(modelos_scroll, fg_color="#0d1726", corner_radius=14, border_width=1, border_color="#2f4869")
                modelo_box.pack(fill="x", padx=10, pady=(10, 8))
                ctk.CTkLabel(modelo_box, text="Modelo 100 anual - Declaración de la renta", font=("Segoe UI", 15, "bold"), text_color="#dfeeff").pack(anchor="w", padx=12, pady=(12, 8))
                for casilla, texto, valor in casillas["modelo_100"]:
                    fila_casilla = ctk.CTkFrame(modelo_box, fg_color="#132638", corner_radius=10, border_width=1, border_color="#2a466b")
                    fila_casilla.pack(fill="x", padx=12, pady=4)
                    ctk.CTkLabel(fila_casilla, text=f"{casilla} - {texto}", font=("Segoe UI", 11, "bold"), text_color="#dfeeff", anchor="w", justify="left", wraplength=240).pack(side="left", padx=10, pady=9, expand=True)
                    ctk.CTkLabel(fila_casilla, text=f"{valor:.2f} €", font=("Segoe UI", 11, "bold"), text_color="#7cc8ff", anchor="e").pack(side="right", padx=10, pady=9)

                validacion = ctk.CTkFrame(modelos_scroll, fg_color="#0d1726", corner_radius=14, border_width=1, border_color="#2f4869")
                validacion.pack(fill="x", padx=10, pady=(0, 10))
                ctk.CTkLabel(validacion, text="Modelo 100 anual", font=("Segoe UI", 14, "bold"), text_color="#dfeeff").pack(anchor="w", padx=12, pady=(12, 4))
                ctk.CTkLabel(
                    validacion,
                    text=(
                        "La declaración anual del IRPF se gestiona con el Modelo 100.\n"
                        "El 303 y el 130 son trimestrales y no deben mezclarse con la renta anual.\n\n"
                        "Resumen correcto: 303/130 por trimestre; 390 en cierre anual de IVA si procede; 100 para la renta anual."
                    ),
                    justify="left",
                    text_color="#dfeeff",
                    font=("Segoe UI", 11, "bold"),
                    wraplength=440,
                    anchor="w",
                ).pack(anchor="w", padx=12, pady=(0, 12))

            cam = tk.Canvas(chart_panel, width=260, height=260, bg="#101f2d", highlightthickness=0)
            cam.grid(row=0, column=0, padx=10, pady=(18, 10), sticky="n")
            cx, cy, r = 130, 130, 90
            cam.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2f4869", width=2, fill="#0d1726")
            cam.create_oval(cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18, outline="#1c3350", width=1, fill="#101f2d")
            valor_base = max(0.0, resumen_obj["base_imponible"])
            valor_gasto = max(0.0, resumen_obj["gastos_deducibles"])
            total = max(valor_base + valor_gasto, 1.0)
            ang = 360 * (valor_base / total)
            cam.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=-ang, style="pieslice", fill="#7ccfc1", outline="#7ccfc1")
            cam.create_arc(cx - r, cy - r, cx + r, cy + r, start=90 - ang, extent=-(360 - ang), style="pieslice", fill="#7ea7c9", outline="#7ea7c9")
            cam.create_oval(cx - 42, cy - 42, cx + 42, cy + 42, fill="#101f2d", outline="#2f4869", width=2)
            cam.create_text(cx, cy - 8, text=f"{valor_base:.0f}€", fill="#edf4ff", font=("Segoe UI", 22, "bold"))
            cam.create_text(cx, cy + 22, text="Base", fill="#9bb7d3", font=("Segoe UI", 10, "bold"))

        def on_tab_changed(value=None):
            nonlocal active_tab
            current = str(value if value is not None else active_tab).upper()
            active_tab = current if current in {"TRIMESTRE", "ANUAL"} else "TRIMESTRE"
            for tab_name, frame in tabs.items():
                if tab_name == active_tab:
                    frame.grid()
                else:
                    frame.grid_remove()

            if active_tab == "TRIMESTRE":
                render_tab("TRIMESTRE", self._sumar_periodo(quarter_choice["months"]), selected_year)
            else:
                render_tab("ANUAL", self._sumar_periodo(self._meses_del_anio()), selected_year)
            sync_header_for_active_tab()

        tab_selector.configure(command=lambda value: on_tab_changed(value))
        on_tab_changed("TRIMESTRE")
        recordatorio_frame = ctk.CTkFrame(ventana, fg_color="#0d1b2a", corner_radius=16, border_width=1, border_color="#2f4869")
        recordatorio_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        recordatorio_frame.grid_columnconfigure(0, weight=1)
        recordatorio_frame.grid_columnconfigure(1, weight=1)
        recordatorio_frame.grid_columnconfigure(2, weight=1)
        recordatorio_frame.grid_rowconfigure(1, weight=1)

        def actualizar_recordatorio_ui():
            trimestre_status = self._obtener_estado_recordatorio(selected_year, "trimestrale").get("status", "active")
            anual_status = self._obtener_estado_recordatorio(selected_year, "anual").get("status", "active")

            def estado_label_text(status):
                if status == "done":
                    return "✅ Hecho"
                if status == "disabled":
                    return "🔒 Desactivado"
                return "⏳ Pendiente"

            trimestre_label = estado_label_text(trimestre_status)
            anual_label = estado_label_text(anual_status)

            for child in recordatorio_frame.winfo_children():
                child.destroy()

            ctk.CTkLabel(recordatorio_frame, text="Recordatorios de declaración", font=("Segoe UI", 15, "bold"), text_color="#5bc0ff", anchor="w").grid(row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=(12, 8))

            paneles = []
            for idx in range(3):
                panel = ctk.CTkFrame(recordatorio_frame, fg_color="#122233", corner_radius=12, border_width=1, border_color="#2f4869")
                panel.grid(row=1, column=idx, sticky="nsew", padx=(14 if idx == 0 else 8, 8 if idx < 2 else 14), pady=(0, 8))
                panel.grid_propagate(False)
                panel.configure(height=110)
                paneles.append(panel)

            def crear_caja(parent, title, status_text, key):
                parent.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(parent, text=title, font=("Segoe UI", 12, "bold"), text_color="#edf4ff", anchor="w").grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
                ctk.CTkLabel(parent, text=status_text, font=("Segoe UI", 10), text_color="#bfd2ea", anchor="w").grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

                botones = ctk.CTkFrame(parent, fg_color="transparent")
                botones.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
                for column in range(3):
                    botones.grid_columnconfigure(column, weight=1)

                ctk.CTkButton(botones, text="✅ Hecho", command=lambda k=key: (self._guardar_estado_recordatorio(selected_year, k, "done"), actualizar_recordatorio_ui()), width=60, height=26, fg_color="#2a4058", hover_color="#334f72", border_color="#5c7ca2", border_width=1, text_color="#edf4ff", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=(0, 4), sticky="ew")
                ctk.CTkButton(botones, text="🔒 Desactivar", command=lambda k=key: (self._guardar_estado_recordatorio(selected_year, k, "disabled"), actualizar_recordatorio_ui()), width=72, height=26, fg_color="#3d4450", hover_color="#495967", border_color="#667788", border_width=1, text_color="#edf4ff", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=4, sticky="ew")
                ctk.CTkButton(botones, text="🔄 Reactivar", command=lambda k=key: (self._guardar_estado_recordatorio(selected_year, k, "active"), actualizar_recordatorio_ui()), width=72, height=26, fg_color="#2a4058", hover_color="#334f72", border_color="#5c7ca2", border_width=1, text_color="#edf4ff", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=(4, 0), sticky="ew")

            crear_caja(paneles[0], "Trimestral", trimestre_label, "trimestral")
            crear_caja(paneles[1], "Anual", anual_label, "anual")

            ctk.CTkLabel(paneles[2], text="Sigue el control del año", font=("Segoe UI", 11), text_color="#bfd2ea", justify="left", wraplength=220).pack(anchor="w", padx=12, pady=(12, 6))
            ctk.CTkLabel(paneles[2], text=f"Periodo actual: {selected_quarter} · {selected_year}", font=("Segoe UI", 11, "bold"), text_color="#5bc0ff", justify="left", wraplength=220).pack(anchor="w", padx=12, pady=(0, 10))

        def on_year_changed(value):
            nonlocal selected_year
            selected_year = str(value)
            render_tab("TRIMESTRE", self._sumar_periodo(quarter_choice["months"]), selected_year)
            render_tab("ANUAL", self._sumar_periodo(self._meses_del_anio()), selected_year)
            actualizar_recordatorio_ui()
            sync_header_for_active_tab()

        selector_anio.configure(command=on_year_changed)

        actualizar_recordatorio_ui()
        render_tab("TRIMESTRE", resumen_trim, selected_year)
        render_tab("ANUAL", resumen_anual, selected_year)
        sync_header_for_active_tab()

        total_trim = resumen_trim["iva_estimado"] + resumen_trim["irpf_estimado"]
        estado_trim = "Sin cuota a pagar" if total_trim <= 0 else "Con cuota a pagar"
        estado_texto = (
            f"Estado fiscal: {estado_trim} | Total a pagar: {total_trim:.2f} €\n"
            f"Bs - IRPF/IVA: {resumen_trim['base_imponible']:.2f} € | IVA: {resumen_trim['iva_estimado']:.2f} € | IRPF: {resumen_trim['irpf_estimado']:.2f} €"
        )

        estado = ctk.CTkFrame(ventana, fg_color="#0f1d2e", corner_radius=14, border_width=1, border_color="#2f4869")
        estado.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        estado_label = ctk.CTkLabel(estado, text=estado_texto, font=("Segoe UI", 14, "bold"), text_color="#dfeeff", justify="left", anchor="w")
        estado_label.pack(anchor="w", padx=18, pady=12)

        def pdf_actual():
            nombre = active_tab.upper()
            if nombre == "TRIMESTRE":
                resumen_actual = self._sumar_periodo(quarter_choice["months"])
                periodo_label = quarter_choice["label"]
                self.generar_pdf_declaracion_renta(resumen_actual, periodo_label, None, selected_year)
            else:
                resumen_actual = resumen_anual
                periodo_label = "ANUAL"
                self.generar_pdf_declaracion_renta(resumen_actual, periodo_label, None, selected_year)

        pie = ctk.CTkFrame(ventana, fg_color="#0f1d2e", corner_radius=18, border_width=1, border_color="#2f4869")
        pie.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        pie.grid_columnconfigure(0, weight=1)
        pie.grid_columnconfigure(1, weight=1)
        pie.grid_columnconfigure(2, weight=1)
        pie.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(
            pie, text="📄 Generar PDF",
            command=pdf_actual,
            width=220, height=42, corner_radius=10,
            fg_color="#233a52", hover_color="#2c4867", border_color="#4f6985", border_width=1,
            text_color="#edf4ff", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, padx=(18, 10), pady=14, sticky="ew")

        ctk.CTkButton(
            pie, text="📦 Exportar archivo",
            command=lambda: self.exportar_periodo_actual(
                year=selected_year,
                tab_name=active_tab,
                periodo_label=(quarter_choice["label"] if active_tab.upper() == "TRIMESTRE" else "ANUAL")
            ),
            width=220, height=42, corner_radius=10,
            fg_color="#233a52", hover_color="#2c4867", border_color="#4f6985", border_width=1,
            text_color="#edf4ff", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=1, padx=(10, 10), pady=14, sticky="ew")

        ctk.CTkButton(
            pie, text="📁 Abrir liquidaciones",
            command=self.abrir_carpeta_declaracion,
            width=220, height=42, corner_radius=10,
            fg_color="#233a52", hover_color="#2c4867", border_color="#4f6985", border_width=1,
            text_color="#edf4ff", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=2, padx=(10, 10), pady=14, sticky="ew")

        ctk.CTkButton(
            pie, text="Cerrar",
            command=ventana.destroy,
            width=220, height=42, corner_radius=10,
            fg_color="#4a3b42", hover_color="#5d4951", border_color="#7d6470", border_width=1,
            text_color="#f3edf2", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=3, padx=(10, 18), pady=14, sticky="ew")

    def _actualizar_ruta_exportacion(self, year=None):
        year_value = str(year or self.anio_actual or get_current_year()).strip() or str(get_current_year())
        self.anio_actual = year_value
        self.CARPETA_PDF = os.path.join(self.BASE_DIR, "PDFS", "liquidaciones", year_value)
        self.CARPETA_DATA = os.path.join(self.CARPETA_PDF, "data")
        self.CARPETA_DECLARACION = os.path.join(self.CARPETA_PDF, "declaraciones")
        os.makedirs(os.path.join(self.BASE_DIR, "PDFS"), exist_ok=True)
        os.makedirs(os.path.join(self.BASE_DIR, "PDFS", "liquidaciones"), exist_ok=True)
        os.makedirs(self.CARPETA_PDF, exist_ok=True)
        os.makedirs(self.CARPETA_DATA, exist_ok=True)
        os.makedirs(self.CARPETA_DECLARACION, exist_ok=True)
        return self.CARPETA_PDF

    def generar_pdf_declaracion_renta(self, resumen=None, periodo="TRIMESTRE", mes_actual=None, year=None):
        if resumen is None:
            mes_actual = self.mes_seleccionado.get().upper().strip()
            placeholder = self.mes_seleccionado.placeholder.upper() if self.mes_seleccionado.placeholder else ""
            if not mes_actual or mes_actual == placeholder:
                messagebox.showwarning("Sin mes", "Selecciona un mes para ver la declaración.")
                return
            trimestre = self._meses_del_trimestre(mes_actual)
            resumen = self._sumar_periodo(trimestre)

        os.makedirs(self.CARPETA_DECLARACION, exist_ok=True)

        year_for_export = str(year or get_current_year())
        periodo_label = str(periodo or (mes_actual or "TRIMESTRE")).strip()
        is_anual = isinstance(periodo, str) and "ANUAL" in periodo.upper()

        if is_anual:
            nome_periodo = "ANUAL"
            file_name = self._generar_nombre_archivo_declaracion(nome_periodo, year_for_export, "pdf")
            modelo_data = self._casillas_modelo_100(resumen, year_for_export)
            casillas = modelo_data["modelo_100"]
            titulo_pdf = "MODELO 100 - DECLARACION ANUAL DE LA RENTA"
            descripcion = (
                "Para la renta anual revisa en este orden: base imponible, cuotas, pagos a cuenta, "
                "casilla 0545 y 0546, y resultado final en 0610/0700."
            )
            pasos = [
                "1. Comprueba la base imponible general y la base liquidable del ejercicio.",
                "2. Revisa las casillas 0435, 0460, 0500 y 0510 para comprobar la base anual.",
                "3. Valida la cuota estatal y autonómica en 0545 y 0546.",
                "4. Comprueba el resultado final en 0610 y la cuota a pagar o devolver en 0700.",
            ]
            modelo_cabecera = "Modelo 100"
        else:
            if not periodo_label or periodo_label == "TRIMESTRE":
                periodo_label = self._get_current_quarter_label()
            nome_periodo = periodo_label
            file_name = self._generar_nombre_archivo_declaracion(nome_periodo, year_for_export, "pdf")
            months = self._resolver_periodo_export(nome_periodo)[1]
            periodo_data = self._casillas_periodo(months, nome_periodo, year_for_export)
            casillas = periodo_data["modelo_303"] + periodo_data["modelo_130"]
            titulo_pdf = "MODELOS 303 Y 130 - DECLARACION TRIMESTRAL"
            descripcion = (
                "Para el trimestre revisa el IVA del 303 y el IRPF del 130, comprobando tanto la base "
                "como la retencion y el resultado final a ingresar o devolver."
            )
            pasos = [
                "1. Calcula la base imponible y la cuota de IVA del 303 en las casillas 07, 09, 28, 29 y 71.",
                "2. Comprueba la base, rendimiento neto y cuota de IRPF en 01, 02, 03, 04 y 05 del 130.",
                "3. Verifica si corresponde ingreso o devolucion segun la cuota final del trimestre.",
                "4. Presenta el resultado final del trimestre con la declaracion independiente del ano.",
            ]
            modelo_cabecera = "Modelos 303 + 130"
        path = file_name

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleBrand",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=colors.HexColor("#0f6cbd"),
            alignment=1,
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "SubtitleBrand",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#355d7a"),
            alignment=1,
            spaceAfter=12,
        )
        label_style = ParagraphStyle(
            "LabelBrand",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#16324b"),
            spaceAfter=4,
        )

        elements = []

        logo_path = None
        posibles = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "logo.png"),
            os.path.join(os.getcwd(), "assets", "logo.png"),
            os.path.join(os.getcwd(), "logo.png"),
        ]
        for p in posibles:
            candidate = os.path.abspath(p)
            if os.path.exists(candidate):
                logo_path = candidate
                break

        header_table = Table([["", "", ""]], colWidths=[90, 300, 110])
        header_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0d1a2a")),
            ("GRID", (0, 0), (-1, -1), 0.0, colors.HexColor("#0d1a2a")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]))

        if logo_path:
            try:
                logo_img = RLImage(logo_path, width=54, height=54)
                header_period = periodo_label or (mes_actual or "Periodo actual")
                header_table = Table([[logo_img, Paragraph("GESTOR PRO", title_style), Paragraph(f"{header_period}", subtitle_style)]], colWidths=[90, 250, 130])
                header_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0d1a2a")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (1, 0), "LEFT"),
                    ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.0, colors.HexColor("#0d1a2a")),
                ]))
            except Exception:
                pass

        elements.append(header_table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(titulo_pdf, title_style))
        elements.append(Paragraph(f"Periodo: {periodo_label or nome_periodo} | Ejercicio {year_for_export}", subtitle_style))
        elements.append(Paragraph(f"Documento: {modelo_cabecera}", label_style))
        elements.append(Spacer(1, 8))

        step_rows = [[Paragraph("PASO A PASO", ParagraphStyle("StepTitle", parent=styles["BodyText"], fontName="Helvetica-Bold", textColor=colors.HexColor("#0f6cbd")))] ]
        for step in pasos:
            step_rows.append([Paragraph(step)])

        steps_table = Table(step_rows, colWidths=[460])
        steps_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f2ff")),
            ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#cfe2ff")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(steps_table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(descripcion, label_style))
        elements.append(Spacer(1, 8))

        row_data = [["CASILLA", "CONCEPTO", "IMPORTE"]]
        for casilla, etiqueta, valor in casillas:
            row_data.append([
                str(casilla).replace("Casilla ", ""),
                str(etiqueta),
                f"{float(valor or 0.0):.2f}",
            ])

        casillas_table = Table(row_data, colWidths=[80, 260, 100])
        casillas_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fbff"), colors.HexColor("#eef5fd")]),
            ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#244b73")),
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
        ]))
        elements.append(casillas_table)
        elements.append(Spacer(1, 12))

        if is_anual:
            cuota_total = float(resumen.get("irpf_estimado", 0.0))
            elements.append(Paragraph(f"Cuota estimada anual: {cuota_total:.2f} €", label_style))
        else:
            cuota = float(resumen.get("iva_estimado", 0.0)) + float(resumen.get("irpf_estimado", 0.0))
            elements.append(Paragraph(f"Cuota estimada trimestre: {cuota:.2f} €", label_style))

        try:
            doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=35, rightMargin=35, topMargin=20, bottomMargin=25)
            doc.build(elements)
            messagebox.showinfo("PDF generado", f"Declaración exportada en:\n{path}")
            return path
        except Exception as e:
            messagebox.showerror("Error al generar PDF", f"No se pudo generar el PDF:\n{e}")
            return None    # ==============================================================
    # OBTENER DATOS + PDF (sin cambios funcionales)
    # ==============================================================
    def obtener_datos(self):
        datos = {}
        datos["base"] = self.numero(self.e_base)
        datos["transferencia"] = self.numero(self.e_trans)
        datos["mes"] = self.mes_seleccionado.get().upper()
        materiales = []; total_material = 0
        for fila in self.cont_mat.winfo_children():
            if len(fila.winfo_children()) == 0: continue
            importe = self.numero(fila.winfo_children()[0])
            materiales.append({"descripcion": "Material", "importe": importe})
            total_material += importe
        datos["materiales"] = materiales
        datos["total_material"] = total_material
        combustible = []; total_comb = 0
        for fila in self.cont_comb.winfo_children():
            if len(fila.winfo_children()) == 0: continue
            importe = self.numero(fila.winfo_children()[0])
            combustible.append({"descripcion": "Ticket", "importe": importe})
            total_comb += importe
        datos["combustible"] = combustible
        datos["total_combustible"] = total_comb
        fijos = []; total_fijos = 0
        for fila in self.cont_fijos.winfo_children():
            nombre = fila.winfo_children()[0].get()
            importe = self.numero(fila.winfo_children()[1])
            fijos.append({"nombre": nombre, "importe": importe})
            total_fijos += importe
        datos["gastos_fijos"] = fijos; datos["total_fijos"] = total_fijos
        ajustes = []; total_ajustes = 0
        for fila in self.cont_ajustes.winfo_children():
            nombre = fila.winfo_children()[0].get()
            importe = self.numero(fila.winfo_children()[1])
            ajustes.append({"nombre": nombre, "importe": importe})
            total_ajustes += importe
        datos["ajustes"] = ajustes; datos["total_ajustes"] = total_ajustes
        extras = []; total_extras = 0
        for fila in self.cont_ext.winfo_children():
            if not hasattr(fila, "c"): continue
            fecha = ""
            for x in fila.winfo_children():
                for y in x.winfo_children() if hasattr(x, "winfo_children") else []:
                    if isinstance(y, DateEntry): fecha = self.formato_fecha(y.get())
            restante = self.numero(fila.c["res"])
            extras.append({"fecha": fecha, "tipo": fila.t,
                           "neto": self.numero(fila.c["n"]),
                           "iva": self.numero(fila.c["iva"]),
                           "irpf": self.numero(fila.c["irpf"]),
                           "restante": restante})
            total_extras += restante
        datos["extras"] = extras; datos["total_extras"] = total_extras
        datos["restando"] = datos["base"] - datos["total_material"] - datos["total_combustible"] / 2
        datos["iva"] = datos["base"] * 0.21
        datos["irpf"] = datos["restando"] * 0.20
        datos["total_factura"] = datos["base"] * 1.21
        datos["recibo"] = datos["transferencia"] - datos["iva"] - datos["irpf"]
        datos["mio"] = datos["recibo"] - datos["total_fijos"] + datos["total_extras"] + datos["total_ajustes"]
        return datos

    def abrir_carpeta(self):
        path = os.path.realpath(self.CARPETA_PDF)
        if os.name == 'nt': os.startfile(path)
        elif os.uname().sysname == 'Darwin': subprocess.call(["open", path])
        else: subprocess.call(["xdg-open", path])

    def abrir_carpeta_declaracion(self):
        path = os.path.realpath(self._actualizar_ruta_exportacion(self.anio_actual))
        os.makedirs(path, exist_ok=True)
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    def generar_pdf(self):
        try:
            datos = self.obtener_datos()

            # --- 1. OBTENER RUTA BASE REAL (Compatible con PyInstaller / .exe) ---
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))

            cwd_dir = os.getcwd()
            parent_dir = os.path.dirname(base_dir)

            # --- 2. BÚSQUEDA ROBUSTA DEL LOGO ---
            nombres_archivo = ["logo.png", "logo.PNG", "logo.jpg", "logo.jpeg", "LOGO.PNG"]
            rutas_a_probar = [
                base_dir,
                cwd_dir,
                parent_dir,
                r"C:\Users\Admin\Desktop\Pruebas"
            ]

            ruta_logo = None
            for carpeta in rutas_a_probar:
                for nombre in nombres_archivo:
                    # Prueba dentro de la carpeta 'assets'
                    posible_ruta_assets = os.path.join(carpeta, "assets", nombre)
                    if os.path.exists(posible_ruta_assets):
                        ruta_logo = posible_ruta_assets
                        break
                    # Prueba directamente en la raíz por si acaso
                    posible_ruta_raiz = os.path.join(carpeta, nombre)
                    if os.path.exists(posible_ruta_raiz):
                        ruta_logo = posible_ruta_raiz
                        break
                if ruta_logo:
                    break

            # --- 3. CONFIGURACIÓN DE CARPETA Y DOCUMENTO ---
            carpeta_pdf = self._actualizar_ruta_exportacion(self.anio_actual)
            os.makedirs(carpeta_pdf, exist_ok=True)

            mes = self.mes_seleccionado.get().upper()
            filename = os.path.join(carpeta_pdf, f"Liquidacion_{mes}_{self.anio_actual}.pdf")

            elements = []
            styles = getSampleStyleSheet()

            # --- 4. INSERTAR LOGO EN EL PDF ---
            if ruta_logo and os.path.exists(ruta_logo):
                img_logo = RLImage(ruta_logo, width=80, height=80)
                img_logo.hAlign = 'CENTER'
                elements.append(img_logo)
                elements.append(Spacer(1, 6))
            else:
                messagebox.showwarning(
                    "Logo no encontrado",
                    f"No se encontró el logo.\nBuscado en: {os.path.join(base_dir, 'assets')}"
                )

            # Título del Informe
            estilo_titulo = ParagraphStyle(
                'TituloPersonalizado', parent=styles['Title'],
                fontSize=18, textColor=colors.black,
                alignment=1, spaceAfter=12
            )
            elements.append(Paragraph(f"INFORME DE LIQUIDACIÓN - {mes}", estilo_titulo))

            # Estilo reutilizable de tablas
            def aplicar_estilo_tabla(t):
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#282828")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                ]))
                return t

            # --- TABLA RESUMEN ---
            bs = datos["base"]; tr = datos["transferencia"]
            tot_fijos = datos["total_fijos"]; tot_ajustes = datos["total_ajustes"]
            restando_gastos = datos["restando"]
            iva_calc = datos["iva"]; irpf_calc = datos["irpf"]
            recibo_final = datos["recibo"]

            data_res = [
                ["CONCEPTO", "VALOR", "RESUMEN", "VALOR"],
                ["BASE IMP.", f"{bs:.2f} €", "REST. GASTOS", f"{restando_gastos:.2f} €"],
                ["IVA (21%)", f"{iva_calc:.2f} €", "IRPF (20%)", f"{irpf_calc:.2f} €"],
                ["TOTAL FACT.", f"{bs + iva_calc:.2f} €", "IVA + IRPF", f"{iva_calc + irpf_calc:.2f} €"],
                ["TRANSFER.", f"{tr:.2f} €", "RECIBO FIN.", f"{recibo_final:.2f} €"]
            ]
            t_res = aplicar_estilo_tabla(Table(data_res, colWidths=[90, 80, 90, 80]))
            t_res.setStyle(TableStyle([
                ('BACKGROUND', (2, 4), (3, 4), colors.yellow),
                ('TEXTCOLOR', (2, 4), (3, 4), colors.black)
            ]))
            elements.append(t_res)
            elements.append(Spacer(1, 20))

            # --- TABLA DESGLOSE DE GASTOS ---
            elements.append(Paragraph("DESGLOSE DE GASTOS", styles["Heading2"]))
            datos_desglose = [["TIPO", "DESCRIPCIÓN", "IMPORTE"]]
            tot_mat = 0; tot_comb = 0

            for w in self.cont_mat.winfo_children():
                if len(w.winfo_children()) > 0:
                    val = self.numero(w.winfo_children()[0])
                    datos_desglose.append(["MATERIAL", "Gasto", f"{val:.2f} €"])
                    tot_mat += val

            for w in self.cont_comb.winfo_children():
                if len(w.winfo_children()) > 0:
                    val = self.numero(w.winfo_children()[0])
                    datos_desglose.append(["COMBUSTIBLE", "Ticket", f"{val:.2f} €"])
                    tot_comb += (val / 2)

            datos_desglose.append(["", "TOTAL MATERIALES", f"{tot_mat:.2f} €"])
            datos_desglose.append(["", "50% COMBUSTIBLE", f"{tot_comb:.2f} €"])
            datos_desglose.append(["", "TOTAL DEDUCIBLE", f"{tot_mat + tot_comb:.2f} €"])
            t_desglose = aplicar_estilo_tabla(Table(datos_desglose, colWidths=[100, 150, 100]))
            t_desglose.setStyle(TableStyle([
                ('BACKGROUND', (1, -1), (2, -1), colors.HexColor("#00FFFF")),
                ('TEXTCOLOR', (1, -1), (2, -1), colors.black)
            ]))
            elements.append(t_desglose)
            elements.append(Spacer(1, 20))

            # --- TABLA GASTOS FIJOS ---
            elements.append(Paragraph("GASTOS FIJOS", styles["Heading2"]))
            datos_fijos = [["CONCEPTO", "IMPORTE"]]
            total_fijos = 0
            for gasto in datos["gastos_fijos"]:
                datos_fijos.append([gasto["nombre"], f'{gasto["importe"]:.2f} €'])
                total_fijos += gasto["importe"]
            datos_fijos.append(["TOTAL GASTOS FIJOS", f"{total_fijos:.2f} €"])

            t_fijos = Table(datos_fijos, colWidths=[200, 100])
            t_fijos.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#282828")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.red),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(t_fijos)
            elements.append(Spacer(1, 20))

            # --- TABLA AJUSTES MES ANTERIOR ---
            elements.append(Paragraph("AJUSTES MES ANTERIOR", styles["Heading2"]))
            datos_ajuste = [["CONCEPTO", "IMPORTE"]]
            total_ajustes = sum(self.numero(w.winfo_children()[1]) for w in self.cont_ajustes.winfo_children())
            for ajuste in datos["ajustes"]:
                datos_ajuste.append([ajuste["nombre"], f'{ajuste["importe"]:.2f} €'])
            datos_ajuste.append(["TOTAL AJUSTES", f"{total_ajustes:.2f} €"])

            t_ajuste = Table(datos_ajuste, colWidths=[200, 100])
            t_ajuste.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#282828")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#90EE90")),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                ('ALIGN', (0, -1), (0, -1), 'LEFT'),
                ('ALIGN', (1, -1), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(t_ajuste)
            elements.append(Spacer(1, 20))

            # --- TABLA EXTRAS ---
            elements.append(Paragraph("EXTRAS TF / EFECTIVO", styles["Heading2"]))
            datos_ext = [["FECHA", "TIPO", "NETO", "TOTAL"]]
            total_extras = 0
            for extra in datos["extras"]:
                datos_ext.append([
                    extra["fecha"],
                    "TF" if extra["tipo"] == "Bizum" else extra["tipo"],
                    f'{extra["neto"]:.2f} €',
                    f'{extra["restante"]:.2f} €'
                ])
                total_extras += extra["restante"]
            datos_ext.append(["TOTAL NETO", "", "", f"{total_extras:.2f} €"])

            t_ext = Table(datos_ext, colWidths=[80, 80, 80, 80])
            t_ext.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#282828")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#90EE90")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(t_ext)
            elements.append(Spacer(1, 20))

            # --- RESULTADO FINAL (€ MIO) ---
            resultado_mio = tr - (iva_calc + irpf_calc) - total_fijos + total_extras + total_ajustes
            texto_final = f"€ MIO: {resultado_mio:.2f}"
            elements.append(Spacer(1, 10))

            t_mio = Table([[texto_final]], colWidths=[450])
            t_mio.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 22),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(t_mio)

            # --- CONSTRUIR PDF ---
            doc = SimpleDocTemplate(
                filename, pagesize=A4, topMargin=20,
                leftMargin=40, rightMargin=40
            )
            doc.build(elements)

            # Guardar snapshot
            self._guardar_mes(mes)
            messagebox.showinfo("Éxito", f"PDF generado correctamente en:\n{filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Error al generar el PDF: {e}")
