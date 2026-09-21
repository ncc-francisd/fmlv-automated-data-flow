# Mink Campers (id 270)

Surveyed 2026-09-21. **Caravans**, despite the brand name — Minks are towed teardrops with
no engine, so they belong in the caravan product area and are exported as touring
caravans. The requester flagged this as the confusing part, and FMLV already agrees: all
four rows are in the touring-caravan export and the motorhome export is empty.

- Requester's source: <https://www.rivermotorhomes.co.uk/mink-campers/> — River Motorhomes,
  the UK distributor
- NCC supplier name: `Mink Campers`
- `fmlv_manufacturer`: `Mink Campers`

## Which manufacturer row

Two could be this brand, and the export settles it rather than the name:

| id | `fmlv_manufacturer` | in the export? |
|---|---|---|
| 168 | `Mink Camppers EHF` — note the double `p`, *ehf.* being the Icelandic "Ltd" | **no** |
| **270** | **`Mink Campers`** | **yes, all four rows** |

Same shape as the Weinsberg pair (112 against 252). The requester named 270 and the export
proves it right.

## The baseline

Four live rows, all 2026, all `type_micro`, range `Campers`, models a bare letter:

| model | MTPLM | MRO | payload | length | width | height | price |
|---|---|---|---|---|---|---|---|
| S | 750 | 520 | 230 | 4116 | 2080 | 1829 | £19,995 |
| X | 750 | 530 | 230 | 4116 | 2080 | 1880 | £21,995 |
| E | 750 | 510 | 230 | 4116 | 2080 | 1850 | £21,995 |
| Z | 750 | 520 | 230 | 4116 | 2080 | 1829 | £16,995 |

**The payload is a flat 230 on all four and only reconciles on two.** 750 − 530 is 220 for
the X and 750 − 510 is 240 for the E. It reads as one figure typed four times.

## The requester's source does not carry the figures

This needs saying plainly, because the brief said the weights and dimensions were on each
model page. They are not, and it was checked properly rather than assumed:

- `/mink-campers/` links exactly **three** models — `mink-s`, `mink-x`, `mink-e`.
- On `mink-s`, **none of FMLV's figures appear at all** — not 4116, 2811, 2080, 1829, 2250,
  750 or the price — in either the static HTML or the browser-rendered DOM.
- The `kg` that looks promising in a grep is 120 occurrences of "bac**kg**round".
- The only dimensions in the page text are a mattress (1400 × 2000) and 20 mm insulation.
- **No price is published anywhere** on the distributor's site.

What the model pages *do* carry is a link to the document that has everything.

## The source: the 2026 catalogue, linked from the distributor's own pages

`https://cdn.web.dragon2000.net/assets/748/brochures/MinkCampers_Catalogue2026.pdf`

Sixteen pages, of which **page 14** is the specification spread, and it holds every figure
FMLV has. It states them **twice**, and the two disagree:

```
2080 mm   4116 mm   1511 mm   1829 mm   2811 mm     <- the dimensioned drawing
Gross weight 750 kg    Net weight 520 kg            <- the table, MINK-S column
Overall length 4120 mm   Cabin length 2810 mm
Overall height 1850 mm   Overall width 2100 mm
```

The **drawing is precise and the table is rounded** — 4116 against 4120, 2811 against 2810,
2080 against 2100, 1511 against 1510. FMLV holds the drawing's figures, which is the better
reading, and the factory site independently publishes the same four.

`Gross weight` is the MTPLM and `Net weight` the mass in running order. Those match FMLV
exactly on all three: 520, 530, 510.

## The factory site agrees, except where it has been copy-pasted

<https://www.minkcampers.com/mink-s>, `/mink-x` and `/mink-e` each publish a clean labelled
block, and they confirm the precise dimensions (4116 / 2811 / 2080 / 1511).

**But the MINK-S page appears to be a copy of the MINK-E page.** It states a net weight of
510 and a height of 1830 — identical to the E, and different from the catalogue's 520 for
the S — and both pages open with the same paragraph, *"The aerodynamic, light-weight design
opens up a variety of possibilities…"*, where the X has its own. FMLV and the catalogue
both say 520 for the S.

So the factory site is corroboration, not the source, and specifically not for the S.

## Height disagrees three ways

The one field with no clean answer:

| model | catalogue drawing | catalogue table | factory site | FMLV |
|---|---|---|---|---|
| S | **1829** | 1850 | 1830 | **1829** |
| X | — | **1880** | 1850 | **1880** |
| E | — | **1850** | 1830 | **1850** |

