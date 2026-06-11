# Casa EP — 3D Walkthrough

An interactive, game-style 3D reconstruction of the **Casa EP** residence
(project by DB Arquitetos / David Bastos, presentation **R01**), built from the
floor plans on pages 2–4 of the PDF: *Pav. Térreo*, *Pav. Superior* and
*Subsolo*, calibrated to the confirmed **40 × 35 m lot**.

## How to open it

**Easiest:** download **[`casa-ep-3d-tour.html`](casa-ep-3d-tour.html)** and
double-click it. It is fully self-contained (Three.js is embedded) and works
offline in any modern browser — no install, no server.

**Dev version:** `index.html` + `vendor/` is the same app with the library kept
as separate files. Because it uses ES-module imports it needs to be served over
HTTP (e.g. `npx http-server` in this folder); it won't open via `file://`.

## Controls

| Action | Input |
|---|---|
| Look around | Click the scene, then move the mouse (ESC releases) |
| Walk | `W` `A` `S` `D` or arrow keys |
| Run | hold `Shift` |
| Switch floor instantly | `E` (up) / `Q` (down) — or walk the real stairs and ramps |
| Overview / dollhouse mode | `V` or the **Overview** button |
| Room name labels | `L` or the **Labels** button |
| Jump to any room | **Teleport** dropdown (grouped by floor) |
| Touch devices | left joystick = move, right joystick = look |

In **Overview** mode you can orbit/zoom the whole property and hide the roof,
upper floor or ground floor to peek inside like a dollhouse.

## What's modeled

The full site section as drawn: the garden/house podium sits a level above the
street, which slopes along the south edge. From the street you can walk:

- **up the vehicle ramp** into the covered ground-floor garage,
- **down through the portal** into the semi-open **subsolo parking court**
  under the garden (pilotis, slatted ceiling, the pool's basin hanging
  through the slab),
- or **up the garden stair** beside the ramp onto the pool deck.

Rooms (as named on the plans):

- **Pav. Térreo:** Gourmet (open pavilion with the 10-seat round table),
  Cozinha + Depósito/Despensa/Lavabo, Brinquedoteca, Academia, Suíte 04 +
  Banho, Escada (walkable U-stair up + flight down), Sala de Jantar,
  Sala de Estar, Garagem, Piscina + deck and courtyard garden
- **Pav. Superior:** Offices 01/02, Estar Íntimo (overlooking the
  double-height gourmet void), louvred south gallery, Suíte 03 + Banho/Closet,
  Home, Suítes 01/02 + Banhos/Closets, and the **master block cantilevering
  over the pool deck**: Suíte Master, Closets Master 01/02, Banho Master,
  with the wood-slat band and cascading planter from the façade renders
- **Subsolo:** parking court, Garagem (enclosed), Dormitórios + Banhos de
  Serviço, Estar Serviço, Área de Serviço, Depósitos, Área Técnica

All walking routes (stairs between the three levels, both street ramps, the
garden stair) are verified walkable by automated tests.

## Photoreal renders (Blender / Cycles)

`blender/casa_ep.py` path-traces realistic images of the same project
(output in [`renders/`](renders/)). **Note:** these renders are from an
earlier iteration with smaller proportions — they predate the 40×35 m
calibration and the street/ramp modeling, and will be regenerated.

## Caveats

This is a visualization aid, not a CAD model. The lot, levels, room layout and
adjacencies follow the drawings at the calibrated scale; wall positions are
read from the presentation plans (±20 cm) and finishes/furniture are
indicative. Some printed area labels in the PDF disagree with the drawn
geometry (they appear to be from an earlier revision); the drawing was taken
as the source of truth. Use the architect's documentation for anything
dimensional.
