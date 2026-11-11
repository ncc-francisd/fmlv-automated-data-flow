# Dreamer — survey and adapter, 11 November 2026

**NCC id 127**, `Dreamer`. **Adapter shipped**, `src/adapters/dreamer.py`, 19 products.
The first pass of this survey stopped for the wrong reason; see "What the second pass
changed".

Part of **Groupe Rapido** (Mayenne, France), alongside Rapido, ITINEO, Campéréve and
Fleurette. Panel-van conversions on Fiat, Peugeot and Ford. No caravans.

| | Dreamer |
|---|---|
| JavaScript needed | No — everything is plain HTML |
| FMLV holds | **16 products**, ranges `Fun` and `Select`, all priced |
| Site shows | **19 models** — 8 FUN, 11 Select |
| Per-model specs | **On each model page**, all 19, uniform |
| Masses | **Nowhere for the current lineup** — see below |
| Price | **In FMLV already**, £53,400–£81,700 on all sixteen |

## What the second pass changed

The first pass read only `fourgon-caracteristiques-techniques_dreamer.php`, concluded the
columns could not be matched to products, and recorded that **"Dreamer's model pages carry
no figures at all."** That last statement is **wrong**, and it was the reason the survey
stopped. Francis's screenshots of the two range pages prompted a second look.

Two things were missed:

1. **The table is the FUN range only.** Its own heading is `<h1>Specifications Range FUN`.
   The eleven Select models have no specification table anywhere on the site.
2. **Every model page publishes a block of eight figures.** They are in
   `newpicto-icon-section` / `newpicto-text-section` div pairs — the Select pages use the
   same classes with a `-select` suffix — each labelled by an SVG class
   (`svg__dimension_ext`, `svg__places`, `svg__lit`, `svg__frigo`, `svg__chauffage`,
   `svg__eaux-propres`, `svg__goutte`).

## What the site actually publishes, per model

Confirmed by fetching all 19 model pages and both range pages:

| field | where | example |
|---|---|---|
| model name, range | range page tile and the page's own `<h1>` | `D68 SELECT` |
| overall length | range page tile | `6.36 m` |
| overall height, width | `svg__dimension_ext` | `(H) 2.63 M (W) 2.05 m` |
| garage H/L/W | `svg__dimension_int` | `(H) 670 MM (L) 1030/660 MM (W) 1330 MM` |
| travel seats | `svg__places` | `4 people` |
| berths, options split out | `svg__lit` | `2 (O : 2 + 1)` |
| fridge | `svg__frigo` | `146 L` |
| heater | `svg__chauffage` | `TRUMA COMBI 4 DIESEL CP PLUS` |
| fresh water | `svg__eaux-propres` | `10/110 L(d)` |
| waste water | `svg__goutte` | `85 L` |

All nineteen carry all of these, bar `CAP LAND SELECT`, which omits the garage.

**No mass and no price appear on a model page**, and no chassis.

## The table describes last season's vans

The table's columns *are* identifiable — the visible text is only half of each heading, the
rest being badge SVGs (`svg__up`, `svg__addict`, `svg__exclusive`):

`D42 · D43 UP · D43 UP ADDICT · D53 · D55 EXCLUSIVE · D55 UP · D55 UP ADDICT · D60 · CAMPER FIVE`

But that is **not the range Dreamer now sell**. Every height has moved by 4 cm:

| | table | model page now |
|---|---|---|
| fixed-roof models | `2,59 (a)` | `2.63` |
| pop-top (`UP`) models | `2,72 (a)` | `2.76` |
| Camper Five | `2,88` | `2.92` |

The table also carries `ADDICT` and `EXCLUSIVE` trims that the site no longer lists, uses a
`D42` / `D53` / `D60` numbering replaced by `D43` / `D55` / `D68`, and has **no CAMPER
SPORT column at all** — a current FUN model at 5.98 m.

**Do not read masses out of it.** They belong to vehicles that are 40 mm shorter in the
roof than the ones being sold, and attaching them to today's models would be the invisible
error this project has guards against elsewhere.

