#!/usr/bin/env python3
"""
DACT Pipeline 文档构建脚本

这个脚本用于构建 DACT Pipeline 的文档，支持多种格式和语言。
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并检查结果"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    
    return result


def clean_build_dir(build_dir):
    """清理构建目录"""
    if build_dir.exists():
        print(f"Cleaning build directory: {build_dir}")
        shutil.rmtree(build_dir)
    
    build_dir.mkdir(parents=True, exist_ok=True)


def install_dependencies():
    """安装文档构建依赖"""
    print("Installing documentation dependencies...")
    run_command("pip install -r requirements.txt")


def build_html_docs(source_dir, build_dir, language="zh_CN"):
    """构建 HTML 文档"""
    print(f"Building HTML documentation in {language}...")
    
    html_dir = build_dir / f"html-{language}"
    html_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = f"sphinx-build -b html -D language={language} {source_dir} {html_dir}"
    run_command(cmd)
    
    print(f"HTML documentation built in: {html_dir}")
    return html_dir


def build_pdf_docs(source_dir, build_dir, language="zh_CN"):
    """构建 PDF 文档"""
    print(f"Building PDF documentation in {language}...")
    
    latex_dir = build_dir / f"latex-{language}"
    latex_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建 LaTeX
    cmd = f"sphinx-build -b latex -D language={language} {source_dir} {latex_dir}"
    run_command(cmd)
    
    # 构建 PDF
    pdf_file = latex_dir / "dact-pipeline.pdf"
    if (latex_dir / "dact-pipeline.tex").exists():
        run_command("pdflatex dact-pipeline.tex", cwd=latex_dir)
        run_command("pdflatex dact-pipeline.tex", cwd=latex_dir)  # 运行两次确保交叉引用正确
        
        if pdf_file.exists():
            print(f"PDF documentation built: {pdf_file}")
            return pdf_file
    
    print("PDF build failed or not available")
    return None


def build_epub_docs(source_dir, build_dir, language="zh_CN"):
    """构建 EPUB 文档"""
    print(f"Building EPUB documentation in {language}...")
    
    epub_dir = build_dir / f"epub-{language}"
    epub_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = f"sphinx-build -b epub -D language={language} {source_dir} {epub_dir}"
    run_command(cmd)
    
    epub_file = epub_dir / "dact-pipeline.epub"
    if epub_file.exists():
        print(f"EPUB documentation built: {epub_file}")
        return epub_file
    
    return None


def serve_docs(html_dir, port=8000):
    """启动文档服务器"""
    print(f"Starting documentation server on port {port}...")
    print(f"Documentation available at: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    
    try:
        run_command(f"python -m http.server {port}", cwd=html_dir)
    except KeyboardInterrupt:
        print("\nServer stopped")


def main():
    parser = argparse.ArgumentParser(description="Build DACT Pipeline documentation")
    parser.add_argument("--format", choices=["html", "pdf", "epub", "all"], 
                       default="html", help="Documentation format to build")
    parser.add_argument("--language", choices=["zh_CN", "en"], 
                       default="zh_CN", help="Documentation language")
    parser.add_argument("--clean", action="store_true", 
                       help="Clean build directory before building")
    parser.add_argument("--serve", action="store_true", 
                       help="Serve HTML documentation after building")
    parser.add_argument("--port", type=int, default=8000, 
                       help="Port for documentation server")
    parser.add_argument("--install-deps", action="store_true", 
                       help="Install documentation dependencies")
    
    args = parser.parse_args()
    
    # 设置路径
    docs_dir = Path(__file__).parent
    source_dir = docs_dir
    build_dir = docs_dir / "_build"
    
    # 切换到文档目录
    os.chdir(docs_dir)
    
    # 安装依赖
    if args.install_deps:
        install_dependencies()
    
    # 清理构建目录
    if args.clean:
        clean_build_dir(build_dir)
    
    # 构建文档
    html_dir = None
    
    if args.format in ["html", "all"]:
        html_dir = build_html_docs(source_dir, build_dir, args.language)
    
    if args.format in ["pdf", "all"]:
        build_pdf_docs(source_dir, build_dir, args.language)
    
    if args.format in ["epub", "all"]:
        build_epub_docs(source_dir, build_dir, args.language)
    
    # 启动服务器
    if args.serve and html_dir:
        serve_docs(html_dir, args.port)
    
    print("Documentation build completed!")


if __name__ == "__main__":
    main()