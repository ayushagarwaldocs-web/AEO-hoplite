# The AEO Handbook

**Answer Engine Optimization: everything an organisation needs to be found, understood and
cited by ChatGPT, Claude, Gemini, Perplexity, Copilot and Google's AI Overviews, in one
evidence-graded source.**

This repository combines four things:

1. **A practitioner handbook** ([`docs/`](docs/)) covering access, content, entities, earned media,
   measurement, corrections, agents and commerce, ethics and roadmaps. Every technique is
   graded by the strength of its evidence.
2. **Engine-specific guides** ([`engines/`](engines/)) for ChatGPT, Claude, Google AI (AI Overviews,
   AI Mode, Gemini), Perplexity, Copilot and others: crawlers, controls, citation behaviour and
   measurement for each.
3. **Open tools** ([`aeotools/`](aeotools/)): a site audit, an RFC 9309 robots.txt evaluator, an
   AI-bot log analyser and a multi-model visibility tracker.
4. **Original research** ([`experiments/`](experiments/) and [`paper/`](paper/)): a measurement of access
   barriers on 569 organisational websites and 703 randomly sampled popular sites, and a pre-specified
   controlled experiment on content techniques run on three open-weight models.

## Start here

| If you want to… | Go to |
|---|---|
| Understand AEO in 10 minutes | [What AEO is](docs/01-what-is-aeo.md) → [How answer engines work](docs/02-how-answer-engines-work.md) |
| Check whether AI can read your site | `python -m aeotools.audit yoursite.com --render`, then [Technical access](docs/03-technical-access.md) |
| Know which content tactics actually work | [Content techniques, graded by evidence](docs/04-content-techniques.md) |
| Optimise for a specific engine | [Engine guides](engines/README.md) |
| Measure your AI visibility | [Measurement](docs/07-measurement.md) and `python -m aeotools.tracker` |
| Fix wrong AI answers about you | [Correcting AI answers](docs/08-correcting-ai-answers.md) |
| Get a plan | [90-day roadmap](docs/12-roadmap.md) and [audit checklist](checklists/aeo-audit-checklist.md) |

## The short version

1. **Access first.** Answer engines can't cite what they can't fetch. Allow the *answer*
   crawlers (`OAI-SearchBot`, `ChatGPT-User`, `Claude-SearchBot`, `Claude-User`,
   `PerplexityBot`, `Googlebot`, `Bingbot`), decide separately about *training* crawlers, check
   your CDN/WAF, and serve content as HTML. Most barriers we found were accidental: a wildcard
   rule, an unreachable robots.txt, a CDN default or text that only JavaScript produces.
2. **Earn corroboration.** Engines lean on reviews, press, communities and reference sites more
   than on your own pages. In our experiment, one recommendation in a neutral guide did more than
   any edit to the brand's own page.
3. **Rank for the questions engines search.** Engines retrieve through search indexes, so be the
   most relevant source for the real question and the sub-questions they fan out to: pricing,
   comparisons, alternatives, use cases.
4. **Put checkable evidence on your pages.** Specific figures, sources and named evaluations are
   what answers pass on to readers. Don't expect Q&A rewrites or freshness stamps to get you
   named: in our experiment they did nothing.
5. **Measure like a poll:** a fixed prompt set, repeated runs, and intervals around every number.
6. **Don't manipulate.** Hidden instructions worked on the small models we tested, but they deceive
   users and violate search engines' spam policies; keyword stuffing does too. Fake reviews and
   astroturfing are deceptive and a losing game when everyone does them.

## What our research found

**Experiment 1: 569 organisational websites, 22 sectors, November 2026** ([details](experiments/exp1_web_readiness/)):

- **34.6%** of sites have at least one barrier to AI answer engines (**19.0%** if refusals at the
  network edge are excluded). Only **9.3%** block an AI search crawler by name; for **25.3%** every
  barrier is implicit and would not show up in an audit of the AI rules in robots.txt.
- **82.2%** of sites with a reachable robots.txt are open to every AI agent we track. **12.2%**
  block at least one AI *answer* agent and **3.1%** block all of them, concentrated in news
  (74% of news sites) and community and review platforms (44%).
