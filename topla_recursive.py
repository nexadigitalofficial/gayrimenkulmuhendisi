#!/usr/bin/env python3
"""
topla_recursive.py - Iki mod:
    all.txt  - tum dosyalar
    all1.txt - filtrelenmis (gurultu/kucuk dosyalar atlanir)

Kullanim:
    python topla_recursive.py C:/NEXA/LABARATOUVAR
    python topla_recursive.py C:/NEXA/LABARATOUVAR --only-all
    python topla_recursive.py C:/NEXA/LABARATOUVAR --only-all1
    python topla_recursive.py C:/NEXA/LABARATOUVAR --no-code
"""

import sys
import os
import subprocess
import importlib
import argparse
from pathlib import Path
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
#  Otomatik kurucu
# ══════════════════════════════════════════════════════════════════════════════

def ensure(package: str, import_as: str = None):
    name = import_as or package
    try:
        return importlib.import_module(name)
    except ImportError:
        print(f"  [KURULUM] {package} kuruluyor...", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package, "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return importlib.import_module(name)


# ══════════════════════════════════════════════════════════════════════════════
#  Donusturuculer
# ══════════════════════════════════════════════════════════════════════════════

def pdf_to_text(path):
    pypdf = ensure("pypdf")
    reader = pypdf.PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Sayfa {i}]\n{text}")
    return "\n\n".join(pages)

def docx_to_text(path):
    docx = ensure("python-docx", "docx")
    doc = docx.Document(str(path))
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            parts.append(" | ".join(cells))
    return "\n".join(parts)

def md_to_text(path):
    md_mod = ensure("markdown")
    bs4    = ensure("beautifulsoup4", "bs4")
    raw    = path.read_text(encoding="utf-8", errors="replace")
    html   = md_mod.markdown(raw)
    soup   = bs4.BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")

def html_to_text(path):
    bs4  = ensure("beautifulsoup4", "bs4")
    raw  = path.read_text(encoding="utf-8", errors="replace")
    soup = bs4.BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n")

def txt_to_text(path):
    return path.read_text(encoding="utf-8", errors="replace")

def xlsx_to_text(path):
    openpyxl = ensure("openpyxl")
    wb = openpyxl.load_workbook(str(path), data_only=True)
    parts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f"-- Sheet: {sheet_name} --")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            line = " | ".join(cells).strip(" |")
            if line.replace("|", "").strip():
                parts.append(line)
    return "\n".join(parts)

def xls_to_text(path):
    xlrd = ensure("xlrd")
    wb   = xlrd.open_workbook(str(path))
    parts = []
    for sheet in wb.sheets():
        parts.append(f"-- Sheet: {sheet.name} --")
        for rx in range(sheet.nrows):
            cells = [str(sheet.cell_value(rx, cx)) for cx in range(sheet.ncols)]
            line  = " | ".join(cells).strip(" |")
            if line.replace("|", "").strip():
                parts.append(line)
    return "\n".join(parts)

def pptx_to_text(path):
    prs_mod = ensure("python-pptx", "pptx")
    prs     = prs_mod.Presentation(str(path))
    parts   = []
    for i, slide in enumerate(prs.slides, 1):
        slide_lines = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        slide_lines.append(t)
        if slide_lines:
            parts.append(f"[Slayt {i}]")
            parts.extend(slide_lines)
    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
#  Konfigurasyon
# ══════════════════════════════════════════════════════════════════════════════

CONVERTERS = {
    ".pdf":  pdf_to_text,
    ".docx": docx_to_text,
    ".doc":  docx_to_text,
    ".md":   md_to_text,
    ".html": html_to_text,
    ".htm":  html_to_text,
    ".txt":  txt_to_text,
    ".py":   txt_to_text,
    ".js":   txt_to_text,
    ".ts":   txt_to_text,
    ".json": txt_to_text,
    ".yaml": txt_to_text,
    ".yml":  txt_to_text,
    ".env":  txt_to_text,
    ".csv":  txt_to_text,
    ".xlsx": xlsx_to_text,
    ".xls":  xls_to_text,
    ".pptx": pptx_to_text,
    ".ppt":  pptx_to_text,
}

MAX_FILE_MB = 10  # 10MB: normal belgeler girer, dev kitap PDF'leri atlanir

SEPARATOR = "\n" + "=" * 72 + "\n"

SKIP_DIRS = {
    "__pycache__", ".git", ".svn", "node_modules",
    ".venv", "venv", "dist", "build",
    "whatsapp_session", "component_crx_cache", "extensions_crx_cache",
    "CacheStorage", "Service Worker",
}

