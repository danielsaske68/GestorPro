# ==========================================================
# PRESUPUESTOS.PY - GESTOR PRO
# INTERFAZ ORIGINAL + PDF PROFESIONAL
# ==========================================================

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
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

# ==========================================================
# CONFIGURACIÓN DE COLORES
# ==========================================================
THEME_COLOR = "#0056b3"
PANEL_COLOR = "#1e1e1e"
BG_COLOR = "#111111"
SUCCESS_COLOR = "#00ff88"
ERROR_COLOR = "#ff4444"

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

        os.makedirs("data", exist_ok=True)
        self.archivo_clientes = os.path.join("data", "clientes.json")
        self.clientes = self.cargar_clientes()
        self.cliente_seleccionado = None
        self.baremos = self.cargar_baremos()

        print("BAREMOS CARGADOS:", len(self.baremos))

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # PANEL IZQUIERDO
        self.left_frame = ctk.CTkScrollableFrame(self, corner_radius=15, fg_color=PANEL_COLOR, width=380)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(self.left_frame, text="📝 DATOS DEL CLIENTE", font=("Arial", 20, "bold"), text_color="#4da6ff").pack(pady=(15, 5), padx=20, anchor="w")

        ctk.CTkLabel(
            self.left_frame,
            text="👤 CLIENTE",
            font=("Arial",20,"bold"),
            text_color="#4da6ff"
        ).pack(pady=(15,5), padx=20, anchor="w")

        self.lbl_cliente_actual = ctk.CTkLabel(
            self.left_frame,
            text="Sin cliente seleccionado",
            font=("Arial",15),
            text_color="white"
        )

        self.lbl_cliente_actual.pack(
            pady=5,
            padx=20,
            anchor="w"
        )

        ctk.CTkButton(
            self.left_frame,
            text="👤 Buscar / Añadir / Editar Cliente",
            height=40,
            command=self.abrir_gestor_clientes
        ).pack(
            pady=10,
            padx=20,
            fill="x"
        )

        ctk.CTkLabel(self.left_frame, text="➕ AÑADIR CONCEPTO", font=("Arial", 20, "bold"), text_color="#4da6ff").pack(pady=(20, 5), padx=20, anchor="w")

        self.txt_desc = ctk.CTkTextbox(self.left_frame, height=90, fg_color="#2b2b2b", border_color="#555555", border_width=1, font=("Arial", 16))
        self.txt_desc.pack(pady=2, padx=20, fill="x")

        self.txt_precio = self.crear_campo_entrada(self.left_frame, "Precio:")
        self.txt_cant = self.crear_campo_entrada(self.left_frame, "Cantidad:")
        self.txt_cant.insert(0, "1")

        self.txt_desc.bind("<KeyRelease>", self.comprobar_campos_item)
        self.txt_desc.bind(
            "<Return>",
            self.enter_analizar
        )

        self.txt_precio.bind(
            "<Return>",
            lambda e: self.pasar_a_cantidad()
        )

        self.txt_cant.bind("<KeyRelease>", self.comprobar_campos_item)

        self.txt_cant.bind(
            "<Return>",
            self.enter_cantidad
        )

        # --- CÓDIGO NUEVO PARA EL TABULADOR ---
        def cambiar_foco(event):
            self.txt_precio.focus()
            return "break" # El "break" evita que se escriba el tabulador en la caja de texto
        
        self.txt_desc.bind("<Tab>", cambiar_foco)

        self.btn_add = ctk.CTkButton(
            self.left_frame,
            text="✨ Añadir Ítem",
            fg_color=THEME_COLOR,
            height=45,
            font=("Arial",18,"bold"),
            command=self.añadir_item,
            state="disabled"
        )

        self.btn_add.pack(
            pady=25,
            padx=20,
            fill="x"
        )

        ctk.CTkButton(
            self.left_frame,
            text="🤖 ANALIZAR TRABAJO",
            fg_color="#00aa66",
            height=45,
            font=("Arial",18,"bold"),
            command=self.analizar_trabajo
        ).pack(pady=10, padx=20, fill="x")

        ctk.CTkButton(
            self.left_frame,
            text="📚 VER BAREMOS",
            fg_color="#3366cc",
            height=45,
            font=("Arial",18,"bold"),
            command=self.ver_baremos
        ).pack(
            pady=10,
            padx=20,
            fill="x"
        )

        # PANEL DERECHO (Scrollable)
        self.right_frame = ctk.CTkScrollableFrame(self, corner_radius=15, fg_color=PANEL_COLOR)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(self.right_frame, text="📋 DESGLOSE DEL PRESUPUESTO", font=("Arial", 20, "bold")).pack(pady=15, padx=20, anchor="w")

        # TABLA
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1a1a1a", fieldbackground="#1a1a1a", foreground="white", rowheight=40, font=("Arial", 12))
        style.configure("Treeview.Heading", background="#333333", foreground="white", font=("Arial", 14, "bold"))

        tabla_frame = tk.Frame(self.right_frame, bg="#1a1a1a")
        tabla_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.tree = ttk.Treeview(tabla_frame, columns=("desc", "precio", "cant", "total"), show="headings")
        self.tree.heading("desc", text="DESCRIPCIÓN")
        self.tree.column("desc", width=250)
        self.tree.heading("precio", text="PRECIO")
        self.tree.heading("cant", text="CANT.")
        self.tree.heading("total", text="TOTAL")
        self.tree.pack(fill="both", expand=True, side="left")

        # BOTONES
        btn_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        btn_frame.pack(pady=10, padx=20, fill="x")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_frame, text="❌ Eliminar", height=40, font=("Arial", 12, "bold"), fg_color=ERROR_COLOR, command=self.eliminar_item).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="🧹 LIMPIAR TODOS LOS DATOS", height=40, font=("Arial", 12, "bold"), fg_color="#ff9900",  text_color="black", command=self.limpiar_todo).grid(row=0, column=1, padx=5, sticky="ew")

        ctk.CTkButton(self.right_frame, text="📂 IR A CARPETA PDF", height=40, font=("Arial", 14, "bold"), fg_color="#4da6ff", text_color="white", command=self.abrir_carpeta_pdf).pack(pady=(0, 10), padx=20, fill="x")

        # TOTALES Y GENERAR
        self.lbl_totales_ui = ctk.CTkLabel(self.right_frame, text="Subtotal: 0.00 € | IVA: 0.00 € | TOTAL: 0.00 €", font=("Arial", 16, "bold"), text_color=SUCCESS_COLOR)
        self.lbl_totales_ui.pack(pady=15)

        ctk.CTkButton(self.right_frame, text="📄 GENERAR PDF", fg_color=SUCCESS_COLOR, text_color="black", height=80, font=("Arial", 20, "bold"), command=self.generar_pdf_presupuesto).pack(fill="x", padx=20, pady=20)

    def enter_analizar(self,event=None):

        # Si hay texto, analiza
        texto = self.txt_desc.get(
            "1.0",
            "end-1c"
        ).strip()

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

    def ver_baremos(self):

        ventana = ctk.CTkToplevel(self)
        ventana.title("📚 Gestor de Baremos PRO")
        ventana.state("zoomed")
        ventana.grab_set()

        ventana.grid_columnconfigure(0, weight=1)
        ventana.grid_rowconfigure(2, weight=1)

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
            pady=5,
            sticky="nsew"
        )


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
            height=180,
            font=("Consolas",13)
        )

        inspector.grid(
            row=2,
            column=0,
            padx=10,
            pady=5,
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
            pady=10
        )

        ctk.CTkButton(
            botones,
            text="➕ Nuevo baremo",
            command=lambda:self.editor_baremo(ventana, None, cargar_tabla)
        ).pack(side="left",padx=5)

        ctk.CTkButton(
            botones,
            text="✏ Editar",
            command=lambda:self.editar_desde_tabla(tree, datos_filtrados, ventana, cargar_tabla)
        ).pack(side="left",padx=5)

        ctk.CTkButton(
            botones,
            text="🗑 Eliminar",
            fg_color="#aa2222",
            command=lambda:self.eliminar_baremo(tree,datos_filtrados)
        ).pack(side="left",padx=5)

        ctk.CTkButton(
            botones,
            text="📋 Duplicar",
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
        ctk.CTkLabel(contenedor, text=texto, font=("Arial", 16, "bold")).pack(pady=(12, 2), padx=20, anchor="w")
        entrada = ctk.CTkEntry(contenedor, height=40, fg_color="#2b2b2b", font=("Arial", 16))
        entrada.pack(pady=2, padx=20, fill="x")
        return entrada

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
        ventana.geometry("900x600")
        ventana.grab_set()

        ventana.grid_columnconfigure(0, weight=1)
        ventana.grid_columnconfigure(1, weight=1)
        ventana.grid_rowconfigure(1, weight=1)

        campos = {}

        # ==========================
        # FUNCIONES INTERNAS
        # ==========================

        def cargar_lista():
            lista.delete(0,"end")

            for cliente in sorted(
                self.clientes,
                key=lambda x:x["nombre"].lower()
            ):
                lista.insert(
                   "end",
                   cliente["nombre"]
                )

        def limpiar_campos():

            for campo in campos.values():
                campo.delete(0,"end")

        def nuevo_cliente():

            limpiar_campos()

        def guardar_cliente():

            cliente = {
                "nombre": campos["nombre"].get(),
                "telefono": campos["telefono"].get(),
                "nif": campos["nif"].get(),
                "direccion": campos["direccion"].get(),
                "localidad": campos["localidad"].get()
            }

            if not cliente["nombre"]:
                messagebox.showwarning(
                    "Aviso",
                    "El nombre es obligatorio"
                )
                return

            self.clientes.append(cliente)

            with open(
                self.archivo_clientes,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.clientes,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            self.cliente_actual = self.cliente_vacio()

            self.lbl_cliente_actual.configure(
                text=cliente["nombre"]
            )

            cargar_lista()

            messagebox.showinfo(
                "Guardado",
                "Cliente guardado correctamente"
            )

        def seleccionar_cliente():

            sel = lista.curselection()

            if not sel:
                return

            nombre = lista.get(sel)

            for cliente in self.clientes:

               if cliente["nombre"] == nombre:

                    self.cliente_actual = cliente
                    self.cliente_seleccionado = cliente

                    for clave in campos:

                        campos[clave].delete(
                            0,
                            "end"
                        )

                        campos[clave].insert(
                            0,
                            cliente.get(clave,"")
                        )

                    self.lbl_cliente_actual.configure(
                        text=cliente["nombre"]
                    )

                    break

        def eliminar_cliente():

            sel = lista.curselection()

            if not sel:
                return

            nombre = lista.get(sel)

            respuesta = messagebox.askyesno(
                "Eliminar",
                f"¿Eliminar {nombre}?"
            )

            if respuesta:

                self.clientes = [
                    c for c in self.clientes
                    if c["nombre"] != nombre
                ]

                with open(
                    self.archivo_clientes,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        self.clientes,
                        f,
                        indent=4,
                        ensure_ascii=False
                    )

                limpiar_campos()
                cargar_lista()

        # ==========================
        # INTERFAZ
        # ==========================

        ctk.CTkLabel(
            ventana,
            text="Clientes",
            font=("Arial",20,"bold")
        ).grid(
            row=0,
            column=0,
            pady=10
        )

        ctk.CTkLabel(
            ventana,
            text="Datos cliente",
            font=("Arial",20,"bold")
        ).grid(
            row=0,
            column=1,
            pady=10
        )

        lista = tk.Listbox(
            ventana,
            font=("Arial",14)
        )

        lista.bind(
            "<Double-Button-1>",
            lambda e: seleccionar_cliente()
        )

        lista.grid(
            row=1,
            column=0,
            padx=20,
            pady=10,
            sticky="nsew"
        )

        panel = ctk.CTkFrame(
            ventana
        )

        panel.grid(
            row=1,
            column=1,
            padx=20,
            pady=10,
            sticky="nsew"
        )

        datos=[
            ("Nombre","nombre"),
            ("Teléfono","telefono"),
            ("NIF","nif"),
            ("Dirección","direccion"),
            ("Localidad","localidad")
        ]

        for texto,clave in datos:

            ctk.CTkLabel(
                panel,
                text=texto
            ).pack(
                anchor="w",
                padx=20
            )

            entrada=ctk.CTkEntry(
                panel
            )

            entrada.pack(
                fill="x",
                padx=20,
                pady=5
            )

            campos[clave]=entrada

        ctk.CTkButton(
            panel,
            text="🆕 Nuevo",
            command=nuevo_cliente
        ).pack(
            fill="x",
            padx=20,
            pady=5
        )

        ctk.CTkButton(
            panel,
            text="💾 Guardar",
            fg_color="#008844",
            command=guardar_cliente
        ).pack(
            fill="x",
            padx=20,
            pady=5
        )

        ctk.CTkButton(
            panel,
            text="✔ Seleccionar",
            command=seleccionar_cliente
        ).pack(
            fill="x",
            padx=20,
            pady=5
        )

        ctk.CTkButton(
            panel,
            text="🗑 Eliminar",
            fg_color="#bb2222",
            command=eliminar_cliente
        ).pack(
            fill="x",
            padx=20,
            pady=5
        )

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
        texto = texto.lower()
        palabras_usuario = texto.split()
        resultados=[]
        for item in self.baremos:
            puntos=0
            palabras_detectadas=[]
            nombre=item.get(
                "nombre",
                ""
            ).lower()
            alias=item.get(
                "alias",
                []
            )
            buscar = item.get(
                "buscar",
                []
            )
            palabras = alias + buscar
            # Coincidencia nombre
            for palabra in palabras_usuario:
                if palabra in nombre:
                    puntos +=15
                    palabras_detectadas.append(
                        palabra
                    )
            # Coincidencia alias
            for frase in palabras:
                frase=frase.lower()
                if frase in texto:
                    puntos +=20
                    palabras_detectadas.append(
                        frase
                    )
                else:
                    for palabra in frase.split():
                        if palabra in palabras_usuario:
                            puntos+=5
                            palabras_detectadas.append(
                                palabra
                            )
            # aprendizaje previo
            aprendizaje=item.get(
                "aprendizaje",
                {}
            )
            palabras_aprendidas = (
                aprendizaje.get(
                    "palabras_aprendidas",
                    []
                )
                +
                aprendizaje.get(
                    "frases_aprendidas",
                    []
                )
            )
            for palabra in aprendizaje.get("palabras_aprendidas", []):
                if palabra in palabras_usuario:
                    puntos += 8
                    palabras_detectadas.append(palabra)
            if puntos>0:
                resultados.append({
                    "item":item,
                    "puntos":puntos,
                    "detectadas":list(
                        set(palabras_detectadas)
                    )
                })
        if not resultados:
            parecido = self.buscar_similitud_baremo(texto)
            if parecido:
                return parecido
            return None
        resultados.sort(
            key=lambda x:x["puntos"],
            reverse=True
        )
        mejor=resultados[0]
        porcentaje=min(
            mejor["puntos"]*5,
            99
        )
        mejor["porcentaje"]=porcentaje
        return mejor

    def mostrar_sugerencia_precio(self, resultado):
        sugerencia = resultado["item"]
        porcentaje = resultado["porcentaje"]
        precio = sugerencia.get(
            "precio_recomendado",
            sugerencia.get(
                "precio_sugerido",
                (
                    sugerencia["precio_min"]+
                    sugerencia["precio_max"]
                )/2
            )
        )
        respuesta = messagebox.askyesno(
            "🤖 Inteligencia Gestor Pro",
f"""
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
"""
        )
        if respuesta:
            self.aprender_confirmacion(
                sugerencia,
                resultado["detectadas"]
            )
            self.txt_desc.delete(
                "1.0",
                "end"
            )
            self.txt_desc.insert(
                "1.0",
                sugerencia["nombre"]
            )
            self.txt_precio.delete(
                0,
                "end"
            )
            self.txt_precio.insert(
                0,
                str(precio)
            )
            self.comprobar_campos_item()
            return True
        # SI DICE QUE NO
        nueva_descripcion = ctk.CTkInputDialog(
            text="No parece correcto.\nEscribe el trabajo correcto:",
            title="Corregir trabajo"
        ).get_input()
        if nueva_descripcion:

            texto_original = self.txt_desc.get(
                "1.0",
                "end-1c"
            ).strip()

            self.txt_desc.delete(
                "1.0",
                "end"
            )
            self.txt_desc.insert(
                "1.0",
                nueva_descripcion
            )
            # volver a analizar la corrección
            resultado_nuevo = self.buscar_precio_baremo(
                nueva_descripcion
            )

            if resultado_nuevo:
                aceptar = messagebox.askyesno(
                    "Corrección encontrada",
                    f"""
        He encontrado este trabajo:
        {resultado_nuevo['item']['nombre']}
        Precio recomendado:
        {resultado_nuevo['item'].get(
            'precio_recomendado',
            0
        )} €

        ¿Es este?
        """
                )
                if aceptar:
                    trabajo = resultado_nuevo["item"]
                    precio = trabajo.get(
                        "precio_recomendado",
                        (
                            trabajo["precio_min"]
                            +
                            trabajo["precio_max"]
                        ) / 2
                    )
                    self.txt_desc.delete(
                        "1.0",
                        "end"
                    )
                    self.txt_desc.insert(
                        "1.0",
                        trabajo["nombre"]
                    )
                    self.txt_precio.delete(
                        0,
                        "end"
                    )
                    self.txt_precio.insert(
                        0,
                        str(precio)
                    )
                    self.aprender_confirmacion(
                        trabajo,
                        [
                            texto_original,
                            nueva_descripcion
                        ]
                    )
        self.comprobar_campos_item()
        return False

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
                        precio = (
                            sugerencia["precio_min"] +
                            sugerencia["precio_max"]
                        ) / 2

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


            desc_resumida = (
                descripcion.replace("\n", " ")[:50] + "..."
                if len(descripcion) > 50
                else descripcion
            )


            self.tree.insert(
                "",
                "end",
                values=(
                    desc_resumida,
                    f"{precio:.2f}",
                    cantidad,
                    f"{total:.2f}"
                )
            )


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

        texto = self.txt_desc.get(
            "1.0",
            "end-1c"
        ).strip()


        if not texto:
            messagebox.showwarning(
                "Aviso",
                "Escribe primero el trabajo a analizar."
            )
            return


        resultado = self.buscar_precio_baremo(texto)


        if resultado:

            self.mostrar_sugerencia_precio(
                resultado
            )


        else:

            messagebox.showinfo(
                "Sin resultado",
                "No encuentro este trabajo todavía."
            )

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
        ventana.geometry("600x650")
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
        seleccionados = self.tree.selection()
        for item in seleccionados:
            indice = self.tree.index(item)
            self.items_presupuesto.pop(indice)
            self.tree.delete(item)
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

        for item in self.tree.get_children():
            self.tree.delete(item)

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
