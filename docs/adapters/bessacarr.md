# Bessacarr — site survey

Surveyed 17 September 2026. FMLV manufacturer id **228**, name **`Swift Group Ltd`**,
display name **`Bessacarr`**. **NCC supplier name `Bessacarr Caravans`.** **Caravans
only.** **Five layouts, one range**; what FMLV holds is not yet known — see *The one
thing not checked* below.

This completes the Swift Group: 26 (Swift), 264 (Ace Motorhomes), 228 (Bessacarr).
`ADAPTERS` is already keyed on `(manufacturer, display name, product area)`, so unlike
Ace this brand needs **no wiring change** — the re-key done for Ace anticipated it.

## Bessacarr By Design is a dealer special, and FMLV already files its predecessor

The most consequential thing the survey found, and it is not what the brand name
suggests. `bessacarrcaravan.co.uk` is titled **"Bessacarr By Design | Couplands Caravans
Ltd"**, and its own copy says the range

> *"combines the innovative design and build technology of the Swift Group and the
> meticulous attention to detail and styling of Couplands Caravans"*

**Swift publish nothing about Bessacarr** — zero mentions on `swiftgroup.co.uk` or
`/caravans`, which the Swift survey had already recorded on 28 August 2026. That cuts
both ways. It means there is no factory page for the usual *"never take specs off a
dealer page"* rule to prefer, so this site is the only source in existence. It also
means nothing here can be corroborated against the manufacturer.

**FMLV's own export proves the arrangement.** The Swift Group Ltd touring-caravan export
holds 28 rows with `dealer='Couplands Caravans'`, `dealer_specials_range='Yes'` and
`dealer_model_variant='Yes'` — nine **Finesse** and five **Cameo by Design**
(480/580/835/845/850, model year 2022). Same dealer, same *"by Design"* naming,
overlapping model numbers. **Bessacarr By Design is the current generation of the same
deal**, and FMLV has a settled shape for it.

### It is a rebadged Swift Elegance Grande

Every dimension FMLV holds for the 2025/26 Elegance Grande is byte-identical to what
this site publishes:

| | internal | shipping | awning | height | berths | axle |
| --- | --- | --- | --- | --- | --- | --- |
| **780** | 5950 | 7570 | 10008 / *site 10300* | 2610 | 4 | single |
| **835 / 845 / 850 / 860** | 6360 | 7980 | 10490 | 2590 | 4 | twin |

Only the masses move, and they move consistently. **MRO is +43 kg on all four
twin-axles** — 1922→1965, 1901→1944, 1908→1951, 1854→1897 — and +73 kg on the 780, which
is the Couplands kit: Truma Aventa aircon, E&P levelling, 2 × 100 W solar, Alde heating.
The twin-axles are then **plated up to a flat 2250 kg MTPLM** from Swift's 2055–2123.

That is a conversion, documented by arithmetic that repeats to the kilogram across four
vehicles. It is not a coincidence of dimensions.

## The source

Plain server-rendered HTML at `/bessacarr780`, `/bessacarr835`, `/bessacarr845`,
`/bessacarr850`, `/bessacarr860`. **No JSON, no JavaScript, no PDF** — the poorest source
of the three Swift Group brands, and the opposite of Ace, whose pages carry their whole
dataset inline. The spec table is a label/value list under a `Specifications` heading:

```
Berths                                          4
Numbers of Axles                                1
Internal Length (at bed box height)             5.95m / 19'6''
Overall Width#                                  2.45m / 8'0''
Overall Height (inc. TV Aerial)#                2.61m / 8'7''
Maximum Internal Headroom                       1.95m / 6'5''
Overall Length#                                 7.57m / 24'10''
Awning A/A Dimension                            10.30m / 33'10''
Mass in Running Order (inc. tolerance)          1774kg / 34.3cwt
Maximum Technical Permissable Laden Mass        1900kg / 37.4cwt
Total User Payload                              215kg
Personal Effects Payload                        156kg / 3.1cwt
Thermal Insulation Grade                        Three
```

There is no `mtplm` token in the raw HTML; the label is spelt out, misspelling
*"Permissable"* included, so the patterns anchor on the printed English.

## The self-check is real, and it catches two of the five pages

`Total User Payload == MTPLM − MRO`. Both masses and the payload are published
independently, so this is a genuine check rather than the true-by-construction identity
several adapters settle for. **It holds on the 835 (285), 845 (306) and 860 (353).**

**The 780 fails outright.** MRO 1774 + payload 215 = 1989 against a stated MTPLM of
**1900** — and the same page's own header badge says **"1800kg MTPLM"**, a *third*
figure. The page is also marked **SOLD OUT**.

