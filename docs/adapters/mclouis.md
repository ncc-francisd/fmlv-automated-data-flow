# McLouis — site survey

Surveyed and built 15 September 2026. FMLV manufacturer id **35**, name **`Trigano S A
McLouis`**, display name **`McLouis`**. Motorhomes only. **Four layouts**, and FMLV holds
four current rows.

Last of the six Trigano brands, and the only one that is not a Marquis page.

## Marquis do not sell this one exclusively, and do not list it at all

The other five brands run through Marquis Leisure. McLouis does not: Marquis sell it and
manage other UK dealers alongside, and **the brand is absent from `marquisleisure.co.uk`
altogether** — no brand index, no range page, and missing from both the motorhome and
campervan line-up pages. So the usual importer-defines-the-range route does not exist, and
none of `adapters/marquis.py` applies.

The requester found the alternative: *"I found a separate site with the UK range of
McLouis, and it's called McLouis Fusion, which explains why FMLV has the Fusion range."*

**`mclouisfusion.co.uk` is the source**, and the brochure's back page shows why it reads
like the others in this group — it is published by **Auto-Sleepers Limited, Orchard Works,
Willersey**, the same address as Marquis. Hence the wording shared with `auto_sleepers.py`
("Maximum User Payload", "mirrors folded") and the equipment-list style shared with
`elnagh.py`.

`mclouis.com`, the Italian parent, is never fetched.

## The roster: four layouts, one page each

| page | layout |
| --- | --- |
| `/explore-the-range/fusion-330` | Fusion 330 |
| `/explore-the-range/fusion-360` | Fusion 360 |
| `/explore-the-range/fusion-373` | Fusion 373 |
| `/explore-the-range/fusion-379` | Fusion 379 |

**One page is one layout here**, unlike every Marquis brand, and the slug carries the model
code so the roster needs no parsing of prose. The count is stated independently twice: the
range page says *"4 coachbuilt models"* and the brochure cover says *"4 BERTHS MODEL RANGE
4 | 4 - 5 SEATBELTS"*.

FMLV also holds six 2022 and one 2024 row under `Fusion 1`, and **four 2025 `Baron` rows**
— the range that moved to Elnagh for 2026. `cli._is_current_model_year` drops all eleven.

## The figures, measured

| layout | belts | berths | length | width | height | MTPLM | MIRO | payload | price |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fusion 330 | 4 | 4 | 6590 | 2350 | *2770* | 3500 | 2910 | 590 | £74,995 |
| Fusion 360 | 5 | 4 | 6990 | 2350 | *2770* | 3500 | 2910 | 590 | £77,495 |
| Fusion 373 | 5 | 4 | 7410 | 2350 | *2770* | 3500 | 2950 | 550 | £79,495 |
| Fusion 379 | 5 | 4 | 7410 | 2350 | *2770* | 3500 | 2940 | 560 | £79,495 |

*Italic* height is what the page prints and **not** what is recorded — see below.

**Dimensions are published in metres**, to two decimals — `Overall length 6.59m` — not in
millimetres like every other brand in this group. The 360 page capitalises `Overall Length`
where the other three do not, so the labels are matched case-insensitively.

Run #92 collected four, changed four, and verified 44 fields unchanged, proposing the three
belt corrections, the one price correction and the four model-year bumps.

## The best self-check of the six

McLouis publish **three chassis columns** and label the payload row `(a-b)`:

```
MTPLM (a)*                   3500kg | 3650kg | 4400kg
Mass in running order (b)    2910kg | 2910kg | 2970kg
Maximum user payload+ (a-b)   590kg |  740kg | 1430kg
```

So each column is an independent statement that `MTPLM - MIRO = payload`, and **all twelve
closed exactly** at survey. A column read out of step with its neighbours — the fault worth
catching — breaks the identity at once.

The three rows must also be the **same length**, because a row yielding fewer figures than
its neighbours means the columns no longer line up, and pairing them by position would then
compare a 3500 kg chassis against a 4400 kg one.

The first column is the base vehicle and the one recorded, per the settled rule; it is the
3500 kg manual that the quoted price buys.

## Three disagreements with FMLV

### Height: overridden back to FMLV's 2950, on all four

The site says `Overall height 2.77m` and **the 2026 brochure independently prints `Height:
2770  9′ 1″`**. FMLV holds 2950, and so does Marquis for the Elnagh Baron — which, as
below, is the same vehicle rebadged.

**One vehicle cannot have two heights**, so this is not a case of two definitions but of one
of the two being wrong. The requester's decision, 15 September 2026: *"can we use the 2950
height, which is what we use on Find My Leisure Vehicle at the moment for both brands. I
think that's just a typo or something, but you're right, it must be the same."*

