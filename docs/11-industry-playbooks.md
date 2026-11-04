# 11. Industry playbooks

The fundamentals are the same everywhere; the emphasis differs. Each playbook lists the
highest-leverage moves for that kind of organisation.

## B2B software (SaaS)

- One page per intent: pricing, each integration, each competitor comparison
  ("X vs Y", "Y alternatives"), each use case and industry.
- Public, server-rendered documentation; an llms.txt for docs is reasonable here.
- Earn coverage on G2/Capterra, analyst notes, practitioner newsletters and communities
  (Reddit, Stack Overflow, Hacker News), where buyers ask for recommendations.
- Consider an MCP server for docs search or account actions (chapter 9).
- Track "best [category] for [segment]" prompts per segment you sell to.

## E-commerce and consumer brands

- Complete, fresh product feeds (Merchant Center, the ChatGPT product feed) with accurate
  prices, availability and variants.
- Product pages with specs in text and tables, sizing and compatibility, return policy, and
  genuine review content.
- Independent reviews (publications, YouTube creators) drive "best X under $Y" answers. Send
  products for honest review, with disclosure.
- Watch for wrong prices or discontinued products in answers (chapter 8).

## Local businesses

- Google Business Profile, Bing Places and Apple Business Connect: complete and consistent
  name, address and phone, hours, services and photos.
- Reviews on the platforms your locals use; respond to them.
- A page per service and location with prices or price ranges, and specifics such as
  parking, accessibility and booking.
- Local press and community mentions (local news, neighbourhood groups).

## Publishers and news organisations

- Decide on training separately from answer visibility: many publishers block training
  crawlers but allow search-index bots so they stay citable. In our sample, news sites block
  AI crawlers far more than other sectors (see the paper).
- Licensing and publisher programmes exist at several AI companies. Weigh them against the
  traffic and attribution you get back.
- Clear bylines, dates and corrections policies help engines attribute and date your
  reporting correctly.

## Health, finance and other high-stakes ("YMYL") topics

- Engines are conservative here and favour institutional sources. Credentials, editorial
  review, citations to primary research and clear dates matter more than anywhere else.
- Never publish promotional health or financial claims you cannot substantiate. Regulators
  apply the same rules to AI-visible content as to any advertising.
- Make it easy to verify who you are: licences, registration numbers, governance pages.

## Education

- Course pages with outcomes, prerequisites, schedules, total cost and verifiable results
  (audited outcome reports beat testimonials).
- Comparison and "is it worth it" questions dominate; answer them honestly on your own site,
  and earn independent reviews.

## Government, nonprofits and public-interest organisations

- Your goal is usually accuracy, not promotion: make authoritative pages easy to retrieve and
  quote (plain language, dates, eligibility rules in text).
- Avoid blocking answer engines unless there is a specific reason. If they cannot read the
  official source, they will quote unofficial ones.

## Developer tools and APIs

- Docs are your AEO: server-rendered, versioned, with complete code examples and error
  references.
- Provide llms.txt and Markdown versions of docs for coding agents; keep changelogs current
  so agents don't suggest deprecated APIs.
- Publish an MCP server or OpenAPI spec so assistants can use your product directly.

Next: [Roadmap →](12-roadmap.md)
