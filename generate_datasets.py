import os
import re
import json
import glob
from typing import List, Dict, Any, Optional

try:
    from pylatexenc.latexwalker import LatexWalker  # type: ignore
except Exception:
    LatexWalker = None  # Fallback: we'll strip LaTeX with regex if missing

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None  # Allow running LaTeX-only generation

try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception:
    PdfReader = None  # If both fitz and PyPDF2 are missing, PDFs will be skipped

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def latex_to_text(latex: str) -> str:
    if LatexWalker is None:
        # Basic fallback: remove common LaTeX commands and braces
        text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", latex)
        text = re.sub(r"\{[^}]*\}", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    walker = LatexWalker(latex)
    nodelist, _, _ = walker.get_latex_nodes(pos=0)
    extracted: List[str] = []
    for node in nodelist:
        if hasattr(node, "nodelist") and getattr(node, "nodelist") is not None:  # type: ignore[attr-defined]
            for subnode in node.nodelist:  # type: ignore[attr-defined]
                try:
                    extracted.append(subnode.latex_verbatim())
                except Exception:
                    pass
        else:
            try:
                extracted.append(node.latex_verbatim())
            except Exception:
                pass
    return "".join(extracted)


def text_formatter(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def parse_exercises(text: str) -> List[Dict[str, Any]]:
    # Match like: 1.1A Question text a) opt; b) opt; ... up to f)
    exercise_pattern = re.compile(
        r"(?P<code>\d+\.\d+[A-Z]?)\s*(?P<question>.+?)(?P<choices>(?:\s*[a-f]\)\s*.*?){2,})\s*(?=\d+\.\d+[A-Z]?|$)",
        re.DOTALL,
    )
    option_pattern = re.compile(r"([a-f])\)\s*(.*?)(?=\s*[a-f]\)|$)", re.DOTALL)

    exercises: List[Dict[str, Any]] = []
    seq_index = 0
    for match in exercise_pattern.finditer(text):
        seq_index += 1
        code = match.group("code").strip()
        question = match.group("question").strip()
        choices_blob = match.group("choices") or ""
        options: List[Dict[str, str]] = []
        for om in option_pattern.finditer(choices_blob):
            label = om.group(1).strip()
            opt_text = text_formatter(om.group(2))
            options.append({"label": label, "text": opt_text})

        exercises.append({
            "index": seq_index,
            "code": code,
            "question": text_formatter(question),
            "options": options,
        })

    return exercises


def parse_answers(text: str) -> Dict[int, str]:
    # Pattern like: 1 d) 2 e) 3 d) ... possibly across lines
    pattern = re.compile(r"(?<!\d)(\d+)\s*([a-f])\)")
    m: Dict[int, str] = {}
    for q, ans in pattern.findall(text):
        try:
            m[int(q)] = ans
        except Exception:
            continue
    return m


def parse_explanations(text: str) -> Dict[int, str]:
    # Numbers followed by explanation text until next number or end
    pattern = re.compile(r"(?P<q>\d+)\s*(?P<exp>(?:.|\n)*?)(?=\n\s*\d+\s|$)", re.DOTALL)
    m: Dict[int, str] = {}
    for mm in pattern.finditer(text):
        q = mm.group("q")
        exp = text_formatter(mm.group("exp"))
        try:
            m[int(q)] = exp
        except Exception:
            continue
    return m


def read_file(path: str, encoding: str = "utf-8") -> str:
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        return f.read()


def write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def extract_latex_file(latex_path: str) -> Dict[str, Any]:
    latex_raw = read_file(latex_path)
    text = text_formatter(latex_to_text(latex_raw))
    return {"file": os.path.basename(latex_path), "text": text}


def generate_latex_jsons(latex_dir: str, out_dir: str) -> None:
    ensure_dir(out_dir)

    # Collect companion files if present to enrich exercises
    rasp_path = os.path.join(latex_dir, "Raspunsuri.tex")
    expl_path = os.path.join(latex_dir, "Explicatii.tex")
    answers_map: Dict[int, str] = {}
    explanations_map: Dict[int, str] = {}

    if os.path.exists(rasp_path):
        rasp_text = text_formatter(latex_to_text(read_file(rasp_path)))
        answers_map = parse_answers(rasp_text)
        write_json(os.path.join(out_dir, "Raspunsuri.json"), [
            {"index": k, "answer": v} for k, v in sorted(answers_map.items())
        ])

    if os.path.exists(expl_path):
        expl_text = text_formatter(latex_to_text(read_file(expl_path)))
        explanations_map = parse_explanations(expl_text)
        write_json(os.path.join(out_dir, "Explicatii.json"), [
            {"index": k, "explanation": v} for k, v in sorted(explanations_map.items())
        ])

    for path in sorted(glob.glob(os.path.join(latex_dir, "*.tex"))):
        base = os.path.basename(path)

        try:
            raw = read_file(path)
            text = text_formatter(latex_to_text(raw))
        except Exception:
            # Fallback to raw read
            text = text_formatter(read_file(path))

        # Skip companion sources we already exported to structured JSON
        if base.lower() in {"raspunsuri.tex", "explicatii.tex"}:
            continue

        # If this looks like the exercises compendium, parse it richly
        if re.search(r"exerciti[iy]|Exercitii|Exerciții", base, re.IGNORECASE):
            items = parse_exercises(text)
            # Merge answers and explanations by sequential index
            for item in items:
                idx = int(item.get("index", 0))
                if idx in answers_map:
                    item["answer"] = answers_map[idx]
                if idx in explanations_map:
                    item["explanation"] = explanations_map[idx]

            write_json(os.path.join(out_dir, f"{os.path.splitext(base)[0]}.json"), items)
        else:
            # Generic LaTeX: still emit plain text JSON to satisfy per-file output
            write_json(os.path.join(out_dir, f"{os.path.splitext(base)[0]}.json"), {
                "file": base,
                "text": text,
            })


def _extract_pdf_with_fitz(pdf_path: str) -> Optional[List[Dict[str, Any]]]:
    if fitz is None:
        return None
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None

    pages: List[Dict[str, Any]] = []
    for page_number, page in enumerate(doc):
        try:
            text = page.get_text()
        except Exception:
            text = ""
        text = text_formatter(text)
        pages.append({
            "page_number": page_number,
            "page_char_count": len(text),
            "page_word_count": len(text.split()),
            "text": text,
        })
    return pages


def _extract_pdf_with_pypdf2(pdf_path: str) -> Optional[List[Dict[str, Any]]]:
    if PdfReader is None:
        return None
    try:
        reader = PdfReader(pdf_path)
    except Exception:
        return None
    pages: List[Dict[str, Any]] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text_formatter(text)
        pages.append({
            "page_number": i,
            "page_char_count": len(text),
            "page_word_count": len(text.split()),
            "text": text,
        })
    return pages


def generate_pdf_jsons(pdf_root: str, out_dir: str) -> None:
    ensure_dir(out_dir)
    pdf_paths = glob.glob(os.path.join(pdf_root, "**", "*.pdf"), recursive=True)
    for pdf_path in sorted(pdf_paths):
        pages: Optional[List[Dict[str, Any]]] = None
        # Try PyMuPDF first for better layout
        pages = _extract_pdf_with_fitz(pdf_path)
        # Fallback to PyPDF2
        if pages is None or len(pages) == 0:
            pages = _extract_pdf_with_pypdf2(pdf_path)
        if pages is None:
            # Could not extract this PDF; skip
            continue

        out_name = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
        write_json(os.path.join(out_dir, out_name), pages)


def main() -> None:
    latex_dir = os.path.join("latex_docs")
    pdf_dir = os.path.join("pdfs")

    out_latex = os.path.join("json_out", "latex")
    out_pdf = os.path.join("json_out", "pdf")

    generate_latex_jsons(latex_dir, out_latex)
    generate_pdf_jsons(pdf_dir, out_pdf)


if __name__ == "__main__":
    main()


