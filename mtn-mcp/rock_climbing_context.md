# Rock Climbing Context

This document gives an AI assistant the domain knowledge needed to reason about rock climbing data — grades, disciplines, gear, protection, tick styles, and crag culture.

---

## Disciplines

**Sport climbing** — Routes with pre-drilled bolts. The leader clips a quickdraw to each bolt as they ascend, clipping the rope through the bottom carabiner. Falls are relatively safe (short, controlled). Grades use the YDS system (5.0–5.15d). The main risk is a ground fall if the first bolt is high.

**Traditional (Trad) climbing** — No pre-placed protection. The leader carries removable gear (cams, nuts, hexes) and places it into cracks as they climb. The follower cleans (removes) the gear on the way up. Grades use YDS. Trad is the dominant style at crack-heavy crags like Tahquitz, Joshua Tree, and Yosemite. Often multi-pitch.

**Bouldering** — Short problems climbed without a rope, usually 10–20 feet. Falls are onto a crash pad. Grades use the V-scale (V0–V17). No protection placed — pure movement problems. Scraped from Mountain Project with `type=boulder`.

**Top-rope (TR)** — The rope runs through an anchor at the top of the route before the climber starts. Falls are immediately caught — the climber never falls more than a few inches. Common for beginners or hard routes being rehearsed. A route labeled only `TR` on Mountain Project is a top-rope-only route (no lead anchors exist).

**Multi-pitch** — A route with more than one rope-length (pitch). Each pitch ends at a ledge or anchor where the leader belays the follower up, then leads the next pitch. Tahquitz routes are commonly 5–7 pitches. Pitch count matters for comparing effort — a 7-pitch 5.10 is a much bigger day than a single-pitch 5.10.

**Aid climbing** — A climbing style where the climber uses gear directly for upward progress rather than only for protection. Instead of free climbing every move, the climber stands in aid ladders (etriers) attached to gear placements such as cams, nuts, pitons, or copperheads. Common on extremely steep or blank big walls where free climbing is impossible or significantly harder.

Aid grades use the A-scale (traditional aid) or C-scale (hammerless clean aid), typically ranging from A0/C0 to A5/C5:
- A0 / C0 — occasional pulling on gear or bolts
- A1 / C1 — straightforward, secure placements
- A2 / C2 — more difficult or awkward placements
- A3 / C3 — many body-weight placements with potential for long falls
- A4 / C4 — dangerous, unreliable placements where falls may be serious
- A5 / C5 — extreme aid climbing with little or no reliable protection

Aid climbing is strongly associated with Yosemite big-wall climbing (El Capitan, Half Dome). Many aid routes are also climbed free at much harder YDS grades. Mountain Project may label routes as `Aid`, `Trad, Aid`, or include aid ratings alongside free-climbing grades.

---

## YDS Grading System (Yosemite Decimal System)

Used for all roped climbing (sport, trad, TR). Invented at Tahquitz Rock in the 1950s.

| Range | Description |
|---|---|
| 5.0–5.7 | Beginner. Easy angle, large holds. |
| 5.8–5.9 | Intermediate. 5.9 was historically the hardest grade when the system was created. |
| 5.10 | Subdivided a/b/c/d. 5.10a is notably easier than 5.10d — a huge gap in difficulty. |
| 5.11 | Solid intermediate-advanced. Most gym climbers plateau here. |
| 5.12 | Advanced. Requires dedicated training. |
| 5.13 | Expert. Elite athletic performance. |
| 5.14+ | World-class. Very few routes. |
| 5.15 | Cutting edge. Extremely rare. |

**Modifiers:**
- `a/b/c/d` — subdivide grades 5.10 and above. `5.10a` < `5.10b` < `5.10c` < `5.10d`.
- `+/-` — sometimes used instead of letter subdivisions for older grades (e.g., `5.9+`).
- `R` — runout. Sparse protection; a fall could be long or dangerous.
- `X` — extremely sparse protection. A fall will likely cause serious injury.
- `PG-13` — somewhat sparse protection, more serious than standard.

## Grade Ordering

YDS grades are ordinal, not numeric strings.

Correct ordering:
5.8 < 5.9 < 5.10a < 5.10b < 5.10c < 5.10d < 5.11a

Incorrect string ordering:
5.10 < 5.9

For analytics, grades should be normalized to a sortable scale.

---

## V-Scale (Hueco Scale) — Bouldering

| Grade | Description |
|---|---|
| VB / V0 | Beginner. |
| V1–V3 | Intermediate. |
| V4–V6 | Solid intermediate. |
| V7–V9 | Advanced. |
| V10–V12 | Expert. |
| V13–V17 | Elite / world-class. |

