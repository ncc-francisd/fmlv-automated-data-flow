# Elnagh — site survey

Surveyed and built 14 September 2026. FMLV manufacturer id **233**, name and display name
**`Elnagh`**. **NCC supplier name `Elnagh`.** Motorhomes only. **Four layouts**, and FMLV
holds four rows.

Fifth of the six Trigano brands.

## The source is Marquis, and only Marquis

Marquis Leisure are the sole UK importer, so the settled importer rule applies and — as
with Benimar, Mobilvetta and Panama — their own range page carries the numbers as well as
the roster and the price. **`elnagh.com` is never fetched.**

The requester found this page himself: *"I've just spotted that panel has got an extra
brand on it now, which is Elno… This page has all the specifications. I think they are
saying they're twenty twenty six, but that's fine. We'll catch it when it changes."*

### The parent sells far more than Marquis do

`elnagh.com` lists several ranges. **Marquis sell the Baron and nothing else**, which is the
standing warning made concrete — *"ranges in the parent website may comprise greater numbers
of models than offered in the UK"* — and the importer rule settles it.

The requester had already fixed the roster independently, before the page was found: *"the
only UK available ones are the ones on FMLV, which are these. Baron 530, Baron 560, Baron
573, Baron 579."* The page agrees exactly.

Note that **the Baron moved brands**: it was a McLouis range in 2025 and is an Elnagh one
now. That is why McLouis's current UK line-up is the `Fusion` 330/360/373/379, whose layout
numbers run parallel to the Baron's.

## The roster: one page, four layouts

| Marquis page | layouts |
| --- | --- |
| `elnagh-baron-2026-motorhome-range` | Baron 530, 560, 573, 579 |

The brand index corroborates the count independently: it carries a `View our Stock` link per
layout, and there are exactly four.

## The figures, measured — and every one already agrees with FMLV

| layout | berths | belts | length | width | height | MTPLM | MIRO | payload | price |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baron 530 | 4 | 4 | 6590 | 2350 | 2950 | 3500 | *2910* | 590 | £67,995 |
| Baron 560 | 4 | 4 | 6990 | 2350 | 2950 | 3500 | *2910* | 590 | £67,995 |
| Baron 573 | 4 | 4 | 7410 | 2350 | 2950 | 3500 | *2950* | 550 | £69,995 |
| Baron 579 | 4 | 4 | 7410 | 2350 | 2950 | 3500 | *2940* | 560 | £69,995 |

*Italic* MIRO is derived.

**Run #90 collected four products, changed nothing, and verified 44 fields unchanged.**
Length, width, height, MTPLM, payload, the derived mass in running order and the price all
match what FMLV already holds, on all four layouts. That is an independent proof of the
parse — the same proof Panama gave — and the only proposals are the four model-year bumps.

```
2026 ELNAGH BARON COACHBUILT MOTORHOME RANGE  Baron 530  Weights and Dimensions
BERTHS 4   BELTS 4
OVERALL LENGTH 6590mm | 21'7''
OVERALL WIDTH (MIRRORS FOLDED) 2350mm | 7'7''
OVERALL HEIGHT 2950mm | 9'8''
MTPLM 3500kg / 3650kg
MAX USER PAYLOAD (3500KG CHASSIS) Manual 590kg / Auto 550kg
MAX USER PAYLOAD (3650KG CHASSIS) Manual 740kg / Auto 700kg
Bed Sizes  DROP DOWN BED 1900 x 810mm   DOUBLE REAR BED 1300 x 1100 x 1900mm
FIAT DUCATO 140BHP MANUAL ENGINE  £67,995 OTR
```

## The older template, and the check it does offer

Elnagh is on the **older** of Marquis's two page templates — `Weights and Dimensions`,
shouted labels, **no printed MIRO**, and a payload row per chassis. So the mass in running
order is derived.

What the page does print is two chassis, and they are independent routes to one figure:

* 3500 − 590 = **2910**
* 3650 − 740 = **2910**

All four layouts agree with themselves this way, unlike Benimar's Primero 282, whose two
rows are 50 kg apart. **A disagreement is narrated rather than fatal**, by the same
reasoning as there: the figure at fault would be in the heavier chassis row, which this
pipeline does not record.

With no arithmetic that can drop a product, **the roster count is the main structural
defence** and a change in it is narrated loudly.

## The equipment list qualifies itself per layout

The single most important thing on this page after the weights:

```
Separate shower and toilet compartment (579 and 573 only)
Combined shower and toilet compartment (530 and 560 only)
```

Read range-wide, whichever line came first would settle `shower_toilet_separated` for all
four. **FMLV holds No, No, Yes, Yes** across 530/560/573/579 — which is the page read per
layout. So this is not a refinement; it is the difference between right and wrong.

`marquis.lines_for_layout` handles it, and **Benimar qualifies the same way** with
`(excl 286)` and `(286)` on its two fridge sizes — where both happen to be fridge-freezers
and the fault would have gone unnoticed.

A qualifier must be **nothing but layout codes and the words joining them**, so
`(MIRRORS FOLDED)`, `(3500KG CHASSIS)` and `(230v socket)` are left alone.

`530` and `560` end up `None` rather than `False`, because "Combined shower and toilet
compartment" is not read as a denial — silence is not a negative, and FMLV's `No` is a
reviewer's judgement rather than something the page asserts.

## Bed sizes are written differently from Benimar's

```
DROP DOWN BED 1900 x 810mm            only the last figure suffixed
DOUBLE REAR BED 1300 x 1100 x 1900mm  three dimensions
```

against Benimar's `Double Drop Down Bed 1400mm × 1900mm`. Requiring the suffix on the first
figure found **none** of Elnagh's four drop-down beds — which FMLV holds for all four. The
shared reader now swallows everything up to the first `mm`.

## Body type

Low-profile coachbuilt for all four, on three agreeing pieces of evidence: Marquis head the
page `COACHBUILT MOTORHOME RANGE`, every block's bed list names a **drop-down** bed rather
than a fixed over-cab one, and FMLV already holds `type_coach_built_low_profile` for all
four. The 2950 mm height is no objection — Mobilvetta's KEA 86 and 90 are low profiles at
exactly that height.

## Width is recorded here, unlike Benimar's Benivan

`OVERALL WIDTH (MIRRORS FOLDED) 2350mm`, and on a coachbuilt that is the body: a 2350 mm
habitation body overhangs a Ducato's folded mirrors. The rule and the contrast are in
`README.md`; Elnagh has no panel van, so the question does not arise.

## One trap at the foot of the page

The page **defines MIRO in prose** in its glossary:

> Mass In Running Order (MIRO) — weight of the motorhome equipped to the manufacturer's
> standard specification…

The last block's body runs to the end of the page, so that text is inside it. Only
`MIRO <n>kg` counts as a figure, so nothing is read from it — pinned by a test.

## Still unverified

* **Floorplans.** Not examined.
* **Whether Elnagh's own figures differ from Marquis's.** Not checked, and unlike Benimar
  there is no evidence they do — FMLV agrees with Marquis on every field.
* **Whether Marquis will move this page to the newer template.** If they do it gains a
  printed MIRO and the adapter needs no change.
* **The caravans export.** `233_Elnagh` has a `touring-caravans` export, and it is empty.
