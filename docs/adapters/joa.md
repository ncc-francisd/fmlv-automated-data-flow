# Joa by Pilote — site survey

Surveyed 10 September 2026. FMLV manufacturer id **261**, name **`Joa by Pilote`**,
display name the same, NCC supplier name the same. Motorhomes and panel vans, no
caravans. Ten products, and FMLV already holds all ten.

## What the requester brought to the survey

* The manufacturer and supplier names are both **`Joa by Pilote`**, that exact spelling.
  *"I have seen that name possibly with the dots over the o, but we haven't got that
  within FMLV"* — so never "correct" it to a diaeresis.
* **It used to be Joacamp and was not part of the Pilote group.** That is visible in the
  data: the NCC list still carries a separate **id 103, `Joa Camp`**, and the site's own
  configurator still lives on `configurateur.joa-camp.com`. Check 103 holds nothing
  before trusting a run against 261.
* The model pages carry *"a technical panel towards the bottom of the page, which you can
  open up and view all equipment"* — correct, and it is the best thing about this source.
* A floorplan *"possibly when you click configure"* — close. The drawings are plain
  images on the page itself; see below.
* Two 2027 documents, supplied by email: a **Technical Book** and a **UK price list**.

## The source: the ten model pages

`joabypilote.fr/en/vehicle/<slug>/`, plain server-rendered WordPress. **One URL is one
vehicle**, so attribution is free and none of the column defences that dominate
`morelo.py` or `burstner.py` are needed. This is the Auto-Trail end of the risk spectrum.

The roster is `vehicle-sitemap.xml`, which lists exactly the ten canonical pages and the
index. That matters, because **the pages have aliases**: `60f`, `motorhome70t` (no
hyphen), `van-54g`, `panel-van-60g-en` and `panel-van-63t-en` all resolve to a canonical
page. Building the roster from in-page links finds fifteen URLs for ten vehicles.

| | motorhomes | panel vans |
| --- | --- | --- |
| layouts | 60F, 70Q, 70T, 75Q, 75T, 75QB, 75TB | 54G, 60G, 63T |
| FMLV range | `Motorhome` | `Van` |

### What one page gives

Two blocks, and both are needed. A summary strip beside the Configure button:

```
starting from £68,400
7,45 m long     2,30 m wide     4 seats     2 berths
```

and a "Technical Information" panel:

```
Width / Length              230 cm / 285 cm
Type of heating             4,000 W Truma® Combi D4 hot water/heating
Refrigerator                Automatic fridge with vent covers: 133-litres
Fuel tank                   90 L
Bed size                    73×190 / 73×200 cm
Payload capacity            470 kg
Fresh water tank capacity   130 L
Waste water tank capacity   95 L
```

**`Width / Length` is mislabelled.** Its second value is the **height** — 285 cm on every
motorhome and 267 cm on every van, against real lengths of 5.41 m to 7.45 m. The length
is in the summary strip. An adapter that trusted the label would record a 599 cm vehicle
as 285 cm long, on all ten.

### `View all equipment` is the habitation source, and it is free

Each page carries an overlay holding **that model's whole standard-equipment list**,
section by section — ENGINE-CHASSIS, CAB FITTINGS, ENERGY-AUTONOMY, LOUNGE, KITCHEN,
BATHROOM AND TOILET, BEDROOM. One model, one list, no marks to read and no columns to
align, which is the opposite of every other brand in this project. The findings come out
of it directly.

Truma Combi D4 on all ten (blown air); a 133-litre automatic fridge on the motorhomes and
a 95-litre compressor on the vans; **the word "microwave" appears on no page and nowhere
in the Technical Book**, which is the itemised-table exception on firm footing.

### Floorplans: ten of ten, on the page

`wp-content/uploads/2026/02/joa-site-implant-<code>.jpg` — *implantation* is French for
layout. Every page carries the whole set in its nav strip, so the join is a code match.

## Two things the site does not publish

* **MTPLM.** The Technical Book gives **3500 kg for all ten base models**, and prices a
  3.65 T derate as a £390 option, so 3500 is the base-vehicle figure. It is a
  page-constant in the Rimor sense — no attribution risk — but it is a **manually
  sourced constant that no run can refresh**. FMLV already holds 3500 on all ten.
