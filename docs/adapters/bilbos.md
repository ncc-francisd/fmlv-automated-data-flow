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

Steve Ayles, 6 October 2026: *"Attached are the dimensions & payload and a price list for
the **new VW T7**. We have 3 models in the range at the moment Celex, Nexa & Nexa+ all
based on the SWB VW T7. LWB and high top variants not available at the moment. All have 4
belted seats and can have a roof bed as an option, so standard 2 berth but could be 2+2 (4
berth)."*

**That is a statement about the T7, not about the range.** Read as "Bilbo's now sell three
campervans" it is wrong, and reading it that way is the mistake this paragraph exists to
stop. The website sells **five**, each on one or both wheelbases — nine products:

| | SWB | LWB |
|---|---|---|
| Space | yes | yes |
| Komba | — | **LWB only** |
| Celex | yes | yes |
| Nexa | yes | yes |
| Nexa+ | yes | yes |

**The website is the T6.1 site.** Its title is *"Bilbo's Campervans | **T6.1**, T6 & T5
Volkswagen Campervan Conversions & Sales"*, its range page offers *"a brand new **T6.1**
Volkswagen"*, and its footer reads © 2025. The T7 is named nowhere on it except in the
stock list, which on 6 October 2026 carried **both** — a `VW T7 Bilbos Celex PRO` at
£75,430 and a `VW T6.1 Nexa+` at £65,950.

So Bilbo's are mid-changeover. Komba and Space are **not discontinued**; they are not yet
offered on the new van. What Steve sent describes the T7 range as it stands: three models,
SWB only, LWB and high top still to come.

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
2. **Can a T6.1 still be ordered new?** The site says yes — *"a brand new T6.1
   Volkswagen"* — but its footer reads © 2025. The answer decides whether the eight T6.1
   rows stay live beside the T7 or give way to it.
3. **LWB and high top** are "not available at the moment" — so any FMLV row for one has no
   current product behind it.
4. **What is the LWB's MTPLM?** The handbook gives the LWB its length (`5.304 m`, which
   FMLV already holds), the same width and height, and `LWB versions ... weigh 70kg more
   than the SWB version` — so MIRO is derivable at 2545 (Celex) and 2530 (Nexa/Nexa+).
   **The payload is not**, because the only MTPLM printed is the SWB T30's 3025 and FMLV's
   LWB rows hold 3200, which is the T32. Without the LWB's own MTPLM those rows cannot be
   completed, and the 2032 mm width cannot safely be carried across to them either: every
   SWB row FMLV holds has a length of 4904 mm, which is the **T6.1**, so the LWB rows may
   describe the older van rather than the T7.

## What FMLV holds, and what was issued

The export of 5 October 2026 carries **26 rows**: a superseded block of 13 (`1174`–`1186`,
all archived) and a current block of 13, of which **eight are live**.

| product_id | range / model | |
|---|---|---|
| **5489** | CELEX / SWB - Elevating Roof | **updated** |
| **5493** | NEXA / SWB - Elevating Roof | **updated** |
| **5496** | NEXA+ / SWB - Elevating Roof | **updated** |
| 5491 | CELEX / LWB Elevating roof | T6.1; no T7 LWB yet |
| 5495 | NEXA / LWB Elevating roof | T6.1; no T7 LWB yet |
| 5498 | NEXA+ / LWB Elevating roof | T6.1; no T7 LWB yet |
| 5492 | KOMBA / LWB Elevating roof | T6.1, and Komba is LWB only |
| 5499 | NEXA / SPACE - SWB - Elevating Roof | T6.1; Space is not yet on the T7 |

Those eight rows are the **T6.1** range and they are correct for it — they match the
website's five models across their wheelbases almost exactly. The three SWB rows are the
only ones Steve's T7 documents cover.

**Which raises the question the figures cannot answer.** FMLV's SWB rows are `4904 mm`
long, which is the T6.1; the T7 is `5050`. Writing the T7 figures into them replaces a
product Bilbo's still advertise with a different one, rather than recording the new van
alongside it. The alternative is to add the three T7 models as **new products** and leave
the T6.1 rows alone. That is a decision for the requester — it turns on whether a T6.1 can
still be ordered new, which the site implies and the changeover makes doubtful.

| | held | issued |
|---|---|---|
| CELEX price / MRO / MTPLM / payload | £59,150 · 2340 · 3000 · 660 | **£65,500 · 2475 · 3025 · 550** |
| NEXA | £59,150 · 2425 · 3000 · 575 | **£65,500 · 2460 · 3025 · 565** |
| NEXA+ | £59,150 · 2425 · 3000 · 575 | **£66,300 · 2460 · 3025 · 565** |
| length / width (all three) | 4904 · 2283 | **5050 · 2032** |

Height `2030`, berths `2` and four travel seats were already right.

**`year` is not written.** The requester updates only the current-year rows and bumps them
into the next year by hand in the export, so writing a year here would pre-empt that.
