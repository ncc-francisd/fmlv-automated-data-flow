# Benimar — site survey

Surveyed and built 14 September 2026. FMLV manufacturer id **236**, name **`Benimar Ocarsa
S.A.U.`**, display name **`Benimar`**. Motorhomes and one campervan range. **Sixteen
layouts**, and FMLV holds sixteen rows.

Fourth of the six Trigano brands, after Auto-Sleepers, Panama and Mobilvetta.

## The source is Marquis, and only Marquis

Marquis Leisure describe themselves as *"the exclusive distributor of Benimar motorhomes in
the UK"*, so the settled importer rule in `README.md` applies in full — and as with
Mobilvetta and Panama, their own range pages carry the numbers as well as the roster and
the price. **`benimar.es` is never fetched.**

The requester's warning about this site still governs the roster: *"you need to be careful
to find not the pages with used stock, but the pages with their brand lineup"*. The roster
comes from `/new-motorhomes/benimar` and only `…-range` slugs are admitted.

## Marquis run two templates, and are mid-redesign

**This is the finding that matters most, and it belongs to all four Marquis brands rather
than to Benimar.** The Mobilvetta survey saw one template and described it as *the*
template. Benimar publishes both, one page against three.

| | older — Primero | newer — Mileo, Tessoro, Benivan |
| --- | --- | --- |
| table heading | `Weights and Dimensions` | `Dimensions` |
| labels | `OVERALL LENGTH`, shouted | `Length`, title case |
| model name | `Primero 201`, title case | `Mileo 243`, title case |
| MIRO | not printed | **printed**, beside MTPLM and payload |
| the two options | `MTPLM 3500kg / 3650kg`, a payload row per chassis | two columns, `Manual` then `Auto` |

```
Primero 201  Weights and Dimensions
BERTHS 2   BELTS 4
OVERALL LENGTH 5950mm | 19'5"
OVERALL WIDTH (MIRRORS FOLDED) 2300mm | 7'6"
OVERALL HEIGHT 2890mm | 9'5"
MTPLM 3500kg / 3650kg
MAX USER PAYLOAD (3500KG CHASSIS) Manual 764kg / Auto 724kg
MAX USER PAYLOAD (3650KG CHASSIS) Manual 914kg / Auto 874kg
FIAT DUCATO 140BHP MANUAL ENGINE  £63,090 OTR
```

```
Mileo 243  Dimensions
Berths 4   Belts 4
Length 6990mm | 22'11"   Width (Mirrors Folded) 2300mm   Height 2890mm | 9'5"
Weights (kg)       Manual   Auto
MTPLM              3650kg   4400kg
MIRO               3149kg   3189kg
Max User Payload    501kg   1211kg
FIAT DUCATO 140BHP MANUAL ENGINE  £82,995 OTR
```

`marquis.py` now reads both: it anchors on the marker rather than on the shape of the
heading, and every field pattern anchors on the part of the label the two share.

### The first build collected zero of sixteen

The block reader required an **upper-case** heading, because that is what Mobilvetta
writes. Benimar's are title case, so nothing matched and run #87 collected nothing at all
against a sixteen-row baseline.

Nothing arithmetic could have caught that. **The roster count did**, which is why
`EXPECTED_LAYOUTS` is pinned and why a mismatch is narrated loudly.

## The roster: four pages, sixteen layouts

| Marquis page | layouts |
| --- | --- |
| `benimar-primero-2026-motorhome-range` | Primero 201, 202, 282, 286 |
| `benimar-mileo-2026-motorhome-range` | Mileo 243, 282, 286, 294 |
| `benimar-tessoro-2026-motorhome-range` | Tessoro 413, 463, 481, 487, 840, 861 |
| `benimar-benivan-2026-campervan-range` | Benivan 122, 144 |

## The figures, measured

| layout | berths | belts | length | width | height | MTPLM | MIRO | payload | price |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primero 201 | 2 | 4 | 5950 | 2300 | 2890 | 3500 | *2736* | 764 | £63,090 |
| Primero 202 | 4 | 4 | 5950 | 2300 | 2890 | 3500 | *2839* | 661 | £65,090 |
| Primero 282 | 4 | 4 | 7390 | 2300 | 2890 | 3500 | *3026* | 474 | £68,090 |
| Primero 286 | 4 | 4 | 6950 | 2300 | 2890 | 3500 | *2991* | 509 | £68,090 |
| Mileo 243 | 4 | 4 | 6990 | 2300 | 2890 | 3650 | 3149 | 501 | £82,995 |
| Mileo 282 | 4 | 4 | 7390 | 2300 | 2890 | 3650 | 3216 | 434 | £84,995 |
| Mileo 286 | 4 | 4 | 6950 | 2300 | 2890 | 3650 | 3131 | 519 | £82,995 |
| Mileo 294 | 4 | 4 | 7390 | 2300 | 2890 | 3650 | 3254 | 400 | £84,995 |
| Tessoro 413 | 4 | 4 | 6410 | 2300 | 2890 | 3500 | 3035 | 465 | £74,995 |
| Tessoro 463 | 4 | 4 | 7380 | 2300 | 2890 | 3500 | 3120 | 380 | £76,995 |
| Tessoro 481 | 4 | 4 | 5980 | 2300 | 2890 | 3500 | 2920 | 580 | £74,995 |
| Tessoro 487 | 4 | 4 | 6980 | 2300 | 2890 | 3500 | 3070 | 430 | £76,995 |
| Tessoro 840 | 3 | 4 | 5990 | 2140 | 2760 | 3500 | 2745 | 755 | £74,995 |
| Tessoro 861 | 3 | 4 | 6690 | 2140 | 2760 | 3500 | 2800 | 700 | £74,995 |
| Benivan 122 | 2 | 4 | 6360 | *—* | 2650 | 3500 | 2905 | 595 | £61,995 |
| Benivan 144 | 2 | 4 | 5990 | *—* | 2650 | 3500 | 2834 | 666 | £59,995 |

