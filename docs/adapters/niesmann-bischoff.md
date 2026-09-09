# Niesmann + Bischoff — site survey

Surveyed 9 September 2026, not yet built. FMLV manufacturer id **13**, name
`Niesmann + Bischoff`, display name the same. NCC supplier name **`Niesmann + Bischoff
shown by Travelworld`** — verified by pulling the export with it, and note it names the
importer rather than the brand.

German, part of the Erwin Hymer Group, and the most expensive brand in the project: three
ranges, seven layouts, £110,220 to £208,800.

## What the requester brought to the survey

* *"Niesmann and Bischoff is within the configurator unfortunately. I looked for a simple
  brochure but I couldn't find it."* Correct, and the reason this one waited.
* **All three Artos are sold in the UK** — 78, 84 and 88 — from the English edition of the
  factory site. That matters because `Arto 88` is the one layout FMLV does not hold.
* **Travelworld cannot be used for price.** *"I don't think we can use the Travelworld
  website for prices because the vehicles — well, they say they're new, but they are
  different variants. I think we have to go from the manufacturer's spec rather than stock
  spec."*

## The source: the configurator's own JSON API

**Not** the shared EHG configurator that Eriba, Dethleffs, Bürstner and Carado use — this
is a bespoke React application. But the application is only a front end, and what sits
behind it is plain JSON with no login:

```
https://konfigurator.niesmann-bischoff.com/backend
    /data/grundriss?modell=Arto&lang=en                    the layouts in a range
    /data/technik?modell=Arto&grundriss=Arto%2078&lang=en   equipment, per layout
    /data/chassis  /data/aufbau  /data/interieur  /data/exterieur
    /data/pakete   /data/auflastung                        options and upgrades
```

The base URL and the parameter shape are **read out of the React bundle** at
`configurator.niesmann-bischoff.com/static/js/main.<hash>.js` rather than guessed. The
hash changes on every deploy, so an adapter has to discover the bundle from the
configurator page and the base URL from the bundle — the same rediscover-don't-hardcode
rule that applies to a PDF whose path carries a model year.

Note the host differs by one letter from the page's own: the app is served from
**c**onfigurator and the API from **k**onfigurator.

### One call gives almost everything

`/data/grundriss` returns every layout in a range, and each record carries:

| FMLV field | JSON |
| --- | --- |
| `rrp_pounds` | `price` |
| `mro_kilograms` | `weight` |
| `mtplm_kilograms` | `totalMass` |
| `mh_length_mm` / `width` / `height` | `length` / `width` / `height`, in mm with thousands commas |
| `mh_passenger_seats_inc_driver` | `seats` |
| the floorplan | `imgGalleryFilename`, `thumbFilename` |

plus a `details` list that is a **full technical specification** in `dt`/`dd` pairs:

```
Base vehicle                                   Fiat Ducato, Euro VI E
Chassis / Frame                                AL-KO low frame AMC 35L (opt.: AMC45H)
Wheel base (in mm)                             4,100
Overall length (in mm)                         7,295
Technically permissible laden mass (in kg)*    3,500 (opt.: 3,650 / 4,250 / 4,500)
Mass in running order (in kg approx.)*         2,983 (2,834 - 3,132)
Manufacturer-specified mass for optional equipment (in kg)*   319
Seats fitted with 3-point safety belt*         2 (opt. 3, 4 or 5)
Overhead front bed (length × width) (in mm)    1,870 x 1,300
Rear bed(s) (length × width) (in mm)           2,000 × 1,380
```

The `Manufacturer-specified mass for optional equipment` row is **not payload** — the same
trap as Dethleffs, Etrusco, Bürstner, Sunlight and Carado.

## The roster: 7 layouts, 3 ranges

| range | layouts | price |
| --- | --- | --- |
| `Arto` | 78, 84, **88** | £164,800 / £179,100 / £181,800 |
| `Flair` | 880, 920 | £207,000 / £208,800 |
| `iSmove` | 6.9 E, 7.3 F | £110,220 / £112,980 |

