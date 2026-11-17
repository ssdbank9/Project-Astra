"""Edit Step: the sheet a Gantt bar opens, as in the shadcnstudio gantt-chart-04 block.

Observed in the block on 2026-11-17: a click on a bar, or Enter on a focused bar, opens "Edit Step"
(Name, Phase, Type, Owner, Status, Start, End, Progress, Depends on, Note; Delete, Discard, Save). Aly
(2026-11-17) chose to build it, to keep the step name for Astra's full task panel, and to turn the
block's Delete into "Cancel step": Astra never deletes a task, so the step is closed as Cancelled through
the existing rules and keeps its history.

The sheet adds no endpoint. It sends only what changed, through the calls the task panel already uses:
POST /api/tasks/{id} (update_task), POST /api/tasks/{id}/parent (set_parent) and POST / DELETE
/api/task-dependencies. So:

- UI tests: Node runs the real app.js (the DOM stub of test_gantt_zoom.py) and checks who gets the sheet,
  what it offers and exactly what it sends, in which order;
- service and HTTP tests: who may cancel a step or move it to another phase, role by role, because the
  page only decides whether to show the sheet; service.py is the check.
"""
import json
import unittest

from astra.service import Forbidden
from test_frontend_gaps_views import run_probe   # a function only: no test class is imported
from test_gantt_new_step import _HttpFixture, _ServiceFixture   # fixtures only: no test class is imported
from test_gantt_zoom import SETUP                # the shared probe prelude: no test class is imported
from test_web import STATIC


