# Rolling Homes — survey, 9 October 2026

**NCC id 70.** `fmlv_manufacturer` **`Rolling Homes`**, display name `Rolling Homes`,
supplier name `Rolling Homes` — all three identical. A family campervan converter in
Shrewsbury. No adapter yet; this is the stage-1 checkpoint.

They convert VW vans (one Ford, one Mercedes historically), register every build as a
Motorcaravan, and hold NCC Approved Workshop status and a place on the VW Van Converter
scheme. The vehicles are named after explorers.

## The requester's context, and what happened to it

| what he said | what the survey found |
|---|---|
| "a lot of conversions, but the range we present are the fully made-up, finished campervans" | **Exactly right, and sharper than expected** — see *The trap is a price*, below |
| "specification download brochure at the foot of each vehicle page" | The link is real and on all 11 pages, but **the brochure holds no specification at all** |
| "I can't find any prices" | **There are prices**, in a table partway down each model page |
| "lots of images" | True, and not useful here — FMLV's images are carried through untouched |

## What FMLV holds

**Eight live products, all 2026, all VW**, and every one reconciles on
`MTPLM − MRO = payload`:

| id | range / model | £ | MTPLM | MRO | payload | L×W×H | berths |
|---|---|---|---|---|---|---|---|
| 5849 | Shackleton / T7 | 59,995 | 3200 | 2355 | 845 | 5050×2270×2050 | 4 |
| 5851 | Columbus S / T7 | 63,495 | 3200 | 2355 | 845 | 5050×2270×2050 | 4 |
| 5853 | Livingstone / T7 | 68,995 | 3200 | 2400 | 800 | 5450×2270×2050 | 4 |
| 5852 | Expedition / SWB | 58,495 | 3200 | 2376 | 824 | 4890×1900×1990 | 2 |
| 7329 | Weekender / Weekender | 46,200 | 2600 | 1887 | 713 | 4904×2297×1978 | 2 |
| 8748 | Darwin / FL | 94,995 | 3500 | 3115 | 385 | 5980×2427×2660 | 2 |
| 8749 | Darwin / ML | 94,995 | 3500 | 3115 | 385 | 6798×2427×2660 | 2 |
| 8750 | Darwin / EL | 94,995 | 3500 | 3115 | 385 | 6798×2427×2660 | 2 |

**FMLV splits the name as range = the explorer, model = the base vehicle** — `Columbus S`
/ `T7`, `Expedition` / `SWB`. **The site publishes only the explorer name.** Nothing on it
says `T7` or `SWB`, so the model half of every identity has no source. That is a decision
for the checkpoint, not something to guess.

Also present and out of scope: five archived 2022 `SWB` products, and four deactivated —
`Columbus T7` (5850), `Classic`, `Kingsley` (Ford) and `Magellan` (Mercedes).

## The brochure is not the spec source

`/wp-content/uploads/2026/01/RH-Range-Brochure-2025-LR2.pdf`, 24 pages, linked
**identically from all eleven van pages** — it is one range brochure, not one per vehicle.

It extracts cleanly and contains **not one `kg`, not one `mm`, and not one price**. It is
marketing copy and "What's included" bullet lists:

```
What's included: ● A front elevating German made SCA roof that is colour coded to
match your vehicle's paintwork. The elevating roof features a comfy ...
```

Worth keeping for the habitation findings, worth nothing for figures. This is the
near-miss document the running order warns about, and it was the requester's own lead —
flagged here rather than quietly worked around.

## The real source is the model page, and it is thin

Eleven pages under `/van/<slug>/`, all linked from the home page. A full one — Columbus S —
gives this, and nothing more:

```
Layout: Oak units with side kitchen with 4 berths and 4 seats
Appliances: 50L fridge freezer, twin burner hob with sink, water tank & pump, sealed gas locker
Power: 100Ah lithium leisure battery, with ultra-low power LED lighting (fully certified)
Sleeping: RIB crash-tested bed with Isofix (188 × 120 cm), SCA elevating roof (220 × 132cm)
Heating: Diesel heating
```

