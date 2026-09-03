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

    "Composición (Ingredientes)": {
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
                "selector": r".ant-modal:not([style*='display: none']) .ant-form-item:has-text('Listado') input, .ant-modal:not([style*='display: none']) .ant-form-item:has-text('referencia') input, .ant-modal-body .ant-form-item:has-text('Listado') input, .ant-modal-body .ant-form-item:has-text('referencia') input, body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(4) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Listado de referencia') input, .ant-modal-body .ant-form-item:has-text('Listado') input",
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
    },

    "Información General (Grupos)": {
        "NOMBRE_HOJA": "Grupos",
        "BOTON_ABRIR_MODAL": r"button:has-text('Agregar grupo'), button:has-text('Adicionar grupo'), button:has-text('Agregar Grupo'), button:has-text('Adicionar Grupo'), #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > form > div:nth-child(25) > div > button, button:has-text('Grupo')",
        "SELECTOR_MODAL": r"body > div:nth-child(7) > div > div.ant-modal-wrap, .ant-modal-content, .ant-modal",
        "BOTON_ENVIAR": r".ant-modal-footer button.ant-btn-primary, body > div:nth-child(7) > div > div.ant-modal-wrap > div > div:nth-child(1) > div > div.ant-modal-footer > button.ant-btn.css-1pu91a6.ant-btn-primary.ant-btn-color-primary.ant-btn-variant-solid, .ant-modal-footer button:has-text('Aceptar'), .ant-modal-footer button:has-text('Guardar'), button:has-text('Aceptar')",
        "CAMPOS": [
            {
                "columna": "Nombre del grupo",
                "selector": r".ant-modal-body input, .ant-modal-body textarea, .ant-modal input, .ant-modal textarea, body > div:nth-child(7) input",
                "tipo": "texto",
            }
        ]
    },

    "Composición (Fórmula Marco)": {
        "NOMBRE_HOJA": "Fórmula Marco",
        "TIPO_PROCESO": "formula_marco",
        "BOTON_ABRIR_MODAL": r"button:has-text('Agregar fórmula marco'), button:has-text('Adicionar fórmula marco'), button:has-text('Agregar formula marco'), button:has-text('Fórmula marco'), button:has-text('Formula marco'), #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > div:nth-child(5) > div button, div:nth-child(5) > div button",
        "SELECTOR_MODAL_PRINCIPAL": r".ant-modal-wrap:not([style*='display: none']), .ant-modal-content, .ant-modal",
        "SELECTOR_CAMPO_NOMBRE_FORMULA": r".ant-modal-body form input, .ant-modal-body .ant-form-item:has-text('Nombre') input, .ant-modal-body .ant-form-item:has-text('fórmula') input, .ant-modal-body input[type='text'], .ant-modal-body input, input[placeholder*='fórmula'], input[placeholder*='formula'], input[placeholder*='nombre']",
        "BOTON_ANADIR_INGREDIENTE": r"button:has-text('Añadir ingrediente'), button:has-text('Agregar ingrediente'), button:has-text('Adicionar ingrediente'), button:has-text('Añadir Ingrediente'), button:has-text('Agregar Ingrediente'), .ant-modal-body button:has-text('ingrediente'), .ant-modal-body button:has-text('Ingrediente'), .ant-modal-body button.ant-btn",
        "SELECTOR_MODAL_INGREDIENTE": r".ant-modal-wrap:not([style*='display: none']) .ant-modal-content, .ant-modal-content, .ant-modal",
        "BOTON_GUARDAR_INGREDIENTE": r".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button:has-text('Aceptar'), button:has-text('Adicionar')",
        "BOTON_GUARDAR_FORMULA": r".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar fórmula'), button:has-text('Guardar'), button:has-text('Aceptar')",
        "COLUMNA_NOMBRE_FORMULA": "Nombre de la fórmula marco",
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
                "selector": r".ant-modal:not([style*='display: none']) .ant-form-item:has-text('Listado') input, .ant-modal:not([style*='display: none']) .ant-form-item:has-text('referencia') input, .ant-modal-body .ant-form-item:has-text('Listado') input, .ant-modal-body .ant-form-item:has-text('referencia') input, body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(4) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Listado de referencia') input, .ant-modal-body .ant-form-item:has-text('Listado') input",
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
    },

    "Composición (Composición por Grupo)": {
        "NOMBRE_HOJA": "Composición por grupo",
        "TIPO_PROCESO": "composicion_grupo",
        "BOTON_ABRIR_MODAL": r"button:has-text('Añadir Composición por Grupo'), button:has-text('Agregar Composición por Grupo'), button:has-text('Composición por Grupo'), button:has-text('Composicion por Grupo'), button:has-text('Composición por grupo'), button:has-text('Composicion por grupo'), #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > div:nth-child(9) > div > button, #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > div:nth-child(9) > div button",
        "SELECTOR_MODAL_PRINCIPAL": r".ant-modal-wrap:not([style*='display: none']), .ant-modal-content, .ant-modal",
        "BOTON_ACCION_PREVIA": r"button:has-text('Usar Fórmula Marco'), button:has-text('Usar fórmula marco'), button:has-text('Usar Formula Marco'), button:has-text('Usar formula marco'), button:has-text('Fórmula Marco'), button:has-text('Formula Marco'), .ant-modal-confirm-body button:has-text('Fórmula Marco'), .ant-modal-confirm-body button:has-text('Formula Marco'), body > div:nth-child(5) > div > div.ant-modal-wrap > div > div:nth-child(1) > div > div > div > div.ant-modal-confirm-body.ant-modal-confirm-body-has-title > div > div > div > button",
        "CAMPOS_CABECERA": [
            {
                "columna": "Grupo",
                "selector": r".ant-modal-body form > div > div:nth-child(1) .ant-select-selector, .ant-modal-body .ant-form-item:has-text('grupo') .ant-select-selector, .ant-modal-body .ant-form-item:has-text('Grupo') .ant-select-selector, .ant-modal-body form > div > div:nth-child(1) input, body > div:nth-child(5) div.ant-modal-body form > div > div:nth-child(1) .ant-select-selector",
                "tipo": "select",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option, .ant-select-item-option",
            },
            {
                "columna": "Fórmula Marco",
                "selector": r".ant-modal-body form > div > div:nth-child(2) .ant-select-selector, .ant-modal-body .ant-form-item:has-text('fórmula') .ant-select-selector, .ant-modal-body .ant-form-item:has-text('Fórmula') .ant-select-selector, .ant-modal-body .ant-form-item:has-text('formula') .ant-select-selector, .ant-modal-body form > div > div:nth-child(2) input, body > div:nth-child(5) div.ant-modal-body form > div > div:nth-child(2) .ant-select-selector",
                "tipo": "select",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option, .ant-select-item-option",
            }
        ],
        "BOTON_ANADIR_INGREDIENTE": r"body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > div.ant-row.ant-row-space-between.ant-row-middle.css-1pu91a6 > div:nth-child(2) > button, button:has-text('Añadir ingrediente'), button:has-text('Agregar ingrediente'), button:has-text('Adicionar ingrediente'), button:has-text('Añadir Ingrediente'), button:has-text('Agregar Ingrediente'), .ant-modal-body button:has-text('ingrediente'), .ant-modal-body button:has-text('Ingrediente'), .ant-modal-body button.ant-btn",
        "SELECTOR_MODAL_INGREDIENTE": r".ant-modal-wrap:not([style*='display: none']) .ant-modal-content, .ant-modal-content, .ant-modal",
        "BOTON_GUARDAR_INGREDIENTE": r".ant-modal-footer button.ant-btn-primary, button:has-text('Guardar'), button:has-text('Aceptar'), button:has-text('Adicionar')",
        "BOTON_GUARDAR_GRUPO": r".ant-modal-footer button.ant-btn-primary, body > div:nth-child(5) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-footer > button.ant-btn.css-1pu91a6.ant-btn-primary.ant-btn-color-primary.ant-btn-variant-solid, button:has-text('Guardar'), button:has-text('Aceptar')",
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
                "selector": r".ant-modal:not([style*='display: none']) .ant-form-item:has-text('Listado') input, .ant-modal:not([style*='display: none']) .ant-form-item:has-text('referencia') input, .ant-modal-body .ant-form-item:has-text('Listado') input, .ant-modal-body .ant-form-item:has-text('referencia') input, body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(4) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input, .ant-modal-body .ant-form-item:has-text('Listado de referencia') input, .ant-modal-body .ant-form-item:has-text('Listado') input",
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
    },

    "Características Técnicas (Características Organolépticas)": {
        "NOMBRE_HOJA": "Características Organolépticas",
        "BOTON_ABRIR_MODAL": r"button:has-text('Agregar Características Organolépticas'), button:has-text('Adicionar Características Organolépticas'), button:has-text('Agregar Caracteristicas Organolepticas'), button:has-text('Características Organolépticas'), button:has-text('Caracteristicas Organolepticas'), button:has-text('Características organolépticas'), button:has-text('Caracteristicas organolepticas'), button:has-text('Organolépticas'), button:has-text('Organolepticas'), #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > div > div:nth-child(1) > div.ant-row.ant-row-end.css-1pu91a6 > div > button, #single-spa-application\:\@cx\/workspace-cosmetics > div > main > div.erHFPg5exWzGeIbPIRYe > div.xhUocBpKVBF6DfRqoST5 > div.vQ8bD_kd41eOJ1OyVQYW > div.ant-row.css-cdzvx5 > div > div > div > div > div > div:nth-child(1) > div.ant-row.ant-row-end.css-1pu91a6 > div button",
        "SELECTOR_MODAL": r".ant-modal-wrap, .ant-modal-content, .ant-modal",
        "BOTON_ENVIAR": r".ant-modal-footer button.ant-btn-primary, body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-footer > button.ant-btn.css-1pu91a6.ant-btn-primary.ant-btn-color-primary.ant-btn-variant-solid, button:has-text('Guardar'), button:has-text('Aceptar')",
        "CAMPOS": [
            {
                "columna": "Grupo Cosmético",
                "alias": ["Grupo", "grupo", "Nombre del grupo", "Grupo cosmetico", "grupo cosmetico", "Grupo Cosmético", "grupo cosmético", "Nombre grupo", "nombre grupo"],
                "selector": r".ant-modal-body form > div > div:nth-child(1) input, .ant-modal-body form > div > div:nth-child(1) .ant-select-selection-search input, .ant-modal-body .ant-form-item:has-text('Grupo') input, .ant-modal-body .ant-form-item:has-text('grupo') input, .ant-modal-body form > div > div:nth-child(1) .ant-select-selector, body > div:nth-child(6) div.ant-modal-body form > div > div:nth-child(1) input",
                "tipo": "autocompletar",
                "selector_sugerencia": r".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option, .ant-select-item-option",
            },
            {
                "columna": "Color",
                "alias": ["Color", "color"],
                "selector": r".ant-modal-body form > div > div:nth-child(2) input, .ant-modal-body .ant-form-item:has-text('Color') input, .ant-modal-body .ant-form-item:has-text('color') input, body > div:nth-child(6) div.ant-modal-body form > div > div:nth-child(2) input, body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(2) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input",
                "tipo": "texto",
            },
            {
                "columna": "Olor",
                "alias": ["Olor", "olor"],
                "selector": r".ant-modal-body form > div > div:nth-child(3) input, .ant-modal-body .ant-form-item:has-text('Olor') input, .ant-modal-body .ant-form-item:has-text('olor') input, body > div:nth-child(6) div.ant-modal-body form > div > div:nth-child(3) input, body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(3) > div > div input",
                "tipo": "texto",
            },
            {
                "columna": "Sabor",
                "alias": ["Sabor", "sabor"],
                "selector": r".ant-modal-body form > div > div:nth-child(4) input, .ant-modal-body .ant-form-item:has-text('Sabor') input, .ant-modal-body .ant-form-item:has-text('sabor') input, body > div:nth-child(6) div.ant-modal-body form > div > div:nth-child(4) input, body > div:nth-child(6) > div > div.ant-modal-wrap.ant-modal-centered > div > div:nth-child(1) > div > div.ant-modal-body > form > div > div:nth-child(4) > div > div > div.ant-col.ant-form-item-control.css-1pu91a6 input",
                "tipo": "texto",
            }
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
