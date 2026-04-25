import os
import io
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import pandas as pd
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Global flag to ensure fonts are only registered once
_FONTS_REGISTERED = False

def register_banking_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    try:
        base_font_dir = os.path.abspath(os.path.join(os.getcwd(), 'assets', 'fonts'))
        # Registering with unique names to avoid system collisions
        pdfmetrics.registerFont(TTFont('BankNotoDev', os.path.join(base_font_dir, 'NotoSansDevanagari-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('BankNotoDevBold', os.path.join(base_font_dir, 'NotoSansDevanagari_SemiCondensed-Bold.ttf')))
        pdfmetrics.registerFont(TTFont('BankNotoTamil', os.path.join(base_font_dir, 'NotoSerifTamil_Condensed-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('BankNotoTamilBold', os.path.join(base_font_dir, 'NotoSerifTamil_Condensed-Bold.ttf')))
        _FONTS_REGISTERED = True
    except Exception as e:
        print(f"Error registering fonts: {e}")

class PDFService:
    """
    PDFService: Generates PDF reports using Jinja2 and xhtml2pdf (Pure Python).
    """
    
    def __init__(self, template_dir: str = 'templates'):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        # Add custom filters
        self.env.filters['format_num'] = lambda v: f"{float(v):,.2f}"
        self.env.globals['abs_val'] = abs
        # Register fonts once
        register_banking_fonts()

    def render_risk_advisory(self, 
                             sol: str, 
                             branch_name: str, 
                             date: datetime, 
                             metrics: dict, 
                             prev_metrics: dict,
                             ref_no: str = "IOB/RO/PLAN/2026/001",
                             office_details: dict = None,
                             branch_details: dict = None,
                             prev_date: datetime = None) -> bytes:
        """
        Renders the Operational Risk Advisory PDF.
        Returns PDF bytes.
        """
        template = self.env.get_template('premium_letter.html')
        
        # Default logo path
        logo_path = os.path.join(os.getcwd(), 'assets', 'doc.svg')
        if not os.path.exists(logo_path):
            logo_path = None

        html_content = template.render(
            sol=sol,
            branch_name=branch_name,
            date=date.strftime('%d-%m-%Y'),
            prev_date=prev_date.strftime('%d-%m-%Y') if prev_date else 'Previous',
            period=date.strftime('%B %Y'),
            ref_no=ref_no,
            metrics=metrics,
            prev_metrics=prev_metrics,
            logo_path=logo_path,
            office_details=office_details or {},
            branch_details=branch_details or {}
        )
        
        # Create a file-like buffer to receive PDF data
        result = io.BytesIO()
        
        # Run pisa to create PDF - passing string directly is more reliable on some systems
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=result,
            encoding='utf-8'
        )
        
        if pisa_status.err:
            # Fallback to HTML bytes if PDF generation fails
            return html_content.encode('utf-8')
            
        return result.getvalue()
