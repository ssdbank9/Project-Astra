"""MXY7BG slice 1 in the browser code: how each attachment kind is drawn, which forms an owner
gets, and how an upload is sent. Slice 2: the upload form states the installation's limit and
the admin Attachments section loads and saves the App Owner's policy. Slice 3: the App Owner's
direct link controls, the warning before one is created, the link shown once and its revocation."""
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
    {id:'f2',kind:'file',display_name:'shared <b>.pdf',size_bytes:5,added_at:'2026-01-01T00:00:00Z',
      direct_link:{id:'L 1',created_at:'2026-01-02T00:00:00Z',created_by_name:'<i>Owner'}},
    {id:'p1',kind:'path',display_name:'old.pdf',path:'',path_hidden:true,added_at:'2026-01-01T00:00:00Z'},
    {id:'p2',kind:'path',display_name:'desk.pdf',path:'C:\\\\docs\\\\desk.pdf',added_at:'2026-01-01T00:00:00Z'}]};
  const html=buildAttachments(task);
  const desktop=buildAttachments({...task,permissions:{can_manage_files:true,can_link_paths:true}});
  const viewer=buildAttachments({...task,permissions:{can_manage_files:false,can_link_paths:false}});
  const raised=buildAttachments({...task,upload_limit_bytes:40*1048576});
  let sent=null;
  globalThis.fetch=async(url,opts)=>{sent={url,method:opts.method,headers:opts.headers,body:opts.body};
    return {ok:false,status:400,json:async()=>({error:'This file looks like a Windows program and cannot be uploaded.'})}};
  state.csrf='tok';
  let error=null;
  try{await uploadAttachment('t 1',{name:'Rapport été.pdf',type:'',size:5},'n&b')}catch(e){error=e.message}
  // Slice 2 admin section: load fills the form from the server, save sends the whole policy with
  // the textareas as raw text, and every server value reaches the page as text.
  const nodes={};
  for(const id of ['attachment-settings-error','attachment-settings-status','attachment-ceiling','attachment-builtin-summary','attachment-builtin'])nodes[id]={textContent:''};
  const form={isConnected:true,elements:{upload_limit_mb:{value:'',max:''},blocked_extensions:{value:''},blocked_mime_types:{value:''}},_submit:null,addEventListener(k,f){if(k==='submit')form._submit=f}};
  nodes['attachment-settings-form']=form;
  const qs2=document.querySelector;document.querySelector=s=>{const m=/^#([\\w-]+)$/.exec(s);return m&&nodes[m[1]]?nodes[m[1]]:qs2(s)};
  const settings={upload_limit_mb:40,saved_limit_mb:120,unusable:null,default_limit_mb:25,hard_limit_mb:250,server_ceiling_mb:40,blocked_extensions:['.abc','.xyz'],blocked_mime_types:['text/plain'],builtin_extensions:['.exe','.js'],builtin_mime_types:[],updated_at:'2026-01-01T00:00:00Z',updated_by_name:'<b>Owner'};
  let put=null;
  api=async(path,opts)=>{if(opts&&opts.method==='PUT'){put={path,body:JSON.parse(opts.body)};return {settings:{...settings,upload_limit_mb:Number(put.body.upload_limit_mb),saved_limit_mb:Number(put.body.upload_limit_mb),unusable:'<i>unreadable'}}}return {settings}};
  await loadAttachmentSettings();
  const loaded={limit:form.elements.upload_limit_mb.value,max:form.elements.upload_limit_mb.max,ext:form.elements.blocked_extensions.value,mime:form.elements.blocked_mime_types.value,
    status:nodes['attachment-settings-status'].textContent,ceiling:nodes['attachment-ceiling'].textContent,summary:nodes['attachment-builtin-summary'].textContent,builtin:nodes['attachment-builtin'].textContent};
  form.elements.upload_limit_mb.value=' 60 ';form.elements.blocked_extensions.value='.q\\n r ';form.elements.blocked_mime_types.value='';
  await form._submit({preventDefault(){},currentTarget:form});
  const admin={loaded,put,saved:nodes['attachment-settings-status'].textContent,error:nodes['attachment-settings-error'].textContent,ceilingAfter:nodes['attachment-ceiling'].textContent};
  document.querySelector=qs2;
  // Slice 3: the direct link flow, driven through the real functions against a stub panel that
  // only hands out a control the panel's markup really contains.
  const kids={},focused=[];
  const panel={hidden:true,_html:'',get innerHTML(){return this._html},set innerHTML(h){this._html=h;for(const k in kids)delete kids[k]},
    querySelector(s){if(!this._html.includes('id="'+s.slice(1)+'"'))return null;return kids[s]||(kids[s]={textContent:'',_l:{},addEventListener(k,f){this._l[k]=f},focus(){focused.push(s)}})}};
  const attErr={textContent:'',classList:{remove(){}}};
  document.querySelector=s=>s==='#direct-link-panel'?panel:s==='#attachment-error'?attErr:qs2(s);
  const calls=[];let refuse='',hold=null;
  api=async(path,opts)=>{const body=JSON.parse(opts.body);calls.push({path,method:opts.method,body});
    if(hold)await hold;
    if(refuse){const e=new Error(refuse);e.status=403;throw e}
    if(opts.method==='POST'&&!body.confirm){const e=new Error('Anyone <i>with the link');e.status=409;e.confirm='direct_link';e.impact=['one <b>','two','three'];throw e}
    if(opts.method==='POST')return {link:{id:'L new',url:'/files/TOK-1'}};
    return {ok:true}};
  location.origin='https://astra.example';
  const copied=[];let clipFails=false;
  Object.defineProperty(globalThis,'navigator',{value:{clipboard:{writeText:async t=>{if(clipFails)throw new Error('denied');copied.push(t)}}},configurable:true,writable:true});
  const reopened=[];openDetail=async id=>{reopened.push(id)};
  detailTaskId='t 1';
  const trigger={focus(){focused.push('trigger')}};
  const dtask={id:'t 1',permissions:{can_manage_files:true},attachments:[{id:'f 2',kind:'file',direct_link:{id:'L new'}}]},dname='shared <b>.pdf';
  await createDirectLink(dtask,'f 2',dname,undefined,trigger);
  const confirmHtml=panel.innerHTML,confirmHidden=panel.hidden;
  panel.querySelector('#direct-link-cancel')._l.click();
  const cancelled={html:panel.innerHTML,hidden:panel.hidden};
  await createDirectLink(dtask,'f 2',dname,undefined,trigger);
  await panel.querySelector('#direct-link-confirm')._l.click();
  const linkHtml=panel.innerHTML,linkHidden=panel.hidden,createFocus=focused.slice();
  await panel.querySelector('#direct-link-copy')._l.click();
  const copiedStatus=panel.querySelector('#direct-link-status').textContent;
  clipFails=true;await panel.querySelector('#direct-link-copy')._l.click();
  const failedStatus=panel.querySelector('#direct-link-status').textContent;
  // Until Done, a redraw of the task puts the waiting link back without moving the focus;
  // another task's redraw shows nothing of it.
  panel.innerHTML='';panel.hidden=true;
  await wireAttachments({...dtask,id:'other'});
  const otherTask=panel.innerHTML;
  await wireAttachments(dtask);
  const redrawn={same:panel.innerHTML===linkHtml,hidden:panel.hidden,focusMoved:focused.length!==createFocus.length};
  const done=panel.querySelector('#direct-link-done')._l.click;
  await done();
  const afterDone={html:panel.innerHTML,hidden:panel.hidden};
  await wireAttachments(dtask);
  afterDone.redraw=panel.innerHTML;
  // Done pressed after the user moved to another task reopens nothing.
  detailTaskId='other';await done();detailTaskId='t 1';
  askRevokeDirectLink(dtask,'L 1',dname,trigger);
  const revokeHtml=panel.innerHTML;
  panel.querySelector('#revoke-link-cancel')._l.click();
  const revokeCancelled={html:panel.innerHTML,hidden:panel.hidden};
  askRevokeDirectLink(dtask,'L 1',dname,trigger);
  const revokeFocus=focused.slice(createFocus.length);
  const submit=panel.querySelector('#revoke-link-form')._l.submit;
  const reason=value=>({preventDefault(){},target:{elements:{reason:{value}}}});
  await submit(reason('sent wrongly'));
  refuse='<b>Only the App Owner';await submit(reason('again'));
  const refused=attErr.textContent;
  refuse='';detailTaskId='other';await submit(reason('later'));
  const cleared=attErr.textContent;
  detailTaskId='t 1';refuse='Not <i>allowed';await createDirectLink(dtask,'f 2',dname);
  const createRefused=attErr.textContent,panelKept=panel.innerHTML===revokeHtml;
  const mainCalls=calls.slice(),mainReopened=reopened.slice();
  // Answers that arrive after the user moved to another task draw nothing there. A link created
  // meanwhile is shown when its task is back on screen, and is dropped for good once the viewer
  // can no longer manage files or the link is no longer on the file.
  refuse='';attErr.textContent='';panel.innerHTML='';panel.hidden=true;detailTaskId='other';
  await createDirectLink(dtask,'f 2',dname);
  const away={ask:panel.innerHTML};
  await createDirectLink(dtask,'f 2',dname,'direct_link');
  away.created=panel.innerHTML;
  refuse='late <b>';await createDirectLink(dtask,'f 2',dname);refuse='';
  away.refused=attErr.textContent;
  detailTaskId='t 1';await wireAttachments(dtask);
  away.back=panel.innerHTML===linkHtml;
  panel.innerHTML='';await wireAttachments({...dtask,permissions:{can_manage_files:false}});
  away.demoted=panel.innerHTML;
  await wireAttachments(dtask);
  away.demotedForGood=panel.innerHTML;
  await createDirectLink(dtask,'f 2',dname,'direct_link');
  away.shownAgain=panel.innerHTML===linkHtml;
  // A redraw that does not carry the link may hold data read before the link was made: Astra
  // looks once more, and drops the link only when a second look does not carry it either.
  const gone={...dtask,attachments:[{id:'f 2',kind:'file'},{id:'f 3',kind:'file',direct_link:{id:'L other'}}]};
  detailTaskId='other';let seen=reopened.length;panel.innerHTML='';await wireAttachments(gone);
  away.elsewhere={html:panel.innerHTML,lookedAgain:reopened.slice(seen)};
  detailTaskId='t 1';seen=reopened.length;await wireAttachments(gone);
  away.firstMiss={html:panel.innerHTML,lookedAgain:reopened.slice(seen)};
  await wireAttachments(dtask);
  away.staleSurvived=panel.innerHTML===linkHtml;
  panel.innerHTML='';await wireAttachments(gone);
  away.unlinked=panel.innerHTML;
  await wireAttachments(dtask);
  away.unlinkedForGood=panel.innerHTML;
  // The buttons drawn on the task reach those functions.
  refuse='';calls.length=0;detailTaskId='t 1';focused.length=0;
  document.querySelector('#detail-body').innerHTML=html;
  await wireAttachments(task);
  const createButton=document.querySelectorAll('#detail-body [data-direct-link]')[0],revokeButton=document.querySelectorAll('#detail-body [data-revoke-link]')[0];
  createButton.focus=()=>{focused.push('create button')};revokeButton.focus=()=>{focused.push('revoke button')};
  const off=()=>[createButton.disabled===true,revokeButton.disabled===true];
  await createButton._l.click[0]();
  const wired={create:calls[0],createPanel:panel.innerHTML,offWhileAsking:off()};
  panel.querySelector('#direct-link-cancel')._l.click();
  revokeButton._l.click[0]();
  wired.revokePanel=panel.innerHTML;
  panel.querySelector('#revoke-link-cancel')._l.click();
  wired.focus=focused.slice();
  revokeButton._l.click[0]();
  await panel.querySelector('#revoke-link-form')._l.submit(reason('wired'));
  wired.revoke=calls[1];
  // One request at a time: while the confirmed request is on its way the link buttons are off
  // and another click, on the task or on the warning, sends nothing.
  await createButton._l.click[0]();
  let release;hold=new Promise(r=>{release=r});
  const confirmButton=panel.querySelector('#direct-link-confirm');
  const sending=confirmButton._l.click();
  const sentSoFar=calls.length;
  await createButton._l.click[0]();await confirmButton._l.click();
  wired.inFlight={off:off(),extraCalls:calls.length-sentSoFar};
  hold=null;release();await sending;
  // While the new link waits to be copied the link buttons stay off; Done turns them on again.
  wired.shown=panel.innerHTML===linkHtml.replace('shared &lt;b&gt;.pdf','report.pdf');
  wired.offWhileShown=off();
  // A redraw draws new buttons: they are off as well while the link waits.
  const linked={...task,attachments:task.attachments.map(a=>a.id==='f1'?{...a,direct_link:{id:'L new',created_at:'2026-01-03T00:00:00Z',created_by_name:'Owner'}}:a)};
  document.querySelector('#detail-body').innerHTML=buildAttachments(linked);
  await wireAttachments(linked);
  const redrawnButtons=()=>[...document.querySelectorAll('#detail-body [data-revoke-link]')];
  wired.offAfterRedraw=redrawnButtons().map(b=>b.disabled===true);
  await panel.querySelector('#direct-link-done')._l.click();
  wired.offAfterDone=redrawnButtons().map(b=>b.disabled===false);
  document.querySelector('#detail-body').innerHTML='';
  const direct={confirmHtml,confirmHidden,cancelled,linkHtml,linkHidden,copied,copiedStatus,failedStatus,reopened:mainReopened,revokeHtml,
    refused,cleared,createRefused,panelKept,calls:mainCalls,wired,createFocus,revokeFocus,otherTask,redrawn,afterDone,revokeCancelled,away,
    labels:[EVENT_LABELS.direct_link_created,EVENT_LABELS.direct_link_revoked,EVENT_LABELS.attachment_direct_download],
    history:[
      renderEvent({event_type:'attachment_direct_download',occurred_at:'2026-01-02T00:00:00Z',actor_name:'Owner <b>',reason:'via direct link'}),
      renderEvent({event_type:'attachment_direct_download',occurred_at:'2026-01-02T00:00:00Z',actor_name:null,reason:'via direct link'}),
      renderEvent({event_type:'direct_link_created',occurred_at:'2026-01-02T00:00:00Z',actor_name:'Owner <b>'}),
      renderEvent({event_type:'attachment_downloaded',occurred_at:'2026-01-02T00:00:00Z',actor_name:null})]};
  document.querySelector=qs2;
  state.projects=[];state.entities=[];
  const qs=document.querySelector.bind(document);document.querySelector=s=>qs(s)||qs('#final-results-body');
  const stamp='2026-01-01T00:00:00Z',base={source_type:'attachment',title:'T',task_id:'t 1',task_title:'Deliver',project_name:'P',marked_at:stamp};
  renderFinalResults([
    {...base,attachment_id:'f1',attachment_kind:'file',attachment_path:'report <b>.pdf'},
    {...base,attachment_id:'l1',attachment_kind:'link',attachment_path:'https://example.org/a?b="c"'},
    {...base,attachment_id:'p1',attachment_kind:'path',attachment_path:''},
    {...base,attachment_id:'p2',attachment_kind:'path',attachment_path:'C:\\\\docs\\\\desk.pdf'}],{});
  const finals=document.querySelector("#final-results-body").innerHTML;
  const storage={labels:[OWNER_EVENT_LABELS.storage_migrated,OWNER_EVENT_LABELS.storage_pruned],server:[viaServerCommand({event_type:'storage_migrated',reason:'server command'}),viaServerCommand({event_type:'storage_pruned',reason:'server command'}),viaServerCommand({event_type:'storage_migrated',reason:null})],
    text:[storageEventText({event_type:'storage_migrated',detail_json:JSON.stringify({target:'s3',moved:2,restored:1,failed:0})}),storageEventText({event_type:'storage_migrated',detail_json:JSON.stringify({target:'folder',moved:'<b>',restored:0,failed:3})}),storageEventText({event_type:'storage_pruned',detail_json:JSON.stringify({pruned:4,failed:1})}),storageEventText({event_type:'storage_pruned',detail_json:'not json'}),storageEventText({event_type:'storage_migrated',detail_json:JSON.stringify({target:'s3',moved:1,restored:0,failed:0,interrupted:true})}),storageEventText({event_type:'storage_pruned',detail_json:JSON.stringify({pruned:1,failed:0,interrupted:true})})],
    kinds:[storageEvent({event_type:'storage_migrated'}),storageEvent({event_type:'storage_pruned'}),storageEvent({event_type:'password_reset'})]};
  return {html,desktop,viewer,raised,sent,error,finals,admin,direct,storage};
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

    def test_the_upload_form_states_the_installations_limit(self):
        self.assertIn('File (up to 25 MB)', self.out['html'])
        self.assertIn('File (up to 40 MB)', self.out['raised'])

    def test_the_admin_attachment_section_loads_and_saves_the_whole_policy(self):
        admin = self.out['admin']
        loaded = admin['loaded']
        self.assertEqual((loaded['limit'], loaded['max'], loaded['ext'], loaded['mime']),
                         (40, 40, '.abc\n.xyz', 'text/plain'))
        self.assertIn('Last saved', loaded['status'])
        self.assertIn('<b>Owner', loaded['status'])  # text, never markup
        self.assertIn('up to 40 MB', loaded['ceiling'])
        self.assertIn('250 MB', loaded['ceiling'])
        self.assertIn('saved limit of 120 MB is applied as 40 MB', loaded['ceiling'])
        self.assertEqual(loaded['summary'], 'Always blocked, whatever is entered here: 2 file types')
        self.assertEqual(loaded['builtin'], '.exe .js')
        self.assertEqual(admin['put']['path'], '/api/attachment-settings')
        self.assertEqual(admin['put']['body'], {'upload_limit_mb': '60', 'blocked_extensions': '.q\n r ',
                                                'blocked_mime_types': ''})
        self.assertIn('Saved. Uploads up to 60 MB', admin['saved'])
        self.assertNotIn('saved limit of', admin['ceilingAfter'])
        self.assertEqual(admin['error'], '<i>unreadable')  # the server's notice, as text

    def test_only_the_owner_gets_direct_link_controls_and_everyone_sees_that_one_exists(self):
        html, viewer = self.out['html'], self.out['viewer']
        # One uploaded file without a link, one with: links and local paths never get a control.
        self.assertEqual((html.count('data-direct-link='), html.count('data-revoke-link=')), (1, 1))
        self.assertIn('data-direct-link="f1" data-att-name="report.pdf">Create direct link</button>', html)
        self.assertIn('data-revoke-link="L 1" data-att-name="shared &lt;b&gt;.pdf">Revoke direct link</button>', html)
        for text in (html, viewer):
            self.assertEqual(text.count('Direct link active since'), 1)
            self.assertIn(' by &lt;i&gt;Owner</small>', text)
            self.assertNotIn('<i>Owner', text)
            self.assertIn('<div id="direct-link-panel" class="direct-link-panel" hidden></div>', text)
        self.assertNotIn('data-direct-link=', viewer)
        self.assertNotIn('data-revoke-link=', viewer)

    def test_creating_a_direct_link_warns_first_then_shows_the_link_once(self):
        direct = self.out['direct']
        self.assertFalse(direct['confirmHidden'])
        self.assertIn('<h4 id="direct-link-title" tabindex="-1">Create a direct link to shared &lt;b&gt;.pdf?</h4>',
                      direct['confirmHtml'])
        self.assertIn('<p>Anyone &lt;i&gt;with the link</p>', direct['confirmHtml'])
        self.assertIn('<li>one &lt;b&gt;</li><li>two</li><li>three</li>', direct['confirmHtml'])
        self.assertEqual(direct['cancelled'], {'html': '', 'hidden': True})
        path = '/api/tasks/t%201/attachments/f%202/direct-link'
        self.assertEqual(direct['calls'][:3], [  # asked, cancelled, asked again, then confirmed
            {'path': path, 'method': 'POST', 'body': {}},
            {'path': path, 'method': 'POST', 'body': {}},
            {'path': path, 'method': 'POST', 'body': {'confirm': 'direct_link'}}])
        self.assertFalse(direct['linkHidden'])
        self.assertIn('<h4 id="direct-link-title" tabindex="-1">Direct link to shared &lt;b&gt;.pdf</h4>',
                      direct['linkHtml'])
        self.assertIn('<code class="direct-link-url" id="direct-link-url">https://astra.example/files/TOK-1</code>',
                      direct['linkHtml'])
        self.assertIn('cannot show it again', direct['linkHtml'])
        self.assertEqual(direct['copied'], ['https://astra.example/files/TOK-1'])
        self.assertEqual((direct['copiedStatus'], direct['failedStatus']),
                         ('Copied.', 'Select the link and copy it yourself.'))
        # A refusal is shown as text and leaves the panel as it was.
        self.assertEqual(direct['calls'][6], {'path': path, 'method': 'POST', 'body': {}})
        self.assertEqual((direct['createRefused'], direct['panelKept']), ('Not <i>allowed', True))

    def test_revoking_asks_for_a_reason_and_reopens_the_task_only_when_it_worked(self):
        direct = self.out['direct']
        self.assertIn('<form id="revoke-link-form"><h4>Revoke the direct link to shared &lt;b&gt;.pdf</h4>',
                      direct['revokeHtml'])
        self.assertIn('<input name="reason" id="revoke-link-reason" maxlength="500" required>', direct['revokeHtml'])
        self.assertEqual(direct['calls'][3:6], [
            {'path': '/api/direct-links', 'method': 'DELETE',
             'body': {'task_id': 't 1', 'link_id': 'L 1', 'reason': reason}}
            for reason in ('sent wrongly', 'again', 'later')])
        self.assertEqual(len(direct['calls']), 7)
        # Done, then the revoke that worked while the task was open; not the refused one, and
        # neither a Done nor a revoke that finished after the user had moved to another task.
        self.assertEqual(direct['reopened'], ['t 1', 't 1'])
        self.assertEqual((direct['refused'], direct['cleared']), ('<b>Only the App Owner', ''))

    def test_the_buttons_on_the_task_reach_the_direct_link_flow(self):
        wired = self.out['direct']['wired']
        self.assertEqual(wired['create'], {'path': '/api/tasks/t%201/attachments/f1/direct-link', 'method': 'POST',
                                           'body': {}})
        self.assertIn('id="direct-link-confirm"', wired['createPanel'])
        self.assertIn('id="revoke-link-form"', wired['revokePanel'])
        self.assertEqual(wired['revoke'], {'path': '/api/direct-links', 'method': 'DELETE',
                                           'body': {'task_id': 't 1', 'link_id': 'L 1', 'reason': 'wired'}})

    def test_focus_moves_into_the_panel_and_back_to_the_button_that_opened_it(self):
        direct = self.out['direct']
        # The warning, cancel, the warning again, then the link itself.
        self.assertEqual(direct['createFocus'],
                         ['#direct-link-title', 'trigger', '#direct-link-title', '#direct-link-title'])
        self.assertEqual(direct['revokeFocus'], ['#revoke-link-reason', 'trigger', '#revoke-link-reason'])
        self.assertEqual(direct['revokeCancelled'], {'html': '', 'hidden': True})
        self.assertEqual(direct['wired']['focus'],
                         ['#direct-link-title', 'create button', '#revoke-link-reason', 'revoke button'])

    def test_a_link_waiting_to_be_copied_survives_a_redraw_until_done(self):
        direct, wired = self.out['direct'], self.out['direct']['wired']
        self.assertEqual(direct['otherTask'], '')  # another task's redraw shows nothing of it
        self.assertEqual(direct['redrawn'], {'same': True, 'hidden': False, 'focusMoved': False})
        self.assertEqual(direct['afterDone'], {'html': '', 'hidden': True, 'redraw': ''})
        # While it waits the other link buttons are off, so no click can replace the panel.
        self.assertTrue(wired['shown'])
        self.assertEqual((wired['offWhileAsking'], wired['offWhileShown'], wired['offAfterRedraw'],
                          wired['offAfterDone']), ([False, False], [True, True], [True, True], [True, True]))

    def test_a_link_request_on_its_way_cannot_be_overtaken(self):
        # Another file's warning arriving after the first link would replace the only panel
        # that ever shows it: until the answer is back, no other link request is sent.
        self.assertEqual(self.out['direct']['wired']['inFlight'], {'off': [True, True], 'extraCalls': 0})

    def test_an_answer_for_a_task_no_longer_on_screen_draws_nothing_there(self):
        self.assertEqual(self.out['direct']['away'], {
            'ask': '', 'created': '', 'refused': '',  # nothing drawn on the other task
            'back': True,  # the link made meanwhile is shown once its task is back
            'demoted': '', 'demotedForGood': '',  # not to someone who can no longer manage files
            'shownAgain': True,
            'elsewhere': {'html': '', 'lookedAgain': []},  # a task that is not on screen is never reopened
            # A redraw without the link may be older than the link: Astra looks once more
            'firstMiss': {'html': '', 'lookedAgain': ['t 1']}, 'staleSurvived': True,
            'unlinked': '', 'unlinkedForGood': ''})  # and drops it when the second look lacks it too

    def test_the_task_history_names_the_direct_link_events(self):
        self.assertEqual(self.out['direct']['labels'],
                         ['Direct link created', 'Direct link revoked', 'Downloaded through a direct link'])

    def test_a_download_through_a_direct_link_names_no_person(self):
        # Aly, 2026-11-17 (question 4). Even a row that still carries a name shows none, and
        # no "Unknown" stands in for it; other rows keep their name, or "Unknown" without one.
        named_old, unnamed, created, other = self.out['direct']['history']
        for row in (named_old, unnamed):
            with self.subTest(row=row):
                self.assertIn('<strong>Downloaded through a direct link</strong>', row)
                self.assertNotIn('Owner', row)
                self.assertNotIn('Unknown', row)
                self.assertEqual(row.count(' · '), 1)  # the date only
                self.assertIn('<em>Reason: via direct link</em>', row)
        self.assertIn(' · Owner &lt;b&gt;</li>', created)
        self.assertEqual(created.count(' · '), 2)
        self.assertIn(' · Unknown</li>', other)

    def test_storage_commands_are_named_in_the_owner_history_as_server_commands(self):
        # MXY7BG slice 4: astra storage-migrate and storage-prune are audited like the other
        # server commands, and the history names them instead of showing the raw event type.
        self.assertEqual(self.out['storage'], {
            'labels': ['Uploaded files moved', 'Old copies of uploaded files removed'],
            'server': [True, True, False],
            # The row says where the files went and how many; numbers only, whatever the detail holds.
            'text': ['to object storage (2 copied and verified, 1 switched back to a kept copy, 0 failed)',
                     'to the server folder (0 copied and verified, 0 switched back to a kept copy, 3 failed)',
                     '4 removed, 1 failed', '0 removed, 0 failed',
                     # A command that was cut short says so in the row, not only in the notice.
                     'to object storage (1 copied and verified, 0 switched back to a kept copy, 0 failed, '
                     'interrupted before it finished)',
                     '1 removed, 0 failed, interrupted before it finished'],
            'kinds': [True, True, False]})
        # The owner history row uses that text in place of the name of the owner the audit row sits on.
        source = (STATIC/'app.js').read_text(encoding='utf-8')
        self.assertIn('storageEvent(e)?`: ${escapeHtml(storageEventText(e))}`:`: <strong>${escapeHtml(e.target_name)}</strong>`',
                      source)

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
