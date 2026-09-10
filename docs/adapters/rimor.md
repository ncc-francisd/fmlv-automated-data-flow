# Rimor — site survey and adapter notes

Rebuilt 5 September 2026 against the UK importer's site plus a redesigned factory site.
The original survey (13 August 2026) read only `rimor.it`; see "What changed in
September" at the end for why that no longer works and what it cost.

Rimor is the first adapter to read **two different sites and let each decide different
fields**. That is not an optimisation — neither site can answer the whole question.

| | decides | because |
|---|---|---|
| **MNC** (`motorhomesandcaravansltd.co.uk`) | which products exist, and the price | Rimor's exclusive UK importer, and Rimor publishes no price anywhere on earth |
| **`rimor.it`** | every specification number | MNC's specs are a sales description, and demonstrably wrong in places |

**34 products**: Horus 7 (including the Rimor Van 238), Kilig 15, Sarus 3, Sailer 5,
Super Brig 4. Both sites are plain server-rendered HTML — no JavaScript, no login.

Confirmed with the requester on 5 September 2026: **MNC defines the UK range.** A layout
MNC does not list is not a UK product and is not emitted, however complete its factory
page. Today that excludes five factory layouts — `horus/45`, `kilig/73-plus`,
`sarus/50`, `sarus/69-plus`, `sarus/95-plus` — each of which the run names explicitly
rather than dropping silently.

## Why MNC cannot supply the specifications

This is the load-bearing part of the design, so it is evidenced rather than asserted.
All three findings come from comparing the 28 layouts both sites describe.

**MNC's berth figure is not a berth count.** On the coachbuilts it repeats its own
travel-seat count in the berth position:

| | MNC says | rimor.it says |
|---|---|---|
| Kilig 5 | 6 berth with 6 travel seats | 6 seats (`6 / 5`), **4** berths |
| Kilig 79 | 7 berth with 7 travel seats | 7 seats (`7 / 6`), **4** berths |
| Kilig 67 | 4 berth with 4 travel seats | 4 seats, **2** berths |

