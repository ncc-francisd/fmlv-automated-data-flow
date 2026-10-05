# Jerba Campervans — survey, 1 October 2026

**NCC id 11**, `fmlv_manufacturer` **`Jerba Campervans`**, display name **`Jerba`**, supplier
name the same as the manufacturer name. Campervans only. North Berwick, employee-owned,
converts three base vehicles. **Adapter written 1 October 2026** — `src/adapters/jerba.py`,
14 products, 11 fetches a run.

## The site publishes almost nothing a run can use

`https://www.jerbacampervans.co.uk` is plain server-rendered WordPress. No JavaScript is
needed, nothing is behind a login, and every page fetches on the first try. That is where
the good news stops.

All eight model pages and all three base-vehicle pages were fetched and searched. Between
them they carry:

| | on the site |
|---|---|
| price | **none** |
| MTPLM / MRO / payload | **none** |
| length, width, height | **none** (one page mentions internal widths) |
| berths, belted seats | prose only, e.g. "Belted seating for 4" |
| downloadable PDF | **none** |

The only `kg` figures anywhere are roof load limits — `100kg`, `150kg`. There is no
`payload`, `MTPLM`, `gross vehicle`, `kerb weight` or `mass in running order` on any page.

**So every number comes from documents the requester supplies**, the same position as
`joa.py`. The site is useful for *existence* and for habitation prose, not for figures.

### The base-vehicle pages are not rosters

`/vw-t7-campervan-conversions/`, `/ford-transit-custom-campervan-conversion/` and
`/vw-crafter-campervan-conversions/` each link **the same 13 model pages** and each mentions
all eight model names, because those links are site navigation. **Nothing on the site says
which layout is sold on which base vehicle** — only the price lists do.

### URL shapes are not uniform

Several models have two page URLs and the pattern does not hold across them —
`/tiree-campervan-layout/` and `/tiree-swb-campervan-layout/`, `/sanna-campervan-layout/`
and `/sanna-lwb-campervan-layout` (no trailing slash), `/taransay-campervan/` and
`/taransay-campervan-layout/`, `/mull-crafter-layout/`. A roster built from a URL pattern
will miss some; take it from the supplied documents instead.

## The products

**Three base vehicles.** The VW T7 and Ford Transit Custom share one layout brochure and
one set of five names; the Crafter has its own.

### VW T7 and Ford Transit Custom — five layouts, one brochure

The layout brochure covers both base vehicles together, which is why the same five names
appear under each. Figures below are the brochure's.

| layout | wheelbase | length | roof | belted travel seats | sleeping berths | record berths |
|---|---|---|---|---|---|---|
| Tiree | short | 5050 mm | front elevating | 5 | sleeps 2 / 4 | **2** |
| Cromarty | long | 5450 mm | front elevating | 5 | sleeps 2 / 4 | **2** |
| Sanna | long | 5450 mm | rear elevating | 4 | sleeps 2 / 4 | **2** |
| Taransay | short | 5050 mm | rear elevating | 4 | sleeps 2 / 4 | **2** |
| Jura | long | 5450 mm | **fixed high top** | 4 | sleeps 2 | **2** |

Also stated per layout: seat and bed width (Tiree/Cromarty `120/126cm`, the other three
`2 x 60cm / double bed`), fitted toilet (Tiree and Cromarty **no**, Sanna and Jura **yes**,
Taransay **optional**), and standard fitment of gas hob and sink, fridge/freezer box,
internal water tank, insulated floor and a full lithium system. Blown air heating, diesel
glass hob, hot water, roof rails, awning rail and solar panel are **optional** on all five
— the Jura is marked `X` for roof rails, meaning unavailable rather than optional.

**Body dimensions**, from the brochure's key: width **2062 mm** excluding mirrors and
2276 mm including them; record the one that excludes them. Closed-roof height is about
2068 mm and the fixed high roof about 2488 mm; **both want confirming against a readable
copy**, though either reading puts the Jura over the 2300 mm high-top threshold.

### VW Crafter — three layouts drawn, four sold

| layout | wheelbase | length | belted travel seats | sleeping berths | record berths | fridge |
|---|---|---|---|---|---|---|
| Mull | medium | 5986 mm | 4 | sleeps 2 / 4 | **2** | 61 litre |
| Barra | medium | 5986 mm | 5 | sleeps 2 / 4 | **2** | 51 litre |
| Harris | long | 6836 mm | 4 | sleeps 4 / 6 | **4** | 51 litre |

Seat and bed width: Mull `60cm`, Barra `129cm`, Harris `86cm and standard double`. Gas hob
and sink, fitted shower, fitted toilet, fresh and waste water tank, insulated floor and a
full 12v lithium system are standard on all three. The 230v system is standard on the Mull
only and optional on the other two. Diesel glass hob, hot water, cassette awning, solar
panel and the ATEC elevating roof are optional throughout.

**Body dimensions**: width **2040 mm** excluding mirrors, 2427 mm including them; height
**2590 mm**, so all of them are high tops.

