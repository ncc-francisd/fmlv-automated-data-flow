# Barefoot Caravans — survey and build, 8 October 2026

**NCC id 30.** `fmlv_manufacturer` **`Barefoot Caravans`**, display name **`Barefoot`**,
supplier name `Barefoot Caravans`. Caravans only, built at Blockley in the Cotswolds.
**Built on 8 October 2026** as `src/adapters/barefoot.py`; the first run is at the foot of
this file.

**One shell, several interiors.** Every model shares the same fibreglass body: 5080 mm over
the hitch, a 3780 mm shell, 1920 wide, 2360 tall. What differs between them is the fit-out,
the price and — on the two newest — the weights.

## What FMLV holds

| id | | year | state |
|---|---|---|---|
| **4129** | Classic / Classic | 2026 | live |
| **4130** | Forward / Forward | 2026 | live |
| **7870** | Country Living / Country Living | 2026 | live |
| **7897** | Eclipse / Eclipse | 2026 | live |
| 7871 | Noir / Noir | 2025 | **deactivated** |
| 1216 | Classic / Classic | 2022 | archived |

**Four live products**, every one filed with the range repeating the model — the
single-name convention in [`README.md`](README.md), because Nova will not take a blank.

> The export of November 2025 held `7870` as `Country`; today's holds `Country Living`.
> The name was corrected at some point in between, which is why a current export matters.

## The source is the catalogue's specification table

**`/wp-content/uploads/2025/10/Go-Barefoot-cat.pdf`**, linked from the home page. Eleven
pages, of which **page 10** is a real specification table covering the whole range in four
columns, and it extracts cleanly:

```
Specification          Barefoot Bothy  Barefoot Lite  Classic, Forward & Eclipse  Country Living
Berth                              3              2                           2               2
Axles                         single         single                      single          single
Weight (MTPLM*), kg          750/850      1100/1200                   1100/1200       1100/1200
Weight (MRO**), kg               706            900                         960             960
Maximum User Payload***, kg   44/144        100/200                     140/240         140/240

Dimensions in mm    Classic, Eclipse, Country Living, Forward, Lite   Bothy
Overall Length                                               5080     5080
Overall Width                                                1920     1920
External Height                                              2360     2360
Body Length (shell)                                          3780     3780
Internal Height                                              1870     1910
```

**Those figures are FMLV's exactly** on all four live products — MTPLM 1100, MRO 960,
payload 140, and every dimension. So this document is demonstrably where they came from.

**A second page is needed for one field.** The catalogue gives no internal length;
`/vital-statistics/` does — 3560 mm — along with the living area (2800 × 1830). FMLV holds
3560, so that page is the source for it. Two fetches per run.

## The self-check is real, and it found an error immediately

`MTPLM − MRO` should be the published `Maximum User Payload`, and the table prints all
three for every column:

| | MTPLM | MRO | published payload | derived |
|---|---|---|---|---|
| Bothy | 750/850 | 706 | 44/144 | **44/144** ✓ |
| **Lite** | **1100/1200** | **900** | **100/200** | **200/300** ✗ |
| Classic, Forward, Eclipse | 1100/1200 | 960 | 140/240 | **140/240** ✓ |
| Country Living | 1100/1200 | 960 | 140/240 | **140/240** ✓ |

**The Lite does not reconcile, and its own page says why.** `/barefoot-lite/` reads *"The
tow weight is just 1,000kg"* — and **1000/1100** against an MRO of 900 gives exactly the
100/200 the catalogue prints. So the catalogue's Lite MTPLM column is wrong and the right
figures are 1000 and 1100.

## Two new models, both badged NEW

The site's navigation lists six: **Bothy**, **Lite**, Eclipse, Classic, Forward, Country
Living. The first two are marked `NEW` and FMLV holds neither.

| | price | berths | MTPLM | MRO | payload |
|---|---|---|---|---|---|
| **Bothy** | £25,950 | **3** | 750 *(or 850)* | 706 | 44 |
| **Lite** | £34,950 | 2 | **1000** *(or 1100)* | 900 | 100 |

The Bothy is the only three-berth Barefoot and the only one without a separate bathroom;
its internal height is 1910 rather than 1870. The Lite is an all-electric model with no gas.

**Nothing is missing.** The deactivated Noir is absent from the site, which is consistent.

## Two figures to settle before building

1. **The Lite's MTPLM.** The catalogue says 1100/1200; its own page and the catalogue's own
   payload column both say 1000/1100. **Recommend 1000**, on the arithmetic.
2. **The Bothy's mass in running order.** The catalogue and `/barefoot-bothy/` both say
   **706**; `/vital-statistics/` says **720**. **Recommend 706** — two sources to one, and
   it is the figure that reconciles with the published payload.

## The upgrade option, and the settled rule

Every MTPLM is published as a pair — `750/850`, `1100/1200` — **specified at the time of
order**, as `/barefoot-bothy/` puts it: *"The MTPLM towing weight can be specified as 750 or
850kg (specify at time of order)"*. The requester's instruction, 8 October 2026, is to
**take the lower**, which is the base-vehicle rule and is what FMLV already holds (1100,
not 1200). The payload follows the same choice: 140 rather than 240.

