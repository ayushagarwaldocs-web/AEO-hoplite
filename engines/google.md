# Google: AI Overviews, AI Mode and Gemini

## Where answers come from

- **AI Overviews and AI Mode** are part of Google Search and draw on the Search index built
  by Googlebot. Both may use **query fan-out**, "issuing multiple related searches across
  subtopics and data sources."
- The **Gemini app** grounds answers with Google Search, as well as using training memory.

## Requirements and controls

From [Google's AI features guidance](https://developers.google.com/search/docs/appearance/ai-features):

- "There are no additional requirements to appear in AI Overviews or AI Mode, nor other
  special optimizations necessary." A page must be indexed and eligible to show a snippet.
- "There's also no special schema.org structured data that you need to add."
- To limit what appears, use `nosnippet`, `data-nosnippet`, `max-snippet` or `noindex`.
- **`Google-Extended`** controls whether content is used to train Gemini models *and for
  grounding in Gemini Apps and Vertex AI*. It "does not impact a site's inclusion in Google
  Search." Blocking it may therefore reduce how the Gemini app uses your pages, while AI
  Overviews are unaffected.
- Google says it intends to support the IETF AIPREF training-preference signal in early 2027.

## Optimisation priorities

1. **Classic SEO excellence.** Crawlable, indexable, fast pages with textual content; this is
   the whole eligibility story.
2. **Cover the fan-out.** Sub-topic pages (pricing, comparisons, how-tos, specs) give the
   fan-out searches something of yours to find.
3. **Video:** YouTube is among the most-cited domains in AI Overviews; publish explainers
   with accurate titles, chapters and transcripts.
4. **Merchant Center and Business Profile:** Google explicitly recommends keeping them
   current for AI experiences. The Universal Commerce Protocol (2026) connects catalogues and
   checkout to AI Mode and Gemini.
5. **Structured data** must match visible content. It helps rich results and understanding,
   but it is not required for AI features.

## Measurement

- Search Console counts AI Overviews and AI Mode traffic inside the "Web" search type, with
  no separate filter.
- Google says clicks from pages with AI Overviews tend to be higher quality (more time on site).
- Use prompt sampling for AI Mode and the Gemini app.

## Ads

Search ads can appear in AI Overviews and AI Mode.
