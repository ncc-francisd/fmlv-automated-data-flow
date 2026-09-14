# Mobilvetta — site survey

Surveyed 14 September 2026. FMLV manufacturer id **12**, name **`Mobilvetta`**, display
name the same. **NCC supplier name `Marquis Leisure`**, shared with Panama. Motorhomes and
one campervan. Ten layouts offered in the UK; FMLV holds eight current rows.

## The source is Marquis, not the Italian parent

The requester described this as the two-source shape — Marquis defining the UK range and
`mobilvetta.it` defining the numbers. **It turns out not to be**: Marquis's own range pages
carry the full UK specification per layout, including the price.

```
K.YACHT 59   Weights and Dimensions
BERTHS 3   BELTS 4
OVERALL LENGTH 5990mm | 19'6''
OVERALL WIDTH (MIRRORS FOLDED) 2350mm | 7'7''
OVERALL HEIGHT (EXC TV AERIAL) 2950mm | 9'8''
MTPLM 4400kg
MAX USER PAYLOAD 1502kg
FIAT DUCATO 180BHP AUTOMATIC ENGINE  £109,995 OTR
```

So **`mobilvetta.it` is not needed at all**, and Mobilvetta joins Auto-Sleepers and Panama
as a single-source build. That also matters for the three brands still to come: if Marquis
publish the same template for Benimar, Elnagh and McLouis, none of them needs a European
parent either.

