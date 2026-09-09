# Carado — site survey

Surveyed 9 September 2026. FMLV manufacturer id **92**, name `Carado`, display name
`Carado`, NCC supplier name `Carado` — all four confirmed against
`resources/manufacturers-full-list.csv` and by the requester.

German, part of the Erwin Hymer Group, and on the **same server-rendered platform as
Etrusco and Dethleffs**. No JavaScript, no PDF, no login.

## What the requester brought to the survey

All of this on 9 September 2026, and every item of it changed the design:

* **30 products in FMLV**, no caravans.
* **The range names carry the build style**, and FMLV's are `Alcoves`, `Campervan`,
  `Campervan Pro`, `Semi-integrated`, `Integrated`, `Van`.
* **`Van` is not a van** — *"which isn't a van but a low profile motorhome"*. The site's own
  copy agrees; see [Body type](#body-type-comes-from-the-construction-not-the-path).
* **Some models are the same layout on a different base vehicle**, sold as separate
  products at separate prices — *"Peugeot for Fiat, and you select that, but the model
  number doesn't change, the base does"*. This is the site's main trap and it is worse than
  described: see [More than one vehicle per page](#the-trap-four-pages-carry-more-than-one-vehicle).
* **The PRO element belongs in the range name, not the model.** FMLV is inconsistent about
  it and the inconsistency is a mistake to correct: see [Identity](#identity-the-pro-tier-belongs-in-the-range).
* He also volunteered that he had **missed the over-cab beds** when he said the range was
  only campervans and low profiles. It is not; there are three alcoves.

## The source: the website, and specifically two pages of it

### The roster page

`/gb/en/motorhomes/model-comparison` lists **every model grouped under its range
headline**, each with a price and a stable numeric id:

```html
<div class="o-compare-form__model-group" data-type="3763007">
  <h2 class="o-compare-form__group-headline">Integrated</h2>
  <div data-controller="CompareListItem" data-id="3779184">
    <span class="m-compare-list-item__title">I338</span>
    <span class="price">from £78,190</span>
```

| Range headline | Models |
| --- | --- |
| `Integrated` | 2 — I338, I447 |
| `Semi-Integrated` | 8 — T135, T328, T447, T448, and T335/T338/T457/T459 `EDITION27` |
| `Vans` | 3 — V132, V337, V347 |
| `Alcoves` | 3 — A132 PRO, A361 PRO, A464 PRO |
| `Camper Vans` | 13 — CV540/600/640 plus their PRO and PRO+ tiers, CV541 PRO, CV601 PRO, CV595 4x4 X-EDITION |

**29 vehicles.** Against the requester's 30 in FMLV, which is the closest first-survey
match in the project so far.

### The layout pages

23 pages under `/gb/en/motorhomes/{body-style}/{slug}`, carrying everything FMLV needs in
plain tables — price, chassis, all three dimensions, both masses, seats, berths, plus a
per-layout floorplan on all but one of them. A real block, from `T447`:

```
Basic price incl. VAT                                  £66,290
Chassis                                                Fiat Ducato
Length | Width | Height (cm)                           741 / 232 / 290
Permitted number of seats (including driver)*          4 - 5 OPT
Mass in running order (kg)*                            2911 (2765 to 3057)*
Technically permissible maximum laden mass (kg) *      3500
Berths                                                 2 - 5 OPT
Refrigerator volume incl. freezer (l)                  78 (11)  156 (29) OPT
Heating type                                           Combi 6 E Electric
```

`OPT` is the optional marker throughout, and the **first** figure is the standard one —
the base-vehicle rule in [`README.md`](README.md), and the berth rule that takes the lower
of a range.

Carado publish no payload, so it is `MTPLM - MRO` as for Dethleffs and Etrusco. The
`Manufacturer-specified mass for optional equipment` row sits where payload would and is
**not** payload — the same trap as those two.

## The self-check: two renderings of every price

The roster page and the layout pages publish the price independently, so every product can
be checked without a second source. Run on 9 September 2026:

**25 of 28 agree exactly.** The three that do not are all three Alcoves, and they disagree
by a consistent amount:

| model | roster page | own page | difference |
| --- | --- | --- | --- |
| A132 PRO | £61,990 | £58,590 | −£3,400 |
| A361 PRO | £65,590 | £62,090 | −£3,500 |
| A464 PRO | £68,190 | £64,790 | −£3,400 |

That is the check earning its keep on first use. It is a *source disagreement*, not a parse
failure, so the right treatment is not to drop the product — these are three real UK
vehicles with three FMLV rows — but to propose it with **both figures in the provenance**
and narrate the disagreement, the way `rimor` says which of two figures a discounted page's
price is.

### Why the Alcove pages are the suspect ones

Three independent signs point the same way:

* They are the **only three pages with no equipment accordions at all** — 7 tables against
  23 or more everywhere else.
* They publish **Citroën Jumper** where FMLV holds `Fiat`. Same Stellantis van, different
  badge, but it means their content has a different provenance from the rest of the site.
* Their price id (`price-info-3777770`) is one of a **duplicated pair** of `Alkoven` series
  in the configurator API — 3773302 and 3777770 carry identical models.

**So treat their weights and dimensions as unverified too, not just the price.** Unresolved
at the checkpoint: which price is authoritative is the requester's call.

The secondary check is the printed ±5% mass band, `2911 (2765 to 3057)*`. It is a function
of the MRO, so it catches a misread digit but not a slipped column — the same weak check as
Eriba's and Laika's, and the price cross-check is the better one.

## The trap: four pages carry more than one vehicle

The requester warned about a chassis swap. It is more than that:

| page | vehicles | chassis | prices |
| --- | --- | --- | --- |
| `cv540` | CV540, CV540 PRO | Peugeot Boxer, Fiat Ducato | £49,990 / £57,990 |
| `cv600` | CV600, CV600 PRO, CV600 PRO+ | Peugeot, Fiat, Fiat | £51,190 / £58,690 / £63,190 |
| `cv602-pro` | CV602 PRO, CV602 PRO+ | Fiat, **Fiat** | £59,190 / £63,490 |
| `cv640` | CV640, CV640 PRO, CV640 PRO+ | Peugeot, Fiat, Fiat | £53,090 / £60,690 / £64,990 |

`cv602-pro`'s two are **both Fiat Ducato, £4,300 apart** — so the PRO tier is a genuine
equipment level, not a badge on a chassis, and it has its own `Edition equipment` accordion
to prove it. A parser taking one price per page would lose 6 of the 29 vehicles and
mis-price four more.

**The join is positional.** All the `<h1>`s sit together at the top of the page, naming the
vehicles in order, and each vehicle then has its own `Technical data` section further down.
The Nth heading belongs to the Nth specification block. That has to be asserted rather than
assumed: if the counts differ, **skip the page and narrate it** — the cardinality rule in
[`README.md`](README.md).

## Identity: the PRO tier belongs in the range

The requester's ruling, 9 September 2026, with two real FMLV rows in front of him:

> *"Really, the PRO element in the name should be part of the range name. Unfortunately we
> have got some where the PRO element has been put in the model name. The Carado Campervan
> CV640 and the Campervan PRO CV602 show that the PRO element needs to be in the range."*

And on the alcoves specifically: *"the Alcoves A464 PRO model should really have been
entered as Alcoves PRO, model A464."* So FMLV's own `Alcoves` + `A464 PRO` is a mistake the
adapter should propose a fix for, not copy.

| site publishes | FMLV range | FMLV model |
| --- | --- | --- |
| `CV640` | `Campervan` | `CV640` |
| `CV602 PRO` | `Campervan PRO` | `CV602` |
| `CV600 PRO+` | `Campervan PRO+` | `CV600` |
| `A464 PRO` | `Alcoves PRO` | `A464` |
| `T447` | `Semi-integrated` | `T447` |
| `I338` | `Integrated` | `I338` |
| `V337` | `Van` | `V337` |

Three things this table encodes, all of them decisions:

* **The model keeps its letter prefix.** `CV602`, not `602` — confirmed from FMLV's own
  rows. Only the PRO element moves.
* **FMLV is internally inconsistent about a space**: it holds `CV602` and `CV 640`. The site
  writes both without, so the adapter emits `CV640` and the run proposes the tidy-up.
* **`EDITION27` and `4x4 X-EDITION` stay in the model.** They are model-year and drivetrain
  editions rather than a PRO tier, and dropping a published qualifier would be inventing.
  Unconfirmed against FMLV, which has no example — worth watching on the first run.

`Campervan PRO+` is the one range string not directly confirmed; the requester said "Pro
Plus" aloud and FMLV shows `Campervan PRO`, so the site's own `PRO+` token is the
consistent choice.

## Body type comes from the construction, not the path

The path names mislead in two directions, so neither is read. The **body construction
lines** in each page's `Exterior setup` list are what decide it:

| range | construction | body type |
| --- | --- | --- |
| `Alcoves` | GRP roof and rear wall, aluminium sidewalls, 314 cm tall | over-cab bed |
| `Integrated` | same | A class |
| `Semi-Integrated` | same | low profile |
| `Vans` | **same**, but 214 cm wide instead of 232 | low profile |
| `Camper Vans` | none of it — rear doors, flyscreen door, lashing rings | campervan high top |

`V337` settles the requester's warning in the site's own words: *"the advantages of a
semi-integrated model in a compact format — only 2.14 m wide"*, on a GRP body with 34 mm
walls. It is a narrow low profile, and the only thing van-like about it is the name.

Every camper van is 258–281 cm, so all thirteen clear the settled 2300 mm high-top
threshold. None has a standard elevating roof to complicate it.

## The configurator is a trap, not a source

Carado is on the shared EHG platform — `brandKey: carado`, `locale: en_GB` — so
`ehg_configurator` reaches it. **It should not be used**, for three reasons found on
9 September 2026:

* **No prices at all.** Neither `grossPrice` nor `price` is in its technical data.
* **It duplicates its series within one model year**, which is worse than the cumulative
  index `ehg_configurator` was written to defend against. For 2027 it returns two identical
  `Alkoven` series, two identical `Teilintegrierte`, two identical `Van`, and two identical
  nine-model `Camper Van` series.
* **It lists four alcoves the UK site does not sell** — `A328`, `A364` and both their PRO
  versions.

52 API models collapse to 33 distinct, against the website's 29. The website over-rules,
which is the standing rule in [`README.md`](README.md) anyway.

## Habitation: richly stated, and cleanly split

Standard and optional equipment sit in **separate accordions** (`Standard equipment`,
`Optional equipment`, and on the PRO+ tiers `Edition equipment`), so the
`habitation.usable_lines` rule about never reading a paid option as standard is enforced by
structure rather than by a price regex. Per-category tables inside each: `Base vehicle`,
`Exterior setup`, `Comfort`, `Installations`, `Heating | gas supply`, `Kitchen`, `Bathroom`,
`Soft furnishing`.

What the copy settles outright:

* **Refrigeration** — `Kitchen: Fridge 78 l with 11 l freezer compartment`, and the
  specification row `Refrigerator volume incl. freezer (l) | 78 (11) 156 (29) OPT`. Take
  the first figure; the second is the optional larger fridge.
* **Separated washroom** — `Bathroom: Spacious bathroom with separate shower on the
  opposite side`.
* **Heating** — `Heating Combi 6 E (with el. heating element)`, which `habitation` already
  reads as warm air via `combi`.
* **Microwave** — absent everywhere, while an **oven is itemised** (`Oven in kitchen (only
  in conjunction with 156 l fridge)`). That earns the itemised-table exception in
  [`README.md`](README.md), so it is reported `No` with the reasoning.

These reach the reviewer as **findings**, not proposals — see
`src/product_model/findings.py`.

## What the build found — 9 September 2026

**29 of 29 products, none dropped, no blank spec field on any of them, 606 fields with
provenance.** Ranges as FMLV will hold them: `Alcoves PRO` 3, `Campervan` 4, `Campervan
PRO` 6, `Campervan PRO+` 3, `Integrated` 2, `Semi-integrated` 8, `Van` 3. Body types: 13
campervan high top, 11 low profile, 3 over-cab bed, 2 A class. Habitation findings:
refrigeration on 29, microwave on 29, heating on 26, a separated washroom on 5.

Three things the survey had not seen, each of which would have shipped a wrong product:

### The site has two specification templates

`cv601-pro` publishes its whole specification as a **definition list** — `<dd
class="m-facts__label">` / `<dt class="m-facts__info">` pairs — where the other 22 use
tables. Its 19 tables are the equipment lists only. A parser that knew about tables alone
lost that vehicle silently, and 28 of 29 looks like success.

The other 22 pages carry a **six-item** facts card *beside* their tables, so the fallback
must only fire when the tables gave nothing — otherwise a six-row summary would replace a
25-row specification.

### A floorplan is told from a photograph by its preset, not its name

Every image on the page is served through the same `/image-thumb__<id>__<preset>/` resizer,
so the preset is the only signal. Carado's drawings all use `wls-carado-floorplan-large`.
Without requiring that token the parser matched the **photography** as well, and reported a
floorplan for all 29 — some of which would have been pictures of a lounge behind a link
labelled "Floorplan".

With it: **28 of 29**. `CV601 PRO` publishes no drawing at all — its only presets are
`wls-carado-stage` and `wls-ambient-*` — and the run narrates that rather than pointing at
a photograph.

This is the [`laika.md`](laika.md) lesson with the opposite conclusion, and the distinction
is worth keeping: a *filename* is metadata about an upload and says nothing, but a
*preset* is the site's own statement of what the image is for. Markup, not naming.

### A dimension row's label is not a statement about the vehicle

`Lying area Alcove / pull-down bed / Clever-lift bed (cm) | 195 x 140 - 110 OPT` is a
measurement heading listing three things a Carado might have. Fed to `habitation` it gave
**14 of the 29 products a bed type read off it** — and every one was wrong. `Bed dimension
middle` and `Bed dimension rear` are the same shape.

So only the two specification rows that state a feature are passed
(`HABITATION_SPEC_LABELS`): the refrigerator volume and the heating type. The equipment
lists go in wholesale, because every line there really is a statement about this vehicle.
Carado now yields no bed types at all, which is correct — the copy never names a bed, and
the floorplan pointer is what answers it.

The same class of mistake as Rimor's `Tags` metadata line and Laika's misfiled filename:
text that looks like content and is not.

### And one honest gap

**The three Alcoves yield no heating.** Their pages have no equipment accordions and no
`Heating type` row, so there is nothing on them to read — which is a fourth sign those
pages are stale, alongside the price, the missing equipment lists and the Citroën chassis.

## Still unverified

* **Which Alcove price is authoritative**, and whether their masses and dimensions are
  current at all. The requester's call; see the self-check above.
* **The `EDITION27` and `4x4 X-EDITION` model strings**, which FMLV has no precedent for.
* **`Campervan PRO+`** as a range string.
* **Whether FMLV holds the Alcoves' base vehicle as `Fiat` deliberately.** The site says
  Citroën Jumper on all three, so the run will propose the change; per
  [`README.md`](README.md) `Citroën` keeps its diaeresis and `fmlv_base_vehicle` already
  normalises it.
* **The 1-product gap** between the site's 29 and FMLV's 30 — expected to be a withdrawn
  layout, and the requester's `CV620`/`Campervan Pro Plus CV620` example suggests exactly
  that kind of older model. The first run against the real export resolves it as a
  disappearance rather than silence.
* **Model year changeover.** Not established for Carado; the sector rolls July to early
  September per [`README.md`](README.md), and the site is on MY2027 now.

## Cost

23 layout pages plus one roster page, all plain HTML, no JavaScript and no PDF — 24 fetches
for a full sweep.
