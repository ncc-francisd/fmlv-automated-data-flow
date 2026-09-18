# VANTourer — site survey and adapter

Surveyed and built 18 September 2026. FMLV manufacturer id **250**, name and display name
**`VANTourer`**, **NCC supplier name `VANTourer`**. **Campervans only.** **Eight products:
four floorplans, each sold standard and as the special edition GO!** — and FMLV already
holds all eight.

German brand, English-language website. The source is neither the site nor the catalogue
but a **UK market edition of the price list**, which is the document the shared rules tell
you to look for *before* planning any currency conversion.

## One document holds everything

`eurocaravaning-vantourer-pricelist-01-2027-uk-web.pdf`, headed *"TECHNICAL DATA / PRICE
LIST … UK | EDITION 1/2027"*:

```
TECHNICAL DATA          540 D  600 D  600 L  630 L
Length in cm             541    599    599    636
Width in cm (exterior/interior)  205/187 …
Height in cm (exterior/interior) 258/190 …
Seats with 3-point seatbelts  4  4  4  4
Maximum authorised laden mass (kg) 1/2  3,500 …
Mass in running order (kg) 1/3
  Standard model | Special edition GO!
  2,660 (2,527 – 2,793) | 2,738 (2,601 – 2,875) …
Maximum mass of the additional equipment (kg) 1  520.9 | 442.9  360.1 | 282.1 …
Minimum payload (kg) 1  94.1  99.9  99.9  103.6
```

**The website publishes no mass at all** — no mass in running order and no payload — which
is what made this look like a brand whose weights would have to be carried over from FMLV.
They are all in the price list.

The dimensions confirm FMLV exactly: 541/599/599/636 cm and 205/258 against FMLV's
5410/5990/5990/6360, 2050, 2580.

## No currency conversion, because VANTourer do it themselves

The prices are **sterling**, and the document says what they are:

> *"All prices in pounds, valid for the UK market are converted at a monthly assessed
> guidance rate and all prices include UK VAT at the current rate of 20%"*

with *"preliminary freight, certificate of title, gas test in Germany and UK RFL … already
included in the base retail price"*. So this is a real UK on-the-road figure, and none of
the exchange-rate trouble that makes Morelo's price data the worst in the project applies.
**`morelo.EUR_TO_GBP_RATE` has no counterpart here and must not gain one.**

**Corroborated per model by the website**, which prints both currencies: the 600 D's page
reads `from €66,427 (£68,790)` against the price list's `68,790`. Two independently
written sources agreeing on all eight.

## A real four-way self-check

Four published masses constrain each other, and the identity holds **exactly, to the tenth
of a kilogram, on all eight**:

```
MTPLM − MRO == (3 × 75 kg) + maximum mass of the additional equipment + minimum payload

540 D      3500−2660 = 840.0    225+520.9+ 94.1 = 840.0
600 D      3500−2815 = 685.0    225+360.1+ 99.9 = 685.0
600 L      3500−2810 = 690.0    225+365.1+ 99.9 = 690.0
630 L GO!  3500−3073 = 427.0    225+ 98.4+103.6 = 427.0
```

The 225 kg is three passengers at the statutory 75 kg — **the driver's 75 kg is already
inside the mass in running order**, so counting four would break it. This is the strongest
check in the project after Ace's, and it is what catches the failure this source is most
exposed to.

**`Minimum payload` is not the payload.** It is the legal floor a converter must leave
free — 94.1 kg on a van that carries 840. An adapter matching on the word "payload"
records a tenth of the real figure, and the arithmetic above is what would notice.

## Three parsing traps, all of which bit during the build

**1. The document explains itself in the same words the rows use.** Page 2's footnote
reads *"The stated weight is the maximum authorised laden mass"* and page 10 is headed
*"2. Mass in running order"*. An unscoped search finds the sentence, comes back with no
figures and drops every vehicle — which is exactly what the first version did, silently
and for all eight. Every row pattern is now scoped to `technical_block`.

**2. The unit is optional and the footnote is not a figure.** `Length in cm 541 599 599
636` has no bracket at all, and a pattern that assumed one swallowed the whole row.
Meanwhile `Maximum authorised laden mass (kg) 1/2 3,500` and `Minimum payload (kg) 1 94.1`
put footnote markers between the unit and the values. The marker is allowed only after a
bracket and only up to three characters — enough for `1/2`, not enough to eat a width's
`205/187`.