FMLV's figures are already the best available reading: the drawing for the S, whose
precise figures it covers, and the table for the two the drawing does not. Taking any
single source wholesale would be worse — the table would push the S to 1850, and the
factory site would push the X to 1850 and the E to 1830, each on the strength of a page
that looks duplicated.

## The Z is nowhere

`Z` is FMLV's cheapest row at £16,995, and it appears in **none** of the sources:

- `rivermotorhomes.co.uk/mink-campers/mink-z/` → **404**
- `minkcampers.com/mink-z` → **404**
- the 2026 catalogue names MINK-S, MINK-X and MINK-E and never Z
- the string `mink-z` appears zero times across every page fetched

A question for the requester rather than something to conclude from absence.

## Nothing calls them micro

`micro` appears **zero times** in every source checked — the distributor's index and all
three model pages, the factory home page and model page, and the catalogue. They are called
a "lightweight caravan" throughout, and "teardrop" twice on the factory site.

So the naming half of the settled micro test fails, exactly as it did for T@B, while the
weight half passes easily at 750 kg. FMLV already holds `type_micro` on all four, so
emitting no body type leaves it standing.

## Used stock

Structurally separate and easy to avoid: it lives under `/vehicles-for-sale/`, and the
four `/mink-campers/...` paths are all new-model pages.

## The self-check

Weak, and worth saying so. Mink publish no payload, so there is no arithmetic to check the
parse against. What is available is **cross-document agreement**: the catalogue's drawing
and the factory site independently publish the same four dimensions, and the catalogue's
masses match FMLV on all three models. A layout whose two sources disagree can be dropped;
a single source cannot check itself.

## First run — #114, 2026-09-21

3 scraped against 4 baseline: **2 changed, 1 unchanged, 0 new, 1 disappeared** — the
disappearance being the `Z`. 28 fields verified unchanged.

**The only real changes are the two payload corrections**, X 230 → 220 and E 230 → 240.
Everything else is either a year bump or a no-op "not found this run" row preserving
FMLV's own figure: height, berths, awning length, price and body type, each deliberately
not proposed for the reasons above. The S has no substantive change at all.

That is the right outcome for this brand — FMLV's data was already close, and the adapter
mostly confirms it.

### The trap the live run exposed

The drawing's two side-view callouts extract **glued together** as `2080 mm4116 mm`. A
trailing `mm\b` fails on the first, because an `m` followed by a `4` is no boundary, and
a leading `\b` fails on the second. Both figures were lost on the first attempt — which is
the entire value of reading the drawing rather than the rounded table, so the run was
proposing nothing for length or width. Matching on "not preceded by a digit" fixes it and
still stops a five-figure number being read as its last four.

The same glued-text shape as Westfalia's berth icons, and worth expecting from any
dimensioned drawing.

## A second UK source, and the price (added 2026-09-21)

The requester then supplied <https://mink-campers.co.uk/> — **Mink Campers UK**, the
importer's own brand site, and the only place in any source that publishes a price. Each
model page heads itself `MINK-S FROM £19,995.00`, on the road.

| model | Mink Campers UK | FMLV |
|---|---|---|
| S | £19,995 | £19,995 |
| **X** | **£20,995** | £21,995 |
| E | £21,995 | £21,995 |

Under the settled rule the UK importer decides what a thing costs, so this is recorded and
it corrects the X by £1,000.

**Two things on that site are deliberately not used.**

Its `/specification/` page looks like a spec sheet and is not one: a single generic block
headed "MINK CAMPER" with one set of masses (750 / 510 / 240, which are the E's) and a
`From £15,995.00 OTR` matching none of the three real prices. Only the per-model pages are
read. Its dimensions — 4116 / 2811 / 2080 / 1511 / 1829 — do independently confirm the
catalogue drawing's, which is worth having.

**The model name and the price sit in two separate headings**,
`<h1>MINK-S</h1><h1>FROM £19,995.00</h1>`, so they only match as one phrase once the
markup between them is stripped. Without that the price was found on no page at all and
the run silently proposed none — the second time on this brand that a parse looked fine
and read nothing.

### The Z, better evidenced

The UK brand site **lists `MINK-Z` in its navigation**, which no other source does — but
the link points at `#`, and `/mink-z/` and every variant 404s there as they do everywhere
else. So the Z is a menu entry with no content anywhere: either announced and not yet
published, or withdrawn and not yet removed. Still a question for the requester, but now
a sharper one.
