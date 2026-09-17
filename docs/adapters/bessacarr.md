# Bessacarr — site survey and adapter

Surveyed and built 17 September 2026. FMLV manufacturer id **228**, name **`Swift Group
Ltd`**, display name **`Bessacarr`**. **NCC supplier name `Bessacarr Caravans`.**
**Caravans only.** **Four layouts, one range**, and FMLV holds all four — product ids
7853-7856, model year 2026.

This completes the Swift Group: 26 (Swift), 264 (Ace Motorhomes), 228 (Bessacarr).
`ADAPTERS` is already keyed on `(manufacturer, display name, product area)`, so unlike
Ace this brand needs **no wiring change** — the re-key done for Ace anticipated it.

## It is a brand, not a dealer special — and that was ruled on, not assumed

The survey's first reading was that this is a dealer special, and the evidence for it was
strong enough to be worth recording even though the conclusion was overturned.
`bessacarrcaravan.co.uk` is titled **"Bessacarr By Design | Couplands Caravans
Ltd"**, and its own copy says the range

> *"combines the innovative design and build technology of the Swift Group and the
> meticulous attention to detail and styling of Couplands Caravans"*

**Swift publish nothing about Bessacarr** — zero mentions on `swiftgroup.co.uk` or
`/caravans`, which the Swift survey had already recorded on 28 August 2026. That cuts
both ways. It means there is no factory page for the usual *"never take specs off a
dealer page"* rule to prefer, so this site is the only source in existence. It also
means nothing here can be corroborated against the manufacturer.

**And FMLV already files a predecessor that way.** The Swift Group Ltd touring-caravan
export holds 28 rows with `dealer='Couplands Caravans'`, `dealer_specials_range='Yes'` and
`dealer_model_variant='Yes'` — nine **Finesse** and five **Cameo by Design**
(480/580/835/845/850, model year 2022). Same dealer, same *"by Design"* naming,
overlapping model numbers.

**The requester settled it on 17 September 2026, against that reading**, and the reasons
are worth keeping because the evidence above will look compelling again to the next person:

* **Swift no longer do dealer specials at all**, so the category the Cameo rows sit in is
  closed rather than current;
* **Bessacarr has its own public-facing website**, separate from Couplands' own — which
  sells Bailey and other makes — so it is presented as a brand rather than as one
  retailer's trim level;
* the arrangement is **the one Benimar has with Marquis Leisure**: sole UK retailer, still
  unambiguously a brand. Sole distribution is not the same fact as a dealer special.

**So the three dealer columns are written by nothing in this adapter**, which matches
FMLV's own four rows, where all three are blank.

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

## The roster is four, and the 780 is the reason it is read from the cards

`/model-range` links **all five** model pages from its navigation dropdown, but publishes
only **four cards** — `835 4 berth 2250 MTPLM Twin Axle Grade 3 Insulation`, and the same
for 845, 850 and 860. The **780 is a 2025 model**, marked SOLD OUT on its own page and
inactive in FMLV, and the requester confirmed on 17 September 2026 that it does not need
reviewing.

So `model_range_roster` reads the **card shape**, which requires an MTPLM beside the berth
count. Taking the `/bessacarr\d+` hrefs instead would collect five, and the fifth is a
vehicle nobody wants proposed. The card's `kg` is **optional** in the pattern: the 835 and
845 cards omit it where the 850 and 860 print it, and requiring it would have halved the
roster silently.

`EXPECTED_LAYOUTS = 4` is the backstop, since Bessacarr publish no count of their own and
a lost card is indistinguishable from a discontinuation.

## The source

Plain server-rendered HTML at `/bessacarr<model>`. **No JSON, no JavaScript, no PDF** — the poorest source
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

## Two self-checks, and the excluded 780 is what proves they work

1. **`Total User Payload == MTPLM − MRO`**, within the spec table. All three figures are
   published independently, so this is a genuine check rather than the
   true-by-construction identity several adapters settle for. **It holds on all four:**
   285, 306, 299, 353.
2. **The `/model-range` card's MTPLM against the model page's own spec table** — a real
   cross-document check, two pages written separately agreeing on 2250.

A `False` on either drops the product, because a vehicle whose own page contradicts itself
cannot be proposed: nothing on the site says which figure is wrong.

**The 780 fails both**, which is the reassurance that neither is vacuous. MRO 1774 + payload 215 = 1989 against a stated MTPLM of
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

## Payload: the total, not the row labelled personal effects