The archived 2022 Classic is the counter-example worth knowing — it holds MTPLM **1200** and
payload **240**, the upgraded pair, which is presumably why it was superseded.

## Prices

`/barefoot-caravan-prices/` carries them, and they match FMLV: £39,950 for the Classic,
Forward and Eclipse, £40,500 for Country Living. It also prices the two new models and a
`Barefoot and Go` bundle at £41,500, which is an accessory package rather than a product.
All prices include VAT.

## What the adapter does

Four fetches of substance and six small ones. The catalogue is **rediscovered from the home
page** each run, because its folder carries a year (`uploads/2025/10/`) and will move.

| source | what it gives |
|---|---|
| catalogue p.10, specification block | berths, axles, MTPLM, MRO, published payload |
| catalogue p.10, dimension block | shipping, body, width, height, internal height |
| `/vital-statistics/` | **internal length**, the one figure the catalogue omits |
| `/barefoot-caravan-prices/` | the price, which the catalogue omits entirely |
| each model's own page | the habitation findings |

**Neither block hardcodes which model sits in which column.** The specification heading
introduces every column with the word `Barefoot`, so splitting on it gives the columns in
order. The dimension heading has no such marker, and is read by **punctuation**: models
within a column are separated by a comma or an ampersand, models in different columns by
nothing at all — `... Forward, Lite Bothy`. A seventh model is therefore picked up rather
than silently given its neighbour's weights.

Two guards sit under that. A row whose cell count disagrees with the heading's column count
is dropped rather than aligned by guesswork, and a heading that stops saying `Specification
Barefoot ...` raises rather than producing a plausible roster.

> The dimension heading **wraps mid-column**, and the first draft matched `[^\n]*` after the
> label — which ate `Classic, Eclipse, Country` and left the shared column reading
> `Forward, Lite`. The Classic came out with no dimensions at all.

## The Lite's MTPLM is corrected, and the correction expires by itself

`ERRATA` holds one entry and is keyed on the **wrong** value, so the day Barefoot fix the
catalogue it stops firing rather than overwriting a corrected figure. Everything downstream,
the self-check included, runs on the corrected pair, and the reviewer's provenance says what
was published and why it was not taken.

## Nothing is proposed for the awning, and nothing for the layout

Barefoot publish no awning length anywhere, so FMLV's own 3000mm stands untouched — the
pipeline shows it as a no-op change, which is the intended way an unfound figure is
surfaced. They publish **no layout drawing of any kind**, so the positional habitation
fields cannot be answered and no floorplan pointer is offered.

## The habitation findings are a genuine blank, which is itself the finding

The Bothy's page and the Lite's each carry a 33-line fittings list; the four older pages
carry prose and navigation alone. Reading those 66 lines settles **no habitation field**,
and the run says so in those words:

* Barefoot describe the washroom in their own language — *"Beautiful curved bathroom with
  basin and shower"*, *"Dometic cassette toilet"* — never the industry phrasing
  `habitation` reads.
* Both new models carry a **24L cool box**, not a fridge. `habitation` reads only the words
  fridge, refrigerator and refrigeration, so this reaches a reviewer as nothing said rather
  than as a fridge Barefoot never claimed.
* Neither new model has heating. The catalogue's `Heating` row is blank in both their
  columns and the Truma Combi 4E belongs to the other four.

Silence is not a negative, so nothing is asserted. The one thing the lists do settle is
`bed_types`, which is dropped for the reason every caravan adapter drops it: the copy names
the beds without saying which are built in and which are made up from the seating.

## Body type is tested, not asserted

Every Barefoot is under the 1250kg a micro may weigh — the 1100kg Classic included — so the
weight half of the rule passes on all six. The **naming** half is what decides it, and
Barefoot's word throughout is *"small caravan"*, never micro or mini. The test is applied
each run rather than its answer written in, because `wingamm_caravan.py` found the brand
that breaks the usual answer by asserting it.

## The first run — #147, 8 October 2026

```
baseline    4 products
scraped     6 products
classified  0 changed, 4 unchanged, 2 new, 0 disappeared
proposed    40 changes for review
            of which 4 are year bumps
            of which 4 are in-scope fields not found this run
verified    64 fields checked and unchanged
```

**Nothing changed on the four FMLV already holds** — every mass, every dimension and every
price came back identical, which is the strongest confirmation available that the right
document is being read. The two new products are the Bothy and the Lite, with the figures
the survey predicted:

| | berths | MTPLM | MRO | payload | headroom | price |
|---|---|---|---|---|---|---|
| **Bothy** | 3 | 750 | 706 | 44 | 1910 | £25,950 |
| **Lite** | 2 | **1000** | 900 | 100 | 1870 | £34,950 |

The four "in-scope fields not found" are the awning length on each matched product, as
expected. The four year bumps are the ordinary changeover-window proposal, not this
adapter's doing.
