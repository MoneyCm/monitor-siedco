import os
import re
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, KeepTogether

class PDFGeneratorSIEDCO:
    """Generador de boletín PDF institucional oficial para SIEDCO Jamundí."""
    def __init__(self):
        self.azul = colors.HexColor("#281FD0")
        self.amarillo = colors.HexColor("#FFE000")
        self.gris_suave = colors.HexColor("#f4f4f8")
        self.rojo = colors.HexColor("#C0392B")
        self.verde = colors.HexColor("#1A7A4A")

    def _crear_grafica_comparativa(self, datos_delitos):
        """Genera y guarda una gráfica de barras comparativas 2025 vs 2026."""
        delitos = [
            name for name, vals in datos_delitos.items() 
            if vals.get("tipo") == "delito" and vals.get("estado") == "OK"
        ]
        if not delitos:
            return None
            
        # Ordenar delitos por cantidad en el año 2026
        delitos = sorted(delitos, key=lambda d: datos_delitos[d].get("2026", 0) or 0, reverse=True)
        
        v_2025 = [datos_delitos[d].get("2025", 0) or 0 for d in delitos]
        v_2026 = [datos_delitos[d].get("2026", 0) or 0 for d in delitos]
        
        fig, ax = plt.subplots(figsize=(10, 4.5), dpi=120)
        fig.patch.set_facecolor("#f4f4f8")
        ax.set_facecolor("#ffffff")
        
        x = range(len(delitos))
        width = 0.35
        
        rects1 = ax.bar([i - width/2 for i in x], v_2025, width, label="Año 2025", color='#606175', alpha=0.8)
        rects2 = ax.bar([i + width/2 for i in x], v_2026, width, label="Año 2026", color='#281FD0')
        
        # Colocar etiquetas numéricas encima de cada barra
        for rect in rects1:
            height = rect.get_height()
            ax.annotate(f'{int(height)}', xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8, color='#555555')
        for rect in rects2:
            height = rect.get_height()
            ax.annotate(f'{int(height)}', xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8, color='#000000', fontweight='bold')
                        
        ax.set_xticks(x)
        ax.set_xticklabels(delitos, rotation=20, ha="right", fontsize=8.5)
        ax.legend(loc='upper right')
        ax.set_title("Comparativo Acumulado de Delitos (Jamundí)", color='#281FD0', fontweight='bold', pad=12, fontsize=11)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cccccc')
        ax.spines['bottom'].set_color('#cccccc')
        
        plt.tight_layout()
        path = "temp_grafica_comparativa_siedco.png"
        plt.savefig(path, facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        return path

    def generar(self, datos_delitos, output_pdf="reporte_siedco_jamundi.pdf", escudo_path="escudo_jamundi.png"):
        """Compone y compila el documento PDF oficial."""
        hoy = datetime.now()
        
        # Encontrar la fecha de corte más reciente
        fechas_2026 = []
        for vals in datos_delitos.values():
            if vals.get("estado") == "OK" and vals.get("fecha_corte_2026"):
                fechas_2026.append(vals.get("fecha_corte_2026"))
        
        fecha_corte = "N/A"
        if fechas_2026:
            try:
                fechas_parsed = sorted(fechas_2026, key=lambda x: datetime.strptime(x, "%d/%m/%Y"), reverse=True)
                fecha_corte = fechas_parsed[0]
            except Exception:
                fecha_corte = fechas_2026[0]

        # Estructura del documento
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=A4,
            leftMargin=1.5*cm,
            rightMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilos tipográficos
        style_title = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=16, textColor=self.azul, fontName='Helvetica-Bold')
        style_subtitle = ParagraphStyle('T2', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#606175"))
        style_section_title = ParagraphStyle('S1', parent=styles['Heading2'], fontSize=12, textColor=self.azul, fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=8)
        style_th = ParagraphStyle('TH', parent=styles['Normal'], fontSize=8.5, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
        style_td = ParagraphStyle('TD', parent=styles['Normal'], fontSize=8.5, textColor=colors.HexColor("#1A1A2E"))
        style_td_bold = ParagraphStyle('TDB', parent=styles['Normal'], fontSize=8.5, textColor=self.azul, fontName='Helvetica-Bold', alignment=TA_CENTER)
        
        # Cabecera con Escudo
        logo = Path(escudo_path)
        header_data = [
            [
                Image(str(logo), 1.3*cm, 1.8*cm) if logo.exists() else "",
                [
                    Paragraph("ALCALDÍA DE JAMUNDÍ · VALLE DEL CAUCA", ParagraphStyle('H1', fontSize=8.5, fontName='Helvetica-Bold', textColor=self.azul)),
                    Paragraph("Observatorio del Delito - Boletín Estadístico SIEDCO", style_title),
                    Paragraph(f"Corte global de información al {fecha_corte} | Generado: {hoy.strftime('%d/%m/%Y %H:%M')}", style_subtitle)
                ],
                [
                    Paragraph("<b>CONFIDENCIAL</b>", ParagraphStyle('Conf', fontSize=8.5, textColor=self.rojo, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
                    Paragraph("Uso Institucional", ParagraphStyle('Conf2', fontSize=7.5, textColor=colors.grey, alignment=TA_RIGHT))
                ]
            ]
        ]
        
        header_table = Table(header_data, colWidths=[1.8*cm, 12.2*cm, 4.0*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(header_table)
        
        # Línea de separación institucional amarilla
        elements.append(HRFlowable(width="100%", thickness=3, color=self.amarillo, spaceBefore=4, spaceAfter=14))
        
        # --- TABLA DE INDICADORES DE CRIMINALIDAD ---
        elements.append(Paragraph("Consolidado de Criminalidad y Convivencia", style_section_title))
        
        delitos_cols = [
            Paragraph("Conducta Delictiva", style_th),
            Paragraph("Año 2025", style_th),
            Paragraph("Año 2026", style_th),
            Paragraph("Var", style_th),
            Paragraph("Estado", style_th),
            Paragraph("Último Caso", style_th)
        ]
        
        delitos_table_data = [delitos_cols]
        
        delitos_ordenados = sorted(
            [d for d, v in datos_delitos.items() if v.get("tipo") == "delito"],
            key=lambda x: (0 if "homicidio" in x.lower() else 1, x)
        )
        
        for d in delitos_ordenados:
            v = datos_delitos[d]
            v25 = v.get("2025", 0) or 0
            v26 = v.get("2026", 0) or 0
            diff = v26 - v25
            
            signo = "+" if diff > 0 else ""
            diff_str = f"{signo}{diff}" if diff != 0 else "0"
            
            var_pct_str = "0.0%"
            if v25 > 0:
                var_pct_str = f"{(diff / v25) * 100.0:+.1f}%"
            elif v26 > 0:
                var_pct_str = "N/A"
                
            if diff > 0:
                color_stat = self.rojo
                est_str = f"SUBE ▲ ({var_pct_str})"
            elif diff < 0:
                color_stat = self.verde
                est_str = f"BAJA ▼ ({var_pct_str})"
            else:
                color_stat = colors.HexColor("#606175")
                est_str = f"IGUAL ＝ ({var_pct_str})"
                
            estado_p = Paragraph(f"<b>{est_str}</b>", ParagraphStyle('Est', fontSize=8, textColor=color_stat, alignment=TA_CENTER, fontName='Helvetica-Bold'))
            
            delitos_table_data.append([
                Paragraph(f"<b>{d}</b>", style_td),
                Paragraph(f"{v25:,}", ParagraphStyle('N1', fontSize=8.5, alignment=TA_CENTER)),
                Paragraph(f"<b>{v26:,}</b>", style_td_bold),
                Paragraph(f"<b>{diff_str}</b>", ParagraphStyle('N2', fontSize=8.5, alignment=TA_CENTER, textColor=color_stat, fontName='Helvetica-Bold')),
                estado_p,
                Paragraph(v.get("fecha_corte_2026") or "N/A", ParagraphStyle('D1', fontSize=8, alignment=TA_CENTER))
            ])
            
        t_delitos = Table(delitos_table_data, colWidths=[5.5*cm, 2.0*cm, 2.0*cm, 2.0*cm, 3.8*cm, 2.7*cm])
        t_delitos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), self.azul),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_delitos)
        elements.append(Spacer(1, 12))
        
        # --- TABLA DE ACTIVIDAD OPERATIVA ---
        elements.append(Paragraph("Actividad Operativa de la Fuerza Pública", style_section_title))
        
        ops_cols = [
            Paragraph("Acción Operativa", style_th),
            Paragraph("Año 2025", style_th),
            Paragraph("Año 2026", style_th),
            Paragraph("Var", style_th),
            Paragraph("Estado", style_th),
            Paragraph("Último Registro", style_th)
        ]
        
        ops_table_data = [ops_cols]
        ops_ordenados = sorted(
            [d for d, v in datos_delitos.items() if v.get("tipo") == "operativo"],
            key=lambda x: x
        )
        
        for d in ops_ordenados:
            v = datos_delitos[d]
            v25 = v.get("2025", 0) or 0
            v26 = v.get("2026", 0) or 0
            diff = v26 - v25
            
            signo = "+" if diff > 0 else ""
            diff_str = f"{signo}{diff}" if diff != 0 else "0"
            
            var_pct_str = "0.0%"
            if v25 > 0:
                var_pct_str = f"{(diff / v25) * 100.0:+.1f}%"
            elif v26 > 0:
                var_pct_str = "N/A"
                
            # Para operativos, un aumento es verde (positivo) y disminución es rojo (negativo)
            if diff > 0:
                color_stat = self.verde
                est_str = f"SUBE ▲ ({var_pct_str})"
            elif diff < 0:
                color_stat = self.rojo
                est_str = f"BAJA ▼ ({var_pct_str})"
            else:
                color_stat = colors.HexColor("#606175")
                est_str = f"IGUAL ＝ ({var_pct_str})"
                
            estado_p = Paragraph(f"<b>{est_str}</b>", ParagraphStyle('EstOps', fontSize=8, textColor=color_stat, alignment=TA_CENTER, fontName='Helvetica-Bold'))
            
            ops_table_data.append([
                Paragraph(f"<b>{d}</b>", style_td),
                Paragraph(f"{v25:,}", ParagraphStyle('N1_op', fontSize=8.5, alignment=TA_CENTER)),
                Paragraph(f"<b>{v26:,}</b>", style_td_bold),
                Paragraph(f"<b>{diff_str}</b>", ParagraphStyle('N2_op', fontSize=8.5, alignment=TA_CENTER, textColor=color_stat, fontName='Helvetica-Bold')),
                estado_p,
                Paragraph(v.get("fecha_corte_2026") or "N/A", ParagraphStyle('D1_op', fontSize=8, alignment=TA_CENTER))
            ])
            
        t_ops = Table(ops_table_data, colWidths=[5.5*cm, 2.0*cm, 2.0*cm, 2.0*cm, 3.8*cm, 2.7*cm])
        t_ops.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), self.azul),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_ops)
        elements.append(Spacer(1, 14))
        
        # --- IMAGEN DE LA GRÁFICA COMPARATIVA ---
        graf_path = self._crear_grafica_comparativa(datos_delitos)
        if graf_path and os.path.exists(graf_path):
            img_element = Image(graf_path, 16.5*cm, 7.5*cm)
            elements.append(KeepTogether([
                Paragraph("Comparativo Visual de Incidencia Delictiva", style_section_title),
                img_element
            ]))
            elements.append(Spacer(1, 10))
            
        # --- BLOQUE DE FIRMA Y PIE DE PÁGINA ---
        style_firma = ParagraphStyle('Firm', parent=styles['Normal'], fontSize=9, textColor=colors.black, alignment=TA_CENTER, leading=13)
        firma_elements = [
            Spacer(1, 12),
            Paragraph("<b>Elaborado por:</b>", style_firma),
            Paragraph("César Alfonso Forero Molano", style_firma),
            Paragraph("Profesional Secretaría de Seguridad y Convivencia", style_firma),
            Spacer(1, 15),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceBefore=2, spaceAfter=8),
            Paragraph("Fuente de datos: Sistema de Información Estadístico, Delincuencial, Contravencional y Operativo (SIEDCO) - Policía Nacional de Colombia", ParagraphStyle('F1', fontSize=7, textColor=colors.grey, alignment=TA_CENTER)),
            Paragraph("Reporte generado de forma automatizada por el Observatorio de Jamundí", ParagraphStyle('F2', fontSize=6.5, textColor=colors.grey, alignment=TA_CENTER))
        ]
        
        elements.append(KeepTogether(firma_elements))
        
        # Compilar el PDF
        doc.build(elements)
        print(f"[OK] Reporte PDF generado exitosamente en: {output_pdf}")
        
        # Eliminar archivo temporal de la gráfica
        if graf_path and os.path.exists(graf_path):
            try:
                os.remove(graf_path)
            except Exception:
                pass
                
        return output_pdf

if __name__ == "__main__":
    # Prueba rápida
    import json
    resumen_test = Path("resumen_actual.json")
    if resumen_test.exists():
        with open(resumen_test, "r", encoding="utf-8") as f:
            data = json.load(f)
        gen = PDFGeneratorSIEDCO()
        gen.generar(data, "reporte_siedco_jamundi_test.pdf")
