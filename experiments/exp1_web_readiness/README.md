# Experiment 1: how ready are organisational websites for AI answer engines?

A measurement of 569 prominent organisational websites across 22 sectors (`domains.csv`),
collected on 3 November 2026, with three extensions:

- **Random sample.** 1,000 domains drawn from the Tranco top-1M list (list `GQ38K`), 250 from
  each rank band (1-1k, 1k-10k, 10k-100k, 100k-1M), measured with the same audit
  (`random_sample.csv`, `run_random_sample.py`). It tests whether the organisational sample is unusual.
- **History.** Archived robots.txt files from the Internet Archive for the 569 sites at five dates
  from July 2023 to July 2026 (`run_history.py`), analysed as a balanced panel with the live crawl
  as the final wave.
- **Inference and barriers.** Wilson intervals, exact McNemar tests (training vs answer agents),
  a permutation test for sector differences, and a site-level measure of barriers to AI answer
  engines (`analyze_extensions.py`).

## What we measured

| Signal | How |
|---|---|
| robots.txt policy for 24 AI and search agents | Fetched `/robots.txt`; evaluated with an RFC 9309 implementation (`aeotools/robots.py`) at the site root and at an arbitrary content path; recorded whether each agent is named or only covered by `*` |
| llms.txt | `/llms.txt` returning 200, not HTML, and starting with a Markdown H1 |
| Content-Signal / Content-Usage | robots.txt extension lines |
| Edge bot blocking | Homepage fetched with a declared bot user agent and with a browser user agent (both carrying our research token); 401/403/429/503 or challenge-page markers |
| Raw-HTML text | Visible words in the homepage HTML without running JavaScript |
| Rendered text | Visible words after rendering in headless Chrome (10 s virtual time budget) |
| Entity markup | JSON-LD types, `Organization`-type entities, `sameAs` links, microdata |

## Ethics and politeness

- The crawler identified itself (`AEOHandbookResearch/1.0`) and made at most five requests per
  site (robots.txt, llms.txt, two homepage fetches, one rendered page load).
- It obeyed robots.txt for its own token before touching any homepage: 37 sites were skipped
  for that reason.
- It never impersonated a real AI crawler.

## Reproduce

```bash
python run_measurement.py            # phase A: robots.txt, llms.txt, homepages
python run_measurement.py --render   # phase B: headless Chrome renders
python analyze.py                    # tables in results/, figures in ../../paper/figures/
python run_random_sample.py --sample # draw the Tranco sample (needs data/raw/tranco/top-1m.csv.zip)
python run_random_sample.py          # measure it
python run_history.py                # archived robots.txt files (slow: rate-limited to 10 requests/min)
python analyze_extensions.py         # results/extended.json, figures 8-10
```

The Internet Archive refuses clients that send requests quickly, so `run_history.py` shares one
rate limit across workers, backs off for 15 minutes when refused, and processes domains in a fixed
random order (a partial run is a random subsample).

Raw records (`data/raw/*.jsonl`) are kept out of git because of their size; `results/sites.csv`
has one row per site with every derived variable.

## Validation

Our robots.txt evaluator agrees with Protego (Scrapy's RFC-compliant parser) on 99.96% of
4,900 agent-by-site decisions. The disagreements come from shortened tokens such as `Perplexity`,
which Protego matches as prefixes and RFC 9309 matching does not.

## Limitations

- The main sample is purposive. The random Tranco sample shows similar training-crawler blocking
  but less answer-agent blocking, because the main sample over-represents news, community and
  reference publishers. Small businesses are under-represented in both.
- robots.txt states intent; it is not enforcement, and edge rules may treat real, verified AI
  crawlers differently from our declared research crawler.
- Rendering succeeded for 269 of 412 fetchable homepages; heavy or bot-protected pages failed
  more often, which probably *understates* JavaScript dependence.
- Root-level evaluation: path-level rules rarely matter (0.9% of sites block an answer agent at an
  article path but not at the root).
- The history depends on what the Internet Archive captured; some sites are excluded from it.
