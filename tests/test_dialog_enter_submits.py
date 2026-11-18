"""Enter in a form's field must submit it, never cancel it.

A browser submits a form on Enter with the form's first submit button. The Create project, close or
reopen project and Add a task forms had Cancel first, as a submit button, so Enter in a field closed
the dialog and nothing was saved (found on 2026-11-16 with the Gantt's New Step sheet, fixed for these
forms on 2026-11-18). Cancel is now a plain button that closes its dialog.

- The scan checks every form in index.html and every form app.js writes: in a form with a field, the
  first submit button is never Cancel, Close, Discard or Keep.
- The probe runs the real app.js (the DOM stub of test_frontend_gaps_views.py) and checks that each
  Cancel closes its dialog and sends nothing.
"""
import re
import unittest

from test_frontend_gaps_views import run_probe   # a function only: no test class is imported
from test_web import STATIC

CANCEL_WORDS = re.compile(r'^\s*(Cancel|Close|Discard|Keep\b)', re.I)


def forms(text):
    return re.findall(r'<form\b[^>]*>.*?</form>', text, re.S)


def first_submitter(form):
    for tag, label in re.findall(r'(<button\b[^>]*>)(.*?)</button>', form, re.S):
        if 'type="button"' in tag or "type='button'" in tag or 'type="reset"' in tag:
            continue
        return tag, re.sub(r'<[^>]+>|\$\{[^}]*\}', '', label)
    return None


def has_field(form):
    return re.search(r'<(input|select|textarea)\b(?![^>]*type="(hidden|checkbox|radio)")', form) is not None


class EnterSubmitsScanTests(unittest.TestCase):
    def offenders(self, text):
        bad = []
        for form in forms(text):
            first = first_submitter(form)
            if first and has_field(form) and CANCEL_WORDS.match(first[1]):
                bad.append((first[0], first[1].strip(), form[:120]))
        return bad

    def test_no_form_in_the_page_cancels_on_enter(self):
        self.assertEqual(self.offenders((STATIC / 'index.html').read_text(encoding='utf-8')), [])

    def test_no_form_the_script_writes_cancels_on_enter(self):
        self.assertEqual(self.offenders((STATIC / 'app.js').read_text(encoding='utf-8')), [])

    def test_the_scan_would_catch_the_old_markup(self):
        old = ('<form method="dialog" id="task-form"><label>Task title<input name="title" required></label>'
               '<div class="actions"><button value="cancel" formnovalidate class="quiet">Cancel</button>'
               '<button value="default">Add task</button></div></form>')
        self.assertEqual(len(self.offenders(old)), 1)

    def test_the_three_forms_submit_with_their_own_button(self):
        html = (STATIC / 'index.html').read_text(encoding='utf-8')
        for form_id, submit in (('project-form', 'Create'), ('project-action-form', 'Continue'), ('task-form', 'Add task')):
            with self.subTest(form=form_id):
                form = next(f for f in forms(html) if f'id="{form_id}"' in f)
                self.assertEqual(first_submitter(form)[1], submit)


CANCEL_PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={},calls=[];
  api=async(path,opt)=>{calls.push([path,opt&&opt.method]);return {}};
  for(const [button,dialog] of [["#project-cancel","#project-dialog"],["#project-action-cancel","#project-action-dialog"],["#task-cancel","#task-dialog"]]){
    const d=document.querySelector(dialog);d.open=true;
    const b=document.querySelector(button);
    out[button]={wired:typeof b.onclick==="function"};
    if(out[button].wired)b.onclick();
    out[button].open=!!d.open;
  }
  out.calls=calls.length;
  return out;
};
'''


class CancelClosesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(CANCEL_PROBE, static=STATIC)

    def test_each_cancel_closes_its_dialog_and_sends_nothing(self):
        for button in ('#project-cancel', '#project-action-cancel', '#task-cancel'):
            with self.subTest(button=button):
                self.assertEqual(self.out[button], {'wired': True, 'open': False})
        self.assertEqual(self.out['calls'], 0)


if __name__ == '__main__':
    unittest.main()
