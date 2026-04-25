import os
import io
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import pandas as pd
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _font_link_callback(uri, rel):
    """
    Standard link_callback for xhtml2pdf to resolve local paths.
    """
    base_path = os.path.abspath(os.getcwd())
    path = os.path.join(base_path, uri)
    return path

class PDFService:
    """
    PDFService: Generates PDF reports using Jinja2 and xhtml2pdf (Pure Python).
    """
    
    def __init__(self, template_dir: str = 'templates'):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        # Add custom filters
        self.env.filters['format_num'] = lambda v: f"{float(v):,.2f}"
        self.env.globals['abs_val'] = abs

        # Register fonts with ReportLab
        font_dir = os.path.join(os.getcwd(), 'assets', 'fonts')

        pdfmetrics.registerFont(TTFont(
            'NotoSerifTamil_Condensed-Regular',
            os.path.join(font_dir, 'NotoSerifTamil_Condensed-Regular.ttf')
        ))

        pdfmetrics.registerFont(TTFont(
            'NotoSerifTamil_Condensed-Bold',
            os.path.join(font_dir, 'NotoSerifTamil_Condensed-Bold.ttf')
        ))

        pdfmetrics.registerFont(TTFont(
            'NotoSansDevanagari-Regular',
            os.path.join(font_dir, 'NotoSansDevanagari-Regular.ttf')
        ))

        pdfmetrics.registerFont(TTFont(
            'NotoSansDevanagari_SemiCondensed-Bold',
            os.path.join(font_dir, 'NotoSansDevanagari_SemiCondensed-Bold.ttf')
        ))

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
        logo_path = os.path.join('assets', 'doc.svg')

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
        
        # Run pisa to create PDF
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=result,
            link_callback=_font_link_callback
        )
        
        if pisa_status.err:
            # Fallback to HTML bytes if PDF generation fails
            return html_content.encode('utf-8')
            
        return result.getvalue()
