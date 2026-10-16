"""Behaviour tests for the 2026-10-16 review gaps in the F1-F9 frontend repairs.

Each case runs the real app.js in Node against the shared DOM stub, so removing the
guard it names makes the test fail.
"""
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
  const out={};
  currentRoute=()=>({name:'home',params:new URLSearchParams(),path:'home'});
  const body=document.querySelector('#detail-body');

  // F2: a disabled people list must stop the single-task assignment save before any request.
  body.innerHTML='<div id="detail-assign-error"></div>';
  let calls=0;const paths=[];api=async(path,o)=>{calls++;paths.push((o&&o.method||'GET')+' '+path);return {task:{id:'A'}}};
  await submitAssign({preventDefault(){},target:{dataset:{taskId:'A'},__entries:[['owner_user_id',''],['expected_revision','1']],
    querySelector:()=>({disabled:true})}});
  out.assign={calls,message:document.querySelector('#detail-assign-error').textContent};
  calls=0;paths.length=0;
  await submitAssign({preventDefault(){},target:{dataset:{taskId:'A'},__entries:[['owner_user_id',''],['expected_revision','1']],
    querySelector:()=>({disabled:false})}});
  out.assignEnabled={first:paths[0]};

  // F5: a Viewer (or a Member who does not manage) gets no Add a task entry point.
  state.user={id:'v',global_role:'member'};
  state.projects=[{id:'p',name:'P',status:'open',can_manage:false}];state.tasks=[];
  try{fillFilters()}catch(e){out.fillFiltersThrew=(out.fillFiltersThrew||0)+1}
  out.viewerNewTaskHidden=document.querySelector('#new-task').hidden;
  const toasts=[];showToast=m=>toasts.push(m);
  openCapture('p');
  out.viewerCapture={toasts};
  state.projects=[{id:'p',name:'P',status:'open',can_manage:true}];
  try{fillFilters()}catch(e){out.fillFiltersThrew=(out.fillFiltersThrew||0)+1}
  out.managerNewTaskHidden=document.querySelector('#new-task').hidden;
  state.projects=[{id:'p',name:'P',status:'closed',can_manage:true}];
  try{fillFilters()}catch(e){out.fillFiltersThrew=(out.fillFiltersThrew||0)+1}
  out.closedNewTaskHidden=document.querySelector('#new-task').hidden;

  // F9: the bell never shows a false zero when notifications could not be loaded.
  const inbox=document.querySelector('#inbox');const attrs={};inbox.setAttribute=(k,v)=>{attrs[k]=v};
  const badge=document.querySelector('#unread-count');
  state.unread=0;state.notificationsKnown=false;state.notificationsStale=true;updateBell();
  out.bellUnknown={text:badge.textContent,hidden:badge.hidden,label:attrs['aria-label']};
  state.unread=7;state.notificationsKnown=true;state.notificationsStale=true;updateBell();
  out.bellStale={text:String(badge.textContent),hidden:badge.hidden,label:attrs['aria-label']};
  state.unread=0;state.notificationsKnown=true;state.notificationsStale=false;updateBell();
  out.bellClear={hidden:badge.hidden,label:attrs['aria-label']};
  state.unread=0;state.notificationsKnown=false;state.notificationsStale=false;updateBell();
  out.bellNeverLoaded={hidden:badge.hidden,label:attrs['aria-label']};
  state.user={id:'o',global_role:'member'};state.notificationsStale=false;
  api=async()=>{throw new Error('offline')};
  await openInbox();
  out.inboxFailure={stale:state.notificationsStale,html:document.querySelector('#inbox-body').innerHTML};
  return out;
};`;
(0,eval)(src+probe);
runProbe().then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{console.error(e);process.exit(1)});
'''


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class FrontendGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        driver = WIRING_DRIVER.split('const harness=')[0] + PROBES
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, 'gaps.js')
            path.write_text(driver, encoding='utf-8')
            result = subprocess.run(['node', str(path), str(STATIC / 'app.js'), str(STATIC / 'index.html')],
                                    input='{}', capture_output=True, text=True, encoding='utf-8', timeout=15)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.out = json.loads(result.stdout)

    def test_assignment_save_is_refused_while_the_people_list_is_unavailable(self):
        self.assertEqual(self.out['assign']['calls'], 0)
        self.assertIn('Retry people', self.out['assign']['message'])

    def test_assignment_save_still_sends_when_the_people_list_is_available(self):
        self.assertEqual(self.out['assignEnabled']['first'], 'POST /api/tasks/A')

    def test_add_a_task_is_hidden_unless_the_user_manages_an_open_project(self):
        self.assertTrue(self.out['viewerNewTaskHidden'])
        self.assertFalse(self.out['managerNewTaskHidden'])
        self.assertTrue(self.out['closedNewTaskHidden'])

    def test_capture_refuses_a_project_the_user_cannot_manage(self):
        self.assertEqual(len(self.out['viewerCapture']['toasts']), 1)
        self.assertIn('manage', self.out['viewerCapture']['toasts'][0])

    def test_bell_shows_a_warning_not_zero_when_notifications_never_loaded(self):
        self.assertEqual(self.out['bellUnknown'], {
            'text': '!', 'hidden': False, 'label': 'Inbox, notifications unavailable'})

    def test_bell_keeps_the_last_count_and_says_it_may_be_outdated(self):
        self.assertEqual(self.out['bellStale']['text'], '7')
        self.assertFalse(self.out['bellStale']['hidden'])
        self.assertIn('may be outdated', self.out['bellStale']['label'])

    def test_bell_is_quiet_before_the_first_load_when_nothing_has_failed(self):
        self.assertEqual(self.out['bellNeverLoaded'], {'hidden': True, 'label': 'Inbox'})

    def test_filters_fill_without_throwing_in_the_probe(self):
        self.assertNotIn('fillFiltersThrew', self.out)

    def test_bell_is_hidden_when_loaded_and_empty(self):
        self.assertEqual(self.out['bellClear'], {'hidden': True, 'label': 'Inbox'})

    def test_inbox_failure_shows_an_error_with_retry_and_marks_the_bell_stale(self):
        self.assertTrue(self.out['inboxFailure']['stale'])
        self.assertIn('could not be refreshed', self.out['inboxFailure']['html'])
        self.assertIn('id="inbox-retry"', self.out['inboxFailure']['html'])


class FrontendCancelCoverageTests(unittest.TestCase):
    def test_every_form_dialog_cancel_or_close_skips_required_field_validation(self):
        html = (STATIC / 'index.html').read_text(encoding='utf-8')
        for form_id in ('project-form', 'project-action-form', 'task-form'):
            form = html.split('id="' + form_id + '"', 1)[1].split('</form>', 1)[0]
            cancels = [t for t in re.findall(r'<button[^>]*>', form) if 'value="cancel"' in t]
            self.assertTrue(cancels, form_id + ' has no Cancel button')
            for tag in cancels:
                self.assertIn('formnovalidate', tag, form_id)
