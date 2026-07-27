import time
import os
import json
import subprocess
import cv2
import numpy as np
import pyautogui
import pygetwindow as gw
import keyboard


# =========================================================
# CONFIGURACIÓN
# =========================================================
USUARIO = "16205"
CONTRASENA = "Aventura69."

UMBRAL_GENERAL = 0.45

BASE_HOME = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Homeserve"
)

ADB = os.path.join(
    BASE_HOME,
    "adb.exe"
)

ARCHIVO_SERVICIOS = os.path.join(
    BASE_HOME,
    "servicios.txt"
)

ARCHIVO_OK = os.path.join(
    BASE_HOME,
    "servicios_ok.txt"
)

ARCHIVO_PROGRESO = os.path.join(
    BASE_HOME,
    "progreso.json"
)

pyautogui.PAUSE = 0.005

# =========================================================
# CONTROL DEL BOT
# =========================================================

BOT_PAUSADO = False
BOT_DETENIDO = False
BOT_EN_EJECUCION = False

BOT_ESTADO = "INICIO"
SERVICIO_ACTUAL = None
PASO_ACTUAL = None


def iniciar_teclas_control():

    def pausa():
        global BOT_PAUSADO
        BOT_PAUSADO = True
        print("[TECLA] BOT PAUSADO")

    def continuar():

        global BOT_PAUSADO
        BOT_PAUSADO = False
        print("[TECLA] BOT CONTINUANDO")


    def detener():
        global BOT_DETENIDO
        BOT_DETENIDO = True
        print("[TECLA] BOT DETENIDO")


    keyboard.add_hotkey(
        "f8",
        pausa
    )

    keyboard.add_hotkey(
        "f9",
        continuar
    )

    keyboard.add_hotkey(
        "f10",
        detener
    )

# =========================================================
# RUTAS HOMESERVE
# =========================================================

def ruta_archivo(nombre):
    return os.path.join(
        BASE_HOME,
        nombre
    )

# =========================================================
# FUNCIONES BÁSICAS
# =========================================================

def guardar_progreso(servicio, estado):

    datos = {
        "servicio": servicio,
        "estado": estado,
        "hora": time.strftime("%d/%m/%Y %H:%M:%S")
    }

    with open(
        ARCHIVO_PROGRESO,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            datos,
            f,
            indent=4
        )

def cambiar_estado(servicio, estado):

    global BOT_ESTADO
    global SERVICIO_ACTUAL
    global PASO_ACTUAL

    BOT_ESTADO = estado
    SERVICIO_ACTUAL = servicio
    PASO_ACTUAL = estado

    guardar_progreso(
        servicio,
        estado
    )

    print(f"[ESTADO] {estado}")

def controlar_bot():

    global BOT_PAUSADO
    global BOT_DETENIDO

    while BOT_PAUSADO:

        if BOT_DETENIDO:
            print("[STOP] Bot detenido durante pausa")
            raise Exception(
                "Bot detenido manualmente"
            )

        print("[PAUSA] Bot esperando F9...")
        time.sleep(0.5)

    if BOT_DETENIDO:

        print("[STOP] Bot detenido")
        raise Exception(
            "Bot detenido manualmente"
        )

def esperar_segundos(segundos):

    for _ in range(segundos * 2):

        controlar_bot()

        time.sleep(0.5)

def punto_seguridad():
    controlar_bot()

def enfocar_scrcpy():
    try:
        ventanas = (
            gw.getWindowsWithTitle('scrcpy')
            or gw.getWindowsWithTitle('POCO')
            or gw.getWindowsWithTitle('M2007J20CG')
        )
        if ventanas:
            ventanas[0].restore()
            ventanas[0].activate()
            time.sleep(0.5)
            return True
    except:
        pass
    return False
# ---------------------------------------------------------
def click_humano(x, y, duracion=0.50):
    controlar_bot()
    pyautogui.moveTo(
        x,
        y,
        duration=duracion
    )
    controlar_bot()
    pyautogui.click()
    controlar_bot()
