# Wildax (id 16)

Surveyed 2026-09-23. **Campervans only** — every one of the 18 models states
`Type: Campervan`, and there is no coachbuilt, no A-class and no caravan anywhere on the
site. A UK manufacturer, based in West Yorkshire, building on Fiat, Ford and MAN.

- Source: <https://wildaxmotorhomes.com/>
- NCC supplier name: `WildAx Motorhomes`
- `fmlv_manufacturer`: `Wildax` — the spelling in the NCC list, id 16. The supplier list
  spells it `WildAx Motorhomes`, with the capital A. **They are different strings and both
  are right**; see the settled rule about one name per company per role.

## The site is not the one the name suggests

`wildax.co.uk` is **a Boston Terrier breeder in Merseyside**, copyright 2026, and it
resolves and returns 200. It is not a stale domain and nothing about the response says
"wrong site" — the first fetch of this survey landed there and the page's own title is
`About Wildax`.

The motorhome company is at **`wildaxmotorhomes.com`**. Worth writing down because the
obvious domain is not merely wrong but confidently wrong.

## Everything is in the static HTML

WordPress with Alpine.js. The Alpine hydrates behaviour, not content: the spec tables, the
habitation positions and the whole price list are all server-rendered and readable with the
plain `Fetcher`. **No browser is needed.** Pages are 310–560 KB.

Eight range pages, each carrying every model in that range:

| range | path | models |
|---|---|---|
| Aurora | `/aurora` | Aurora, Aurora Leisure, Aurora XL, Aurora Leisure XL |
| Europa | `/europa` | Europa, Europa XL |
| Pulsar | `/pulsar` | Pulsar |
| Solaris | `/solaris` | Solaris 6m, Solaris XL |
| Constellation | `/constellation` | Constellation 3, Constellation 4, Constellation 3 XL, Constellation 4 XL |
| Equinox | `/equinox` | Equinox, Equinox 4x4 |
| Meteor | `/meteor` | Meteor 165 |
| Altair | `/altair` | Altair RS, Altair RL |

**Eighteen models**, which matches the requester's "eight ranges, several models each".

`/vehicle_model/<slug>` URLs exist and are linked from the homepage, but they carry **no
spec panel at all** — 459 lines and nothing in them. The range pages are the source.
`/browse/all` is dealer stock, new and used, and is not a roster.

## What each model publishes

Every model has an `Essentials Spec.` panel giving, in order:

```
Range          Constellation      MTPLM          3500 kg
Model          3                  MRO            3040 kg
Type           Campervan          Est Payload    460 kg
Chassis        Fiat Ducato        Length (m)     6 m
Bodystyle      High Top           Width (m)      2.05 m
Bed type       Lounge Conversion  Height (m)     2.7 m
Berths         2
Seatbelts      3                  Lounge         Front
Layout type    End Kitchen/Wash.  Kitchen        Rear Side
Gearbox        6-Speed Manual     Shower/Toilet  Rear Side
Engine         140BHP             Sleeping area  Front
Drive side     Right-Hand Drive
```

That covers every field FMLV holds for a campervan, and the last four lines are the
**habitation findings free of charge** — lounge, kitchen, washroom and sleeping area
positions, stated by the manufacturer rather than read off a drawing. `Sleeping area` uses
exactly FMLV's own vocabulary (`Front`, `Rear`), so it needs no interpretation.

`Chassis` reduces to the base vehicle under the settled abbreviation rule: `Fiat Ducato` →
`Fiat`, `MAN TGE` → `MAN`, `Ford` → `Ford`.

## The self-check: Est Payload = MTPLM − MRO

WildAx publish all three, and the arithmetic is FMLV's own payload formula. **Fifteen of
the eighteen reconcile exactly.** The three that do not are each informative rather than
alarming:

| model | MTPLM | MRO | stated | MTPLM − MRO | reading |
|---|---|---|---|---|---|
| Constellation 3 XL | **3496** | 3058 | 442 | 438 | the MTPLM is the typo |
| Aurora XL | 3500 | 3013 | **485** | 487 | the payload is the typo |
| Altair RL | 3500 | 3190 | **306** | 310 | undetermined |

The first two are settled by their siblings. `Constellation 4 XL` has the *same* MRO of
3058 and states MTPLM 3500 and payload 442 — so 3496 is a slip for 3500, and the stated
payload proves it. `Aurora Leisure XL` has the same MRO of 3013 and states 487, so Aurora
XL's 485 is the slip. Altair RL has no sibling sharing its MRO and is off by 4 with no way
to tell which figure moved.

Payload is derived (`MTPLM − MRO`) under the settled rule regardless, so the published
figure is only ever the check. Worth keeping the mismatch narrated rather than silent.

## The price list exists — it is just not where it looks

