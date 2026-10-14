# Airstream — assessment, 14 October 2026

**NCC id 274.** `fmlv_manufacturer` **`Airstream`** (one word), display name `Airstream`,
and the NCC **supplier name is `Lowdhams`** — the UK importer, not the marque. The two
disagree by design, which is worth knowing before anyone "corrects" one to the other.

Caravans only.

## Lowdhams are the importer, which decides what we take from where

The settled rule: an exclusive UK importer decides **what exists and what it costs**, and
the factory decides **every number**. Lowdhams is both the importer and a dealer, so the
division matters here more than usual — the range and the price are theirs to state, the
weights are not.

## What FMLV holds — four, all live, all 2026

| id | range / model | £ | MTPLM | MRO | shipping | body | W | H |
|---|---|---|---|---|---|---|---|---|
| 8863 | International / 25 IB | 109,950 | 3500 | 2475 | 8290 | 6970 | 2490 | 2840 |
| 8861 | International / 534 | 97,950 | 1900 | 1580 | 6860 | 5470 | 2280 | 2700 |
| 8862 | International / 684 | 107,450 | 2920 | 2165 | 8290 | 6970 | 2490 | 2750 |
| 8860 | World Traveller / 22RB | 79,995 | 2000 | 1700 | 7210 | 5840 | 2290 | 2740 |

## The roster and the prices are readable, and two of them are wrong

`/browse/new-airstream-caravans` is **server-rendered** — no JavaScript — with a card per
product giving the name, the price and the berths:

```
Airstream International 684      Only £109,950    4 Berth
Airstream World Traveller 22RB   Only £72,995     4 Berth
Airstream International 534      Only £97,950     4 Berth
```

Against FMLV, **two of the three disagree**, and not in the same direction:

| | FMLV | Lowdhams |
|---|---|---|
| International 684 | 107,450 | **109,950** |
| World Traveller 22RB | 79,995 | **72,995** |
| International 534 | 97,950 | 97,950 ✓ |

## One brochure, covering one range of the two

`AIRSTREAM-WORLD-TRAVELER-BROCHURE-2025-EN.pdf` — the filename says 2025 and the content
says 2026. Page 10 is a real specification block:

```
World Traveler 22RB
Up to 4 SLEEPING CAPACITY   1 AXLE   6 M BODY LENGTH   2.3 M WIDTH
Typical hitch weight  Maximum hitch weight  Kerb weight (MRO):  GVWR (MTPLM):  Payload
100-140 kg            150 kg                1,700 kg            2,000 kg       up to 300 kg
```

**It carries a published self-check and it reconciles**: 2,000 − 1,700 = 300, exactly the
payload printed beside it, and both masses match FMLV to the kilogram.

**Its dimensions are too coarse to use**: `6 M` body length and `2.3 M` width, against
FMLV's 5840mm and 2290mm.

## The gap closed: Airstream publish the Internationals after all

A first pass concluded FMLV's three Internationals had **no discoverable source** for their
masses or dimensions. That was wrong, and the document that disproves it is Airstream's
own: `2024-aeu-owners-manual-rev01.pdf`, the European owner's manual, whose page 7 is a
full specification table for exactly the three models in question.

```
                                      534      684     25IB
MASS IN RUNNING ORDER               1580kg   2165kg  2475kg
ACTUAL MASS                         1800kg   2500kg  2800kg
MTPLM Lower limit                   1830kg   2500kg  2800kg
MTPLM Upper limit                   1900kg   2920kg  3500kg
Shipping length                     686cm    829cm   829cm
External height, with AC fitted     270cm    275cm   284cm
External width                      228cm    249cm   249cm
External length (body shell)        547cm    697cm   697cm
Internal length                     530cm    674cm   674cm
Internal height, max                198cm    201cm   201cm
```

**Every figure in it is already in FMLV, exactly.** The MROs to the kilogram; the shipping
lengths as 6860, 8290 and 8290; the heights as 2700, 2750 and 2840; the widths as 2280,
2490 and 2490; the internal lengths and the headrooms. FMLV's MTPLMs — 1900, 2920 and
3500 — are the **upper** limits.

So the gap was never in the data. It was in the search: the first pass looked for a
*brochure*, and the specification is in a *manual*.

### It is not worth fetching, and nothing would be proposed from it

The manual sits on a content-hashed Storyblok CDN URL, reachable only through a search
engine — `airstream.com/owners/manuals/` is an Algolia-driven index that serves no links to
a plain fetch. There is no rediscovery path worth depending on.

That costs nothing, because **there is nothing to propose**: FMLV already matches it. The
table is written into the adapter as `EUROPEAN_SPECIFICATION`, not to be recorded but to be
*defended with* — it is what every stock-page mass is tested against.

## Why no mass or dimension is taken from Lowdhams

### The MTPLM on a stock page is a plate, not a specification

The decisive finding, and now a cross-manufacturer rule in [`README.md`](README.md). A
caravan may be plated anywhere inside its published band, so the figure on a specific unit
describes **that unit**:

| | Lowdhams' plate | Airstream's band | FMLV |
|---|---|---|---|
| 534 | 1830kg | 1830–1900 | **1900** |
| 684 | 2400kg | 2500–2920 | **2920** |
| 22RB | 2000kg | 2000 (one figure) | **2000** ✓ |
| 25 IB | 2750kg | 2800–3500 | **3500** |

The 534 is plated at its band's floor; the 684 sits **below** its band. Recorded, that
second one would have cut 520kg off a live product while looking entirely plausible doing
it. `plating_verdict` places every stock-page MTPLM against the band and narrates which it
is, so the refusal is reasoned and visible.

The one that matches is the World Traveller — the only model whose page carries a
placeholder registration (`SHOWROOM301`) rather than a real one.

### `Overall Height` is the interior height, mislabelled

Not merely imprecise but wrong. The World Traveller brochure, page 11:

```
Exterior height  2.74 m
Interior height  2 m
```

FMLV holds **2740** for the 22RB — the exterior height — and Lowdhams' `Overall Height`
reads **2.00m**. The same shape appears on the 534 (1.99m) and the 25 IB (1.99m). Only the
684's 2.69m looks like a genuine exterior figure, so the field is **inconsistent as well as
mislabelled**.

### The lengths and widths merely confirm

They agree — exactly on the 22RB — but the site gives two decimals of a metre where FMLV
holds millimetres, so taking `6.80m` would round 6860 down to 6800.

## A first pass read the stock pages as sold units and was wrong

Worth recording, because the mistake is reusable. The HTML carries both `In Stock Now` and
*"Sorry, this one has hit the road. This model has sold"*; the second is **dormant template
markup that is not displayed**. Presence in the DOM is not the same as being shown, and a
text search cannot tell them apart.

Three of the four pages do carry a real registration — `ST575111`, `TA578259`, `RA572231` —
so these are specific vehicles. But their `Range`, `Model`, `Berths` and `Axles` are
properties of the model, and their price is the importer's. The division is the usual one:
**what exists and what it costs** is Lowdhams', **every number** is the factory's.

---

# Built — 14 October 2026

`src/adapters/airstream.py`. Five fetches: the browse page, then the four vehicle pages it
links. Plain HTML throughout — no browser, no PDF.

## What it maintains, and what it refuses

| takes | leaves to FMLV |
|---|---|
| the roster, from the one page that lists it | every mass — a unit's plate is not the model's |
| the price, from the card's `Only £…` | every dimension — less precise, and the height is the wrong measurement |
| berths, range and model, from the structured spec block | the heating (see below) |
| **`Axles` → `twin_axle`**, which no Airstream document states | |
| the body type, `rigid` | |

## Run #173 — the first one

```
baseline    4 products
scraped     3 products
classified  2 changed, 1 unchanged, 0 new, 1 disappeared
proposed    28 changes, of which 3 are year bumps
verified    17 fields checked and unchanged
```

Four of those 28 are real, and they are both prices:

| | FMLV held | Lowdhams | |
|---|---|---|---|
| International 684 | 107,450 | **109,950** | up |
| World Traveller 22RB | 79,995 | **72,995** | down |
| International 534 | 97,950 | 97,950 | confirmed |

The remaining 21 are the masses and dimensions, proposed as **no-op changes** so the figure
is preserved rather than blanked — the settled behaviour for a field an adapter did not
find. `twin_axle` verified unchanged on all three, which independently confirms FMLV.

## The 25 IB leaves the range

Lowdhams list it only as a **used 2024 unit at £97,500**, and the requester confirmed on
14 October 2026 that it is discontinued. The adapter drops it on `Condition: Used` — the
manufacturer-independent test — rather than on its `used-` slug, so it is reported as
disappeared with a note to **deactivate, never archive**.

## `Full central heating` is deliberately left unresolved

The feature lists say it, and FMLV holds wet central heating for all four, so the temptation
is to teach `habitation` that the phrase means wet. **The fixtures say otherwise.** Every
other `central heating` line in this repo carries `Alde` or `radiator` with it — and one
reads `Truma diesel central heating`, which is warm air. The bare phrase does not settle
the kind, so the run narrates it and FMLV's own value stands.

## Two things that would have gone wrong quietly

* **The price is not on the vehicle page**, only on the browse card, and the card also
  prints `£1,229 / Monthly`. That figure is *smaller* than the price and in some cards comes
  *first*, so neither "the lowest" nor "the first" picks correctly. The reading is anchored
  on the word `Only`.
* **The specification block is a flat run of alternating labels and values.** A label whose
  value is missing would pair with the next label and shift everything after it, so only a
  value that is not itself a label is kept.

## Still to ask Lowdhams

1. **Is the 684 really plated at 2400kg?** That is below Airstream's own published band of
   2500–2920. Either that unit is plated unusually or the model has changed since the
   European manual.
2. **Is there a newer European manual than the 2024 edition?**
