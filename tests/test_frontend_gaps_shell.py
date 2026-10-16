"""Behaviour tests for the shell, task panel, inbox and people-list gaps in the frontend.

Node runs the real src/astra/static/app.js against a small DOM stub (the shared WIRING_DRIVER
stub, extended here so listeners, aria attributes, history and the clipboard can be observed).
Every test names a guard or behaviour; removing that guard from app.js makes it fail.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_web import WIRING_DRIVER, STATIC


# Added to the shared stub, after its definitions and before app.js is evaluated.
PRELUDE = r'''
globalThis.__el=el;
globalThis.location={hash:"",search:"",origin:"http://astra",pathname:"/"};
globalThis.__hist=[];
globalThis.history={replaceState(a,b,u){__hist.push(["replace",u]);location.hash=u},back(){__hist.push(["back"])}};
const __docL={};globalThis.__docL=__docL;
document.addEventListener=(k,f)=>{(__docL[k]=__docL[k]||[]).push(f)};
const __shared={};
const __baseQS=document.querySelector,__baseQSA=document.querySelectorAll;
document.querySelector=s=>{
  if(/dialog\[open\]|\.menu:not/.test(s))return null;
  if(/select\[name="owner_user_id"\]/.test(s))return globalThis.__holdPicker||(globalThis.__holdPicker=el());
  if(s==="#move-error")return globalThis.__moveError||(globalThis.__moveError=el());
  if(s==="#toast-action"||s==="#toast-dismiss")return __shared[s]||(__shared[s]=el());
  return __baseQS(s);
};
document.querySelectorAll=s=>s==="[data-nav]"?(globalThis.__navs||[]):__baseQSA(s);
const __probeSrc=fs.readFileSync(process.argv[4],"utf8");
(0,eval)(src+"\n;"+__probeSrc);
runProbe().then(x=>process.stdout.write(JSON.stringify(x),()=>process.exit(0))).catch(e=>{console.error(e);process.exit(1)});
'''

PROBE = r'''
globalThis.runProbe=async()=>{
const out={};
const tick=()=>new Promise(r=>setTimeout(r,0));
const settle=async()=>{for(let i=0;i<8;i++)await tick()};
const guard=async(name,fn)=>{try{out[name]=await fn()}catch(e){out[name]={error:String(e&&e.stack||e)}}};
const U1='11111111-1111-4111-8111-111111111111',U2='22222222-2222-4222-8222-222222222222';
const alerts=[];globalThis.alert=m=>alerts.push(m);
for(const f of ['load','openDetail','shellTitle','renderBulkBar'])globalThis[f]=async()=>{};
state.user={id:'u1',display_name:'U One',global_role:'member'};state.projects=[];state.tasks=[];

// ---- 1. Rail: aria-current follows the screen -------------------------------------------------
await guard('rail',async()=>{
  const navs=['home','my-work','inbox','projects'].map(n=>{const o={dataset:{nav:n},_a:{},
    setAttribute(k,v){o._a[k]=String(v)},removeAttribute(k){delete o._a[k]},getAttribute(k){return k in o._a?o._a[k]:null}};return o});
  globalThis.__navs=navs;
  const quiet=['renderHome','loadHomePortfolio','openInbox','renderMyWork','renderProjects','renderProject','render','setPortfolioLinks'];
  const real=quiet.map(f=>globalThis[f]);
  for(const f of quiet)globalThis[f]=()=>{};
  const routes=[['#/home','home'],['#/my-work','my-work'],['#/inbox','inbox'],['#/projects','projects'],['#/home','home'],
    ['#/my-work/calendar','my-work'],['#/portfolio','projects'],['#/project/'+U1+'/board','projects'],['#/task/'+U1,null],['#/inbox','inbox']];
  const rows=[],errors=[];
  for(const [hash,expect] of routes){
    location.hash=hash;panelState.rendered=null;
    try{applyRoute(false,false)}catch(e){errors.push(hash+': '+String(e))}
    rows.push({hash,expect,current:navs.filter(n=>n.getAttribute('aria-current')!==null).map(n=>n.dataset.nav+'='+n.getAttribute('aria-current'))});
  }
  quiet.forEach((f,i)=>{globalThis[f]=real[i]});
  return {rows,errors};
});

// ---- 2. Top bar search ------------------------------------------------------------------------
await guard('search',async()=>{
  const calls=[];let opened=0;
  api=async p=>{calls.push(p);return {results:{tasks:[{id:'t1',title:'Budget <b>plan</b>',status:'draft',project_name:'P'}],projects:[]}}};
  const dlg=document.querySelector('#search-dialog');dlg.open=false;dlg.showModal=()=>{opened++};
  const handlers=document.querySelector('#search-box')._l.keydown||[];
  const press=async(key,value)=>{let prevented=false;
    for(const f of handlers)f({key,target:{value},preventDefault(){prevented=true}});
    await settle();return prevented};
  const r={handlers:handlers.length};
  r.emptyEnter=await press('Enter','');r.afterEmpty={calls:calls.slice(),opened};
  r.blankEnter=await press('Enter','   ');r.afterBlank={calls:calls.slice(),opened};
  r.otherKey=await press('a','budget & plan');r.afterOtherKey={calls:calls.slice(),opened};
  r.enter=await press('Enter','budget & plan');
  r.afterEnter={calls:calls.slice(),opened,body:document.querySelector('#search-body').innerHTML};
  return r;
});

// ---- 3. Task panel: Copy link, Close button, Esc ----------------------------------------------
await guard('panel',async()=>{
  const panel=document.querySelector('#detail-dialog'),app=document.querySelector('#app'),cls=new Set();
  app.classList={add:(...c)=>c.forEach(x=>cls.add(x)),remove:(...c)=>c.forEach(x=>cls.delete(x)),
    toggle:(c,on)=>{if(on===undefined?!cls.has(c):on)cls.add(c);else cls.delete(c)},contains:c=>cls.has(c)};
  const keyErrors=[];
  const key=(k)=>{const e={key:k,target:{closest:()=>null},ctrlKey:false,metaKey:false,altKey:false,defaultPrevented:false,prevented:false,
    preventDefault(){this.prevented=true;this.defaultPrevented=true},stopPropagation(){}};
    for(const f of (__docL.keydown||[])){try{f(e)}catch(x){keyErrors.push(String(x))}}return e.prevented};
  const open=(id)=>{location.hash='#/home';panelState.shown=null;panelState.pushed=null;panelState.quiet=false;panel.hidden=true;cls.clear();
    __hist.length=0;detailTaskId=id;openPanel(id)};
  const snap=()=>({hidden:panel.hidden,shown:panelState.shown,detail:detailTaskId,classes:[...cls].sort(),hist:__hist.slice()});
  const r={};
  open(U1);r.opened=snap();
  await Promise.all((document.querySelector('#detail-close')._l.click||[]).map(f=>f()));r.afterCloseButton=snap();
  open(U1);key('x');r.afterOtherKey=snap();
  key('Escape');r.afterEsc=snap();
  // Copy link
  const written=[];let mode='ok';
  Object.defineProperty(globalThis,'navigator',{configurable:true,value:{clipboard:{writeText:async t=>{written.push(t);if(mode==='fail')throw new Error('denied')}}}});
  const copy=()=>Promise.all((document.querySelector('#detail-copy')._l.click||[]).map(f=>f()));
  open(U1);await copy();r.copy={written:written.slice(),toast:document.querySelector('#toast').innerHTML};
  written.length=0;open(U1);openPanel(U2);await copy();r.copySwapped={written:written.slice()};
  written.length=0;mode='fail';open(U1);await copy();
  r.copyFailed={written:written.slice(),toast:document.querySelector('#toast').innerHTML};
  r.keyErrors=keyErrors;
  return r;
});

// ---- 4. Inbox: Mark read and Mark all read ----------------------------------------------------
await guard('inbox',async()=>{
  const now=new Date().toISOString();
  let notes=[{id:'n1',summary:'task assigned: Alpha',task_id:null,task_title:null,created_at:now,read_at:null},
             {id:'n2',summary:'task assigned: Beta',task_id:null,task_title:null,created_at:now,read_at:null}];
  const calls=[];let failPost=false;
  api=async(path,opts)=>{const method=(opts&&opts.method)||'GET';calls.push(method+' '+path+(opts&&opts.body?' '+opts.body:''));
    if(method==='POST'&&failPost)throw new Error('server said no');
    let m=/^\/api\/notifications\/([^/]+)\/read$/.exec(path);
    if(method==='POST'&&m){notes=notes.map(n=>n.id===m[1]?{...n,read_at:now}:n);return {}}
    if(method==='POST'&&path==='/api/notifications/read-all'){notes=notes.map(n=>({...n,read_at:now}));return {}}
    if(path==='/api/notifications')return {notifications:notes,unread:notes.filter(n=>!n.read_at).length};
    return {}};
  const badge=document.querySelector('#unread-count'),body=()=>document.querySelector('#inbox-body').innerHTML;
  const click=async(sel,attr,val)=>{
    const node=attr?document.querySelectorAll('['+attr+']').find(n=>n.dataset[val[0]]===val[1]):document.querySelector(sel);
    if(!node)return {missing:true};
    const hs=node._l.click||[];calls.length=0;await Promise.all(hs.map(f=>f({target:node,preventDefault(){}})));await settle();return {handlers:hs.length};
  };
  const r={};
  location.hash='#/inbox';state.user={id:'u1',display_name:'U One',global_role:'member'};
  await openInbox();
  r.initial={unread:state.unread,badge:String(badge.textContent),badgeHidden:badge.hidden,readButtons:document.querySelectorAll('[data-read]').map(n=>n.dataset.read),
    readAllMarkup:body().indexOf('id="read-all"')>=0};
  r.markRead=await click(null,'data-read',['read','n2']);
  r.markReadCalls=calls.slice();
  r.afterMarkRead={unread:state.unread,badge:String(badge.textContent),badgeHidden:badge.hidden,
    readButtons:document.querySelectorAll('[data-read]').map(n=>n.dataset.read),alerts:alerts.slice()};
  r.markAll=await click('#read-all');
  r.markAllCalls=calls.slice();
  r.afterMarkAll={unread:state.unread,badgeHidden:badge.hidden,readButtons:document.querySelectorAll('[data-read]').map(n=>n.dataset.read)};
  // A refused POST tells the person and does not pretend it worked.
  notes=notes.map(n=>({...n,read_at:null}));await openInbox();alerts.length=0;failPost=true;
  r.failRead=await click(null,'data-read',['read','n1']);r.failReadCalls=calls.slice();
  r.failReadState={alerts:alerts.slice(),unread:state.unread};
  alerts.length=0;r.failAll=await click('#read-all');r.failAllCalls=calls.slice();r.failAllState={alerts:alerts.slice(),unread:state.unread};
  return r;
});

// ---- 5. F2: the people list must be loaded before holding or adding a reviewer ----------------
const detailTask=()=>({id:'t1',title:'Synthetic task',project_id:'p1',project_name:'P',status:'in_progress',revision:3,criticality:'high',
  due_state:'scheduled',start_date:'2026-09-01',due_date:'2026-10-10',progress:null,description:'',owner_user_id:null,
  permissions:{can_edit_ordinary:true,can_request_protected:false,can_decide_protected:true,can_manage_files:true,can_read_files:true},
  baseline:{},subtasks:[],final_results:[],dependencies:[],reviewers:[],attachments:[],submissions:[],schedule_proposals:[]});
let peopleMode='ready';let requests=[];
api=async(path,opts)=>{const m=(opts&&opts.method)||'GET';
  if(path.indexOf('/api/assignable-users')===0){requests.push({people:true});
    if(peopleMode==='pending')return new Promise(()=>{});
    if(peopleMode==='fail')throw new Error('offline');
    return {users:[{id:'u2',display_name:'Una Person'}]}}
  requests.push({m,path,body:opts&&opts.body?JSON.parse(opts.body):null});return {task:{id:'t1'},request:null}};
const sent=()=>requests.filter(r=>!r.people);

await guard('lifecycleHold',async()=>{
  const r={};
  for(const mode of ['pending','fail','ready']){
    peopleMode=mode;requests=[];globalThis.__holdPicker=__el();
    document.querySelector('#detail-body').innerHTML='';detailTaskId='t1';
    renderDetail(detailTask(),[]);await settle();
    const picker=document.querySelector('[data-life="hold"] select[name="owner_user_id"]');
    const form=document.querySelectorAll('[data-life]').find(f=>f.dataset.life==='hold');
    if(!form)return {error:'hold form not rendered'};
    form.__entries=[['reason','waiting for parts'],['checkpoint_date','2026-11-01'],['owner_user_id','u2']];
    requests=[];
    const hs=form._l.submit||[];
    for(const f of hs)await f({target:form,preventDefault(){}});await settle();
    const err=document.querySelector('#lifecycle-error');
    r[mode]={handlers:hs.length,disabled:picker.disabled,sent:sent(),message:err.textContent};
  }
  return r;
});

await guard('addReviewer',async()=>{
  const r={};
  for(const mode of ['pending','fail','ready']){
    peopleMode=mode;requests=[];globalThis.__holdPicker=__el();
    document.querySelector('#detail-body').innerHTML='';detailTaskId='t1';
    renderDetail(detailTask(),[]);await settle();
    const button=document.querySelector('#add-reviewer-button'),picker=document.querySelector('#reviewer-user'),role=document.querySelector('#reviewer-role');
    if(!button)return {error:'add reviewer button not rendered'};
    picker.value='u2';role.value='reviewer';requests=[];
    const hs=button._l.click||[];
    for(const f of hs)await f({target:button,preventDefault(){}});await settle();
    r[mode]={handlers:hs.length,disabled:picker.disabled,sent:sent(),message:document.querySelector('#reviewer-error').textContent};
  }
  return r;
});

await guard('boardHold',async()=>{
  const r={};
  for(const mode of ['pending','fail','ready']){
    peopleMode=mode;requests=[];globalThis.__holdPicker=__el();globalThis.__moveError=__el();
    const t={id:'t1',project_id:'p1',title:'Synthetic',status:'in_progress',revision:2,owner_user_id:'u1',owner_name:'Una'};
    const moving=moveCard(t,'blocked');await settle();
    const form=document.querySelector('#move-form'),picker=document.querySelector('select[name="owner_user_id"]');
    form.__entries=[['reason','waiting for parts'],['checkpoint_date','2026-11-01'],['owner_user_id','u2']];
    requests=[];
    form.onsubmit({preventDefault(){}});
    await settle();
    if(mode==='ready')await moving;
    r[mode]={handlers:typeof form.onsubmit==='function'?1:0,disabled:picker.disabled,sent:sent(),message:globalThis.__moveError.textContent};
  }
  return r;
});
return out;
};
'''


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class FrontendShellGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        head = WIRING_DRIVER.split('const harness=')[0]
        with tempfile.TemporaryDirectory() as temp:
            driver_path = Path(temp, 'shell_gaps.js')
            probe_path = Path(temp, 'probe.js')
            driver_path.write_text(head + PRELUDE, encoding='utf-8', newline='\n')
            probe_path.write_text(PROBE, encoding='utf-8', newline='\n')
            result = subprocess.run(
                ['node', str(driver_path), str(STATIC / 'app.js'), str(STATIC / 'index.html'), str(probe_path)],
                input='{}', capture_output=True, text=True, encoding='utf-8', timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.out = json.loads(result.stdout)

    def probe(self, name):
        value = self.out[name]
        self.assertNotIn('error', value, value.get('error') if isinstance(value, dict) else None)
        return value

    # ---- 1. rail ----
    def test_each_main_screen_marks_only_its_own_rail_item_as_current(self):
        rail = self.probe('rail')
        self.assertEqual(rail['errors'], [])
        for row in rail['rows'][:6]:
            with self.subTest(hash=row['hash']):
                self.assertEqual(row['current'], [row['expect'] + '=page'])

    def test_rail_current_marker_follows_nested_screens_and_clears_on_the_task_page(self):
        rows = {r['hash']: r for r in self.probe('rail')['rows']}
        self.assertEqual(rows['#/portfolio']['current'], ['projects=page'])
        self.assertEqual(rows['#/project/11111111-1111-4111-8111-111111111111/board']['current'], ['projects=page'])
        self.assertEqual(rows['#/task/11111111-1111-4111-8111-111111111111']['current'], [])
        self.assertEqual(self.probe('rail')['rows'][-1]['current'], ['inbox=page'])

    # ---- 2. search ----
    def test_enter_in_the_search_box_searches_for_the_typed_text(self):
        s = self.probe('search')
        self.assertGreater(s['handlers'], 0)
        self.assertTrue(s['enter'])  # Enter is consumed, not left to submit a form
        self.assertEqual(s['afterEnter']['calls'], ['/api/search?q=budget%20%26%20plan'])
        self.assertEqual(s['afterEnter']['opened'], 1)
        self.assertIn('Budget &lt;b&gt;plan&lt;/b&gt;', s['afterEnter']['body'])
        self.assertIn('Search: budget &amp; plan', s['afterEnter']['body'])

    def test_empty_or_blank_search_text_does_nothing(self):
        s = self.probe('search')
        self.assertEqual(s['afterEmpty'], {'calls': [], 'opened': 0})
        self.assertEqual(s['afterBlank'], {'calls': [], 'opened': 0})

    def test_other_keys_do_not_search(self):
        s = self.probe('search')
        self.assertFalse(s['otherKey'])
        self.assertEqual(s['afterOtherKey'], {'calls': [], 'opened': 0})

    # ---- 3. task panel ----
    def test_copy_link_copies_the_url_of_the_task_shown(self):
        panel = self.probe('panel')
        self.assertEqual(panel['copy']['written'], ['http://astra/#/task/11111111-1111-4111-8111-111111111111'])
        self.assertIn('copied', panel['copy']['toast'])
        self.assertEqual(panel['copySwapped']['written'], ['http://astra/#/task/22222222-2222-4222-8222-222222222222'])

    def test_copy_link_shows_the_link_to_copy_by_hand_when_the_clipboard_refuses(self):
        panel = self.probe('panel')
        self.assertEqual(panel['copyFailed']['written'], ['http://astra/#/task/11111111-1111-4111-8111-111111111111'])
        self.assertIn('Copy this link: http://astra/#/task/11111111-1111-4111-8111-111111111111',
                      panel['copyFailed']['toast'])
        self.assertNotIn('copied', panel['copyFailed']['toast'])

    def test_the_close_button_closes_the_panel(self):
        panel = self.probe('panel')
        self.assertFalse(panel['opened']['hidden'])
        self.assertEqual(panel['opened']['shown'], '11111111-1111-4111-8111-111111111111')
        self.assertIn('panel-open', panel['opened']['classes'])
        closed = panel['afterCloseButton']
        self.assertTrue(closed['hidden'])
        self.assertIsNone(closed['shown'])
        self.assertIsNone(closed['detail'])
        self.assertNotIn('panel-open', closed['classes'])
        self.assertEqual(closed['hist'], [['back']])  # opened with a history entry, so Back undoes it

    def test_escape_closes_the_panel_and_other_keys_do_not(self):
        panel = self.probe('panel')
        self.assertEqual(panel['keyErrors'], [])
        other = panel['afterOtherKey']
        self.assertFalse(other['hidden'])
        self.assertEqual(other['shown'], '11111111-1111-4111-8111-111111111111')
        esc = panel['afterEsc']
        self.assertTrue(esc['hidden'])
        self.assertIsNone(esc['shown'])
        self.assertNotIn('panel-open', esc['classes'])
        self.assertEqual(esc['hist'], [['back']])

    # ---- 4. inbox ----
    def test_inbox_starts_with_two_unread_notifications_and_a_mark_read_button_each(self):
        initial = self.probe('inbox')['initial']
        self.assertEqual(initial['unread'], 2)
        self.assertEqual(initial['badge'], '2')
        self.assertFalse(initial['badgeHidden'])
        self.assertEqual(initial['readButtons'], ['n1', 'n2'])
        self.assertTrue(initial['readAllMarkup'])

    def test_mark_read_posts_for_that_notification_and_refreshes_the_inbox_and_bell(self):
        inbox = self.probe('inbox')
        self.assertEqual(inbox['markRead'], {'handlers': 1})
        self.assertEqual(inbox['markReadCalls'], ['POST /api/notifications/n2/read {}', 'GET /api/notifications'])
        after = inbox['afterMarkRead']
        self.assertEqual(after['unread'], 1)
        self.assertEqual(after['badge'], '1')
        self.assertFalse(after['badgeHidden'])
        self.assertEqual(after['readButtons'], ['n1'])
        self.assertEqual(after['alerts'], [])

    def test_mark_all_read_posts_the_all_read_endpoint_and_clears_the_bell(self):
        inbox = self.probe('inbox')
        self.assertEqual(inbox['markAll'], {'handlers': 1})
        self.assertEqual(inbox['markAllCalls'], ['POST /api/notifications/read-all {}', 'GET /api/notifications'])
        after = inbox['afterMarkAll']
        self.assertEqual(after['unread'], 0)
        self.assertTrue(after['badgeHidden'])
        self.assertEqual(after['readButtons'], [])

    def test_a_refused_mark_read_is_reported_and_does_not_reload_or_clear_the_bell(self):
        inbox = self.probe('inbox')
        self.assertEqual(inbox['failReadCalls'], ['POST /api/notifications/n1/read {}'])
        self.assertEqual(inbox['failReadState'], {'alerts': ['server said no'], 'unread': 2})
        self.assertEqual(inbox['failAllCalls'], ['POST /api/notifications/read-all {}'])
        self.assertEqual(inbox['failAllState'], {'alerts': ['server said no'], 'unread': 2})

    # ---- 5. F2 people-list guards ----
    def _refused_while_unavailable(self, name, what):
        """Pending and failed lookups send nothing and say 'Retry people'; return what the ready case sent."""
        run = self.probe(name)
        for mode in ('pending', 'fail'):
            with self.subTest(people=mode):
                self.assertGreater(run[mode]['handlers'], 0, what + ' not wired')
                self.assertTrue(run[mode]['disabled'])
                self.assertEqual(run[mode]['sent'], [], 'a request was sent while the people list was unavailable')
                self.assertIn('Retry people', run[mode]['message'])
        self.assertFalse(run['ready']['disabled'])
        self.assertNotIn('Retry people', run['ready']['message'])
        return run['ready']['sent']

    def test_hold_in_the_task_panel_is_refused_while_the_people_list_is_unavailable(self):
        sent = self._refused_while_unavailable('lifecycleHold', 'hold form')
        self.assertEqual(sent, [{'m': 'POST', 'path': '/api/tasks/t1/hold', 'body': {
            'reason': 'waiting for parts', 'checkpoint_date': '2026-11-01', 'owner_user_id': 'u2'}}])

    def test_hold_on_the_board_is_refused_while_the_people_list_is_unavailable(self):
        sent = self._refused_while_unavailable('boardHold', 'hold dialog')
        self.assertEqual(len(sent), 1)
        self.assertEqual((sent[0]['m'], sent[0]['path']), ('POST', '/api/tasks/t1/board-move'))
        self.assertEqual(sent[0]['body']['to_column'], 'blocked')
        self.assertEqual(sent[0]['body']['owner_user_id'], 'u2')
        self.assertEqual(sent[0]['body']['reason'], 'waiting for parts')

    def test_add_reviewer_is_refused_while_the_people_list_is_unavailable(self):
        sent = self._refused_while_unavailable('addReviewer', 'Add reviewer button')
        self.assertEqual(sent, [{'m': 'POST', 'path': '/api/task-reviewers',
                                 'body': {'task_id': 't1', 'user_id': 'u2', 'role': 'reviewer'}}])
