# Roller Team — survey and adapter

Surveyed and built 13 November 2026. `src/adapters/roller_team.py`, 20 products, first
run below.

`manufacturer_id` **229**, from `resources/manufacturers-full-list.csv`. Two names, and
they differ:

| | string |
|---|---|
| `fmlv_manufacturer` / `fmlv_display_name` | `Roller Team` |
| `ncc_supplier_name` | `Roller Team Motorhomes` |

Given by the requester, 13 November 2026, with the warning attached: *"in the supplier
list, it's listed as roller team motorhomes… in the manufacturers list, it's listed just
as roller team."* Neither has a hyphen.

Motorhomes and campervans only — no caravans — so `categories` is `motorhome`.

## Italian company, Italian website, English words

Roller Team is Trigano, which makes it a sister brand to Auto-Trail, Chausson and Adria.
The requester expected the site to resemble Auto-Trail's. It does not, and the reason is
worth knowing before reading a line of markup: **`rollerteammotorhomes.co.uk` is not a UK
build.** It is site 4 of the Italian WordPress multisite — every upload path is
`/wp-content/uploads/sites/4/…` — translated into English but with the Italian information
architecture left in place.

So the post type is `modello`, and the taxonomies are `gamma` (range), `tipologia` (body
type), `posti-letto` (berths), `posti-omologati` (homologated seats), `tipologia-letto`
(bed type) and `lunghezza` (length band). The sitemap index names all of them.

That matters because it decides where the data is, which is the next section.

## Twenty models, confirmed three ways

| range | models | body |
|---|---|---|
| Livingstone | 2, DUO | campervan |
| Kronos Compact | 590, 665, 670 | low profile |
| Zefiro | 675, 685, 696, 707, 746, 747, Sport | low profile and over-cab |
| T-Line | 590, 700, 740, 750 | low profile |
| Pegaso | 590, 740, 745, 750 | A-class |

Twenty is not an estimate. It is the count in the 2027 price list, the number of
spec-table columns in the 2027 brochure, and the `x-wp-total: 20` header the REST roster
returns. Three independent statements, no discrepancy.

## Three sources, each doing one job

Nothing here is a single-document adapter. The split is clean, and each part is the only
place its data exists.

### 1. The roster, the range and the body type — the WordPress REST API

```
https://www.rollerteammotorhomes.co.uk/wp-json/wp/v2/modello?per_page=100
```

Open, unauthenticated, server-rendered, one fetch for the lot. Each record carries
`title`, `link` and a `class_list` holding the taxonomy slugs:

```json
{"slug": "zefiro-707", "title": {"rendered": "Zefiro 707"},
 "class_list": ["gamma-zefiro", "tipologia-low-profile", "posti-letto-6-berths"]}
```

`gamma-*` gives the range and `tipologia-*` gives the body type — `low-profile`,
`a-class`, `over-cab`, `campervan` — which is a manufacturer publishing its own body type
as typed data rather than leaving us to derive it. Both are complete and correct on all
twenty.

The site's own model finder, `/ricerca-camper/`, renders **zero** model links in plain
HTML; it is a JavaScript filter UI. The REST roster replaces it, and needs no browser.

### 2. Every number — the 2027 brochure PDF

`/catalog-2025/` → `RT-Brochure-2027.pdf`, 24 pages. Each range gets a two-page
**Technical Specifications** table, columnar, one column per model. The weights block is
identical in shape across all five ranges:

```
Technical Specifications   Kronos Compact 590   Kronos Compact 665   Kronos Compact 670
Berths                     2 (+2 optional)      4 (+1 optional)      2 (+2 optional)
Belted seats               4                    4 (+1 optional)      4
External length            5.99m                6.41m                6.69m
External width             2.15m                2.15m                2.15m
External height            2.85m                2.85m                2.85m
Internal height            2.04m                2.04m                2.04m
Gross vehicle weight       3,500kg              3,500kg              3,500kg
Mass in running order      2,695kg              2,775kg              2,795kg
```

