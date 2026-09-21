# Campod (Leisure Pods Ltd, id 253)

Surveyed 2026-09-21. **Caravans** — small towed pods, all `type_micro` in FMLV.

- Source: <https://www.campodcaravans.com/>
- NCC supplier name: `Campod`
- `fmlv_manufacturer`: `Leisure Pods Ltd`

## Which manufacturer row

Two rows share the **same** `fmlv_manufacturer`, so the display name is what separates
them — and it is part of the adapter key:

| id | `fmlv_manufacturer` | display | in the export? |
|---|---|---|---|
| 130 | `Leisure Pods Ltd` | `Campod Caravans` | no |
| **253** | **`Leisure Pods Ltd`** | **`Campod`** | **yes, all three rows** |

The requester confirmed 253 as the newer row, and the export agrees: every row carries
`manufacturer_display_name = Campod`.

## The baseline

Three live rows, all 2026, all range `O2`, all `type_micro`, all sharing one set of
dimensions:

| model | MTPLM | MRO | payload | price |
|---|---|---|---|---|
| M | 900 | 790 | 52 | £26,995 |
| N | 1000 | 800 | 142 | £26,995 |
| Laura Ashley | 900 | 775 | 125 | £29,995 |

Dimensions, identical on all three and matching the diagram the requester supplied:
shipping length 4305, width 2000, height 2340, headroom 1930, body length 3605, internal
length 2830, awning 2570.

Only the Laura Ashley's payload reconciles (900 − 775 = 125). M's is 52 against an
arithmetic 110, and N's 142 against 200.

## Where the data is

Wix, and everything worth having is on **one product page**,
`/product-page/campod-caravan`, which states it plainly:

```
Dimensions                        Weights
Total length     4305 mm          MTPLM  800kg (upgrade to 900kg & 1,000kg available)
Total width      2000 mm          MiRO   750kg
Total height     2340 mm          Nose weight
Standing height  1905 mm (6 ft 3")
```

The Laura Ashley has its own page, `/laura-ashley-campod`, with its own block:
`MiRO 775kg`, `MTPLM 900kg/1,000kg`.

Everything else in the shop is an accessory — the store sitemap lists fifteen products
and fourteen are jockey wheels, covers and water containers.

## The thing to understand: MTPLM is an option, not a model

The product page has exactly two dropdowns, **Colour scheme** and **MTPLM**, and the
MTPLM one offers **800kg, 900kg, 1000kg**. The page carries three prices to match:

| MTPLM | price |
|---|---|
| 800 kg | £26,995 |
| 900 kg | £27,095 |
| 1,000 kg | £27,555 |

So the site sells *one* configurable caravan plus a Laura Ashley edition. FMLV instead
holds the chassis ratings as **separate products** — `M` at 900 kg and `N` at 1000 kg —
and the newly offered 800 kg version has no row.

That is almost certainly the "new one" the requester spotted: the home page promotes
**"MTPLM of 800kg available"** as a new option, and 800 is the only rating FMLV lacks.

## The base vehicle is the 800 kg version

Under the settled rule, where a manufacturer offers several ratings for one vehicle the
base is recorded, not the upgrade. The page says so in as many words: *"800kg (upgrade to
900kg & 1,000kg available)"*, with MiRO 750 kg beside it. So the base Campod is
**MTPLM 800 / MiRO 750**, a payload of 50 kg, at £26,995.

The Laura Ashley's own page applies the same shape — `MTPLM 900kg/1,000kg`, MiRO 775 —
and FMLV already holds the lower of the two, 900, with 775. That row needs nothing.

## What the site does not publish

**A mass in running order per chassis rating.** The product page states one figure, 750 kg,
which is the base. The only hint that it varies is prose on the home page: *"With a MiRO
of 750kg's to 800kg's and MTPLM options ranging from 800kg to 1,000kg"*. Nothing maps a
MiRO to a rating.

FMLV's `M` holds 790 and `N` holds 800, both inside that stated range and neither
derivable from anything published. They may well be right; they simply cannot be
confirmed or refreshed from this site.

**A payload.** Campod publish none, so it would be derived as MTPLM − MiRO.

**Nose weight** appears as a label on the product page with no value; the requester's
diagram gives 50 kg.

Two small conflicts with that diagram, which is otherwise exact: it gives MiRO as
"750 - 775kg depending on MTPLM chosen" where the site's prose says 750–800, and standing
height 1905 mm where FMLV holds a headroom of 1930.

## The self-check

Weak. Campod publish no payload, so there is no arithmetic to test a parse against, and
the whole specification is a dozen lines on one page. What is checkable is that the
figures are internally consistent and that the diagram the requester supplied agrees with
the page on all four dimensions — which it does, exactly.

## The answer, and the shape of the adapter

The requester settled it on 21 September 2026:

> *"M and N aren't sold as separate models anymore. They simply sell a Campod Caravan
> with slightly different options … take the lower end of the weight spectrum as the base
> for a Campod Caravan and then the lower option for the Laura Ashley version, which is
> the 900 kilogram, which would leave us just with two models."*

So the adapter emits **two** products, each at the bottom of its own range, and maps the
standard caravan onto `M` so one product id keeps its images and hand-entered habitation
flags. `N` is left unmatched and retires.

That mapping is a **consolidation, not a rename discovery**, and the module says so: the
usual mass test cannot identify it, because all three FMLV rows already share one set of
dimensions and `M` and `N` differed only by a rating that is now a dropdown option.
Choosing `M` preserves a row rather than finding one.

## First run — #117, 2026-09-21

2 scraped against 3 baseline: **2 changed, 0 new, 1 disappeared** (`N`). 15 fields
verified unchanged.

| | proposed |
|---|---|
| `O2 / Campod` | model `M` → `Campod`, MTPLM 900 → 800, MiRO 790 → 750, payload 52 → 50, headroom 1930 → 1905 |
| `O2 / Laura Ashley` | headroom 1930 → 1905 |

What is *absent* is as telling: the Campod's price, total length, width and height all
verified unchanged, and the Laura Ashley's MTPLM and MiRO verified at 900 and 775 — FMLV
already held the lower option for that edition.

The headroom change is well evidenced: the product page and the requester's own dimension
diagram both say 1905 mm, against FMLV's 1930.

### The trap the tests caught

**`MTPLM` labels two different things on the product page** — the chassis dropdown, whose
next line is the `*` marking it required, and the Weights block. Taking the first
occurrence read the asterisk. Every occurrence is now tried until one is followed by a
figure.
