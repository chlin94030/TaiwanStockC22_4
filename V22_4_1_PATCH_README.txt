Alpha Radar V22.4.1 PRECHECK Fix

Fixes:
  DataError: Requested pool not present in pinned snapshot

Cause:
KOSTO250/KOSTO300 are V22-derived monthly pools built deterministically from the
pinned ADV500 snapshot. V22.4 incorrectly validated them with the legacy native
snapshot pool lock.

Upgrade from V22.4:
1. Keep data/ unchanged.
2. Copy these files to repository root and overwrite existing files.
3. Redeploy Streamlit.
4. Open V22快速策略驗證 and press 開始／繼續完整驗證.
5. Do not rerun/rebuild the database and do not delete checkpoints.

QA: 202 passed, 0 failed.