Boulder grades on Mountain Project appear as `V0`, `V3`, etc. in the `Grade` column of the routes CSV.

---

## Tick Styles

A "tick" is a logged ascent of a route. The `Details` field in the ticks CSV begins with a style tag:

| Style | Meaning |
|---|---|
| `Lead / Onsight` | First-ever attempt, no prior knowledge of moves, climbed clean (no falls, no rests). The highest achievement. |
| `Lead / Flash` | Climbed clean on the first attempt but with prior knowledge (beta) — e.g., watched someone else climb it. |
| `Lead / Redpoint` | Climbed clean after prior attempts (falls allowed on earlier tries). |
| `Lead / Pinkpoint` | Climbed clean with pre-placed gear (rare distinction that mainly applies to trad). |
| `Lead / Fell/Hung` | Led the route but fell or rested on the rope. Did not complete cleanly. |
| `TR` | Top-roped. Rope from above; falls immediately caught. |
| `Follow` | Climbed second on a rope after the leader placed protection. Common on trad and multi-pitch routes. The follower removes ("cleans") the gear during the ascent. |
| `Solo` | Climbed alone with no rope. Extremely serious. |
| `Boulder` | Bouldering ascent. |

Multi-pitch ticks include `· X pitch` in the Details (e.g., `Lead / Redpoint. · 5 pitch`). The `parse_pitches()` function in `ticks_analysis.py` extracts pitch count from this field.

---

## Crag Terminology

- **Crag** — A climbing area. Could be a single cliff, a canyon, or a loose geographic cluster of routes. E.g., "Tahquitz," "Joshua Tree Hidden Valley," "Mission Gorge."
- **Route** — A specific line up a cliff with a name, grade, and type. Identified on Mountain Project by a URL slug (e.g., `illusion-dweller`).
- **Wall / Sub-area** — A named section of a crag, e.g., "Tahquitz - North Face," "Sentinel - W Face." The `areas` CSV captures this hierarchy.
- **Tick** — A logged ascent of a route. One climber ticking a route once = one tick.
- **Beta** — Information or advice about how to climb a route (hold sequences, gear placements, rests).
- **Send** — A successful clean ascent (no falls, no rests on gear).
- **Project** — A route a climber is working on across multiple sessions.
- **Rack** — A climber's collection of protection gear for a given route.
- **Anchor** — Fixed point(s) at the top of a route where the rope is secured.
- **Belay** — The act of managing the rope for a climber to catch falls.

---

## Crack Climbing and Technique

Crack climbing is the defining technique for trad climbing. Crack width determines both the technique used and the gear required.

| Crack type | Width | Technique |
|---|---|---|
| Thin finger | 7–15 mm | Fingertips only, first knuckle inserted |
| Finger crack | 15–28 mm | 1–2 knuckles inserted, twist to lock |
| Ring lock / thin hand | 28–42 mm | Wrist torqued, ring finger creates lock |
| Hand crack | 38–55 mm | Full hand jam — thumb tucked, heel of hand locks. The most comfortable and "classic" crack style. |
| Fist crack | 65–90 mm | Fist inserted, fingers flex outward to grip |
| Off-width (OW) | 90–200 mm | Arm bars, chicken wings, knee locks — awkward and widely disliked |
| Chimney | 200 mm+ | Entire body inside the crack; back on one wall, feet on the other |

Hand cracks are widely considered the most enjoyable crack style. Off-widths are widely disliked. A climber recommending gear for a hand crack is recommending a very different set of cams than for an off-width.

---

## Protection: Cams

Cams (spring-loaded camming devices, SLCDs) are the primary trad protection. They are inserted into cracks and expand to grip the walls when loaded.

### Black Diamond C4 (industry standard, double-axle)

| Size | Color | Range (mm) | Crack type |
|---|---|---|---|
| 0.3 | Blue | 13.8–23.4 | Finger |
| 0.4 | Gray | 15.5–26.7 | Finger |
| 0.5 | Purple | 19.6–33.5 | Finger–ring lock |
| 0.75 | Green | 23.9–41.2 | Ring lock |
| #1 | Red | 30.2–52.1 | Ring lock–hand |
| #2 | Yellow | 37.2–64.9 | Hand |
| #3 | Blue | 50.7–87.9 | Hand–fist |
| #4 | Gray | 66.0–114.7 | Fist–OW |
| #5 | Purple | 85.4–148.5 | OW |
| #6 | Green | 114.1–195.0 | OW |

The #1 and #2 are the most-used cams; many climbers carry doubles or triples of each. The BD Z4 extends coverage below the C4 down to 7.5 mm (sizes #0–#0.75) for very thin seams.

### Totem Cam (independent lobes, excellent in flares and pin scars)

