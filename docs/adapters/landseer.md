# Landseer — survey, 10 November 2026

**NCC id 249**, `Landseer`. Campervans only, converted at Brindle Store, Bournes Row,
Hoghton, Lancashire PR5 0DR — `01772 429763`, `info@landseerleisure.com`. The site carries
a news page announcing that Landseer have joined the NCC as an approved manufacturer
member, so this is a new member rather than a long-standing one.

**Stage 1 only. No adapter has been written.**

## What was asked

The requester reported that FMLV holds **two** `Custom 2.0` campervans, that the site now
shows something called an **Artemis**, and that he could see only **one** Custom 2.0 — with
the explicit instruction to watch for a rename rather than a new model.

**It is not a rename, and the arithmetic of two-versus-one has a dull answer.**

* The **Artemis is a MAN TGE**. The Custom 2.0 is a Ford Transit Custom. Different base
  vehicle, different price class — £106,900 against £76,000–£94,000 — and a separate
  brochure with its own print job number. Nothing has been renamed into anything.
* **One page covers both wheelbases.** `/campervans/ford-custom-landseer` is a single page
  whose price list sells the Custom in SWB *and* LWB. So the site shows one *page* where
  FMLV holds two *products*. Counting pages against products is what produced the
  discrepancy; see `docs/adapters/README.md` on a claimed-new count needing checking
  against what disappeared.

The sitemap confirms there is no third model page.

## The site publishes two PDFs and finds them the way RS Motorhomes did

`landseerleisure.com` is WordPress (Yoast, Elementor). The nav links exactly two model
pages, and the model pages themselves carry almost no figures — the Artemis page is prose
from end to end. **Everything numeric is in two 4pp A4 PDFs**, and both were found through
the site's own media library:

```
/wp-json/wp/v2/media?per_page=100&media_type=application
```

Ten documents, of which eight are superseded editions going back to August 2024:

| date | title |
|---|---|
| **2026-10-12** | **57688 Landseer Custom 2.0 2026 4pp Pricing A4** |
| **2026-10-12** | **57682 Landseer Artemis 4pp A4 (1)** |
| 2026-08-21 | 57682 Landseer Artemis 4pp A4-1 |
| 2026-08-21 | 57688 Landseer Custom 2.0 2026 4pp Pricing A4 |
| 2026-06-11 | 57688 Landseer 2026 4pp Pricing A4 |
| 2026-06-11 | 57682 Landseer Artemis 4pp A4 |
| 2025-12-26 | 56143 Landseer 2026 4pp Pricing A4 Inner |
| 2025-02-05 | 54582 Landseer 2024-25 4pp A4 |
| 2024-11-29 | 54120 Landseer 2024-25 4pp A4 |
| 2024-08-21 | Landseer Custom 2.0 – 2025 – Retail Pricing |

**The filename repeats across editions.** `57682-Landseer-Artemis-4pp-A4-1.pdf` exists
under `/2026/10/` *and* under `/2026/08/`, byte-identical in name and different in content.
So the rule already written up for RS Motorhomes applies here with teeth: **take the date
from the listing, never from the path**, and never hardcode a URL.

The five-digit prefix is a print job number and is stable: **57688 is the Custom pricing,
57682 is the Artemis**. That is a better key than the title, which has changed wording
three times in fifteen months.

## The two documents are not equals

### The Custom 2.0 sheet is a real price list

Quoted verbatim from the 2026-10-12 edition, headed *"2027 Landseer Custom 2.0"*:

```
Model options - 2027 Season Pricing OTR* (inc VAT)
2027 Landseer Custom 2.0 - 150ps 6 Speed Manual (SWB)          £76,000
2027 Landseer Custom 2.0 - 170ps 8 Speed Automatic (SWB)       £79,950
2027 Landseer Custom 2.5 - PHEV 232ps 1 Speed Automatic (SWB)  £89,000
2027 Landseer Custom 2.0 - 150ps 6 Speed Manual (LWB)          £81,000
2027 Landseer Custom 2.0 - 170ps 8 Speed Automatic (LWB)       £84,950
2027 Landseer Custom 2.5 - PHEV 232ps 1 Speed Automatic (LWB)  £94,000
2027 Landseer Custom 2.0/2.5 - Leighton LV-RF™ Edition    Additional £7,000

Dimensions - SWB 5.05m long, LWB 5.45m long, 2.15m wide (mirrors folded), 2.07m high
Maximum GVW SWB 3175kg, LWB 3225kg
Mobiframe SAF43 "any-locking position" sliding rear seat and bed system
 - with 3 x 3-point safety belts. ISOFIX & top tether system
 - 5 travelling seats (upgradable to 7) / 6' 4" bed. Fully crash-tested and M1 Approved
*NEW* SCA "pop-top" roof system, with integrated roof bed (froli sprung) - 6'5" bed
Webasto AirTop diesel heater with multi-function smart controller
Webasto Isotherm 42L 'Cruise Elegance' refrigerator with freezer compartment
```

