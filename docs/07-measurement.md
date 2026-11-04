# 7. Measuring AI visibility

AI answers are probabilistic, personalised and mostly click-free. Measure them like an
opinion poll (a defined sample, repeated, with error bars), not like a rank tracker.

## 7.1 Build a prompt set

A prompt set is your keyword list for AEO. Start from [`templates/prompt-set.csv`](../templates/prompt-set.csv).

- **50–200 prompts** covering the journey: problem discovery ("how do I…"), category
  ("best X for Y"), comparison ("X vs Y", "alternatives to X"), brand ("is X good",
  "X pricing", "X reviews") and post-purchase ("how to set up X").
- **Phrase them the way customers do**, including personas and constraints ("for a
  15-person agency", "under $300", "in Manchester").
- **Include paraphrases** of your most important prompts: wording changes results.
- **Tag each prompt** by intent, funnel stage, product line, market and language.
- Freeze a core set so trends are comparable; rotate a smaller exploratory set.

## 7.2 Sample properly

- Run each prompt **several times** (5–10 for key prompts) per engine. Lists of
  recommendations almost never repeat exactly, but *how often* a brand appears is stable
  enough to track (SparkToro/Gumshoe, 2026).
- Record the engine, model, surface (app with search or API), location, language and date.
- Report rates with intervals. For a mention rate *p* from *n* runs, use a Wilson interval;
  at n = 10 a 50% rate has a 95% interval of roughly 24–76%. Don't over-read week-to-week
  wiggles.

## 7.3 Metrics

| Metric | Definition | Use |
|---|---|---|
| **Mention rate** | Share of answers that name your brand | Headline awareness KPI |
| **Share of voice** | Your mentions ÷ all tracked brands' mentions | Competitive position |
| **Top-pick rate** | Share of answers where you are the first brand named | Recommendation strength |
| **Citation rate** | Share of answers citing any of your URLs | Whether *your* pages are trusted sources |
| **Citation share** | Your citations ÷ all citations | Source prominence |
| **Position-adjusted word count** | Words in sentences citing you, weighted by position ([GEO](https://arxiv.org/abs/2311.09735)) | How much of the answer you shape |
| **Accuracy** | Share of answers whose claims about you are correct | Brand risk |
| **Sentiment / framing** | How you are described (strengths, caveats) | Positioning |
| **Source mix** | Which domains are cited when you are (or aren't) mentioned | Where to earn coverage |

Implementations of the brand and source metrics are in [`aeotools/metrics.py`](../aeotools/metrics.py).

## 7.4 Tools

- **This repo:** `python -m aeotools.tracker templates/prompt-set.csv --brand "Acme"
  --competitors "Rival,Other" --models anthropic:claude-sonnet-5-5 openai:<model>` runs a
  prompt set through model APIs and reports mention, top-pick and share-of-voice metrics.
  API answers differ from consumer apps (no personal memory, different search settings);
  use them for trends, and spot-check the apps by hand.
- **Commercial trackers** (for example Profound, Peec AI, Otterly, Scrunch, and AI-visibility
  features in Semrush and Ahrefs) sample consumer surfaces at scale. Ask any vendor how many
  runs per prompt they take, which surfaces and locations they use, and whether they report
  uncertainty.
- **Bing Webmaster Tools → AI Performance** (preview since February 2026) is the only
  first-party citation report among major engines as of this writing. It shows citations in
  Copilot and Bing AI summaries, cited pages and grounding queries, but no clicks.
- **Google Search Console** counts AI Overviews and AI Mode traffic inside the normal "Web"
  performance data, without a separate filter.

## 7.5 Analytics and logs

- **Referrals:** segment sessions from `chatgpt.com` (ChatGPT adds `utm_source=chatgpt.com`),
  `perplexity.ai`, `claude.ai`, `gemini.google.com`, `copilot.microsoft.com` and similar.
  Volumes are small but often high-intent.
- **Server logs:** live-fetch agents (`ChatGPT-User`, `Claude-User`, `Perplexity-User`)
  hitting a page usually mean someone just asked an assistant about it, which makes them a
  leading indicator of demand. Search-index bots show crawl coverage. Run
  `python -m aeotools.logs access.log` for a per-agent, per-path summary; verify important
  bots by IP range before trusting the user agent.
- **Self-reported attribution:** add "AI assistant (ChatGPT, Claude, Gemini…)" to "How did
  you hear about us?" Much AI influence never produces a referral.

## 7.6 Reporting cadence

- **Monthly:** mention rate, share of voice and citation rate per engine for the core
  prompt set, with intervals, plus accuracy issues found and fixed.
- **Quarterly:** source-mix review (where citations come from), competitor movements,
  progress on citation-gap plays.
- **After launches or incidents:** targeted prompt runs to check that new facts propagate.

Next: [Correcting what AI gets wrong →](08-correcting-ai-answers.md)
