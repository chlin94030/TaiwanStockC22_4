# Alpha Radar V22.4 — One-Click Guided Validation

V22.4 keeps the V22.3 adaptive-hybrid engine but changes the normal workflow to a resumable one-click pipeline: reuse prepared data → reuse or run one-time pool calibration → freeze one pool rule → compare manual / hybrid-IC / IC-adaptive models for 5/20/60 sessions → export the complete ZIP/XLSX report. Normal users no longer need to choose model type, JSON, GBM, pool rule, or final-tail controls on the main screen.

The compatibility fix also treats legacy cached `null` numeric evidence as missing (`NaN`) rather than attempting arithmetic such as `None - cost`. Existing caches can therefore be reused instead of deleted and rebuilt. The guided pipeline never opens the final holdout; final confirmation remains an advanced one-time action after the strategy is frozen.

See `V22_4_START_HERE.txt` and `V22_4_QA_STATUS.md`.

# Alpha Radar V22.3 — Adaptive Hybrid Stage-First Studio

V22.3 keeps the V22.2 data coverage repair and the V22 Kostolany six-stage gate, but borrows the strongest ideas from the supplied Claude `engine.py` / `app.py`: horizon-specific weights, walk-forward rank-IC adaptation, manual-vs-adaptive model comparison, an optional walk-forward GBM challenger, and a one-click Excel research workbook. The fixed pool remains separate from strategy tuning; fast tests reuse local feature/label caches and never re-download the whole market.

Default strategy candidates are: manual book prior, book×IC hybrid, stronger IC-adaptive, and a no-stage-control diagnostic. The GBM challenger is opt-in and diagnostic-only by default. Adaptive models may use only labels whose holding period has already matured before the new signal date.

See `V22_3_CLAUDE_FUSION.md`, `V22_3_START_HERE.txt`, and `V22_3_QA_STATUS.md`.

# Alpha Radar V22.2 — Kostolany Stage-First + Robust Fast Bootstrap

V22.2 keeps the V22 market-stage/strategy model and fixes the V22.1 Yahoo partial-history false-success condition. `AUTO_FAST` is now the default: authenticated FinLab bulk when available, otherwise Yahoo multi-ticker batches for rapid development. It does **not** silently fall back to the multi-hour FinMind per-stock path. `OFFICIAL_BULK` is provided as a free exact-turnover confirmation path using TWSE+TPEx whole-market daily history. See `V22_1_START_HERE.txt` and `V22_1_FAST_BOOTSTRAP.md`.

# Alpha Radar V21.6 - Bulk-first Data Layer + Fixed Pool Strategy Studio

Use V21_6_Quickstart.txt for the V21.6 data-layer guide and V21_5_Quickstart.txt for the fixed-pool strategy workflow. app.py remains the Streamlit entry point.

Default page: fixed-pool, offline strategy development. Adopt an existing prepared run and explicitly freeze a pool rule. Do not re-download the whole market or rerun four universe sizes merely to change weights.

See FIXED_POOL_PROTOCOL.md for architecture, cache invalidation, fast-vs-confirmation boundaries, CLI and limitations. See KOSTOLANY_DESIGN.md for source provenance and the distinction between book ideas and our numerical hypotheses. OLD V21_4/21_3 QA documents are historical release notes, not evidence of this version's performance; the current record is QA_STATUS.md.

Quick CLI (after restoring your own data cache):
```
python run_studio.py --action adopt
python run_studio.py --action lock --pool ADV200
python run_studio.py --action fast
```

Important: a completed LAB_RESULTS.zip is a report, not the daily-price database. New local feature preparation needs the daily SQLite cache and prepared snapshot. No live profits or global optimum have been established.

## V21.6 bulk-first data layer
V21.6 preserves the V21.5 fixed-pool strategy studio but replaces the slow first-time all-market transport. `history_provider=AUTO` prefers authenticated FinLab whole-market tables; if unavailable/incomplete it falls back to FinMind. FinMind fallback now reads the account's reported API quota instead of treating every token as 520 requests/hour. See `V21_6_Quickstart.txt`, `V21_6_Data_Architecture.md`, and `V21_6_QA_Status.md`.


## V22.2 Yahoo coverage repair
See `V22_2_YAHOO_COVERAGE_FIX.md`. Yahoo fast bootstrap now validates 252-session rankability before any Top-N pool claim, retries sparse tickers in smaller batches, and AUTO_FAST falls back to official TWSE/TPEx whole-market history if Yahoo remains incomplete.
