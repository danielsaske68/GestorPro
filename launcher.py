import sys
import os
import subprocess

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ruta al main.py real que descargará GitHub
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")

if __name__ == "__main__":
    # Arranca el main.py usando el intérprete de python disponible
    if os.path.exists(MAIN_SCRIPT):
        subprocess.run([sys.executable, MAIN_SCRIPT])
    else:
        print("No se encuentra el archivo main.py en la carpeta.")