| field | available? |
|---|---|
| price | **yes** — a table by trim and engine |
| berths, seats | **yes** on five models, as a range (`2-4 berths and 4-5 seats`) |
| habitation equipment | **yes**, richly |
| body type | **partly** — the SCA elevating roof is standard and stated |
| MTPLM, MRO, payload | **no** — except the Darwin's `Payload as tested 380kg` |
| length, width, height | **no**, on any page, anywhere |

**No mass and no dimension is published on this site.** FMLV's figures must have come from
somewhere else — they look like base-vehicle data — and this adapter cannot maintain them.
Per the settled rule they would simply not be proposed, and FMLV's own figures would stand.

## The trap is a price, and it is the lowest number on the page

Every model page carries **two** price blocks:

* **New Vehicle** — the finished campervan, priced by VW trim and engine. Columbus S runs
  from `VW Commerce 110 Manual £64,495` up to `Commerce Pro T32 150 Automatic 4×4 £80,001`.
* **Conversion Only** — converting a van the customer already owns. Columbus S **£20,495**,
  Livingstone **£20,995**.

The conversion price is the smallest figure on the page, so "take the lowest price" — the
obvious reading of the base-vehicle rule — takes the wrong one **every time**. The price
must be the lowest of the *New Vehicle* table specifically.

**That rule is confirmed against FMLV's own data.** The lowest New Vehicle price reproduces
what FMLV holds exactly on two models — Shackleton **£59,995** and Livingstone **£68,995** —
which is strong evidence the figures came from this table and that the base trim is the one
recorded.

Where it differs, it differs upward by about £1,000: Columbus S £63,495 → £64,495,
Columbus £62,995 → £63,995. The **Darwin is the exception and needs a decision**: all four
Darwin pages share one price table running £89,995–£96,095, where FMLV holds all three at
£94,995. Taking the base would cut all three by £5,000.

## There is no self-check — a first

Every manufacturer surveyed so far has published something against itself. Rolling Homes
publish no mass, so there is no `MTPLM − MRO = payload` to test; no dimensions, so no
length to sanity-check; and one price table per page with no cross-reference. **A misread
would be undetectable by arithmetic.**

What can be done instead is structural rather than numeric, and the checkpoint should say
so plainly:

* require the price to come from the **New Vehicle** block, and reject one that matches the
  Conversion Only figure;
* require `berths ≤ seats`;
* require the page to carry a `Key Features` block at all before believing anything on it.

## Two pages are empty shells

`/van/weekender/` and `/van/ability/` render the tab headings — `New Vehicle`,
`Key Features`, `Vehicle Upgrades`, `Extras`, `Conversion Only` — **with no content under
any of them.** No price, no features, no berths.

**The Weekender is a live FMLV product at £46,200**, so this matters: the adapter must
collect nothing for it rather than read the empty page as a discontinuation. One more
reason an absence here cannot be trusted.

## Ability is not a product

`/van/ability/` is wheelchair accessibility offered **across the range** — *"whether you
need a slide out…"* — with an empty page and no specification of its own. It has a name and
a page, which is the usual test, but nothing behind them. It should not become a product.

## Slugs lie

`/van/darwin-rl/` is the **Darwin EL**. `/van/darwin/` is the **Darwin ML**. The name must
be read from the page's `<h1>`, never derived from the URL.

## Three on the site that the live baseline does not hold

| | note |
|---|---|
| **Columbus** (plain) | A full page with prices and features. FMLV's `Columbus T7` (5850) is **deactivated and archived**, so this would arrive as new |
| **Darwin FL 6.0** | A fourth Darwin page. FMLV's `Darwin FL` is 5980mm — i.e. 6.0m — so whether this is a new layout or the same vehicle needs the requester's eye |
| **Ability** | Not a product, per above |

## Expected count

**Eight to ten.** Eleven `/van/` pages, less Ability (not a product), less whatever the
requester decides about Darwin FL 6.0; the Weekender collects nothing but must not be
reported missing.

