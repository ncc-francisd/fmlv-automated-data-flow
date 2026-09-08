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

## The roster: 10 layouts, and two of them nearly invisible

Four range pages, from the sitemap (which agrees with the index page's own links):

| Range page | Layouts |
| --- | --- |
| `/en-gb/motorhomes/a-class/ecovip-titanio/` | 3 — H 2109, H 3119, H 4109 DS |
| `/en-gb/motorhomes/a-class/kreos/` | 1 — H 5109 MB |
| `/en-gb/motorhomes/coachbuilt/ecovip-titanio/` | 5 — L 2009, L 3019, L 4009, L 4009 DS, L 4012 DS |
| `/en-gb/motorhomes/coachbuilt/kreos/` | 1 — L 5009 MB |

**10 in total**, and the index page's JSON-LD lists all ten, so the roster needs one fetch
rather than four.

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

## Floorplans: 9 of 10, and one is somebody else's vehicle

Each range page has a `section__floorplan-slider` whose slides carry `data-name` and a
drawing named after the layout — `25-Laika-Ecovip-Titanio-L-2009_b-1920x983.png`. So the
join is trivial: the slide names its own layout.

**Except Coachbuilt Kreos.** Every image in `L 5009 MB`'s floorplan section is

```
carado-imagebank-data_VE_Camper-Van_CV540_CU_2025_…_WEB-2-1920x762.png
```

— a **Carado campervan photograph**, not a Laika floorplan, and there is no correct drawing
anywhere in that section. A Laika site bug, and exactly the case where a wrong drawing is
worse than none: a reviewer would read a layout off a different manufacturer's van. So the
floorplan pointer must be **name-checked against the layout** rather than taken as the
first image in the slider, and `L 5009 MB` gets none until Laika fix it.

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

9 September 2026. **10 products across 2 ranges, none dropped, 155 fields with
provenance**, and no blank among price, both masses, payload, all three dimensions, seats,
berths, chassis or body type. Four A-class, six low profile. **9 of 10 carry a floorplan
pointer** — `L 5009 MB` is the Carado-photograph bug above, and the run says so by name.

## Still unverified

* **The FMLV baseline join.** `fmlv_manufacturer` is `Laika` from
  `resources/manufacturers-full-list.csv` (id 52) but has not been checked against a real
  FMLV export, so the first run will classify all ten as new until it is.
* **When the model year turns over.** Not established for Laika; per
  [`README.md`](README.md) the sector rolls July to early September, so re-check at the end
  of September with the rest.
* **Whether the Carado floorplan is ever corrected.** If it is, `L 5009 MB` picks up its
  pointer with no code change — the filename check is what gates it.
