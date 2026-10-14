# Airstream — assessment, 14 October 2026

**NCC id 274.** `fmlv_manufacturer` **`Airstream`** (one word), display name `Airstream`,
and the NCC **supplier name is `Lowdhams`** — the UK importer, not the marque. The two
disagree by design, which is worth knowing before anyone "corrects" one to the other.

Caravans only. No adapter yet; this is an assessment rather than a full stage-1 survey,
because the answer turns on a gap rather than on a parsing choice.

## Lowdhams are the importer, which decides what we take from where

The settled rule: an exclusive UK importer decides **what exists and what it costs**, and
the factory decides **every number**. Lowdhams is both the importer and a dealer, so the
division matters here more than usual — the range and the price are theirs to state, the
weights are not.

## What FMLV holds — four, all live, all 2026

| id | range / model | £ | MTPLM | MRO | shipping | body | W | H |
|---|---|---|---|---|---|---|---|---|
| 8863 | International / 25 IB | 109,950 | 3500 | 2475 | 8290 | 6970 | 2490 | 2840 |
| 8861 | International / 534 | 97,950 | 1900 | 1580 | 6860 | 5470 | 2280 | 2700 |
| 8862 | International / 684 | 107,450 | 2920 | 2165 | 8290 | 6970 | 2490 | 2750 |
| 8860 | World Traveller / 22RB | 79,995 | 2000 | 1700 | 7210 | 5840 | 2290 | 2740 |

## The roster and the prices are readable, and two of them are wrong

`/browse/new-airstream-caravans` is **server-rendered** — no JavaScript — with a card per
product giving the name, the price and the berths:

```
Airstream International 684      Only £109,950    4 Berth
Airstream World Traveller 22RB   Only £72,995     4 Berth
Airstream International 534      Only £97,950     4 Berth
```

Against FMLV, **two of the three disagree**, and not in the same direction:

| | FMLV | Lowdhams |
|---|---|---|
| International 684 | 107,450 | **109,950** |
| World Traveller 22RB | 79,995 | **72,995** |
| International 534 | 97,950 | 97,950 ✓ |

**The 25 IB is not on the site at all.** FMLV holds it live at £109,950, and the only
mention anywhere on Lowdhams is a news article a year old. That needs asking about before
anyone deactivates it — a dealer's browse page is a stock-and-range listing, and absence
from it is weaker evidence than a manufacturer withdrawing a model.

## One brochure, covering one range of the two

`AIRSTREAM-WORLD-TRAVELER-BROCHURE-2025-EN.pdf` — the filename says 2025 and the content
says 2026. Page 10 is a real specification block:

```
World Traveler 22RB
Up to 4 SLEEPING CAPACITY   1 AXLE   6 M BODY LENGTH   2.3 M WIDTH
Typical hitch weight  Maximum hitch weight  Kerb weight (MRO):  GVWR (MTPLM):  Payload
100-140 kg            150 kg                1,700 kg            2,000 kg       up to 300 kg
```

**It carries a published self-check and it reconciles**: 2,000 − 1,700 = 300, exactly the
payload printed beside it, and both masses match FMLV to the kilogram. Page 11 is a full
equipment list with every line marked `STD`, which would serve the habitation findings.

## The two gaps that decide this

**There is no International brochure anywhere.** Lowdhams host none, and neither
`airstream.eu` nor `airstreameurope.com` renders a model server-side. So FMLV's **three
International products have no discoverable source** for their masses or dimensions — those
figures came from somewhere off-site and nothing on the web can refresh them.

**The brochure's dimensions are too coarse to use.** `6 M` body length and `2.3 M` width,
against FMLV's 5840mm and 2290mm. Recording 6000 and 2300 would replace better figures with
rounder ones, so nothing should be proposed for any dimension.

## Verdict

**Worth building, but scoped — the Rolling Homes pattern.** It would reliably maintain:

