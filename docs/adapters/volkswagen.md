# Volkswagen California — survey, 11 October 2026

**NCC id 259.** `fmlv_manufacturer` **`Volkswagen`**, display name `Volkswagen`, supplier
name **`Volkswagen Commercial`**. No adapter yet — this is the stage-1 checkpoint.

## Two names that look like mistakes and are not

**Three Volkswagen entries exist in the NCC list** — 67 `Volkswagen Transporters Ltd`, 188
`Volkswagen`, and 259 `Volkswagen`. The requester confirms **259**. 188 and 259 are
indistinguishable by name, so this is not derivable and must not be guessed at.

And every product's **base vehicle is `VW`** while the **manufacturer is `Volkswagen`**.
That is the deliberate naming protocol in `base.py` — one name per company per role, for
the filters — and it must not be "corrected".

## Scope: the California, and nothing else

The requester's instruction: the California is **the only true pre-built campervan VW
sell**. Ordinary vans are out of scope, and so is the *"build your own"* configurator the
site pushes hard — we record a pre-built model, at its **base variant**, not a configured
one.

## What FMLV holds — exactly eight, all live, all 2026

| id | range / model | £ | MTPLM | MRO | payload | berths / seats |
|---|---|---|---|---|---|---|
| 8753 | California / Beach | 63,481 | 2850 | 2383 | 467 | 4 / 5 |
| 8754 | California / Beach eHybrid | 71,545 | 2980 | 2611 | 369 | 2 / 4 |
| 8755 | California / Coast | 70,681 | 2850 | 2447 | 403 | 2 / 4 |
| 8756 | California / Coast eHybrid | 78,515 | 2980 | 2672 | 308 | 2 / 4 |
| 8757 | California / Ocean | 77,581 | 2850 | 2468 | 382 | 2 / 4 |
| 8758 | California / Ocean eHybrid | 85,415 | 2980 | 2693 | 287 | 2 / 4 |
| 8751 | Grand California / 600 | 85,393 | 3500 | 3098 | 402 | 2 / 4 |
| 8752 | Grand California / 680 | 88,180 | 3880 | 3273 | 607 | 2 / 4 |

All six Californias are 5173 × 1941 × 1972 and `campervan_elevating_roof`; both Grand
Californias are `campervan_high_top`.

## Four documents, all UK editions in sterling

Everything lives under `/idhub/content/dam/onehub_nfz/importers/gb/downloads/`, and all four
are linked from **`/en/download-a-brochure.html`**, so the URLs should be rediscovered each
run rather than written in.

| document | what it holds |
|---|---|
| `california-brochure.pdf` | **p26** weights per variant and engine, **p25** dimensions |
| `california-pl.pdf` | **p3** model prices — and the seat count |
| `grand_california-brochure.pdf` | **p24** weights, **p25-26** dimensions and beds, **p29** prices |

**There is no separate Grand California price guide.** Its prices are inside its brochure,
which is the kind of near-miss worth writing down: the price-guide folder has eleven files
and none of them is the Grand California.

## The brochure is demonstrably where FMLV's figures came from

Page 26, verbatim:

```
Engine/transmission        Gross vehicle weight, kg   Unladen weight¹, kg   Payload², kg
California Beach Camper
150PS 2.0 TDI 7-Speed DSG            2,850                   2,383              467
245PS eHybrid 1.5 TSI 6-Speed DSG    2,980                   2,611              369
California Coast
150PS 2.0 TDI 7-Speed DSG            2,850                   2,447              403
```

and page 25:

```
H3 Vehicle height – mm   1,972
W1 Width – mm            1,941
                         5,173
W2 Width including mirrors – mm   2,252
```

Every one of those is FMLV's figure to the kilogram and the millimetre. **`Width including
mirrors` is published and is not what FMLV holds**, which is the settled rule working.

## The self-check is published — and the two brochures define the mass differently

The California's own footnote: *"Payload = gross vehicle weight minus unladen weight"*, and
all three columns are printed. That is a real arithmetic check, and it holds exactly:
2,850 − 2,383 = 467.

**The Grand California does not work the same way, and the difference is the driver.**

| | the California | the Grand California |
|---|---|---|
| the column is called | Unladen weight | Kerb weight |
| its footnote says | *"includes approximately 90% fuel load **and 75kg for driver**"* | *"includes 90% fuel load with **no driver or passengers**"* |
| so the column is | the mass in running order | **not** the mass in running order |

Its printed payload is **consistently 75kg less** than gross weight minus kerb weight, on
every one of its eight rows:

| | GVW | kerb | GVW − kerb | printed payload |
|---|---|---|---|---|
| 600 3.5T | 3,500 | 3,021 | 479 | **404** |
| 600 3.88T | 3,880 | 3,024 | 856 | **781** |
| 680 3.88T | 3,880 | 3,196 | 684 | **609** |

So **MRO = kerb + 75**, which gives 3,096 and 3,271 against FMLV's 3,098 and 3,273 — two
kilograms apart, i.e. a slightly older brochure. Recording the kerb weight as the mass in
running order would put a different quantity in that column.

## The base variant, and what it excludes

Per the requester, the base variant is the **lowest-engine row for each named model**:

* **take** 150PS 2.0 TDI for Beach, Coast and Ocean, and 245PS eHybrid for the hybrids;
* **leave** the 204PS 2.0 TSI on Coast and Ocean, the 4MOTION and the 3.88T upgrade on the
  Grand California 600, and the **Dune** trims entirely.

The 680 is only sold at 3.88T, which is why FMLV holds 3880 for it.

## The price is the column the website headlines

The price list prints five columns. The one to take is **`Total RRP inc. OTR inc. VAT`** —
the California page shows **£64,432** for the Beach, and that is exactly that column:

```
California Beach Camper 150PS 2.0 TDI 7-Speed DSG   M1 SP Camper   5
  £52,480.00   £10,496.00   £62,976.00   £53,765.00   £64,432.00
```

The price list also states the **seat count** per model — `5` for the Beach, `4` for
everything else — which agrees with FMLV.

**Every price FMLV holds is stale**, and not all in the same direction: the Beach is
£63,481 against £64,432, but the Grand California 600 is £85,393 against **£84,208**, which
has come *down*.

## Expected count: eight

Six Californias and two Grand Californias, which is exactly what FMLV holds — so the first
run should match all eight and propose no new products.

## What still needs care

**Berths.** FMLV holds 4 for the Beach and 2 for everything else, and neither brochure
states a berth count as a figure. The California's is in prose — the Beach's folding rear
seats *"creates two additional sleeping spaces"*, and *"eHybrid Beach models have 2
individual seats in the rear"* — while the Grand California gives `Number of beds: 2, +2`
with the over-cab bed optional. The lower figure of that is 2, which is what FMLV holds.
Reading berths reliably from prose is the one field this source does not make easy.