- **59.4%** of sites that block OpenAI's training crawler correctly leave its search crawler
  open. Among sites blocking an answer agent, **19.4%** do so only through an inherited
  wildcard rule, and some still rely on retired or misspelled tokens.
- **18.6%** of homepage requests from a plainly declared crawler were refused or challenged at
  the network edge, whatever the user agent.
- **11.2%** of rendered homepages expose less than half their text without JavaScript, which
  most AI crawlers don't run. Some well-known airline, bank and streaming homepages had no
  text at all in their raw HTML.
- **23.0%** publish an llms.txt (around half of SaaS, AI and fintech sites), despite little
  evidence that answer engines read it.
- Sites refuse AI *training* crawlers far more often than the agents that fetch pages for
  answers: **38** sites block `GPTBot` but not `OAI-SearchBot`, none do the reverse, and a random
  sample of **703** popular sites shows the same asymmetry.

![AI crawler block rates](paper/figures/fig1_block_rates.png)

**Experiment 2: 14 page treatments on three open-weight models** ([design and results](experiments/exp2_content_treatments/)):
30 scenarios with fictional, DNS-verified brands; access and retrieval held fixed; a length-matched
placebo; Llama-3.2-3B, Qwen2.5-3B and Granite-3.3-2B run locally; 4,050 answers; a pre-specified
analysis with Holm correction. Effects are on the chance that the brand is named, pooled over models:

- **Third-party endorsement: +26.7 points** (95% CI 20.0 to 33.3), and +39.3 on being named
  first. No single edit to the brand's own page came close; all five recommended edits together
  added +18.9.
- **Statistics +10.0 and source citations +11.9.** Both beat the length-matched placebo, but not
  the unedited page after correction. Repeated keywords also beat the placebo and gave the largest
  single-edit gain in being named first (+17.0).
- **Evidence is what reaches the reader.** Answers that named the brand repeated an added
  statistic 62% of the time and a cited source 71%, against 32% for persuasive phrases.
- **No effect:** restating the page as Q&A, adding a freshness date or stating limitations.
- **Position among the results mattered for one model only** (Llama named a page in first place
  94% of the time and in last place 38%).
- **A hidden "note to AI assistants" was the most effective treatment** (+28.9 points named, +58.1
  named first) and was disclosed in 0.4% of answers.

**Paper:** [`paper/main.pdf`](paper/main.pdf), *The Discoverability Gap: Access Barriers and Content
Effects in Answer Engine Optimization* (draft).

## Install and use the tools

```bash
pip install -r requirements.txt

# Audit a site: robots.txt for 24 AI agents, edge blocking, JS dependence, entity markup, llms.txt
python -m aeotools.audit example.com --render

# AI-bot traffic and AI referrals from server logs (optionally verify bot IPs)
python -m aeotools.logs /var/log/nginx/access.log --verify

# Track brand visibility across models (keys in .env; see .env.example)
python -m aeotools.tracker templates/prompt-set.csv --brand Acme --competitors Rival \
    --models anthropic:claude-sonnet-5-5 gemini:<model> --runs 5 --web-search

# Tests
python -m pytest
```

## Repository map

```
docs/          12-chapter handbook and glossary
engines/       per-engine guides and comparison matrix
checklists/    audit and page checklists
templates/     robots.txt variants, llms.txt, JSON-LD, facts page, prompt set, content brief
aeotools/      Python toolkit (audit, robots, logs, tracker, metrics, LLM clients)
experiments/   exp1_web_readiness (measurement) and exp2_content_treatments (benchmark)
paper/         LaTeX source, figures, generated numbers, PDF
references/    annotated bibliography
tests/         unit tests for the toolkit and templates
```

## How current is this?

Facts about crawlers, controls and products were checked against operator documentation in
November 2026. This field changes monthly; each claim links to its source so you can recheck it.
Pull requests that update facts with sources are welcome.

## Citing

See [`CITATION.cff`](CITATION.cff). Code is MIT-licensed ([`LICENSE`](LICENSE)); handbook text and
figures are CC BY 4.0 ([`LICENSE-docs`](LICENSE-docs)).

## Disclaimer

This handbook describes how public systems behaved at the time of writing. It is not
affiliated with or endorsed by OpenAI, Anthropic, Google, Microsoft, Perplexity or any other
company named. All brands in Experiment 2 are fictional.
