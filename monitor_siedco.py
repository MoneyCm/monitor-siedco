import os
import sys
import io
import re
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Forzar codificación UTF-8 en la consola de salida estándar para evitar errores en Windows
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent
RESUMEN_ACT = BASE_DIR / "resumen_actual.json"
RESUMEN_ANT = BASE_DIR / "resumen_anterior.json"
ESCUDO_PATH = BASE_DIR / "escudo_jamundi.png"

# Temáticas prioritarias a monitorear con sus respectivos patrones de búsqueda en el DOM
TEMATICAS = [
    {"nombre": "Homicidios", "keywords": ["homicidio"], "pattern": "Homicidios"},
    {"nombre": "Hurto a personas", "keywords": ["hurto", "personas"], "pattern": "Hurto.*personas"},
    {"nombre": "Hurto a residencias", "keywords": ["hurto", "residencias"], "pattern": "Hurto.*residencias"},
    {"nombre": "Hurto a comercio", "keywords": ["hurto", "comercio"], "pattern": "Hurto.*comercio"},
    {"nombre": "Hurto automotores", "keywords": ["hurto", "automotor"], "pattern": "Hurto.*automotores"},
    {"nombre": "Hurto motocicletas", "keywords": ["hurto", "motocicleta"], "pattern": "Hurto.*motocicletas"},
    {"nombre": "Lesiones personales", "keywords": ["lesiones"], "pattern": "Lesiones.*personales"},
    {"nombre": "Extorsión", "keywords": ["extorsi"], "pattern": "Extorsi[oó]n"},
    {"nombre": "Violencia intrafamiliar", "keywords": ["intrafamiliar"], "pattern": "Violencia.*intrafamiliar"}
]

def extraer_casos(text, delito_pattern, anio):
    # 1. Intentar con el patrón específico del delito (ej: "Homicidios | Año 2025")
    patron_especifico = rf"{delito_pattern}\s*\|\s*A.{{1,2}}o\s*{anio}\s*\n\s*([\d,.]+)"
    match = re.search(patron_especifico, text, re.IGNORECASE)
    
    # 2. Si falla, usar patrón genérico (ej: "Sin título | Año 2025" o cualquier texto/espacio antes del pipe)
    if not match:
        patron_generico = rf"(?:[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]*)\|\s*A.{{1,2}}o\s*{anio}\s*\n\s*([\d,.]+)"
        match = re.search(patron_generico, text, re.IGNORECASE)
        
    if match:
        valor_str = match.group(1).replace(",", "").replace(".", "")
        try:
            return int(valor_str)
        except ValueError:
            print(f"[ERROR] No se pudo convertir el valor '{valor_str}' a entero para {delito_pattern} en {anio}.")
    return None

def aplicar_filtro_qlik(page, panel_titulo, valor_busqueda, valor_confirmar=None):
    if not valor_confirmar:
        valor_confirmar = valor_busqueda
        
    print(f"  Esperando a que el panel de {panel_titulo} esté visible...")
    panel = page.locator(".qv-object-filterpane", has_text=panel_titulo).first
    panel.wait_for(state="visible", timeout=60000)
    page.wait_for_timeout(1500)
    
    listbox = panel.locator(".folded-listbox").first
    search_input_locator = page.locator("input[placeholder='Buscar en cuadro de lista']:visible")
    
    # Reintento robusto de apertura del panel
    panel_abierto = False
    for intento in range(3):
        listbox.click(force=True)
        try:
            search_input_locator.first.wait_for(state="visible", timeout=5000)
            panel_abierto = True
            break
        except Exception:
            print(f"    [AVISO] Intento {intento + 1} fallido para abrir {panel_titulo}. Reintentando...")
            page.wait_for_timeout(2000)
            
    if not panel_abierto:
        raise Exception(f"No se pudo abrir el filtro de {panel_titulo}")
        
    print(f"  Buscando y seleccionando '{valor_confirmar}'...")
    search_field = search_input_locator.first
    search_field.click()
    search_field.fill("")
    search_field.press_sequentially(valor_busqueda, delay=100)
    page.wait_for_timeout(2500)  # Espera para sincronización WebSocket
    
    print(f"  Seleccionando la opción '{valor_confirmar}'...")
    item_selector = page.locator("[data-testid='listbox.item']", has_text=valor_confirmar).first
    item_selector.wait_for(state="visible", timeout=15000)
    item_selector.click(force=True)
    page.wait_for_timeout(1500)
    
    print(f"  Confirmando selección de {panel_titulo}...")
    confirm_btn = page.locator(".qs-actions-confirm:visible, .qv-confirm-button:visible, button[title*='Confirmar']:visible, .actions-toolbar-confirm:visible").first
    confirm_btn.click(force=True)
    page.wait_for_timeout(5000)

