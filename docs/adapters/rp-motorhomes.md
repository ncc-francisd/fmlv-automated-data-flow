# RP Motorhomes — survey, 16 October 2026

**NCC id 258.** `fmlv_manufacturer` **`RP Motorhomes`**, display name the same, and the NCC
supplier name is **`RP Motorhomes`** too — no trap this time. Contact **Steve Yeadin**,
`info@rpmotorhomes.com`.

`https://rpmotorhomes.com/`. High-top campervans on the Mercedes-Benz Sprinter, built in
the UK. No adapter yet; this is the stage-1 checkpoint.

## What FMLV holds — four, all live, all 2026

Each is filed as range + drivetrain, which is also how RP market them.

| id | range / model | £ | MRO | MTPLM | payload | L | W | H |
|---|---|---|---|---|---|---|---|---|
| 8738 | Rebel / RWD | 126,000 | 3150 | 3500 | 350 | 5932 | 2020 | 2780 |
| 8739 | Rebel / AWD | 134,000 | 3280 | 4100 | 820 | 5932 | 2020 | 2990 |
| 8740 | Rebellion / RWD | 136,000 | 3350 | 3500 | 150 | 6967 | 2020 | 3050 |
| 8741 | Rebellion / AWD | 148,000 | 3750 | 4100 | 350 | 6967 | 2020 | 3170 |

All four `campervan_high_top` on a Mercedes base, 2 berths and 2 seats apiece — as the
requester said.

## The brochures are the source, and they are directly fetchable

Squarespace again, so the same thing as Fifth Wheel Co applies: the PDFs sit on `/s/`
paths and fetch without any form.

* `/s/2027-Rebel-Brochure-Final-Share-Version-v1.pdf` — 28 pages
* `/s/2027-Rebellion-Brochure-Final-Share-Version-v1.pdf` — 24 pages

Both are linked from `/brochures` and from the `/rebel-2027` and `/rebellion-2027` pages,
so the URL can be rediscovered per run. **Page 21 of each is a `Technical Data` spread** —
the one the requester screenshotted — carrying the prices, the GVW, the belts and beds, and
dimensioned side and rear drawings.

Note the site keeps `/rebel` and `/rebellion` as well as the `-2027` pages, so the right
pair must be chosen deliberately rather than by taking whatever `/rebel` returns.

## Every price is stale, by about £21,000

The requester's worry — that there are no prices on the site — is right about the site and
wrong about the brochures. Page 21 of each prices the range outright:

| | FMLV | 2027 brochure |
|---|---|---|
| Rebel RWD | 126,000 | **147,000** |
| Rebel AWD | 134,000 | **155,000** |
| Rebellion RWD | 136,000 | **157,000** |
| Rebellion AWD | 148,000 | **170,000** |

Four products, each about £21,000 light. **That is the case for building this**, and it is
the largest single correction any adapter here has been built for.

## Take the drawing's millimetres, not the summary box

The Technical Data spread gives each dimension twice: once rounded in a summary tile and
once dimensioned on the drawing. **They disagree, and the box is wrong.**

The Rebel's tiles read `5.9m` and `7.0m` for RWD and AWD, while **both** drawings say
`5932 mm`. FMLV holds 5932 for both, so the AWD's `7.0m` is an error — almost certainly
copied from the Rebellion page, whose two models genuinely are 6967mm. Taking the tile
would stretch a Rebel AWD by a metre.

The heights tell the same story in reverse and need watching:

| | tile | drawing | FMLV |
|---|---|---|---|
| Rebel RWD | 2.8m | 2780 | 2780 ✓ |
| Rebel AWD | 2.9m | 2900 | **2990** |
| Rebellion RWD | 3.05m | 3050 | 3050 ✓ |
| Rebellion AWD | 3.17m | 3180 | **3170** |

So FMLV's Rebel AWD height matches neither, and its Rebellion AWD matches the tile rather
than the drawing. Both are 2026 figures against a 2027 document, so a change is expected —
but a 10mm and a 90mm move are worth a reviewer's eye rather than silent acceptance.

**Width is published twice too**: `2020 mm` on the body and `2345 mm` across the mirrors.
The settled rule takes the body, and FMLV holds 2020.

## There is no self-check, because the payload is not published

Every model's payload reads **`TBC*`**, footnoted *"Payload is affected by additional
habitation options"*, and **no mass in running order appears anywhere in either brochure** —
only the GVW. So `MTPLM - MRO = payload` cannot be run, and this adapter would be as
lightly defended as Rolling Homes and Kaktus.

FMLV's four MROs and payloads came from the 2026 material and **cannot be maintained from
the 2027 brochures**. They would carry through untouched, which is right: a `TBC` is not a
figure.

## The GVW upgrades are priced options

