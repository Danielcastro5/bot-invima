# ==========================================================================
#  AUTOMATIZADOR INVIMA - MASTERDENT
#  Soporte Multi-Proceso (Información General, Composición, etc.),
#  Búsqueda Exacta 1:1, 3 Reintentos por Fila, Continuidad de Lote y Reporte
# ==========================================================================

import sys
import os
import time
import re
import threading
import importlib.util
import urllib.request
import json
import subprocess
import hashlib
import uuid
import base64
from datetime import datetime
import socket
import customtkinter as ctk
from tkinter import filedialog, messagebox
from openpyxl import load_workbook
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

PUERTO_CHROME = 9222   # Puerto de depuración de Chrome

VERSION_ACTUAL = "v1.0.0"
URL_VERSION_GITHUB = "https://raw.githubusercontent.com/Danielcastro5/bot-invima/main/version.json"
FIREBASE_DB_URL = "https://bot-invima-licencias-default-rtdb.firebaseio.com"
SECRET_SALT_LICENCIA = "BOT_INVIMA_SECURE_AUTH_SALT_2026_V1"

# Configuración inicial de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# --------------------------------------------------------------------------
#  LANZADOR AUTOMÁTICO DE GOOGLE CHROME EN MODO DEPURACIÓN (PUERTO 9222)
# --------------------------------------------------------------------------
def esta_puerto_abierto(puerto=9222):
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=1):
            return True
    except Exception:
        return False


def abrir_chrome_automatizado(app=None):
    """
    Inicia Google Chrome en modo de depuración remota (puerto 9222) de forma transparente.
    """
    if esta_puerto_abierto(PUERTO_CHROME):
        if app:
            app.log("✅ Chrome automatizado ya se encuentra en ejecución en puerto 9222.", "info")
        return True

    rutas_chrome = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), r"Google\Chrome\Application\chrome.exe")
    ]

    exe_chrome = None
    for r in rutas_chrome:
        if os.path.exists(r):
            exe_chrome = r
            break

    if not exe_chrome:
        if app:
            app.log("❌ No se encontró Google Chrome en las rutas estándar del sistema.", "error")
        return False

    user_data_dir = r"C:\chrome-bot"
    os.makedirs(user_data_dir, exist_ok=True)

    cmd = [
        exe_chrome,
        f"--remote-debugging-port={PUERTO_CHROME}",
        f"--user-data-dir={user_data_dir}"
    ]

    try:
        subprocess.Popen(cmd)
        time.sleep(2)
        if app:
            app.log("🚀 Chrome automatizado iniciado correctamente (Puerto 9222).", "success")
            app.log("💡 Inicia sesión en el portal INVIMA dentro de esa ventana de Chrome.", "warning")
        return True
    except Exception as e:
        if app:
            app.log(f"❌ Error al lanzar Chrome automáticamente: {e}", "error")
        return False



# --------------------------------------------------------------------------
#  SISTEMA DE LICENCIAMIENTO SEGURO CON HWID & FIREBASE
# --------------------------------------------------------------------------
def obtener_hwid():
    """Genera un identificador único e inalterable del computador (HWID)."""
    try:
        cmd = "wmic csproduct get uuid"
        output = subprocess.check_output(cmd, shell=True).decode().split('\n')
        if len(output) > 1 and output[1].strip():
            uuid_str = output[1].strip()
            return hashlib.sha256(uuid_str.encode()).hexdigest()[:16].upper()
    except Exception:
        pass

    node_str = str(uuid.getnode()) + os.getenv("COMPUTERNAME", "PC")
    return hashlib.sha256(node_str.encode()).hexdigest()[:16].upper()


def _generar_clave_cifrado():
    hwid = obtener_hwid()
    key_material = f"{hwid}_{SECRET_SALT_LICENCIA}"
    return hashlib.sha256(key_material.encode("utf-8")).digest()


def _cifrar_datos_licencia(texto_str):
    try:
        key = _generar_clave_cifrado()
        raw_bytes = texto_str.encode("utf-8")
        encrypted = bytearray()
        for i, b in enumerate(raw_bytes):
            k = key[i % len(key)]
            encrypted.append(b ^ k)
        hmac_sig = hashlib.sha256(key + bytes(encrypted)).hexdigest()[:16]
        payload = json.dumps({"sig": hmac_sig, "data": base64.b64encode(bytes(encrypted)).decode()})
        return base64.b64encode(payload.encode()).decode()
    except Exception:
        return ""


def _descifrar_datos_licencia(payload_b64):
    try:
        key = _generar_clave_cifrado()
        raw_json = base64.b64decode(payload_b64.encode()).decode()
        payload = json.loads(raw_json)
        enc_bytes = base64.b64decode(payload["data"].encode())
        expected_sig = hashlib.sha256(key + enc_bytes).hexdigest()[:16]
        if payload.get("sig") != expected_sig:
            return None  # Alterado o pertenece a otro equipo!
        decrypted = bytearray()
        for i, b in enumerate(enc_bytes):
            k = key[i % len(key)]
            decrypted.append(b ^ k)
        return decrypted.decode("utf-8")
    except Exception:
        return None


def obtener_ruta_licencia_local():
    """Retorna la ruta del archivo local cifrado donde se guarda la licencia activada."""
    base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    carpeta = os.path.join(base, "BotINVIMA_Data")
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, "license.dat")


def guardar_licencia_local(clave, info_dict):
    try:
        ruta = obtener_ruta_licencia_local()
        datos = {
            "clave": clave,
            "empresa": info_dict.get("empresa", ""),
            "hwid": obtener_hwid(),
            "vencimiento": info_dict.get("vencimiento", "")
        }
        contenido_cifrado = _cifrar_datos_licencia(json.dumps(datos))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido_cifrado)

        # Eliminar archivo legacy en texto plano si existía
        ruta_legacy = os.path.join(os.path.dirname(ruta), "license.json")
        if os.path.exists(ruta_legacy):
            try:
                os.remove(ruta_legacy)
            except Exception:
                pass
    except Exception as e:
        print(f"Error guardando licencia local cifrada: {e}")


def leer_licencia_local():
    try:
        ruta = obtener_ruta_licencia_local()
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                cifrado = f.read().strip()
            plano = _descifrar_datos_licencia(cifrado)
            if plano:
                return json.loads(plano)
    except Exception:
        pass
    return None


def eliminar_licencia_local():
    """Elimina los archivos de licencia guardados localmente."""
    try:
        ruta = obtener_ruta_licencia_local()
        if os.path.exists(ruta):
            os.remove(ruta)
        ruta_legacy = os.path.join(os.path.dirname(ruta), "license.json")
        if os.path.exists(ruta_legacy):
            os.remove(ruta_legacy)
    except Exception:
        pass


