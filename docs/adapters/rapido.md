# Rapido — survey, 27 October 2026

**Status: surveyed, adapter not yet written.** Registry row added (`manufacturer_id` 129,
`fmlv_manufacturer` "Rapido").

Rapido is a French manufacturer (Groupe Rapido, Mayenne) building campervans, low-profile
coachbuilts and A-class motorhomes. No caravans — the `touring-caravans` sheet of the FMLV
export is empty, and the registry row is `categories=motorhome`.

Sister brands in the same group, each on its own site and **out of scope here**: Itineo,
Dreamer, Campéréve, Fleurette (see `fleurette-florium.md`).

## Where the data is

Three sources, and the adapter needs two of them.

| What | Where | Gives |
|---|---|---|
| **2027 Technical Guide** | Calaméo flipbook, 32pp | masses, dimensions, berths, seats, garage, heating, fridge, bed sizes |
| **Comparator** | `comparateur-camping-cars.php` | roster, length, berths, belts, heating, bed and kitchen type |
| 2027 Catalogue | Calaméo flipbook, 88pp | editorial only — no specs, no prices |

The model pages (`motorhome_<body>_<serie>_<model>.chtml`) carry equipment prose and a
floorplan image but **no weights or dimensions at all**, so they are not a spec source.

### The Technical Guide is a Calaméo flipbook, and that is fine

<https://www.calameo.com/read/0076927327ec66b0c8590?authid=guYHFJ2c2o8e> — "Rapido-gt-2027-GB",
32 pages, published 2026-05-07, linked from `catalogue-camping-cars-rapido.php` as
"TECHNICAL GUIDE 2027" beside the thumbnail `dist/images/catalogues/gt-2027.jpg`.

Three things to know before writing the parser:

- **The pages are SVG with real text, not scans.** 45 private-use glyphs in 109,000
  characters, all of them in prose; none in the numeric tables.
- **The assets are token-signed.** `https://www.calameo.com/download/<id>` is 403, and so is
  a bare fetch of `p1.svgz`. The viewer mints a short-lived per-file token. Loading the
  reader in `BrowserFetcher` and capturing responses matching `\.svgz` yields every page;
  visiting pages 1, 6, 11, 16, 21, 26, 30, 32 pulls all 32, because the viewer preloads
  neighbours. **This is why the registry says `needs_javascript=yes`** — the site itself is
  plain HTML and needs nothing.
- **Rediscover the Calaméo URL from the catalogues page each run.** The book code is opaque
  and will change for 2028. Find the `<a>` whose sibling `<h2>` says `TECHNICAL GUIDE`.

### Splitting the cells: parse `dx`, not `x`

Each table row is a **single** `<text>` element whose content is the label and every value
run together — `Payload (kg)615580`. The `x` of the element is the label's x, so x-position
tells you nothing about where the columns are, and splitting "615580" by digit count is a
guess.

The element carries a `dx` attribute: one advance per character. Within a word they are
0 to -0.6; **at a cell boundary they jump by several hundred**:

```xml
<text ... dx="0 -0.48 0 -0.19 0 0 0 0 0 0 -0.48 0 536.08 -0.46 0 473.63">Payload (kg)615580</text>
```

Index 12 is `536.08` and index 15 is `473.63`, so the cells are `Payload (kg)`, `615`, `580`.
A threshold of 5.0 separates them cleanly on every page. **Do not guess at the split** — the
README's warning under "A cardinality failure is not proof that cells are missing" applies,
and here the structure makes guessing unnecessary.

A parsed row whose cell count does not equal the page's model count must be dropped with an
`on_progress` warning, not realigned.

### The self-check: MIRO + payload = GVW

Rapido publish all three. **It holds for all 29 models**, including the two chassis weights:

- C03 — 2885 + 615 = 3500
- i66M ALDE — 3360 + 1140 = 4500
- i166M — 3740 + 760 = 4500

Any model failing this is dropped, not proposed. The guide prints the GVW as a chassis
*choice* (`LIGHT: 3,5 T / 3,65 T`, `HEAVY: 4,25 T*`), so take the base figure — the one the
arithmetic lands on — per the README's "One column, so record the base vehicle".

### The comparator is a free second opinion

`comparateur-camping-cars.php` holds all 29 models as cards whose attributes are already
machine-readable:

```html
<a href="motorhome_low-profile_serie-c_c50.chtml" class="cell-modele"
   data-chauffage="TRUMA Combi" data-couchages="2+1"
   data-long="659" data-ceintures="2+2"
   data-couchage="Central bed" data-repas="5"
   data-cuisine="Straight kitchen">
```

