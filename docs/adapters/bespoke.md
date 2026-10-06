# Bespoke NI — survey and adapter, 5 October 2026

**NCC id 68**, `fmlv_manufacturer` **`Bespoke NI`**, display name **`Bespoke`**, supplier
name the same as the manufacturer name. Campervans only, converted in Ballymena, County
Antrim. Contact **Shane**, `shane@bespokeni.com`.

**Adapter written and deliberately partial.** What it can and cannot do is set by one
fact, stated here first because everything else follows from it.

## Bespoke publish no mass of any kind

Six model pages and three PDFs were searched. There is **not one `kg` figure**, and no
occurrence of *payload*, *gross vehicle weight*, *kerb weight*, *MIRO* or *MTPLM*.

FMLV holds `mro_kilograms` and `mtplm_kilograms` for all eight of its rows, and
`payload == MTPLM - MRO` reconciles on **every one**. So the figures exist and are simply
not published. The adapter emits nothing for them; a blank would destroy good data.

**That also removes the usual self-check.** With no mass there is no arithmetic to
reconcile, which is why the check that *is* available — see below — is a weak one, and
this file says so rather than implying otherwise.

## Two halves, and only one is strong

### The Explore — six variants, priced

Sold on the **VW Transporter T7** and the **Ford Transit Custom**. The leaflet linked from
its model pages carries a real base-vehicle price table:

| | price | | price |
|---|---|---|---|
| Ford Custom Trend 110PS 6 speed manual | £60,995 | VW T7 Commerce Plus 110PS 6 speed manual | £64,995 |
| Ford Custom Limited 136PS 8 speed auto | £65,995 | VW T7 Commerce Plus 150PS 8 speed auto | £69,995 |
| Ford Custom Tourneo 170PS 8 speed auto | £68,995 | VW T7 Commerce Pro 170PS 8 speed auto | £73,995 |

That table is the roster *and* the price source, and it is **rediscovered every run**.

**Never hardcode the leaflet path.** Its upload folder carries the issue month —
`/wp-content/uploads/2026/02/` — and moves every time Bespoke reissue. Three pages are
tried, because the leaflet is two thirds of the range and losing it is expensive.

**The table prints Ford on the left of each line and VW on the right**, so a line-by-line
read finds three variants and silently misses three. The pattern runs over the whole
document instead.

### The Edition — three products, one price

The **VW Crafter**. Its page states **one** on-the-road price (£109,995) for what FMLV
holds as three products — `Edition 2 / 140 Auto`, `Edition 2 / 177 Commerce Plus Auto
Fixed Roof`, `Edition 4 / 177 Commerce Plus Auto Elevating Roof` — and breaks out no
engine, roof or berth count. Its leaflet carries no price at all, saying only *"For latest
pricing please visit BespokeLeisure.co.uk"*.

One price cannot be attributed to three variants, so the three are collected **by identity
alone**. Nothing is proposed, but their FMLV rows are claimed — without that, a run reports
three vans Bespoke still sell as missing from the site. That is the Carthago lesson; see
[`README.md`](README.md).

## Length and height are emitted, width is not

The Explore pages state three dimensions. Two of them agree with FMLV to the millimetre
and one does not:

| | site | FMLV | emitted |
|---|---|---|---|
| length | `Explore Length 5.05m` | 5050 | **yes** |
| height | `1.98m` | 1980 | **yes** |
| width | `Explore Width 2.27m` | 2032 | **no** |

2.27 m is 2270 mm **across the mirrors**; 2032 is the body width, which is what FMLV holds
and what the rule in [`README.md`](README.md) asks for. The Crafter page's `2.44m` against
FMLV's 2427 is much closer, but the Edition products are identity-only anyway.

## The self-check, such as it is

No mass means no arithmetic. What is left is that the leaflet and the model pages are
maintained separately and state overlapping facts, so `price_disagreements` reports a page
quoting a price the leaflet does not print — the signal that one has been reissued without
the other.

## What the first run found

Against the export of 5 October 2026: **9 collected against 8 live rows — 5 unchanged,
3 price corrections, 1 new, nothing missing.**

| | |
|---|---|
| `Explore Custom / 110 Trend` | £61,000 → **£60,995** |
| `Explore Custom / 136 Limited` | £64,995 → **£65,995** |
| `Explore Custom / 170 Limited` | £69,995 → **£68,995**, and renamed **`170 Tourneo`** |
| `Explore Transporter / 170 Commerce Pro` | **new**, £73,995 |

## Settled: the 170 PS Ford is a Tourneo, not a Limited

Below the price table the **same leaflet** carries a specification table — alloy wheels,
cameras, warranty — and its columns are headed **`Ford Custom TREND 110PS Manual`**,
**`Ford Custom LIMITED 136PS Auto`** and **`Ford Custom TOURNEO 170PS Auto`**, with the VW
columns reading **`T7 Commerce PLUS`** and **`T7 Commerce PRO`** the same way. **Custom is
the Transit Custom family and the capitalised word is the trim**, which is why the site
gives the Tourneo its own page.

So FMLV's `Explore Custom / 170 Limited` carries the wrong trim — `Limited` is the 136 PS.
The adapter emits **`170 Tourneo Elevating Roof`** with provenance on `model`, so the run
proposes the rename rather than quietly agreeing with FMLV. It still matches the right row
(0.714, over the 0.5 threshold) and scores 0.000 against the 110 and the 136, whose engine
codes read as layout codes and disagree.

**This is the one place the adapter does not use FMLV's own string.** The rule in
[`README.md`](README.md) says file products as FMLV files them; it does not say repeat an
error the manufacturer's own brochure contradicts.

## Open questions

1. **Weights.** Worth asking Shane for MIRO and maximum permissible weight per variant —
   FMLV has figures but nothing can confirm them, and the new Commerce Pro has none.
2. **The PHEV and the Sports Edition** have pages but no FMLV rows. The Sports Edition
   states no price at all, so it may be an upgrade pack rather than a product.
