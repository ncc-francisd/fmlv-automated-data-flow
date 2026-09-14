# Auto-Sleepers — site survey

Surveyed 14 September 2026. FMLV manufacturer id **212**, name **`Auto-Sleepers Limited`**,
display name **`Auto-Sleepers`**, NCC supplier name **`Auto-Sleepers`**. Motorhomes and
campervans, no caravans. Eighteen layouts on the site; FMLV holds 19 live 2026 rows.

## What the requester brought to the survey

* **Six Trigano brands are being added together** — Benimar (236), Elnagh (233), Panama
  (221), Mobilvetta (12), McLouis (35) and this one. Chausson (53) is a seventh and is
  already built.
* **Auto-Sleepers is the odd one out, and that is why it goes first.** The other five are
  sold through Marquis Leisure, who define the UK range while the European parent site
  defines the numbers. Auto-Sleepers *"runs pretty much like a UK brand"* — its own UK
  site defines both, and it sells through many dealers.
* *"All models on the website are current in the UK."* So the site is the roster, with no
  importer subset to reconcile against a larger European one.
* *"The technical specifications are very clear — when you click on more information it
  gives you all of the weight information and the dimensions and the floor plans."*
  Correct, and it understates it: see below.

## The source: 18 model pages, in plain HTML

`auto-sleepers.com/<body-type>/<base-vehicle>/<model>`, and **`sitemap.xml` is a complete,
accurate roster** — 325 URLs, of which exactly 18 match the model-page shape. No
JavaScript: everything below came out of a plain `Fetcher.fetch`.

The path carries two facts before the page is even read:

| segment | values | what it gives |
| --- | --- | --- |
| body type | `campervans`, `motorhomes` | the coarse body type |
| base vehicle | `fiat`, `fiat-active`, `mercedes` | `base_vehicle_manufacturer` |

| | Fiat | Fiat Active | Mercedes |
| --- | --- | --- | --- |
| campervans | Fairford, Kingham, Symbol, Symbol Plus, Warwick Duo, Warwick XL | FG 635, FL 635, KB 635 | M-Star |
| motorhomes | Broadway EB, Broadway EK TB LP, Broadway EL, Broadway FB, Nuevo EK Plus | — | Bourton, Burford, Burford Duo |

## Every field FMLV wants is published, and labelled unambiguously

This is the best-documented source surveyed so far. Each page states its figures **twice** —
a summary strip and a detailed table — and the detailed table names each measurement
properly rather than leaving it to be inferred:

```
Designated Passenger Seats                              2
Berths (Sleeping positions)                             2
Overall Length                                       6445mm
Overall Width (mirrors folded)                       2260mm
Overall Width (mirrors extended)                     2660mm
Overall Height Standard Roof (excl TV aerial)        2865mm
Maximum Technically Permissible Laden Mass (a) (est) 3500kg
Mass in Running Order (b) (est)                      3043kg
Maximum User Payload (c) (c=a-b) (est)                457kg
```

— the real Bourton, verbatim.

Three things follow that usually cost a survey a day each:

* **The width is already the right one.** `Overall Width (mirrors folded)` is exactly
  FMLV's definition, and the mirrors-extended figure sits beside it *labelled*, so there
  is no risk of taking the wrong one. Contrast Pilote, where the same two figures are
  published and only one is named.
* **The roof options are named too.** `Overall Height Standard Roof` and `Overall Height
  Pop Top Roof` appear separately, which is what `body_type` needs to distinguish a high
  top from one with an elevating roof — a distinction FMLV already makes on three of these
  products.
* **The base vehicle is stated in the page and in the URL**, so it can be cross-checked
  rather than inferred.

### Prices are published, as on-the-road

`Prices from £69,749 OTR`. That is the manufacturer's own headline website price, which is
the settled rule for `rrp_pounds`, so **no emailed document is needed for any field** —
the first brand in a while where that is true.

## The self-check is printed, labelled and exact

`Maximum User Payload (c) (c=a-b)`. Auto-Sleepers publish the arithmetic *and* its
derivation, so `payload == MTPLM - MRO` is a genuine check on the parse rather than an
identity true by construction:

| | MTPLM | MRO | payload | a − b |
| --- | --- | --- | --- | --- |
| Bourton | 3500 | 3043 | 457 | **457** ✓ |
| FG 635 | 3500 | 2937 | 563 | **563** ✓ |
| Fairford | 3500 | 3112 | — | — |

