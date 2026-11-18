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

## The source: nine model pages on a UK site

This is not the two-source shape the other Marquis brands have. `panamauk.co.uk` carries
both the roster and the numbers, so Panama is closer to Auto-Sleepers than to Benimar.

Every page is plain HTML on a Wix site — large (2–2.5 MB raw, 13 KB of text) but
server-rendered, so no browser is needed.

### The roster moved, and reading the homepage alone was costing us five models

**At the survey, September 2026**, `sitemap.xml` listed five *other* sitemaps — videos,
news, events — and no model page at all, so the homepage's own links were the only roster
there was.

**That changed when Panama rebuilt the site in autumn 2026**, and it changed quietly.
`pages-sitemap.xml` now lists **all nine** model pages. The homepage links **four**. The
rest hang off two new range pages, `/panama-core-range` (titled *Panama Signature*) and
`/panama-se-range`, whose *DISCOVER* buttons Wix renders client-side — they are not in the
served HTML, so a plain fetch cannot follow them.

Between 15 September and 18 November 2026 the adapter therefore collected three models and
said nothing about the other six. **An unlinked page and a withdrawn model look identical
from here**, which is why the roster is now the sitemap, with the homepage kept as its
fallback and its cross-check: a page in one and not the other is read, and said out loud.

| page | site name | range | in FMLV, Sept 2026 |
| --- | --- | --- | --- |
| `/p12` | `P\12` | Signature | `P` / `/12` |
| `/p12-plus` | `P\12+` | Signature | — |
| `/p50` | `P\50` | Signature | — |
| `/p50-plus` | `P\50+` | Signature | — |
| `/p57` | `P\57` | Signature | `P` / `/57` |
| `/p12-se` | `P\12 SE` | SE | — |
| `/p12-se-awd` | `P\12 SE AWD` | SE | — |
| `/p57-se` | `P\57 SE` | SE | — |
| `/p10-e` | `P\10E Hybrid` | — | `P` / `\10E Hybrid` |

**The Signature and SE names are not recorded.** FMLV files all nine under range `P` with
the layout as the model, which is what it already holds for the three it has, and the SE
is in the model name anyway.

### Three readers had to change with it

Found on 18 November 2026, each of them a silent failure rather than an error:

* **The path pattern allowed one hyphenated word**, so `/p12-se-awd`, `/p12-se` and
  `/p57-se` matched nothing — even on the one page that did link the first of them.
* **The title pattern took one word and an optional `Hybrid`.** `P\12 SE AWD| Panama MPV
  Campervan` is three, with two spaces inside the name and none before the pipe, so the
  page was narrated as carrying no model name at all.
* **`Maximum User Payload (A-B` is missing its closing bracket** on all three SE pages.
  Unread, their payload would be derived from the two masses with nothing corroborating
  it. The `P\57` is a different case and not fixable in a label: that page prints no
  payload row at all.

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

## Width: the folded figure, never the one beside it

Panama are the only brand in the group that print **both**, which makes them the place a
column mixing folded and extended mirrors would come from:

```
Overall Width (inc mirrors)     7'5 1/2" | 2275mm
Overall Width (mirrors folded)  7' 1/2"  | 2150mm
```

**2150 mm is recorded and 2275 mm never is.** A Ford Tourneo Custom's body is about
1986 mm, so the folded figure is the mirrors rather than the body — but the settled rule is
to reflect what the manufacturer states with the mirrors folded, whatever the body shape,
so that one column means one thing. See `README.md`.

FMLV already holds 2150 on its existing rows, so nothing changes for them.

## A dimension can arrive without its unit

**18 November 2026.** The `P\12+` page prints `Overall Height 6'7" | 2000` — no `mm`, and
the row moved below the tyre size. The same page printed `2000mm` in September and its
eight siblings still do, and 6'7" is 2007mm, so the figure is millimetres.

`_first_millimetres` falls back to a bare number **after the pipe**, which is where this
site puts the metric figure in every row. Not to any bare number: the window after a label
runs on into the next row, so left loose the height on that page would have read the `215`
of `215/60 R17 C`.

## Still unverified

* **Price.** Not yet looked for. Marquis are the seller, so their price is the one that
  counts by the settled rule, and it may not be on `panamauk.co.uk` at all.
* **Habitation.** Not yet examined.
* **Floorplans.** Not yet examined.
* **Whether the Signature and SE pages ever carry a model the sitemap does not.** Their
  buttons are client-side, so nothing here has read them; the sitemap has been complete
  every time it has been checked, which is twice.
* **Whether the P\12's two columns are two FMLV products.** If the seven-seat version is
  sold as a distinct vehicle, the answer to question 1 is "both", not "column 1".
