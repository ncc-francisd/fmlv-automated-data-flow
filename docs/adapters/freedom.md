# Freedom Caravans — survey, 7 October 2026

**NCC id 161**, `fmlv_manufacturer` **`Freedom Caravans`**, display name **`Freedom`**,
supplier name the same. **Caravans only**, and small ones: every model in the range is
750–850 kg MTPLM. No adapter yet — this is the checkpoint.

## What the requester supplied

The site, the two names, and that the range is *"slightly fewer models now"*. Also that
**the prices came from Freedom by email in July 2026 and are all FMLV has to go on** —
which turns out to matter, because it is how the site's two price sources can be told
apart. See below.

## The source is the model pages, and nothing else will do

One page per model at `/models/<slug>/`, each carrying a `Weights & Dimensions` block in
plain HTML. **No tables, no JavaScript, no login.** The Microlite Sport's, in full:

```
Weights
MTPLM:               750kg
Unladen Weight:      580kg
Payload:             170kg
Noseweight:          70kg
Dimensions — External
Overall Length:      4m (13′,1″)
Body Length:         2.82m (9′,3″)
Width:               1.94m (6′,4″)
Height (Roof Down):  2.21m (7′,3″)
Dimensions — Internal
Headroom (Roof Up):  1.88m (6′,2″)
Double Bed Size:     1.85m x 1.25m
Single Bed Size:     1.85m x 0.5m
```

`MTPLM`, `Unladen Weight`, `Payload`, `Noseweight`, `Overall Length`, `Body Length`,
`Width` and `Double Bed Size` appear on **all eight**. Height and headroom do too, under
two spellings — see the pop-top note.

### There is no price list, and the one PDF is not it

The whole site links **exactly one** PDF, `2025-Freedom-Web-Brochure-v1.1.pdf`. It carries
weights but **not one price**, and it still describes models no longer sold, so it is
neither the price source nor the roster. Checked `/`, `/models/`, `/buy/`, `/buy/dealers/`,
`/buy/shows/`, `/about/`, `/owners/`, `/owners/servicing/`, `/used/` and `/contact/`.

## The trap: `/models/` is stale and would propose five wrong prices

The index page and the model pages disagree on **six of the eight**. The model pages agree
with FMLV **to the pound on all five it holds**:

| | `/models/` index | the model page | FMLV holds |
|---|---|---|---|
| Jetstream Twin Sport | £19,295 | **£18,495** | 18,495 |
| Jetstream First Class | £19,295 | **£18,495** | 18,495 |
| Sunseeker | £15,795 | **£16,995** | 16,995 |
| Microlite Discovery | £15,295 | **£15,995** | 15,995 |
| Microlite Sport | £13,995 | **£14,995** | 14,995 |
| Carpento 360 | £23,995 | £23,995 | — |
| Wayfarer Quad | £14,995 | **£16,495** | — |
| Wayfarer Duet | £14,995 | **£16,495** | — |

The index is not simply older — it is dearer on the Jetstreams and cheaper on the
Sunseeker, so it is a page nobody has maintained rather than a superseded price round.
**Read the model page. Use the index only for the roster.**

## The self-check is arithmetic, and it holds on every model

Each page states MTPLM, Unladen Weight and Payload, and **`MTPLM − unladen == payload` on
all eight**:

| | MTPLM | unladen | payload |
|---|---|---|---|
| Jetstream Twin Sport | 850 | 700 | 150 |
| Jetstream First Class | 850 | 700 | 150 |
| Sunseeker | 750 | 650 | 100 |
| Microlite Discovery | 750 | 600 | 150 |
| Microlite Sport | 750 | 580 | 170 |
| Carpento 360 | 750 | 660 | 90 |
| Wayfarer Quad | 850 | 700 | 150 |
| Wayfarer Duet | 850 | 680 | 170 |

Per [`README.md`](README.md) the derived payload goes in `personal_effects_payload_kilograms`,
with provenance and no value on `optional_equipment_payload_kilograms`.

## Eight models, and FMLV holds five

The site's ranges are **Classic**, **Carpento** and **Wayfarer** — but **FMLV does not use
them.** It files by model family instead, which is the naming to keep:

| FMLV | product_id | on the site |
|---|---|---|
| Jetstream / First Class | 5951 | Classic Range |
| Jetstream / Twin Sport | 5952 | Classic Range |
| Microlite / Discovery | 5953 | Classic Range |
| Microlite / Sport | 5954 | Classic Range |
| Sunseeker / Classic | 5955 | Classic Range |
| — | — | **Carpento 360** |
| — | — | **Wayfarer Quad** |
| — | — | **Wayfarer Duet** |

So the first run should find **three new products and nothing missing**. The Wayfarer range
is badged *"New for 2025"* on the index, which fits.

## Lengths, and which is which

