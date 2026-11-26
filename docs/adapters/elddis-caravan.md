# Elddis touring caravans — site survey

Surveyed **and built** 26 November 2026, after the `Riviera` range turned up in the
motorhome adapter's roster and was filtered out of it. The adapter is
`src/adapters/elddis_caravan.py`; five layouts collected, none dropped.

FMLV manufacturer id **8**, `fmlv_manufacturer` **`Elddis (EHG UK)`** — the same row the
motorhome adapter uses, so this is a **second product area on an existing row**, the shape
`adria_caravan.py` already has.

## The headline: Elddis have not released this range

The five Riviera layouts are in the configurator API and **flagged as not published**:

| layout | available | availableForWebsite | price | floorplan | MTPLM | MRO | length | berths |
|---|---|---|---|---|---|---|---|---|
| Riviera 580 FL | false | false | — | — | 1800kg | 1265kg | 7170mm | 4 |
| Riviera 590 SDW | false | false | — | — | 1800kg | 1310kg | 7330mm | 3 |
| Riviera 600 FDB | false | false | — | — | 1800kg | 1315kg | 7330mm | 5 |
| Riviera 640 LS | false | false | — | — | 1800kg | 1335kg | 7650mm | 4 |
| Riviera 660 IU | false | false | — | — | 2000kg | 1380kg | 7840mm | 4 |

That is why the requester could not find it on the website and could only find social
media posts: `elddis.co.uk` links no Riviera page, and the API says why. The homepage
range-link scan the motorhome adapter runs finds no slug matching it either.

**They are collected and emitted anyway**, on the requester's instruction: *"it looks
like we're going to have to enter those as new models, but yeah, build them, and then the
moment they go on their website we will activate them, and probably not before."* FMLV's
staging state is an inactive product, not an absent one, so the right place for an
unlaunched model is a row somebody has created and not yet switched on. The adapter
narrates the flag it read, once per layout, so a reviewer knows to leave the product
inactive:

```
[Riviera 580 FL] NOT YET PUBLISHED BY ELDDIS: the configurator flags this layout
`availableForWebsite: false` and publishes no price and no floorplan, and elddis.co.uk
links no page for it. It is collected so the product can be created in FMLV ready to go,
and it should be left INACTIVE until Elddis put it on their site
```

## FMLV's Elddis caravan area exists, and is entirely switched off

The NCC supplier dropdown carries **three** Elddis entries — `Elddis Motorhomes`,
`Elddis Campervans` and `Elddis Caravans`. The caravan export returns **63 rows**:

* **43 archived**, every one of them model year 2022–2025.
* **20 not archived**, all model year 2026 — `Crusader` (8), `Avante Apex` (6),
  `Whirlwind` (3), `Whirlwind Evolve` (3) — and **all 20 are `active = false`**.

So **no Elddis caravan passes the baseline filter**: nothing is both active and of the
current model year. A caravan run today would diff against an empty baseline and propose
everything it found as new. See `docs/adapters/README.md`, "A relisted product comes back
as new".

Per the settled rule a deactivated product is never archived and is kept findable on
purpose, so these 20 are a decision for the requester, not something an adapter should
touch.

## Riviera is a new range, not a rename of the Whirlwind caravans

Worth settling now, because the 2026 rows are deactivated and a careless match would
reactivate the wrong ones. Applying the rename rule — **match on mass, never on a
dimension**:

| FMLV 2026 (deactivated) | MTPLM | MRO | shipping length |
|---|---|---|---|
| Whirlwind 520 | 1500 | 1214 | 6697 |
| Whirlwind 550 | 1550 | 1286 | 7475 |
| Whirlwind 554 | 1550 | 1316 | 7475 |
| Whirlwind Evolve 840 | 2000 | 1568 | 8188 |
| Whirlwind Evolve 860 | 2000 | 1550 | 8188 |
| Whirlwind Evolve 868 | 2000 | 1565 | 8188 |

