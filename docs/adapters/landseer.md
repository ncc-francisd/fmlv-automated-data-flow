# Landseer — survey and adapter

**Surveyed and built 10 November 2026.** The adapter is `src/adapters/landseer.py`.

**NCC id 249.** Campervans only, converted at Brindle Store, Bournes Row, Hoghton,
Lancashire PR5 0DR — `01772 429763`, `info@landseerleisure.com`. The site carries a news
page announcing that Landseer have joined the NCC as an approved manufacturer member, so
this is a new member rather than a long-standing one.

**The two names are different and must not be crossed.** FMLV’s export spells the
`manufacturer` column **`Landseer`**, one word — confirmed against the export of
10 November 2026. The NCC supplier dropdown spells it **`Landseer Leisure`**, two words,
confirmed by the requester the same day. The first is `fmlv_manufacturer` and the
adapter’s `MANUFACTURER`; the second is `ncc_supplier_name` and nothing else.

| | Landseer |
|---|---|
| JavaScript needed | No |
| Products | **5** — Custom 2.0 SWB/LWB, Custom 2.5 PHEV SWB/LWB, Artemis |
| Fetches | 1 index + 1 media listing + 2 PDFs |
| Price | **In both PDFs**, on-the-road including one year’s VED |
| Berths | **Never published, for anything** |
| Weights | **GVW only. No mass in running order and no payload, in any of ten editions** |
| Dimensions | Custom only, and the width is qualified `(mirrors folded)` |
| Self-check | **The price grid**, not mass arithmetic — plus seats against belts |

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

## Built, 10 November 2026 — and the first run against the real export

The requester supplied the NCC supplier name (`Landseer Leisure`) and both FMLV exports —
one of current products, one of everything ever loaded. **They are byte-identical**, so
nothing has ever been deactivated here and the relisting trap does not apply. FMLV holds
exactly two products, `8421` and `8422`, as range `Custom 2.0` with the wheelbase as the
model. The adapter matches both.

Run #218 compared five scraped products against that baseline: **2 changed, 3 new, 0
disappeared**, which is the shape a correct first run has.

### What the run found on the two products FMLV already holds

| | FMLV held | Landseer publish |
|---|---|---|
| Custom 2.0 SWB price | £77,900 | **£76,000** |
| Custom 2.0 LWB price | £81,400 | **£81,000** |
| Custom 2.0 LWB automatic price | £85,950 | **£84,950** |
| Custom 2.0 SWB automatic price | £79,950 | £79,950 — unchanged |

**The two automatic prices FMLV holds are the 2026-season figures, exactly.** The December
2025 and June 2026 editions both print £79,950 and £85,950, and the LWB's has since moved
to £84,950. The two *manual* prices FMLV holds match **no edition Landseer have ever
published**: every edition back to December 2025 prints £76,000 for the short wheelbase,
and £82,000 then £81,000 for the long one. £77,900 and £81,400 come from somewhere else.

### `automatic.rrp_pounds`, populated for the first time

No adapter before this one has written that column. The field guide reserves it for a
model offered with an automatic, and until now no surveyed manufacturer published a
separate price for one — Landseer print it as its own line on every wheelbase. The PHEV is
a 1-speed automatic with no manual at all, so its automatic price is its only price, and
it is recorded in both columns so the product reaches FMLV's automatic filter.

The automatic *mass* columns stay blank, because no automatic weight is published either.

### The Custom has no washroom as standard

The rear shower attachment is £240 and the Thetford porta toilet £100, both in the options
list, and the rear awning "creating privacy/shower/toilet area" is price on application.
So the vehicle as built has neither — yet **both of FMLV's existing Custom 2.0 rows carry
`rear_shower_toilet`**. The adapter cannot propose that away, because silence about a
washroom is not a statement that there is none, so it narrates the three option lines on
every run instead. The Artemis, by contrast, has a real shower room as standard.

### What the habitation module cannot read here

`habitation.bed_types_from` drops any line containing the word `mattress` — a sound rule
against "bed linen and mattresses" copy, which here costs the Artemis its shape, because
its only statement of one is *"Custom Design Premium Memory Foam Mattress – 6' 5"
Transverse Bed"*. Loosening that filter would reach seventy adapters, so the adapter
quotes the bed lines into the run narration instead. Bed types are a finding a person
types in, so the sentence in front of them is what the field actually needs.

## Still open

1. **A mass in running order and a payload, per model.** Landseer have never published
   either, in any of ten editions, for anything. FMLV's own 2,400kg / 2,450kg and 775kg on
   the two Custom rows have no Landseer document behind them and no known source; the
   adapter leaves them alone rather than blanking them.
2. **The body width excluding mirrors.** `2.15m wide (mirrors folded)` is their only
   published width, and it is recorded as stated with their wording mirrored — which is
   also what FMLV already holds. A Transit Custom's body is narrower than 2,150mm.
3. **The Artemis's height, length, width, GVW and berth count**, none of which exist
   anywhere. Its height is what blocks a body type.
4. **Whether the Artemis's standard bench has three-point belts**, and how many travel
   seats that makes. The brochure says `2 travel positions, see options for 4 positions`
   and names a belt type only on the £3,500 option.
5. **Whether the PHEV has its own GVW.** The sheet states one pair for the whole document
   and a PHEV is the heavier vehicle, so the figure recorded for it is Landseer's own
   published number rather than one measured for that engine. The provenance says so.
6. **Berths**, which are published for nothing. FMLV holds 4 on both Customs; the Artemis
   is a single fixed transverse bed.

All six are a letter to Landseer. They are an NCC member, which usually makes that a short
conversation.
