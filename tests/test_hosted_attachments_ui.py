"""MXY7BG slice 1 in the browser code: how each attachment kind is drawn, which forms an owner
gets, and how an upload is sent."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_web import WIRING_DRIVER, STATIC


PROBE = r'''
const probe = `;
globalThis.runProbe=async()=>{
  const task={id:'t 1',permissions:{can_manage_files:true,can_link_paths:false},final_results:[],attachments:[
    {id:'l1',kind:'link',display_name:'Spec <b>',url:'https://example.org/a?b="c"',added_at:'2026-01-01T00:00:00Z'},
    {id:'f1',kind:'file',display_name:'report.pdf',size_bytes:2097152,added_at:'2026-01-01T00:00:00Z'},
    {id:'p1',kind:'path',display_name:'old.pdf',path:'',path_hidden:true,added_at:'2026-01-01T00:00:00Z'},
    {id:'p2',kind:'path',display_name:'desk.pdf',path:'C:\\\\docs\\\\desk.pdf',added_at:'2026-01-01T00:00:00Z'}]};
  const html=buildAttachments(task);
  const desktop=buildAttachments({...task,permissions:{can_manage_files:true,can_link_paths:true}});
  const viewer=buildAttachments({...task,permissions:{can_manage_files:false,can_link_paths:false}});
  let sent=null;
  globalThis.fetch=async(url,opts)=>{sent={url,method:opts.method,headers:opts.headers,body:opts.body};
    return {ok:false,status:400,json:async()=>({error:'This file looks like a Windows program and cannot be uploaded.'})}};
  state.csrf='tok';
  let error=null;
  try{await uploadAttachment('t 1',{name:'Rapport été.pdf',type:'',size:5},'n&b')}catch(e){error=e.message}
  state.projects=[];state.entities=[];
  const qs=document.querySelector.bind(document);document.querySelector=s=>qs(s)||qs('#final-results-body');
  const stamp='2026-01-01T00:00:00Z',base={source_type:'attachment',title:'T',task_id:'t 1',task_title:'Deliver',project_name:'P',marked_at:stamp};
  renderFinalResults([
    {...base,attachment_id:'f1',attachment_kind:'file',attachment_path:'report <b>.pdf'},
    {...base,attachment_id:'l1',attachment_kind:'link',attachment_path:'https://example.org/a?b="c"'},
    {...base,attachment_id:'p1',attachment_kind:'path',attachment_path:''},
    {...base,attachment_id:'p2',attachment_kind:'path',attachment_path:'C:\\\\docs\\\\desk.pdf'}],{});
  const finals=document.querySelector("#final-results-body").innerHTML;
  return {html,desktop,viewer,sent,error,finals};
};
`;
(0,eval)(src+probe);
runProbe().then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{console.error(e);process.exit(1)});
'''


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class HostedAttachmentUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        driver = WIRING_DRIVER.split('const harness=')[0] + PROBE
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, 'hosted_attachments.js')
            path.write_text(driver, encoding='utf-8')
            result = subprocess.run(['node', str(path), str(STATIC/'app.js'), str(STATIC/'index.html')],
                                    input='{}', capture_output=True, text=True, encoding='utf-8', timeout=15)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.out = json.loads(result.stdout)

    def test_a_link_opens_in_a_new_tab_without_referrer_or_opener(self):
        html = self.out['html']
        self.assertIn('<a href="https://example.org/a?b=&quot;c&quot;" target="_blank" rel="noopener noreferrer">', html)
        self.assertIn('Spec &lt;b&gt;', html)
        self.assertNotIn('Spec <b>', html)

    def test_final_results_draw_each_attachment_kind(self):
        finals = self.out['finals']
        self.assertIn('<a href="/api/tasks/t%201/attachments/f1/download" download>report &lt;b&gt;.pdf</a>', finals)
        self.assertIn('<a href="https://example.org/a?b=&quot;c&quot;" target="_blank" rel="noopener noreferrer">'
                      'https://example.org/a?b=&quot;c&quot;</a>', finals)
        self.assertIn('Local file link, not available on this server.', finals)
        self.assertIn('<code class="att-path">C:\\docs\\desk.pdf</code>', finals)
        self.assertNotIn('<code class="att-path"></code>', finals)

    def test_a_file_downloads_through_astra(self):
        self.assertIn('<a href="/api/tasks/t%201/attachments/f1/download" download>', self.out['html'])
        self.assertIn('2.0 MB', self.out['html'])

    def test_no_local_path_or_copy_button_where_paths_are_hidden(self):
        html = self.out['html']
        self.assertIn('Local file link, not available on this server.', html)
        self.assertEqual(html.count('data-copy-path='), 1)  # only the desktop row that has a path
        self.assertNotIn('id="attachment-form"', html)
        self.assertIn('id="attachment-form"', self.out['desktop'])

    def test_no_wording_calls_a_file_safe_or_scanned(self):
        for text in (self.out['html'], self.out['viewer']):
            for word in ('safe', 'scanned', 'virus', 'malware', 'clean'):
                self.assertNotIn(word, text.lower())

    def test_owner_gets_upload_and_link_forms_and_a_viewer_gets_neither(self):
        self.assertIn('id="upload-form"', self.out['html'])
        self.assertIn('id="link-form"', self.out['html'])
        for form in ('upload-form', 'link-form', 'attachment-form'):
            self.assertNotIn(f'id="{form}"', self.out['viewer'])

    def test_an_upload_sends_raw_bytes_with_its_name_and_token_and_shows_the_refusal(self):
        sent = self.out['sent']
        self.assertEqual((sent['url'], sent['method']), ('/api/tasks/t%201/files', 'POST'))
        self.assertEqual(sent['headers']['X-CSRF-Token'], 'tok')
        self.assertEqual(sent['headers']['X-Filename'], 'Rapport%20%C3%A9t%C3%A9.pdf')
        self.assertEqual(sent['headers']['X-Note'], 'n%26b')
        self.assertEqual(sent['headers']['Content-Type'], 'application/octet-stream')
        self.assertIn('cannot be uploaded', self.out['error'])


if __name__ == '__main__':
    unittest.main()