Note also that the `c-table-modele__*` CSS class names are **positional leftovers, not
identity** — `dreamer-select-equipements.php` reuses `__d53` and `__d55ex` for columns
headed `SELECT RANGE FINISH SAPHIR` and `CAP LAND SELECT / CITY CAMP SELECT`. Read the cell
contents, never the class.

## Why there is no alignment risk left

The reason the first pass stopped was the risk of attaching one van's figures to another
across a wide table with no way to check. **Reading per-model pages removes that risk
entirely** — each page is reached by its own URL and states its own name in `<h1>`, so the
check is an identity check (does the `<h1>` match the model this URL was supposed to be?),
exactly as `itineo._check_alignment` does.

What is lost with the table is the **arithmetic** self-check (`MIRO + payload == GVW`), and
that only because there are no masses to check.

## The Calaméo route is closed

Dreamer's catalogue page (`fourgon-dreamer-doc.php`) mentions one, and the request form
offers a *"Technical guide"* checkbox, but the three Calaméo URLs on that page sit **inside
an HTML comment**, as legacy `FR/DE` and `FR/IT` editions. **The publisher account also
differs** — Dreamer's book codes begin `0003556`, Rapido's and Itineo's `00769273` — so
nothing about `rapido.py` transfers. The live route emails the document on request, which a
run cannot walk through.

`fourgon-caracteristiques-techniques_dreamer-select.php` does not exist (16-byte response).

## The current 19 against FMLV's 16

Site, with the lengths off the range tiles:

| range | models |
|---|---|
| FUN | D43 *(new)* 5.41 · D43 UP 5.41 · D55 5.99 · D55 UP 5.99 · D68 6.36 · D68 UP *(new)* 6.36 · CAMPER SPORT 5.98 · CAMPER FIVE 6.36 |
| Select | Cap Easy *(new)* 5.48 · D43 5.41 · D55 5.99 · City Camp 5.05 · D64 *(new)* 6.36 · D68 6.36 · Cap Land 5.45 · LIFT VAN *(new)* 6.36 · LIFT VAN UP *(new)* 6.36 · Camper Van XL 6.36 · Family Van 5.99 |

FMLV, from the export downloaded 11 November 2026 (16 live products, all year 2027):

| range | models |
|---|---|
| `Fun` | D43 UP, D55 UP, D55, CAMPER SPORT, D68 |
| `Select` | CAP LAND, D55, D62, D68, FAMILY, CAMPER VAN XL, D68 UP, LIVING VAN, D43, CITY CAMP, CITY CAMP HYBRIDE |

Several look like **renames rather than new models**, and should be matched on mass before
anyone believes otherwise:

* FMLV `LIVING VAN` against the site's `LIFT VAN` — one letter apart, same range.
* FMLV `D62` against the site's `D64 Select`.
* FMLV `FAMILY` against the site's `FAMILY VAN Select` — resolved: the matcher paired them on run #232.
* FMLV lists `D68 UP` under `Select`; the site shows it under FUN.

`CITY CAMP HYBRIDE` is in FMLV and not on the site at all.

`D55` and `D68` each appear in **both** ranges, so the range is part of the identity and
cannot be derived from the model code.

Base vehicles in FMLV: Fiat, except CAP LAND, CITY CAMP and CITY CAMP HYBRIDE, which are
Ford. **The site publishes no chassis per model**, so this cannot currently be refreshed.

## What the adapter emits, and what it refuses to

| emitted | not emitted |
|---|---|
| `manufacturer_range` (`Fun` / `Select`), `model` | `mro_kilograms`, `mtplm_kilograms`, `mh_payload_kilograms` |
| `mh_length_mm`, `mh_height_mm`, `mh_width_mm` | `rrp_pounds` |
| `berths`, `mh_passenger_seats_inc_driver` | `base_vehicle_manufacturer` |
| `body_type`, `automatic_available` | |
| habitation findings (`heating`, `refrigeration`, `bed_types`, `shower_toilet_separated`) | |

