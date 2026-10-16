# Globe-Traveller — survey, 16 October 2026

An enquiry from **Globe-Traveller RV Sp. z o.o.**, Kraków, Poland —
`https://globe-traveller.eu/`. High-top campervans, twelve models across four series.

**Not in `resources/manufacturers-full-list.csv` and not on FMLV**, so there is no
manufacturer id yet and no registry row can be written. No adapter; this is the stage-1
checkpoint.

## The site is as good a source as any surveyed, with three holes in it

The structure is excellent. Every model has its own server-rendered page at
`/models/<series>/<model>/`, with a specification table laid out identically across all
twelve. No JavaScript, no PDF, no configurator — and the root of the site is already
English, with `/pl/`, `/de/` and `/fr/` as the translations.

Twelve models, which matches the requester's count exactly:

| series | models |
|---|---|
| **Explorer** | X, XS, Z, Z EVO |
| **Falcon** | XS, YS, Z |
| **Pathfinder** | X, Z |
| **Voyager** | X, XS, Z |

`/models/` carries all twelve as cards with a filter panel, so the roster is rediscoverable
per run rather than hardcoded.

## What each page publishes, verbatim

From `/models/explorer-series/explorer-x/`:

```
Specifications
  Model Series   Explorer Series
  Model          Explorer X
  No. of seats   2(3)
  Bed type       French
  No. of berths  2
Technical Details
  Base model                    Ducato / Boxer
  Engine power                  180 / 140 HP
  Automatic gearbox             Standard
  Permissible Max. Mass (PMM)   3500 kg
  Extended PMM (*Fiat only)     3820 or 4200 kg
Dimensions
  Lenght         636 cm          (their spelling)
  Width          206 cm
  Height         280 cm
  Internal Height 195 cm
Living area
  Main bed size  200 cm x 123 cm
  Additional bed N/A
  Fridge         90 l
  Bathroom       Integrated with toilet
  Shower tray    65 cm x 60 cm
  Toilet         Chemical or dry
  Double floor   16 cm
```

So FMLV's **range** and **model** are published as separate fields, the **MTPLM** is
published, and so are **length, width and height**.

### Three things it gets right

* **The MTPLM comes with its upgrades named as upgrades.** `PMM 3500 kg` with
  `Extended PMM 3820 or 4200`, so the base-vehicle rule applies cleanly: record 3500 and
  leave the heavier plates as the options they are. The VW-based Falcon offers
  `3820 or 4000` instead, so the figures are per base vehicle rather than global.
* **The body type is derivable.** Heights run 280–300 cm, so every one is over the 2300mm
  the settled rule puts a `campervan_high_top` above. The site calls it a *"Super-High
  roof"* itself.
* **The habitation findings are unusually well served** — fridge capacity in litres, the
  bathroom as integrated or separate, shower tray size, toilet type, double-floor depth and
  both bed sizes.

## The three holes, and all three are required fields

**No price, anywhere.** Not on a model page, not in the sitemap's 88 URLs. The footer
carries a **"Catalogues and prices"** link that has **no `href` at all** — a placeholder.
That is worth knowing when asking: the slot exists, so a catalogue and a price list are
things they intend to publish rather than things they have refused.

**No mass in running order.** The `PMM` is the MTPLM; nothing states what the vehicle
weighs empty.

**No payload.** Which follows, since payload needs the MRO.

`schema.REQUIRED` wants all three. For a manufacturer FMLV already held, they could be
left to carry over — but **this brand has no products at all**, so there is nothing to
carry over and a first upload would create twelve rows with three required fields blank.

### Consequently there is no self-check

`MTPLM - MRO = payload` is the test every strong adapter here leans on, and with only one
of the three published it cannot be run. As with Rolling Homes and Kaktus, the check would
have to be structural. **A price list that carried the MRO as well would fix both problems
at once.**

## The open question: `Ducato / Boxer` is two base vehicles

Every Fiat-based model states its base as **`Ducato / Boxer`** — a Fiat Ducato *or* a
Peugeot Boxer. The settled rule is explicit that **a different base vehicle is a different
product**, which would make the twelve models up to **twenty-four products**.

Nothing on the site resolves it, and there is no baseline to consult. It needs deciding
before a build, because it doubles or halves the whole roster. The Falcon series is on a
**VW Crafter** and does not have the ambiguity.

## Three smaller questions

* **`No. of berths: 2+2`** on six models, against a plain `2` on the others. The `+2` is
  not vague: those pages also carry an **`Additional bed`** with a size — `187 cm x 134 cm`
  — where the two-berth models read `N/A`. So the second bed exists and is listed as
  specification rather than as an option. **Recommendation: record 4**, since the berths
  rule takes the lower figure only where the upper needs options, and nothing here says
  this one does. Worth confirming.
* **`No. of seats: 2(3)` and `4(3)`.** The bracketed figure is unexplained. On the
  Bürstner precedent a parenthetical or "permitted" seat count is a ceiling rather than a
  fitment, so the plain figure is the one to take — but what Globe-Traveller mean by it
  should be asked rather than assumed.
* **The Falcon XS states no berth count at all** — the field is present and empty. One
  missing value out of twelve, which an adapter should narrate rather than guess.

## Verdict

**The website is a good source and the adapter would be straightforward — but it cannot be
built yet**, because three of FMLV's required fields are unpublished and there are no
existing products for them to carry over from.

What is needed is small and specific:

1. a **UK price list**, or any price list;
2. the **mass in running order** per model;
3. the **payload** per model, or just the MRO, from which it follows;
4. a decision on **Ducato versus Boxer** — one product or two.

With those, everything else is already on the page and parses cleanly.

## On creating a placeholder in Nova

The requester offered to create the brand with a false product to review against.
**That is not needed, and Beauer showed why**: the mock placed there on 15 October was
`active: No`, so the baseline scope excluded it and every scraped product arrived as new
regardless. `fmlv empty-baseline <manufacturer>` covers the no-baseline case by design.

What *is* needed, per the three-things rule, is the **manufacturer id** — the NCC's to
allocate — and the **supplier/exhibitor record**, which no upload can create.
