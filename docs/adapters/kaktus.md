# Kaktus — survey, 15 October 2026

**NCC id 219.** `fmlv_manufacturer` **`KAKTUS`** — in capitals, which is how the NCC list
spells it and how the export's `manufacturer` column reads. Display name **`Kaktus`**, and
the NCC supplier is **`Kaktus`** too.

Campervans, hand-built in Pontypool by **Kaktus Adventure Vans Ltd**. No adapter yet; this
is the stage-1 checkpoint.

## What FMLV holds — four, all live, all 2026

The four are **two ranges × two berth counts**, and the model name carries both the berth
count and the wheelbase:

| id | range / model | £ | berths | seats | MRO | MTPLM | payload | L × W × H |
|---|---|---|---|---|---|---|---|---|
| 7747 | Oasis / **X4 LWB** | 149,000 | 4 | 4 | 3500 | 3500 | 200 | 6836 × 2040 × 2590 |
| 7748 | Oasis / **X2 LWB** | 149,000 | 2 | 4 | 3500 | 3500 | 200 | 6836 × 2040 × 2590 |
| 7749 | Dune / **X4 MWB** | 135,000 | 4 | 4 | 3500 | 3500 | 400 | 5986 × 2040 × 2590 |
| 7750 | Dune / **X2 MWB** | 135,000 | 2 | 4 | 3500 | 3500 | 400 | 5986 × 2040 × 2590 |

All four are `campervan_high_top` on a MAN base vehicle.

**Two things in that table are worth noticing before anything else.** The masses are
internally contradictory — `MRO 3500` and `MTPLM 3500` leave no payload at all, yet 200kg
and 400kg are recorded beside them. And both prices are stale, which is the thing an
adapter would actually fix.

## The site is Next.js, and that turns out not to matter

`kaktusvans.co.uk` is a Next.js App Router site: the pages render almost nothing as plain
HTML and the content arrives in a **streamed `self.__next_f` payload**. It looks at first
like a browser job.

**It is not.** The chunks are `self.__next_f.push([1, "…"])` with JSON-encoded strings;
concatenating and decoding them yields the whole page's data to an ordinary HTTP fetch. No
`BrowserFetcher` is needed — which is the thing `docs/adapters/README.md` warns about
reaching for too early.

## The model pages publish nothing an adapter wants

`/vans/oasis` and `/vans/dune` carry a four-row summary and no figures at all:

```
Base    MAN TGE / VW Crafter
Drive   All-wheel drive · 8-gear auto
Power   Victron · 2×100Ah lithium · 250W+ solar
Water   75L fresh · 75L waste · diesel heater
Sleeps  Up to 4 · swivel cab seats
```

No price, no MTPLM, no mass in running order, no length, width or height — in the rendered
page **or** in the decoded payload. The requester had already found as much; this confirms
it rather than contradicting it.

## The configurator is the data source

`/configure` is where the numbers live, and its payload is clean structured data:

```json
{"id":"oasis","name":"Oasis","tier":"LWB · Luxury off-grid","basePrice":157000}
{"id":"dune","name":"Dune","tier":"4x4 · Expedition","basePrice":142000}
```

**Against FMLV, both prices are stale:**

| | FMLV | Kaktus |
|---|---|---|
| Oasis | 149,000 | **157,000** |
| Dune | 135,000 | **142,000** |

That is £8,000 and £7,000 adrift across four live products, and it is the entire case for
building this.

### The berth options map exactly onto FMLV's X2/X4 split

```json
{"id":"2-berth",  "label":"2-berth",                "price":0, "desc":"Fixed memory-foam double over the garage"}
{"id":"pop-top",  "label":"4-berth · pop-top roof", "price":0, "poa":true, "desc":"Elevating roof adds an upstairs double - sleeps four"}
{"id":"cabbunk",  "label":"4-berth · Cabbunk system","price":0,"poa":true, "desc":"Removable cab bunk-bed system - sleeps four"}
```

This is the find that makes the adapter tractable. FMLV splits each range into an **X2** and
an **X4**, and the configurator's sleeping-layout choice is that same split: **2-berth is
the base configuration**, and four berths come from an elevating roof or a cab bunk system.

**Both 4-berth options carry `poa: true`** — price on application. So `basePrice` is the
two-berth price and the four-berth premium is **not published**. FMLV already holds the
same figure for both berth counts, which is consistent with a "from" price, so recording
`basePrice` against both and saying so is the honest reading. Nothing is invented for a
POA, per the settled rule.

