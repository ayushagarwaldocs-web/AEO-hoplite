# 5. Be an unambiguous entity

Answer engines reason about *entities* (organisations, products, people, places), not just
pages. If the web disagrees about who you are, what you sell and what it costs, models hedge,
confuse you with namesakes, or repeat outdated facts.

## 5.1 Decide your canonical facts

Write down, in one place, the facts you want every source to agree on:

- Legal and trading name, and any former names
- One-sentence description and category ("Acme is a project management tool for agencies")
- Founding year, headquarters, leadership
- Products and current prices; regions served
- Official profiles (LinkedIn, X, YouTube, GitHub, app stores, Crunchbase, G2, and so on)

Publish them on a crawlable **facts page** (template: [`templates/facts-page.md`](../templates/facts-page.md))
and keep your About, Press and Pricing pages consistent with it.

## 5.2 Make every profile agree

Update the profiles engines and journalists read: LinkedIn, Crunchbase, Google Business
Profile, Bing Places, Apple Business Connect, app store listings, G2/Capterra/Trustpilot,
industry directories, and your own social bios. Inconsistent descriptions are one of the
most common causes of wrong AI answers.

## 5.3 Wikipedia and Wikidata, carefully

- **Wikidata** items help disambiguate entities and are widely reused. You may add factual,
  referenced statements; follow Wikidata's notability and referencing rules.
- **Wikipedia** requires independent notability and forbids promotional editing. Never write
  or pay for your own article. If you have a conflict of interest, propose corrections on the
  article's talk page with independent sources, and disclose your affiliation.

## 5.4 Structured data: useful, but not magic

Schema.org markup helps search engines understand entities and is required for some rich
results. Google, however, says "there's no special schema.org structured data that you need
to add" for AI Overviews and AI Mode, and a 2026 matched-control study found adding JSON-LD
produced roughly no change in AI citations for pages already being cited. Treat it as hygiene
for entity understanding, not a ranking lever.

Recommended minimum (templates in [`templates/`](../templates/)):

| Page | Types |
|---|---|
| Home or About | `Organization` (or a subtype) with `name`, `url`, `logo`, `description`, `sameAs`, `foundingDate`, `address` |
| Product pages | `Product` with `offers` (`price`, `priceCurrency`, `availability`), `brand`, `aggregateRating` only if genuine |
| Articles | `Article` / `NewsArticle` with `author` (a `Person` with `sameAs`), `datePublished`, `dateModified` |
| Local business | `LocalBusiness` subtype with `address`, `geo`, `openingHoursSpecification`, `telephone` |

Rules: markup must match visible content (Google requires it); never mark up reviews you
don't display; keep `dateModified` honest.

In our measurement of 412 fetchable organisational homepages, about half carried an
`Organization`-type JSON-LD entity, with a median of 5 `sameAs` links where present.

Next: [Earned media and off-site presence →](06-earned-media-and-offsite.md)
