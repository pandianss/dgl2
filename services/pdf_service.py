import os
import io
import logging
import base64
import subprocess
import tempfile
from jinja2 import Environment, FileSystemLoader
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf_service")

BASE_DIR = Path(__file__).parent.parent

class PDFService:
    """
    v1.2.0 - Added render_standard_document
    """
    """
    PDFService: Generates PDF reports using Jinja2 and an isolated Playwright process.
    Uses subprocess.run with a helper script to avoid asyncio NotImplementedError 
    on Windows/Python 3.14 while maintaining professional PDF formatting.
    """
    
    def __init__(self, template_dir: str = 'templates'):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.env.filters['format_num'] = lambda v: f"{float(v):,.2f}"
        self.env.globals['abs_val'] = abs
        self._font_cache = {}

    def _get_font_b64(self, font_name: str) -> str:
        """Loads and caches base64 font data."""
        if font_name in self._font_cache:
            return self._font_cache[font_name]
        
        font_path = BASE_DIR / 'assets' / 'fonts' / font_name
        if font_path.exists():
            with open(font_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                self._font_cache[font_name] = b64
                return b64
        return ""

    def render_risk_advisory(self, 
                             sol: str, 
                             branch_name: str, 
                             date: datetime, 
                             metrics: dict, 
                             prev_metrics: dict,
                             ref_no: str = "IOB/RO/PLAN/2026/001",
                             office_details: dict = None,
                             branch_details: dict = None,
                             prev_date: datetime = None,
                             header_logo: str = None) -> tuple[bytes, str]:
        """
        Renders the Operational Risk Advisory PDF.
        Delegates rendering to an isolated subprocess for maximum stability.
        """
        template = self.env.get_template('premium_letter.html')
        
        # Load fonts as Base64 for maximum reliability in isolated mode
        font_data = {
            'tamil_reg': self._get_font_b64('NotoSerifTamil_Condensed-Regular.ttf'),
            'hindi_reg': self._get_font_b64('NotoSansDevanagari-Regular.ttf'),
            'tamil_bold': self._get_font_b64('NotoSerifTamil_Condensed-Bold.ttf') or self._get_font_b64('NotoSerifTamil_Condensed-Regular.ttf'),
            'hindi_bold': self._get_font_b64('NotoSansDevanagari_SemiCondensed-Bold.ttf') or self._get_font_b64('NotoSansDevanagari-Regular.ttf')
        }
        
        # Inline the unified branding elements
        assets_dir = BASE_DIR / 'assets'
        logo_raw = ""
        watermark_raw = ""
        
        import re
        logo_path = assets_dir / 'doc.svg'
        if logo_path.exists():
             try:
                 with open(logo_path, 'r', encoding='utf-8') as f:
                     logo_raw = f.read()
                 logo_raw = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"', r'\1', logo_raw)
                 logo_raw = re.sub(r'(<svg[^>]*?)\s+height="[^"]*"', r'\1', logo_raw)
             except Exception as e: logger.error(f"Error reading logo: {e}")

        wm_path = assets_dir / 'logo_center.svg'
        if wm_path.exists():
             try:
                 with open(wm_path, 'r', encoding='utf-8') as f:
                     watermark_raw = f.read()
                 watermark_raw = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"', r'\1', watermark_raw)
                 watermark_raw = re.sub(r'(<svg[^>]*?)\s+height="[^"]*"', r'\1', watermark_raw)
             except Exception as e: logger.error(f"Error reading watermark: {e}")

        html_content = template.render(
            sol=sol,
            branch_name=branch_name,
            date=date.strftime('%d-%m-%Y'),
            prev_date=prev_date.strftime('%d-%m-%Y') if prev_date else 'Previous',
            period=date.strftime('%B %Y'),
            ref_no=ref_no,
            metrics=metrics,
            prev_metrics=prev_metrics,
            header_logo_svg=logo_raw,
            center_watermark_svg=watermark_raw,
            office_details=office_details or {},
            branch_details=branch_details or {},
            font_data=font_data
        )
        
        # Generate temp files for communication with the isolated process
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f_in:
            f_in.write(html_content)
            in_path = f_in.name
            
        out_path = in_path.replace(".html", ".pdf")
        helper_path = BASE_DIR / "services" / "render_helper.py"
        
        try:
            # Execute isolated rendering process
            cmd = ["python", str(helper_path), in_path, out_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Read back the generated PDF
            if os.path.exists(out_path):
                with open(out_path, 'rb') as f_out:
                    pdf_bytes = f_out.read()
                return pdf_bytes, html_content
            else:
                raise RuntimeError("PDF file was not created by helper script.")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Isolated Rendering Error: {e.stderr}")
            raise RuntimeError(f"PDF generation failed in isolated process: {e.stderr}")
        finally:
            # Cleanup
            if os.path.exists(in_path): os.remove(in_path)
            if os.path.exists(out_path): os.remove(out_path)

    def render_standard_document(self, 
                                 template_name: str,
                                 data: dict,
                                 office_details: dict = None) -> tuple[bytes, str]:
        """
        Renders a document using the Standard Premium Layout.
        """
        template = self.env.get_template(template_name)
        
        # Load fonts as Base64 for the Standard Layout
        font_data = {
            'tamil_reg': self._get_font_b64('NotoSerifTamil_Condensed-Regular.ttf'),
            'hindi_reg': self._get_font_b64('NotoSansDevanagari-Regular.ttf'),
            'tamil_bold': self._get_font_b64('NotoSerifTamil_Condensed-Bold.ttf') or self._get_font_b64('NotoSerifTamil_Condensed-Regular.ttf'),
            'hindi_bold': self._get_font_b64('NotoSansDevanagari_SemiCondensed-Bold.ttf') or self._get_font_b64('NotoSansDevanagari-Regular.ttf')
        }
        
        # Inline the unified branding elements
        assets_dir = BASE_DIR / 'assets'
        import re
        
        logo_path = assets_dir / 'doc.svg'
        logo_raw = ""
        if logo_path.exists():
             with open(logo_path, 'r', encoding='utf-8') as f:
                 logo_raw = f.read()
             logo_raw = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"', r'\1', logo_raw)
             logo_raw = re.sub(r'(<svg[^>]*?)\s+height="[^"]*"', r'\1', logo_raw)

        wm_path = assets_dir / 'logo_center.svg'
        watermark_raw = ""
        if wm_path.exists():
             try:
                 with open(wm_path, 'r', encoding='utf-8') as f:
                     watermark_raw = f.read()
                 watermark_raw = re.sub(r'(<svg[^>]*?)\s+width="[^"]*"', r'\1', watermark_raw)
                 watermark_raw = re.sub(r'(<svg[^>]*?)\s+height="[^"]*"', r'\1', watermark_raw)
             except Exception as e: logger.error(f"Error reading watermark: {e}")

        # Merge standard context
        context = {
            **data,
            'font_data': font_data,
            'header_logo_svg': logo_raw,
            'center_watermark_svg': watermark_raw,
            'office_details': office_details or {
                "name": "Regional Office, Dindigul", 
                "contact": "0451-2423456", 
                "email": "roplanning@iob.in",
                "address_en": "80 Feet Road, Dindigul - 624002",
                "address_ta": "80 அடி சாலை, திண்டுக்கல் - 624002",
                "address_hi": "80 फीट रोड, डिंडीगुल - 624002"
            }
        }

        html_content = template.render(**context)
        
        # Generate temp files
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f_in:
            f_in.write(html_content)
            in_path = f_in.name
            
        out_path = in_path.replace(".html", ".pdf")
        helper_path = BASE_DIR / "services" / "render_helper.py"
        
        try:
            cmd = ["python", str(helper_path), in_path, out_path]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if os.path.exists(out_path):
                with open(out_path, 'rb') as f_out:
                    pdf_bytes = f_out.read()
                return pdf_bytes, html_content
            else:
                raise RuntimeError("PDF file was not created.")
        finally:
            if os.path.exists(in_path): os.remove(in_path)
            if os.path.exists(out_path): os.remove(out_path)

    def render_special_report(self, 
                              facts_df: pd.DataFrame, 
                              metric_configs: list,
                              ref_no: str,
                              date: datetime) -> tuple[bytes, str]:
        """
        Generates a Special Analytics Report with Top/Bottom rankings.
        metric_configs: list of {'id': 'CASA_PCT', 'label': 'CASA Mix (%)', 'higher_is_better': True}
        """
        report_metrics = []
        
        for config in metric_configs:
            m_id = config['id']
            if m_id not in facts_df.columns: continue
            
            # Sort data
            sorted_df = facts_df.dropna(subset=[m_id]).sort_values(by=m_id, ascending=not config.get('higher_is_better', True))
            
            top_10 = sorted_df.head(10)
            bottom_10 = sorted_df.tail(10).iloc[::-1] # Reverse to show worst at bottom
            
            def map_items(df):
                max_val = df[m_id].max() or 1
                return [{
                    'name': row['branch_name'],
                    'value': row[m_id],
                    'percent': min(100, (row[m_id] / max_val) * 100) if row[m_id] > 0 else 0,
                    'formatted_value': f"{row[m_id]:,.2f}"
                } for _, row in df.iterrows()]

            report_metrics.append({
                'label': config['label'],
                'top': map_items(top_10),
                'bottom': map_items(bottom_10)
            })

        data = {
            'ref_no': ref_no,
            'date': date.strftime('%d-%m-%Y'),
            'period': date.strftime('%B %Y'),
            'title_en': 'Performance Analytics Report',
            'metrics': report_metrics
        }
        
        return self.render_standard_document('special_report.html', data)
