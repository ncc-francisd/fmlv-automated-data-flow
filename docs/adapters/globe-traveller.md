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

> **Superseded, 30 October 2026 — the adapter is built.** Two of the three holes closed:
> the UK price list supplies nine of the twelve prices and the catalogue supplies the
> three Falcon masses. Read "Built, 30 October 2026" at the foot of this file. The
> verdict below is kept because its reasoning about the site is still the reasoning the
> adapter follows.

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

> **Read the correction at the foot of this file first.** This section concluded there was
> no usable price. That was wrong: it was written from the PDF behind the flipbook's
> download link, which is a superseded euro edition of a book whose displayed pages are a
> sterling UK list. The reasoning below about mass and roster still stands; everything it
> says about price does not.

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

### The names, settled 30 October 2026, and the registry row

The requester gave both strings, and they split the way `KAKTUS` does:

| field | value |
|---|---|
| `fmlv_manufacturer` | **`GLOBE-TRAVELLER`** — capitals, hyphen, two `L`s |
| `fmlv_display_name` | `Globe-Traveller` |
| `ncc_supplier_name` | `Globe-Traveller` |

Neither is a typo of the other and neither should be "fixed".

**Row written on provisional id `9003`**, because the brand is in no NCC list — the same
arrangement Fleurette and Florium have on 9001/9002, to be repointed when a real id is
allocated. `status` is **`paused`**, which the registry README defines as *"skip in
scheduled sweeps but still runnable manually"*: there is no adapter, and there should be no
sweep until there is a price. `fmlv run 9003` says so plainly rather than failing oddly.

The row carries the catalogue and price-list flipbook URLs in `brochure_url` and
`price_list_url`, so the documents are findable from the registry rather than only from
this file.

**That leaves exactly one thing outstanding: a sterling price list.** The id and the
supplier record are no longer blockers — they are written down and waiting.

---

# Correction — there *is* a sterling price list, 30 October 2026

**Everything above about the price being unusable is wrong, and the registry note that
repeated it has been rewritten.** The requester opened `/books/pyci/#p=3` in a browser and
found sterling prices on the page. He was right.

## What happened

The flipbook's own config offers the source PDF, and that PDF is a **different edition from
the pages the viewer displays**:

    "downloadconfig":{"pdf":{"isOriginPath":true, …, "type":"originalFiles"}}

`originalFiles` is the file *first uploaded*. Globe-Traveller have since replaced the
book's contents with a UK edition, and FlipHTML5 still serves the superseded euro one
behind the download link. The two have **no pound sign and 92 euro signs** versus a page
headed `GBP` throughout — so this was not a near-miss that careful reading would have
caught. The only thing that catches it is checking the download against the live pages,
which is now written up in `docs/adapters/README.md`.

The other `type=` values return the literal string `NOT_DOWNLOAD`, so there is no second
URL. The displayed pages are hashed `.webp` images whose filenames sit in an obfuscated
`fliphtml5_pages` blob.

## What the UK list actually says

Page 3, Fiat Ducato | 180 Hp | 2.2 l | AT8 | **RHD**, prices in **GBP**:

| series | models and prices | series MRO |
|---|---|---|
| **Explorer** | XS `95 119`, X `95 671`, Z `95 671`, Z EVO `104 013`, Z Bike `96 018` | 3 060 kg |
| **Pathfinder** | X `101 580`, Z `101 580`, Z Bike `101 927` | 3 160 kg |
| **Voyager** | XS `110 181`, X `110 733`, Z `110 733` | 3 170 kg |

All eleven read off the page by the requester, 30 October 2026.

And the footer gives the basis outright:

> **Prices are on the road, collected from dealer premises.**
> **They include — Full UK specification, righthand drive, transport to dealer premises,
> VAT @ 20% and 1st registration and road fund licence.**

That is **exactly** the basis FMLV records — the same one Auto-Trail and Dethleffs publish.
No conversion, no provenance caveat, nothing to explain away.

## What this changes

**The Ducato-versus-Boxer question is answered the other way, and the roster shrinks.** The
UK page is headed `Fiat Ducato … RHD` and carries **no Peugeot Boxer table**. The euro list
prices both because the EU gets both; the UK list is Fiat, right-hand drive, only. So the
roster is **not** 21 — it is the eleven models on this page, and the three Falcons.

**The two Bike variants looked like real UK models here, and they are not** — see
"Built, 30 October 2026" below. `Explorer Z Bike` and `Pathfinder Z Bike` are priced in
this list, which at the time settled the earlier doubt the wrong way. The catalogue says
outright that Bike Version is an **option**, and the uplift is £347 on both, which is one
option at one price. They have no website page and no catalogue spec block because there
is nothing to specify: they are the Z with a box ticked.