The **summary strip repeats all three**, so there is a second check for free: a figure read
from the wrong row disagrees with its own twin higher up the page.

**Every weight is marked `(est)`.** Worth recording in the provenance so a reviewer knows
the manufacturer has hedged them, but they are the only figures published and they are
what FMLV already holds.

## What the first run should find

Eighteen site pages against nineteen live FMLV rows, and it reconciles exactly:

| | what | why |
| --- | --- | --- |
| **new** | `Broadway EK TB LP` | a page with no FMLV row |
| **gone** | `Air` | Ford-based, and the site has no `/campervans/ford/` at all |
| **gone** | `Fairford Plus` | the site has `fairford` and no `fairford-plus`, though it does have `symbol-plus` |

19 − 2 + 1 = 18. That the arithmetic closes is the roster check `docs/adapters/README.md`
asks for.

### All 18 pass the printed self-check, and the field diff is coherent

Every page was fetched and its eight summary figures read. **`MTPLM − MIRO == payload` on
18 of 18**, exactly, with no rounding slack. Against FMLV's 2026 rows the comparison gives
**47 field changes over 17 matched products**, and its shape is what makes it believable:

| field | changes | |
| --- | --- | --- |
| `mh_passenger_seats_inc_driver` | **0** | 18 of 18 agree |
| `mh_width_mm` | **0** | 18 of 18 agree |
| `mtplm_kilograms` | **0** | 18 of 18 agree |
| `mh_height_mm` | **17** | see below — systematic |
| `mro_kilograms` / `mh_payload_kilograms` | 13 each | small, and they move together |
| `berths` | 1 | KB 635, 4 → 2 |
| `mh_length_mm` | 1 | M-Star, 6967 → 7100 |

Seats, width and MTPLM agreeing on every product is strong corroboration that the parse is
reading the right rows. The MRO and payload moves are 10-60 kg and always offset each
other exactly, which is a manufacturer revising figures rather than a parse slipping.

### The height question: does FMLV's figure include the TV aerial?

**Every one of the 17 changes its height**, in two tight groups:

| | FMLV | site | difference |
| --- | --- | --- | --- |
| Mercedes and coachbuilt Fiat | 2900 | **2865** | 35 mm |
| Fiat campervans | 2640 | **2615** | 25 mm |

That is too systematic to be a revision. The site's label is the clue: **`Overall Height
Standard Roof (excl TV aerial)`**. So FMLV's figure very likely *includes* an aerial that
the site's excludes.

**This is not decided here**, because it turns on what FMLV's height column means and
whether the aerial is standard equipment. If it is standard, FMLV's larger figure is right
and the adapter should not propose 17 reductions; if it is an option, the settled
base-vehicle rule says take the site's. The Active vans' pop-top figure (2815) is a third
number again and is not what either holds.

### One thing to settle before building: 635 or 365?

The three Active campervans are **`FG 635`, `FL 635`, `KB 635`** on the site — in the page
heading *and* in the URL slug — against **`FG365`, `FL365`, `KB365`** in FMLV. The digits
are transposed, and it affects all three products.

Two site sources agree with each other, which usually settles it. But a model code is an
identity, so this is put to the requester rather than decided here: if the adapter emits
`FG 635` against FMLV's `FG365`, the identity tokeniser scores them **0.000** — codes that
disagree force zero — so all three would arrive as new beside three disappearances.

## Identity

`manufacturer_range` and `model` need care, because FMLV uses two conventions:

| FMLV range | FMLV model | shape |
| --- | --- | --- |
| `Air` | `Air` | a singleton repeats itself |
| `Bourton` | `Bourton` | ditto |
| `Broadway` | `EB`, `EL`, `FB` | a family splits into variants |
| `Warwick` | `Duo`, `XL` | ditto |
| `FG365 Active` | `FG365` | the range carries the suffix, the model does not |

So the range is not derivable from the page heading alone, and the mapping has to be built
against the export rather than guessed.

## Still unverified

* **The 635/365 question above**, which blocks the three Active products.
* **Whether 2027 has landed.** Every live FMLV row is 2026 and the site does not say a year
  anywhere obvious. Worth confirming before a run, since a rollover mid-survey would
  change the roster.
* **Floorplans.** The requester says they are on the page behind *more information*; the
  layout images are present (`Day Layout`, `Night Layout`, `Night Option Layout`) but their
  URLs have not yet been extracted.
* **Habitation.** Not yet examined. The pages carry an `Essential Habitation` section, which
  is promising, but it has not been read.