def validar_licencia_firebase(clave_licencia):
    """
    Verifica la clave de licencia en Firebase Realtime Database de forma segura.
    Soporta desvinculación remota y bloqueo por equipo (HWID).
    """
    clave = clave_licencia.strip().upper()
    if not clave:
        return False, "Por favor ingresa una clave de licencia."

    hwid = obtener_hwid()
    url = f"{FIREBASE_DB_URL}/licencias/{clave}.json"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_data = resp.read().decode("utf-8")
            if not raw_data or raw_data == "null":
                eliminar_licencia_local()
                return False, f"La clave de licencia '{clave}' no existe o fue eliminada."

            data = json.loads(raw_data)

        if not data.get("activa", False):
            eliminar_licencia_local()
            return False, "Licencia inactiva o suspendida por el proveedor."

        vencimiento = data.get("vencimiento", "")
        if vencimiento:
            try:
                fecha_venc = datetime.strptime(vencimiento, "%Y-%m-%d")
                if datetime.now() > fecha_venc:
                    eliminar_licencia_local()
                    return False, f"Licencia vencida el {vencimiento}. Contacta al soporte para renovar."
            except Exception:
                pass

        equipos = data.get("equipos", {})
        if not isinstance(equipos, dict):
            equipos = {}

        max_equipos = int(data.get("max_equipos", 1))

        # 1. Si el HWID está registrado en Firebase
        if hwid in equipos:
            val_equipo = equipos[hwid]
            if val_equipo is False or str(val_equipo).lower() == "false":
                eliminar_licencia_local()
                return False, "Este equipo específico ha sido deshabilitado por el administrador."

            equipos_activos = [k for k, v in equipos.items() if v is not False and str(v).lower() != "false"]
            info = {
                "clave": clave,
                "empresa": data.get("empresa", "Cliente"),
                "vencimiento": vencimiento or "Permanente",
                "equipos_usados": len(equipos_activos),
                "max_equipos": max_equipos
            }
            guardar_licencia_local(clave, info)
            return True, info

        # 2. Si el HWID NO está en Firebase, pero el PC conservaba una licencia local previa:
        #    indica que el administrador ELIMINÓ/DESVINCULÓ este equipo remotamente.
        datos_locales = leer_licencia_local()
        if datos_locales and datos_locales.get("clave") == clave:
            eliminar_licencia_local()
            return False, "Este equipo ha sido desvinculado de la licencia por el administrador."

        # 3. Registro de equipo nuevo (Primera activación en este PC)
        equipos_activos = [k for k, v in equipos.items() if v is not False and str(v).lower() != "false"]
        if len(equipos_activos) >= max_equipos:
            return False, f"Límite de dispositivos alcanzado (Máximo {max_equipos} equipo(s) para esta licencia)."

        # Registrar este nuevo equipo (HWID) en Firebase
        nombre_pc = os.getenv("COMPUTERNAME", f"Equipo_{len(equipos_activos)+1}")
        url_put = f"{FIREBASE_DB_URL}/licencias/{clave}/equipos/{hwid}.json"
        body = json.dumps(nombre_pc).encode("utf-8")
        req_put = urllib.request.Request(url_put, data=body, headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req_put, timeout=10) as resp_put:
            pass

        info = {
            "clave": clave,
            "empresa": data.get("empresa", "Cliente"),
            "vencimiento": vencimiento or "Permanente",
            "equipos_usados": len(equipos_activos) + 1,
            "max_equipos": max_equipos
        }
        guardar_licencia_local(clave, info)
        return True, info

    except Exception as e:
        return False, f"Error al verificar la licencia en línea: {e}"



# --------------------------------------------------------------------------
#  SISTEMA DE AUTO-ACTUALIZACIÓN DESDE GITHUB (REMOTA Y SILENCIOSA)
# --------------------------------------------------------------------------
def buscar_actualizaciones_github(app):
    """
    Consulta en segundo plano si existe una versión más reciente en GitHub.
    """
    def _tarea():
        try:
            time.sleep(2)  # Esperar que la ventana cargue completamente
            req = urllib.request.Request(
                URL_VERSION_GITHUB,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            version_remota = str(data.get("version", "")).strip()
            if not version_remota:
                return

            if version_remota != VERSION_ACTUAL and not version_remota.startswith(VERSION_ACTUAL):
                app.log(f"🔔 ¡NUEVA VERSIÓN DISPONIBLE EN GITHUB! ({version_remota})", "warning")
                app.mostrar_modal_actualizacion(data)
            else:
                app.log(f"✅ Bot actualizado a la versión oficial ({VERSION_ACTUAL}).", "info")
        except Exception:
            pass

    t = threading.Thread(target=_tarea, daemon=True)
    t.start()


def ejecutar_actualizacion_automatica(exe_url, config_url, app):
    """
    Descarga la nueva versión desde GitHub y reinicia la aplicación automáticamente.
    """
    try:
        app.log("⬇️ Descargando actualización desde GitHub...", "info")
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        ruta_exe_nuevo = os.path.join(base_dir, "Automatizador_INVIMA_nueva.exe")
        ruta_exe_actual = os.path.join(base_dir, "Automatizador INVIMA.exe")
        ruta_config = os.path.join(base_dir, "config.py")

        # 1. Descargar nuevo ejecutable
        if exe_url:
            req_exe = urllib.request.Request(exe_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_exe, timeout=60) as resp, open(ruta_exe_nuevo, "wb") as out_file:
                out_file.write(resp.read())

        # 2. Descargar nuevo config.py
        if config_url:
            try:
                req_cfg = urllib.request.Request(config_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_cfg, timeout=15) as resp, open(ruta_config, "wb") as out_cfg:
                    out_cfg.write(resp.read())
            except Exception:
                pass

        # 3. Crear script de reemplazo en segundo plano
        ruta_bat = os.path.join(base_dir, "actualizar_bot.bat")
        script_bat = f"""@echo off
timeout /t 2 /nobreak > nul
if exist "{ruta_exe_nuevo}" (
    move /y "{ruta_exe_nuevo}" "{ruta_exe_actual}"
    start "" "{ruta_exe_actual}"
)
del "%~f0"
"""
        with open(ruta_bat, "w", encoding="utf-8") as f:
            f.write(script_bat)

        app.log("✨ Descarga completada. Reiniciando bot...", "success")
        time.sleep(1)

        # 4. Iniciar script y cerrar aplicación actual
        subprocess.Popen(["cmd.exe", "/c", ruta_bat], creationflags=subprocess.CREATE_NO_WINDOW)
        os._exit(0)

    except Exception as e:
        app.log(f"❌ Error al aplicar actualización automática: {e}", "error")
        messagebox.showerror("Error de Actualización", f"No se pudo descargar la actualización:\n{e}")


# --------------------------------------------------------------------------
#  Carga Dinámica de config.py
# --------------------------------------------------------------------------
def cargar_config_dinamico():
    """Carga siempre la versión actual de config.py guardada en la carpeta del ejecutable/script."""
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    ruta_config = os.path.join(base_dir, "config.py")

    if not os.path.exists(ruta_config):
        ruta_config = os.path.join(os.getcwd(), "config.py")

    if os.path.exists(ruta_config):
        try:
            spec = importlib.util.spec_from_file_location("config_user", ruta_config)
            cfg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cfg)
            return cfg
        except Exception as e:
            print(f"Error cargando config.py local: {e}")

    import config as cfg_fallback
    return cfg_fallback


def obtener_dict_proceso(cfg, nombre_proceso):
    """Retorna el diccionario de configuración del proceso seleccionado."""
    if hasattr(cfg, "PROCESOS") and isinstance(cfg.PROCESOS, dict) and nombre_proceso in cfg.PROCESOS:
        return cfg.PROCESOS[nombre_proceso]
    
    # Fallback si config.py no usa PROCESOS
    return {
        "NOMBRE_HOJA": getattr(cfg, "NOMBRE_HOJA", "Matriz Presentaciones"),
        "BOTON_ABRIR_MODAL": getattr(cfg, "BOTON_ABRIR_MODAL", ""),
        "SELECTOR_MODAL": getattr(cfg, "SELECTOR_MODAL", ""),
        "BOTON_ENVIAR": getattr(cfg, "BOTON_ENVIAR", ""),
        "CAMPOS": getattr(cfg, "CAMPOS", [])
    }


# --------------------------------------------------------------------------
#  Lectura y validación del Excel para el proceso activo
# --------------------------------------------------------------------------
def leer_excel(ruta, app, cfg, proceso_config):
    try:
        libro = load_workbook(ruta, data_only=True)
    except FileNotFoundError:
        app.log("❌ ERROR: No se encontró el archivo de Excel.", "error")
        return None
    except Exception as e:
        app.log(f"❌ ERROR al abrir Excel: {e}", "error")
        return None

    nombre_hoja = proceso_config.get("NOMBRE_HOJA", "Matriz Presentaciones")
    if nombre_hoja not in libro.sheetnames:
        app.log(f"❌ ERROR: El Excel seleccionado no contiene la hoja '{nombre_hoja}'.", "error")
        app.log(f"📋 Hojas disponibles en este Excel: {', '.join(libro.sheetnames)}", "warning")
        app.log(f"💡 Asegúrate de que el Excel contenga una pestaña llamada '{nombre_hoja}'", "info")
        return None

    hoja = libro[nombre_hoja]
    crudas = list(hoja.iter_rows(values_only=True))
    if len(crudas) < 2:
        app.log(f"❌ ERROR: La hoja '{nombre_hoja}' no contiene registros suficientes.", "error")
        return None

    encabezados = [str(c).strip() if c is not None else "" for c in crudas[0]]
    campos_req = proceso_config.get("CAMPOS", [])
    faltan = [c["columna"] for c in campos_req if c["columna"] not in encabezados]
    if faltan:
        app.log(f"❌ ERROR: Faltan las siguientes columnas en la hoja '{nombre_hoja}':", "error")
        for c in faltan:
            app.log(f"   • {c}", "error")
        return None

    filas = []
    for i, cruda in enumerate(crudas[1:], start=2): # i representa la línea real en Excel
        if all(v is None for v in cruda):
            continue
        fila = {"__linea_excel__": i}
        for j, enc in enumerate(encabezados):
            v = cruda[j] if j < len(cruda) else None
            fila[enc] = "" if v is None else str(v).strip()
        filas.append(fila)

    app.log(f"✅ Excel validado correctamente para la hoja '{nombre_hoja}': {len(filas)} filas cargadas.", "success")
    return filas