So `_KNOWN_HEIGHT_ERROR` records **2950** and neither brand proposes a height change. The
override is narrated on every run and **keyed on the published figure rather than on the
model**, exactly as `murvi._KNOWN_PRICE_TYPO` is: the day McLouis print anything other than
2770 mm it lapses, and the new figure is proposed normally instead of a stale correction
quietly overwriting a real change.

The provenance a reviewer sees says outright that 2950 is **not this page's figure**, so it
can never be mistaken for something McLouis published.

### Belts: 4 → 5, on the 360, 373 and 379

The site says `Designated Passenger Seats 5`, and two things confirm these are belts rather
than seating capacity:

* the brochure cover reads **"4 - 5 SEATBELTS"** across the range;
* the equipment list explains the difference — *"5th Homologated seat in running order
  (exc 330)"* — so it is standard, not an option.

Nothing on either document suggests a lap belt, so the settled rule to count three-point
belts only is satisfied. **FMLV's own older rows held 5** for the 360/373/379, so the
current 4s look like a carry-over from the Elnagh Baron.

### Price: the 330 alone, £77,495 → £74,995

**The brochure's price list disagrees with the site on three of the four:**

| | brochure | site | FMLV |
| --- | --- | --- | --- |
| 330 | £74,995 | £74,995 | £77,495 |
| 360 | £74,995 | £77,495 | £77,495 |
| 373 | £76,995 | £79,495 | £79,495 |
| 379 | £76,995 | £79,495 | £79,495 |

The settled rule is that **the website over-rules a document unless the site can be shown
wrong**, and FMLV's own figures match the site on three of four — so the site is taken and
only the 330 changes, which is the one where site and brochure agree anyway.

The brochure is internally inconsistent about its own date, saying both *"PRICES AND
SPECIFICATION EFFECTIVE 1ST APRIL 2026"* and *"Effective 1st October 2025"*, which is
further reason to prefer the live page.

## The Fusion is the Elnagh Baron rebadged

Worth recording, because it looks like a data error and is not:

| | length | MTPLM | MIRO | payload |
| --- | --- | --- | --- | --- |
| Fusion 330 / Baron 530 | 6590 | 3500 | 2910 | 590 |
| Fusion 360 / Baron 560 | 6990 | 3500 | 2910 | 590 |
| Fusion 373 / Baron 573 | 7410 | 3500 | 2950 | 550 |
| Fusion 379 / Baron 579 | 7410 | 3500 | 2940 | 560 |

Identical to the kilogram, and the washroom splits the same way (separate on the two long
layouts, combined on the two short). FMLV's four 2025 `Baron` rows sitting under **McLouis**
are the direct evidence of the move.

**The two brands disagree on exactly two things**, and they are resolved differently:

* **the fifth belt** is a real UK specification difference between importers — McLouis make
  it standard, *"5th Homologated seat in running order (exc 330)"*, and Elnagh do not — so
  both are recorded as published;
* **the height** cannot be a specification difference, because the shell is the same. One of
  the two published figures is simply wrong, and both brands are aligned to FMLV's 2950 mm.
  See above.

## Habitation

The equipment list **qualifies lines per layout**, in the same house style as Elnagh but
spelling the exclusion `(exc 330)` rather than `(excl …)`:

```
5th Homologated seat in running order (exc 330)
Separate shower and toilet compartment (373 and 379 only)
Combined shower and toilet compartment (330 and 360 only)
Pleated privacy separation curtain for rear bedroom area (373 & 379)
King size central bed with a width of 1500mm (379)
```

`habitation.lines_for_layout` handles all of these. `(model specific)` names nothing and so
restricts nothing.

**Bed sizes carry no `Bed` in the name** — `Rear Drop Down Double 1300 x1100x1900mm` — so
the split keys on the size and the word is appended afterwards. The unit lands
inconsistently within one page: once at the end, or on every figure (`1300mm x 2070mm`),
and one typo with a single `m` (`1500mm x 1900m`). Stopping at the first `mm` left `x
2070mm` behind, which the next iteration read as a bed named `x`.

The resulting bed types corroborate FMLV's Elnagh twins exactly — the 379 gives fixed,
island and drop-down, which is what FMLV holds for the Baron 579.

## Still unverified

* **Which of the two heights is physically right.** Both brands now record 2950 mm, on the
  requester's decision, but McLouis's own site and brochure both say 2770 mm. Worth an email
  to Auto-Sleepers so the published figure gets corrected at source; until then the override
  carries it.
* **Floorplans.** Not examined.
* **The caravans export.** `35_Trigano S A McLouis` has a `touring-caravans` export, and it
  is empty.
* **Whether the brochure's price list or the site is the one dealers honour.** The site is
  taken; the £2,500 gap on three layouts is unexplained.
* **`Fusion 1`**, FMLV's range name on the 2022 and 2024 rows. Nothing on the current site
  uses it, and those rows are out of the baseline anyway.
