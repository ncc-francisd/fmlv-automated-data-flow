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

## The baseline, and the thing it exposed

FMLV holds **53 live rows, every one already 2027** — so the requester's bump has been done
and the year needs no proposing.

### The model does *not* carry the chassis. A separate column does.

This corrects the survey above. FMLV splits a Carthago like this:

| `manufacturer_range` | `model` | `base_vehicle_manufacturer` |
|---|---|---|
| `C1-tourer` | `T 143 KB-LE lightweight 3.5 t` | `Fiat` |
| `C1-tourer` | `T 143 KB-LE lightweight 3.5 t` | `Mercedes` |

The public card reads *"Carthago C1-tourer T 143 KB-LE lightweight 3.5 t Fiat"* because the
site appends the base vehicle to the display — not because the model contains it. **No
manufacturer anywhere in FMLV puts a chassis name in a model**; checked across all 41
exports, there is not one.

Note also that FMLV's ranges are not the site's. The site sells `C1-tourer T` and
`C1-tourer EDITION+`; FMLV has range `C1-tourer` with the `T` pushed into the model. Its
`chic c-line` range holds both the A-class `I` models and the semi-integrated `T 4.9 LE`.
And FMLV spells Iveco `IVECO`.

### 22 of the 53 rows are invisible to the pipeline

**`(manufacturer_range, model)` is the product's identity everywhere** — `_dedupe_baseline`,
`diff.matching`, `store.products.upsert_seen`, and a
`UNIQUE (manufacturer_id, vehicle_class, manufacturer_range, model)` constraint in the
database. The base vehicle appears in none of them.

So Carthago's 53 live rows collapse to **31 distinct keys**, and `_dedupe_baseline` discards
**22 products** before matching starts — no disappearance notice, because a discarded
duplicate never reaches the diff:

```
discarded 6303 (Fiat) in favour of 6315 (Mercedes)  ->  chic c-line / I 4.9 LE
discarded 6304 (Fiat) in favour of 6316 (Mercedes)  ->  chic c-line / I 4.9 LE L
... 22 in total
```

An adapter that emits all 76 would then propose those 22 as new, giving FMLV a second copy
of each.

### Frankia already has this, and is already losing a row

`Noctra / Cruiser 7.6 L` exists twice — **8888 Mercedes** (MRO 3788) and **8889 Fiat** (MRO
3837), same price. `frankia.py` declares one `_Layout` for it and emits one product, so on
every run one of the pair is discarded and the survivor takes the match. One row, silently,
since 2026-09-19.

That makes this a **pipeline gap rather than a Carthago quirk** — Carthago is simply the
brand that makes it impossible to ignore, at 42% of its line-up instead of 3% of Frankia's.

## How it was resolved

The requester chose the pipeline change on 23 September 2026: *"if the base vehicle is
different then it is a different vehicle … we are not getting lots of new models when
they are not really new models."* The chassis now joins product identity in
`_dedupe_baseline`, `diff.matching`, `store.products` and the `product` table's unique key.
All 53 rows survive the baseline, and Frankia's Noctra Cruiser pair stopped being dropped
at the same time.

He drew the neighbouring line in the same breath, and it is in
`docs/adapters/README.md`: **a trim or option package is not a different product** unless
it carries a name of its own. Carthago's `lightweight 3.5 t` and `comfort 4.2 t` are named,
are different homologated weight classes, and FMLV already holds them separately — so
they stay as they are.

## What the build settled

### Identity comes from the page it was found on

Titles are `C1-tourer T 143 KB-LE lightweight 3.5 t` and the series is stripped off the
front. But **one title drops its layout letter** — the T 148 KB-LE H is headed
`C1-tourer 148 KB-LE H comfort 4.2 t` — so `RANGES` carries the letter per range page
and `identity_for` restores it. FMLV holds the `T`.

The chassis comes from the JSON where a range has one and from the URL otherwise:
**eight C2-tourer permalinks end `-2` and never name it**, which on this manufacturer is
half a product's identity.

### A page with no technical table is still a product

The T 148 KB-LE H pages publish nothing at all — no weights, no dimensions, no price.
Dropping them was the obvious thing and was wrong: their FMLV rows went unclaimed, and the
matcher handed 8899 and 8904 to two unmatched **C2-tourer** products and proposed renaming
a C1-tourer into one. They are now collected on their identity alone, which claims the row,
proposes no field and leaves FMLV's figures standing as no-op rows.

### Three Fiat chic c-lines really have gone

`I 5.0 QB`, `I 5.0 QB L` and `I 6.2 XL QB` are listed on the site **only as Mercedes**.
FMLV holds a Fiat of each. Those three disappearance notices are genuine — Carthago have
withdrawn the Fiat chassis on those layouts — and are the one case here where
deactivating is the right answer.

## First run — #127, 2026-09-23

76 collected against 53 baseline: **48 changed, 2 unchanged, 26 new, 3 disappeared**, 689
proposals, **371 fields verified unchanged** and 76 habitation findings.

The two unchanged are the T 148 KB-LE H pair, which propose nothing because their pages
publish nothing. The 26 new are almost all C2-tourer: FMLV held four of that range, all
Mercedes, where the site sells 26 across both chassis.

Four model names are corrected rather than renamed — FMLV writes the C2-tourer's weight
class as `4.2t` and `3.5t` where every other range and the site itself write `4.2 t`.

Every product proposes a new price, a new mass in running order and a seat count; the seat
figure is Carthago's own *"maximum number of seats with 3-point safety belt"*, which is the
settled rule in their words.

## Fetches per run

**85** — nine range pages for the roster, then one per product. Easily the largest of any
adapter here; the sweep takes about two minutes.