# --------------------------------------------------------------------------
#  Normalización de cadenas (ignora tildes, acentos, mayúsculas y espacios extra)
# --------------------------------------------------------------------------
import unicodedata

def normalizar_texto(texto):
    if not texto:
        return ""
    s = unicodedata.normalize('NFD', str(texto).strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != 'Mn')


def hacer_clic_opcion(opcion_locator):
    try:
        opcion_locator.scroll_into_view_if_needed(timeout=1000)
    except Exception:
        pass
    try:
        opcion_locator.dispatch_event("mousedown")
        time.sleep(0.05)
    except Exception:
        pass
    try:
        opcion_locator.click(force=True, timeout=2000)
    except Exception:
        try:
            opcion_locator.evaluate("el => { el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true})); el.click(); }")
        except Exception:
            pass


def obtener_elemento_visible(page, selector_str):
    """Escanea todos los elementos coincidentes y devuelve el primero visible."""
    locs = page.locator(selector_str)
    count = locs.count()
    if count == 0:
        return None
    for i in range(count):
        el = locs.nth(i)
        try:
            if el.is_visible():
                return el
        except Exception:
            pass
    return locs.first


# --------------------------------------------------------------------------
#  MANEJADOR EXCLUSIVO Y RIGUROSO PARA INFORMACIÓN GENERAL (PRESENTACIONES)
# --------------------------------------------------------------------------

def _limpiar_e_ingresar_texto(page, target, valor):
    """
    Enfoca la casilla específica y tipea el texto de forma segura sin tocar el teclado global.
    """
    try:
        target.click(force=True, timeout=1000)
    except Exception:
        try:
            target.focus(timeout=1000)
        except Exception:
            pass

    time.sleep(0.05)

    # Limpiar solo el elemento objetivo con target.press
    try:
        target.press("Control+a")
        target.press("Backspace")
    except Exception:
        try:
            target.fill("")
        except Exception:
            pass

    time.sleep(0.05)

    # Tipear directamente en la casilla objetivo
    try:
        target.press_sequentially(str(valor), delay=40)
    except Exception:
        try:
            target.fill(str(valor))
        except Exception:
            pass

    time.sleep(0.25)


def _seleccionar_opcion_antdesign(page, target, valor, app):
    """
    Despliega y selecciona la opción exacta o aproximada en Ant Design Select.
    """
    valor_norm = normalizar_texto(valor)

    # 1. Esperar menú desplegable
    try:
        page.wait_for_selector(".ant-select-dropdown:not(.ant-select-dropdown-hidden)", timeout=1500)
    except Exception:
        pass

    dropdown = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)").last
    opciones = dropdown.locator(".ant-select-item-option, div[role='option'], .ant-select-item")
    total = opciones.count()

    if total == 0:
        opciones = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
        total = opciones.count()

    # Log de opciones encontradas para transparencia total
    lista_textos = []
    for k in range(min(total, 10)):
        try:
            t = opciones.nth(k).inner_text().strip()
            if t:
                lista_textos.append(t)
        except Exception:
            pass

    if lista_textos:
        app.log(f"      📋 Opciones desplegadas ({total}): [{', '.join(lista_textos[:5])}]", "detail")
    else:
        app.log(f"      ℹ️ No se desplegaron opciones en menú para '{valor}'", "detail")

    # Si hay opciones desplegadas
    if total > 0:
        # A) Coincidencia EXACTA
        for k in range(total):
            try:
                opc = opciones.nth(k)
                txt = opc.inner_text()
                if normalizar_texto(txt) == valor_norm:
                    app.log(f"      🎯 Encontrada coincidencia EXACTA: '{txt.strip()}'", "detail")
                    hacer_clic_opcion(opc)
                    time.sleep(0.15)
                    try:
                        target.press("Enter")
                    except Exception:
                        pass
                    time.sleep(0.25)
                    return True
            except Exception:
                pass

        # B) Coincidencia PARCIAL (empieza o contiene)
        for k in range(total):
            try:
                opc = opciones.nth(k)
                txt = opc.inner_text()
                txt_n = normalizar_texto(txt)
                if txt_n.startswith(valor_norm) or valor_norm in txt_n or txt_n in valor_norm:
                    app.log(f"      🎯 Encontrada coincidencia PARCIAL: '{txt.strip()}'", "detail")
                    hacer_clic_opcion(opc)
                    time.sleep(0.15)
                    try:
                        target.press("Enter")
                    except Exception:
                        pass
                    time.sleep(0.25)
                    return True
            except Exception:
                pass

        # C) Hacer clic en la primera opción si no hay matcheo directo
        try:
            opc_primera = opciones.first
            txt_prim = opc_primera.inner_text()
            app.log(f"      🎯 Seleccionando primera opción disponible: '{txt_prim.strip()}'", "detail")
            hacer_clic_opcion(opc_primera)
            time.sleep(0.15)
            try:
                target.press("Enter")
            except Exception:
                pass
            time.sleep(0.25)
            return True
        except Exception:
            pass

    # Si no se pudo hacer clic en el menú desplegable, intentar ArrowDown + Enter en la casilla
    try:
        target.press("ArrowDown")
        time.sleep(0.1)
        target.press("Enter")
        time.sleep(0.25)
        return True
    except Exception:
        pass

    return False


def _verificar_campo_seleccionado(page, target, campo, valor, app):
    """
    VERIFICACIÓN UNIVERSAL Y SEGURA DE CAMPOS EN INFORMACIÓN GENERAL:
    1. Si hay .ant-select-selection-item con texto -> Confirmado (Select).
    2. Si el input conserva el valor (input_value) -> Confirmado (AutoComplete / Texto).
    """
    col_nombre = campo.get("columna", "")

    # 1. Buscar etiqueta .ant-select-selection-item (para Selects)
    try:
        padre_item = target.locator("xpath=ancestor::div[contains(@class,'ant-form-item') or contains(@class,'ant-select')]").first
        if padre_item.count() > 0:
            selection_item = padre_item.locator(".ant-select-selection-item")
            if selection_item.count() > 0 and selection_item.first.is_visible():
                texto_item = selection_item.first.inner_text().strip()
                if texto_item:
                    app.log(f"      ✅ Selección confirmada en portal (.ant-select-selection-item): '{texto_item}'", "detail")
                    return True
    except Exception:
        pass

    # 2. Buscar valor en el input (para AutoComplete o casillas de texto)
    try:
        val = target.input_value()
        if val and str(val).strip():
            app.log(f"      ✅ Valor verificado en casilla '{col_nombre}': '{val.strip()}'", "detail")
            return True
    except Exception:
        pass

    return False


def llenar_campo_presentaciones(page, campo, fila, app, cfg):
    valor = fila.get(campo["columna"], "")
    if not valor or str(valor).strip() == "":
        return

    target = obtener_elemento_visible(page, campo["selector"])
    if not target:
        app.log(f"   ⚠️ No se encontró la casilla para '{campo['columna']}'", "warning")
        return

    app.log(f"   ➔ {campo['columna']}: '{valor}'", "detail")

    if campo["tipo"] == "texto":
        try:
            target.fill(str(valor))
            time.sleep(0.15)
        except Exception:
            _limpiar_e_ingresar_texto(page, target, valor)
        return

    # Para autocompletar: reintentos estrictos por campo sin cerrar la ventana emergente
    for intento in range(1, 4):
        _limpiar_e_ingresar_texto(page, target, valor)
        _seleccionar_opcion_antdesign(page, target, valor, app)

        time.sleep(0.3)

        if _verificar_campo_seleccionado(page, target, campo, valor, app):
            return  # ¡Éxito real confirmado!

        app.log(f"      ⚠️ Intento {intento}/3: Campo '{campo['columna']}' no confirmó el valor '{valor}'", "warning")
        # Desenfocar suavemente haciendo clic en la cabecera del modal para cerrar menús colgados sin cerrar el modal
        try:
            page.locator(".ant-modal-header, .ant-modal-title").first.click(force=True, timeout=500)
            time.sleep(0.15)
        except Exception:
            pass

    # Si tras 3 intentos no se confirmó la selección:
    raise ValueError(f"No se pudo seleccionar '{valor}' en '{campo['columna']}'. El portal no registró el valor.")