`3,880kg GVW £505` on both RWD models and `4,400kg GVW £505` on the Rebellion AWD. The
base-vehicle rule records the base, so 3,500 and 4,100 — which is what FMLV holds.

## The Rebel Raid is a named edition with no specification

The brochure's own contents page reads **`2027 Specification REBEL RWD AWD RAID`**, and
page 23 prices it: **`Special Edition Rebel Raid - £199,995`**. The text calls it *"the
Special Edition Rebel Raid AWD"*, so it sits on the AWD platform.

The settled rule is explicit that **a named edition is a product** — *"if that extra
package comes with a different name to it, like Special or Anniversary version, then it's a
different model"*. On that test the Raid is a fifth product, and FMLV does not hold it.

**But pages 24 to 26 carry no technical figures at all** — no GVW, no dimensions, no belts
or beds of its own. Creating it would mean inferring every required field from the Rebel
AWD, which is a guess on a brand-new product rather than a reading.

**Recommendation: collect the four and report the Raid, rather than proposing it as new.**
A new product with guessed masses is worse than a documented absence, and the requester's
own count is four. Ask RP for the Raid's technical data and add it properly.

## Verdict — build it

The brochures carry the price, the GVW, both lengths, the width, the heights, the belts and
the beds, in a table laid out identically across the two documents and fetchable per run.
Four live products are each about £21,000 adrift.

It would propose **nothing** for the mass in running order or the payload, which the 2027
brochures put at `TBC`.

---

# Built — 16 October 2026

`src/adapters/rp_motorhomes.py`, **NCC id 258**. Four fetches: a range page and its 2027
brochure, twice over.

## Run #188 — the first one

```
baseline    4 products
scraped     4 products
classified  4 changed, 0 unchanged, 0 new, 0 disappeared
proposed    30 changes, of which 4 are year bumps
verified    26 fields checked and unchanged
```

**Six real corrections, and four of them are the prices:**

| | FMLV held | 2027 brochure | |
|---|---|---|---|
| Rebel RWD | 126,000 | **147,000** | +21,000 |
| Rebel AWD | 134,000 | **155,000** | +21,000 |
| Rebellion RWD | 136,000 | **157,000** | +21,000 |
| Rebellion AWD | 148,000 | **170,000** | +22,000 |

**£85,000 of price correction across four products**, which is the largest any adapter
here has delivered on a first run.

The other two are heights, both on the AWDs: **Rebel AWD 2990 → 2900** and **Rebellion AWD
3170 → 3180**. Both are 2026 figures meeting a 2027 drawing, so a change is expected — but
the 90mm move is worth a reviewer's eye rather than a nod.

## Reading the drawing, never the tile

The one thing this adapter has to get right. Each dimension is published twice and the
tiles are wrong: the Rebel's read `5.9m` and `7.0m` where **both** its drawings say
`5932 mm`, and FMLV holds 5932 for both. The `7.0m` looks copied from the Rebellion page.

So nothing is read from the tiles except the **GVW**, which they give cleanly on a line of
their own and the drawings do not give at all.

The drawing's six figures are assigned without trusting their order:

* the **widths** by size — 2020mm body against 2345mm across the mirrors, and the settled
  rule takes the body;
* the **heights** by magnitude, because an all-wheel-drive Sprinter sits higher on the same
  body. Position could not be trusted: the captions beneath the drawings run AWD first and
  then RWD, the reverse of the figures above them;
* the **length** only where both drawings agree. They do on both ranges; if one ever gave
  two there would be nothing to say which belonged to which model, since the tiles have
  already been shown wrong.

## Four fields deliberately not proposed

* **The payload**, which reads `TBC*` on every model, footnoted *"Payload is affected by
  additional habitation options"*.
* **The mass in running order**, which neither brochure publishes anywhere — only the GVW.
* **The berths and the seats.** The tiles state them as bare digits that run into the
  figure beside them in the extracted text — `2.9m2 2` — so neither reads reliably. FMLV
  holds 2 and 2 on all four and they carry through.

With no payload and no running-order mass there is **no arithmetic self-check**, so the
check here is structural: a price above what any option on the page costs, a GVW inside the
band a Sprinter is plated in, and a body width narrower than the figure across the mirrors.

## The Rebel Raid is reported, not collected

`Special Edition Rebel Raid - £199,995`, found and priced on every run. A named edition is
a product under the settled rule and FMLV does not hold it — but pages 24 to 26 carry no
technical figures at all, so every required field would be inferred from the Rebel AWD.
The run names it and asks for its data instead of creating a product with guessed masses.

## To ask RP Motorhomes

1. **The payload and the mass in running order** for all four, which read `TBC` throughout.
2. **The Rebel Raid's technical data**, so it can be added as the product the naming rule
   makes it.
3. **The Rebel AWD's length** — the summary tile says 7.0m where the drawing says 5932mm.
   Worth telling them the tile is wrong.
