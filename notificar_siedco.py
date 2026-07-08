"""
notificar_siedco.py — Envío de correos electrónicos premium con reporte consolidado multi-delito (Soporte de Estados)
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path

# Configuración de credenciales y destino
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")
EMAIL_DEST = os.environ.get("EMAIL_DEST") or GMAIL_USER

def enviar_alerta(datos_delitos: dict, representative_image_path: Path, escudo_path: Path):
    hoy = datetime.now()
    fecha_hoy = hoy.strftime("%d/%m/%Y %H:%M")
    
    # Encontrar la fecha más reciente (fecha del último registro global)
    fechas_2026 = []
    for d_name, d_vals in datos_delitos.items():
        if d_vals.get("estado") == "OK" and d_vals.get("fecha_corte_2026"):
            fechas_2026.append(d_vals.get("fecha_corte_2026"))
            
    fecha_ultimo_registro = "N/A"
    if fechas_2026:
        try:
            fechas_parsed = sorted(fechas_2026, key=lambda x: datetime.strptime(x, "%d/%m/%Y"), reverse=True)
            fecha_ultimo_registro = fechas_parsed[0]
        except Exception:
            fecha_ultimo_registro = fechas_2026[0]

    # Construir las filas de la tabla de delitos en HTML
    filas_delitos_html = ""
    filas_operativos_html = ""
    resumen_novedades_list = []
    
    # Ordenar delitos colocando Homicidios primero, y luego por orden alfabético
    delitos_ordenados = sorted(
        datos_delitos.keys(), 
        key=lambda x: (0 if "homicidio" in x.lower() else 1, x)
    )
    
    for delito in delitos_ordenados:
        valores = datos_delitos[delito]
        tipo_tematica = valores.get("tipo", "delito")
        estado_delito = valores.get("estado", "OK")
        fecha_corte_2026 = valores.get("fecha_corte_2026")
        
        # Subtexto de fecha del último caso
        subtexto_fecha = ""
        if fecha_corte_2026:
            subtexto_fecha = f"""
            <div style="font-size: 10px; font-weight: normal; color: #888899; margin-top: 2px;">
              Último caso: {fecha_corte_2026}
            </div>
            """
        
        # Si el delito falló en la recolección, se pinta una fila de error destacada
        if estado_delito != "OK":
            fila_err = f"""
            <tr style="border-bottom: 1px solid #eef0f7; background-color: #fffafb;">
              <td style="padding: 10px 12px; font-size: 13px; font-weight: bold; color: #1A1A2E;">
                {delito}
              </td>
              <td style="padding: 10px 12px; font-size: 13px; text-align: center; color: #a1a3b5;">—</td>
              <td style="padding: 10px 12px; font-size: 13px; text-align: center; color: #a1a3b5;">—</td>
              <td style="padding: 10px 12px; font-size: 13px; text-align: center; color: #a1a3b5;">—</td>
              <td style="padding: 10px 12px; font-size: 11px; text-align: center; font-weight: bold; color: #c0392b; background-color: #fdf2f2; border-radius: 4px; display: inline-block; margin: 6px 12px; padding: 4px 8px;">{estado_delito}</td>
            </tr>
            """
            if tipo_tematica == "operativo":
                filas_operativos_html += fila_err
            else:
                filas_delitos_html += fila_err
            continue
            
        v_2025 = valores.get("2025", 0) or 0
        v_2026 = valores.get("2026", 0) or 0
        
        # Calcular variaciones
        diff = v_2026 - v_2025
        var_pct_str = "0.0%"
        if v_2025 > 0:
            var_pct = (diff / v_2025) * 100.0
            var_pct_str = f"{var_pct:+.1f}%"
        elif v_2026 > 0:
            var_pct_str = "N/A"
            
        signo = "+" if diff > 0 else ""
        diff_str = f"{signo}{diff}" if diff != 0 else "0"
        
        # Colores e iconos de estado
        if diff > 0:
            if tipo_tematica == "operativo":
                color = "#1A7A4A"  # Verde para aumento en operativos (acciones positivas)
                estado = "SUBE ▲"
            else:
                color = "#C0392B"  # Rojo para aumentos en delitos
                estado = "SUBE ▲"
        elif diff < 0:
            if tipo_tematica == "operativo":
                color = "#C0392B"  # Rojo para reducción en operativos
                estado = "BAJA ▼"
            else:
                color = "#1A7A4A"  # Verde para disminuciones en delitos
                estado = "BAJA ▼"
        else:
            color = "#606175"  # Gris sin cambios
            estado = "IGUAL ＝"
            
        # Añadir al resumen rápido en texto
        if diff != 0:
            resumen_novedades_list.append(
                f"<li><b>{delito}</b>: {v_2025} -> {v_2026} ({var_pct_str})</li>"
            )
            
        fila_ok = f"""
        <tr style="border-bottom: 1px solid #eef0f7;">
          <td style="padding: 10px 12px; font-size: 13px; font-weight: bold; color: #1A1A2E;">
            {delito}
            {subtexto_fecha}
          </td>
          <td style="padding: 10px 12px; font-size: 13px; text-align: center; color: #606175;">{v_2025}</td>
          <td style="padding: 10px 12px; font-size: 13px; text-align: center; font-weight: bold; color: #281FD0;">{v_2026}</td>
          <td style="padding: 10px 12px; font-size: 13px; text-align: center; font-weight: bold; color: {color};">{diff_str}</td>
          <td style="padding: 10px 12px; font-size: 12px; text-align: center; font-weight: bold; color: {color};">{estado} ({var_pct_str})</td>
        </tr>
        """
        if tipo_tematica == "operativo":
            filas_operativos_html += fila_ok
        else:
            filas_delitos_html += fila_ok
        
    novedades_box_html = ""
    if resumen_novedades_list:
        novedades_box_html = f"""
        <div style="background: #fff8eb; border-left: 4px solid #ff9800; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">
          <div style="font-size: 13px; font-weight: bold; color: #b7791f; margin-bottom: 6px;">Novedades del Monitoreo:</div>
          <ul style="font-size: 12px; color: #555; margin: 0; padding-left: 18px; line-height: 1.6;">
            {"".join(resumen_novedades_list)}
          </ul>
        </div>
        """
        
    asunto = f"🚨 Actualización SIEDCO Jamundí · {hoy.strftime('%d/%m/%Y %H:%M')}"
    
    # Estructura del HTML Premium (Similar a Mindefensa/Policía + Escudo Oficial)
    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f8; padding: 20px; margin: 0; color: #1A1A2E;">
      <div style="max-width: 650px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,.12); border: 1px solid #e1e2eb;">
        
        <!-- Encabezado con Escudo e Identidad Institucional -->
        <table style="width: 100%; background: #281FD0; border-bottom: 4px solid #FFE000; border-collapse: collapse;">
          <tr>
            <td style="padding: 24px 12px 20px 24px; width: 70px; vertical-align: middle;">
              <img src="cid:escudo_img" alt="Escudo Jamundí" style="width: 55px; height: auto; display: block;" />
            </td>
            <td style="padding: 24px 24px 20px 12px; vertical-align: middle;">
              <div style="font-size: 10px; color: #FFE000; letter-spacing: 2px; font-weight: bold; text-transform: uppercase;">Alcaldía de Jamundí · Valle del Cauca</div>
              <div style="font-size: 20px; font-weight: bold; color: white; margin-top: 4px;">Observatorio del Delito</div>
              <div style="font-size: 12px; color: rgba(255,255,255,.75); margin-top: 4px;">Monitoreo SIEDCO (Estadística Delictiva Policía Nacional)</div>
            </td>
          </tr>
        </table>
        
        <!-- Cuerpo del mensaje -->
        <div style="padding: 24px 28px;">
          <span style="background: #281FD0; color: white; font-size: 10px; font-weight: bold; letter-spacing: 2px; padding: 5px 14px; border-radius: 20px; text-transform: uppercase;">Boletín Informativo</span>
          
          <h2 style="color: #281FD0; font-size: 18px; margin: 15px 0 8px;">Consolidado de Criminalidad y Convivencia</h2>
          <p style="color: #606175; font-size: 13px; margin: 0 0 20px; line-height: 1.5;">
            Se ha realizado la descarga y comparación en tiempo real de los principales indicadores delictivos oficiales registrados en el portal <b>SIEDCO</b> para el municipio de <b>Jamundí</b> (corte global de información: <b>{fecha_ultimo_registro}</b>). Cifras acumuladas al corte del periodo de consulta:
          </p>
          
          {novedades_box_html}
          
          <!-- Tabla Consolidada Comparativa -->
          <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
            <thead>
              <tr style="background: #281FD0; color: white; border-bottom: 3px solid #FFE000;">
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: left; letter-spacing: 0.5px;">Conducta Delictiva</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 12%;">Año 2025</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 12%;">Año 2026</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 12%;">Var</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 26%;">Estado</th>
              </tr>
            </thead>
            <tbody>
              {filas_delitos_html}
            </tbody>
          </table>
          
          <h2 style="color: #281FD0; font-size: 18px; margin: 28px 0 8px;">Actividad Operativa de la Fuerza Pública</h2>
          <p style="color: #606175; font-size: 13px; margin: 0 0 20px; line-height: 1.5;">
            Acciones preventivas, detenciones y recuperación de bienes registradas en el municipio:
          </p>
          
          <!-- Tabla Consolidada de Operativos -->
          <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
            <thead>
              <tr style="background: #281FD0; color: white; border-bottom: 3px solid #FFE000;">
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: left; letter-spacing: 0.5px;">Acción Operativa</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 12%;">Año 2025</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 12%;">Año 2026</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 12%;">Var</th>
                <th style="padding: 10px 12px; font-size: 11px; text-transform: uppercase; font-weight: bold; text-align: center; letter-spacing: 0.5px; width: 26%;">Estado</th>
              </tr>
            </thead>
            <tbody>
              {filas_operativos_html}
            </tbody>
          </table>
          
          <!-- Captura de Pantalla del Dashboard Principal -->
          <div style="margin: 20px 0 10px; border: 1px solid #e1e2eb; border-radius: 6px; overflow: hidden; background: #fff;">
            <div style="background: #f8f9fc; padding: 8px 12px; font-size: 11px; color: #606175; border-bottom: 1px solid #e1e2eb; font-weight: bold;">
              📊 Visualización del panel SIEDCO (Homicidios Jamundí):
            </div>
            <img src="cid:dashboard_img" alt="Dashboard SIEDCO" style="width: 100%; height: auto; display: block;" />
          </div>
          
          <p style="font-size: 11px; color: #a1a3b5; margin-top: 15px; text-align: center; font-style: italic;">
            * Nota: Las cifras representan el acumulado del año actual frente al mismo periodo del año anterior para fines comparativos del Observatorio.
          </p>
        </div>
        
        <!-- Pie de Página -->
        <div style="background: #281FD0; padding: 14px 28px; border-top: 3px solid #FFE000; text-align: center;">
          <p style="color: rgba(255,255,255,.8); font-size: 10px; margin: 0;">
            Alcaldía de Jamundí · Secretaría de Seguridad y Convivencia · Observatorio del Delito
          </p>
          <p style="color: rgba(255,255,255,.5); font-size: 9px; margin: 4px 0 0;">
            Generado automáticamente por el Monitor SIEDCO en GitHub Actions · {fecha_hoy}
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    
    # 1. Guardar siempre una copia local de prueba del HTML para que el usuario la visualice directamente
    prueba_path = Path("reporte_siedco_prueba.html")
    # Para la visualización local en navegador sin servidor, reemplazamos el cid por la ruta relativa
    html_local = cuerpo_html.replace("cid:escudo_img", "escudo_jamundi.png")
    html_local = html_local.replace("cid:dashboard_img", representative_image_path.name)
    
    with open(prueba_path, "w", encoding="utf-8") as pf:
        pf.write(html_local)
    print(f"[OK] Reporte HTML de prueba local generado en: {prueba_path.absolute()}")
    
    # 2. Intentar enviar por correo si hay credenciales
    if not GMAIL_USER or not GMAIL_PASS:
        print("Aviso: Faltan las credenciales GMAIL_USER o GMAIL_PASS en las variables de entorno. Se omite el envío de correo.")
        return

    # Crear el mensaje de correo
    msg = MIMEMultipart("related")
    msg["Subject"] = asunto
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_DEST
    
    # Cuerpo HTML
    msg_html = MIMEText(cuerpo_html, "html", "utf-8")
    msg.attach(msg_html)
    
    # Incrustar el Escudo (CID)
    if escudo_path.exists():
        with open(escudo_path, "rb") as esc_file:
            mime_esc = MIMEImage(esc_file.read())
            mime_esc.add_header("Content-ID", "<escudo_img>")
            mime_esc.add_header("Content-Disposition", "inline", filename=escudo_path.name)
            msg.attach(mime_esc)
    else:
        print(f"Advertencia: No se encontró el escudo en {escudo_path} para la cabecera.")
        
    # Incrustar la imagen del dashboard (CID)
    if representative_image_path.exists():
        with open(representative_image_path, "rb") as img_file:
            mime_img = MIMEImage(img_file.read())
            mime_img.add_header("Content-ID", "<dashboard_img>")
            mime_img.add_header("Content-Disposition", "inline", filename=representative_image_path.name)
            msg.attach(mime_img)
            
        # Adjuntarla como archivo ordinario
        with open(representative_image_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={representative_image_path.name}")
        msg.attach(part)
    else:
        print(f"Advertencia: No se encontró la captura en {representative_image_path} para adjuntar.")

    # Conectar al SMTP SSL de Gmail y enviar
    lista_destinatarios = [email.strip() for email in EMAIL_DEST.split(",") if email.strip()]
    print(f"Conectando al SMTP de Gmail para enviar reporte consolidado a {lista_destinatarios}...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, lista_destinatarios, msg.as_string())
    print(f"[OK] Alerta de correo SIEDCO consolidada enviada exitosamente a {EMAIL_DEST}.")

if __name__ == "__main__":
    # Datos de prueba para correr notificar_siedco.py directamente con errores
    test_data = {
        "Homicidios": {"2025": 58, "2026": 61, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "delito"},
        "Hurto a personas": {"2025": 232, "2026": 197, "fecha_corte_2025": "12/06/2025", "fecha_corte_2026": "12/06/2026", "estado": "OK", "tipo": "delito"},
        "Hurto a residencias": {"2025": 31, "2026": 35, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "delito"},
        "Hurto a comercio": {"2025": 32, "2026": 31, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "delito"},
        "Hurto automotores": {"2025": 25, "2026": 36, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "delito"},
        "Hurto motocicletas": {"2025": 68, "2026": 92, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "delito"},
        "Lesiones personales": {"2025": 171, "2026": 151, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "delito"},
        "Violencia intrafamiliar": {"2025": 111, "2026": 139, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "delito"},
        "Capturas": {"2025": 238, "2026": 157, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "operativo"},
        "Automotores recuperados": {"2025": 16, "2026": 12, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "operativo"},
        "Motocicletas recuperadas": {"2025": 61, "2026": 50, "fecha_corte_2025": "11/06/2025", "fecha_corte_2026": "11/06/2026", "estado": "OK", "tipo": "operativo"}
    }
    TEST_IMG = Path(__file__).resolve().parent / "siedco_homicidios.png"
    if not TEST_IMG.exists():
        TEST_IMG = Path(__file__).resolve().parent / "siedco_jamundi_final.png"
    ESCUDO_IMG = Path(__file__).resolve().parent / "escudo_jamundi.png"
    enviar_alerta(test_data, TEST_IMG, ESCUDO_IMG)
