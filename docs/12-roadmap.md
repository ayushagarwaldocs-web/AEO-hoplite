# 12. A 90-day roadmap

## Days 1–30: baseline and unblock

| Task | Owner | Output |
|---|---|---|
| Run `python -m aeotools.audit` on every important hostname | Engineering / SEO | List of blocked agents, JS-only pages, robots.txt errors |
| Decide the training versus answers policy; deploy robots.txt (templates in `templates/`) | Legal + SEO | Documented policy |
| Check CDN/WAF bot settings; allow verified AI search and user agents | Engineering | Verified 200s in logs |
| Build the prompt set (50–200 prompts) and run the first baseline (5+ runs per prompt, 3+ engines) | SEO / Analytics | Baseline mention, citation and accuracy report |
| Segment AI referrals in analytics; add "AI assistant" to attribution surveys | Analytics | Dashboard |
| Fix critical factual errors found in the baseline (chapter 8) | Comms + Web | Corrected pages, profile updates |

## Days 31–60: make content quotable

| Task | Owner | Output |
|---|---|---|
| Publish the canonical facts page; align profiles and Organization schema | Comms / SEO | One consistent entity |
| Rewrite the top 20 commercial pages answer-first with specific, dated facts | Content | Updated pages |
| Fill fan-out gaps: pricing, comparisons, alternatives, use-case pages | Content / Product marketing | New pages |
| Server-render any important pages that are JS-dependent | Engineering | Raw-HTML parity |
| Register with Bing Webmaster Tools; enable IndexNow; review AI Performance data | SEO | Grounding-query insights |

## Days 61–90: earn corroboration

| Task | Owner | Output |
|---|---|---|
| Citation-gap analysis: which third-party domains engines cite in your category | SEO / PR | Target list |
| Review programme on the platforms engines cite | Customer success | Steady, genuine reviews |
| One original-data asset (survey, benchmark, index) with a press push | PR / Research | Earned coverage |
| Community participation plan (disclosed, expert-led) | Product / DevRel | Presence where buyers ask |
| Second measurement round; compare with the baseline, with intervals | Analytics | Quarterly AEO report |

## KPIs

- Mention rate and share of voice on the core prompt set, per engine (with 95% intervals)
- Citation rate of your own URLs
- Accuracy rate of brand facts (target: 100% on prices and leadership)
- AI-referred sessions and conversions; "AI assistant" share in self-reported attribution
- Coverage: the share of priority third-party sources where you are present and accurate

## Team

AEO spans functions. The minimum is an owner in SEO or growth, an engineer for access and
rendering, a content lead, PR/comms for earned media and corrections, and analytics for
measurement. Legal decides the training-data policy.