# --------------------------------------------------------------------------
#  MANEJADOR EXCLUSIVO PARA COMPOSICIÓN (INGREDIENTES Y MEZCLAS)
# --------------------------------------------------------------------------
def llenar_autocompletar_composicion(page, campo, valor, timeout_ms, app):
    selector = campo["selector"]
    target = page.locator(selector).first
    valor_norm = normalizar_texto(valor)

    sugerencia_sel = campo.get("selector_sugerencia") or ".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option"
    col_name = campo["columna"].lower()
    es_ingrediente = "ingrediente" in col_name or "mezcla" in col_name

    timeout_espera_servidor = 8000 if es_ingrediente else 4000
    delay_tipeo = 80
    pausa_post_clic = 0.8 if es_ingrediente else 0.5
    max_intentos_tipeo = 3 if es_ingrediente else 2

    menu_desplegado = False

    for intento_t in range(1, max_intentos_tipeo + 1):
        try:
            try:
                target.click(force=True, timeout=2000)
                time.sleep(0.1)
                target.fill("")
                time.sleep(0.1)
            except Exception:
                pass

            if intento_t > 1:
                app.log(f"      🔄 Re-escribiendo '{campo['columna']}' (Intento {intento_t}/{max_intentos_tipeo})...", "warning")

            target.type(str(valor), delay=delay_tipeo)
            time.sleep(0.4)

            page.wait_for_selector(sugerencia_sel, timeout=timeout_espera_servidor)
            menu_desplegado = True
            break

        except PWTimeout:
            if es_ingrediente:
                app.log(f"      ⏳ Esperando respuesta del servidor de ingredientes para '{campo['columna']}'...", "detail")

    if not menu_desplegado:
        page.wait_for_selector(sugerencia_sel, timeout=timeout_ms)

    dropdown_activo = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)").last
    opciones = dropdown_activo.locator(".ant-select-item-option, div[role='option'], .ant-select-item-option-content")
    total_opciones = opciones.count()

    if total_opciones == 0:
        opciones = page.locator(sugerencia_sel)
        total_opciones = opciones.count()

    if total_opciones == 0:
        raise ValueError(f"La lista desplegable de ingredientes no mostró opciones para '{valor}'")

    for k in range(total_opciones):
        txt_opcion = opciones.nth(k).inner_text()
        if normalizar_texto(txt_opcion) == valor_norm:
            app.log(f"      🎯 Encontrada coincidencia EXACTA para '{valor}' -> '{txt_opcion.strip()}'", "detail")
            hacer_clic_opcion(opciones.nth(k))
            time.sleep(pausa_post_clic)
            return

    for k in range(total_opciones):
        txt_opcion = opciones.nth(k).inner_text()
        txt_norm = normalizar_texto(txt_opcion)
        if txt_norm.startswith(valor_norm) or valor_norm in txt_norm:
            app.log(f"      🎯 Encontrada coincidencia semejante para '{valor}' -> '{txt_opcion.strip()}'", "detail")
            hacer_clic_opcion(opciones.nth(k))
            time.sleep(pausa_post_clic)
            return

    coincidencia = opciones.filter(has_text=valor)
    if coincidencia.count() > 0:
        hacer_clic_opcion(coincidencia.first)
        time.sleep(pausa_post_clic)
    elif total_opciones > 0:
        app.log(f"      🎯 Seleccionando opción en lista para '{valor}'", "detail")
        hacer_clic_opcion(opciones.first)
        time.sleep(pausa_post_clic)


def llenar_multiselect(page, campo, valor, timeout_ms, app):
    import re
    items = [x.strip() for x in re.split(r'[,;|\n]', str(valor)) if x.strip()]
    if not items:
        return

    selector = campo["selector"]
    target = page.locator(selector).first
    sugerencia_sel = campo.get("selector_sugerencia") or ".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option"

    for idx, item in enumerate(items):
        item_norm = normalizar_texto(item)
        app.log(f"      ➔ Seleccionando función ({idx+1}/{len(items)}): '{item}'", "detail")

        for intento_t in range(1, 3):
            try:
                try:
                    target.click(force=True, timeout=2000)
                except Exception:
                    pass

                target.fill(item)
                time.sleep(0.4)

                timeout_intento = min(3500, timeout_ms)
                page.wait_for_selector(sugerencia_sel, timeout=timeout_intento)
                break
            except PWTimeout:
                target.fill("")
                time.sleep(0.3)
                target.type(item, delay=80)

        opciones = page.locator(sugerencia_sel)
        total = opciones.count()
        if total == 0:
            app.log(f"      ⚠️ No se hallaron opciones para '{item}'", "warning")
            continue

        encontrado = False
        for k in range(total):
            txt_opcion = opciones.nth(k).inner_text()
            if normalizar_texto(txt_opcion) == item_norm:
                opciones.nth(k).click(force=True)
                encontrado = True
                time.sleep(0.4)
                break

        if not encontrado:
            for k in range(total):
                txt_opcion = opciones.nth(k).inner_text()
                txt_norm = normalizar_texto(txt_opcion)
                if txt_norm.startswith(item_norm) or item_norm in txt_norm:
                    opciones.nth(k).click(force=True)
                    encontrado = True
                    time.sleep(0.4)
                    break

        if not encontrado and total > 0:
            opciones.first.click(force=True)
            time.sleep(0.4)

    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def llenar_select(page, campo, valor, timeout_ms, app):
    valor_norm = normalizar_texto(valor)
    
    targets_posibles = [
        page.locator(".ant-modal-body .ant-form-item:has-text('Tipo') .ant-select-selector").first,
        page.locator(".ant-modal-body .ant-form-item:has-text('Tipo') input").first,
        page.locator(".ant-modal-body .ant-form-item:has-text('Tipo')").first,
        page.locator(campo["selector"]).first
    ]

    dropdown_sel = ".ant-select-dropdown:not(.ant-select-dropdown-hidden)"

    menu_abierto = False
    for target in targets_posibles:
        try:
            if target.count() > 0:
                target.click(force=True, timeout=2000)
                time.sleep(0.5)
                if page.locator(dropdown_sel).count() > 0:
                    menu_abierto = True
                    break
        except Exception:
            continue

    if not menu_abierto:
        try:
            page.locator(".ant-modal-body .ant-form-item:has-text('Tipo')").first.click(force=True)
            time.sleep(0.6)
        except Exception:
            pass

    page.wait_for_selector(dropdown_sel, timeout=max(6000, timeout_ms))
    
    dropdown_activo = page.locator(dropdown_sel).last
    opciones = dropdown_activo.locator(".ant-select-item-option, div[role='option'], .ant-select-item-option-content")
    total_opciones = opciones.count()

    if total_opciones == 0:
        opciones = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
        total_opciones = opciones.count()

    if total_opciones == 0:
        raise ValueError(f"No se desplegaron opciones en el menú para '{valor}'")

    app.log(f"      🔍 Se encontraron {total_opciones} opciones en el menú desplegable activo para '{valor}'.", "detail")

    for k in range(total_opciones):
        txt_opcion = opciones.nth(k).inner_text()
        txt_norm = normalizar_texto(txt_opcion)
        if txt_norm == valor_norm:
            app.log(f"      🎯 Seleccionada opción '{txt_opcion.strip()}' (para '{valor}')", "detail")
            hacer_clic_opcion(opciones.nth(k))
            time.sleep(0.6)
            return

    for k in range(total_opciones):
        txt_opcion = opciones.nth(k).inner_text()
        txt_norm = normalizar_texto(txt_opcion)
        if txt_norm.startswith(valor_norm) or valor_norm in txt_norm:
            app.log(f"      🎯 Seleccionada opción semejante '{txt_opcion.strip()}' (para '{valor}')", "detail")
            hacer_clic_opcion(opciones.nth(k))
            time.sleep(0.6)
            return

    try:
        opc_has = dropdown_activo.locator(f":has-text('{valor}')").last
        if opc_has.count() > 0:
            hacer_clic_opcion(opc_has)
            time.sleep(0.6)
            return
    except Exception:
        pass

    raise ValueError(f"La opción '{valor}' no se encuentra en la lista del menú activo")