# ---------------------------------------------------------
def adb_texto(texto):

    controlar_bot()

    subprocess.run(
        f'"{ADB}" shell input text "{texto}"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    controlar_bot()
# ---------------------------------------------------------
def adb_back():
    controlar_bot()
    subprocess.run(
        f'"{ADB}" shell input keyevent 4',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
# ---------------------------------------------------------
def adb_enter():
    controlar_bot()
    subprocess.run(
        f'"{ADB}" shell input keyevent 66',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
# ---------------------------------------------------------
def adb_tab():
    controlar_bot()
    subprocess.run(
        f'"{ADB}" shell input keyevent 61',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
# ---------------------------------------------------------
def obtener_coordenadas_visuales(
    ruta_imagen,
    umbral=UMBRAL_GENERAL
):
    if not os.path.exists(ruta_imagen):
        print(f"[-] Imagen no encontrada: {ruta_imagen}")
        return None
    pantalla = cv2.cvtColor(
        np.array(pyautogui.screenshot()),
        cv2.COLOR_RGB2BGR
    )
    plantilla = cv2.imread(ruta_imagen)
    resultado = cv2.matchTemplate(
        pantalla,
        plantilla,
        cv2.TM_CCOEFF_NORMED
    )
    _, max_val, _, max_loc = cv2.minMaxLoc(resultado)
    print(f"[*] Buscando {ruta_imagen} | Confianza: {round(max_val, 2)}")
    if max_val >= umbral:
        x = max_loc[0] + plantilla.shape[1] // 2
        y = max_loc[1] + plantilla.shape[0] // 2
        return (x, y)
    return None
# ---------------------------------------------------------

def buscar_y_click(
    imagen,
    umbral=UMBRAL_GENERAL,
    espera=1
):

    pos = obtener_coordenadas_visuales(
        imagen,
        umbral
    )

    if pos:

        click_humano(
            pos[0],
            pos[1]
        )

        time.sleep(espera)

        return True

    return False

# ---------------------------------------------------------

def esperar_imagen(
    imagen,
    timeout=15,
    umbral=UMBRAL_GENERAL
):

    inicio = time.time()

    while time.time() - inicio < timeout:

        controlar_bot()

        #resultado_vigilante = vigilante_pantalla()

        #if resultado_vigilante == "ERROR":

        #    print("[VIGILANTE] Reiniciando búsqueda")

        #   return "REBUSCAR"


        pos = obtener_coordenadas_visuales(
            imagen,
            umbral
        )


        if pos:
            return pos


        time.sleep(0.5)

    return None

# =========================================================
# VIGILANTE DE PANTALLA
# =========================================================

def comprobar_popup():

    for img in [
        ruta_archivo('boton_aceptar_real.png'),
        ruta_archivo('btn_aceptar_aviso.png')
    ]:

        if buscar_y_click(
            img,
            umbral=0.42,
            espera=1
        ):

            print("[VIGILANTE] Popup aceptado")
            return True

    return False

# =========================================================
# VIGILANTE GENERAL DE PANTALLA
# =========================================================

def vigilante_pantalla():

    controlar_bot()

    # POPUP
    if comprobar_popup():
        return True


    # ERROR (cuando creemos la imagen)
    pos_error = obtener_coordenadas_visuales(
        ruta_archivo("error.png"),
        0.45
    )

    if pos_error:

        print("[VIGILANTE] Error detectado")

        return "ERROR"


    return False

# =========================================================
# SISTEMA DE FIRMAS JSON
# =========================================================

def ejecutar_firma_json(tipo, ref_x, ref_y):

    archivo = (
        ruta_archivo('mauricio.json')
        if tipo == "profesional"
        else ruta_archivo('ausente_1.json')
    )

    with open(archivo, 'r') as f:

        trazos = json.load(f)

    offset_x = ref_x - trazos[0]['pos'][0]
    offset_y = ref_y - trazos[0]['pos'][1]

    if tipo == "profesional":

        offset_y += 20

    else:

        offset_x += 20

    for evento in trazos:
        controlar_bot()
        x = evento['pos'][0] + offset_x
        y = evento['pos'][1] + offset_y

        pyautogui.moveTo(x, y)

        if evento['action'] == 'down':

            pyautogui.mouseDown()

        elif evento['action'] == 'up':

            pyautogui.mouseUp()

    pyautogui.mouseUp()

    print(f"[+] Firma {tipo} ejecutada.")

# =========================================================
# BUSCAR BOTÓN EN ZONA
# =========================================================

def hacer_clic_boton(
    img_nombre,
    y_min,
    y_max
):

    pantalla = cv2.cvtColor(
        np.array(pyautogui.screenshot()),
        cv2.COLOR_RGB2BGR
    )

    zona = pantalla[
        y_min:y_max,
        0:pantalla.shape[1]
    ]

    plantilla = cv2.imread(img_nombre)

    if plantilla is None:

        return None

    resultado = cv2.matchTemplate(
        zona,
        plantilla,
        cv2.TM_CCOEFF_NORMED
    )

    _, max_val, _, max_loc = cv2.minMaxLoc(resultado)

    print(f"[*] Buscando {img_nombre} zona {y_min}-{y_max} | {round(max_val, 2)}")

    if max_val >= 0.40:

        x = max_loc[0] + plantilla.shape[1] // 2
        y = max_loc[1] + plantilla.shape[0] // 2 + y_min

        click_humano(x, y)

        return (x, y)

    return None

# =========================================================
# SISTEMA DE LISTA DE SERVICIOS
# =========================================================
def cargar_servicios():

    if not os.path.exists(ARCHIVO_SERVICIOS):

        print("[-] No existe servicios.txt")
        return []

    with open(ARCHIVO_SERVICIOS, "r") as f:

        return [
            linea.strip()
            for linea in f
            if linea.strip()
        ]

# ---------------------------------------------------------

def marcar_ok(servicio):

    with open(ARCHIVO_OK, "a") as f:

        f.write(servicio + "\n")

# =========================================================
# PROCESAR SERVICIO
# =========================================================

def procesar_servicio(NUM_SERVICIO):

    # =========================================================
    # BUSCAR SERVICIO
    # =========================================================

    print("\n==================================================")
    print("BUSCAR SERVICIO")
    print("==================================================")
    
    cambiar_estado(
        NUM_SERVICIO,
        "BUSCANDO_SERVICIO"
    )

    pos_barra = esperar_imagen(
        ruta_archivo('barra_buscar.png'),
        timeout=10
    )


    if pos_barra == "REBUSCAR":

        print("[+] Volviendo a buscar servicio")

        return procesar_servicio(NUM_SERVICIO)

    if pos_barra:
        click_humano(
            pos_barra[0],
            pos_barra[1]
        )
        time.sleep(0.5)

        print(f"[*] Introduciendo servicio: {NUM_SERVICIO}")
        adb_texto(NUM_SERVICIO)
        time.sleep(0.5)
        adb_back()
        time.sleep(0.5)

        if buscar_y_click(ruta_archivo('boton_lupa.png')):
            print("[+] Servicio buscado con lupa.")

        else:

            adb_enter()

            print("[+] Servicio buscado con ENTER.")

        print("[*] Esperando carga...")

        esperar_segundos(5)

    # =========================================================
    # CREAR ALBARÁN
    # =========================================================

    print("\n==================================================")
    print("CREAR ALBARÁN")
    print("==================================================")

    cambiar_estado(
        NUM_SERVICIO,
        "CREANDO_ALBARAN"
    )

    pos_albaran = esperar_imagen(
        ruta_archivo('boton_albaran.png'),
        timeout=15,
        umbral=0.40
    )

    if pos_albaran:

        click_humano(
            pos_albaran[0],
            pos_albaran[1]
        )

        print("[+] Click en Crear Albarán.")

        time.sleep(2)

    # =========================================================
    # POPUP
    # =========================================================

    print("\n==================================================")
    print("POPUP")
    print("==================================================")

    for img in [
        ruta_archivo('boton_aceptar_real.png'),
        ruta_archivo('btn_aceptar_aviso.png')
    ]:

        if buscar_y_click(
            img,
            umbral=0.42,
            espera=1
        ):

            print("[+] Popup aceptado.")

            break

    # =========================================================
    # ESPERA CARGA FIRMAS
    # =========================================================

    print("\n==================================================")
    print("CARGANDO FIRMAS")
    print("==================================================")

    esperar_segundos(10)

    # =========================================================
    # FIRMA PROFESIONAL
    # =========================================================

    print("\n==================================================")
    print("FIRMA PROFESIONAL")
    print("==================================================")

    cambiar_estado(
        NUM_SERVICIO,
        "FIRMA_PROFESIONAL"
    )

    pos = hacer_clic_boton(
        ruta_archivo("boton_firmar_general.png"),
        0,
        540
    )

    if pos:

        time.sleep(2)

        ejecutar_firma_json(
            "profesional",
            pos[0],
            pos[1]
        )

        time.sleep(1)

        hacer_clic_boton(
            ruta_archivo('boton_aceptar_firma.png'),
            0,
            1080
        )

        print("[+] Firma profesional completada.")

        time.sleep(4)

    # =========================================================
    # FIRMA CLIENTE
    # =========================================================

    print("\n==================================================")
    print("FIRMA CLIENTE")
    print("==================================================")

    cambiar_estado(
        NUM_SERVICIO,
        "FIRMA_CLIENTE"
    )

    pos = hacer_clic_boton(
        ruta_archivo("boton_firmar_general.png"),
        540,
        1080
    )

    if pos:

        time.sleep(2)

        ejecutar_firma_json(
            "cliente",
            pos[0],
            pos[1]
        )

        time.sleep(1)

        hacer_clic_boton(
            ruta_archivo('boton_aceptar_firma.png'),
            0,
            1080
        )

        print("[+] Firma cliente completada.")

        esperar_segundos(5)

    # =========================================================
    # IMPRIMIR / ENVIAR
    # =========================================================

    print("\n==================================================")
    print("IMPRIMIR / ENVIAR")
    print("==================================================")

    cambiar_estado(
        NUM_SERVICIO,
        "ENVIANDO"
    )

    pos_env = esperar_imagen(
        ruta_archivo('boton_imprimir_enviar.png'),
        timeout=20
    )

    if pos_env:

        click_humano(
            pos_env[0],
            pos_env[1]
        )

        print("[+] Documento enviado.")

        # =====================================================
        # POPUP FINAL
        # =====================================================

        print("\n==================================================")
        print("POPUP FINAL")
        print("==================================================")

        print("[*] Esperando popup final (8 segundos)...")

        esperar_segundos(12)

        # =====================================================
        # IR A DETALLES DEL SERVICIO
        # =====================================================

        print("[*] Buscando botón 'Ir a detalles del servicio'...")

        if buscar_y_click(
            ruta_archivo('ir_detalles_servicio.png'),
            umbral=0.40,
            espera=5
        ):

            print("[+] Ir a detalles del servicio pulsado.")

        else:

            print("[-] No se encontró ir_detalles_servicio.png")

        # =====================================================
        # ESPERA CARGA DETALLES
        # =====================================================

        print("[*] Esperando carga pantalla detalles...")

        time.sleep(6)

        # =====================================================
        # BOTÓN ATRÁS
        # =====================================================

        print("[*] Buscando botón atrás...")

        pos_atras = esperar_imagen(
            ruta_archivo('boton_atras.png'),
            timeout=10,
            umbral=0.35
        )

        if pos_atras:

            click_humano(
                pos_atras[0],
                pos_atras[1]
            )

            print("[+] Botón atrás pulsado.")

        else:

            print("[-] No se encontró boton_atras.png")

    else:

        print("[-] No se encontró botón imprimir/enviar.")

# =========================================================
# INICIO SCRCPY
# =========================================================
def iniciar_homeserve():

    iniciar_teclas_control()

    print("==================================================")
    print("      AUTOMATIZACIÓN HOMESERVE")
    print("==================================================")
    BASE = os.path.dirname(
        os.path.abspath(__file__)
    )
    SCRCPY = os.path.join(
        BASE_HOME,
        "scrcpy.exe"
    )
    print("[*] Comprobando scrcpy...")
    ventana = enfocar_scrcpy()
    if not ventana:
        print("[*] scrcpy no encontrado, abriendo...")
        subprocess.Popen(
            [
                SCRCPY,
                "--max-fps=60",
                "--video-bit-rate=4M"
            ],
            shell=True
        )
        esperar_segundos(5)
        if enfocar_scrcpy():
            print("[+] scrcpy abierto correctamente")
        else:
            print("[-] No se pudo abrir/enfocar scrcpy")
    else:
        print("[+] scrcpy ya estaba abierto")

    if enfocar_scrcpy():
        print("[+] scrcpy encontrado")
    else:
        print("[-] No se pudo enfocar scrcpy")
    servicios = cargar_servicios()
    print(
        f"[+] Servicios cargados: {len(servicios)}"
    )
    for servicio in servicios:

        print("\n==================================================")
        print(f"PROCESANDO SERVICIO: {servicio}")
        print("==================================================")
        
        try:

            cambiar_estado(
                servicio,
                "INICIANDO"
            )

            procesar_servicio(servicio)

            marcar_ok(servicio)

            cambiar_estado(
                servicio,
                "FINALIZADO"
            )

            print(
                f"[✓] Servicio {servicio} completado"
            )


        except Exception as e:

            print(
                f"[x] Error en servicio {servicio}"
            )

            print(e)


        time.sleep(3)



    print("\n==================================================")
    print("TODOS LOS SERVICIOS FINALIZADOS")
    print("==================================================")


    print("Proceso terminado")