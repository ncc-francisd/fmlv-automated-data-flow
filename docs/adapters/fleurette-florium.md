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

## The blocker: there is no price, anywhere

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

## Verdict

**Not buildable yet, and the reason is commercial rather than technical.** The
specification is as good as any surveyed: one document, both brands, mirrors already
excluded, a real mass in running order, berths marked standard against optional. Every
core field is there **except the price**, which is required.

If a price list arrives, this is a straightforward build — one column reader over one PDF,
registered twice.

## To ask

1. **Is anyone actually importing them?** Four dealers are mapped — three of them River
   Motorhomes — but none lists either brand on its own website, so the map may be stale.
   River are already the Mink importer, which makes them the obvious person to ask.
2. **Is there a UK or export price list?** The dealer portal implies tariffs exist; they
   are just not public.
3. **Are all thirty products coming to the UK**, or a subset? Thirteen of the thirty are
   Fleurette trim of a vehicle Florium also sells.
4. **The ten missing `NC` masses** — the entire Discover and Wincester ranges plus the
   Black Pearl 63LD.