The price basis is stated and is FMLV's: *"OTR = Registered 'on the road' and with 1 year's
VED included"*.

That one page carries the price, the MTPLM, all three dimensions, the travel seats with
their belt type named, both beds, the heating and the refrigeration.

### The Artemis brochure is a brochure

The 2026-10-12 edition, headed *"2027 Landseer Artemis"*, carries:

* `LAUNCH PRICING £106,900 inc. VAT`
* `MAN TGE Brand New, High Specification MAN TGE 3.180 (see full details on our website)`
* `YAKKT - PRO Roof Rack: MWB MAN TGE/VW Crafter`
* a long options list — `Pop-Top for MWB MAN TGE (including bed and mattress) £9,200`,
  `Mobiframe RAM03 Dual Seat with Seat Belts incorporated (4-seat campervan) £3,500`

and **no mass, no dimensions and no berth count anywhere**. Its model page adds nothing:
79 displayed lines, all prose, and the only `kg` on it is a towing capacity.

## The gaps, and they are not small

| field | Custom 2.0 | Artemis |
|---|---|---|
| price | ✓ £76,000 / £81,000 | ✓ £106,900 |
| MTPLM | ✓ 3175 / 3225 | ✗ |
| **MIRO** | ✗ | ✗ |
| **payload** | ✗ | ✗ |
| length | ✓ 5050 / 5450 | ✗ |
| width | **qualified** | ✗ |
| height | ✓ 2070 | ✗ |
| seats | ✓ 5 | option list only |
| berths | ✓ 2 + 2 | ✗ |

**No mass in running order and no payload is published for anything**, only a GVW. That is
two required fields blank on every product — which does not block an upload (FMLV holds
live rows with both blank) but does mean no payload arithmetic exists to check a parse
against.

**Width is published only as `2.15m wide (mirrors folded)`.** The cross-manufacturer rule
excludes mirrors, and mirrors *folded* is not the body width — a Transit Custom's body is
narrower than 2150mm. Murvi's sheet had the same shape and FMLV held the body width rather
than the printed one. **This must be resolved before any width is recorded**; recording
2150 would be recording the wrong quantity, not merely an imprecise one.

## The self-check is the price grid, not the masses

There is no `payload == MTPLM - MIRO` to lean on. What the price list does offer is a
**rectangle that has to close**:

| | SWB | LWB | difference |
|---|---|---|---|
| 150ps manual | £76,000 | £81,000 | **£5,000** |
| 170ps automatic | £79,950 | £84,950 | **£5,000** |
| 2.5 PHEV | £89,000 | £94,000 | **£5,000** |
| manual → automatic | **£3,950** | **£3,950** | |

Six figures, two constants, and every one agrees. A misread cell, a dropped row or a
column shifted by one breaks it immediately. It is weaker than mass arithmetic because it
checks the *price* parse alone, but it is a genuine redundancy the manufacturer published
against itself, and the lengths and GVWs differing consistently between the two wheelbases
is a second, coarser one.

## How many products

The price list sells six lines; FMLV holds two. The six are three drivetrains across two
wheelbases, and the drivetrains are not all equal:

* **SWB and LWB are different vehicles** — different length and different GVW. Two
  products at least.
* **The automatic is an option on a manual base**, £3,950 either way. On the settled rule
  that an automatic offered as an option is still a `Yes`, that is `automatic_available`
  and not a second product; the recorded price is the manual's £76,000 / £81,000.
* **The 2.5 PHEV is a different model name**, a different engine and £13,000 more. Whether
  that is a product or a variant is the requester's call.
* **The Leighton LV-RF Edition is an option** — one price, £7,000, on either vehicle, which
  is the signature of an option rather than a model.

So the count is **three** (Custom 2.0 SWB, Custom 2.0 LWB, Artemis) or **five** if the PHEV
is split out. FMLV's existing two are most likely the Custom 2.0 SWB and LWB, but no export
has ever been downloaded for this manufacturer, so that is inference rather than fact.

## Body type

**Not a high top.** The Custom 2.0 is 2.07m high with an SCA pop-top, so it is a campervan
with an **elevating roof**, well under the 2300mm threshold. The Artemis's height is not
published; its pop-top is a £9,200 *option*, which implies a fixed roof as standard, but
that is an inference and the figure is missing, so the Artemis body type cannot be derived
and must stay blank.

## What is unverified

1. **`ncc_supplier_name` and `fmlv_manufacturer`.** Both are `Landseer`, taken from
   `resources/manufacturers-full-list.csv` id 249. Neither has been checked against the NCC
   export dropdown or an FMLV export.
2. **What FMLV's two rows are actually called**, which decides whether an adapter matches
   them or proposes everything as new.
3. **The Artemis's dimensions and masses**, which the manufacturer publishes nowhere.
4. **The body width**, as above.

Items 3 and 4 are a letter to Landseer. They are an NCC member, which usually makes that a
short conversation.
