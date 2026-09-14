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
| K.YACHT 86 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1222 | — |
| K.YACHT 90 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1252 | £119,995 |
| K.YACHT 95 | 4 | 4 | 7410 | 2350 | 2950 | 4400 | 1262 | £118,995 |
| K.YACHT 80 | 4 | 4 | 6990 | 2350 | 2850 | 3650 | 524 | — |
| KEA 80 | 4 | 4 | 6990 | 2350 | 2850 | 3650 | 524 | — |
| KEA 86 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1212 | — |
| KEA 90 | 4 | 4 | 7470 | 2350 | 2950 | 4400 | 1242 | £99,995 |
| KEA KOMPAKT 55 | 4 | 4 | 6390 | 2150 | 2850 | 3500 | 612 | £79,995 |

**Four of the ten carry no price.** They are still listed and specified, so this is a gap in
Marquis's page rather than a discontinued layout — `rrp_pounds` stays unset on those and
FMLV keeps whatever it holds.

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

## The question the survey cannot answer: the 80s

**K.YACHT 80 and KEA 80 will arrive as new products, and FMLV already holds them.**

FMLV's 18 live Mobilvetta rows split 8 × 2026 and 10 × 2025, and the 80s are among the
2025 group:

| FMLV row | year |
| --- | --- |
| `K-YACHT TEKNO LINE` / `80`, `80/2` | **2025** |
| `KEA` / `80`, `80/2` | **2025** |

`cli._is_current_model_year` keeps only the current calendar year and the next, so every
2025 row is dropped from the baseline before matching. The site offers both 80s as current
2026 stock, so each would be collected, match nothing, and be proposed as new — beside
rows that already exist.

That is a data question rather than an adapter one. Either those four rows want their year
moving to 2026, or the 80s are genuinely new listings and the old rows should be archived.

## Still unverified

* **Habitation.** Not examined. The Marquis pages carry marketing copy of the same shape as
  Auto-Sleepers', so the same reader may serve.
* **Floorplans.** Not examined.
* **The `/2` suffix** on ten of FMLV's rows — `59/2`, `80/2`, `86/2`. It appears on 2025
  rows only and nothing on either site explains it.
* **Whether `ADMIRAL` is still current at the factory.** Marquis sell it as a 2026
  campervan, but it is absent from `mobilvetta.it`'s range list entirely.