That is berths, travel seats, every dimension and both masses, for all twenty. The facing
page carries bed sizes, tank capacities, heating and fridge — the habitation findings,
already in the same document.

### 3. The price — the 2027 UK price list PDF

`/price-list/` → `Roller-Team-Price-List-2027.pdf`, 2 pages, footed *"2027 Retail Price
Guide, Issue 1 | 1st September 2026"*.

```
Zefiro 707   7.12m (23'4")   Ford Transit 130 bhp   £58,800   £11,760   £70,560   £70,995
```

— model, length, chassis, retail ex VAT, VAT, ex-works incl VAT, **on the road**.

**The website publishes no price at all**, so this is the only price source and no
website-overrules-PDF conflict can arise. The on-the-road column is the one to record, and
it is internally checkable: it is the ex-works figure plus exactly £435 on all twenty,
which the list itself explains as *"number plates, twelve months Vehicle Excise Duty and
first registration fee (as set by H.M. Government) – total £435."*

## The self-check: external length, published three times

Every one of the twenty models has its external length stated independently by the model
page's headline tiles, the price list and the brochure spec table. **All twenty agree to
the centimetre, with zero mismatches.**

This is the self-check the README asks for, and it earns its place for a specific reason
rather than a general one. The brochure's masses are read out of a flattened columnar PDF,
which is the single highest-risk parse in this repo — a column shifted by one yields
plausible, internally consistent motorhomes carrying each other's weights. Length sits in
the same column block as `Gross vehicle weight` and `Mass in running order`. **If the
length in column 2 matches what two other documents say about that model, column 2 is that
model's column, and the masses beside it are its own.**

Chassis is a second, weaker check: published by both PDFs, agreeing on all twenty.

## Four traps

### The slug lies

```
https://www.rollerteammotorhomes.co.uk/tipologia/low-profile/zefiro-647/
    <title>Zefiro 747 - RollerTeam UK</title>
```

There is no Zefiro 647. Both PDFs list a **747**, the page title says 747, and the slug is
the only thing anywhere that says 647. **Read the title, never the slug.** An adapter that
keyed on the slug would propose a phantom `Zefiro 647` as a new product every run and
report the real 747 as disappeared — a rename that never happened, in both directions at
once.

### The taxonomies look like data and are partly wrong

The temptation, having found a REST API that publishes berths as a term, is to read berths
from it. Do not:

| | REST taxonomy | page tile | brochure table |
|---|---|---|---|
| Kronos Compact 590 / 665 / 670 | *no `posti-letto` term at all* | 2 / 2 / 2 | 2 (+2 opt) / 4 (+1 opt) / 2 (+2 opt) |
| Zefiro 746 | `posti-letto-4-berths` | 6 | 6 |
| Zefiro 747 | `posti-letto-4-berths` | 6 | 6 |

`posti-omologati` is worse — its slugs are `43`, `44`, `45`, which are WordPress term ids
left behind where the slug was numeric, not seat counts. `tipologia-letto-53` is the same
failure.

**`gamma-` and `tipologia-` only.** They are the two the site actually uses for
navigation, which is presumably why they are the two that are maintained.

### The page slugs are stale as well, and neither page states a year

The 2027 brochure lives behind a page slugged `/catalog-2025/`. Neither that page nor
`/price-list/` states a model year anywhere a customer can see — both are titled just
"Catalogue" and "Price List". The Etrusco rule says take the year from the page that links
the document; here the page says nothing, so the year comes from inside the documents,
where both state it plainly.

There is exactly **one** price list and **one** brochure linked, so the
superseded-document hazard does not arise. But both URLs are date-stamped upload paths —
`…/2026/09/…` and `…/2026/11/…` — so they must be rediscovered from the two pages each
run, never hardcoded.

### The site 403s a bare user agent

`curl -A "Mozilla/5.0"` gets a 403; the repo's own `USER_AGENT` gets a 200. `robots.txt`
is `Disallow:` — nothing excluded — and names four sitemaps including the UK one. No
action needed, but a future "the site is blocking us" report should check what user agent
was actually sent before concluding anything.

