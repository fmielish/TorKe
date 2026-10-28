# Manual sites and their terms

Every manual site in TorKe starts **off**. An admin turns sites on in the tool's settings (Workspace > Tools > TorKe > gear).

Your own manuals come first: PDFs attached to the item in Homebox (type Manual) or attached in a chat. TorKe reads those on your own server, so no site's terms are involved.

TorKe treats manual sites three ways:

- **Read through an API:** TorKe reads the content through the site's official API and links back to it.
- **Links only:** TorKe never opens the site's pages. It gives the user search links to open themselves, because the site's terms ban automated access or couldn't be confirmed.
- **Readable:** TorKe opens one page at a time when the user asks, with no crawling or prefetching.

Terms were checked in October 2026. They change, so check them again before turning a site on.

| Site | How TorKe uses it | What the terms say |
|---|---|---|
| iFixit | Read through its public API | Reads are public with no key. Real-time AI use to answer a person's question is welcome; scraping HTML, AI training and commercial use are not. Content is CC BY-NC-SA 3.0: credit iFixit, link the exact guide, and link every tool and part the guide lists. TorKe does all three. |
| ManualsLib | Links only | Its terms ban bots, spiders, scrapers, crawlers "or other automated devices", and allow personal, non-commercial use only. |
| RepairClinic | Links only | TorKe couldn't load or confirm its terms, so it doesn't read its pages. |
| Carmaker owner's manuals | Links only | Most carmakers post owner's manuals free on their own sites. Each maker's terms differ, so TorKe only links. Factory service procedures and torque specs are usually paid (the maker's service site, ALLDATA); many public libraries offer free ALLDATA or Chilton access. |
| Operation CHARM (charm.li) | Readable, **legal gray area** | No terms of use or license posted. It hosts factory service manuals for 1982-2013 vehicles; their copyright status is unclear. |
| LEMON Manuals | Readable, **legal gray area** | Same as CHARM, which calls LEMON its successor: no terms posted, manuals for 1960-2025 vehicles, unclear copyright status. |
| Your own sites | Readable | Add a site only if its terms allow automated reading. |

## Recall data (Safety warnings)

With **Recall checks** on, Safety warnings also checks two free US government sources. No key is needed.

- **NHTSA** recalls by year, make and model: vehicles and car seats.
- **CPSC** recalls by product name: household and children's products.

## Sources

- [iFixit guidance for AI and automated use](https://www.ifixit.com/llms.txt)
- [iFixit content licensing](https://www.ifixit.com/Info/Licensing)
- [ManualsLib terms of use](https://www.manualslib.com/terms.html)
- [Operation CHARM](https://charm.li/)
- [LEMON Manuals](https://lemon-manuals.la/)
- [NHTSA datasets and APIs](https://www.nhtsa.gov/node/102181)
- [CPSC recalls API](https://www.cpsc.gov/node/5808)
