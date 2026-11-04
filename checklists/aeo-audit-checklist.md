# AEO audit checklist

Work top to bottom: each section depends on the one before it.

## Access (chapter 3)

- [ ] robots.txt returns 200 on every important hostname (not 5xx, not HTML)
- [ ] Answer agents allowed: `OAI-SearchBot`, `ChatGPT-User`, `Claude-SearchBot`, `Claude-User`, `PerplexityBot`, `Perplexity-User`, `Googlebot`, `Bingbot`
- [ ] Training policy decided and implemented deliberately (`GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `CCBot`, `Meta-ExternalAgent`)
- [ ] No answer agent blocked by accident through the `*` group
- [ ] Deprecated tokens (`anthropic-ai`, `Claude-Web`) replaced with current ones
- [ ] CDN/WAF lets verified AI agents through (check the logs for 200s, not 403s or challenges)
- [ ] Key pages' content is present in raw HTML (`python -m aeotools.audit <site> --render`)
- [ ] XML sitemap with accurate `lastmod`; Search Console and Bing Webmaster Tools verified; IndexNow on

## Entity (chapter 5)

- [ ] Canonical facts page published and current
- [ ] Name, description, category, leadership and prices consistent across site and profiles
- [ ] `Organization` JSON-LD with `sameAs` to official profiles; markup matches visible content
- [ ] Wikidata accurate (and Wikipedia, if notable, via conflict-of-interest-compliant requests)

## Content (chapter 4)

- [ ] A page for each key intent: pricing, comparisons, alternatives, use cases, integrations
- [ ] Answer-first sections with specific, dated facts
- [ ] Original data asset published or planned
- [ ] Limitations stated honestly where buyers care

## Off-site (chapter 6)

- [ ] Citation-gap analysis done (which domains engines cite for your category)
- [ ] Present and accurate on the top review platforms for your category
- [ ] PR and community plan in place, with disclosure

## Measurement (chapter 7)

- [ ] Prompt set (50+ prompts), tagged, with a baseline across 3+ engines and 5+ runs each
- [ ] AI referrals segmented in analytics; "AI assistant" in attribution surveys
- [ ] Server-log monitoring for AI agents (`python -m aeotools.logs`)
- [ ] Bing Webmaster Tools AI Performance reviewed monthly
- [ ] Brand-accuracy audit run monthly; correction workflow in place (chapter 8)

## Ethics (chapter 10)

- [ ] No hidden instructions, cloaking, fake reviews or undisclosed promotion
