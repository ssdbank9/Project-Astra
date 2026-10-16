"""Behaviour tests for the Gantt, People, reviewer, template and search frontend gaps.

Node runs the real src/astra/static/app.js against a DOM stub that lives in this file. The
stub keeps what the app writes with innerHTML and can find tags in it again (by attribute,
tag name or id), so a button the app rendered can be "clicked" through the handler the app
itself attached. Every test names the behaviour it protects and fails if that behaviour is
removed from app.js.

Covered: D73AQW (Gantt expand state, +N overflow chip, phone default to the table),
GTEYTG/KBWY86 (People badges, owner buttons, blocked lists), F3 (reviewer select names),
F4 (template form without prompt()), F8 (search hits and closing the dialog).
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from test_web import STATIC


DRIVER = r'''
const fs=require("fs");
const src=fs.readFileSync(process.argv[2],"utf8"),probe=fs.readFileSync(process.argv[4],"utf8");
const indexIds=new Set([...fs.readFileSync(process.argv[3],"utf8").matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
const input=JSON.parse(fs.readFileSync(0,"utf8")||"{}");
const unesc=s=>s.replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&amp;/g,"&");
const camel=s=>s.replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
const store={},ghost={},cache=new Map(),H={};
// localStorage backed by a map: the seed lets a second run start from what the first run saved.
const ls=new Map(Object.entries(input.storage||{}));H.lsWrites=[];
globalThis.localStorage={getItem:k=>ls.has(k)?ls.get(k):null,setItem(k,v){ls.set(k,String(v));H.lsWrites.push([k,String(v)])}};
function el(id,init){
  const cls=new Set(),listeners={},attrs={};
  const t={_id:id,_l:listeners,_attrs:attrs,_v:0,innerHTML:"",textContent:"",value:"",checked:false,hidden:false,open:false,disabled:false,
    isConnected:true,style:{},dataset:{},clientWidth:1180,...(init||{}),
    setAttribute(k,v){attrs[k]=String(v)},getAttribute(k){return k in attrs?attrs[k]:null},removeAttribute(k){delete attrs[k]},hasAttribute(k){return k in attrs},
    addEventListener(k,f){(listeners[k]=listeners[k]||[]).push(f)},
    classList:{add:(...c)=>c.forEach(x=>cls.add(x)),remove:(...c)=>c.forEach(x=>cls.delete(x)),toggle:(c,on)=>{if(on===undefined?!cls.has(c):on)cls.add(c);else cls.delete(c)},contains:c=>cls.has(c)},
    insertAdjacentHTML(pos,h){t.innerHTML=pos==="afterbegin"?h+t.innerHTML:t.innerHTML+h;t._v++},
    focus(){},blur(){},select(){},scrollIntoView(){},
    showModal(){t.open=true;t.shown=(t.shown||0)+1},close(){t.open=false},
    contains(){return false},closest(){return null},matches(){return false},
    querySelector(s){return document.querySelector(s)},querySelectorAll(s){return document.querySelectorAll(s)}};
  // "then" must read as undefined: an element returned from an async function is otherwise taken for a thenable.
  return new Proxy(t,{get(o,k){if(k===Symbol.toPrimitive)return()=>"";if(k==="then")return undefined;if(k in o)return o[k];return function(){return el()}},
    set(o,k,v){o[k]=v;if(k==="innerHTML")o._v++;return true}});
}
function attrsOf(text){const a={};for(const m of text.matchAll(/\s([\w:-]+)(?:="([^"]*)")?/g))a[m[1]]=m[2]===undefined?"":unesc(m[2]);return a}
function nodeFor(key,tag,attrs){
  if(cache.has(key))return cache.get(key);
  const dataset={};for(const k in attrs)if(k.startsWith("data-"))dataset[camel(k.slice(5))]=attrs[k];
  const n=el(attrs.id?"#"+attrs.id:tag,{dataset,hidden:"hidden" in attrs,_tag:tag});
  for(const k in attrs)n._attrs[k]=attrs[k];
  cache.set(key,n);return n;
}
function scan(container,cid,test){
  const out=[];
  for(const tm of String(container.innerHTML||"").matchAll(/<(\w+)((?:\s[^>]*)?)>/g)){
    const attrs=attrsOf(tm[2]);
    if(test(tm[1],attrs))out.push(nodeFor(`${cid}|${container._v}|${tm.index}|${tm[0]}`,tm[1],attrs));
  }
  return out;
}
function selTest(sel){
  let m=/^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(sel);
  if(m)return (tag,a)=>m[1] in a&&(m[2]===undefined||a[m[1]]===m[2]);
  if(/^[a-z][a-z0-9]*$/.test(sel))return tag=>tag===sel;
  return null;
}
globalThis.document={
  activeElement:null,
  querySelectorAll(s){
    const out=[];
    for(let part of s.split(",")){
      part=part.trim();const sm=/^#([\w-]+)\s+(.+)$/.exec(part),test=selTest(sm?sm[2]:part);
      if(!test)continue;
      if(sm){const c=store["#"+sm[1]];if(c)out.push(...scan(c,"#"+sm[1],test))}
      else for(const [k,c] of Object.entries(store))if(c.innerHTML)out.push(...scan(c,k,test));
    }
    return out;
  },
  querySelector(s){
    if(s.includes(":not([hidden])")||s.includes("[open]"))return null;
    const idm=/^#([\w-]+)$/.exec(s);
    if(idm){
      if(indexIds.has(idm[1]))return store[s]||(store[s]=el(s));
      for(const [k,c] of Object.entries(store)){if(!c.innerHTML)continue;const f=scan(c,k,(tag,a)=>a.id===idm[1])[0];if(f)return f}
      return ghost[s]||(ghost[s]=el(s));
    }
    if(/^\[[\w-]+="[^"]*"\]$/.test(s)){const f=document.querySelectorAll(s)[0];if(f)return f}
    return store[s]||(store[s]=el(s));
  },
  getElementById(s){return document.querySelector("#"+s)},createElement(){return el()},addEventListener(){},body:el("body"),documentElement:el("html")};
document.activeElement=document.body;
globalThis.window=globalThis;globalThis.addEventListener=()=>{};
globalThis.Option=function(t,v){return{text:t,value:v}};
globalThis.CSS={escape:s=>String(s)};
globalThis.FormData=function(form){return globalThis.__entries||[]};
globalThis.matchMedia=q=>({get matches(){return !!globalThis.__phone&&/760px/.test(q)},addEventListener(){}});
globalThis.fetch=()=>new Promise(()=>{});
globalThis.location={hash:"",search:"",pathname:"/",origin:"http://astra"};
globalThis.history={replaceState(){}};
document.querySelector("#more-btn").setAttribute("aria-controls","more-menu");document.querySelector("#more-menu").hidden=true;
document.querySelector("#detail-dialog").hidden=true;
H.ticks=async(n=5)=>{for(let i=0;i<n;i++)await new Promise(r=>setTimeout(r,0))};
H.store=store;
globalThis.__phone=!!input.phone;
(0,eval)(src+"\n;"+probe);
globalThis.runProbe(input,H).then(o=>{fs.writeFileSync(process.argv[5],JSON.stringify(o));process.exit(0)})
  .catch(e=>{console.error(e&&e.stack||e);process.exit(1)});
'''


GANTT_PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
  state.user={id:"u1",display_name:"Pat",global_role:"member"};
  state.projects=[{id:"proj",name:"P",status:"active",can_manage:false}];
  state.today="2026-06-01";
  const T=o=>({project_id:"proj",project_name:"P",owner_name:"Sara",status:"in_progress",due_state:"scheduled",days_to_due:5,
    criticality:"high",is_blocked:false,is_critical_path:false,...o});
  // The timeline runs Jan 1 to Dec 31 (371 days with padding) at about 710px, so one day is about 1.9px.
  const tasks=[
    T({id:"p1",title:"Parent one",start_date:"2026-01-01",due_date:"2026-12-31"}),
    T({id:"s1",parent_task_id:"p1",title:"One day step",start_date:"2026-02-01",due_date:"2026-02-01"}),
    T({id:"s2",parent_task_id:"p1",title:"Four day step",start_date:"2026-03-01",due_date:"2026-03-04"}),
    T({id:"s3",parent_task_id:"p1",title:"Five day step",start_date:"2026-04-01",due_date:"2026-04-05"}),
    T({id:"p2",title:"Parent two",start_date:"2026-01-01",due_date:"2026-12-31"}),
    T({id:"s4",parent_task_id:"p2",title:"Month step",start_date:"2026-05-01",due_date:"2026-05-30"}),
  ];
  state.tasks=tasks;
  const gantt=document.querySelector("#gantt"),table=document.querySelector("#schedule-table");
  const stepsHidden=id=>{const n=document.getElementById("steps-"+id);return n?n.hidden:null};
  const click=async id=>{
    const btn=document.querySelector(`[data-expand="${id}"]`);
    for(const f of gantt._l.click||[])await f({target:{closest:s=>s==="[data-expand]"?btn:null}});
    return btn;
  };
  renderGantt(tasks);
  out.view={ganttHidden:gantt.hidden,tableHidden:table.hidden,ganttHtml:gantt.innerHTML,tableHtml:table.innerHTML};
  out.initial={p1:stepsHidden("p1"),p2:stepsHidden("p2"),html:gantt.innerHTML};
  if(input.click){
    out.steps=[];
    for(const id of input.click){
      const btn=await click(id);
      out.steps.push({id,writes:H.lsWrites.slice(),hidden:{p1:stepsHidden("p1"),p2:stepsHidden("p2")},
        expanded:btn.getAttribute("aria-expanded"),label:btn.getAttribute("aria-label")});
    }
    renderGantt(tasks);
    out.rerender={p1:stepsHidden("p1"),p2:stepsHidden("p2"),html:gantt.innerHTML};
  }
  return out;
};
'''


PEOPLE_PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
  const U=(id,name,role,o)=>({id,display_name:name,email:id+"@example.org",global_role:role,active:1,is_primary_owner:0,...o});
  const users=[U("u-prim","Pia Primary","owner",{is_primary_owner:1}),U("u-sec","Sam <Second>","owner"),
    U("u-mem","Mia Member","member"),U("u-off","Ona Off","member",{active:0})];
  const memberships=[{project_id:"p1",project_name:"Harbour",user_id:"u-sec",user_name:"Sam <Second>",role:"manager"},
    {project_id:"p1",project_name:"Harbour",user_id:"u-mem",user_name:"Mia Member",role:"member"}];
  const events=[
    {event_type:"owner_change_blocked",occurred_at:"2026-10-01T10:00:00Z",target_name:"Sam <Second>",actor_name:"Olive Owner",
     reason:"Only the primary owner may do this",detail_json:JSON.stringify({action:"grant secondary owner"})},
    {event_type:"owner_change_blocked",occurred_at:"2026-10-02T10:00:00Z",target_name:"Pia Primary",actor_name:"Olive Owner",
     reason:"",detail_json:JSON.stringify({action:"password reset of the primary owner"})},
    {event_type:"import_blocked",occurred_at:"2026-10-03T10:00:00Z",target_name:"",actor_name:"Pat Planner",
     reason:"No project chosen for budget.xlsx",detail_json:null},
    {event_type:"secondary_owner_granted",occurred_at:"2026-10-04T10:00:00Z",target_name:"Sam <Second>",actor_name:"Pia Primary",
     reason:"Cover while away",detail_json:null},
  ];
  state.projects=[{id:"p1",name:"Harbour",status:"active"}];state.entities=[];
  api=async()=>{throw new Error("offline")};
  const view=(viewer,evs)=>{
    state.user=viewer;renderPeople(users,memberships,evs);
    return document.querySelector("#people-body").innerHTML;
  };
  out.primary=view({id:"u-prim",global_role:"owner",is_primary_owner:1},events);
  out.secondary=view({id:"u-sec",global_role:"owner",is_primary_owner:0},events);
  out.noEvents=view({id:"u-prim",global_role:"owner",is_primary_owner:1},[]);
  // Click wiring for the primary owner: grant and revoke call the secondary-owner endpoint.
  view({id:"u-prim",global_role:"owner",is_primary_owner:1},events);
  const calls=[];
  api=async(path,o)=>{calls.push([o&&o.method||"GET",path,o&&o.body?JSON.parse(o.body):null]);
    return path==="/api/users"?{users}:path==="/api/memberships"?{memberships}:{events:[]}};
  globalThis.prompt=()=>"Cover while away";
  const grant=document.querySelectorAll("#people-body [data-owner-grant]");
  const revoke=document.querySelectorAll("#people-body [data-owner-revoke]");
  out.buttonCount={grant:grant.length,revoke:revoke.length};
  for(const b of [...grant,...revoke])for(const f of b._l.click||[])await f({target:b});
  await H.ticks();
  out.calls=calls.filter(c=>c[1].includes("secondary-owner"));
  return out;
};
'''


REVIEWER_PROBE = r'''
globalThis.runProbe=async function(input,H){
  state.user={id:"u1",display_name:"Owner",global_role:"owner"};
  state.tasks=[];state.projects=[{id:"p1",name:"P",status:"active"}];
  api=()=>new Promise(()=>{});
  const perms={can_edit_ordinary:true,can_request_protected:false,can_decide_protected:true,can_manage_files:true,can_read_files:true};
  const task=s=>({id:"t1",title:"Synthetic task",project_id:"p1",project_name:"P",status:s,revision:3,criticality:"high",
    due_state:"scheduled",start_date:"2026-09-01",due_date:"2026-10-10",progress:null,description:"",owner_user_id:null,
    permissions:perms,baseline:{},subtasks:[],final_results:[],dependencies:[],reviewers:[{display_name:"Rae Reviewer",role:"approver",user_id:"u2"}],
    attachments:[],submissions:[],schedule_proposals:[]});
  detailTaskId="t1";
  renderDetail(task("in_progress"),[]);
  const open=document.querySelector("#detail-body").innerHTML;
  renderDetail(task("completed"),[]);
  return {open,closed:document.querySelector("#detail-body").innerHTML};
};
'''


TEMPLATE_PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
  state.user={id:"u1",display_name:"Olive Owner",global_role:"owner"};
  state.projects=[{id:"p1",name:"Open <P>",status:"active"},{id:"p2",name:"Closed P",status:"closed"}];
  state.tasks=[{id:"t1",project_id:"p1",title:"Task A"},{id:"t2",project_id:"p2",title:"Other project task"},{id:"t3",project_id:"p1",title:"Task <B>"}];
  templatePicker.templates=[{id:"tpl1",name:"Launch <kit>",kind:"task"},{id:"tpl2",name:"Project kit",kind:"project"}];
  const calls=[],toasts=[];out.dialogsUsed=[];
  globalThis.prompt=()=>{out.dialogsUsed.push("prompt");return ""};
  globalThis.alert=m=>{out.dialogsUsed.push("alert")};
  globalThis.confirm=()=>{out.dialogsUsed.push("confirm");return false};
  showToast=m=>toasts.push(m);
  load=async()=>{calls.push(["load"])};
  const people=[{id:"u-mia",display_name:"Mia Manager",project_role:"manager",global_role:"member",active:1},
    {id:"u-bob",display_name:"Bob Member",project_role:"member",global_role:"member",active:1}];
  api=async(path,o)=>{
    if(!o||!o.method||o.method==="GET"){calls.push(["GET",path]);return {users:people}}
    calls.push([o.method,path,JSON.parse(o.body)]);return {};
  };
  const body=document.querySelector("#templates-body"),dialog=document.querySelector("#templates-dialog");
  const submit=async entries=>{
    globalThis.__entries=entries;
    for(const f of document.querySelector("#template-role-form")._l.submit||[])await f({preventDefault(){}});
    await H.ticks();
  };
  // Task template: the form, choosing a project, the parent list, an early submit and the real one.
  dialog.open=true;
  await useTemplate("tpl1","task",["owner","manager"]);
  out.taskForm=body.innerHTML;
  out.createDisabledBefore=document.querySelector("#template-create").disabled;
  await submit([["project_id",""],["parent_task_id",""],["anchor_date",""]]);
  out.earlyCalls=calls.splice(0);
  document.querySelector('[name="project_id"]').value="p1";
  for(const f of document.querySelector("#template-project")._l.change||[])await f();
  await H.ticks();
  out.parentOptions=document.querySelector("#template-parent").innerHTML;
  out.roleFields=document.querySelector("#template-role-fields").innerHTML;
  out.createDisabledAfter=document.querySelector("#template-create").disabled;
  out.pickCalls=calls.splice(0);
  await submit([["project_id","p1"],["parent_task_id","t3"],["anchor_date","2026-11-02"],["role_manager","u-mia"],["role_owner","ignored"]]);
  out.taskSubmit={calls:calls.splice(0),dialogOpen:dialog.open,toasts:toasts.splice(0)};
  // Project template: a name instead of a project, and the same role handling.
  dialog.open=true;
  await useTemplate("tpl2","project",["manager"]);
  out.projectForm=body.innerHTML;
  calls.length=0;
  await submit([["name","New P"],["anchor_date",""],["role_manager","u-bob"]]);
  out.projectSubmit={calls:calls.splice(0),dialogOpen:dialog.open};
  return out;
};
'''


SEARCH_PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
  const P1="11111111-1111-4111-8111-111111111111",T1="22222222-2222-4222-8222-222222222222";
  api=async path=>{out.requested=path;return {results:{
    tasks:[{id:T1,title:"Pour <b>concrete</b>",status:"in_progress",project_name:"Harbour & Co"}],
    projects:[{id:P1,name:"Harbour & Co"},{id:"a/b c",name:"Odd id"}]}}};
  const opened=[];openDetail=async id=>{opened.push(id)};
  const dialog=document.querySelector("#search-dialog");
  await openSearch("harbour");
  out.html=document.querySelector("#search-body").innerHTML;
  out.openedAfterSearch=dialog.open;
  const anchors=document.querySelectorAll("#search-body a");
  out.anchorCount=anchors.length;
  for(const f of (anchors[0]&&anchors[0]._l.click)||[])f({target:anchors[0]});
  out.openedAfterAnchor=dialog.open;
  dialog.open=true;
  const links=document.querySelectorAll("#search-body [data-detail]");
  out.linkCount=links.length;
  for(const f of (links[0]&&links[0]._l.click)||[])f({target:links[0]});
  out.afterTaskClick={open:dialog.open,opened};
  // No hits at all: the dialog says so for both lists.
  api=async()=>({results:{tasks:[],projects:[]}});
  await openSearch("nothing");
  out.empty=document.querySelector("#search-body").innerHTML;
  return out;
};
'''


def run_probe(probe, payload=None, static=None):
    """Run app.js (the module's STATIC, read at call time) through DRIVER with one probe; returns its JSON."""
    static = Path(static if static is not None else STATIC)
    with tempfile.TemporaryDirectory() as temp:
        driver, probe_file, result_file = Path(temp, 'driver.js'), Path(temp, 'probe.js'), Path(temp, 'result.json')
        driver.write_text(DRIVER, encoding='utf-8')
        probe_file.write_text(probe, encoding='utf-8')
        result = subprocess.run(
            ['node', str(driver), str(static / 'app.js'), str(static / 'index.html'), str(probe_file),
             str(result_file)],
            input=json.dumps(payload or {}), capture_output=True, text=True, encoding='utf-8', timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result_file.read_text(encoding='utf-8'))


class _Tags(HTMLParser):
    """Collects the tags of a fragment and, for each select, the text of the label that wraps it."""

    def __init__(self, html):
        super().__init__()
        self.tags, self.select_labels = [], {}
        self._labels, self._select_depth = [], 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == 'label':
            self._labels.append({'text': [], 'selects': []})
        elif tag == 'select':
            self._select_depth += 1
            if self._labels:
                self._labels[-1]['selects'].append(attrs.get('name') or attrs.get('id'))

    def handle_endtag(self, tag):
        if tag == 'select':
            self._select_depth -= 1
        elif tag == 'label' and self._labels:
            label = self._labels.pop()
            for name in label['selects']:
                self.select_labels[name] = ''.join(label['text']).strip()

    def handle_data(self, data):
        if self._labels and not self._select_depth:
            self._labels[-1]['text'].append(data)

    def find(self, tag, **match):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in match.items())]