* **The three panel vans' prices.** The seven motorhome pages carry `starting from £x`
  and all seven match the 2027 list to the pound. The van pages carry none. The list
  gives 54G £58,900, 60G £59,900, 63T £61,900.

**Neither document is published on the website.** The whole WordPress media library holds
two PDFs, both from 2021 and both irrelevant, so the Technical Book and the price list
arrive by email from Pilote and cannot be rediscovered per run. That is the opposite of
every other brand here and it is why the two figures above have to be constants.

## The price basis differs from Pilote's own

Joa's list says **"including 20% VAT and transport"** and heads the column *Delivered*.
Pilote's 2027 list says "incl. VAT **excluding** transport". Two brands of one group, two
bases — so nothing about the price may be shared between their adapters.

## The self-check: the model code is the length

The number in the code is the length in decimetres, and it holds on all ten:

| 54G | 60F / 60G | 63T | 70Q / 70T | 75Q / 75T | 75QB / 75TB |
| --- | --- | --- | --- | --- | --- |
| 5.41 m | 5.99 m | 6.36 m | 6.99 m | 7.39 m | 7.45 m |

Worst miss 0.11 m (the 75Qs), so a ±0.15 m band passes all ten — and it **catches a real
error**: the 63T's summary strip says `5.99 m long`, which is the 60G's length, and is
off its expected 6.3 m by 0.31 m. The Technical Book says 6.36 m and FMLV holds 6360.
This is Le Voyageur's check, and the same failure it was built for.

### The page states the length twice, and the second one is right

Found 10 September 2026, after the first run, when the requester pointed at the
campervans index: **every page carries a model strip naming nine of the ten vehicles
with their lengths** — `Panel van 63T L6,36m`, `Motorhome 70Q L6,99m`. On the 63T's own
page that strip says **6,36 m**, six inches from the summary strip's wrong 5.99 m, and it
is the figure the Technical Book and FMLV both carry.

So the check can now **repair** rather than only reject: where the summary strip fails
the model-code test, `length_from_the_strip` supplies the strip's figure instead — but
only if that figure passes the same test, so a page whose strip is also wrong still ends
with a blank length rather than a different wrong one. **The 54G is the one model the
strip omits**, which is why this is a fallback and not the primary source; its own
summary is correct anyway.

The requester's own index screenshot shows the same 6,36 m on the `/en/our-campervans/`
card. Both second sources agree, and no extra fetch is needed for either — the strip was
already in the page the adapter had.

Two decimal separators are in play and both must be read: the summary strip prints
`5.99 m long` with a full stop on the van pages, the model strip prints `L6,36m` with a
comma. A pattern that assumes one of them silently finds nothing.

The usual `payload = MTPLM − MRO` is **not** available: no MRO is published anywhere, so
it has to be derived from the other two and the identity becomes true by construction —
Murvi's situation exactly.

## The Technical Book is the cross-check, not the source

Read against the site, the 2027 book agrees on **9 of 10 lengths, 10 widths, 10 heights,
10 seat counts, 10 berth counts, 7 of 7 prices and 7 of 10 payloads**. That is a real
two-document check, but a one-off one, since the book cannot be fetched.

Where they disagree, the site wins, and the FMLV export settles it independently:

* **The 63T's length** — the site is wrong, for the reason above.
* **The three van payloads.** The book says 730 / 630 / 555; the site says 610 / 540 /
  500. FMLV's stored MRO is 2890 / 2960 / 3000, and `3500 − site payload` reproduces all
  three **exactly** while the book's figures reproduce none. So the site's are the ones
  FMLV is built on and the ones that balance against a 3500 kg MAM. Both sources agree on
  all seven motorhomes, so this is not a difference of convention.

The book also carries per-layout standard-equipment tables marked `● Standard ○ Optional
- Unavailable` — the same shape as Pilote's and as Knaus's `s o -`. **They are not needed
here**, because the site's per-model overlay says the same thing without any column to
align. They will be needed for Pilote.

## What the first run should propose