The three absences are **left unset rather than emitted empty**, so FMLV's existing values
survive a run untouched. The pipeline flags each as a no-op change for a person to confirm
— the "not found this run" rows in the review.

## What the first run found (#232, 11 November 2026)

19 scraped against 16 baseline: **5 new, 2 disappeared, 12 changed**.

The single most useful result is a **systematic +40 mm correction to every height**:

```
Fun    D55            2590 -> 2630      Select D43            2590 -> 2630
Fun    D43 UP         2720 -> 2760      Select D68            2590 -> 2630
Fun    CAMPER SPORT   2880 -> 2920      Select CAMPER VAN XL  2880 -> 2920
```

That is the superseded table's own figures sitting in FMLV, corrected to what Dreamer now
publish — and it is independent confirmation that **FMLV's Dreamer data was taken from
that table**. The same shift explains the berth corrections (`3 -> 2` on the Select D55 and
D68, `5 -> 4` on Cap Land and Camper Van XL): the old figures counted the optional dinette
bed, and the model pages now split the options out as `2 (O : 2 + 1)`.

## Two things the adapter deliberately will not decide

**City Camp Select's roof.** The settled rule is that silence means the elevating roof is
an option, and the first run duly proposed downgrading it from
`campervan_elevating_roof` to a plain `campervan`. That proposal was wrong and has been
suppressed: City Camp publishes **four berths in a van 2,040 mm tall**, and its twin the
Cap Land Select — same height, same chassis, same four berths — says *"4 adult berths with
pop-up roof"* in so many words. `ROOF_UNSTATED` names it, no `body_type` is emitted, and
FMLV's own value stands.

**Which product is which, in the Select 6,360 mm group.** FMLV holds `D68 UP` (4 berths,
2,720 mm, 3,165 kg) and `LIVING VAN` (4 berths, 2,880 mm, 3,105 kg). The site now holds
`LIFT VAN` (2 berths, 2,630 mm) and `LIFT VAN UP` (4 berths, 2,760 mm), and has moved a
`D68 UP` into **FUN**, badged new. The automatic matcher reads the FUN `D68 UP` as FMLV's
Select one moved between ranges, which makes `LIFT VAN UP` new. **The heights suggest
otherwise** — 2,720 → 2,760 is the same +40 mm every other model shifts by. It cannot be
settled without a mass, so `AMBIGUOUS_IDENTITY` states it every run instead.

## Three traps, each of which cost a run or a test

1. **A `New` badge hides the length.** The tile is the only place Dreamer publish an
   overall length, and a model badged `New` carries an extra span *inside* `class="dim"`
   and before the figure. Stopping at the first `</span>` lost the length on six of the
   nineteen — silently, because the other thirteen still worked.
2. **The site is `iso-8859-1` and means it.** Cap Easy Select's heater is
   `WEBASTO 2500\xa0W FUEL HEATING` with a real non-breaking space: one byte, not valid
   UTF-8. Read with `errors="replace"` it becomes U+FFFD, which then cannot be written to
   a Windows console, and the run dies on one page's typography. `dreamer._read` tries
   strict UTF-8 and falls back to cp1252.
3. **A cruise-control caveat reads as an automatic being ruled out.** The Select equipment
   list contains `Adaptive cruise control - manual transmission only`, which
   `gearbox.automatic_available_from` correctly reads as an explicit *No* — and it is
   nothing of the kind, because the line directly below offers lane-keeping *"automatic
   transmission only"*. `_transmission_lines` keeps only lines that name a make.

## What is still open

1. **A current weights table** — MIRO, MTPLM/GVW and payload for the 19 models now sold.
   A question for Dreamer, who are in the same group as two manufacturers already
   answering us. It would also settle the identity question above.
2. **Chassis per model**, which the site no longer states.
3. **Whether City Camp Select has a pop-up roof**, and whether `CITY CAMP HYBRIDE` has
   been withdrawn.
