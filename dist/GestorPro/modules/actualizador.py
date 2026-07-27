import customtkinter as ctk
import threading
import requests
import zipfile
import os
import sys
import json
import shutil
import subprocess

class ActualizadorFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        titulo = ctk.CTkLabel(
            self,
            text="Actualizador de Gestor PRO",
            font=("Arial", 28, "bold")
        )
        titulo.pack(pady=(30, 15))

        self.estado = ctk.CTkLabel(
            self,
            text="Pulsa el botón para comprobar si existen actualizaciones.",
            font=("Arial", 15)
        )
        self.estado.pack(pady=10)

        self.barra = ctk.CTkProgressBar(self, width=500)
        self.barra.pack(pady=20)
        self.barra.set(0)

        self.boton = ctk.CTkButton(
            self,
            text="Buscar actualizaciones",
            command=self.buscar_actualizaciones,
            height=40,
            width=250
        )
        self.boton.pack(pady=20)

        self.log = ctk.CTkTextbox(self, width=700, height=300)
        self.log.pack(padx=20, pady=20, fill="both", expand=True)

    def escribir(self, texto):
        self.log.insert("end", texto + "\n")
        self.log.see("end")

    def buscar_actualizaciones(self):
        self.boton.configure(state="disabled")
        self.log.delete("0.0", "end")
        threading.Thread(
            target=self.proceso_actualizacion,
            daemon=True
        ).start()

    def proceso_actualizacion(self):
        try:
            GITHUB_USER = "danielsaske68"
            GITHUB_REPO = "GestorPro"
            URL_VERSION_REMOTE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.json"
            URL_ZIP_REPO = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/main.zip"

            self.estado.configure(text="Conectando con GitHub...")
            self.barra.set(0.05)
            self.escribir("✔ Conectando con GitHub...")

            # Directorio base (funciona tanto en script como en .exe)
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                is_exe = True
            else:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                is_exe = False

            version_path = os.path.join(base_dir, "version.json")
            
            local_version = "1.0.0"
            if os.path.exists(version_path):
                with open(version_path, "r", encoding="utf-8") as f:
                    local_version = json.load(f).get("version", "1.0.0")

            self.escribir(f"📍 Versión local actual: {local_version}")
            
            # Consultar versión remota en GitHub
            response = requests.get(URL_VERSION_REMOTE, timeout=10)
            if response.status_code != 200:
                raise Exception(f"No se pudo conectar (Código HTTP {response.status_code})")
            
            remote_data = response.json()
            remote_version = remote_data.get("version", "1.0.0")
            self.escribir(f"📍 Versión en el servidor: {remote_version}")

            if local_version == remote_version:
                self.barra.set(1.0)
                self.estado.configure(text="Gestor PRO está actualizado.")
                self.escribir("✔ No hay actualizaciones pendientes.")
                self.boton.configure(state="normal")
                return

            # Descarga con cálculo de porcentaje en tiempo real
            self.estado.configure(text="Descargando actualización...")
            self.escribir("⬇ Iniciando descarga del paquete...")

            zip_path = os.path.join(base_dir, "update.zip")
            response_zip = requests.get(URL_ZIP_REPO, stream=True, timeout=30)
            
            total_size = int(response_zip.headers.get('content-length', 0))
            downloaded_size = 0

            with open(zip_path, "wb") as f:
                for chunk in response_zip.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            percent = downloaded_size / total_size
                            barra_val = 0.10 + (percent * 0.50)
                            self.barra.set(barra_val)
                            
                            percent_int = int(percent * 100)
                            if percent_int % 20 == 0: 
                                self.estado.configure(text=f"Descargando... {percent_int}%")

            self.escribir("✔ Descarga completada al 100%.")
            self.barra.set(0.65)

            self.estado.configure(text="Instalando archivos...")
            self.escribir("📦 Reemplazando archivos y carpetas...")

            extract_dir = os.path.join(base_dir, "temp_update")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            os.makedirs(extract_dir)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            extracted_folders = os.listdir(extract_dir)
            source_folder = os.path.join(extract_dir, extracted_folders[0])

            # Archivos protegidos que no deben sobrescribirse para no perder datos del usuario
            archivos_protegidos = {
                os.path.normpath(os.path.join("data", "usuarios.db")),
                os.path.normpath(os.path.join("data", "clientes.json")),
                os.path.normpath(os.path.join("data", "baremos_v2.json")),
                os.path.normpath(os.path.join("Homeserve", "progreso.json")),
                os.path.normpath(os.path.join("Homeserve", "servicios.txt")),
                os.path.normpath(os.path.join("Homeserve", "servicios_ok.txt")),
                os.path.normpath(os.path.join("Homeserve", "ausente_1.json")),
                os.path.normpath(os.path.join("Homeserve", "mauricio.json")),
            }

            # Recorremos todo el repositorio descargado para actualizar carpetas y archivos
            for root, dirs, files in os.walk(source_folder):
                rel_root = os.path.relpath(root, source_folder)
                
                # Ignorar carpetas ocultas o de control de versiones si las hubiera
                if any(part.startswith('.') for part in rel_root.split(os.sep)):
                    continue

                dest_root = base_dir if rel_root == "." else os.path.join(base_dir, rel_root)
                os.makedirs(dest_root, exist_ok=True)

                for file in files:
                    if file.startswith('.'):
                        continue

                    src_file = os.path.join(root, file)
                    rel_file_path = file if rel_root == "." else os.path.normpath(os.path.join(rel_root, file))
                    dst_file = os.path.join(base_dir, rel_file_path)

                    # Verificar si es un archivo protegido de datos del usuario y ya existe
                    if rel_file_path in archivos_protegidos and os.path.exists(dst_file):
                        self.escribir(f"  -> Omitido (protegido): {rel_file_path}")
                        continue

                    try:
                        # Si es un ejecutable nuevo y estamos corriendo como .exe
                        if is_exe and file.endswith(".exe"):
                            nuevo_exe_path = os.path.join(base_dir, "nuevo_" + file)
                            shutil.copy2(src_file, nuevo_exe_path)
                            self.escribir(f"  -> Preparado nuevo ejecutable: {file}")
                        else:
                            shutil.copy2(src_file, dst_file)
                            self.escribir(f"  -> Actualizado: {rel_file_path}")
                    except PermissionError:
                        self.escribir(f"  -> Omitido (en uso por Windows): {rel_file_path}")
                    except Exception as sub_err:
                        self.escribir(f"  -> No se pudo actualizar {rel_file_path}: {sub_err}")

            # Limpiar zip temporal
            if os.path.exists(zip_path):
                os.remove(zip_path)

            self.barra.set(1.0)
            self.estado.configure(text="¡Actualización completada con éxito!")
            self.escribir("🎉 Archivos actualizados correctamente.")

            # Si estamos corriendo como .exe y hay un ejecutable nuevo pendiente de aplicar
            if is_exe:
                exe_actual_nombre = os.path.basename(sys.executable)
                nuevo_exe_encontrado = os.path.join(base_dir, "nuevo_" + exe_actual_nombre)

                if os.path.exists(nuevo_exe_encontrado):
                    self.escribir("🔄 Actualizando archivo ejecutable principal (.exe)...")
                    
                    bat_path = os.path.join(base_dir, "actualizar.bat")
                    with open(bat_path, "w", encoding="utf-8") as bat_file:
                        bat_file.write(f"""@echo off
timeout /t 2 /nobreak > nul
del /f /q "{sys.executable}"
move /y "{nuevo_exe_encontrado}" "{sys.executable}"
start "" "{sys.executable}"
del "%~f0"
""")
                    
                    self.escribir("🚀 Reiniciando aplicación para aplicar los cambios...")
                    subprocess.Popen(bat_path, shell=True)
                    os._exit(0)

            # Limpieza general de archivos temporales
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)

            self.boton.configure(state="normal")
            
        except Exception as e:
            self.estado.configure(text="Error en la actualización.")
            self.escribir(f"❌ Error crítico: {str(e)}")
            self.boton.configure(state="normal")