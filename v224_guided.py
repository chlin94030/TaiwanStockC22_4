"""V22.4 one-click guided validation pipeline.

Normal users should not have to choose pool/model/JSON controls in the UI.
This module resumes from durable checkpoints:
  prepared dataset -> one-time pool lock -> fast strategy comparison -> report.
The final blind confirmation is deliberately NOT part of this pipeline because the
report is intended for iterative adjustment; repeatedly opening the final tail
would destroy its value as a holdout.
"""
from __future__ import annotations
from pathlib import Path
import copy
import threading
import traceback

from lab_io import DataError, atomic_json, read_json
from studio_pool import load_dataset, load_pool, lock_pool, timestamp, digest
from v22_runner import run_pool_study, run_experiment

GUIDED_VERSION = '22.4-guided-one-click'
_STATE = 'guided_state.json'
_THREADS = {}
_LOCK = threading.Lock()


def _state_path(root):
    return Path(root) / 'v22' / _STATE


def guided_state(root):
    return read_json(_state_path(root))


def _write(root, **updates):
    root = Path(root)
    root.joinpath('v22').mkdir(parents=True, exist_ok=True)
    state = read_json(_state_path(root))
    state.update(updates, updated_at=timestamp(), guided_version=GUIDED_VERSION)
    atomic_json(_state_path(root), state)
    return state


def _guided_profiles(profiles):
    """Keep only the three normal comparison models; GBM/diagnostics stay advanced."""
    obj = copy.deepcopy(profiles)
    keep = []
    for c in obj.get('candidates', []):
        mt = c.get('model_type', 'manual')
        if mt in ('manual', 'hybrid_ic', 'ic_adaptive') and c.get('selection_eligible', True):
            c['selection_eligible'] = True
            keep.append(c)
    if not keep:
        raise DataError('V22.4 guided mode found no normal strategy candidates')
    obj['candidates'] = keep
    return obj


def _current_pool_lock(root, dataset_id):
    try:
        obj = load_pool(root)
    except Exception:
        return None
    if obj.get('dataset_id') != dataset_id:
        return None
    vals = list((obj.get('mapping') or {}).values())
    if not vals or len(set(vals)) != 1:
        return None
    return vals[0]


def _latest_pool_suggestion(root):
    latest = read_json(Path(root) / 'v22' / 'latest_pool_study.json')
    pool = latest.get('suggested_pool')
    if pool in ('ADV200', 'ADV300', 'KOSTO250', 'KOSTO300'):
        return pool, latest.get('run')
    return None, None


def _freeze_pool(root, dataset_id, pool, evidence_run=None):
    mapping = {5: pool, 20: pool, 60: pool}
    evidence = {'source': 'V22_DEVELOPMENT_POOL_STUDY', 'run': evidence_run,
                'guided_version': GUIDED_VERSION, 'final_tail_used': False}
    obj = lock_pool(root, mapping, reason='V22_4_GUIDED_DEVELOPMENT_LOCK', evidence=evidence)
    _write(root, dataset_id=dataset_id, pool_rule=pool, pool_lock_id=obj.get('lock_id'),
           pool_study_run=evidence_run, phase='POOL_LOCKED', progress=0.32,
           message=f'母池已固定為 {pool}；後續策略驗證不再重跑母池。')
    return pool


