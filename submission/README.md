# Submission packages

Rebuild everything after any change to the paper (it recompiles each package from a clean copy):

```bash
python3 submission/build_submission.py
```

## Where to submit

1. **arXiv preprint first.** Primary category `cs.IR`, cross-list `cs.CL` and `cs.CY`, licence CC BY 4.0. This
   timestamps the work; Elsevier and ACM both allow preprints of submitted papers.
2. **Journal: Information Processing & Management (Elsevier).** Covers information retrieval, information access
   and the evaluation of LLM-based systems, and publishes long empirical papers. Publishing on the subscription
   route is free, so there is no fee unless you choose open access. Elsevier blocked automated reading of the
   journal's author guide, so check the length limit, review type and file rules in Editorial Manager before
   uploading.
3. **If rejected:** ACM Transactions on the Web (best topical fit, but ACM journals are open access with a fee
   since 2026; as an unaffiliated author you would have to ask ACM for a waiver), then JASIST (Wiley) or Internet
   Research (Emerald).

## Files

| File | Use |
|---|---|
| `arxiv-source.zip` | Upload to arXiv as the source (LaTeX, figures, `main.bbl`) |
| `arxiv-metadata.txt` | Title, author, abstract (1,511 of 1,920 characters), comments, categories |
| `arxiv-preview.pdf` | What the upload should look like; compare with arXiv's own preview |
| `endorsement-request.txt` | Email template for one arXiv endorser |
| `journal/manuscript.pdf` | Journal version with your name and Elsevier-style declarations before the references |
| `journal/manuscript-anonymized.pdf` | The same without your name, if the journal uses double-anonymized review |
| `journal/title-page.pdf` | Title, author and contact details, uploaded separately with the anonymized version |
| `journal/highlights.txt` | Five highlights, each at most 85 characters |
| `journal/keywords.txt` | Seven keywords |
| `journal/cover-letter.txt` | Cover letter (fill in the arXiv number; confirm the competing-interest line) |
| `journal/declarations.txt` | Competing interests, funding, CRediT roles, data availability, AI declaration |
| `journal/source.zip` | LaTeX source of the journal version, if the editor asks for it |

## Steps

1. Create an ORCID iD (free, orcid.org); journals ask for it.
2. Make the repository public (for example on GitHub, archived on Zenodo for a DOI) and put its link in
   `arxiv-metadata.txt` (Comments) and `journal/declarations.txt` (Data availability). Check first that `.env`
   and `RESOURCES.local.md` are not included; both are in `.gitignore`.
3. arXiv: create an account, start a submission in `cs.IR`, and arXiv will email you an endorsement code. Since
   21 January 2026 an institutional email no longer gives automatic endorsement, so ask one eligible author
   (`endorsement-request.txt`). Then upload `arxiv-source.zip`, copy the metadata, and compare arXiv's preview with
   `arxiv-preview.pdf` before you confirm.
4. Journal: in Elsevier's Editorial Manager for Information Processing & Management, upload the manuscript (the
   anonymized one plus the title page if the form asks for anonymized files), the highlights and the cover letter,
   enter the keywords, and complete the declarations. Confirm the competing-interest statement is true for you.
5. Keep the AI declaration accurate. Elsevier's policy accepts AI-assisted code and analysis when declared, but
   expects the author's own intellectual contribution; be ready to describe yours (the questions, the choices of
   models, budget and design, and your review of the results) if the editor asks.
