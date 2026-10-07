# AURA — survey and adapter, 7 October 2026

**NCC id 276.** `fmlv_manufacturer` **`Hobby`**, display name **`AURA`**, supplier name
`AURA`. Contact **Mike Lake**. Two modules: `aura.py` for motorhomes and campervans,
`aura_caravan.py` for caravans.

**AURA is Hobby rebadged for the UK**, and Hobby is no longer sold here under its own name.

## The join key, and the other Aura

**NCC id 243 is a different Aura** — the brand as it was when it had its own vehicles — and
its ten products arrive in the *same export*, under `manufacturer = AURA`, every one
deactivated. Two independent filters separate them:

| | manufacturer | display | state | rows |
|---|---|---|---|---|
| this one | **`Hobby`** | `AURA` | active | 13 motorhomes & campervans, 8 caravans |
| id 243 | `AURA` | `AURA` | **deactivated** | 10 |

**The display name is part of the adapter key regardless**, because NCC id 37 is also
`Hobby`. The old products are recognisable at a glance — ranges that are bare numbers,
`5 / EK`, `4 / Trend`, `4 / T7`.

> Our copy of `resources/manufacturers-full-list.csv` stops at id 275 and is dated
> 13 August 2026, so 276 is not in it. The file is stale, not the id.

## The site is not the specification source for caravans

**The requester's ruling, 7 October 2026:** Mike Lake's spreadsheets are the authority for
AURA, because they are defensible — *"at least I can say 'that's what you gave me'"* — and
FMLV matches them field for field, on every column of all eight caravans.

**The site lags.** Its footer reads 2026 where Hobby's own site is already on 2027, and its
caravan masses disagree with the spreadsheet on every layout. The requester's own
observation is the general rule here: *"with some of these smaller brands the website seems
to lag behind reality, unlike the larger brands."*

So the caravans are collected **by identity alone**, in the shape of `bespoke.py`'s Edition
half: the figures are narrated for comparison, never proposed over good data, and emitting
the identity still claims the FMLV row so a run cannot report a caravan AURA still sell as
missing. **The roster is the value** — a new or withdrawn layout shows up on the site first,
and the first run found three.

**There is also no self-check on that side.** The caravan pages publish MTPLM and MIRO but
no payload, so there is no arithmetic to test a parse against — a second reason to propose
nothing.

## The motorhome pages are a different matter

They publish **MTPLM, MIRO *and* payload**, so `mtplm - miro == payload` can be checked per
product. It holds on all thirteen, and the masses agree with FMLV on twelve of them.

| | | |
|---|---|---|
| berths | `3 (up to 4)` | the lower figure, per the settled rule |
| seat belts | `4`, or `6 (inc x2 lap belts)` | three-point belts only |
| masses | MTPLM, MIRO, payload | proposed; exact kilograms on both sides |
| dimensions | `Length 676cm` | **not proposed** — see below |

### Three things the site says that FMLV gets wrong

Each is a settled rule rather than a judgement made here:

- **Berths.** FMLV holds the *upper* figure on seven of the thirteen. `Berths 3 (up to 4)`
  is three; the extra berths need an option.
- **Belts.** The OnTour A 720 GFM reads `Seat Belts 6 (inc x2 lap belts)` where FMLV holds
  six. A lap belt is not a travel seat, so that is **four**.
- **A mass.** The campervan Prestige 640 ET reads MIRO 3120 against FMLV's 3032.

### No dimension is proposed, and that is deliberate

The site publishes **centimetres** where FMLV holds **millimetres**, so every length comes
back rounded — `676cm` against FMLV's `6759`, `288cm` against `2883`. The first run
proposed thirty such rows, every one asking a reviewer to make good data one millimetre
worse. The site is the coarser source for dimensions, so it is read for the narration and
nothing else. Masses are exact on both sides and are proposed.

### Body type is derived only where the site settles it

A **campervan**'s height does settle it: 2670 mm is over the shared 2300 mm threshold, so
high top — which is what FMLV already holds for all three. A **coach-built**'s range name
does not: the OnTour A describes its over-cab bed as an *option*, so nothing distinguishes a
low profile from an over-cab, and FMLV's own value is better than a guess.

## The shape of the pages, which is the whole parsing problem

