# Barefoot Caravans — survey, 8 October 2026

**NCC id 30.** `fmlv_manufacturer` **`Barefoot Caravans`**, display name **`Barefoot`**,
supplier name `Barefoot Caravans`. Caravans only, built at Blockley in the Cotswolds.
No adapter yet — this is the stage-1 checkpoint.

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
