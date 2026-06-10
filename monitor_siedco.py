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
    {"nombre": "Homicidios", "pattern": "Homicidios"},
    {"nombre": "Hurto a personas", "pattern": "Hurto.*personas"},
    {"nombre": "Hurto a residencias", "pattern": "Hurto.*residencias"},
    {"nombre": "Hurto a comercio", "pattern": "Hurto.*comercio"},
    {"nombre": "Hurto automotores", "pattern": "Hurto.*automotores"},
    {"nombre": "Hurto motocicletas", "pattern": "Hurto.*motocicletas"},
    {"nombre": "Lesiones personales", "pattern": "Lesiones.*personales"},
    {"nombre": "Extorsión", "pattern": "Extorsi[oó]n"},
    {"nombre": "Violencia intrafamiliar", "pattern": "Violencia.*intrafamiliar"}
]

def extraer_casos(text, delito_pattern, anio):
    # Expresión regular flexible para buscar "[delito_pattern] | Año/Ano XXXX" seguido del valor
    patron = rf"{delito_pattern}\s*\|\s*A[ñn]o\s*{anio}\s*\n\s*([\d,.]+)"
    match = re.search(patron, text, re.IGNORECASE)
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
            search_input_locator.first.wait_for(state="visible", timeout=3000)
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
    
    item_selector = page.locator("[data-testid='listbox.item']", has_text=valor_confirmar).first
    item_selector.wait_for(state="visible", timeout=10000)
    
    # Hacer clic robusto y verificar que aparezca el botón de confirmación
    confirm_btn = page.locator(".actions-toolbar-confirm:visible").first
    seleccion_realizada = False
    for intento in range(3):
        item_selector.click(force=True)
        page.wait_for_timeout(1200)
        if confirm_btn.is_visible():
            seleccion_realizada = True
            break
        else:
            print(f"    [AVISO] No se detectó barra de confirmación tras click (Intento {intento + 1}). Reintentando...")
            page.wait_for_timeout(1000)
            
    if not seleccion_realizada:
        print(f"    [AVISO] Se procede sin detectar barra de confirmación explícita para {panel_titulo}.")
        
    print(f"  Confirmando selección de {panel_titulo}...")
    if confirm_btn.is_visible():
        confirm_btn.click(force=True)
        try:
            confirm_btn.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass
    else:
        # Clic genérico de confirmación
        try:
            page.locator(".actions-toolbar-confirm:visible").first.click(force=True)
        except Exception:
            pass
            
    page.wait_for_timeout(2500)

def extraer_datos_delito(browser, delito_nombre, delito_pattern):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    url = "https://portalsiedco.policia.gov.co:4443/extensions/PortalPublico/index.html#/home"
    
    try:
        print(f"Navegando al portal de SIEDCO para: {delito_nombre}...")
        page.goto(url, wait_until="networkidle", timeout=60000)
        # Espera de estabilización inicial para asegurar carga del WebSocket
        page.wait_for_timeout(6000)
        
        # 1. Seleccionar temática y año usando inyección limpia de AngularJS Scope y DOM
        print(f"  Inyectando Angular para '{delito_nombre}' y Año: 2026...")
        js_result = page.evaluate(f"""() => {{
            const sel = document.getElementById('tematicasCombo');
            if (!sel) return "No select element found";
            const scope = angular.element(sel).scope();
            if (!scope) return "No scope found";
            
            // Buscar la opción del delito
            const optionObj = scope.tematicasCombo.find(item => item.label.includes('{delito_nombre}'));
            if (!optionObj) return "Option not found in scope for label '{delito_nombre}'";
            
            // Buscar año 2026
            const selectedYear = scope.aniosCombo.find(y => y === 2026) || scope.aniosCombo[0] || 2026;
            
            // Sincronizar el DOM directamente
            sel.value = optionObj.value;
            sel.dispatchEvent(new Event('change'));
            const selAnio = document.querySelector("select[id$='osCombo']");
            if (selAnio) {{
                selAnio.value = selectedYear.toString();
                selAnio.dispatchEvent(new Event('change'));
            }}
            
            scope.$apply(() => {{
                scope.tematicaSeleccionada = optionObj;
                scope.anioSeleccionado = selectedYear;
                scope.getSeleccionesCombos();
            }});
            return "SUCCESS - Selected Year: " + selectedYear + ", Val: " + sel.value;
        }}""")
        
        if "SUCCESS" not in js_result:
            return None, None, f"ERROR: Selección Angular fallida ({js_result[:60]})"
            
        page.wait_for_timeout(1500)
        
        # Esperar a que el botón se habilite orgánicamente en Angular y hacer clic
        print("  Esperando a que Angular habilite el botón de entrar...")
        btn_enter = page.locator(".btn-enter:not([disabled])").first
        btn_enter.wait_for(state="visible", timeout=10000)
        btn_enter.click()
        
        # Aplicar filtros usando la función robusta
        aplicar_filtro_qlik(page, "Departamento", "VALLE")
        aplicar_filtro_qlik(page, "Municipio", "JAMUNDI", "JAMUNDÍ")
        
        print("  Esperando 10 segundos a que se actualicen los gráficos...")
        page.wait_for_timeout(10000)
        
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
            pattern = temp["pattern"]
            v_25, v_26, estado = extraer_datos_delito(browser, nombre, pattern)
            
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