| Size | Color | Range (mm) | Approx C4 equivalent |
|---|---|---|---|
| 0.50 | Black | 11.7–18.9 | C4 0.3 |
| 0.65 | Blue | 13.8–22.5 | C4 0.4 |
| 0.80 | Yellow | 17.0–27.7 | C4 0.5 |
| 1.00 | Purple | 20.9–34.2 | C4 0.75 |
| 1.25 | Green | 25.7–42.3 | C4 1 |
| 1.50 | Red | 31.6–52.2 | C4 1–2 |
| 1.80 | Orange | 39.7–64.2 | C4 2 |

Totems only cover finger-to-hand range (up to ~64 mm / C4 #2). No Totem covers fist or off-width. Their independent lobe design self-equalizes in flared or uneven cracks — a significant advantage at granite crags like Joshua Tree where cracks are often polished and slightly flared.

### Nuts / Stoppers

Passive (no moving parts) wedge-shaped metal pieces slotted into constrictions in a crack. Lighter and cheaper than cams. Effective in horizontal cracks and constrictions where cams cannot fit. Common sizes (e.g., BD Stopper #1–#13) cover roughly 6–37 mm.

---

## Protection: Fixed Gear

- **Bolt** — A metal expansion anchor drilled into the rock. Found on sport routes and at sport anchors. Permanent; the leader clips a quickdraw to it.
- **Piton (pin)** — A metal spike hammered into a crack. Largely obsolete for leading but leaves behind "pin scars" — small holes or flared spots in cracks — which affect gear placement (Totems excel here).
- **Fixed nut / fixed cam** — Gear left in place by a previous party (often stuck, sometimes intentionally left). Not to be relied upon.

---

## Route Types on Mountain Project

The `Type` field in the routes CSV reflects Mountain Project's tagging:

| Type value | Meaning |
|---|---|
| `Trad` | Traditional — leader places removable gear |
| `Sport` | Bolted — leader clips bolts |
| `Boulder` | Boulder problem — no rope |
| `TR` | Top-rope only — no lead anchors exist on the route |
| `Trad, Sport` | Mixed — has both gear placements and bolts |
| `Alpine` | High-altitude mountaineering context |
| `Aid` | Climber hangs on gear for upward progress (not free climbing) |

A route labeled `Trad, Sport` often means it can be led either way, or that the crux section has a bolt while the rest requires gear.

---

## Crags in This Dataset

Current most of the crags in mtn-data/ are in Southern California, Northern California, Arizona, or Joshua Tree. The scraper collects both rock routes and boulder problems for each crag. Trad climbing dominates at Tahquitz and Joshua Tree; sport climbing is more common at Mission Gorge and Mt. Woodson; bouldering is tracked at all crags.

Key characteristics:
- **Tahquitz / Suicide Rock** — Granite, Idyllwild CA. Multi-pitch trad. Historic routes; where YDS was invented.
- **Joshua Tree** — Granite, high desert. Crack climbing, bouldering. Very popular trad crag.
- **Mission Gorge / Mt. Woodson** — San Diego. Sport-dominant, single-pitch.
- **Malibu Creek** — Conglomerate, LA area. Mixed sport/trad.

---

## Tick Count Bias

Tick counts do not directly measure route quality or difficulty.

High tick counts may reflect:
- easy access
- beginner-friendly grades
- classic status
- proximity to urban areas
- guidebook popularity
- historical significance

Remote or dangerous routes may have low tick counts despite being highly regarded.

---

## Style Hierarchy

In traditional climbing culture, ascent styles are valued differently.

Generally:
Onsight > Flash > Redpoint > Pinkpoint > Fell/Hung > TR

Leading is generally considered a higher commitment style than following or top-roping. A clean "Send" is considered when a climber free climbs a pitch (doesn't use any aid) and doesn't fall or hang on the rope (Onsight, Flash, Redpoint, Pinkpoint are all types of "Sends").

A climber may tick a route multiple times in different styles across multiple sessions.

---

## Sandbagging

A "sandbagged" route is widely considered harder than its assigned grade.

Older trad areas (Tahquitz, Joshua Tree, Yosemite) are notorious for sandbagged grades.

Modern sport areas tend to have more consistent grading.

---

## Tick Parsing Examples

Example tick:
Lead / Redpoint. · 3 pitches. Fun hand crack. Took gear from 0.5–3.

Parsed:
- Style: Lead / Redpoint
- Pitch count: 3
- Route type likely: Trad
- Gear sizes mentioned: 0.5–3
- Crack style: Hand crack

---

## Classic Routes

A "classic" route is a highly regarded climb known for quality movement, aesthetics, history, or position.

Classic routes often accumulate disproportionately high tick counts.