## Mojave is not a product

`/vans/mojave` is a third range the requester had not seen, and it should **not** be
recorded. The page says so itself:

* *"Production planned from April 2027"*;
* *"Specification is for the prototype show vehicle and may change before production"*,
  with several lines marked `Provisional`;
* *"Prices from £235,000 … Final specification, pricing and availability are subject to
  confirmation"*.

It is also a different kind of vehicle: a Mercedes-Benz Sprinter 519 AWD expedition build
at **5,000–5,350 kg MAM**, far above the 3,500kg the rest of the range sits at.

An adapter must therefore exclude it by name, or it arrives as a new product carrying a
provisional price.

### Re-checked 29 October 2026: launched, but still not a product

Kaktus showed the Mojave at an **October 2026 show** and the page now carries a `New`
badge, a `View specifications` button and a tabbed **Specifications** panel. It reads as a
launch, and it was reported here as one. **The verdict does not change**, and the page's
own words are why:

* *"Production planned from April 2027"* — unchanged;
* *"The Mojave on display at the October 2026 show is a **prototype**. It will undergo
  further testing and development before production. The final vehicle may differ from the
  show model, and equipment, specifications, finishes, weights and availability may
  change"* — new wording, and more explicit than what it replaced;
* *"Specification is for the prototype show vehicle and may change before production.
  Items marked provisional are still being confirmed"* — still verbatim, so the exclusion
  message in `kaktus.py` still quotes the live page;
* *"Deposits for future build slots are now being accepted"* — a deposit list, not an
  order book.

It is also **still absent from `/configure`**, which carries two `basePrice` keys and
always has. The configurator is this adapter's data source, so the Mojave has no price
there to read even if it were wanted.

#### What the Specifications tab actually publishes

Three rows, and only one of them is a figure:

| row | value |
|---|---|
| Base vehicle | Mercedes-Benz Sprinter 519, all-wheel drive |
| Wheels & weight | 5,000 kg MAM super-single, or up to 5,350 kg dual rear wheel — badged **`Provisional`** |
| Habitation structure | 54mm fibreglass sandwich panels, 50mm foam core |

So the tab adds a confirmed base vehicle and a provisional MAM. **There is still no mass in
running order, no payload, no length, width or height, and no berth or seat count** — the
same gap the rest of this document describes, and none of it is fixed by the new tab.

#### What it will be when it is a product

Worth writing down now, because none of it matches the four live Kaktus:

* **Two products, not one.** *"Fixed rear bed or a rear U-shaped lounge that converts into
  a double bed"* — two layouts, which is how FMLV would carry them.
* **Mercedes, not MAN**, so `base_vehicle_manufacturer` differs from every existing row.
* **5,000–5,350 kg**, against 3,500 for the rest. That is a C1-licence vehicle and a
  composite habitation body on a chassis cab, not a van conversion — so it is very unlikely
  to be `campervan_high_top` like the others. Decide its body type from a floorplan or a
  photograph when there is one, never from the weight.

## What is still missing everywhere

**No mass and no dimension is published anywhere on the site** — not on the model pages,
not in the configurator, not in any download. There is no brochure and no specification
PDF.

So FMLV's MTPLM, mass in running order, payload, length, width and height came from
somewhere off-site, and **this adapter could not maintain or correct them**, including the
contradictory `MRO = MTPLM = 3500`. They would carry through untouched.

## There is no arithmetic self-check

Nothing is published that can be tested against anything else — no payload against two
masses, no tolerance. As with Rolling Homes, the check would have to be **structural**: that
the price came from a model's `basePrice` rather than from the forty-odd priced options
beside it, and that it is credible for a complete vehicle. A reviewer should know this
adapter is less defended than most.

The option list is a real trap in miniature: `/configure` publishes about forty prices from
£85 to £4,750, and the lowest-number heuristic that works on some sites picks a windscreen
cover.

## Verdict — worth building, scoped like Rolling Homes

**Yes, build it.** It is a small adapter against clean structured data, and it fixes a
real, current error: two stale prices across four live products.

It would reliably maintain:

* the **price**, from each model's `basePrice`;
* the **berths**, from the sleeping-layout options that mirror FMLV's own X2/X4 split;
* the **base vehicle** (MAN);
* the **habitation findings**, from the model pages and the configurator's equipment
  descriptions.

It would propose **nothing** for any mass or dimension, and would exclude the Mojave.