Its lengths and heating types agree with the Technical Guide on every model, which is worth
using as a cross-check. It is the better roster source — the homepage nav lists the same
models but files several under two different body-type path segments (866F appears as both
`a-class` and `low-profile`), so **the URL's body-type segment is not evidence**.

`data-couchage` lists the bed options *available*, not the one fitted — 686F reads
"Central bed ; XL central bed ; Face-to-face bench seats". `data-cuisine` is a kitchen
*shape* (Straight / L-shaped / V-shaped / Curved), not a position, so it does not map to
`rear_kitchen` / `side_kitchen` / `corner_kitchen`.

## Body type is stated, not inferred

Rapido name the body type in the Technical Guide's own section headers, one per series:

| Series | Guide's words | FMLV body type |
|---|---|---|
| Vans | CAMPERVANS WITH FIAT CHASSIS | campervan high top (2630–2920mm) |
| Serie C (C03…C86) | COMPACT **LOW-PROFILE** MODELS | coach built low profile |
| Serie C (C55i, C66i, C86i) | COMPACT **A-CLASS** MODELS | A class |
| Serie 6F | **LOW-PROFILE** MODELS WITH SPECIAL FIAT CHASSIS | coach built low profile |
| Serie 8F | **A-CLASS** MODELS WITH FIAT CHASSIS | A class |
| Serie 80dF | **A-CLASS** MODELS WITH FIAT AL-KO CHASSIS | A class |
| Serie Distinction | **A-CLASS** MODELS WITH MERCEDES AL-KO CHASSIS | A class |

So there is nothing to estimate here, and the height must not be used to decide — see the
Auto-Trail note in `auto-trail.md`.

**This makes FMLV's 696F wrong.** It is recorded as `coach_built_over_cab_bed`; Rapido file
it under LOW-PROFILE with the rest of Serie 6F. The 6F models have a *drop-down* bed,
offered as an option (`Berths (with drop-down bed option)`), which is not an over-cab bed.

## Base vehicle

`Fiat` for everything except Serie Distinction, which is `Mercedes` on an AL-KO chassis.
Both spellings already match what FMLV holds (53 Fiat, 10 Mercedes) and the abbreviated
house style.

## Price: there isn't one, and that is the finding

**Rapido publish no price, anywhere.** Not in the 2027 Technical Guide, not in the 88-page
2027 Catalogue, not on any UK page. The only money in either document is the aside that
"All mentioned options are included in the vehicle price for Right Hand Drive models".

There is also **no exclusive UK importer** to set one. Rapido run the UK site themselves and
sell direct to independent dealers — Brownhills, Dicksons of Perth, Oakwell, Wokingham,
Cara, Destination, Harbour Creek. Their asking prices for the same vehicle disagree by
thousands (C66 quoted at £83,470 by one and £87,995 by another), so they are dealer prices,
not a manufacturer guide price, and must not be recorded.

**The adapter must therefore emit no price at all**, so that the figures FMLV already holds
are preserved and surfaced as a no-op rather than inherited silently.

**Outstanding ask: a UK price list from Rapido.** Until then the 2026 prices stand.

## What the 2027 guide says

All 29 reconcile. Width is "excluding wing mirrors", which is the figure FMLV wants.

