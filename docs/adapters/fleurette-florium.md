# Fleurette Florium — feasibility, 14 October 2026

A potential new exhibitor, French, `https://www.fleurette-florium.fr/`. **Not in
`resources/manufacturers-full-list.csv`**, so there is no NCC id yet and no registry row
can be written. Part of the **Groupe RAPIDO** since 2005, per the catalogue's own page 2.

No adapter. This is a feasibility scan, and it turns on one gap: **there is no price
anywhere.**

## It is two brands, not one — and the combined name is the company

The requester's reading, confirmed by the site's own navigation, which has two headed
columns. **Neither brand carries the other's name**: a Mayflower is a *Florium Mayflower*,
never a "Fleurette Florium Mayflower".

| **FLEURETTE** | **FLORIUM** | shared shape |
|---|---|---|
| Migrateur — 60LG, 64LDF, 69LJG | Baxter — 60LG, 64LDF, 69LJG | compact low-profile |
| Magister — 67LO, 70LMF, 70LJG, 74LMF | Mayflower — 67LO, 70LMF, 70LJG, 74LMF | pavilion-bed low-profile |
| Elister — 73LMF, 73LJG | Belixter — 73LMF, 73LJG | ultra-spacious |
| Discover — 72LMF, 72LJG, 74LJG, 75LMF | Wincester — 72LMF, 72LJG, 74LJG, 75LMF | A-class |
| — | **Black Pearl** — 59LT, 63LJ, 63LD, 63KS | van conversions |

**13 Fleurette + 17 Florium = 30 products.** The catalogue states the difference outright:
*"Deux marques, deux styles"*, and *"Deux boiseries, deux ambiances : Noyer sur Fleurette
et Frêne sur Florium"* — walnut against ash. So the two brands are **the same vehicle in a
different trim**, which is why the ranges run in parallel.

### The layout code repeats across both brands, and that is a collision waiting to happen

`70LMF` is a Magister *and* a Mayflower; `73LJG` is an Elister *and* a Belixter. Twelve of
the thirteen codes are used twice. Any keying on the layout code alone collapses thirty
products into seventeen — the same trap that halved the Malibu roster, and here it is
guaranteed rather than accidental.

**If this is ever built it is two FMLV manufacturers**, each with its own id and display
name, almost certainly served by one shared column reader — the Pilote Group pattern.

## The data is good, and it is all in one table

`Catalogue_Fleurette_297x210_2027_FR_BD-17.pdf`, linked from
`/le-catalogue-camping-cars/` alongside the superseded 2026 edition, so the right one must
be rediscovered per run rather than written in. **One catalogue covers both brands.**

Page 38 carries all thirteen shared layouts in one grid, and page 42 the four Black Pearls.
Verbatim:

```
                               MIGRATEUR / BAXTER   MAGISTER / MAYFLOWER   ...
                               60LG  64LDF  69LJG   67LO  70LMF  70LJG  74LMF
Longueur hors tout*            5,99   6,47   6,99   6,77   6,97   6,97   7,38
Largeur hors tout (sans rétroviseurs)*  2,23  2,23  2,23  2,30  2,30  2,30  2,30
Hauteur hors tout*             2,70   2,70   2,70   2,82   2,82   2,82   2,82
Masse maximale en charge       3500/  3500/  3500/  3500/  3500/  3500/  3500/
  techniquement admissible      3650   3650   3650   3650   3650   3650   3650
                                             /4250  /4250  /4250  /4250  /4250
Masse à vide en ordre de marche 2693   2794   2866   2974   2996   3047   3014
Places carte grise***             4      4      4      4      4      4      4
Places couchage                   3      3      3      4      4      4   3 (S) /4 (O)
```

**The column headings pair the brands**, which is the cleanest possible confirmation that
one spec serves both: `MIGRATEUR / BAXTER`.

### Three things it gets right that usually have to be fought for

* **`Largeur hors tout (sans rétroviseurs)`** — the width is published *excluding mirrors*,
  which is the settled rule already satisfied at source.
* **`Masse à vide en ordre de marche` is a genuine MRO.** Its footnote: *"Avec 1
  conducteur, 90% d'eau propre, 90% 1 bte gaz, 90% gasoil et outillage, sans options et
  sans attelage"* — **with one driver**, 90% water, gas and fuel, tools, no options, no
  towbar. That is the mass in running order as FMLV defines it, so unlike Volkswagen's
  *kerb weight* no driver allowance has to be added back.