# ── all1 icin gurultu filtreleri ──────────────────────────────────────────────

# Dosya adinda bu string varsa all1'den atla
NOISE_NAME_KEYWORDS = [
    "package_info", "entry_points", "top_level", "_dependencies",
    "license", "licence", "copyright", "_metadata", "metadata.json",
    "dependency_info", "dependency_details", "library_metadata",
    "requirements.txt.txt", "robots.txt.txt", "handshake_header",
    "pdist_", "cdist_", "pcg64", "mt19937", "philox", "sfc64",
    "arctan", "arccos", "arcsin", "arcsinh", "arccosh", "arctanh",
    "umath_validation", "cbrt_validation", "tanh-validation",
    "svmlight", "iris_flower", "linnerud", "winequalityred",
    "fr_fr_translation", "saved_resource",
    "capacitor.plugins", "index.txt",
    "cordova.js", "cordova_plugins",
]

# Yolda bu parcalar varsa all1'den atla
NOISE_PATH_KEYWORDS = [
    "\\License\\", "\\Licenses\\", "\\License_alt\\", "\\Licenses_alt\\",
    "/License/", "/Licenses/",
    "\\Copyright", "\\IP_Rights\\",
    "\\Testing\\", "\\Test_Data", "\\Test_Results", "\\Validation\\",
    "\\Random_Number", "\\Random_Test", "\\RandomizationTests",
    "\\Distance_Metric", "\\Distance_Measurement",
    "\\Iris_Data", "\\Machine_Learning_Datasets", "\\Polytope_Data",
    "\\whatsapp_session\\", "\\CacheStorage\\", "\\crx_cache\\",
    " - Kopya\\",           # kopyalanmis klasorler
    "- Kopya - Kopya\\",
    "\\ARAŞTIRMA PDF DOWNLOAD PUBMED VS - Kopya\\",
    "\\GEMİNİ ARAŞTIRMA RAPORLARI - Kopya\\",
    "\\KİTAPLAR AI - Kopya\\",
    "\\OSINT - Kopya\\",
    "\\transcript - Kopya\\",
    "\\gayrimenkulmuhendisi-main - Kopya\\",
    "\\Real-Estate-main - Kopya",
    "\\SPRINT 2 - Kopya",
    "\\Blog Oezelliği - Kopya\\",
    "\\PROMPTLAR - Kopya\\",
    "\\arayış botu - Kopya\\",
    "\\AutoReply AI - Kopya\\",
    "\\Yeni klasör - Kopya\\",
    "\\FINANCEIA\\Yeni klasör\\",    # FINANCEIA altındaki tekrarlar
    "\\NEXADIGITAL\\LLM MODELS\\",  # LLM MODELS zaten BIOTECHNOLOGY'de var
]

# all1'de en az bu kadar karakter olmali (geri kalan gürültü vs kucuk dosyalar)
MIN_CHARS = 150


# ══════════════════════════════════════════════════════════════════════════════
#  Filtre
# ══════════════════════════════════════════════════════════════════════════════

def is_noise(fp: Path, root: Path):
    """(True, neden) ya da (False, '') dondurur."""
    name_lower = fp.name.lower()

    if fp.name.startswith("~$"):
        return True, "Word temp (~$)"

    for kw in NOISE_NAME_KEYWORDS:
        if kw.lower() in name_lower:
            return True, f"gurultu isim: {kw}"

    try:
        rel = str(fp.relative_to(root))
    except ValueError:
        rel = str(fp)

    for kw in NOISE_PATH_KEYWORDS:
        if kw.lower() in rel.lower():
            return True, f"gurultu yol: {kw.strip(chr(92) + '/')}"

    return False, ""


# ══════════════════════════════════════════════════════════════════════════════
#  Toplama
# ══════════════════════════════════════════════════════════════════════════════

def collect_files(root: Path, out_all: Path, out_all1: Path):
    all_files  = []
    all1_files = []
    skipped    = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for fname in filenames:
            fp  = Path(dirpath) / fname
            ext = fp.suffix.lower()

            if ext not in CONVERTERS:
                continue
            if fp.resolve() in (out_all.resolve(), out_all1.resolve()):
                continue

            try:
                size = fp.stat().st_size
            except OSError:
                continue

            if size > MAX_FILE_MB * 1024 * 1024:
                print(f"  [ATLA-BOYUT >50MB] {fp.name}")
                continue

            all_files.append(fp)

            noise, reason = is_noise(fp, root)
            if noise:
                skipped += 1
            else:
                all1_files.append(fp)

    return sorted(all_files), sorted(all1_files), skipped