Not one Riviera mass in running order matches any of them, and no length matches either
— the Rivieras are 7170/7330/7650/7840, the 2026 range 6697/7475/8188. Different chassis
lengths and different masses means a different range.

## The source is the configurator API, and the plumbing already exists

Identical to the motorhome side — `adapters/ehg_configurator.py` plus the readers in
`elddis.py`. No browser, no PDF, no price list:

```
/configurator-api/brand/elddis/series        -> Riviera, vehicleType=caravan, modelYear 2027
/configurator-api/series/4653583/models      -> five layouts with technicalData
```

`technicalData` carries, per layout: `sleepingBerths`, `weightGrossVehicle` (MTPLM),
`weightRoadworthy` (MRO), `manufacturerSpecifiedWeightForOptionalEquipment`,
`lengthOverall` (cm), `widthOverallwithoutMirrors` (cm), `heightOverall` (cm),
`headroomLivingArea` (cm), `tireSize`, socket counts, and `technicalDataBed` with bed
widths and lengths.

**The self-check is the payload identity**, as on the motorhome side: MTPLM − MRO against
`manufacturerSpecifiedWeightForOptionalEquipment` where present. On the 580 FL,
1800 − 1265 = 535 against a stated optional-equipment allowance of 438 — the two are
different quantities, so this needs confirming on a released layout before it is relied
on.

## What is not published, and what is unverified

* **No price.** `grossPrice` is `null` on all five.
* **No floorplan or photograph** — `layoutImage` is `null`, the same gap the motorhome
  adapter reports.
* **No nose weight.** `trailingLoadMax` and `trailingLoadMaxUnrestrained` are present but
  empty on all five. Nothing in the payload carries a hitch or nose load.
* **No awning size**, no internal length, no axle count.
* **Body type** is `null`, which for a caravan is expected — the settled rule is rigid
  unless the walls fold, and nothing here says otherwise.
* **Whether `Elddis Campervans` is a real third export.** It timed out on 26 November
  rather than returning. The GTV campervans are known to sit in the *motorhome* export
  (`Autoquest Apex` holds 8 motorhomes and 4 campervans), so this is probably empty or
  duplicative — but it has not been read, and the Panama lesson is that a second supplier
  entry can hold products the first does not.
* **Whether Elddis will publish a price list** of the kind the motorhome side gets its
  figures from.

## The registry row carries both product areas

Two edits on the existing row 13, `Elddis (EHG UK)`, made 26 November 2026:

* `ncc_supplier_name_caravan` is **`Elddis Caravans`** — read off the NCC dropdown and
  confirmed by the requester, not guessed. `ncc_supplier_name` was left as
  `Elddis Motorhomes` on the day and **corrected to `Elddis Campervans` later the
  same day** — see below.
* `categories` is **`motorhome,caravan`**.

**`Elddis Campervans` is deliberately unused.** The GTV campervans sit in the *motorhome*
export — `Autoquest Apex` holds 8 motorhomes and 4 campervans — and that third entry timed
out twice rather than returning anything on 26 November. It is probably empty or
duplicative, but it has not been read, and Panama is the precedent for a second supplier
entry holding products the first does not.

## What the first live run found

```
model year 2027: 7 series in the catalogue, 1 of them touring caravans — Riviera
[Riviera] 5 layout(s)
[Riviera 580 FL] read: 4 berth, MTPLM 1800kg less mass in running order 1265kg,
                 giving a payload of 535kg, 7170mm shipping length
collected 5 Elddis caravan(s)
```

All five reconcile. Each carries berths, both masses, a derived payload, shipping length,
width, height, headroom and a rigid body type, plus bed types and a sleeping area as
findings. None carries a price, and **none carries `twin_axle`** — the payload states no
axle count, and the field is a `bool` defaulting to `False`, so recording no provenance
for it is what keeps "we did not look" from reaching FMLV as "it has one axle".
