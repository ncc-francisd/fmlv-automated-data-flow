# Laika — site survey

Surveyed and built 9 September 2026. FMLV manufacturer id **52**, name `Laika`, NCC
supplier name `Laika`.

Italian, part of the Erwin Hymer Group — but **not on the EHG configurator platform** that
Eriba, Dethleffs, Bürstner and Carado share. Laika's own site is better than that API, so
there is nothing to regret about it.

## The source: JSON-LD on the models index

`https://www.laika.it/en-gb/motorhomes/` carries **schema.org JSON-LD describing every
layout in the UK range**, in plain server-rendered HTML. One fetch, no JavaScript, no PDF,
no login, and — importantly — no rate-limited API.

`/en-gb/` is a real market edition: prices are in **sterling** and the page declares
`GBP`, so none of the exchange-rate trouble that makes Morelo's data the worst in the
project applies here.

Per layout, the JSON-LD gives:

| FMLV field | JSON-LD |
| --- | --- |
| `rrp_pounds` | `offers.price` + `offers.priceCurrency` = `GBP` |
| `mro_kilograms` | `weight` (kg) |
| `mtplm_kilograms` | `weightTotal` (kg) |
| `mh_length_mm` / `width` / `height` | `depth` / `width` / `height`, in **cm** |
| `mh_passenger_seats_inc_driver` | `vehicleSeatingCapacity` |
| `berths` | `additionalProperty.sleepingBerthsMinMax`, e.g. `"2 - 4"` |
| `base_vehicle_manufacturer` | `additionalProperty.baseChassis`, e.g. `Fiat Ducato 35 Light 160` |
| range | `vehicleConfiguration` |

Also present and not needed: engine power, emission standard, tyre size, fresh and waste
water capacities, wheelbase, braked towing capacity.

A real row, from `L 2009`:

```json
{"name": "L 2009", "model": "L 2009", "vehicleConfiguration": "Ecovip Titanio",
 "weight":      {"value": 2971, "unitCode": "KGM"},
 "weightTotal": {"value": 3500, "unitCode": "KGM"},
 "depth":       {"value": 659,  "unitCode": "CMT"},
 "offers":      {"price": "85100.00", "priceCurrency": "GBP"}}
```

### The gated technical table adds nothing that matters

Each range page has a **Technical Data** panel behind a terms-and-conditions click. It
publishes interior width, headroom, insulation thicknesses and the optional-equipment mass
— and, for everything FMLV records, **exactly the figures already in the JSON-LD**: 659 /
225 / 299 / 2971 / 3500 / wheelbase 3450 on `L 2009`, checked value by value. So the gate
never has to be passed.

## The roster: 15 layouts across **two** indexes

| Index / range page | Layouts |
| --- | --- |
| `/en-gb/motorhomes/a-class/ecovip-titanio/` | 3 — H 2109, H 3119, H 4109 DS |
| `/en-gb/motorhomes/a-class/kreos/` | 1 — H 5109 MB |
| `/en-gb/motorhomes/coachbuilt/ecovip-titanio/` | 5 — L 2009, L 3019, L 4009, L 4009 DS, L 4012 DS |
| `/en-gb/motorhomes/coachbuilt/kreos/` | 1 — L 5009 MB |
| `/en-gb/camper-van/ecovip-evoluzione/` | 2 — 540, 600 |
| `/en-gb/camper-van/ecovip-performance/` | 3 — 540, 600, 645 |

**15 in total, and it takes two fetches, not one.** `/en-gb/motorhomes/` lists the ten
coachbuilts and A-classes and says **nothing at all** about the vans, which sit under their
own top-level `/en-gb/camper-van/` path. Both indexes are read, and `INDEX_PATHS` is where
a third body style would be added.

### How this went wrong, and what would have caught it

The first version of this adapter shipped **10 products**. It missed the vans twice over:
the sitemap sweep filtered on `/motorhomes/` in the path, and the requester's own remark —
*"there are some camper vans as well"* — was misread as saying there were none.

**What would have caught it in minutes is a target count.** FMLV holds 38 Laika products;
the requester said so on sight and the discrepancy was obvious. Stage 1.5 of
`.claude/skills/add-manufacturer` asks for the manufacturer's public claim precisely so
there is a number to fail against, and no number was obtained here — the four range pages
found by the sitemap were taken as the roster, which made the roster self-confirming.

The residual gap, **15 published against 38 in FMLV**, is not a parsing gap: the UK site
publishes one model year, and FMLV accumulates. The first run against a real export is what
resolves it, as disappearances rather than silence.

### A paint colour is not a layout

The vans publish **one structured record per colour** — `Ecovip Performance 540 - Grigio
Torino`, `… - Azzurro Portofino`, `… - Bianco Cortina`, `… - Grigio Napoli` — at identical
prices, weights and dimensions, and the floorplan slider does the same. Twenty records,
five vehicles. `strip_colour` collapses them, keyed on `(range, model)` so the first wins.

The requester's rule, 9 September 2026: *"we wouldn't count different colours as a
different model. We would count a different model if it has a different model code or
name."* The suffix pattern needs a space-dash-space, so `L 4009 DS` and `H 5109 MB` survive
it untouched.

