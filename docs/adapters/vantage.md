# Vantage — site survey and adapter

Surveyed and built 17 September 2026. FMLV manufacturer id **88**, name and display name
**`Vantage`**, **NCC supplier name `Vantage Motorhomes`**. **Campervans only** — Vantage
convert panel vans at their own factory in Leeds. **Thirteen models across three ranges**,
of which FMLV held eleven.

## The range is the vehicle's length

**Identity is inverted from every other brand in the project.** `manufacturer_range` is
how long the van is; `model` is its name.

| `manufacturer_range` | `model` |
| --- | --- |
| `5.41m` | CUB, GEM, MED |
| `5.99m` | MAX, ORA, SOL, TEO, ORA F-Line, SOL F-Line |
| `6.36m` | EOS, NEO, RIO, VUE |

The requester, 17 September 2026: *"the range is 5.41 metres which seems confusing and
then the model is the cub or the gem or the med or the max or the aura or the soul or the
teo"*. FMLV's own export holds exactly that, so nothing is inferred — and "aura" and
"soul" are **ORA** and **SOL**.

Every model page states both in its heading (`CUB | 5.41m`), so the range is read from the
page and the index that led there is used only to check it.

## The site sells other people's vehicles, and its own used stock

Flagged by the requester before the survey began, and the easiest way to get this badly
wrong. Alongside the thirteen models:

* **`/pilote`, `/pilote-atlas`, `/pilote-pacific`, `/pilote-panel-vans`, `/galaxy`** —
  Pilote products. Pilote are separate FMLV manufacturers (104, 105, 261) with their own
  adapters, so reading these proposes one manufacturer's vehicles against another's ids.
* **`/motorhome-stock`, `/vantage-r`** — used and ex-demo stock. `/vantage-r` reads
  *"Stock Bonus Of £5000 Off This Stock Model, IMMEDIATE DELIVERY"* against individual
  2025 vehicles, each with its own price.

**The roster is taken from the three length index pages only**, and every candidate then
has to *parse as a Vantage model page* — a `NAME | x.xxm` heading and a `Base Vehicle
Specification` line — before it is collected. A stock listing has neither, so **the page
itself is the filter** rather than a list of paths to avoid. The known-nav set exists only
to keep the narration quiet.

## Model pages are at the site root, linked absolutely

`/cub`, `/ora-f-line`, `/vue` — **not** nested under `/panel-vans/`, and the hrefs are
written in full. A pattern looking for relative or nested paths finds nothing at all,
which is how this nearly read as a site with no models on it.

## The base vehicle splits the range, and not where the menu says

Eleven are **Fiat Ducato 2.2 Multijet3 140bhp**; the two **F-Lines** are **Ford Transit
V363 350 L3 H2**. The requester's framing — "campervans are Fords, panel vans are Fiats" —
is true of the vehicles and **not** of the site's menu: both F-Lines are linked from the
**5.99m panel van** index, and `/campervans` links no model pages at all (it is prose
about Fuze and Luna, illustrated with 2023 photographs).

So the make is read from each page's own line. Deriving it from the section would put
Fiat on two Fords.

## The self-check, and its limit

**Thinner than most, and said plainly.** Vantage publish two masses and the third is
derived, so `payload == GVW − MRO` is true by construction. Gross Vehicle Weight is
**3500 kg on all thirteen**, so it cannot discriminate either.

What is real is a **cross-check on identity**: the index states the range, the page states
its own, and a disagreement drops the layout.

**The derivation is corroborated once.** `MRO = GVW − payload` reproduces FMLV's stored
figure *exactly* on all eleven existing models — 3500−600=2900, 3500−500=3000,
3500−450=3050, 3500−400=3100, 3500−380=3120.

## The bug the roster count caught

The first live run collected **11 of 13** and reported the two F-Lines as "not a Vantage
model page". The heading pattern required an all-upper-case name: eleven pages head
themselves `CUB` or `VUE`, and the other two head themselves **`ORA F Line`** and **`SOL F
Line`**. Nothing else would have noticed — the run looked entirely successful — and
`EXPECTED_LAYOUTS` was the only thing that disagreed. It is the clearest case in the
project for keeping a published count even when the manufacturer does not supply one.

## Length, width and height are not emitted

**The site rounds and FMLV does not.** The only length published is the range name,
`5.41m`, against FMLV's **5413**; the others are 5998 and 6363. Emitting 5410 would
degrade eleven good figures to fill a blank.

**No width or height appears anywhere.** Both are left alone so FMLV's figures stand and
arrive as a flagged no-op — the requester's instruction: *"we'll have to have the option
of using the current height and width if it's an existing vehicle"*.

