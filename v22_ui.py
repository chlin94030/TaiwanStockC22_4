"""V22.4 mobile-first one-click validation UI.

The normal path intentionally exposes one action only. Advanced research controls
are kept behind a collapsed section so a phone user cannot accidentally consume
the final holdout or restart expensive pool research.
"""
from pathlib import Path
import copy
import json
import pandas as pd

from lab_io import read_json, DataError
from studio_pool import discover_prepared, adopt_dataset, load_dataset
from v22_runner import start_v22, v22_alive
from v224_guided import start_guided, guided_alive, guided_state, GUIDED_VERSION

HERE = Path(__file__).resolve().parent


def _fmt_pct(v):
    try:
        if v is None or not pd.notna(v): return '—'
        return f'{float(v):+.2%}'
    except Exception:
        return '—'


def _guided_profiles(default_profiles):
    q=copy.deepcopy(default_profiles)
    q['candidates']=[c for c in q.get('candidates',[]) if c.get('model_type','manual') in ('manual','hybrid_ic','ic_adaptive') and c.get('selection_eligible',True)]
    return q


def render(st, root):
    root=Path(root)
    st.title('Alpha Radar V22.4.1｜一鍵接續驗證')
    st.caption(GUIDED_VERSION+'｜手機優先：資料 → 母池固定 → 5/20/60日策略比較 → 完整報告。')
    st.info('平常只按一個按鈕。系統會自動沿用已完成步驟；失敗後不刪資料、不重跑母池，修正後再按「開始／繼續」即可。')

    from lab_jobs import workspace_busy
    busy=guided_alive(root) or v22_alive(root) or workspace_busy(root)
    prepared=discover_prepared(root)
    dataset=None
    try:
        if (root/'studio'/'active_dataset.json').exists():
            _,dataset=load_dataset(root)
    except Exception as exc:
        st.warning(str(exc))

    # Step 1: dataset. Only show controls if a dataset is not active.
    if dataset:
        st.success('① 資料庫已就緒｜'+str(dataset['source_config'].get('start'))+' ～ '+str(dataset['source_config'].get('end')))
    else:
        st.subheader('① 選擇已完成的資料庫')
        if not prepared:
            st.warning('目前沒有可沿用的完整資料庫。請先切到「資料準備與備份」完成一次資料建置。')
            return
        selected=st.selectbox('已準備資料',prepared,format_func=lambda p:p['name']+'｜'+str(p['start'])+'～'+str(p['end']))
        if st.button('採用這份資料並繼續',type='primary',disabled=busy,use_container_width=True):
            try:
                adopt_dataset(root,selected['run']);st.rerun()
            except Exception as exc:st.error(str(exc))
        return

    default_profiles=read_json(HERE/'v22_profiles.json')
    profiles=_guided_profiles(default_profiles)
    settings=read_json(HERE/'v22_settings.json')
    state=guided_state(root)

    # Step 2/3 are automatic and resume-aware.
    pool=state.get('pool_rule')
    if pool:
        st.success('② 母池已固定｜'+str(pool)+'｜後續策略調整不再重跑母池')
    else:
        latest_pool=read_json(root/'v22'/'latest_pool_study.json')
        if latest_pool.get('suggested_pool'):
            st.success('② 已找到先前母池校準｜系統將自動固定 '+str(latest_pool['suggested_pool']))
        else:
            st.info('② 尚未做母池校準｜第一次按開始時會自動比較 ADV200／ADV300／KOSTO250／KOSTO300，完成後永久固定。')

    st.subheader('③ 一鍵完整驗證')
    st.write('自動執行：**固定權重基準 → Hybrid IC → IC Adaptive → 5/20/60日同條件比較 → 產出 Excel＋ZIP 報告**。')
    st.caption('不加入GBM、不開JSON、不需要手選模型，也不會查看最後保留期。')

    label='▶ 開始／繼續完整驗證'
    if state.get('status')=='COMPLETE': label='✓ 驗證已完成（報告在下方）'
    if st.button(label,type='primary',disabled=busy or state.get('status')=='COMPLETE',use_container_width=True):
        try:
            start_guided(root,profiles,settings)
            st.success('已啟動。離開或重新整理頁面不會取消已完成的checkpoint；回來後可查看狀態。')
        except Exception as exc:st.error(str(exc))

    @st.fragment(run_every='3s')
    def monitor():
        s=guided_state(root)
        if not s:return
        progress=float(s.get('progress') or 0.0)
        st.progress(max(0.0,min(1.0,progress)),text=str(s.get('message') or s.get('phase') or '準備中'))
        st.caption('目前步驟：'+str(s.get('phase','—'))+'｜狀態：'+str(s.get('status','—')))

        if s.get('status')=='ERROR':
            err=s.get('error') or {}
            st.error(str(err.get('type','ERROR'))+'：'+str(err.get('message','未知錯誤')))
            st.warning('已完成的資料與母池不會刪除。部署修正版後，再按「開始／繼續完整驗證」即可從未完成步驟接續。')
            with st.expander('除錯資訊（需要時才開）',expanded=False):
                st.code(str(err.get('traceback','')))

        run_path=s.get('fast_run')
        if s.get('status')=='COMPLETE' and run_path:
            run=Path(run_path);result=read_json(run/'results.json')
            st.success('④ 驗證報告已完成｜現在只要下載報告，交給我做下一輪因子／權重調整。')
            rows=[]
            for h,m in result.get('models',{}).items():
                sm=m.get('development_validation') or {}
                rows.append({'週期':str(h)+'日','母池':m.get('pool'),'勝出策略':(m.get('choice') or {}).get('name'),
                    '模型':(m.get('choice') or {}).get('model_type','manual'),'開發分數':_fmt_pct(m.get('choice_score')),
                    'vs 0050':_fmt_pct((sm.get('versus_0050') or {}).get('mean')),
                    'vs 同母池':_fmt_pct((sm.get('versus_same_pool') or {}).get('mean')),
                    '額外成本後':_fmt_pct(sm.get('extra_cost_stress_excess'))})
            if rows:st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
            if (run/'V22_TEST_REPORT.zip').is_file():
                st.download_button('⬇ 下載完整驗證報告 ZIP', (run/'V22_TEST_REPORT.zip').read_bytes(),
                    'V22_TEST_REPORT.zip','application/zip',type='primary',use_container_width=True,on_click='ignore')
            if (run/'V22_TEST_REPORT.xlsx').is_file():
                st.download_button('⬇ 下載 Excel 驗證報告', (run/'V22_TEST_REPORT.xlsx').read_bytes(),
                    'V22_TEST_REPORT.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True,on_click='ignore')
            if (run/'REPORT.txt').is_file():
                with st.expander('直接閱讀摘要',expanded=False):st.text((run/'REPORT.txt').read_text(encoding='utf-8-sig'))

    monitor()

    # Advanced actions are deliberately hidden from the normal workflow.
    with st.expander('進階／只有特殊情況才使用',expanded=False):
        st.warning('一般驗證不要碰這裡。尤其「最終確認」只有策略完全凍結後才能做一次。')
        c1,c2=st.columns(2)
        if c1.button('只重跑策略驗證（保留母池）',disabled=busy,use_container_width=True):
            try:start_guided(root,profiles,settings,force_fast=True);st.info('保留固定母池，只重跑快速策略驗證。')
            except Exception as exc:st.error(str(exc))
        if c2.button('重新校準母池（極少使用）',disabled=busy,use_container_width=True):
            try:start_guided(root,profiles,settings,force_pool_recalibration=True,force_fast=True);st.info('將重新比較四種母池。')
            except Exception as exc:st.error(str(exc))

        s=guided_state(root)
        if s.get('status')=='COMPLETE' and s.get('pool_rule'):
            st.markdown('**策略真正定案後：一次性最後保留期確認**')
            frozen=st.checkbox('我確認母池、因子、權重都不再修改；這次要正式打開最後保留期',key='v224_final_frozen')
            if st.button('執行一次最終確認',disabled=busy or not frozen,use_container_width=True):
                final_settings=dict(settings);final_settings['pool_rule']=s['pool_rule']
                try:start_v22(root,profiles,final_settings,'confirm');st.success('已啟動一次性最終確認。')
                except Exception as exc:st.error(str(exc))