* **`Places couchage` marks what is optional**: `3 (S) /4 (O)` and `2/3 (O)`. The lower
  figure is the standard one, which is the berths rule, stated rather than inferred.

### Two things that need care

* **`Masse maximale en charge … VL ou PL` is a list of chassis options**, `3500/3650/4250`.
  The base vehicle is **3500** per the settled rule; the heavier plates are upgrades.
* **`Places carte grise`** is footnoted *"Nombre de places carte grise maximum en version
  véhicule léger, variable selon configuration"* — a **maximum**, and some columns read
  `4/3 selon configuration` or `3/2/4 selon configuration`. This is the Bürstner trap
  already in [`README.md`](README.md): a "permitted" seat count is a ceiling, not a
  fitment claim. It should not be recorded without corroboration.

### Five masses are simply not published

`Masse à vide` reads **`NC`** — *non communiqué* — for the whole Discover / Wincester row
(72LMF, 72LJG, 74LJG, 75LMF) and for the Black Pearl 63LD. That is ten products with no
MRO, and therefore no derived payload. Nothing should be emitted for them.

A **±3% tolerance** is printed against every weight and measure.

## The prices arrived, 28 October 2026 — and they are sterling

Léa Timores (Responsable communication, `ltimores@fleurette.fr`) emailed four 2027 price
lists, which between them cover **all thirty products**. They are not on the website and
were not in the 7,252-URL sitemap, so no run can rediscover them: this is the **Pilote
arrangement**, and `joa.py` is the pattern to copy — a module constant with a
`PRICE_LIST_SOURCE` string, a `price_manually_sourced` flag driving the provenance
wording, and a re-verify at the model-year changeover.

| document | brand | covers | base vehicle |
|---|---|---|---|
| `FLEURETTE RRP GB 2027.pdf` | Fleurette | Migrateur 3, Magister 4, Discover 4 | Fiat |
| `FLORIUM RRP GB 2027.pdf` | Florium | Baxter 3, Mayflower 4, Wincester 4 | Fiat |
| `ELISTER BELIXTER RRP GB 2027.pdf` | both | Elister 2 + Belixter 2 | Mercedes |
| `BLACK PEARL RRP GB 2027.pdf` | Florium | Black Pearl 4 | Fiat |

**13 Fleurette + 17 Florium = 30.** The basis is as good as it gets: *"2027 Recommended
Retail Prices (£) with VAT + Transport — OTR — valid from the 1st July 2026"*. Native
sterling, so no conversion and `euro-prices-convert-at-1-15` never comes into it.

### Two prices per layout, and which one is the base

Every Fiat coachbuilt is listed twice, manual and automatic, the automatic **£2,800–£2,900**
dearer. The base vehicle is the **manual**, by the settled rule.

The exception is the A-class: Discover and Wincester are published *only* as
`based on FIAT chassis with automatic gearbox`, so there the automatic price **is** the
base. The 74 LJG and 75 LMF are on an **AL-KO** chassis — a chassis variant, still Fiat.

The Mercedes sheet prices `ELISTER / BELIXTER 73LMF / 73LJG` at a single **£102,990**, on
a `Sprinter Mercedes Benz - 150 hp - Manual Transmission - FWD`. One figure, four
products. The automatic arrives inside the DELUXE PACK at £3,350, so it is an option and
the manual remains the base.

### `Wellness` — the catalogue's "same vehicle, different veneer" is not the whole story

The catalogue says *"Deux marques, deux styles"* and puts the difference at walnut against
ash. The price lists say otherwise on six layouts. **Fleurette** label 69 LJG, 70 LMF,
70 LJG, 74 LMF, 74 LJG and 75 LMF as **Wellness**; **Florium never use the word.**

The pricing corroborates it. Where there is no `Wellness` the two brands are priced
**identically** — 60 LG £68,690 and 64 LDF £70,990 in both, 67 LO £74,390 in both. Where
Fleurette add it they are £2,000–£3,300 dearer: 69 LJG £75,790 against Florium's £73,790,
70 LMF £77,890 against £74,590.

**It stays out of the model name.** The model is `69LJG`, not `69 LJG Wellness` — the
catalogue spec table is where every other figure comes from and it spells them bare,
`Wellness` is not a layout, and a word that could later be dropped would churn the
range/model identity key. The Wellness figure is the price, said so in provenance.

**Unexplained:** 72 LMF and 72 LJG carry no `Wellness` on either side yet differ by
**£1,300** (£94,990/£95,890 against £93,690/£94,590), and 75 LMF differs by £1,700.

