# V22.4 QA status

Release: `22.4-guided-one-click`

## Main changes
- One-button resumable validation path for mobile use.
- Automatically reuses/completes one-time pool calibration and freezes the pool.
- Automatically compares manual, hybrid IC and IC-adaptive models at 5/20/60 sessions.
- GBM, raw JSON and model-selection controls removed from the normal path.
- Final holdout remains excluded from iterative validation.
- Legacy cached `null` numeric evidence no longer causes `NoneType - float` crashes.
- Error state preserves completed checkpoints and exposes traceback only under a collapsed diagnostic section.

## Automated QA
- Full repository test suite: **200 passed, 0 failed**.
- Python compileall: passed.
- Added regression test for old cached null numeric evidence.
- Added regression test that guided mode excludes diagnostic/GBM candidates from the normal path.

## Limits
- No real Streamlit Cloud deployment was performed from this container.
- No new real-market profitability test was run for this UI/workflow release.
- Repeated fast-mode tuning still uses exposed development evidence and is not a fresh holdout.