**26 of 34** MNC listings have `berths == seats`, and where the factory can be checked
MNC is too high in **11 of 21** cases — always too high, never too low. Berths therefore
always come from the factory. (Horus is the exception that proves it is a coachbuilt
template bug: MNC's Horus pages do print two different figures, and they agree.)

**MNC truncates dimensions to whole centimetres.** Kilig 55 Plus is 7338 mm on the
factory page and `7.33m` on MNC — truncated, not rounded, so MNC is systematically 0–9 mm
low. That cap is what makes the cross-site check below usable.

**At least two MNC layouts carry another layout's figures.**

* Kilig 79 — MNC prints `6.75m`, which is the *78*'s length; the factory says 6970 mm.
* Kilig 99 — MNC prints `7.44m × 2.90m` against the factory's 7308 × 2845 mm.

Both are caught by the self-check on every run and narrated, with the factory figure
kept.

## Why the factory cannot supply the price

**Rimor publishes no price anywhere** — not the HTML, not the leaflets, not the 60-page
catalogue (zero hits for any currency symbol), and the FAQ directs price questions to
dealers. MNC's is the only price that exists.

Prices are **banded by range** rather than set per layout: Horus and Kilig £56,995–61,995,
Sarus £64,995, Sailer and Super Brig £69,995. That is worth knowing before reading a
uniform column as a parse failure.

## Site shapes

```
MNC     /product-category/new-motorhomes-for-sale/new-rimor-motorhomes/<range>
          -> /product/rimor-<range>-<layout>-<year>[-variant]    price, body type
rimor.it /int/en/gamma/<range>
          -> /int/en/gamma/<range>/<body-style>
               -> /int/en/gamma/<range>/modello/<layout>         every specification
```

Two entry-point quirks. **MNC spells Sailer's category `sailer`, not `rimor-sailer`** —
the other four carry the prefix, and guessing costs a 404. And the factory has no
`/int/en/gamma` index (it 404s) and no sitemap, so the five ranges are listed in the
adapter rather than discovered.

`DEFAULT_RANGES` therefore carries **three** elements per entry — MNC slug, factory slug,
label — where every other adapter carries two. `cli.resolve_ranges` was changed to read
only the entry's *last* element as the label and pass the rest back untouched, which
leaves the other adapters exactly as they were.

## Stock units are not products

MNC sells actual vehicles alongside its layout listings, which is the thing to get right
here. **48 URLs reduce to 34 products.**

* **Demo vans** carry a struck-through price and `Demo` in the title.
* **`-copy` slugs** are WordPress duplicates whose slug is the only thing wrong with them.
* **`-automatic` variants** are a transmission option on the same layout.
* **10 URLs are 301s** onto a sibling that is already listed.

`select_listings` groups every URL by `(range, layout)` and prefers a plain listing, then
a duplicate, then a demo unit; within that, the latest model year and then the shortest
slug, which favours the base vehicle over an optioned variant.

**A demo or copy listing is still used when it is all a layout has.** Four layouts are in
that position — Sailer 55 Plus, Sailer 56 Plus, Kilig 50 and Kilig 695 — and dropping
them would lose layouts MNC genuinely sells.

### Which price a discounted page gives

Two discounts that look identical in the markup mean opposite things, and the difference
is what is being discounted:

| | MNC shows | take | why |
|---|---|---|---|
| Sailer 55 Plus (demo unit) | £69,995 → £64,995 | **£69,995** | the discount is on one van; £69,995 is exactly what the other three Sailers cost |
| Horus 40 (range promotion) | £61,990 → £59,995 | **£59,995** | the whole Horus range is promoted, and £59,995 is the figure MNC's page leads with |

**`is_demo` must be read from the fetched page's title, never from the requested slug.**
Several plain layout URLs 301 *onto* a demo listing — `rimor-sailer-55-plus-2026` lands on
`rimor-sailer-55-plus-2026-automatic-demo-van`, and `rimor-horus-40-2026` lands on
`-automatic` — so the slug asked for and the page returned routinely disagree. Only the
page that comes back can say what was actually read.

## The join, and Rimor's renaming

Rimor moved its **whole Kilig low-profile line** from `<n>` to `<n> Plus` for the new
season while MNC still lists the old names. `_factory_slug` tries `<layout>`, then
`<layout>-plus`, then `<layout>` with `-plus` removed, and only ever returns a slug the
factory actually publishes — nothing is invented. Six Kilig layouts join that way today
(66, 67, 69, 77, 78, 79), each reported in the run output.

This is exactly the "name drift is not a new model" case: treating those as new products
would have proposed six creations and six disappearances instead of six matches.

**The dimension check is what proves the join** rather than assuming it. `rimor.it` and
MNC publish each layout's dimensions independently, so comparing them is a genuine second
source and not the same number read twice. MNC's truncation caps an honest disagreement at
9 mm, so the tolerance is 10 mm; anything larger is a real conflict, narrated loudly, with
the factory figure kept. A conflict does **not** drop the product — MNC being wrong about
a dimension says nothing about whether the layout is on sale.

## Body type: `/vans` does not settle it

The body-style URL segment settles `low-profile` and `overcab` outright. **`vans` does
not** — it says the vehicle is a panel-van conversion, and FMLV splits those four ways on
what the roof does. Height decides it, on the same **2300 mm** threshold the NCC side set
on 16 August 2026 and every other campervan-producing adapter applies:

| Height | Body type |
|---|---|
| > 2300 mm | campervan high top |
| ≤ 2300 mm | campervan |

Every Rimor van is 2659 mm (the Van 238 is 2800 mm), so **all of them are high tops**, and
none is anywhere near the threshold — the closest clears it by 359 mm.

This was wrong until 5 September 2026: the adapter mapped `vans` straight to plain
`campervan`, and Rimor was the **only** adapter emitting a campervan without applying the
rule. Two notes for anyone tempted to re-derive the threshold from FMLV's own data, as I
briefly was:

* **Height does not separate the two classes in the baseline.** Across 237 campervan rows,
  `high_top` spans 1900–3120 mm and plain `campervan` spans 2580–3050 mm — the plain class
  has the *higher* median. That is not evidence the rule is wrong; it is a picture of the
  errors the rule exists to correct, and reading it as ground truth argues for keeping
  them.
* **A missing height yields no body type at all**, rather than a guess. The four campervan
  types are mutually exclusive columns.

The two elevating-roof types never arise: no Rimor van publishes a pop-top, as standard or
as an option. If one appears, the elevating question is independent of the height one, and
`body_type_for` is where both belong — `auto_trail._campervan_body_type` has the full
four-way table.

## MNC writes its dimensions two ways

Most listings read `Height: 2.65m` — whole centimetres, truncated. **A few read
`Overall height: 2,659mm`**, which is exact, comma-separated, and agrees with the factory
to the millimetre. Today that is Horus 12 and Horus 54; the other 36 use metres.

Missing the second form is not harmless. It left Horus 12 — a layout with no factory page
— looking as though nobody published its dimensions, when MNC publishes them exactly.
`mnc_dimensions` tries the exact form first and reports which it found, and all three axes
must come from the same form so that `dimensions_are_exact` cannot be true of one axis and
false of another.

### Dimensions fall back to MNC

Where the factory has no page for a layout, its dimensions come from MNC rather than being
left blank. The requester's ruling, 5 September 2026: *"if you can't get the specification
on the manufacturer's site, plan B would be to use the MNC site for the dimensions — in
that case we wouldn't have fields where you can't validate them."*

The fallback only ever fills a gap. Where the factory has a figure it always wins, so this
does not reintroduce MNC's truncation or its two wrong layouts anywhere the factory can
speak. Where a fallback figure *is* truncated, the run and the provenance snippet say so,
because that is the one thing a reviewer cannot see from the value itself.

## Habitation features, and where each site wins

Added 6 September 2026 as the pilot for `adapters/habitation.py` — see the habitation
section of `README.md` for the policy. The split here is the opposite of the numbers, and
worth stating plainly:

| Field | Source | Why |
|---|---|---|
| refrigeration, heating, bathroom, microwave | **MNC** | the factory publishes none of them |
| bed types | **MNC**, factory as fallback | see below |
| rear garage | **the factory** | MNC never mentions one |

**MNC's prose beats the factory's single word for bed types.** The factory publishes one
enum-like `Bedding solution` per layout; MNC writes out what is fitted. Where they differ
MNC is the accurate one:

| | factory says | MNC says | truth |
|---|---|---|---|
| Sarus 66 Plus | `Central bed` → island | "Rear double island bed" + "Electric drop-down double bed" | both |
| Horus 38 | `Double bed` → fixed | "Rear fold-away double bed" | a made-up bed, not a fixed one |
| Horus 66 | `Twin beds` → fixed separate | "Rear lounge which converts into single beds" | made up from the lounge |

The Sarus 66 Plus is the case that prompted the whole thing: FMLV holds island +
drop-down, and the adapter had been proposing island alone. FMLV was right.

**The rear garage comes from an unlabelled Italian icon.** `lc-icons-gavone` — *gavone*
is the garage or locker in Italian camper terminology — carries the opening size and no
label, in either language edition. Its presence is the signal: it is on all ten
coachbuilt layouts checked and on none of the six Horus vans, whose bed sits over the
back. That pattern is what makes the **negative** safe, and only for a van: a coachbuilt
with no garage value returns nothing rather than `False`, because that would be a layout
breaking the pattern and is a reviewer's call.

**Every Rimor is blown air.** All 34 say "Combi C4/C6 heating and hot water system",
"Truma Combi C6" or "Webasto AirTop" — warm-air heaters with a water tank, not wet
systems, which the requester confirmed. `wet_central_heating` is never proposed for Rimor.
Note that seven products say "Wet room" about the *bathroom*; matching a bare "wet" would
have called all seven wet central heating.

**Microwave is never proposed, but its absence is reported.** No Rimor page mentions one
— 24 list "Oven", which is not the same thing. The value stays `None` and provenance is
recorded anyway, so a reviewer gets a confirm-or-replace saying the specification does not
mention a microwave, rather than a proposed `No` quietly deleting a fact nobody disproved.
See `UNCONFIRMED_FEATURES`.

**The washroom is two fields, and the copy settles only one of them.** 23 of 34 say
"separate" of the shower or toilet and 7 say "Wet room", so `shower_toilet_separated` is
proposed True or False on 30 of them from the words. The *location* — `bathroom_layout`'s
rear or side — is never read from prose and always goes to the floorplan.

Getting that wrong was a real regression: Kilig 66 Plus was proposed as
`separate_shower_toilet` over a `side_shower_toilet` FMLV already held, which overwrote
the location with a construction detail. Both are true at once, and FMLV holds both on 84
of its rows. See the habitation section of `README.md`.

### The floorplan is the source for everything positional

Every one of the 16 model pages checked publishes a floorplan drawing —
`…/immagine_piantina/full/Kilig-9.jpg`, *piantina* being Italian for a floorplan — and
some are UK-specific editions (`Horus-40-UK.jpg`). It is the only thing on either site
that says **where in the vehicle** something sits, so it is what the reviewer is handed
for the fields no wording settles:

| Field | What to read off it |
|---|---|
| `sleeping_area` | which end the beds are at |
| `kitchen_location` | rear, side or corner |
| `lounge_location` | front, rear or twin |
| `bathroom_layout` | rear or side — **only** on the 11 the copy left open |
| `bed_types` | built in versus made up — only where the copy named no beds |

Each gets a row of its own with the same link, rather than one detached reference, so the
drawing is beside the field being decided. They carry
`Provenance(reviewer_reference=True)` and no value, which is what makes them survive onto
a new product — see the habitation section of `README.md` for why an ordinary empty field
does not.

**The factory's "Double bed" is not evidence of a fixed bed.** It names the sleeping
arrangement and says nothing about whether the bed is permanently there — and on the Horus
vans the drawing shows a lounge that becomes a bed at night, which is a *made-up* bed. So
`AMBIGUOUS_BEDDING` stops that word proposing anything and hands over the floorplan
instead. `Transverse bed`, `Bunk beds` and `Central bed` name shapes only a built-in bed
has, and stay usable.

**A bed can be named without a verb.** Kilig 77 Plus reads *"Consists of double bed rear
dinette, a front & rear drop-down bed and a Front & rear dinette"*, and the dinette double
went unrecorded: the copy names it as the seating it is made from rather than saying it
converts, so there was no verb for the make-up pattern to match. `habitation._SEATING_BED`
catches that idiom — "double bed rear dinette", "half dinette bed", "settee bed" — and the
requester supplied the answer on 8 September 2026: *"the correct answer is a drop down bed
and a makeup bed."* One of the 34 layouts changed.

It deliberately does **not** suppress the other beds on its line, which is where it
differs from the converting-lounge case: in *"lounge which converts into single beds"* the
singles **are** the converted lounge, so the shape is not credited; in Kilig 77's sentence
the drop-down is its own bed listed alongside, so it is.

This is latent rather than live: MNC's prose names the beds on all 34 layouts today, so
the factory fallback never fires. It was live before 5 September 2026, when bed types came
from the factory word alone — which is what produced the wrong `fixed_bed` proposals on
the Horus vans.

Horus 12 gets none, having no factory page and therefore no drawing. The Van 238 has no
page either, but its range leaflet carries the layout drawing, so its four positional
fields point there instead — see below.

**Marking these fields `in_scope` would have been the wrong way to do it**, even though
that is the other route to showing an empty field on a new product. FMLV holds
`sleeping_area`, `kitchen_location` and `lounge_location` on 99% of its 1,590 baseline
rows and no adapter sets any of them, so the flag would raise a confirm-or-replace on
roughly 4,700 rows across the twenty adapters that cannot answer them.

## Traps on the factory site

**Seats and berths are distinguishable only by Italian icon classes.** The two widgets
are otherwise identical, and the site's English does not reach either:

```html
<span class="lc-icons-posti-omologati ..."></span>   <!-- homologated SEATS -->
  <a href="#nota-numero_posti_omologati" ...>2</a>   <!-- footnote, skip it -->
  <span class="valore-caratteristica-modello">6 / 5</span>
<span class="lc-icons-posti-letto ..."></span>       <!-- BERTHS -->
  <span class="valore-caratteristica-modello">4</span>
```

Anchor on the name, never on position. These were `title="numero posti omologati"`
attributes until the 2026 redesign; the Italian words survived the move to class names,
and so does the rule.

**Two fields publish a list, and the first entry is the FMLV figure.**

* Seats read `6 / 5` — the `5` is a reduced-seat homologation Rimor offers to free up
  payload (85 kg per seat removed), not the standard figure.
* MTPLM reads `3500 / 3550 / 4100` — the first is the standard chassis; the rest are paid
  uprates. Sarus reads `3500 / 3650`, Horus a bare `3500`.

**The dimension rows pair outside with inside.** `outside width - inside width
2340 - 2200 mm` and `maximum outside height inside height 3040 - 2060 mm`. Only the first
of each pair is the FMLV figure.

**The overview block must be scoped to.** Every model page also carries an "other range
models" list, and the range and body-style links that name this layout appear again in the
navigation. `_OVERVIEW` brackets on `id="panoramica-modello"` and an `END PANORAMICA
MODELLO` **HTML comment** — worth knowing when trimming fixtures, since stripping comments
destroys the closing marker.

**Footnote links sit inside the label cell**, before its `</td>`, on any row carrying a
note. `_spec_row` allows for that and for the padding described below, which is why all
five table fields are built from one helper rather than written out five times.

## The products with no factory model page

* **Horus 12** — `/int/en/gamma/horus/modello/12` now 302s to `/`. MNC sells it as a 2027
  and publishes its dimensions in the exact millimetre form, `5413 × 2050 × 2659 mm`. It
  keeps MNC's price, body type, base vehicle and dimensions, and nothing else.
* **Rimor Van 238** — the factory gives it a standalone `/int/en/special/rimor-van` page
  with no spec table. MNC files it under its **Horus** category, and MNC decides the
  range, so `manufacturer_range` is Horus and the model is `Van 238`. It has no model
  page either, but since 8 September 2026 it is fully specified anyway — from the range
  leaflet. See [The Van 238's leaflet](#the-van-238s-leaflet-is-a-spec-sheet).

Where MNC is the only source, its seats and berths are taken **only when the two figures
differ** (both of these publish `3 berth with 4 travel seats`). Two equal figures cannot
be told apart from the repeat-the-seat-count bug, so they are left empty rather than
guessed. Masses are never taken from MNC, which publishes no MRO at all and no MTPLM.

Worth a second look one day: Horus 12's MNC dimensions are **identical to Horus 54's**,
and MNC demonstrably copy-pastes between layouts elsewhere. Both are sub-6m Ducato vans
that plausibly share a shell, and the factory dropped Horus 12 before this could be
checked against it.

## What changed in September, and what it cost

The factory redesigned its model pages between 13 August and 5 September 2026 — a
changeover consistent with Caravan Salon Düsseldorf running 28.08–06.09.2026. **Five of
the previous adapter's six field extractors stopped matching**, leaving bed type as the
only field still parsing:

* The dimension cells gained `class="uc-first"` and newline padding, so `outside
  length</td>` no longer matched `outside length\n    </td>`.
* `title="numero posti omologati"` became `class="lc-icons-posti-omologati"`.

A run in that state would have failed safe — every field absent, so every change a no-op
and the stored figures preserved — but it would have silently stopped updating. That is
the argument for the plausibility floor and for asserting per-range counts, not just a
total.

The range also moved **41 → 37 layouts**, with Sarus dropping 13 → 6 while Kilig gained
12 → 16. Given the wholesale rename, that looks like a reshuffle between ranges rather
than seven deletions, and it is worth re-checking rather than believing.

**Two things got better.** The redesigned pages publish **MRO per model** (Kilig 5:
`MRO 2961 kg` against `3500 / 3550 / 4100 kg`), so `mro_kilograms` and
`mh_payload_kilograms` are available for the first time — 30 of 34 products carry a
payload now. And that removed the last reason to fetch the catalogue PDF, which existed
only for MTPLM and the chassis; the chassis now comes from MNC's `Vehicle:` line. **The
catalogue and leaflet machinery is gone entirely**, along with its season-and-version URL
probing, its unrecoverable column alignment, and the four leaflet fetches per run.

> Both came back within three days, and neither for the reason it was dropped. Rimor
> withdrew the MRO row on 7 September, so the catalogue is the only source of that figure
> again — but for one row, not the whole table. And the Rimor Van leaflet turned out to be
> a single-layout spec sheet, which is the Van 238's only specification. The URL probing
> did not come back: both PDFs are now linked from a real download page. See
> [Rimor withdrew MRO](#rimor-withdrew-mro-on-7-september-2026) below.

The old cross-document check (each range's leaflet republishing every layout's
`length × width`, compared as an unordered multiset) is replaced by the cross-site
dimension check, which is cheaper, needs no PDF parsing, and immediately found two errors
the leaflet check never could — because it compares MNC against the factory rather than
the factory against itself.

## First run

5 September 2026, all five ranges, **34 products and 396 fields with provenance**. Every
per-range count matches the survey above. Body types come out **7 campervan high top, 17
low profile, 10 over-cab** — every van a high top, as the height rule requires.
Hand-checked against both sources:

| | Kilig 66 Plus | Sailer 55 Plus | Van 238 |
|---|---|---|---|
| MNC lists it as | Kilig 66 2026 | 55 Plus, demo van only | Van 238 2026-Automatic |
| Price | £59,995 | £69,995 (pre-discount) | £56,995 |
| L / W / H (mm) | 7338 / 2340 / 2845 | 7338 / 2340 / 2845 | 5980 / 2050 / 2800 (MNC) |
| Seats / berths | 4 / 4 | 4 / 4 | 4 / 3 |
| MTPLM / MRO / payload | 3500 / 3017 / 483 | 3500 / 3051 / 449 | — |
| Body type | low profile | low profile | campervan high top |

Note Kilig 66 Plus: MNC calls it "Kilig 66", the factory now calls it "66 Plus", and the
stored model is the factory's current name. Its 7330 mm on MNC against 7338 mm on the
factory is truncation, within tolerance, and is what confirms the rename join is right.

Horus 54 is the useful case for the other direction: its MNC page gives exact
millimetres, so the check runs at **zero tolerance**, and the two sites agree on all three
axes exactly.

## Rimor withdrew MRO on 7 September 2026

One day after it appeared. The overview block now reads:

```
outside length 7338 mm
outside width - inside width 2340 - 2200 mm
maximum outside height inside height 2845 - 2060 mm
maximum overall weight 3500 / 3550 / 4100 kg
4  4  1150x850
Bedding solution : Transverse bed
```

Both `MRO` and `available mass for optional equipment installation` are gone, as are the
footnote markers. So **`mro_kilograms` and `mh_payload_kilograms` are unavailable again**,
and the payload arithmetic with them. Everything else still parses — dimensions, the
homologated seat count, berths, MTPLM, the bedding solution and the garage were all
checked against the live pages the same day.

Nothing in the adapter changed for this and nothing needed to: the run reports the field
as unfound, a matched product keeps whatever FMLV holds, and the figure is not silently
inherited into anything that would look collected. That is
`docs/adapters/README.md`'s rule on a withdrawn spec working as intended.

**It leaves a real gap on new products**, though, and this is where it hurts: a layout
FMLV has never held has no MRO from anywhere, so its upload row carries none and
`validation` reports `required field 'mro_kilograms' is missing`. That is honest but it
used to surface only in the issues file, after the upload was generated — which is why
`store.changes.fields_needing_a_choice` now puts a row in the review for it instead.

`_MRO` still matches the markup it had, so a republished figure is picked up without a
code change — and the model page stays preferred over the catalogue below whenever it has
one.

### The catalogue is the source of MRO again

Found on 8 September 2026, the day after the withdrawal. `/int/en/rimor-download` links
the season catalogue (`RIM_Catalogo 2026-27 EU_V6.pdf`, 6 MB) plus five range leaflets,
and its technical-data tables carry MRO for **35 layouts** — every one MNC sells, and five
it does not.

**It is linked from a real page now**, which is what changed: in August the catalogue sat
at an unadvertised path and had to be probed by season and version. The URL is
rediscovered per run like any other, matched on `catalogo` rather than a filename, since
the name carries both a season and a version.

**Only MRO is read out of it, and that restriction is the whole design.** The tables put
two or three layouts side by side and pypdf returns each row as one text run, so a row
printing a value once where it spans several columns cannot be split — every run starts at
the same x, so the coordinates give nothing either. The Horus page is the illustration:
three layouts, but

```
Wheelbase (mm) 4035 3450
Outside length (mm) 5998 5413
MRO (kg) 2770 2866 2714
```

Two values for three columns on the first two rows, and nothing to say which column the
shared one covers. That is what made the catalogue useless for dimensions in August, and
still does.

MRO escapes it because **every layout's is distinct**, so its row always carries exactly
as many values as the page has columns. `parse_catalogue_mro` therefore reads a row
positionally when the counts match, applies it to every layout on the page when there is
exactly one value — Kilig 669 and 695 genuinely share 3024 — and **skips it otherwise**,
that being the only case that could misattribute.

**Validated against the site's own figures**, which is what makes this trustworthy rather
than merely plausible: of the 30 MROs `rimor.it` published before withdrawing the field,
the catalogue agrees on **30 and differs on none**. The provenance says the figure came
from the catalogue and that the model page no longer carries it, so a reviewer clicking
through to the layout does not find it absent and read it as invented.

Four of the 34 still have no MRO, and none of them is a parsing failure:

| Layout | Why |
| --- | --- |
| Horus 40 | Not in the catalogue's technical-data tables — it carries Horus 38, 45, 54 and 95 only |
| Horus 66 | Same |
| Horus 12 | No factory page, and no catalogue row |
| Van 238 | No factory page — but the leaflet supplies it, so this one is closed |

Horus 40 and 66 are named in the Horus leaflet's prose, so they are current models the
catalogue's spec tables simply omit. Both have an MTPLM from their model pages, so a
published MRO is all that stands between them and a payload.

### The Van 238's leaflet is a spec sheet

The same download page links five range leaflets alongside the catalogue. Four are
marketing — the Horus and Kilig ones were checked on 8 September 2026 and carry no
technical table at all, no MRO row, no weights, no dimensions rows. The Horus one prints
six unlabelled `5998x2050`-style pairs for six layouts, which is exactly the attribution
problem the catalogue has and `parse_catalogue_mro` refuses to guess at.

`RIM_Pieghevole Rimor Van 2026-27 EU_V2_WEB.pdf` is different, because **Rimor Van is a
one-layout range**, so its leaflet doubles as the layout's data sheet: one value per row,
nothing side by side, nothing to misattribute.

```
Outside length (mm) 5981
Outside width - inside width (mm) 2059 - 1850
Maximum outside height - inside height (mm)2800 - 2070
Certified seats 4
Maximum overall weight (kg) 3500
MRO (kg) 2765
Fixed berths 2
Assemblable berths 1
```

That closed the last product with no factory specification. The Van 238 went from price,
body type and three truncated dimensions to every figure FMLV asks for:

| | Before | From the leaflet |
| --- | --- | --- |
| Length | 5980 mm, MNC truncated | **5981 mm** |
| Width | 2050 mm, MNC truncated | **2059 mm** |
| Height | 2800 mm, MNC truncated | 2800 mm, exact |
| MTPLM | — | **3500 kg** |
| MRO | — | **2765 kg** |
| Payload | — | **735 kg** |
| Berths | 3, from MNC | 3 — `2 fixed + 1 assemblable` |

The width is the case for the leaflet in one line: MNC's `2.05 m` truncates to 2050 and
the vehicle is 2059. It also **agrees with MNC on all three axes** within the 9 mm
truncation allows, which is a genuine cross-check — the two sites publish independently.

Three things the implementation is careful about:

* **The layout is read from the leaflet, not assumed.** A leaflet is a range document. If
  Rimor adds a second van, the file at that URL becomes a different vehicle's data sheet,
  and quietly handing the 238 someone else's weights is the failure worth designing out.
  `parse_van_leaflet` reads `Rimor Van 238` and the caller checks it against the layout
  MNC listed.
* **Numbers only.** The leaflet's prose does name beds and equipment, but MNC's names them
  better and already does: MNC gives the Van 238 a transverse bed *and* a made-up one off
  "middle dinette, which converts into a single bed", where the leaflet says only
  "transverse". Same division of labour as everywhere else — the factory settles every
  figure, the importer's prose settles the fittings.
* **The provenance says it is a leaflet.** Every snippet it sourced ends `from the range
  leaflet`, because the link opens a PDF and a reviewer who clicked expecting a model page
  has to be told what they are looking at.

The leaflet also carries the layout drawing, beside the technical data and captioned with
the bed sizes and the `5981x2059` overall callout. It is not a `/public/...piantina...`
image like the model pages carry, so the four positional fields point at the PDF. Before
this the Van 238's positional fields had no row at all, which is what the requester saw on
7 September 2026: *"I didn't see any flags saying that that wasn't completed."*

## The 2027 catalogue, checked against FMLV — 10 September 2026

The requester obtained `RIM_27_EU_CAT`, the **2026-2027 factory catalogue**, from a
contact at MNC. It is a factory EU document, not a UK one, and its technical data is
dated **May 2026**. Nothing in the adapter changed as a result; it was read as a
cross-check and it is a good one.

**It publishes no prices.** Zero, in 48 pages. That is the third independent
confirmation of the note above — Rimor publish no price in the HTML, not in the
leaflets, and not in the catalogue. MNC's remains the only price there is.

### The specification data agrees on 30 of 30 products, across five fields

Every model FMLV holds for 2027 that the catalogue also lists was compared on outside
length, outside width, maximum outside height, MRO and certified seats. **All thirty
agree on all five.** For a source read off two websites and checked against a document
neither of them produced, that is as strong a result as this project has had.

One thing to know before repeating the check: **the certified-seats row reads
first-figure-wins**, and it is the opposite of the usual convention. The catalogue
prints `Certified seats 6 / 5`, and footnote 1 explains why — *"the reduction in the
number of approved seats increases the mass available for the installation of optional
equipment by 85 kg for each seat removed"*. So the **higher** figure is the approved
standard and the lower is what you get by deleting a seat to buy payload. That is not
the Bürstner case, where the upper figure is a paid option; it is its mirror image, and
taking the lower figure would understate eleven products. The adapter already reads it
correctly.

### Four Horus layouts are absent from the factory's 2027 line-up

| in FMLV as 2027 | in the 2027 catalogue |
| --- | --- |
| Horus 12, 40, 66, Van 238 | **absent** |

The catalogue's Horus range is four layouts — 38, 45, 54 and 95 — against the seven FMLV
holds. This is the requester's own expectation, from 10 September: *"I think we might
find a few more models being stood down."*

**It is not proof, and must not be actioned from this document.** The roster is MNC's,
not the factory's, and MNC's site is what a run reads. Two things have to be true before
these are archived: MNC has to have dropped them too, and they must not be **renames** —
Horus 12 and 54 share a 5413mm length, and 38, 40 and 66 all share 5998mm, so the old
codes could be the new ones under another name. Rimor have renamed a whole line before
(the Kilig `<n>` → `<n> Plus` move recorded above). Check the claimed disappearances
against the survivors on length and MRO before believing any of them.

### The five layouts MNC do not sell are confirmed exactly

The catalogue lists five models FMLV has never held: **Horus 45, Kilig 73 Plus, Sarus 50,
Sarus 69 Plus and Sarus 95 Plus.** That is byte-for-byte the list in the registry note of
5 September — the layouts the requester confirmed MNC do not list. An independent factory
document naming exactly those five, and no others, settles the "is the Sarus gap a
deliberate importer decision or an unfinished page?" question left open above: it is
deliberate, and the factory builds them for other markets.

### Two smaller things

* **The publisher is Luano Camp S.r.l.** The catalogue's legal page and its chassis
  disclaimers name Luano Camp throughout, not Rimor. The brand is theirs now. Nothing in
  FMLV changes — `fmlv_manufacturer` stays `Rimor` — but it explains the domain and is
  worth knowing before anyone reads a Luano Camp document as a different manufacturer.
* **The heater is confirmed blown air on all 35.** `Gas heater Combi C4` on Horus, Kilig
  and Sarus, `Combi C6` on Super Brig and Sailer. The catalogue also gives fridge
  capacities per layout — 70, 89, 90, 150 and 158 litres — which is finer than anything
  the websites publish, though the habitation findings do not need it.

## What is unverified

* **`ncc_supplier_name`** is `Rimor`, inherited from the seed list and **not confirmed**
  against the NCC site's export dropdown.
* **`fmlv_manufacturer`** is `Rimor` from `resources/manufacturers-full-list.csv` (id
  `75`); it has not been checked against a real FMLV export, so the baseline join is still
  unproven and every run to date has classified all products as new.
* **The Rimor Van 238's range.** Filed under Horus because MNC files it there; the factory
  treats it as a standalone "RIMOR VAN". If FMLV would rather see a Rimor Van range, this
  is a one-line change to `RANGE_LABELS`.
* **Whether MNC's prices are on-the-road or ex-works.** The pages say only "£ 59,995" with
  options priced separately, and carry a "check our full current and technical
  specifications with us before placing your order" disclaimer.
* **The Sarus gap.** MNC lists 3 of the factory's 6 Sarus layouts. Read as a deliberate
  importer decision, per the rule that MNC defines the range — but it is the largest gap
  of the five and worth confirming it is not simply a page MNC has not finished building.