### Two Black Pearl rows contradict the sheet's own options table

Among the van prices sit two rows that do not belong to the pattern:

```
Model 63LJ - Fiat L3H2 180 hp - Automatic transmission   25 kg   £57 275
Model 59LT - Fiat L2H2 180 hp - Automatic transmission   25 kg   £55 300
```

Both are on a **shorter body** than that model's other rows (the 63s are otherwise L4H2,
the 59 otherwise L3H2), both are out of sequence in the list, and both are **£10,000 to
£12,000 cheaper** than the same layout's 140 hp manual. The same sheet's Fiat Options
price `180 HP Engine (On base price 140 HP Automatic gearbox)` at **+£2,160** — so a 59LT
180 hp automatic should be £67,190 + £2,160 = £69,350, not £55,300. The two cannot both be
right, and the arithmetic says it is not these rows.

**Record the 140 hp manual** for all four — 59LT £64,390, 63LJ £66,990, 63LD £67,690,
63KS £68,690 — and query the pair.

The Black Pearl sheet also footnotes *"exclude factory charge of €330.00"*: a euro charge
excluded from a sterling OTR price. Record the printed sterling figure and note the
exclusion. Nothing is added to it.

### Habitation, free with the price lists

The standard-fittings blocks are unusually full, and two settled rules bite immediately:
Black Pearl's *"rear shower with hot and cold water"* and the Elister's *"cold-water
shower in the garage"* are **outdoor showers, not washrooms**. Likewise the Elister's
Serenity Pack carries the `Combi 4000ED` as an **option**, so it must not set the base
heating, and the built-in oven is £560 extra.

What is standard and readable: Black Pearl `157-litre compressor refrigerator` and
`Truma 4000 Diesel heating system`; Elister/Belixter `150-litre compressor refrigerator`,
`Height-adjustable garage with electric operation` (rear garage) and a `2-berth drop-down
bed`.

### Still missing

* **MIRO for Discover and Wincester** — eight products. Léa: *"The MiRO weights for the
  Discover and Wincester models will not be available until next week. Testing is
  currently underway."*
* **MIRO for the Black Pearl 63LD**, which the catalogue also prints as `NC` and the email
  does not mention.

### Not in scope

The same email carried four **Westfalia** lists (Kelsey, Kipling, Nansen 600 L, Nansen
640 LS) and a Westfalia dealer link. Westfalia is a separate brand and is out of scope
here; the requester struck them out on 28 October 2026.

## Why it was blocked until then

This is the whole finding, and it is not a near miss.

* **The model pages carry none.** Not a euro figure, not the word *prix*, not *tarif*, on
  any of them.
* **The catalogue carries none.** Forty-four pages, no *prix*, no *tarif*. (A naive search
  finds sixteen `€` which are all mojibake from the text extraction, not money.)
* **The sitemap carries none.** 7,252 URLs, and not one is a tariff or price page.
* **The only price route is `espacepro.fleurette-constructeur.fr/login`**, a dealer portal
  behind authentication.

So **the proposed euro conversion at 1.15 has nothing to convert.** There is no published
euro price to divide.

### The four UK dealers, and why none of them is a price either

The dealer page renders nothing server-side — it is a **WP Google Maps Pro** map — but the
plugin's own REST route is open and returns all 64 markers:

```
https://www.fleurette-florium.fr/wp-json/wpgmza/v1/markers
```

Four are in the UK, which is the number the requester had without a list:

| dealer | | |
|---|---|---|
| **Wandahome South Cave** | Brough Rd, South Cave, Brough HU15 2DB | +44 1430 330430 |
| **River Motorhomes** Birmingham | Kingsbury Rd, Sutton Coldfield B76 9EE | +44 330 808 0805 |
| **River Motorhomes** Hereford | Worcester Rd, Whitestone HR1 3RX | +44 1432 278833 |
| **River Motorhomes** Newport | Mere Park, Stafford Rd, Newport TF10 9BY | +44 1952 446989 |

**Three of the four are River Motorhomes**, who this repo already knows: they are the UK
importer for **Mink Campers**, and `mink.py` reads their site precisely because it is *"the
only place a price is"*. That made them the obvious route to a price here.

**They are not.** River's own site mentions neither brand — 255 URLs in their sitemap and
not one match for Fleurette, Florium or any of the nine range names, with only Mink on
their home page. So either the French dealer map is stale or the arrangement has not gone
live. Wandahome would need the same check.

