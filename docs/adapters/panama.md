# Panama — site survey

Surveyed 14 September 2026. FMLV manufacturer id **221**, name **`Panama`**, display name
the same. **NCC supplier name `Marquis Leisure`**, not `Panama`. Campervans only. Five
layouts on the site; FMLV holds three.

## What the requester brought to the survey

* **Sole UK importer and seller is Marquis Leisure**, so by the settled rule Marquis
  decide what exists and what it costs, and the factory decides every number.
* **The export comes back with Mobilvetta products in it** — *"a little bit unusual... you
  may have to separate the ones we need"*. In practice **nothing special is needed**: the
  export holds 29 rows, 26 Mobilvetta and 3 Panama, and the pipeline filters the baseline
  to one `fmlv_manufacturer` before diffing. Mobilvetta (id 12) shares the supplier name
  and will fetch its own copy of the same file.
* *"Ranges in the parent website may comprise greater numbers of models than offered in
  the UK."* Here the reverse is true, because `panamauk.co.uk` **is** a UK site: it lists
  five and FMLV holds three.

## The source: five model pages on a UK site

This is not the two-source shape the other Marquis brands have. `panamauk.co.uk` carries
both the roster and the numbers, so Panama is closer to Auto-Sleepers than to Benimar.

**Do not use `sitemap.xml`.** It lists five *other* sitemaps — videos, news, events — and
no model pages. The roster comes from the homepage's own links:

| page | site name | in FMLV |
| --- | --- | --- |
| `/p12` | `P\12` | `P` / `/12` |
| `/p57` | `P\57` | `P` / `/57` |
| `/p10-e` | `P\10E Hybrid` | `P` / `\10E Hybrid` |
| `/p12-plus` | `P\12+` | — **new** |
| `/p50-plus` | `P\50+` | — **new** |

Every page is plain HTML on a Wix-style site — large (2 MB raw, 13 KB of text) but
server-rendered, so no browser is needed.

## Every page states the specification, and labels the widths

```
Approved Belted Travel Seats (including driver)   5
Berths (sleeping positions)                       4
Overall length              17'10" | 5440mm
Overall Width (inc mirrors)  7'5 1/2" | 2275mm
Overall Width (mirrors folded) 7' 1/2" | 2150mm
Overall Height               6'7" | 2000mm
MTPLM (A)                   3225kg
Mass in Running Order (B)   2655kg
Maximum User Payload (A-B)   570kg
```

— the real P\12+, verbatim.

**`Overall Width (mirrors folded)` is FMLV's definition and the mirrors-included figure is
named beside it**, so there is no way to take the wrong one. Every layout is 2150 mm.

### The self-check is printed on three pages and derivable on the other two

`Maximum User Payload (A-B)` appears on the P\12+, P\50+ and P\10E Hybrid, and is exact on
all three:

| | MTPLM | MIRO | payload | A − B |
| --- | --- | --- | --- | --- |
| P\12+ | 3225 | 2655 | 570 | **570** ✓ |
| P\50+ | 3225 | 2695 | 530 | **530** ✓ |
| P\10E Hybrid | 3245 | 2780 | 465 | **465** ✓ |
| P\57 | 3225 | 2875 | *not printed* | 350 |
| P\12 | 3175 | 2558 | *not printed* | 617 |

So where Panama print it, it checks the parse; where they do not, the payload is derived
and the identity becomes true by construction. That is a weaker position than
Auto-Sleepers but stronger than Joa or Pilote.

## Three traps in the markup

* **The labels vary.** `MTPLM (A) kg` on the P\12 and `MTPLM (A)` on the other four. Match
  the stem.
* **`Berths (sleeping potitions)`** — misspelled on the P\10E Hybrid and spelled correctly
  on the rest. The same class of thing as Auto-Sleepers' *"Seperate"*.
* **The P\10E Hybrid leaves its HTML entities unescaped** in the rendered text —
  `7&#x27; 1/2&quot;` where the others give `7' 1⁄2"`. One page generated differently from
  its siblings, so entity handling cannot be skipped.

## The two questions this survey cannot answer

### 1. The P\12 publishes two columns for one FMLV product

Alone among the five, its table has **two variants side by side**:

| | column 1 | column 2 |
| --- | --- | --- |
| Approved Belted Travel Seats | **5** | **7** |
| Berths | 4 | 4 |
| MTPLM (A) | 3175 | 3175 |
| Mass in Running Order (B) | **2558** | **2630** |

Everything else is identical. FMLV holds one `P` / `/12`, so one column has to be chosen —
and this is exactly the column-alignment risk `docs/adapters/README.md` warns about, where
picking wrongly yields a plausible, internally consistent vehicle carrying another's
weights.

**The settled base-vehicle rule points at column 1**: 5 seats is the standard fitment and
the seventh seat the addition, and the lower MIRO goes with it. But the page does not say
so, and nothing else on the site distinguishes them, so this is put to the requester.

### 2. FMLV's slash direction disagrees with itself

The site writes a **backslash** on all five — `P\12`, `P\57`, `P\10E Hybrid` — and the page
titles confirm it is a real `U+005C`, not a rendering artefact. FMLV holds:

| FMLV model | site |
| --- | --- |
| `/12` | `\12` |
| `/57` | `\57` |
| `\10E Hybrid` | `\10E Hybrid` ✓ |

So FMLV is **internally inconsistent** — two forward slashes and one backslash — and two
of the three disagree with the manufacturer. A model code is an identity, so this is the
requester's call rather than the adapter's.

## Width: not recorded at all, because every Panama is a panel van

Panama publish **both** mirror figures and no body width:

```
Overall Width (inc mirrors)     7'5 1/2" | 2275mm
Overall Width (mirrors folded)  7' 1/2"  | 2150mm
```

A Ford Tourneo Custom's body is about **1986 mm**, so neither measures it. The 2150 mm FMLV
holds on its existing rows is the folded-mirror figure carried over; emitting nothing leaves
those untouched and stops a new layout arriving about 160 mm too wide.

Run #84, before this rule, proposed 2150 mm for `P\12+` and `P\50+` as new products. The
adapter can stop asserting the figure but cannot remove one already in FMLV, so clearing or
correcting the existing five is a manual edit.

The rule and the contrast with a coachbuilt are in `README.md`; it is decided in
`base.width_from_mirrors_folded`, which Benimar, Mobilvetta and Panama all route through.
The requester's ruling, 12 September 2026: *"if they don't have a figure excluding mirrors,
we'll have to leave that blank as we don't have the correct figure, unless it's an existing
model that appears to have the same height and length."* Emitting nothing satisfies both
halves — an existing row keeps the body width FMLV holds, and a new one arrives visibly
blank rather than too wide.

**The blank explains itself in the review.** Left to itself the pipeline says the field
*"was not found on the manufacturer's site this run"*, which is untrue and reads as a parse
failure — the requester asked, on 15 September 2026, why the published figure was not being
taken. The adapter now records provenance for the field it deliberately leaves unset, and
`diff.compare` appends it, so the row names the published figure and says why it is not the
one FMLV wants.

## Still unverified

* **Price.** Not yet looked for. Marquis are the seller, so their price is the one that
  counts by the settled rule, and it may not be on `panamauk.co.uk` at all.
* **Habitation.** Not yet examined.
* **Floorplans.** Not yet examined.
* **Whether the P\12's two columns are two FMLV products.** If the seven-seat version is
  sold as a distinct vehicle, the answer to question 1 is "both", not "column 1".
