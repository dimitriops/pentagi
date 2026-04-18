"""Simple Markdown to PDF converter for guided scan reports."""

import subprocess
import os
import logging

log = logging.getLogger(__name__)


def md_to_pdf(md_path, pdf_path):
    """Convert markdown file to PDF. Tries multiple methods with proper fallback."""
    
    # Method 1: pandoc (best quality)
    try:
        result = subprocess.run(
            ["pandoc", md_path, "-o", pdf_path, 
             "--pdf-engine=xelatex",
             "-V", "geometry:margin=2cm",
             "-V", "fontsize=11pt"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(pdf_path):
            return pdf_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Generate HTML from markdown (needed for methods 2 and 3)
    html_path = None
    try:
        import markdown
        with open(md_path, 'r') as f:
            md_content = f.read()
        
        html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
        
        html_full = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: sans-serif; font-size: 11pt; line-height: 1.5; margin: 2cm; color: #1a1a1a; }}
h1 {{ color: #c0392b; border-bottom: 2px solid #c0392b; padding-bottom: 8px; }}
h2 {{ color: #2c3e50; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 25px; }}
pre {{ background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; font-size: 9pt; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
code {{ background: #f0f0f0; padding: 2px 5px; border-radius: 3px; font-size: 9.5pt; }}
pre code {{ background: none; color: #d4d4d4; padding: 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }}
th {{ background: #2c3e50; color: white; padding: 8px; text-align: left; }}
td {{ border: 1px solid #ddd; padding: 7px; }}
tr:nth-child(even) {{ background: #f9f9f9; }}
strong {{ color: #2c3e50; }}
</style></head><body>{html_body}</body></html>"""
        
        html_path = md_path.replace('.md', '.html')
        with open(html_path, 'w') as f:
            f.write(html_full)
    except Exception as e:
        log.warning(f"HTML generation failed: {e}")
        return None
    
    # Method 2: wkhtmltopdf
    try:
        result = subprocess.run(
            ["wkhtmltopdf", "--quiet", "--page-size", "A4", html_path, pdf_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(pdf_path):
            return pdf_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # wkhtmltopdf not installed — try next method
    
    # Method 3: weasyprint (Python library)
    try:
        from weasyprint import HTML as WeasyHTML
        WeasyHTML(filename=html_path).write_pdf(pdf_path)
        if os.path.exists(pdf_path):
            return pdf_path
    except ImportError:
        log.warning("weasyprint not installed")
    except Exception as e:
        log.warning(f"weasyprint failed: {e}")
    
    # All methods failed
    log.error("All PDF conversion methods failed")
    return None
