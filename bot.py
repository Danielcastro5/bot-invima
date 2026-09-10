# ==========================================================================
#  AUTOMATIZADOR INVIMA
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
import winreg
import ctypes
from datetime import datetime
import socket
import shutil
import math

# Activar Alta Resolución Nativa en Windows (Evita pixelación y texto borroso por escalado)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Establecer ID de Modelo de Usuario de Aplicación explícito (AppUserModelID)
# Garantiza que Windows vincule permanentemente el icono oficial (.ico) en la barra de tareas y accesos directos
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MCProcesosIntegrales.AutomatizadorINVIMA.App.v1")
except Exception:
    pass

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

PUERTO_CHROME = 9222   # Puerto de depuración de Chrome

VERSION_ACTUAL = "v1.2.1"
URL_VERSION_GITHUB = "https://raw.githubusercontent.com/Danielcastro5/bot-invima/main/version.json"
FIREBASE_DB_URL = "https://bot-invima-licencias-default-rtdb.firebaseio.com"
SECRET_SALT_LICENCIA = "BOT_INVIMA_SECURE_AUTH_SALT_2026_V1"

# Configuración inicial de CustomTkinter (Estilo Ejecutivo MC Procesos Integrales)
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


def obtener_ruta_recurso(nombre_relativo):
    """
    Obtiene la ruta absoluta para un recurso, compatible con desarrollo local y PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    ruta = os.path.join(base_path, nombre_relativo)
    if os.path.exists(ruta):
        return ruta

    if getattr(sys, 'frozen', False):
        ruta_exe = os.path.join(os.path.dirname(sys.executable), nombre_relativo)
        if os.path.exists(ruta_exe):
            return ruta_exe

    return ruta


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
            app.log("❌ No se encontró Google Chrome en las rutas predeterminadas.", "error")
        return False

    # Guardar el perfil permanentemente en AppData\Local (evita llenar el Escritorio o OneDrive de archivos)
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    user_data_dir = os.path.join(local_app_data, "AutomatizadorINVIMA", "chrome_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    # Migración transparente de perfil anterior (ej: si estaba en el Escritorio o en base_dir)
    # para no perder certificados ni inicio de sesión activo en INVIMA
    if not os.path.exists(os.path.join(user_data_dir, "Default")):
        candidatos_previos = [
            os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Escritorio", "chrome_profile_bot"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "chrome_profile_bot"),
            os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), "chrome_profile_bot"),
            r"C:\bot-registro\chrome_profile_bot"
        ]
        for c_prev in candidatos_previos:
            if os.path.exists(os.path.join(c_prev, "Default")):
                try:
                    for item in os.listdir(c_prev):
                        if item in ["lockfile", "SingletonLock", "SingletonCookie", "SingletonSocket"]:
                            continue
                        s = os.path.join(c_prev, item)
                        d = os.path.join(user_data_dir, item)
                        if os.path.isdir(s) and not os.path.exists(d):
                            shutil.copytree(s, d, ignore=shutil.ignore_patterns("*.tmp", "*lock*"))
                        elif os.path.isfile(s) and not os.path.exists(d):
                            shutil.copy2(s, d)
                    break
                except Exception:
                    pass

    # Intentar limpiar perfiles huérfanos del escritorio si ya no están en uso por Chrome
    for r_esc in [
        os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Escritorio", "chrome_profile_bot"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "chrome_profile_bot")
    ]:
        if os.path.exists(r_esc) and not os.path.exists(os.path.join(r_esc, "lockfile")):
            try:
                shutil.rmtree(r_esc, ignore_errors=True)
            except Exception:
                pass

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
#  SISTEMA DE LICENCIAMIENTO SEGURO CON HWID INMUTABLE & FIREBASE
# --------------------------------------------------------------------------
def obtener_hwid():
    """
    Genera un identificador 100% permanente e inalterable del computador (HWID).
    Utiliza el MachineGuid del registro de Windows y el UUID del sistema (Motherboard/BIOS).
    No depende de la red, Wi-Fi, Ethernet, VPN ni conexiones de internet.
    """
    identificadores = []

    # 1. MachineGuid del Registro de Windows (Inmutable por instalación)
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            if machine_guid and str(machine_guid).strip():
                identificadores.append(str(machine_guid).strip())
    except Exception:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ) as key:
                machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if machine_guid and str(machine_guid).strip():
                    identificadores.append(str(machine_guid).strip())
        except Exception:
            pass

    # 2. UUID del Hardware / Placa Base (PowerShell / CIM / WMIC)
    try:
        cmd = 'powershell -NoProfile -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"'
        out = subprocess.check_output(cmd, shell=True, timeout=3).decode().strip()
        if out and len(out) > 8 and "error" not in out.lower():
            identificadores.append(out)
    except Exception:
        try:
            cmd = "wmic csproduct get uuid"
            out = subprocess.check_output(cmd, shell=True, timeout=3).decode().split('\n')
            if len(out) > 1 and out[1].strip():
                identificadores.append(out[1].strip())
        except Exception:
            pass

    # 3. Nombre del Computador
    nombre_pc = os.getenv("COMPUTERNAME", "PC_DEFAULT")
    identificadores.append(nombre_pc)

    cadena_unica = "_".join(identificadores)
    return hashlib.sha256(cadena_unica.encode("utf-8")).hexdigest()[:16].upper()


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
            try:
                os.remove(ruta_legacy)
            except Exception:
                pass
    except Exception:
        pass


def validar_licencia_firebase(clave_licencia):
    """
    Verifica la clave de licencia en Firebase Realtime Database de forma segura.
    Soporta desvinculación remota, anti-duplicación automática y bloqueo por HWID permanente.
    """
    clave = clave_licencia.strip().upper()
    if not clave:
        return False, "Por favor ingresa una clave de licencia."

    hwid = obtener_hwid()
    nombre_pc_actual = os.getenv("COMPUTERNAME", "PC_ACTUAL").strip().upper()
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

        # 1. Si el HWID inmutable ya está registrado en Firebase
        if hwid in equipos:
            val_equipo = equipos[hwid]
            if val_equipo is False or str(val_equipo).lower() == "false":
                eliminar_licencia_local()
                return False, "Este equipo específico ha sido deshabilitado por el administrador."

            # Actualizar nombre si fuera necesario
            if val_equipo != nombre_pc_actual and val_equipo is not True:
                try:
                    url_put = f"{FIREBASE_DB_URL}/licencias/{clave}/equipos/{hwid}.json"
                    req_put = urllib.request.Request(url_put, data=json.dumps(nombre_pc_actual).encode("utf-8"), headers={"Content-Type": "application/json"}, method="PUT")
                    with urllib.request.urlopen(req_put, timeout=5): pass
                except Exception: pass

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

        # 2. Anti-duplicación inteligente:
        #    Si este mismo nombre de computador ya existía bajo una clave vieja generada por el adaptador anterior,
        #    migramos esa clave al HWID inmutable y eliminamos el duplicado anterior sin consumir un nuevo cupo.
        hwid_antiguo_encontrado = None
        for k_old, v_name in equipos.items():
            if str(v_name).strip().upper() == nombre_pc_actual and v_name is not False and str(v_name).lower() != "false":
                hwid_antiguo_encontrado = k_old
                break

        if hwid_antiguo_encontrado:
            # Eliminar el HWID antiguo de Firebase
            try:
                url_del = f"{FIREBASE_DB_URL}/licencias/{clave}/equipos/{hwid_antiguo_encontrado}.json"
                req_del = urllib.request.Request(url_del, headers={"User-Agent": "Mozilla/5.0"}, method="DELETE")
                with urllib.request.urlopen(req_del, timeout=5): pass
            except Exception: pass

            # Registrar el nuevo HWID inmutable
            try:
                url_put = f"{FIREBASE_DB_URL}/licencias/{clave}/equipos/{hwid}.json"
                req_put = urllib.request.Request(url_put, data=json.dumps(nombre_pc_actual).encode("utf-8"), headers={"Content-Type": "application/json"}, method="PUT")
                with urllib.request.urlopen(req_put, timeout=5): pass
            except Exception: pass

            equipos[hwid] = nombre_pc_actual
            if hwid_antiguo_encontrado in equipos:
                del equipos[hwid_antiguo_encontrado]

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

        # 3. Si el HWID NO está en Firebase, pero el PC conservaba una licencia local previa:
        datos_locales = leer_licencia_local()
        if datos_locales and datos_locales.get("clave") == clave:
            eliminar_licencia_local()
            return False, "Este equipo ha sido desvinculado de la licencia por el administrador."

        # 4. Registro de un computador nuevo en la licencia
        equipos_activos = [k for k, v in equipos.items() if v is not False and str(v).lower() != "false"]
        if len(equipos_activos) >= max_equipos:
            return False, f"Límite de dispositivos alcanzado (Máximo {max_equipos} equipo(s) para esta licencia)."

        # Registrar este nuevo equipo (HWID) en Firebase
        url_put = f"{FIREBASE_DB_URL}/licencias/{clave}/equipos/{hwid}.json"
        body = json.dumps(nombre_pc_actual).encode("utf-8")
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

            def _parse_version(v):
                import re
                nums = re.findall(r'\d+', str(v))
                return tuple(int(x) for x in nums) if nums else (0,)

            if _parse_version(version_remota) > _parse_version(VERSION_ACTUAL):
                app.log(f"🔔 ¡NUEVA VERSIÓN DISPONIBLE! ({version_remota})", "warning")
                app.mostrar_modal_actualizacion(data)
            else:
                app.log(f"✅ Bot actualizado a la versión oficial ({VERSION_ACTUAL}).", "info")
        except Exception:
            pass

    t = threading.Thread(target=_tarea, daemon=True)
    t.start()


def ejecutar_actualizacion_automatica(exe_url, config_url, app):
    """
    Descarga la nueva versión y reinicia la aplicación automáticamente de forma robusta.
    """
    ruta_exe_nuevo = None
    try:
        app.log("⬇️ Iniciando descarga de actualización...", "info")
        es_empaquetado = getattr(sys, 'frozen', False)
        if es_empaquetado:
            ruta_exe_actual = sys.executable
            base_dir = os.path.dirname(sys.executable)
            nombre_exe = os.path.basename(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ruta_exe_actual = os.path.join(base_dir, "Automatizador INVIMA.exe")
            nombre_exe = "Automatizador INVIMA.exe"

        ruta_exe_nuevo = os.path.join(base_dir, "Automatizador_INVIMA_nueva.exe")
        ruta_config = os.path.join(base_dir, "config.py")

        # Limpiar cualquier residuo previo si existiera
        if os.path.exists(ruta_exe_nuevo):
            try:
                os.remove(ruta_exe_nuevo)
            except Exception:
                pass

        # 1. Descargar nuevo ejecutable por bloques con reporte de avance
        if exe_url:
            req_exe = urllib.request.Request(exe_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_exe, timeout=600) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0))
                descargados = 0
                ultimo_porcentaje_notificado = -1

                with open(ruta_exe_nuevo, "wb") as out_file:
                    while True:
                        chunk = resp.read(256 * 1024)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        descargados += len(chunk)

                        if total_bytes > 0:
                            porcentaje = int((descargados / total_bytes) * 100)
                            if porcentaje != ultimo_porcentaje_notificado and porcentaje % 15 == 0:
                                ultimo_porcentaje_notificado = porcentaje
                                app.log(f"⬇️ Descargando actualización... ({porcentaje}%)", "info")

        if os.path.exists(ruta_exe_nuevo) and os.path.getsize(ruta_exe_nuevo) < 10 * 1024 * 1024:
            if os.path.exists(ruta_exe_nuevo):
                os.remove(ruta_exe_nuevo)
            raise Exception("El archivo de actualización descargado está incompleto o dañado.")

        # 2. Descargar nuevo config.py si aplica
        if config_url:
            try:
                req_cfg = urllib.request.Request(config_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_cfg, timeout=30) as resp, open(ruta_config, "wb") as out_cfg:
                    out_cfg.write(resp.read())
            except Exception:
                pass

        # 3. En entorno de desarrollo (ejecución desde script .py), no cerramos el editor ni ejecutamos script bat
        if not es_empaquetado:
            app.log("✨ Actualización descargada exitosamente en la carpeta local.", "success")
            app.log("💡 Para probarla como ejecutable, compila el binario localmente.", "info")
            messagebox.showinfo("Actualización Descargada", "La nueva versión se descargó correctamente en la carpeta del proyecto.")
            return

        # 4. Crear script de reemplazo en segundo plano para el cliente empaquetado (.exe)
        pid_actual = os.getpid()
        ruta_bat = os.path.join(base_dir, "actualizar_bot.bat")
        script_bat = f"""@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: 1. Ir a la carpeta del ejecutable
cd /d "{base_dir}"

:: 2. Esperar cierre ordenado y asegurar liberacion de memoria
timeout /t 2 /nobreak > nul
taskkill /F /PID {pid_actual} >nul 2>&1
taskkill /F /IM "{nombre_exe}" >nul 2>&1
taskkill /F /IM "Automatizador INVIMA.exe" >nul 2>&1
taskkill /F /IM "Automatizador_INVIMA.exe" >nul 2>&1

:: 3. Reintentar reemplazo hasta que Windows y OneDrive liberen el bloqueo de archivos
set INTENTOS=0
:BUCLE_REEMPLAZO
set /a INTENTOS+=1
timeout /t 1 /nobreak > nul
if exist "{ruta_exe_nuevo}" (
    move /y "{ruta_exe_nuevo}" "{ruta_exe_actual}" >nul 2>&1
    if errorlevel 1 (
        if !INTENTOS! lss 30 goto BUCLE_REEMPLAZO
    )
)

:: 4. Pausa de seguridad para sincronizacion de sistema de archivos
timeout /t 2 /nobreak > nul

:: 5. Iniciar la version actualizada
if exist "{ruta_exe_actual}" (
    start "" "{ruta_exe_actual}"
)

