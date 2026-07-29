import sys
import os
import runpy

# Determinar la carpeta base donde está el .exe o el launcher.py
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Asegurar que la carpeta base esté en el PATH de Python para imports de módulos
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Cambiar el directorio de trabajo a la carpeta del .exe para que las rutas relativas ("assets/...", "data/...") funcionen
os.chdir(BASE_DIR)

MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")

if __name__ == "__main__":
    if os.path.exists(MAIN_SCRIPT):
        try:
            # Ejecuta main.py en el mismo proceso de Python con todas las librerías cargadas
            runpy.run_path(MAIN_SCRIPT, run_name="__main__")
        except Exception as e:
            import traceback
            print("ERROR AL EJECUTAR MAIN.PY:")
            traceback.print_exc()
            input("Presiona ENTER para salir...")
    else:
        print(f"Error: No se encuentra {MAIN_SCRIPT}")
        input("Presiona ENTER para salir...")