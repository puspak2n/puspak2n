# Dekot — milestone 1 engine

Deterministic village simulation, stdlib only. See SPEC.md.

    python -m dekot serve --seed 16           # live village at http://localhost:8080/
    python -m dekot run --seed 1              # 5-year run, prints event feed
    python -m dekot run --seed 1 --save-at 20 # saves runs/run/state.json at day 20
    python -m dekot resume runs/run/state.json
    python -m dekot experiment --runs 1000    # metrics per SPEC §10
    pip install pytest && pytest -q           # acceptance tests (SPEC §11)

## Live mode

`dekot serve` runs one authoritative simulation paced by the wall clock
(default 1 real hour = 1 Dekot day) and serves a mobile-friendly viewer at
`/` with pause and speed controls. The engine advances tick by tick and
checkpoints after every tick (`runs/live/state.json`, written atomically),
so a crash or reboot loses at most the current tick: restarting the same
command reconnects to the existing village. `--force` overrides the engine
fingerprint check on an old checkpoint; delete the state file to found a
new village. Host it anywhere a Python process can run; something like
Tailscale works for private access to a home-hosted server.

Changes vs first cut: landless farmers forage (no farming without ownership), `founder_seed` fixes the
starting village across experiments, ledger applies and logs at 4-decimal precision with opening balances,
checkpoints carry the engine fingerprint (`resume --force` to override), experiment metrics report
KM survival, hunger as meals/agent-days/village-days, and unobserved years as missing.
