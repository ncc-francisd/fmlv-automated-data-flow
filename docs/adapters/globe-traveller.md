# Globe-Traveller — survey, 16 October 2026

An enquiry from **Globe-Traveller RV Sp. z o.o.**, Kraków, Poland —
`https://globe-traveller.eu/`. High-top campervans, twelve models across four series.

**Not in `resources/manufacturers-full-list.csv` and not on FMLV**, so there is no
manufacturer id yet and no registry row can be written. No adapter; this is the stage-1
checkpoint.

## The site is as good a source as any surveyed, with three holes in it

The structure is excellent. Every model has its own server-rendered page at
`/models/<series>/<model>/`, with a specification table laid out identically across all
twelve. No JavaScript, no PDF, no configurator — and the root of the site is already
English, with `/pl/`, `/de/` and `/fr/` as the translations.

Twelve models, which matches the requester's count exactly:

| series | models |
|---|---|
| **Explorer** | X, XS, Z, Z EVO |
| **Falcon** | XS, YS, Z |
| **Pathfinder** | X, Z |
| **Voyager** | X, XS, Z |

`/models/` carries all twelve as cards with a filter panel, so the roster is rediscoverable
per run rather than hardcoded.

## What each page publishes, verbatim

From `/models/explorer-series/explorer-x/`:

```
Specifications
  Model Series   Explorer Series
  Model          Explorer X
  No. of seats   2(3)
  Bed type       French
  No. of berths  2
Technical Details
  Base model                    Ducato / Boxer
  Engine power                  180 / 140 HP
  Automatic gearbox             Standard
  Permissible Max. Mass (PMM)   3500 kg
  Extended PMM (*Fiat only)     3820 or 4200 kg
Dimensions
  Lenght         636 cm          (their spelling)
  Width          206 cm
  Height         280 cm
  Internal Height 195 cm
Living area
  Main bed size  200 cm x 123 cm
  Additional bed N/A
  Fridge         90 l
  Bathroom       Integrated with toilet
  Shower tray    65 cm x 60 cm
  Toilet         Chemical or dry
  Double floor   16 cm
```

So FMLV's **range** and **model** are published as separate fields, the **MTPLM** is
published, and so are **length, width and height**.

### Three things it gets right

* **The MTPLM comes with its upgrades named as upgrades.** `PMM 3500 kg` with
  `Extended PMM 3820 or 4200`, so the base-vehicle rule applies cleanly: record 3500 and
  leave the heavier plates as the options they are. The VW-based Falcon offers
  `3820 or 4000` instead, so the figures are per base vehicle rather than global.
* **The body type is derivable.** Heights run 280–300 cm, so every one is over the 2300mm
  the settled rule puts a `campervan_high_top` above. The site calls it a *"Super-High
  roof"* itself.
* **The habitation findings are unusually well served** — fridge capacity in litres, the
  bathroom as integrated or separate, shower tray size, toilet type, double-floor depth and
  both bed sizes.

## The three holes, and all three are required fields

**No price, anywhere.** Not on a model page, not in the sitemap's 88 URLs. The footer
carries a **"Catalogues and prices"** link that has **no `href` at all** — a placeholder.
That is worth knowing when asking: the slot exists, so a catalogue and a price list are
things they intend to publish rather than things they have refused.

**No mass in running order.** The `PMM` is the MTPLM; nothing states what the vehicle
weighs empty.

**No payload.** Which follows, since payload needs the MRO.

`schema.REQUIRED` wants all three. For a manufacturer FMLV already held, they could be
left to carry over — but **this brand has no products at all**, so there is nothing to
carry over and a first upload would create twelve rows with three required fields blank.

### Consequently there is no self-check

`MTPLM - MRO = payload` is the test every strong adapter here leans on, and with only one
of the three published it cannot be run. As with Rolling Homes and Kaktus, the check would
have to be structural. **A price list that carried the MRO as well would fix both problems
at once.**

## The open question: `Ducato / Boxer` is two base vehicles

Every Fiat-based model states its base as **`Ducato / Boxer`** — a Fiat Ducato *or* a
Peugeot Boxer. The settled rule is explicit that **a different base vehicle is a different
product**, which would make the twelve models up to **twenty-four products**.

Nothing on the site resolves it, and there is no baseline to consult. It needs deciding
before a build, because it doubles or halves the whole roster. The Falcon series is on a
**VW Crafter** and does not have the ambiguity.

## Three smaller questions

* **`No. of berths: 2+2`** on six models, against a plain `2` on the others. The `+2` is
  not vague: those pages also carry an **`Additional bed`** with a size — `187 cm x 134 cm`
  — where the two-berth models read `N/A`. So the second bed exists and is listed as
  specification rather than as an option. **Recommendation: record 4**, since the berths
  rule takes the lower figure only where the upper needs options, and nothing here says
  this one does. Worth confirming.
