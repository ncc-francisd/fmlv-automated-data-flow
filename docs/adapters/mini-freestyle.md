# Mini Freestyle — survey, 7 October 2026

**NCC id 222.** `fmlv_manufacturer` **`Trigano`**, display name **`Mini Freestyle`**.
**Caravans only**, and very small ones. No adapter yet — this is the stage-1 checkpoint.

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

## Still to decide at the build checkpoint

1. Whether the catalogue's tables survive extraction for all four models.
2. Whether the 442 arrives as a new product or is the archived Silver/Trend 442 returning
   under a new badge — the masses will tell, per the rename rule.
