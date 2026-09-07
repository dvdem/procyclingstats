import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
from datetime import datetime

def build_pdf():
    # Paths
    json_path = 'c:/Users/echav/.gemini/antigravity-ide/brain/d6da1dcb-0cff-4c6f-b06e-29394814a5b1/scratch/wellness_out.json'
    pdf_path = 'C:/Users/echav/OneDrive/Documentos/GitHub/procyclingstats/data/wellness_evolucion.pdf'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort data chronologically for line charts
    df = df.sort_values(by=['athlete_name', 'date'])
    
    with PdfPages(pdf_path) as pdf:
        # PAGE 1: TITLE & SUMMARY TABLE
        fig, ax = plt.subplots(figsize=(11, 8.5)) # Letter size landscape
        ax.axis('off')
        
        # Draw background elements / style
        fig.patch.set_facecolor('#f8fafc') # Very light slate/gray background
        
        # Title
        plt.text(0.5, 0.9, 'INFORME DE BIENESTAR (WELLNESS) DE ATLETAS', 
                 transform=ax.transAxes, fontsize=18, fontweight='bold', ha='center', color='#1e293b')
        plt.text(0.5, 0.85, f'Histórico de HRV y Peso (01/Jun/2026 - 08/Jul/2026) | Generado: {datetime.now().strftime("%Y-%m-%d")}', 
                 transform=ax.transAxes, fontsize=11, style='italic', ha='center', color='#64748b')
        
        # Summary statistics per athlete
        stats = []
        for name, group in df.groupby('athlete_name'):
            records_count = len(group)
            
            # HRV stats
            hrv_group = group[group['hrv_rmssd'].notnull()]
            avg_hrv = round(hrv_group['hrv_rmssd'].mean(), 1) if not hrv_group.empty else '-'
            min_hrv = round(hrv_group['hrv_rmssd'].min(), 1) if not hrv_group.empty else '-'
            max_hrv = round(hrv_group['hrv_rmssd'].max(), 1) if not hrv_group.empty else '-'
            
            # Weight stats
            weight_group = group[group['weight'].notnull()]
            last_weight = round(weight_group.iloc[-1]['weight'], 1) if not weight_group.empty else '-'
            
            stats.append([name, records_count, avg_hrv, f"{min_hrv} - {max_hrv}", last_weight])
            
        # Draw a clean table
        headers = ['Ciclista', 'Días con Datos', 'Media HRV (RMSSD)', 'Rango HRV (RMSSD)', 'Último Peso (kg)']
        
        table = plt.table(cellText=stats, colLabels=headers, loc='center', cellLoc='center',
                          colWidths=[0.28, 0.15, 0.18, 0.20, 0.18])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.1, 2.2) # Scale height for better readability
        
        # Style table headers and cells
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#1e293b') # Dark slate header
            else:
                cell.set_facecolor('#ffffff')
                cell.set_edgecolor('#cbd5e1')
                # Alternate row coloring
                if row % 2 == 0:
                    cell.set_facecolor('#f1f5f9')
                    
        # Footer
        plt.text(0.5, 0.05, 'PCS Procyclingstats | Intervals.icu Integration', 
                 transform=ax.transAxes, fontsize=9, ha='center', color='#94a3b8')
                 
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # PAGE 2: HRV EVOLUTION CHART
        fig, ax = plt.subplots(figsize=(11, 8.5))
        fig.patch.set_facecolor('#f8fafc')
        ax.set_facecolor('#ffffff')
        
        # Group and plot lines
        colors = ['#0ea5e9', '#d946ef', '#8b5cf6', '#f59e0b', '#10b981']
        color_idx = 0
        
        for name, group in df.groupby('athlete_name'):
            # Filter non-null HRV records
            hrv_data = group[group['hrv_rmssd'].notnull()]
            if not hrv_data.empty:
                color = colors[color_idx % len(colors)]
                ax.plot(hrv_data['date'], hrv_data['hrv_rmssd'], marker='o', markersize=4, 
                        linewidth=2, label=name, color=color)
                color_idx += 1
                
        # Chart styling
        ax.set_title('Evolución de HRV (RMSSD) por Ciclista', fontsize=16, fontweight='bold', pad=20, color='#1e293b')
        ax.set_xlabel('Fecha', fontsize=11, fontweight='bold', labelpad=10, color='#475569')
        ax.set_ylabel('HRV RMSSD (ms)', fontsize=11, fontweight='bold', labelpad=10, color='#475569')
        
        # Grid lines
        ax.grid(True, linestyle='--', alpha=0.5, color='#cbd5e1')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#94a3b8')
        ax.spines['bottom'].set_color('#94a3b8')
        
        # Legend
        ax.legend(loc='upper right', frameon=True, facecolor='#ffffff', edgecolor='#cbd5e1')
        
        # Format dates on X axis nicely
        fig.autofmt_xdate()
        
        # Footer
        plt.text(0.5, -0.15, 'PCS Procyclingstats | Intervals.icu Integration', 
                 transform=ax.transAxes, fontsize=9, ha='center', color='#94a3b8')
                 
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
    print("PDF generated successfully.")

if __name__ == '__main__':
    build_pdf()
