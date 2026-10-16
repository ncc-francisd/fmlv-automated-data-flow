# Fifth Wheel Co — survey, 16 October 2026

**NCC id 268.** `fmlv_manufacturer` **`Fifth Wheel Co`**, display name the same, and the
NCC **supplier name is `Fifth Wheel Co.`** — with a trailing full stop. The requester
flagged that as a trap and he was right: `fetch-export` selects on that exact string.
Verified on 16 October, when it triggered the download for `'Fifth Wheel Co.'`.

`https://fifthwheelco.com/`. Caravans, built in St Asaph. No adapter yet; this is the
stage-1 checkpoint.

## These are not conventional touring caravans

Two things about the vehicles shape everything below, both as the requester described them.

**The body slides outwards when parked.** Every range publishes two widths — the
travelling one and the extended one — and only the travelling width is FMLV's.

**The Celtic Rambler and DreamSeeker couple to a pickup's bed, not a tow bar.** So the
length that sits behind the tow vehicle is *shorter* than the body, because the gooseneck
overhangs the truck. The INOS is a conventional tow with a slide-out — their own brochure
calls it *"the only British-made caravan to offer this feature"*.

FMLV's own data bears the geometry out exactly:

| | shipping | body |
|---|---|---|
| Celtic Rambler | 6500 | **8500** |
| DreamSeeker | 6400 | **7600** |
| INOS | **8200** | 7000 |

The INOS's shipping length exceeds its body, as a drawbar caravan's does. The two
fifth-wheels' are shorter than theirs, as a gooseneck's must be.

## What FMLV holds — three, one per range

Each is a one-name product carrying its name twice, the settled convention.

| id | range / model | £ | MTPLM | MRO | payload | shipping | body | W | H | headroom |
|---|---|---|---|---|---|---|---|---|---|---|
| 8824 | Celtic Rambler | 95,000 | 4300 | 3300 | 1000 | 6500 | 8500 | 2300 | 3300 | 2200 |
| 8825 | DreamSeeker | 85,000 | 4300 | 2800 | 1500 | 6400 | 7600 | 2300 | 3000 | 2000 |
| 8826 | INOS | 77,500 | 2800 | 2400 | 400 | 8200 | 7000 | 2300 | 2700 | 2000 |

## The website carries more than expected, and it agrees with FMLV

The requester thought there was little on the site. In fact each range page has a
**`Technical Specifications & Service`** accordion with a `Masses & Dimensions` block, and
its figures reproduce FMLV's **exactly** — mass in running order, MTPLM, payload, body
length, height and the travelling width, on all three.

DreamSeeker, verbatim:

```
Unit Weight:                     2,800kg
MTPLM:                           4,300kg
Payload:                         1,500kg
Overall Length:                  7.6m (24'11")
Overall Height:                  3.0m (9'10")
Overall Width:                   2.3m (7'6")
Width with Slide Out Extended:   3.2m (10'2")
```

**`Unit Weight + Payload = MTPLM` closes on all three** — 2,800 + 1,500 = 4,300;
3,300 + 1,000 = 4,300; 2,400 + 400 = 2,800. A published self-check, which is what the
strongest adapters here lean on.

### Both mass rules apply, one per range, and FMLV already follows both

This brand happens to demonstrate the difference between two rules that point opposite
ways, which is worth recording.

* **Celtic Rambler** publishes `MTPLM: 4,300kg (3,500kg if downplated for towing on
  standard licence)` and `Payload: 1,000kg (200kg if downplated)`. That is the **same
  chassis plated differently**, so the MTPLM-band rule applies and the **upper** figure is
  the MTPLM. FMLV holds 4300. ✓
* **INOS**'s website gives `MTPLM: from 2800kg to 3,500kg*` with `Payload: up to 1000kg**`,
  footnoted *"MTPLM and payload can be increased with upgraded chassis"*. That is a
  **different chassis**, so the base-vehicle rule applies and the **base** figure is the
  one to record. FMLV holds 2800. ✓

So the test is **whether the larger figure needs a different chassis**. Downplating within
one chassis takes the upper limit; an upgraded chassis takes the base.

## Three traps

**1. The Celtic Rambler's page says `Unlit Weight`.** A typo for `Unit Weight`, and the
only range that has it. A parser anchored on the correct spelling silently loses that
range's masses while the other two parse perfectly — which is the worst shape a fault can
take. Both spellings must be accepted.

**2. The width is published twice.** `Overall Width: 2.3m` against `Width with Slide Out
Extended: 3.2m`. Recording the second would put a caravan wider than a motorway lane into
the width column. This is the Beauer problem again, and the same discipline answers it:
anchor on the label, never on the magnitude.

**3. The INOS website contradicts the INOS brochure.** The site quotes the upgraded
chassis — Unit Weight 2,500kg, MTPLM from 2800 to 3,500kg, Payload up to 1000kg — while
the brochure gives the base: **2,400kg / 2,800kg / 400kg**. FMLV holds the brochure's
figures, so the brochure is the authority and the website's larger numbers are the
upgrade. Any adapter must prefer the brochure for the INOS, or propose a 700kg error.

Also minor: the INOS labels its length `Overall Body Length` where the other two say
`Overall Length`, and only the INOS publishes `Length Behind Tow Vehicle`.

## The price and the berths are in the brochures, not on the site

The range pages carry no price and no berth count. The brochure does both — the INOS one
opens *"Prices from £77,500"*, which is exactly what FMLV holds, and gives
*"Sleeps 4: island bed (1.9m x 1.4m) & front sofa bed (1.9m x 1.3m)"*. The DreamSeeker
page mentions *"sleeps 5"* in prose, matching FMLV's 5, but the Celtic Rambler's states
nothing.

**The brochures are behind an email form**, so they cannot be fetched per run. The INOS
one the requester supplied is `2026 - Fifth Wheel Company - INOS Brochure.pdf`, seven
pages, with the masses and dimensions on page 3 and the interior on page 4.

## What the two fifth-wheels' shipping lengths would rest on

Nothing published. `Length Behind Tow Vehicle` appears only on the INOS page, so FMLV's
6500 and 6400 came from elsewhere and this adapter could not maintain them. They would
carry through untouched — which is the right outcome, not a gap to fill by guessing.

## Verdict — buildable, and the brochures make it worth doing

The website alone would maintain the masses and every dimension for all three, with a
published self-check behind them. But those already agree with FMLV, so a website-only
adapter would propose almost nothing today.

**The value is in the price and the berths, and those are in the brochures.** Unlike
Globe-Traveller, the missing piece here is *additive* rather than structural — the
brochure adds two fields to a design the website already settles — so nothing is wasted by
building the website half first if the brochures are slow.

**Asked of the requester:** the Celtic Rambler and DreamSeeker brochures, which need an
email to Fifth Wheel Co. With all three, this ships complete.

## To ask Fifth Wheel Co

1. **The Celtic Rambler's berth count**, which nothing published states.
2. **Shipping lengths for the Celtic Rambler and DreamSeeker** — the length behind the tow
   vehicle, which only the INOS publishes.
3. **`Unlit Weight`** on the Celtic Rambler page is a typo worth reporting to them.
