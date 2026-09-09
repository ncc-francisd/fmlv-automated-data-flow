# Hymer — site survey

Surveyed and built 9 September 2026. FMLV manufacturer id **86**, name **`HYMER`** in
capitals, display name `Hymer`, NCC supplier name `Hymer`. The Erwin Hymer Group's own
brand and the last of them; motorhomes and campervans, no caravans.

The biggest EHG roster this project handles: **25 layouts across 11 range pages**, against
**42** products FMLV still holds.

## What the requester brought to the survey

* The site is *"almost a carbon copy of the other EHG brands"* — correct.
* The configurator has a **standard equipment** tab worth reading for the fridge and
  similar. Not needed in the end: the model pages publish both the fridge and the heating
  in their own specification tables.
* On the roster: *"I don't know if the range is shrinking. EHG do seem to be reducing
  ranges on a few of their brands and even stopping production of some like Buccaneer and
  Xplore."* The diff says it is shrinking — 23 disappearances.

## The source: the GB range pages

`/gb/en/` is a real market edition and differs from `/de/en/`, so it is the one read. Same
shape as Dethleffs, Carado and the Eriba Car: `has-columns--1+` specification tables, a
layout heading above each block, floorplans. One real block, from `Exsis-t 474`:

```
Price                                                    £96,290
Standard chassis                                         Fiat Ducato
Length / Width / Height (cm)                             659 / 222 / 279
Mass in running order (-/+ 5%) (kg)*                     2824 (2683 - 2965)*
Manufacturer-specified mass for optional equipment (kg)* 342
Technically permissible maximum laden mass (kg)*         3500
Permitted number of seats (including driver) *           4
Overall clearance storage- / garage door W x H (cm)      99 x 108
Berths                                                   2 - 3 (○)
Fridge volume (freezer compartment) (l)                  142
Standard heating                                         Gas warm air, 6 kW
```

`(○)` marks a paid upgrade throughout, and the standard figure is the first.

### The roster is a stated list, not the sitemap

The GB sitemap's `/motorhomes/` section is mostly **category** pages —
`2-berth-motorhomes`, `winterized-motorhomes`, `luxury-motorhomes` — and the site's shared
navigation names ranges this market has no page for at all. A crawl would find both too
much and too little, so `DEFAULT_RANGES` is the roster and `collect` narrates a range page
that stops producing layouts.

| range page | layouts |
| --- | --- |
| B-ML I | 780, 880 |
| B-ML T | 780 |
| B-MC I | 580, 600, 680 |
| B-MC T | 580, 600, 680 |
| Exsis-t | 474, 580 |
| GT-S | 600, 685 |
| ML-T | 570, 580 |
| Venture S | S |
| Grand Canyon S | 600, 700 |
| Redwood | 600, 601 |
| Yellowstone | 540, 600, 601, 602, 640 |

## Attributing a specification to a layout is the whole problem

Two things make the join awkward, and `parse_layouts` exists for them:

* **A layout's name appears twice** — as a teaser near the top of the page and again
  immediately above its specification. Anchoring on the *first* occurrence gives a region
  with no tables in it.
* **A layout's specification then appears twice** inside that region, identically — the
  same quirk the Eriba Car has.

So each specification is found by its `Mass in running order` row, given to the nearest
heading above it, the distinct owners are taken in order, and each layout's region runs
from its own heading to the next owner's. Duplicate tables inside a region simply re-state
the same values and `setdefault` keeps the first. Nothing has to be deduplicated and no
count has to be guessed.

The heading level is no help: `h2` on the B-ML page, `h4` on the Exsis-t page.

## Three smaller traps, all real

**A layout need not have a number.** `Hymer Venture S`. The first sweep of this site used
a pattern requiring digits and found **24 layouts instead of 25**.

**`&nbsp;` lives inside the labels** — `Price&nbsp;&nbsp;` and `Mass in running order (-/+
5%)&nbsp;(kg)*` — so a lookup on the printed label misses without unescaping. No sibling
EHG site does this.

**A drawing's filename carries the layout code as a token, not a suffix.** All three of
these are real, on three different pages:

```
hymer-exsis-t-474.jpg
hymer-redwood-600-hoch.png
hymer-b-ml-i-780_bis_2026.png
```