**The wording is nearly Auto-Sleepers' own** — `OVERALL WIDTH (MIRRORS FOLDED)`, `OVERALL
HEIGHT (EXC TV AERIAL)`, `MAX USER PAYLOAD`. Both are Trigano, and the family resemblance
is close enough that the readers should be written to be shareable.

### Why the parent site is the wrong roster

`mobilvetta.it/en/` lists **seven** ranges — K-Yacht Tekno Design, K-Yacht Tekno Line,
Karys, KEA I, KEA Kompakt, KEA P, Krosser. Marquis sell **four**. That is the requester's
warning made concrete: *"ranges in the parent website may comprise greater numbers of
models than offered in the UK"*, and it is the settled importer rule — Marquis decide what
exists here.

## The roster: five pages, ten layouts

**A page is a range, not a product.** Each carries one `Weights and Dimensions` block per
layout, so the parse has to split a page into several products — the first adapter in this
group that does.

| Marquis page | layouts |
| --- | --- |
| `mobilvetta-admiral-2026-campervan-range` | ADMIRAL K 6.3 |
| `mobilvetta-k-yacht-2026-motorhome-range` | K.YACHT 59, 86, 90, 95 |
| `mobilvetta-k-yacht-80-and-kea-80-2026-motorhome-range` | K.YACHT 80, KEA 80 |
| `mobilvetta-kea-2026-motorhome-range` | KEA 86, 90 |
| `mobilvetta-kea-kompakt-2026-motorhome-range` | KEA KOMPAKT 55 |

**One page carries two different ranges.** The `k-yacht-80-and-kea-80` page holds a K.YACHT
and a KEA, so the range cannot be taken from the page — it has to come from each block's
own heading.

## The figures, measured

| layout | berths | belts | length | width | height | MTPLM | payload | price |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ADMIRAL K 6.3 | 2 | 4 | 6360 | 2260 | 2650 | 3500 | 376 | £79,995 |
| K.YACHT 59 | 3 | 4 | 5990 | 2350 | 2950 | 4400 | 1502 | £109,995 |
| K.YACHT 86 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1222 | £119,995 |
| K.YACHT 90 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1252 | £119,995 |
| K.YACHT 95 | 4 | 4 | 7410 | 2350 | 2950 | 4400 | 1262 | £118,995 |
| K.YACHT 80 | 4 | 4 | 6990 | 2350 | 2850 | 3650 | 524 | £109,995 *(excluded)* |
| KEA 80 | 4 | 4 | 6990 | 2350 | 2850 | 3650 | 524 | £89,995 *(excluded)* |
| KEA 86 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1212 | £99,995 |
| KEA 90 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1242 | £99,995 |
| KEA KOMPAKT 55 | 4 | 4 | 6390 | 2150 | 2850 | 3500 | 612 | £79,995 |

**Every layout is priced**, and all eight of the kept ones match what FMLV displays. The
price column above was wrong in a first pass — see "The prices need the whole block".

**`BELTS` is the travel-seat count and `BERTHS` the sleeping count** — named unambiguously,
unlike Pilote where "Berth" meant a seat.

## There is no self-check, and that is the main risk

Marquis publish **MTPLM and MAX USER PAYLOAD but no MIRO**, so `mro_kilograms` has to be
derived and the identity `payload == MTPLM - MRO` becomes true by construction. Nothing on
the page corroborates any figure against any other.

Nor is there a naming convention to fall back on: `K.YACHT 59` is 5990 mm, which looks
promising, but 86 is 7470, 90 is 7470 and 95 is 7410. The numbers are layout codes, not
lengths.

**So this adapter has no arithmetic check at all** — the weakest position of the three
built in this group, and the one thing `docs/adapters/README.md` asks to be stated plainly
rather than glossed. The available mitigations are:

* **cross-check against `mobilvetta.it`**, which publishes its own figures per layout. They
  are European rather than UK specifications, so a disagreement would not automatically
  mean a parse error — but it would be a signal worth narrating;
* **rely on the roster check** — ten blocks across five pages, and a page that yields a
  different number of blocks than last time is the thing that would break first.

The second is cheap and is what a first build should do. The first is worth adding only if
the second proves insufficient.

## The 80s are excluded, by the requester's ruling

**Settled 14 September 2026.** FMLV's current Mobilvetta range is exactly **eight**
vehicles — the requester checked the live site — and neither 80 is among them:

```
KEA Kompakt 55  £79,995     ADMIRAL K 6.3  £79,995
KEA 86          £99,995     KEA 90         £99,995
K-YACHT 59     £109,995     K-YACHT 95    £118,995
K-YACHT 86     £119,995     K-YACHT 90    £119,995
```

His reasoning: *"They may well be sold as current stock. But remember, we're not looking
for current stock. We're looking at the range lineup."* FMLV holds the K.YACHT 80 and
KEA 80 only as **2025** rows, which `cli._is_current_model_year` drops from the baseline,
so collecting them would add two products to a range that is meant to have eight.

**So `mobilvetta-k-yacht-80-and-kea-80-2026-motorhome-range` is excluded from the roster**,
and the remaining four pages yield exactly the eight FMLV holds.

One caveat recorded honestly: that page does not *look* like a stock page. Its URL says
`2026-motorhome-range`, and it carries the same `Weights and Dimensions` blocks and OTR
prices (£109,995 and £89,995) as its four siblings. If Marquis ever promote the 80s into
the range proper, the fix is to delete one entry from `EXCLUDED_PAGES`.

## Avoid the used-stock pages

The requester's other warning: *"you have to avoid the used stock for sale pages and find
this one."* The roster is taken from the brand index at `/new-motorhomes/mobilvetta` and
restricted to `mobilvetta-*-2026-*-range` slugs, so a stock listing cannot reach it.

## The prices need the whole block, not a window

Every layout on the K-Yacht page is priced — £109,995, £119,995, £119,995, £118,995 — and
all four match what FMLV displays. A first extraction using a fixed 700-character window
after each heading lost two of them, because the price sits at the end of a block rather
than beside the dimensions.

**Three pages also carry a stray `£4,000`**, which is an offer rather than a vehicle price.
Only a figure followed by `OTR` is a price.

## Still unverified

* **Habitation.** Not examined. The Marquis pages carry marketing copy of the same shape as
  Auto-Sleepers', so the same reader may serve.
* **Floorplans.** Not examined.
* **The `/2` suffix** on ten of FMLV's rows — `59/2`, `80/2`, `86/2`. It appears on 2025
  rows only and nothing on either site explains it.
* **Whether `ADMIRAL` is still current at the factory.** Marquis sell it as a 2026
  campervan, but it is absent from `mobilvetta.it`'s range list entirely.
