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

## To ask Kaktus

1. **MTPLM, mass in running order and payload**, which nothing published reaches. FMLV's
   `MRO 3500 / MTPLM 3500 / payload 200` cannot all be right.
2. **Length, width and height** — FMLV's look like the MAN TGE's own figures.
3. **What the four-berth upgrade costs**, since both options are POA.
4. **Is the Oasis really offered on a VW Crafter as well as a MAN TGE?** Its page says
   *"MAN TGE / VW Crafter"* while the configurator offers only `MAN TGE 4MOTION`, and a
   different base vehicle would be a different product.