**Every layout page is a two-column HTML table** — two layouts side by side, their names in
one row, their floorplans in the next, their figures in the one after. Reading the page as
a stream of text pairs the second layout's name with the first one's figures, and on the
Maxia page it did exactly that: the **740 WE came out with the 710 GE's weights**, plausible
and internally consistent and completely wrong. `columns_of` reads column by column, and a
table whose heading and figure counts disagree yields nothing rather than a guess.

**Four heading shapes**, all real and all found the hard way:

| | |
|---|---|
| `AURA OnTour C 680 GE` | the common one |
| `AURA Prestige 710 GE \| First Edition` | the badge shares the cell |
| `AURA Prestige \| 640 ET` | range and model are separate elements |
| `Beachy 360` | the caravan pages drop the `AURA` prefix |

**The range comes from the page, never the heading** — the Prestige T and Maxia T pages
both head their layouts without the `T`.

**Every table repeats**, in a slider and again in a dialog, so layouts are deduplicated on
the model name.

## Names FMLV spells differently

| the site | FMLV | why it matters |
|---|---|---|
| `700 F`, `700 FH` | `700F`, `700FH` | `700 FH` failed to match at all and arrived as a new product beside a disappearance notice for the row it was meant to update |
| `420+` | `420 Plus` | both reduce to the single token `420`, so the two Beachys collided on one FMLV row |
| `400 SFE` | `400 SFe` | cosmetic, but the rule is to file as FMLV files |

## What the first runs found

**Motorhomes and campervans, run #143:** 13 scraped against 13 baseline — **9 changed,
4 unchanged, 0 new, 0 disappeared**, 24 proposals, 71 fields verified unchanged.

**Caravans, run #144:** 11 scraped against 8 baseline — **0 changed, 8 unchanged, 3 new,
0 disappeared.** The three are `Prestige / 560 FC`, `Beachy / 360` and `Beachy / 450`.
Hobby's own site lists a 560 FC, which corroborates it.

A new caravan arrives as a name and nothing else, because the caravans are identity-only —
so it brings a row per in-scope field it lacks. That is noisy but honest, and it is the
price of not overwriting the importer's figures on the eight that already exist.

## Data defects found in FMLV, inherited from the spreadsheet

- **Every caravan claimed double its payload.** Both payload columns held the same figure,
  where the rule is that they must *sum* to `MTPLM − MIRO`. Fixed on the requester's ruling
  that payload is the difference and is **not** split: the derived figure stays in personal
  effects and the optional column is cleared.
- **Three internal lengths exceed their body length** — `DeLuxe 495 WFB` 6827 against a
  5947 body, and both Beachys 4260 against 4105. The five correct ones are all exactly
  `body − 120`, so the 495 WFB's is almost certainly a transposed `5827`. **Left exactly as
  Mike Lake supplied them** on the requester's instruction, pending his answer after the
  October show — defensibility first.

## Prices never come from the site

It carries only range-level `from` figures, and they match no FMLV row at the entry end:
motorhomes advertise from £83,995 where the cheapest layout is £85,795, campervans from
£74,777 where the cheapest is £77,295. Prices come from the importer's lists, and
`rrp_pounds == price_min_range_pounds` on all 21 live rows.

## Hobby's own site is not a fallback

Checked on the requester's suggestion, and it does not work:

- **Only two of AURA's six caravan layouts appear on it**, and the ranges do not map —
  AURA's `DeLuxe 495 WFB` is Hobby's **Excellent** 495 WFB.
- **It publishes no dimensions in HTML at all.** Every layout name on a range page is an
  image caption; the figures live behind a JavaScript configurator.

It is still worth knowing that Hobby's site **is** on 2027, which is how we know AURA's is
the one behind.

## Other traps

- **Never read `/aura-ex-display-demo-campervans.php`** — individual used and ex-demo
  vehicles at their own prices, the trap `vantage.py` documents.
- **Site defects to expect:** `Boby Length` for `Body Length` on a DeLuxe layout (both
  spellings are matched); the Beachy specification page heads its price block `Prestige`;
  a children's bed listed as `197x690cm`.
- **The caravan export carries a Campod**, product 8722 `Leisure Pods Ltd / O2 / Laura
  Ashley` — Nova's supplier filter matches **AURA** inside "L-**aura**-Ashley", the same
  substring bug that put Bodans in Carado's export. Our manufacturer filter drops it.
