#!/usr/bin/env python3
"""
Vlan24 Accounting System 사용자 매뉴얼 PDF 생성기
"""

import markdown
import weasyprint
from pathlib import Path
import os

def generate_pdf_manual():
    """마크다운 매뉴얼을 PDF로 변환"""
    
    # 입력 및 출력 파일 경로
    md_file = "한국형_오픈뱅킹_회계시스템_사용자_매뉴얼.md"
    pdf_file = "한국형_오픈뱅킹_회계시스템_사용자_매뉴얼.pdf"
    
    try:
        # 마크다운 파일 읽기
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # 마크다운을 HTML로 변환
        html = markdown.markdown(md_content, extensions=['tables', 'codehilite', 'toc'])
        
        # CSS 스타일 추가
        css_style = """
        <style>
        @page {
            size: A4;
            margin: 2cm;
            @bottom-right {
                content: "페이지 " counter(page);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Noto Sans KR', 'Malgun Gothic', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            font-size: 11pt;
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            page-break-before: always;
            font-size: 24pt;
        }
        
        h1:first-child {
            page-break-before: avoid;
        }
        
        h2 {
            color: #34495e;
            border-bottom: 2px solid #e74c3c;
            padding-bottom: 5px;
            margin-top: 30px;
            font-size: 18pt;
        }
        
        h3 {
            color: #2980b9;
            margin-top: 25px;
            font-size: 14pt;
        }
        
        h4 {
            color: #27ae60;
            margin-top: 20px;
            font-size: 12pt;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }
        
        table, th, td {
            border: 1px solid #ddd;
        }
        
        th, td {
            padding: 8px;
            text-align: left;
        }
        
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        
        pre {
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
            overflow-x: auto;
        }
        
        ul, ol {
            margin: 10px 0;
            padding-left: 25px;
        }
        
        li {
            margin: 5px 0;
        }
        
        blockquote {
            border-left: 4px solid #e74c3c;
            margin: 15px 0;
            padding: 10px 20px;
            background-color: #f9f9f9;
        }
        
        .page-break {
            page-break-before: always;
        }
        
        .no-break {
            page-break-inside: avoid;
        }
        
        /* 목차 스타일 */
        .toc {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        
        .toc h2 {
            margin-top: 0;
            color: #2c3e50;
        }
        
        .toc ul {
            list-style-type: none;
            padding-left: 0;
        }
        
        .toc ul ul {
            padding-left: 20px;
        }
        
        .toc a {
            text-decoration: none;
            color: #3498db;
        }
        
        .toc a:hover {
            text-decoration: underline;
        }
        </style>
        """
        
        # 완전한 HTML 문서 생성
        full_html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Vlan24 Accounting System 사용자 매뉴얼</title>
            {css_style}
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        
        # HTML을 PDF로 변환
        print("PDF 생성 중...")
        weasyprint.HTML(string=full_html).write_pdf(pdf_file)
        
        print(f"✅ PDF 매뉴얼이 성공적으로 생성되었습니다: {pdf_file}")
        print(f"📄 파일 크기: {os.path.getsize(pdf_file) / 1024 / 1024:.1f} MB")
        
        return pdf_file
        
    except Exception as e:
        print(f"❌ PDF 생성 중 오류가 발생했습니다: {str(e)}")
        return None

if __name__ == "__main__":
    generate_pdf_manual()