**This is the answer to the requester's main concern.** No price appears beside any model,
which is what he saw. But the `Pricelist` item in the nav opens an off-canvas panel
(`#offcanvas-pricelist-modal`) whose **full contents are in every page's HTML**, on all
eight ranges. 38 priced lines, in sterling, plus an options list.

```
Constellation Manual        Fiat   £73,495
Constellation Auto          Fiat   £75,995
Constellation XL Manual     Fiat   £74,495
Altair RS Auto              MAN   £101,995
Meteor (Blue) 130 Manual    Ford   £72,495
Equinox 4x4 (Grey) 165 Man. Ford   £83,495
```

There is also a `Brochure` link, but it is a **Heyzine flipbook**
(`heyzine.com/flip-book/cc9e801007.html`), not a PDF. Nothing in it is needed — the site
carries everything.

### But the price list and the model list are keyed differently

The price list is keyed on **drivetrain, engine and paint**; the model list is keyed on
**layout**. They do not line up one to one, and that is the one real design decision in
this adapter:

- **Constellation 3 and Constellation 4 share a single price row.** The price list knows
  only `Constellation` and `Constellation XL`; the 3 and the 4 differ by seatbelt count,
  not by price. Same for the XL pair. So four models draw on two price rows.
- **Meteor is priced four ways** — Blue/Grey × 130 Manual/165 Auto, £72,495 to £74,495 —
  and there is only one model, whose panel says `130BHP` and `6-Speed Manual` while its
  name says `165`.
- **Pulsar and both Altairs are priced only as automatics**, while their spec panels state
  `6-Speed Manual`. No manual price is published for them at all.
- **Equinox's Grey is cheaper than its Blue** at 130 Manual (£72,995 against £73,495) and
  dearer at 165 Manual. Not an error to correct, just not monotonic.
- `Altair Sport Upgrade £7,400` is an option, not a vehicle, and must not become a product.
- `Equinox (Grey) 165 Auto £76,492` is very likely £76,495. It does not affect any base
  price.

Under the settled base-vehicle rule — record the base, not the optioned variant — the price
for each model is **the lowest published price in its group**: manual over automatic,
cheaper paint over dearer, smaller engine over bigger. That gives all 18 models a price:

| model | price | from |
|---|---|---|
| Aurora / Aurora Leisure | £73,495 / £74,495 | Manual |
| Aurora XL / Aurora Leisure XL | £75,495 / £75,495 | Manual |
| Europa / Europa XL | £74,495 / £74,995 | Manual |
| Pulsar | £75,495 | **Auto — no manual published** |
| Solaris 6m / Solaris XL | £73,495 / £74,995 | Manual |
| Constellation 3 / 4 | £73,495 | shared `Constellation Manual` |
| Constellation 3 XL / 4 XL | £74,495 | shared `Constellation XL Manual` |
| Equinox | £72,995 | Grey 130 Manual |
| Equinox 4x4 | £82,495 | Blue 130 Manual |
| Meteor 165 | £72,495 | Blue 130 Manual — **but the model is named 165** |
| Altair RS / RL | £101,995 / £104,495 | **Auto — no manual published** |

The two to put to the requester are **Meteor** (whether the £72,495 130 or the £73,995 165
is the vehicle FMLV holds) and **Pulsar/Altair** (whether an automatic-only price is the
guide price when the spec panel describes a manual).

## The Equinox is the one body-type question

Its panel states `Bodystyle: Elevating Roof`, 4 berths, 2.8 m high — but the options list
offers `Equinox add pop-top roof option £5,500`. Either the elevating roof is standard and
the option is something else, or the panel describes the optioned vehicle and the base
Equinox is a high top sleeping two.

Everything else is unambiguous: seven ranges state `High Top` and every height is 2.65 m or
more, well over the settled 2300 mm threshold.

## Seat belts are unqualified

The panel says `Seatbelts 3` or `Seatbelts 4` and nowhere states whether they are
three-point. The settled rule counts three-point belts only, and nothing on the site
mentions a lap belt. Recording the published figure is right unless the requester knows
otherwise for a specific model — flagging rather than assuming.

## Model year

Every page is headed `2026 Models`, the price list says the prices are correct at time of
publishing, and **2027 appears nowhere on the site**. The requester expects this to roll
over. `_is_current_model_year` keeps the current calendar year and the next, so 2026 is in
scope now and the adapter needs no change when 2027 lands — only the figures will move.

## Still needed before a build

**There is no FMLV export for id 16.** `data/exports/` has 41 manufacturers and Wildax is
not among them, so nothing here has been checked against what FMLV actually holds: not the
model names, not the range names, not the live count. Everything above is the source side
only.

## Fetches per run

Eight — one per range page. The price list rides along inside each of them, so it costs
nothing extra, and it can be read from the first page fetched and reused.