def section(html, heading):
    """The list that follows a heading, as written by the app."""
    tail = re.split(r'<h3[^>]*>' + re.escape(heading) + '</h3>', html, maxsplit=1)[1]
    return tail.split('<ul class="people-list">', 1)[1].split('</ul>', 1)[0]


def rows(fragment):
    return [r for r in fragment.split('<li>')[1:]]


def parent_row(html, task_id):
    """The Gantt row of one parent task: its name, meta and timeline columns, without its step rows."""
    timeline = html.index('data-timeline-task="' + task_id + '"')
    head = html.rfind('<div class="gantt-row', 0, timeline)   # the name and meta columns come first
    end = html.index('<div class="step-rows" id="steps-' + task_id + '"', timeline)
    return html[head:end]


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class GanttExpandAndOverflowTests(unittest.TestCase):
    """D73AQW: remembered expand state, the +N overflow chip and the phone default."""

    @classmethod
    def setUpClass(cls):
        cls.first = run_probe(GANTT_PROBE, {'click': ['p1', 'p2', 'p1']})
        writes = cls.first['steps'][-1]['writes']
        # A reload: a new page load that starts from what the first run saved.
        cls.reload = run_probe(GANTT_PROBE, {'storage': dict(writes[-1:])})
        cls.phone = run_probe(GANTT_PROBE, {'phone': True})
        cls.phone_chart = run_probe(GANTT_PROBE, {'phone': True, 'storage': {'astra.gantt.view': '"chart"'}})

    def test_steps_start_collapsed_when_nothing_was_remembered(self):
        self.assertEqual((self.first['initial']['p1'], self.first['initial']['p2']), (True, True))

    def test_toggling_a_parent_saves_the_set_of_open_parents_under_the_gantt_key(self):
        writes = [[json.loads(v) for k, v in s['writes'] if k == 'astra.gantt.expanded'] for s in self.first['steps']]
        self.assertEqual([w[-1] for w in writes], [['p1'], ['p1', 'p2'], ['p2']])

    def test_each_parent_opens_and_closes_on_its_own(self):
        hidden = [(s['hidden']['p1'], s['hidden']['p2']) for s in self.first['steps']]
        self.assertEqual(hidden, [(False, True), (False, False), (True, False)])
        self.assertEqual([s['expanded'] for s in self.first['steps']], ['true', 'true', 'false'])
        self.assertIn('Hide', self.first['steps'][0]['label'])
        self.assertIn('Show', self.first['steps'][2]['label'])

    def test_a_redraw_keeps_each_parent_as_the_user_left_it(self):
        redraw = self.first['rerender']
        self.assertEqual((redraw['p1'], redraw['p2']), (True, False))
        self.assertIn('data-expand="p2" aria-expanded="true"', redraw['html'])
        self.assertIn('data-expand="p1" aria-expanded="false"', redraw['html'])

    def test_a_reload_restores_the_saved_parents_from_local_storage(self):
        initial = self.reload['initial']
        self.assertEqual((initial['p1'], initial['p2']), (True, False))
        self.assertIn('data-expand="p2" aria-expanded="true"', initial['html'])

    def test_a_step_narrower_than_8px_folds_into_the_plus_n_chip(self):
        html = self.first['initial']['html']
        row = parent_row(html, 'p1')
        self.assertIn('data-more="p1"', row)
        self.assertRegex(row, r'data-more="p1"[^>]*>\+2</button>')  # the 1 day (1.9px) and 4 day (7.6px) steps
        drawn = {a['data-detail'] for a in _Tags(row).find('button') if 'step' in (a.get('class') or '').split()}
        self.assertEqual(drawn, {'s3'})  # the 5 day step (9.6px) is still drawn
        more_list = html.split('id="more-p1"', 1)[1].split('</ul>', 1)[0]
        self.assertIn('One day step', more_list)
        self.assertIn('Four day step', more_list)
        self.assertNotIn('Five day step', more_list)

    def test_a_parent_whose_steps_are_all_wide_enough_has_no_chip(self):
        row = parent_row(self.first['initial']['html'], 'p2')
        self.assertNotIn('data-more=', row)
        drawn = {a['data-detail'] for a in _Tags(row).find('button') if 'step' in (a.get('class') or '').split()}
        self.assertEqual(drawn, {'s4'})

    def test_phone_width_opens_on_the_schedule_table_instead_of_the_chart(self):
        view = self.phone['view']
        self.assertTrue(view['ganttHidden'])
        self.assertFalse(view['tableHidden'])
        self.assertIn('class="sched-table"', view['tableHtml'])
        self.assertNotIn('gantt-row', view['ganttHtml'])
        desk = self.first['view']
        self.assertFalse(desk['ganttHidden'])
        self.assertTrue(desk['tableHidden'])
        self.assertIn('gantt-row', desk['ganttHtml'])

    def test_a_saved_chart_choice_beats_the_phone_default(self):
        view = self.phone_chart['view']
        self.assertFalse(view['ganttHidden'])
        self.assertTrue(view['tableHidden'])


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class PeopleScreenTests(unittest.TestCase):
    """GTEYTG/KBWY86: owner badges, owner buttons for the primary owner only, blocked lists."""

    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(PEOPLE_PROBE)

    @staticmethod
    def user_row(html, name):
        return [r for r in html.split('<li class="user-row">')[1:] if name in r][0].split('</li>')[0]

    def test_owners_carry_a_primary_or_secondary_badge_and_members_do_not(self):
        for viewer in ('primary', 'secondary'):
            html = self.out[viewer]
            self.assertIn('data-level="ok">Primary owner</span>', self.user_row(html, 'Pia Primary'))
            self.assertIn('data-level="info">Secondary owner</span>', self.user_row(html, 'Sam &lt;Second&gt;'))
            self.assertNotIn('class="badge"', self.user_row(html, 'Mia Member'))
            self.assertIn('Mia Member</strong> · u-mem@example.org · member', self.user_row(html, 'Mia Member'))

    def test_the_primary_owner_can_remove_a_secondary_owner_or_promote_an_active_member(self):
        html = self.out['primary']
        self.assertIn('data-owner-revoke="u-sec"', self.user_row(html, 'Sam &lt;Second&gt;'))
        self.assertIn('data-owner-grant="u-mem"', self.user_row(html, 'Mia Member'))
        self.assertNotIn('data-owner-grant', self.user_row(html, 'Ona Off'))   # inactive: no promotion
        primary_row = self.user_row(html, 'Pia Primary')
        self.assertNotIn('data-owner-grant', primary_row)
        self.assertNotIn('data-owner-revoke', primary_row)                     # the primary owner cannot be removed

    def test_a_secondary_owner_sees_no_grant_or_revoke_buttons_at_all(self):
        html = self.out['secondary']
        self.assertNotIn('data-owner-grant', html)
        self.assertNotIn('data-owner-revoke', html)
        self.assertIn('data-reset-password="u-mem"', html)                      # the rest of the screen still works
        self.assertNotIn('Daily summary', html)                                 # primary-only section

    def test_only_the_primary_owner_may_revoke_an_owners_project_access(self):
        revokes = lambda html: _Tags(html).find('button', **{'data-revoke-user': 'u-sec'})
        self.assertEqual(len(revokes(self.out['primary'])), 1)
        self.assertEqual(len(revokes(self.out['secondary'])), 0)
        self.assertEqual(len(_Tags(self.out['secondary']).find('button', **{'data-revoke-user': 'u-mem'})), 1)

    def test_blocked_owner_attempts_are_listed_with_who_what_and_why(self):
        items = rows(section(self.out['primary'], 'Blocked owner-access attempts'))
        self.assertEqual(len(items), 2)
        self.assertIn('Blocked owner change: <strong>Sam &lt;Second&gt;</strong> by Olive Owner', items[0])
        self.assertIn('Only the primary owner may do this', items[0])
        self.assertIn('Blocked password reset of the primary owner: <strong>Pia Primary</strong> by Olive Owner', items[1])

    def test_blocked_imports_are_listed_with_their_reason_and_no_target(self):
        items = rows(section(self.out['primary'], 'Blocked imports without a project'))
        self.assertEqual(len(items), 1)
        self.assertIn('Blocked import without a project by Pat Planner', items[0])
        self.assertIn('No project chosen for budget.xlsx', items[0])
        self.assertNotIn('<strong>', items[0])

    def test_blocked_events_stay_out_of_the_ordinary_access_history(self):
        history = section(self.out['primary'], 'Owner access history')
        self.assertIn('Made secondary owner: <strong>Sam &lt;Second&gt;</strong> by Pia Primary', history)
        self.assertNotIn('Blocked', history)

    def test_both_blocked_lists_say_none_when_nothing_was_blocked(self):
        for heading in ('Blocked owner-access attempts', 'Blocked imports without a project'):
            self.assertEqual(section(self.out['noEvents'], heading), '<li>None.</li>')

    def test_the_primary_owners_grant_and_remove_buttons_call_the_secondary_owner_endpoint(self):
        self.assertEqual(self.out['buttonCount'], {'grant': 1, 'revoke': 1})
        self.assertEqual(sorted(self.out['calls']), sorted([
            ['POST', '/api/users/u-mem/secondary-owner', {'reason': 'Cover while away'}],
            ['DELETE', '/api/users/u-sec/secondary-owner', {'reason': 'Cover while away'}]]))


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class ReviewerSelectNameTests(unittest.TestCase):
    """F3: the reviewer selects in the task detail have accessible names."""

    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(REVIEWER_PROBE)

    def test_the_person_and_role_selects_are_named_for_screen_readers(self):
        tags = _Tags(self.out['open'])
        person, role = tags.find('select', id='reviewer-user'), tags.find('select', id='reviewer-role')
        self.assertEqual(len(person), 1)
        self.assertEqual(len(role), 1)
        self.assertEqual(person[0].get('aria-label'), 'Reviewer person')
        self.assertEqual(role[0].get('aria-label'), 'Reviewer role')

    def test_the_add_reviewer_controls_are_offered_only_while_the_task_is_open(self):
        self.assertIn('Rae Reviewer', self.out['open'])
        self.assertNotIn('id="reviewer-user"', self.out['closed'])
        self.assertIn('Rae Reviewer', self.out['closed'])


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class TemplateFormTests(unittest.TestCase):
    """F4: using a template opens a real form (no prompt()) and submits the chosen ids."""

    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(TEMPLATE_PROBE)

    def test_a_task_template_opens_a_form_with_named_project_and_parent_selects(self):
        tags = _Tags(self.out['taskForm'])
        self.assertEqual(tags.select_labels['project_id'], 'Target project')
        self.assertEqual(tags.select_labels['parent_task_id'], 'Part of task (optional)')
        project = tags.find('select', id='template-project')[0]
        self.assertIn('required', project)
        self.assertIn('Use Launch &lt;kit&gt;', self.out['taskForm'])
        # Only open projects are offered, escaped.
        self.assertIn('<option value="p1">Open &lt;P&gt;</option>', self.out['taskForm'])
        self.assertNotIn('Closed P', self.out['taskForm'])

    def test_choosing_a_project_lists_only_its_tasks_as_parents_and_its_people_per_role(self):
        parents = self.out['parentOptions']
        self.assertIn('<option value="t1">Task A</option>', parents)
        self.assertIn('<option value="t3">Task &lt;B&gt;</option>', parents)
        self.assertNotIn('Other project task', parents)
        self.assertIn('/api/assignable-users?project_id=p1&for=reviewer', [c[1] for c in self.out['pickCalls']])
        fields = _Tags(self.out['roleFields'])
        self.assertEqual(fields.select_labels, {'role_manager': 'Project manager'})
        self.assertIn('<option value="u-mia">Mia Manager</option>', self.out['roleFields'])
        self.assertNotIn('Bob Member', self.out['roleFields'])        # wrong project role for the manager slot
        self.assertIn('App Owner: Olive Owner', self.out['roleFields'])

    def test_opening_and_submitting_a_template_never_uses_prompt_alert_or_confirm(self):
        self.assertEqual(self.out['dialogsUsed'], [])
        self.assertTrue(self.out['taskSubmit']['calls'])   # the flow ran to the end, so the empty list means something

    def test_create_stays_disabled_and_submit_does_nothing_until_a_project_is_chosen(self):
        self.assertTrue(self.out['createDisabledBefore'])
        self.assertEqual(self.out['earlyCalls'], [])
        self.assertFalse(self.out['createDisabledAfter'])

    def test_submitting_a_task_template_sends_the_chosen_project_parent_date_and_people(self):
        sent = self.out['taskSubmit']
        self.assertEqual(sent['calls'][0], ['POST', '/api/templates/tpl1/create-task', {
            'project_id': 'p1', 'parent_task_id': 't3', 'anchor_date': '2026-11-02',
            'role_assignments': {'manager': 'u-mia'}}])   # the owner role is never assigned from the form
        self.assertIn(['load'], sent['calls'])
        self.assertFalse(sent['dialogOpen'])
        self.assertEqual(sent['toasts'], ['Tasks created from template.'])

    def test_a_project_template_asks_for_a_name_and_submits_it_with_the_chosen_person(self):
        tags = _Tags(self.out['projectForm'])
        self.assertTrue(tags.find('input', name='name'))
        self.assertFalse(tags.find('select', name='project_id'))
        sent = self.out['projectSubmit']
        self.assertEqual(sent['calls'][0], ['POST', '/api/templates/tpl2/create-project', {
            'name': 'New P', 'anchor_date': None, 'role_assignments': {'manager': 'u-bob'}}])
        self.assertFalse(sent['dialogOpen'])


