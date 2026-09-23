# Carthago (id 54)

Surveyed 2026-09-23. **Motorhomes only** — six A-class ranges and three semi-integrated
(low-profile coachbuilt). No campervans and no caravans, which FMLV agrees with.

- Source: <https://www.carthago.com/en/>
- NCC supplier name: `Carthago Motorhomes`
- `fmlv_manufacturer`: `Carthago` — id 54. The supplier list adds `Motorhomes`; both are
  right, per the settled one-name-per-role rule.

A German manufacturer (Carthago Reisemobilbau GmbH, Aulendorf), but **`/en/` is a genuine
UK price list**, not a translation of the German one. See below — that took proving.

## The roster: nine ranges, 76 products

| family | range | products |
|---|---|---|
| A-class | `c1-tourer-edition` | 2 |
| A-class | `c2-tourer` | **26** |
| A-class | `chic-c-line` | 9 |
| A-class | `chic-e-line` | 10 |
| A-class | `chic-s-plus` | 3 |
| A-class | `liner-for-two` | 4 |
| semi-integrated | `c1-tourer-edition-t` | 2 |
| semi-integrated | `c1-tourer-t` | 18 |
| semi-integrated | `chic-c-line-t` | 2 |

**76**, and this is the manufacturer's own claim: each range's overview card states a
`Floor plans` count, and those nine counts add to exactly 76. That is the number to assert
in the tests.

## A product is a layout × trim × weight class × chassis

**This is the whole difficulty, and the requester flagged it before the survey started.**
Carthago sell one layout as up to four separate vehicles, and they are genuinely different
— not options on one product:

| | length | height | MRO | price |
|---|---|---|---|---|
| C1-tourer T 143 KB-LE lightweight 3.5 t **Fiat** | 6900 | 2920 | 2943 | £96,100 |
| C1-tourer T 143 KB-LE lightweight 3.5 t **Mercedes** | **7060** | **2950** | **2896** | £94,580 |
| C1-tourer T 143 KB-LE comfort 4.2 t **Fiat** | 6900 | 2920 | 2983 | £99,670 |
| C1-tourer T 143 KB-LE comfort 4.2 t **Mercedes** | 7060 | 2950 | — | £96,040 |

So the model name has to carry **the layout code, the trim word, the weight class and the
chassis** — `T 143 KB-LE lightweight 3.5 t Fiat`. Drop any one of the four and two distinct
vehicles collapse into one. FMLV already names them this way.

**A third chassis exists that the requester did not mention: Iveco.** The three Chic S-plus
and two of the four Liner-for-two are `Iveco Daily`. Across the 50 card-rendered products
the split is Fiat 23, Mercedes 22, Iveco 5.

## Two page templates, and only one carries JSON

Eight of the nine ranges server-render a card per product, each carrying:

- `data-compare-brand-icon="fiat-icon"` / `"mb-icon"` — the chassis;
- a `Find vehicle` link whose query string states `fahrzeug_baureihe` (the range) and
  `fahrzeug_modell` (the model) explicitly, so the identity need not be parsed out of prose;
- a `Technical data` link to the product's own page, whose slug ends in the chassis
  (`...-lightweight-3-5-t-2-fiat-ducato`, `...-mercedes-benz`).

**`c2-tourer` alone uses a different component**, `wp-block-carthago-grundrissberater`, whose
entire dataset sits inline in `<script type="application/json" class="cgrb__data">`. It has
no cards at all, so a card-only reader silently returns **zero** products for the largest
range in the line-up — 26 of the 76. That is the trap this survey nearly walked into.

The JSON is much the nicer source where it exists, giving `seriesTitle`, `groupTitle`,
`title`, `basisfahrzeugLabel`, `lengthMeters`, `massTons`, `priceLabel`, `permalink` and
`isNew` per product. Both readers are needed.

## The currency trap: the JSON says euro and means sterling

The `cgrb__data` blob states `"priceLabel": "104.500 €"` while the rendered page shows
`₤104.500` for the same vehicle. **Same number, two currencies.** Taking the JSON at its
word and applying the 1.15 conversion would divide a sterling price by 1.15.

Three things settle it as sterling:

1. **The French site prices the same vehicles differently.** All 26 C2-tourer products
   differ between `/en/` and `/fr/`, consistently — `104.500` against `117.890`,
   `110.640` against `124.960`. The ratio is a steady ≈1.128, which is a real exchange
   rate, not a rounding. If `/en/` were euro the two would be identical.
2. **Every configurator link carries `MPL_PREISLISTE=GB`** — the GB price list.
3. **FMLV already agrees.** Its C1-tourer T 143 KB-LE lightweight 3.5 t Fiat holds
   £86,770, and the site's C1-tourer T range states `from ₤86.770`.

So no conversion, and the euro sign in the JSON is a template that was never localised.
Read the number, ignore the symbol. Note the thousands separator is a **dot**, German-style.

Prices are on the range pages only — **the product pages carry no price at all.**

## What each product page publishes

```
Lightweight / Comfort                                comfort
Type of construction                                 Coachbuilt
Basic vehicle                                        Fiat Ducato
Length / width / height (mm)                         6900 / 2270 1) / 2920
Technically permissible gross vehicle weight (kg)    4.250 / 4.500  2)
Weight in running order (kg)                         2.983 (2.834 - 3.132)
Max. number of seats with 3-point safety belt        4
Sleeping berths standard / optional                  2 / 3
Rear garage interior height (mm)                     1200
Refrigerator volume / of which freezer (l)           133 / 12
Heating system                                       Truma Combi 6
```

**Dimensions are already in millimetres**, so none of the centimetre-rounding trouble Wildax
had. `Type of construction` states `Coachbuilt` or `A class`, which gives the body type
without deriving it from a height.

`Max. number of seats with 3-point safety belt` says *three-point* in so many words, which
is exactly the settled rule — no interpretation needed.

### Four fields state a base and an upgrade, and the base is what FMLV wants

Each of these is `standard / optional`, and the settled base-vehicle rule takes the first:

| field | example | record |
|---|---|---|
| gross vehicle weight | `5.600 / 5.800` | 5600 — footnote 2 is "optional weight increase" |
| sleeping berths | `2 / 3` | 2 — and the settled lower-figure rule says the same |
| seats with 3-point belt | `4 / 5` | 4 |
| height | `3125 (3290 2)` | 3125 |

**No payload is published.** It is `MTPLM − MRO` as usual — 4250 − 2983 = 1267 for the
worked example. There is a `Weight of additional equipment in series production specified
by the manufacturer (kg) 899`, which is **not** FMLV's payload and must not be recorded as
one; it is the same shape of trap as Frankia's `Nutzlast`.

## The self-check: a ±5% band on every mass

`Weight in running order (kg) 2.983 (2.834 - 3.132)` — the bracket is the production
tolerance, and 2983 × 0.95 = 2834 and × 1.05 = 3132 to the kilogram. The same redundancy
`frankia.py`, `knaus.py` and `weinsberg.py` use, and it verifies the parse per product with
no second document.

**Six of six reconciled exactly** on a sample spanning both templates, all three chassis and
both body types.

## A parse trap already found

`Basic vehicle` appears **twice** on every page — once in the range-navigation card, where
its value is a floor-plan count (`Basic vehicle / 2 / Floor plans`), and once in the
technical table, where it is `Fiat Ducato`. Reading the first occurrence gives `2`. The
technical block has to be located first and the labels read inside it.

## Model year

The requester's position: FMLV holds these as **2027**, the website still presents 2026, and
the intention is to keep 2027 and bump each model.

The site quietly supports him. Its own image assets are named `MJ2027` — Modelljahr 2027 —
**179 times against 61 for `MJ2026`**, so the photography is predominantly next year's
vehicles even though no page states a model year in words.

## Fetches per run

**85** — nine range pages for the roster, the chassis and the price, then 76 product pages
for the specification. Easily the largest of any adapter so far; Frankia is ten and Wildax
eight. Worth knowing before the first run.

## Still needed before a build

**There is no FMLV export for id 54.** Nothing here has been checked against what FMLV
actually holds: not the range/model split, not the live count, not the naming of the trim
and chassis suffixes. The public site shows the display name as
`Carthago C1-tourer T 143 KB-LE lightweight 3.5 t Fiat`, but whether that is range
`C1-tourer T` + model `143 KB-LE lightweight 3.5 t Fiat`, or range `C1-tourer` + model
`T 143 KB-LE ...`, only the export says.
