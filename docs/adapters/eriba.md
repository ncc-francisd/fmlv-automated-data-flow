# Eriba — site survey

Surveyed 7 September 2026 against the **2027 model year** UK site at `www.eriba.com/gb/en`.
Twenty-first manufacturer, and the third caravan brand after Bailey and Swift.

**No adapter has been written yet.** This document and the `config/manufacturers.csv` row
are the whole of the work so far; nothing is registered in `src/adapters/`, so Eriba does
not appear in the review app's trigger dropdown. Two decisions are waiting on the requester
before stage 2 — [body type](#the-open-question-roof-type-is-not-uniform-and-twelve-of-eighteen-lift)
and [the NCC supplier name](#what-is-still-unverified) — and one of them changes what is
emitted on twelve of the eighteen products.

Eriba is an **Erwin Hymer Group** brand, built in Germany. **18 caravan layouts across 3
ranges.**

| Range | Layouts | Roof | Height |
|---|---|---|---|
| Touring | 310, 420, 430, 530, 540, 542 | Pop-up roof | 227 cm |
| Touring | 620, 630, 642 | Sleeping roof | 227 cm |
| Feeling | 425, 442, 470 | Sleeping roof | 225 cm |
| Novaline | 442, 465, 470, 485, 495, 515 | Fix roof | 254 cm |

The **Eriba Car** campervan at `/gb/en/models/camper-vans/eriba-car` is deliberately out of
scope — see [scope](#what-the-requester-brought-to-the-survey). It would be a second module
with `VEHICLE_CLASS = VehicleClass.MOTORHOME`, and it has its own UK price list at
`/eriba/drucksachen/preislisten/campervans/eriba-camper-vans-gb_en.pdf`.

## What the requester brought to the survey

Blanca, 7 September 2026, supplied before any fetching:

- **`https://www.eriba.com/gb/en`, and the rule that `/gb/` paths are all UK.** Correct, and
  it saved the survey from ever going near another market. The sitemap serves eleven
  market-and-language pairs off one file and `/gb/en` is 29 of its 328 URLs.
- **Caravans only for now — no motorhomes.** Eriba build one campervan (the Eriba Car) and
  no motorhomes, so in practice this excludes exactly one range, and it is excluded by
  product area rather than by guesswork: the caravans sit under `/models/caravans/` and the
  campervan under `/models/camper-vans/`.
- **A German brand that also sells into the UK**, which is what made the price basis and the
  currency the first things to check rather than the last.

To which the repository added, from the Etrusco and Bürstner rows:

**Eriba is a "non-core" EHG brand.** Etrusco, Bürstner, Carado and Eriba are European brands
of which only a selection of the full European range reaches the UK, and per
[`README.md`](README.md) the `/gb/en/` path **is** the UK range. So eighteen layouts is not a
short parse of a longer European roster — it is the roster. The contact, Emma Hughes at EHG
UK, covers all four brands, and her note on the internal list reads *"EHG will notify us"*:
they push updates rather than us polling. As with Etrusco, the strategy is to build against
the site and re-run, not to write to the manufacturer.

## Where the data lives: the UK price list, because the website only holds half the range

The answer [`README.md`](README.md) tells you to ask first — *is there a brochure or price
list PDF?* — is yes, and unusually it is also the right answer, because the website is
**structurally incomplete**.

`/gb/en/service/brochures` offers two price lists and a parts catalogue. The caravan one is
what this survey is built on:

```
Price list | ERIBA Caravans (English for UK) - Valid from 01.07.2026    PDF | 1.89 MB
  -> /eriba/drucksachen/preislisten/caravans/eriba-caravans-gb_en.pdf
```

29 pages. Page 1 reads `ERIBA CARAVANS 2027 / Price list for UK and IRL - Valid from 1 July
2026`, so the **model year is 2027** and the document and the card that links it agree — no
repeat of the Etrusco case where the filename, the footer and the page label said three
different things. The filename carries no year at all, which is the safer failure: there is
nothing to mislead anyone.

The four pages that matter are the `PRICES AND TECHNICAL DATA` spreads — pages 5 and 6 for
Touring, 16 and 17 for Feeling and Novaline — each setting four or five layouts side by side
in columns.

### The Touring range page publishes no technical data at all

This is the finding that decides the source, and it took checking a second market to be sure
of it. `/gb/en/models/caravans/eriba-touring` is 455 KB of marketing — awards, colours,
upholstery, equipment lines — with **no floorplan slider, no spec tables, and no
`selectedModelId` anywhere**. Its "Floor plans" section simply does not exist.

The instinct is to read that as a UK omission, given the non-core rule above. It is not: the
**international English page at `/de/en/models/caravans/eriba-touring` is the same 451 KB
page with the same absence**, so it is a site-wide template difference. The configurator at
`/gb/en/configurator/touring` is a 42 KB JavaScript shell with no data in the served HTML.

So nine of the eighteen layouts — half the range, and the range Eriba is famous for — exist
on the website only as a range-level "from" summary. The price list is the only source that
covers them.

The other two ranges do publish per-layout data, in the shape Dethleffs uses: each layout is
a `b-floorplaninteractive__slide` carrying `<h2 class="b-floorplaninteractive__model">`, a
Technical Data modal repeating the name in an `m-heading__subline`, and a run of
`has-columns--1+` tables whose rows are clean two-cell `<td>label</td><td>value</td>` pairs.
Every layout's block is rendered **twice** in the served HTML, so read them into a dict and
let the duplicate collapse. It is plain server-rendered HTML: `needs_javascript=no`.

### What the two sources are for

**The price list is the source. The website's nine layouts are the verification** — and they
verify it about as well as two sources can:

> The website and the price list agree on **165 of 165 comparable values** across the nine
> Feeling and Novaline layouts and about nineteen fields each. The only differences are the
> website appending a `(○)` standard-equipment marker to an otherwise identical value.

That single number does two jobs. It shows the PDF is **not** a model year behind the site,
which is the standing assumption [`README.md`](README.md) requires you to disprove before
building on a document. And it shows the columnar splitter is **correctly aligned**, on nine
layouts, before it is trusted on the nine Touring layouts where nothing can check it. An
adapter should keep doing this every run and narrate any disagreement, with the website
winning per the general rule.

## What one layout looks like

Touring 310, from page 5, with the four columns of that page reduced to one:

```
                                              Touring 310
Price £                                        25,170.-
Axle                                           Mono
Length / Width / Height (cm)                   506 / 200 / 227
Body length (exterior) (cm)                    371
Interior length (cm)                           366
Roof type                                      Pop-up roof
Headroom in living area (cm)                   195
A-measurement awning (cm)                      635
Mass in running order (-/+ 5%) (kg)*           820 (779 - 861)*
Manufacturer-specified mass for optional
equipment (kg)*                                92
Unladen weight, approx. kg                     779
Technically permissible maximum laden mass     1000
Berths                                         3
Refrigerator volume incl. freezer (l)          81 (10)
Heating type                                   Gas heating, 3.5 kW
Fresh water supply (l)                         30
```

## All four caravan lengths are published, and distinctly labelled

[`README.md`](README.md) warns that getting shipping and exterior body length the wrong way
round is "the most plausible single mistake available". Eriba makes it unusually hard to get
wrong, because all four appear in the same table under four unambiguous labels:

| FMLV field | Eriba's label | Touring 310 |
|---|---|---|
| `shipping_length_mm` | first figure of `Length / Width / Height (cm)` | 5060 |
| `exterior_body_length_mm` | `Body length (exterior) (cm)` | 3710 |
| `internal_length_mm` | `Interior length (cm)` | 3660 |
| `awning_length_mm` | `A-measurement awning (cm)` | 6350 |

Shipping exceeds exterior body on **all eighteen**, as `validation` requires, and the
difference is a consistent 123–135 cm of drawbar. The awning measurement exceeds the body
length everywhere, exactly as that file predicts it would.

Two notes. Everything is in **centimetres**, so every figure is ×10 — and `Interior width
(cm)` and `Maximum nose weight (kg)` have no FMLV column, so they are read only as
context. And `exterior_body_length_mm` is **out of automated scope** per
[`README.md`](README.md), on the grounds that Bailey do not publish it and the requester
reads that as an industry trend. **Eriba does publish it**, and that file requires the
question to be asked rather than assumed either way — so it was asked, and the requester
approved collecting it on 7 September 2026. It is in scope for this adapter, because the
figure sits under its own label beside the other two lengths and so carries none of the
ambiguity the scope rule guards against.

## The self-check: a printed tolerance band, and a payload decomposition

Eriba publishes **two** redundancies against itself, which is one more than most.

**The primary check is the ±5% band on the mass in running order**, the same device as
Sunlight and Etrusco. The mass is printed with its legally permissible range in brackets:

```
Mass in running order (-/+ 5%) (kg)*    820 (779 - 861)*
```

820 × 0.95 = 779 and 820 × 1.05 = 861, so the band is a *function* of the mass. A slipped
column pairs one layout's mass with another's band and fails immediately. **All eighteen
pass**, within 1 kg of the printed rounding — allow 3 kg of slack as `etrusco.py` does.

The document explains the mechanism itself, which is worth quoting into the provenance:

> *"Deviations of up to ±5% of the mass in running order are legally permissible and
> possible. The permissible range in kilograms is stated in parentheses after the mass in
> running order."*

**The second check is the payload decomposition**, and it is what settles the two caravan
payload columns. `MTPLM − MRO − manufacturer-specified mass for optional equipment` leaves a
positive personal-effects payload on all eighteen, from 88 kg to 128 kg, consistent with the
EU minimum-payload formula in Regulation 2021/535 that the document cites on page 27.

This needs care, because **the same label means something different on the motorhome side.**
There, [`README.md`](README.md) records "Manufacturer-specified mass for optional equipment"
as a trap: a cap on factory-fitted extras and emphatically *not* payload. For a caravan there
are two payload columns that must sum to `MTPLM − MRO`, and Eriba's own footnote describes
this figure as exactly the optional-equipment half of that sum:

> *"The mass for optional equipment specified by the manufacturer is an imputed value
> determined for each type and layout by which ERIBA specifies the maximum weight available
> for factory-fitted optional equipment. The purpose of limiting optional equipment is to
> ensure that the minimum payload, i.e. the legally required free mass for baggage and
> retrofitted accessories, is actually available."*

So the reading is `optional_equipment_payload_kilograms` = the published figure and
`personal_effects_payload_kilograms` = the remainder. That is a **different** answer from the
one Bailey, Adria and Swift needed, where the manufacturer published a single figure and it
was taken as the personal-effects total, so it should be confirmed before it is emitted.

There is a third, weaker redundancy: `Unladen weight, approx. kg` sits exactly 41 kg below
the MRO on every Touring layout and exactly 61 kg below it on every Feeling and Novaline —
the gas and water allowance, which differs because Touring carries 2 × 5 kg bottles and 30 l
of water against the others' 2 × 11 kg and 45 l. It is a real check but a range-dependent
one, and the band above is cleaner. FMLV's `mro_kilograms` takes **Mass in running order**,
not this figure.

## Roof type is not uniform, and twelve of eighteen lift — but all eighteen are rigid

**Settled by the requester, 7 September 2026: `type_rigid` on all eighteen.** The reasoning
is now a cross-manufacturer rule in [`README.md`](README.md#body-type-is-nearly-always-type_rigid)
— a lifting roof does not make a caravan `type_pop_up`, because an Eriba is a hard-sided
rigid caravan with a lifting panel while `type_pop_up` reads to a UK audience as a folding
camper. The roof still belongs in the `body_type` provenance snippet, quoting the row below,
so a reviewer can see why the obvious alternative was refused.

Every layout carries a `Roof type` row, and it does not follow the range:

| `Roof type` | Layouts | Count |
|---|---|---|
| `Pop-up roof` | Touring 310, 420, 430, 530, 540, 542 | 6 |
| `Sleeping roof` | Touring 620, 630, 642; Feeling 425, 442, 470 | 6 |
| `Fix roof` | Novaline 442, 465, 470, 485, 495, 515 | 6 |

A neat 6/6/6 split, and the practical effect is that **only the six Novaline are
unambiguously `type_rigid`**. The other twelve have a roof that raises — and the Feeling and
the three big Tourings put a bed in it, which is what `Sleeping roof` means and why those six
also carry a `Bed dimension: Sleeping roof, L x W (cm)` row of `193 x 150`.

`CaravanBodyType` offers `type_rigid`, `type_folding`, `type_pop_up` and `type_micro`, and
Eriba was the first brand with a plausible claim on `type_pop_up`. The arguments as they were
put, since the losing one is the more intuitive of the two and will come round again:

- **For `type_pop_up`:** the manufacturer's own spec row says `Pop-up roof`, in its own
  words, on six of them. The Touring range page sells "Pop-top roof" and "Low height (226
  cm)" as headline features. On the campervan side the analogous distinction is drawn from
  exactly this kind of standard-fit wording.
- **For `type_rigid` throughout:** an Eriba Touring is a rigid-bodied, hard-sided caravan
  with a lifting roof *section*. In UK trade usage a pop-up or folding caravan means a
  Pennine- or Conway-style folding camper, which is a different kind of vehicle, and a
  reader filtering FMLV for `type_pop_up` is probably looking for those. FMLV's own field
  guide may well intend the term that way.

The evidence could not settle it — it was a question about what FMLV's column means, which
only the NCC side knew, and the second argument won.

**Related, and this one the evidence does settle: none of them is a `type_micro`.** Five
layouts are at or under the 1250 kg threshold — Touring 310 at 1000, Touring 420 and 430 at
1100, Feeling 425 and Novaline 465 at 1200 — but the words "micro" and "compact" appear
**nowhere** in the price list, and `CaravanBodyType`'s own docstring is explicit that weight
alone is not the test. Eriba's nearest claim is an award for "1st place in the compact class
category", which is a magazine's category and not the manufacturer naming a body type.

## Price: sterling and on-the-road, and the PDF's own footnote is wrong about both

Prices are per layout, in sterling, from £25,170 (Touring 310) to £33,600 (Touring 620, 630
and 642). No conversion is needed — the exchange-rate problem that is the worst data in the
Morelo adapter does not arise.

But the document **libels itself**, and anything asserting on the footnote would refuse a
perfectly good price list. Page 24 reads:

> *"All prices are recommended retail prices in **Euro** including legal applicable VAT **ex
> works**. Freight from Germany, first registration fee and handover are not included and
> will be charged separately."*

That is un-localised boilerplate from the German master document, and four things contradict
it: the title is `Price list for UK and IRL`, every figure is printed with a pound sign, the
Silver Edition page quotes a "2.840 **GBP**" price advantage, and the figures match the
website's GBP figures exactly. The word `EUR` appears **zero** times in the document.

The authoritative basis statement is the website's own tooltip, which is also the basis FMLV
prefers:

> *"All prices are recommended retail prices in GBP including legal applicable VAT, On The
> Road Charges (OTR including delivery from Germany, registration and PDI). Possible import
> duties are not included and will be charged separately."*

So: **on-the-road, including VAT, sterling** — recorded here because
[`README.md`](README.md) asks for the basis to be written down wherever it is known, so that
a change of basis is diagnosable in seconds instead of reading as a range-wide price move.

**This inverts the Weinsberg trap** rather than repeating it. There, a card reassuringly
labelled "Price list, UK" linked a euro document, and the lesson was to read the currency out
of the document rather than trusting the label. Here the label is right and the *footnote* is
stale. The check that survives both is the same one: assert on what the price column actually
shows — the pound sign and the title — and refuse a document whose figures are quoted in
euros. Do not assert on the boilerplate.

The range-level `Price from` figures on each range page give a free cross-check of the kind
Etrusco provides, and all three hold: Touring from £25,170 is the 310, Feeling from £27,390
is the 425, and the `Technically permissible total mass from` and `Length from` figures agree
with the cheapest layout in each range too.

## Parsing: the columns are recoverable, but not from coordinates

The spec pages are columnar, four or five layouts abreast, which is where
[`README.md`](README.md) locates the real risk — misalign them and you get plausible,
internally consistent caravans carrying each other's weights.

**`extract_positioned_text` cannot carry the alignment here.** On page 5 pypdf places about
70 of 167 runs and reports **97 of them at (0, 0)**, including the whole header row as a
single run. This is the Morelo problem, not the Sunlight one, and coordinates have to be
abandoned rather than trusted blindly.

The line-based text, though, is **complete**. So the shape that works is: locate a known
label, read to the start of the *next* known label, and split that span with a **typed regex
for the field**, requiring **exactly one value per model named in the page header**. Drop the
page otherwise, per the standing rule — never guess at the alignment. On all four spec pages
this yields 13 of 13 fields at the right cardinality, and all eighteen band checks pass,
which is the evidence that it is right.

Four traps, all of which a whitespace split would walk into:

- **Values contain spaces.** `185 R14 C 102 L`, `Gas heating, 3.5 kW`, `Electric boiler 5 l`,
  `188 x 73 - 53 / 188 x 73`. Splitting a row on whitespace is not an option, which is why
  each field needs its own pattern anchored on its own shape.
- **Labels wrap across lines.** `Manufacturer-specified mass for optional equipment` and
  `(kg)*` arrive as two lines with the values trailing the second, and
  `Clearance of storage compartment / garage doors or flap,` / `W x H (cm)` does the same.
  Matching a label prefix and reading to the next label handles this for free.
- **Blank cells exist — but only in rows FMLV does not need.** Page 16 prints
  `Bed dimension: Sleeping roof, L x W (cm)` with **three** values against four models,
  because the Novaline has no such roof, and **which** model is missing cannot be recovered
  from the line. This is Rimor's "present and unattributable" failure in miniature. So **do
  not parse the four bed-dimension rows or the storage-compartment clearance from these
  pages**; `bed_types` belongs with a reviewer and a `reviewer_reference` floorplan pointer.
  Every field FMLV *does* need carries one value per model on all four pages.
- **Page 15 does not extract.** The Touring Silver Edition price table yields
  `BASE PRICE (incl. VAT) £ £ £  3.0 3.0` and `PRICE xxxxx`. It is an edition and options
  table rather than a layout roster, so nothing is lost — but it is the kind of page that
  invites a parser to try. Do not.

## What else the source gives, and the roster

Beyond the fields above, each layout publishes `Heating type` (`Gas heating, 3.5 kW`
throughout), `Refrigerator volume incl. freezer (l)` as `81 (10)` — volume with the freezer
compartment in brackets, so `fridge_freezer` is evidenced in words on all eighteen —
`Burner hob`, `Gas bottle storage`, `Fresh water supply (l)`, `Warm water tank (l)` and
socket counts. `adapters/habitation.py` should be given these lines rather than a
brand-specific reimplementation.

**`Axle` is `Mono` on all eighteen**, so `twin_axle` is `False` throughout — including the
three 1500 kg Novalines, where a tandem would not be surprising.

**The roster needs no reconciliation, unusually.** The sitemap index points to one file,
`sitemap.site_9.xml`, whose 29 `/gb/en` URLs include exactly three caravan range pages and
one campervan page; the price list's contents page lists the same three ranges; and the
website's nine layouts are a subset of the price list's eighteen with no layout appearing in
one and not the other. Nothing is hiding in an orphan page — `robots.txt` allows everything
and there are only three PDFs on the site.

Expect **18 products** and compare every run against that number.

## What is still unverified

- **`ncc_supplier_name` is not known, so the FMLV baseline export has not been fetched.**
  This is the one genuinely blocking gap. It means the question
  [`README.md`](README.md) says to answer before choosing identity strings — *what does FMLV
  already call these vehicles?* — is unanswered. `manufacturer_range` and `model` are
  presumably `Touring` + `310`, but the export decides that, not this document, and Weinsberg
  is the warning: it is filed under `fmlv_manufacturer` `Knaus Tabbert AG` with display name
  `Weinsberg`, so a Hymer parent-company string is entirely possible here.
  `fmlv_manufacturer` is drafted as `Eriba` from `resources/manufacturers-full-list.csv` ID
  196 and **must be checked against the export before an adapter is registered.**
- **Whether any of these products is already in FMLV**, and so whether the first run proposes
  eighteen new products or matches an existing set. Also blocked on the export.
- **The optional-equipment payload reading**, per
  [the self-check](#the-self-check-a-printed-tolerance-band-and-a-payload-decomposition).
  Put to the requester on 7 September 2026 with a recommendation and not contradicted, so it
  is being taken as agreed rather than as confirmed: emit the published figure as
  `optional_equipment_payload_kilograms` and the remainder as
  `personal_effects_payload_kilograms`. Worth re-confirming when the first run's numbers are
  in front of a reviewer, since it is the one field here that departs from what Bailey,
  Adria and Swift needed.

Settled since the checkpoint, and recorded above rather than here: `body_type` is
`type_rigid` on all eighteen, and `exterior_body_length_mm` is in scope.
- **The positional habitation fields** — `sleeping_area`, `kitchen_location`,
  `lounge_location`, `bathroom_layout`. The price list names bed dimensions but not
  positions, and the floorplan drawings are images on the range pages, so these need
  `reviewer_reference` pointers. Note the Touring range page has no floorplans at all, so
  there is no per-layout drawing to point a reviewer at for nine of the eighteen — the
  configurator may be the only place, and it needs JavaScript.
- **When the 2028 price list lands.** This one is valid from 1 July 2026 and the model year
  rolls over July to early September, so per [`README.md`](README.md) re-check at the end of
  September.

## What this adds to the general pattern

Three things worth promoting to [`README.md`](README.md) if a second brand shows them:

- **A range page can publish no technical data at all, and the fix is to check another
  market before concluding anything.** "No single menu is a complete roster" covers menus
  that are short; this is a whole range whose page carries none of the data its siblings'
  pages do. Checking `/de/en` is what separated "the UK does not get this data" from "nobody
  does".
- **A document can be wrong about its own currency and price basis.** Weinsberg established
  that a label can lie about a document; this establishes that a document's *own boilerplate*
  can lie about the document, in the safe direction, and that an adapter asserting on the
  footnote rather than the price column would refuse a good source.
- **Two sources covering different halves of a range can still verify each other.** The
  website covers 9 of 18 and is not needed as a source at all, but running it every run and
  comparing gives a live check on the columnar parse of the other 9, which nothing else can
  check. Cheap, and it is the only reason the Touring figures can be trusted.