**The sterling figures confirm why the euro ones could never have been converted.** Explorer
X is €78,470 ex-works and £95,671 on the road — the sterling figure is *higher* than the
euro one, because VAT at 20%, transport and registration all land on top. A conversion would
have put it at £68,235, roughly £27,000 light.

## What is still outstanding

Much less than before, and none of it is the price:

1. **A machine-readable copy of the UK list.** The download link serves the wrong edition
   and the displayed pages are images, so an adapter cannot read it per run. Ask
   Globe-Traveller to email the UK price list PDF — the Fleurette precedent — and carry it
   as a `joa.py`-style constant, re-verified at the model-year changeover.
2. **Mass in running order per model.** Still the one unsolved data problem: the UK list
   repeats the euro list's *per-series* figure, footnoted *"the heaviest model variant in
   the series"*. The three Falcons have per-model masses in the catalogue; the other eleven
   have none.
3. **The Falcon's UK price.** The list is titled *"Voyager | Pathfinder | Explorer"* and
   the Falcon is absent from it, so the three VW models have a mass and no price while the
   eleven Fiat ones have a price and no per-model mass.
4. Whether the catalogue's download is **also** a superseded edition. Its contents matched
   the website on all twelve models, so it is probably current, but it has not been
   spot-checked against the live viewer and should be before anything is built from it.

---

# Built, 30 October 2026

`src/adapters/globe_traveller.py`, 60 tests, run #211 locally: **twelve products, nothing
dropped, sixteen seconds, thirteen plain HTTP fetches and no browser.**

The requester asked whether to build now or wait for the brand to answer. Build: nothing
being asked for changes how the site is read, and the site is where most of the fields come
from. What is being waited on is two numbers.

## The roster is twelve, not fourteen — the Bike Versions are an option

The UK price list has fourteen priced lines; the website has twelve pages. The two extra
lines are `Explorer Z Bike` and `Pathfinder Z Bike`, and they are not models. The catalogue
says so on page 31:

> The Explorer Z and Pathfinder Z can be ordered in **Bike Version**, with the garage
> adapted to carry two bicycles inside the vehicle.

And the prices corroborate it without needing the prose at all:

| | base | Bike | uplift |
|---|---|---|---|
| Explorer Z | £95,671 | £96,018 | **£347** |
| Pathfinder Z | £101,580 | £101,927 | **£347** |

**One option costs one price wherever it is fitted.** Two different vehicles differing by
the same £347 is an option line in a price list, not two products — a genuinely new model
would not land on its sibling's figure to the pound. By the base-vehicle rule what gets
recorded is the base, so the Bikes are out and the ask to the brand loses an item.

Globe-Traveller's own photography agrees: the Explorer Z's gallery images are all named
`Globe-Traveller-Explorer-Z-Bike-…`, because it is the same van.

## The seats notation is the opposite of what it looks like

Every page prints `No. of seats` as a plain figure with a second in brackets:

| series | printed | records |
|---|---|---|
| Explorer | `2(3)` | **2** |
| Falcon | `2` | **2** |
| Pathfinder, Voyager | `4(3)` | **4** |

The instinct from the berth-range rule is to take the lower. On the Explorers that happens
to be right; on the six Pathfinders and Voyagers it would record **three seats against a
stated four**. The pair is not a range, because it is not ordered: **the plain figure is
the fitment and the bracket is the option, in both directions.**

The catalogue says it three separate times, in prose, and that is what settled it:

> **Four travel seats are standard**, while an optional three seat configuration provides
> more room in the living area without reducing the number of berths

> Four travel seats are standard, with an optional three seat configuration available for
> those who prefer more living space

> an **optional three seat layout**, removable bedroom wall and Bike Version

and for the Explorers, the other direction: *"an optional third travel seat available
depending on the model"*. It also confirms these are belted — *"An additional single travel
seat with a seat belt"* — which is what the seat count is for.

This is the README's own warning arriving in the field: the lower-figure rule is safe for
berths because that row is labelled `standard / max`, and it does not transfer to a seats
row by analogy. **Worth asking the brand to confirm the belts are three-point**, since they
never say so.

## `2+2` berths is four, and the second two are not optional

Six layouts state `No. of berths 2+2`, and those same six carry an `Additional bed` with a
size — `187 cm x 134 cm` — where the other six read `N/A`. The berth-range rule takes the
lower figure *where the upper needs options*; here it does not. The catalogue describes the
extra bed as part of the layout, in a cabinet above the dinette, *"providing four berths
without giving up the use of the seating"*, and says the optional three-seat configuration
is *"without reducing the number of berths"* — so the berths stand independently of it.

The catalogue calls it *"sleeping space for two kids or teenagers"*, which is a real
qualification and worth putting to the brand, but it is a bed the vehicle has.

## What is recorded, and what is deliberately not

| | nine Fiat models | three Falcons |
|---|---|---|
| price | ✓ UK price list | ✗ **asked for** |
| MTPLM, length, width, height, seats, berths, base vehicle, body type | ✓ the model page | ✓ the model page |
| mass in running order | ✗ **asked for** | ✓ catalogue, ±5% |
| payload | ✗ follows the mass | ✓ derived |