* **`No. of seats: 2(3)` and `4(3)`.** The bracketed figure is unexplained. On the
  Bürstner precedent a parenthetical or "permitted" seat count is a ceiling rather than a
  fitment, so the plain figure is the one to take — but what Globe-Traveller mean by it
  should be asked rather than assumed.
* **The Falcon XS states no berth count at all** — the field is present and empty. One
  missing value out of twelve, which an adapter should narrate rather than guess.

## Verdict

**The website is a good source and the adapter would be straightforward — but it cannot be
built yet**, because three of FMLV's required fields are unpublished and there are no
existing products for them to carry over from.

What is needed is small and specific:

1. a **UK price list**, or any price list;
2. the **mass in running order** per model;
3. the **payload** per model, or just the MRO, from which it follows;
4. a decision on **Ducato versus Boxer** — one product or two.

With those, everything else is already on the page and parses cleanly.

## On creating a placeholder in Nova

The requester offered to create the brand with a false product to review against.
**That is not needed, and Beauer showed why**: the mock placed there on 15 October was
`active: No`, so the baseline scope excluded it and every scraped product arrived as new
regardless. `fmlv empty-baseline <manufacturer>` covers the no-baseline case by design.

What *is* needed, per the three-things rule, is the **manufacturer id** — the NCC's to
allocate — and the **supplier/exhibitor record**, which no upload can create.

---

# Addendum — the catalogue and price list, 30 October 2026

The requester supplied two FlipHTML5 flipbooks. **Both are machine-readable**, and between
them they close one of the three holes, half-close a second and answer the open question —
but they do **not** make the brand buildable, because the price they publish is the wrong
kind of price.

## Getting at them: FlipHTML5 hands over the original PDF

The viewers are at `public.globe-traveller.eu/books/<id>/`, and fetching that path
redirects to the site's home page. The route in is three steps, all plain HTTP:

1. `/<id>/index.html` — the directory redirects, the file does not;
2. `/<id>/javascript/config.js` — 50-60 KB, holding `pageCount`, the title, and
3. `"downloadconfig":{"pdf":{"isOriginPath":true,"url":"https://fliphtml5.com/api/download/download-file?bookId=<n>&type=1"}}`

That URL returns the **original PDF**, text and all — `%PDF-1.4`, no OCR, no browser.
Page images are hashed `.webp` under `files/large/` and are not needed.

| document | book id | pages | bytes |
|---|---|---|---|
| EN Globe-Traveller Catalogue 2026/2027 | 75073062 | 32 | 4.7 MB |
| UK Voyager / Pathfinder / Explorer Pricelist 2026/2027 | 18168864 | 8 | 350 KB |

So an adapter could **rediscover both per run** rather than carrying constants, which is
better than the `joa.py` arrangement Fleurette needed. The book ids would be the hardcoded
part, and `config.js` is the thing to re-read.

## The catalogue: every dimension, and the mass for three models only

Pages 6-29 are one spread per model, twelve in all — the same twelve as the website.

    Total length 636 cm
    Total width 206 cm
    Total height 280 cm
    Internal height 195 cm
    Technically permissible weight 3 500 / 3 820 (Fiat) / 4 200 (Fiat) kg
    Number of seats 2 / 3
    Number of berths 2

**The `Weight in running order ±5%` row appears on the three Falcons and nowhere else:**

| model | MRO | base PMM | derived payload |
|---|---|---|---|
| Falcon XS | 2 980 kg | 3 500 | 520 |
| Falcon YS | 3 000 kg | 3 500 | 500 |
| Falcon Z | 3 300 kg | **3 820** | 520 |

Note **Falcon Z offers no 3 500 kg plate at all** — `3 820 / 4 000 kg`. Its base is 3.82 t,
which is a C1-licence vehicle and the only one in the range.

## The price list: euros, ex-VAT, ex-works — and no Falcon

Despite a flipbook titled *"UK ... Pricelist"*, page 1 reads **"Prices in euros. Valid from
27 August 2026."** and **"UE ex. VAT"**, with every page footed *"All prices are in Euro net
ex works."* There is no sterling figure in either document.

It covers **Explorer, Pathfinder and Voyager only**. The Falcon series is absent, so the
three models with a published mass are the three with no published price, and the nine with
a price have no per-model mass. The two documents cover opposite halves of the range.

### It does publish a mass in running order, but one per *series*

    Mass in running order: 3 060 kg.
    The value refers to the heaviest model variant in the series, in running order
    and with standard equipment.

Explorer 3 060, Pathfinder 3 160, Voyager 3 170 — **one figure for a whole series, and
explicitly another model's.** Spreading it across the series would record the Explorer Z
EVO's mass against the 37 cm shorter Explorer XS. That is the Airstream mistake (a unit's
plate is not the model's) and the WildAx one (a copied figure that the self-check cannot
see), so it must not be done. It is **not** the `one-qualified-mass-is-still-the-mass` case
either: that rule covers a figure qualified as options-dependent *for the model it is
printed against*, not a figure belonging to a sibling.

### Why the euro price cannot simply be converted

