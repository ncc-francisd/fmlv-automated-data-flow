# T@B (Knaus Tabbert AG T@B, id 141)

Surveyed 2026-09-19. **Caravans only**, and the whole brand is five products.

Fourth Knaus Tabbert row in FMLV, alongside Knaus (96), Weinsberg (252 and 112) and
Morelo (46). Each is a separate FMLV row with its own adapter and its own site; nothing
here is shared with them except the corporate habit described under *Payload* below.

- Source: <https://www.tabme.de/en/>
- NCC supplier name: `T@B`
- `fmlv_manufacturer`: `Knaus Tabbert AG T@B`

## What the requester supplied

Given on 2026-09-19, and every figure checked against the site:

- Three models, a specific kind of caravan the brand calls a **micro**, under 1200 kg.
- The weights have "slightly different names for the three weights we need". For the 320:
  MTPLM 800 kg ("Tecnically maximum authorized laden mass"), MRO 653 kg ("Mass in ready
  to travel condition"), payload 147 kg.
- **The trap:** the site states a maximum payload of 57 kg for the 320, but that is an
  assumption based on full gas cylinders and full water tanks. The figure to record is the
  arithmetic one.

All three weights and the trap are confirmed exactly. Two parts of the brief turned out
to need adjusting, and both are set out below: the roster is **five products, not three**,
and the word *micro* does not appear on the site.

## Where the data lives

Static HTML, no JavaScript, no PDF. The only `CATALOGUE` link on the site goes to
`shop.tabme.de`, which sells T@B merchandise; every `/downloads/` path 404s. The page
text says "You can also find all the information here as a PDF file to download!" but the
link behind it no longer exists.

Each layout has a `Technical data` table in plain markup:

```
Technical data
320
Overall length in cm                                517
Usable length in cm                                 398
Overall Width / interior width in cm            201 / 180
Overall height / interieur height in cm         244 / 182
Mass of unladen vehicle, approx. in kg*             620
Mass in ready to travel condition, approx. in kg*   653
Tecnically maximum authorized laden mass (kg)**     800
Maximum payload, approx. in kg*                      57
Number of beds                                 up to  2
```

Three spec pages carry it: `/en/320/`, `/en/400/`, `/en/320-offroad/`.

## The roster is five, not three

`/en/models/basic/`, `/en/models/metropolis/` and `/en/models/offroad/` are **styles, not
ranges of their own**, and they do not have spec pages. Basic and Metropolis *both* link
the same `/en/320/` and `/en/400/`; Offroad links `/en/320-offroad/`.

FMLV's own identity confirms the shape: `manufacturer_range` is the style and `model` is
the number — `Basic` / `320`, `Metropolis` / `400`.

Each spec page carries an **`AVAILABLE STYLES`** panel naming the styles that layout is
sold in, each with its own price:

| page | available styles |
|---|---|
| `/en/320/` | BASIC 14.990, METROPOLIS 16.380, OFFROAD 18.490 |
| `/en/400/` | BASIC 13.990, METROPOLIS 15.380 |
| `/en/320-offroad/` | *(none — it is the 320's OFFROAD style, reached by "GO TO 320 OFFROAD")* |

So the roster is the product of the two, and it matches FMLV's five live rows exactly:

| range (style) | model | specs from | FMLV product |
|---|---|---|---|
| Basic | 320 | `/en/320/` | 5754 |
| Metropolis | 320 | `/en/320/` | 5758 |
| Offroad | 320 | `/en/320-offroad/` | 5760 |
| Basic | 400 | `/en/400/` | 5755 |
| Metropolis | 400 | `/en/400/` | 5759 |

**Only one technical table is published per spec page**, so Basic/320 and Metropolis/320
necessarily receive the same figures, as do Basic/400 and Metropolis/400. The site
publishes no per-style weights.

## The baseline

The export holds 23 rows, but `_is_current_model_year` keeps only the five above: the rest
are 2022, 2023 and 2024, and all but two are archived. Two things follow.

**`Mexican Sunset` is a retired style.** It is a `manufacturer_range` on six baseline rows,
all 2022/2023 and all archived, and it appears once on each current page as a historical
mention only. It is not in any `AVAILABLE STYLES` panel. Because the year filter drops
those rows before the diff, its absence raises no disappearance notice and needs no action.

**Two rows have a range that is a number.** Products 7552 (`320`/`RS`) and 7553 (`450`/`L`)
invert the convention — the range holds the model number and the model holds a letter. Both
are 2024 and are dropped by the year filter. 7553 is *not* archived, so if the year filter
ever loosens it would reappear as an unmatched row; it is not on the current site.

## The self-check

Every page states its MTPLM twice. The `Technical data` row is restated by a
**`Load increase to N kg`** line in the equipment list, and the two agree on all three
pages:

| page | MTPLM in the table | standard `Load increase` | optional load increases |
|---|---|---|---|
| `/en/320/` | 800 | **800** (850 kg chassis) | 850, 1000 |
| `/en/400/` | 1200 | **1200** (1300 kg chassis) | 1500, 1300, 1400 |
| `/en/320-offroad/` | 1000 | **1000** (1000 kg chassis) | — |

This is a genuine redundancy rather than a restatement of the same parse: the two figures
sit in different sections of the page, in different markup, hundreds of lines apart.

It also settles which figure is the base vehicle. The load increase that matches the table
is in **`Standard Equipment`**; the larger ones are under **`Optional equipment` /
`Packages`**. So the table's MTPLM is the vehicle as sold, and the bigger chassis is a paid
upgrade — the same shape as the settled base-vehicle rule, and the reason the 320 reads
800 rather than its 750 kg bare chassis.

## Traps

**The published `Maximum payload` is not the payload.** Confirmed on all three pages:

| model | MTPLM | MRO | site "Maximum payload" | MTPLM − MRO |
|---|---|---|---|---|
| 320 | 800 | 653 | 57 | **147** |
| 400 | 1200 | 986 | 106 | **214** |
| 320 Offroad | 1000 | 708 | 202 | **292** |

This is the same trap the two sibling adapters already record — `knaus.py` ("Maximum
payload / Remaining payload are homologation figures reconciling with nothing; SKY TI
650 MEG says 8 kg") and `weinsberg.py` ("CaraCore 700 MEG prints 18 kg"). It is a Knaus
Tabbert house habit, not a T@B quirk.

**Three masses are published and only the middle one is the MRO.** `Mass of unladen
vehicle` (320: 620), `Mass in ready to travel condition` (653 — this one), `Tecnically
maximum authorized laden mass` (800, the MTPLM). Note the site misspells *Technically*;
match it as published.

**The summary card lies about the mass.** Above the table each page repeats length, width,
beds and a bare `Mass`, and that `Mass` is the *unladen* figure (320: 620), not the MRO.
Read the table, never the card.

**Mixed thousands separators in one document.** The table and the standard equipment line
use German dots (`1.200`), while the optional equipment lines use English commas
(`1,000 kg`). Both appear on the same page.

**Dimensions are cm**, so multiply by 10, and widths and heights are published as
`overall / interior` pairs in a single cell — take the first.

**Berths read `up to N`** on a line of their own below the label.

## Field mapping

| site | FMLV | 320 check |
|---|---|---|
| Overall length in cm | `shipping_length_mm` | 517 → 5170 ✓ |
| Overall Width (first of the pair) | `overall_width_mm` | 201 → 2010 ✓ |
| Overall height (first of the pair) | `height_mm` | 244 → 2440 ✓ |
| interieur height (second of the pair) | `headroom_mm` | 182 → 1820 ✓ |
| Mass in ready to travel condition | `mro_kilograms` | 653 |
| Tecnically maximum authorized laden mass | `mtplm_kilograms` | 800 |
| Number of beds | `berths` | 2 |

`Usable length` is **not** FMLV's `internal_length_mm`: the site says 398 cm where FMLV
holds 3400 mm, and FMLV's `exterior_body_length_mm` (4400) is published nowhere. Neither
of those two length columns can be sourced from this site, and both are left alone.

## Decisions taken, and what is still open

**Payload conflicts with the cross-manufacturer rule.** `docs/adapters/README.md` says for
caravans that `personal_effects_payload_kilograms` "is *not* MTPLM minus MRO but the
personal-effects half of a split, and one published figure may be the total. Deriving it
would be wrong." T@B's baseline says the opposite: **all 23 rows hold
`personal_effects_payload_kilograms` exactly equal to MTPLM − MRO**, with no
`optional_equipment_payload_kilograms` anywhere, and the requester's instruction is to
record 147 for the 320. Recommendation: derive it here, because FMLV's own data for this
brand is unambiguous, and record the exception rather than changing the general rule.

**Prices: the English edition drops the headline, and one panel is stale.** Two figures
are published and they are not equally trustworthy. The **German** page carries a headline
`Listenpreis ab` at the top; the **English** page does not carry it at all, having only an
`AVAILABLE STYLES` panel with a `List price from` per style.

| page | German headline | `AVAILABLE STYLES` panel |
|---|---|---|
| `/320/` | 14.990 | BASIC 14.990, METROPOLIS 16.380, OFFROAD 18.490 |
| `/400/` | **24.390** | BASIC 13.990, METROPOLIS 15.380 |
| `/320-offroad/` | 18.490 | *(no panel)* |

On the 320 the two agree exactly. On the 400 the panel is 74% under its own headline — and
under the *smaller* 320 at that — it is undated where the 320's carries `(08/2026)`, and
FMLV's own GBP 24,970 and GBP 24,394 side with the headline. So a panel is trusted **only
when its base style's price equals the page's own headline**, and is otherwise discarded
whole rather than half-trusted. Metropolis 400 therefore gets no price at all.

Offroad/320 is the one product with two independent price statements that agree: the 320
panel's OFFROAD entry and the 320-offroad page's own headline are both 18.490.

**The rate is 1.15 euros per pound**, chosen by the requester on 2026-09-19 "like we've
done on some of the other brands", so a euro figure is **divided** by it.
`morelo.EUR_TO_GBP_RATE` is the same judgement the other way up — 0.855 pounds per euro,
which is 1/1.1696. The two are close but not equal and neither is a typo of the other.

Worth a reviewer's eye, and stated in every price's provenance: this converts a **German
domestic list price including 19% German VAT**, which is not a UK on-the-road price. Every
converted figure lands below what FMLV already holds, which is what a home-market price at
spot rate does.

## Body type is deliberately not emitted

The requester states these are micros and FMLV holds `type_micro` on all 23 baseline rows.
The settled rule needs the manufacturer's own naming **as well as** MTPLM of 1250 kg or
lower, and the naming is absent: *micro* appears zero times on tabme.de in English and in
German, and zero times on knaustabbert.de.

All five products match rows that already hold `type_micro`, so emitting nothing leaves it
standing. Asserting `type_rigid` — the usual answer — would propose downgrading five rows
that are already correct, which is `wingamm_caravan.py`'s mistake in reverse. Note the 400
is exactly 1200 kg, on the line the requester quoted ("under 1200") but inside the settled
1250.

## First run — #105, 2026-09-19

5 scraped against 5 baseline, **5 matched, 0 new, 0 disappeared**, which is the roster
reading confirmed. 33 proposals and 42 fields verified unchanged.

| product | MTPLM | MRO | payload | price |
|---|---|---|---|---|
| Basic 320 | 750 -> **800** | 655 -> 653 | 95 -> **147** | GBP 16,990 -> 13,035 |
| Metropolis 320 | 800 *(unchanged)* | 655 -> 653 | 145 -> 147 | GBP 15,460 -> 14,243 |
| Basic 400 | 1200 *(unchanged)* | 980 -> 986 | 220 -> 214 | GBP 24,970 -> 21,209 |
| Metropolis 400 | 1200 *(unchanged)* | 990 -> 986 | 210 -> 214 | *no price proposed* |
| Offroad 320 | 850 -> **1000** | 690 -> 708 | 160 -> **292** | GBP 20,830 -> 16,078 |

Basic 320's 147 kg is the requester's own figure, reached independently. Its MTPLM rises to
800 because the load increase to 800 kg is in the page's standard equipment; Metropolis 320
already held 800, and that row verifying unchanged is a useful cross-check on the other.

Offroad 320 also gains 50 mm of height (2440 -> 2490), which its own page states.

The 11 "in-scope fields not found this run" are the five `body_type` and five
`internal_length_mm` no-ops described above, plus Metropolis 400's price.

## Fetches per run

Six: three model pages to establish which styles exist, and three spec pages. The model
pages could be skipped if the style-to-layout mapping were hardcoded, but reading the
`AVAILABLE STYLES` panel is what makes a style being added or dropped visible.
