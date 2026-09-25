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

## What the build settled

**The range comes from the product's own name, not the page it was found on.** All four
motorhome range pages list the same 28 products, so the page proves nothing. Only two are
Edition + and Malibu say so in their names: `Edition + I 490 RB-LE` and
`Edition + T 490 RB-LE`. Nothing else carries it, on any page.

**FMLV groups them differently** — `I450`, `I470 K`, `I480 K` and `I490` under
`A-Class Edition +`, and the matching `T` layouts under `Coachbuilt Edition +`, sixteen
rows in all. Nothing on the site today supports that, so `range_for` follows the site and
twelve rows are proposed as moving to their base range. That function is the one place to
change if the existing grouping is to be kept instead.

**Two pages have a table that slipped a row.** The Coachbuilt Edition + T 490 pages print
`1050 x 1140` under `Technically permissible gross vehicle weight (kg)` — a rear-garage
door opening. Dropping them would have made two live rows look discontinued, so the
product is kept and only that mass withheld; everything else on those pages reads
normally. `_mass` refuses anything shaped like a dimension or outside 1500–8000 kg, and
the self-check now also refuses a gross weight below the mass in running order, which is
the test the first pass lacked.

**A van states no berth count of its own**, but the range hero does: `up to 4` /
`sleeping berths`, beside `Optional: Pop-up roof family-for-4` on the same page. **That is
not four berths** — the third and fourth need an option bought, and the settled rule takes
the lower figure of a range, which these pages never state. So nothing is proposed and
FMLV's 2 stands, which is also the reading its high-top body type implies.

The Genius is the exception and states a bare `2`, with no pop-up roof mentioned anywhere,
so that one is recorded. Every motorhome states its berths in the table as usual.

**Two false disappearances are named in the run**: `Genius 641 LE performance 4x4`, which
has a section page but no product page, and nothing else.

## First run — #131, 2026-09-25

47 collected against 42 baseline: **31 changed, 16 new, 11 disappeared**, 473 proposals,
**205 fields verified unchanged** and 44 habitation findings.

The **11 disappearances are all expected**: the ten `Van Charming` rows, which are option
packages rather than vehicles and which the requester ruled should be deactivated, and the
Genius 4x4.

The 16 new are the comfort or lightweight half of each pair FMLV holds singly, plus the
`I460`, `I500`, `T460` and `T500` layouts it does not have at all.

## Fetches per run

**57** — ten range pages and 47 products.