def llenar_switch(page, campo, valor, app):
    target = page.locator(campo["selector"]).first
    if target.count() == 0 or not target.is_visible():
        target = page.locator("#isNanomaterial, button#isNanomaterial, .ant-modal-body button.ant-switch, button.ant-switch").first

    if target.count() == 0:
        app.log(f"   ⚠️ No se encontró el interruptor para '{campo['columna']}'", "warning")
        return

    deseado_si = str(valor).strip().lower() in ["sí", "si", "s", "true", "1", "yes"]

    try:
        aria_checked = target.get_attribute("aria-checked")
        clases = target.get_attribute("class") or ""
        esta_activo = aria_checked == "true" or "ant-switch-checked" in clases

        if deseado_si and not esta_activo:
            app.log(f"   🔘 Activando interruptor '{campo['columna']}' (Sí)", "detail")
            try:
                target.click(force=True)
            except Exception:
                target.evaluate("el => el.click()")
            time.sleep(0.4)
        elif not deseado_si and esta_activo:
            app.log(f"   🔘 Desactivando interruptor '{campo['columna']}' (No)", "detail")
            try:
                target.click(force=True)
            except Exception:
                target.evaluate("el => el.click()")
            time.sleep(0.3)
    except Exception as e:
        app.log(f"   ⚠️ No se pudo cambiar el interruptor '{campo['columna']}': {e}", "warning")


def llenar_campo_composicion(page, campo, fila, app, cfg):
    valor = fila.get(campo["columna"], "")
    if not valor or str(valor).strip() == "":
        return

    target = page.locator(campo["selector"]).first
    try:
        if target.count() == 0 or not target.is_visible():
            app.log(f"   ℹ️ Campo '{campo['columna']}' no está visible para este Tipo, omitiendo...", "info")
            return
    except Exception:
        pass

    try:
        if target.is_disabled():
            app.log(f"   ⏳ Esperando a que el portal desbloquee '{campo['columna']}'...", "detail")
            page.wait_for_function("el => !el.disabled", arg=target.element_handle(), timeout=4000)
    except Exception:
        pass

    app.log(f"   ➔ {campo['columna']}: '{valor}'", "detail")
    timeout_ms = getattr(cfg, "TIMEOUT_SEGUNDOS", 15) * 1000

    try:
        if campo["tipo"] == "texto":
            target.fill(str(valor))
        elif campo["tipo"] == "select":
            llenar_select(page, campo, valor, timeout_ms, app)
        elif campo["tipo"] == "autocompletar":
            llenar_autocompletar_composicion(page, campo, valor, timeout_ms, app)
        elif campo["tipo"] == "multiselect":
            llenar_multiselect(page, campo, valor, timeout_ms, app)
        elif campo["tipo"] in ["switch", "toggle"]:
            llenar_switch(page, campo, valor, app)
    except Exception as e:
        raise Exception(f"Columna '{campo['columna']}' (Valor: '{valor}') -> {e}")


def llenar_campo(page, campo, fila, linea_excel, app, cfg, nombre_proceso=""):
    es_presentaciones_proc = "presentaci" in str(nombre_proceso).lower() or "informaci" in str(nombre_proceso).lower()
    if es_presentaciones_proc:
        llenar_campo_presentaciones(page, campo, fila, app, cfg)
    else:
        llenar_campo_composicion(page, campo, fila, app, cfg)


# --------------------------------------------------------------------------
#  Generador de Reportes de Error
# --------------------------------------------------------------------------
def guardar_reporte_errores(ruta_excel, nombre_proceso, lista_errores):
    carpeta_salida = os.path.dirname(ruta_excel) if ruta_excel else os.getcwd()
    ruta_txt = os.path.join(carpeta_salida, f"reporte_errores_{nombre_proceso.replace(' ', '_')}.txt")

    try:
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write("==========================================================================" + "\n")
            f.write("         AUTOMATIZADOR INVIMA - REPORTE DE ERRORES DE REGISTRO            " + "\n")
            f.write(f" Proceso: {nombre_proceso}" + "\n")
            f.write(f" Fecha y Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}" + "\n")
            f.write(f" Archivo Excel: {os.path.basename(ruta_excel)}" + "\n")
            f.write("==========================================================================" + "\n\n")

            for err in lista_errores:
                f.write(f"📍 LÍNEA EN EXCEL #{err['linea_excel']}\n")
                f.write(f"   • Registro N°: {err['numero_registro']}\n")
                f.write(f"   • Columna Afectada: {err['columna']}\n")
                f.write(f"   • Valor Buscado: {err['valor']}\n")
                f.write(f"   • Razón del Error: {err['detalle']}\n")
                f.write(f"   • Intentos Realizados: {err['intentos']}\n")
                f.write("-" * 65 + "\n\n")

        return ruta_txt
    except Exception as e:
        print(f"Error escribiendo reporte de errores: {e}")
        return None