FMLV holds six of them; `Arto 88` is new, and the requester confirmed it is sold here.

Note the model strings differ in spacing: the API says `iSmove 6.9 E`, FMLV holds
`6.9E`. The range is the first word and the model is the rest, so the adapter must
normalise the space or propose a rename on every iSmove.

## The prices are sterling

This is the thing that had to be checked before anything else, because a euro price is the
worst data in the project (see [`morelo.md`](morelo.md)). With `lang=en` every figure lands
**1.7 to 4.4 per cent above what FMLV already holds** — a year-on-year rise. A euro figure
would be 15 to 20 per cent out.

| | API | FMLV |
| --- | --- | --- |
| Arto 78 | 164,800 | £162,100 |
| Arto 84 | 179,100 | £176,300 |
| Flair 880 | 207,000 | £202,900 |
| Flair 920 | 208,800 | £204,700 |
| iSmove 6.9 E | 110,220 | £105,570 |
| iSmove 7.3 F | 112,980 | £108,330 |

## The importer publishes nothing, so the factory is authoritative

`docs/adapters/README.md` says the UK importer decides what exists and what it costs. Here
it cannot: **`travelworld.co.uk` serves 114 bytes and its sitemap contains a single URL.**
`travelworldmotorhomes.co.uk` does not resolve.

The requester ruled on what that leaves: Travelworld's listings are individual **stock**
vehicles with their own option packs, so a price taken from one is the price of that
vehicle rather than of the model. FMLV records the manufacturer's specification. This is
the first manufacturer in the project where the factory rather than the importer is the
price source, and the reason is that the importer publishes nothing usable — not a change
to the rule.

## The self-check

**Every key figure is stated twice in the same response**: once as a structured field
(`weight`, `totalMass`, `length`, `width`, `height`) and again as a prose row inside
`details` (`Mass in running order (in kg approx.)* 2,983`). Two renderings of one record,
which is exactly what a `_reconciles()` wants and is stronger than an arithmetic check.

Secondary and weaker: the printed ±5% band, `2,983 (2,834 - 3,132)`. It is a function of
the mass, so it catches a misread digit and not a slipped field — the same limitation as
Eriba's and Laika's.

## What the first run will do

Worth knowing before it is run, because two of these are systematic:

* **It fills MRO and payload on all six.** FMLV holds **neither** for any Niesmann +
  Bischoff product — every one is blank today. The API supplies the mass in running order,
  and payload is `totalMass - weight`.
* **It will propose dropping the seat count from 4 to 2** on all six (3 → 2 on Flair 920).
  The API says `Seats fitted with 3-point safety belt* 2 (opt. 3, 4 or 5)`, and both the
  count-three-point-belts-only rule and the base-vehicle-figure rule make the standard
  figure 2. **Put this to the requester before accepting it** — it changes every listing,
  and 4 is what FMLV has shown customers until now.
* **`Arto 88` arrives as a new product.**

## Still unverified

* **Berths.** The API gives bed *dimensions* — an overhead front bed and rear bed(s) — but
  no berth count, and FMLV holds 4 for all six. Reading 4 from two double beds is
  inference, not a published figure, so confirm before relying on it.
* **The floorplan assets.** `imgGalleryFilename` and `thumbFilename` are bare filenames
  (`a78.png`, `cart_arto78.png`) and the bundle references `/assets/02-grundrisse/`; the
  full URL has not been resolved. Note `imageKey` is **not** per-layout — Flair 880 and 920
  share `F920`, and both iSmoves share `iS69` — so the key cannot be the join.
* **Model year changeover.** Not established for this brand.
* **Whether `lang=en` alone gives the UK market**, or whether a market parameter exists that
  the bundle sets separately. The prices reconcile with FMLV, which is good evidence, but
  the bundle does contain market-switching logic worth reading before building.