### The trap: a one-layout range is a different JSON-LD shape

A multi-layout range page is a `ProductGroup` with `hasVariant`. **A one-layout range is a
bare `["Product", "Vehicle"]` with no `hasVariant` at all** — so a parser that looks only
for the group shape silently drops both Kreos ranges, which is 2 of 10. This is Rimor's
one-layout-range lesson in a different costume, and the survey caught it only because the
two Kreos pages returned zero where the roster said one.

**And on those pages the `name` is the range, not the layout.** Coachbuilt Kreos publishes
`"name": "Kreos"`; the layout `L 5009 MB` appears only in the floorplan slider's
`data-name`. The index page has it right (`Kreos H 5109 MB`), which is another reason to
take the roster from there — but note the index prefixes the range on *one* of the two
(`Kreos H 5109 MB` against a plain `L 5009 MB`), so model names need normalising.

## The self-check

The page publishes the same figures **twice, independently**: once in the JSON-LD, and
again as data attributes on the floorplan slider's slides —

```html
<div class="embla__slide" data-model-id="4171200" data-name="L 2009"
     data-price="£85,100.00" data-sleeping="2 - 4" data-length="659 cm"
     data-weight="3500 kg" data-width="225 cm" data-height="299 cm">
```

Checked across the eight multi-layout products: **price, length, width, height, MTPLM and
berths agree on 8 of 8.** That is a genuine redundancy — two renderings of one record — and
it is what a `_reconciles()` should use.

Secondary and weaker: the gated table prints mass in running order with its ±5% band,
`2971 (2822 - 3120)*`. It is a *function* of the mass (×0.95, ×1.05), so it catches a
misread digit but not a slipped column, and it is behind the gate. The slider cross-check
is the better one.

## Floorplans: 10 of 10

Each range page has a `section__floorplan-slider` whose slides carry the layout in
`data-name` and its own drawing inside the slide. **That structure is the join** — the
search is bounded to the span between one `data-name` and the next, so a slide without a
drawing yields nothing rather than borrowing its neighbour's.

### A filename is not evidence about its content

Worth recording, because the first version of this adapter got it wrong. `L 5009 MB`'s
drawing is served as

```
carado-imagebank-data_VE_Camper-Van_CV540_CU_2025_…_WEB-2-1920x762.png
```

and it was read as a **Carado campervan photograph misfiled by Laika** — a site bug — so
the adapter required a drawing's filename to name its own layout and dropped this one. The
requester opened the page and said it looked like a low-profile motorhome. **He was right:
downloading the image shows Laika's own correct Kreos L 5009 MB drawing**, twin rear
singles, side washroom, front lounge.

The Erwin Hymer Group brands share an image bank, and Laika's WordPress keeps whatever
name a file was uploaded under. So a `carado-…` filename on a Laika page says nothing
about the picture — not even which brand it belongs to.

The general lesson, which is why this is in the notes rather than just the git history:
**a filename is metadata about an upload, not about an image.** Where the markup already
ties an asset to a record — a slide to its `data-name` — trust the markup. Dethleffs is the
opposite case and shows when a filename check *is* worth having: there the page shows
sixteen plans in one flat list with nothing structural to tell them apart, so the name is
the only signal available. Structure first; names only when there is no structure.

## Settled by the requester, 9 September 2026

* **`ncc_supplier_name` is `Laika`** — plain, unlike Niesmann+Bischoff's, which is
  "Niesmann + Bischoff shown by Travelworld".
* **Two ranges, models beneath them.** `Ecovip Titanio` and `Kreos`. Laika's
  `vehicleConfiguration` distinguishes `Ecovip Titanio I` from `Ecovip Titanio`, the `I`
  marking the integrated (A-class) build — but that is a body type FMLV already has a
  column for, so the suffix is dropped. The same precedent as Adria's 60Y editions filing
  under `Matrix` rather than `Matrix 60Y`.
* **Low profile, not over-cab.** *"I don't see any over-cab bed"* — which agrees with
  Laika's own index description, *"Low-profile and A-class"*. **No campervans** in the UK
  line-up either, which the sitemap confirms: only `/a-class/` and `/coachbuilt/`.

## First run

9 September 2026. **15 products across 4 ranges, none dropped, 240 fields with
provenance**, and no blank among price, both masses, payload, all three dimensions, seats,
berths, chassis or body type. Four A-class, six low profile, five campervan high tops — all
five vans are 2650 mm, clearing the settled 2300 mm threshold. **All fifteen carry a
floorplan pointer.**

## Still unverified

* **Why FMLV holds 38 and the site publishes 15.** The requester confirmed FMLV spells the
  manufacturer `Laika`, matching the supplier list, so the join key is right and the
  baseline will match. The gap is therefore products FMLV has accumulated that the current
  UK site no longer lists — older model years and withdrawn layouts — which the first run
  against a real export will report as disappearances. Worth reading that first run
  carefully rather than assuming.
* **When the model year turns over.** Not established for Laika; per
  [`README.md`](README.md) the sector rolls July to early September, so re-check at the end
  of September with the rest.
* **Nothing about the floorplans.** All ten resolve, and the one that looked wrong was not.