**The per-series mass is not used and the numbers are not in the code.** Both documents
print Explorer 3 060, Pathfinder 3 160, Voyager 3 170, footnoted *"the heaviest model
variant in the series"* — a sibling's figure. Spreading it across the four Explorers would
put a heavier vehicle's mass on three lighter ones, which is the Airstream unit-plate
mistake wearing a different hat. A test asserts those three figures appear nowhere.

**So no product yet has both a price and a mass**, and the run says so on every pass rather
than only at build time. The brand is left at `status: paused`, which is exactly what that
value is for — runnable by hand, skipped by scheduled sweeps — until the answers land.

## Why the two constants are constants

Both documents are FlipHTML5 flipbooks whose config hands over a downloadable PDF, so an
adapter *could* fetch them every run. It must not. That download is
`"type":"originalFiles"` — the file first uploaded — and on the price list it is **already**
serving a superseded euro edition while the pages on screen are sterling. A fetch that
looks live but quietly returns last season's document is worse than a constant that says
what it is and carries a re-verify date.

The catalogue's download was spot-checked and **is** current: 32 pages matching the viewer,
created 16 August 2026, its title agreeing with the viewer's, and its contents agreeing
with the website on all twelve models. Note what did *not* discriminate — **page count**.
The euro and the UK price list both have eight.

## The self-check is structural, and the drawings are why it had to be

`payload == MTPLM - MRO` is unavailable: nine models have no MRO, and on the three that do,
the payload is derived from that identity and so cannot also test it.

What the pages support instead is **the identity stated twice**: the roster supplies a URL,
and the table restates its own `Model Series` and `Model`. A page served for the wrong
vehicle breaks that agreement, and a failure drops the product rather than a field — the
disagreement is about *which vehicle this is*, so nothing on the page can be trusted. A
third check catches the two height rows being read the wrong way round.

That the check is needed is not theoretical, because **the layout filenames lie**:

| page | drawing it carries |
|---|---|
| `explorer-z-evo` | `voyager_z_layout-3.png` |
| `falcon-ys` | `falcon_2XS_SE_layout-3.png` |
| `pathfinder-x` *and* `voyager-x` | `voyager_pathfinder_x_layout-1.png` |

So the drawing is taken **from the page** and never matched by name — one URL is one
vehicle, and the page is the attribution. A filename naming a different model still warns,
because it may mean the wrong drawing was uploaded; the shared one and the version-numbered
`falcon_2XS` do not, because they name the model they are on. Two of the twelve warn, and
both are genuine.

## Smaller things worth knowing

* **`Lenght` is their spelling** and the label set keeps it. Correcting it loses the row.
* **The footer re-uses the table's span class** and its headings include all four series
  names, so the cells are bounded at `Model Series` and `Models` rather than filtered.
* **`Extended PMM` arrives as six ragged cells** — `(*Fiat only)`, `3820`, `or`, `4200`,
  `kg` — which is why the parser pairs cells rather than flattening the page to one line.
  It is skipped: those are the optional heavier plates, and the base-vehicle rule records
  `Permissible Max. Mass (PMM)`.
* **`Falcon Z` has no 3 500 kg plate** — `3 820` — and is the only C1 vehicle here.
* **The Falcons are `VW`, not `Volkswagen`.** The page says Volkswagen; the base-vehicle
  column says VW. `fmlv_base_vehicle` deliberately does not map one onto the other, so the
  adapter translates before handing it over.
* **`Fiat/Peugeot` is one UK product.** The euro list prices the Boxer separately, but the
  UK list is headed `Fiat Ducato … RHD` and has no Peugeot table, so it never arises.
* **Their `Seperate shower` is handled by the shared vocabulary** — `habitation` already
  spells it both ways. Their opposite value, `Integrated with toilet`, has no phrase there
  and is read in the adapter, because "the page did not say" would be wrong when it does.
* **No heating anywhere.** No row, no equipment list, so nothing is recorded and nothing is
  claimed to have been looked at.
* **Ranges are set, not matched.** FMLV holds no Globe-Traveller products, so `Explorer` /
  `X` is a convention being chosen rather than an export being followed — the `Series`
  suffix is dropped so the display name does not read "Explorer Explorer X". Redirectable.

## Still outstanding

Three, down from five, and the first is the only one blocking an upload:

1. **Mass in running order, per model, for the nine Fiat models.** Everything else about
   them is in hand.
2. **UK prices for the three Falcons.** The price list omits the range.
3. **A machine-readable copy of the UK price list** — email the PDF — so the nine prices
   stop being a constant. Not blocking; a convenience and a safeguard.

And two confirmations worth having: that the travel-seat belts are three-point, and that
Bike Version is an option rather than a model.
