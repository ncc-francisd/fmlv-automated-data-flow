# SUN LIVING (id 27)

Surveyed 2026-09-22. Adria Mobil's own sub-brand, and **the site is literally Adria's
machinery**: the same Laravel+Livewire range pages, the same scroll-triggered
`/livewire/update` call, the same per-configuration technical-data PDF.

- Source: <https://www.sun-living.co.uk/>
- NCC supplier name: `SUN LIVING`
- `fmlv_manufacturer`: `SUN LIVING` — capitals in both, as the requester said, and only
  one candidate row in the full list, so no ambiguity to resolve.

## The one change needed to `adria.py`

`technical_data_pdf_url` derives the market and period from each product's
`configuratorURL` but **hardcodes the host** as `configure.adria-mobil.com`. Sun Living's
configurator lives at `configure.sun-living.com`, so every one of the ten PDFs 404s.

Deriving the host from the same URL that already supplies the market and period fixes it,
and all ten then fetch — the requester independently supplied
`https://configure.sun-living.com/gb/25-26/100351-2526-fkle-fk300s031-11/pdf`, which is
exactly what the corrected helper builds for the C 70DL.

Worth saying plainly: **the 404 was nearly a wrong conclusion.** On the first pass the C
70DL looked like a model with no technical data at all, which fitted its £0.00 price and
the "in transition" theory. It has a full PDF.

Everything else transfers unchanged — `parse_livewire_products`, `parse_technical_data_pdf`,
`pdf_title`, `pdf_describes_layout` and `parse_base_vehicle_manufacturer` all read a Sun
Living document correctly, including the `(WITHOUT ALL INC' PACK)` qualifier.

## The roster: four ranges, ten configurations

| range | path | configurations |
|---|---|---|
| A Series | `/motorhomes/a-series` | A 70DK |
| C Series | `/motorhomes/c-series` | C 70DL |
| S Series | `/motorhomes/s-series` | S 72DC, S 72DL, S 75SL |
| V Series | `/campervans/v-series` | V 55SP ×2, V 60SP, V 65GX, V 65SL |

Against FMLV's eight live rows that is **8 matched, 2 new** (C 70DL and V 65GX) and
nothing disappearing.

## The weights are the base ones, and FMLV already agrees

Every PDF states the mass in running order as
`Mass in running order (MIRO-min, kg) 3002 (WITHOUT ALL INC' PACK)`. The requester's
ruling, 22 September 2026:

> *"use the weights quoted which say excluding the supplementary all-inclusive pack …
> the customer can discuss that if they want the all-inclusive pack, we're doing the base
> level"*

That is the settled base-vehicle rule, and FMLV's own figures confirm it is already what
it holds: the S 72DC's 3002 matches to the kilogram. Payload is `MTPLM − MiRO` — the
requester's formula — and it reconciles with FMLV on seven of the eight live rows.

## What the ten PDFs say against FMLV

| configuration | berths | seats | MTPLM | MiRO | price | against FMLV |
|---|---|---|---|---|---|---|
| A 70DK | 6 | 4 | 3500 | 2994 | £71,990 | MiRO 3000, seats 6, price £74,130 |
| C 70DL | 2 | 4 | 3500 | 2763 | **£0.00** | **new** |
| S 72DC | 4 | 4 | 3500 | 3002 | £69,995 | price £72,130 |
| S 72DL | 4 | 4 | 3500 | 2992 | £69,995 | berths 5, price £72,130 |
| S 75SL | 4 | 4 | 3500 | 2983 | **none** | berths 5 |
| V 55SP StdF | 2 | 4 | 3500 | 2674 | £57,995 | MiRO 2794, price £69,835 |
| V 55SP TentTop | 4 | 4 | 3500 | 2794 | £61,995 | price £72,235 |
| V 60SP | 2 | 4 | 3500 | 2769 | £59,995 | price £66,690 |
| V 65GX | 2 | 4 | 3500 | 2798 | £62,995 | **new** |
| V 65SL | 2 | 4 | 3500 | 2854 | £61,995 | berths 3, price £68,410 |

Dimensions match FMLV exactly on every matched row.

### Prices are lower across the board

Every published price is below FMLV's, and on the three motorhomes by an almost identical
amount — **£2,135, £2,135 and £2,140**. The campervans drop further and less evenly:
£6,415 to £11,840. Under the settled rule the UK site's own headline price is what FMLV
should match, so these are what to record, but the size of the campervan gap is worth a
look before accepting.