def extraer_datos_delito(browser, delito_nombre, delito_keywords, delito_pattern):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    url = "https://portalsiedco.policia.gov.co:4443/extensions/PortalPublico/index.html#/home"
    
    try:
        print(f"Navegando al portal de SIEDCO para: {delito_nombre}...")
        page.goto(url, wait_until="networkidle", timeout=60000)
        # Esperar a que los combos de temáticas y años carguen las opciones en el DOM
        print("  Esperando a que el combo de temáticas cargue las opciones...")
        try:
            page.locator("select#tematicasCombo option").nth(1).wait_for(state="attached", timeout=25000)
            page.locator("select[id$='osCombo'] option").nth(1).wait_for(state="attached", timeout=15000)
        except Exception as err_wait:
            print(f"  [AVISO] Espera de opciones falló/agotó tiempo: {err_wait}")
            
        # Espera adicional de estabilización
        page.wait_for_timeout(3000)
        
        # 1. Buscar la etiqueta de la temática en el Angular Scope y seleccionarla con Playwright de forma nativa
        import json
        keywords_str = json.dumps(delito_keywords)
        print(f"  Buscando opción en combo para '{delito_nombre}' (Keywords: {delito_keywords})...")
        option_label = page.evaluate(f"""() => {{
            const sel = document.getElementById('tematicasCombo');
            if (!sel) return null;
            const scope = angular.element(sel).scope();
            if (!scope) return null;
            const kws = {keywords_str};
            const optionObj = scope.tematicasCombo.find(item => {{
                const labelLower = item.label.toLowerCase();
                return kws.every(kw => labelLower.includes(kw));
            }});
            return optionObj ? optionObj.label : null;
        }}""")
        
        if not option_label:
            return None, None, f"ERROR: No se encontró etiqueta para temática {delito_nombre}"
            
        print(f"  Seleccionando temática '{option_label}'...")
        page.select_option("select#tematicasCombo", label=option_label)
        page.wait_for_timeout(1000)
        
        print("  Seleccionando Año 2026 de forma nativa...")
        page.select_option("select[id$='osCombo']", label="2026")
        page.wait_for_timeout(1000)
        
        # Forzar la sincronización del modelo de AngularJS con los valores del DOM
        print("  Sincronizando el modelo AngularJS...")
        sync_result = page.evaluate("""() => {
            const selectTematica = document.getElementById('tematicasCombo');
            const selectAnio = document.querySelector("select[id$='osCombo']");
            if (!selectTematica || !selectAnio) return "Error: Elementos no encontrados";
            
            const scope = angular.element(selectTematica).scope();
            if (!scope) return "Error: Scope de Angular no encontrado";
            
            const labelTematica = selectTematica.options[selectTematica.selectedIndex].text;
            const labelAnio = selectAnio.options[selectAnio.selectedIndex].text;
            
            const optionObj = scope.tematicasCombo.find(item => item.label === labelTematica);
            const selectedYear = scope.aniosCombo.find(y => y.toString() === labelAnio) || parseInt(labelAnio) || 2026;
            
            if (optionObj) {
                scope.$apply(() => {
                    scope.tematicaSeleccionada = optionObj;
                    scope.anioSeleccionado = selectedYear;
                    scope.getSeleccionesCombos();
                });
                return `Exitoso: Tematica=${labelTematica}, Año=${labelAnio}`;
            }
            return `Error: Objeto no encontrado en el scope para '${labelTematica}'`;
        }""")
        print(f"  [Angular Sync] {sync_result}")
        page.wait_for_timeout(1500)
        
        # Habilitar y hacer clic en el botón de entrar
        print("  Haciendo clic en el botón de entrar...")
        btn_enter = page.locator(".btn-enter").first
        btn_enter.evaluate("el => el.removeAttribute('disabled')")
        btn_enter.click()
        
        # Esperar a que el dashboard de Qlik cargue completamente antes de interactuar con filtros
        print("  Esperando a que el dashboard de Qlik cargue completamente...")
        page.locator(".qv-object-filterpane", has_text="Departamento").first.wait_for(state="visible", timeout=60000)
        
        # Esperar dinámicamente a que Qlik Sense aplique la temática (filtro de Delito) en el dashboard
        filtro_tematica_ok = True
        if delito_nombre.lower() != "extorsión":
            print("  Esperando dinámicamente la aplicación del filtro 'Delito'...")
            filtro_aplicado = False
            for _ in range(30):
                body_text = page.locator("body").inner_text()
                if "Delito" in body_text:
                    filtro_aplicado = True
                    break
                page.wait_for_timeout(500)
            if filtro_aplicado:
                print("    [OK] Filtro 'Delito' detectado en el dashboard.")
            else:
                print("    [AVISO] No se detectó la etiqueta 'Delito' en la barra de filtros tras 15s.")
                filtro_tematica_ok = False
            page.wait_for_timeout(3000)  # Estabilización final
        else:
            page.wait_for_timeout(8000)  # Espera fija para Extorsión que no usa el filtro Delito en el dashboard Operativo
        
        # Aplicar filtros usando la función robusta
        aplicar_filtro_qlik(page, "Departamento", "VALLE")
        aplicar_filtro_qlik(page, "Municipio", "JAMUNDI", "JAMUNDÍ")
        
        print("  Esperando 12 segundos a que se actualicen los gráficos...")
        page.wait_for_timeout(12000)
        
        # Guardar captura específica de la temática
        delito_file_name = f"siedco_{delito_nombre.lower().replace(' ', '_')}.png"
        img_path = BASE_DIR / delito_file_name
        page.screenshot(path=str(img_path), full_page=True)
        print(f"  [OK] Captura de pantalla guardada en: {delito_file_name}")
        
        body_text = page.locator("body").inner_text()
        
        casos_2025 = extraer_casos(body_text, delito_pattern, 2025)
        casos_2026 = extraer_casos(body_text, delito_pattern, 2026)
        
        if casos_2025 is None or casos_2026 is None:
            return None, None, "ERROR: Falló parseo de números del DOM"
            
        # Validar si el filtro de Delito no se aplicó (retornó totales departamentales/municipales sin filtrar)
        if delito_nombre.lower() != "extorsión":
            if not filtro_tematica_ok or (casos_2025 == 308374 and casos_2026 == 1051159):
                return None, None, "ERROR: Filtro de Delito no se aplicó (se detectaron cifras acumuladas totales)"
            
        print(f"  [OK] Datos extraídos -> {delito_nombre} 2025: {casos_2025}, 2026: {casos_2026}")
        return casos_2025, casos_2026, "OK"

    except Exception as e:
        print(f"  [ERROR] Ocurrió una excepción durante el procesamiento de {delito_nombre}: {e}")
        try:
            err_img = BASE_DIR / f"siedco_error_{delito_nombre.lower().replace(' ', '_')}.png"
            page.screenshot(path=str(err_img), full_page=True)
            print(f"  [OK] Captura de pantalla de error guardada en: {err_img.name}")
        except Exception:
            pass
        return None, None, f"ERROR: Excepción en navegador ({str(e)[:60]})"
    finally:
        context.close()