| model | range | L mm | W mm | H mm | MIRO | payload | MTPLM | berths | seats | base |
|---|---|---|---|---|---|---|---|---|---|---|
| V55 | Vans | 5990 | 2050 | 2630 | 3045 | 455 | 3500 | 3 | 4 | Fiat |
| V62 | Vans | 6360 | 2050 | 2630 | 3025 | 475 | 3500 | 3 | 4 | Fiat |
| V64 | Vans | 6360 | 2050 | 2630 | 3025 | 475 | 3500 | 3 | 4 | Fiat |
| V65 XL | Vans | 6360 | 2050 | 2920 | 3050 | 450 | 3500 | 4 | 4 | Fiat |
| V68 | Vans | 6360 | 2050 | 2630 | 3025 | 475 | 3500 | 3 | 4 | Fiat |
| C03 | Serie C | 6190 | 2170 | 2790 | 2885 | 615 | 3500 | 3 | 4 | Fiat |
| C50 | Serie C | 6590 | 2170 | 2790 | 2920 | 580 | 3500 | 3 | 4 | Fiat |
| C55 | Serie C | 6720 | 2170 | 2790 | 2925 | 575 | 3500 | 3 | 4 | Fiat |
| C66 | Serie C | 6990 | 2170 | 2790 | 3005 | 495 | 3500 | 3 | 4 | Fiat |
| C86 | Serie C | 6990 | 2170 | 2790 | 2995 | 505 | 3500 | 3 | 4 | Fiat |
| C55i | Serie C | 6720 | 2190 | 2790 | 2960 | 540 | 3500 | 4 | 4 | Fiat |
| C66i | Serie C | 6990 | 2190 | 2790 | 3040 | 460 | 3500 | 4 | 4 | Fiat |
| C86i | Serie C | 6990 | 2190 | 2790 | 3030 | 470 | 3500 | 4 | 4 | Fiat |
| 606F | Serie 6F | 6690 | 2350 | 2940 | 2980 | 520 | 3500 | 4 | 4 | Fiat |
| 666F | Serie 6F | 7490 | 2350 | 2940 | 3065 | 435 | 3500 | 3 | 4 | Fiat |
| 686F | Serie 6F | 7200 | 2350 | 2940 | 3035 | 465 | 3500 | 3 | 4 | Fiat |
| 696F | Serie 6F | 7490 | 2350 | 2940 | 3055 | 445 | 3500 | 3 | 4 | Fiat |
| 850F | Serie 8F | 6990 | 2350 | 2940 | 3080 | 420 | 3500 | 4 | 4 | Fiat |
| 866F | Serie 8F | 7490 | 2350 | 2940 | 3155 | 345 | 3500 | 4 | 4 | Fiat |
| 896F | Serie 8F | 7490 | 2350 | 2940 | 3140 | 360 | 3500 | 4 | 4 | Fiat |
| 8066dF | Serie 80dF | 7490 | 2350 | 2940 | 3140 | 360 | 3500 | 4 | 4 | Fiat |
| 8086dF | Serie 80dF | 7200 | 2350 | 2940 | 3100 | 400 | 3500 | 4 | 4 | Fiat |
| 8096dF | Serie 80dF | 7490 | 2350 | 2940 | 3140 | 360 | 3500 | 4 | 4 | Fiat |
| i66M TRUMA | Serie Distinction | 7540 | 2350 | 2950 | 3245 | 255 | 3500 | 4 | 3 | Mercedes |
| i66M ALDE | Serie Distinction | 7540 | 2350 | 2950 | 3360 | 1140 | 4500 | 4 | 4 | Mercedes |
| i96M TRUMA | Serie Distinction | 7540 | 2350 | 2950 | 3230 | 270 | 3500 | 4 | 3 | Mercedes |
| i96M ALDE | Serie Distinction | 7540 | 2350 | 2950 | 3350 | 1150 | 4500 | 4 | 4 | Mercedes |
| i166M | Serie Distinction | 8150 | 2350 | 2990 | 3740 | 760 | 4500 | 4 | 4 | Mercedes |
| i196M | Serie Distinction | 8150 | 2350 | 2990 | 3700 | 800 | 4500 | 4 | 4 | Mercedes |

### Reading berths and seats

Both print as `a+b`, and **the FMLV figure is the sum** — confirmed against the five FMLV
rows that are already correct (850F 2+2 = 4, V62 2+1 = 3, i166M 2+2 = 4).

Two traps:

- **Take the standard line, not the optioned one.** 666F prints `Berths 2+1` and
  `Berths (with drop-down bed option) 2+2`. Record 3 — the extra berth needs an option, per
  the lower-figure rule. The rows `Berths (with no cab bed option)` go the other way: they
  describe deleting standard equipment, so the standard `Berths` line still stands.
- **Seats come from "Registered (driving) seats", not "Seats with seatbelts".** Every model
  shows `Seats with seatbelts 2+2`, but the Distinction's 3.5-tonne variants are registered
  for three, footnoted *"GVW 3500 kg = 3 registered seats without towing capability /
  2 registered seats with towing capability; GVW 3880 / 4500 kg = 4 registered seats"*. FMLV
  already holds i66M TRUMA at 3, so this is the column FMLV has been using. An asterisk on
  8F/80dF seat counts refers to the heavy-chassis option, not to the seats.

## Habitation findings

The technical-data pages carry, per model and cleanly parseable: rear garage (width, length,
height, heated, access aperture both sides), heating type, fridge type and volume, fresh and
waste water, and bed sizes including drop-down and cab beds.

Heating maps straightforwardly — `TRUMA Combi` and `WEBASTO` are blown air, `ALDE 3030+` is
wet central. Note `TRUMA Combi 6 INET X / ALDE` on the 80dF, where ALDE is an option: take
the standard. The existing `_WARM_AIR` combi-oven guard in `habitation.py` already handles
the word "combi" safely.

