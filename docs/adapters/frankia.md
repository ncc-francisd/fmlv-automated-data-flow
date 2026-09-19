# Frankia (id 111)

Surveyed 2026-09-19. **Motorhomes only** — A-class and coach built, no campervans and no
caravans. High-end, and a large range: 38 live baseline rows across eight FMLV ranges.

- Source: <https://www.frankia.com/en/motorhomes-recreational-vehicles>
- NCC supplier name: `Frankia`
- `fmlv_manufacturer`: `Frankia`

Same UK distributor as Globecar (id 83). Frankia itself is a German manufacturer and
frankia.com is the factory site; there is no UK site and no sterling price anywhere.

## What the requester supplied

Given on 2026-09-19, and all of it confirmed:

- `Frankia` for both the manufacturer and supplier name, exactly as spelt — id 111.
- Each model has a summary, then "view details" gives specifications. Confirmed.
- There are download brochures, "but I'm not even sure you'll need them". **They are
  needed, and for two different things** — the price list for the mass in running order,
  and the Highlights Magazine for the MY2027 roster, which is published nowhere else.
- Motorhomes only, A-class and coach built. FMLV agrees.
- Prices are in euros, so they need the conversion.
- **"We did a manual update of Frankia recently and re-added the year 2027 … it needs
  checking. It was more of a placeholder than having come from a valid source. It was
  simply what was on the website at the time and we called it 2027 about a month ago."**

That last point turns out to be the crux of the survey.

## Two candidate sources, and only one has the mass in running order

**The website's per-layout block** is good but incomplete. Each model page carries a
`Technical Overview` per layout:

```
Platform         Mercedes-Benz • Sprinter 415
Total height     296 cm
Total width      224 cm
Total length     699 cm
Max allowed load 3,500 | 4,500 kg
Sleeping places  2
Seats with seatbelts  4
Price from       106,900 €
```

It states **no mass in running order at all** — the page's footnotes define the term but
never give a figure. MRO is the one field FMLV holds for all 38 live rows.

**The German price list PDF** has it, per layout, in columnar tables:

```
Masse in fahrbereitem Zustand, kg    2.9531  2.9001  3.1651  3.1121
Technisch zulässige Gesamtmasse, kg   4.500   4.500   4.500   4.500
```

`/fileadmin/user_upload/infomaterial/preisliste_2026_deutsch_final_p2_ok_neu_WEB.pdf`,
linked from every model page.

**And it is demonstrably the document FMLV was built from.** Those four NEO figures are
FMLV's to the kilogram — MT 7 GDK 2953, MT 7 BD 2900, MI 7 GDK Black Line 3165, MI 7 BD
Black Line 3112 — and the price list names the layouts *the way FMLV does*
(`MT 7 GDK NEO`, `MI 7 GDK NEO BLACK LINE`), not the way the website now does.

Shape for the build: `morelo.py`, a price list PDF with columnar spec pages.

## The 2027 range is published, and it is a big contraction

**Corrects the first pass of this survey**, which listed
`highlights_2027_englisch_ok_ok_ANSICHT.pdf` and dismissed it as "a highlights brochure
with no weights" *without opening it*. The requester pointed at it. It is 44 pages, and
pages 42 and 43 are a spread headed **ALL MODELS AT A GLANCE** — the definitive MY2027
roster, which nothing else on the site states.

Twenty layouts across five ranges:

| range | layouts |
|---|---|
| NOCTRA | Cruiser 7.6 L (x2, Fiat and Mercedes), Liner 7.6 L **NEW**, Liner 8.3 L **NEW** |
| NEO | Cruiser 7.0 L, Cruiser 7.0 B, Liner 7.0 L, Liner 7.0 B, Liner 6.6 H **NEW** |
| NOW | Cruiser 7.0 L |
| FINAL EDITION | I 640 SD, I 740 GD, I 790 GDW, I 7400 GD, I 7400 PLUS, I 7900 GD |
| TOGETHER | A 680 PLUS, I 680 PLUS, A 740 PLUS, I 740 PLUS |

**There is no TITAN, no PLATIN, no F-LINE and no M-LINE in MY2027.** FMLV holds 26 live
rows across those four ranges. The brochure is still dated `© Copyright 2026` and the
footer confirms `FRANKIA is a PILOTE Group company`.

The old ranges have not simply vanished — they have been redistributed, and the layout
codes make the mapping legible:

| FMLV live row | MY2027 |
|---|---|
| F-Line `I 640 SD`, `I 740 GD` | **FINAL EDITION** I 640 SD, I 740 GD |
| Titan `I 790 GDW` | **FINAL EDITION** I 790 GDW |
| M-Line `I 7400 GD`, `I 7400 Plus` | **FINAL EDITION** I 7400 GD, I 7400 PLUS |
| Platin `I 7900 GD` | **FINAL EDITION** I 7900 GD |
| F-Line `A 680 Plus`, `A 740 Plus`, `I 680 Plus`, `I 740 Plus` | **TOGETHER** A/I 680/740 PLUS |
| Neo `MT 7 GDK` / `MT 7 BD` | **NEO Cruiser** 7.0 L / 7.0 B |
| Neo `MI 7 GDK Black Line` / `MI 7 BD Black Line` | **NEO Liner** 7.0 L / 7.0 B |
| Now `7.0 L` | **NOW Cruiser** 7.0 L |

So FINAL EDITION is a run-out drawing one or two layouts each from F-Line, Titan, M-Line
and Platin, and the rest of those four ranges — roughly 20 FMLV rows — is genuinely
finishing. **Do not evidence any of these pairings on length alone**; see the rename rule
in `docs/adapters/README.md`. The codes agree here, which is stronger, but the masses
still need checking per pair before a rename is declared.