* the **roster** — which models Lowdhams still sell;
* the **price**, which is demonstrably stale on two of three;
* **berths**;
* the **World Traveller's masses**, with a self-check behind them;
* the **habitation findings**, from the brochure's `STD` list.

It would propose **nothing** for any dimension, nor for the International masses, and those
figures would carry through untouched.

Four products is small, but unlike a brand-new manufacturer these are already live on FMLV
with wrong prices, so the value is real and immediate.

## To ask Lowdhams

1. **Is the International 25 IB discontinued?** It is on FMLV and not on their site.
2. **Weights and dimensions for the three Internationals** — nothing published reaches them.
3. **Is there an International brochure** to match the World Traveller one?

## The stock pages are the model entries — 14 October 2026

The requester pointed at Lowdhams' stock listings for the Internationals' weights and
dimensions, and **he is right that they are the model's own entry**, not a customer
vehicle. Each is badged `New`, `In Stock Now` and, for the World Traveller, `Lowdhams
Exclusive`, and its `Registration` reads **`SHOWROOM301`** — a showroom placeholder.

> **A first pass read them as sold units and was wrong.** The page's HTML carries both
> `In Stock Now` and *"Sorry, this one has hit the road. This model has sold"*; the second
> is **dormant template markup that is not displayed**. Presence in the DOM is not the same
> as being shown, and a text search cannot tell them apart. Check a rendered page, or at
> least check what sits beside the string, before reading it as state.

Four vehicles are linked from the browse page, each with a `Specification` block:

```
Make Airstream   Range International   Model 534   Condition New
Berths 4   Overall Width 2.28m   MTPLM 1830kg   Overall Length 6.80m
Overall Height 1.99m   Axles Single   Registration SHOWROOM301
```

### `Overall Height` is the interior height, mislabelled

This is the one field that must not be taken. The World Traveller brochure settles it on
page 11:

```
Exterior height  2.74 m
Interior height  2 m
```

FMLV holds **2740** for the 22RB — the exterior height — and Lowdhams' `Overall Height`
reads **2.00m**, which is the interior figure. The same shape appears on the 534 (1.99m)
and the 25 IB (1.99m). Only the 684's 2.69m looks like a genuine exterior height, so the
field is **inconsistent as well as mislabelled**, and FMLV's heights are the correct ones.

### Against FMLV

| | MTPLM | length | width | height |
|---|---|---|---|---|
| **534** site / FMLV | 1830 / 1900 | 6.80m / 6860 | 2.28m / 2280 | 1.99m / **2700** |
| **684** site / FMLV | 2400 / 2920 | 8.20m / 8290 | 2.50m / 2490 | 2.69m / **2750** |
| **22RB** site / FMLV | 2000 / 2000 ✓ | 7.21m / 7210 ✓ | 2.29m / 2290 ✓ | 2.00m / **2740** |
| **25 IB** site / FMLV | 2750 / 3500 | 8.21m / 8290 | 2.50m / 2490 | 1.99m / **2840** |

**The MTPLM field is trustworthy where it can be checked**: the 22RB reads 2000 on the
stock page, in the brochure and in FMLV. So the 534's 1830 and the 684's 2400 are most
likely current UK plating and FMLV's figures the stale ones — but that is a 520kg change on
the 684 and wants the requester's eye rather than an assertion.

**Lengths and widths agree** — exactly on the 22RB — but the site gives two decimals of a
metre where FMLV holds millimetres, so taking them would round 6860 to 6800. They confirm
FMLV rather than improve on it.

**No mass in running order and no payload** appear on any stock page. Only the World
Traveller has them, from its brochure.

### What a build should take

| take | leave |
|---|---|
| the roster, and that the 25 IB is `used` stock only | every dimension — less precise, and the height is the wrong measurement |
| price, berths | mass in running order and payload for the Internationals |
| **`Axles` → `twin_axle`**, which nothing else here publishes | |
| MTPLM | |
| the World Traveller's masses and habitation, from its brochure | |
