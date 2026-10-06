# Bilbo's — survey, and why there is no adapter

**NCC id 1**, `Bilbo's`. Campervans only, converted at South Godstone, Surrey. Contact
**Steve Ayles**, Sales Manager, `Steve@bilbos.com`, 01342 89 24 99.

**No adapter, and not for want of data.** The data is excellent — it is simply not
published. Everything below arrived as email attachments on 6 October 2026 in answer to a
letter, and is recorded here because otherwise it exists only in one inbox.

## The site publishes nothing an adapter could read

`www.bilbos.com` was fetched across `/`, `/bilbos-campervans/`, `/prices/`, `/downloads/`
and `/brochure/`:

| | |
|---|---|
| PDFs linked | **none**, on any page |
| `kg` figures | **none**, on any page |
| prices | only `£39,950`, `£43,950`, `£46,950` on the home page — **used stock** |

The model pages carry photographs and prose. There is no price list, no weights table and
no downloads area. **An adapter would be a hardcoded table with nothing to re-fetch**,
which is worse than no adapter: it would report every figure as confirmed each run while
nobody had re-read the source. Revisit only if Bilbo's start publishing the price list.

## The range, as Bilbo's state it

Steve Ayles, 6 October 2026: *"We have 3 models in the range at the moment Celex, Nexa &
Nexa+ all based on the SWB VW T7. LWB and high top variants not available at the moment.
All have 4 belted seats and can have a roof bed as an option, so standard 2 berth but
could be 2+2 (4 berth)."*

**The site still lists Komba and Space** alongside those three. Both are absent from the
2026 price list and from Steve's range, so the menu is stale — but that is a question for
the requester, not an inference to act on.

## What the two documents hold

*T7 Price list SEPT 2026.pdf*, dated 1 August 2026, and *T7 Dimensions & payload.pdf*,
from **THE BILBO'S T7 HANDBOOK July 2026**.

| | Celex | Nexa | Nexa+ |
|---|---|---|---|
| on-the-road price | **£65,500** | **£65,500** | **£66,300** |
| MTPLM | 3025 | 3025 | 3025 |
| MIRO | 2475 | **2460** | **2460** |
| payload (MUP) | 550 | **565** | **565** |

Shared by all three, SWB with the Low-Lie elevating roof:

| | | |
|---|---|---|
| length | **5050** mm | `5.050 m` |
| width | **2032** mm | `Width – body excluding mirror fittings` |
| height | **2030** mm | `Height – elevating roof – standard suspension` |
| berths | **2** | `2 (+ 2 optional on some models)` |
| travel seats | **4** | Steve's email |
| body type | campervan, elevating roof | 2030 mm, under the 2300 mm threshold |

**Do not take the 2.275 m width.** That is `with mirrors out`, and the rule in
[`README.md`](README.md) excludes mirrors. 2032 mm is the same T7 body width Bespoke's
conversions carry, which is a useful cross-check on both.

**The quoted figures are the base vehicle**, per [`README.md`](README.md): 110 PS,
6-speed manual, Commerce, SWB, standard suspension. The handbook's adjustments are for
optioned variants and are *not* what FMLV records — DSG `+38 kg`, 4MOTION `+97 kg`, LWB
`+70 kg` and `5.304 m` long, lowered suspension up to 30 mm lower, high top `2.540 m`.
The 150 PS weighs the same as the 110 PS.

## Both documents check against themselves

The price list prints the base vehicle and the conversion separately as well as a headline,
so the headline can be rebuilt — and is exact on all three:

| | base vehicle | conversion | built | headline |
|---|---|---|---|---|
| Celex | £36,000 | £29,500 | £65,500 | £65,500 |
| Nexa | £36,000 | £29,500 | £65,500 | £65,500 |
| Nexa+ | £36,000 | £30,300 | £66,300 | £66,300 |

`MTPLM − MIRO == MUP` holds for both columns: `3025 − 2475 = 550`, `3025 − 2460 = 565`.

**One figure does not reconcile.** The handbook breaks MUP into four components. Celex sums
exactly (`181 + 225 + 65 + 79 = 550`); **Nexa/Nexa+ sums to 580 against a stated 565**
(`196 + 225 + 80 + 79`), 15 kg out. The headline trio is self-consistent and is what to
record; the breakdown is where the error is, most likely the `196 kg` for optional
equipment, which would be 181 kg if it matched Celex. Worth putting to Steve.

## Open questions

1. **Are all four belted seats three-point?** Steve says "4 belted seats" without saying
   which. [`README.md`](README.md) counts three-point belts only, so a lap belt in the
   four would change the figure.
2. **Komba and Space**, still on the site but not in the range or the price list.
3. **LWB and high top** are "not available at the moment" — so any FMLV row for one has no
   current product behind it.

## What FMLV holds, and what was issued

The export of 5 October 2026 carries **26 rows**: a superseded block of 13 (`1174`–`1186`,
all archived) and a current block of 13, of which **eight are live**.

| product_id | range / model | |
|---|---|---|
| **5489** | CELEX / SWB - Elevating Roof | **updated** |
| **5493** | NEXA / SWB - Elevating Roof | **updated** |
| **5496** | NEXA+ / SWB - Elevating Roof | **updated** |
| 5491 | CELEX / LWB Elevating roof | LWB not available |
| 5495 | NEXA / LWB Elevating roof | LWB not available |
| 5498 | NEXA+ / LWB Elevating roof | LWB not available |
| 5492 | KOMBA / LWB Elevating roof | not in the range, and LWB |
| 5499 | NEXA / SPACE - SWB - Elevating Roof | not in the range |

The three SWB rows are the only ones Steve's documents cover. The other five have no
current product behind them — a question for the requester, and **not** an archiving one.

The figures FMLV held were the **T6.1** Transporter: `4904 mm` long against the T7's
`5050`, and `2283 mm` wide, which is a mirrors-included figure. Both are superseded.

| | held | issued |
|---|---|---|
| CELEX price / MRO / MTPLM / payload | £59,150 · 2340 · 3000 · 660 | **£65,500 · 2475 · 3025 · 550** |
| NEXA | £59,150 · 2425 · 3000 · 575 | **£65,500 · 2460 · 3025 · 565** |
| NEXA+ | £59,150 · 2425 · 3000 · 575 | **£66,300 · 2460 · 3025 · 565** |
| length / width (all three) | 4904 · 2283 | **5050 · 2032** |

Height `2030`, berths `2` and four travel seats were already right.

**`year` is not written.** The requester updates only the current-year rows and bumps them
into the next year by hand in the export, so writing a year here would pre-empt that.
