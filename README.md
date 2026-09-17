# Dekot — milestone 1 engine

Deterministic village simulation, stdlib only. See SPEC.md.

    python -m dekot run --seed 1              # 5-year run, prints event feed
    python -m dekot run --seed 1 --save-at 20 # saves runs/run/state.json at day 20
    python -m dekot resume runs/run/state.json
    python -m dekot experiment --runs 1000    # metrics per SPEC §10
    pip install pytest && pytest -q           # acceptance tests (SPEC §11)

Changes vs first cut: landless farmers forage (no farming without ownership), `founder_seed` fixes the
starting village across experiments, ledger applies and logs at 4-decimal precision with opening balances,
checkpoints carry the engine fingerprint (`resume --force` to override), experiment metrics report
KM survival, hunger as meals/agent-days/village-days, and unobserved years as missing.
