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

### Phase 0 — Visual sample (approve the style before any engine work)
- One representative scene, code-drawn pixel art: houses, river, paddy
  fields, cows, banyan, a few recognizable villagers, day/night lighting.
- Published as an artifact, judged on a phone. Sprite-sheet assets remain
  an open option if code-drawn art disappoints.
- Exit: an explicit yes/no on "does this look like the village I want?"

### Phase 1 — Space in the engine
- Widen the map to a 24×16 tile layout: river, paths, one home per
  founding household, plots (existing x,y), grazing field, banyan.
- Agent `pos`/`dest`/`activity`; a `_move` step in `_act` before work;
  meals at home or in the field, rest at home, disputes gather at the
  good plot.
- **Travel economics (settled before building):** a tick spent walking
  produces nothing — work requires being at the plot or herd, so distant
  plots genuinely cost output. This changes the economy, so the 1,000-seed
  experiment metrics are re-run before/after and the calibration
  (fertility, forage, rations) re-tuned to hold the Phase-"family fixes"
  mortality profile (~25% child mortality, elder-weighted deaths).
- Tests: replay byte-identical, mid-day save/resume with positions,
  fingerprint updated, no agent occupies an impassable tile.
- Exit: `events.jsonl` unchanged in meaning; `/state` can report space.

### Phase 2 — One shared state format, tick-level
- A single schema used identically by the live `/state` endpoint and by
  recorded playback files: monotonic `tick_id` (`day * ticks_per_day +
  tick`), per-agent position, destination, activity, plus events keyed by
  tick_id. Daily snapshots are not enough to replay trips, gifts, or
  disputes; recordings capture every tick.
- Interpolation contract: the renderer eases toward reported targets and
  **snaps** on any discontinuity greater than one tile — pause, speed
  change, and timeline scrubbing never slide characters across the map.
- Exit: `curl /state` and a recorded file parse with the same code, and
  scrubbing a recording never produces a gliding villager.

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

### Phase 5 — Live deployment (an explicit deliverable, not a footnote)
- The village runs continuously on a host: a documented service setup
  (systemd unit or equivalent) around `dekot serve`, persistent checkpoint
  storage, verified restart/reboot recovery, private phone access
  (Tailscale or LAN documented), and reopening the page always reconnects
  to the existing village — never resets it.
- Exit: the owner opens the page on a phone days later and the same
  village has kept living.

### Phase 6 — Richer village life (as simulation features arrive)
- Weather and festivals: **if they affect farming or behaviour they are
  engine features first** (seeded, tested, in the fingerprint), rendered
  second; only purely cosmetic ambience lives in the renderer alone.
- Herd behaviour, richer buildings, AI-written diaries when the LLM
  milestone lands.

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
Visual sample → engine space → shared state format → recorded animated
viewer → live deployment → richer village life. Each phase ends pushed to
the branch with tests green. A later stylized-3D version would reuse the
simulation and interface work wholesale; the rendering and artwork would
be largely replaced — accepted.