**The fourth Crafter is a wheelbase variant the layout brochure does not draw.** The price
list sells a `MWB Harris` at GBP83,500 beside the long-wheelbase `Harris` at GBP88,500 —
different wheelbase, different length, GBP5,000 apart, so two products rather than one. Its
length will be 5986 mm if it follows the other mediums, but that is inference and wants
confirming.

## Prices — supplied lists, inc VAT

Jerba quote a **starting price** per base vehicle that already includes the factory
features they list, "a full tank of fuel, number plates and all VW charges — nothing is
hidden". That is an on-the-road price in our terms. Every transmission, paint and equipment
line in the same document is an **option** and is not recorded — the base vehicle figure is
the one to take.

| base vehicle | layout | roof / wheelbase | price inc VAT |
|---|---|---|---|
| VW T7 | Tiree | front elevating, SWB | GBP71,000 |
| VW T7 | Taransay | **front** elevating, SWB — see below | GBP73,000 |
| VW T7 | Cromarty | front elevating, LWB | GBP74,000 |
| VW T7 | Sanna | rear elevating, LWB | GBP75,000 |
| Ford Transit Custom | Tiree | front elevating, SWB | GBP69,000 |
| Ford Transit Custom | Cromarty | front elevating, LWB | GBP72,000 |
| Ford Transit Custom | Taransay | rear elevating, SWB | GBP71,000 |
| Ford Transit Custom | Sanna | rear elevating, LWB | GBP73,000 |
| VW Crafter | Barra | fixed high roof, MWB | GBP77,500 |
| VW Crafter | MWB Harris | fixed high roof, MWB | GBP83,500 |
| VW Crafter | Mull | fixed high roof, MWB | GBP85,500 |
| VW Crafter | Harris | fixed high roof, LWB | GBP88,500 |

The roof and wheelbase in the Ford list agree with the layout brochure on all four.

**The two lists disagree about the Taransay's roof.** The VW T7 list calls it a *front*
elevating roof; the Ford list calls it *rear*. Everything else about the two vans matches,
and the layout brochure gives the Taransay the same rear-elevating treatment as the Sanna
rather than the front-elevating one the Tiree and Cromarty get. So the Ford list is
probably right and the T7 list has a typo — **but one of the two documents is wrong and
this survey will not guess which.** Ask Jerba. Until they answer, the roof is a *finding*
on that product rather than a proposal, with both documents quoted.

### The VW T7 list, supplied 1 October 2026

"Volkswagen T7 Factory Options — Commerce Pro", supplied by the requester as a page image.
Its base-vehicle block is the four rows above, followed by a priced road-tax line and then
the transmission options.

**Two things corroborate the reading**, and this adapter has little else:

* **The roof and wheelbase agree with the layout brochure on all four**, exactly as the
  Ford list did — the self-check described at the end of this file, passing a second time.
* **Every T7 price is exactly GBP2,000 above its Ford twin**, on all four layouts
  (69→71, 72→74, 71→73, 73→75). A misread figure or a layout matched to the wrong price
  would almost certainly break that.

**What is *not* recorded from this document:**

* **First 12 months road tax, GBP345 (code T009).** It is a separate priced line, so the
  headline starting price stands as the figure — see the price rule in `README.md`.
* **Every transmission, drivetrain and paint line.** The standard 150bhp manual is
  GBP0, which is what makes it the base vehicle; the automatic (+GBP1,842), 4MOTION
  (+GBP4,788), PHEV (+GBP2,946) and BEV (+GBP7,830 to +GBP12,288) lines are options and
  do not become products.

**A lead on the missing weights, not a figure to record.** Every T7 drivetrain line is a
`T32` and the BEV lines are `T34`. In VW's naming that is the gross vehicle weight in
hundreds of kilograms — 3,200 kg for the diesel the price covers, 3,400 kg for the
battery-electric. If Jerba confirm the conversion is not re-plated, that is `MTPLM` for the
four T7 products, and the first hard weight anywhere in this manufacturer. **It must be
confirmed before it is recorded**: a model code is not a published specification, and
`README.md` does not allow a figure to be inferred from one.

## Open questions — none of them now block the build

1. ~~The VW T7 price list has not been supplied.~~ **Supplied 1 October 2026** — see above.
   Twelve of the products now have a price.
2. **Is the Jura still sold at all?** It was expected to be the fifth name on one list or
   both. It is on **neither**: the Ford base-vehicle block names four layouts and so does
   the T7's, and both move straight on to transmission options. So the Jura has a model
   page and a column in the layout brochure but no price in either list, and the count is
   **12 priced products, not 13 or 14**.

   Three readings fit, and only the requester or Jerba can say which: it is quoted on
   application, it is priced in a document not yet supplied, or it has been withdrawn and
   the site has not caught up. **Never invent a POA** — if it is still sold and still
   unpriced, it is a product recorded without a price, not a product with a made-up one.

   One caveat on the evidence: the supplied T7 copy is an image of the top of the page,
   cut off partway down the BEV rows. A second base-vehicle block below that would change
   this, though a high top listed under "Transmission" would be an odd document.
