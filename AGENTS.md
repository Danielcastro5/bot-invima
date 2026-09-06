# GUÍA DE ARQUITECTURA, CONTEXTO Y DIRECTRICES - AUTOMATIZADOR INVIMA

Este documento es la referencia definitiva para cualquier Agente de Inteligencia Artificial o Desarrollador que trabaje en este repositorio. Contiene la arquitectura del sistema, reglas críticas de negocio, lecciones aprendidas y directrices estrictas de desarrollo.

---

## 1. PROPÓSITO DEL PROYECTO
El software **Automatizador INVIMA** es una aplicación de escritorio con interfaz gráfica construida en Python (`CustomTkinter`) que automatiza el registro de trámites de cosméticos (NSO) en el portal oficial de **INVIMA (Invimágil)** mediante **Playwright**.

---

## 2. REGLAS DE ORO DE DESARROLLO (ESTRICTAS Y OBLIGATORIAS)

### ⛔ REGLA 1: NO TOCAR NI ALTERAR PROCESOS ANTERIORES EXISTENTES
- Cuando se añada un nuevo proceso o se modifique uno en particular, **está estrictamente prohibido modificar o refactorizar el código de los procesos ya existentes y comprobados**.
- Cada proceso (`Información General (Presentaciones)`, `Composición`, `Grupos`, `Fórmula Marco`, `Composición por Grupo`, `Características Organolépticas`) tiene particularidades ya validadas con el portal de INVIMA. Modificar selectores compartidos o flujos previos sin necesidad puede romper lo que ya funciona.
- Siempre mantén los cambios encapsulados dentro del proceso específico que se está trabajando.

