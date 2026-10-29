"""0RHNMG review: an owner who resets their own password from People goes straight to the
forced change screen instead of a People dialog whose data calls the server now refuses."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_web import WIRING_DRIVER, STATIC


PROBE = r'''
const probe = `;
globalThis.runProbe=async(own)=>{
  const me={id:'owner',global_role:'owner',display_name:'Owner',must_change_password:0};
  state.user={...me};
  document.querySelector('#detail-body').innerHTML='<form id="reset-password-form"></form><div id="reset-password-error"></div>';
  document.querySelector('#password-required').hidden=true;document.querySelector('#app').hidden=false;
  const realClasses=node=>{const c=new Set();node.classList={add:k=>c.add(k),remove:(...k)=>k.forEach(x=>c.delete(x)),toggle(){},contains:k=>c.has(k)};return node};
  const note=realClasses(document.querySelector('#forced-password-error'));note.textContent='';
  const dialog=document.querySelector('#people-dialog');dialog.open=true;dialog.close=()=>{dialog.open=false};
  const target=own?'owner':'member',calls=[];
  api=async(path,opts)=>{
    calls.push(((opts&&opts.method)||'GET')+' '+path);
    if(path==='/api/users/'+target+'/password')return {user:own?{...me,must_change_password:1}:{id:'member',must_change_password:1}};
    if(own){const e=new Error('Change your temporary password before using Astra.');e.status=403;throw e}
    return {users:[],memberships:[],events:[]};
  };
  const form={__entries:[['user_id',target],['password','fresh pass 8'],['confirm','fresh pass 8']],cleared:false,
    reset(){this.cleared=true},querySelector:()=>({selectedOptions:[{dataset:{name:'Member'}}]})};
  await submitResetPassword({preventDefault(){},target:form});
  const result={calls,
    forcedShown:!document.querySelector('#password-required').hidden,
    appHidden:document.querySelector('#app').hidden,
    mustChange:!!state.user.must_change_password,
    forcedNote:note.textContent,noteIsInfo:note.classList.contains('is-info'),
    peopleOpen:dialog.open,formCleared:form.cleared,
    peopleNote:document.querySelector('#reset-password-error')?.textContent||''};
  // A later failure on the forced form must read as an error, not keep the info styling.
  api=async()=>{throw new Error('Current password is incorrect.')};
  await changePasswordFromForm({__entries:[['current_password','x'],['new_password','fresh pass 9'],['confirm_password','fresh pass 9']],reset(){}},note,true);
  result.afterFailure={text:note.textContent,isInfo:note.classList.contains('is-info')};
  return result;
};
`;
(0,eval)(src+probe);
(async()=>({own:await runProbe(true),other:await runProbe(false)}))()
  .then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{console.error(e);process.exit(1)});
'''


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class OwnPasswordResetUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        driver = WIRING_DRIVER.split('const harness=')[0] + PROBE
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, 'own_reset.js')
            path.write_text(driver, encoding='utf-8')
            result = subprocess.run(['node', str(path), str(STATIC/'app.js'), str(STATIC/'index.html')],
                                    input='{}', capture_output=True, text=True, encoding='utf-8', timeout=15)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.out = json.loads(result.stdout)

    def test_own_reset_goes_to_the_forced_change_screen(self):
        own = self.out['own']
        self.assertTrue(own['mustChange'])
        self.assertTrue(own['forcedShown'])
        self.assertTrue(own['appHidden'])
        self.assertIn('other sessions were signed out', own['forcedNote'])
        self.assertNotIn('temporary password before using Astra', own['forcedNote'])
        self.assertTrue(own['noteIsInfo'])
        self.assertFalse(own['peopleOpen'])
        self.assertTrue(own['formCleared'])  # the typed password does not linger in the closed dialog

    def test_a_later_error_on_the_forced_form_is_not_styled_as_info(self):
        self.assertEqual(self.out['own']['afterFailure'], {'text': 'Current password is incorrect.', 'isInfo': False})

    def test_own_reset_makes_no_call_the_server_would_refuse(self):
        self.assertEqual(self.out['own']['calls'], ['POST /api/users/owner/password'])

    def test_resetting_someone_else_still_refreshes_people(self):
        other = self.out['other']
        self.assertFalse(other['mustChange'])
        self.assertFalse(other['forcedShown'])
        self.assertIn('GET /api/users', other['calls'])
        self.assertIn('Password reset for Member', other['peopleNote'])


if __name__ == '__main__':
    unittest.main()
