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

---

# Built — 16 October 2026

`src/adapters/fifth_wheel.py`, **NCC id 268**. Six fetches: a range page and its brochure,
three times over.

## The email form turned out not to matter

Each range page offers its brochure behind an email form, and **every page also carries the
PDF's own Squarespace `/s/` path in its markup**. Fetching that returns the document, on
all three. So the adapter needs no stored copy and no manual step — the requester filled in
the form three times and, as it turns out, did not need to.

## Run #184 — the first one

```
baseline    3 products
scraped     3 products
classified  0 changed, 3 unchanged, 0 new, 0 disappeared
proposed    6 changes, of which 3 are year bumps
verified    39 fields checked and unchanged
findings    3 habitation readings
```

**Nothing is proposed but the year**, which is the right answer: FMLV already holds all
three correctly, and 39 fields were confirmed against the manufacturer's own brochures.

## The INOS is published three times, and only two of the three add up

The finding that shaped the adapter.

| source | unit weight | payload | MTPLM | adds up |
|---|---|---|---|---|
| the brochure the email form sends | 2,400 | 400 | 2,800 | **yes** |
| the brochure the site links | 2,600 | 1,000 | 2,800 or 3,500 | **no — 3,600** |
| the range page itself | 2,500 | up to 1,000 | from 2,800 to 3,500 | yes, at 3,500 |

**Settled by the requester on 16 October 2026, on the arithmetic**: *"the one that is in
the brochure and matches FMLV should be the one that we go with. It is defendable, it's in
the brochure as well … it's the fact that it adds up where the other one doesn't that sways
me."*

So the normal protocol — record what the manufacturer publishes now — gives way here, and
`KNOWN_MASSES` carries the emailed brochure's three figures. They are still a brochure's
rather than anyone's invention, and the provenance names both documents so a reviewer sees
exactly which was preferred and why.

**Only the three masses are overridden.** The two INOS brochures agree on every dimension,
so length, width, height and headroom are always read from the fetched document. And **the
fetch is preferred whenever its own sums work**, so this retires itself the day Fifth Wheel
Co fix their file.

`_reconciles` tests the document's *own* masses rather than the overridden ones — which
were chosen because they reconcile, so checking those would always pass and the check would
say something different the second time it ran.

## Three parsing traps, all of which cost the whole table

The specification is **columnar** — every label first, grouped under its section heading,
then every value in the same order — so a single lost value unbalances the columns and the
table is refused entirely. Each of these cost all three ranges until it was fixed:

**1. A value written in words.** The site's INOS gives `up to 1000kg` and `from 2800kg to
3,500kg`. A pattern anchored on a leading digit misses both and folds them into the value
above, leaving fourteen labels against twelve values.

**2. `²` is a word character.** The slide-out areas read `5.3m²`, and a word boundary after
the unit — `m` — fails on exactly those rows. One row lost, whole table refused. There is
no boundary now, which is safe because no label on any brochure contains a digit.

**3. A wrapped value.** `4,300kg (3,500kg if downplated` continues onto `for towing on
standard licence)`. A continuation is told from a value by carrying **no figure at all**,
which is what lets it coexist with trap 1.

## Both mass rules appear here, one per range

* **Celtic Rambler and DreamSeeker** publish `4,300kg (3,500kg if downplated for towing on
  standard licence)` — one chassis plated differently, so the band rule takes the **upper**
  figure.
* **INOS**'s larger figure needs an **upgraded chassis**, so the base-vehicle rule takes
  the **base**.

`_primary_figure` reads the figure stated before any bracket, which is correct in both
cases for the same reason: it is what the manufacturer states plainly before qualifying it.

## FMLV's spelling is kept over the manufacturer's

They write **`Dreamseeker`** throughout their site and brochure; FMLV holds
**`DreamSeeker`**. The first run proposed the rename, and it was removed: the settled rule
is that the export decides the identity strings, and a casing change buys a reviewer
nothing while touching the one thing a rename can corrupt. Their spelling is in the
provenance instead.

## What is not recorded

* **The extended width** — `3.3m` on the Celtic Rambler against a travelling `2.3m`. Kept
  out by its label, never by its magnitude.
* **The internal length** — not published. FMLV's three look like a typist's
  approximation: two equal the length behind the tow vehicle and one the body length.
* **Internal width, bathroom and bedroom heights, and every slide-out dimension** — read
  and discarded, because FMLV holds no column for them. The run lists them each time.

## The Celtic Rambler's berths are written down, not counted

Its brochure describes *"a fitted island king-size bed (1.9m x 1.5m)"* and *"a 2.5m
L-shaped slide-out sofa (converts to double bed)"*, and never states a count. The requester
settled it on 16 October 2026 — *"it's designed to sleep four people, so that's two double
beds, so a four berth"* — which is what FMLV already holds.

`KNOWN_BERTHS` carries that answer rather than a rule for counting beds, because the
settled rules do not derive a berth figure from furniture and one confirmed answer is no
reason to teach every adapter to try. **A brochure that starts stating a count is preferred
over it**, so the written-down figure retires itself. The provenance names its source.

## All three ranges publish their floorplans

Each range page carries a DAY and a NIGHT drawing per layout variant — `INOS-Day.png`,
`DS20-Night.png`, and both `CR20` and `U-Shape` on the Celtic Rambler, which is the only
range with two. They are offered as a reviewer pointer on every positional habitation field
still unanswered, since those can only be read off a drawing by a person.

## To ask Fifth Wheel Co

2. **Shipping lengths for the Celtic Rambler and DreamSeeker** — the length behind the tow
   vehicle, which only the INOS publishes.
3. **`Unlit Weight`** on the Celtic Rambler page is a typo worth reporting to them.
