# Ace Motorhomes — site survey

Surveyed and built 16 September 2026. FMLV manufacturer id **264**, name **`Swift Group
Ltd`**, display name **`Ace Motorhomes`**. **NCC supplier name `Ace Motorhomes`.**
Campervans and motorhomes. **22 layouts across three ranges**; FMLV held ten at survey.

## The second brand under one manufacturer

`fmlv_manufacturer` names the *legal* manufacturer, and Swift Group Ltd owns three FMLV
rows:

| id | `fmlv_manufacturer` | display name |
| --- | --- | --- |
| 26 | `Swift Group Ltd` | Swift |
| 228 | `Swift Group Ltd` | Bessacarr |
| **264** | `Swift Group Ltd` | **Ace Motorhomes** |

`swift.py` already declared `Swift Group Ltd` for motorhomes, so **`ADAPTERS` had to be
re-keyed on `(manufacturer, display name, product area)`** before this adapter could exist —
see `adapters/__init__.py` and the rule in `README.md`. Keyed on the manufacturer alone, one
of the two modules would have answered for the other and written a full set of plausible,
wrong proposals against the other brand's real `product_id`s.

Two consequences worth knowing:

* **`fmlv run "Swift Group Ltd"` no longer resolves**, and says so usefully — *"one
  manufacturer, several brands. Use the brand name or the id: 26 (Swift), 264 (Ace
  Motorhomes)"*. `fmlv run "Ace Motorhomes"` and `fmlv run "Swift"` both work;
* `adapter_for` returns `None` for an ambiguous manufacturer rather than picking one.

Bessacarr became the third on 17 September 2026 and needed no further change — `bessacarr.py` registered under `(Swift Group Ltd, Bessacarr, caravan)` with three lines in `adapters/__init__.py` and nothing else. It also made the *caravan* half ambiguous, so `fmlv run "Swift Group Ltd"` now resolves in neither product area; see `docs/adapters/bessacarr.md`.

## The source: the site publishes its own spec sheet as JSON

**The cleanest source in the project.** Every range page carries its whole layout dataset
inline:

```html
<script type="application/json"> [ … ] </script>
```

```json
{"title":"1500 DB (4 berth)","berths":4,"travellingSeats":4,
 "length":"7.81m","width":"2.37m","height":"2.88m",
 "weightMtplm":"3500kg","weightMro":"3045kg","payload":"455kg",
 "startingPrice":71490,"axleType":"Motorhome - Standard axle",
 "licenceCategory":"B","hasPopTopImage":false,
 "beds":[{"name":"Rear double","size":"6'9\" x 4'3\""}],
 "optionalExtras":[…]}
```

Plain HTTP. **No browser, no PDF, nothing parsed out of prose**, and every field FMLV wants
in one place. A page carries more than one JSON block, so the right one is found by what it
contains — the list whose entries carry a `weightMtplm` — rather than by its position.

This is what a site rebuild would break first, and `collect` says so rather than reporting
an empty range.

## The roster: 22 layouts, of which 12 were new

| range | path | chassis | body | layouts |
| --- | --- | --- | --- | --- |
| **1200** | `/campervans/1200/` | Fiat | campervan high top | GS, GST, RB, RL, RLT, GL, GLT, SL, SLT |
| **1500** | `/motorhomes/1500/` | Ford | low-profile coachbuilt | GL, ET, DB2, DB4, SL2, SL4 |
| **Supreme** | `/motorhomes/supreme/` | Ford | low-profile coachbuilt | DB2, DB4, ET2, ET4, EW2, SL2, SL4 |

FMLV held ten at survey — six 1200s and four 1500s — so **GS, GST and RB on the 1200, GL and
ET on the 1500, and the whole Supreme range are new.**

Ace publish no count of their own, so `EXPECTED_LAYOUTS` is the only thing that would notice
a range page losing one. The arithmetic below cannot see an absence.

## The berth count is part of the model

**The problem the requester spotted from the export**, and the one that would have done real
damage. Ace sell one floorplan two ways — a 2-berth, and a 4-berth with a drop-down electric
bed over the front lounge and two extra belted seats. FMLV held both as `1500 SL`:

| id | range | model | seats | berths | MRO | price |
| --- | --- | --- | --- | --- | --- | --- |
| 8792 | 1500 | SL | 2 | 2 | 3005 | £66,905 |
| 8793 | 1500 | **SL** | 4 | 4 | 3075 | £68,900 |