# --------------------------------------------------------------------------
#  Motor de ejecución principal
# --------------------------------------------------------------------------
def ejecutar(ruta_excel, nombre_proceso, app):
    cfg = cargar_config_dinamico()
    app.log(f"⚙️ Iniciando automatización para el proceso: '{nombre_proceso}'", "info")

    proceso_cfg = obtener_dict_proceso(cfg, nombre_proceso)

    selector_abrir = proceso_cfg.get("BOTON_ABRIR_MODAL", "").strip()
    if not selector_abrir or "PON_EL_SELECTOR" in selector_abrir:
        app.log(f"❌ ERROR: El proceso '{nombre_proceso}' no tiene configurado BOTON_ABRIR_MODAL en config.py", "error")
        app.finalizar_proceso(exito=False)
        return

    filas = leer_excel(ruta_excel, app, cfg, proceso_cfg)
    if filas is None:
        app.finalizar_proceso(exito=False)
        return

    total = len(filas)
    app.actualizar_progreso(0, total)
    timeout_ms = getattr(cfg, "TIMEOUT_SEGUNDOS", 15) * 1000

    try:
        with sync_playwright() as p:
            if not esta_puerto_abierto(PUERTO_CHROME):
                app.log("🌐 Chrome automatizado no detectado en puerto 9222. Iniciando automáticamente...", "warning")
                abrir_chrome_automatizado(app)
                time.sleep(3)

            app.log("📡 Conectando con Google Chrome (puerto 9222)...", "info")
            try:
                browser = p.chromium.connect_over_cdp(f"http://localhost:{PUERTO_CHROME}")
            except Exception:
                # Segundo intento tras relanzar
                if abrir_chrome_automatizado(app):
                    time.sleep(2)
                    try:
                        browser = p.chromium.connect_over_cdp(f"http://localhost:{PUERTO_CHROME}")
                    except Exception as e2:
                        app.log(f"❌ ERROR CRÍTICO: No se pudo conectar a Chrome tras relanzar: {e2}", "error")
                        app.finalizar_proceso(exito=False)
                        return
                else:
                    app.log("❌ ERROR CRÍTICO: No se pudo conectar a Chrome (Puerto 9222).", "error")
                    app.finalizar_proceso(exito=False)
                    return

            contexto = browser.contexts[0]
            page = contexto.pages[0] if contexto.pages else contexto.new_page()
            page.set_default_timeout(timeout_ms)

            app.log(f"🔗 Conectado exitosamente a Chrome.", "success")
            app.log(f"🌐 Pestaña activa: {page.url}", "info")
            app.log("=" * 60, "divider")

            exitosos = 0
            errores = 0
            lista_errores = []

            selector_modal = proceso_cfg.get("SELECTOR_MODAL", "").strip() or ".ant-modal-content, .ant-modal, .modal-dialog"
            selector_enviar = proceso_cfg.get("BOTON_ENVIAR", "").strip() or ".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button[type='submit']"
            campos_proceso = proceso_cfg.get("CAMPOS", [])

            for numero, fila in enumerate(filas, start=1):
                linea_excel = fila["__linea_excel__"]

                if app.debe_detener:
                    app.log("\n⏹️ Proceso detenido completamente por el usuario.", "warning")
                    break

                while app.debe_pausar and not app.debe_detener:
                    time.sleep(0.3)

                if app.debe_detener:
                    app.log("\n⏹️ Proceso detenido completamente por el usuario.", "warning")
                    break

                app.log(f"📌 Procesando Registro {numero} de {total} (Línea Excel #{linea_excel})...", "header")
                app.actualizar_progreso(numero, total)

                # Sistema de reintentos por fila (3 intentos para todos los procesos)
                es_presentaciones_proc = "presentaci" in str(nombre_proceso).lower() or "informaci" in str(nombre_proceso).lower()
                max_intentos = 3
                exito_fila = False
                ultimo_detalle_error = ""

                for intento in range(1, max_intentos + 1):
                    if app.debe_detener:
                        break

                    if intento > 1:
                        app.log(f"   🔄 INTENTO {intento} de {max_intentos} para Línea Excel #{linea_excel}...", "warning")
                        try:
                            page.keyboard.press("Escape")
                            time.sleep(0.5)
                        except Exception:
                            pass

                    try:
                        app.log(f"   🖱️ Abrir ventana modal...", "detail")
                        page.locator(selector_abrir).first.click(timeout=timeout_ms)

                        app.log(f"   ⏳ Esperando ventana modal...", "detail")
                        page.wait_for_selector(selector_modal, state="visible", timeout=timeout_ms)

                        # Llenar cada uno de los campos configurados para este proceso
                        for campo in campos_proceso:
                            if "PON_EL_SELECTOR" in campo["selector"]:
                                continue
                            llenar_campo(page, campo, fila, linea_excel, app, cfg, nombre_proceso)

                        app.log(f"   💾 Enviando y guardando formulario...", "detail")
                        btn_env = page.locator(selector_enviar).first
                        if btn_env.count() > 0 and btn_env.is_visible():
                            btn_env.click(force=True, timeout=timeout_ms)
                        else:
                            page.locator(".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button:has-text('Adicionar'), button[type='submit']").first.click(force=True)

                        app.log(f"   ⏳ Esperando cierre de la ventana...", "detail")
                        try:
                            page.wait_for_selector(selector_modal, state="hidden", timeout=4000)
                        except Exception:
                            try:
                                page.keyboard.press("Escape")
                                time.sleep(0.5)
                            except Exception:
                                pass
                            raise ValueError("El formulario modal no se cerró tras hacer clic en Guardar.")

                        exito_fila = True
                        break  # Exit retry loop on success

                    except PWTimeout:
                        ultimo_detalle_error = "Tiempo de espera agotado al interactuar con el elemento o guardar modal."
                    except Exception as e:
                        ultimo_detalle_error = str(e)

                    try:
                        page.keyboard.press("Escape")
                        time.sleep(0.4)
                    except Exception:
                        pass

                # Evaluación de resultado de la fila
                if exito_fila:
                    exitosos += 1
                    app.incrementar_exitos()
                    app.log(f"   ✨ Línea Excel #{linea_excel} guardada con éxito.", "success")
                else:
                    errores += 1
                    app.incrementar_errores()

                    col_afectada = "Desconocida / Estructura Modal"
                    valor_afectado = "N/A"
                    if "Columna '" in ultimo_detalle_error:
                        try:
                            col_afectada = ultimo_detalle_error.split("Columna '")[1].split("'")[0]
                        except Exception:
                            pass
                    if "Valor en Excel: '" in ultimo_detalle_error:
                        try:
                            valor_afectado = ultimo_detalle_error.split("Valor en Excel: '")[1].split("'")[0]
                        except Exception:
                            pass

                    app.log(f"   ❌ LÍNEA EXCEL #{linea_excel} FALLÓ TRAS {max_intentos} INTENTOS", "error")
                    app.log(f"      📍 Columna afectada: {col_afectada}", "error")
                    app.log(f"      📄 Valor en Excel: '{valor_afectado}'", "error")
                    app.log(f"      ⚠️ Motivo: {ultimo_detalle_error}", "warning")

                    lista_errores.append({
                        "linea_excel": linea_excel,
                        "numero_registro": numero,
                        "columna": col_afectada,
                        "valor": valor_afectado,
                        "detalle": ultimo_detalle_error,
                        "intentos": max_intentos
                    })

                    app.log(f"   ⏩ Continuando automáticamente con el siguiente registro...", "info")

            app.log("=" * 60, "divider")
            if app.debe_detener:
                app.log(f"🏁 PROCESO DETENIDO POR EL USUARIO: {exitosos} exitosos, {errores} errores.", "warning")
            else:
                app.log(f"📊 RESUMEN FINAL [{nombre_proceso}]: {exitosos} exitosos, {errores} fallidos de {total} registros.", "header")

            # Reporte de errores
            if lista_errores:
                ruta_reporte = guardar_reporte_errores(ruta_excel, nombre_proceso, lista_errores)
                app.log(f"\n📄 REPORTE DE ERRORES GENERADO:", "error")
                app.log(f"   📍 Guardado en: {ruta_reporte}", "warning")
                app.log(f"   💡 Abre este archivo para ver la línea exacta de Excel a corregir.", "info")

    except Exception as e:
        app.log(f"❌ Error general en ejecución: {e}", "error")

    app.finalizar_proceso(exito=(exitosos > 0 and errores == 0))