## The gross weight is a choice, and the payload is not published

Every model is **3,500 kg**, with a free upgrade to 3,650 kg (Fiat) or 3,550 kg (Ford).
The base-vehicle rule takes 3,500. No payload is printed anywhere in either document, so
it derives as 3,500 − MRO and the provenance says derived.

The masses are real and complete: MRO runs from 2,695 kg (Kronos Compact 590) to 3,060 kg
(Pegaso 750), all twenty present.

## Settled: the Kronos Compact 665 tile is a website typo

| source | says |
|---|---|
| page tile | `2` |
| brochure technical table | `4 (+1 optional)` |

**Settled by the requester, 13 November 2026, from the floorplan:** *"I've just looked at
the floor plan and I can see that there's a fixed bed and there's also a drop-down bed at
the front, both of them are doubles, so that's four berth… I think it's just a typo on the
website."*

So **4**, and the reason matters as much as the figure. This is not the
summary-tile-versus-technical-table rule arbitrating between two honest sources — it is
one wrong number on one page. The distinction decides what the adapter does with it: a
rule would be applied silently to every tile, whereas **a typo is named once and not
re-raised**, the way Bailey's Endeavour B65 length is. The tile is still worth reading as
a cross-check, but a disagreement on the 665 specifically is a known fault, not a question
for a reviewer.

The price list corroborates the brochure independently: a `5th homologated seat + 5th
sleeping berth` option at £290 is offered on exactly four models, and the brochure marks
exactly four with `(+1 optional)` or `(5 optional)` — Kronos 665, Zefiro 685, Zefiro
Sport, T-Line 700.

**A caution about how this was nearly argued instead.** The first draft of this survey
reasoned that the 665 "has no rear bed and a standard elevating bed" from the brochure's
`Rear bed (cm)` row. That row carries **one value for three models**, so it says nothing
about which model it belongs to — and the floorplan shows the 665 does have a fixed bed.
The conclusion was right and the evidence was not. The bed-dimension rows are ragged in a
way the weights block is not; do not read them positionally.

Livingstone DUO disagrees the same way (`2+1` on the tile, `2` in the table) but resolves
to **2** under either source once the berth-range rule is applied, so nothing turns on it.

## What is unresolved, and needs a decision before stage 2

### The automatic gearbox

Three facts, pulling in different directions, all from the price list:

- It is priced separately, but as an **uplift**, not a price: Ford 8-speed £1,860, Fiat
  8-speed £3,840, or £6,660 with the 180 bhp engine. Landseer, the only precedent,
  published two complete prices.
- *"When Hi-Line, automatic gearbox is mandatory"* — which makes **Zefiro 675 and Zefiro
  Sport** automatic-only, though the list still prints a manual price for both.
- *"Please be aware when Ford automatic is chosen at 3,500 kg, one seatbelt will be removed
  due to weight limits."* So the automatic variant of a Ford model has one travel seat
  fewer.

**Recommendation:** `automatic_available = Yes` on all twenty, which the citation rule
gives directly. Leave the four `automatic_*` figure columns for a decision — filling
`automatic_rrp_pounds` means publishing on-the-road plus uplift as though Roller Team
printed it, and the seatbelt note means the automatic variant is not simply the same
vehicle at a higher price.

## What has not been checked

- **No FMLV baseline was examined.** There is no export under `data/exports/` for 229 and
  no registry row existed before today, so the comparison that normally catches a wrong
  parse — every product proposed as new — has not been run. Needs `fmlv fetch-export`
  against `Roller Team Motorhomes` before any build.
- **Habitation prose** on the model pages has not been passed through `habitation.py`. The
  brochure's equipment tables are the better source and are structured, but the pages carry
  marketing sentences of the kind that need the prose-option filter.
- **The optional-extras grid** on price list page 2 is a model-by-model matrix of £ marks.
  Its columns were *not* parsed and should not be trusted positionally from flattened text.

## Built, 13 November 2026

Run #252 against the live site and the real FMLV baseline: **20 collected, none dropped,
every length checked out across all three sources.** 17 changed, 3 new, 2 disappeared, 78
changes proposed, 6 habitation findings.