Nineteen changes across ten products, and no product is new or disappeared:

| field | count | what |
| --- | --- | --- |
| `berths` | **7** | 3 → 2 on every motorhome |
| `mh_passenger_seats_inc_driver` | 4 | 5 → 4 on the four 75s |
| `mh_length_mm` | 3 | 70Q 7390 → 6990; 75QB and 75TB 7390 → 7450 |
| `mh_height_mm` | 3 | 54G 2600 → 2670; 60G and 63T 2850 → 2670 |
| `mh_width_mm` | 2 | 60G and 63T 2300 → 2050 |
| `rrp_pounds`, `mh_payload_kilograms`, `mtplm_kilograms` | **0** | agree 10 of 10 |

Three of those groups need a word before anyone accepts them:

* **The seven berth changes are the settled rule, not a reading error.** Both sources say
  sleeping space 2, and the electric drop-down bed is a £1,760 **option** (unavailable on
  the 60F). The berth-range rule takes the standard figure.
* **The four seat changes are the same rule.** The book prints `●4 - ○5` on the 75s and
  prices a fifth seatbelt at £1,240; the site's strip says 4.
* **The 60G and 63T corrections are FMLV holding motorhome figures on panel vans** —
  2300 × 2850 against a Fiat panel van's real 2050 × 2670. The 54G is already 2050 and
  only its height is out.

## Identity

`manufacturer_range` is **`Motorhome`** or **`Van`**, from the export — not the site's own
"Our motorhomes / Our panel vans" and not the book's "Motorhomes / Panelvans". Models are
the bare codes.

**FMLV writes the 60G as `60 G`, with a space**, and the other nine without one. The
matcher tokenises letters and digits so both reduce to the same bag and the product will
match either way; emitting the site's `60G` proposes a one-character rename that is
probably worth taking, but it is the reviewer's call rather than the adapter's.

## Body type

Motorhomes are 2.85 m coach-built low profile — FMLV agrees on all seven. Vans are 2.67 m,
above the 2300 mm threshold, so `campervan_high_top`; the **lacquered pop-up roof is a
£6,080 option**, so by the settled rule it never changes the type. FMLV agrees on all
three.

## First run — 10 September 2026, run #70

**10 collected, 10 matched, 0 new, 0 disappeared**, in 17.9 seconds over eleven fetches.
21 proposals and 109 fields verified unchanged, which is exactly what the survey
predicted plus two things it did not:

* the **`60 G` → `60G`** model tidy-up, which the requester approved on 10 September;
* the 63T's `mh_length_mm` arriving as an **in-scope field not found** — FMLV's own 6360
  shown beside "nothing scraped", because the self-check discarded the page's 5990. That
  is the field working, not failing.

Prices and payloads agreed on all ten, so nothing was proposed for either. The habitation
findings produced **the floorplan pointer on all ten and nothing else**, which is correct:
findings are recorded for new products only, and there are none.

The self-check fired once, on the page it was built for:

```
[Van 63T] LENGTH DISCARDED and left for FMLV's own figure: the page states 5990mm but
the model code implies about 6300mm, a 310mm gap against a 150mm tolerance
```

**Superseded on 10 September**, by the model strip described above. The next run reads
the 63T's length as 6360 and narrates the repair instead:

```
[Van 63T] LENGTH TAKEN FROM THE MODEL STRIP (6360mm) because the page states 5990mm
but the model code implies about 6300mm ...
```

That agrees with what FMLV already holds, so the in-scope-field-not-found on the 63T
disappears and no length is proposed on any of the ten.

Three products were hand-checked against both the page and Pilote's documents — 75TB,
54G and 60F — on length, width, height, payload, derived MRO, price, seats and berths.
All three agree on all eight.

## Still unverified

* **Whether id 103 `Joa Camp` still holds products.** If it does, they are the same
  vehicles under the old brand and would need archiving rather than being left to look
  like a parallel range.
* **Model year changeover.** The 2027 collection is dated 25 May 2026 and the price list
  1 June 2026, so Joa move earlier than the NEC-driven British brands. Not yet observed
  across a rollover.
* **Whether the site ever gets the van prices.** If it does, the two constants can go.
