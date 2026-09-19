# Globecar (id 83)

Surveyed 2026-09-19. **Campervans only** — eleven layouts across three ranges, all high top.

- Source: <https://globecar.co.uk/range/>
- NCC supplier name: `Globecar`
- `fmlv_manufacturer`: `Globecar`

Globecar is a Pössl-group brand; globecar.co.uk is the UK and Ireland importer's own site
("© 2019-2024 – Globecar Motorhomes UK & Ireland"), which under the settled rule is what
defines the range.

## What the requester supplied

Given on 2026-09-19, and all of it confirmed:

- Same name in the manufacturer and supplier lists — id 83, `Globecar` for both.
- Source <https://globecar.co.uk/range/>.
- All high top campervans. FMLV holds `type_campervan_high_top` on all 24 baseline rows.
- "FMLV has the range as 2027 already but data hasn't been updated."
- "All the specs are found by clicking the floorplans" — confirmed: the `/range/` page is a
  grid of floorplan tiles, and each links a per-layout page carrying the whole
  specification inline. There is no deeper layer and nothing needs a click to reveal it.

One correction to the last point, and it is the main finding: **the 2027 weights in FMLV
are already right.** What is actually missing is a whole range — see below.

## Where the data lives

Plain static WordPress HTML, no JavaScript. No PDF: `/brochure/` renders no document link
at all, and no `.pdf` is referenced from any layout page.

Each layout page carries the figures twice, in two blocks that do not always agree:

- a **header card** — `SLEEPS`, `SEATS`, `MPLM`, `LENGTH`, `WIDTH`, `HEIGHT`;
- a **`TECHNICAL DATA`** section, in `Vehicle Dimensions` / `On Board Technology` /
  `Living Area` / `Weight & Load` groups.

```
Weight & Load
MPLM                     3500kg
Mass in running order    2680kg
Payload                   820kg
```

Note the site's label is **`MPLM`**, not MTPLM.

## The roster

Eleven layouts, listed on `/range/` under the heading **"2026 Range"**:

| range | layouts |
|---|---|
| Summit | 540, 600, 600L, 640 |
| Summit Prime | 540, 600, 640 |
| Summit Shine | 540, 600, 600L, 640 |

**Two slugs are misspelt** and must be hardcoded as published: `sumit-prime-540` and
`sumit-shine-640`, both missing the second `m`. The other nine are `summit-…`.

## The self-check

`Payload == MPLM − Mass in running order`, and it holds on **11 of 11**. Globecar is one of
the few sources that publishes all three, so the parse can be checked without a second
document.

There is a second, independent corroboration: the `TECHNICAL DATA` figures agree with
FMLV's own 2027 rows on MTPLM, MRO **and** payload for **7 of 7** matched products. Two
separately-sourced agreements on the same numbers is as good as this gets.

## Traps

**The header card disagrees with `TECHNICAL DATA`, and the header is the wrong one.** It
differs on 2 of 11:

| layout | header `MPLM` | `TECHNICAL DATA` `MPLM` | FMLV holds |
|---|---|---|---|
| Summit 540 | 3300 | **3500** | *(not in FMLV)* |
| Summit Shine 540 | 3000 | **3300** | **3300** |

Three things settle it for the technical block: only its figure reconciles with the
published payload (3500 − 2680 = 820, the stated figure; 3300 would give 620), it agrees
with FMLV on all seven matched products, and the header's 3000 kg on the Shine 540 is not a
chassis Globecar offers at all. **Read `Weight & Load`; never the header card.**

The header also inflates the counts, folding options into the headline: it says `SEATS 4`
where the technical block says `3/3 (+1 optional)`, and `SLEEPS 2 (+3 opt.)` where the
technical block says `2 (+1 optional)`.

**Seats are ambiguous on seven layouts and cannot be read.** The `Seats/Seatbelts` cell
takes two forms:

| form | layouts | reading |
|---|---|---|
| `3/3 (+1 optional)` | Summit 540, 600, 640 | 3 belts |
| `4/4 (+1 optional)` | Summit 600L | 4 belts |
| `3/3 (+1 optional)/4 (+1 optional)` | **all 7 Prime and Shine** | **3 or 4** |

The double form is two configurations in one cell, and FMLV proves it is genuinely both:
against that identical string it holds **4** for Summit Prime 540 and 600 and **3** for the
other five. Nothing on the page says which layout gets which. So seats are read only where
the cell states one configuration — which is all four plain Summits, the ones that need a
value — and left alone on the seven that already have one.

**Berths read `2 (+N optional)`**, so the base is 2 throughout, per the settled rule. The
optional third berth is a factory-order extra seat, which the page says in words.

