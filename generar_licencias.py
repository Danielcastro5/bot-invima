# ==========================================================================
#  GENERADOR DE LICENCIAS INDIVIDUALES (1 PUESTO POR LICENCIA) - BOT INVIMA
# ==========================================================================
import json
import random
import string
import argparse
import sys
import os
from datetime import datetime

def generar_codigo_licencia(prefijo="INVIMA", ano="2026", longitud_aleatoria=4):
    """
    Genera una clave con formato profesional y único.
    Ejemplo: INVIMA-2026-A8K2-9M4P
    """
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" # Sin 0, O, 1, I para evitar confusiones
    bloque1 = "".join(random.choices(chars, k=longitud_aleatoria))
    bloque2 = "".join(random.choices(chars, k=longitud_aleatoria))
    return f"{prefijo}-{ano}-{bloque1}-{bloque2}".upper()

def crear_paquete_licencias(cantidad=20, empresa="Cliente INVIMA", vencimiento="2026-12-31", prefijo="INVIMA", ano="2026"):
    licencias_dict = {}
    lista_licencias = []
    
    claves_creadas = set()
    while len(lista_licencias) < cantidad:
        clave = generar_codigo_licencia(prefijo=prefijo, ano=ano)
        if clave not in claves_creadas:
            claves_creadas.add(clave)
            licencia_data = {
                "activa": True,
                "empresa": empresa,
                "max_equipos": 1,
                "vencimiento": vencimiento,
                "equipos": {}
            }
            licencias_dict[clave] = licencia_data
            lista_licencias.append((clave, licencia_data))
            
    return licencias_dict, lista_licencias

def exportar_archivos(licencias_dict, lista_licencias, output_json="licencias_firebase_import.json", output_txt="LISTADO_20_LICENCIAS_CLIENTE.txt"):
    # 1. Guardar archivo JSON para importar en la RAIZ de Firebase (Recomendado)
    json_raiz = {"licencias": licencias_dict}
    with open("licencias_importar_en_RAIZ.json", "w", encoding="utf-8") as f:
        json.dump(json_raiz, f, indent=2, ensure_ascii=False)

    # 2. Guardar archivo JSON directo para el nodo /licencias
    with open("licencias_firebase_import.json", "w", encoding="utf-8") as f:
        json.dump(licencias_dict, f, indent=2, ensure_ascii=False)
    
    # 2. Guardar archivo de entrega para el cliente
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("=" * 78 + "\n")
        f.write(f"           ENTREGA OFICIAL DE LICENCIAS - AUTOMATIZADOR INVIMA\n")
        f.write("=" * 78 + "\n\n")
        f.write(f"Empresa / Titular: {lista_licencias[0][1]['empresa']}\n")
        f.write(f"Total de Licencias / Puestos: {len(lista_licencias)}\n")
        f.write(f"Modalidad: 1 Computador / Puesto por Licencia (Max_equipos: 1)\n")
        f.write(f"Vencimiento: {lista_licencias[0][1]['vencimiento']}\n")
        f.write(f"Fecha de Emisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("-" * 78 + "\n")
        f.write(f"{'N°':<4} | {'CLAVE DE LICENCIA':<30} | {'PUESTOS':<10} | {'ESTADO':<10}\n")
        f.write("-" * 78 + "\n")
        
        for idx, (clave, data) in enumerate(lista_licencias, 1):
            f.write(f"{idx:<4} | {clave:<30} | 1 PC       | ACTIVA\n")
            
        f.write("-" * 78 + "\n\n")
        f.write("INSTRUCCIONES PARA CADA PUESTO / COMPUTADOR:\n")
        f.write("1. En cada computador de la empresa, abrir 'Automatizador INVIMA.exe'.\n")
        f.write("2. Cuando el programa solicite la activación, asignar una clave única de esta lista a ese equipo.\n")
        f.write("3. Al activarse, la clave queda vinculada de forma segura e inmutable al hardware de ese computador.\n")
        f.write("4. Ningún otro computador podrá usar esa misma clave.\n")
        f.write("=" * 78 + "\n")
        
    print(f"[OK] Archivo JSON generado con exito: {output_json}")
    print(f"[OK] Documento de entrega generado con exito: {output_txt}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de 20 licencias individuales (1 puesto por licencia) para Bot INVIMA")
    parser.add_argument("--cantidad", type=int, default=20, help="Cantidad de licencias a generar (default: 20)")
    parser.add_argument("--empresa", type=str, default="Cliente INVIMA", help="Nombre de la empresa")
    parser.add_argument("--vencimiento", type=str, default="2026-12-31", help="Fecha de vencimiento (AAAA-MM-DD)")
    parser.add_argument("--prefijo", type=str, default="INVIMA", help="Prefijo de la clave (ej: INVIMA, CLIENTE)")
    parser.add_argument("--ano", type=str, default="2026", help="Año para la clave (default: 2026)")
    
    args = parser.parse_args()
    
    dict_lic, list_lic = crear_paquete_licencias(
        cantidad=args.cantidad,
        empresa=args.empresa,
        vencimiento=args.vencimiento,
        prefijo=args.prefijo,
        ano=args.ano
    )
    
    exportar_archivos(dict_lic, list_lic)
