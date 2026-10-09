# Mini Freestyle — survey, 7 October 2026

**NCC id 222.** `fmlv_manufacturer` **`Trigano`**, display name **`Mini Freestyle`**.
**Caravans only**, and very small ones. **Adapter written 8 October 2026.**

## The join key, and the two other Triganos

**`Trigano` is the manufacturer; `Mini Freestyle` is the display name**, exactly as Hobby
is to AURA. The requester gave the name as "Mini Freestyle, two words, no hyphen" — which
is right for the *display* name, and the export settles the rest.

**Trigano is not unique**, which `atom.md` predicted in September: the NCC list holds
**187 Trigano / Silver** and **278 Trigano / Atom** as well. All three coexist because the
adapter key is `(manufacturer, display name, vehicle class)` — but `fmlv_manufacturer`
must be `Trigano`, and a row that says `Mini Freestyle` would find an empty baseline.

## What FMLV holds

| id | display | year | | state | type |
|---|---|---|---|---|---|
| **7234** | Mini Freestyle | 2026 | Mini / 270 | live | `pop_up` |
| **7235** | Mini Freestyle | 2026 | Mini / 290 | live | `pop_up` |
| **7698** | Mini Freestyle | 2026 | Mini / 300 | live | `pop_up` |
| 7777 | Mini Freestyle | 2025 | Sport / 300 | **deactivated** | `pop_up` |
| 7237–7239 | **Silver** | 2023–24 | Trend / 350, 380, 442 | archived | `micro` |

**Three live products.** The Silver rows are id 187's and drop out on the display name.

## Body type: rigid, settled 7 October 2026

The site calls them **pop top caravans** and describes a **pop-up roof**, and FMLV holds
`type_pop_up` on all four Mini Freestyle rows. **The requester ruled rigid**, and the
reasoning is that FMLV's `Pop Up` means a folding camper — a pop *top* is a rigid caravan
with a roof that raises, which is a different vehicle.

