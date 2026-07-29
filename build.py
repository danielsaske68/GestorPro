"""
BUILD.PY
========
Compila launcher.py a .exe (carpeta dist/GestorPro/) y coloca junto a él
todo lo que debe quedar EDITABLE sin recompilar: main.py, modules/, cloud/,
assets/, data/, Homeserve/, datos_lector/, liquidaciones_pdf/, version.json.

USO:
    python build.py

Se puede ejecutar las veces que quieras. Los archivos de DATOS
(usuarios.db, clientes.json, baremos_v2.json, progreso.json, etc.)
NO se sobrescriben si ya existen en dist/GestorPro, para no perder
información entre compilaciones. El código (main.py, modules/, cloud/)
SÍ se sobrescribe siempre con la versión más reciente de esta carpeta,
porque normalmente ya lo estarás editando ahí directamente y no hace
falta volver a compilar para verlo (ver README.md).
"""

import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "GestorPro"
DIST_DIR = os.path.join(BASE_DIR, "dist", APP_NAME)

# Paquetes de terceros usados en TODO el proyecto (main.py + modules + cloud).
# Como el launcher carga main.py de forma dinámica (runpy), PyInstaller NO
# los detecta solo -> hay que decírselo explícitamente.
HIDDEN_IMPORTS = [
    "customtkinter",
    "PIL",
    "PIL._tkinter_finder",
    "tkcalendar",
    "requests",
    "cv2",
    "numpy",
    "pyautogui",
    "pygetwindow",
    "keyboard",
    "bs4",
    "flask",
    "dotenv",
    "reportlab",
    "reportlab.graphics.barcode",
    "sqlite3",
]

# Paquetes con archivos internos (temas, iconos, imágenes) que necesitan
# empaquetarse completos, no solo el código .py.
COLLECT_ALL = [
    "customtkinter",
    "tkcalendar",
]

# Carpetas/archivos que deben quedar SUELTOS (editables) junto al .exe.
CARPETAS_A_COPIAR = [
    "main.py",
    "modules",
    "cloud",
    "assets",
    "data",
    "Homeserve",
    "datos_lector",
    "liquidaciones_pdf",
    "version.json",
]

# Dentro de esas carpetas, lo que NUNCA se debe sobrescribir si ya existe
# en el destino (para no perder datos entre compilaciones).
NO_SOBRESCRIBIR_SI_EXISTE = {
    os.path.join("data", "usuarios.db"),
    os.path.join("data", "clientes.json"),
    os.path.join("data", "baremos_v2.json"),
    os.path.join("Homeserve", "progreso.json"),
    os.path.join("Homeserve", "servicios.txt"),
    os.path.join("Homeserve", "servicios_ok.txt"),
    os.path.join("Homeserve", "ausente_1.json"),
    os.path.join("Homeserve", "mauricio.json"),
}


def compilar():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", APP_NAME,
        "launcher.py",
    ]
    for hi in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", hi]
    for pkg in COLLECT_ALL:
        cmd += ["--collect-all", pkg]

    print("Ejecutando PyInstaller...")
    subprocess.run(cmd, cwd=BASE_DIR, check=True)


def copiar_archivo(origen, destino):
    rel = os.path.relpath(destino, DIST_DIR)
    if rel in NO_SOBRESCRIBIR_SI_EXISTE and os.path.exists(destino):
        return  # ya existe -> no lo tocamos, puede tener datos reales
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.copy2(origen, destino)


def copiar_arbol(origen, destino):
    for root, dirs, files in os.walk(origen):
        # no copiar cachés de python
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(src, origen)
            dst = os.path.join(destino, rel)
            copiar_archivo(src, dst)


def copiar_editables():
    print("Copiando archivos editables junto al .exe...")
    for nombre in CARPETAS_A_COPIAR:
        origen = os.path.join(BASE_DIR, nombre)
        if not os.path.exists(origen):
            continue
        destino = os.path.join(DIST_DIR, nombre)
        if os.path.isdir(origen):
            copiar_arbol(origen, destino)
        else:
            copiar_archivo(origen, destino)


if __name__ == "__main__":
    compilar()
    copiar_editables()
    print()
    print(f"Listo. Tu programa está en: {DIST_DIR}")
    print(f"  -> {APP_NAME}.exe  (compilado, casi nunca hace falta tocarlo)")
    print("  -> main.py, modules/, cloud/, assets/, data/... (editables, sin recompilar)")