FMLV already held 20 Roller Team rows, and they did not line up with the site.

### The baseline turned out to be the best check of all

The one weakness of the length self-check is that it cannot separate two models in the
same range that share a chassis length — T-Line 740 and 750 are both 7.43m, Pegaso 740 and
745 both 7.41m, Zefiro 746 and 747 both 7.24m, Zefiro 685 and 696 both 7.45m. For those
eight the column assignment rests on the header's own left-to-right order.

**FMLV's own figures settle every one of them.** Each ambiguous model's held mass in
running order matches the column this adapter assigned it, exactly:

| | FMLV holds | brochure column |
|---|---|---|
| Zefiro 685 / 696 | 2,895 / 2,875 | 2,895 / 2,875 |
| Zefiro 746 / 747 | 2,935 / 2,925 | 2,935 / 2,925 |
| Pegaso 740 / 745 | 3,040 / 3,010 | 3,040 / 3,010 |

The T-Line is the one range whose masses moved this season, so it has no such
confirmation — but its prices supply one instead. The price list gives the 700 and the 750
**the same** on-the-road figure of £76,900 and the 740 a different £79,155; FMLV likewise
holds the 700 and the 750 at an identical £75,455 and the 740 apart at £77,655. Two
documents a season apart agreeing on *which two of the three are priced alike* is the same
kind of evidence as a matching mass.

### `Auto-Roller` is a range rename, and was nearly three new products

The first run reported **6 new and 5 disappeared**, which is the shape the README warns is
*"almost always"* a rename. Three of them were: FMLV files the Zefiro 707, 746 and 747
under `Auto-Roller`, Roller Team's older UK brand name, as a *range*. The masses are
identical to the kilogram and so are the lengths, so `RENAMED_MODELS` declares the three
and the run now reports **3 new and 2 disappeared**, proposing the range correction on the
existing products instead of orphaning them.

It is keyed per model rather than range-wide on purpose: the other four Zefiros are already
filed as `Zefiro`, and a range-wide entry would have orphaned every one of them.

### The three genuinely new, and the two genuinely gone

New, with no FMLV row and no disappearance that matches on mass: **Kronos Compact 670**,
**Livingstone DUO** and **Pegaso 750**.

Gone, and worth a different action each:

* **`Livingstone 6 Sport` (7699's sibling, 7700)** is discontinued. It is *not* the DUO —
  2,904kg against 2,994kg, and 5,995mm against 6,360mm, which is a different chassis
  length rather than a spec change.
* **`Zefiro 665` (4190) is a duplicate, not a discontinuation.** FMLV holds it at 2,775kg
  and 6,410mm, which are the **Kronos Compact 665**'s figures exactly — and FMLV holds
  that model too, at 8403. 4190 is the same vehicle under the old range name.

One more that never reached the run: **`Kronos Compact 590` is in FMLV twice**, 7883
(year 2025, 2,865kg, £70,890) and 8402 (year 2027, 2,695kg, £58,545). The baseline reader
deduplicated them and kept 8402, so 7883 is invisible to the diff and will stay in FMLV
until someone deactivates it.

### What the adapter does not propose

* **No bed type.** The brochure's bed-dimension rows are ragged — `Rear bed (cm)` gives one
  value for the Kronos's three columns — so nothing can be assigned from them. They are
  narrated with the floorplan link instead. This is the trap that produced a wrong
  inference during the survey, and `_cells` now refuses any row whose cell count does not
  match the column count.
* **No `automatic_*` figures.** `automatic_available` is a plain Yes on all twenty, cited
  from the price list. The four figure columns stay blank because Roller Team price the
  automatic as an **uplift** (£1,860 Ford, £3,840 Fiat), not as a price of its own.
* **No model-page prose is read for habitation.** It would have put a make-up bed on every
  model from one sentence about a dinette, on models where the price list prices
  "Dinette-into-bed transformation" at £320 as an option. Heating and the fridge come from
  the brochure's equipment tables, where they are per-column and checkable.
