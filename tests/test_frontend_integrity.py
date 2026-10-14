"""Exercise actual frontend functions under reordered and failed HTTP responses."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_web import WIRING_DRIVER, STATIC


PROBES = r'''
const probe = `;
globalThis.runProbe=async()=>{
  state.user={id:'owner',global_role:'owner'};state.tasks=[];state.projects=[];
  const realOpen=openDetail,realClose=closePanel,realFill=fillAssignees,realLoad=load;
  currentRoute=()=>({name:'home',params:new URLSearchParams(),path:'home'});
  syncPanelInert=()=>{};dropLease=async()=>{};
  let rendered=null;
  renderDetail=t=>{rendered=t.id};
  openPanel=id=>{panelState.shown=id;document.querySelector('#detail-dialog').hidden=false};
  const pending={};
  api=path=>path.endsWith('/events')?Promise.resolve({events:[]}):new Promise((resolve,reject)=>{pending[path]={resolve,reject}});
  const a=realOpen('A'),b=realOpen('B');
  pending['/api/tasks/B'].resolve({task:{id:'B'}});await b;
  pending['/api/tasks/A'].resolve({task:{id:'A'}});await a;
  const race={rendered,saveTarget:detailTaskId,panel:panelState.task?.id};
  const old=realOpen('B');const oldResolve=pending['/api/tasks/B'].resolve;
  const latest=realOpen('B');pending['/api/tasks/B'].resolve({task:{id:'B',revision:2}});await latest;
  oldResolve({task:{id:'B',revision:1}});await old;
  const sameTask=panelState.task?.revision;
  const closing=realOpen('C');realClose(true);
  pending['/api/tasks/C'].resolve({task:{id:'C'}});await closing;
  const closed=document.querySelector('#detail-dialog').hidden;
  const nodes=[];
  const makeSelect=()=>({innerHTML:'',value:'saved-owner',options:[],dataset:{},disabled:false,
    parentElement:{appendChild:n=>nodes.push(n)},add(o){this.options.push(o);if(o.selected)this.value=o.value},
    setAttribute(){},removeAttribute(){},insertAdjacentElement(p,n){nodes.push(n)},closest(){return null}});
  const select=makeSelect();api=async()=>{throw new Error('lookup failed')};
  await realFill('p',select,'saved-owner','task','Existing owner');
  const failed={value:select.value,disabled:select.disabled,feedback:nodes.map(n=>n.textContent).join(' ')};
  const pendingSelect=makeSelect();let release;
  api=()=>new Promise(r=>{release=r});const filling=realFill('p',pendingSelect,'saved-owner','task','Existing owner');
  const during={value:pendingSelect.value,disabled:pendingSelect.disabled};
  release({users:[{id:'saved-owner',display_name:'Existing owner'}]});await filling;
  const after={value:pendingSelect.value,disabled:pendingSelect.disabled};
  state.notifications=[{id:'n1'}];state.unread=7;state.notificationsKnown=true;
  fillFilters=()=>{};applyRoute=()=>{};
  api=async path=>{if(path==='/api/notifications')throw new Error('offline');return {projects:[],tasks:[],entities:[]}};
  await realLoad();const notice={unread:state.unread,notifications:state.notifications.length,stale:state.notificationsStale};
  const history=renderEvent({event_type:'task_updated',occurred_at:'2026-10-13T15:00:00Z',actor_name:'Owner',
    before_json:JSON.stringify({owner_user_id:'old',owner_name:'Jordan'}),
    after_json:JSON.stringify({owner_user_id:'new',owner_name:'Taylor'})});
  api=async()=>({users:[{id:'a',display_name:'Alex Lee',email:'alex.a@example.org'},
    {id:'b',display_name:'Alex Lee',email:'alex.b@example.org'}]});
  const duplicates=makeSelect();await realFill('p',duplicates,'');
  document.querySelector('#detail-body').innerHTML='<div id="template-role-fields"></div><div id="detail-edit-error"></div><select id="bulk-input"></select>';
  renderRolePicker('project',['member'],[{id:'off',display_name:'Inactive',active:0,global_role:'member'},
    {id:'on',display_name:'Active person',active:1,global_role:'member'}]);
  const rolesHtml=document.querySelector('#template-role-fields').innerHTML;
  const writes=[];let sendLater,finished;
  load=async()=>{};openDetail=async id=>{writes.push({reopened:id})};
  api=async(path,options)=>{writes.push({path,body:JSON.parse(options.body)});return {task:{id:'A'}}};
  withDependencyConfirm=async(t,s,send)=>{sendLater=send;return new Promise(r=>{finished=r})};
  detailTaskId='A';panelState.shown='A';panelState.task={id:'A'};
  const saving=submitDetailEdit({preventDefault(){},target:{dataset:{taskId:'A'},__entries:[['expected_revision','1'],['title','Edit A']]}});
  detailTaskId='B';panelState.shown='B';panelState.task={id:'B'};
  finished(await sendLater({}));await saving;
  const stableWrite={path:writes[0].path,reopened:writes.some(x=>x.reopened),selected:detailTaskId};
  writes.length=0;let saved;
  api=()=>new Promise(r=>{saved=r});detailTaskId='A';panelState.shown='A';
  const marking=markFinalResult('A','submission','s1');detailTaskId='B';panelState.shown='B';saved({});await marking;
  const stayedOnB=!writes.some(x=>x.reopened);
  bulk.action='assignee';document.querySelector('#bulk-input').disabled=true;let bulkCalls=0;
  api=async()=>{bulkCalls++;return {}};showToast=()=>{};askBulk=async()=>null;await reviewBulk('p');
  return {race,sameTask,closed,failed,during,after,notice,history,rolesHtml,stableWrite,stayedOnB,bulkCalls,
    duplicates:duplicates.options.map(o=>o.text)};
};`;
(0,eval)(src+probe);
runProbe().then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{console.error(e);process.exit(1)});
'''


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class FrontendIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        driver = WIRING_DRIVER.split('const harness=')[0] + PROBES
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, 'integrity.js')
            path.write_text(driver, encoding='utf-8')
            result = subprocess.run(['node', str(path), str(STATIC/'app.js'), str(STATIC/'index.html')],
                                    input='{}', capture_output=True, text=True, encoding='utf-8', timeout=15)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.out = json.loads(result.stdout)

    def test_late_task_response_cannot_change_rendered_identity(self):
        self.assertEqual(self.out['race'], {'rendered':'B', 'saveTarget':'B', 'panel':'B'})

    def test_late_same_task_response_cannot_replace_newer_revision(self):
        self.assertEqual(self.out['sameTask'], 2)

    def test_close_during_load_cannot_reopen_panel(self):
        self.assertTrue(self.out['closed'])

    def test_failed_assignee_lookup_preserves_owner_and_reports_failure(self):
        self.assertEqual(self.out['failed']['value'], 'saved-owner')
        self.assertTrue(self.out['failed']['disabled'])
        self.assertIn('could not', self.out['failed']['feedback'].lower())

    def test_pending_assignee_lookup_preserves_owner(self):
        self.assertEqual(self.out['during'], {'value':'saved-owner','disabled':True})
        self.assertEqual(self.out['after'], {'value':'saved-owner','disabled':False})

    def test_failed_notifications_preserve_last_known_snapshot(self):
        self.assertEqual(self.out['notice'], {'unread':7,'notifications':1,'stale':True})

    def test_assignment_history_names_old_and_new_owners(self):
        self.assertIn('Jordan', self.out['history'])
        self.assertIn('Taylor', self.out['history'])
        self.assertNotIn('No field changes', self.out['history'])

    def test_duplicate_names_can_be_distinguished_in_picker(self):
        self.assertTrue(any('alex.a@example.org' in t for t in self.out['duplicates']))
        self.assertTrue(any('alex.b@example.org' in t for t in self.out['duplicates']))

    def test_templates_exclude_numeric_inactive_users(self):
        self.assertNotIn('Inactive', self.out['rolesHtml'])
        self.assertIn('Active person', self.out['rolesHtml'])

    def test_confirmation_retry_keeps_original_task_identity(self):
        self.assertEqual(self.out['stableWrite'], {'path':'/api/tasks/A','reopened':False,'selected':'B'})

    def test_finishing_final_result_does_not_reopen_previous_task(self):
        self.assertTrue(self.out['stayedOnB'])

    def test_unavailable_bulk_picker_cannot_preview_unassignment(self):
        self.assertEqual(self.out['bulkCalls'], 0)


class FrontendControlTests(unittest.TestCase):
    def test_cancel_does_not_submit_or_validate_required_fields(self):
        html = (STATIC/'index.html').read_text(encoding='utf-8')
        for form_id in ('project-form','task-form'):
            form = html.split('id="'+form_id+'"',1)[1].split('</form>',1)[0]
            cancel = next(t for t in re.findall(r'<button[^>]*>',form) if 'value="cancel"' in t)
            self.assertIn('formnovalidate', cancel)

    def test_reviewer_controls_are_named(self):
        js = (STATIC/'app.js').read_text(encoding='utf-8')
        for name in ('reviewer-user','reviewer-role'):
            tag = re.search(r'<select[^>]*id="'+name+r'"[^>]*>',js).group()
            self.assertIn('aria-label=', tag)

    def test_templates_do_not_ask_for_internal_identifiers(self):
        js = (STATIC/'app.js').read_text(encoding='utf-8')
        self.assertFalse('prompt("Target project id' in js, 'Task template still requests a project UUID')
        self.assertFalse('prompt("Parent task id' in js, 'Task template still requests a parent UUID')

    def test_project_search_results_are_links(self):
        js = (STATIC/'app.js').read_text(encoding='utf-8')
        part = js.split('async function openSearch(',1)[1].split('document.querySelector',1)[0]
        self.assertIn('#/project/', part)

    def test_colours_outside_root_use_tokens(self):
        css = (STATIC/'style.css').read_text(encoding='utf-8')
        css = re.sub(r'/\*.*?\*/','',css,flags=re.S)
        outside = css.split(':root {',1)[1].split('}',1)[1]
        self.assertEqual(re.findall(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(',outside), [])