:: 6. Auto-eliminacion del archivo temporal de actualizacion
timeout /t 1 /nobreak > nul
del "%~f0"
"""
        with open(ruta_bat, "w", encoding="utf-8") as f:
            f.write(script_bat)

        app.log("✨ Descarga completada al 100%. Reiniciando bot...", "success")
        time.sleep(1)

        # 5. Iniciar script y cerrar aplicación actual
        subprocess.Popen(["cmd.exe", "/c", ruta_bat], creationflags=subprocess.CREATE_NO_WINDOW)
        os._exit(0)

    except Exception as e:
        if ruta_exe_nuevo and os.path.exists(ruta_exe_nuevo):
            try:
                os.remove(ruta_exe_nuevo)
            except Exception:
                pass
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
#  Normalización de cadenas (ignora tildes, acentos, mayúsculas y espacios extra)
# --------------------------------------------------------------------------
import unicodedata

def normalizar_texto(texto):
    if not texto:
        return ""
    s = unicodedata.normalize('NFD', str(texto).strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != 'Mn')


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
    
    # Búsqueda flexible de la hoja (exacta, alias o ignorando tildes y mayúsculas)
    hoja_encontrada = None
    candidatos_hoja = [nombre_hoja]
    if "ingrediente" in nombre_hoja.lower() or "composici" in nombre_hoja.lower():
        if "grupo" not in nombre_hoja.lower() and "marco" not in nombre_hoja.lower():
            candidatos_hoja.extend(["Ingredientes", "Composición Ingredientes", "Composicion Ingredientes", "Composición", "Composicion"])

    for cand in candidatos_hoja:
        if cand in libro.sheetnames:
            hoja_encontrada = cand
            break
        norm_cand = normalizar_texto(cand)
        for s in libro.sheetnames:
            if normalizar_texto(s) == norm_cand:
                hoja_encontrada = s
                break
        if hoja_encontrada:
            break

    if not hoja_encontrada:
        app.log(f"❌ ERROR: El Excel seleccionado no contiene la hoja '{nombre_hoja}'.", "error")
        app.log(f"📋 Hojas disponibles en este Excel: {', '.join(libro.sheetnames)}", "warning")
        app.log(f"💡 Asegúrate de que el Excel contenga una pestaña llamada '{nombre_hoja}' (o 'Ingredientes')", "info")
        return None

    hoja = libro[hoja_encontrada]
    crudas = list(hoja.iter_rows(values_only=True))
    if len(crudas) < 2:
        app.log(f"❌ ERROR: La hoja '{hoja_encontrada}' no contiene registros suficientes.", "error")
        return None

    encabezados = [str(c).strip() if c is not None else "" for c in crudas[0]]
    campos_req = proceso_config.get("CAMPOS_CABECERA", []) + proceso_config.get("CAMPOS", [])
    
    # Mapeo de columnas requeridas con soporte de alias y normalización
    mapa_columnas = {}
    faltan = []

    for c in campos_req:
        col_nombre = c["columna"]
        alias_lista = [col_nombre] + c.get("alias", [])
        encontrado_idx = None

        for idx, enc in enumerate(encabezados):
            norm_enc = normalizar_texto(enc)
            for a in alias_lista:
                if enc == a or norm_enc == normalizar_texto(a):
                    encontrado_idx = idx
                    break
            if encontrado_idx is not None:
                break

        if encontrado_idx is not None:
            mapa_columnas[col_nombre] = encontrado_idx
        else:
            faltan.append(col_nombre)

    col_extra = proceso_config.get("COLUMNA_NOMBRE_FORMULA")
    if col_extra:
        encontrado_extra = None
        for idx, enc in enumerate(encabezados):
            if enc == col_extra or normalizar_texto(enc) == normalizar_texto(col_extra) or "formula" in normalizar_texto(enc):
                encontrado_extra = idx
                break
        if encontrado_extra is not None:
            mapa_columnas[col_extra] = encontrado_extra
        elif col_extra not in faltan:
            faltan.append(col_extra)

    if faltan:
        app.log(f"❌ ERROR: Faltan las siguientes columnas en la hoja '{hoja_encontrada}':", "error")
        for c in faltan:
            app.log(f"   • {c}", "error")
        return None

    filas = []
    for i, cruda in enumerate(crudas[1:], start=2): # i representa la línea real en Excel
        if all(v is None for v in cruda):
            continue
        fila = {"__linea_excel__": i}
        for col_nombre, col_idx in mapa_columnas.items():
            v = cruda[col_idx] if col_idx < len(cruda) else None
            fila[col_nombre] = "" if v is None else str(v).strip()
        filas.append(fila)

    app.log(f"✅ Excel validado correctamente para la hoja '{hoja_encontrada}': {len(filas)} filas cargadas.", "success")
    return filas


def hacer_clic_opcion(opcion_locator):
    try:
        opcion_locator.scroll_into_view_if_needed(timeout=1000)
    except Exception:
        pass
    try:
        hijo_txt = opcion_locator.locator(".ant-select-item-option-content")
        if hijo_txt.count() > 0 and hijo_txt.first.is_visible():
            hijo_txt.first.click(force=True, timeout=1500)
            return
    except Exception:
        pass
    try:
        opcion_locator.click(force=True, timeout=1500)
    except Exception:
        try:
            opcion_locator.evaluate("el => el.click()")
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

    try:
        target.fill("")
    except Exception:
        try:
            target.press("Control+a")
            target.press("Backspace")
        except Exception:
            pass

    time.sleep(0.05)

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
    Despliega y selecciona la opción exacta en Ant Design Select.
    Prioriza opciones de texto real sobre códigos internos.
    """
    valor_norm = normalizar_texto(valor)
    valor_str = str(valor).strip()

    # 1. Esperar menú desplegable
    try:
        page.wait_for_selector(".ant-select-dropdown:not(.ant-select-dropdown-hidden)", timeout=1500)
    except Exception:
        pass

    dropdown = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)").last
    opciones = dropdown.locator(".ant-select-item-option:not(.ant-select-item-option-disabled)")
    total = opciones.count()

    if total == 0:
        opciones = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
        total = opciones.count()

    # Log de opciones encontradas para transparencia total
    lista_textos = []
    for k in range(total):
        try:
            t = opciones.nth(k).inner_text().strip()
            if t and t not in lista_textos:
                lista_textos.append(t)
        except Exception:
            pass

    if lista_textos:
        app.log(f"      📋 Opciones en menú ({total}): [{', '.join(lista_textos[:6])}]", "detail")
    else:
        app.log(f"      ℹ️ No se desplegaron opciones en menú para '{valor}'", "detail")

    # Si hay opciones desplegadas
    if total > 0:
        # A) Coincidencia EXACTA DIRECTA (Case-sensitive: 'Envase' == 'Envase', evitando 'envase' y 'envas1')
        for k in range(total):
            try:
                opc = opciones.nth(k)
                txt = opc.inner_text().strip()
                if txt == valor_str:
                    app.log(f"      🎯 Clic en coincidencia EXACTA (Directa): '{txt}'", "detail")
                    hacer_clic_opcion(opc)
                    time.sleep(0.3)
                    return True
            except Exception:
                pass

        # B) Coincidencia EXACTA NORMALIZADA (ej: 'Cartón' vs 'carton', descartando sufijos como carto1)
        for k in range(total):
            try:
                opc = opciones.nth(k)
                txt = opc.inner_text().strip()
                if normalizar_texto(txt) == valor_norm and not (len(txt) > 3 and txt[-1].isdigit()):
                    app.log(f"      🎯 Clic en coincidencia EXACTA (Normalizada): '{txt}'", "detail")
                    hacer_clic_opcion(opc)
                    time.sleep(0.3)
                    return True
            except Exception:
                pass

        # C) Coincidencia PARCIAL (solo opciones reales sin sufijos de código como envas1)
        for k in range(total):
            try:
                opc = opciones.nth(k)
                txt = opc.inner_text().strip()
                txt_n = normalizar_texto(txt)
                if (txt_n.startswith(valor_norm) or valor_norm in txt_n) and not (len(txt) > 3 and txt[-1].isdigit()):
                    app.log(f"      🎯 Clic en coincidencia PARCIAL: '{txt}'", "detail")
                    hacer_clic_opcion(opc)
                    time.sleep(0.3)
                    return True
            except Exception:
                pass

    # D) Fallback con teclado ArrowDown + Enter
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
    VERIFICACIÓN ESTRICTA DEL CAMPO:
    Para autocompletar, exige que .ant-select-selection-item esté visible y activo.
    """
    valor_norm = normalizar_texto(valor)
    col_nombre = campo.get("columna", "")
    tipo_campo = campo.get("tipo", "autocompletar")

    # 1. Buscar etiqueta .ant-select-selection-item dentro del .ant-select MAS CERCANO a este input
    try:
        contenedor_select = target.locator("xpath=ancestor::div[contains(@class,'ant-select')][1]")
        if contenedor_select.count() > 0:
            selection_item = contenedor_select.locator(".ant-select-selection-item").first
            if selection_item.count() > 0 and selection_item.is_visible():
                texto_item = selection_item.inner_text().strip()
                if texto_item:
                    app.log(f"      ✅ Selección confirmada en portal (.ant-select-selection-item): '{texto_item}'", "detail")
                    return True
    except Exception:
        pass

    # 2. Si es campo de tipo 'texto', verificar target.input_value()
    if tipo_campo == "texto":
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
    valor_norm = normalizar_texto(valor)

    # Identificar el modal activo superior si existe
    modal_activo = page.locator(".ant-modal:not([style*='display: none'])")
    if modal_activo.count() > 0:
        modal_top = modal_activo.last
        target = modal_top.locator(selector).last
        if target.count() == 0:
            target = modal_top.locator(f".ant-form-item:has-text('{campo['columna']}') input").last
        if target.count() == 0:
            target = page.locator(selector).last
    else:
        target = page.locator(selector).last
        if target.count() == 0:
            target = page.locator(selector).first

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
                target.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass
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


def esperar_seleccion_manual_funcion(page, campo, app):
    """
    Pausa interactiva para el campo 'Función':
    Abre el menú desplegable en el portal, inyecta un banner flotante en Chrome
    con opciones para 'Continuar' o 'Descartar', y espera la decisión del usuario.
    Si el usuario presiona 'Detener' en el bot, NO salta la función ni guarda datos corruptos;
    espera a que el usuario decida guardar este último ingrediente o descartarlo.
    """
    app.log("🖐️ [MODO MANUAL] Selecciona la(s) función(es) para este ingrediente en el portal de INVIMA.", "warning")
    app.log("👉 Pulsa 'Continuar' cuando termines, o 'Descartar' si deseas cancelar este ingrediente.", "info")

    modal_activo = page.locator(".ant-modal:not([style*='display: none'])")
    modal_top = modal_activo.last if modal_activo.count() > 0 else page

    dropdown_sel = ".ant-select-dropdown:not(.ant-select-dropdown-hidden)"
    col_nombre = campo.get("columna", "Función")

    try:
        if page.locator(dropdown_sel).count() == 0:
            selector_box = modal_top.locator(f".ant-form-item:has-text('Función') .ant-select-selector, .ant-form-item:has-text('Funcion') .ant-select-selector, .ant-form-item:has-text('{col_nombre}') .ant-select-selector").last
            if selector_box.count() > 0:
                selector_box.click(force=True, timeout=1200)
            else:
                target = modal_top.locator(campo.get("selector", "")).last
                if target.count() > 0:
                    target.click(force=True, timeout=1200)
    except Exception:
        pass

    # Inyectar banner flotante moderno en Chrome con dos opciones claras
    js_inyectar_banner = """
    (() => {
        let banner = document.getElementById('invima_banner_manual_funcion');
        if (banner) banner.remove();

        window.__invima_continuar_manual = false;
        window.__invima_cancelar_manual = false;

        banner = document.createElement('div');
        banner.id = 'invima_banner_manual_funcion';
        banner.style.position = 'fixed';
        banner.style.top = '16px';
        banner.style.right = '24px';
        banner.style.zIndex = '9999999';
        banner.style.backgroundColor = '#1E1B4B';
        banner.style.color = '#FFFFFF';
        banner.style.padding = '14px 20px';
        banner.style.borderRadius = '12px';
        banner.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3)';
        banner.style.fontFamily = 'Segoe UI, system-ui, sans-serif';
        banner.style.display = 'flex';
        banner.style.alignItems = 'center';
        banner.style.gap = '14px';
        banner.style.border = '2px solid #7D51E9';

        banner.innerHTML = `
            <div style="display: flex; flex-direction: column;">
                <span id="txt_banner_manual_titulo" style="font-weight: 700; font-size: 13px; color: #F8FAFC;">🖐️ Selección manual de Función</span>
                <span id="txt_banner_manual_desc" style="font-size: 11px; color: #CBD5E1;">Elige la(s) función(es) en la lista del portal:</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <button id="btn_invima_continuar_manual" style="
                    background: linear-gradient(135deg, #0DBE8A, #059669);
                    color: #FFFFFF;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 12px;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(13, 190, 138, 0.35);
                ">
                    Continuar ▶
                </button>
                <button id="btn_invima_cancelar_manual" style="
                    background: #EF4444;
                    color: #FFFFFF;
                    border: none;
                    padding: 8px 14px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 12px;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25);
                ">
                    🛑 Descartar
                </button>
            </div>
        `;

        document.body.appendChild(banner);

        const btnCont = document.getElementById('btn_invima_continuar_manual');
        if (btnCont) {
            btnCont.onclick = () => {
                window.__invima_continuar_manual = true;
                banner.style.opacity = '0.5';
                btnCont.innerText = 'Guardando...';
            };
        }

        const btnCanc = document.getElementById('btn_invima_cancelar_manual');
        if (btnCanc) {
            btnCanc.onclick = () => {
                window.__invima_cancelar_manual = true;
                banner.style.opacity = '0.5';
                btnCanc.innerText = 'Descartando...';
            };
        }
    })();
    """

    try:
        page.evaluate(js_inyectar_banner)
    except Exception as e:
        app.log(f"   ℹ️ Interfaz interactiva: {e}", "detail")

    # Notificar a la GUI del bot
    app.confirmar_manual_listo = False
    app.cancelar_ingrediente_actual = False
    if hasattr(app, "activar_espera_manual_ui"):
        app.activar_espera_manual_ui(True)

    banner_aviso_detener_puesto = False

    # Ciclo de espera activo: NO sale a ciegas si app.debe_detener es True, espera decisión del usuario
    while True:
        # 1. Comprobar decisiones desde Chrome
        try:
            if page.evaluate("() => window.__invima_cancelar_manual === true"):
                app.cancelar_ingrediente_actual = True
                app.debe_detener = True
                break
            if page.evaluate("() => window.__invima_continuar_manual === true"):
                break
        except Exception:
            pass

        # 2. Comprobar decisiones desde la GUI del Bot
        if getattr(app, "cancelar_ingrediente_actual", False):
            break
        if getattr(app, "confirmar_manual_listo", False):
            break

        # 3. Si el usuario pulsó 'Detener' en los botones principales del bot, avisar en Chrome
        if app.debe_detener and not banner_aviso_detener_puesto:
            banner_aviso_detener_puesto = True
            try:
                page.evaluate("""() => {
                    const b = document.getElementById('invima_banner_manual_funcion');
                    if (b) {
                        b.style.borderColor = '#EF4444';
                        const desc = document.getElementById('txt_banner_manual_desc');
                        if (desc) desc.innerText = '🛑 Detención solicitada: Pulsa Continuar para guardar este ingrediente, o Descartar para salir.';
                    }
                }""")
            except Exception:
                pass

        time.sleep(0.2)

    # Limpieza del banner flotante en Chrome
    try:
        page.evaluate("() => { const b = document.getElementById('invima_banner_manual_funcion'); if (b) b.remove(); }")
    except Exception:
        pass

    # Desactivar botón de espera en la GUI del bot
    if hasattr(app, "activar_espera_manual_ui"):
        app.activar_espera_manual_ui(False)

    if getattr(app, "cancelar_ingrediente_actual", False):
        app.log("🛑 Ingrediente actual descartado por el usuario a petición manual.", "warning")
        try:
            page.keyboard.press("Escape")
            time.sleep(0.3)
        except Exception:
            pass
        return

    # Cerrar el menú desplegable en Chrome con Escape
    try:
        page.keyboard.press("Escape")
        time.sleep(0.2)
    except Exception:
        pass

    # Contar funciones seleccionadas visualmente
    try:
        cant_sel = modal_top.locator(f".ant-form-item:has-text('Función') .ant-select-selection-item, .ant-form-item:has-text('Funcion') .ant-select-selection-item, .ant-form-item:has-text('{col_nombre}') .ant-select-selection-item").count()
        if cant_sel > 0:
            app.log(f"   ✅ Se registraron {cant_sel} función(es) seleccionada(s) manualmente.", "success")
        else:
            app.log("   ℹ️ Continuando con selección directa en portal.", "detail")
    except Exception:
        pass


def llenar_multiselect(page, campo, valor, timeout_ms, app):
    """
    Selección automática directa para el campo 'Función' (Multiselect):
    Lee el Excel y busca directamente la coincidencia en la lista desplegable sin escribir
    caracteres en el campo. Si una función no existe en el portal, lanza un error para que
    el sistema de reintentos vuelva a intentarlo en lugar de continuar con datos incompletos.
    """
    import re
    items = [x.strip() for x in re.split(r'[,;|\n]', str(valor)) if x.strip()]
    if not items:
        return

    modal_activo = page.locator(".ant-modal:not([style*='display: none'])")
    modal_top = modal_activo.last if modal_activo.count() > 0 else page

    dropdown_sel = ".ant-select-dropdown:not(.ant-select-dropdown-hidden)"
    col_nombre = campo.get("columna", "Función")

    selector_box_candidatos = [
        modal_top.locator(".ant-form-item:has-text('Función') .ant-select-selector").last,
        modal_top.locator(".ant-form-item:has-text('Funcion') .ant-select-selector").last,
        modal_top.locator(f".ant-form-item:has-text('{col_nombre}') .ant-select-selector").last,
        modal_top.locator(".ant-form-item:has-text('Función') .ant-select-selection-overflow").last,
        modal_top.locator(".ant-form-item:has-text('Funcion') .ant-select-selection-overflow").last,
        modal_top.locator(".ant-modal-body .ant-select-multiple .ant-select-selector").last,
        modal_top.locator(".ant-select-multiple .ant-select-selector").last,
        page.locator(".ant-modal:not([style*='display: none']) .ant-form-item:has-text('Función') .ant-select-selector").last,
        page.locator(".ant-modal:not([style*='display: none']) .ant-form-item:has-text('Funcion') .ant-select-selector").last,
        page.locator(".ant-modal:not([style*='display: none']) .ant-select-multiple .ant-select-selector").last,
    ]

    menu_abierto = False
    for box in selector_box_candidatos:
        if box is None:
            continue
        try:
            if box.count() > 0:
                box.scroll_into_view_if_needed(timeout=500)
                box.evaluate("el => el.click()")
                time.sleep(0.3)
                if page.locator(dropdown_sel).count() > 0:
                    menu_abierto = True
                    break
                box.click(force=True, timeout=1000)
                time.sleep(0.3)
                if page.locator(dropdown_sel).count() > 0:
                    menu_abierto = True
                    break
        except Exception:
            continue

    if not menu_abierto or page.locator(dropdown_sel).count() == 0:
        for box in selector_box_candidatos:
            try:
                if box and box.count() > 0:
                    box.click(force=True, timeout=600)
                    time.sleep(0.2)
                    page.keyboard.press("ArrowDown")
                    time.sleep(0.3)
                    if page.locator(dropdown_sel).count() > 0:
                        menu_abierto = True
                        break
            except Exception:
                pass

    if page.locator(dropdown_sel).count() == 0:
        raise ValueError(f"No se pudo abrir el menú desplegable para el campo '{col_nombre}'")

    dropdown_activo = page.locator(dropdown_sel).last

    for idx, item in enumerate(items):
        item_norm = normalizar_texto(item)
        app.log(f"      ➔ Seleccionando función ({idx+1}/{len(items)}): '{item}'", "detail")

        # Asegurar que el menú siga visible
        if page.locator(dropdown_sel).count() == 0:
            for box in selector_box_candidatos:
                if box is None:
                    continue
                try:
                    if box.count() > 0:
                        box.evaluate("el => el.click()")
                        time.sleep(0.3)
                        if page.locator(dropdown_sel).count() > 0:
                            break
                except Exception:
                    pass
            dropdown_activo = page.locator(dropdown_sel).last

        encontrado = False

        # 1. Búsqueda en opciones visibles actuales (búsqueda directa exacta y semejante sin escribir)
        opciones = dropdown_activo.locator(".ant-select-item-option, .ant-select-item-option-content")
        cnt = opciones.count()

        for k in range(cnt):
            opt = opciones.nth(k)
            try:
                txt = opt.inner_text().strip()
                t_norm = normalizar_texto(txt)
                if t_norm == item_norm or (len(item_norm) >= 4 and (t_norm.startswith(item_norm) or item_norm in t_norm or t_norm in item_norm)):
                    # Comprobar si ya está seleccionada para no desmarcarla
                    clase = opt.get_attribute("class") or ""
                    aria_sel = opt.get_attribute("aria-selected") or ""
                    if aria_sel == "true" or "ant-select-item-option-selected" in clase:
                        app.log(f"      ℹ️ Función '{txt}' ya se encuentra seleccionada.", "detail")
                        encontrado = True
                        break
                    app.log(f"      🎯 Seleccionada función directa: '{txt}'", "detail")
                    hacer_clic_opcion(opt)
                    encontrado = True
                    time.sleep(0.25)
                    break
            except Exception:
                continue

        # 2. Si no se encontró en la primera vista, realizar scroll en la lista virtual para inspeccionar las demás
        if not encontrado:
            holder = dropdown_activo.locator(".rc-virtual-list-holder").first
            if holder.count() > 0:
                try:
                    holder.evaluate("el => { el.scrollTop = 0; el.dispatchEvent(new Event('scroll')); }")
                    time.sleep(0.06)

                    max_scrolls = 18
                    for s_step in range(max_scrolls):
                        opcs_scroll = dropdown_activo.locator(".ant-select-item-option, .ant-select-item-option-content")
                        for m in range(opcs_scroll.count()):
                            opt_m = opcs_scroll.nth(m)
                            try:
                                txt_m = opt_m.inner_text().strip()
                                tm_norm = normalizar_texto(txt_m)
                                if tm_norm == item_norm or (len(item_norm) >= 4 and (tm_norm.startswith(item_norm) or item_norm in tm_norm or tm_norm in item_norm)):
                                    clase = opt_m.get_attribute("class") or ""
                                    aria_sel = opt_m.get_attribute("aria-selected") or ""
                                    if aria_sel == "true" or "ant-select-item-option-selected" in clase:
                                        app.log(f"      ℹ️ Función '{txt_m}' ya se encuentra seleccionada.", "detail")
                                        encontrado = True
                                        break
                                    app.log(f"      🎯 Seleccionada función tras búsqueda en lista: '{txt_m}'", "detail")
                                    hacer_clic_opcion(opt_m)
                                    encontrado = True
                                    time.sleep(0.25)
                                    break
                            except Exception:
                                continue

                        if encontrado:
                            break

                        # Scroll siguiente paso
                        holder.evaluate("el => { el.scrollTop += 180; el.dispatchEvent(new Event('scroll')); }")
                        time.sleep(0.08)

                except Exception as e_scroll:
                    app.log(f"      ℹ️ Desplazamiento en lista: {e_scroll}", "detail")

        # 3. Si definitivamente no se encontró, LANZAR ERROR para que el sistema de reintentos vuelva a probar
        if not encontrado:
            raise ValueError(f"No se encontró la función '{item}' en la lista desplegable de opciones del portal INVIMA.")

    # Cerrar menú desplegable al finalizar todas las funciones
    try:
        page.keyboard.press("Escape")
        time.sleep(0.2)
    except Exception:
        pass


def llenar_select(page, campo, valor, timeout_ms, app):
    valor_norm = normalizar_texto(valor)
    col_nombre = campo.get("columna", "")
    selector_config = campo.get("selector", "")

    modal_activo = page.locator(".ant-modal:not([style*='display: none'])")
    if modal_activo.count() > 0:
        modal_top = modal_activo.last
    else:
        modal_top = page

    targets_posibles = [
        modal_top.locator(selector_config).last if selector_config else None,
        modal_top.locator(f".ant-form-item:has-text('{col_nombre}') .ant-select-selector").last,
        modal_top.locator(f".ant-form-item:has-text('{col_nombre}') input").last,
        modal_top.locator(f".ant-form-item:has-text('{col_nombre}')").last,
        page.locator(selector_config).last if selector_config else None,
        page.locator(selector_config).first if selector_config else None,
    ]

    dropdown_sel = ".ant-select-dropdown:not(.ant-select-dropdown-hidden)"

    menu_abierto = False
    for target in targets_posibles:
        if target is None:
            continue
        try:
            if target.count() > 0:
                target.scroll_into_view_if_needed(timeout=400)
                target.click(force=True, timeout=1000)
                time.sleep(0.25)
                if page.locator(dropdown_sel).count() > 0:
                    menu_abierto = True
                    break
        except Exception:
            continue

    if not menu_abierto:
        try:
            modal_top.locator(f".ant-form-item:has-text('{col_nombre}')").last.click(force=True, timeout=1000)
            time.sleep(0.25)
        except Exception:
            pass

    page.wait_for_selector(dropdown_sel, timeout=min(4000, timeout_ms))
    
    dropdown_activo = page.locator(dropdown_sel).last
    opciones = dropdown_activo.locator(".ant-select-item-option, div[role='option'], .ant-select-item-option-content")
    total_opciones = opciones.count()

    if total_opciones == 0:
        opciones = page.locator(dropdown_sel + " .ant-select-item-option")
        total_opciones = opciones.count()

    if total_opciones == 0:
        raise ValueError(f"No se desplegaron opciones en el menú para '{valor}'")

    app.log(f"      🔍 Se encontraron {total_opciones} opciones en el menú desplegable para '{valor}'.", "detail")

    for k in range(total_opciones):
        txt_opcion = opciones.nth(k).inner_text()
        txt_norm = normalizar_texto(txt_opcion)
        if txt_norm == valor_norm:
            app.log(f"      🎯 Seleccionada opción '{txt_opcion.strip()}' (para '{valor}')", "detail")
            hacer_clic_opcion(opciones.nth(k))
            time.sleep(0.2)
            return

    for k in range(total_opciones):
        txt_opcion = opciones.nth(k).inner_text()
        txt_norm = normalizar_texto(txt_opcion)
        if txt_norm.startswith(valor_norm) or valor_norm in txt_norm:
            app.log(f"      🎯 Seleccionada opción semejante '{txt_opcion.strip()}' (para '{valor}')", "detail")
            hacer_clic_opcion(opciones.nth(k))
            time.sleep(0.2)
            return

    # 3. Coincidencia por palabras clave (tolerancia plural/singular, ej: 'GRUPO COLORES' vs 'GRUPOS COLORES')
    palabras_val = [p for p in valor_norm.split() if len(p) > 2]
    if palabras_val:
        for k in range(total_opciones):
            txt_opcion = opciones.nth(k).inner_text().strip()
            txt_norm = normalizar_texto(txt_opcion)
            palabras_opt = txt_norm.split()
            if all(any(pv in po or po in pv for po in palabras_opt) for pv in palabras_val):
                app.log(f"      🎯 Seleccionada opción coincidente '{txt_opcion}' (para '{valor}')", "detail")
                hacer_clic_opcion(opciones.nth(k))
                time.sleep(0.2)
                return

    try:
        opc_has = dropdown_activo.locator(f":has-text('{valor}')").last
        if opc_has.count() > 0 and opc_has.is_visible():
            hacer_clic_opcion(opc_has)
            time.sleep(0.2)
            return
    except Exception:
        pass

    # Soporte para listas virtuales con muchas opciones (ej: listas de grupos > 10 elementos)
    holder = dropdown_activo.locator(".rc-virtual-list-holder")
    if holder.count() > 0:
        try:
            scroll_h = holder.evaluate("el => el.scrollHeight")
            client_h = holder.evaluate("el => el.clientHeight") or 256
            step = 220
            app.log(f"      📜 Buscando '{valor}' en lista desplegable amplia...", "detail")
            for pos in range(0, scroll_h + step, step):
                holder.evaluate(f"""el => {{
                    el.scrollTop = {pos};
                    el.dispatchEvent(new Event('scroll'));
                }}""")
                time.sleep(0.03)
                items_js = dropdown_activo.evaluate("""
                    el => Array.from(el.querySelectorAll('.ant-select-item-option')).map((node, i) => ({
                        i: i,
                        text: (node.innerText || '').trim()
                    }))
                """)
                for item in items_js:
                    txt_opt = item["text"]
                    txt_opt_norm = normalizar_texto(txt_opt)
                    opt_elem = dropdown_activo.locator(".ant-select-item-option").nth(item["i"])
                    if txt_opt_norm == valor_norm:
                        app.log(f"      🎯 Seleccionada opción '{txt_opt}' (para '{valor}')", "detail")
                        hacer_clic_opcion(opt_elem)
                        time.sleep(0.2)
                        return
                    if (txt_opt_norm.startswith(valor_norm) or valor_norm in txt_opt_norm) and not (len(txt_opt) > 3 and txt_opt[-1].isdigit()):
                        app.log(f"      🎯 Seleccionada opción semejante '{txt_opt}' (para '{valor}')", "detail")
                        hacer_clic_opcion(opt_elem)
                        time.sleep(0.2)
                        return
                    if palabras_val and all(any(pv in po or po in pv for po in txt_opt_norm.split()) for pv in palabras_val):
                        app.log(f"      🎯 Seleccionada opción coincidente '{txt_opt}' (para '{valor}') tras desplazamiento", "detail")
                        hacer_clic_opcion(opt_elem)
                        time.sleep(0.2)
                        return
        except Exception as e_scroll:
            app.log(f"      ⚠️ Detalle en búsqueda de lista: {e_scroll}", "detail")

    # Fallback si el selector permite o requiere búsqueda por tipeo (showSearch)
    try:
        search_inp = modal_top.locator(".ant-select-focused input, .ant-select-open input, .ant-select-selection-search input").last
        if search_inp.count() > 0 and search_inp.is_visible():
            search_inp.fill("")
            time.sleep(0.05)
            search_inp.type(str(valor), delay=40)
            time.sleep(0.4)
            opcs_filtradas = dropdown_activo.locator(".ant-select-item-option:not(.ant-select-item-option-disabled)")
            if opcs_filtradas.count() > 0:
                for idx_f in range(opcs_filtradas.count()):
                    txt_f = opcs_filtradas.nth(idx_f).inner_text().strip()
                    if normalizar_texto(txt_f) == valor_norm or valor_norm in normalizar_texto(txt_f):
                        app.log(f"      🎯 Seleccionada opción filtrada por búsqueda '{txt_f}' (para '{valor}')", "detail")
                        hacer_clic_opcion(opcs_filtradas.nth(idx_f))
                        time.sleep(0.2)
                        return
                hacer_clic_opcion(opcs_filtradas.first)
                time.sleep(0.2)
                return
    except Exception:
        pass

    raise ValueError(f"La opción '{valor}' no se encuentra en la lista del menú activo")


def llenar_switch(page, campo, valor, app):
    modal_activo = page.locator(".ant-modal:not([style*='display: none'])")
    if modal_activo.count() > 0:
        modal_top = modal_activo.last
        target = modal_top.locator(campo["selector"]).last
        if target.count() == 0:
            target = modal_top.locator("#isNanomaterial, button#isNanomaterial, button.ant-switch").last
    else:
        target = page.locator(campo["selector"]).last
        if target.count() == 0:
            target = page.locator("#isNanomaterial, button#isNanomaterial, .ant-modal-body button.ant-switch, button.ant-switch").last

    if target.count() == 0:
        app.log(f"   ℹ️ Casilla/interruptor '{campo['columna']}' no presente en este formulario, omitiendo...", "detail")
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
            time.sleep(0.2)
        elif not deseado_si and esta_activo:
            app.log(f"   🔘 Desactivando interruptor '{campo['columna']}' (No)", "detail")
            try:
                target.click(force=True)
            except Exception:
                target.evaluate("el => el.click()")
            time.sleep(0.2)
    except Exception as e:
        app.log(f"   ⚠️ No se pudo cambiar el interruptor '{campo['columna']}': {e}", "warning")


def _seleccionar_primera_opcion_listado_referencia(page, campo, app, timeout_ms=6000):
    # 1. Obtener el modal activo superior
    modal_activo = page.locator(".ant-modal:not([style*='display: none'])")
    modal_top = modal_activo.last if modal_activo.count() > 0 else page

    # 2. Localizadores específicos del input de Listado de referencia
    candidatos = [
        modal_top.locator(".ant-form-item:has-text('Listado') input").last,
        modal_top.locator(".ant-form-item:has-text('referencia') input").last,
        modal_top.locator(".ant-form-item:has-text('Referencia') input").last,
        modal_top.locator("form > div > div:nth-child(4) input").last,
        modal_top.locator("#referenceList, input[id*='reference'], input[id*='Reference']").last,
        modal_top.locator(".ant-form-item:has-text('Listado') .ant-select-selector").last,
        modal_top.locator(".ant-form-item:has-text('referencia') .ant-select-selector").last,
        modal_top.locator("form > div > div:nth-child(4) .ant-select-selector").last,
        page.locator(".ant-modal-body .ant-form-item:has-text('Listado') input").last,
        page.locator(campo.get("selector", "")).last,
    ]

    target = None
    for cand in candidatos:
        try:
            if cand.count() > 0:
                target = cand
                break
        except Exception:
            continue

    if not target or target.count() == 0:
        app.log("   ⚠️ No se encontró el campo 'Listado de referencia' en el formulario activo.", "warning")
        raise Exception("El campo obligatorio 'Listado de referencia' no se encontró en el modal actual.")

    # Si el target no es input directo, buscar su input interno
    try:
        if target.evaluate("el => el.tagName.toLowerCase()") != "input":
            inp_hijo = target.locator("input").first
            if inp_hijo.count() > 0:
                target = inp_hijo
    except Exception:
        pass

    app.log("   ➔ Listado de referencia: (Vacío en Excel -> Disparando búsqueda y seleccionando primera opción)...", "detail")

    # Función auxiliar para hacer clic JavaScript en la primera opción visible del dropdown
    def intentar_clic_js():
        return page.evaluate("""() => {
            const dropdowns = Array.from(document.querySelectorAll('.ant-select-dropdown')).filter(d => {
                const style = window.getComputedStyle(d);
                return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
            });
            if (dropdowns.length === 0) return null;
            const activeDd = dropdowns[dropdowns.length - 1];
            const opt = activeDd.querySelector('.ant-select-item-option');
            if (opt) {
                const text = (opt.innerText || opt.textContent || '').trim();
                opt.scrollIntoView();
                const content = opt.querySelector('.ant-select-item-option-content') || opt;
                content.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                content.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                content.click();
                return text;
            }
            return null;
        }""")

    # 3. Primer intento: Clic en el campo y flecha abajo
    try:
        target.scroll_into_view_if_needed(timeout=800)
        target.click(force=True, timeout=1000)
        time.sleep(0.3)
        page.keyboard.press("ArrowDown")
        time.sleep(0.3)
        res_js = intentar_clic_js()
        if res_js:
            app.log(f"      🎯 Seleccionada opción de referencia: '{res_js}'", "detail")
            time.sleep(0.6)
            return True
    except Exception:
        pass

    # 4. Segundo intento: Tipear letras clave para disparar la consulta al catálogo
    terminos = ["a", "d", "c", "i", "e", "CosIng", " "]
    for termino in terminos:
        try:
            target.click(force=True, timeout=1000)
            time.sleep(0.1)
            target.fill("")
            time.sleep(0.1)
            target.type(termino, delay=60)
            time.sleep(0.6)

            # Apenas escribe, chequear si el dropdown se abrió y hacer clic JS
            for _ in range(5):
                res_js = intentar_clic_js()
                if res_js:
                    app.log(f"      🎯 Seleccionada opción de referencia: '{res_js}'", "detail")
                    time.sleep(0.8)
                    return True
                time.sleep(0.3)

            # Si no hizo clic JS, probar inmediatamente ArrowDown y Enter sin volver a clickear el input
            page.keyboard.press("ArrowDown")
            time.sleep(0.2)
            page.keyboard.press("Enter")
            time.sleep(0.6)

            # Verificar si se seleccionó algo en el input
            val_input = target.evaluate("el => el.value") or ""
            if val_input and val_input != termino:
                app.log(f"      🎯 Opción confirmada por teclado: '{val_input}'", "detail")
                time.sleep(0.4)
                return True
        except Exception:
            continue

    # 5. Si ninguna búsqueda funcionó, verificar si hay opciones visibles y cliquearlas con Playwright
    try:
        opciones_visibles = page.locator(".ant-select-dropdown:visible .ant-select-item-option:visible, .ant-select-dropdown:visible .ant-select-item-option-content:visible")
        if opciones_visibles.count() > 0:
            txt_opc = opciones_visibles.first.inner_text().strip()
            app.log(f"      🎯 Clic Playwright en opción visible: '{txt_opc}'", "detail")
            opciones_visibles.first.click(force=True)
            time.sleep(0.8)
            return True
    except Exception:
        pass

    raise Exception("El campo 'Listado de referencia' es obligatorio y no se pudo seleccionar ninguna opción de la lista.")


def llenar_campo_composicion(page, campo, fila, app, cfg):
    col_nombre = campo["columna"]
    valor = fila.get(col_nombre, "")
    if not valor:
        for a in campo.get("alias", []):
            if a in fila and fila[a]:
                valor = fila[a]
                break

    es_listado_ref = "listado" in col_nombre.lower() or "referencia" in col_nombre.lower()
    timeout_ms = getattr(cfg, "TIMEOUT_SEGUNDOS", 15) * 1000

    tipo_fila = normalizar_texto(fila.get("Tipo") or fila.get("tipo") or "")
    col_norm = normalizar_texto(col_nombre)

    if getattr(app, "cancelar_ingrediente_actual", False):
        return

    # Si la fila es de Tipo Mezcla, ignorar campos que no aplican a mezclas en el portal
    if tipo_fila == "mezcla":
        if "nanomaterial" in col_norm or "particula" in col_norm or "listado" in col_norm or "referencia" in col_norm or "funcion" in col_norm:
            return

    # Detección y manejo especializado del campo Función (Manual o Automático)
    es_campo_funcion = ("funcion" in col_norm) or (campo.get("tipo") == "multiselect")
    if es_campo_funcion and tipo_fila != "mezcla":
        modo_manual = getattr(app, "modo_manual_funcion", False)
        if modo_manual:
            esperar_seleccion_manual_funcion(page, campo, app)
            return
        else:
            if not valor or str(valor).strip() == "":
                app.log(f"   ℹ️ Campo '{col_nombre}' vacío en Excel para este registro.", "detail")
                return
            llenar_multiselect(page, campo, valor, timeout_ms, app)
            return

    if not valor or str(valor).strip() == "":
        if es_listado_ref and tipo_fila != "mezcla":
            _seleccionar_primera_opcion_listado_referencia(page, campo, app, timeout_ms)
        return

    # Buscar target en el modal activo superior
    modal_activo = page.locator(".ant-modal:not([style*='display: none'])")
    if modal_activo.count() > 0:
        modal_top = modal_activo.last
        target = modal_top.locator(campo["selector"]).last
        if target.count() == 0:
            target = modal_top.locator(f".ant-form-item:has-text('{col_nombre}') input, .ant-form-item:has-text('{col_nombre}') textarea").last
        if target.count() == 0:
            target = modal_top.locator(f".ant-form-item:has-text('{col_nombre}') .ant-select-selector").last
    else:
        target = page.locator(campo["selector"]).last

    if target.count() == 0:
        target = page.locator(campo["selector"]).first

    if target.count() == 0:
        app.log(f"   ℹ️ Campo '{campo['columna']}' no visible/encontrado, omitiendo...", "info")
        return

    # Esperar si el elemento está deshabilitado
    try:
        if target.is_disabled(timeout=200):
            app.log(f"   ⏳ Esperando a que el portal desbloquee '{campo['columna']}'...", "detail")
            page.wait_for_function("el => !el.disabled", arg=target.element_handle(), timeout=1000)
    except Exception:
        pass

    app.log(f"   ➔ {campo['columna']}: '{valor}'", "detail")

    try:
        if campo["tipo"] == "texto":
            try:
                tag_name = target.evaluate("el => el.tagName.toLowerCase()")
            except Exception:
                tag_name = "input"
            if tag_name not in ["input", "textarea"]:
                input_child = target.locator("input, textarea").first
                if input_child.count() > 0:
                    target = input_child
            target.fill(str(valor))
            time.sleep(0.1)
        elif campo["tipo"] == "select":
            llenar_select(page, campo, valor, timeout_ms, app)
        elif campo["tipo"] == "autocompletar":
            es_campo_ing_mezcla = "mezcla" in col_norm or "ingrediente" in col_norm
            es_campo_grupo = "grupo" in col_norm
            if tipo_fila == "mezcla" and es_campo_ing_mezcla:
                app.log(f"   ℹ️ Modo Mezcla: seleccionando '{valor}' directamente de la lista desplegable sin escribir...", "detail")
                campo_mezcla = dict(campo)
                campo_mezcla["tipo"] = "select"
                campo_mezcla["selector"] = ".ant-select:has(#referenceMixtureId) .ant-select-selector, .ant-form-item:has(#referenceMixtureId) .ant-select-selector"
                llenar_select(page, campo_mezcla, valor, timeout_ms, app)
            elif es_campo_grupo:
                app.log(f"   ℹ️ Campo de grupo: seleccionando '{valor}' directamente de la lista desplegable...", "detail")
                campo_grp = dict(campo)
                campo_grp["tipo"] = "select"
                campo_grp["selector"] = r".ant-modal:not([style*='display: none']) .ant-form-item:has-text('Grupo') .ant-select-selector, .ant-modal:not([style*='display: none']) form > div > div:nth-child(1) .ant-select-selector, " + campo.get("selector", "")
                llenar_select(page, campo_grp, valor, timeout_ms, app)
            else:
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
                f.write(f"📍 LÍNEA EN EXCEL #{err.get('linea_excel', '-')}\n")
                f.write(f"   • Registro N°: {err.get('numero_registro', '-')}\n")
                f.write(f"   • Columna Afectada: {err.get('columna', err.get('columna_afectada', '-'))}\n")
                f.write(f"   • Valor Buscado: {err.get('valor', err.get('valor_excel', '-'))}\n")
                f.write(f"   • Razón del Error: {err.get('detalle', err.get('motivo', '-'))}\n")
                f.write(f"   • Intentos Realizados: {err.get('intentos', 3)}\n")
                f.write("-" * 65 + "\n\n")

        return ruta_txt
    except Exception as e:
        print(f"Error escribiendo reporte de errores: {e}")
        return None


# --------------------------------------------------------------------------
#  Manejador Especializado para Fórmula Marco (2 Niveles: Fórmula e Ingredientes)
# --------------------------------------------------------------------------
def ejecutar_proceso_formula_marco(page, proceso_cfg, filas, app, cfg, timeout_ms, ruta_excel):
    from itertools import groupby

    col_nombre_formula = proceso_cfg.get("COLUMNA_NOMBRE_FORMULA", "Nombre de la fórmula marco")
    selector_abrir_formula = proceso_cfg.get("BOTON_ABRIR_MODAL", "")
    selector_modal_formula = proceso_cfg.get("SELECTOR_MODAL_PRINCIPAL", ".ant-modal-wrap, .ant-modal-content")
    selector_campo_nombre = proceso_cfg.get("SELECTOR_CAMPO_NOMBRE_FORMULA", ".ant-modal-body form input, .ant-modal-body input")
    selector_anadir_ing = proceso_cfg.get("BOTON_ANADIR_INGREDIENTE", "button:has-text('Añadir ingrediente'), button:has-text('Agregar ingrediente')")
    selector_modal_ing = proceso_cfg.get("SELECTOR_MODAL_INGREDIENTE", ".ant-modal-wrap, .ant-modal-content")
    selector_guardar_ing = proceso_cfg.get("BOTON_GUARDAR_INGREDIENTE", ".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar')")
    selector_guardar_formula = proceso_cfg.get("BOTON_GUARDAR_FORMULA", ".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar')")
    campos_ingrediente = proceso_cfg.get("CAMPOS", [])

    # Detectar el nombre real de la columna en el Excel
    col_nombre_formula_real = col_nombre_formula
    if filas:
        for k in filas[0].keys():
            if k == "__linea_excel__": continue
            if normalizar_texto(k) == normalizar_texto(col_nombre_formula) or "formula" in normalizar_texto(k):
                col_nombre_formula_real = k
                break

    grupos_formulas = []
    for nombre_f, items in groupby(filas, key=lambda f: f.get(col_nombre_formula_real, "").strip()):
        if not nombre_f:
            nombre_f = "Fórmula Marco"
        grupos_formulas.append((nombre_f, list(items)))

    total_formulas = len(grupos_formulas)
    total_ingredientes = len(filas)
    ingredientes_procesados = 0
    app.actualizar_progreso(0, total_ingredientes)
    app.log(f"📋 Se detectaron {total_formulas} fórmulas marco para procesar ({total_ingredientes} ingredientes en total).", "info")

    exitosos = 0
    errores = 0
    lista_errores = []

    for idx_f, (nombre_formula, lista_ingredientes) in enumerate(grupos_formulas, start=1):
        if app.debe_detener:
            app.log("\n⏹️ Proceso detenido completamente por el usuario.", "warning")
            break

        while app.debe_pausar and not app.debe_detener:
            time.sleep(0.3)

        if app.debe_detener:
            break

        app.log(f"\n🏷️ [Fórmula {idx_f} de {total_formulas}] '{nombre_formula}' ({len(lista_ingredientes)} ingredientes)...", "header")

        # 1. Abrir modal principal de Fórmula Marco con hasta 3 intentos
        modal_abierto = False
        for intento_f in range(1, 4):
            try:
                if intento_f > 1:
                    app.log(f"   🔄 Intento {intento_f}/3 para abrir Fórmula '{nombre_formula}'...", "warning")
                    try:
                        page.keyboard.press("Escape")
                        time.sleep(0.4)
                    except Exception:
                        pass

                app.log(f"   🖱️ Abriendo ventana de Fórmula Marco...", "detail")
                btn_abrir_form = page.locator(selector_abrir_formula).first
                try:
                    btn_abrir_form.scroll_into_view_if_needed(timeout=1000)
                    btn_abrir_form.click(force=True, timeout=3000)
                except Exception:
                    try:
                        btn_abrir_form.evaluate("el => el.click()")
                    except Exception:
                        page.locator("button:has-text('Fórmula marco'), button:has-text('Formula marco'), button:has-text('Agregar fórmula'), button:has-text('Adicionar fórmula')").first.click(force=True, timeout=3000)
                
                page.wait_for_selector(selector_modal_formula, state="visible", timeout=timeout_ms)
                time.sleep(0.4)

                app.log(f"   ✍️ Asignando nombre: '{nombre_formula}'", "detail")
                campo_nombre = page.locator(selector_campo_nombre).first
                campo_nombre.click(force=True, timeout=3000)
                campo_nombre.fill(nombre_formula)
                time.sleep(0.3)
                modal_abierto = True
                break
            except Exception as e_f:
                app.log(f"   ⚠️ Error en intento {intento_f}/3 de abrir fórmula: {e_f}", "warning")
                if intento_f == 3:
                    errores += len(lista_ingredientes)
                    lista_errores.append({
                        "linea_excel": lista_ingredientes[0]["__linea_excel__"] if lista_ingredientes else 0,
                        "columna_afectada": "Cabecera Fórmula Marco",
                        "valor_excel": nombre_formula,
                        "motivo": str(e_f)
                    })

        if not modal_abierto:
            continue

        # 2. Llenar cada uno de los ingredientes en el submodal con 3 intentos individuales
        for num_ing, fila_ing in enumerate(lista_ingredientes, start=1):
            while app.debe_pausar and not app.debe_detener:
                time.sleep(0.3)

            ingredientes_procesados += 1
            app.actualizar_progreso(ingredientes_procesados, total_ingredientes)

            linea_ex = fila_ing["__linea_excel__"]
            ing_nombre = fila_ing.get("Ingrediente / Mezcla") or fila_ing.get("Ingrediente") or f"#{num_ing}"
            app.log(f"   🧪 Ingrediente {num_ing}/{len(lista_ingredientes)}: '{ing_nombre}' (Línea Excel #{linea_ex})...", "detail")

            exito_ing = False
            ultimo_err_ing = ""

            for intento_ing in range(1, 4):
                if intento_ing > 1:
                    app.log(f"      🔄 INTENTO {intento_ing}/3 para ingrediente '{ing_nombre}' (Línea #{linea_ex})...", "warning")
                    try:
                        page.keyboard.press("Escape")
                        time.sleep(0.4)
                    except Exception:
                        pass

                try:
                    app.log(f"      🖱️ Clic en 'Añadir ingrediente'...", "detail")
                    btn_anadir = page.locator(selector_anadir_ing).first
                    try:
                        btn_anadir.scroll_into_view_if_needed(timeout=1000)
                        btn_anadir.click(force=True, timeout=timeout_ms)
                    except Exception:
                        page.locator("button:has-text('Añadir'), button:has-text('Agregar'), button:has-text('Adicionar')").first.click(force=True)

                    time.sleep(0.5)

                    for campo in campos_ingrediente:
                        llenar_campo(page, campo, fila_ing, linea_ex, app, cfg, "Composición")
                        if getattr(app, "cancelar_ingrediente_actual", False):
                            break

                    if getattr(app, "cancelar_ingrediente_actual", False):
                        app.log(f"      🛑 Ingrediente descartado por el usuario. Cancelando ventana...", "warning")
                        try:
                            page.keyboard.press("Escape")
                            time.sleep(0.3)
                            btn_canc = page.locator(".ant-modal:not([style*='display: none']) button:has-text('Cancelar'), .ant-modal:not([style*='display: none']) .ant-modal-close").last
                            if btn_canc.count() > 0:
                                btn_canc.click(force=True)
                        except Exception:
                            pass
                        app.cancelar_ingrediente_actual = False
                        if app.debe_detener:
                            break
                        continue

                    app.log(f"      💾 Guardando ingrediente...", "detail")
                    btn_guardar_ing = page.locator(selector_guardar_ing).last
                    btn_guardar_ing.click(force=True, timeout=timeout_ms)
                    time.sleep(0.8)

                    exito_ing = True
                    exitosos += 1
                    app.incrementar_exitos()
                    app.log(f"      ✅ Ingrediente '{ing_nombre}' registrado con éxito.", "success")
                    break
                except Exception as e_ing:
                    ultimo_err_ing = str(e_ing)
                    app.log(f"      ⚠️ Intento {intento_ing}/3 falló: {e_ing}", "warning")

            if not exito_ing:
                errores += 1
                app.incrementar_errores()
                app.log(f"      ❌ ERROR DEFINITIVO en Ingrediente '{ing_nombre}' tras 3 intentos.", "error")
                lista_errores.append({
                    "linea_excel": linea_ex,
                    "columna_afectada": "Registro Ingrediente Fórmula Marco",
                    "valor_excel": ing_nombre,
                    "motivo": ultimo_err_ing
                })

            # Si el usuario presionó Detener durante el llenado, aseguramos este ingrediente y guardamos la fórmula
            if app.debe_detener:
                app.log(f"   🛑 Detención solicitada: Ingrediente #{num_ing} asegurado. Procediendo a guardar Fórmula '{nombre_formula}'...", "warning")
                break

        # 3. Guardar SIEMPRE la fórmula marco para asegurar los datos en el portal
        try:
            app.log(f"   💾 Guardando Fórmula Marco '{nombre_formula}'...", "detail")
            btn_guardar_form = page.locator(selector_guardar_formula).first
            btn_guardar_form.click(force=True, timeout=timeout_ms)
            time.sleep(1.0)
            app.log(f"   ✨ Fórmula Marco '{nombre_formula}' guardada exitosamente.", "success")
        except Exception as e_form_save:
            app.log(f"   ⚠️ Error al guardar Fórmula Marco '{nombre_formula}': {e_form_save}", "warning")

        if app.debe_detener:
            app.log(f"\n⏹️ Operación '{nombre_formula}' guardada exitosamente. Proceso detenido de forma segura.", "warning")
            break

    if lista_errores:
        guardar_reporte_errores(ruta_excel, "Fórmula Marco", lista_errores)

    return exitosos, errores


# --------------------------------------------------------------------------
#  Manejador Especializado para Composición por Grupo (Grupo + Fórmula Marco + Ingredientes)
# --------------------------------------------------------------------------
def ejecutar_proceso_composicion_grupo(page, proceso_cfg, filas, app, cfg, timeout_ms, ruta_excel):
    from itertools import groupby

    selector_abrir = proceso_cfg.get("BOTON_ABRIR_MODAL", "")
    selector_modal_principal = proceso_cfg.get("SELECTOR_MODAL_PRINCIPAL", ".ant-modal-wrap, .ant-modal-content")
    boton_accion_previa = proceso_cfg.get("BOTON_ACCION_PREVIA", "")
    campos_cabecera = proceso_cfg.get("CAMPOS_CABECERA", [])
    selector_anadir_ing = proceso_cfg.get("BOTON_ANADIR_INGREDIENTE", "button:has-text('Añadir ingrediente'), button:has-text('Agregar ingrediente'), button:has-text('Adicionar ingrediente')")
    selector_modal_ing = proceso_cfg.get("SELECTOR_MODAL_INGREDIENTE", ".ant-modal-wrap, .ant-modal-content")
    selector_guardar_ing = proceso_cfg.get("BOTON_GUARDAR_INGREDIENTE", ".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button:has-text('Aceptar')")
    selector_guardar_grupo = proceso_cfg.get("BOTON_GUARDAR_GRUPO", ".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button:has-text('Aceptar')")
    campos_ingrediente = proceso_cfg.get("CAMPOS", [])

    # Determinar la clave de agrupación (Grupo / Nombre del grupo)
    col_grupo = "Grupo"
    if filas:
        for k in filas[0].keys():
            if k == "__linea_excel__": continue
            if "grupo" in normalizar_texto(k):
                col_grupo = k
                break

    # Agrupación inteligente para Composición por Grupo:
    # Soporta tanto si repiten el nombre del Grupo en cada fila como si dejan la celda en blanco hacia abajo (Forward Fill)
    from collections import OrderedDict
    grupos_map = OrderedDict()
    ultimo_grupo = None

    for fila in filas:
        val_g = (fila.get(col_grupo) or "").strip()
        if val_g:
            ultimo_grupo = val_g
        elif not ultimo_grupo:
            ultimo_grupo = "Grupo Principal"

        if ultimo_grupo not in grupos_map:
            grupos_map[ultimo_grupo] = []
        grupos_map[ultimo_grupo].append(fila)

    grupos_lista = list(grupos_map.items())

    total_grupos = len(grupos_lista)
    total_ingredientes = len(filas)
    ingredientes_procesados = 0
    app.actualizar_progreso(0, total_ingredientes)
    app.log(f"📋 Se detectaron {total_grupos} grupos de composición para procesar ({total_ingredientes} ingredientes en total).", "info")

    exitosos = 0
    errores = 0
    lista_errores = []

    for idx_g, (nombre_grupo, lista_ingredientes) in enumerate(grupos_lista, start=1):
        if app.debe_detener:
            app.log("\n⏹️ Proceso detenido de forma segura antes de iniciar el siguiente grupo.", "warning")
            break

        while app.debe_pausar and not app.debe_detener:
            time.sleep(0.3)

        if app.debe_detener:
            app.log("\n⏹️ Proceso detenido de forma segura antes de iniciar el siguiente grupo.", "warning")
            break

        app.log(f"\n👥 [Grupo {idx_g} de {total_grupos}] '{nombre_grupo}' ({len(lista_ingredientes)} ingredientes)...", "header")

        # 1. Abrir y configurar Grupo con hasta 3 intentos
        modal_grupo_abierto = False
        for intento_g in range(1, 4):
            try:
                if intento_g > 1:
                    app.log(f"   🔄 INTENTO {intento_g}/3 para inicializar Grupo '{nombre_grupo}'...", "warning")
                    try:
                        page.keyboard.press("Escape")
                        time.sleep(0.4)
                        page.keyboard.press("Escape")
                        time.sleep(0.4)
                    except Exception:
                        pass

                app.log(f"   🖱️ Abriendo ventana 'Composición por Grupo'...", "detail")
                btn_abrir_grp = page.locator("button:has-text('Añadir Composición por Grupo'), button:has-text('Agregar Composición por Grupo'), button:has-text('Añadir composición por grupo'), button:has-text('Agregar composición por grupo'), button:has-text('Composición por Grupo'), button:has-text('Composicion por Grupo')").first
                try:
                    btn_abrir_grp.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                
                try:
                    btn_abrir_grp.evaluate("el => el.click()")
                except Exception:
                    btn_abrir_grp.click(force=True, timeout=3000)
                
                page.wait_for_selector(".ant-modal:not([style*='display: none']), .ant-modal-wrap:not([style*='display: none']), .ant-modal-confirm", state="visible", timeout=timeout_ms)
                time.sleep(0.5)

                # Clic en 'Usar Fórmula Marco'
                if boton_accion_previa:
                    app.log(f"   🖱️ Seleccionando opción 'Usar Fórmula Marco'...", "detail")
                    time.sleep(0.3)
                    btn_marco = page.locator("button:has-text('Usar Fórmula Marco'), button:has-text('Usar fórmula marco'), button:has-text('Usar Formula Marco'), button:has-text('Usar formula marco'), .ant-modal-confirm-body button:has-text('Marco'), .ant-modal-confirm-body button:has-text('Fórmula')").first
                    try:
                        btn_marco.evaluate("el => el.click()")
                    except Exception:
                        btn_marco.click(force=True, timeout=3000)

                    time.sleep(0.8)
                    page.wait_for_selector(".ant-modal-body form, .ant-modal:not(.ant-modal-confirm)", state="visible", timeout=timeout_ms)

                # Llenar campos de cabecera del grupo (Grupo, Fórmula Marco)
                primera_fila = lista_ingredientes[0]
                linea_cabecera = primera_fila["__linea_excel__"]
                for campo_c in campos_cabecera:
                    val = primera_fila.get(campo_c["columna"], "")
                    if not val:
                        for a in campo_c.get("alias", []):
                            if a in primera_fila and primera_fila[a]:
                                val = primera_fila[a]
                                break
                    if val:
                        app.log(f"   📝 Asignando {campo_c['columna']}: '{val}'", "detail")
                        llenar_campo(page, campo_c, primera_fila, linea_cabecera, app, cfg, "Composición")
                        time.sleep(0.4)

                modal_grupo_abierto = True
                break

            except Exception as e_grp:
                app.log(f"   ⚠️ Intento {intento_g}/3 falló al inicializar Grupo: {e_grp}", "warning")
                if intento_g == 3:
                    errores += len(lista_ingredientes)
                    app.log(f"   ❌ ERROR DEFINITIVO al inicializar Grupo '{nombre_grupo}' tras 3 intentos.", "error")
                    lista_errores.append({
                        "linea_excel": lista_ingredientes[0]["__linea_excel__"] if lista_ingredientes else 0,
                        "columna_afectada": "Cabecera Composición por Grupo",
                        "valor_excel": nombre_grupo,
                        "motivo": str(e_grp)
                    })

        if not modal_grupo_abierto:
            try:
                page.keyboard.press("Escape")
                time.sleep(0.3)
                btn_canc = page.locator(".ant-modal:not([style*='display: none']) button:has-text('Cancelar'), .ant-modal:not([style*='display: none']) .ant-modal-close").first
                if btn_canc.count() > 0:
                    btn_canc.click(force=True)
                    time.sleep(0.5)
            except Exception:
                pass
            continue

        # 2. Añadir cada ingrediente del grupo con sistema de 3 reintentos individuales
        for num_ing, fila_ing in enumerate(lista_ingredientes, start=1):
            while app.debe_pausar and not app.debe_detener:
                time.sleep(0.3)

            ingredientes_procesados += 1
            app.actualizar_progreso(ingredientes_procesados, total_ingredientes)

            linea_ex = fila_ing["__linea_excel__"]
            ing_nombre = fila_ing.get("Ingrediente / Mezcla") or fila_ing.get("Ingrediente") or f"#{num_ing}"
            app.log(f"   🧪 Ingrediente {num_ing}/{len(lista_ingredientes)}: '{ing_nombre}' (Línea Excel #{linea_ex})...", "detail")

            exito_ing = False
            ultimo_err_ing = ""

            for intento_ing in range(1, 4):
                if intento_ing > 1:
                    app.log(f"      🔄 INTENTO {intento_ing}/3 para ingrediente '{ing_nombre}' (Línea #{linea_ex})...", "warning")
                    try:
                        page.keyboard.press("Escape")
                        time.sleep(0.4)
                    except Exception:
                        pass

                try:
                    app.log(f"      🖱️ Clic en 'Añadir ingrediente'...", "detail")
                    btn_anadir = page.locator("button:has-text('Añadir Ingrediente'), button:has-text('Añadir ingrediente'), button:has-text('Agregar Ingrediente'), button:has-text('Agregar ingrediente')").first
                    if btn_anadir.count() == 0:
                        btn_anadir = page.locator(selector_anadir_ing).first
                    try:
                        btn_anadir.evaluate("el => el.click()")
                    except Exception:
                        btn_anadir.click(force=True, timeout=timeout_ms)

                    time.sleep(0.4)

                    # Llenar campos de ingrediente
                    for campo in campos_ingrediente:
                        llenar_campo(page, campo, fila_ing, linea_ex, app, cfg, "Composición")
                        if getattr(app, "cancelar_ingrediente_actual", False):
                            break

                    if getattr(app, "cancelar_ingrediente_actual", False):
                        app.log(f"      🛑 Ingrediente descartado por el usuario. Cancelando ventana...", "warning")
                        try:
                            page.keyboard.press("Escape")
                            time.sleep(0.3)
                            btn_canc = page.locator(".ant-modal:not([style*='display: none']) button:has-text('Cancelar'), .ant-modal:not([style*='display: none']) .ant-modal-close").last
                            if btn_canc.count() > 0:
                                btn_canc.click(force=True)
                        except Exception:
                            pass
                        app.cancelar_ingrediente_actual = False
                        if app.debe_detener:
                            break
                        continue

                    # Guardar ingrediente (en el sub-modal de ingrediente)
                    app.log(f"      💾 Guardando ingrediente...", "detail")
                    btn_guardar_ing = page.locator(".ant-modal:not([style*='display: none']) .ant-modal-footer button.ant-btn-primary, .ant-modal:not([style*='display: none']) button:has-text('Guardar')").last
                    try:
                        btn_guardar_ing.evaluate("el => el.click()")
                    except Exception:
                        btn_guardar_ing.click(force=True, timeout=timeout_ms)
                    time.sleep(0.5)

                    exito_ing = True
                    exitosos += 1
                    app.incrementar_exitos()
                    app.log(f"      ✅ Ingrediente '{ing_nombre}' registrado con éxito.", "success")
                    break

                except Exception as e_ing:
                    ultimo_err_ing = str(e_ing)
                    app.log(f"      ⚠️ Intento {intento_ing}/3 falló: {e_ing}", "warning")

            if not exito_ing:
                errores += 1
                app.incrementar_errores()
                app.log(f"      ❌ ERROR DEFINITIVO en Ingrediente '{ing_nombre}' (Línea #{linea_ex}) tras 3 intentos.", "error")
                lista_errores.append({
                    "linea_excel": linea_ex,
                    "columna_afectada": "Registro Ingrediente",
                    "valor_excel": ing_nombre,
                    "motivo": ultimo_err_ing
                })

            # Si el usuario presionó Detener durante el llenado, aseguramos este ingrediente y guardamos el grupo completo
            if app.debe_detener:
                app.log(f"   🛑 Detención solicitada: Ingrediente #{num_ing} asegurado. Procediendo a guardar Grupo '{nombre_grupo}'...", "warning")
                break

        # 3. Guardar SIEMPRE el grupo completo para asegurar los datos en el portal
        try:
            app.log(f"   💾 Guardando Grupo '{nombre_grupo}'...", "detail")
            btn_guardar_grp = page.locator(".ant-modal:not([style*='display: none']) .ant-modal-footer button.ant-btn-primary, .ant-modal:not([style*='display: none']) button:has-text('Guardar')").first
            try:
                btn_guardar_grp.evaluate("el => el.click()")
            except Exception:
                btn_guardar_grp.click(force=True, timeout=timeout_ms)
            time.sleep(0.6)
            app.log(f"   ✨ Grupo '{nombre_grupo}' guardado exitosamente.", "success")
        except Exception as e_grp_save:
            app.log(f"   ⚠️ Error al guardar Grupo '{nombre_grupo}': {e_grp_save}", "warning")

        if app.debe_detener:
            app.log(f"\n⏹️ Operación '{nombre_grupo}' guardada exitosamente. Proceso detenido de forma segura.", "warning")
            break

    if lista_errores:
        guardar_reporte_errores(ruta_excel, "Composición por Grupo", lista_errores)

    return exitosos, errores


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

            # Manejadores especializados según TIPO_PROCESO
            tipo_proceso = proceso_cfg.get("TIPO_PROCESO")
            if tipo_proceso == "formula_marco":
                exitosos, errores = ejecutar_proceso_formula_marco(page, proceso_cfg, filas, app, cfg, timeout_ms, ruta_excel)
                app.log("=" * 60, "divider")
                app.log(f"🏁 PROCESO FINALIZADO: {exitosos} ingredientes registrados, {errores} fallidos.", "header")
                app.finalizar_proceso(exito=(errores == 0))
                return
            elif tipo_proceso == "composicion_grupo":
                exitosos, errores = ejecutar_proceso_composicion_grupo(page, proceso_cfg, filas, app, cfg, timeout_ms, ruta_excel)
                app.log("=" * 60, "divider")
                app.log(f"🏁 PROCESO FINALIZADO: {exitosos} ingredientes registrados, {errores} fallidos.", "header")
                app.finalizar_proceso(exito=(errores == 0))
                return

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
                        btn_abrir_elem = page.locator(selector_abrir).first
                        try:
                            btn_abrir_elem.evaluate("el => el.click()")
                        except Exception:
                            btn_abrir_elem.click(timeout=timeout_ms)

                        app.log(f"   ⏳ Esperando ventana modal...", "detail")
                        page.wait_for_selector(selector_modal, state="visible", timeout=timeout_ms)
                        time.sleep(0.5)

                        # Si el proceso requiere una acción previa dentro del modal (ej. 'Usar Fórmula Marco')
                        boton_accion_previa = proceso_cfg.get("BOTON_ACCION_PREVIA", "").strip()
                        if boton_accion_previa:
                            app.log(f"   🖱️ Buscando opción interior (Usar Fórmula Marco)...", "detail")
                            time.sleep(0.4)
                            clic_exitoso = False

                            candidatos = [
                                "button:has-text('Usar Fórmula Marco')",
                                "button:has-text('Usar fórmula marco')",
                                "button:has-text('Usar Formula Marco')",
                                "button:has-text('Usar formula marco')",
                                "button:has-text('Fórmula Marco')",
                                "button:has-text('Formula Marco')",
                                "button:has-text('Marco')",
                                ".ant-modal-confirm-body button",
                                ".ant-modal-body button",
                                boton_accion_previa
                            ]

                            for cand in candidatos:
                                try:
                                    loc = page.locator(cand)
                                    cnt = loc.count()
                                    if cnt > 0:
                                        for idx_btn in range(cnt):
                                            btn_elem = loc.nth(idx_btn)
                                            txt_btn = btn_elem.inner_text().strip()
                                            if "marco" in txt_btn.lower() or "formula" in txt_btn.lower():
                                                app.log(f"   🎯 Clic en opción encontrada: '{txt_btn}'", "detail")
                                                btn_elem.scroll_into_view_if_needed(timeout=1000)
                                                btn_elem.click(force=True, timeout=3000)
                                                clic_exitoso = True
                                                break
                                        if clic_exitoso:
                                            break
                                        if cand == boton_accion_previa:
                                            loc.first.click(force=True, timeout=3000)
                                            clic_exitoso = True
                                            break
                                except Exception:
                                    continue

                            if not clic_exitoso:
                                app.log(f"   ⚠️ Intentando clic forzado en selector configurado...", "warning")
                                page.locator(boton_accion_previa).first.click(force=True, timeout=timeout_ms)

                            time.sleep(0.8)

                        # Llenar cada uno de los campos configurados para este proceso
                        for campo in campos_proceso:
                            if "PON_EL_SELECTOR" in campo["selector"]:
                                continue
                            llenar_campo(page, campo, fila, linea_excel, app, cfg, nombre_proceso)
                            if getattr(app, "cancelar_ingrediente_actual", False):
                                break

                        if getattr(app, "cancelar_ingrediente_actual", False):
                            app.log(f"   🛑 Registro descartado por el usuario. Cancelando ventana...", "warning")
                            try:
                                page.keyboard.press("Escape")
                                time.sleep(0.3)
                                btn_canc = page.locator(".ant-modal:not([style*='display: none']) button:has-text('Cancelar'), .ant-modal:not([style*='display: none']) .ant-modal-close").last
                                if btn_canc.count() > 0:
                                    btn_canc.click(force=True)
                            except Exception:
                                pass
                            app.cancelar_ingrediente_actual = False
                            if app.debe_detener:
                                break
                            continue

                        app.log(f"   💾 Enviando y guardando formulario...", "detail")
                        btn_env = page.locator(selector_enviar).first
                        if btn_env.count() == 0 or not btn_env.is_visible():
                            btn_env = page.locator(".ant-modal:not([style*='display: none']) .ant-modal-footer button.ant-btn-primary, .ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button:has-text('Aceptar'), button:has-text('Adicionar'), button[type='submit']").first
                        if btn_env.count() > 0:
                            try:
                                btn_env.evaluate("el => el.click()")
                            except Exception:
                                btn_env.click(force=True, timeout=timeout_ms)
                        else:
                            page.locator(".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button:has-text('Adicionar'), button[type='submit']").first.click(force=True)

                        app.log(f"   ⏳ Esperando cierre de la ventana...", "detail")
                        try:
                            page.wait_for_selector(selector_modal, state="hidden", timeout=4000)
                        except Exception:
                            errores_form = []
                            try:
                                loc_errs = page.locator(".ant-form-item-explain-error, .ant-form-item-explain, .ant-form-item-has-error")
                                for e_idx in range(loc_errs.count()):
                                    txt_err = loc_errs.nth(e_idx).inner_text().strip()
                                    if txt_err and txt_err not in errores_form:
                                        errores_form.append(txt_err)
                            except Exception:
                                pass

                            try:
                                page.keyboard.press("Escape")
                                time.sleep(0.5)
                            except Exception:
                                pass

                            if errores_form:
                                detalle_err = "Error en el portal de INVIMA: " + " | ".join(errores_form)
                            else:
                                detalle_err = "El formulario modal no se cerró tras hacer clic en Guardar (campos requeridos incompletos o inválidos)."
                            raise ValueError(detalle_err)

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
#  Interruptor Rectangular de Movimiento Suave (Cubic Ease-Out)
# --------------------------------------------------------------------------
class ElegantRectSwitch(ctk.CTkFrame):
    """
    Interruptor Rectangular de Movimiento Suave (Cubic Ease-Out).
    Altamente visual, estético y diseñado con la paleta de colores corporativa (#7D51E9).
    """
    def __init__(self, master, width=230, height=34, command=None, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=8,
            fg_color="#F1F5F9",
            border_width=2,
            border_color="#CBD5E1",
            **kwargs
        )
        self.pack_propagate(False)
        self.w = width
        self.h = height
        self.command = command
        self.state = False
        self._animating = False

        pad = 3
        self.thumb_w = (width // 2) - pad
        self.thumb_h = height - (pad * 2)
        self.min_x = pad
        self.max_x = width - self.thumb_w - pad
        self.current_x = float(self.min_x)

        # Labels de fondo estáticos (se ven en la mitad descubierta)
        self.bg_off = ctk.CTkLabel(
            self,
            text="🔴 APAGADO",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#94A3B8",
            cursor="hand2"
        )
        self.bg_off.place(x=self.min_x + (self.thumb_w // 2), y=height // 2, anchor="center")

        self.bg_on = ctk.CTkLabel(
            self,
            text="🟢 ENCENDIDO",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#94A3B8",
            cursor="hand2"
        )
        self.bg_on.place(x=self.max_x + (self.thumb_w // 2), y=height // 2, anchor="center")

        # Bloque rectangular deslizante
        self.thumb = ctk.CTkFrame(
            self,
            width=self.thumb_w,
            height=self.thumb_h,
            corner_radius=6,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#CBD5E1",
            cursor="hand2"
        )
        self.thumb.place(x=int(self.current_x), y=pad)

        # Texto sobre el bloque deslizante
        self.thumb_lbl = ctk.CTkLabel(
            self.thumb,
            text="🔴 APAGADO",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#DC2626",
            cursor="hand2"
        )
        self.thumb_lbl.place(relx=0.5, rely=0.5, anchor="center")

        self._bind_click_recursive(self)

    def _bind_click_recursive(self, widget):
        try:
            widget.configure(cursor="hand2")
        except Exception:
            pass
        widget.bind("<Button-1>", self._on_click)
        if hasattr(widget, "_canvas") and widget._canvas:
            try:
                widget._canvas.configure(cursor="hand2")
            except Exception:
                pass
            widget._canvas.bind("<Button-1>", self._on_click)
        if hasattr(widget, "_label") and widget._label:
            try:
                widget._label.configure(cursor="hand2")
            except Exception:
                pass
            widget._label.bind("<Button-1>", self._on_click)
        if hasattr(widget, "_text_label") and widget._text_label:
            try:
                widget._text_label.configure(cursor="hand2")
            except Exception:
                pass
            widget._text_label.bind("<Button-1>", self._on_click)
        for child in widget.winfo_children():
            self._bind_click_recursive(child)

    def _on_click(self, event=None):
        if self._animating:
            return
        self.toggle()

    def get(self):
        return 1 if self.state else 0

    def set(self, valor):
        nuevo = bool(valor)
        if nuevo != self.state:
            self.state = nuevo
            self._aplicar_estado_instantaneo()

    def toggle(self):
        if self._animating:
            return
        self.state = not self.state
        self._start_animation()
        if self.command:
            self.command()

    def _aplicar_estado_instantaneo(self):
        pad = 3
        if self.state:
            self.current_x = float(self.max_x)
            self.configure(fg_color="#7D51E9", border_color="#6D28D9")
            self.thumb.configure(fg_color="#FFFFFF", border_color="#7D51E9")
            self.thumb_lbl.configure(text="🟢 ENCENDIDO", text_color="#7D51E9")
            self.bg_off.configure(text_color="#DDD6FE")
        else:
            self.current_x = float(self.min_x)
            self.configure(fg_color="#F1F5F9", border_color="#CBD5E1")
            self.thumb.configure(fg_color="#FFFFFF", border_color="#CBD5E1")
            self.thumb_lbl.configure(text="🔴 APAGADO", text_color="#DC2626")
            self.bg_on.configure(text_color="#94A3B8")
        self.thumb.place(x=int(self.current_x), y=pad)

    def _start_animation(self):
        self._animating = True
        start_x = self.current_x
        target_x = float(self.max_x if self.state else self.min_x)
        distance = target_x - start_x

        if self.state:
            self.configure(fg_color="#7D51E9", border_color="#6D28D9")
            self.thumb.configure(fg_color="#FFFFFF", border_color="#7D51E9")
            self.thumb_lbl.configure(text="🟢 ENCENDIDO", text_color="#7D51E9")
            self.bg_off.configure(text_color="#DDD6FE")
        else:
            self.configure(fg_color="#F1F5F9", border_color="#CBD5E1")
            self.thumb.configure(fg_color="#FFFFFF", border_color="#CBD5E1")
            self.thumb_lbl.configure(text="🔴 APAGADO", text_color="#DC2626")
            self.bg_on.configure(text_color="#94A3B8")

        total_steps = 15
        step = 0
        pad = 3

        def _step():
            nonlocal step
            step += 1
            if step >= total_steps:
                self.current_x = target_x
                self.thumb.place(x=int(self.current_x), y=pad)
                self._animating = False
            else:
                t = step / total_steps
                ease = 1.0 - math.pow(1.0 - t, 3)
                self.current_x = start_x + (distance * ease)
                self.thumb.place(x=int(self.current_x), y=pad)
                self.after(16, _step)

        _step()


# --------------------------------------------------------------------------
#  Interfaz Gráfica Profesional con Selector de Proceso (CustomTkinter)
# --------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MC PROCESOS INTEGRALES - Automatizador")

        # Geometría adaptable con soporte completo para computadores portátiles
        pantalla_w = self.winfo_screenwidth()
        pantalla_h = self.winfo_screenheight()
        alto_inicial = min(840, max(580, pantalla_h - 90))
        ancho_inicial = min(1240, max(1050, pantalla_w - 60))
        self.geometry(f"{ancho_inicial}x{alto_inicial}")
        self.minsize(1050, 500)
        self.configure(fg_color="#CEDDF0")

        # Cargar icono de ventana y de barra de tareas con persistencia total
        self._icono_ref = None
        for cand_ico in ["app_icon.ico", os.path.join("assets", "app_icon.ico"), os.path.join("assets", "icon.ico")]:
            ruta_ico = obtener_ruta_recurso(cand_ico)
            if os.path.exists(ruta_ico):
                try:
                    self.iconbitmap(ruta_ico)
                except Exception:
                    pass
                try:
                    self.wm_iconbitmap(ruta_ico)
                except Exception:
                    pass
                try:
                    ico_img = Image.open(ruta_ico)
                    self._icono_ref = ImageTk.PhotoImage(ico_img)
                    self.iconphoto(True, self._icono_ref)
                except Exception:
                    pass
                break

        # Variables de control
        self.cfg = cargar_config_dinamico()
        self.ruta_excel = None
        self.debe_pausar = False
        self.debe_detener = False
        self.en_ejecucion = False
        self.modo_manual_funcion = False
        self.confirmar_manual_listo = False
        self.cancelar_ingrediente_actual = False
        self.num_exitos = 0
        self.num_errores = 0
        self.licencia_info = None
        self._modal_ayuda = None
        self._modal_manual = None

        self._construir_interfaz()
        self.protocol("WM_DELETE_WINDOW", self._on_cerrar_aplicacion)
        buscar_actualizaciones_github(self)
        self.after(300, self._verificar_licencia_inicial)

    def _on_cerrar_aplicacion(self):
        try:
            if hasattr(self, 'dropdown_menu') and self.dropdown_menu:
                self.dropdown_menu.cerrar()
        except Exception:
            pass
        self.destroy()

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
        top.title("🔐 Activación de Licencia - MC PROCESOS INTEGRALES")
        top.geometry("520x360")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.configure(fg_color="#F8FAFC")
        if getattr(self, '_icono_ref', None):
            try:
                top.iconphoto(True, self._icono_ref)
            except Exception:
                pass
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
            text_color="#1E1B4B"
        )
        lbl_title.pack(pady=(22, 6))

        lbl_sub = ctk.CTkLabel(
            top,
            text="Ingresa tu Clave de Licencia proporcionada por el proveedor\npara activar el Automatizador INVIMA en este equipo.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#64748B"
        )
        lbl_sub.pack(pady=(0, 16))

        entry_clave = ctk.CTkEntry(
            top,
            placeholder_text="XXXX-XXXX-XXXX-XXXX",
            width=380,
            height=42,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#FFFFFF",
            border_color="#CBD5E1",
            text_color="#1E293B"
        )
        entry_clave.pack(pady=8)

        lbl_status = ctk.CTkLabel(
            top,
            text=mensaje_error_inicial,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#EF4444" if mensaje_error_inicial else "#64748B"
        )
        lbl_status.pack(pady=6)

        def _activar():
            clave_ingresada = entry_clave.get().strip().upper()
            if not clave_ingresada:
                lbl_status.configure(text="❌ Por favor ingresa tu clave de licencia.", text_color="#EF4444")
                return

            lbl_status.configure(text="⏳ Verificando licencia en línea...", text_color="#7D51E9")
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
            font=ctk.CTkFont(family="Segoe UI", weight="bold", size=14),
            fg_color="#7D51E9",
            hover_color="#6D28D9",
            text_color="#FFFFFF",
            height=42,
            width=220,
            corner_radius=8,
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
                top.title("✨ Actualización Disponible - MC PROCESOS INTEGRALES")
                top.geometry("500x340")
                top.resizable(False, False)
                top.attributes("-topmost", True)
                top.configure(fg_color="#F8FAFC")
                if getattr(self, '_icono_ref', None):
                    try:
                        top.iconphoto(True, self._icono_ref)
                    except Exception:
                        pass
                top.grab_set()

                lbl = ctk.CTkLabel(
                    top,
                    text=f"🎉 ¡Nueva versión {version_n} disponible!",
                    font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                    text_color="#0DBE8A"
                )
                lbl.pack(pady=(18, 6))

                lbl_sub = ctk.CTkLabel(
                    top,
                    text="Una versión más reciente del Automatizador está lista para instalar.",
                    font=ctk.CTkFont(family="Segoe UI", size=12),
                    text_color="#64748B"
                )
                lbl_sub.pack(pady=(0, 10))

                txt = ctk.CTkTextbox(
                    top,
                    width=450,
                    height=140,
                    fg_color="#FFFFFF",
                    text_color="#1E293B",
                    border_color="#CBD5E1",
                    border_width=1,
                    corner_radius=8,
                    font=ctk.CTkFont(family="Segoe UI", size=11)
                )
                txt.pack(pady=4)
                txt.insert("0.0", f"Novedades:\n{novedades}")
                txt.configure(state="disabled")

                def _actualizar():
                    top.destroy()
                    threading.Thread(target=ejecutar_actualizacion_automatica, args=(exe_url, config_url, self), daemon=True).start()

                btn = ctk.CTkButton(
                    top,
                    text="🚀 Actualizar Ahora Automáticamente",
                    font=ctk.CTkFont(family="Segoe UI", weight="bold"),
                    fg_color="#0DBE8A",
                    hover_color="#0AA779",
                    text_color="#FFFFFF",
                    height=38,
                    corner_radius=8,
                    command=_actualizar
                )
                btn.pack(pady=14)
            except Exception as e:
                print(f"Error mostrando modal de actualización: {e}")

        self.after(500, _construir_dialogo)

    def mostrar_modal_manual(self):
        if getattr(self, "_modal_manual", None) and self._modal_manual.winfo_exists():
            self._modal_manual.lift()
            self._modal_manual.focus_force()
            return

        top = ctk.CTkToplevel(self)
        self._modal_manual = top
        top.title("📖 Manual de Usuario y Guía de Operación - MC PROCESOS INTEGRALES")
        top.geometry("740x620")
        top.resizable(True, True)
        top.attributes("-topmost", True)
        top.configure(fg_color="#F8FAFC")
        if getattr(self, '_icono_ref', None):
            try:
                top.iconphoto(True, self._icono_ref)
            except Exception:
                pass

        def _cerrar_manual():
            self._modal_manual = None
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", _cerrar_manual)

        lbl_title = ctk.CTkLabel(
            top,
            text="📖 Manual de Operación y Cláusula de Exención de Responsabilidad",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_title.pack(pady=(16, 6))

        txt_manual = ctk.CTkTextbox(
            top,
            width=700,
            height=480,
            fg_color="#FFFFFF",
            text_color="#1E293B",
            border_color="#CBD5E1",
            border_width=1,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        txt_manual.pack(pady=8, padx=16, fill="both", expand=True)

        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        ruta_txt = obtener_ruta_recurso("MANUAL_DE_USUARIO.txt")
        texto_contenido = ""

        if os.path.exists(ruta_txt):
            try:
                with open(ruta_txt, "r", encoding="utf-8") as f:
                    texto_contenido = f.read()
            except Exception:
                pass

        if not texto_contenido:
            texto_contenido = """========================================================================
             MANUAL DE USUARIO Y GUÍA DE OPERACIÓN
                   AUTOMATIZADOR INVIMA
========================================================================

1. REQUISITOS PREVIOS DEL SISTEMA
------------------------------------------------------------------------
- Sistema Operativo: Windows 10 o Windows 11.
- Navegador: Google Chrome instalado.
- Formato de Archivo: Planillas en formato Microsoft Excel (.xlsx).
- Licencia Activa: Clave de Licencia proporcionada por el proveedor.

2. PASOS PARA LA EJECUCIÓN DEL PROGRAMA
------------------------------------------------------------------------
Paso 1: Abre la aplicación "Automatizador INVIMA.exe".
Paso 2: Si es la primera vez, ingresa tu Clave de Licencia y presiona "Activar Licencia".
Paso 3: Haz clic en el botón "🌐 Abrir Chrome Bot" situado en la barra superior.
Paso 4: En la ventana de Chrome que se abre, ingresa al portal de INVIMA con tus credenciales y navega exactamente hasta el formulario del trámite a diligenciar.
Paso 5: Selecciona el Requisito a procesar en la aplicación.
Paso 6: Haz clic en "📂 Seleccionar archivo" y carga tu plantilla oficial.
Paso 7: Haz clic en "▶ Iniciar automatización".

3. ESTRUCTURA Y REGLAS DE LAS HOJAS DE EXCEL
------------------------------------------------------------------------
⚠️ REGLA DE ORO 1: Los nombres de las Hojas (pestañas de Excel) deben ser EXACTOS.
⚠️ REGLA DE ORO 2: Los encabezados de las columnas en la Fila 1 deben coincidir al 100% con los requeridos.
⚠️ REGLA DE ORO 3: Los valores y textos ingresados en las celdas deben coincidir AL 100% con las opciones desplegables del portal INVIMA, incluyendo tildes, mayúsculas y espacios.

4. MANEJO DE ERRORES Y REPORTES
------------------------------------------------------------------------
- Si una fila presenta inconsistencias, el bot realizará reintentos automáticos.
- El avance quedará registrado en la consola de trazabilidad y se puede exportar el reporte final.

5. CLÁUSULA DE EXENCIÓN DE RESPONSABILIDAD LEGAL (DISCLAIMER)
------------------------------------------------------------------------
• El software Automatizador INVIMA es una herramienta de asistencia y automatización robótica de tareas (RPA).
• EL DESARROLLADOR / PROVEEDOR NO SE HACE RESPONSABLE por mal uso de la herramienta, datos mal digitados por el usuario, errores en la plantilla Excel, nombres de encabezados incorrectos, inconsistencias en los registros ante la entidad INVIMA o multas/sanciones derivadas de información errónea ingresada por el usuario.
• Es responsabilidad exclusiva del usuario verificar y validar la exactitud de los datos ingresados en el archivo Excel y en la plataforma de INVIMA antes y después de ejecutar el proceso de automatización.
========================================================================
"""

        txt_manual.insert("0.0", texto_contenido)
        txt_manual.configure(state="disabled")

        def _abrir_txt():
            ruta_disco = os.path.join(base_dir, "MANUAL_DE_USUARIO.txt")
            if os.path.exists(ruta_disco):
                os.startfile(ruta_disco)
            elif os.path.exists(ruta_txt):
                os.startfile(ruta_txt)
            else:
                with open(ruta_disco, "w", encoding="utf-8") as f:
                    f.write(texto_contenido)
                os.startfile(ruta_disco)

        btn_abrir = ctk.CTkButton(
            top,
            text="📄 Abrir en Bloc de Notas / Editor",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#7D51E9",
            hover_color="#6D28D9",
            text_color="#FFFFFF",
            height=34,
            corner_radius=8,
            command=_abrir_txt
        )
        btn_abrir.pack(pady=12)

    def _obtener_lista_procesos(self):
        if hasattr(self.cfg, "PROCESOS") and isinstance(self.cfg.PROCESOS, dict):
            procesos_disponibles = list(self.cfg.PROCESOS.keys())
            # Orden de trabajo oficial de la plataforma Invima ágil
            orden_preferido = [
                "Información General (Grupos)",
                "Información General (Presentaciones)",
                "Composición (Ingredientes)",
                "Composición (Fórmula Marco)",
                "Composición (Composición por Grupo)",
                "Características Técnicas (Características Organolépticas)"
            ]
            def _orden_key(nombre):
                try:
                    return orden_preferido.index(nombre)
                except ValueError:
                    return 999
            return sorted(procesos_disponibles, key=_orden_key)
        return ["Información General (Grupos)", "Información General (Presentaciones)"]

    def _obtener_icono_proceso(self, nombre_proceso):
        nombre_lower = str(nombre_proceso).lower()
        if "presentaci" in nombre_lower:
            return "📦"
        elif "grupo" in nombre_lower and "composici" in nombre_lower:
            return "🔗"
        elif "grupo" in nombre_lower:
            return "👥"
        elif "marco" in nombre_lower:
            return "🧬"
        elif "ingrediente" in nombre_lower:
            return "🧪"
        elif "organol" in nombre_lower:
            return "👃"
        return "📋"

    def _obtener_hoja_para(self, nombre_proceso):
        if "ingrediente" in str(nombre_proceso).lower():
            return "Ingredientes"
        proceso_cfg = obtener_dict_proceso(self.cfg, nombre_proceso)
        return proceso_cfg.get("NOMBRE_HOJA", "Matriz")

    def _obtener_hoja_actual(self):
        nombre_proceso = getattr(self, 'proceso_seleccionado', self._obtener_lista_procesos()[0])
        return self._obtener_hoja_para(nombre_proceso)

    def _obtener_info_campos(self):
        nombre_proceso = getattr(self, 'proceso_seleccionado', self._obtener_lista_procesos()[0])
        proceso_cfg = obtener_dict_proceso(self.cfg, nombre_proceso)
        campos = proceso_cfg.get("CAMPOS", [])
        return f"{len(campos)} campos configurados"

    def seleccionar_proceso(self, nuevo_proceso):
        if self.en_ejecucion:
            return
        self.proceso_seleccionado = nuevo_proceso
        if hasattr(self, 'dropdown_menu'):
            self.dropdown_menu.actualizar_seleccion(nuevo_proceso)
        self.on_proceso_changed(nuevo_proceso)

    def generar_o_descargar_plantilla(self):
        """
        Permite al usuario descargar la plantilla oficial de trabajo en Excel
        con todas las hojas oficiales requeridas y encabezados exactos.
        Si existe un archivo 'plantilla_base.xlsx' en la carpeta de la app, copia ese archivo.
        """
        ruta_destino = filedialog.asksaveasfilename(
            title="Guardar Plantilla Oficial de Trabajo Excel",
            defaultextension=".xlsx",
            initialfile="Plantilla_Oficial_Automatizador_INVIMA.xlsx",
            filetypes=[("Archivos Excel (*.xlsx)", "*.xlsx"), ("Todos los archivos", "*.*")]
        )
        if not ruta_destino:
            return

        try:
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            plantilla_personalizada = os.path.join(base_dir, "plantilla_base.xlsx")
            if os.path.exists(plantilla_personalizada):
                shutil.copyfile(plantilla_personalizada, ruta_destino)
                self.log(f"📥 Plantilla oficial exportada exitosamente: {os.path.basename(ruta_destino)}", "info")
                messagebox.showinfo("Plantilla Descargada", f"¡Plantilla exportada exitosamente!\n\nSe guardó en:\n{ruta_destino}")
                return

            # Generar dinámicamente con openpyxl con todas las hojas oficiales
            wb = Workbook()
            wb.remove(wb.active)  # Quitar hoja inicial vacía

            hojas_config = [
                {
                    "nombre": "Grupos",
                    "columnas": ["Nombre del grupo"],
                    "ejemplo": ["Grupo Labial Mate"]
                },
                {
                    "nombre": "Presentaciones comerciales",
                    "columnas": [
                        "Contenido Neto", "Unidad de Medida", "Tipo de Envase Primario",
                        "Material del Envase Primario", "Tipo de Envase Secundario",
                        "Material del Envase Secundario", "Observaciones"
                    ],
                    "ejemplo": [30, "g", "Tubo", "Plástico", "Caja", "Cartón", "Presentación individual"]
                },
                {
                    "nombre": "Ingredientes",
                    "columnas": [
                        "Tipo", "Ingrediente / Mezcla", "Función",
                        "Listado de referencia", "Cantidad", "Unidad de medida",
                        "¿Es nanomaterial?", "Tamaño de partícula (nm)"
                    ],
                    "ejemplo": ["Ingrediente", "Glicerina", "Humectante", "CosIng", "5", "%", "No", ""]
                },
                {
                    "nombre": "Fórmula Marco",
                    "columnas": [
                        "Nombre de la fórmula marco", "Tipo", "Ingrediente / Mezcla",
                        "Función", "Listado de referencia", "Cantidad", "Unidad de medida",
                        "¿Es nanomaterial?", "Tamaño de partícula (nm)"
                    ],
                    "ejemplo": ["Fórmula Base Labial", "Ingrediente", "Agua", "Solvente", "CosIng", "80", "%", "No", ""]
                },
                {
                    "nombre": "Composición por grupo",
                    "columnas": [
                        "Grupo", "Fórmula Marco", "Tipo", "Ingrediente / Mezcla",
                        "Función", "Listado de referencia", "Cantidad", "Unidad de medida",
                        "¿Es nanomaterial?", "Tamaño de partícula (nm)"
                    ],
                    "ejemplo": ["Grupo Labial Mate", "Fórmula Base Labial", "Ingrediente", "CI 77491", "Colorante", "CosIng", "2", "%", "No", ""]
                },
                {
                    "nombre": "Características Organolépticas",
                    "columnas": ["Grupo Cosmético", "Color", "Olor", "Sabor"],
                    "ejemplo": ["Grupo Labial Mate", "Rojo carmín", "Frutos rojos", "Neutro"]
                }
            ]

            header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

            data_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
            data_font = Font(name="Calibri", size=10, italic=True, color="475569")
            data_align = Alignment(horizontal="center", vertical="center")

            thin_side = Side(border_style="thin", color="CBD5E1")
            cell_border = Border(top=thin_side, left=thin_side, right=thin_side, bottom=thin_side)

            for item in hojas_config:
                ws = wb.create_sheet(title=item["nombre"])
                ws.append(item["columnas"])
                ws.append(item["ejemplo"])

                for col_idx in range(1, len(item["columnas"]) + 1):
                    # Fila 1: Encabezados
                    c1 = ws.cell(row=1, column=col_idx)
                    c1.fill = header_fill
                    c1.font = header_font
                    c1.alignment = header_align
                    c1.border = cell_border

                    # Fila 2: Ejemplo
                    c2 = ws.cell(row=2, column=col_idx)
                    c2.fill = data_fill
                    c2.font = data_font
                    c2.alignment = data_align
                    c2.border = cell_border

                    col_letter = c1.column_letter
                    ancho = max(len(str(item["columnas"][col_idx - 1])) + 4, 15)
                    ws.column_dimensions[col_letter].width = ancho

                ws.row_dimensions[1].height = 28
                ws.row_dimensions[2].height = 20

            wb.save(ruta_destino)
            try:
                wb.save(plantilla_personalizada)
            except Exception:
                pass

            self.log(f"📥 Plantilla oficial generada y descargada: {os.path.basename(ruta_destino)}", "info")
            messagebox.showinfo(
                "Plantilla Descargada",
                f"¡Plantilla generada con éxito!\n\nSe guardó en:\n{ruta_destino}\n\nIncluye todas las 6 pestañas oficiales con sus encabezados exactos y filas de ejemplo."
            )
        except Exception as e:
            self.log(f"❌ Error al descargar plantilla: {e}", "error")
            messagebox.showerror("Error al Descargar", f"No se pudo generar la plantilla Excel:\n{e}")

    def limpiar_consola(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")
        self.log("🧹 Consola de trazabilidad limpiada.", "info")

    def exportar_reporte(self):
        contenido = self.txt_log.get("1.0", "end").strip()
        if not contenido:
            messagebox.showinfo("Reporte Vacío", "No hay eventos registrados en la consola para exportar.")
            return
        ruta = filedialog.asksaveasfilename(
            title="Exportar Reporte de Trazabilidad",
            defaultextension=".txt",
            initialfile=f"reporte_trazabilidad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Archivos de texto (*.txt)", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if ruta:
            try:
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(contenido)
                self.log(f"📄 Reporte exportado a: {os.path.basename(ruta)}", "info")
                messagebox.showinfo("Reporte Exportado", f"Reporte guardado exitosamente en:\n{ruta}")
            except Exception as e:
                self.log(f"❌ Error exportando reporte: {e}", "error")

    def mostrar_modal_ayuda(self):
        if getattr(self, "_modal_ayuda", None) and self._modal_ayuda.winfo_exists():
            self._modal_ayuda.lift()
            self._modal_ayuda.focus_force()
            return

        top = ctk.CTkToplevel(self)
        self._modal_ayuda = top
        top.title("💬 Soporte y Asistencia - MC PROCESOS INTEGRALES")
        top.geometry("480x290")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.configure(fg_color="#F8FAFC")
        if getattr(self, '_icono_ref', None):
            try:
                top.iconphoto(True, self._icono_ref)
            except Exception:
                pass

        def _cerrar_ayuda():
            self._modal_ayuda = None
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", _cerrar_ayuda)

        lbl_t = ctk.CTkLabel(
            top,
            text="🎧 Centro de Soporte y Acompañamiento",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_t.pack(pady=(22, 6))

        lbl_sub = ctk.CTkLabel(
            top,
            text="MC Procesos Integrales • Automatización & Inteligencia Sanitaria\nNuestro equipo te acompaña en cada etapa regulatoria.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748B"
        )
        lbl_sub.pack(pady=(0, 14))

        box = ctk.CTkFrame(top, fg_color="#FFFFFF", border_color="#E2E8F0", border_width=1, corner_radius=10)
        box.pack(padx=24, pady=6, fill="x")

        lbl_contacto = ctk.CTkLabel(
            box,
            text="📧 Correo: mcserviciosintegrales.co@gmail.com\n📞 Soporte Regulatorio: 3011318258 - 3007758234",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#334155",
            justify="left",
            padx=14,
            pady=12
        )
        lbl_contacto.pack(anchor="w")

        btn_cerrar = ctk.CTkButton(
            top,
            text="Entendido",
            font=ctk.CTkFont(family="Segoe UI", weight="bold"),
            fg_color="#7D51E9",
            hover_color="#6D28D9",
            text_color="#FFFFFF",
            width=120,
            corner_radius=8,
            command=_cerrar_ayuda
        )
        btn_cerrar.pack(pady=(16, 10))

    def _on_window_resize(self, event):
        if event.widget == self:
            w, h = event.width, event.height
            if w > 300 and h > 300 and (w != getattr(self, '_last_bg_w', 0) or h != getattr(self, '_last_bg_h', 0)):
                self._last_bg_w = w
                self._last_bg_h = h
                if getattr(self, 'img_app_bg', None):
                    try:
                        self.img_app_bg.configure(size=(w, h))
                    except Exception:
                        pass

    def _construir_interfaz(self):
        self.configure(fg_color="#EEF2F8")

        lista_procesos = self._obtener_lista_procesos()
        self.proceso_seleccionado = lista_procesos[0]

        # Cargar recursos gráficos corporativos oficiales
        self.img_logo_mc = None
        self.img_cosmetics_card = None
        self.img_doc_badge = None
        self.iconos_servicios = {}

        # Insignias vectoriales suavizadas de alta definición para el Wizard (4x Supersampled)
        self.img_s1_active = None
        self.img_s1_inactive = None
        self.img_s2_active = None
        self.img_s2_inactive = None
        self.img_s3_active = None
        self.img_s3_inactive = None

        try:
            r_s1_a = obtener_ruta_recurso(os.path.join("assets", "badge_s1_active.png"))
            r_s1_i = obtener_ruta_recurso(os.path.join("assets", "badge_s1_inactive.png"))
            r_s2_a = obtener_ruta_recurso(os.path.join("assets", "badge_s2_active.png"))
            r_s2_i = obtener_ruta_recurso(os.path.join("assets", "badge_s2_inactive.png"))
            r_s3_a = obtener_ruta_recurso(os.path.join("assets", "badge_s3_active.png"))
            r_s3_i = obtener_ruta_recurso(os.path.join("assets", "badge_s3_inactive.png"))

            if os.path.exists(r_s1_a):
                self.img_s1_active = ctk.CTkImage(light_image=Image.open(r_s1_a), size=(32, 32))
            if os.path.exists(r_s1_i):
                self.img_s1_inactive = ctk.CTkImage(light_image=Image.open(r_s1_i), size=(32, 32))
            if os.path.exists(r_s2_a):
                self.img_s2_active = ctk.CTkImage(light_image=Image.open(r_s2_a), size=(32, 32))
            if os.path.exists(r_s2_i):
                self.img_s2_inactive = ctk.CTkImage(light_image=Image.open(r_s2_i), size=(32, 32))
            if os.path.exists(r_s3_a):
                self.img_s3_active = ctk.CTkImage(light_image=Image.open(r_s3_a), size=(32, 32))
            if os.path.exists(r_s3_i):
                self.img_s3_inactive = ctk.CTkImage(light_image=Image.open(r_s3_i), size=(32, 32))
        except Exception:
            pass

        try:
            ruta_doc = obtener_ruta_recurso(os.path.join("assets", "doc_icon.png"))
            if not os.path.exists(ruta_doc):
                ruta_doc = obtener_ruta_recurso(os.path.join("assets", "icon_bot_doc.png"))
            if os.path.exists(ruta_doc):
                self.img_doc_badge = ctk.CTkImage(light_image=Image.open(ruta_doc), size=(38, 38))
        except Exception:
            pass

        try:
            ruta_logo_mc = obtener_ruta_recurso(os.path.join("assets", "logo_mc_clean.png"))
            if os.path.exists(ruta_logo_mc):
                self.img_logo_mc = ctk.CTkImage(light_image=Image.open(ruta_logo_mc), size=(50, 50))
        except Exception:
            pass

        for k in ["srv_tramites", "srv_analisis", "srv_certificacion", "srv_auditorias", "srv_automatizacion"]:
            try:
                r = obtener_ruta_recurso(os.path.join("assets", f"{k}_42.png"))
                if not os.path.exists(r):
                    r = obtener_ruta_recurso(os.path.join("assets", f"{k}.png"))
                if os.path.exists(r):
                    self.iconos_servicios[k] = ctk.CTkImage(light_image=Image.open(r), size=(38, 38))
            except Exception:
                pass

        try:
            ruta_aliado = obtener_ruta_recurso(os.path.join("assets", "aliado_feather.png"))
            if not os.path.exists(ruta_aliado):
                ruta_aliado = obtener_ruta_recurso(os.path.join("assets", "aliado_clean_alpha.png"))
            if os.path.exists(ruta_aliado):
                self.img_aliado = ctk.CTkImage(light_image=Image.open(ruta_aliado), size=(250, 48))
        except Exception:
            pass

        try:
            ruta_flask = obtener_ruta_recurso(os.path.join("assets", "flask_clean_feather.png"))
            if not os.path.exists(ruta_flask):
                ruta_flask = obtener_ruta_recurso(os.path.join("assets", "flask_clean_alpha.png"))
            if os.path.exists(ruta_flask):
                self.img_flask = ctk.CTkImage(light_image=Image.open(ruta_flask), size=(240, 150))
        except Exception:
            pass

        # Componente de Dropdown Flotante Moderno (Estilo Ejecutivo Claro)
        class ModernFloatingDropdown(ctk.CTkFrame):
            def __init__(self, master, app, procesos):
                super().__init__(master, fg_color="transparent")
                self.app = app
                self.procesos = procesos
                self.popup = None
                self._bind_ids = []

                # Botón Principal Claro y Elegante
                self.btn_principal = ctk.CTkButton(
                    self,
                    text=f"{self.app._obtener_icono_proceso(self.app.proceso_seleccionado)}  {self.app.proceso_seleccionado}   ▼",
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    fg_color="#FFFFFF",
                    hover_color="#F5F3FF",
                    border_color="#DDD6FE",
                    border_width=1,
                    text_color="#1E1B4B",
                    corner_radius=8,
                    height=38,
                    anchor="w",
                    command=self.toggle
                )
                self.btn_principal.pack(fill="x", pady=(2, 2))

            def toggle(self):
                if self.app.en_ejecucion:
                    return
                if self.popup and self.popup.winfo_exists():
                    self.cerrar()
                else:
                    self.abrir()

            def abrir(self):
                self.cerrar()

                self.btn_principal.update_idletasks()
                x = self.btn_principal.winfo_rootx()
                y = self.btn_principal.winfo_rooty() + self.btn_principal.winfo_height() + 4
                ancho = max(self.btn_principal.winfo_width(), 460)
                alto_total = min(len(self.procesos) * 48 + 14, 280)

                self.popup = ctk.CTkToplevel(self.app)
                self.popup.overrideredirect(True)
                self.popup.transient(self.app)
                self.popup.geometry(f"{ancho}x{alto_total}+{x}+{y}")
                self.popup.configure(fg_color="#FFFFFF")

                frame_borde = ctk.CTkFrame(
                    self.popup,
                    fg_color="#FFFFFF",
                    corner_radius=10,
                    border_width=2,
                    border_color="#7D51E9"
                )
                frame_borde.pack(fill="both", expand=True)

                scroll_frame = ctk.CTkScrollableFrame(
                    frame_borde,
                    fg_color="transparent",
                    corner_radius=8,
                    scrollbar_button_color="#DDD6FE",
                    scrollbar_button_hover_color="#C4B5FD"
                )
                scroll_frame.pack(fill="both", expand=True, padx=4, pady=4)

                for proc in self.procesos:
                    icono = self.app._obtener_icono_proceso(proc)
                    hoja = self.app._obtener_hoja_para(proc)
                    es_activo = (proc == self.app.proceso_seleccionado)

                    btn_item = ctk.CTkButton(
                        scroll_frame,
                        text=f"  {icono}  {proc}{'  ✓' if es_activo else ''}\n     📄 Hoja: {hoja}",
                        font=ctk.CTkFont(family="Segoe UI", size=11),
                        fg_color="#F5F3FF" if es_activo else "#FFFFFF",
                        hover_color="#EDE9FE",
                        border_color="#C4B5FD" if es_activo else "#E2E8F0",
                        border_width=1 if es_activo else 0,
                        text_color="#6D28D9" if es_activo else "#334155",
                        corner_radius=6,
                        height=40,
                        anchor="w",
                        command=lambda p=proc: self.seleccionar(p)
                    )
                    btn_item.pack(fill="x", padx=3, pady=2)

                self.btn_principal.configure(
                    text=f"{self.app._obtener_icono_proceso(self.app.proceso_seleccionado)}  {self.app.proceso_seleccionado}   ▲"
                )

                self._bind_app_events()

            def _bind_app_events(self):
                self._unbind_app_events()
                b1 = self.app.bind("<Button-1>", self._on_app_click, add="+")
                b2 = self.app.bind("<Configure>", self._on_app_move, add="+")
                b3 = self.app.bind("<Unmap>", lambda e: self.cerrar(), add="+")
                b4 = self.app.bind("<Escape>", lambda e: self.cerrar(), add="+")
                b5 = self.app.bind("<MouseWheel>", lambda e: self.cerrar(), add="+")
                self._bind_ids = [("<Button-1>", b1), ("<Configure>", b2), ("<Unmap>", b3), ("<Escape>", b4), ("<MouseWheel>", b5)]

            def _unbind_app_events(self):
                for seq, bid in self._bind_ids:
                    try:
                        self.app.unbind(seq, bid)
                    except Exception:
                        pass
                self._bind_ids = []

            def _on_app_move(self, event):
                if event.widget == self.app:
                    self.cerrar()

            def _on_app_click(self, event):
                if not self.popup or not self.popup.winfo_exists():
                    return
                x_click = event.x_root
                y_click = event.y_root
                try:
                    px = self.popup.winfo_rootx()
                    py = self.popup.winfo_rooty()
                    pw = self.popup.winfo_width()
                    ph = self.popup.winfo_height()
                    bx = self.btn_principal.winfo_rootx()
                    by = self.btn_principal.winfo_rooty()
                    bw = self.btn_principal.winfo_width()
                    bh = self.btn_principal.winfo_height()

                    if not (px <= x_click <= px + pw and py <= y_click <= py + ph) and \
                       not (bx <= x_click <= bx + bw and by <= y_click <= by + bh):
                        self.cerrar()
                except Exception:
                    pass

            def cerrar(self):
                self._unbind_app_events()
                if self.popup and self.popup.winfo_exists():
                    try:
                        self.popup.destroy()
                    except Exception:
                        pass
                    self.popup = None
                try:
                    self.btn_principal.configure(
                        text=f"{self.app._obtener_icono_proceso(self.app.proceso_seleccionado)}  {self.app.proceso_seleccionado}   ▼"
                    )
                except Exception:
                    pass

            def seleccionar(self, proc):
                self.app.seleccionar_proceso(proc)
                self.cerrar()

            def actualizar_seleccion(self, proc):
                self.btn_principal.configure(
                    text=f"{self.app._obtener_icono_proceso(proc)}  {proc}   ▼"
                )

            def configure_state(self, state):
                self.btn_principal.configure(state=state)
                if state == "disabled":
                    self.cerrar()

        # Proxy para compatibilidad con código existente que use self.opt_proceso
        class SelectorProcesoProxy:
            def __init__(self, app):
                self.app = app
            def get(self):
                return self.app.proceso_seleccionado
            def set(self, valor):
                self.app.seleccionar_proceso(valor)
            def configure(self, **kwargs):
                state = kwargs.get("state")
                if state and hasattr(self.app, "dropdown_menu"):
                    self.app.dropdown_menu.configure_state(state)

        self.opt_proceso = SelectorProcesoProxy(self)

        # ======================================================================
        # 1. CABECERA PRINCIPAL SUPERIOR (MC PROCESOS INTEGRALES - TIPOGRAFÍA NATIVA NÍTIDA)
        # ======================================================================
        frame_header = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=0
        )
        frame_header.pack(fill="x", padx=14, pady=(10, 8))
        frame_header.grid_columnconfigure(1, weight=1)

        # 1A. Isotipo / Logotipo Oficial y Marca Corporativa
        frame_brand = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_brand.grid(row=0, column=0, padx=12, pady=5, sticky="w")

        if getattr(self, 'img_logo_mc', None):
            lbl_logo_mc = ctk.CTkLabel(frame_brand, image=self.img_logo_mc, text="")
            lbl_logo_mc.pack(side="left", padx=(0, 10))

        frame_brand_text = ctk.CTkFrame(frame_brand, fg_color="transparent")
        frame_brand_text.pack(side="left")

        # Fila 1: MC PROCESOS INTEGRALES
        row_title_brand = ctk.CTkFrame(frame_brand_text, fg_color="transparent")
        row_title_brand.pack(anchor="w")

        lbl_mc = ctk.CTkLabel(
            row_title_brand,
            text="MC",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#DC2626"
        )
        lbl_mc.pack(side="left", padx=(0, 5))

        lbl_pi = ctk.CTkLabel(
            row_title_brand,
            text="PROCESOS INTEGRALES",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#6D28D9"
        )
        lbl_pi.pack(side="left")

        # Fila 2: Subtítulo
        lbl_brand_sub = ctk.CTkLabel(
            frame_brand_text,
            text="Automatización & Inteligencia Sanitaria",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#1E293B"
        )
        lbl_brand_sub.pack(anchor="w", pady=(1, 1))

        # Fila 3: Servicios y Alcance
        lbl_brand_scope = ctk.CTkLabel(
            frame_brand_text,
            text="Trámites · Análisis técnico · Certificaciones · Auditorías · Sistemas de gestión",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#64748B"
        )
        lbl_brand_scope.pack(anchor="w")

        # 1B. Lema Central: "Ciencia que impulsa cumplimiento"
        frame_slogan = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_slogan.grid(row=0, column=1, padx=12, pady=5, sticky="e")

        lbl_slogan_top = ctk.CTkLabel(
            frame_slogan,
            text="Ciencia que\nimpulsa cumplimiento",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic", weight="bold"),
            text_color="#1E1B4B",
            justify="right"
        )
        lbl_slogan_top.pack(anchor="e")

        frame_accent_line = ctk.CTkFrame(frame_slogan, fg_color="#DC2626", height=2, width=120, corner_radius=1)
        frame_accent_line.pack(anchor="e", pady=(2, 0))

        # 1C. Acciones Rápidas (Estado, Manual, Chrome, Ayuda)
        frame_header_actions = ctk.CTkFrame(frame_header, fg_color="transparent")
        frame_header_actions.grid(row=0, column=2, padx=12, pady=5, sticky="e")

        self.badge_estado = ctk.CTkLabel(
            frame_header_actions,
            text="● Sistema listo",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#059669",
            fg_color="#ECFDF5",
            corner_radius=12,
            padx=14,
            pady=4
        )
        self.badge_estado.pack(side="left", padx=3)

        btn_manual = ctk.CTkButton(
            frame_header_actions,
            text="📖 Manual",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F5F3FF",
            text_color="#334155",
            border_color="#CBD5E1",
            border_width=1,
            height=28,
            width=80,
            corner_radius=6,
            command=self.mostrar_modal_manual
        )
        btn_manual.pack(side="left", padx=2)

        btn_chrome = ctk.CTkButton(
            frame_header_actions,
            text="🌐 Chrome Bot",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F5F3FF",
            text_color="#334155",
            border_color="#CBD5E1",
            border_width=1,
            height=28,
            width=100,
            corner_radius=6,
            command=lambda: abrir_chrome_automatizado(self)
        )
        btn_chrome.pack(side="left", padx=2)

        btn_ayuda = ctk.CTkButton(
            frame_header_actions,
            text="❓ Ayuda",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#FFFFFF",
            hover_color="#F5F3FF",
            text_color="#334155",
            border_color="#CBD5E1",
            border_width=1,
            height=28,
            width=75,
            corner_radius=6,
            command=self.mostrar_modal_ayuda
        )
        btn_ayuda.pack(side="left", padx=2)

        # ======================================================================
        # 2. CONTENEDOR PRINCIPAL EN DOS COLUMNAS INDEPENDIENTES
        # ======================================================================
        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        frame_main.grid_columnconfigure(0, weight=3)
        frame_main.grid_columnconfigure(1, weight=1)
        frame_main.grid_rowconfigure(0, weight=1)

        col_left = ctk.CTkScrollableFrame(
            frame_main,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#C4B5FD",
            scrollbar_button_hover_color="#7D51E9",
            scrollbar_fg_color="#F1F5F9"
        )
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        col_right = ctk.CTkFrame(frame_main, fg_color="transparent")
        col_right.grid(row=0, column=1, sticky="nsew")

        # ----------------------------------------------------------------------
        # 2A. TARJETA 1 (COL IZQ): CONTROLES Y CONFIGURACIÓN DEL TRÁMITE
        # ----------------------------------------------------------------------
        card_controls = ctk.CTkFrame(
            col_left,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=0
        )
        card_controls.pack(fill="x", pady=(0, 8))
        card_controls.grid_columnconfigure(0, weight=1)

        # Banner Interno Automatizador INVIMA con Ícono
        frame_bot_title = ctk.CTkFrame(card_controls, fg_color="transparent")
        frame_bot_title.grid(row=0, column=0, padx=12, pady=(6, 2), sticky="ew")
        frame_bot_title.grid_columnconfigure(0, weight=1)

        frame_bot_title_left = ctk.CTkFrame(frame_bot_title, fg_color="transparent")
        frame_bot_title_left.pack(side="left")

        if getattr(self, 'img_doc_badge', None):
            lbl_doc_badge_img = ctk.CTkLabel(frame_bot_title_left, image=self.img_doc_badge, text="")
            lbl_doc_badge_img.pack(side="left", padx=(0, 8))

        frame_bot_text_box = ctk.CTkFrame(frame_bot_title_left, fg_color="transparent")
        frame_bot_text_box.pack(side="left")

        lbl_app_name = ctk.CTkLabel(
            frame_bot_text_box,
            text="Automatizador INVIMA",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_app_name.pack(anchor="w")

        lbl_app_desc = ctk.CTkLabel(
            frame_bot_text_box,
            text="Digitaliza, valida y registra la información de tus trámites de forma ágil y segura",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748B"
        )
        lbl_app_desc.pack(anchor="w")

        self.badge_modulo_activo = ctk.CTkLabel(
            frame_bot_title,
            text="● Módulo activo",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#059669",
            fg_color="#ECFDF5",
            corner_radius=12,
            padx=14,
            pady=4
        )
        self.badge_modulo_activo.pack(side="right")

        # Barra de 3 Pasos (Wizard Visual Dinámico)
        frame_wizard = ctk.CTkFrame(card_controls, fg_color="#F8FAFC", corner_radius=8, border_width=0)
        frame_wizard.grid(row=1, column=0, padx=12, pady=(2, 3), sticky="ew")
        frame_wizard.grid_columnconfigure((0, 1, 2), weight=1)

        # Paso 1: Selecciona el proceso
        frame_s1 = ctk.CTkFrame(frame_wizard, fg_color="transparent")
        frame_s1.grid(row=0, column=0, padx=8, pady=4, sticky="w")
        self.badge_step1 = ctk.CTkLabel(
            frame_s1,
            image=self.img_s1_active if self.img_s1_active else None,
            text="" if self.img_s1_active else "✓",
            width=28,
            height=28
        )
        self.badge_step1.pack(side="left", padx=(0, 6))
        f_s1_txt = ctk.CTkFrame(frame_s1, fg_color="transparent")
        f_s1_txt.pack(side="left")
        ctk.CTkLabel(f_s1_txt, text="1. Selecciona el proceso", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color="#1E1B4B").pack(anchor="w")
        ctk.CTkLabel(f_s1_txt, text="Elige el requisito a procesar", font=ctk.CTkFont(family="Segoe UI", size=9), text_color="#64748B").pack(anchor="w")

        # Paso 2: Carga tu archivo
        frame_s2 = ctk.CTkFrame(frame_wizard, fg_color="transparent")
        frame_s2.grid(row=0, column=1, padx=8, pady=4, sticky="w")
        self.badge_step2 = ctk.CTkLabel(
            frame_s2,
            image=self.img_s2_inactive if self.img_s2_inactive else None,
            text="" if self.img_s2_inactive else "2",
            width=28,
            height=28
        )
        self.badge_step2.pack(side="left", padx=(0, 6))
        f_s2_txt = ctk.CTkFrame(frame_s2, fg_color="transparent")
        f_s2_txt.pack(side="left")
        ctk.CTkLabel(f_s2_txt, text="2. Carga tu archivo", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color="#1E1B4B").pack(anchor="w")
        ctk.CTkLabel(f_s2_txt, text="Usa la plantilla oficial Excel", font=ctk.CTkFont(family="Segoe UI", size=9), text_color="#64748B").pack(anchor="w")

        # Paso 3: Inicia automatización
        frame_s3 = ctk.CTkFrame(frame_wizard, fg_color="transparent")
        frame_s3.grid(row=0, column=2, padx=8, pady=4, sticky="w")
        self.badge_step3 = ctk.CTkLabel(
            frame_s3,
            image=self.img_s3_inactive if self.img_s3_inactive else None,
            text="" if self.img_s3_inactive else "3",
            width=28,
            height=28
        )
        self.badge_step3.pack(side="left", padx=(0, 6))
        f_s3_txt = ctk.CTkFrame(frame_s3, fg_color="transparent")
        f_s3_txt.pack(side="left")
        ctk.CTkLabel(f_s3_txt, text="3. Inicia automatización", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color="#1E1B4B").pack(anchor="w")
        ctk.CTkLabel(f_s3_txt, text="El sistema procesará en INVIMA", font=ctk.CTkFont(family="Segoe UI", size=9), text_color="#64748B").pack(anchor="w")

        # FILA: DESCARGA DE PLANTILLA (IZQUIERDA) + REQUISITO A PROCESAR (DERECHA)
        frame_proc_row = ctk.CTkFrame(card_controls, fg_color="transparent")
        frame_proc_row.grid(row=2, column=0, padx=12, pady=(2, 3), sticky="ew")
        frame_proc_row.grid_columnconfigure(0, weight=2)
        frame_proc_row.grid_columnconfigure(1, weight=3)

        # Columna Izquierda: Tarjeta de Descarga de Plantilla Oficial
        frame_template_card = ctk.CTkFrame(frame_proc_row, fg_color="#FAF5FF", corner_radius=8, border_width=0)
        frame_template_card.grid(row=0, column=0, padx=(0, 4), sticky="nsew")

        lbl_tmpl_title = ctk.CTkLabel(
            frame_template_card,
            text="📥 Plantilla de Trabajo Oficial",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#6D28D9"
        )
        lbl_tmpl_title.pack(anchor="w", padx=10, pady=(4, 1))

        lbl_tmpl_desc = ctk.CTkLabel(
            frame_template_card,
            text="Excel prediseñado con las 6 hojas y columnas exactas.",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#7C3AED"
        )
        lbl_tmpl_desc.pack(anchor="w", padx=10, pady=(0, 2))

        btn_download_tmpl = ctk.CTkButton(
            frame_template_card,
            text="💾 Descargar Plantilla Excel",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#7D51E9",
            hover_color="#6D28D9",
            text_color="#FFFFFF",
            height=28,
            corner_radius=6,
            command=self.generar_o_descargar_plantilla
        )
        btn_download_tmpl.pack(fill="x", padx=8, pady=(1, 4))

        # Columna Derecha: Requisito a Procesar
        frame_proc_right = ctk.CTkFrame(frame_proc_row, fg_color="#F8FAFC", corner_radius=8, border_width=0)
        frame_proc_right.grid(row=0, column=1, padx=(4, 0), sticky="nsew")

        lbl_req_title = ctk.CTkLabel(
            frame_proc_right,
            text="📋 REQUISITO A PROCESAR",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_req_title.pack(anchor="w", padx=10, pady=(4, 1))

        self.dropdown_menu = ModernFloatingDropdown(frame_proc_right, self, lista_procesos)
        self.dropdown_menu.pack(fill="x", padx=8, pady=(0, 1))

        frame_info_hoja_box = ctk.CTkFrame(frame_proc_right, fg_color="transparent")
        frame_info_hoja_box.pack(fill="x", padx=10, pady=(0, 4))

        self.lbl_info_hoja = ctk.CTkLabel(
            frame_info_hoja_box,
            text=f"📌 Hoja en Excel: '{self._obtener_hoja_actual()}'",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#7D51E9"
        )
        self.lbl_info_hoja.pack(side="left")

        self.lbl_info_campos = ctk.CTkLabel(
            frame_info_hoja_box,
            text=f"🧪 {self._obtener_info_campos()}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#059669"
        )
        self.lbl_info_campos.pack(side="right")

        # FILA: CARGA DE ARCHIVO EXCEL
        frame_file_card = ctk.CTkFrame(card_controls, fg_color="#F8FAFC", corner_radius=8, border_width=0)
        frame_file_card.grid(row=3, column=0, padx=12, pady=(2, 3), sticky="ew")
        frame_file_card.grid_columnconfigure(0, weight=1)

        frame_file_header = ctk.CTkFrame(frame_file_card, fg_color="transparent")
        frame_file_header.pack(fill="x", padx=10, pady=(4, 1))

        lbl_file_header = ctk.CTkLabel(
            frame_file_header,
            text="📁 Archivo Excel de entrada",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#334155"
        )
        lbl_file_header.pack(side="left")

        lbl_file_drag_hint = ctk.CTkLabel(
            frame_file_header,
            text="Arrastra tu archivo Excel aquí o haz clic para seleccionar",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#64748B"
        )
        lbl_file_drag_hint.pack(side="right")

        frame_file_input = ctk.CTkFrame(frame_file_card, fg_color="transparent")
        frame_file_input.pack(fill="x", padx=8, pady=(1, 2))
        frame_file_input.grid_columnconfigure(0, weight=1)

        self.entry_path = ctk.CTkEntry(
            frame_file_input,
            placeholder_text="Haz clic en 'Seleccionar archivo' para cargar tu matriz de datos...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=32,
            fg_color="#FFFFFF",
            border_color="#CBD5E1",
            text_color="#0F172A",
            corner_radius=6
        )
        self.entry_path.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_browse = ctk.CTkButton(
            frame_file_input,
            text="📂 Seleccionar archivo",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#7D51E9",
            hover_color="#6D28D9",
            text_color="#FFFFFF",
            height=32,
            corner_radius=6,
            command=self.seleccionar_excel
        )
        self.btn_browse.grid(row=0, column=1)

        lbl_formats_hint = ctk.CTkLabel(
            frame_file_card,
            text="Formatos admitidos: .xlsx · .xls  |  Usa la plantilla oficial para mejores resultados",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#94A3B8"
        )
        lbl_formats_hint.pack(anchor="w", padx=10, pady=(0, 4))

        # FILA 4: SELECCIÓN MANUAL DE FUNCIÓN (INTERRUPTOR RECTANGULAR FLUIDO)
        frame_manual_card = ctk.CTkFrame(card_controls, fg_color="#F8FAFC", corner_radius=8, border_width=0)
        frame_manual_card.grid(row=4, column=0, padx=12, pady=(2, 3), sticky="ew")
        frame_manual_card.grid_columnconfigure(0, weight=1)

        frame_manual_inner = ctk.CTkFrame(frame_manual_card, fg_color="transparent")
        frame_manual_inner.pack(fill="x", padx=10, pady=5)

        frame_manual_left = ctk.CTkFrame(frame_manual_inner, fg_color="transparent")
        frame_manual_left.pack(side="left", fill="both", expand=True)

        lbl_manual_title = ctk.CTkLabel(
            frame_manual_left,
            text="🖐️ Selección manual para 'Función'",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_manual_title.pack(anchor="w")

        self.lbl_manual_sub = ctk.CTkLabel(
            frame_manual_left,
            text="Pausa en cada ingrediente para elegir funciones directamente en el portal",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#64748B"
        )
        self.lbl_manual_sub.pack(anchor="w")

        self.sw_manual_funcion = ElegantRectSwitch(
            frame_manual_inner,
            width=230,
            height=34,
            command=self._on_switch_manual_toggled
        )
        self.sw_manual_funcion.pack(side="right")

        # FILA 5: BOTONES DE ACCIÓN (INICIAR, PAUSAR, DETENER)
        frame_actions = ctk.CTkFrame(card_controls, fg_color="transparent")
        frame_actions.grid(row=5, column=0, padx=12, pady=(2, 4), sticky="ew")
        frame_actions.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_comenzar = ctk.CTkButton(
            frame_actions,
            text="▶ Iniciar automatización",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#0DBE8A",
            hover_color="#0AA779",
            text_color="#FFFFFF",
            height=36,
            corner_radius=6,
            command=self.action_comenzar_reanudar
        )
        self.btn_comenzar.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_pausar = ctk.CTkButton(
            frame_actions,
            text="⏸ Pausar",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#F5C495",
            hover_color="#EBB682",
            text_color="#78350F",
            border_color="#FCD34D",
            border_width=1,
            height=36,
            corner_radius=6,
            state="disabled",
            command=self.action_pausar
        )
        self.btn_pausar.grid(row=0, column=1, padx=2, sticky="ew")

        self.btn_detener = ctk.CTkButton(
            frame_actions,
            text="⏹ Detener",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#EE7B9D",
            hover_color="#E06A8D",
            text_color="#831843",
            border_color="#FCA5A5",
            border_width=1,
            height=36,
            corner_radius=6,
            state="disabled",
            command=self.action_detener
        )
        self.btn_detener.grid(row=0, column=2, padx=(4, 0), sticky="ew")

        # FILA 6: BANNER INTERACTIVO DE ESPERA MANUAL (SE ACTIVA DINÁMICAMENTE)
        self.frame_manual_waiting = ctk.CTkFrame(card_controls, fg_color="#EDE9FE", corner_radius=8, border_width=1, border_color="#7D51E9")
        frame_wait_inner = ctk.CTkFrame(self.frame_manual_waiting, fg_color="transparent")
        frame_wait_inner.pack(fill="x", padx=10, pady=5)
        frame_wait_inner.grid_columnconfigure(0, weight=1)

        f_wait_txt = ctk.CTkFrame(frame_wait_inner, fg_color="transparent")
        f_wait_txt.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            f_wait_txt,
            text="🖐️ Esperando selección manual de Función...",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#5B21B6"
        ).pack(anchor="w")
        ctk.CTkLabel(
            f_wait_txt,
            text="Selecciona en Chrome y pulsa Continuar, o Descartar para cancelar este ingrediente.",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#6D28D9"
        ).pack(anchor="w")

        f_wait_btns = ctk.CTkFrame(frame_wait_inner, fg_color="transparent")
        f_wait_btns.grid(row=0, column=1, sticky="e")

        self.btn_confirmar_manual = ctk.CTkButton(
            f_wait_btns,
            text="🟢 Continuar ▶",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#0DBE8A",
            hover_color="#0AA779",
            text_color="#FFFFFF",
            height=28,
            width=105,
            corner_radius=6,
            command=self.confirmar_manual
        )
        self.btn_confirmar_manual.pack(side="left", padx=(0, 6))

        self.btn_descartar_manual = ctk.CTkButton(
            f_wait_btns,
            text="🛑 Descartar",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="#FFFFFF",
            height=28,
            width=95,
            corner_radius=6,
            command=self.descartar_manual
        )
        self.btn_descartar_manual.pack(side="left")

        # ----------------------------------------------------------------------
        # 2B. TARJETA 2 (COL IZQ): EJECUCIÓN EN PROCESO Y TELEMETRÍA
        # ----------------------------------------------------------------------
        card_telemetry = ctk.CTkFrame(
            col_left,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=0
        )
        card_telemetry.pack(fill="x", pady=(0, 8))
        card_telemetry.grid_columnconfigure((0, 1, 2), weight=1)

        frame_progress_header = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        frame_progress_header.grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 2), sticky="ew")

        lbl_telemetry_title = ctk.CTkLabel(
            frame_progress_header,
            text="📊  Ejecución en proceso",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_telemetry_title.pack(side="left")

        self.lbl_porcentaje = ctk.CTkLabel(
            frame_progress_header,
            text="0%",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#FFFFFF",
            fg_color="#7D51E9",
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_porcentaje.pack(side="right")

        self.lbl_metric_filas = ctk.CTkLabel(
            frame_progress_header,
            text="Progreso general: 0 / 0 registros",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748B"
        )
        self.lbl_metric_filas.pack(side="right", padx=8)

        self.progress_bar = ctk.CTkProgressBar(
            card_telemetry,
            height=7,
            corner_radius=3,
            progress_color="#0DBE8A",
            fg_color="#F1F5F9"
        )
        self.progress_bar.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 5), sticky="ew")
        self.progress_bar.set(0.0)

        # 3 Tarjetas de Métricas Ejecutivas
        frame_cards = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        frame_cards.grid(row=2, column=0, columnspan=3, padx=8, pady=(0, 5), sticky="ew")
        frame_cards.grid_columnconfigure((0, 1, 2), weight=1)

        card_p = ctk.CTkFrame(frame_cards, fg_color="#F8FAFC", corner_radius=6, border_width=0)
        card_p.grid(row=0, column=0, padx=2, sticky="ew")
        lbl_p_tag = ctk.CTkLabel(card_p, text="📄 Total procesados", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="#64748B")
        lbl_p_tag.pack(anchor="w", padx=8, pady=(4, 0))
        self.lbl_metric_procesados_val = ctk.CTkLabel(card_p, text="0", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#1E1B4B")
        self.lbl_metric_procesados_val.pack(anchor="w", padx=8, pady=(0, 4))

        card_ok = ctk.CTkFrame(frame_cards, fg_color="#F0FDF4", corner_radius=6, border_width=0)
        card_ok.grid(row=0, column=1, padx=2, sticky="ew")
        lbl_ok_tag = ctk.CTkLabel(card_ok, text="✅ Guardados con éxito", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="#15803D")
        lbl_ok_tag.pack(anchor="w", padx=8, pady=(4, 0))
        self.lbl_metric_exitos_val = ctk.CTkLabel(card_ok, text="0", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#059669")
        self.lbl_metric_exitos_val.pack(anchor="w", padx=8, pady=(0, 4))

        card_err = ctk.CTkFrame(frame_cards, fg_color="#FEF2F2", corner_radius=6, border_width=0)
        card_err.grid(row=0, column=2, padx=2, sticky="ew")
        lbl_err_tag = ctk.CTkLabel(card_err, text="⚠️ Alertas / Revisión", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="#B91C1C")
        lbl_err_tag.pack(anchor="w", padx=8, pady=(4, 0))
        self.lbl_metric_errores_val = ctk.CTkLabel(card_err, text="0", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#DC2626")
        self.lbl_metric_errores_val.pack(anchor="w", padx=8, pady=(0, 4))

        self.lbl_metric_exitos = self.lbl_metric_exitos_val
        self.lbl_metric_errores = self.lbl_metric_errores_val

        # ----------------------------------------------------------------------
        # 2C. TARJETA 3 (COL IZQ): CONSOLA DE TRAZABILIDAD (MÁXIMO ESPACIO VERTICAL)
        # ----------------------------------------------------------------------
        card_log = ctk.CTkFrame(
            col_left,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=0
        )
        card_log.pack(fill="x", pady=(0, 6))
        card_log.grid_columnconfigure(0, weight=1)
        card_log.grid_rowconfigure(1, weight=1)

        frame_log_header = ctk.CTkFrame(card_log, fg_color="transparent")
        frame_log_header.grid(row=0, column=0, padx=8, pady=(4, 2), sticky="ew")

        lbl_log_title = ctk.CTkLabel(
            frame_log_header,
            text="📋 Trazabilidad del proceso",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_log_title.pack(side="left")

        btn_limpiar = ctk.CTkButton(
            frame_log_header,
            text="🗑 Limpiar",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#475569",
            border_color="#CBD5E1",
            border_width=1,
            height=22,
            width=60,
            corner_radius=4,
            command=self.limpiar_consola
        )
        btn_limpiar.pack(side="right", padx=(4, 0))

        btn_export = ctk.CTkButton(
            frame_log_header,
            text="📥 Exportar reporte",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="#F1F5F9",
            hover_color="#E2E8F0",
            text_color="#475569",
            border_color="#CBD5E1",
            border_width=1,
            height=22,
            width=100,
            corner_radius=4,
            command=self.exportar_reporte
        )
        btn_export.pack(side="right")

        self.txt_log = ctk.CTkTextbox(
            card_log,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color="#0F172A",
            text_color="#38BDF8",
            corner_radius=6,
            border_width=0,
            height=260
        )
        self.txt_log.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="nsew")

        # ----------------------------------------------------------------------
        # 2D. TARJETAS DERECHAS (Servicios MC + Ayuda Flotante Compacta)
        # ----------------------------------------------------------------------

        # 1. Tarjeta Blanca de Servicios MC
        frame_services_card = ctk.CTkFrame(
            col_right,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=0
        )
        frame_services_card.pack(fill="x", pady=(0, 8))

        # Título y Subtítulo de la Sección de Servicios
        lbl_side_title = ctk.CTkLabel(
            frame_services_card,
            text="Servicios MC Procesos Integrales",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_side_title.pack(anchor="w", padx=10, pady=(6, 0))

        lbl_side_desc = ctk.CTkLabel(
            frame_services_card,
            text="Áreas de consultoría y gestión especializada",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#64748B"
        )
        lbl_side_desc.pack(anchor="w", padx=10, pady=(0, 3))

        # Lista de 5 Servicios
        servicios_data = [
            ("srv_tramites", "Trámites sanitarios", "Cosméticos, dispositivos médicos, aseo y más"),
            ("srv_analisis", "Análisis técnicos", "Soporte científico y regulatorio"),
            ("srv_certificacion", "Certificación de plantas", "BPM e ISO 22716"),
            ("srv_auditorias", "Auditorías internas", "Diagnóstico y planes de acción"),
            ("srv_automatizacion", "Diseño y automatización", "Sistemas de gestión más eficientes")
        ]

        for icon_key, titulo, desc in servicios_data:
            card_srv = ctk.CTkFrame(
                frame_services_card,
                fg_color="#F8FAFC",
                corner_radius=6,
                border_width=0
            )
            card_srv.pack(fill="x", padx=6, pady=2)

            row_srv = ctk.CTkFrame(card_srv, fg_color="transparent")
            row_srv.pack(fill="x", padx=6, pady=3)
            row_srv.grid_columnconfigure(1, weight=1)

            img_ico = self.iconos_servicios.get(icon_key)
            if img_ico:
                lbl_ico = ctk.CTkLabel(row_srv, image=img_ico, text="")
                lbl_ico.grid(row=0, column=0, rowspan=2, padx=(0, 8), sticky="nw")

            col_pos = 1 if img_ico else 0
            lbl_t = ctk.CTkLabel(
                row_srv,
                text=titulo,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color="#1E1B4B",
                anchor="w"
            )
            lbl_t.grid(row=0, column=col_pos, sticky="w")

            lbl_d = ctk.CTkLabel(
                row_srv,
                text=desc,
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color="#64748B",
                wraplength=190,
                justify="left",
                anchor="w"
            )
            lbl_d.grid(row=1, column=col_pos, sticky="w", pady=(1, 0))

        # Frase: "Tu aliado en la ruta regulatoria" con línea roja
        frame_slogan_mid = ctk.CTkFrame(frame_services_card, fg_color="transparent")
        frame_slogan_mid.pack(pady=(4, 6))

        lbl_slogan_mid = ctk.CTkLabel(
            frame_slogan_mid,
            text="Tu aliado en la ruta regulatoria",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic", weight="bold"),
            text_color="#1E1B4B"
        )
        lbl_slogan_mid.pack(anchor="center")

        frame_accent_mid = ctk.CTkFrame(frame_slogan_mid, fg_color="#DC2626", height=2, width=130, corner_radius=1)
        frame_accent_mid.pack(anchor="center", pady=(2, 0))

        # 2. Tarjeta Flotante: "¿Necesitas ayuda?" (Compacta)
        card_help_floating = ctk.CTkFrame(
            col_right,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=0
        )
        card_help_floating.pack(fill="x", pady=0)

        lbl_help_h = ctk.CTkLabel(
            card_help_floating,
            text="🎧 ¿Necesitas ayuda?",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#5B21B6"
        )
        lbl_help_h.pack(anchor="w", padx=10, pady=(6, 1))

        lbl_help_p = ctk.CTkLabel(
            card_help_floating,
            text="Nuestro equipo especializado te acompaña en cada proceso.",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#7C3AED",
            wraplength=240,
            justify="left"
        )
        lbl_help_p.pack(anchor="w", padx=10, pady=(0, 4))

        btn_contact = ctk.CTkButton(
            card_help_floating,
            text="💬 Contactar soporte",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#7D51E9",
            hover_color="#6D28D9",
            text_color="#FFFFFF",
            height=28,
            corner_radius=6,
            command=self.mostrar_modal_ayuda
        )
        btn_contact.pack(fill="x", padx=10, pady=(0, 6))

        self.actualizar_estado_wizard()

    def actualizar_estado_wizard(self):
        try:
            # Paso 1: Selecciona el proceso
            if getattr(self, 'proceso_seleccionado', None):
                if self.img_s1_active:
                    self.badge_step1.configure(image=self.img_s1_active, text="")
                else:
                    self.badge_step1.configure(text="✓", fg_color="#7D51E9", text_color="#FFFFFF")
            else:
                if self.img_s1_inactive:
                    self.badge_step1.configure(image=self.img_s1_inactive, text="")
                else:
                    self.badge_step1.configure(text="1", fg_color="#FFFFFF", text_color="#7D51E9")

            # Paso 2: Carga tu archivo Excel
            if getattr(self, 'ruta_excel', None) and os.path.exists(self.ruta_excel):
                if self.img_s2_active:
                    self.badge_step2.configure(image=self.img_s2_active, text="")
                else:
                    self.badge_step2.configure(text="✓", fg_color="#7D51E9", text_color="#FFFFFF")
            else:
                if self.img_s2_inactive:
                    self.badge_step2.configure(image=self.img_s2_inactive, text="")
                else:
                    self.badge_step2.configure(text="2", fg_color="#FFFFFF", text_color="#7D51E9")

            # Paso 3: Inicia automatización
            if self.en_ejecucion or (self.num_exitos > 0 or self.num_errores > 0):
                if self.img_s3_active:
                    self.badge_step3.configure(image=self.img_s3_active, text="")
                else:
                    self.badge_step3.configure(text="✓", fg_color="#0DBE8A", text_color="#FFFFFF")
            else:
                if self.img_s3_inactive:
                    self.badge_step3.configure(image=self.img_s3_inactive, text="")
                else:
                    self.badge_step3.configure(text="3", fg_color="#FFFFFF", text_color="#7D51E9")
        except Exception:
            pass

    def on_proceso_changed(self, nuevo_proceso):
        self.cfg = cargar_config_dinamico()
        hoja_req = self._obtener_hoja_actual()
        campos_info = self._obtener_info_campos()
        if hasattr(self, 'lbl_info_hoja'):
            self.lbl_info_hoja.configure(text=f"📌 Hoja en Excel: '{hoja_req}'")
        if hasattr(self, 'lbl_info_campos'):
            self.lbl_info_campos.configure(text=f"🧪 {campos_info}")
        self.log(f"🔄 Requisito seleccionado: '{nuevo_proceso}' (Hoja requerida: '{hoja_req}')", "info")

        # Limpiar datos anteriores
        self.progress_bar.set(0.0)
        self.num_exitos = 0
        self.num_errores = 0
        if hasattr(self, 'lbl_metric_filas'):
            self.lbl_metric_filas.configure(text="Progreso general: 0 / 0 registros")
        if hasattr(self, 'lbl_porcentaje'):
            self.lbl_porcentaje.configure(text="0%")
        if hasattr(self, 'lbl_metric_procesados_val'):
            self.lbl_metric_procesados_val.configure(text="0")
        if hasattr(self, 'lbl_metric_exitos_val'):
            self.lbl_metric_exitos_val.configure(text="0")
        if hasattr(self, 'lbl_metric_errores_val'):
            self.lbl_metric_errores_val.configure(text="0")
        self.actualizar_estado_wizard()

    def set_estado_badge(self, texto, color_bg, color_txt="#FFFFFF"):
        if hasattr(self, 'badge_modulo_activo'):
            self.badge_modulo_activo.configure(text=f"● {texto}", fg_color=color_bg, text_color=color_txt)
        if hasattr(self, 'badge_estado'):
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
            self.actualizar_estado_wizard()

    def actualizar_progreso(self, actual, total):
        porcentaje = actual / total if total > 0 else 0
        def _update():
            try:
                self.progress_bar.set(porcentaje)
                self.lbl_porcentaje.configure(text=f"{int(porcentaje * 100)}%")
                self.lbl_metric_filas.configure(text=f"Progreso general: {actual} / {total} registros")
                self.lbl_metric_procesados_val.configure(text=str(actual))
                self.actualizar_estado_wizard()
            except Exception:
                pass
        self.after(0, _update)

    def incrementar_exitos(self):
        self.num_exitos += 1
        def _update():
            try:
                self.lbl_metric_exitos_val.configure(text=str(self.num_exitos))
                self.lbl_metric_procesados_val.configure(text=str(self.num_exitos + self.num_errores))
                self.actualizar_estado_wizard()
            except Exception:
                pass
        self.after(0, _update)

    def incrementar_errores(self):
        self.num_errores += 1
        def _update():
            try:
                self.lbl_metric_errores_val.configure(text=str(self.num_errores))
                self.lbl_metric_procesados_val.configure(text=str(self.num_exitos + self.num_errores))
                self.actualizar_estado_wizard()
            except Exception:
                pass
        self.after(0, _update)

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
            self.lbl_metric_exitos_val.configure(text="0")
            self.lbl_metric_errores_val.configure(text="0")
            self.lbl_metric_procesados_val.configure(text="0")
            self.lbl_porcentaje.configure(text="0%")

            self.btn_browse.configure(state="disabled")
            self.opt_proceso.configure(state="disabled")
            self.btn_comenzar.configure(text="🚀 Ejecutando...", fg_color="#0DBE8A", state="disabled")
            self.btn_pausar.configure(state="normal", text="⏸️ Pausar", fg_color="#F5C495")
            self.btn_detener.configure(state="normal")
            self.set_estado_badge("Ejecutando...", "#059669")
            self.actualizar_estado_wizard()

            threading.Thread(target=ejecutar, args=(self.ruta_excel, nombre_proceso, self), daemon=True).start()

        elif self.debe_pausar:
            self.debe_pausar = False
            self.btn_comenzar.configure(text="🚀 Ejecutando...", fg_color="#0DBE8A", state="disabled")
            self.btn_pausar.configure(text="⏸️ Pausar", fg_color="#F5C495")
            self.set_estado_badge("Ejecutando...", "#059669")
            self.log("▶️ Proceso reanudado por el usuario.", "info")
            self.actualizar_estado_wizard()

    def action_pausar(self):
        if self.en_ejecucion and not self.debe_pausar:
            self.debe_pausar = True
            self.btn_pausar.configure(text="▶️ Reanudar", fg_color="#0DBE8A")
            self.btn_comenzar.configure(text="▶️ Reanudar", fg_color="#0DBE8A", state="normal")
            self.set_estado_badge("Pausado", "#D97706")
            self.log("⏸️ Proceso pausado. Haz clic en 'Reanudar' para continuar.", "warning")

    def action_detener(self):
        if self.en_ejecucion:
            self.debe_detener = True
            self.debe_pausar = False
            self.set_estado_badge("Deteniendo...", "#DC2626")
            self.log("🛑 Cancelando proceso... Espere a finalizar la fila actual.", "warning")

    def _on_switch_manual_toggled(self):
        activo = bool(self.sw_manual_funcion.get())
        self.modo_manual_funcion = activo
        if activo:
            if hasattr(self, 'lbl_manual_sub'):
                self.lbl_manual_sub.configure(text="Activo: El bot pausará en cada ingrediente para elegir funciones en el portal")
            self.log("🖐️ Selección manual para 'Función' ACTIVADA: El bot pausará en cada ingrediente para que elijas las funciones en el portal.", "info")
        else:
            if hasattr(self, 'lbl_manual_sub'):
                self.lbl_manual_sub.configure(text="Pausa en cada ingrediente para elegir funciones directamente en el portal")
            self.log("⚡ Selección automática para 'Función' ACTIVADA: El bot seleccionará automáticamente según el Excel.", "info")

    def activar_espera_manual_ui(self, visible):
        def _gui():
            try:
                if hasattr(self, 'frame_manual_waiting'):
                    if visible:
                        self.frame_manual_waiting.grid(row=6, column=0, padx=12, pady=(2, 4), sticky="ew")
                    else:
                        self.frame_manual_waiting.grid_forget()
            except Exception:
                pass
        self.after(0, _gui)

    def confirmar_manual(self):
        self.confirmar_manual_listo = True
        self.log("▶️ Continuando con el ingrediente actual...", "detail")

    def descartar_manual(self):
        self.cancelar_ingrediente_actual = True
        self.confirmar_manual_listo = True
        self.log("🛑 Ingrediente descartado por el usuario.", "warning")

    def finalizar_proceso(self, exito=True):
        self.en_ejecucion = False
        self.debe_pausar = False
        self.debe_detener = False
        self.activar_espera_manual_ui(False)

        self.btn_browse.configure(state="normal")
        self.opt_proceso.configure(state="normal")
        self.btn_comenzar.configure(text="▶ Iniciar automatización", fg_color="#0DBE8A", state="normal")
        self.btn_pausar.configure(text="⏸ Pausar", fg_color="#F5C495", state="disabled")
        self.btn_detener.configure(state="disabled")

        texto_badge_actual = self.badge_estado.cget("text").lower() if hasattr(self, 'badge_estado') else ""
        if "deteni" in texto_badge_actual or "detenido" in texto_badge_actual:
            self.set_estado_badge("Detenido", "#DC2626")
        elif exito:
            self.set_estado_badge("Completado", "#0DBE8A")
        else:
            self.set_estado_badge("Finalizado con errores", "#EF4444")
        self.actualizar_estado_wizard()


if __name__ == "__main__":
    app = App()
    app.mainloop()