**Two have no price at all**: the C 70DL publishes `£0.00` and the S 75SL publishes
nothing. Neither is recorded — a zero is not a price, and inventing one is exactly what
the "never invent a POA" rule forbids.

### Seats read 4 on all ten

The PDFs state `Max number of homologated seats (incl. driver's seat) 4 (ADDINIG OPTIONS
MAY REDUCE)` — Sun Living's own typo — for every configuration, where FMLV holds 4, 5 and
6 across its rows.

FMLV's figures look copied from the berths: on the archived 2022 rows, seats equals berths
on the A 70DK (7/7), the 75 DP (6/6) and the S 70 DF (6/6), which is the signature of a
column filled from its neighbour. The live A 70DK holds 6 seats and 6 berths.

Four is the manufacturer's own homologation figure, stated per configuration in a document
that names the vehicle in its own title. Recommendation: propose it.

## The answer: the trim goes in the model

The requester chose it on 22 September 2026 — *"can we not include the words TentTop in
the model name, so it would become the V Series, that's the range, 55SP TentTop being the
model"*. So the model is the layout label plus whatever the trim says beyond the
right-hand-drive boilerplate: `V 55SP` and `V 55SP TentTop`.

The boilerplate is **subtracted** rather than the interesting words listed, so a future
`Sport` or `Elevating Roof` carries across without a code change.

### One FMLV edit is needed before the run

`_dedupe_baseline` collapses identically-named rows **before** matching, and FMLV holds
both V 55SPs under that one name. Simulated against the real matcher:

| | as FMLV stands | with 7945 renamed |
|---|---|---|
| `V 55SP` | → **7945**, the 4-berth row | → 7946 ✓ |
| `V 55SP TentTop` | → **new** | → 7945 ✓ |
| product 7946 | **silently discarded**, no notice | matched |

So as it stands the run rewrites the 4-berth row as the 2-berth caravan, creates a third
product, and leaves 7946 orphaned without even a disappearance notice. **Renaming product
7945's model to `V 55SP TentTop`** — it is the 4-berth, £72,235 one — makes both match
exactly. The pipeline says so itself on every run:

> *BASELINE DUPLICATE: FMLV holds V Series V 55SP twice … If both are current vehicles,
> give them different model names in FMLV so each can be matched.*

## Body type is derived per range, and FMLV's V 55SP pair is transposed

Every range is internally consistent in FMLV across live *and* archived rows, so the style
is derived rather than asserted as one constant:

| range | body type |
|---|---|
| A Series | coach built, over-cab bed *(requester confirmed)* |
| C Series | coach built, low profile |
| S Series | coach built, low profile |
| V Series | campervan, high top |

The exception is the **V 55SP pair, which FMLV holds the wrong way round**: plain
`high_top` on the TentTop and `high_top_elevating_roof` on the base. The TentTop is the one
with the roof bed -- its own name says so and it sleeps four where the base sleeps two --
so the run proposes a swap, and the provenance explains it as one correction rather than
two unrelated ones. It is the predictable result of two rows sharing a model name: an edit
lands on whichever the editor opened.

The first run asserted `campervan_high_top` for the whole V Series, which quietly proposed
downgrading the base. Deriving it caught that.

## First run — #119, 2026-09-22

All ten configurations collected. **7 changed, 3 new, 0 disappeared**, 70 fields verified.

The three "new" are the C 70DL, the V 65GX and the V 55SP TentTop — the last only because
the base V 55SP took 7945's id. After the rename it should be **8 matched, 2 new**.

The substantive changes:

| | proposed |
|---|---|
| A 70DK | seats 6 → 4, payload 816 → 506, MiRO 3000 → 2994, price £74,130 → £71,990 |
| S 72DC | price £72,130 → £69,995 |
| S 72DL | berths 5 → 4, price £72,130 → £69,995 |
| S 75SL | berths 5 → 4, seats 5 → 4 |
| V 55SP | *(matched the wrong row — see above)* |
| V 60SP | price £66,690 → £59,995 |
| V 65SL | berths 3 → 2, price £68,410 → £61,995 |

Dimensions verified unchanged on every matched row, which is the strongest signal the
parse is right.
