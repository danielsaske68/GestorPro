# Gestor Pro — cómo compilar y editar sin recompilar

## Qué cambió

Antes, PyInstaller metía `main.py` y todos los `modules/` dentro del `.exe`
compilado. Cada cambio de código = recompilar.

Ahora hay un archivo nuevo, **`launcher.py`**, que es el único que se
compila. Su única función es leer `main.py` desde el disco cada vez que
abres el programa (usando `runpy`), en vez de llevarlo empaquetado.

Resultado: `main.py`, `modules/`, `cloud/`, `assets/`, `data/`, `Homeserve/`,
etc. quedan como archivos sueltos junto al `.exe`. Los puedes editar
directamente ahí (con VSCode, Notepad++, lo que uses) y el cambio se
aplica la próxima vez que abras el `.exe` — **sin recompilar**.

## Bugs de rutas que corregí de paso

Encontré 3 sitios que usaban rutas relativas al "directorio de trabajo"
en lugar de a la carpeta del programa. Eso es justo lo que puede hacer
que, al compilar o al abrir el `.exe` desde un acceso directo, la base de
datos o carpetas de datos "cambien de sitio" o se creen vacías en otro
lugar:

- `modules/Lector_de_codigos.py`: `datos_lector/` y `assets/logo.png`
- `modules/presupuestos.py`: `data/clientes.json`
- `modules/liquidaciones.py`: `liquidaciones_pdf/`

Ahora los tres calculan su ruta a partir de la carpeta real del programa
(`BASE_DIR`), igual que ya hacía `main.py`, `homeserve.py` y
`cloud/railway_app.py`. Con esto, la base de datos (`data/usuarios.db`) y
el resto de archivos siempre quedan en el mismo sitio, compilado o no.

## Cómo compilar (primera vez o si tocas `launcher.py`)

Necesitas PyInstaller instalado:

```
pip install pyinstaller
```

Y luego, desde esta carpeta:

```
python build.py
```

Esto hace dos cosas:
1. Compila `launcher.py` → `dist/GestorPro/GestorPro.exe`
2. Copia junto al `.exe` todo lo editable: `main.py`, `modules/`, `cloud/`,
   `assets/`, `data/`, `Homeserve/`, `datos_lector/`, `liquidaciones_pdf/`,
   `version.json`.

`dist/GestorPro/` es la carpeta que hay que distribuir/copiar tal cual a
otro PC (todo junto: el `.exe` y los archivos sueltos al lado).

## Cómo editar código DESPUÉS de compilar

Vas directamente a `dist/GestorPro/main.py` (o a cualquier archivo dentro
de `dist/GestorPro/modules/`), lo editas, guardas, y abres
`GestorPro.exe` otra vez. Ya está — no hace falta volver a ejecutar
`build.py` ni tocar PyInstaller para nada de esto.

Solo necesitas recompilar (`python build.py` de nuevo) si:
- Cambias `launcher.py` mismo (raro).
- Añades una librería nueva de Python que el `.exe` no tenga instalada
  dentro (hay que añadirla a `HIDDEN_IMPORTS` en `build.py` y recompilar
  una vez).

## Sobre los datos (base de datos, jsons, PDFs)

`build.py` copia `data/`, `Homeserve/`, etc. la primera vez, pero
**nunca sobrescribe** `usuarios.db`, `clientes.json`, `baremos_v2.json`,
`progreso.json` ni los `.txt`/`.json` de estado de Homeserve si ya
existen en `dist/GestorPro/`. Así que puedes recompilar tantas veces
como quieras sin miedo a perder datos ya guardados ahí.

## Botón "Actualizar"

Lo dejamos tal cual está por ahora, como comentaste — lo revisamos
después.