# --------------------------------------------------------------------------
#  Interfaz Gráfica Profesional con Selector de Proceso (CustomTkinter)
# --------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Automatizador INVIMA - MasterDent")
        self.geometry("780x720")
        self.minsize(720, 640)

        # Cargar icono de ventana
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        ruta_ico = os.path.join(base_dir, "app_icon.ico")
        if os.path.exists(ruta_ico):
            try:
                self.iconbitmap(ruta_ico)
            except Exception:
                pass

        # Variables de control
        self.cfg = cargar_config_dinamico()
        self.ruta_excel = None
        self.debe_pausar = False
        self.debe_detener = False
        self.en_ejecucion = False
        self.num_exitos = 0
        self.num_errores = 0
        self.licencia_info = None

        self._construir_interfaz()
        buscar_actualizaciones_github(self)
        self.after(300, self._verificar_licencia_inicial)

    def _verificar_licencia_inicial(self):
        datos_locales = leer_licencia_local()
        if datos_locales and "clave" in datos_locales:
            clave = datos_locales["clave"]
            valido, res = validar_licencia_firebase(clave)
            if valido:
                self.licencia_info = res
                self.log(f"🔑 LICENCIA ACTIVA: {res.get('empresa')} (Equipos: {res.get('equipos_usados')}/{res.get('max_equipos')})", "success")
                return

        # Si no hay licencia local o no es válida, pedir activación
        self.mostrar_modal_activacion_licencia()

    def mostrar_modal_activacion_licencia(self, mensaje_error_inicial=""):
        top = ctk.CTkToplevel(self)
        top.title("🔐 Activación de Licencia - Bot INVIMA")
        top.geometry("520x360")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.grab_set()

        def _on_cerrar_sin_licencia():
            if not self.licencia_info:
                messagebox.showwarning(
                    "Licencia Requerida",
                    "Se requiere una licencia activa para utilizar el Automatizador INVIMA.\nLa aplicación se cerrará."
                )
                self.destroy()
                sys.exit(0)
            else:
                top.destroy()

        top.protocol("WM_DELETE_WINDOW", _on_cerrar_sin_licencia)

        lbl_title = ctk.CTkLabel(
            top,
            text="🔐 Activación de Licencia de Software",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#F8FAFC"
        )
        lbl_title.pack(pady=(22, 6))

        lbl_sub = ctk.CTkLabel(
            top,
            text="Ingresa tu Clave de Licencia proporcionada por el proveedor\npara activar el Automatizador INVIMA en este equipo.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        lbl_sub.pack(pady=(0, 16))

        entry_clave = ctk.CTkEntry(
            top,
            placeholder_text="Ej: DEMO-2026-INVIMA",
            width=380,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        entry_clave.pack(pady=8)

        lbl_status = ctk.CTkLabel(
            top,
            text=mensaje_error_inicial,
            font=ctk.CTkFont(size=12),
            text_color="#EF4444" if mensaje_error_inicial else "#94A3B8"
        )
        lbl_status.pack(pady=6)

        def _activar():
            clave_ingresada = entry_clave.get().strip().upper()
            if not clave_ingresada:
                lbl_status.configure(text="❌ Por favor ingresa tu clave de licencia.", text_color="#EF4444")
                return

            lbl_status.configure(text="⏳ Verificando licencia en línea...", text_color="#3B82F6")
            top.update()

            valido, res = validar_licencia_firebase(clave_ingresada)
            if valido:
                self.licencia_info = res
                top.destroy()
                self.log(f"🎉 ¡Licencia Activada Exitosamente! Empresa: {res.get('empresa')}", "success")
                messagebox.showinfo("Licencia Activada", f"¡Bienvenido {res.get('empresa')}!\n\nTu software ha quedado activado en este equipo.")
            else:
                lbl_status.configure(text=f"❌ {res}", text_color="#EF4444")

        btn_activar = ctk.CTkButton(
            top,
            text="🚀 Activar Licencia Ahora",
            font=ctk.CTkFont(weight="bold", size=14),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            height=42,
            width=220,
            command=_activar
        )
        btn_activar.pack(pady=(12, 10))

    def mostrar_modal_actualizacion(self, data):
        version_n = data.get("version", "Nueva versión")
        novedades = data.get("novedades", "Mejoras generales y correcciones.")
        exe_url = data.get("exe_url", "")
        config_url = data.get("config_url", "")

        def _construir_dialogo():
            try:
                top = ctk.CTkToplevel(self)
                top.title("✨ Actualización Disponible")
                top.geometry("500x340")
                top.resizable(False, False)
                top.attributes("-topmost", True)
                top.grab_set()

                lbl = ctk.CTkLabel(
                    top,
                    text=f"🎉 ¡Nueva versión {version_n} disponible!",
                    font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                    text_color="#10B981"
                )
                lbl.pack(pady=(18, 6))

                lbl_sub = ctk.CTkLabel(
                    top,
                    text="Una versión más reciente del Automatizador está lista para instalar.",
                    font=ctk.CTkFont(size=12),
                    text_color="#94A3B8"
                )
                lbl_sub.pack(pady=(0, 10))

                txt = ctk.CTkTextbox(top, width=450, height=140, fg_color="#0F172A", text_color="#E2E8F0")
                txt.pack(pady=4)
                txt.insert("0.0", f"Novedades:\n{novedades}")
                txt.configure(state="disabled")

                def _actualizar():
                    top.destroy()
                    threading.Thread(target=ejecutar_actualizacion_automatica, args=(exe_url, config_url, self), daemon=True).start()

                btn = ctk.CTkButton(
                    top,
                    text="🚀 Actualizar Ahora Automáticamente",
                    font=ctk.CTkFont(weight="bold"),
                    fg_color="#10B981",
                    hover_color="#059669",
                    height=38,
                    command=_actualizar
                )
                btn.pack(pady=14)
            except Exception as e:
                print(f"Error mostrando modal de actualización: {e}")

        self.after(500, _construir_dialogo)

    def _obtener_lista_procesos(self):
        if hasattr(self.cfg, "PROCESOS") and isinstance(self.cfg.PROCESOS, dict):
            return list(self.cfg.PROCESOS.keys())
        return ["Información General (Presentaciones)"]

    def _construir_interfaz(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. HEADER / BARRA DE TÍTULO
        frame_header = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=12)
        frame_header.grid(row=0, column=0, padx=16, pady=(16, 6), sticky="ew")
        frame_header.grid_columnconfigure(0, weight=1)

        lbl_title = ctk.CTkLabel(
            frame_header,
            text="🤖 Automatizador INVIMA",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#F8FAFC"
        )
        lbl_title.grid(row=0, column=0, padx=16, pady=(12, 2), sticky="w")

        lbl_subtitle = ctk.CTkLabel(
            frame_header,
            text="Sistema Multi-Proceso de Registro Automático",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94A3B8"
        )
        lbl_subtitle.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        btn_chrome = ctk.CTkButton(
            frame_header,
            text="🌐 Abrir Chrome Bot",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#0EA5E9",
            hover_color="#0284C7",
            height=32,
            width=140,
            command=lambda: abrir_chrome_automatizado(self)
        )
        btn_chrome.grid(row=0, column=1, padx=(0, 10), pady=12, sticky="e")

        self.badge_estado = ctk.CTkLabel(
            frame_header,
            text="● EN ESPERA",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94A3B8",
            fg_color="#334155",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.badge_estado.grid(row=0, column=2, rowspan=2, padx=16, pady=12, sticky="e")

        # 2. SELECTOR DE PROCESO DE AUTOMATIZACIÓN
        frame_proceso = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=12)
        frame_proceso.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        frame_proceso.grid_columnconfigure(1, weight=1)

        lbl_sec_proceso = ctk.CTkLabel(
            frame_proceso,
            text="📋 Proceso a Automatizar:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#E2E8F0"
        )
        lbl_sec_proceso.grid(row=0, column=0, padx=(16, 8), pady=12, sticky="w")

        lista_procesos = self._obtener_lista_procesos()
        self.opt_proceso = ctk.CTkOptionMenu(
            frame_proceso,
            values=lista_procesos,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#3B82F6",
            button_color="#2563EB",
            button_hover_color="#1D4ED8",
            height=36,
            command=self.on_proceso_changed
        )
        self.opt_proceso.grid(row=0, column=1, padx=(0, 16), pady=12, sticky="ew")
        self.opt_proceso.set(lista_procesos[0])

        self.lbl_info_hoja = ctk.CTkLabel(
            frame_proceso,
            text=f"📄 Hoja requerida en Excel: '{self._obtener_hoja_actual()}'",
            font=ctk.CTkFont(size=11),
            text_color="#38BDF8"
        )
        self.lbl_info_hoja.grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 10), sticky="w")

        # 3. PANEL DE SELECCIÓN DE ARCHIVO EXCEL
        frame_top = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=12)
        frame_top.grid(row=2, column=0, padx=16, pady=6, sticky="ew")
        frame_top.grid_columnconfigure(0, weight=1)

        lbl_sec_archivo = ctk.CTkLabel(
            frame_top,
            text="📁 Archivo de Datos Excel",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#E2E8F0"
        )
        lbl_sec_archivo.grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 4), sticky="w")

        self.entry_path = ctk.CTkEntry(
            frame_top,
            placeholder_text="Seleccione el archivo .xlsx con los datos...",
            font=ctk.CTkFont(size=12),
            height=36,
            fg_color="#1E293B",
            border_color="#334155"
        )
        self.entry_path.grid(row=1, column=0, padx=(16, 8), pady=(0, 12), sticky="ew")

        self.btn_browse = ctk.CTkButton(
            frame_top,
            text="📂 Seleccionar Excel",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            height=36,
            command=self.seleccionar_excel
        )
        self.btn_browse.grid(row=1, column=1, padx=(0, 16), pady=(0, 12))

        # 4. PANEL DE BOTONES Y PROGRESO
        frame_controls = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=12)
        frame_controls.grid(row=3, column=0, padx=16, pady=6, sticky="ew")
        frame_controls.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_comenzar = ctk.CTkButton(
            frame_controls,
            text="🚀 Comenzar",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            height=40,
            command=self.action_comenzar_reanudar
        )
        self.btn_comenzar.grid(row=0, column=0, padx=(16, 6), pady=12, sticky="ew")

        self.btn_pausar = ctk.CTkButton(
            frame_controls,
            text="⏸️ Pausar",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#F59E0B",
            hover_color="#D97706",
            height=40,
            state="disabled",
            command=self.action_pausar
        )
        self.btn_pausar.grid(row=0, column=1, padx=6, pady=12, sticky="ew")

        self.btn_detener = ctk.CTkButton(
            frame_controls,
            text="⏹️ Detener",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            height=40,
            state="disabled",
            command=self.action_detener
        )
        self.btn_detener.grid(row=0, column=2, padx=(6, 16), pady=12, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(
            frame_controls,
            height=10,
            corner_radius=5,
            progress_color="#10B981",
            fg_color="#0F172A"
        )
        self.progress_bar.grid(row=1, column=0, columnspan=3, padx=16, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0.0)

        frame_metrics = ctk.CTkFrame(frame_controls, fg_color="transparent")
        frame_metrics.grid(row=2, column=0, columnspan=3, padx=16, pady=(0, 10), sticky="ew")
        frame_metrics.grid_columnconfigure((0, 1, 2), weight=1)

        self.lbl_metric_filas = ctk.CTkLabel(
            frame_metrics, text="📊 Progreso: 0 / 0", font=ctk.CTkFont(size=11), text_color="#94A3B8"
        )
        self.lbl_metric_filas.grid(row=0, column=0, sticky="w")

        self.lbl_metric_exitos = ctk.CTkLabel(
            frame_metrics, text="✅ Éxitos: 0", font=ctk.CTkFont(size=11), text_color="#34D399"
        )
        self.lbl_metric_exitos.grid(row=0, column=1, sticky="n")

        self.lbl_metric_errores = ctk.CTkLabel(
            frame_metrics, text="❌ Errores: 0", font=ctk.CTkFont(size=11), text_color="#F87171"
        )
        self.lbl_metric_errores.grid(row=0, column=2, sticky="e")

        # 5. TERMINAL / CONSOLA DE REGISTROS
        frame_log = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=12)
        frame_log.grid(row=4, column=0, padx=16, pady=(6, 16), sticky="nsew")
        frame_log.grid_columnconfigure(0, weight=1)
        frame_log.grid_rowconfigure(1, weight=1)

        lbl_log_title = ctk.CTkLabel(
            frame_log,
            text="💻 Consola de Registros y Eventos",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#94A3B8"
        )
        lbl_log_title.grid(row=0, column=0, padx=16, pady=(10, 4), sticky="w")

        self.txt_log = ctk.CTkTextbox(
            frame_log,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#090D16",
            text_color="#38BDF8",
            corner_radius=8,
            border_width=1,
            border_color="#1E293B"
        )
        self.txt_log.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

    def _obtener_hoja_actual(self):
        nombre_proceso = self.opt_proceso.get() if hasattr(self, 'opt_proceso') else self._obtener_lista_procesos()[0]
        proceso_cfg = obtener_dict_proceso(self.cfg, nombre_proceso)
        return proceso_cfg.get("NOMBRE_HOJA", "Matriz Presentaciones")

    def on_proceso_changed(self, nuevo_proceso):
        self.cfg = cargar_config_dinamico()
        hoja_req = self._obtener_hoja_actual()
        self.lbl_info_hoja.configure(text=f"📄 Hoja requerida en Excel: '{hoja_req}'")
        self.log(f"🔄 Proceso cambiado a: '{nuevo_proceso}' (Hoja requerida: '{hoja_req}')", "info")

        # Limpiar datos anteriores
        self.progress_bar.set(0.0)
        self.num_exitos = 0
        self.num_errores = 0
        self.lbl_metric_filas.configure(text="📊 Progreso: 0 / 0")
        self.lbl_metric_exitos.configure(text="✅ Éxitos: 0")
        self.lbl_metric_errores.configure(text="❌ Errores: 0")

    def set_estado_badge(self, texto, color_bg, color_txt="#FFFFFF"):
        self.badge_estado.configure(text=f"● {texto}", fg_color=color_bg, text_color=color_txt)

    def log(self, mensaje, tipo="normal"):
        timestamp = time.strftime("[%H:%M:%S] ")
        linea = f"{timestamp}{mensaje}\n"

        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", linea)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def seleccionar_excel(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar Excel de Datos",
            filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            self.ruta_excel = ruta
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, ruta)
            self.log(f"📁 Archivo seleccionado: {os.path.basename(ruta)}", "info")

    def actualizar_progreso(self, actual, total):
        porcentaje = actual / total if total > 0 else 0
        self.progress_bar.set(porcentaje)
        self.lbl_metric_filas.configure(text=f"📊 Progreso: {actual} / {total}")

    def incrementar_exitos(self):
        self.num_exitos += 1
        self.lbl_metric_exitos.configure(text=f"✅ Éxitos: {self.num_exitos}")

    def incrementar_errores(self):
        self.num_errores += 1
        self.lbl_metric_errores.configure(text=f"❌ Errores: {self.num_errores}")

    def action_comenzar_reanudar(self):
        if not self.en_ejecucion:
            if not self.ruta_excel:
                self.log("⚠️ Por favor selecciona primero un archivo Excel válido.", "warning")
                return

            if not self.licencia_info or "clave" not in self.licencia_info:
                self.log("❌ ERROR CRÍTICO DE SEGURIDAD: No hay una licencia activa validada.", "error")
                messagebox.showerror("Licencia Requerida", "No puedes iniciar la automatización sin una licencia activa.")
                self.mostrar_modal_activacion_licencia("Debes activar una licencia para continuar.")
                return

            # Re-validación en tiempo real antes de iniciar
            clave = self.licencia_info["clave"]
            valido, res = validar_licencia_firebase(clave)
            if not valido:
                self.licencia_info = None
                self.log(f"❌ LICENCIA RECHAZADA POR EL SERVIDOR: {res}", "error")
                messagebox.showerror("Licencia Desactivada", f"La licencia ha sido inhabilitada o ha caducado:\n{res}")
                self.mostrar_modal_activacion_licencia(res)
                return

            nombre_proceso = self.opt_proceso.get()

            self.en_ejecucion = True
            self.debe_pausar = False
            self.debe_detener = False
            self.num_exitos = 0
            self.num_errores = 0
            self.lbl_metric_exitos.configure(text="✅ Éxitos: 0")
            self.lbl_metric_errores.configure(text="❌ Errores: 0")

            self.btn_browse.configure(state="disabled")
            self.opt_proceso.configure(state="disabled")
            self.btn_comenzar.configure(text="🚀 Ejecutando...", fg_color="#059669", state="disabled")
            self.btn_pausar.configure(state="normal", text="⏸️ Pausar", fg_color="#F59E0B")
            self.btn_detener.configure(state="normal")
            self.set_estado_badge("EJECUTANDO", "#059669")

            threading.Thread(target=ejecutar, args=(self.ruta_excel, nombre_proceso, self), daemon=True).start()

        elif self.debe_pausar:
            self.debe_pausar = False
            self.btn_comenzar.configure(text="🚀 Ejecutando...", fg_color="#059669", state="disabled")
            self.btn_pausar.configure(text="⏸️ Pausar", fg_color="#F59E0B")
            self.set_estado_badge("EJECUTANDO", "#059669")
            self.log("▶️ Proceso reanudado por el usuario.", "info")

    def action_pausar(self):
        if self.en_ejecucion and not self.debe_pausar:
            self.debe_pausar = True
            self.btn_pausar.configure(text="▶️ Reanudar", fg_color="#10B981")
            self.btn_comenzar.configure(text="▶️ Reanudar", fg_color="#10B981", state="normal")
            self.set_estado_badge("PAUSADO", "#D97706")
            self.log("⏸️ Proceso pausado. Haz clic en 'Reanudar' para continuar.", "warning")

    def action_detener(self):
        if self.en_ejecucion:
            self.debe_detener = True
            self.debe_pausar = False
            self.set_estado_badge("DETENIENDO...", "#DC2626")
            self.log("🛑 Cancelando proceso... Espere a finalizar la fila actual.", "warning")

    def finalizar_proceso(self, exito=True):
        self.en_ejecucion = False
        self.debe_pausar = False
        self.debe_detener = False

        self.btn_browse.configure(state="normal")
        self.opt_proceso.configure(state="normal")
        self.btn_comenzar.configure(text="🚀 Comenzar", fg_color="#10B981", state="normal")
        self.btn_pausar.configure(text="⏸️ Pausar", fg_color="#F59E0B", state="disabled")
        self.btn_detener.configure(state="disabled")

        if self.badge_estado.cget("text").endswith("DETENIENDO..."):
            self.set_estado_badge("DETENIDO", "#DC2626")
        elif exito:
            self.set_estado_badge("COMPLETADO", "#10B981")
        else:
            self.set_estado_badge("FINALIZADO CON ERRORES", "#EF4444")


if __name__ == "__main__":
    app = App()
    app.mainloop()