def main():
    print("=== INICIANDO MONITOREO MULTI-DELITO DE SIEDCO (JAMUNDÍ) ===")
    
    datos_consolidados = {}
    
    with sync_playwright() as p:
        print("Lanzando navegador Chromium...")
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--ignore-certificate-errors"]
        )
        
        for temp in TEMATICAS:
            nombre = temp["nombre"]
            keywords = temp["keywords"]
            pattern = temp["pattern"]
            
            # Reintento robusto para cada delito (hasta 5 intentos)
            v_25, v_26, estado = None, None, "ERROR: No iniciado"
            for intento in range(5):
                print(f"Intento {intento + 1} para extraer {nombre}...")
                v_25, v_26, estado = extraer_datos_delito(browser, nombre, keywords, pattern)
                if estado == "OK":
                    break
                print(f"  [AVISO] Falló extracción de {nombre} en intento {intento + 1} (Estado: {estado}). Reintentando en 6s...")
                time.sleep(6)
                
            datos_consolidados[nombre] = {
                "2025": v_25,
                "2026": v_26,
                "estado": estado
            }
            print("-" * 50)
            
        browser.close()
        
    exitosas = sum(1 for info in datos_consolidados.values() if info.get("estado") == "OK")
    fallidas = len(datos_consolidados) - exitosas
    print(f"[INFO] Monitoreo completado. Se procesaron {len(datos_consolidados)} temáticas: {exitosas} exitosas, {fallidas} fallidas.")
    
    # 5. Lógica de control de cambios y persistencia
    # Rotar archivos
    if RESUMEN_ACT.exists():
        if RESUMEN_ANT.exists():
            os.remove(RESUMEN_ANT)
        os.rename(RESUMEN_ACT, RESUMEN_ANT)
        print("[INFO] Rotado resumen_actual.json a resumen_anterior.json")
    
    # Guardar el estado actual estructurado
    with open(RESUMEN_ACT, "w", encoding="utf-8") as f:
        json.dump(datos_consolidados, f, indent=4, ensure_ascii=False)
    print("[INFO] Guardado nuevo resumen_actual.json con estados detallados")
    
    # Comparar cambios
    hay_cambio = True
    if RESUMEN_ANT.exists():
        with open(RESUMEN_ANT, "r", encoding="utf-8") as f:
            datos_anteriores = json.load(f)
        
        coincide_todo = True
        for delito, info in datos_consolidados.items():
            info_ant = datos_anteriores.get(delito, {})
            # Comparar valores si ambos están correctos
            if info.get("estado") == "OK" and info_ant.get("estado") == "OK":
                if (info.get("2025") != info_ant.get("2025") or 
                    info.get("2026") != info_ant.get("2026")):
                    coincide_todo = False
                    break
            # Si el estado del delito cambió (por ejemplo pasó de ERROR a OK o viceversa)
            elif info.get("estado") != info_ant.get("estado"):
                coincide_todo = False
                break
                
        if coincide_todo:
            print("[OK] No se detectaron cambios numéricos ni de estado en ningún delito. Se omite la alerta.")
            hay_cambio = False
    else:
        print("[INFO] No existe un registro anterior completo. Se disparará alerta inicial.")
        
    # 6. Disparar notificaciones si hay cambios
    if hay_change := hay_cambio:
        print("[ALERTA] Novedades detectadas en los delitos. Disparando notificaciones por correo...")
        # Imagen representativa (Homicidios, si existe, de lo contrario la primera que haya)
        rep_img = BASE_DIR / "siedco_homicidios.png"
        if not rep_img.exists():
            capturas = list(BASE_DIR.glob("siedco_*.png"))
            if capturas:
                rep_img = capturas[0]
                
        try:
            import notificar_siedco
            notificar_siedco.enviar_alerta(datos_consolidados, rep_img, ESCUDO_PATH)
        except Exception as err_notify:
            print(f"[ERROR] No se pudo enviar la notificación: {err_notify}")

if __name__ == "__main__":
    main()