## The model year problem, restated

Three documents disagree about what year it is, and each has exactly one thing the others
lack:

| source | year | roster | dimensions, berths, seats, price | **MRO** |
|---|---|---|---|---|
| Highlights Magazine | **2027** | **definitive** | no | no |
| Model pages | mixed | partial | **yes** | **no** |
| Price list PDF | **2026** | 2026 only | yes | **yes** |

**Nothing published states a mass in running order for MY2027.** The price list is the
only document that carries MRO at all, it is `P2-2026` / `MODELLE 2026`, and no 2027 price
list exists — `/en/information-material` publishes exactly one downloadable brochure, the
2027 Highlights.

That the 2026 price list is nevertheless the right source for *its* rows is not in doubt:
its NEO figures are FMLV's to the kilogram (MT 7 GDK 2953, MT 7 BD 2900, MI 7 GDK Black
Line 3165, MI 7 BD Black Line 3112) and it names layouts the way FMLV does.

So the requester's judgement was right twice over: the 2027 label reflects a real,
published range, and it "needs checking" because no priced or weighed source backs it yet.

## Traps

**`Nutzlast` is not FMLV's payload.** The price list defines it as MTPLM minus MRO minus
passengers minus options, and works the example itself: `3.500 − 2.950 − 225 − 65 = 260`.
FMLV's payload is MTPLM − MRO, which would be 550. Never record `Nutzlast`. This is the
same trap as Knaus, Weinsberg and T@B — a German-manufacturer habit, not a Frankia quirk.

**Footnote markers are glued to the values.** `2.9531` is 2.953 kg with footnote 1, and
`3.8601` is 3.860. Every mass in the tables carries one. Reading the digit as part of the
number gives a 29-tonne motorhome, so this has to be stripped explicitly.

**The website states two permissible masses**, `Max allowed load 3,500 | 4,500 kg`, where
the price list gives each variant its own column and its own price. FMLV records 3500 for
`MT` layouts and 4500 for `MI`, which is the base-vehicle rule applied — take the lower
where both are offered.

**Prices are euro and German-market**, stated on the page as "non-binding recommended
prices for the German market". Conversion at the requester's 1.15 euros per pound, as for
T@B.

**Base vehicle is published as `Mercedes-Benz • Sprinter 415`.** FMLV holds `Mercedes` and
`Fiat`, per the settled abbreviation rule, so the platform string needs reducing to the
make.

**One navigation link mixes languages**:
`/en/wohnmobile-reisemobile/together/frankia-together-overcab` sits among the `/en/`
links with a German path segment. A roster built by pattern-matching `/en/motorhomes-…/`
silently drops the Together Overcab.

## The self-check

The price list prints a **±5% production tolerance band** with every mass in running
order — `fertigungsbedingte Abweichung von +/- 5 % in kg 147,5` against 2.950 — which is
the same redundancy `knaus.py` and `weinsberg.py` use, and it verifies the parse per
column.

There is a second and stronger one available on the first run: the price list's MRO agrees
with FMLV on the four NEO layouts checked by hand, so a wholesale disagreement would mean
the parse has gone wrong rather than the data having changed.

## Fetches per run

Around ten: the range index, eight model pages for the roster and the website-only fields,
and the price list PDF.

## First run — #109, 2026-09-19

16 scraped against 37 baseline: **13 changed, 3 new, 24 disappeared**, 96 proposals and
112 fields verified unchanged.

The three new products are **Noctra Liner 7.6 L, Noctra Liner 8.3 L and Neo Liner 6.6 H**
— exactly the three the Highlights Magazine marks `NEW`, which is the roster transcription
checking out against the diff.

All eleven declared moves landed on their predecessors and proposed the new name:

| matched FMLV row | proposed |
|---|---|
| Neo `MT 7 GDK` / `MT 7 BD` | `Cruiser 7.0 L` / `Cruiser 7.0 B` |
| Neo `MI 7 GDK Black Line` / `MI 7 BD Black Line` | `Liner 7.0 L` / `Liner 7.0 B` |
| Now `7.0 L` | `Cruiser 7.0 L` |
| F-Line → `Final Edition` | I 640 SD, I 740 GD |
| Titan → `Final Edition` | I 790 GDW |
| F-Line → `Together` | A 680 Plus, A 740 Plus |
| Together `I 740` | `I 740 Plus` |

### Three of the 24 disappearances are false

**`M-Line / I 7400 GD`, `M-Line / I 7400 Plus` and `Platin / I 7900 GD` are continuing
models**, listed in the 2027 roster as Final Editions. Only the three *Fiat* Final Editions
have a page, so no figures can be read for the Mercedes three and they fall out unmatched.

The run names them and says not to deactivate them. The other 21 are genuine: the rest of
F-Line, M-Line, Titan and Platin, which MY2027 does not carry.

### Two traps that only the live run exposed

Both dropped a layout silently on the first attempt, and both now have a test.

- **The NOW page appends a tagline** to its heading — `FRANKIA NOW 7.0 L – A NOW AGE OF
  SPACE` — so an exact match lost the layout. Matching now tolerates a prefix, and refuses
  an ambiguous one.
- **The Noctra Cruiser is a two-column block.** Mercedes and Fiat sit side by side, every
  label carries two values, and only the last carries the unit (`Total height` → `314`,
  then `312 cm`). Reading `lines[i + 1]` produced a bare `314` that parsed as nothing, and
  the whole block came out empty.
