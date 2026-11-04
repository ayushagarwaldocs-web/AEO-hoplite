# Microsoft Copilot and Bing

## Where answers come from

Copilot and Bing's AI summaries are grounded in Bing's index, crawled by `Bingbot`. There is
no separate AI crawler token. Bing's index is also a major source for ChatGPT search, so Bing
visibility pays off twice.

## Controls

- Bing has documented `NOCACHE` and `NOARCHIVE` robots meta values as controls over use in
  its chat answers. Check current Bing Webmaster guidelines before relying on them.
- [IndexNow](https://www.indexnow.org/) gets new and changed URLs to Bing (and other
  participating engines) quickly.

## Microsoft's own guidance

Microsoft's October 2025 post *Optimizing your content for inclusion in AI search answers*
says sections are evaluated on clarity, structure and how directly they answer user intent;
recommends clear headings, concise answer-first passages and schema markup; and notes there is
no guaranteed way to be included.

## Optimisation priorities

1. **Verify the site in Bing Webmaster Tools**, submit sitemaps, enable IndexNow.
2. **Use the AI Performance report** (preview since February 2026): total citations in
   Copilot and Bing AI summaries, citations per page, and the **grounding queries** behind
   them. Grounding queries show which sub-topics pull you into answers; write for the gaps.
   No click data is included, and the grounding-query table paginates.
3. **Answer-first sections with clear headings**, matching Microsoft's stated evaluation
   criteria.
4. **Schema markup:** Microsoft says it helps its systems understand content.

## Measurement

AI Performance in Bing Webmaster Tools is the only first-party AI citation report among the
major engines as of November 2026. Pair it with referral data from `copilot.microsoft.com`
and `bing.com`.