### ⛔ REGLA 2: ACTUALIZACIÓN OBLIGATORIA DEL MANUAL DE USUARIO
- Siempre que se agregue o modifique un proceso, es **obligatorio actualizar [`MANUAL_DE_USUARIO.txt`](file:///c:/bot-registro/MANUAL_DE_USUARIO.txt)**.
- Se debe detallar con máxima exactitud:
  1. El **Nombre exacto de la Hoja de Excel** (ej: `Composición por grupo`, `Presentaciones comerciales`).
  2. Los **Encabezados exactos de las columnas** en la Fila 1. Los nombres no pueden tener variaciones arbitrarias porque el bot mapea por nombre de columna.
  3. Indicar claramente al usuario que **los valores y textos ingresados en las celdas deben coincidir al 100% con los textos de las listas desplegables del portal INVIMA** (mismas mayúsculas, minúsculas, tildes y espacios).

### ⛔ REGLA 3: MENSAJES Y NOTAS DE ACTUALIZACIÓN 100% AMIGABLES (SIN TECNICISMOS NI LENGUAJES)
- Los usuarios finales del bot son personal administrativo y químico, **no programadores ni técnicos de sistemas**.
- En las notas de actualización (`version.json`) y en las ventanas emergentes del bot:
  - **PROHIBIDO** mencionar nombres de lenguajes de programación o librerías técnicas (`Python`, `Playwright`, `JavaScript`, `React`, `HTML`, `CSS`, `DOM`, `CDP`, etc.).
  - **PROHIBIDO** usar términos como "selectores", "eventos sintéticos", "hooks", "threads", "APIs", etc.
  - **PROHIBIDO** mencionar orígenes de código como "GitHub" dentro de la interfaz de la aplicación (usar "Descargando actualización...", "¡Nueva versión disponible!").
  - **FORMA CORRECTA:** Redactar de forma simple, profesional y orientada al usuario. Ejemplo: *"Mejora en la apertura automática de ventanas", "Soporte para agregar múltiples ingredientes en un mismo grupo", "Detención segura para no perder datos"*.

### ⛔ REGLA 4: DESARROLLO LOCAL PRIMERO Y PROHIBIDO HACER PUSH SIN AUTORIZACIÓN
- Todos los cambios, mejoras o correcciones se realizan, compilan y prueban **estrictamente en local primero**.
- **PROHIBIDO hacer `git push` a GitHub (sea `origin` o `public`) sin la orden y confirmación explícita del usuario.**
- Cada vez que se realice un cambio o ajuste en el código fuente, se debe **recompilar y actualizar de inmediato el archivo ejecutable local (`Automatizador INVIMA.exe`)** para que el usuario pueda probarlo directamente en su entorno.

---

## 3. ARQUITECTURA DE CONEXIÓN AL NAVEGADOR

### Modo Depuración de Google Chrome (Puerto 9222)
- El bot **NUNCA abre un navegador Chromium headless o aislado** desde cero.
- El bot se conecta a una instancia real de **Google Chrome** en el puerto `9222` mediante:
  ```python
  browser = p.chromium.connect_over_cdp("http://localhost:9222")
  context = browser.contexts[0]
  page = context.pages[0]
  ```
- **Razón fundamental:** El usuario inicia sesión manualmente con su certificado, usuario y contraseña de INVIMA en esa ventana de Chrome (`chrome_profile_bot`), y navega hasta el formulario deseado antes de iniciar el bot.

---

## 4. PATRONES CRÍTICOS PARA EL PORTAL INVIMA (ANT DESIGN 5)

El portal INVIMA utiliza el framework **Ant Design 5 (React)**. Esto impone comportamientos específicos que deben respetarse siempre:

1. **Clics en botones con íconos (`<svg>`):**
   - Los botones de Ant Design contienen etiquetas `<span class="ant-btn-icon"><svg>...</svg></span>`.
   - Si se usa `locator.click()` mediante coordenadas del mouse, el ícono o un contenedor padre suele interceptar el puntero físico y el evento `onClick` de React no se dispara.
   - **SOLUCIÓN ESTABLECIDA:** Disparar clics nativos de JavaScript directamente sobre el elemento del botón:
     ```python
     btn.evaluate("el => el.click()")
     ```
2. **Selección en Listas Desplegables (`.ant-select`):**
   - Para seleccionar opciones, se hace clic en el selector `.ant-select-selector` o se escribe la búsqueda, se espera la aparición del contenedor flotante `.ant-select-dropdown:not(.ant-select-dropdown-hidden)`, y se dispara el evento `mousedown`, `mouseup` y `click()` sobre el elemento de opción `.ant-select-item-option-content`.
3. **Detención Segura:**
   - Si el usuario presiona el botón "Detener", el bot **no debe interrumpir a la mitad un ingrediente o un grupo**. Siempre debe terminar de guardar el ingrediente actual y guardar el grupo/fórmula en curso antes de salir del ciclo, evitando que queden ventanas abiertas o datos incompletos.
4. **Agrupación Inteligente con Forward-Fill:**
   - En procesos con cabecera y detalle (como `Composición por Grupo`), el bot utiliza un `OrderedDict` que agrupa filas tanto si el usuario repite el nombre del grupo en cada fila, como si deja las celdas de grupo en blanco en las filas siguientes.

---

## 5. INFRAESTRUCTURA DE REPOSITORIOS Y DESPLIEGUES

El proyecto cuenta con dos repositorios remotos en Git:

1. **`origin` (`https://github.com/Danielcastro5/bot-invima-privado.git`):**
   - Repositorio **privado**.
   - Contiene todo el código fuente del proyecto (`bot.py`, `config.py`, scripts de compilación, manuales, etc.).
   - Aquí se suben todos los commits de desarrollo.

2. **`public` (`https://github.com/Danielcastro5/bot-invima.git`):**
   - Repositorio **público** de distribución.
   - **NO contiene el código fuente de la aplicación** (por seguridad y propiedad intelectual).
   - Solo contiene:
     - `version.json`: Archivo de metadatos que lee el auto-actualizador del bot.
     - `README.md`: Descripción general para los clientes.
     - **Releases de GitHub:** Aloja las versiones compiladas oficiales (`Automatizador_INVIMA.exe`).

### Procedimiento de Nueva Versión y Release
Cuando se completa una versión:
1. Incrementar la versión en `bot.py` (`VERSION_ACTUAL = "vX.X.X"`).
2. Actualizar `version.json` con las novedades (redacción simple y amigable sin tecnicismos).
3. Actualizar `MANUAL_DE_USUARIO.txt` si hubo cambios en hojas, encabezados o procesos.
4. Recompilar con PyInstaller:
   ```powershell
   python -m PyInstaller --clean "Automatizador INVIMA.spec" --noconfirm
   ```
5. Copiar el binario generado de `dist\` a la raíz y al Escritorio del usuario si corresponde.
6. Enviar cambios y tag a `origin`:
   ```powershell
   git commit -am "Release vX.X.X: ..."
   git tag -a vX.X.X -m "Release vX.X.X"
   git push origin main --tags
   ```
7. Publicar `version.json` en `public/main` y crear el Release en GitHub adjuntando el nuevo `Automatizador_INVIMA.exe`.

---

## 6. SISTEMA DE LICENCIAMIENTO
- **Mecanismo:** Identificador único de hardware (**HWID** inmutable) basado en `MachineGuid` de Windows y UUID del sistema.
- **Base de Datos:** Firebase Realtime Database (`bot-invima-licencias-default-rtdb`).
- **Validación:** Se autentica mediante HMAC SHA-256 con salt secreto (`SECRET_SALT_LICENCIA`). Cada licencia se asocia a un único computador para prevenir piratería o copias no autorizadas.
