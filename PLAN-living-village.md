# Dekot Living Village — Plan

Direction: warm isometric pixel-art village, watched from a phone browser,
backed by the one authoritative Python engine. The renderer animates
smoothly between engine ticks; the engine alone decides outcomes.

## What it will feel like

A riverside village fills the screen: mud houses with tiled roofs, narrow
paths, paddy plots, grazing cows, a banyan tree, the river along one edge.
Light shifts from morning to evening; lamps glow at night. Ten named
villagers (and their children) walk to their plots, bend to farm, follow
the herd, carry rice to neighbours, gather beside the good plot when a
dispute breaks out, and go home to sleep. Tap a villager for their card
(age, activity, health, food, family, closest relationships). Tap an event
to jump to the people involved. A "since your last visit" recap catches
you up. One small clock, population count, and pause/speed controls float
over the scene; charts live behind a Village Records button.

## Architecture decisions (settled)

1. **The engine owns space.** Agents gain `pos`, `dest`, and `activity`
   (sleeping, walking, farming, herding, eating, carrying, disputing,
   idle). Movement advances per tick along deterministic straight-line
   grid steps. This is simulation state: seeded, replayed, checkpointed,
   fingerprinted — same guarantees as everything else.
2. **The client owns motion.** The server reports each agent's position,
   destination, activity, and seconds-per-tick; the page tweens walks,
   loops work animations, ripples water, and fades daylight from the
   tick fraction. No gameplay decisions client-side.
3. **All art is procedural.** Tiles and sprites are drawn into offscreen
   canvases at load (16px pixel-art tiles, 4-frame walk cycles,
   palette-swapped clothing per villager). No image files, no CDN assets —
   the same page works served by `dekot serve` and as a recorded artifact.
4. **Two builds of one page.** The live page polls `/state`; the artifact
   build embeds a recorded run and a timeline. The renderer is shared.

## Phases

### Phase 1 — Space in the engine
- Widen the map to a 24×16 tile layout: river, paths, one home per
  founding household, plots (existing x,y), grazing field, banyan.
- Agent `pos`/`dest`/`activity`; a `_move` step in `_act` before work;
  meals at home or in the field, rest at home, disputes gather at the
  good plot.
- Tests: replay byte-identical, mid-day save/resume with positions,
  fingerprint updated, no agent occupies an impassable tile.
- Exit: `events.jsonl` unchanged in meaning; `/state` can report space.

### Phase 2 — Server surface
- Snapshot gains positions, activities, destinations, tick fraction,
  and a `since=seq` parameter for recap digests.
- Exit: `curl /state` shows a walking village in numbers.

### Phase 3 — The scene (first visible build)
- Isometric canvas renderer: tile drawing, depth sort, day/night tint,
  animated water; villagers rendered at their positions.
- Ship as a **recorded artifact first** — viewable on the phone
  immediately, no server needed — then wire the same renderer into the
  live page.
- Exit: the 20-year seed-34 run plays as an animated village.

### Phase 4 — Life and touch
- Interpolated walking, work/carry/dispute poses, tap-a-villager card,
  tap-an-event camera focus, "since your last visit" recap
  (localStorage high-water mark), Village Records drawer reusing the
  household view.
- Exit: everything in "What it will feel like" works on a phone.

### Phase 5 — Polish (as simulation features arrive)
- Weather, festivals on piety days, richer buildings, herd behaviour,
  AI-written diaries when the LLM milestone lands.

## Risks and answers
- **Pixel art quality from code**: constrain the palette (6 colours per
  sprite), 16px grid, test on the phone early — Phase 3 artifact exists
  precisely to judge this cheaply.
- **Battery/perf**: one canvas, requestAnimationFrame capped at 30fps,
  pause rendering when the tab is hidden, poll at half the tick rate.
- **Determinism drift**: movement lives in the engine and under the
  existing 1,000-seed invariant tests; the renderer can be wrong but
  never the village.

## Order of work
Phase 1 and 2 together (one engine session), Phase 3 next (the big
visual session, artifact preview at the end), Phase 4, then 5. Each phase
ends pushed to the branch with tests green.