@unittest.skipUnless(shutil.which('node'), 'Node required for actual frontend driver')
class SearchDialogTests(unittest.TestCase):
    """F8: search hits are real links and choosing one closes the dialog."""

    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(SEARCH_PROBE)
        cls.tags = _Tags(cls.out['html'])

    def test_search_asks_the_server_and_opens_the_dialog(self):
        self.assertEqual(self.out['requested'], '/api/search?q=harbour')
        self.assertTrue(self.out['openedAfterSearch'])

    def test_a_project_hit_is_an_anchor_to_its_overview(self):
        anchors = self.tags.find('a')
        self.assertEqual([a.get('href') for a in anchors], [
            '#/project/11111111-1111-4111-8111-111111111111/overview', '#/project/a%2Fb%20c/overview'])
        self.assertIn('>Harbour &amp; Co</a>', self.out['html'])

    def test_a_task_hit_is_a_task_link_that_shows_its_status_and_project(self):
        links = self.tags.find('button', **{'data-detail': '22222222-2222-4222-8222-222222222222'})
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].get('class'), 'link')
        self.assertIn('Pour &lt;b&gt;concrete&lt;/b&gt;</button> · in_progress', self.out['html'])
        self.assertNotIn('<b>', self.out['html'])

    def test_choosing_a_project_closes_the_dialog(self):
        self.assertEqual(self.out['anchorCount'], 2)
        self.assertFalse(self.out['openedAfterAnchor'])

    def test_choosing_a_task_closes_the_dialog_and_opens_that_task(self):
        self.assertEqual(self.out['linkCount'], 1)
        self.assertEqual(self.out['afterTaskClick'], {'open': False, 'opened': ['22222222-2222-4222-8222-222222222222']})

    def test_a_search_with_no_hits_says_so_for_tasks_and_projects(self):
        self.assertIn('<li>No matching tasks.</li>', self.out['empty'])
        self.assertIn('<li>No matching projects.</li>', self.out['empty'])


if __name__ == '__main__':
    unittest.main()