A rule anchored to the end of the stem finds only the first. Splitting on non-alphanumeric
runs finds all three, and still refuses `6001` for `600`. As on Carado, a drawing is told
from a photograph by its **resizer preset** (`wls-floorplan`), not its name.

## FMLV's identity conventions differ per range

Checked against the real export. The site's own label is never what FMLV holds:

| site | FMLV range | FMLV model |
| --- | --- | --- |
| `Hymer B-ML I 780` | `B-Class MasterLine` | `I 780` |
| `Hymer B-ML T 780` | `B-Class MasterLine` | `T 780` |
| `Hymer B-MC I 600` | `B-Class ModernComfort I` | `I600` |
| `Hymer B-MC T 680` | `B-Class ModernComfort T` | `T680` |
| `Hymer Exsis-t 474` | `Exsis-T` | `474` |
| `Hymer Venture S` | `Venture` | `S` |

Note the spacing is inconsistent — `I 780` against `I600` — which is why the template is
per range rather than a rule.

## The self-check

The printed ±5% band against the stated running order. Weak, because the band is a function
of the mass, and the same limitation as Eriba's and Laika's. The stronger structural check
is that a layout's specification appears twice and the two must agree.

## The first diff — 9 September 2026

**25 collected, no blank spec field, 18 carrying a floorplan.**

| | |
| --- | --- |
| matched | 19 |
| new | 6 — B-MC I 580 and 680, B-MC T 580, Yellowstone 540, 600, 602 |
| disappeared | 23 |

19 price changes, 12 masses and payloads, 7 heights, 2 seat counts, 2 body types, and one
rename (`Exsis-T / 580 Pure` → `580`).

### The identity the matcher could not make

FMLV holds a product under range **`Hymer`**, model `I680`. It is a misfiled
`B-Class ModernComfort I / I680` — same model string, same figures — but the two range
names share nothing, so it scores below the threshold and arrives as **a new product *and*
a disappearance rather than a rename**. Accepting both would create a duplicate and orphan
the old row. Treat it as a rename by hand.

### Seven layouts get no drawing, all of them the site's doing

* `B-MC I 580` and `GT-S 600` have a specification and no plan. The GT-S page publishes a
  `hymer-gt-s-585.png` matching **no** layout it lists, so its drawings and its
  specifications have drifted apart.
* The Yellowstone page shows five layouts but only `601` has a numbered plan. Its other
  drawings — `ayers-rock`, `grand-canyon`, `yosemite` — belong to **sibling models the page
  displays but gives no specification to**, and those are three of the products FMLV still
  holds. Worth knowing when reading the disappearances: they are not obviously dead, just
  undocumented here.

Better no drawing than a sibling's — the [`laika.md`](laika.md) lesson.

### Two things to put to a reviewer before accepting

* **Both Grand Canyon S products change body type**, from campervan high top with an
  elevating roof to plain high top. The page publishes `Roof type: Sleeping roof (○)` and
  the circle marks a paid upgrade, so by the settled rule an optional rising roof does not
  change what the vehicle is. FMLV disagrees today.
* **`B-Class MasterLine I 790` and `I 890` disappear.** The page publishes only 780 and 880.

## A second opinion, and where it was wrong

The requester obtained an independent estimate. It agreed on the **total** — 25 to 30 UK
layouts across 11 core ranges, against the measured 25 across 11 pages — and that agreement
is worth something. Its per-range detail was not reliable, and is recorded so nobody takes
it as a roster:

| it said | the pages publish |
| --- | --- |
| B-MC I and B-MC T: 2 layouts each | **3** each — 580, 600, 680 |
| MasterLine I: 4 (780, 790, 880, 890) | **2** — 780, 880 |
| GT-S: 1 "with modular lounge options" | **2** — 600, 685 |
| Yosemite and Ayers Rock campervans | **no page**; they appear only as drawings on the Yellowstone page |

Where an estimate and the pages disagree, the pages were read directly and win — the same
rule as website-over-PDF.

## Still unverified

* **Whether the 23 disappearances are all real withdrawals.** Blackline, T-Class, Exsis-I
  and the Xperience and CrossTrail editions have no GB page, but three of them do have
  drawings on the Yellowstone page, so "no page" is not quite "not sold".
* **The configurator's standard-equipment tab**, which was not needed but may carry a
  microwave mention the model pages lack.
* **Model year changeover.** Not established for this brand.
