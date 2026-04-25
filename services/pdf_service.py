import os
import io
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import pandas as pd
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from PIL import Image, ImageDraw, ImageFont
import base64

def _render_text_to_b64(text, font_path, font_size=40, color=(30, 41, 59)):
    """
    Renders text to a transparent PNG and returns it as a Base64 string.
    This ensures perfect rendering of Hindi/Tamil characters on systems where PDF font embedding fails.
    """
    try:
        # Load font
        font = ImageFont.truetype(font_path, font_size)
        # Calculate text size - simplified for compatibility
        # We'll use a generous canvas and then crop or just fixed width
        canvas_width = 1200
        canvas_height = 100
        image = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        
        # Render text
        draw.text((0, 0), text, font=font, fill=color)
        
        # Trim whitespace (approximate)
        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)
        
        # Save to buffer
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Text rendering error: {e}")
        return None

def _font_link_callback(uri, rel):
    """
    Convert HTML temporary paths to absolute paths for xhtml2pdf.
    """
    font_dir = os.path.abspath(
        os.path.join(os.getcwd(), 'assets', 'fonts')
    )
    filename = os.path.basename(uri)
    # Only use callback for non-font files (like logos)
    if not filename.endswith('.ttf'):
        return os.path.join(font_dir, filename)
    return uri

class PDFService:
    """
    PDFService: Generates PDF reports using Jinja2 and xhtml2pdf (Pure Python).
    """
    
    def __init__(self, template_dir: str = 'templates'):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        # Add custom filters
        self.env.filters['format_num'] = lambda v: f"{float(v):,.2f}"
        self.env.globals['abs_val'] = abs

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

        # Pre-render trilingual addresses as images to ensure perfect display on Windows
        font_dir = os.path.abspath(os.path.join(os.getcwd(), 'assets', 'fonts'))
        
        # English Address (Optional but keeps consistency)
        addr_en_clean = (office_details.get('address_en') or '').replace('<br/>', '\n')
        
        # Tamil Address
        addr_ta_clean = (office_details.get('address_ta') or '').replace('<br/>', '\n')
        font_ta = os.path.join(font_dir, 'NotoSerifTamil_Condensed-Regular.ttf')
        addr_ta_img = _render_text_to_b64(addr_ta_clean, font_ta, font_size=32)
        
        # Hindi Address
        addr_hi_clean = (office_details.get('address_hi') or '').replace('<br/>', '\n')
        font_hi = os.path.join(font_dir, 'NotoSansDevanagari-Regular.ttf')
        addr_hi_img = _render_text_to_b64(addr_hi_clean, font_hi, font_size=32)

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
            branch_details=branch_details or {},
            addr_ta_img=addr_ta_img,
            addr_hi_img=addr_hi_img
        )
        
        # Create a file-like buffer to receive PDF data
        result = io.BytesIO()
        
        # Run pisa to create PDF - passing string directly is more reliable on some systems
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=result,
            encoding='utf-8',
            link_callback=_font_link_callback
        )
        
        if pisa_status.err:
            # Fallback to HTML bytes if PDF generation fails
            return html_content.encode('utf-8')
            
        return result.getvalue()
