#!/usr/bin/env python3
"""Generate editable and print-ready Matchmind front/back flyers."""

from __future__ import annotations

import argparse
import html
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "marketing" / "pub-flyers"
QR_HELPER_PATH = ROOT / "scripts" / "pub_flyer_qr.swift"
DEFAULT_OUTPUT_DIR = TEMPLATE_DIR / "generated"
DEFAULT_DESTINATION_URL = "https://trymatchmind.com/"
MM_TO_POINTS = 72 / 25.4
PRINT_WIDTH_MM = 154
PRINT_HEIGHT_MM = 216
PREVIEW_DPI = 180

COPY = {
    "en": {
        "front_title": "Before you bet, ask Matchmind.",
        "kicker": "WORLD CUP 2026 · AI BETTING COACH",
        "front_headline": ["BEFORE", "YOU BET,"],
        "front_accent": "ASK AI.",
        "front_accent_size": "20",
        "front_body": ["One scan. One straight answer.", "Is the bet smart, emotional, or overpriced?"],
        "front_cta": "ASK THE AI FREE",
        "front_cta_size": "5.4",
        "free_line": "3 FREE COACH CHATS A DAY",
        "scan_line": "SCAN BEFORE YOU STAKE",
        "scan_subline": ["Odds · data · market signals", "A direct verdict before you stake"],
        "back_kicker": "THE SECOND OPINION YOUR BET NEEDS",
        "back_headline": ["YOUR INSTINCT", "HAS BLIND SPOTS."],
        "back_headline_2_size": "13.2",
        "back_intro": ["Matchmind reads the ticket, checks the market,", "and tells you what the hype is hiding."],
        "question": "Argentina to win the World Cup at 7.50. Good value or trap?",
        "verdict": "I like the idea. I don't love the odds.",
        "answer": ["The price already carries a lot of optimism.", "Wait for a better number or keep the stake small."],
        "confidence": "CONFIDENCE 7/10",
        "proof_kicker": "WHAT THE AI CHECKS IN SECONDS",
        "proofs": [
            ("01", "THE ODDS", "What probability is the bookmaker really pricing?"),
            ("02", "THE DATA", "What does the World Cup context actually support?"),
            ("03", "THE MARKET", "Where do crowd signals and prices disagree?"),
        ],
        "back_cta": "TRY THE AI COACH FREE",
        "footer": "Analysis only. No guarantees. Matchmind never places bets. 18+.",
    },
    "es": {
        "front_title": "Antes de apostar, pregunta a Matchmind.",
        "kicker": "MUNDIAL 2026 · COACH IA PARA APUESTAS",
        "front_headline": ["ANTES DE", "APOSTAR,"],
        "front_accent": "PREGUNTA A LA IA.",
        "front_accent_size": "12.7",
        "front_body": ["Un escaneo. Una respuesta directa.", "¿La apuesta tiene sentido o te puede la emoción?"],
        "front_cta": "PREGUNTA A LA IA GRATIS",
        "front_cta_size": "4.25",
        "free_line": "3 CHATS GRATIS AL DÍA",
        "scan_line": "ESCANEA ANTES DE APOSTAR",
        "scan_subline": ["Cuotas · datos · señales de mercado", "Un veredicto directo antes de apostar"],
        "back_kicker": "LA SEGUNDA OPINIÓN QUE TU APUESTA NECESITA",
        "back_headline": ["TU INSTINTO", "TIENE PUNTOS CIEGOS."],
        "back_headline_2_size": "10.6",
        "back_intro": ["Matchmind lee tu jugada, comprueba el mercado", "y te dice lo que el hype no te está contando."],
        "question": "Argentina gana el Mundial a cuota 7.50. ¿Valor o trampa?",
        "verdict": "Me gusta la idea. No me convence la cuota.",
        "answer": ["El precio ya descuenta demasiado optimismo.", "Espera una cuota mejor o apuesta muy poco."],
        "confidence": "CONFIANZA 7/10",
        "proof_kicker": "LO QUE LA IA COMPRUEBA EN SEGUNDOS",
        "proofs": [
            ("01", "LA CUOTA", "¿Qué probabilidad está poniendo realmente la casa?"),
            ("02", "LOS DATOS", "¿Qué respalda de verdad el contexto del Mundial?"),
            ("03", "EL MERCADO", "¿Dónde discrepan las señales y los precios?"),
        ],
        "back_cta": "PRUEBA EL COACH IA GRATIS",
        "footer": "Solo análisis. Sin garantías. Matchmind nunca coloca apuestas. +18.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination-url", default=DEFAULT_DESTINATION_URL, help="QR destination. Defaults to the Matchmind site.")
    parser.add_argument("--language", choices=("en", "es", "both"), default="both")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def validate_destination_url(destination_url: str) -> None:
    parsed = urlparse(destination_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Destination URL must be an absolute https:// URL.")
    if parsed.query or parsed.fragment:
        raise ValueError("Destination URL must not contain query parameters or fragments.")


def compile_qr_helper(temp_dir: Path) -> Path:
    binary_path = temp_dir / "pub_flyer_qr"
    environment = os.environ.copy()
    environment["CLANG_MODULE_CACHE_PATH"] = str(temp_dir / "clang-module-cache")
    environment["SWIFT_MODULECACHE_PATH"] = str(temp_dir / "swift-module-cache")
    subprocess.run(["/usr/bin/swiftc", str(QR_HELPER_PATH), "-o", str(binary_path)], check=True, env=environment)
    return binary_path


def run_qr_helper(binary_path: Path, *arguments: str) -> str:
    result = subprocess.run([str(binary_path), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "QR helper failed without an error message.")
    return result.stdout.strip()


def read_qr_matrix(qr_png: Path) -> list[list[bool]]:
    image = Image.open(qr_png).convert("L")
    width, height = image.size
    scale = 12
    if width != height or width % scale:
        raise ValueError("Unexpected QR raster dimensions.")
    pixels = image.load()
    modules = width // scale
    return [[pixels[x * scale + scale // 2, y * scale + scale // 2] < 128 for x in range(modules)] for y in range(modules)]


def qr_svg_rects(matrix: list[list[bool]]) -> str:
    quiet_zone = 4
    module_size = 48 / (len(matrix) + quiet_zone * 2)
    return "\n        ".join(
        f'<rect x="{(x + quiet_zone) * module_size:.4f}" y="{(y + quiet_zone) * module_size:.4f}" '
        f'width="{module_size:.4f}" height="{module_size:.4f}" fill="#04101D"/>'
        for y, row in enumerate(matrix)
        for x, is_dark in enumerate(row)
        if is_dark
    )


def render_template(template_name: str, language: str, destination_url: str, qr_modules: str) -> str:
    copy = COPY[language]
    replacements = {
        "LANGUAGE": language,
        "URL": destination_url,
        "FALLBACK_URL": destination_url.removeprefix("https://").rstrip("/"),
        "QR_MODULES": qr_modules,
        **{key.upper(): value for key, value in copy.items() if isinstance(value, str)},
        "FRONT_HEADLINE_1": copy["front_headline"][0],
        "FRONT_HEADLINE_2": copy["front_headline"][1],
        "FRONT_BODY_1": copy["front_body"][0],
        "FRONT_BODY_2": copy["front_body"][1],
        "SCAN_SUBLINE_1": copy["scan_subline"][0],
        "SCAN_SUBLINE_2": copy["scan_subline"][1],
        "BACK_HEADLINE_1": copy["back_headline"][0],
        "BACK_HEADLINE_2": copy["back_headline"][1],
        "BACK_INTRO_1": copy["back_intro"][0],
        "BACK_INTRO_2": copy["back_intro"][1],
        "ANSWER_1": copy["answer"][0],
        "ANSWER_2": copy["answer"][1],
    }
    for index, (number, title, body) in enumerate(copy["proofs"], start=1):
        replacements[f"PROOF_{index}_NUMBER"] = number
        replacements[f"PROOF_{index}_TITLE"] = title
        replacements[f"PROOF_{index}_BODY"] = body
    template = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        template = template.replace(f"{{{{{placeholder}}}}}", value if placeholder == "QR_MODULES" else html.escape(value))
    return template


def write_side(svg: str, svg_path: Path, png_path: Path) -> bytes:
    svg_path.write_text(svg, encoding="utf-8")
    svg_document = fitz.open(stream=svg.encode("utf-8"), filetype="svg")
    pdf_bytes = svg_document.convert_to_pdf()
    pdf_document = fitz.open("pdf", pdf_bytes)
    pdf_document[0].get_pixmap(dpi=PREVIEW_DPI, alpha=False).save(png_path)
    pdf_document.close()
    svg_document.close()
    return pdf_bytes


def write_print_pdf(front_pdf: bytes, back_pdf: bytes, pdf_path: Path) -> None:
    output = fitz.open()
    for source_pdf in (front_pdf, back_pdf):
        source = fitz.open("pdf", source_pdf)
        output.insert_pdf(source)
        source.close()
    output.set_metadata(
        {
            "title": "Matchmind A5 front/back flyer",
            "subject": "Two-sided A5 portrait flyer with 3 mm bleed and 148 x 210 mm trim size",
            "creator": "scripts/generate_pub_flyer.py",
        }
    )
    output.save(pdf_path)
    output.close()


def verify_pdf(pdf_path: Path) -> None:
    document = fitz.open(pdf_path)
    if document.page_count != 2:
        raise ValueError(f"Unexpected PDF page count: {document.page_count}.")
    expected_width = PRINT_WIDTH_MM * MM_TO_POINTS
    expected_height = PRINT_HEIGHT_MM * MM_TO_POINTS
    for page in document:
        if abs(page.rect.width - expected_width) > 0.1 or abs(page.rect.height - expected_height) > 0.1:
            raise ValueError(f"Unexpected PDF size: {page.rect.width:.2f} x {page.rect.height:.2f} pt.")
    document.close()


def generate(args: argparse.Namespace) -> None:
    destination_url = args.destination_url.strip()
    validate_destination_url(destination_url)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    languages = ("en", "es") if args.language == "both" else (args.language,)

    with tempfile.TemporaryDirectory(prefix="matchmind-flyer-") as temp_dir:
        temp_path = Path(temp_dir)
        qr_helper = compile_qr_helper(temp_path)
        qr_png = temp_path / "qr.png"
        run_qr_helper(qr_helper, "encode", destination_url, str(qr_png))
        decoded_url = run_qr_helper(qr_helper, "decode", str(qr_png))
        if decoded_url != destination_url:
            raise ValueError(f"QR verification failed: decoded {decoded_url!r}.")
        qr_modules = qr_svg_rects(read_qr_matrix(qr_png))

        for language in languages:
            front_svg = render_template("template-a5-front.svg", language, destination_url, qr_modules)
            back_svg = render_template("template-a5-back.svg", language, destination_url, qr_modules)
            front_svg_path = output_dir / f"matchmind-{language}-a5-front.svg"
            back_svg_path = output_dir / f"matchmind-{language}-a5-back.svg"
            front_png_path = output_dir / f"matchmind-{language}-a5-front-preview.png"
            back_png_path = output_dir / f"matchmind-{language}-a5-back-preview.png"
            print_pdf_path = output_dir / f"matchmind-{language}-a5-front-back-print.pdf"
            front_pdf = write_side(front_svg, front_svg_path, front_png_path)
            back_pdf = write_side(back_svg, back_svg_path, back_png_path)
            write_print_pdf(front_pdf, back_pdf, print_pdf_path)
            verify_pdf(print_pdf_path)
            for preview_path in (front_png_path, back_png_path):
                preview_url = run_qr_helper(qr_helper, "decode", str(preview_path))
                if preview_url != destination_url:
                    raise ValueError(f"Rendered preview QR verification failed: decoded {preview_url!r}.")
            for path in (front_svg_path, back_svg_path, print_pdf_path, front_png_path, back_png_path):
                print(f"created: {path.relative_to(ROOT)}")

    print(f"verified source and rendered QR decode: {decoded_url}")
    print("verified print PDF: 2 pages, 154 x 216 mm each (A5 trim plus 3 mm bleed)")


if __name__ == "__main__":
    generate(parse_args())