**So there is no exclusive UK importer**, which matters beyond the missing number. The
settled rule gives the importer authority over what exists and what it costs; with four
independent dealers and no distributor, there is no single UK price to record and no one
deciding which of the thirty products reach the UK.


## Verdict — buildable, once the masses land

**The commercial blocker is gone.** All thirty products have a UK on-the-road price in
sterling, and the specification was never the problem. What is left is the eight Discover
and Wincester masses (due the week of 2 November 2026) and the Black Pearl 63LD.

The build is one column reader over the catalogue for the specification, a manually
sourced price table per `joa.py` for the money, and **two registrations** — the Swift
arrangement, one `fmlv_manufacturer` carrying two brands:

| manufacturer | display name | NCC supplier | products |
|---|---|---|---|
| Fleurette Constructeur | Fleurette | Fleurette | 13 |
| Fleurette Constructeur | Florium | Florium | 17 |

Both rows were created on the NCC side on 28 October 2026 with **one seed product each**,
so the baseline is *not* empty and `fmlv empty-baseline` is not wanted. The seed row's
`manufacturer_range` and `model` must name a real layout, or the first run matches it
against nothing, reports it as disappeared and proposes all thirty as new.

`manufacturer_id` for each still has to reach `resources/manufacturers-full-list.csv`
before a registry row can be written.

## To ask

1. **The two Black Pearl 180 hp rows** — 63LJ at £57,275 on an L3H2 and 59LT at £55,300 on
   an L2H2, both cheaper than the 140 hp manual while the options table prices 180 hp as a
   £2,160 *extra*. Are these a different, shorter vehicle, or an error?
2. **The Black Pearl 63LD mass**, still `NC` and not covered by the Discover/Wincester
   testing.
3. **Why 72 LMF and 72 LJG differ by £1,300 between the brands** when neither carries
   `Wellness` and the other unlabelled layouts are priced identically.
4. **Is `Wellness` standard on those six Fleurette layouts**, or an orderable pack? The
   price list reads as standard; the catalogue does not mention it.

## Build in progress, 28 October 2026

`src/adapters/fleurette_florium.py` reads the catalogue; `fleurette.py` and `florium.py`
are still to write. The reader takes all seventeen technical columns off pages 38 and 42
with every field correct, and rejects a row that has gained or lost a cell rather than
shifting every vehicle's figures along one.

### The model pages are not a specification source

Tempting, because each layout has one and it carries a technical panel. **They mix model
years with no warning**, and where they disagree with the catalogue the catalogue is
current:

| page | empty weight | marked |
|---|---|---|
| Wincester 74LJG | 3180 kg | *Photos of the 2026 collection* |
| Discover 75LMF | 3134 kg | *2026 collection* |
| Discover 72LMF | — | *2027 collection* |
| Elister 73LMF | 3121 kg | *2025 collection* (the 2027 catalogue says **3122**) |

The pattern is exact: **every page carrying a mass is a previous year's page, and the
2027 pages carry none.** That corroborates Léa Timores's "the MiRO weights for the
Discover and Wincester will not be available until next week" rather than contradicting
it — so the eight masses genuinely are not published yet, and 3180 would have gone in
looking entirely plausible. Specifications come from the catalogue, prices from the price
lists, and the site from neither. This is `aura.md`'s lesson about smaller brands' sites
lagging, met again.

### Seats: the catalogue states all seventeen, and the pictos confirm them

The seats row — `Places carte grise et nombre de ceinture suivant la configuration` —
is the one the extraction cannot lay out as a single line, because four of its cells are
phrases that wrap onto lines of their own. Rejoined, page 38 reads:

    4 4 4 4 4 4 4  4/3 selon configuration  4/3 selon configuration  4 4
    3/2/4 selon configuration  4/3 selon configuration

Thirteen cells for thirteen columns: nine plain, four banded. Page 42 gives the four
vans a plain `4` each. **Nothing is missing** — the first parser read only the leading
run of plain integers and so stopped at column 8, losing `72LMF` and `72LJG`, which the
catalogue states as plainly as the rest. `seat_counts` now reads the whole region in
column order and refuses the row outright unless the cell count comes out exact.

The four banded cells stay unset, because the row's own footnote calls it *"Nombre de
places carte grise **maximum** ... variable selon configuration"* — a type-approval
ceiling, which the README says not to record uncorroborated.

#### The corroboration is the manufacturer's own picto, and it is the same field