3. ~~No weights exist anywhere.~~ **Settled 1 October 2026: build without them.** The
   requester asked Jerba for weights and had no reply, and decided to proceed. MTPLM, MRO
   and payload are therefore **not emitted at all** — not emitted blank, which would wipe
   what FMLV holds, but omitted, which leaves it standing. See the missing-field rule in
   `README.md`.

   The T7 list's `T32`/`T34` codes remain a lead on MTPLM for four of the twelve — see
   above — and are the first thing to pick up if Jerba ever answer. They say nothing about
   MRO or payload, so even then the payload could not be derived.
4. **Are the belted travel seats all three-point?** Only three-point belts count — see
   `README.md`. "Belted seating for 4, tested to full Type Approval" reads like proper
   belts, but a lap belt in a rear bench would reduce the figure.

## What the requester holds

FMLV has **five** Jerba products. Expect **12** once the Ford, VW T7 and Crafter variants
are added — 13 if the Jura turns out to be sold and priced somewhere — so most of a first
run will be new products. No export has been taken yet.

`base_vehicle_manufacturer` is **`VW`** for the T7 and the Crafter and **`Ford`** for the
Transit Custom. Those are FMLV's own spellings, counted across the 44 saved exports: `VW`
on 23 rows and `Ford` on 342, with no "Volkswagen" anywhere. The column holds the marque
alone, so "T7", "Crafter" and "Commerce Pro" have nowhere to go but the provenance.

## The self-check, and that there isn't a strong one

`payload = MTPLM - MRO` is unavailable because none of the three figures is published.
The redundancy that *is* available is weak but real: **the layout brochure and the price
list independently state the wheelbase and roof type**, and they agreed on all four Ford
rows. Length follows wheelbase (5050 short / 5450 long on the panel vans, 5986 medium /
6836 long on the Crafter), so a length that does not match its stated wheelbase is a parse
error. That is the check to build on, and it should be said plainly that this adapter has
nothing as strong as the arithmetic self-checks elsewhere in this project.

## What the build settled

**Range and model — the other way up from the obvious guess.** FMLV files these by
**layout**: range `Tiree`, model `T7`. Not range `VW T7`, model `Tiree`, which is what this
adapter shipped with and which matched **none** of the five existing products — a run would
have added all fourteen as new ones beside them. Corrected 5 October 2026 against the
export:

| id | range | model | base vehicle |
|---|---|---|---|
| 8280 | Tiree | T7 | VW |
| 3992 | Tiree | Transit Custom | Ford |
| 8281 | Cromarty | Transit Custom | Ford |
| 3990 | Sanna | Transit Custom | Ford |
| 7959 | Mull | **Mull** | VW |

The marque lives separately in `base_vehicle_manufacturer` (`VW` or `Ford`), so `model`
carries the range designation rather than the make.

**`Mull / Mull` is a slip** — every sibling carries the base vehicle there. The adapter
emits `Mull / Crafter`, which still matches at 0.50 and proposes the correction. The
requester agreed on 5 October 2026.

**The two Crafter Harrises** would otherwise be one product, both `Harris / Crafter`, so
the medium-wheelbase one takes the range `Harris MWB`. FMLV holds neither yet, so this is
ours to choose.

**`manufacturer_range` and `model` carry provenance deliberately.** `compare_fields` only
examines fields the adapter records provenance for, so without it a wrong name in FMLV can
never be corrected by a run — which is exactly the state the Mull was in.

**What a run actually does.** Eleven fetches, one per distinct model page, contributing no
figures — the site has none. They exist to confirm each product still has a page. A page
that stops resolving is narrated as a warning and **the product is still collected**,
because the price list is the more recent document and a missing page is not a withdrawal.
That is the Carthago lesson: a gap in one source should not deactivate a vehicle that is
plainly on sale.

**The first live run**, 1 October 2026: all eleven pages resolved, 14 products built, the
Taransay roof disagreement reported, and no mass emitted on any product.

| | |
|---|---|
| products | 14 |
| priced | 12 — both Juras have none |
| with a length | 13 — the MWB Harris has none |
| masses emitted | **0**, by design |
| body types | 4 elevating-roof campervans, 10 high tops |

**Body type, derived not guessed.** The four elevating-roof panel vans sit at 2068 mm and
do not reach the 2300 mm threshold, so they are `type_campervan_elevating_roof`. The Jura
(2488 mm) and all four Crafters (2590 mm) clear it and are `type_campervan_high_top`. The
Crafters' **optional** ATEC elevating roof is deliberately ignored — an optional rising
roof never changes what the vehicle is, the same call `joa.py` makes about its pop-up.

**The seat count is proposed with a warning attached.** The brochure's `BELTED TRAVEL
SEATS` row says 4 or 5 but never says the belts are three-point, and only three-point belts
count. The figure is proposed with the uncertainty written into its provenance, so the
reviewer decides rather than it passing as settled.
