# Visiontech Automotive — survey, and the 6 October 2026 re-check

**NCC id 44**, `Visiontech Automotive` — **`Visiontech` is one word, capital V only**, and
the NCC supplier name is the same string. VW Transporter campervan converter, Colchester.
No adapter; the registry row's `notes` hold the September survey in full.

**They sell conversions, not vehicles.** Every price is quoted twice — the conversion
alone, and the conversion **`+ VAN`** as a complete vehicle — and each of those twice
again, **2 berth** and **4 berth**. FMLV records the `+ VAN` 2-berth figure, which is the
complete campervan at its base berth count.

## The range, 6 October 2026

`/campervan-conversions/` lists **20/20 Vision, Edge, Beach, Premier** and a fifth card,
**Bespoke**, which is an invitation rather than a product. FMLV holds exactly those four,
all at model year 2026. **The range is unchanged and nothing has been added or dropped.**

## The prices check against themselves

The van is a flat **£30,000** on top of the conversion, on every model and both berth
counts:

| | conversion | + VAN | the van adds |
|---|---|---|---|
| 20/20 Vision 2 berth | £13,995 | £43,995 | £30,000 |
| 20/20 Vision 4 berth | £18,795 | £48,795 | £30,000 |
| Beach 2 berth | £8,995 | £38,995 | £30,000 |
| Beach 4 berth | £13,795 | £43,795 | £30,000 |
| Premier 4 berth | £15,795 | £45,795 | £30,000 |
| **Premier 2 berth** | **£10,995** | **£10,995** | **£0** |

**That last row is a site error, and the arithmetic proves FMLV right.** The
`PREMIER + VAN / 2 BERTH` cell repeats the conversion-only figure. What it should read is
`10,995 + 30,000 = 40,995` — **exactly the £40,995 FMLV already holds**. The error was
present at the September survey and is still there.

So every price FMLV holds is confirmed:

| | site | FMLV | |
|---|---|---|---|
| 20/20 Vision | £43,995 | £43,995 | unchanged |
| Beach | £38,995 | £38,995 | unchanged |
| Premier | cell broken | £40,995 | confirmed by the £30,000 rule |
| Edge | none published | blank | see below |

## Two things to know before reading those pages

**The Beach pricing page labels its `+ VAN` blocks `2020 VISION + VAN`.** The figures
(£38,995 and £43,795) are the Beach's and match FMLV, but the headings name the wrong
conversion. Combined with the Premier cell, **two of the four pricing pages carry an error
in the exact cell FMLV reads** — which is the standing reason there is no adapter.

**Every price is ex-VAT.** Each block is footed *"all prices are subject to vat"*, so
FMLV's stored figures are ex-VAT where every other brand's is on-the-road. Inc-VAT they
would be £52,794, £49,194 and £46,794. This needs a decision; it is not a parsing problem.

## The Edge has no price because it is not a fixed product

`/edge-pricing/` now resolves rather than returning 404, but renders no pricing panel at
all. The `/edge/` page carries no price and no link to one, describing instead a
**`MODULAR DESIGN`** and **`DESIGN YOUR OWN TO SUIT YOUR NEEDS`**; the index card calls it
a *"Sports van build & design"* with an *"Option for bespoke build"*, and it sits beside
**Bespoke** in the menu.

So the Edge reads as made-to-order. **Leave the price blank** — [`README.md`](README.md)
says never invent a POA. Worth asking Visiontech whether a starting price exists.

## Still no technical data of any kind

No weights, no dimensions, no seat counts, on any page. Everything FMLV records beyond
price came from elsewhere and cannot be checked here. Two consequences stand from
September and are unchanged:

- **FMLV's own widths disagree**: 1904 on the 20/20 Vision and Premier, 2297 on the Beach
  and Edge. A Transporter is about 1904 without mirrors and 2297 with them, so two rows
  break the mirrors-excluded rule. Nothing on the site can settle which.
- **The index says every conversion is `4 Berth sleeping capacity`** where FMLV holds 2.
  That is the top of a range, not a correction: the pricing pages sell each conversion as
  2 berth *and* 4 berth, and the rule takes the lower figure — which is also the berth
  count FMLV's recorded price belongs to. **Do not raise it to 4.**

## What a 2027 update amounts to

**The year, and nothing else.** The site confirms the range and every price we hold, and
publishes nothing we do not already have. There is no figure to change.

**Avoid the stock pages** if an adapter is ever written — `/stock/`,
`/campervan-for-sale-uk/`, `/campervan-dealer-in-uk/` carry individual used and ex-demo
vehicles at their own prices, the trap `vantage.py` guards against.