Where those numbers come from is now clear. The 780's published Personal Effects Payload
of **156 kg is exactly what FMLV holds for the Swift Elegance Grande 780**, and 1900 is
exactly Swift's MTPLM. So the 780 page is carrying the **base Elegance Grande's spec
sheet with only the MRO updated** for the conversion. Its 215 kg total belongs to neither
vehicle — Swift's own 780 works out at 1900 − 1701 = 199.

One published figure on that page is wrong and nothing on the site says which, so **the
780 is dropped with a narrated warning rather than proposed**.

**The 850 is a softer case.** Its Total User Payload of 299 reconciles correctly, but its
*Personal Effects Payload* of **306 exceeds the total** — and 306 is the 845's figure,
one row up. So the total is trustworthy and the personal-effects figure is a copy-paste.
The layout goes forward; the personal-effects figure does not.

## The payload columns, where this brand is better than its parent

Bessacarr publish **both halves FMLV has columns for** — `Total User Payload` and
`Personal Effects Payload` — which Swift no longer do. `swift_caravan.py` has to derive
`MTPLM − MRO` into the personal-effects column precisely because the split was withdrawn;
here it is printed.

So `personal_effects_payload_kilograms` takes the **published Personal Effects Payload**.

**`optional_equipment_payload_kilograms` is not derived from Total − Personal.** NCC user
payload is essential habitation + optional equipment + personal effects, and Bessacarr
publish no essential-habitation figure, so the remainder is not safely optional
equipment. On three of the five the two printed figures are equal anyway, which would
make the remainder zero and says the site is not using the split rigorously. FMLV holds
`pe=160 oe=41` on the Swift 835–860.

## The length trap, inherited

Identical to `swift_caravan.py`'s, and settled the same way — against FMLV's own rows
rather than by reasoning:

* **`Overall Length` → `shipping_length_mm`** (7.57 m / 7.98 m);
* **`Internal Length (at bed box height)` → `internal_length_mm`** (5.95 m / 6.36 m);
* **`Awning A/A Dimension` → `awning_length_mm`**.

Reading the overall figure as the internal one would overstate every caravan's habitable
space by about 1.6 m while looking entirely plausible on any single product.

**Height is published only as "Overall Height (inc. TV Aerial)"**, which reads like the
wrong figure and is not — FMLV's 2610 and 2590 match it exactly, so that is what FMLV
wants.

## Habitation is thin, but it is per layout

A `Bed Sizes` block naming Front Double, Rear Double, front and side singles with
centimetre and imperial sizes, plus a `Side Bunk (Offside) 4 berth only` carrying no
size. Nearside/offside is stripped per the habitation rule.

The bed lists carry the same class of copy error as the payloads: the **835 lists "Front
Single (Nearside)" twice**, and so do the 850 and 860, where one of each pair is plainly
the offside bunk.

Beyond the beds there is an `Exclusive Bessacarr Features` list per page — Truma Aventa
Comfort aircon, 100–200 W solar, Alde heating, freezer shelf, Swift Command — which is
where heating and refrigeration findings come from.

## Model year is a live risk

The pages say **"Model 2025"** and link a **"2024 brochure"**, while
`cli._is_current_model_year` keeps only the current calendar year and next. If FMLV's id
228 rows are badged 2025 or older, **the baseline arrives empty and all five are proposed
as new.**

## The one thing not checked

**There is no export under `data/exports/` for 228**, so what FMLV holds for Bessacarr
today has not been seen. Two possibilities, and they lead to different first runs:

* FMLV holds the **pre-2020 factory Bessacarr** caravans (Cameo, Vantage and the rest).
  A run then proposes five new products and reports the whole historic range as
  disappeared. That is correct behaviour, but it should be expected rather than
  discovered.
* FMLV holds **nothing**, in which case this is an empty-baseline bootstrap like Atom —
  `fmlv empty-baseline`, upload, supplier record, re-run.

**`fmlv fetch-export "Bessacarr Caravans"` settles it, and should be run before the
adapter is built.**

## Still unverified

* **Whether these should sit under supplier `Bessacarr Caravans` at all**, rather than
  under Swift Group Ltd with the dealer columns filled, as Cameo by Design is. That is an
  NCC-side decision, not an adapter one; the requester specified `Bessacarr Caravans`.
* **The dealer columns.** `dealer`, `dealer_specials_range` and `dealer_model_variant`
  are filled on FMLV's Couplands rows and are not currently written by any adapter.
* **Prices.** £50,995 on the 780 and a flat £54,995 on all four twin-axles, which is
  plausible for a fixed-spec dealer range but is a suspiciously round uniformity.
* **Whether a sixth layout exists.** Bessacarr publish no count of their own, so
  `EXPECTED_LAYOUTS` is the only thing that would notice a page being lost.