Bessacarr print **both** halves FMLV has columns for — `Total User Payload` and `Personal
Effects Payload` — which Swift no longer do; `swift_caravan.py` has to derive `MTPLM −
MRO` into the personal-effects column precisely because the split was withdrawn. So the
obvious move is to take the figure whose label matches the column. **It is the wrong one.**

The two are printed **equal** on the 835, 845 and 860, which says the site is not using the
split rigorously. On the **850** they differ — total 299, personal effects **306** — and
306 is the 845's figure, one row up. It exceeds its own vehicle's total capacity, so it is
not merely a different basis; it is a copy-paste.

So `personal_effects_payload_kilograms` takes the **total**, which is the one figure that
reconciles against the masses on all four, and the 850's disagreement is narrated rather
than silently resolved. This is also the requester's settled rule of 4 September 2026
applied unchanged: *where a model has one published payload figure, use it as the
personal-effects total.*

`optional_equipment_payload_kilograms` is recorded with **no value**, saying the adapter
looked. FMLV holds it blank on all four, so it comes back confirmed and no reviewer sees a
row.

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

## Habitation is thin, and it is the wrong equipment list

Worth stating plainly rather than leaving a reviewer to infer it. The only per-model list
on the site is **`Exclusive Bessacarr Features`** — the kit Couplands *add* to the base
caravan. The underlying Swift equipment is published nowhere on this site, and Swift
publish nothing about Bessacarr at all, so there is **no standard-equipment list to read**.

What survives is genuine but sparse: a `Freezer Shelf` on the twin-axles, `Truma Aventa
Comfort` air conditioning, solar, and `Alde Heating` where the prose mentions it. These
reach the reviewer as findings with the page's own words attached, never as proposals.

**`bed_types` is dropped**, for the same reason as on both halves of Swift. There is a
`Bed Sizes` block naming Front Double, Rear Double, front and side singles with
centimetre and imperial sizes, plus a `Side Bunk (Offside) 4 berth only` carrying no size
— but it names **positions**, without saying whether a bed is built in or made up from the
seating, which is exactly what `BedType` has to distinguish. Left to the reviewer and the
drawing.

The bed lists carry the same class of copy error as the payloads: the **835, 850 and 860
each list "Front Single (Nearside)" twice**, where one of each pair is plainly the offside.
Nearside/offside is stripped per the habitation rule in any case.

## What FMLV holds, and what this run corrects

FMLV holds **all four**, product ids **7853–7856**, model year 2026, range `Bessacarr By
Design`, dealer columns blank. So this is an ordinary update, not a bootstrap: nothing is
new and nothing disappears.

**Two fields are stale on all four, and correcting them is what this adapter is for:**

| | FMLV MTPLM | FMLV MRO | FMLV payload | site MTPLM | site payload |
| --- | --- | --- | --- | --- | --- |
| 835 | 2125 | 1965 | 160 | **2250** | **285** |
| 845 | 2104 | 1944 | 160 | **2250** | **306** |
| 850 | 2111 | 1951 | 160 | **2250** | **299** |
| 860 | 2057 | 1897 | 160 | **2250** | **353** |

FMLV's MTPLM is `MRO + 160` on every one of them — derived from the old personal-effects
figure of 160 kg rather than from any published plate, and 160 kg is what FMLV holds in the
payload column too. The site's flat 2250 kg reconciles **exactly** against the site's own
published payloads on all four. Both figures are stale in FMLV and both are corrected.

Everything else already agrees: MRO, all three lengths, width, height, headroom, berths,
twin axle and the £54,995 price are byte-identical to what FMLV holds, so they come back
verified unchanged.

## Model year

The pages say **"Model 2025"** and link a **"2024 brochure"**, while FMLV holds all four as
**2026**. `year` is a carry-through field only a person bumps
(`src/diff/year_rollover.py`), so nothing here emits it. Worth watching only because
`cli._is_current_model_year` keeps the current calendar year and next: if FMLV's rows ever
fall behind, the baseline empties and all four arrive as new.

## Still unverified

* **Whether a fifth layout returns.** Bessacarr publish no count of their own, so
  `EXPECTED_LAYOUTS` is the only thing that would notice a card being lost — or a new one
  being added, which arrives as a narrated count mismatch rather than silently.
* **The 780**, if it is ever wanted. It cannot be collected safely as the page stands: one
  of its MRO, MTPLM and payload is wrong and nothing on the site says which.
* **The flat £54,995** across all four twin-axles. Plausible for a fixed-spec range, but a
  suspiciously round uniformity, and the only price source is this site.
* **Floorplans.** Each card links one, and none is read.
* **Whether Swift ever publish Bessacarr themselves.** If they do, the factory page
  outranks this one under the usual rule, and this adapter's source choice should be
  revisited.