The settled euro rule covers a **domestic VAT-inclusive retail** price. This is neither: it
is net of VAT *and* ex works, so it excludes VAT, transport to the UK, registration and
PDI. Converting the Explorer X's EUR 78,470 gives GBP 68,235, while ES Hartley advertise an
Explorer 2X at **GBP 84,995 and call that a sale price**. A converted figure would
understate the real UK price by a quarter and would not be comparable with any other
product on FMLV.

## The open question is answered: Ducato and Boxer are two products

The price list settles it, because it **prices them separately**:

    Fiat Ducato | 180 Hp | 2.2 l | AT8     Explorer X  78 470 EUR
    Peugeot Boxer | 140 Hp | 2.2 l | AT8   Explorer X  74 193 EUR

Different engine, different output, EUR 4,277 apart. Under the settled rule a different
base vehicle is a different product, so the nine Fiat/Peugeot models are **eighteen**, and
with the three VW Falcons the roster is **21 products, not 12**. Worth confirming with the
brand that both are genuinely offered in the UK before doubling the roster.

## Two models exist only in the price list

**Explorer Z Bike** and **Pathfinder Z Bike** are priced (EUR 78,806 and 80,241 on Fiat)
but have no page on the website and no catalogue spread. On the website-overrules-the-PDF
rule they are out of scope, but they look like a real variant rather than an error — the
options list prices a *"Preparation for a Thule Lift V16 bike rack"* separately, so the
Bike is something more than that option. Ask.

## The UK dealer is ES Hartley, and their prices are not list prices

Page 8 lists dealers by country. The United Kingdom has one, at two sites:

    UNITED KINGDOM  ES HARTLEY  Ings Kendal; Cumbria, LA8 9PY                 +441539 822 450
    UNITED KINGDOM  ES HARTLEY  Rossmore Road East; Ellesmere Port, CH65 3DD  +441513 506 870

`eshartleygroup.co.uk/globe-traveller-motorhomes` states *"Country Poland - Established
2012 - Dealer Since 2023 - Pricing GBP 85,000 to GBP 130,000"* and lists stock. **Those
stock figures are not model prices**: every one is discounted and optioned —

    NEW GLOBE-TRAVELLER EXPLORER 2X  EX DISPLAY SALE!   GBP 84,995
    NEW GLOBE-TRAVELLER VOYAGER Z    SPECIAL PRICING    GBP 96,995
    NEW GLOBE-TRAVELLER FALCON 2Z    EX DISPLAY SALE!   Was GBP 121,254  Now GBP 114,995
    NEW GLOBE-TRAVELLER FALCON 2XS   EX DISPLAY SALE!   Was GBP 117,205  Now GBP 98,990

The `Was` figures are nearer a list price but are still one unit's build. Their lengths do
corroborate the catalogue exactly (6,360 / 6,840 / 5,990 mm), which is a useful check on
the parse but not a source of price.

## Where this leaves the build

| field | before | now |
|---|---|---|
| length, width, height | site yes | site yes, catalogue agrees |
| MTPLM | site yes | site yes, catalogue agrees |
| seats, berths | site yes | site yes, catalogue agrees |
| **mass in running order** | no | **Falcon only**; series-level for the rest |
| **payload** | no | **Falcon only**, derived |
| **price** | no | euro ex-works ex-VAT, and no Falcon — **still unusable** |

**Still not buildable, and now for one reason rather than three.** The single thing that
would unblock it is a **sterling retail price list**, per model, on the same on-the-road
basis FMLV holds for everything else. Globe-Traveller plainly produce market-specific lists
— this one is headed UE — so a GB edition is a thing to ask for rather than invent, and it
would most likely carry the per-model masses too, as other brands' market lists do.

### What to ask Globe-Traveller for

1. A **GB price list in sterling**, on-the-road, per model — including the Falcon.
2. **Mass in running order per model**, not per series, for Explorer, Pathfinder and
   Voyager.
3. Whether **Boxer and Ducato are both sold in the UK**, which decides 12 products or 21.
4. What the **Z Bike** variants are, and whether they are UK models.

## On the Nova record, re-answered 30 October 2026

The requester asked whether to add a couple of models on a template so the supplier appears
in the export dropdown, or to hand over a file of what they have.

**Neither, yet.** There are no existing products, so there is nothing to diff against and
nothing a file would tell a run that the catalogue does not. `fmlv empty-baseline` covers
the no-baseline case, and seeding dummy products has now gone wrong twice — Beauer's mock
was `active: No` and never reached the baseline, and Fleurette's two seed rows had to be
deleted afterwards.

What is needed before a build, and only before a build:

* a **manufacturer id** — the NCC's to allocate; `resources/manufacturers-full-list.csv`
  has no Globe-Traveller row, so the registry would start on a provisional id outside the
  NCC range as Fleurette did on 9001/9002;
* the exact **`ncc_supplier_name`** string, which no upload can invent.

Neither blocks the survey, and both are moot until there is a sterling price.
