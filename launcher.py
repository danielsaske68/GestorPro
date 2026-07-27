"""
LAUNCHER.PY
===========
Este es el ÚNICO archivo que se compila a .exe con PyInstaller.

Su trabajo es mínimo: averiguar en qué carpeta está el programa y
CARGAR main.py DESDE DISCO en tiempo real (con runpy), en vez de
llevarlo empaquetado dentro del .exe.

Gracias a esto:
- main.py, la carpeta modules/, cloud/, assets/, data/, Homeserve/, etc.
  quedan como archivos sueltos, editables, junto al .exe.
- Si cambias algo en main.py o en cualquier módulo, con volver a abrir
  el .exe ya se aplica el cambio. NO hay que recompilar.
- Solo tendrías que volver a compilar si cambias este launcher.py,
  o si añades una librería nueva que PyInstaller no haya empaquetado
  (ver build.bat -> lista de --hidden-import / --collect-all).

NO borres ni muevas main.py de al lado del .exe: sin él, el launcher
no tiene qué ejecutar.
"""

import sys
import os
import runpy

# --- Carpeta base: la carpeta donde está el .exe (o este script, si se
# ejecuta como .py sin compilar) ---
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Que Python pueda encontrar "modules", "cloud", etc. junto al .exe
sys.path.insert(0, BASE_DIR)

# Importante: fija el directorio de trabajo a la carpeta del programa.
# Así cualquier ruta relativa que quede suelta en el código también
# apunta siempre al sitio correcto.
os.chdir(BASE_DIR)

MAIN_PATH = os.path.join(BASE_DIR, "main.py")

if not os.path.exists(MAIN_PATH):
    # Si esto salta, es que main.py no está junto al .exe.
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Gestor Pro",
        f"No se encuentra main.py en:\n{BASE_DIR}\n\n"
        "Asegúrate de que main.py, la carpeta 'modules', 'cloud', "
        "'assets' y 'data' estén junto al .exe."
    )
    sys.exit(1)

# Ejecuta main.py como si fuese el script principal ("__main__"),
# leyéndolo directamente del disco cada vez.
runpy.run_path(MAIN_PATH, run_name="__main__")