The consequence: the **two new F-Lines have nothing stored to preserve**, so their length,
width and height arrive blank and need filling by hand.

## The campervans live in modal dialogues, and are a different vehicle

`/campervans` links **no model pages at all** — `/fuze` and `/luna` both 404. The section
is built from modal dialogues: a card carries `data-modal-target="fuze_modal"` and the
dialogue repeats that key. Read from there, both are collected and **neither is reported
as discontinued**, which is what happened before this was found.

**Their full specification is unreachable.** The dialogue's "View Full Specifications"
button opens a *Flipsnack* flipbook (`player.flipsnack.com/?hash=...`) whose page is a
7.5 KB JavaScript shell carrying no text and no PDF; the book's pages are rendered images.
So the masses, payload and price are not emitted and FMLV's own figures stand.

**They are a different vehicle and a different roof.** Ford Transit Customs at
4.97 m × 2.08 m × **2.15 m**, against the panel vans' 2.6 m — a standard roof with a
pop-top, so `campervan_elevating_roof`, which is what FMLV holds. Not
`campervan_high_top`, and not `campervan_high_top_elevating_roof` either.

**Both of those were asserted at some point and both were wrong**, and the real baseline
caught each before it reached a reviewer. The lesson is the one the shared rules already
draw for caravans — *fetch the baseline before writing a rule about what a field means* —
and it applies just as much to a body type asserted from a sentence as to one derived from
a figure. "All definitely high top camper vans" was true of the thirteen panel vans in
front of us and not of the two vehicles neither of us was looking at.

The roof is therefore **emitted only where the page states it**: "pop-top" appears exactly
once in the whole document, in Luna's description. Fuze carries identity alone, so its
stored value is preserved rather than overwritten by an assumption.

## Body type is asserted

All thirteen are **`campervan_high_top`** — the requester, *"all definitely high top
camper vans"*. Asserted rather than derived because the roof rule needs a published height
and there is none. FMLV already holds this on all eleven, so it agrees with the baseline
and gives the two new F-Lines a body type instead of a blank.

An elevating roof is checked for **in each model's equipment list** and narrated if found.
Deliberately not in the page's prose: the CUB is sold as *"the ideal upgrade from a
pop-top"*, which is a sentence about a different kind of van and produced a false warning
on every run.

## The price, and the options beside it

Every page carries `FROM £74,995 (OTR)` — sterling, on-the-road, the manufacturer's own
headline, which is what the shared rules ask for.

**The trap is further down the same page**: a "Vehicle Quotation Calculator" listing
`8 Speed Automatic Transmission £2520`, `Primo Pack £4200`, `CAT 1 Alarm £525`. The
pattern therefore requires both the `FROM` and the `(OTR)`, and a page with option prices
but no OTR line yields **no price** rather than a £525 campervan.

## The first run

Against the export of 17 September 2026 — 29 rows, of which 16 are model year 2022–2024
and drop out on age, leaving 13 in scope:

* **7 price changes** — the 5.41m trio £73,995 → £74,995, the 5.99m trio £76,950 →
  £77,995, and TEO £82,000 → £81,950.
* **6 confirmed unchanged** — the whole 6.36m range, plus both campervans.
* **2 new** — `5.99m ORA F-Line` and `5.99m SOL F-Line`.
* **nothing disappeared.**

Every berth count, travel-seat count, mass and base vehicle was verified unchanged, which
is the parse corroborated against FMLV across the board.

## Still unverified

* **Fuze and Luna's masses, payload and price.** Published only inside the Flipsnack
  flipbook, whose pages are rendered images behind a JavaScript shell. The requester's
  screenshots give them — Fuze 3190 kg GVW, 588 kg payload, £59,950 OTR; Luna 3190 kg,
  542 kg, **£64,950** — and FMLV agrees on every one except the **Luna price, which it
  holds as £59,950**. That looks like Fuze's figure copied across, and it cannot be
  corrected automatically from anything this adapter can read.
* **Fuze's roof**, likewise. Both are pop-tops, but only Luna's dialogue says so in HTML.
* **`SKY` and `4.97m LUX`**, in FMLV at 2022–2023 only and absent from the site. Out of
  scope for the diff on age, so they are neither matched nor reported.
* **`/2026-vantage`**, linked from the nav and not read — it may be where a new model year
  appears first.
* **The optional packs.** Primo, Techno Plus and Style & Visibility change equipment and
  weight, and none is read; the payload figures carry Vantage's own caveat that they are
  *"weights with standard equipment installed"*.