**No price is published anywhere.** Not on a layout page, not on `/range/`, not in the
configurator — the pound sign appears zero times across the site. FMLV holds prices
(£62,995–£69,995 on the 2027 rows), sourced elsewhere. Nothing is proposed for price and
no POA is invented.

**The site says "2026 Range"** where FMLV has these as 2027. Worth watching at the model
year rollover, but it changes nothing we record.

## The baseline, and what the first run will say

The export holds 24 rows; `_is_current_model_year` keeps ten — three 2026 and seven 2027.

| range | model | year | in FMLV | on the site |
|---|---|---|---|---|
| Elegance | R Roadscout, Globescout, Campscout | 2026 | yes | **no** |
| Summit Prime | 540, 600, 640 | 2027 | yes | yes |
| Summit Shine | 540, 600, 600L, 640 | 2027 | yes | yes |
| Summit | 540, 600, 600L, 640 | — | **no** | yes |

So the run should report **7 matched, 4 new, 3 disappeared** — and the new and the
disappeared are mostly the same vehicles. Checked against the disappearance notices before
calling anything new, as the rename rule requires, the three Elegance layouts line up with
three of the four Summits by exterior length, exactly:

| Elegance (2026) | length | Summit (site) | length |
|---|---|---|---|
| R Roadscout | 5413 | Summit 540 | 5413 |
| Globescout | 5998 | Summit 600 | 5998 |
| Campscout | 6358 | Summit 640 | 6358 |

Their masses have moved a little with the model year (Roadscout MRO 2720 → Summit 540
2680; Globescout 2820 → 2835; Campscout 2970 → 2960), which is a respec, not a different
vehicle. **Only Summit 600L is genuinely a new layout.**

**A wrinkle for the requester.** FMLV also holds 2022 rows under range `H - Line` with
models `Summit 540`, `Summit 600` and `Summit 640` — the same names, in the old
range-and-model arrangement. The year filter drops them, so they are not in the baseline
and the adapter cannot match them. Creating the four Summits as new products will therefore
sit alongside those older rows rather than replace them.

## Field mapping

All from `TECHNICAL DATA`.

| site | FMLV | Summit 540 |
|---|---|---|
| `Length:` | `mh_length_mm` | 5413 |
| `Width:` | `mh_width_mm` | 2050 |
| `Height:` | `mh_height_mm` | 2580 |
| `MPLM` | `mtplm_kilograms` | 3500 |
| `Mass in running order` | `mro_kilograms` | 2680 |
| `Payload` | `mh_payload_kilograms` | 820 |
| `Sleeping places` | `berths` | 2 |
| `Seats/Seatbelts` | `mh_passenger_seats_inc_driver` | 3 |

`Interior height` and `Wheelbase` are published and have no FMLV column. Body type is
`campervan_high_top` on all eleven: the requester states it, FMLV holds it on all 24 rows,
and every published height is 2580 mm, comfortably over the settled 2300 mm threshold.

## First run — #106, 2026-09-19

11 scraped against 10 baseline: **7 unchanged, 0 changed, 4 new, 3 disappeared**, exactly
as the survey predicted. 66 proposals, 70 fields verified unchanged, 8 habitation findings.

**Nothing changed on the seven matched products.** The 2027 rows agree with the site on
every figure read — MTPLM, MRO, payload, dimensions and berths — which is the survey's
main finding confirmed: the weights were already right.

The four new products, hand-checked against their pages:

| product | length | MPLM | MRO | payload | berths | belts |
|---|---|---|---|---|---|---|
| Summit 540 | 5413 | 3500 | 2680 | 820 | 2 | 3 |
| Summit 600 | 5998 | 3500 | 2835 | 665 | 2 | 3 |
| Summit 600L | 5998 | 3500 | 2835 | 665 | 2 | 4 |
| Summit 640 | 6358 | 3500 | 2960 | 540 | 2 | 3 |

The three disappearances are the 2026 `Elegance` rows, and they are the rename described
above rather than a withdrawal. Each raises a notice rather than a change, so nothing is
proposed for them; retiring them is a manual step in Nova.

Habitation findings on all eleven: `blown_air_heating` from `Heating: Truma Combi 4`, and
`fridge_freezer` from `Refrigerator in L (capacity/including freezer): ca. 100/8`. Stated
for a person to enter, not proposed.

The no-op "in scope but not found" rows are `rrp_pounds` and `base_vehicle_manufacturer`,
neither of which this site publishes.

## Fetches per run

Twelve: the range index to confirm the roster, and eleven layout pages.
