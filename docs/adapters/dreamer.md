# Dreamer — survey, 11 November 2026

**NCC id 127**, `Dreamer`. **Stage 1 only. No adapter has been written, and I stopped
before writing one** — see "Why this is not an Itineo repeat".

Part of **Groupe Rapido** (Mayenne, France), alongside Rapido, ITINEO, Campéréve and
Fleurette. Panel-van conversions on Fiat and Ford. No caravans.

| | Dreamer |
|---|---|
| JavaScript needed | No — the specification table is plain HTML |
| FMLV holds | **16 products**, ranges `Fun` and `Select`, all priced |
| Site shows | **20 model pages**, 17 distinct models |
| The technical table covers | **9 columns** |
| Price | **In FMLV already**, £53,400–£81,700 on all sixteen |
| Self-check | `MIRO + payload == GVW` — holds on 8 of the 9 it reaches |

## What is good here

**The specifications are plain HTML**, not a Calaméo flipbook —
`fourgon-caracteristiques-techniques_dreamer.php` carries an ordinary `<table>` with
`<tr>`/`<td>`, which is the simplest source this project has met. No browser, no SVG, no
`dx` splitting:

```
Overall length                       5,41 | 5,41 | 5,41 | 5,99 | 5,99 | 5,99 | 5,99 | 6,36 | 6,36
Gross vehicle weight (GVW)           3,3 T | 3,3 T | 3,5 T | 3,3 T | 3,3 T | 3,3 T | 3,5 T | 3,5 T | 3,5 T
Mass in Running Order (MIRO) (kg)    2865 | 2889 | 2889 | 2885 | 2885 | 2940 | 2940 | 3000 | 2995
Payload (kg)                          435 |  411 |  611 |  415 |  415 |  360 |  650 |  500 |  505
Berths                              2 + 1 | 2 + 2 | 2 + 2 | 2 + 2 | 2 + 1 | 2 + 1 | 2 + 2 | 2 (O : + 2) | 2 + 2 + 1
```

It also carries registered seats, dining seats, wheelbase, every bed size and a long
equipment list, and it writes berths with the **options split out** — `2 (O : + 2)` — the
way Itineo does.

**`MIRO + payload == GVW` holds on eight of the nine**, so the self-check is real. The
ninth is Dreamer's own arithmetic: `2940 + 650 = 3590` against a published 3.5 T.

## Why this is not an Itineo repeat, and why I stopped

**The table reaches nine columns; FMLV holds sixteen products.** Worse, the three naming
schemes do not line up:

| source | model names |
|---|---|
| the technical table | `D42`, `D43`, `D43`, `D53`, `D55`, `D55`, `D55`, `D60`, `CAMPER FIVE` |
| the site's model pages | `d43`, `d55`, `d64`, `d68`, `capland`, `citycamp`, `camperfive`, `campersport`, `campervan-xl`, `capeasy`, `caplife`, `family`, `lift-van`, (+ `-up` and `-select` variants) |
| FMLV | `D43`, `D55`, `D62`, `D68`, `D43 UP`, `D55 UP`, `D68 UP`, `CAP LAND`, `CITY CAMP`, `CITY CAMP HYBRIDE`, `FAMILY`, `LIVING VAN`, `CAMPER VAN XL`, `CAMPER SPORT` |

**`D42`, `D53` and `D60` exist in the table and nowhere else** — not on the site's own
model pages, not in FMLV. **`D62`, `D68`, `CAP LAND`, `CITY CAMP`, `FAMILY`, `LIVING VAN`,
`CAMPER VAN XL` and `CAMPER SPORT` are in FMLV and not in the table.** The page is headed
`Vans DREAMER 2027` and FMLV's rows are all year 2027, so this is not a collection-year
mismatch.

Building against that would mean guessing which column belongs to which product, on a
table where every value is a plausible figure for any Dreamer. That is precisely the
alignment risk the Itineo adapter has a dedicated guard for — and here there is nothing to
check an alignment *against*, because the model pages carry **no figures at all**, unlike
Itineo's.

## The Calaméo route is closed

Itineo's masses came from a Calaméo technical guide. Dreamer's catalogue page
(`fourgon-dreamer-doc.php`) does mention one, and the form offers a *"Technical guide"*
checkbox — but:

* the three Calaméo URLs on that page sit **inside an HTML comment**, as legacy `FR/DE` and
  `FR/IT` editions; and
* **the publisher account is different.** Dreamer's book codes begin `0003556`; Rapido's
  and Itineo's begin `00769273`. So the group does **not** share one Calaméo account, and
  nothing about Rapido's parser can be assumed to transfer here.

The live route is a request form that emails the document, which is not something a run
can walk through.

## What FMLV holds

Sixteen products, every one year 2027, every one with a price and an MRO:

| range | models |
|---|---|
| `Fun` | D43 UP, D55 UP, D55, CAMPER SPORT, D68 |
| `Select` | CAP LAND, D55, D62, D68, FAMILY, CAMPER VAN XL, D68 UP, LIVING VAN, D43, CITY CAMP, CITY CAMP HYBRIDE |

`D55` and `D68` each appear in **both** ranges, so the range is part of the identity and
cannot be derived from the model code.

Base vehicles: Fiat, except CAP LAND, CITY CAMP and CITY CAMP HYBRIDE, which are Ford.

**The export read for this survey is dated 5 August 2026** — three months old. Anything
about the current FMLV state should be re-checked against a fresh one before a run.

## What has to be settled before building

1. **Which nine products the technical table's columns are.** Without that the masses
   cannot be attached to anything.
2. **Where the other seven get their masses**, if anywhere.
3. **A fresh FMLV export.**

One and two are a question for Dreamer, who are in the same group as two manufacturers
already answering us.
