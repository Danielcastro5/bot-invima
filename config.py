# ==========================================================================
#  CONFIGURACIÓN MULTI-PROCESO - AUTOMATIZADOR INVIMA
#
#  Este archivo permite definir múltiples procesos de automatización
#  (ej. "Información General", "Composición", etc.).
#  Cada proceso define su hoja de Excel, botón modal y mapa de campos.
# ==========================================================================

# Segundos máximos de espera por cada elemento antes de avisar y reintentar.
TIMEOUT_SEGUNDOS = 15

# True = verifica visualmente el valor en el campo tras seleccionarlo.
VERIFICAR_VALORES = True


# --- MAPA DE PROCESOS DE AUTOMATIZACIÓN ----------------------------------
PROCESOS = {
    "Información General (Presentaciones)": {
        "NOMBRE_HOJA": "Presentaciones comerciales",
        "BOTON_ABRIR_MODAL": r"button:has-text('Agregar presentación comercial'), #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > form > div:nth-child(30) > div button, #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > form > div:nth-child(30) > div > button > span",
        "SELECTOR_MODAL": r".ant-modal-content, .ant-modal",
        "BOTON_ENVIAR": r".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar')",
        "CAMPOS": [
            {
                "columna": "Contenido Neto",
                "selector": r".ant-modal-body form > div:nth-child(1) > div:nth-child(1) input, .ant-modal-body .ant-form-item:has-text('Contenido') input, .ant-modal-body input[type='number'], body > div:nth-child(7) div.ant-modal-body form > div:nth-child(1) > div:nth-child(1) input",
                "tipo": "texto",
            },
            {
                "columna": "Unidad de Medida",
                "selector": r".ant-modal-body form > div:nth-child(1) > div:nth-child(2) input, .ant-modal-body .ant-form-item:has-text('Unidad') input, body > div:nth-child(7) div.ant-modal-body form > div:nth-child(1) > div:nth-child(2) input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Tipo de Envase Primario",
                "selector": r".ant-modal-body form > div:nth-child(2) > div:nth-child(1) input, .ant-modal-body .ant-form-item:has-text('Tipo de Envase Primario') input, body > div:nth-child(7) div.ant-modal-body form > div:nth-child(2) > div:nth-child(1) input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Material del Envase Primario",
                "selector": r".ant-modal-body form > div:nth-child(2) > div:nth-child(2) input, .ant-modal-body .ant-form-item:has-text('Material del Envase Primario') input, body > div:nth-child(7) div.ant-modal-body form > div:nth-child(2) > div:nth-child(2) input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Tipo de Envase Secundario",
                "selector": r".ant-modal-body form > div:nth-child(3) > div:nth-child(1) input, .ant-modal-body .ant-form-item:has-text('Tipo de Envase Secundario') input, body > div:nth-child(7) div.ant-modal-body form > div:nth-child(3) > div:nth-child(1) input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Material del Envase Secundario",
                "selector": r".ant-modal-body form > div:nth-child(3) > div:nth-child(2) input, .ant-modal-body .ant-form-item:has-text('Material del Envase Secundario') input, body > div:nth-child(7) div.ant-modal-body form > div:nth-child(3) > div:nth-child(2) input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Observaciones",
                "selector": r".ant-modal-body form > div:nth-child(4) input, .ant-modal-body form > div:nth-child(4) textarea, body > div:nth-child(7) div.ant-modal-body form > div:nth-child(4) input, body > div:nth-child(7) div.ant-modal-body form > div:nth-child(4) textarea, .ant-modal-body .ant-form-item:has-text('Observaciones') input, .ant-modal-body .ant-form-item:has-text('Observaciones') textarea",
                "tipo": "texto",
            },
        ]
    },

    "Composición": {
        "NOMBRE_HOJA": "Composición",
        "BOTON_ABRIR_MODAL": r"#single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > div.ant-row.ant-row-end.ant-row-middle.css-1pu91a6 > div button, button:has-text('Agregar'), button:has-text('Adicionar')",
        "SELECTOR_MODAL": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div, .ant-modal-content, .ant-modal",
        "BOTON_ENVIAR": r".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button[type='submit']",
        "CAMPOS": [
            {
                "columna": "Tipo",
                "selector": r".ant-modal-body .ant-form-item:has-text('Tipo') .ant-select-selector, .ant-modal-body .ant-form-item:has-text('Tipo') input, .ant-modal-body .ant-form-item:has-text('Tipo')",
                "tipo": "select",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option, .ant-select-item-option",
            },
            {
                "columna": "Ingrediente / Mezcla",
                "selector": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(2) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Ingrediente') input, .ant-modal-body .ant-form-item:has-text('Mezcla') input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Función",
                "selector": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(3) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Función') input",
                "tipo": "multiselect",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Listado de referencia",
                "selector": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(4) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Listado de referencia') input, .ant-modal-body .ant-form-item:has-text('Listado') input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "Cantidad",
                "selector": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(5) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Cantidad') input",
                "tipo": "texto",
            },
            {
                "columna": "Unidad de medida",
                "selector": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(6) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Unidad de medida') input, .ant-modal-body .ant-form-item:has-text('Unidad') input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
            },
            {
                "columna": "¿Es nanomaterial?",
                "selector": r"#isNanomaterial, button#isNanomaterial, .ant-modal-body button.ant-switch, .ant-switch",
                "tipo": "switch",
            },
            {
                "columna": "Tamaño de partícula (nm)",
                "selector": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(8) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Tamaño de partícula') input, .ant-modal-body .ant-form-item:has-text('partícula') input",
                "tipo": "texto",
            },
        ]
    }
}


# --- Compatibilidad hacia atrás ---------------------------------------------
# Si el script busca las variables globales antiguas, se extraen del proceso principal.
PROCESO_DEFAULT = PROCESOS["Información General (Presentaciones)"]
NOMBRE_HOJA = PROCESO_DEFAULT["NOMBRE_HOJA"]
BOTON_ABRIR_MODAL = PROCESO_DEFAULT["BOTON_ABRIR_MODAL"]
SELECTOR_MODAL = PROCESO_DEFAULT["SELECTOR_MODAL"]
BOTON_ENVIAR = PROCESO_DEFAULT["BOTON_ENVIAR"]
CAMPOS = PROCESO_DEFAULT["CAMPOS"]