The site publishes no "N models" claim of its own — the "Meet the explorers" footer is a
rotating carousel showing three at a time, not a roster — so the home page's eleven `/van/`
links are the only roster, and should be rediscovered each run rather than written in.

---

# Built — 9 October 2026

`src/adapters/rolling_homes.py`. The requester's instruction, the same day: **roll the
weights and dimensions over** on the continuing models and ask Rolling Homes for figures,
with their exhibition appearance next week as levered, *"rather than not build and not have
them updated."*

## What it proposes, and what it deliberately never touches

| proposed | never proposed |
|---|---|
| `rrp_pounds`, `price_min_range_pounds` | `mtplm_kilograms`, `mro_kilograms`, `mh_payload_kilograms` |
| `berths`, `mh_passenger_seats_inc_driver` | `mh_length_mm`, `mh_width_mm`, `mh_height_mm` |
| `manufacturer_range`, `base_vehicle_manufacturer` | **`model`** |
| `body_type` where a roof is stated | |
| habitation findings | |

**`model` is never proposed**, and that is deliberate rather than an omission. FMLV files
the model as the base-vehicle generation — `Columbus S` / `T7`, `Expedition` / `SWB` — and
the site prints neither string anywhere. `FMLV_IDENTITY` carries FMLV's own answer so each
product *matches*; no provenance is recorded for it, so `compare_fields` is never invited
to look and nothing can be disturbed.

## Three cuts, each of which the first run got wrong

**1. The New Vehicle section, against the Conversion Only one.** Taken between the two
`<h2>` headings. Everything after the second describes converting a customer's own van: a
price a fifth of the real one *and* a second `Key Features` list stating different berths.
Reading the page whole gets price, berths and seats wrong together, and nothing downstream
could tell.

**2. The Key Features tab, against Vehicle Upgrades and Extras.** The New Vehicle block
holds three tabs and the last two are options. Run #153 reported the Columbus's heating as
`'Diesel blown air heating*'` — an item off its Extras list, not equipment it has. Berths,
seats, body type and the habitation findings all read the first tab only. **The price does
not**, because the trim tables live under Vehicle Upgrades.

**3. The section, against the whole page, for the base vehicle.** Every page carries a
"Volkswagen Van Converters" block in its furniture, so a page-wide search answers `VW` for
everything — including a Ford-based van, and including a page with no content at all.

## An empty page is not a withdrawal

`/van/expedition/` and `/van/weekender/` render every tab heading with nothing under any of
them, and **both are live FMLV products**. Run #152 collected nothing for them and reported
both as disappeared, which is the one failure this manufacturer makes easy.

They are now emitted **for their identity alone**: they match, carry through unchanged, and
the run says in terms that the page is an empty shell rather than the vehicle being gone.
A missing price is likewise not a failure — `_reconciles` passes it, because dropping the
product would lose the fields the page *does* publish.

> Worth raising with Rolling Homes: the Expedition's berths and seats exist **only** in its
> Conversion Only block. Its New Vehicle tab has simply not been filled in.

## Run #155 — the first clean one

```
scraped     10 products against a baseline of 8
classified  4 changed, 4 unchanged, 2 new, 0 disappeared
            60 in-scope fields not found this run
```

The 60 not-found are the masses and dimensions across all ten, which is the roll-over
working as instructed. The 2 new are **Columbus / T7** (FMLV's 5850 is deactivated and
archived) and **Darwin / FL 6.0**.

Only four real changes, and they divide cleanly:

| | |
|---|---|
| Shackleton £59,995, Livingstone £68,995 | **unchanged** — the base-vehicle price rule reproduces FMLV exactly |
| Columbus S £63,495 → **£64,495** | a £1,000 increase |
| Darwin EL, FL, ML £94,995 → **£89,995** | **needs a decision** — see below |

**The Darwin price is the one open question.** All four Darwin pages share a single price
table running £89,995–£96,095, and FMLV holds all three at £94,995. The base-vehicle rule
says take the entry trim, which cuts each by £5,000. It is proposed rather than suppressed
so a reviewer sees it, but if £94,995 came from Rolling Homes directly it should be
rejected each run until their table agrees.
