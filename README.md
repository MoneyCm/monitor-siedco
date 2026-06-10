# 🚔 Monitor Consolidado SIEDCO · Jamundí

### **Observatorio del Delito — Secretaría de Seguridad y Convivencia**
*Alcaldía de Jamundí · Valle del Cauca*

---

## 📋 Descripción General

Este monitor automatiza la extracción, análisis y alerta en tiempo real de las estadísticas delictivas del municipio de **Jamundí** registradas en el portal público **SIEDCO** (Policía Nacional de Colombia). 

El script realiza una navegación simulada por Playwright, interactúa con el framework AngularJS del portal para seleccionar la temática y el año de corte (2026 vs 2025), aplica los filtros del Departamento del **Valle del Cauca** y el Municipio de **Jamundí** en Qlik Sense, extrae los KPIs y guarda capturas de pantalla de los gráficos de cada una de las siguientes conductas delictivas priorizadas:

*   Homicidios
*   Hurto a personas
*   Hurto a residencias
*   Hurto a comercio
*   Hurto automotores
*   Hurto motocicletas
*   Lesiones personales
*   Extorsión
*   Violencia intrafamiliar

---

## 🛠️ Estructura del Proyecto

*   **`monitor_siedco.py`**: Script principal que ejecuta el bucle de scraping robusto en Chromium, analiza los cambios delictivos y guarda capturas por cada conducta en formato PNG.
*   **`notificar_siedco.py`**: Formatea el boletín de alerta en HTML con diseño corporativo premium, incrusta los gráficos capturados y el escudo municipal de Jamundí, y realiza el envío SMTP SSL. Si se ejecuta de forma local y no detecta variables de entorno SMTP, genera un reporte de prueba llamado `reporte_siedco_prueba.html` para previsualización inmediata.
*   **`resumen_actual.json`**: Guarda las cifras del último monitoreo con sus respectivos estados de extracción (ej. `OK` o `ERROR`).
*   **`resumen_anterior.json`**: Estado de la penúltima ejecución para el control y cálculo de novedades.
*   **`run_monitor.bat`**: Ejecutor local directo de Windows configurado para utilizar el entorno virtual compartido en `..\monitor-policia\.venv`.
*   **`requirements.txt`**: Librerías y dependencias necesarias (`playwright`).
*   **`.github/workflows/monitor_siedco.yml`**: Flujo de GitHub Actions para el monitoreo automatizado programado cada 12 horas en la nube con caché de estado persistente.

---

## 🚀 Guía de Ejecución Local

### **Requisitos Previos**
1.  Disponer de Python 3.10 o superior.
2.  Instalar las dependencias listadas en `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

### **Ejecución Directa**
Para ejecutar de forma inmediata el monitor desde la consola de Windows, simplemente corra:
```bash
run_monitor.bat
```
Una vez terminado el proceso, podrá hacer doble clic en el archivo generado **`reporte_siedco_prueba.html`** para validar la apariencia visual del reporte consolidado premium en su navegador web.

---

## ☁️ Automatización en GitHub Actions (Nube)

El workflow se ejecutará automáticamente cada 12 horas (programación Cron) y también puede iniciarse de forma manual desde la pestaña *Actions* de su repositorio en GitHub.

### **Variables de Entorno y Secretos Requeridos**
Para habilitar el envío automatizado de las alertas consolidadas por correo, configure los siguientes **Repository Secrets** en GitHub:

1.  `GMAIL_USER`: Cuenta de correo Gmail emisora (ej: `observatorio.jamundi@gmail.com`).
2.  `GMAIL_PASS`: Contraseña de aplicación de 16 caracteres generada desde la seguridad de su cuenta Google.
3.  `EMAIL_DEST`: Correo electrónico del destinatario final del reporte (si se omite, se enviará a la misma cuenta emisora).
