# Malibu (id 64)

Surveyed 2026-09-25. Part of the **Carthago Group**, and its own About page says so — but
**the website is not Carthago's**, which is the first thing to get straight.

- Source: <https://www.malibu-carthago.com/en/>
- NCC supplier name: `Malibu`
- `fmlv_manufacturer`: `Malibu` — id 64, the same word in both roles for once.

## It is the same group, not the same site

Carthago's adapter reads a `cgrb__data` JSON blob and `data-compare-brand-icon` cards.
**Neither exists here.** `carthago.py` cannot be pointed at this domain:

| marker | carthago.com | malibu-carthago.com |
|---|---|---|
| `cgrb__data` | yes | **0** |
| `data-compare-brand-icon` | yes | **0** |
| `cgrb_return` | yes | **0** |
| `MPL_PREISLISTE=GB` | yes | yes |

What *is* shared is the configurator (so the GB price list applies) and the general shape
of a product page. The adapter will be a sibling of `carthago.py` in structure and a
rewrite in detail.

## Two product areas, which Carthago did not have

Malibu sell **camper vans as well as motorhomes**, where Carthago is motorhomes only. Both
are the motorhome product area in FMLV, but they take different body types, and the vans
are on a different URL shape.

### Motorhomes — four ranges, 39 products

| range | path | products |
|---|---|---|
| A-Class | `/en/motorhome/a-class-motorhome/` | **19** |
| A-Class Edition + | `/en/motorhome/a-class-motorhome-edition-plus/` | 2 |
| Coachbuilt | `/en/motorhome/coachbuilt-motorhome/` | **16** |
| Coachbuilt Edition + | `/en/motorhome/coachbuilt-motorhome-edition-plus/` | 2 |

**39**, and the A-Class figure checks out against the site's own claim — its range page
states `19 layouts`, and `9 layouts on a Fiat Ducato chassis` plus `10 layouts on a
Mercedes Benz`, which is exactly the 19 found.

As on Carthago, **a product is a layout, a trim and a chassis**, and the letter is the body
type: `I` for A-class, `T` for coachbuilt. `malibu-i-430-kb-le-comfort-fiat-ducato`.

### Camper vans — five ranges plus *genius*, roster incomplete

`compact`, `comfort`, `diversity`, `first class - two rooms`, `relax`, and the `genius`
line (which has its own 4x4 performance page). Five products found so far —
`compact-540-db`, `compact-600-le`, `comfort-600-db`, `comfort-640-le`, `genius-641-le` —
but **three van ranges return nothing to the pattern that works for the other two**, so
their slugs differ again. This is the one part of the survey still open.

Van slugs carry **no chassis**, which fits a single-chassis range but needs confirming.

## The roster has two URL shapes, and that cost a pass

A motorhome product sits at **either**:

- `/en/motorhome/a-class-motorhome/malibu-i-430-kb-le-comfort-fiat-ducato/`, or
- `/en/malibu-i-441-kb-le-comfort-mercedes-benz/` — **at the site root**.

Ten of the A-Class 19 are under the range path and nine are at the root. A reader that
scopes to the range path finds 10 and reports the range as shrunk by half.

Matching `malibu-(i|t|edition)[-0-9]` anywhere in the href finds all 19. The motorhome
pages carry the whole roster in a shared nav, so one fetch lists every motorhome product —
the van pages do not, and link only their own.

## What a product page publishes

```
Basic vehicle                                              Fiat Ducato
Standard chassis                                           Low frame 40 heavy
Transmission                                               8-speed automatic torque converter
Total length (mm)                                          6850
Total width (mm)                                           2170**
Total height (mm)                                          2970
Rear garage interior height (mm)                           1200
Technically permissible gross vehicle weight (kg           4250
Weight in running order (kg) | Legal tolerance of -/+ 5 %  3.013 (2.862 - 3.164)
Max. weight of additional equipment in series production…  869
Max. number of seats with 3-point / 2-point safety belt…   4
Standard sleeping places                                   4
Optional sleeping places                                   5
Fridge volume (l)                                          133
Freezer compartment volume (l)                             12
Heating system                                             Truma Combi 6
```

Better than Carthago in two ways: **length, width and height are separate labels already in
millimetres**, and **standard and optional berths are separate labels** rather than a
`4 / 5` string to split.

`Max. weight of additional equipment in series production` is **not** FMLV's payload — the
same trap as Carthago's and Frankia's `Nutzlast`. Payload is `MTPLM − MRO`.

## The self-check is Carthago's, and it is labelled

`Weight in running order (kg) | Legal tolerance of -/+ 5 %` → `3.013 (2.862 - 3.164)`.
Malibu **name the tolerance in the label**, where Carthago left it to be inferred. 3013 ×
0.95 = 2862 and × 1.05 = 3164, to the kilogram. Same per-product verification, no second
document needed.

## The seat label names two kinds of belt and means one

```
Max. number of seats with 3-point / 2-point safety belt while driving
```

**Carthago's equivalent says three-point only**, and the settled rule is that a lap belt is
not a travel seat. So the worry was that Malibu's figure quietly includes one.

It does not. Across all 19 A-Class products the label is **identical and the value is
always 4**, and **no page mentions a two-point belt, a lap belt, or any belt at all**
outside that one line. It is boilerplate covering the range, not a statement about a
vehicle — and Carthago, same group and same chassis, states three-point-only and also says
4 on comparable models.

The requester ruled on 25 September 2026: *"on the website, which we normally take as our
aim to reflect, it says four, so perhaps we follow that."* **Record the published figure.**

**The assumption is made self-checking rather than left silent.** If any page ever names a
two-point or lap belt, the adapter narrates it instead of counting it, because the day that
appears is the day this reading stops being safe.

## Smaller traps, all real

- **`malibu-i-441-le-lightweight-fiat-duacto`** — the chassis is misspelt in the slug.
  A reader matching `fiat-ducato` drops that product.
- **`Technically permissible gross vehicle weight (kg`** — the bracket is never closed.
- **`4 / 5 (Sstandard / optional)`** appears on some pages — Malibu's typo, on a label that
  elsewhere reads `Standard sleeping places` as its own row. **Two layouts of the same
  facts**, so both need reading.
- **`2170**`** — dimension values carry footnote asterisks.
- Pages are **large**: the A-Class range page is 3.5 MB.

## Prices

In **sterling**, on the range page (`from £91,410`) and per product. No euro sign anywhere
in the product area, and the configurator carries `MPL_PREISLISTE=GB`, so unlike Carthago
there is no currency question to settle.

## Model year

The requester expects 2027. Not yet confirmed on the site — worth checking the image asset
names for an `MJ2027` marker as Carthago's carried.

## Still needed before a build

1. **There is no FMLV export for id 64**, so no model name, range name or live count has
   been checked against what FMLV holds.
2. **The van roster is incomplete** — three of the five van ranges use a slug shape not yet
   identified.
3. ~~The seat-belt ruling~~ — settled 25 September 2026, see above.