Every model page carries a travel-seats tile, and **the figure is in the image
filename**, not the pixels:

    pictos-4-carte-grise-fleurette-florium-GB.png
    pictos-3-4-carte-grise-fleurette-florium-GB.png

`carte grise` is exactly what the catalogue calls its row. Checked against all seventeen
columns on 29 October 2026, the two sources agree completely: the picto prints a plain
number on every column the catalogue states plainly, and prints `3-4` on precisely the
four it bands. That is a genuine second reading of the same field, and it is the reason
the four banded layouts can be recorded at all.

Banded reads **3**, the requester's reading of the rendered tile on 28 October and his
ruling on 29 October, which the base-vehicle rule gives independently. Each of the four
has at least one 2027-marked page — Belixter 73LMF/73LJG, Discover 74LJG and Wincester
75LMF — so the corroboration is current even though some twins' pages are 2025 or 2026.

**The adapter does not read the site.** The pages mix model years with no warning, as the
table above shows, so the picto is carried as a `SUPPLIED_SEATS` constant with its source
in provenance, and re-verified at the model-year changeover. Automating it would mean
fetching thirty-two pages a run to re-read a figure that changes once a year, from a
source this document has just finished disqualifying for masses.

### The Elister and Belixter MTPLM is 3500, and the low payload is real

These two are the only layouts whose maximum mass is printed as a pair. The catalogue's
technical table gives:

    Masse en ordre de marche (kg)    3122   3161
    MTPLM / PTAC (kg)                3500 / 4100

Taking 3500 leaves a payload of **378 kg** on the 73LMF and **339 kg** on the 73LJG —
the two lowest figures in the range, on its longest and most expensive vehicles, where
the 5.99m Migrateur 60LG gets 807 kg. That looks wrong, and the Elister/Belixter price
list makes it look wronger still by pricing an option as *"Upgrade from 4T1 GVW with 5T5
autorised rolling weight £300"*, which reads as 4.1 tonnes already being on the plate.

**It is nonetheless 3500, and that is settled — do not change it on the arithmetic.**
The requester ruled on 29 October 2026: 3500 is the standard weight and 4100 is what
certain optional extras buy, which is the README's own rule that an option never sets the
base specification. The catalogue prints 3500 first for exactly that reason, and the
price list's own header reads `3T5 - 5T5`, 3.5 tonnes laden against a 5.5 tonne train
weight — so the £300 upgrade is a *towing* upgrade, not a replating.

The implausible-looking payload is therefore the correct figure for the base vehicle, and
a future session that recomputes it from 4100 would be recording an optioned variant. The
question is with Fleurette for confirmation, and nothing changes until they answer.

### An extra layout on the site: 68LMC

`migrateur-68-lmc-central-bed` and `baxter-68-lmc-central-bed` exist as pages — 6.85m,
2929 kg, and built on a **Peugeot** where every other layout is Fiat or Mercedes. It is in
neither the 2027 catalogue nor the 2027 price list, so it reads as a 2026 model that has
been dropped, and it is **out of scope**. On the open-questions list for Léa.

### Built, 29 October 2026 — and what is still open

`fleurette.py` (13 layouts) and `florium.py` (17) both read `fleurette_florium.py`, are
registered on provisional ids 9001 and 9002, and have 51 tests over seven catalogue
fixtures. Runs #201 and #202 built all thirty products off an empty baseline.

**Twenty-one of the thirty can be uploaded.** Nine cannot, and are collected anyway with
a pointer rather than dropped, because an adapter that returns 21 of 30 reads to a
reviewer as nine discontinuations — the `vantage.py` mistake:

| blocked | missing |
|---|---|
| Discover + Wincester 72LMF, 72LJG, 74LJG, 75LMF | mass |
| Black Pearl 63LD | mass |

Mass is now the **only** thing holding any of them back: every one of the thirty has a
seat count as of 29 October 2026. When Léa's weights arrive, the nine go straight
through.

Still open with Fleurette, and all of it with Léa Timores:

* the eight Discover and Wincester masses, promised for the week of 3 November 2026;
* the Black Pearl 63LD mass;
* the two Black Pearl price rows the arithmetic rejects (63LJ £57,275, 59LT £55,300);
* whether `68LMC` is dropped for 2027;
* confirmation of the Elister and Belixter MTPLM, MRO and payload — see above.

Still open on our side: the provisional ids 9001 and 9002 want repointing once the NCC
issues real ones.