*Italic* MIRO is derived; *—* is deliberately not recorded, see below.

**Every layout is priced**, and the price is the last thing in a block — after the bed
sizes and the tolerance footnote. Stopping a block short of the next heading lost three of
the four Primero prices, the same fault a fixed window caused on Mobilvetta.

## Take the first figure in every row

Three different ways of printing an option, one rule:

* `MTPLM 3650kg 4400kg` — manual before automatic;
* `MTPLM 3500kg / 3650kg` — the lighter chassis before the heavier;
* `MIRO 2834kg` before `MIRO (Pop Top) 2964kg`.

In all three the first is the base vehicle, and it is the one the quoted OTR price buys —
the pages name the engine in that price line, and it is always the manual.

Likewise `Berths 2 | Optional 4 Berth Pop Top (Manual)` records **2**, by the settled rule
that a berth range takes the lower figure.

## There is a self-check after all

The Mobilvetta survey concluded *"this adapter has no arithmetic check at all"* and
extended that to every Marquis brand. **For the newer template that is wrong.** Twelve of
the sixteen layouts print MTPLM, MIRO and payload together, so the three must close, and a
figure taken from the automatic column instead of the manual misses by about 40 kg. That is
the fault worth catching, and it is now caught.

The four Primero layouts remain unchecked in that sense — but their two chassis rows are
two routes to one mass in running order, which corroborates the parse.

### Two places Benimar's own arithmetic does not close

Both hand-verified against the pages, both **kept and narrated** rather than dropped:

* **Mileo 294** prints MTPLM 3650 kg, MIRO 3254 kg and payload 400 kg. Those miss by 4 kg;
  the automatic column beside them closes exactly. Four kilograms cannot be a misread.
* **Primero 282** gives the 3650 kg chassis 574 kg of payload where the 3500 kg chassis
  gets 474 kg — 100 kg apart where the chassis are 150 kg apart. Every other Primero moves
  both together. The wrong figure is in **a row this pipeline does not record**.

Neither is a reason to withhold a vehicle Marquis really sell, so the reconciliation judges
only the figures that reach FMLV and reports the rest.

## Width is not recorded for the Benivan

Marquis print `Width (Mirrors Folded) 2260mm` for both Benivan layouts. **On a panel van
that figure is the mirrors, not the body**: a Ducato's body is about 2050 mm and its folded
mirrors reach about 2260 mm. FMLV already holds **2050** for both, and for Mobilvetta's
Admiral campervan too.

On a coachbuilt the same label means the opposite: the 2300 mm habitation body overhangs the
folded mirrors, so the figure does measure the body. That is why only the campervan range
is affected.

The requester's ruling, 12 September 2026: *"if they don't have a figure excluding mirrors,
we'll have to leave that blank as we don't have the correct figure, unless it's an existing
model that appears to have the same height and length."* Emitting nothing satisfies both
halves — Benivan 144 keeps the 2050 mm FMLV holds, and the new Benivan 122 goes in visibly
blank rather than 210 mm too wide.

**It applied to Mobilvetta's Admiral K 6.3 and to every Panama layout too**, and both were
brought onto the same rule on 15 September 2026 — the rule now lives in
`base.width_from_mirrors_folded`. See `docs/adapters/mobilvetta.md` and `panama.md` for what
each of those was proposing before.

## Benivan 161 is discontinued, not renamed

FMLV holds `Benivan 161`; Marquis now publish `Benivan 122`. That is the shape a rename
makes, so it was checked rather than assumed:

| | length | MIRO | payload | price |
| --- | --- | --- | --- | --- |
| FMLV Benivan 161 | 5995 | 2844 | 656 | £59,495 |
| Marquis Benivan 122 | 6360 | 2905 | 595 | £61,995 |

**365 mm apart.** The 161 was the same length as the 144; the 122 is a longer van. They are
different vehicles, so the 161 has been withdrawn and the 122 introduced.

## Habitation

Read from the **range's standard-equipment list** for the fittings, and from each layout's
own `Bed Sizes` list for the beds — a page covers up to six vehicles, so a bed named in the
equipment list could belong to another layout.

```
145 litre fridge/freezer with automatic energy selection (excl 286)
Truma combi 6kw heating & water system which operates on gas or electric
Fully separate shower
Thetford cassette toilet with electric flush & 18 litre wheeled holding tank
```

`Optional Elevating Roof Bed` is dropped on both Benivans — a pop-top the buyer may not
have bought. `habitation.usable_lines` does not catch it, because the page neither prices
it nor writes `Option:`.

## Still unverified

* **Two gaps in the shared habitation vocabulary**, both left alone because changing it
  touches five other adapters and belongs in its own commit:
  * `fixed rear bed` yields no bed type, where `fixed double bed` does. It is a common
    phrasing and appears in the Auto-Sleepers, Eriba and Mobilvetta fixtures too.
  * `Combined washroom with wash basin & shower area` — the Benivan's wording — is not read
    as *not* separated, so `shower_toilet_separated` is left blank rather than `False`.
* **Floorplans.** Not examined.
* **Whether Benimar's own figures differ from Marquis's.** FMLV's lengths and widths are
  consistently a few millimetres off Marquis's (2316 against 2300, 5999 against 5950), which
  looks like factory figures against importer ones. `benimar.es` was not fetched to check,
  per the single-source decision above.
* **Whether the older Primero template will be redesigned too.** If Marquis convert it, it
  gains a printed MIRO and the adapter needs no change.