`Overall Length` is the **shipping length including the hitch**; `Body Length` is the
**exterior body**. They differ by more than a metre on the Microlites — 4.00 m against
2.82 m — so there is no risk of reading them the wrong way round, but
[`README.md`](README.md) warns the confusion is the most plausible single mistake in a
caravan adapter. **No internal length is published anywhere**, by any model.

Note `exterior_body_length_mm` is out of automated scope by default. Freedom publishes it
under its own distinct label, which is the case the rule says to **ask** about rather than
assume — as Eriba did on 7 September 2026.

## Two Microlites are pop-tops

Those two pages say **`Height (Roof Down)`** and **`Headroom (Roof Up)`** where the other
six say plain `Height` and `Headroom`. That is a real roof difference and the label is the
only thing that marks it.

**But FMLV marks all five of its rows `type_micro`, not `type_pop_up`**, and the caravan
type columns are single-select — the export's own header says *"SELECT 'YES' AGAINST ONE
'TYPE' PER MODEL IN THIS SECTION"*. Leave that alone; it is a settled choice, and every
Freedom model is under the 1250 kg micro threshold anyway.

## What is missing

- **Berths are not stated on two pages** — Jetstream Twin Sport and Microlite Discovery.
  The other six carry them in the `<title>` (`3 Berth Caravan That's Made For Adventure`).
  FMLV holds 2 for both of the gaps, so nothing is at risk for them; a third model arriving
  without a berth count would be.
- **No internal length**, from any model.
- **No awning length**, and no twin-axle question — all are single-axle.

## First run — #140, 7 October 2026

**8 scraped against 9 baseline: 1 changed, 7 unchanged, 0 new, 1 disappeared**, 3 rows for
review and **117 fields verified unchanged**. Every price, mass and dimension on all eight
models matches FMLV exactly — which is the strongest confirmation available that the model
pages, and not the index, are where FMLV's own figures came from.

The three rows:

| | |
|---|---|
| `Carpento / 360` berths | **4 → 3**, from the page titling itself a *3 Berth Caravan* |
| `Jetstream / Twin Sport` berths | not found this run — FMLV's 2 stands |
| `Microlite / Discovery` berths | not found this run — FMLV's 2 stands |

**The Carpento 360 is a genuine correction.** The page says three berths and lists a double
plus a single, which is three sleeping places; FMLV holds four. Worth a reviewer's eye
rather than a blind accept, but the evidence is on the site's side.

**The one disappearance is `Carpento / 410` (5958)**, which Freedom no longer list — the
requester's "slightly fewer models now". It is a genuine withdrawal, not a rename: no
other model shares its 1000 kg MTPLM or its 5400 mm length.

## The five-versus-nine confusion, for the record

The first pass of this survey said FMLV held five products. It holds **nine** — the
screenshot it was read from showed only the first five rows. The four it missed are
`Carpento / 360`, `Carpento / 410`, `Wayfarer / Quad` and `Wayfarer / Duet`, which changed
the expected first run from *three new* to *none new and one withdrawn*. Count off the
export, never off a screenshot of one.

## The names follow the website

The requester's rule for this brand, 7 October 2026: *"we just match the website for the
names — if they call it the Freedom Sunseeker we'll call it the Freedom Sunseeker. We have
a Classic on it because that's what was there in the past and it must have changed."*

**One product argues with FMLV because of it.** Freedom give the Sunseeker no variant name
— its page is simply `/models/sunseeker/` — where FMLV holds `Sunseeker / Classic`, a name
the site now uses nowhere. So the adapter emits **`Sunseeker / Sunseeker`** and the run
proposes `model: Classic → Sunseeker`.

**Repeating the range is FMLV's own convention for a product with no variant**, not an
invention: counted across every export on disk, **27 rows do exactly this** — Auto-Sleepers
(`Air / Air`, `Burford / Burford`, and seven more), Hymer's `Grand Canyon`, Wingamm,
Wildax, Westfalia, Visiontech and Moto-Trek — and **not one row in any export leaves the
model blank**.

**It reads oddly on purpose, and never reaches a consumer.** Nova requires a brand, a
range and a model and rejects an upload that leaves any of them empty, so a single-named
product carries its name twice; the requester corrects the display name by hand in Nova
after the upload. See the rule in [`README.md`](README.md) — this is a storage shape, not
what the site shows.

**`RENAMED_MODELS` is what keeps it matching.** Without it the correction scores exactly
**0.500** against the row it corrects, which is the default threshold itself — one shared
token of a two-token union. It would match, with no margin whatever, and if it ever
slipped the correction would arrive as a *new product beside a disappearance notice for
the row it was meant to fix*. Declared, it scores 1.000 against the name FMLV holds now
and 1.000 against its own once the fix is accepted, so the entry is safe to leave in place
afterwards.

### Run #141, after the change

**8 scraped against 9 baseline: 2 changed, 6 unchanged, 0 new, 1 disappeared**, 116 fields
verified unchanged. The Sunseeker rename lands on product 5955 as a field change — not as
a new product — which is the whole point of the rename entry.