Four products is small, but these are live on FMLV with wrong prices, so the value is
immediate — the same argument that justified Airstream.

---

# Built — 15 October 2026

`src/adapters/kaktus.py`, **NCC id 219**. Four fetches: the configurator, the home page
for the roster, and the two model pages for their summary prose.

## Run #175 — the first one

```
baseline    4 products
scraped     4 products
classified  4 changed, 0 unchanged, 0 new, 0 disappeared
proposed    44 changes, of which 4 are year bumps
verified    12 fields checked and unchanged
```

**All four matched, and nothing arrived as new** — the right answer for a manufacturer
FMLV already holds in full, and confirmation that the X2/X4 split was read correctly.

| | FMLV held | Kaktus |
|---|---|---|
| Oasis X2 LWB / X4 LWB | 149,000 | **157,000** |
| Dune X2 MWB / X4 MWB | 135,000 | **142,000** |

`manufacturer_range`, `berths` and `base_vehicle_manufacturer` verified unchanged on all
four, which independently confirms the identity mapping.

## Reject the derived payload of 0kg, every run

The one thing a reviewer must get right. FMLV holds **MRO 3500 and MTPLM 3500** for every
Kaktus, so the pipeline derives a payload of **0** and offers it against the 200kg and
400kg on record:

> *"Derived payload, not read from the site: 3500kg MTPLM - 3500kg MRO = 0kg, against the
> 200kg on record. Neither mass was published this run, so both are FMLV's own figures
> carried over."*

**The arithmetic is right and the conclusion is wrong.** A campervan has a payload, so the
figure at fault is the mass in running order — it cannot be 3500 if the MTPLM is. Kaktus
publish nothing that can correct it, so this will be proposed on **every** run until they
supply real masses. Reject it each time rather than leaving it pending, as with the Bailey
B65 length.

The adapter names this in its own output so nobody has to rediscover it.

## What it maintains, and what it refuses

| takes | leaves to FMLV |
|---|---|
| the price, from each model's `basePrice` | every mass — none is published anywhere |
| berths, from the sleeping-layout group | every dimension — likewise |
| the range name and the base vehicle | the body type: no height is published, and the elevating roof is an *option* |
| the habitation findings, from the model page summaries | the seat count: `Sleeps up to 4` is berths, not belted seats |

## The four things that would have gone wrong quietly

**1. Reaching for a browser.** The pages render almost nothing as HTML and look like a
`BrowserFetcher` job. They are not: the `self.__next_f` chunks are JSON-encoded strings
that concatenate and decode over an ordinary fetch.

**2. The option prices.** `/configure` publishes **41 options** from an £85 windscreen
cover to a £4,750 seat retrim, beside the two `basePrice` keys that matter. Any
lowest-number heuristic buys the windscreen cover, so the price is read from `basePrice`
alone and `MINIMUM_CREDIBLE_PRICE` is set at £50,000 — a gap the options cannot cross.

**3. Mojave.** Linked from the home page like the other two, and excluded by name. Without
that, a prototype priced "from £235,000 subject to confirmation" arrives as a new product.

**4. The Dune's stance row.** `60mm lift · 16" off-road tyres` carries a quote that is
escaped in the flight payload, where a naive value pattern stops at it and loses the row.
The summary is therefore read from the **rendered** `<dt>`/`<dd>` markup, which carries
the same text as an HTML entity.

## Two readings deliberately left alone

* **The heating.** The Oasis's summary says `75L fresh · 75L waste · diesel heater`, which
  names a heater without saying whether the system is blown air or wet. Narrated, not
  guessed — the same call as Beauer's "central heating".
* **The model string.** `X4 LWB` carries a wheelbase Kaktus publish only for the Oasis;
  the Dune's page names none. `FMLV_WHEELBASE` carries FMLV's own answer so the products
  *match*, and `model` is given no provenance so it is never offered as a change.

## To ask Kaktus

1. **MTPLM, mass in running order and payload**, which nothing published reaches. FMLV's
   `MRO 3500 / MTPLM 3500 / payload 200` cannot all be right.
2. **Length, width and height** — FMLV's look like the MAN TGE's own figures.
3. **What the four-berth upgrade costs**, since both options are POA.
4. **Is the Oasis really offered on a VW Crafter as well as a MAN TGE?** Its page says
   *"MAN TGE / VW Crafter"* while the configurator offers only `MAN TGE 4MOTION`, and a
   different base vehicle would be a different product.