# ══════════════════════════════════════════════════════════════════════════════
#  Isleme
# ══════════════════════════════════════════════════════════════════════════════

def process_files(files: list, root: Path, output_file: Path, label: str, min_chars=0):
    sections = []
    basarili = hatali = bos = atlanan = 0

    print(f"\n{'─'*65}")
    print(f"  {label}")
    print(f"  {len(files)} dosya → {output_file}")
    print(f"{'─'*65}")

    for fp in files:
        ext     = fp.suffix.lower()
        convert = CONVERTERS[ext]
        try:
            rel = fp.relative_to(root)
        except ValueError:
            rel = fp

        tag = f"[{ext.upper()[1:]:5s}] {str(rel)[-60:]}"
        print(f"  {tag:<65}", end="", flush=True)

        try:
            text  = convert(fp)
            clean = text.strip()

            if not clean:
                print("⚠  bos")
                bos += 1
                continue

            if min_chars and len(clean) < min_chars:
                print(f"⊘  kucuk ({len(clean)} kr)")
                atlanan += 1
                continue

            header = (
                f"{'=' * 72}\n"
                f"DOSYA : {rel}\n"
                f"TUR   : {ext.upper()[1:]}\n"
                f"{'=' * 72}"
            )
            sections.append(f"{header}\n\n{clean}")
            print(f"OK ({len(clean):,} kr)")
            basarili += 1

        except Exception as exc:
            print(f"HATA: {exc}")
            hatali += 1

    meta = (
        f"{'=' * 72}\n"
        f"NEXA TOPLA — {label}\n"
        f"Kok      : {root}\n"
        f"Tarih    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Basarili : {basarili} | Hatali: {hatali} | Bos: {bos} | Kucuk: {atlanan}\n"
        f"{'=' * 72}\n"
    )
    combined = meta + SEPARATOR.join(sections)
    output_file.write_text(combined, encoding="utf-8")

    mb = len(combined) / 1024 / 1024
    print(f"\n  Sonuc: {basarili} ok  {hatali} hata  {bos} bos  {atlanan} kucuk")
    print(f"  Cikti: {output_file}  ({mb:.1f} MB)")


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Nexa Topla — Cift Versiyon")
    parser.add_argument("folder", nargs="?", default=None,
                        help="Taranacak kok klasor")
    parser.add_argument("--no-code", action="store_true",
                        help=".py .js .ts .json .yaml dosyalarini atla")
    parser.add_argument("--only-all", action="store_true",
                        help="Sadece all.txt uret")
    parser.add_argument("--only-all1", action="store_true",
                        help="Sadece all1.txt uret")
    args = parser.parse_args()

    root = Path(args.folder).resolve() if args.folder else Path(__file__).resolve().parent

    if not root.is_dir():
        print(f"[HATA] '{root}' klasor degil.")
        sys.exit(1)

    if args.no_code:
        for ext in [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env"]:
            CONVERTERS.pop(ext, None)

    out_all  = root / "all.txt"
    out_all1 = root / "all1.txt"

    print(f"\n{'='*65}")
    print(f"  NEXA TOPLA — Cift Versiyon")
    print(f"  Kok : {root}")
    print(f"{'='*65}")
    print(f"\n[TARAMA] Dosyalar taranıyor...")

    all_files, all1_files, skipped = collect_files(root, out_all, out_all1)

    print(f"\n  all.txt  icin : {len(all_files)} dosya")
    print(f"  all1.txt icin : {len(all1_files)} dosya  ({skipped} gurultu atlandı)")

    if not all_files:
        print("[BILGI] Hic dosya bulunamadi.")
        sys.exit(0)

    # Once all1 (hizli, temiz) sonra all (tam arsiv)
    if not args.only_all:
        process_files(all1_files, root, out_all1,
                      "all1.txt - FILTRELENMIS (gurultu + kopyalar atlanir)",
                      min_chars=MIN_CHARS)

    if not args.only_all1:
        process_files(all_files, root, out_all,
                      "all.txt - TAM ARSIV (hicbir sey atlanmaz)")

    print(f"\n{'='*65}")
    print(f"  TAMAMLANDI")
    if not args.only_all1:
        print(f"  all.txt  -> {out_all}")
    if not args.only_all:
        print(f"  all1.txt -> {out_all1}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()