Matching keys on range plus model, so those are **one product** to the pipeline — and
`cli._dedupe_baseline` exists to strip duplicate range/model rows, so it would have dropped
one of each pair *before the diff ran*, silently, with nothing reported as disappeared. Four
real products would have gone unmanaged.

So the berth count joins the code, **with no separator**:

| | score against its sibling | |
| --- | --- | --- |
| `SL` / `SL` | 1.000 | collide |
| `SL 2` / `SL 4` | **0.500** | collide — that *is* the threshold |
| `SL (2 berth)` / `SL (4 berth)` | 0.600 | collide |
| **`SL2` / `SL4`** | **0.333** | distinct |

The tokeniser splits on non-alphanumerics, so `SL 2` becomes `{sl, 2}` and the shared `sl`
plus the shared range carries half the score. A hyphen behaves the same. Settled with the
requester on 16 September 2026, who renamed FMLV's four rows to match.

**A layout with no berth count in its title keeps its bare code.** The 1200 already
separates its 4-berths with a `T` suffix, and `1500 GL` is 2-berth only.

### The title is load-bearing

`1500 DB (2 berth)` and `1500 SL (2 berth)` publish **identical** length, width, height,
MTPLM, MRO, payload and price. Only the title and the bed list differ. So if Ace ever
stopped writing the berth count, nothing in the data could tell the pairs apart.

## Supreme is a new range, not a rename

Worth recording because it was considered and rejected. The requester's first reading was
that `1500 DB` had been renamed `Supreme DB` — which would have been a `RENAMED_MODELS`
entry. The site says otherwise:

* **both range pages exist**, and both are linked from `/motorhomes/`;
* the Supreme's own copy: *"Building on the popularity of the 1500 range, it offers that
  little bit extra"*;
* the figures differ — `Supreme DB (2 berth)` is 7.85 m against the 1500's 7.81 m, and
  3032 kg against 2975 kg.

Settled 16 September 2026: **the Supreme layouts are new products and the 1500 continues.**
Treating it as a rename would have merged two real vehicles onto one `product_id`.

## A real arithmetic self-check

Ace publish all three masses, so `payload == MTPLM - MRO` is a genuine check rather than the
true-by-construction identity several other adapters have to settle for. **It held on 21 of
the 22 layouts.**

The exception is **`1200 RLT`**: MTPLM 3500, MRO 2990, payload 540 — and 3500 − 2990 is 510,
a 30 kg gap. Ace's own optional-extras note explains it:

> *"This option increases the MRO by 30kg and decreases the Max Payload by 30kg"* — the
> automatic gearbox.

So it is one figure taken from the automatic and the rest from the manual: their slip, not
this parse. Narrated every run and the vehicle goes forward, since its dimensions and price
are not in doubt.

## The Supreme has no prices yet

Every Supreme entry reads `"startingPrice": 0`, which is not a price. **It is emitted as
nothing**, never as £0 — a wrong figure is worse than an absent one, and the run says so per
layout. The 1200 and 1500 are fully priced.

## Habitation is qualified by letter, not by number

Ace write `Separate shower cubicle (DB, ET & SL)`, which no pattern can tell from `(LED)` or
`(5G ready)`. So `habitation.lines_for_layout` now takes a **codes vocabulary** and treats a
parenthetical as a qualifier only when *every* token inside it is one of that manufacturer's
codes. Nothing is guessed from letters alone.

That matters here for the same reason it did on Elnagh: the 1500 GL has **no** separate
shower and the DB, ET and SL do, so reading the feature range-wide would be wrong rather
than merely vague.

**The beds come from each layout's own entry** — `Rear double`, `Front dinette`, `Drop
down`, with sizes — which is better than the range prose and is per layout.

## Still unverified

* ~~**Bessacarr**, id 228~~ — built 17 September 2026, caravans only. See
  `docs/adapters/bessacarr.md`.
* **Floorplans**, and the `tour360Url` and `videoTourTikTokId` fields, which are not read.
* **`optionalExtras`**, which carries priced options per layout — an automatic gearbox, a
  comfort pack — and is not read. It is what explains the RLT discrepancy.
* **Whether the 1500 survives into 2027.** The requester expects it to be withdrawn in
  favour of the Supreme, but it was still published with prices at survey. If Ace take it
  down the layouts simply stop being collected and FMLV's rows get disappearance notices,
  which needs no code change.