The **equipment and comfort** pages (4, 5, 10, 11, 14, 15, 18, 19, 22, 23, 26, 27) hold the
oven, microwave and washroom marks as ●/○/- grids, but there the label and the marks sit on
separate lines and the mark counts do not always equal the model count. That is the genuine
cardinality risk in this source: parse it carefully or skip it with a narrated warning —
never realign by assumption.

## How the 2027 site compares with FMLV

FMLV holds 63 Rapido rows, of which **27 are live** (not archived, active). The site lists
**29**. The difference is not 2 — it is 4 new against 2 gone, one of which is a rename.

### Four new, and Rapido say so

The catalogue's foreword names them: *"The range is expanding with brand new models: the C66
and C66i … and the brand new V64 campervan"*. All three carry a `NEW` flag in the Technical
Guide and a `nouveaute 2027` badge on the site.

| new | range | why |
|---|---|---|
| C66 | Serie C | genuinely new for 2027 |
| C66i | Serie C | genuinely new for 2027 |
| V64 | Vans | genuinely new for 2027 |
| **i96M TRUMA** | Serie Distinction | **not new — this is FMLV's `I96M` renamed** |

**`I96M` (product 7109) is `i96M TRUMA`.** Rapido now suffix every Distinction with its
heating, and FMLV already holds `i66M TRUMA` under the new convention. The mass agrees —
MTPLM 3500 both, payload 290 → 270, length 7540. Rename 7109 rather than creating a second
product; this is the `relisted-product-looks-new` / `name-drift-is-not-a-new-model` case
again, and the adapter should carry it in `RENAMED_MODELS`.

Similarly, FMLV's `8066dF ULTIMATE` and `8096dF ULTIMATE` are the site's plain `8066dF` and
`8096dF` — the ULTIMATE special edition has been replaced for 2027 by **OPTIMUM LINE**, which
is a trim (upholstery, keyless pack, exterior logo) marked on the same spec column, *not* a
separate layout. Do not create Optimum Line products.

### One genuinely gone

**854F** (product 7099, Serie 8F, 6700mm, £86,300) is absent from the 2027 roster. Serie 8F
is now 850F / 866F / 896F. Propose a deactivation, not an archive.

### The existing FMLV data is substantially wrong

This matters more than the roster. **22 of the 27 live rows carry a price in
`mro_kilograms`** — C50 reads 78790, i66M ALDE reads 135890 — and the same 22 rows carry
placeholder `berths` = 2 and `seats` = 2, including 7.5m A-class motorhomes.

Only the five most recently added rows (8831–8835: V62, 850F, i66M TRUMA, i166M, i196M) are
right; they match the 2027 guide almost exactly, so somebody has already been working from
this document.

The true MRO is recoverable without the guide — MTPLM minus payload — and that arithmetic
agrees with the archived 2022 rows for every affected model (C50: 3500 − 610 = 2890, and the
2022 C50 row holds 2890). The first run will therefore propose a large number of changes;
that is a correction, not drift. Expect roughly:

- 22 × `mro_kilograms` (price → mass)
- 22 × `berths`, 22 × `seats` (placeholder 2 → real figure)
- ~27 × `mh_height_mm` (every height is 30–190mm out; V68 is recorded at 2880 but is 2630,
  having apparently inherited V65 XL's roof)
- `width` 2170 → 2190 on C55i and C86i
- `mtplm` 3650 → 4500 on i66M ALDE and 3500 → 4500 on i96M ALDE — the ALDE Distinctions are
  4.5-tonne for 2027
- `type_coach_built_over_cab_bed` → `type_coach_built_low_profile` on 696F

### Range names need settling

FMLV uses eight range strings for six ranges, and none match Rapido's own:

| FMLV | count | Rapido |
|---|---|---|
| COMPACT / COMPACT i | 4 / 2 | Serie C |
| SERIE 6F / SERIE 8F / SERIE 80dF | 4 / 4 / 3 | Serie 6F / 8F / 80dF |
| SERIE DISTINCTION | 6 | Serie Distinction |
| **SERIE VANS** / **VAN** | 1 / 3 | Vans |

`SERIE VANS` and `VAN` are the same range spelt two ways, and `COMPACT` / `COMPACT i` splits
one Rapido range in two on body type — the Wingamm Brownie defect the README describes. Per
"Let the FMLV export decide the range and model strings", the adapter should not propose a
`manufacturer_range` change unless we decide to tidy these, and that is Francis's call.

## Open questions for Rapido

1. **A UK price list** — nothing is published and the dealers disagree.
2. Whether **OPTIMUM LINE** is orderable on every model or only some; the guide marks it on
   Campervans, Serie C, 6F and 80dF.