def run_guided(root, profiles, settings, force_pool_recalibration=False, force_fast=False):
    root = Path(root)
    _, meta = load_dataset(root)
    dataset_id = meta['dataset_id']
    profiles = _guided_profiles(profiles)
    settings = dict(settings)
    identity = digest({'guided_version': GUIDED_VERSION, 'dataset_id': dataset_id,
                       'profiles': profiles, 'settings_without_pool': {k:v for k,v in settings.items() if k != 'pool_rule'}})[:24]

    old = guided_state(root)
    if old.get('dataset_id') != dataset_id or old.get('identity') != identity:
        old = {}
    _write(root, status='RUNNING', phase='PRECHECK', progress=0.05,
           dataset_id=dataset_id, identity=identity, error=None,
           message='資料庫檢查完成，準備固定母池。')

    # 1) Reuse an explicit compatible pool lock first.
    pool = None if force_pool_recalibration else _current_pool_lock(root, dataset_id)
    pool_run = None

    # 2) Reuse a completed one-time study from the same working database. Older
    # V22.3 records did not store dataset_id, so this is intentionally secondary
    # to an explicit active lock and is immediately converted into one.
    if pool is None and not force_pool_recalibration:
        pool, pool_run = _latest_pool_suggestion(root)

    # 3) Only if neither exists, run the one-time development pool study.
    if pool is None:
        _write(root, phase='POOL_CALIBRATION', progress=0.12,
               message='第一次才會做：自動比較 ADV200 / ADV300 / KOSTO250 / KOSTO300。')
        folder = run_pool_study(root, profiles, settings)
        pool_run = str(folder)
        latest = read_json(root / 'v22' / 'latest_pool_study.json')
        pool = latest.get('suggested_pool')
        if pool not in ('ADV200', 'ADV300', 'KOSTO250', 'KOSTO300'):
            raise DataError('母池校準完成但沒有可固定的建議母池')

    pool = _freeze_pool(root, dataset_id, pool, pool_run)

    # Development-only fast validation. Never open the final holdout here.
    settings['pool_rule'] = pool
    prior_fast = old.get('fast_run') if old else None
    if prior_fast and not force_fast:
        p = Path(prior_fast)
        if read_json(p / 'state.json').get('status') == 'COMPLETE' and (p / 'V22_TEST_REPORT.zip').is_file():
            _write(root, status='COMPLETE', phase='REPORT_READY', progress=1.0,
                   fast_run=str(p), report_zip=str(p/'V22_TEST_REPORT.zip'), report_xlsx=str(p/'V22_TEST_REPORT.xlsx'),
                   message='完整快速驗證已完成；可直接下載報告供下一輪調整。')
            return p

    _write(root, phase='FAST_VALIDATION', progress=0.42,
           message='固定母池後，自動比較固定權重 / Hybrid IC / IC Adaptive，並分別驗證 5 / 20 / 60 日。')
    run = run_experiment(root, profiles, settings, mode='fast')
    if read_json(run / 'state.json').get('status') != 'COMPLETE':
        raise DataError('快速策略驗證未完成')
    if not (run / 'V22_TEST_REPORT.zip').is_file():
        raise DataError('策略驗證完成但報告 ZIP 未產生')

    _write(root, status='COMPLETE', phase='REPORT_READY', progress=1.0,
           fast_run=str(run), report_zip=str(run/'V22_TEST_REPORT.zip'),
           report_xlsx=str(run/'V22_TEST_REPORT.xlsx'),
           message='完整快速驗證已完成；下載報告後即可依結果調整，不需查看最後保留期。')
    return run


def _mark_error(root, exc):
    msg = str(exc) or type(exc).__name__
    _write(root, status='ERROR', progress=guided_state(root).get('progress', 0.0),
           error={'type': type(exc).__name__, 'message': msg[:1000], 'traceback': traceback.format_exc()[-5000:]},
           message='本次停在目前步驟；已完成的資料與母池鎖會保留。修正後按「開始／繼續」即可從未完成步驟接續。')


def start_guided(root, profiles, settings, force_pool_recalibration=False, force_fast=False):
    root = Path(root)
    key = str(root.resolve())
    with _LOCK:
        if _THREADS.get(key) and _THREADS[key].is_alive():
            raise DataError('完整驗證程序已在執行')
        root.joinpath('v22').mkdir(parents=True, exist_ok=True)
        # Clear the old V22.3 launch banner. Guided state owns errors now.
        (root/'v22'/'launch_error.json').unlink(missing_ok=True)
        def target():
            try:
                run_guided(root, profiles, settings, force_pool_recalibration, force_fast)
            except Exception as exc:
                _mark_error(root, exc)
        t = threading.Thread(target=target, daemon=True, name='v224-guided-one-click')
        _THREADS[key] = t
        t.start()


def guided_alive(root):
    t = _THREADS.get(str(Path(root).resolve()))
    return bool(t and t.is_alive())
