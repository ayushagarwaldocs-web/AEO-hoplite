"""Build the arXiv and journal submission packages from paper/ (run after paper/make_numbers.py).

    python3 submission/build_submission.py

Writes, next to this script:
  arxiv/                          the LaTeX source exactly as uploaded (main.tex and its inputs, figures,
                                  references.bib and the generated main.bbl, which arXiv needs)
  arxiv-source.zip                the same files, zipped for upload
  arxiv-metadata.txt              title, author, plain-text abstract, comments, categories, licence
  journal/manuscript.pdf          journal version: Elsevier-style declarations before the references
  journal/manuscript-anonymized.pdf  the same without the author block, for double-anonymized review
  journal/title-page.pdf          title, author, affiliation and contact details
  journal/source.zip              LaTeX source of the journal version
Every package is compiled from a clean copy with tectonic before it is written, and the arXiv folder is scanned
for anything that looks like an API key.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent / "paper"
TITLE = "The Discoverability Gap: Access Barriers and Content Effects in Answer Engine Optimization"
AUTHOR, AFFIL, EMAIL = "Ayush Agarwal", "Independent researcher", "ayushag1002@gmail.com"
REPO_URL = "https://github.com/ayushagarwaldocs-web/AEO-hoplite"
LIGATURES = {"\ufb01": "fi", "\ufb00": "ff", "\ufb03": "ffi", "\ufb02": "fl", "\ufb04": "ffl", "\u2019": "'",
             "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u2212": "-"}


def sources() -> tuple[list[str], list[str]]:
    """The .tex files main.tex pulls in (recursively) and the figures they include."""
    seen, todo, figs = [], ["main.tex"], []
    while todo:
        f = todo.pop(0)
        if f in seen:
            continue
        seen.append(f)
        text = (PAPER / f).read_text()
        for m in re.findall(r"\\input\{([^}]+)\}", text):
            name = m if m.endswith(".tex") else m + ".tex"
            if (PAPER / name).exists():
                todo.append(name)
        figs += re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", text)
    return seen, sorted(set(figs))


def stage(dest: Path, tex: list[str], figs: list[str]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for f in tex + figs + ["references.bib"]:
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PAPER / f, dest / f)


def compile_pdf(folder: Path, keep_bbl: bool = False) -> Path:
    cmd = ["tectonic", "-X", "compile"] + (["--keep-intermediates"] if keep_bbl else []) + ["main.tex"]
    r = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"compile failed in {folder}:\n{r.stderr[-2000:]}")
    if "undefined" in (r.stderr + r.stdout).lower():
        print(f"warning: undefined references reported in {folder.name}")
    return folder / "main.pdf"


def pdf_text(pdf: Path) -> list[str]:
    from pypdf import PdfReader
    return [p.extract_text() for p in PdfReader(str(pdf)).pages]


def plain(text: str) -> str:
    for a, b in LIGATURES.items():
        text = text.replace(a, b)
    return " ".join(text.replace("-\n", "").split())


def journal_main(text: str, anonymized: bool) -> str:
    """Elsevier-style end matter: separate declaration sections immediately before the references."""
    start, end = text.index("\\paragraph{Ethics.}"), text.index("\\bibliographystyle")
    old = text[start:end]
    para = lambda name: re.search(r"\\paragraph\{" + re.escape(name) + r"\}(.*?)(?=\\paragraph\{|\Z)", old, re.S).group(1).strip()  # noqa: E731
    new = (
        "\\section*{Ethics}\n" + para("Ethics.") + "\n\n"
        "\\section*{Data availability}\n" + para("Data and code.") + "\n\n"
        "\\section*{Funding}\nThis research did not receive any specific grant from funding agencies in the public, "
        "commercial, or not-for-profit sectors. The author paid for model access, in part with the free credits that "
        "Amazon Web Services and Microsoft Azure give new accounts; Gemini ran on Google's free API tier.\n\n"
        "\\section*{Declaration of generative AI and AI-assisted technologies in the manuscript preparation process}\n"
        "During the preparation of this work the author used Claude (Anthropic) in order to write and debug the "
        "measurement and analysis software, run and analyse the experiments, and draft and revise the manuscript. "
        "After using this tool, the author reviewed and edited the content as needed and takes full responsibility "
        "for the content of the publication.\n\n")
    text = text[:start] + new + text[end:]
    if anonymized:
        text = re.sub(r"\\author\{.*?\}\n\\date", r"\\author{Anonymous author}\n\\date", text, count=1, flags=re.S)
        text = text.replace("\\url{" + REPO_URL + "}", "[repository link withheld for anonymized review]")
        assert AUTHOR not in text and EMAIL not in text and "ayushagarwal" not in text.lower()
    return text


def zip_folder(folder: Path, out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(folder))


def main() -> int:
    tex, figs = sources()
    n_fig = sum((PAPER / f).read_text().count("\\begin{figure") for f in tex)
    n_tab = sum((PAPER / f).read_text().count("\\begin{table") for f in tex)

    # arXiv: the paper as it stands, with \pdfoutput=1 and the .bbl that arXiv needs.
    arxiv = HERE / "arxiv"
    shutil.rmtree(arxiv, ignore_errors=True)
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp) / "build"
        stage(build, tex, figs)
        m = build / "main.tex"
        if "\\pdfoutput=1" not in m.read_text()[:200]:  # arXiv looks for it in the first lines; XeTeX skips it
            m.write_text("\\ifdefined\\XeTeXversion\\else\\pdfoutput=1\\fi\n" + m.read_text())
        compile_pdf(build, keep_bbl=True)
        stage(arxiv, tex, figs)
        shutil.copy(m, arxiv / "main.tex")
        shutil.copy(build / "main.bbl", arxiv / "main.bbl")
    with tempfile.TemporaryDirectory() as tmp:  # compile the upload from a clean copy
        check = Path(tmp) / "arxiv"
        shutil.copytree(arxiv, check)
        pages = pdf_text(compile_pdf(check))
        shutil.copy(check / "main.pdf", HERE / "arxiv-preview.pdf")
    key_like = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|api[-_]?key\s*[=:]\s*\S{12,})", re.I)
    leaks = [str(f.relative_to(arxiv)) for f in arxiv.rglob("*") if f.is_file() and f.suffix in (".tex", ".bib", ".bbl")
             and key_like.search(f.read_text(errors="ignore"))]
    if leaks:
        sys.exit(f"possible secret in {leaks}; not packaging")
    zip_folder(arxiv, HERE / "arxiv-source.zip")

    first = pages[0]
    abstract = plain(first[first.index("Abstract") + len("Abstract"):first.index("1 Introduction")])
    assert len(abstract) <= 1920, f"abstract too long for arXiv ({len(abstract)} characters)"
    (HERE / "arxiv-metadata.txt").write_text(
        f"Title:\n{TITLE}\n\nAuthors:\n{AUTHOR}\n\nAbstract ({len(abstract)} characters; arXiv allows 1,920):\n{abstract}\n\n"
        f"Comments:\n{len(pages)} pages, {n_fig} figures, {n_tab} tables. Code, benchmark and data: {REPO_URL}\n\n"
        "Primary category:\ncs.IR (Information Retrieval)\n\nCross-lists:\ncs.CL (Computation and Language)\n"
        "cs.CY (Computers and Society)\n\nLicence:\nCC BY 4.0 (allows the journal submission; Elsevier lets authors "
        "post preprints under any licence)\n\nACM class (optional):\nH.3.3; I.2.7\n")

    # Journal: Elsevier-style declarations; one version with the author block, one without.
    jdir = HERE / "journal"
    jdir.mkdir(exist_ok=True)
    for anonymized, name in ((False, "manuscript.pdf"), (True, "manuscript-anonymized.pdf")):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp) / "journal"
            stage(build, tex, figs)
            m = build / "main.tex"
            m.write_text(journal_main(m.read_text(), anonymized))
            pdf = compile_pdf(build)
            text = " ".join(pdf_text(pdf))
            if anonymized:
                assert AUTHOR not in text and EMAIL not in text and "ayushagarwal" not in text.lower(), \
                    "author details left in the anonymized manuscript"
            shutil.copy(pdf, jdir / name)
            if not anonymized:
                for f in build.glob("*.pdf"):
                    if f.name == "main.pdf":
                        f.unlink()
                zip_folder(build, jdir / "source.zip")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "main.tex").write_text(
            "\\documentclass[11pt]{article}\n\\usepackage[margin=1in]{geometry}\n\\usepackage[T1]{fontenc}\n"
            "\\usepackage{lmodern}\n\\pagestyle{empty}\n\\begin{document}\n\\section*{Title page}\n"
            f"\\textbf{{Title:}} {TITLE}\\\\[1em]\n"
            f"\\textbf{{Author:}} {AUTHOR}\\\\\n\\textbf{{Affiliation:}} {AFFIL} (no institutional affiliation)\\\\\n"
            f"\\textbf{{Corresponding author:}} {AUTHOR}, \\texttt{{{EMAIL}}}\\\\[1em]\n"
            "\\textbf{Funding:} This research did not receive any specific grant from funding agencies in the public, "
            "commercial, or not-for-profit sectors.\n\\end{document}\n")
        compile_pdf(t)
        shutil.copy(t / "main.pdf", jdir / "title-page.pdf")
    print(f"arXiv: {len(pages)} pages, {n_fig} figures, {n_tab} tables; abstract {len(abstract)} characters")
    print("written:", ", ".join(sorted(str(p.relative_to(HERE)) for p in HERE.rglob("*") if p.is_file()
                                       and not p.name.startswith(".") and "arxiv/" not in str(p.relative_to(HERE)))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