EDIT_PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
''' + SETUP + r'''
  const sheet=document.querySelector("#step-sheet"),form=document.querySelector("#step-form");
  form.closest=s=>s==="dialog"?sheet:null;
  sheet.close=()=>{sheet.open=false;for(const f of sheet._l.close||[])f()};
  const F=n=>document.querySelector(`#step-form [name="${n}"]`),S=id=>document.querySelector(id);
  const calls=[],toasts=[],details=[],people=[];let reply=()=>({task:{id:"k1"}});
  api=async(path,opt)=>{
    if(path.startsWith("/api/assignable-users")){people.push(path.split("?")[1]);return {users:[{id:"u1",display_name:"Olive Owner"},{id:"u2",display_name:"Mo Member"}]}}
    const body=opt&&opt.body?JSON.parse(opt.body):null;calls.push([path,opt&&opt.method,body]);return reply(path,body)};
  let loads=0;load=async()=>{loads++};
  showToast=(...a)=>{toasts.push(a[0])};
  openDetail=async id=>{details.push(id)};
  // Leases run on timers; the panel's lease code has its own tests.
  takeLease=async()=>({ok:true});dropLease=async()=>{};
  const tick=()=>new Promise(r=>setTimeout(r,60));
  const tasks=()=>[
    T("a","Alpha","2026-06-01","2026-06-05",{status:"completed",timeline_order:1}),
    T("par","Design","2026-06-08","2026-06-19",{timeline_order:2}),
    T("k1","Kid one","2026-06-08","2026-06-09",{parent_task_id:"par",predecessors:P(["a"]),progress:20,description:"Draft it",revision:4}),
    T("sub","Inside kid one","2026-06-08","2026-06-08",{parent_task_id:"k1"}),
    T("k2","Kid two","2026-06-10","2026-06-12",{parent_task_id:"par",predecessors:P(["k1"])}),
    T("k3","Kid three","2026-06-13","2026-06-14",{parent_task_id:"par",predecessors:P(["k2"])}),
    T("b","Beta","2026-06-15","2026-06-16",{timeline_order:3}),
    T("m","Launch",null,"2026-06-20",{is_milestone:true,timeline_order:4}),
    T("x","Dropped","2026-06-01","2026-06-02",{status:"cancelled",timeline_order:5}),
    T("rev","In review","2026-06-03","2026-06-04",{status:"submitted",timeline_order:6}),
    T("y","Other project","2026-06-10","2026-06-11",{project_id:"pr2",project_name:"Second"}),
  ];
  const projects=[{id:"pr1",name:"Release Plan",status:"active",can_manage:true},{id:"pr2",name:"Second",status:"active",can_manage:false}];
  const clickBar=id=>{for(const f of g._l.click||[])f({target:{closest:s=>s==="[data-bar]"?{dataset:{bar:id}}:null}})};
  const key=(id,k,o={})=>{
    const bar={dataset:{bar:id}};bar.closest=s=>s==="[data-bar]"?bar:null;
    const target=o.child?{closest:s=>s==="[data-bar]"?bar:null}:bar;let prevented=false;
    for(const f of g._l.keydown||[])f({key:k,repeat:!!o.repeat,target,preventDefault(){prevented=true}});return prevented};
  const opts=sel=>[...F(sel).innerHTML.matchAll(/<option value="([^"]*)">([^<]*)<\/option>/g)].map(m=>[m[1],m[2]]);
  const depRows=()=>[...S("#step-deps").innerHTML.matchAll(/name="dep" value="([^"]*)"( checked)?><span class="gx-dep-name">([^<]*)</g)].map(m=>[m[1],!!m[2]]);
  // Parsed boxes start from their markup, as a browser's do.
  const boxes=()=>{const n=document.querySelectorAll('#step-deps [name="dep"]');n.forEach(b=>{if(!b.hasAttribute("data-probe")){b.setAttribute("data-probe","1");b.value=b.getAttribute("value");b.checked=b.hasAttribute("checked")}});return n};
  const tickBox=(id,on)=>{const b=boxes().find(x=>x.value===id);if(!b)throw new Error("no box "+id+" in "+JSON.stringify(depRows())+" "+JSON.stringify(boxes().map(x=>x.value)));b.checked=on;for(const f of form._l.change||[])f({target:{name:"dep"}})};
  const submit=async()=>{for(const f of form._l.submit||[])await f({preventDefault(){},target:form,submitter:{value:"default",disabled:false}});await tick()};
  const face=()=>({title:S("#step-sheet-title").textContent,desc:S("#step-sheet-desc").textContent,submit:S("#step-submit").textContent,
    openTask:!S("#step-open-task").hidden,cancel:!S("#step-cancel-step").hidden,typeLocked:!!F("type").disabled,statuses:opts("status").map(o=>o[0])});
  const open=id=>{boot(tasks(),{projects});clickBar(id);F("owner_user_id").value=(state.tasks.find(t=>t.id===id)||{}).owner_user_id||"";boxes()};

  // ---- who gets the sheet ----
  open("k1");
  out.opened={open:!!sheet.open,face:face(),phase:F("phase").value,phases:opts("phase"),deps:depRows(),people:people.slice(-1)[0],
    fields:["title","type","status","start_date","due_date","progress","description"].map(n=>F(n).value),endHidden:S("#step-form [data-end-field]").hidden,
    reasonHidden:S("#step-reason-field").hidden,error:S(".error").textContent};
  sheet.close();
  out.others={};
  for(const id of ["x","rev","y"]){details.length=0;open(id);out.others[id]={sheet:!!sheet.open,details:details.slice()}}
  open("m");out.milestone={type:F("type").value,date:F("start_date").value,endHidden:S("#step-form [data-end-field]").hidden,label:S("#step-form [data-start-label]").textContent};sheet.close();

  // ---- the keyboard ----
  boot(tasks(),{projects});
  out.keys={};
  for(const [name,k,o] of [["enter","Enter",{}],["space"," ",{}],["letter","a",{}],["held","Enter",{repeat:true}],["inside","Enter",{child:true}]]){
    sheet.open=false;const prevented=key("b",k,o);out.keys[name]={open:!!sheet.open,prevented}}
  sheet.close();

  // ---- saving ----
  open("k1");calls.length=0;const loadsNothing=loads;S("#gantt-live").textContent="";await submit();
  out.nothing={calls:calls.length,open:!!sheet.open,reloads:loads-loadsNothing,said:S("#gantt-live").textContent};

  open("k1");calls.length=0;F("progress").value="50";F("title").value="  Kid one, renamed ";await submit();
  out.fields={calls:calls.splice(0),open:!!sheet.open,loads};

  open("k1");calls.length=0;F("start_date").value="2026-06-09";F("due_date").value="2026-06-11";
  for(const f of form._l.input||[])await f({target:{name:"due_date"}});
  F("reason").value="";await submit();
  out.noReason={calls:calls.length,open:!!sheet.open,error:S(".error").textContent,reasonHidden:S("#step-reason-field").hidden,required:!!F("reason").required};
  F("reason").value="Review moved";await submit();
  out.dates={calls:calls.splice(0),open:!!sheet.open};

  open("k1");calls.length=0;tickBox("a",false);tickBox("b",true);
  out.dropNeedsReason=!S("#step-reason-field").hidden;
  F("reason").value="Alpha is not needed";await submit();
  out.links={calls:calls.splice(0)};

  open("k1");calls.length=0;F("phase").value="p:pr1";for(const f of form._l.change||[])f({target:{name:"phase"}});await tick();boxes();
  out.phaseDeps=depRows();
  F("progress").value="30";tickBox("b",true);await submit();
  out.order={calls:calls.splice(0).map(c=>[c[0],c[1]]),parent:null};

  // ---- refusals ----
  open("k1");calls.length=0;const before=loads;
  reply=()=>{throw Object.assign(new Error("Task title is required."),{status:400})};
  F("progress").value="55";await submit();
  out.refused={calls:calls.length,open:!!sheet.open,error:S(".error").textContent,loads:loads-before};

  open("k1");calls.length=0;
  reply=(path)=>{if(path==="/api/task-dependencies")throw Object.assign(new Error("That link would make a loop."),{status:400});return {task:{id:"k1"}}};
  F("progress").value="60";tickBox("b",true);await submit();
  out.partial={calls:calls.splice(0).map(c=>c[0]),open:!!sheet.open,error:S(".error").textContent,reloaded:loads>before};

  open("k1");calls.length=0;
  reply=()=>{throw Object.assign(new Error("Task revision conflict: expected 4, current revision is 5."),{status:409})};
  F("progress").value="61";await submit();
  out.conflict={calls:calls.length,open:!!sheet.open,error:S(".error").textContent};

  // ---- confirmations, as from the task panel ----
  const asked=[];let answer={confirmed:true},first=true;
  askMove=async(kind,t)=>{asked.push([kind,t.title]);return answer};
  reply=(path,body)=>{if(first&&!body.confirmed){first=false;throw Object.assign(new Error("Moving it has consequences."),{status:409,confirm:"impact",impact:["x"]})}return {task:{id:"k1"}}};
  open("k1");calls.length=0;F("due_date").value="2026-06-12";F("reason").value="Later";await submit();
  out.confirmed={asked:asked.splice(0),calls:calls.splice(0).map(c=>c[2]),open:!!sheet.open};
  first=true;answer=null;
  open("k1");calls.length=0;F("due_date").value="2026-06-12";F("reason").value="Later";await submit();
  out.declined={asked:asked.splice(0).length,calls:calls.splice(0).length,open:!!sheet.open,error:S(".error").textContent};

  // ---- a manager's status change becomes an Owner request ----
  reply=()=>({request:{id:"r1"}});
  open("k1");calls.length=0;F("status").value="delayed";F("reason").value="Supplier late";await submit();
  out.request={calls:calls.splice(0).map(c=>c[2]),toast:toasts.slice(-1)[0]};

  // ---- Cancel step ----
  reply=()=>({task:{id:"k1",status:"cancelled"}});
  open("k1");calls.length=0;S("#step-cancel-step").onclick();
  out.ask={shown:!S("#step-cancel-confirm").hidden,text:S("#step-cancel-text").textContent};
  F("cancel_reason").value="  ";await S("#step-cancel-go").onclick();
  out.cancelNoReason={calls:calls.length,error:S(".error").textContent,open:!!sheet.open};
  S("#step-cancel-keep").onclick();out.kept={hidden:S("#step-cancel-confirm").hidden,open:!!sheet.open};
  S("#step-cancel-step").onclick();F("cancel_reason").value="Supplier gone";await S("#step-cancel-go").onclick();await tick();
  out.cancelled={calls:calls.splice(0),open:!!sheet.open,toast:toasts.slice(-1)[0]};
  reply=()=>({request:{id:"r2"}});
  open("k1");S("#step-cancel-step").onclick();F("cancel_reason").value="Supplier gone";await S("#step-cancel-go").onclick();await tick();
  out.cancelRequest={toast:toasts.slice(-1)[0],open:!!sheet.open};

  // ---- Enter in the reason for cancelling cancels; it never saves ----
  reply=()=>({task:{id:"k1",status:"cancelled"}});
  open("k1");calls.length=0;F("progress").value="77";S("#step-cancel-step").onclick();F("cancel_reason").value="Gone";await submit();
  out.enterCancels={calls:calls.splice(0).map(c=>c[2]),open:!!sheet.open};

  // ---- a lock held by someone else keeps what was typed ----
  const lock={holder_name:"Mo Member",kind:"edit",expires_at:"2026-06-10T10:05:00Z"};
  reply=()=>{throw Object.assign(new Error("Task is locked."),{status:409,lock})};
  open("k1");calls.length=0;const loadsBefore=loads;F("progress").value="66";await submit();
  out.locked={calls:calls.length,open:!!sheet.open,progress:F("progress").value,reloaded:loads>loadsBefore,error:S(".error").textContent};

  // ---- a stale cancel reloads the step, so a second try can work ----
  reply=()=>{throw Object.assign(new Error("Task revision conflict."),{status:409})};
  open("k1");S("#step-cancel-step").onclick();F("cancel_reason").value="Gone";const before2=loads;await S("#step-cancel-go").onclick();await tick();
  out.staleCancel={open:!!sheet.open,reloaded:loads>before2,error:S(".error").textContent};

  // ---- a lease that arrives after the sheet closed is let go ----
  let grant;const dropped=[];
  takeLease=()=>new Promise(r=>{grant=r});dropLease=async(id,kind)=>{dropped.push([id,kind])};
  open("k1");for(const f of form._l.input||[])f({target:{name:"title"}});
  sheet.close();const atClose=dropped.length;grant({ok:true});await tick();
  out.lateLease={atClose,dropped:dropped.slice()};
  takeLease=async()=>({ok:true});dropLease=async()=>{};

  // ---- Open task, and New Step afterwards ----
  open("k1");details.length=0;S("#step-open-task").onclick();
  out.openTask={sheet:!!sheet.open,details:details.slice()};
  boot(tasks(),{projects});H.store["#gantt-new-step"].onclick();
  out.newAfter={face:face(),editId:gx.editId};
  return out;
};
'''


class EditStepSheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(EDIT_PROBE, static=STATIC)

    # ---- who gets the sheet ------------------------------------------------------------------------
    def test_a_click_on_a_bar_opens_edit_step_filled_from_the_step(self):
        o = self.out['opened']
        self.assertTrue(o['open'])
        self.assertEqual((o['face']['title'], o['face']['desc'], o['face']['submit']),
                         ('Edit Step', 'Update the schedule, status and links of this step.', 'Save'))
        self.assertEqual(o['fields'], ['Kid one', 'task', 'assigned', '2026-06-08', '2026-06-09', '20', 'Draft it'])
        self.assertEqual(o['phase'], 't:par')
        self.assertEqual((o['face']['openTask'], o['face']['cancel']), (True, True))
        self.assertEqual(o['error'], '')
        self.assertTrue(o['reasonHidden'])

    def test_the_owner_list_is_asked_for_the_steps_project_as_a_sub_task(self):
        self.assertEqual(self.out['opened']['people'], 'project_id=pr1&for=subtask')

    def test_the_type_is_shown_but_cannot_change(self):
        self.assertTrue(self.out['opened']['face']['typeLocked'])

    def test_the_status_list_is_the_task_panels_without_owner_only_statuses_and_without_cancelling(self):
        self.assertEqual(self.out['opened']['face']['statuses'],
                         ['draft', 'assigned', 'in_progress', 'changes_requested', 'delayed'])

    def test_the_phase_list_leaves_out_the_step_and_anything_inside_it(self):
        self.assertEqual(self.out['opened']['phases'], [['p:pr1', 'Release Plan'], ['t:par', 'Release Plan › Design (RP-01)']])

    def test_depends_on_ticks_the_current_predecessors_and_leaves_out_loops(self):
        # Kid one cannot wait for itself, the step inside it, Kid two and Kid three (they wait on it), its own
        # phase, or a cancelled step; Alpha is its predecessor now.
        rows = dict(self.out['opened']['deps'])
        self.assertEqual(rows, {'a': True, 'b': False, 'm': False, 'rev': False})

    def test_a_closed_step_a_step_in_review_and_a_step_the_user_cannot_change_open_the_task_panel(self):
        self.assertEqual(self.out['others'], {'x': {'sheet': False, 'details': ['x']},
                                              'rev': {'sheet': False, 'details': ['rev']},
                                              'y': {'sheet': False, 'details': ['y']}})

    def test_a_milestone_shows_its_one_date(self):
        self.assertEqual(self.out['milestone'], {'type': 'milestone', 'date': '2026-06-20', 'endHidden': True, 'label': 'Date'})

    def test_enter_and_space_on_a_bar_open_the_sheet_and_nothing_else_does(self):
        k = self.out['keys']
        self.assertEqual(k['enter'], {'open': True, 'prevented': True})
        self.assertEqual(k['space'], {'open': True, 'prevented': True})
        for name in ('letter', 'held', 'inside'):
            self.assertEqual(k[name], {'open': False, 'prevented': False}, name)

    # ---- saving --------------------------------------------------------------------------------------
    def test_save_with_nothing_changed_sends_nothing_and_closes(self):
        # Nothing was saved, so the page is not reloaded and nothing is announced as saved.
        self.assertEqual(self.out['nothing'], {'calls': 0, 'open': False, 'reloads': 0, 'said': ''})

    def test_save_sends_only_the_changed_fields_with_the_revision(self):
        f = self.out['fields']
        self.assertEqual(f['calls'], [['/api/tasks/k1', 'POST', {'title': 'Kid one, renamed', 'progress': 50, 'reason': '', 'expected_revision': 4}]])
        self.assertFalse(f['open'])
        self.assertGreater(f['loads'], 0)

    def test_new_dates_need_a_reason_before_anything_is_sent(self):
        n = self.out['noReason']
        self.assertEqual((n['calls'], n['open'], n['reasonHidden'], n['required']), (0, True, False, True))
        self.assertIn('Give a reason', n['error'])
        self.assertEqual(self.out['dates']['calls'], [['/api/tasks/k1', 'POST', {
            'start_date': '2026-06-09', 'due_date': '2026-06-11', 'reason': 'Review moved', 'expected_revision': 4}]])
        self.assertFalse(self.out['dates']['open'])

    def test_links_are_added_and_removed_through_the_dependency_endpoint_with_the_reason(self):
        self.assertTrue(self.out['dropNeedsReason'])
        self.assertEqual(self.out['links']['calls'], [
            ['/api/task-dependencies', 'POST', {'predecessor_task_id': 'b', 'successor_task_id': 'k1'}],
            ['/api/task-dependencies', 'DELETE', {'predecessor_task_id': 'a', 'successor_task_id': 'k1', 'reason': 'Alpha is not needed'}]])

    def test_moving_to_the_project_offers_the_old_phase_as_a_predecessor_and_saves_in_order(self):
        self.assertIn(['par', False], self.out['phaseDeps'])
        self.assertIn(['a', True], self.out['phaseDeps'])          # the ticks are kept across the change
        # The phase first, so the owner is checked against where the step will sit.
        self.assertEqual(self.out['order']['calls'], [['/api/tasks/k1/parent', 'POST'], ['/api/tasks/k1', 'POST'],
                                                      ['/api/task-dependencies', 'POST']])

    # ---- refusals and confirmations --------------------------------------------------------------------
    def test_a_refusal_with_nothing_saved_keeps_the_sheet_and_its_values(self):
        self.assertEqual(self.out['refused'], {'calls': 1, 'open': True, 'error': 'Task title is required.', 'loads': 0})

    def test_a_refusal_after_part_was_saved_reloads_and_says_so(self):
        p = self.out['partial']
        self.assertEqual(p['calls'], ['/api/tasks/k1', '/api/task-dependencies'])
        self.assertTrue(p['open'])
        self.assertTrue(p['reloaded'])
        self.assertEqual(p['error'], 'Some changes were saved, but not all: That link would make a loop.')

    def test_a_revision_conflict_reloads_the_step(self):
        c = self.out['conflict']
        self.assertEqual((c['calls'], c['open']), (1, True))
        self.assertTrue(c['error'].startswith('This step changed since it was opened; it has been reloaded.'), c['error'])

    def test_a_change_with_consequences_is_confirmed_as_from_the_task_panel(self):
        c = self.out['confirmed']
        self.assertEqual(c['asked'], [['impact', 'Kid one']])
        self.assertEqual([b.get('confirmed') for b in c['calls']], [None, True])
        self.assertFalse(c['open'])

    def test_declining_the_confirmation_saves_nothing_more(self):
        self.assertEqual(self.out['declined'], {'asked': 1, 'calls': 1, 'open': True, 'error': ''})

    def test_a_managers_status_change_that_becomes_an_owner_request_says_so(self):
        r = self.out['request']
        self.assertEqual(r['calls'], [{'status': 'delayed', 'reason': 'Supplier late', 'expected_revision': 4}])
        self.assertTrue(r['toast'].startswith('Owner request created'), r['toast'])

    # ---- Cancel step -------------------------------------------------------------------------------------
    def test_cancel_step_asks_first(self):
        self.assertTrue(self.out['ask']['shown'])
        self.assertEqual(self.out['ask']['text'], 'Cancel “Kid one”? It is closed as Cancelled; its history is kept, '
                                                   'and it can be reopened from the task panel.')

    def test_cancel_step_needs_a_reason(self):
        self.assertEqual(self.out['cancelNoReason'], {'calls': 0, 'error': 'Give a reason for cancelling the step.', 'open': True})
        self.assertEqual(self.out['kept'], {'hidden': True, 'open': True})

    def test_cancel_step_sets_the_status_through_the_ordinary_update(self):
        c = self.out['cancelled']
        self.assertEqual(c['calls'], [['/api/tasks/k1', 'POST', {'status': 'cancelled', 'reason': 'Supplier gone', 'expected_revision': 4}]])
        self.assertFalse(c['open'])
        self.assertEqual(c['toast'], '“Kid one” was cancelled.')

    def test_a_managers_cancel_becomes_an_owner_request(self):
        self.assertEqual(self.out['cancelRequest']['toast'], 'Owner request created to cancel “Kid one”; the step stays until it is decided.')
        self.assertFalse(self.out['cancelRequest']['open'])

    def test_enter_in_the_reason_for_cancelling_cancels_and_saves_nothing_else(self):
        self.assertEqual(self.out['enterCancels'], {'calls': [{'status': 'cancelled', 'reason': 'Gone', 'expected_revision': 4}], 'open': False})

    def test_a_lock_keeps_the_sheet_and_what_was_typed(self):
        l = self.out['locked']
        self.assertEqual((l['calls'], l['open'], l['progress'], l['reloaded']), (1, True, '66', False))
        self.assertTrue(l['error'].startswith('Mo Member is changing this task (an edit)'), l['error'])

    def test_a_stale_cancel_reloads_the_step(self):
        s = self.out['staleCancel']
        self.assertEqual((s['open'], s['reloaded']), (True, True))
        self.assertTrue(s['error'].startswith('This step changed since it was opened; it has been reloaded.'), s['error'])

    def test_an_edit_lease_granted_after_the_sheet_closed_is_let_go(self):
        self.assertEqual(self.out['lateLease'], {'atClose': 1, 'dropped': [['k1', 'edit'], ['k1', 'edit']]})

    # ---- the rest -----------------------------------------------------------------------------------------
    def test_open_task_closes_the_sheet_and_opens_the_task_panel(self):
        self.assertEqual(self.out['openTask'], {'sheet': False, 'details': ['k1']})

    def test_new_step_after_an_edit_shows_the_new_step_sheet_again(self):
        f = self.out['newAfter']['face']
        self.assertEqual((f['title'], f['submit'], f['openTask'], f['cancel'], f['typeLocked']), ('New Step', 'Create', False, False, False))
        self.assertEqual(f['statuses'], ['draft', 'assigned', 'in_progress', 'delayed'])
        self.assertIsNone(self.out['newAfter']['editId'])


class EditStepMarkupTests(unittest.TestCase):
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    js = (STATIC / 'app.js').read_text(encoding='utf-8')

    def sheet(self):
        s = self.html[self.html.index('<dialog id="step-sheet"'):]
        return s[:s.index('</dialog>')]

    def test_the_sheet_has_open_task_cancel_step_and_a_reason_hidden_until_needed(self):
        s = self.sheet()
        self.assertIn('<button type="button" class="link gx-sheet-open" id="step-open-task" hidden>Open task</button>', s)
        self.assertIn('<button type="button" class="quiet gx-danger" id="step-cancel-step" hidden>Cancel step</button>', s)
        self.assertIn('<label id="step-reason-field" hidden>Reason<input name="reason"', s)
        self.assertIn('<div class="gx-cancel-confirm" id="step-cancel-confirm" role="group" aria-labelledby="step-cancel-text" hidden>', s)
        # Enter still submits with Save (or Create): every other button is type="button".
        buttons = __import__('re').findall(r'<button[^>]*>', s)
        self.assertEqual([b for b in buttons if 'type="button"' not in b], ['<button value="default" id="step-submit">'])
        self.assertNotIn('style=', s)

    def test_the_sheet_uses_the_existing_endpoints_only(self):
        for needle in ('api(taskApi(t.id),{method:"POST"', 'api(taskApi(t.id,"/parent"),{method:"POST"',
                       'api("/api/task-dependencies",{method:"POST"', 'api("/api/task-dependencies",{method:"DELETE"'):
            self.assertIn(needle, self.js)


class EditStepServiceTests(_ServiceFixture, unittest.TestCase):
    """What the sheet's writes allow, role by role: service.py is the check."""

    def revision(self, task_id):
        return self.db.execute('SELECT revision FROM tasks WHERE id=?', (task_id,)).fetchone()[0]

    def status(self, task_id):
        return self.db.execute('SELECT status FROM tasks WHERE id=?', (task_id,)).fetchone()[0]

    def cancel(self, actor, task_id, reason='Not needed'):
        return self.s.update_task(actor, task_id, {'status': 'cancelled', 'reason': reason, 'expected_revision': self.revision(task_id)})

    def test_the_app_owner_cancels_a_step_and_it_keeps_its_history(self):
        self.cancel(self.owner, self.a['id'])
        self.assertEqual(self.status(self.a['id']), 'cancelled')
        self.assertEqual(self.db.execute('SELECT count(*) FROM tasks WHERE id=?', (self.a['id'],)).fetchone()[0], 1)
        self.assertEqual(self.events(self.a['id'], 'task_updated')[-1]['status'], 'cancelled')

    def test_a_managers_cancel_is_an_owner_request_and_the_step_stays_open(self):
        out = self.cancel(self.people['manager'], self.a['id'])
        self.assertIn('request', out)
        self.assertEqual(self.status(self.a['id']), 'draft')

    def test_a_member_a_viewer_and_an_outsider_cannot_cancel_a_step(self):
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role), self.assertRaises(Forbidden):
                self.cancel(self.people[role], self.a['id'])
        self.assertEqual(self.status(self.a['id']), 'draft')

    def test_cancelling_needs_a_reason(self):
        with self.assertRaises(ValueError):
            self.cancel(self.owner, self.a['id'], reason='')
        self.assertEqual(self.status(self.a['id']), 'draft')

    def test_only_the_owner_and_the_manager_move_a_step_to_another_phase(self):
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role), self.assertRaises(Forbidden):
                self.s.set_parent(self.people[role], self.b['id'], self.a['id'])
        self.assertIsNone(self.db.execute('SELECT parent_task_id FROM tasks WHERE id=?', (self.b['id'],)).fetchone()[0])
        self.s.set_parent(self.people['manager'], self.b['id'], self.a['id'])
        self.assertEqual(self.db.execute('SELECT parent_task_id FROM tasks WHERE id=?', (self.b['id'],)).fetchone()[0], self.a['id'])
        self.s.set_parent(self.owner, self.b['id'], None)
        self.assertIsNone(self.db.execute('SELECT parent_task_id FROM tasks WHERE id=?', (self.b['id'],)).fetchone()[0])


class EditStepHttpTests(_HttpFixture, unittest.TestCase):
    def status(self, task_id):
        return self.s.db.execute('SELECT status FROM tasks WHERE id=?', (task_id,)).fetchone()[0]

    def cancel(self, email, task_id):
        revision = self.s.db.execute('SELECT revision FROM tasks WHERE id=?', (task_id,)).fetchone()[0]
        return self.request('POST', f'/api/tasks/{task_id}', {'status': 'cancelled', 'reason': 'Not needed', 'expected_revision': revision},
                            self.login(email))

    def test_cancel_step_over_http_by_role(self):
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role):
                response, body = self.cancel(f'step-{role}@example.org', self.a['id'])
                self.assertEqual(response.status, 403, body)
        self.assertEqual(self.status(self.a['id']), 'draft')
        response, body = self.cancel('step-manager@example.org', self.a['id'])
        self.assertEqual(response.status, 202, body)
        self.assertIn('request', body)
        self.assertEqual(self.status(self.a['id']), 'draft')
        response, body = self.cancel('step-owner@example.org', self.b['id'])
        self.assertEqual(response.status, 200, body)
        self.assertEqual(self.status(self.b['id']), 'cancelled')

    def test_moving_a_step_to_another_phase_over_http_by_role(self):
        path, move = f"/api/tasks/{self.b['id']}/parent", {'parent_task_id': self.a['id']}
        for role in ('member', 'viewer', 'outsider'):
            with self.subTest(role=role):
                response, body = self.request('POST', path, move, self.login(f'step-{role}@example.org'))
                self.assertEqual(response.status, 403, body)
        response, body = self.request('POST', path, move, self.login('step-manager@example.org'))
        self.assertEqual(response.status, 200, body)
        self.assertEqual(json.loads(json.dumps(body))['task']['parent_task_id'], self.a['id'])


if __name__ == '__main__':
    unittest.main()
