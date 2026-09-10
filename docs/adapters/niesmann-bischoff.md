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

## The build, and the first diff — 9 September 2026

**7 of 7 collected, no blank field on any of them, 133 fields with provenance, all seven
carrying a floorplan.** Diffed against the live export, scoped the way a run scopes it:

| | |
| --- | --- |
| collected | 7 |
| baseline | 6 |
| matched | 6 |
| new | 1 — `Arto 88` |
| **disappeared** | **0** |

No identity renames: the ranges and models the adapter emits match FMLV's strings exactly,
`6.9E` and `7.3F` included. No dimension or maximum-laden-mass change either — the API and
FMLV already agree on every one, which is the strongest evidence the parse reads the right
fields.

24 field changes across the six, and half of them fill a blank:

| n | field | |
| --- | --- | --- |
| 6 | `mro_kilograms` | **FMLV held none** |
| 6 | `mh_payload_kilograms` | **FMLV held none** |
| 6 | `rrp_pounds` | the year's rise |
| 6 | `mh_passenger_seats_inc_driver` | 4 → 2, or 3 → 2 on the Flair 920 |

**The seat correction is settled.** It is right by both standing rules — count three-point
belts only, and record the base vehicle rather than the optioned variant — and the
requester confirmed it on 9 September 2026 after reading the row himself: *"it clearly
states two seats are fitted with a three-point safety belt and option to have three, four
and five. So within our normal parameters, we would call that two. So that's a change from
the four that we have on FMLV."* Accept it on all six.

### Berths are derived, and the derivation is corroborated

The API states bed dimensions and never a berth count. Each dimension pair is one bed and
its width decides whether it sleeps one or two, at a 1,200 mm threshold that sits in a
545 mm gap — every Niesmann single is 730 or 735 mm and every double 1,280 or wider.

That gives **4 on all seven layouts, matching FMLV's 4 on all six existing products**,
including the iSmove 6.9 E whose rear is twin singles where the others have a double. The
requester approved the approach: *"the fact that there are two double beds is our best
guidance on the berths, so that would be four."* The provenance quotes the bed sizes, so a
reviewer can see the working.

### Two things the survey had not seen

**`thumbFilename` is not per-layout.** Flair 880 and 920 share `cart_flair_2022.png` and
both iSmoves share `cart_ismove.png`, so joining a drawing on it would give two products the
same floorplan. `imgGalleryFilename` is the per-layout one — `a78.png`, `flair_2023_880.png`
— and resolves under `/assets/02-grundrisse/`.

**The backend wraps its JSON in PHP output when it feels like it** — a notice ahead of the
document when a parameter is missing, and trailing output after it — so a plain
`json.loads` fails on a response that is otherwise perfectly good. The captured fixtures
happen to be clean, which is why the tests construct both cases rather than relying on them.

## Habitation — added 10 September 2026, and the flag that makes it honest

The requester noticed a new product arriving with no findings panel. The layout record
carries the numbers and nothing habitational, so the findings come from
`/data/technik?modell=…&grundriss=…&lang=en`.

**The configurator is an options catalogue, so `serie` is what makes it usable.** Every
item carries `serie: true` or `serie: false`, and reading the endpoint without that filter
would have been actively wrong rather than merely noisy:

| range | items | standard | what an unfiltered read would have said |
| --- | --- | --- | --- |
| Arto 78 | 34 | **7** | correct |
| Flair 880 | 37 | **0** | wet central, off a £2,308 floor-heating upgrade |
| iSmove 6.9 E | 44 | **0** | wet central, off a **£3,186 Alde 3030+** |

iSmove is the case worth remembering: its warm-water heating is an upgrade, so its
standard heating is something the endpoint does not publish at all. Reporting the option
would have put a wet system against a vehicle that very likely has blown air.

So **the three Artos get a heating finding and the other four get none** — honest, and the
alternative was worse. `/data/interieur` is the same story with nothing standard in it at
all: its drawer fridge and its 800-watt microwave are both priced extras.

### What the Arto's heating says

`Warm water heating with thermostat. control, heating cartridge and touch screen panel
(independent heating circuit in the rear bedroom)`, alongside `Engine heat exchanger` and
`Floor heating` — all three standard. That reads as **wet central**, and seeing it needed
two additions to the shared vocabulary: `warm water heating` beside Dethleffs'
`hot-water heating`, and `heating circuit`, which is plumbing by definition.

### The microwave note is narrower than the others'

Niesmann **do** sell one — `Microwave (230V, 800 watts, mounted behind cupboard door)` — so
the finding says it is not fitted as standard rather than that it cannot be had. The field
is set to `False` explicitly so `findings.SILENCE_MEANS` does not append its generic "no
mention anywhere" reasoning, which would be untrue here.

## Still unverified

* **Model year changeover.** Not established for this brand.
* **Whether `lang=en` alone gives the UK market**, or whether a market parameter exists that
  the bundle sets separately. The prices reconcile with FMLV, which is good evidence, but
  the bundle does contain market-switching logic worth reading before building.