**Micro was considered and rejected on the naming half of the test.** The word `micro`
appears nowhere on the site, and `docs/adapters/README.md` requires the maker to name it
one as well as it being light. (Note the archived *Silver* Trends are `micro`, which is a
different brand's decision and not a precedent here.)

So three live products would move from `pop_up` to `type_rigid`.

## The range names stay as FMLV has them

The site groups its four models under two nav headings — **Minis** (270, 300) and
**Silver** (290, 442), the latter headed *"EXCLUSIVE LINE: FREEDOM, WITH ADDED COMFORT"*,
with the 442 at `/en/exclusive-line-442.html`.

**That is a marketing grouping, not a model name** — the same shape as Freedom's "Classic
Range", which was settled the same day. FMLV files the 290 under `Mini` and it stays
there. Reusing "Silver" as a range would also collide confusingly with NCC id 187, which
*is* Silver.

**So the site's roster is four and FMLV's live set is three**: the **442 is new**.

## The source is the catalogue, with one caution

`/files/2026/Minifreestyle_catalogue_2025_EN.pdf` — note the hrefs on this site are
**relative**, so the `files/` prefix is easy to lose and the URL 404s without it. The file
is dated August 2025 in its own text and in its name, while sitting under `/2026/`.

It carries exactly the table FMLV wants:

```
BERTHS                           2        2
Overall length                3,95     4,42
External body length          2,99     3,47
Internal length                2,5     2,97
Internal height               1,87     1,87
Overall width                 2,03     2,03
Internal width                 1,9      1,9
Overall height (roof closed)  1,98     1,98
Overall height (roof open)    2,33     2,33
Empty weight                   600      688
Mass in running order          641  695/807
Max authorized weight          750      750
```

**The caution: only ~6,000 characters extracted from a 524 KB file**, so some pages are
images. Every model's column must be confirmed to survive extraction before anything is
built — a missing column here is the cardinality failure `README.md` warns about.

Note `Mass in running order` carries **two values on one model** (`695/807`), and
`Administrative payload modification 750/1200` is a chassis upgrade option — the settled
rule takes the standard figure, never the upgrade.

## The self-check is weaker than usual, and that is worth knowing

Three masses are published — empty weight, mass in running order and max authorised weight
— but **no payload**, so there is no single arithmetic identity to test a parse against.
Only that the three are ordered sensibly. Say so at the build checkpoint rather than
implying otherwise.

## Model pages

`/en/mini-freestyle-270.html`, `/en/mini-freestyle-290.html`,
`/en/mini-freestyle-300.html` and `/en/exclusive-line-442.html` — note the fourth is named
differently from the other three. `/en/Minis.html` and `/en/exclusives.html` are the two
range indexes, and `/en/pop-top-caravans.html` is prose.

## Both checkpoint questions, answered 8 October 2026

### The tables extract cleanly, and the catalogue is only four pages

Not a 500-page catalogue with image tables, as the byte count suggested — **four pages**,
two of which carry a full spec table in extractable text. Page 2 is the Minis and page 4
the Silver line, each laying two models side by side:

| | page 2 | | page 4 | |
|---|---|---|---|---|
| | **270** | **300** | **290** | **442** |
| Overall length | 3,95 | 4,42 | 4,42 | 5,91 |
| External body length | 2,99 | 3,47 | 3,47 | 4,88 |
| Internal length | 2,5 | 2,97 | 2,97 | 4,4 |
| Overall width | 2,03 | 2,03 | 2,03 | 2,03 |
| Overall height (roof closed) | 1,98 | 1,98 | 1,98 | 2,03 |
| Overall height (roof open) | 2,33 | 2,33 | 2,33 | 2,33 |
| Internal height | 1,87 | 1,87 | 1,87 | 1,95 |
| Empty weight | 600 | 688 | 676 | 925* |
| Mass in running order | 641 | 695 | 693 | 942* |
| Max authorized weight | 750 | 750 | 750 | 1050 |
| BERTHS | 2 | 2 | 2 | 3 |

**Models are identified by overall length**, because the column headings are *graphics* —
`MINI 270`, `MINI 300`, `MINI 290`, `MINI 442` are set as styled artwork and never reach
the extracted text. So 3,95 is the 270, 5,91 the 442, and the two 4,42 columns are the 300
(Minis page) and the 290 (Silver page).

**Confirmed twice over.** FMLV's own figures match every pairing to the millimetre, and the
requester supplied screenshots of the printed pages on 8 October 2026 showing the headings
above exactly those columns. The mapping is the manufacturer's, not an inference.

**Every dimension matches FMLV exactly** on all three live models — shipping, body,
internal, width, berths and MTPLM, six fields apiece, no exceptions. That is as strong a
confirmation as a survey gets that this document is where FMLV's figures came from.

### The 442 is the archived Trend 442 returning

Conclusive on mass and dimension, which is what the rename rule requires: shipping
**5910** and body **4880** match FMLV's archived `7239` to the millimetre, berths 3 agree,
and the mass in running order is **942** against FMLV's **943**.

**But it is archived under the display name `Silver`, which is NCC id 187** — a different
manufacturer from this one. So reviving it is a cross-manufacturer question rather than
something this adapter can propose, and its FMLV row has errors besides: an internal
length of 1950 that merely repeats its width, against the catalogue's 4400, and an MTPLM
of 1200 where the catalogue now says 1050.

## Decided before the build

**The mass in running order does not match, on any model.**

| | catalogue MiRO | catalogue empty | FMLV |
|---|---|---|---|
| 270 | 641 | 600 | **583** |
| 290 | 693 | 676 | **676** |
| 300 | 695 | 688 | **612** |

Only the 290 lines up, and with the *empty weight* rather than the MiRO. An adapter
proposing the catalogue's figure would change all three. The catalogue is explicitly
*"valid at the time of printing (August 2025)"* while FMLV's rows are model year 2026, so
FMLV may hold newer figures from a source we have not seen. **This is the blocking
question.**

**Both height fields look wrong in FMLV.** All three hold **2330**, which is the
catalogue's *roof-open* height, in `height_mm` **and** in `headroom_mm`. The roof-closed
height is 1980 and the internal height is 1870. Freedom settled the equivalent question by
taking the roof-down figure as the height, which would make these 1980 and 1870.

**There is no price anywhere** — not in the catalogue, not on the site. FMLV holds
£13,994.99, £14,995 and £14,994.99, so they came from elsewhere and an adapter cannot
maintain them.

**The model pages are empty.** `/en/mini-freestyle-270.html` and its siblings carry no
figure at all, so the catalogue PDF is the only source and a run is one or two fetches.


## The build, 8 October 2026

**Source:** the catalogue PDF alone. Two fetches per run — the home page, to rediscover
the catalogue, and the catalogue itself.

**Read page by page, never as one document.** Both spec tables share every row label, so a
search across the joined text finds only the first table's — which silently gave the 290
the 300's masses and lost two models entirely. `ExtractedPdf.pages` is what makes it work.

**The two 4,42 m columns are told apart by their page**: the 300 among the Minis, the 290
on the Silver page, which is the only one carrying an awning row. They differ in exactly
one figure — the mass in running order, 695 against 693 — so getting it wrong would be
invisible in every other field.

### Run #146

4 scraped against 3 baseline — **3 changed, 0 unchanged, 1 new, 0 disappeared**, 36
proposals, 27 fields verified unchanged. Every proposal is one of the decisions above:

| | |
|---|---|
| `body_type` | `pop_up` → `rigid` on all three |
| `height_mm` | 2330 → **1980**, the roof-closed figure |
| `headroom_mm` | 2330 → **1870**, the internal height |
| `mro_kilograms` | 583 → 641, 676 → 693, 612 → 695 |
| **442** | arrives new, with every field |

### Prices

**Carried over, and not maintainable.** There is no price in the catalogue or on the site,
so the adapter proposes none and FMLV's existing three stand. The requester is writing to
Mini Freestyle to ask them to check them.

## The 442 is withdrawn — 9 October 2026

Mini Freestyle told the requester the **442 is no longer in the range**, and it is still
on their website and still in the catalogue this adapter reads. Their word settles it: it
is not collected, and it is **not to be uploaded as a 2027 model**.

This reverses the plan of 7 October, when the intention was to bring the deactivated 442
back by reusing product 7239. `EXPECTED_LAYOUTS` is **3**, and `WITHDRAWN` carries the
reason so a run says out loud why a model in the source is being passed over.