**3. The berth block is not a row.** Four labels print as a stack and their figures follow
**column by column**, so the berth count is the first of each group of four, and the en
dash on the 630 L (which cannot take a pop-up roof) counts as a position. The run is read
a line at a time and stops at the chassis description below it; a fixed character window
ran straight past and collected sixty tokens.

## The column-alignment risk

Four model columns, and **the masses interleave the two trims** — `520.9 | 442.9 360.1 |
282.1 …` is (540 D standard, 540 D GO!, 600 D standard, 600 D GO!, …). Read one value out
of step and every vehicle carries its neighbour's weights, plausibly and consistently.
Two defences: every row's value count is asserted against the header (four, or eight for an
interleaved row) and a wrong count yields nothing rather than zipping short; and the
self-check runs per product, where a one-column shift is obvious because the
additional-equipment figures differ by 150 kg or more between neighbours.

## Identity: the range is the number, the model is the letters

FMLV holds range `540`/`600`/`630`, model `D`/`L`, and the special edition as **`D GO!
Edition`** — which is neither the technical table's `540 D` nor the price table's `GO! 540
D`. The requester flagged the naming before the survey: *"the ranges are numbers so five
forty six hundred etc … for example this one L GO! Edition"*.

## The 600 Ds is on the website and is not ours yet

The model index links a fifth floorplan, the **600 Ds**, with its own 2027 folder in
German, English, Italian, Swedish, Austrian and Swiss editions — and **no UK edition of
anything**, nor a line in the UK price list. Under "the UK importer defines the range",
that reads as not sold here yet, so it is **excluded and narrated every run**: the day a UK
price appears it should be collected.

## Body type is not emitted, and FMLV's values are right

Every one is 2,580 mm tall, so the roof class is not in doubt — they are all high tops.
**The pop-up roof is fitted per variant**, and FMLV records exactly that:

| | 540 D | 600 D | 600 L | 630 L |
| --- | --- | --- | --- | --- |
| standard | elevating | high top | high top | high top |
| GO! | elevating | high top | **elevating** | high top |

The survey read that as an inconsistency — the 600 L held both ways across its two trims,
and the 630 L marked high top though the price list shows it cannot take the roof — and
proposed that the website calling the roof *"optional"* made all eight plain high tops.

**The requester checked the photographs on 18 September 2026 and it is neither.** The
600 L and the 600 L GO! are both high tops, and only the GO! carries the elevating roof.
The 540 D has it in both trims; the 600 D and 630 L in neither. The roof follows the
individual variant, not the floorplan and not the trim — which is why no rule over the
price list's columns could have produced it.

Nothing in the price list says which variants carry the roof, so **nothing here can derive
it and the field is left alone**. The decision not to assert was right; the reasoning
behind it was not, and the correction is worth keeping: *an apparent inconsistency in the
baseline is not evidence the baseline is wrong.* Asserting all eight as high tops would
have quietly removed a real elevating roof from two vehicles.

## The first run

Eight matched, nothing new, nothing disappeared, **no unvalidated fields**:

* **All eight prices change** — 540 D £65,295 → £65,090, 600 D £67,895 → £68,790, 630 L
  GO! £72,995 → £74,527.
* **Six masses in running order correct by a few kilograms**, because FMLV holds rounded
  figures: 600 D 2810 → **2815**, 630 L 2990 → **2995**, 540 D GO! 2740 → **2738**, 600 L
  GO! 2890 → **2885**, 630 L GO! 3070 → **3073**. Payload moves with each.
* Dimensions, berths, travel seats and base vehicle all verify unchanged.

## Still unverified

* **Habitation.** The model pages carry feature lists and the catalogue has more; none is
  read yet, and FMLV holds `heating` and `refrigeration` blank on all eight.
* **The 2027 catalogue** (`katalog-2027-en-web.pdf`), which is not read — the price list
  carries everything FMLV records.
* **Whether the GO! is a trim or a range.** FMLV files it as part of the model, which this
  follows; VANTourer's own website gives it a page of its own as a "special model".
* **The pop-up roof's price**, which would settle the body-type question: if it appears as
  a priced option line, the base vehicle is a high top on all eight.
