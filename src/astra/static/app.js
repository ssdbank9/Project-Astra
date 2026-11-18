const state={user:null,csrf:null,projects:[],tasks:[],entities:[],unread:0,sort:"criticality",dailyDigest:null,dailyDigestError:""};
async function api(path,options={}){options.headers={"Content-Type":"application/json",...(state.csrf?{"X-CSRF-Token":state.csrf}:{}),...(options.headers||{})};const response=await fetch(path,options);const data=await response.json();if(!response.ok){const err=new Error(data.lock&&data.error?data.error.replace(/at \d{2}:\d{2}:\d{2} UTC/,`at ${lockTime(data.lock)}`):data.error||"Request failed");err.status=response.status;err.confirm=data.confirm;err.impact=data.impact;err.lock=data.lock;throw err}return data}
function clearFeedback(element){if(!element)return;element.classList.remove("message-info","message-success");element.textContent=""}
function showLogin(){document.querySelector("#login").hidden=false;document.querySelector("#password-required").hidden=true;document.querySelector("#app").hidden=true}
function showForcedPasswordChange(){document.querySelector("#login").hidden=true;document.querySelector("#app").hidden=true;document.querySelector("#password-required").hidden=false;document.querySelector('#forced-password-form [name="current_password"]').focus()}
function showApp(){document.querySelector("#login").hidden=true;document.querySelector("#password-required").hidden=true;document.querySelector("#app").hidden=false;document.querySelector("#user-name").textContent=state.user.display_name;document.querySelector("#user-role").textContent=roleLabel(state.user);document.querySelector("#user-initials").textContent=initials(state.user.display_name);document.querySelector("#new-project").hidden=document.querySelector("#people").hidden=!isOwner();projectActions();refreshImportAccess()}
function showSignedInState(){if(state.user.must_change_password)showForcedPasswordChange();else showApp()}
async function load(){if(!state.loads){const s=currentRoute().params.get("sort");if(s==="due_date")state.sort=s}const [p,t,e,n]=await Promise.all([api("/api/projects"),api(`/api/tasks?sort=${encodeURIComponent(state.sort)}`),api("/api/entities").catch(()=>({entities:[]})),api("/api/notifications").catch(()=>null)]);state.projects=p.projects;state.tasks=t.tasks;state.today=t.today||null;state.timezone=t.timezone||null;state.entities=e.entities;if(n){state.notifications=n.notifications;state.unread=n.unread;state.notificationsKnown=true}state.notificationsStale=!n;state.loads=(state.loads||0)+1;updateBell();fillFilters();applyRoute(false,true)}
function updateBell(){const n=state.unread||0,stale=state.notificationsStale,badge=document.querySelector("#unread-count"),inbox=document.querySelector("#inbox");badge.textContent=stale&&!state.notificationsKnown?"!":n;badge.hidden=!n&&!stale;inbox.classList.toggle("has-unread",n>0);inbox.setAttribute("aria-label",stale?(state.notificationsKnown?`Inbox, ${n} unread (may be outdated)`:"Inbox, notifications unavailable"):n?`Inbox, ${n} unread`:"Inbox");inbox.title=stale?"Cannot refresh notifications. Open Inbox to retry.":""}
function fillFilters(){const pf=document.querySelector("#project-filter"),tp=document.querySelector('#task-form select[name="project_id"]');const selected=pf.value;pf.innerHTML='<option value="">All projects</option>';tp.innerHTML="";for(const p of state.projects){pf.add(new Option(p.status==="closed"?`${p.name} (closed)`:p.name,p.id));if(canCaptureProject(p))tp.add(new Option(p.name,p.id))}document.querySelector("#new-task").hidden=!state.projects.some(canCaptureProject);pf.value=selected;const statuses=[...new Set(state.tasks.map(t=>t.status))].sort();document.querySelector("#status-filter").innerHTML='<option value="">All statuses</option>'+statuses.map(s=>`<option>${escapeHtml(s)}</option>`).join("");const ef=document.querySelector("#entity-filter"),efSel=ef.value;ef.innerHTML='<option value="">All entities</option>'+(state.entities||[]).map(e=>`<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)}</option>`).join("");ef.value=efSel;fillPredecessors()}
function canCaptureProject(project){return project.status!=="closed"&&(isOwner()||project.can_manage===true)}
function projectEntityIds(projectId){const p=state.projects.find(p=>p.id===projectId);return new Set((p&&p.entities?p.entities:[]).map(e=>e.id))}
function fillPredecessors(){const project=document.querySelector('#task-form select[name="project_id"]').value,select=document.querySelector('#task-form select[name="predecessor_task_id"]'),parent=document.querySelector('#task-form select[name="parent_task_id"]');select.innerHTML='<option value="">No predecessor</option>';parent.innerHTML='<option value="">No parent</option>';for(const task of state.tasks.filter(t=>t.project_id===project)){select.add(new Option(task.title,task.id));parent.add(new Option(task.title,task.id))}}
function render(){
  // The Gantt nodes may be on a project page; the portfolio takes them back.
  mountGantt(document.querySelector("#gantt-panel"),null);state.ganttDay=null;
  projectActions();
  const tasks=visibleTasks();
  document.querySelector("#project-count").textContent=state.projects.length;
  document.querySelector("#task-count").textContent=tasks.length;
  document.querySelector("#overdue-count").textContent=tasks.filter(t=>t.due_state==="overdue").length;
  document.querySelector("#attention-count").textContent=tasks.filter(t=>t.due_state==="undated").length;
  document.querySelector("#as-of").textContent=asOfText();
  renderBands(tasks);
  renderGantt(tasks);
  noteFilters(tasks.length);
}
function projectActions(){
  // 5WZ4A8: project history is per project, so the button shows only when one project is selected.
  document.querySelector("#project-history-btn").hidden=!document.querySelector("#project-filter").value;
  // PZTYC9: the More menu offers the owner's project actions only while one project is selected.
  const oneProject=!!document.querySelector("#project-filter").value,owner=!!state.user&&state.user.global_role==="owner";
  document.querySelector("#close-project").hidden=document.querySelector("#save-template-btn").hidden=!(oneProject&&owner);
}
// VPYGY5: the Risk filter behind the Home tiles (service.py export_tasks applies the same rules).
function isAtRisk(t){return t.due_state==="overdue"||!!t.is_blocked||!!t.is_critical_path||t.status==="delayed"}
function matchesRisk(t,risk){return risk==="blocked"?!!t.is_blocked:risk==="critical"?!!t.is_critical_path:risk==="atrisk"?isAtRisk(t):risk==="reassign"?!!(t.needs_new_assignee||t.needs_new_collaborator):true}
// The portfolio filters, applied to the loaded tasks (the same rules the export reuses on the server).
function visibleTasks(){
  const project=document.querySelector("#project-filter").value,status=document.querySelector("#status-filter").value,
    entity=document.querySelector("#entity-filter").value,crit=document.querySelector("#crit-filter").value,
    band=document.querySelector("#band-filter").value,owner=document.querySelector("#owner-filter").value.toLowerCase(),
    openOnly=document.querySelector("#open-only").checked,risk=document.querySelector("#risk-filter").value;
  return state.tasks.filter(t=>
    (!risk||matchesRisk(t,risk))&&
    (!project||t.project_id===project)&&
    (!status||t.status===status)&&
    (!entity||projectEntityIds(t.project_id).has(entity))&&
    (!crit||(crit==="unrated"?!t.criticality:t.criticality===crit))&&
    (!band||matchesBand(t,band))&&
    (!owner||(t.owner_name||"").toLowerCase().includes(owner))&&
    (!openOnly||!CLOSED_STATUSES.includes(t.status)));
}
function matchesBand(t,band){
  if(band==="undated")return t.due_state==="undated";
  if(band==="overdue")return t.due_state==="overdue";
  if(band==="today")return t.due_state==="today";
  const n=Number(band);
  return t.days_to_due!=null&&t.days_to_due>=0&&t.days_to_due<=n;
}
function renderBands(tasks){
  const inRange=(a,b)=>tasks.filter(t=>t.days_to_due!=null&&t.days_to_due>=a&&t.days_to_due<=b).length;
  const bands=[
    ["Overdue",tasks.filter(t=>t.due_state==="overdue").length,"overdue"],
    ["Today",tasks.filter(t=>t.due_state==="today").length,"today"],
    ["Days 1–7",inRange(1,7),"soon"],
    ["Days 8–14",inRange(8,14),"scheduled"],
    ["Days 15–30",inRange(15,30),"scheduled"],
    ["Undated",tasks.filter(t=>t.due_state==="undated").length,"undated"],
  ];
  document.querySelector("#bands").innerHTML=bands.map(([label,count,cls])=>
    `<div class="band ${cls}"><strong>${count}</strong><span>${escapeHtml(label)}</span></div>`).join("");
}
function fmtTick(d){return d.toLocaleDateString(undefined,{month:"short",day:"numeric"})}
// D73AQW: a task's steps are its subtasks. In the Schedule table and the task panel's sub-task
// list each step has a numbered swatch (hue = step index, Okabe-Ito order); colour is never the
// only carrier, the number is always beside it. The chart itself (2026-11) colours by status.
const STEP_HUES=7;
const CLOSED_STATUSES=["completed","cancelled","abandoned"];
const STATUS_LABELS={draft:"Draft",assigned:"Assigned",in_progress:"In progress",submitted:"Submitted",changes_requested:"Changes requested",completed:"Completed",on_hold:"On hold",delayed:"Delayed",cancelled:"Cancelled",abandoned:"Abandoned",reopened:"Reopened"};
// localStorage holds per-viewer conveniences only (collapsed phases, chart/table choice, day width).
const storage={get(k,f){try{const v=localStorage.getItem(k);return v==null?f:JSON.parse(v)}catch(e){return f}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
const phoneMQ=window.matchMedia?window.matchMedia("(max-width: 760px)"):{matches:false};
// 3C1Z74 review M1: below 1024px (and at 200% zoom) the task panel covers the screen, so everything behind it
// is made inert while it is open: Tab stays in the panel and nothing hidden behind it can take focus.
const fullMQ=window.matchMedia?window.matchMedia("(max-width: 1023px)"):{matches:false};
function syncPanelInert(){
  const panel=document.querySelector("#detail-dialog"),app=document.querySelector("#app");
  const covers=!!panel&&!panel.hidden&&fullMQ.matches&&!app.classList.contains("task-page");
  for(const el of [document.querySelector(".rail"),document.querySelector(".topbar"),document.querySelector("#skip-link"),...document.querySelectorAll("[data-view]")])
    if(el){if(covers)el.setAttribute("inert","");else el.removeAttribute("inert")}
}
if(fullMQ.addEventListener)fullMQ.addEventListener("change",syncPanelInert);
function currentView(){if(state.viewOverride)return state.viewOverride;const stored=storage.get("astra.gantt.view",null);if(stored==="table"||stored==="chart")return stored;return phoneMQ.matches?"table":"chart"}
// ISO dates parse as UTC midnight, so format them in UTC too or viewers west of UTC see the day before.
function fmtDay(iso){if(!iso)return "—";return new Date(iso).toLocaleDateString(undefined,{day:"numeric",month:"short",year:"numeric",timeZone:"UTC"})}
function statusLabel(s){return STATUS_LABELS[s]||String(s||"").replace(/_/g," ")}
function initials(name){return (name||"").split(/\s+/).filter(Boolean).slice(0,2).map(w=>w[0].toUpperCase()).join("")}
function dueText(t){if(t.due_state==="undated")return "No due date";if(t.due_state==="closed")return "Closed";const d=t.days_to_due;if(d==null)return "";if(d<0)return `${-d} day${d===-1?"":"s"} overdue`;if(d===0)return "Due today";return `Due in ${d} day${d===1?"":"s"}`}
function stepOrder(children){return children.slice().sort((a,b)=>{const da=a.start_date||a.due_date||"9999",db=b.start_date||b.due_date||"9999";return da<db?-1:da>db?1:String(a.title||"").localeCompare(String(b.title||""))})}
function stepHue(idx){return ((idx-1)%STEP_HUES)+1}
function groupSteps(tasks){
  const visible=new Set(tasks.map(t=>t.id));
  // Step index comes from ALL children of a parent (state.tasks), so a step keeps its
  // number and colour whatever the filters hide; only the drawn set follows the filters.
  const allChildren=new Map();
  for(const t of state.tasks){if(t.parent_task_id){if(!allChildren.has(t.parent_task_id))allChildren.set(t.parent_task_id,[]);allChildren.get(t.parent_task_id).push(t)}}
  const stepIndex=new Map();
  for(const kids of allChildren.values()){const ordered=timelineOrder(stepOrder(kids));ordered.forEach((k,i)=>stepIndex.set(k.id,{idx:i+1,total:ordered.length}))}
  const childrenOf=new Map(),top=[];
  for(const t of tasks){
    if(t.parent_task_id&&visible.has(t.parent_task_id)){if(!childrenOf.has(t.parent_task_id))childrenOf.set(t.parent_task_id,[]);childrenOf.get(t.parent_task_id).push(t)}
    else top.push(t);
  }
  for(const [pid,kids] of childrenOf)childrenOf.set(pid,timelineOrder(stepOrder(kids)));
  top.splice(0,top.length,...timelineOrder(top));
  return {top,childrenOf,stepIndex,visible,hasSteps:childrenOf.size>0};
}
// GF-6: a re-render (resize, filter, view change) replaces the chart's DOM. If focus was inside it,
// remember which control held it (kind + id attribute) and put focus back on its replacement.
const FOCUS_ATTRS=["data-detail","data-phase","data-bar"],FOCUS_KINDS=["gx-name","gx-open","gx-phase-toggle","gx-bar","gx-ms","link"];
function focusKeyIn(root){const a=document.activeElement;if(!a||!root.contains(a))return null;const attr=FOCUS_ATTRS.find(x=>a.hasAttribute(x));if(!attr)return null;const kind=FOCUS_KINDS.find(k=>a.classList.contains(k));return `${kind?"."+kind:""}[${attr}="${CSS.escape(a.getAttribute(attr))}"]`}
function restoreFocus(root,sel){if(!sel)return;const n=root.querySelector(sel);if(n&&!n.closest("[hidden]"))n.focus({preventScroll:true})}
function projectSchedule(p,selected=""){
  const forecasts=p.schedule_forecasts||{};
  if(selected&&forecasts[selected])return forecasts[selected];
  if(p.scheduled_dates)return p.scheduled_dates;
  const all=Object.values(forecasts),starts=all.map(f=>f.start_date).filter(Boolean).sort(),finishes=all.map(f=>f.finish_date).filter(Boolean).sort();
  return {start_date:starts[0]||null,finish_date:finishes.at(-1)||null,undated_count:all.some(f=>f.undated_count)?1:0};
}
// The Gantt follows shadcnstudio's gantt-chart-04 block (phase and step plan with dependencies),
// rebuilt in plain JS: a sticky Step pane beside a day grid for one month or one week, status
// coloured bars that move and resize by whole days, milestones, phase summaries and finish-to-start
// arrows. Positions travel as data-l / data-w pixels and are applied through the CSSOM (gxPlace),
// because the CSP drops inline style attributes. docs/handoff/README.md maps every feature to its code.
const GX_DAY=86400000,GX_ROW=48,GX_WIDTHS=[32,40,48,64,88,120],GX_PANE={sm:192,md:288,lg:560};
const MONTH_SHORT=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const MONTH_LONG=["January","February","March","April","May","June","July","August","September","October","November","December"];
const DOW_SHORT=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const GX_STATUS={completed:"Completed",progress:"In Progress",risk:"At Risk",blocked:"Blocked",queued:"Queued"};
const GX_ICON_OF={completed:"check",progress:"loader",risk:"alert",blocked:"ban",queued:"dashed"};
const GX_ICONS={
  chevron:'<path d="m9 18 6-6-6-6"/>',
  check:'<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  loader:'<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
  alert:'<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  ban:'<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  dashed:'<path d="M10.1 2.182a10 10 0 0 1 3.8 0"/><path d="M13.9 21.818a10 10 0 0 1-3.8 0"/><path d="M17.609 3.721a10 10 0 0 1 2.69 2.7"/><path d="M2.182 13.9a10 10 0 0 1 0-3.8"/><path d="M20.279 17.609a10 10 0 0 1-2.7 2.69"/><path d="M21.818 10.1a10 10 0 0 1 0 3.8"/><path d="M3.721 6.391a10 10 0 0 1 2.7-2.69"/><path d="M6.391 20.279a10 10 0 0 1-2.69-2.7"/>',
  link:'<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  flag:'<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
  open:'<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
};
function gxIcon(name,cls=""){return `<svg class="gx-icon${cls?" "+cls:""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${GX_ICONS[name]}</svg>`}
// What the chart remembers between renders. anchor is a date inside the shown period; scope is the
// set of projects it was chosen for, so a different page starts at its own work again.
const gx={anchor:null,scope:null,hiddenStatus:new Set(),hiddenOwner:new Set(),hover:null,focus:null,geo:new Map(),edges:[],popOpen:false};
const gxIso=ms=>new Date(ms).toISOString().slice(0,10);
function gxMode(){return storage.get("astra.gantt.period","month")==="week"?"week":"month"}
// The day width is kept as pixels, so a change to the list of steps never reads an old index.
function gxZoom(){const w=storage.get("astra.gantt.daywidth",48),i=GX_WIDTHS.indexOf(w);return i<0?GX_WIDTHS.indexOf(48):i}
function gxCollapsed(){const v=storage.get("astra.gantt.collapsed",[]);return new Set(Array.isArray(v)?v:[])}
// The shown period: a calendar month, or a Monday to Sunday week. All dates are UTC days.
function gxPeriod(anchor,mode){
  const d=new Date(Date.parse(anchor));
  if(mode==="week"){const start=d.getTime()-((d.getUTCDay()+6)%7)*GX_DAY,s=new Date(start);return {mode,start,days:7,title:`Week of ${MONTH_SHORT[s.getUTCMonth()]} ${s.getUTCDate()}, ${s.getUTCFullYear()}`}}
  const y=d.getUTCFullYear(),m=d.getUTCMonth();
  return {mode,start:Date.UTC(y,m,1),days:new Date(Date.UTC(y,m+1,0)).getUTCDate(),title:`${MONTH_LONG[m]} ${y}`};
}
function gxShift(anchor,mode,dir){const d=new Date(Date.parse(anchor));return gxIso(mode==="week"?d.getTime()+dir*7*GX_DAY:Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+dir,1))}
// ISO 8601 week number: the week belongs to the year of its Thursday.
function gxWeek(ms){const dow=(new Date(ms).getUTCDay()+6)%7,thu=new Date(ms+(3-dow)*GX_DAY);return Math.floor((thu.getTime()-Date.UTC(thu.getUTCFullYear(),0,1))/GX_DAY/7)+1}
function gxDay(ms){const d=new Date(ms);return `${MONTH_SHORT[d.getUTCMonth()]} ${d.getUTCDate()}`}
function gxRange(s,e){if(s===e)return gxDay(s);const a=new Date(s),b=new Date(e);return a.getUTCMonth()===b.getUTCMonth()&&a.getUTCFullYear()===b.getUTCFullYear()?`${gxDay(s)} – ${b.getUTCDate()}`:`${gxDay(s)} – ${gxDay(e)}`}
// A task's drawn days. A milestone is one day (its due date); a task with one date is one day.
function gxSpan(t){const s=t.is_milestone?(t.due_date||t.start_date):(t.start_date||t.due_date);if(!s)return null;const e=t.is_milestone?s:(t.due_date||t.start_date);return {s,e:e<s?s:e}}
function gxDates(t){const p=gxSpan(t);return p?gxRange(Date.parse(p.s),Date.parse(p.e)):"—"}
function gxLen(t){const p=gxSpan(t);return !p||t.is_milestone?"—":`${Math.round((Date.parse(p.e)-Date.parse(p.s))/GX_DAY)+1}d`}
function gxProgress(t){return t.status==="completed"?100:Math.max(0,Math.min(100,Math.round(+t.progress||0)))}
// Astra's eleven statuses and its blocked / overdue flags fold into the block's five colours.
// The pane's badge keeps Astra's own status name in its title.
function gxStatus(t){
  if(t.status==="completed")return "completed";
  if(t.is_blocked||t.status==="on_hold")return "blocked";
  if(t.status==="cancelled"||t.status==="abandoned")return "queued";
  if(t.due_state==="overdue"||t.status==="delayed")return "risk";
  if(["in_progress","submitted","reopened","changes_requested"].includes(t.status))return "progress";
  return "queued";
}
function gxCode(name){const w=String(name||"").replace(/[^A-Za-z0-9 ]+/g," ").split(/\s+/).filter(Boolean);return ((w.length>1?w.slice(0,4).map(x=>x[0]).join(""):(w[0]||"").slice(0,3)).toUpperCase())||"PH"}
// Phase codes: a project is its initials (REL); a task that has steps is that code and its number
// among the project's parent tasks (REL-01). Numbered over state.tasks so filters never renumber.
function gxCodes(){
  const parents=new Set(state.tasks.map(t=>t.parent_task_id).filter(Boolean)),byProject=new Map(),codes=new Map();
  for(const t of state.tasks)if(parents.has(t.id)){if(!byProject.has(t.project_id))byProject.set(t.project_id,[]);byProject.get(t.project_id).push(t)}
  for(const [pid,list] of byProject){const p=(state.projects||[]).find(x=>x.id===pid),base=gxCode(p?p.name:list[0].project_name);stepOrder(list).forEach((t,i)=>codes.set(t.id,`${base}-${String(i+1).padStart(2,"0")}`))}
  return codes;
}
function gxPhaseCode(t,codes){if(t.parent_task_id&&codes.has(t.parent_task_id))return codes.get(t.parent_task_id);const p=(state.projects||[]).find(x=>x.id===t.project_id);return gxCode(p?p.name:t.project_name)}
function gxExtent(list){let s=null,e=null;for(const t of list){const p=gxSpan(t);if(!p)continue;if(s==null||p.s<s)s=p.s;if(e==null||p.e>e)e=p.e}return s==null?null:{s,e}}
// Rows, top to bottom: a phase row per project, then its tasks; a task that has steps is itself a
// phase row with its steps under it. The Filter popover hides steps here, in the browser; a phase
// with no step left is hidden with them. Phase totals count every step, whatever the popover hides.
function gxModel(groups){
  const {top,childrenOf}=groups,rows=[],collapsed=gxCollapsed(),codes=gxCodes();
  const pass=t=>!gx.hiddenStatus.has(gxStatus(t))&&!gx.hiddenOwner.has(t.owner_user_id||"");
  const leavesOf=t=>{const kids=childrenOf.get(t.id);return kids&&kids.length?kids.flatMap(leavesOf):[t]};
  const walk=(t,depth)=>{
    const kids=childrenOf.get(t.id)||[];
    if(!kids.length){if(pass(t))rows.push({kind:"step",t,depth});return}
    const leaves=kids.flatMap(leavesOf);if(!leaves.some(pass))return;
    const key="t:"+t.id,open=!collapsed.has(key);
    rows.push({kind:"phase",key,t,name:t.title,code:codes.get(t.id)||"",depth,open,leaves,ext:gxExtent([t,...leaves])});
    if(open)kids.forEach(k=>walk(k,depth+1));
  };
  const byProject=new Map(),order=(state.projects||[]).map(p=>p.id),rank=id=>{const i=order.indexOf(id);return i<0?order.length:i};
  for(const t of top){if(!byProject.has(t.project_id))byProject.set(t.project_id,[]);byProject.get(t.project_id).push(t)}
  const all=[];
  for(const pid of [...byProject.keys()].sort((a,b)=>rank(a)-rank(b))){
    const list=byProject.get(pid),leaves=list.flatMap(leavesOf);all.push(...leaves);
    if(!leaves.some(pass))continue;
    const p=(state.projects||[]).find(x=>x.id===pid),name=p?p.name:(list[0].project_name||"Project"),key="p:"+pid,open=!collapsed.has(key);
    rows.push({kind:"phase",key,name,code:gxCode(name),depth:0,open,leaves,ext:gxExtent(leaves)});
    if(open)list.forEach(t=>walk(t,1));
  }
  return {rows,leaves:all};
}
// The period to open on: today's, when any work falls in it; otherwise the period of the dated work
// nearest today, so a plan that starts next quarter does not open on an empty month.
function gxAnchor(tasks,mode,el){
  const scope=[...new Set(tasks.map(t=>t.project_id))].sort().join(",");
  if(gx.anchor&&gx.scope===scope)return gx.anchor;
  gx.scope=scope;el.scrollLeft=0;
  // Other projects mean other people: a filter chosen for the last page could hide steps with no box left to untick.
  gx.hiddenStatus.clear();gx.hiddenOwner.clear();
  const today=ganttToday(),p=gxPeriod(today,mode),from=gxIso(p.start),to=gxIso(p.start+(p.days-1)*GX_DAY);
  let best=null,gap=Infinity;
  for(const t of tasks){
    const span=gxSpan(t);if(!span)continue;
    if(span.s<=to&&span.e>=from)return gx.anchor=today;
    const near=span.e<from?span.e:span.s,d=Math.abs(Date.parse(near)-Date.parse(today));
    if(d<gap){gap=d;best=near}
  }
  return gx.anchor=best||today;
}
function gxPlace(root){
  root.querySelectorAll("[data-l]").forEach(n=>{n.style.left=`${n.dataset.l}px`});
  root.querySelectorAll("[data-w]").forEach(n=>{n.style.width=`${n.dataset.w}px`});
  root.querySelectorAll("[data-pc]").forEach(n=>{n.style.width=`${n.dataset.pc}%`});
}
function gxAvatar(t,cls=""){return `<span class="gx-avatar${cls?" "+cls:""}" title="${escapeHtml(t.owner_name||"Unassigned")}" role="img" aria-label="Owner: ${escapeHtml(t.owner_name||"Unassigned")}">${escapeHtml(initials(t.owner_name)||"–")}</span>`}
function gxRender(el,groups,period){
  const mode=period.mode,cw=el.clientWidth||window.innerWidth||1280,size=cw<640?"sm":cw<1024?"md":"lg",paneW=GX_PANE[size];
  // Month view: a fixed day width from the zoom steps. Week view: seven days share the room left.
  const dw=mode==="week"?Math.max(48,Math.floor((cw-paneW)/7)):GX_WIDTHS[gxZoom()];
  el.dataset.pane=size;el.dataset.mode=mode;el.dataset.day=dw;
  el.style.setProperty("--gx-day",`${dw}px`);el.style.setProperty("--gx-pane",`${paneW}px`);el.style.setProperty("--gx-days",period.days);
  const {rows,leaves}=gxModel(groups),todayMs=Date.parse(ganttToday());
  gxFilterFill(leaves);
  // Header: ISO week groups over one cell per day.
  const days=[...Array(period.days)].map((_,i)=>{const ms=period.start+i*GX_DAY,d=new Date(ms),dow=(d.getUTCDay()+6)%7;return {ms,dow,n:d.getUTCDate(),we:dow>4,today:ms===todayMs}});
  const weeks=[];for(const d of days){const w=gxWeek(d.ms),last=weeks[weeks.length-1];if(last&&last.w===w){last.n++;last.to=d.ms}else weeks.push({w,n:1,from:d.ms,to:d.ms})}
  const weekRow=weeks.map(w=>`<span class="gx-week" data-w="${w.n*dw}"><span>W${w.w} · ${gxRange(w.from,w.to)}</span></span>`).join("");
  const dayRow=days.map(d=>`<span class="gx-day${d.we?" we":""}${d.today?" today":""}"${d.today?' aria-current="date"':""}>${mode==="week"?`<i>${DOW_SHORT[d.dow]}</i> `:""}${d.today?`<b class="gx-today-pill">${d.n}</b>`:d.n}</span>`).join("");
  const cols=days.map(d=>`<i class="gx-col${d.we?" we":""}${d.today?" today":""}"></i>`).join("");
  const idx=v=>Math.round((Date.parse(v)-period.start)/GX_DAY);
  // A bar is drawn only inside the shown period; cutS / cutE say which end runs past it.
  const clip=(s,e)=>{const a=idx(s),b=idx(e);if(b<0||a>=period.days)return null;const ca=Math.max(0,a),cb=Math.min(period.days-1,b);return {l:ca*dw,w:(cb-ca+1)*dw,cutS:a<0,cutE:b>=period.days}};
  gx.geo=new Map();gx.edges=[];gx.period={start:period.start,days:period.days,dw};
  const pane=[],time=[];
  rows.forEach((r,i)=>{
    const d=`gx-d${Math.min(r.depth,4)}`;
    if(r.kind==="phase"){
      const total=r.leaves.length,done=r.leaves.filter(t=>t.status==="completed").length,pct=total?Math.round(r.leaves.reduce((n,t)=>n+gxProgress(t),0)/total):0;
      const open=r.t?`<button type="button" class="gx-open" data-detail="${escapeHtml(r.t.id)}" aria-label="Open ${escapeHtml(r.name)}">${gxIcon("open")}</button>`:"";
      pane.push(`<div class="gx-row gx-phase ${d}" data-phase-row="${escapeHtml(r.key)}"${r.t?` data-timeline-task="${escapeHtml(r.t.id)}"`:""}><button type="button" class="gx-phase-toggle" data-phase="${escapeHtml(r.key)}" aria-expanded="${r.open}">${gxIcon("chevron","gx-chevron")}<span class="sr-only">${r.open?"Collapse":"Expand"} phase</span><span class="gx-phase-name" title="${escapeHtml(r.name)}">${escapeHtml(r.name)}</span>${r.code?`<span class="gx-code">${escapeHtml(r.code)}</span>`:""}</button>${open}<span class="gx-stat">${done}/${total}<span class="gx-stat-pct"> · ${pct}%</span></span></div>`);
      const c=r.ext&&clip(r.ext.s,r.ext.e);
      if(c&&r.t)gx.geo.set(r.t.id,{l:c.l,w:c.w,row:i,s:r.ext.s,e:r.ext.e});
      time.push(`<div class="gx-row gx-phase">${c?`<div class="gx-sum" data-l="${c.l}" data-w="${c.w}" role="img" aria-label="${escapeHtml(r.name)} · ${pct}%"><i class="gx-sum-fill" data-pc="${pct}"></i></div><span class="gx-sum-pct" data-l="${c.l+c.w+8}">${pct}%</span>`:""}</div>`);
      return;
    }
    const t=r.t,st=gxStatus(t),pct=gxProgress(t),id=escapeHtml(t.id),deps=(t.predecessors||[]).length,icon=gxIcon(GX_ICON_OF[st],"gx-status");
    pane.push(`<div class="gx-row gx-step ${d} gx-s-${st}" data-timeline-task="${id}"><span class="gx-guide" aria-hidden="true"></span><button type="button" class="gx-name" data-detail="${id}">${icon}<span class="gx-name-text" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</span><span class="sr-only"> · ${GX_STATUS[st]}</span>${deps?`<span class="gx-links" title="Depends on ${deps} step${deps===1?"":"s"}">${gxIcon("link")}<span aria-hidden="true">${deps}</span><span class="sr-only"> · depends on ${deps} step${deps===1?"":"s"}</span></span>`:""}</button>${gxAvatar(t,"gx-col-owner")}<span class="gx-badge gx-col-status" title="${escapeHtml(statusLabel(t.status))}"><i class="gx-dot"></i>${GX_STATUS[st]}</span><span class="gx-col-dates" data-dates="${id}">${gxDates(t)}</span><span class="gx-col-len" data-len="${id}">${gxLen(t)}</span></div>`);
    const span=gxSpan(t),c=span&&clip(span.s,span.e),label=escapeHtml(`${t.title} · ${GX_STATUS[st]} · ${pct}%`),drag=canDragBar(t)?` data-drag="${id}"`:"";
    let bar="";
    if(c&&t.is_milestone){
      const l=c.l+(dw-28)/2;gx.geo.set(t.id,{l,w:28,row:i,s:span.s,e:span.e});
      bar=`<div class="gx-ms gx-s-${st}" role="button" tabindex="0" aria-haspopup="dialog" data-bar="${id}"${drag} data-l="${l}" data-w="28" title="${label}" aria-label="${label}">${gxIcon("flag")}<span class="gx-ms-label">${escapeHtml(t.title)}</span></div>`;
    }else if(c){
      gx.geo.set(t.id,{l:c.l,w:c.w,row:i,s:span.s,e:span.e});
      const grips=drag?`${c.cutS?"":'<i class="gx-grip start" data-edge="start" aria-hidden="true"></i>'}${c.cutE?"":'<i class="gx-grip end" data-edge="end" aria-hidden="true"></i>'}`:"";
      bar=`<div class="gx-bar gx-s-${st}${c.cutS?" cut-start":""}${c.cutE?" cut-end":""}" role="button" tabindex="0" aria-haspopup="dialog" data-bar="${id}"${drag} data-l="${c.l}" data-w="${c.w}" title="${label}" aria-label="${label}"><i class="gx-fill" data-pc="${pct}"></i>${icon}<span class="gx-bar-name">${escapeHtml(t.title)}</span><span class="gx-bar-pct">${pct}%</span>${gxAvatar(t)}${grips}</div>`;
    }
    time.push(`<div class="gx-row gx-step">${bar}</div>`);
  });
  // An arrow needs both ends drawn: a step hidden by a filter, a collapsed phase or the edge of the
  // period takes its arrows with it.
  for(const r of rows){const t=r.t;if(!t||!gx.geo.has(t.id))continue;for(const p of t.predecessors||[])if(gx.geo.has(p.task_id)&&p.task_id!==t.id)gx.edges.push([p.task_id,t.id])}
  const none=rows.length?"":`<div class="gx-none">No steps match the filter.</div>`;
  const marker=(id,size,cls)=>`<marker id="${id}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="${size}" markerHeight="${size}" markerUnits="userSpaceOnUse" orient="auto"><path class="${cls}" d="M0 0.5 L7 4 L0 7.5 Z"/></marker>`;
  el.innerHTML=`<div class="gx-inner"><div class="gx-pane"><div class="gx-pane-head"><span class="gx-col-step">Step</span><span class="gx-col-owner">Owner</span><span class="gx-col-status">Status</span><span class="gx-col-dates">Dates</span><span class="gx-col-len">Length</span></div>${pane.join("")}${none}</div>`
    +`<div class="gx-time"><div class="gx-time-head"><div class="gx-weeks">${weekRow}</div><div class="gx-days">${dayRow}</div></div>`
    +`<div class="gx-body"><div class="gx-cols" aria-hidden="true">${cols}</div><svg class="gx-deps" width="${period.days*dw}" height="${rows.length*GX_ROW}" aria-hidden="true" focusable="false"><defs>${marker("gx-arrow",7,"gx-head-idle")}${marker("gx-arrow-active",8,"gx-head-active")}${marker("gx-arrow-conflict",7,"gx-head-conflict")}</defs><g class="gx-deps-paths"></g></svg>${time.join("")}</div></div></div>`;
  gxPlace(el);
  gxDrawDeps();
}
// One arrow, finish to start, with 6px corners. Forward: out of the predecessor's right edge, down
// (or up) a vertical 12px to its right, into the successor's left edge. When the successor starts
// too close or earlier, the line goes round under the predecessor's row and comes in from the left.
function gxPath(a,b){
  const sx=a.l+a.w,sy=a.row*GX_ROW+GX_ROW/2,ex=b.l-1,ey=b.row*GX_ROW+GX_ROW/2;
  if(ex-sx>=24){
    if(ey===sy)return `M ${sx} ${sy} L ${ex} ${ey}`;
    const d=ey>sy?1:-1,x=sx+12;
    return `M ${sx} ${sy} L ${sx+6} ${sy} Q ${x} ${sy} ${x} ${sy+6*d} L ${x} ${ey-6*d} Q ${x} ${ey} ${x+6} ${ey} L ${ex} ${ey}`;
  }
  // bx never lies right of x-12, so the line between the rows always runs leftwards (no kink for a 12-24px gap).
  const d1=ey>=sy?1:-1,my=sy+GX_ROW/2*d1,d2=ey>my?1:-1,x=sx+12,bx=Math.min(ex-12,x-12);
  return `M ${sx} ${sy} L ${sx+6} ${sy} Q ${x} ${sy} ${x} ${sy+6*d1} L ${x} ${my-6*d1} Q ${x} ${my} ${x-6} ${my} L ${bx+6} ${my} Q ${bx} ${my} ${bx} ${my+6*d2} L ${bx} ${ey-6*d2} Q ${bx} ${ey} ${bx+6} ${ey} L ${ex} ${ey}`;
}
// Draws every arrow. `over` is the bar being dragged, with the place and dates it would get, so a
// conflict shows while the pointer is still down. Conflict (the successor starts on or before the
// day its predecessor ends) beats active (the pointer or focus is on either end).
function gxDrawDeps(over){
  const g=document.querySelector("#gantt .gx-deps-paths");if(!g)return;
  if(storage.get("astra.gantt.deps",true)===false){g.innerHTML="";return}
  const at=id=>over&&over.id===id?over:gx.geo.get(id),hot=new Set([gx.hover,gx.focus,over&&over.id].filter(Boolean));
  g.innerHTML=gx.edges.map(([from,to])=>{
    const a=at(from),b=at(to),st=b.s<=a.e?"conflict":hot.has(from)||hot.has(to)?"active":"idle";
    return `<path class="gx-dep gx-dep-${st}" data-from="${escapeHtml(from)}" data-to="${escapeHtml(to)}" d="${gxPath(a,b)}" marker-end="url(#gx-arrow${st==="idle"?"":"-"+st})"/>`;
  }).join("");
}
// While a bar is dragged or resized the Dates and Length cells of its row and its arrows follow it.
// Called with no place (l == null) to put the row back as the server has it.
function gxDragLive(t,dates,l,w){
  const el=document.querySelector("#gantt"),next={...t,start_date:dates.start_date,due_date:dates.due_date},sel=`="${CSS.escape(t.id)}"]`;
  const d=el.querySelector(`[data-dates${sel}`),n=el.querySelector(`[data-len${sel}`);
  if(d)d.textContent=gxDates(next);if(n)n.textContent=gxLen(next);
  const span=gxSpan(next),geo=gx.geo.get(t.id);
  gxDrawDeps(l==null||!geo||!span?null:{...geo,id:t.id,l,w,s:span.s,e:span.e});
}
// Where a bar with these dates sits in the drawn period, cut at its edges (a milestone is its 28px flag).
function gxBarBox(t,next){
  const p=gx.period;if(!p)return null;
  const idx=v=>Math.round((Date.parse(v)-p.start)/GX_DAY),last=p.days-1,clamp=i=>Math.min(Math.max(i,0),last);
  const s=next.start_date||next.due_date,e=next.due_date||s;if(!s)return null;
  const a=clamp(idx(s)),b=clamp(idx(e));
  if(t.is_milestone)return {left:b*p.dw+(p.dw-28)/2,width:28};
  return {left:a*p.dw,width:(Math.max(a,b)-a+1)*p.dw};
}
function gxTogglePhase(key){
  const c=gxCollapsed(),open=c.has(key);if(open)c.delete(key);else c.add(key);
  storage.set("astra.gantt.collapsed",[...c]);
  const id=key.slice(2),name=(key.startsWith("t:")?state.tasks.find(t=>t.id===id)?.title:(state.projects||[]).find(p=>p.id===id)?.name)||"Phase";
  announce(`${name} ${open?"expanded":"collapsed"}.`);
  refreshGantt();
}
// Filter popover: a tick box per status and per owner, with the number of steps each has. Everything
// is ticked to begin with; unticking hides those steps and their arrows in this browser only.
function gxFilterFill(leaves){
  const pop=document.querySelector("#gantt-filter"),btn=document.querySelector("#gantt-filter-btn");if(!pop||!btn)return;
  // The rows are rebuilt on every redraw (a resize too): a box that had focus gets it back.
  const a=document.activeElement,ds=a&&pop.contains(a)?a.dataset||{}:{},held=ds.fstatus!=null?["data-fstatus",ds.fstatus]:ds.fowner!=null?["data-fowner",ds.fowner]:null;
  const count=new Map(),owners=new Map();
  for(const t of leaves){const s=gxStatus(t),o=t.owner_user_id||"";count.set(s,(count.get(s)||0)+1);const cur=owners.get(o)||{name:o?(t.owner_name||"Unknown"):"Unassigned",n:0};cur.n++;owners.set(o,cur)}
  const row=(attr,key,on,mark,label,n)=>`<label class="gx-pop-row"><input type="checkbox" ${attr}="${escapeHtml(key)}"${on?" checked":""}>${mark}<span class="gx-pop-label">${escapeHtml(label)}</span><span class="gx-count">${n}</span></label>`;
  pop.innerHTML='<p class="gx-pop-head">Status</p>'+Object.keys(GX_STATUS).map(k=>row("data-fstatus",k,!gx.hiddenStatus.has(k),`<i class="gx-dot gx-s-${k}"></i>`,GX_STATUS[k],count.get(k)||0)).join("")
    +'<p class="gx-pop-head">Owner</p>'+([...owners].sort((a,b)=>(!a[0])-(!b[0])||a[1].name.localeCompare(b[1].name)).map(([id,o])=>row("data-fowner",id,!gx.hiddenOwner.has(id),`<span class="gx-avatar">${escapeHtml(initials(id?o.name:"")||"–")}</span>`,o.name,o.n)).join("")||'<p class="gx-pop-empty">No steps yet.</p>');
  const active=gx.hiddenStatus.size+gx.hiddenOwner.size>0;
  btn.classList.toggle("is-on",active);btn.setAttribute("aria-label",active?"Filter (some steps are hidden)":"Filter");
  if(held)pop.querySelector(`[${held[0]}="${CSS.escape(held[1])}"]`)?.focus();
}
function gxCloseFilter(refocus){const pop=document.querySelector("#gantt-filter"),btn=document.querySelector("#gantt-filter-btn");if(!pop||!gx.popOpen)return;gx.popOpen=false;pop.hidden=true;btn.setAttribute("aria-expanded","false");if(refocus)btn.focus()}
// Toolbar state for this render. The period controls, the switch, the popover and the zoom buttons
// belong to the chart, so the Schedule table hides them.
function gxToolbar(showTable,period){
  const q=s=>document.querySelector(s),zi=gxZoom(),week=period.mode==="week";
  q("#gantt-title").textContent=showTable?"Schedule":period.title;
  q("#gantt-period").value=period.mode;
  for(const s of ["#gantt-nav","#gantt-today","#gantt-period","#gantt-filter-btn","#gantt-zoom"])q(s).hidden=showTable;
  const depBox=q("#gantt-deps"),depLabel=depBox.closest("label");depBox.checked=storage.get("astra.gantt.deps",true)!==false;if(depLabel)depLabel.hidden=showTable;
  if(showTable)gxCloseFilter(false);
  // Zoom changes the day width of the month view; a week always fills the width it has.
  q('#gantt-zoom [data-zoom="in"]').disabled=week||zi>=GX_WIDTHS.length-1;
  q('#gantt-zoom [data-zoom="out"]').disabled=week||zi<=0;
  q("#gantt-new-step").hidden=!gxSheetProjects().length;
}
// New Step: the block's sheet. The step is created by the same POST /api/tasks as every other task,
// so service.py decides who may add it, where, and with which predecessors.
function gxSheetProjects(){const r=currentRoute();return (state.projects||[]).filter(p=>canCaptureProject(p)&&(r.name!=="project"||p.id===r.id))}
function gxSheetField(name){return document.querySelector(`#step-form [name="${name}"]`)}
function gxSheetPhase(){
  const v=gxSheetField("phase").value,parent=v.startsWith("t:")?state.tasks.find(t=>t.id===v.slice(2)):null;
  return {pid:parent?parent.project_id:v.slice(2),parent};
}
function gxSheetSync(owner){
  const {pid,parent}=gxSheetPhase(),codes=gxCodes(),edit=gxEditTask();
  // Editing keeps the owner chosen (or the step's own on opening); a new step starts unassigned.
  const pick=gxSheetField("owner_user_id"),keep=owner||(edit?[pick.value,pick.selectedOptions?.[0]?.textContent||""]:["",""]);
  fillAssignees(pid,pick,keep[0]||"",parent?"subtask":"task",keep[1]||"");
  // A step cannot wait for the phase it sits in, or a phase above it: that bar spans the step, so the
  // link would always be a conflict. service.py refuses it too.
  const above=new Set();for(let p=parent;p&&!above.has(p.id);p=p.parent_task_id?state.tasks.find(x=>x.id===p.parent_task_id):null)above.add(p.id);
  // An edited step cannot wait for itself, a step inside it, or a step that already waits on it
  // (directly or through others): the block leaves those out, and service.py refuses a loop.
  const out=edit?new Set([edit.id,...gxSubtree(edit.id),...gxDownstream(edit.id)]):new Set();
  const ticked=edit?gx.editChecked:new Set();
  const list=timelineOrder(stepOrder(state.tasks.filter(t=>t.project_id===pid&&!above.has(t.id)&&!out.has(t.id)&&!["cancelled","abandoned"].includes(t.status))));
  document.querySelector("#step-deps").innerHTML=list.map(t=>`<label class="gx-dep-row"><input type="checkbox" name="dep" value="${escapeHtml(t.id)}"${ticked.has(t.id)?" checked":""}><span class="gx-dep-name">${escapeHtml(t.title)}</span><span class="gx-code">${escapeHtml(gxPhaseCode(t,codes))}</span></label>`).join("")||'<p class="gx-dep-empty">No other steps in this project yet.</p>';
}
function gxSheetType(){
  const milestone=gxSheetField("type").value==="milestone";
  document.querySelector("#step-form [data-end-field]").hidden=milestone;
  document.querySelector("#step-form [data-start-label]").textContent=milestone?"Date":"Start";
}
function gxOpenSheet(){
  const projects=gxSheetProjects();
  if(!projects.length){showToast("You can add steps only to an open project you manage.");return}
  const form=document.querySelector("#step-form"),codes=gxCodes();
  form.reset();form.querySelector(".error").textContent="";
  gx.editId=null;gxSheetMode(null);
  // As in the block, a new step starts and ends today.
  gxSheetField("start_date").value=gxSheetField("due_date").value=appToday();
  gxSheetField("phase").innerHTML=projects.map(p=>`<option value="p:${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`
    +stepOrder(state.tasks.filter(t=>t.project_id===p.id&&codes.has(t.id)&&!CLOSED_STATUSES.includes(t.status))).map(t=>`<option value="t:${escapeHtml(t.id)}">${escapeHtml(p.name)} › ${escapeHtml(t.title)} (${escapeHtml(codes.get(t.id))})</option>`).join("")).join("");
  const want=currentRoute().name==="portfolio"?document.querySelector("#project-filter").value:"";
  if(want&&projects.some(p=>p.id===want))gxSheetField("phase").value="p:"+want;
  gxSheetType();gxSheetSync();
  document.querySelector("#step-sheet").showModal();
}
async function gxSubmitStep(e){
  e.preventDefault();
  const form=e.target,dialog=form.closest("dialog"),error=form.querySelector(".error");
  // One request at a time: a double click on Create must not create the step twice.
  if(gx.sheetBusy)return;
  error.textContent="";
  // Enter in the reason for cancelling answers that question: it cancels the step, it does not Save.
  if(gx.editId&&!document.querySelector("#step-cancel-confirm").hidden)return gxCancelStep();
  if(gx.editId)return gxSaveStep(form,dialog,error,e.submitter);
  const f=n=>gxSheetField(n).value,{pid,parent}=gxSheetPhase(),milestone=f("type")==="milestone";
  const payload={title:f("title").trim(),project_id:pid,status:f("status"),is_milestone:milestone,description:f("description"),
    predecessor_task_ids:[...form.querySelectorAll('[name="dep"]')].filter(i=>i.checked).map(i=>i.value)};
  if(parent)payload.parent_task_id=parent.id;
  if(f("owner_user_id"))payload.owner_user_id=f("owner_user_id");
  // A milestone is one day: its date is the due date, as everywhere else in Astra.
  if(milestone){if(f("start_date"))payload.due_date=f("start_date")}
  else{if(f("start_date"))payload.start_date=f("start_date");if(f("due_date"))payload.due_date=f("due_date")}
  if(f("progress")!=="")payload.progress=Number(f("progress"));
  let out;gx.sheetBusy=true;if(e.submitter)e.submitter.disabled=true;
  try{out=await withConfirms({title:payload.title||"the new step"},COLUMN_OF_STATUS[payload.status]||"draft",more=>api("/api/tasks",{method:"POST",body:JSON.stringify({...payload,...more})}))}
  catch(err){error.textContent=err.message;return}
  finally{gx.sheetBusy=false;if(e.submitter)e.submitter.disabled=false}
  if(!out)return;
  const {task}=out;form.reset();dialog.close();
  // The step exists now: a failed reload is the page's to report, not the closed sheet's.
  try{await load()}catch(err){showToast(`“${payload.title}” was added, but the page could not reload: ${err.message}`,null,null,true);return}
  if(task&&currentRoute().name==="portfolio"&&!visibleTasks().some(t=>t.id===task.id))showToast(`“${task.title}” was added · the current filters hide it`,"Show it",showAllOnPortfolio);
  else if(task)announce(`“${task.title}” was added.`);
}
// Edit Step: in the block a bar opens this sheet (a click, Enter or Space). Astra keeps the step name
// for the full task panel and gives the sheet an "Open task" link. Every change goes through the same
// service call the task panel uses (update, parent, dependencies), with the same confirmations, so
// service.py decides; a step the user cannot change here, or a closed one, opens the task panel.
const GX_NEW_STATUSES=["draft","assigned","in_progress","delayed"];
const GX_SHEET_TEXT={null:["New Step","Add a step to the pipeline.","Create"],edit:["Edit Step","Update the schedule, status and links of this step.","Save"]};
function gxEditTask(){return gx.editId?state.tasks.find(t=>t.id===gx.editId)||null:null}
function gxEditable(t){const p=(state.projects||[]).find(x=>x.id===t.project_id);return !!(p&&canCaptureProject(p))&&!CLOSED_STATUSES.includes(t.status)&&t.status!=="submitted"}
function gxOpenBar(id){const t=state.tasks.find(x=>x.id===id);if(!t)return;if(gxEditable(t))gxOpenEdit(t);else openDetail(id)}
function gxSubtree(id){const seen=new Set(),todo=[id];while(todo.length){const cur=todo.pop();for(const x of state.tasks)if(x.parent_task_id===cur&&!seen.has(x.id)){seen.add(x.id);todo.push(x.id)}}return seen}
function gxDownstream(id){const seen=new Set(),todo=[id];while(todo.length){const cur=todo.pop();for(const x of state.tasks)if(!seen.has(x.id)&&(x.predecessors||[]).some(p=>p.task_id===cur)){seen.add(x.id);todo.push(x.id)}}return seen}
function gxTicked(){return new Set([...document.querySelectorAll('#step-deps [name="dep"]')].filter(b=>b.checked).map(b=>b.value))}
function gxSheetMode(t){
  const mode=t?"edit":null,[title,desc,submit]=GX_SHEET_TEXT[mode],q=s=>document.querySelector(s);
  q("#step-sheet-title").textContent=title;q("#step-sheet-desc").textContent=desc;q("#step-submit").textContent=submit;
  q("#step-open-task").hidden=q("#step-cancel-step").hidden=!t;q("#step-cancel-confirm").hidden=true;
  // A step's type is set when it is made: the service has no change from task to milestone.
  gxSheetField("type").disabled=!!t;
  // Cancelling has its own button, with its own question; Abandoned stays in the task panel.
  const statuses=t?STATUSES.filter(s=>!GOVERNED.includes(s)&&!["submitted","cancelled","abandoned"].includes(s)):GX_NEW_STATUSES;
  if(t&&!statuses.includes(t.status))statuses.unshift(t.status);
  gxSheetField("status").innerHTML=statuses.map(s=>`<option value="${s}">${escapeHtml(statusLabel(s))}</option>`).join("");
  q("#step-reason-field").hidden=q("#step-reason-hint").hidden=true;
  gxSheetField("reason").required=false;
}
function gxOpenEdit(t){
  const form=document.querySelector("#step-form"),codes=gxCodes(),p=(state.projects||[]).find(x=>x.id===t.project_id),F=gxSheetField;
  form.reset();form.querySelector(".error").textContent="";
  gx.editId=t.id;gx.editChecked=new Set((t.predecessors||[]).map(x=>x.task_id));gxSheetMode(t);
  // A step can move to the project itself or to another phase, never into itself or a step inside it.
  const inside=new Set([t.id,...gxSubtree(t.id)]),parent=t.parent_task_id?state.tasks.find(x=>x.id===t.parent_task_id):null;
  const phases=stepOrder(state.tasks.filter(x=>x.project_id===t.project_id&&codes.has(x.id)&&!inside.has(x.id)&&!CLOSED_STATUSES.includes(x.status)));
  if(parent&&!phases.includes(parent))phases.push(parent);
  const pname=p?p.name:t.project_name||"";
  F("phase").innerHTML=`<option value="p:${escapeHtml(t.project_id)}">${escapeHtml(pname)}</option>`
    +phases.map(x=>`<option value="t:${escapeHtml(x.id)}">${escapeHtml(pname)} › ${escapeHtml(x.title)}${codes.has(x.id)?` (${escapeHtml(codes.get(x.id))})`:""}</option>`).join("");
  F("phase").value=parent?"t:"+parent.id:"p:"+t.project_id;
  F("title").value=t.title||"";F("type").value=t.is_milestone?"milestone":"task";F("status").value=t.status;
  if(t.is_milestone){F("start_date").value=t.due_date||""}else{F("start_date").value=t.start_date||"";F("due_date").value=t.due_date||""}
  F("progress").value=t.progress==null?"":String(t.progress);F("description").value=t.description||"";
  gxSheetType();gxSheetSync([t.owner_user_id||"",t.owner_name||""]);gxReasonSync();
  const sheet=document.querySelector("#step-sheet");if(!sheet.open)sheet.showModal();
}
// What the sheet would send: only the fields that differ from the step, and the links to add or remove.
function gxEditPlan(t){
  const F=n=>gxSheetField(n).value,body={},milestone=!!t.is_milestone;
  const title=F("title").trim();if(title!==t.title)body.title=title;
  if((F("owner_user_id")||null)!==(t.owner_user_id||null))body.owner_user_id=F("owner_user_id")||null;
  if(F("status")!==t.status)body.status=F("status");
  // A milestone has one date, its due date; a start after it would be refused, so it moves with it.
  const due=milestone?(F("start_date")||null):(F("due_date")||null);
  const start=milestone?(t.start_date&&due&&t.start_date>due?due:(t.start_date||null)):(F("start_date")||null);
  if(start!==(t.start_date||null))body.start_date=start;
  if(due!==(t.due_date||null))body.due_date=due;
  const pr=F("progress")===""?null:Number(F("progress"));if(pr!==(t.progress??null))body.progress=pr;
  if(F("description")!==(t.description||""))body.description=F("description");
  const {parent}=gxSheetPhase(),parentId=parent?parent.id:null;
  const had=new Set((t.predecessors||[]).map(p=>p.task_id)),boxes=[...document.querySelectorAll('#step-deps [name="dep"]')];
  const add=boxes.filter(b=>b.checked&&!had.has(b.value)).map(b=>b.value),drop=boxes.filter(b=>!b.checked&&had.has(b.value)).map(b=>b.value);
  return {body,start,due,parentId,moveParent:parentId!==(t.parent_task_id||null),add,drop,
    needsReason:"status" in body||"start_date" in body||"due_date" in body||drop.length>0};
}
function gxReasonSync(){
  const t=gxEditTask();if(!t)return;
  const need=gxEditPlan(t).needsReason;
  document.querySelector("#step-reason-field").hidden=document.querySelector("#step-reason-hint").hidden=!need;
  gxSheetField("reason").required=need;
}
async function gxSheetInput(e){
  const t=gxEditTask();if(!t)return;
  if(["start_date","due_date","status"].includes(e.target.name))gxReasonSync();
  // As in the task panel, typing in the sheet takes an edit lease so no one else changes the step meanwhile.
  if(leases.has(t.id))return touchLease(t.id);
  if(gx.leaseAsked)return;gx.leaseAsked=true;
  const got=await takeLease(t.id,"edit").catch(err=>({ok:false,err}));gx.leaseAsked=false;
  if(got.ok&&gx.editId!==t.id){dropLease(t.id,"edit");return}   // the sheet closed meanwhile
  if(!got.ok&&gx.editId===t.id)document.querySelector("#step-form").querySelector(".error").textContent=got.err&&got.err.lock?lockText(got.err.lock):(got.err&&got.err.message)||"This step is in use.";
}
function gxSheetClosed(){const id=gx.editId;gx.editId=null;if(id)dropLease(id,"edit")}
async function gxSaveStep(form,dialog,error,submitter){
  const t=gxEditTask();if(!t){dialog.close();return}
  const plan=gxEditPlan(t),reason=gxSheetField("reason").value.trim();
  if(!Object.keys(plan.body).length&&!plan.moveParent&&!plan.add.length&&!plan.drop.length){dialog.close();return}
  if(plan.needsReason&&!reason){gxReasonSync();error.textContent="Give a reason: it is needed to change the dates or the status, or to remove a link.";gxSheetField("reason").focus();return}
  gx.sheetBusy=true;if(submitter)submitter.disabled=true;
  const done=[];let request=false;
  try{
    // The phase first: the owner is checked against where the step will sit (a sub-task or not).
    let revision=t.revision;
    if(plan.moveParent){
      const out=await withConfirms(t,null,more=>api(taskApi(t.id,"/parent"),{method:"POST",body:JSON.stringify({parent_task_id:plan.parentId,...more})}));
      if(!out)return;   // a confirmation was declined: nothing was saved
      if(out.task&&Number.isInteger(out.task.revision))revision=out.task.revision;
      done.push("phase");
    }
    if(Object.keys(plan.body).length){
      const out=await withDependencyConfirm(t,plan.body.status||t.status,more=>api(taskApi(t.id),{method:"POST",body:JSON.stringify({...plan.body,reason,expected_revision:revision,...more})}),
        {dates:{start_date:plan.start,due_date:plan.due}});
      if(!out){if(done.length)throw new Error("The other changes were not saved.");return}   // declined: nothing more is saved
      request=!!out.request;done.push("details");
    }
    for(const id of plan.add){await api("/api/task-dependencies",{method:"POST",body:JSON.stringify({predecessor_task_id:id,successor_task_id:t.id})});done.push("link")}
    for(const id of plan.drop){await api("/api/task-dependencies",{method:"DELETE",body:JSON.stringify({predecessor_task_id:id,successor_task_id:t.id,reason})});done.push("link")}
  }catch(err){
    // Nothing saved: the sheet stays as it is. Part saved: the step is reloaded and shown again, so
    // what the sheet shows is what is stored, with the refusal above it.
    if(!done.length&&(err.status!==409||err.lock)){error.textContent=err.lock?lockText(err.lock):err.message;return}
    try{await load()}catch{}
    const fresh=state.tasks.find(x=>x.id===t.id);
    if(fresh&&gxEditable(fresh)&&dialog.open){gxOpenEdit(fresh);form.querySelector(".error").textContent=(done.length?"Some changes were saved, but not all: ":"This step changed since it was opened; it has been reloaded. ")+err.message}
    else{dialog.close();showToast(`“${t.title}”: ${err.message}`,null,null,true)}
    return;
  }finally{gx.sheetBusy=false;if(submitter)submitter.disabled=false}
  dialog.close();
  try{await load()}catch(err){showToast(`“${t.title}” was saved, but the page could not reload: ${err.message}`,null,null,true);return}
  const said=request?"Owner request created for the status change; the step's live status is unchanged until it is decided.":`“${plan.body.title||t.title}” was saved.`;
  if(request)showToast(said);announce(said);
}
function gxAskCancel(){
  const t=gxEditTask();if(!t)return;
  document.querySelector("#step-cancel-text").textContent=`Cancel “${t.title}”? It is closed as Cancelled; its history is kept, and it can be reopened from the task panel.`;
  document.querySelector("#step-cancel-confirm").hidden=false;
  gxSheetField("cancel_reason").value="";gxSheetField("cancel_reason").focus();
}
async function gxCancelStep(){
  const t=gxEditTask(),dialog=document.querySelector("#step-sheet"),error=document.querySelector("#step-form").querySelector(".error");if(!t||gx.sheetBusy)return;
  const reason=gxSheetField("cancel_reason").value.trim();
  if(!reason){error.textContent="Give a reason for cancelling the step.";gxSheetField("cancel_reason").focus();return}
  error.textContent="";gx.sheetBusy=true;
  let out;
  try{out=await withDependencyConfirm(t,"cancelled",more=>api(taskApi(t.id),{method:"POST",body:JSON.stringify({status:"cancelled",reason,expected_revision:t.revision,...more})}))}
  catch(err){
    if(err.status!==409||err.lock){error.textContent=err.lock?lockText(err.lock):err.message;return}
    // The step changed since it was opened: show it as it is now, so a second try can succeed.
    try{await load()}catch{}
    const fresh=state.tasks.find(x=>x.id===t.id);
    if(fresh&&gxEditable(fresh)&&dialog.open){gxOpenEdit(fresh);document.querySelector("#step-form").querySelector(".error").textContent="This step changed since it was opened; it has been reloaded. "+err.message}
    else{dialog.close();showToast(`“${t.title}”: ${err.message}`,null,null,true)}
    return;
  }
  finally{gx.sheetBusy=false}
  if(!out)return;
  dialog.close();
  try{await load()}catch{}
  const said=out.request?`Owner request created to cancel “${t.title}”; the step stays until it is decided.`:`“${t.title}” was cancelled.`;
  showToast(said);announce(said);
}
function renderGantt(tasks){
  const planSelect=document.querySelector("#gantt-plan");
  const previous=planSelect.value;
  const names=[...new Set(tasks.map(t=>t.plan_option||"Shared"))].sort();
  planSelect.innerHTML='<option value="">All plans</option>'+names.map(name=>`<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
  if(names.includes(previous))planSelect.value=previous;
  planSelect.hidden=names.every(name=>name==="Shared");
  const planLabel=planSelect.closest("label");if(planLabel)planLabel.hidden=planSelect.hidden;
  planSelect.onchange=()=>refreshGantt();
  if(planSelect.value)tasks=tasks.filter(t=>(t.plan_option||"Shared")==="Shared"||t.plan_option===planSelect.value).map(t=>({...t,is_critical_path:(t.critical_for_plans||[]).includes(planSelect.value)}));
  const el=document.querySelector("#gantt"),tableEl=document.querySelector("#schedule-table");
  const focusKey=focusKeyIn(el);
  const showTable=currentView()==="table";
  document.querySelector("#view-table").checked=showTable;
  el.hidden=showTable;tableEl.hidden=!showTable;
  const period=gxPeriod(gxAnchor(tasks,gxMode(),el),gxMode());
  gxToolbar(showTable,period);
  renderBands(tasks);
  const groups=groupSteps(tasks);
  gx.geo=new Map();gx.edges=[];
  if(!tasks.length){const empty='<div class="empty">No tasks match these filters. Undated or unassigned work will appear here rather than being hidden.</div>';el.innerHTML=empty;tableEl.innerHTML=empty;gxFilterFill([]);return}
  if(showTable){renderScheduleTable(groups,tableEl);el.innerHTML="";return}
  tableEl.innerHTML="";
  gxRender(el,groups,period);
  restoreFocus(el,focusKey);
}
function canMoveTimelineTask(t){const p=(state.projects||[]).find(x=>x.id===t.project_id);return !!(p&&p.status!=="closed"&&canMoveOnBoard(t.project_id)&&!CLOSED_STATUSES.includes(t.status))}
function timelineMoveButton(t){return canMoveTimelineTask(t)?`<button type="button" class="quiet task-row-handle" data-task-move="${escapeHtml(t.id)}" aria-label="Move task ${escapeHtml(t.title)}">Move task</button>`:""}
function renderScheduleTable(groups,tableEl){
  const {top,childrenOf,stepIndex}=groups,scope=bulkScope();
  let steps=0;const rows=[];
  const cell=v=>`<td>${escapeHtml(v??"—")}</td>`;
  const walk=(t,parent)=>{
    const kids=childrenOf.get(t.id)||[];const m=stepIndex.get(t.id);const isStep=!!parent;
    const link=`<button type="button" class="link" data-detail="${escapeHtml(t.id)}">${escapeHtml(t.title)}</button>${timelineMoveButton(t)}`;
    const stepNo=isStep?`<i class="sw step-c${stepHue(m.idx)}${m.idx>STEP_HUES?" wrap":""}" aria-hidden="true">${m.idx}</i><span class="sr-only">Step ${m.idx}</span> of ${m.total}`:"—";
    const pick=scope?`<td class="pick">${isStep?"":pickBox(t)}</td>`:"";
    rows.push(`<tr data-timeline-task="${escapeHtml(t.id)}" class="${isStep?"step-tr":"task-tr"}${bulk.ids.has(t.id)?" is-picked":""}">${pick}${cell(t.project_name)}<td>${isStep?escapeHtml(parent.title):link}</td><td>${stepNo}</td><td>${isStep?link:"—"}</td><td>${escapeHtml(t.owner_name||"Unassigned")}${t.needs_new_assignee||t.needs_new_collaborator?" "+reassignChip(t):""}</td>${cell(t.start_date||"—")}${cell(t.due_date||"—")}${cell(statusLabel(t.status))}<td>${critLabel(t.criticality)}</td>${cell(dueText(t)||t.due_state)}<td>${t.is_critical_path?"Yes":"No"}</td></tr>`);
    if(isStep)steps++;
    kids.forEach(k=>walk(k,t));
  };
  top.forEach(t=>walk(t,null));
  const asOf=document.querySelector("#as-of").textContent;
  const head=(scope?'<th scope="col" class="pick"><input type="checkbox" data-pick-all aria-label="Select every task in this list"></th>':"")+["Project","Task","Step #","Step","Owner","Start","Due","Status","Criticality","Due state","Critical path"].map(h=>`<th scope="col">${h}</th>`).join("");
  tableEl.innerHTML=`<table class="sched-table"><caption>Schedule table · ${top.length} task${top.length===1?"":"s"}, ${steps} step${steps===1?"":"s"} · same filters as the Gantt · ${escapeHtml(asOf)}</caption><thead><tr>${head}</tr></thead><tbody>${rows.join("")}</tbody></table>`;
}
// Shared tooltip: the chart has none of its own any more. As in the block it follows, a bar says
// what it is through its title and aria-label ("Name · Status · 70%").
function announce(msg){const live=document.querySelector("#gantt-live");if(!live)return;live.textContent="";setTimeout(()=>{live.textContent=msg},30)}
(function wireGantt(){
  const gantt=document.querySelector("#gantt"),q=s=>document.querySelector(s);
  // Arrows touching the bar under the pointer, or the bar that has keyboard focus, turn active.
  const hot=(key,id)=>{if(gx[key]===id)return;gx[key]=id;if(!gdrag.active)gxDrawDeps()};
  gantt.addEventListener("mouseover",e=>{const b=e.target.closest("[data-bar]");hot("hover",b?b.dataset.bar:null)});
  gantt.addEventListener("mouseleave",()=>hot("hover",null));
  gantt.addEventListener("focusin",e=>{const b=e.target.closest("[data-bar]");hot("focus",b?b.dataset.bar:null)});
  gantt.addEventListener("focusout",()=>hot("focus",null));
  // Space on a bar opens Edit Step (or the task panel), as Enter does: it must not scroll the page.
  gantt.addEventListener("keydown",e=>{if(e.key===" "&&e.target.closest("[data-bar]"))e.preventDefault()});
  const step=dir=>{gx.anchor=gxShift(gx.anchor||ganttToday(),gxMode(),dir);refreshGantt()};
  q("#gantt-prev").onclick=()=>step(-1);
  q("#gantt-next").onclick=()=>step(1);
  q("#gantt-today").onclick=()=>{gx.anchor=ganttToday();refreshGantt()};
  q("#gantt-period").onchange=e=>{storage.set("astra.gantt.period",e.target.value==="week"?"week":"month");refreshGantt()};
  q("#gantt-zoom").addEventListener("click",e=>{const b=e.target.closest("[data-zoom]");if(!b||b.disabled)return;
    const i=Math.max(0,Math.min(GX_WIDTHS.length-1,gxZoom()+(b.dataset.zoom==="in"?1:-1)));storage.set("astra.gantt.daywidth",GX_WIDTHS[i]);refreshGantt();
    announce(`Day width ${GX_WIDTHS[i]} pixels.`)});
  q("#gantt-deps").onchange=e=>{storage.set("astra.gantt.deps",e.target.checked);gxDrawDeps()};
  const pop=q("#gantt-filter"),popBtn=q("#gantt-filter-btn");
  popBtn.onclick=()=>{if(gx.popOpen){gxCloseFilter(false);return}gx.popOpen=true;pop.hidden=false;popBtn.setAttribute("aria-expanded","true");pop.querySelector("input")?.focus()};
  pop.addEventListener("change",e=>{
    const box=e.target,status=box.dataset.fstatus,set=status!=null?gx.hiddenStatus:gx.hiddenOwner,key=status!=null?status:box.dataset.fowner;
    if(key==null)return;
    if(box.checked)set.delete(key);else set.add(key);
    refreshGantt();
    // The popover's rows were rebuilt with new counts: give focus back to the same box.
    pop.querySelector(`[${status!=null?"data-fstatus":"data-fowner"}="${CSS.escape(key)}"]`)?.focus();
  });
  document.addEventListener("click",e=>{if(!e.target.closest(".gx-pop-wrap"))gxCloseFilter(false)});
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&gx.popOpen&&!gdrag.active){e.preventDefault();gxCloseFilter(true)}});
  q("#gantt-new-step").onclick=gxOpenSheet;
  q("#step-discard").onclick=()=>q("#step-sheet").close();
  q("#step-close").onclick=()=>q("#step-sheet").close();
  q("#step-open-task").onclick=()=>{const id=gx.editId;q("#step-sheet").close();if(id)openDetail(id)};
  q("#step-cancel-step").onclick=gxAskCancel;
  q("#step-cancel-keep").onclick=()=>{q("#step-cancel-confirm").hidden=true;q("#step-cancel-step").focus()};
  q("#step-cancel-go").onclick=gxCancelStep;
  q("#step-sheet").addEventListener("close",gxSheetClosed);
  q("#step-form").addEventListener("input",gxSheetInput);
  q("#step-form").addEventListener("submit",gxSubmitStep);
  q("#step-form").addEventListener("change",e=>{
    if(e.target.name==="phase"){if(gx.editId)gx.editChecked=gxTicked();gxSheetSync()}
    else if(e.target.name==="type")gxSheetType();
    if(gx.editId){if(e.target.name==="dep")gx.editChecked=gxTicked();gxReasonSync()}
  });
  document.querySelector("#view-table").onchange=e=>{storage.set("astra.gantt.view",e.target.checked?"table":"chart");render()};
  if(phoneMQ.addEventListener)phoneMQ.addEventListener("change",()=>{if(state.user)refreshGantt()});
  let resizeTimer;window.addEventListener("resize",()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(state.user)refreshGantt()},150)});
})();
function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
// PZTYC9: the Gate 2 shell. A small hash router: #/home, #/my-work, #/inbox, #/projects. Moving between
// screens assigns location.hash (a history entry and a hashchange of its own), and a filter edit rewrites
// the Home link with history.replaceState, so nothing here needs pushState. Home filters ride in the query
// (#/home?status=delayed&open=1), so reload, Back and a pasted link restore them.
const VIEWS=["home","portfolio","my-work","inbox","projects"];
// The rail item a screen belongs to (the portfolio timeline sits under Projects).
const NAV_OF={portfolio:"projects",project:"projects"};
const VIEW_TITLES={home:["Home","Command Center"],portfolio:["Projects","Portfolio timeline"],"my-work":["My Work","Assigned to me"],inbox:["Inbox","Needs action and activity"],projects:["Projects","All projects"],project:["Projects","Project"],task:["Task","Task"]};
const FILTER_PARAMS=[["project","#project-filter"],["status","#status-filter"],["entity","#entity-filter"],["crit","#crit-filter"],["due","#band-filter"],["risk","#risk-filter"],["owner","#owner-filter"],["sort","#sort-filter"]];
// Task ids are UUIDs; anything else in a link is ignored rather than sent to the server.
const TASK_ID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function isTaskId(id){return typeof id==="string"&&TASK_ID.test(id)}
// CR121Z: a project page is #/project/<id>/<tab>; the tab defaults to Overview.
const PROJECT_TABS=[["overview","Overview"],["list","List"],["board","Board"],["timeline","Timeline"],["activity","Activity"]];
function parseRoute(hash){
  const raw=String(hash||"").replace(/^#\/?/,""),q=raw.indexOf("?"),path=q<0?raw:raw.slice(0,q);
  const [name,rawId,rawTab]=path.split("/");
  let id=null;try{id=rawId?decodeURIComponent(rawId):null}catch{id=null}   // a truncated %-escape is an unknown route, not an error
  const known=VIEWS.includes(name)||((name==="task"||name==="project")&&isTaskId(id));
  const tab=known&&name==="project"?(PROJECT_TABS.some(([k])=>k===rawTab)?rawTab:"overview"):null;
  const sub=known&&(name==="task"||name==="project"||(name==="my-work"&&id==="calendar"))?id:null;
  const routePath=!known?"home":name==="project"?`project/${encodeURIComponent(id)}/${tab}`:sub?`${name}/${encodeURIComponent(sub)}`:name;
  return {name:known?name:"home",id:sub,tab,path:routePath,params:new URLSearchParams(q<0?"":raw.slice(q+1))};
}
function currentRoute(){return parseRoute(location.hash)}
function filtersFromUrl(params){
  for(const [key,sel] of FILTER_PARAMS){const el=document.querySelector(sel),v=params.get(key)||(key==="sort"?"criticality":"");if(el.value!==v)el.value=v}
  document.querySelector("#open-only").checked=params.get("open")==="1";
}
function homeQuery(){
  const p=new URLSearchParams();
  for(const [key,sel] of FILTER_PARAMS){const v=document.querySelector(sel).value;if(v&&!(key==="sort"&&v==="criticality"))p.set(key,v)}
  if(document.querySelector("#open-only").checked)p.set("open","1");
  return p.toString();
}
function syncFilters(){
  const q=homeQuery(),hash="#/portfolio"+(q?"?"+q:""),task=currentRoute().params.get("task"),full=task?routeHash(parseRoute(hash),task):hash;
  // A filter changed while a task is open: closing must keep it, so the panel no longer goes Back to the
  // entry from before it opened; it strips ?task from this link instead.
  if(location.hash!==full){if(history.replaceState)history.replaceState(null,"",full);if(task)panelState.pushed=null}
  panelState.rendered=hash;
  setPortfolioLinks(hash);
}
// Every "Portfolio timeline" link returns to the filters last used there.
function setPortfolioLinks(hash){state.portfolioHash=hash;document.querySelectorAll(".portfolio-link").forEach(a=>a.setAttribute("href",hash))}
function filtersChanged(){syncFilters();render();shellTitle(currentRoute())}
function roleLabel(u){if(u.is_primary_owner)return "Primary owner";const r=String(u.global_role||"");return r.charAt(0).toUpperCase()+r.slice(1)}
function shellTitle(r){
  let [crumb,title]=VIEW_TITLES[r.name];
  if(r.name==="task"&&panelState.task){crumb=`Task · ${panelState.task.project_name||""}`;title=panelState.task.title}
  if(r.name==="project"){const p=(state.projects||[]).find(x=>x.id===r.id);if(p)title=p.name}
  const pid=r.name==="portfolio"&&document.querySelector("#project-filter").value,proj=pid&&state.projects.find(p=>p.id===pid);
  if(proj){crumb="Projects · Portfolio timeline";title=proj.name}
  document.querySelector("#crumb").textContent=crumb;document.querySelector("#page-title").textContent=title;document.title=`${title} · Astra`;
}
// Under the filters: "Showing X of Y" and one removable chip per active filter.
function activeFilters(){
  const chips=[];
  for(const [key,sel] of FILTER_PARAMS){
    const el=document.querySelector(sel);if(key==="sort"||!el.value)continue;
    const label=el.labels&&el.labels[0]?el.labels[0].firstChild.textContent.trim():key;
    const text=(el.selectedOptions&&el.selectedOptions[0]&&el.selectedOptions[0].textContent)||el.value;
    chips.push([key,`${label}: ${text}`]);
  }
  if(document.querySelector("#open-only").checked)chips.push(["open","Open work only"]);
  return chips;
}
function noteFilters(shown){
  const chips=activeFilters(),total=state.tasks.length;
  document.querySelector("#filter-note").innerHTML=chips.length?`<span>Showing <strong>${shown} of ${total}</strong> task${total===1?"":"s"}</span>`+
    chips.map(([key,text])=>`<button type="button" class="filter-chip" data-clear="${key}" aria-label="Remove filter ${escapeHtml(text)}">${escapeHtml(text)}<span aria-hidden="true">×</span></button>`).join("")+
    '<button type="button" class="link" id="clear-filters" data-clear="all">Clear all</button>':"";
}
function clearFilter(key){
  if(key==="all"){clearAllFilters();document.querySelector("#project-filter").focus();return}
  if(key==="open")document.querySelector("#open-only").checked=false;
  else{const f=FILTER_PARAMS.find(([k])=>k===key);if(f)document.querySelector(f[1]).value=""}
  filtersChanged();
  (document.querySelector("#filter-note .filter-chip")||document.querySelector("#project-filter")).focus();
}
// "Show it" after a capture: clear the filters and make sure Home is the screen the link, rail and title show.
function showAllOnPortfolio(){clearAllFilters();if(currentRoute().name!=="portfolio")location.hash="#/portfolio"}
function clearAllFilters(){filtersFromUrl(new URLSearchParams());const sorted=state.sort!=="criticality";state.sort="criticality";syncFilters();shellTitle(currentRoute());if(sorted)load();else render()}
document.querySelector("#filter-note").addEventListener("click",e=>{const b=e.target.closest("[data-clear]");if(b)clearFilter(b.dataset.clear)});
// A short notice at the bottom of the screen. A plain notice fades after 6 seconds; one with an action, or
// one the person must act on by hand (sticky), stays until used or dismissed (WCAG 2.2.1). A notice belongs
// to the screen it was shown on: moving to another screen clears it.
let toastTimer=null,toastView=null;
function clearToast(){clearTimeout(toastTimer);document.querySelector("#toast").innerHTML="";toastView=null}
function showToast(text,actionLabel,action,sticky,ms){
  const box=document.querySelector("#toast");clearTimeout(toastTimer);toastView=currentRoute().name;
  const keep=!!actionLabel||!!sticky;
  box.innerHTML=`<span>${escapeHtml(text)}</span>${actionLabel?`<button type="button" class="link" id="toast-action">${escapeHtml(actionLabel)}</button>`:""}${keep?'<button type="button" class="link" id="toast-dismiss" aria-label="Dismiss">×</button>':""}`;
  if(actionLabel)document.querySelector("#toast-action").addEventListener("click",()=>{clearToast();action()});
  if(keep)document.querySelector("#toast-dismiss").addEventListener("click",clearToast);
  // JN1QYG: an Undo notice lasts exactly as long as its Undo (owner decision: 15 seconds).
  if(ms)toastTimer=setTimeout(clearToast,ms);else if(!keep)toastTimer=setTimeout(clearToast,6000);
}
function applyRoute(moveFocus,fromLoad){
  if(!state.user)return;
  // Links from before the Command Center put the dashboard filters on #/home; they belong to #/portfolio now.
  const old=currentRoute();
  if(old.name==="home"&&[...FILTER_PARAMS.map(([k])=>k),"open"].some(k=>old.params.has(k))&&history.replaceState)
    history.replaceState(null,"",`#/portfolio?${old.params.toString()}`);
  // An unknown project tab shows Overview, and the link says so.
  const pr=currentRoute(),rawPath=String(location.hash||"").replace(/^#\/?/,"").split("?")[0];
  if(pr.name==="project"&&rawPath!==pr.path&&history.replaceState){const q=String(location.hash).indexOf("?");history.replaceState(null,"",`#/${pr.path}${q<0?"":String(location.hash).slice(q)}`)}
  const r=currentRoute(),linked=r.name==="task"?r.id:r.params.get("task"),taskId=isTaskId(linked)?linked:null;
  if(bulk.ids.size&&(r.name!=="project"||r.id!==bulk.pid)){bulk.ids.clear();bulk.last=null}
  renderBulkBar();
  const viewHash=routeHash(r,null),sameView=!fromLoad&&viewHash===panelState.rendered;
  if(r.name!=="task"){panelState.lastView=viewHash;panelState.rendered=viewHash}
  // The first load after sign-in always fetches the task again: nothing rendered earlier is trusted.
  if(taskId&&(taskId!==panelState.shown||(fromLoad&&state.loads===1)))openDetail(taskId);else if(!taskId)closePanel(true);
  else{document.querySelector("#app").classList.toggle("task-page",r.name==="task");syncPanelInert()}
  document.querySelectorAll("[data-view]").forEach(v=>{v.hidden=v.dataset.view!==r.name});
  const nav=NAV_OF[r.name]||r.name;
  document.querySelectorAll("[data-nav]").forEach(a=>{if(a.dataset.nav===nav)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current")});
  if(sameView){shellTitle(r);return}
  if(r.name==="portfolio"){
    filtersFromUrl(r.params);
    const sort=r.params.get("sort")==="due_date"?"due_date":"criticality";
    if(sort!==state.sort){state.sort=sort;load();return}
    setPortfolioLinks(routeHash(r,null));
    render();
  }else if(r.name==="home"){
    renderHome();
    if((state.projects||[]).length)loadHomePortfolio();
    if(isOwner()&&(!fromLoad||state.inboxLoads===undefined))openInbox();
  }else if(r.name==="my-work")renderMyWork(r);
  else if(r.name==="projects")renderProjects();
  else if(r.name==="project")renderProject(r);
  else if(r.name==="inbox"&&(!fromLoad||state.inboxLoads===undefined))openInbox();
  shellTitle(r);
  if(moveFocus&&!taskId)document.querySelector("#page-title").focus();
}
window.addEventListener("hashchange",()=>{closeMenus();if(toastView&&toastView!==currentRoute().name)clearToast();const quiet=panelState.quiet;panelState.quiet=false;applyRoute(!quiet)});
// FKVHH8: My Work has two tabs over the same open work. List groups the tasks you own by when they are
// due; Calendar lays them on a month grid (#/my-work/calendar?month=YYYY-MM&scope=all). "This week" means
// due in the next 7 days, the same rule as Home.
// FKVHH8 (review M1, M2): one "today" and one "this week" for Home, My Work and the calendar. Today is
// the server's date in the app's timezone (/api/tasks "today"), never the browser's clock; each task's
// days_to_due is computed by the server in its project's timezone. "This week" is today through the
// next 7 days, the same span as the "Due in 7 days" tile and its link (?due=7).
const WEEK_AHEAD=7;
function dueThisWeek(t){return t.days_to_due!=null&&t.days_to_due>=0&&t.days_to_due<=WEEK_AHEAD}
function appToday(){return /^\d{4}-\d{2}-\d{2}$/.test(state.today||"")?state.today:dayKey(new Date())}
function utcDay(key,plus=0){return new Date(Date.UTC(+key.slice(0,4),+key.slice(5,7)-1,+key.slice(8,10)+plus))}
function utcKey(d){return d.toISOString().slice(0,10)}
// 3C1Z74: "As of" names the server's date and timezone that due states are counted in. A project's own
// Timeline uses that project's today and timezone (review 11 L2); the portfolio uses the app's.
function ganttToday(){return state.ganttDay&&state.ganttDay.today||appToday()}
function asOfText(){const tz=state.ganttDay?state.ganttDay.timezone:state.timezone;return `Due dates as of ${fmtDay(ganttToday())}${tz?` (${tz})`:""}`}
const WORK_GROUPS=[["overdue","Overdue"],["today","Today"],["week","This week"],["later","Later"],["undated","No date"]];
const WORK_EMPTY={overdue:"Nothing overdue.",today:"Nothing due today.",week:"Nothing due in the next 7 days.",later:"Nothing due later.",undated:"Every task has a due date."};
function workGroup(t){if(t.due_state==="overdue")return "overdue";if(t.due_state==="today")return "today";if(!t.due_date)return "undated";return dueThisWeek(t)?"week":"later"}
function workRow(t){
  const group=workGroup(t);
  return `<li class="work-row"><button type="button" class="link work-title" data-detail="${escapeHtml(t.id)}">${escapeHtml(t.title)}</button>
    <span class="work-meta">${escapeHtml(t.project_name||"")}${t.parent_title?` · step of ${escapeHtml(t.parent_title)}`:""} · ${escapeHtml(statusLabel(t.status))}</span>
    <span class="due-chip" data-due="${group}">${escapeHtml(dueText(t)||"No due date")}</span></li>`;
}
function openWork(scope){
  const me=state.user&&state.user.id;
  return state.tasks.filter(t=>!CLOSED_STATUSES.includes(t.status)&&(scope==="all"||t.owner_user_id===me))
    .sort((a,b)=>String(a.due_date||"9999").localeCompare(String(b.due_date||"9999"))||String(a.title).localeCompare(String(b.title)));
}
// Every group is listed with its count, so an empty Overdue reads as good news rather than a missing heading.
function workGroupsHtml(tasks){
  return WORK_GROUPS.map(([key,label])=>{const rows=tasks.filter(t=>workGroup(t)===key);
    return `<section class="work-group" data-group="${key}"><h3>${label} <span class="count">${rows.length}</span></h3>`+
      (rows.length?`<ul class="work-list">${rows.map(workRow).join("")}</ul>`:`<p class="empty-line">${WORK_EMPTY[key]}</p>`)+"</section>"}).join("");
}
function workMatches(t,q){q=q.trim().toLowerCase();return !q||[t.title,t.project_name,t.parent_title].some(v=>String(v||"").toLowerCase().includes(q))}
function filteredWorkHtml(mine){
  const q=state.workQuery||"",shown=mine.filter(t=>workMatches(t,q));
  return shown.length?workGroupsHtml(shown):`<p class="empty-line">No open work you own matches “${escapeHtml(q.trim())}”.</p>`;
}
function myWorkTabs(r){
  const cal=r.id==="calendar";
  const calHash=cal?routeHash(r,null):state.calendarHash||"#/my-work/calendar";
  return `<nav class="tabs" aria-label="My Work views"><a href="#/my-work"${cal?"":' aria-current="page"'}>List</a><a href="${escapeHtml(calHash)}"${cal?' aria-current="page"':""}>Calendar</a></nav>`;
}
function renderMyWork(r=currentRoute()){
  const body=document.querySelector("#my-work-body");
  if(r.id==="calendar"){state.calendarHash=routeHash(r,null);body.innerHTML=myWorkTabs(r)+workCalendar(r);return}
  const mine=openWork("mine");
  body.innerHTML=myWorkTabs(r)+(mine.length
    ?`<div class="work-head"><h2>Open work you own <span class="count">${mine.length}</span></h2>
      <label class="work-search"><span class="sr-only">Filter my work</span><input type="search" id="my-work-search" placeholder="Filter by task or project" autocomplete="off" value="${escapeHtml(state.workQuery||"")}"></label></div>
      <div id="my-work-groups" aria-live="polite">${filteredWorkHtml(mine)}</div>`
    :`<div class="empty-state"><h2>Nothing is assigned to you</h2><p>Open tasks you own show up here, soonest first.</p><a class="button-link primary" href="#/projects">Browse projects</a></div>`);
}
// The month grid: Monday first, whole weeks, open tasks on their due day. More than 3 in a day fold into
// "+N more", which opens that day in place. The same month is also written as an agenda (days with work
// only); CSS shows the grid on wide screens and the agenda on phones.
const MONTHS=["January","February","March","April","May","June","July","August","September","October","November","December"];
const WEEKDAYS=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
const CAL_LIMIT=3,calExpanded=new Set();
function dayKey(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`}
function monthParam(s){const m=/^(\d{4})-(0[1-9]|1[0-2])$/.exec(s||"");return m?[+m[1],+m[2]-1]:null}
function calHref(year,month,scope){const d=new Date(Date.UTC(year,month,1)),p=new URLSearchParams();p.set("month",utcKey(d).slice(0,7));if(scope==="all")p.set("scope","all");return "#/my-work/calendar?"+p.toString()}
function calTone(t){return t.due_state==="overdue"?"overdue":t.due_state==="today"?"today":t.is_critical_path||t.criticality==="critical"?"critical":""}
function calItem(t){const tone=calTone(t);
  return `<button type="button" class="cal-item" data-detail="${escapeHtml(t.id)}"${tone?` data-tone="${tone}"`:""} title="${escapeHtml(t.title)}">${escapeHtml(t.title)}${tone==="overdue"?'<span class="sr-only"> (overdue)</span>':tone==="critical"?'<span class="sr-only"> (critical)</span>':""}</button>`}
function calendarMonth(tasks,year,month,todayKey,scope){
  const byDay={};
  for(const t of tasks)if(t.due_date){const k=String(t.due_date).slice(0,10);(byDay[k]=byDay[k]||[]).push(t)}
  const rank=t=>(calTone(t)==="overdue"?0:calTone(t)==="critical"?1:2);
  for(const k in byDay)byDay[k].sort((a,b)=>rank(a)-rank(b)||String(a.title).localeCompare(String(b.title)));
  // Dates are built in UTC so the browser's timezone cannot shift a day.
  const first=new Date(Date.UTC(year,month,1)),lead=(first.getUTCDay()+6)%7,days=new Date(Date.UTC(year,month+1,0)).getUTCDate(),weeks=Math.ceil((lead+days)/7);
  const title=`${MONTHS[month]} ${year}`,inMonth=Object.keys(byDay).filter(k=>k.startsWith(utcKey(first).slice(0,8)));
  const count=inMonth.reduce((n,k)=>n+byDay[k].length,0),undated=tasks.filter(t=>!t.due_date).length;
  const cells=[...Array(weeks*7)].map((_,i)=>{
    const d=new Date(Date.UTC(year,month,1-lead+i)),k=utcKey(d),items=byDay[k]||[],out=d.getUTCMonth()!==month,open=calExpanded.has(k);
    const shown=open||items.length<=CAL_LIMIT?items:items.slice(0,CAL_LIMIT);
    const more=items.length>CAL_LIMIT?`<button type="button" class="link cal-more" data-cal-more="${k}" aria-expanded="${open}">${open?"Show fewer":`+${items.length-CAL_LIMIT} more`}</button>`:"";
    return `<li class="cal-day${out?" out":""}${k===todayKey?" today":""}"><p class="cal-date"><span aria-hidden="true">${d.getUTCDate()}</span><span class="sr-only">${WEEKDAYS[(d.getUTCDay()+6)%7]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}${k===todayKey?", today":""}, ${items.length} task${items.length===1?"":"s"}</span></p>${shown.map(calItem).join("")}${more}</li>`;
  }).join("");
  const agenda=inMonth.sort().map(k=>{const d=utcDay(k);
    return `<li><h3 class="agenda-date">${WEEKDAYS[(d.getUTCDay()+6)%7].slice(0,3)} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()].slice(0,3)}${k===todayKey?' <span class="badge" data-level="info">Today</span>':""} <span class="count">${byDay[k].length}</span></h3><ul class="work-list">${byDay[k].map(workRow).join("")}</ul></li>`}).join("");
  const [py,pm]=[year,month-1],[ny,nm]=[year,month+1];
  return `<div class="cal-bar"><h2 class="cal-title" id="cal-title">${title}</h2>
    <nav class="cal-nav" aria-label="Month"><a class="button-link quiet" href="${calHref(py,pm,scope)}"><span aria-hidden="true">‹</span> Previous</a><a class="button-link quiet" href="${calHref(+todayKey.slice(0,4),+todayKey.slice(5,7)-1,scope)}">Today</a><a class="button-link quiet" href="${calHref(ny,nm,scope)}">Next <span aria-hidden="true">›</span></a></nav>
    <label class="cal-scope">Show<select id="cal-scope"><option value="mine"${scope==="all"?"":" selected"}>My tasks</option><option value="all"${scope==="all"?" selected":""}>All tasks I can see</option></select></label></div>
    <p class="fine cal-summary">${count} open task${count===1?"":"s"} due in ${MONTHS[month]}${undated?` · ${undated} with no due date · <a href="#/my-work">See them in List</a>`:""}</p>
    <div class="cal-month" aria-labelledby="cal-title"><div class="cal-weekdays" aria-hidden="true">${WEEKDAYS.map(w=>`<span>${w.slice(0,3)}</span>`).join("")}</div><ol class="cal-grid">${cells}</ol></div>
    <ol class="cal-agenda" aria-labelledby="cal-title">${agenda||`<li><p class="empty-line">Nothing is due in ${title}.</p></li>`}</ol>`;
}
function workCalendar(r){
  const today=appToday(),[y,m]=monthParam(r.params.get("month"))||[+today.slice(0,4),+today.slice(5,7)-1],scope=r.params.get("scope")==="all"?"all":"mine";
  return calendarMonth(openWork(scope),y,m,today,scope);
}
// Projects: every project the person can see; a row opens it on Home (its own workspace comes later).
function renderProjects(){
  const rows=state.projects.map(p=>{
    const tasks=state.tasks.filter(t=>t.project_id===p.id),open=tasks.filter(t=>!CLOSED_STATUSES.includes(t.status)).length,overdue=tasks.filter(t=>t.due_state==="overdue").length;
    const ents=(p.entities||[]).map(e=>e.name).join(", ");
    return `<li><a class="project-row" href="#/project/${encodeURIComponent(p.id)}/overview"><span class="project-name">${escapeHtml(p.name)}${p.status==="closed"?' <span class="badge" data-level="info">Closed</span>':""}</span>
      <span class="work-meta">${ents?escapeHtml(ents)+" · ":""}${open} open task${open===1?"":"s"}${p.target_date?` · target ${escapeHtml(fmtDay(p.target_date))}`:""}</span>
      ${overdue?`<span class="due-chip" data-due="overdue">${overdue} overdue</span>`:""}</a></li>`;
  }).join("");
  document.querySelector("#projects-body").innerHTML=`<h2>Projects <span class="count">${state.projects.length}</span></h2>`+
    (rows?`<ul class="project-list">${rows}</ul>`:`<p class="empty">No projects yet.${state.user&&state.user.global_role==="owner"?" Use New project to start one.":" You see a project once you are added to it."}</p>`);
}
// CR121Z: the Gantt, its schedule table and their listeners live in one #gantt-host. The portfolio and the
// project page move that node into place instead of keeping two copies; view forces chart or table.
function mountGantt(slot,view){const host=document.querySelector("#gantt-host");if(host.parentElement!==slot)slot.appendChild(host);state.viewOverride=view}
function refreshGantt(){const r=currentRoute();if(r.name==="project")renderProject(r);else if(r.name==="portfolio")render()}
// Board columns. Closed statuses win over everything, Submitted over Blocked; see README for the mapping.
const BOARD_COLUMNS=[["draft","Draft"],["ready","Ready"],["progress","In progress"],["blocked","Blocked"],["submitted","Submitted"],["accepted","Accepted"],["closed","Closed"]];
const LOCKED_COLUMNS=["accepted","closed"];
function boardColumn(t){
  if(t.status==="completed")return "accepted";
  if(t.status==="cancelled"||t.status==="abandoned")return "closed";
  if(t.status==="submitted")return "submitted";
  if(t.status==="on_hold"||t.is_blocked)return "blocked";
  if(t.status==="draft")return "draft";
  if(t.status==="assigned")return "ready";
  return "progress";   // in_progress, reopened, changes_requested, delayed
}
const CRIT_ORDER=["critical","high","normal","low",""];
const boardExpanded=new Set();
// JN1QYG: a saved order (board_rank) first, then the list order for cards never ranked.
function byBoardRank(a,b){return (a.board_rank==null)-(b.board_rank==null)||(a.board_rank??0)-(b.board_rank??0)}
function canMoveOnBoard(pid){const p=(state.projects||[]).find(x=>x.id===pid);return !!(p&&p.can_manage)}
// 3FQEKB (Aly 2026-09-26): the Chairman may assign but not otherwise manage; the server decides.
function canAssignIn(pid){const p=(state.projects||[]).find(x=>x.id===pid);return !!(p&&(p.can_manage||p.can_assign))}
function assignOnly(pid){return canAssignIn(pid)&&!canMoveOnBoard(pid)}
// An open task assigned before the assignment rules to the Chairman, or (top level) to a viewer.
function reassignChip(t){return (t&&t.needs_new_assignee?'<span class="tag reassign-chip" data-tone="amber">⚠ Needs a new assignee</span>':"")
  +(t&&t.needs_new_collaborator?'<span class="tag reassign-chip" data-tone="amber">⚠ Collaborator not allowed</span>':"")}
function boardCard(t,kids,movable){
  const done=kids.filter(k=>k.status==="completed").length,col=boardColumn(t),tags=[];
  if(t.is_blocked&&!CLOSED_STATUSES.includes(t.status))tags.push(`<span class="tag" data-tone="purple">⊘ Waits on ${escapeHtml((t.blocked_by&&t.blocked_by[0]&&t.blocked_by[0].title)||"a predecessor")}</span>`);
  if(t.status==="on_hold")tags.push('<span class="tag" data-tone="purple">∥ On hold</span>');
  if(t.status==="delayed")tags.push('<span class="tag" data-tone="amber">Delayed</span>');
  if(t.status==="changes_requested")tags.push('<span class="tag" data-tone="amber">Changes requested</span>');
  if(t.is_critical_path&&!CLOSED_STATUSES.includes(t.status))tags.push('<span class="tag" data-tone="red">◆ Critical path</span>');
  if(col==="accepted")tags.push('<span class="tag" data-tone="green">✓ Accepted</span>');
  if(col==="closed")tags.push(`<span class="tag">× ${escapeHtml(statusLabel(t.status))}</span>`);
  if(t.needs_new_assignee||t.needs_new_collaborator)tags.push(reassignChip(t));
  if(lockedByOther(t))tags.push(`<span class="tag lock-chip" data-tone="amber">🔒 ${escapeHtml(t.lock.holder_name)}<span class="sr-only"> is changing this task</span></span>`);
  const due=CLOSED_STATUSES.includes(t.status)?"":`<span class="due-chip" data-due="${workGroup(t)}">${escapeHtml(dueText(t)||"No due date")}</span>`;
  const id=escapeHtml(t.id),move=movable?`<button type="button" class="link card-move" data-move-menu="${id}" aria-haspopup="menu" aria-expanded="false" aria-controls="move-menu" aria-label="Move “${escapeHtml(t.title)}” to…">Move to…</button>`:"";
  return `<article class="board-card${bulk.ids.has(t.id)?" is-picked":""}"${movable?` data-card="${id}"`:""}>${movable?pickBox(t):""}<button type="button" class="link card-title" data-detail="${id}">${escapeHtml(t.title)}</button>
    <div class="card-meta"><span class="avatar-sm" aria-hidden="true">${escapeHtml(initials(t.owner_name)||"–")}</span><span class="sr-only">Owner: ${escapeHtml(t.owner_name||"Unassigned")}.</span>${due}${t.criticality?`<span class="card-crit">${escapeHtml(t.criticality.charAt(0).toUpperCase()+t.criticality.slice(1))}</span>`:""}</div>
    ${tags.length?`<div class="tags">${tags.join("")}</div>`:""}${kids.length?`<p class="card-steps">Steps ${done} of ${kids.length} done</p>`:""}${move}</article>`;
}
function renderBoard(tasks,divide){
  const ids=new Set(tasks.map(t=>t.id)),top=tasks.filter(t=>!t.parent_task_id||!ids.has(t.parent_task_id)).sort(byBoardRank);
  const kidsOf=id=>tasks.filter(t=>t.parent_task_id===id),movable=!!top.length&&canMoveOnBoard(top[0].project_id);
  // 3C1Z74: owner lanes are keyed by user id, so two people who share a display name get their own lanes.
  const laneKey=divide==="owner"?t=>t.owner_user_id||"":divide==="criticality"?t=>t.criticality||"":()=>"";
  const names=new Map(top.map(t=>[t.owner_user_id||"",t.owner_name||"Unassigned"]));
  let lanes=[...new Set(top.map(laneKey))];
  if(divide==="criticality")lanes.sort((a,b)=>CRIT_ORDER.indexOf(a)-CRIT_ORDER.indexOf(b));
  else if(divide==="owner")lanes.sort((a,b)=>(a===""?1:b===""?-1:names.get(a).localeCompare(names.get(b))||a.localeCompare(b)));
  const nth=k=>{const same=lanes.filter(x=>x&&names.get(x)===names.get(k));return same.length>1?` (${same.indexOf(k)+1} of ${same.length})`:""};
  const laneName=k=>divide==="owner"?(k?names.get(k)+nth(k):"Unassigned"):divide==="criticality"?(k?k.charAt(0).toUpperCase()+k.slice(1):"Unrated"):"";
  const shut=key=>LOCKED_COLUMNS.includes(key)&&!boardExpanded.has(key);
  const count=key=>top.filter(t=>boardColumn(t)===key).length;
  const project=top.length?(state.projects||[]).find(p=>p.id===top[0].project_id):null,limits=(project&&project.wip_limits)||{};
  const countTag=key=>{const n=count(key),max=limits[key];return max?`<span class="count${n>max?" over-limit":n===max?" at-limit":""}">${n} / ${max}<span class="sr-only"> (work-in-progress limit ${max})</span></span>`:`<span class="count">${n}</span>`};
  const head=BOARD_COLUMNS.map(([key,label])=>{
    const locked=LOCKED_COLUMNS.includes(key),inner=`<span class="col-name">${label}</span>${countTag(key)}${locked?(shut(key)?'<span class="col-lock" aria-hidden="true">🔒</span><span class="sr-only">Owner decides; collapsed</span>':'<span class="col-lock">🔒 Owner decides</span>'):""}`;
    return `<div class="col col-head${shut(key)?" is-collapsed":""}" data-col="${key}">${locked?`<button type="button" class="col-toggle" data-toggle-col="${key}" aria-expanded="${!shut(key)}">${inner}</button>`:inner}</div>`;
  }).join("");
  const laneRows=lanes.map(k=>{
    const inLane=top.filter(t=>laneKey(t)===k);
    const cells=BOARD_COLUMNS.map(([key])=>{const cards=inLane.filter(t=>boardColumn(t)===key);
      return `<div class="col${shut(key)?" is-collapsed":""}" data-col="${key}">${shut(key)?(cards.length?`<p class="col-hidden">${cards.length}</p>`:""):cards.map(t=>boardCard(t,kidsOf(t.id),movable)).join("")}</div>`}).join("");
    return `${divide?`<h3 class="lane-head">${escapeHtml(laneName(k))} <span class="count">${inLane.length}</span></h3>`:""}<div class="board-cols">${cells}</div>`;
  }).join("");
  const opts=[["","None"],["owner","Owner"],["criticality","Criticality"]].map(([v,l])=>`<option value="${v}"${v===(divide||"")?" selected":""}>${l}</option>`).join("");
  return `<div class="board-bar"><label class="inline">Divide by <select id="board-divide">${opts}</select></label>${movable&&isOwner()?'<button type="button" class="quiet" id="wip-settings">Limits…</button>':""}
      <span class="work-meta">${top.length} task${top.length===1?"":"s"} · steps show on their parent · ${movable?'<span class="drag-only">drag a card or </span>use Move to…; ordinary moves can be undone for 15 seconds':"read-only for your role"}${movable&&divide?" · Dropping into another lane changes status, not owner.":""}</span></div>
    ${top.length?`<div class="board${LOCKED_COLUMNS.filter(shut).map(k=>" shut-"+k).join("")}" role="region" aria-label="Board" tabindex="0"><div class="board-cols board-head">${head}</div>${laneRows}</div>`
      :'<p class="empty-line">No tasks in this project yet. Use Add a task to start.</p>'}`;
}
function projectOverview(p,tasks){
  const ids=new Set(tasks.map(t=>t.id)),top=tasks.filter(t=>!t.parent_task_id||!ids.has(t.parent_task_id));
  const counted=top.filter(t=>t.status!=="cancelled"&&t.status!=="abandoned"),done=counted.filter(t=>t.status==="completed").length;
  const open=tasks.filter(isOpen),pct=counted.length?Math.round(done/counted.length*100):0;
  const facts=[
    fact("Status",p.status==="closed"?"Closed":p.status==="on_hold"?"On hold":"Active"),
    fact("Agreed start",p.start_date?fmtDay(p.start_date):"Not set"),fact("Agreed deadline",p.target_date?fmtDay(p.target_date):"Not set"),
    fact("Scheduled start",projectSchedule(p).start_date?fmtDay(projectSchedule(p).start_date):"Need task dates"),
    fact("Scheduled finish",projectSchedule(p).finish_date?fmtDay(projectSchedule(p).finish_date):"Need task dates"),
    fact("Open tasks",String(open.length)),fact("Overdue",String(open.filter(t=>t.due_state==="overdue").length)),
    fact("Blocked",String(open.filter(t=>t.is_blocked).length)),fact("Critical path",String(open.filter(t=>t.is_critical_path).length)),
    fact("Timezone",p.timezone||"—"),
  ].join("");
  const next=open.filter(t=>t.due_date).sort((a,b)=>a.due_date.localeCompare(b.due_date)).slice(0,5);
  return `<div class="page-card overview">
    <div class="progress-line"><label for="project-progress">Progress</label><progress id="project-progress" max="100" value="${pct}">${pct}%</progress>
      <span><strong>${done} of ${counted.length}</strong> task${counted.length===1?"":"s"} accepted (${pct}%)</span></div>
    <div class="facts">${facts}</div>
    ${Object.keys(p.schedule_forecasts||{}).some(n=>n!=="Shared")?`<p>Scheduled dates above show the range across plans. Each alternative keeps its own finish:</p><ul>${Object.entries(p.schedule_forecasts).filter(([name])=>name!=="Shared").map(([name,s])=>`<li>${escapeHtml(name)}: ${escapeHtml(s.start_date||"Need dates")} → ${escapeHtml(s.finish_date||"Need dates")}${s.undated_count?" (provisional)":""}</li>`).join("")}</ul>`:projectSchedule(p).undated_count?'<p>Scheduled dates are provisional while some tasks need dates.</p>':""}
    ${p.description?`<p class="desc">${escapeHtml(p.description)}</p>`:""}
    ${p.status==="closed"&&p.closure_note?`<div class="state-note"><p><strong>Closed.</strong> ${escapeHtml(p.closure_note)}</p></div>`:""}
    <h3 class="group-head">Next due</h3>${next.length?`<ul class="home-list">${next.map(t=>homeRow(t,`<span class="due-chip" data-due="${workGroup(t)}">${escapeHtml(dueText(t))}</span>`)).join("")}</ul>`:'<p class="empty-line">No open task has a due date.</p>'}
  </div>`;
}
function renderProject(r){
  const q=s=>document.querySelector(s),p=(state.projects||[]).find(x=>x.id===r.id),body=q("#project-body"),slot=q("#project-gantt-slot");
  q("#project-tabs").innerHTML=p?PROJECT_TABS.map(([k,l])=>`<a href="#/project/${encodeURIComponent(p.id)}/${k}"${k===r.tab?' aria-current="page"':""}>${l}</a>`).join(""):"";
  q("#project-capture").hidden=!p||!canCaptureProject(p);
  q("#project-import").hidden=!p||p.status==="closed"||!(importState.targets?.projects||[]).some(project=>project.id===p.id);
  q("#project-save-template").hidden=!p||!isOwner();
  q("#project-close").hidden=!p||!isOwner()||p.status==="closed";
  q("#project-reopen").hidden=!p||!canReopenProject()||p.status!=="closed";
  slot.hidden=!p||!(r.tab==="list"||r.tab==="timeline");body.hidden=!slot.hidden;
  if(!p){
    q("#project-facts").textContent="";
    body.innerHTML='<div class="card empty-state"><h2>This project is not available</h2><p>It may have been removed, or you are not a member of it.</p><a class="button-link primary" href="#/projects">All projects</a></div>';
    return;
  }
  const tasks=state.tasks.filter(t=>t.project_id===p.id),ents=(p.entities||[]).map(e=>e.name).join(", ");
  q("#project-facts").textContent=[ents,p.status==="closed"?"Closed":null,projectSchedule(p).finish_date?`Scheduled finish ${fmtDay(projectSchedule(p).finish_date)}`:null,p.target_date?`Agreed deadline ${fmtDay(p.target_date)}`:null,(()=>{const ids=new Set(tasks.map(t=>t.id)),steps=tasks.filter(t=>t.parent_task_id&&ids.has(t.parent_task_id)).length,top=tasks.length-steps;
    return `${top} task${top===1?"":"s"}${steps?`, ${steps} step${steps===1?"":"s"}`:""}`})()].filter(Boolean).join(" · ");
  if(!slot.hidden){
    mountGantt(slot,r.tab==="list"||phoneMQ.matches?"table":"chart");
    state.ganttDay=/^\d{4}-\d{2}-\d{2}$/.test(p.today||"")?{today:p.today,timezone:p.timezone||null}:null;
    document.querySelector("#as-of").textContent=asOfText();
    renderBands(tasks);renderGantt(tasks);return;
  }
  if(r.tab==="board")body.innerHTML=`<div class="page-card board-card-wrap">${renderBoard(tasks,r.params.get("divide"))}</div>`;
  else if(r.tab==="activity"){
    body.innerHTML='<div class="page-card"><h2>Activity</h2><p class="muted">Loading…</p></div>';
    api(`/api/projects/${encodeURIComponent(p.id)}/events`).then(({events})=>{
      const now=currentRoute();if(now.name!=="project"||now.id!==p.id||now.tab!=="activity")return;
      const items=(events||[]).slice().reverse().map(renderProjectEvent).join("")||'<li class="muted">No history yet.</li>';
      body.innerHTML=`<div class="page-card"><h2>Activity</h2><p class="fine">Project changes, closures, imports and Owner decisions, newest first. Task history is in each task.</p><div class="history"><ul>${items}</ul></div></div>`;
    }).catch(err=>{body.innerHTML=`<div class="page-card"><p class="error">${escapeHtml(err.message)}</p></div>`});
  }else body.innerHTML=projectOverview(p,tasks);
}
document.querySelector("#project-body").addEventListener("click",e=>{
  if(e.target.closest("#wip-settings"))return openWipSettings(currentRoute().id);
  const t=e.target.closest("[data-toggle-col]");
  if(t){const k=t.dataset.toggleCol;if(boardExpanded.has(k))boardExpanded.delete(k);else boardExpanded.add(k);renderProject(currentRoute());document.querySelector(`[data-toggle-col="${k}"]`)?.focus();return}
  const m=e.target.closest("[data-move-menu]");
  if(m){const menu=document.querySelector("#move-menu");if(!menu.hidden&&menu.dataset.task===m.dataset.moveMenu)closeMoveMenu(true);else openMoveMenu(m);return}
  const b=e.target.closest("[data-detail]");if(b)openDetail(b.dataset.detail);
});
document.querySelector("#project-body").addEventListener("change",e=>{
  if(e.target.id!=="board-divide")return;
  const r=currentRoute(),p=new URLSearchParams(r.params);if(e.target.value)p.set("divide",e.target.value);else p.delete("divide");
  const q=p.toString(),h=`#/${r.path}${q?"?"+q:""}`;if(history.replaceState)history.replaceState(null,"",h);panelState.rendered=routeHash(parseRoute(h),null);
  renderProject(currentRoute());document.querySelector("#board-divide")?.focus();
});
// JN1QYG: governed board drag and drop (owner decisions 2026-09-19: Kanban dragging, protected status
// authority, Undo, touch). The server runs today's rules for every drop; the board only mirrors who may
// move. Mouse and pen drag at once past a small threshold; a finger drags after a deliberate long press on
// tablets (a quick swipe still scrolls); phones use the Move to menu, which is also the keyboard path.
const COL_LABEL=Object.fromEntries(BOARD_COLUMNS);
const drag={card:null};
function boardAnnounce(text){const live=document.querySelector("#board-live");if(live)live.textContent=text}
function columnOrder(pid,column,without){
  const ids=new Set(state.tasks.map(t=>t.id));
  return state.tasks.filter(t=>t.project_id===pid&&(!t.parent_task_id||!ids.has(t.parent_task_id))&&boardColumn(t)===column&&t.id!==without).sort(byBoardRank).map(t=>t.id);
}
async function saveColumnOrder(pid,column,order,undoable){
  const before=columnOrder(pid,column);
  await api(`/api/projects/${encodeURIComponent(pid)}/board-order`,{method:"POST",body:JSON.stringify({column,task_ids:order})});
  if(undoable){
    showToast(`Order saved in ${COL_LABEL[column]}.`,"Undo",async()=>{
      try{await api(`/api/projects/${encodeURIComponent(pid)}/board-order`,{method:"POST",body:JSON.stringify({column,task_ids:before})});showToast("Order restored.")}
      catch(err){showToast(`The order was not restored: ${err.message}`,null,null,true)}
      await load();
    },false,15000);
  }
}
// What a drop onto a column needs from the person first (the reason or record the rules ask for).
function moveDialogKind(t,column){
  if(column==="blocked")return "hold";
  if(column==="closed")return "close";
  if(column==="submitted")return "submit";
  if(column==="accepted"&&t.status==="submitted")return "accept";
  if(BOARD_WORK.has(column)&&CLOSED_STATUSES.includes(t.status))return "reopen";
  return null;
}
const BOARD_WORK=new Set(["draft","ready","progress"]);
function askMove(kind,t,column,err){
  const d=document.querySelector("#move-dialog"),f=document.querySelector("#move-form"),name=`“${escapeHtml(t.title)}”`;
  const today=appToday(),reason=(label,hint)=>`<label>${label}<input name="reason" required autocomplete="off"${hint?` placeholder="${hint}"`:""}></label>`;
  const view={
    hold:["Put on hold",`Moving ${name} to Blocked puts it on hold. The rules ask for a reason, a follow-up checkpoint and who is responsible.`,
      `${reason("Reason")}<div class="grid"><label>Checkpoint date<input name="checkpoint_date" type="date" required min="${today}"></label><label>Responsible<select name="owner_user_id"></select></label></div>`,"Put on hold"],
    close:["Close task",`Closing ${name} needs how it ended and why.`,
      `<fieldset class="choice"><legend>Close as</legend><label><input type="radio" name="status" value="cancelled" checked> Cancelled</label><label><input type="radio" name="status" value="abandoned"> Abandoned</label></fieldset>${reason("Reason")}`,"Close task"],
    reopen:["Reopen task",`Moving ${name} back into work reopens it, with a reason and a revised due date.`,
      `${reason("Reason")}<label>New due date<input name="new_due_date" type="date" required min="${today}"></label>`,"Reopen"],
    submit:["Submit for review",`Submit ${name} for review?`,`<label>Note (optional)<textarea name="note"></textarea></label>`,"Submit"],
    accept:["Accept submission",`Accept the submission of ${name}?`,`<label>Decision note (optional)<textarea name="note"></textarea></label>`,"Accept"],
    impact:["Confirm the new dates",`${err&&err.dates&&err.dates.due_date&&t.due_date?`New dates for ${name}: ${escapeHtml(dateTip(t,err.dates,appliedDays(t,err.dates)))}. `:`New dates for ${name}. `}This change has consequences:`,
      `<ul class="impact-list">${((err&&err.impact)||[]).map(i=>`<li>${escapeHtml(i)}</li>`).join("")}</ul><p class="muted">Tasks that follow are not moved for you. The other owners are told once you confirm.</p>`,"Move anyway"],
    unlock:["Force unlock",`${escapeHtml(err&&err.lock?lockText(err.lock):"")} Unlocking lets others change ${name} now; anything they have not saved will be refused, and they are told.`,
      `<label>Reason (optional)<input name="reason" autocomplete="off"></label>`,"Unlock"],
    wip:["Go over the limit",`${escapeHtml(((err&&err.impact)||[""])[0])} Move ${name} to ${COL_LABEL[column]||"its new column"} anyway? Going over is recorded and the other owners are told.`,"","Move anyway"],
    dependencies:["Override dependency",`${name} waits on ${escapeHtml(((err&&err.impact)||[]).join(", "))}. Move it to ${COL_LABEL[column]||"its new column"} anyway? The override is recorded and the other owners are told.`,"","Move anyway"],
  }[kind];
  f.innerHTML=`<h2 id="move-dialog-title">${view[0]}</h2><p>${view[1]}</p>${view[2]}<div class="error" id="move-error" role="alert"></div><div class="actions"><button type="button" class="quiet" data-move-cancel>Cancel</button><button type="submit">${view[3]}</button></div>`;
  if(kind==="hold")fillAssignees(t.project_id,f.querySelector('select[name="owner_user_id"]'),t.owner_user_id,t.parent_task_id?"subtask":"task",t.owner_name);
  return new Promise(resolve=>{
    let settled=false;const done=v=>{if(settled)return;settled=true;if(d.open)d.close();resolve(v)};
    f.onsubmit=e=>{e.preventDefault();if(kind==="hold"&&f.querySelector('select[name="owner_user_id"]')?.disabled===true){document.querySelector("#move-error").textContent="Load the people list before choosing a responsible owner. Use Retry people.";return}const data=Object.fromEntries(new FormData(f));
      if(kind==="dependencies")return done({override_dependencies:true});
      if(kind==="wip")return done({override_wip:true});
      if(kind==="impact")return done({confirmed:true});
      if(kind==="unlock")return done({reason:data.reason||""});
      if(kind==="submit"||kind==="accept")return done({confirmed:true,note:data.note||""});
      done(data)};
    f.querySelector("[data-move-cancel]").onclick=()=>done(null);
    d.addEventListener("close",()=>done(null),{once:true});
    clearToast();   // review 12b L8: an earlier Undo notice never shows behind the dialog
    d.showModal();(f.querySelector("input:not([type=radio]),textarea")||f.querySelector('button[type="submit"]'))?.focus();
  });
}
async function moveCard(t,column,beforeId=null){
  const pid=t.project_id,from=boardColumn(t),kind=moveDialogKind(t,column),fromOrder=columnOrder(pid,from);
  let extra={};
  if(kind){const answer=await askMove(kind,t,column);if(!answer){boardAnnounce("Move cancelled.");return}extra=answer}
  const send=more=>api(`/api/tasks/${encodeURIComponent(t.id)}/board-move`,{method:"POST",body:JSON.stringify({to_column:column,expected_revision:t.revision,...extra,...more})});
  try{
    // An owner confirms a dependency override and a work-in-progress override, one after the other;
    // a reopen whose new due date has consequences confirms those too (review 12d L1).
    let out,more={};
    for(;;){
      try{out=await send(more);break}
      catch(err){
        const flag=CONFIRM_FLAGS[err.confirm];
        if(err.status!==409||!flag||more[flag])throw err;
        const ok=await askMove(err.confirm,t,column,err);if(!ok){boardAnnounce("Move cancelled.");await load();return}
        more={...more,...ok};
      }
    }
    if(out.request){showToast(`Sent to an owner for approval: “${t.title}” to ${COL_LABEL[column]}.`);await load();return}
    const moved=out.task;Object.assign(t,moved);
    // Review 12a L3: dropped before a card, it takes that place; otherwise the server appends it.
    if(beforeId&&boardColumn(t)===column){
      const order=columnOrder(pid,column,t.id),at=beforeId?order.indexOf(beforeId):-1;
      order.splice(at<0?order.length:at,0,t.id);
      try{await saveColumnOrder(pid,column,order,false)}catch{}
    }
    const landed=boardColumn(t),waits=(t.blocked_by||[]).map(p=>p.title).join(", ");
    const text=(from===column?`Put “${t.title}” on hold.`:`Moved “${t.title}” from ${COL_LABEL[from]} to ${COL_LABEL[column]}.`)+(landed==="blocked"&&column!=="blocked"&&waits?` It shows under Blocked until ${waits} is completed.`:"");
    if(out.undo)showToast(text,"Undo",()=>undoMove(t,out.undo.event_id,from,fromOrder),false,out.undo.seconds*1000);else showToast(text);
    boardAnnounce(text);
  }catch(err){
    const text=err.message.includes(`“${t.title}”`)?`Not moved. ${err.message}`:`“${t.title}” stays in ${COL_LABEL[from]}: ${err.message}`;
    showToast(text,null,null,true);boardAnnounce(text);
  }
  await load();
}
async function undoMove(t,eventId,from,fromOrder){
  try{
    // The column it goes back to may be at its work-in-progress limit: an owner confirms going over it.
    const done=await withConfirms(t,from,more=>api(`/api/tasks/${encodeURIComponent(t.id)}/undo-move`,{method:"POST",body:JSON.stringify({event_id:eventId,...more})}));
    if(!done){showToast("Undo cancelled; the move stands.");await load();return}
    // Put the card back where it was in its column too (best effort: skipped if that column changed meanwhile).
    if(fromOrder&&fromOrder.length>1)try{await api(`/api/projects/${encodeURIComponent(t.project_id)}/board-order`,{method:"POST",body:JSON.stringify({column:from,task_ids:fromOrder})})}catch{}
    showToast(`Move undone: “${t.title}” is back.`)}
  catch(err){showToast(`The move was not undone: ${err.message}`,null,null,true)}
  await load();
}
function cellAt(x,y){const el=document.elementFromPoint(x,y);return el&&el.closest(".board .col[data-col]")}
function clearDropMarks(){document.querySelectorAll(".col.drop-target").forEach(c=>c.classList.remove("drop-target"));document.querySelectorAll(".drop-marker").forEach(m=>m.remove())}
function startDrag(x,y){
  clearTimeout(drag.timer);drag.active=true;
  const r=drag.card.getBoundingClientRect(),ghost=drag.card.cloneNode(true);
  ghost.classList.add("drag-ghost");ghost.setAttribute("aria-hidden","true");ghost.removeAttribute("data-card");ghost.style.width=`${r.width}px`;
  drag.ghost=ghost;drag.ox=x-r.left;drag.oy=y-r.top;document.body.appendChild(ghost);
  drag.card.classList.add("is-dragging");document.body.classList.add("board-dragging");
  try{drag.card.setPointerCapture(drag.pointer)}catch{}
  drag.lease=takeLease(drag.id,"drag");
  if(drag.touch)document.addEventListener("touchmove",holdTouchScroll,{passive:false});
  boardAnnounce(`Dragging “${drag.title}”. Drop it on a column, or press Escape to cancel.`);
  dragTo(x,y);
}
function dragTo(x,y){
  drag.ghost.style.transform=`translate(${Math.round(x-drag.ox)}px,${Math.round(y-drag.oy)}px)`;
  const cell=cellAt(x,y);clearDropMarks();drag.over=cell;drag.before=null;
  if(cell){
    cell.classList.add("drop-target");
    const cards=[...cell.querySelectorAll(".board-card:not(.is-dragging)")],next=cards.find(c=>{const b=c.getBoundingClientRect();return y<b.top+b.height/2});
    drag.before=next?next.dataset.card||null:null;
    if(!cell.classList.contains("col-head")&&!cell.classList.contains("is-collapsed")){const m=document.createElement("div");m.className="drop-marker";cell.insertBefore(m,next||null)}
  }
  const board=document.querySelector(".board");if(board){const b=board.getBoundingClientRect();if(x<b.left+40)board.scrollLeft-=16;else if(x>b.right-40)board.scrollLeft+=16}
}
function endDrag(drop){
  clearTimeout(drag.timer);
  const {active,over,before,id}=drag;
  if(drag.ghost)drag.ghost.remove();
  if(drag.card)drag.card.classList.remove("is-dragging");
  document.body.classList.remove("board-dragging");clearDropMarks();
  document.removeEventListener("touchmove",holdTouchScroll,{passive:false});
  drag.card=null;drag.active=false;drag.ghost=null;
  if(!active)return;
  drag.suppressClick=true;setTimeout(()=>{drag.suppressClick=false},0);
  const t=state.tasks.find(x=>x.id===id),lease=drag.lease;drag.lease=null;
  if(!drop||!over||!t){boardAnnounce("Move cancelled.");lease?.then(()=>dropLease(id,"drag"));return}
  lease.then(got=>{
    if(!got.ok){const text=leaseRefusal(t,got.err);showToast(text,null,null,true);boardAnnounce(text);return load()}
    return Promise.resolve(placeDrop(t,over,before)).finally(()=>dropLease(id,"drag"));
  },()=>placeDrop(t,over,before));
}
function placeDrop(t,over,before){
  const column=over.dataset.col;
  if(column===boardColumn(t)){
    if(over.classList.contains("col-head"))return;
    const was=columnOrder(t.project_id,column),order=columnOrder(t.project_id,column,t.id),at=before?order.indexOf(before):-1;order.splice(at<0?order.length:at,0,t.id);
    if(order.join()===was.join())return;
    return saveColumnOrder(t.project_id,column,order,true).then(load,err=>{showToast(`The order was not saved: ${err.message}`,null,null,true);load()});
  }
  return moveCard(t,column,over.classList.contains("col-head")?null:before);
}
const boardBody=document.querySelector("#project-body");
boardBody.addEventListener("pointerdown",e=>{
  const card=e.target.closest(".board-card[data-card]");
  if(!card||e.button>0||e.target.closest(".card-move,.bulk-pick")||phoneMQ.matches)return;
  Object.assign(drag,{card,id:card.dataset.card,title:card.querySelector(".card-title")?.textContent||"",x:e.clientX,y:e.clientY,pointer:e.pointerId,touch:e.pointerType==="touch",active:false});
  if(drag.touch)drag.timer=setTimeout(()=>startDrag(drag.x,drag.y),450);
});
document.addEventListener("pointermove",e=>{
  if(!drag.card||e.pointerId!==drag.pointer)return;
  if(!drag.active){
    const moved=Math.hypot(e.clientX-drag.x,e.clientY-drag.y);
    if(drag.touch){if(moved>8){clearTimeout(drag.timer);drag.card=null}return}   // a swipe scrolls; it never moves work
    if(moved<6)return;
    startDrag(e.clientX,e.clientY);
  }
  e.preventDefault();dragTo(e.clientX,e.clientY);
});
document.addEventListener("pointerup",e=>{if(drag.card&&e.pointerId===drag.pointer)endDrag(true)});
document.addEventListener("pointercancel",e=>{if(drag.card&&e.pointerId===drag.pointer)endDrag(false)});
// Review 12a L6: the non-passive touchmove listener exists only while a touch drag is active,
// so ordinary scrolling never waits on it.
const holdTouchScroll=e=>e.preventDefault();
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&drag.active){e.preventDefault();endDrag(false)}});
boardBody.addEventListener("click",e=>{if(drag.suppressClick){e.preventDefault();e.stopPropagation()}},true);
// The Move to menu: the same moves from the keyboard, a screen reader or a phone.
function openMoveMenu(btn){
  const menu=document.querySelector("#move-menu"),t=state.tasks.find(x=>x.id===btn.dataset.moveMenu);if(!t)return;
  const col=boardColumn(t),order=columnOrder(t.project_id,col),at=order.indexOf(t.id);
  const items=BOARD_COLUMNS.filter(([k])=>k!==col).map(([k,l])=>`<button type="button" role="menuitem" data-move-to="${k}">Move to ${l}</button>`);
  // Review 12a I1: a card in Blocked only because it waits on a predecessor can still be put on hold.
  if(col==="blocked"&&t.status!=="on_hold")items.unshift('<button type="button" role="menuitem" data-move-to="blocked">Put on hold…</button>');
  if(at>=0&&at<order.length-1)items.unshift('<button type="button" role="menuitem" data-move-to="down">Move down in this column</button>');
  if(at>0)items.unshift('<button type="button" role="menuitem" data-move-to="up">Move up in this column</button>');
  menu.innerHTML=items.join("");menu.dataset.task=t.id;
  closeMenus(menu);menu.hidden=false;btn.setAttribute("aria-expanded","true");drag.menuButton=btn;
  const r=btn.getBoundingClientRect(),w=Math.min(260,(window.innerWidth||1024)-16);
  menu.style.left=`${Math.max(8,Math.min(r.left,(window.innerWidth||1024)-w-8))}px`;menu.style.top=`${Math.min(r.bottom+4,(window.innerHeight||768)-(menu.offsetHeight||0)-8)}px`;
  menu.querySelector('[role="menuitem"]')?.focus();
}
function closeMoveMenu(refocus){const menu=document.querySelector("#move-menu");menu.hidden=true;const b=drag.menuButton;if(b){b.setAttribute("aria-expanded","false");if(refocus&&b.isConnected)b.focus()}}
document.querySelector("#move-menu").addEventListener("click",async e=>{
  const item=e.target.closest("[data-move-to]");if(!item)return;
  const menu=e.currentTarget,t=state.tasks.find(x=>x.id===menu.dataset.task),to=item.dataset.moveTo;closeMoveMenu(false);if(!t)return;
  if(to==="up"||to==="down"){
    const col=boardColumn(t),order=columnOrder(t.project_id,col),at=order.indexOf(t.id),j=to==="up"?at-1:at+1;[order[at],order[j]]=[order[j],order[at]];
    try{await saveColumnOrder(t.project_id,col,order,true)}catch(err){showToast(`The order was not saved: ${err.message}`,null,null,true)}
    await load();document.querySelector(`[data-move-menu="${CSS.escape(t.id)}"]`)?.focus();return;
  }
  await moveCard(t,to);document.querySelector(`[data-move-menu="${CSS.escape(t.id)}"]`)?.focus();
});
document.querySelector("#move-menu").addEventListener("keydown",e=>{
  const list=[...e.currentTarget.querySelectorAll('[role="menuitem"]')],i=list.indexOf(document.activeElement);
  if(e.key==="Escape"){e.preventDefault();e.stopPropagation();closeMoveMenu(true)}
  else if(e.key==="Tab")closeMoveMenu(false);
  else if(e.key==="ArrowDown"||e.key==="ArrowUp"){e.preventDefault();list[(i+(e.key==="ArrowDown"?1:list.length-1))%list.length]?.focus()}
  else if(e.key==="Home"||e.key==="End"){e.preventDefault();list[e.key==="Home"?0:list.length-1]?.focus()}
});
// X07XV4: task locks are renewable leases. A drag or the edit form takes one; it is renewed every
// 20 seconds while in use and released on drop, cancel, save or close. The server refuses anyone
// else's write while a lease lives, and an abandoned one runs out after 60 seconds.
const leases=new Map();
function lockedByOther(t){return !!(t&&t.lock&&state.user&&t.lock.holder_user_id!==state.user.id)}
function lockTime(lock){try{return new Date(lock.expires_at).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"})}catch{return lock.expires_at}}
function lockText(lock){return `${lock.holder_name} is changing this task (${{drag:"a drag",edit:"an edit",bulk:"a bulk change"}[lock.kind]||lock.kind}); their lock runs out at ${lockTime(lock)} unless they keep working.`}
// Review 12b L1: a drag of a task whose edit form you are using borrows that edit lease and
// leaves it alone afterwards; each caller releases only the kind of lease it took.
async function takeLease(id,kind){
  const held=leases.get(id);if(held){held.last=Date.now();return {ok:true,borrowed:held.kind!==kind}}
  try{
    const {lock}=await api(taskApi(id,"/lock"),{method:"POST",body:JSON.stringify({kind})});
    const lease={token:lock.token,kind,last:Date.now(),timer:null};
    lease.timer=setInterval(()=>renewLease(id,lease),20000);
    leases.set(id,lease);return {ok:true};
  }catch(err){if(err.status===409)return {ok:false,err};throw err}
}
async function renewLease(id,lease){
  if(lease.kind==="edit"&&Date.now()-lease.last>60000)return dropLease(id,"edit");   // an idle form lets go
  try{await api(taskApi(id,"/lock/renew"),{method:"POST",body:JSON.stringify({token:lease.token})})}
  catch(err){
    // Review 12b L3: a lease that ran out is not revived by renewing; take a new one, or say so and reload.
    clearInterval(lease.timer);leases.delete(id);
    const again=await takeLease(id,lease.kind).catch(()=>({ok:false,err}));
    if(again.ok)return;
    const why=(again.err&&again.err.lock)?lockText(again.err.lock):"Your lock on this task has ended.";
    showToast(`Your changes to this task are no longer protected: ${why} The task has been reloaded.`,null,null,true);
    if(lease.kind==="edit")showLockBanner(again.err&&again.err.lock,again.err&&again.err.message);
    await load();if(detailTaskId===id&&panelState.shown===id)await openDetail(id);
  }
}
async function dropLease(id,kind){
  const lease=leases.get(id);if(!lease||(kind&&lease.kind!==kind))return;leases.delete(id);clearInterval(lease.timer);
  try{await api(taskApi(id,"/lock/release"),{method:"POST",body:JSON.stringify({token:lease.token})})}catch{}
}
function leaseRefusal(t,err){return err.lock?`Not moved: “${t.title}” is in use. ${lockText(err.lock)} Try again then, or ask an owner to unlock it.`:`Not moved: ${err.message}`}
function touchLease(id){const l=leases.get(id);if(l)l.last=Date.now()}
function lockBanner(lock,message,canForce){
  return `<div class="lock-banner" role="status"><span>🔒 ${escapeHtml(message||lockText(lock))} Your changes wait until then.</span>${canForce?'<button type="button" class="quiet" id="force-unlock">Force unlock</button>':""}</div>`;
}
function showLockBanner(lock,message){
  const slot=document.querySelector("#lock-slot");if(!slot)return;
  slot.innerHTML=lockBanner(lock,message,!!(panelState.task&&panelState.task.permissions&&panelState.task.permissions.can_force_unlock&&lock));
}
async function forceUnlock(task){
  const answer=await askMove("unlock",task,null,{lock:task.lock});if(!answer)return;
  try{await api(taskApi(task.id,"/lock/force"),{method:"POST",body:JSON.stringify(answer)});showToast(`Unlocked “${task.title}”; ${task.lock?task.lock.holder_name:"the holder"} has been told.`)}
  catch(err){showToast(`Not unlocked: ${err.message}`,null,null,true)}
  await refreshDetail(task.id);
}
document.querySelector("#detail-body").addEventListener("click",e=>{if(e.target.closest("#force-unlock")&&panelState.task)forceUnlock(panelState.task)});
// The panel's edit form takes an edit lease as soon as someone types in it.
function wireEditLease(task){
  const form=document.querySelector("#detail-edit");
  if(!form||!task.permissions||!task.permissions.can_edit_ordinary)return;
  let asked=false;
  form.addEventListener("input",async()=>{
    if(leases.has(task.id))return touchLease(task.id);
    if(asked)return;asked=true;
    const got=await takeLease(task.id,"edit");asked=false;
    if(!got.ok)showLockBanner(got.err.lock,got.err.message);
  });
}

// X07XV4: Gantt bars move by dragging (both dates) or by their ends (start or due). Owners and the
// project's managers only; phones and touch use the task panel's date fields. Positions change
// through CSSOM (the CSP forbids inline style attributes); the server decides, and a move with
// consequences asks first.
const gdrag={bar:null};
const DAY=86400000;
function canDragBar(t){return canMoveOnBoard(t.project_id)&&!CLOSED_STATUSES.includes(t.status)&&!!t.due_date&&!phoneMQ.matches}
const iso=ms=>new Date(ms).toISOString().slice(0,10);
const shortDate=v=>new Date(Date.parse(v)).toLocaleDateString(undefined,{day:"numeric",month:"short",timeZone:"UTC"});
function barDates(t,edge,days){
  const due0=Date.parse(t.due_date),start0=t.start_date?Date.parse(t.start_date):null;
  let start=start0,due=due0;
  if(edge==="start")start=Math.min((start0??due0)+days*DAY,due0);
  else if(edge==="end")due=Math.max(due0+days*DAY,start0??-Infinity);
  else{due=due0+days*DAY;if(start0!=null)start=start0+days*DAY}
  return {start_date:start==null?null:iso(start),due_date:iso(due)};
}
function dateTip(t,next,days){
  const parts=[];if(next.start_date&&next.start_date!==t.start_date)parts.push(`Start ${shortDate(next.start_date)}`);
  if(next.due_date!==t.due_date)parts.push(`Due ${shortDate(next.due_date)}`);
  return parts.length?`${parts.join(" · ")} (${days>0?"+":""}${days} day${Math.abs(days)===1?"":"s"})`:"No change";
}
function showDragTip(x,y,text){const tip=document.querySelector("#drag-tip");tip.textContent=text;tip.hidden=false;
  tip.style.left=`${Math.min(x+14,(window.innerWidth||1024)-tip.offsetWidth-8)}px`;tip.style.top=`${Math.max(8,y-40)}px`}
function endBarDrag(){
  const g=gdrag;if(!g.bar)return null;
  g.bar.classList.remove("is-dragging");document.body.classList.remove("bar-dragging");document.querySelector("#drag-tip").hidden=true;
  g.bar.style.left=`${g.l0}px`;g.bar.style.width=`${g.w0}px`;
  if(g.active)gxDragLive(g.t,g.t,null);
  const done={...g};gdrag.bar=null;gdrag.active=false;return done;
}
// Review 12b L8: the tip and toast count the change that will be applied, not the pointer's days.
function appliedDays(t,dates){
  const due=Math.round((Date.parse(dates.due_date)-Date.parse(t.due_date))/DAY);
  const start=dates.start_date&&t.start_date?Math.round((Date.parse(dates.start_date)-Date.parse(t.start_date))/DAY):0;
  return due||start;
}
async function rescheduleTask(t,dates,days){
  days=appliedDays(t,dates);
  const send=more=>api(taskApi(t.id,"/reschedule"),{method:"POST",body:JSON.stringify({...dates,expected_revision:t.revision,...more})});
  try{
    let out;
    try{out=await send({})}
    catch(err){
      if(err.status!==409||err.confirm!=="impact")throw err;
      const ok=await askMove("impact",t,null,{impact:err.impact,dates});if(!ok){announce("Move cancelled.");return}
      out=await send(ok);
    }
    if(out.request){showToast(`Sent to an owner for approval: new dates for “${t.title}”.`);return}
    const text=`Moved “${t.title}”: ${dateTip(t,dates,days)}.`+(out.impact?" The other owners have been told.":"");
    if(out.undo)showToast(text,"Undo",async()=>{
      try{const done=await withConfirms(t,null,more=>api(taskApi(t.id,"/undo-move"),{method:"POST",body:JSON.stringify({event_id:out.undo.event_id,...more})}),{dates:{start_date:t.start_date,due_date:t.due_date}});
        showToast(done?`Dates restored for “${t.title}”.`:"Undo cancelled; the new dates stand.")}
      catch(err){showToast(`The move was not undone: ${err.message}`,null,null,true)}
      await load();
    },false,out.undo.seconds*1000);
    else showToast(text);
    announce(text);
  }catch(err){showToast(`“${t.title}” keeps its dates: ${err.message}`,null,null,true);announce(err.message)}
  finally{await dropLease(t.id,"drag");await load()}
}
const ganttEl=document.querySelector("#gantt");
ganttEl.addEventListener("pointerdown",e=>{
  const bar=e.target.closest("[data-drag]");
  if(!bar||e.button>0||e.pointerType==="touch")return;
  const t=state.tasks.find(x=>x.id===bar.dataset.drag);if(!t||!canDragBar(t))return;
  Object.assign(gdrag,{bar,t,x:e.clientX,pointer:e.pointerId,edge:e.target.closest("[data-edge]")?.dataset.edge||null,
    l0:+bar.dataset.l,w0:+bar.dataset.w,dw:+ganttEl.dataset.day,days:0,active:false,lease:null});
});
document.addEventListener("pointermove",e=>{
  const g=gdrag;if(!g.bar||e.pointerId!==g.pointer)return;
  const dx=e.clientX-g.x;
  if(!g.active){if(Math.abs(dx)<5)return;g.active=true;g.bar.classList.add("is-dragging");document.body.classList.add("bar-dragging");
    try{g.bar.setPointerCapture(g.pointer)}catch{};g.lease=takeLease(g.t.id,"drag")}
  e.preventDefault();
  // Whole days only: the bar snaps to the day grid, and the row's Dates, Length and arrows follow it.
  g.days=Math.round(dx/g.dw);
  g.next=barDates(g.t,g.edge,g.days);
  // The bar is placed from the dates it would get, cut to the shown period as gxRender cuts it, so a
  // bar that runs past an edge, or has a due date only, shows exactly what the drop will save.
  const box=gxBarBox(g.t,g.next)||{left:g.l0,width:g.w0},left=box.left,width=box.width;
  g.bar.style.left=`${left}px`;g.bar.style.width=`${width}px`;
  gxDragLive(g.t,g.next,left,width);showDragTip(e.clientX,e.clientY,dateTip(g.t,g.next,appliedDays(g.t,g.next)));
});
document.addEventListener("pointerup",async e=>{
  if(!gdrag.bar||e.pointerId!==gdrag.pointer)return;
  const g=endBarDrag();if(!g.active)return;
  gdrag.suppressClick=true;setTimeout(()=>{gdrag.suppressClick=false},0);
  const got=await g.lease;
  if(got&&!got.ok){showToast(leaseRefusal(g.t,got.err),null,null,true);return load()}
  if(!g.days||(g.next.start_date===g.t.start_date&&g.next.due_date===g.t.due_date)){await dropLease(g.t.id,"drag");return}
  await rescheduleTask(g.t,g.next,g.days);
});
document.addEventListener("pointercancel",e=>{if(gdrag.bar&&e.pointerId===gdrag.pointer){const g=endBarDrag();if(g&&g.active)g.lease?.then(()=>dropLease(g.t.id,"drag"))}});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&gdrag.active){e.preventDefault();const g=endBarDrag();announce("Move cancelled.");g.lease?.then(()=>dropLease(g.t.id,"drag"))}});
ganttEl.addEventListener("click",e=>{if(gdrag.suppressClick){e.preventDefault();e.stopPropagation()}},true);
// XV92JJ: bulk changes. On a project's Board and List, owners and the project's managers tick tasks
// (Shift-click for a range, Space to toggle, Shift+Arrow to extend in the list), then change status,
// assignee or due dates for all of them in one previewed, all-or-nothing, undoable change.
const bulk={ids:new Set(),pid:null,last:null,action:"status"};
// Review 13a L1: someone who may only assign (the Chairman) selects in the List, never on the board.
function bulkScope(){const r=currentRoute();return r.name==="project"&&r.id&&(canMoveOnBoard(r.id)||(canAssignIn(r.id)&&r.tab==="list"))?r.id:null}
function pickBox(t){return `<input type="checkbox" class="bulk-pick" data-pick="${escapeHtml(t.id)}"${bulk.ids.has(t.id)?" checked":""} aria-label="Select “${escapeHtml(t.title)}”">`}
function syncPicks(){
  document.querySelectorAll("[data-pick]").forEach(b=>{const on=bulk.ids.has(b.dataset.pick);b.checked=on;b.closest(".board-card,tr")?.classList.toggle("is-picked",on)});
  const all=document.querySelector("[data-pick-all]"),boxes=[...document.querySelectorAll("[data-pick]")];
  if(all){all.checked=boxes.length>0&&boxes.every(b=>b.checked);all.indeterminate=!all.checked&&boxes.some(b=>b.checked)}
  renderBulkBar();
}
function clearBulk(){bulk.ids.clear();bulk.last=null;syncPicks()}
function pick(id,on){if(on)bulk.ids.add(id);else bulk.ids.delete(id)}
// Shift-click: everything between the last box ticked and this one, in the order shown.
function pickRange(order,from,to){const i=order.indexOf(from),j=order.indexOf(to);if(i<0||j<0)return [to];return order.slice(Math.min(i,j),Math.max(i,j)+1)}
document.addEventListener("click",e=>{
  const box=e.target.closest("[data-pick]");if(!box)return;
  const pid=bulkScope();if(!pid)return;
  if(bulk.pid!==pid){bulk.ids.clear();bulk.pid=pid}
  const id=box.dataset.pick,boxes=[...document.querySelectorAll("[data-pick]")].map(b=>b.dataset.pick);
  (e.shiftKey&&bulk.last?pickRange(boxes,bulk.last,id):[id]).forEach(x=>pick(x,box.checked));
  bulk.last=id;syncPicks();
});
document.addEventListener("change",e=>{
  if(!e.target.matches("[data-pick-all]"))return;
  const pid=bulkScope();if(!pid)return;if(bulk.pid!==pid){bulk.ids.clear();bulk.pid=pid}
  document.querySelectorAll("[data-pick]").forEach(b=>pick(b.dataset.pick,e.target.checked));syncPicks();
});
document.addEventListener("keydown",e=>{
  const box=e.target.closest&&e.target.closest("[data-pick]");if(!box||!e.shiftKey||(e.key!=="ArrowDown"&&e.key!=="ArrowUp"))return;
  e.preventDefault();
  const boxes=[...document.querySelectorAll("[data-pick]")],next=boxes[boxes.indexOf(box)+(e.key==="ArrowDown"?1:-1)];
  if(!next)return;const pid=bulkScope();if(bulk.pid!==pid){bulk.ids.clear();bulk.pid=pid}
  pick(box.dataset.pick,true);pick(next.dataset.pick,true);bulk.last=next.dataset.pick;next.focus();syncPicks();
});
function renderBulkBar(){
  const bar=document.querySelector("#bulk-bar"),n=bulk.ids.size,pid=bulkScope();
  if(!n||!pid){bar.hidden=true;bar.innerHTML="";document.body.classList.remove("has-bulk-bar");return}
  if(bar.hidden||!bar.innerHTML){
    // 3FQEKB: the Chairman's bulk change is Assign only.
    const only=assignOnly(pid);if(only)bulk.action="assignee";
    bar.innerHTML=`<span class="bulk-count" id="bulk-count"></span>
      <label class="bulk-field"><span class="bulk-label">Change</span><select id="bulk-action">${only?'<option value="assignee">Assignee</option>':'<option value="status">Status</option><option value="assignee">Assignee</option><option value="due_shift">Due dates</option>'}</select></label>
      <span id="bulk-value" class="bulk-field"></span>
      <button type="button" id="bulk-review">Review change…</button>
      <button type="button" class="quiet" id="bulk-clear">Clear selection</button>`;
    bar.querySelector("#bulk-action").value=bulk.action;fillBulkValue(pid);
    bar.querySelector("#bulk-action").addEventListener("change",e=>{bulk.action=e.target.value;fillBulkValue(pid)});
    bar.querySelector("#bulk-review").addEventListener("click",()=>reviewBulk(pid));
    bar.querySelector("#bulk-clear").addEventListener("click",()=>{clearBulk();document.querySelector("[data-pick]")?.focus()});
    bar.hidden=false;document.body.classList.add("has-bulk-bar");
  }
  // Review 12c I1: say when some of the selection is hidden by the current filters.
  const shown=new Set([...document.querySelectorAll("[data-pick]")].map(b=>b.dataset.pick)),hidden=[...bulk.ids].filter(id=>!shown.has(id)).length;
  bar.querySelector("#bulk-count").textContent=`${n} selected`+(hidden?` · ${hidden} hidden by filters`:"");
}
function fillBulkValue(pid){
  const slot=document.querySelector("#bulk-value");
  if(bulk.action==="status")slot.innerHTML='<label><span class="bulk-label">to</span><select id="bulk-input"><option value="draft">Draft</option><option value="ready">Ready</option><option value="progress">In progress</option></select></label>';
  else if(bulk.action==="assignee"){slot.innerHTML='<label><span class="bulk-label">to</span><select id="bulk-input"><option value="">Unassigned</option></select></label>';fillAssignees(pid,slot.querySelector("select"),"")}
  else slot.innerHTML='<label><span class="bulk-label">by</span><input id="bulk-input" type="number" min="-365" max="365" step="1" value="7" inputmode="numeric"><span>days</span></label>';
}
function bulkPayload(){
  const raw=document.querySelector("#bulk-input").value;
  return {task_ids:[...bulk.ids],action:bulk.action,value:bulk.action==="due_shift"?Number(raw):raw};
}
async function reviewBulk(pid){
  if(bulk.action==="assignee"&&document.querySelector("#bulk-input").disabled===true){showToast("Load the people list before reviewing assignments. Use Retry people.",null,null,true);return}
  const payload=bulkPayload();
  let plan;
  try{({preview:plan}=await api(`/api/projects/${encodeURIComponent(pid)}/bulk/preview`,{method:"POST",body:JSON.stringify(payload)}))}
  catch(err){showToast(`Cannot change these tasks: ${err.message}`,null,null,true);return}
  const answer=await askBulk(plan);if(!answer)return;
  if(answer.drop){plan.blocked.forEach(b=>bulk.ids.delete(b.id));syncPicks();if(bulk.ids.size)return reviewBulk(pid);return}
  try{
    // The reviewed preview is the confirmation of its schedule consequences (review 12c L5).
    const out=await api(`/api/projects/${encodeURIComponent(pid)}/bulk/apply`,{method:"POST",body:JSON.stringify({...payload,
      expected_revisions:Object.fromEntries(plan.ok.map(i=>[i.id,i.revision])),override_wip:!!answer.override_wip,confirmed:plan.impact.length>0})});
    const n=out.tasks.length,text=`Changed ${n} task${n===1?"":"s"}: ${out.summary}.`;
    clearBulk();
    showToast(text,"Undo",async()=>{
      try{const u=await api(`/api/projects/${encodeURIComponent(pid)}/bulk/undo`,{method:"POST",body:JSON.stringify({bulk_id:out.bulk_id})});showToast(`Bulk change undone for ${u.tasks.length} task${u.tasks.length===1?"":"s"}.`)}
      catch(err){showToast(`The bulk change was not undone: ${err.message}`,null,null,true)}
      await load();
    },false,out.undo.seconds*1000);
    boardAnnounce(text);
  }catch(err){showToast(/nothing was changed/i.test(err.message)?err.message:`Nothing was changed: ${err.message}`,null,null,true)}
  await load();
}
function askBulk(plan){
  const d=document.querySelector("#move-dialog"),f=document.querySelector("#move-form");
  const list=(items,fn)=>`<ul class="bulk-list">${items.slice(0,8).map(fn).join("")}${items.length>8?`<li class="muted">and ${items.length-8} more</li>`:""}</ul>`;
  const total=plan.counts.ok+plan.counts.blocked,blocked=plan.blocked.length,wip=plan.wip;
  const okPart=plan.ok.length?`<p>${plan.counts.ok} of ${total} task${total===1?"":"s"} will change: <strong>${escapeHtml(plan.summary)}</strong>.</p>${list(plan.ok,i=>`<li>${escapeHtml(i.title)}</li>`)}`:`<p>None of the ${total} selected tasks can change: <strong>${escapeHtml(plan.summary)}</strong>.</p>`;
  const blockedPart=blocked?`<h3>Blocked (${blocked})</h3><p class="muted">Nothing changes until these are out of the selection.</p>${list(plan.blocked,b=>`<li><strong>${escapeHtml(b.title)}</strong> ${escapeHtml(b.reason)}</li>`)}`:"";
  const wipPart=wip?`<div class="lock-banner"><span>${escapeHtml(wip.message)}</span></div>${wip.can_override?'<label class="check"><input type="checkbox" name="override_wip"> Go over the limit (recorded; the other owners are told)</label>':""}`:"";
  const impactPart=plan.impact.length?`<h3>Schedule consequences</h3>${list(plan.impact,i=>`<li><strong>${escapeHtml(i.title)}</strong>: ${escapeHtml(i.impact.join(" "))}</li>`)}<p class="muted">Tasks that follow are not moved. The other owners are told.</p>`:"";
  const canApply=!blocked&&plan.ok.length&&!(wip&&!wip.can_override);
  f.innerHTML=`<h2 id="move-dialog-title">Review bulk change</h2>${okPart}${blockedPart}${wipPart}${impactPart}<div class="error" id="move-error" role="alert"></div>
    <div class="actions"><button type="button" class="quiet" data-move-cancel>Cancel</button>${blocked?'<button type="button" data-bulk-drop>Remove blocked from selection</button>':""}${canApply?`<button type="submit">Apply to ${plan.counts.ok} task${plan.counts.ok===1?"":"s"}</button>`:""}</div>`;
  return new Promise(resolve=>{
    let settled=false;const done=v=>{if(settled)return;settled=true;if(d.open)d.close();resolve(v)};
    f.onsubmit=e=>{e.preventDefault();
      if(wip&&!f.querySelector('[name="override_wip"]')?.checked){f.querySelector("#move-error").textContent="Tick “Go over the limit” to apply, or change fewer tasks.";return}
      done({override_wip:!!wip})};
    f.querySelector("[data-move-cancel]").onclick=()=>done(null);
    const drop=f.querySelector("[data-bulk-drop]");if(drop)drop.onclick=()=>done({drop:true});
    d.addEventListener("close",()=>done(null),{once:true});
    d.showModal();(f.querySelector('button[type="submit"],[data-bulk-drop]')||f.querySelector("[data-move-cancel]")).focus();
  });
}
// XV92JJ: an owner sets each open column's work-in-progress limit (empty for none).
const WIP_COLUMNS=["draft","ready","progress","blocked","submitted"];
async function openWipSettings(pid){
  const p=(state.projects||[]).find(x=>x.id===pid),limits=(p&&p.wip_limits)||{};
  const d=document.querySelector("#move-dialog"),f=document.querySelector("#move-form");
  f.innerHTML=`<h2 id="move-dialog-title">Work-in-progress limits</h2><p>A move that would put more tasks in a column than its limit is refused; only an owner may go over it, and that is recorded. Leave a box empty for no limit.</p>
    <div class="grid wip-grid">${WIP_COLUMNS.map(k=>`<label>${COL_LABEL[k]}<input name="${k}" type="number" min="1" max="999" step="1" inputmode="numeric" value="${limits[k]??""}"></label>`).join("")}</div>
    <label>Reason (optional)<input name="reason" autocomplete="off"></label>
    <div class="error" id="move-error" role="alert"></div><div class="actions"><button type="button" class="quiet" data-move-cancel>Cancel</button><button type="submit">Save limits</button></div>`;
  f.querySelector("[data-move-cancel]").onclick=()=>d.close();
  f.onsubmit=async e=>{
    e.preventDefault();const data=Object.fromEntries(new FormData(f));
    const changed=WIP_COLUMNS.filter(k=>String(limits[k]??"")!==String(data[k]||""));
    if(!changed.length){d.close();showToast("No limits changed.");return}
    // Review 12c L6: every column in one request and one transaction; whole numbers only.
    try{
      await api(`/api/projects/${encodeURIComponent(pid)}/wip-limits`,{method:"POST",body:JSON.stringify({limits:Object.fromEntries(changed.map(k=>[k,data[k]||null])),reason:data.reason})});
      d.close();showToast(`Saved ${changed.length} limit${changed.length===1?"":"s"}.`);await load();
    }catch(err){f.querySelector("#move-error").textContent=err.message}
  };
  d.showModal();f.querySelector("input")?.focus();
}
document.querySelector("#project-capture").addEventListener("click",()=>openCapture(currentRoute().id));
document.querySelector("#project-save-template").addEventListener("click",()=>saveProjectAsTemplate(currentRoute().id));
document.querySelector("#project-close").addEventListener("click",()=>closeProject(currentRoute().id));
// VPYGY5: the Command Center. Everything is drawn from what is already loaded (tasks, projects, the Owner's
// cached requests) plus /api/portfolio; each count links to the list behind it, and rows open the task panel.
function isOwner(){return !!state.user&&state.user.global_role==="owner"}
function canReopenProject(){return isOwner()}
function isOpen(t){return !CLOSED_STATUSES.includes(t.status)}
function hhmm(){return new Date().toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}
function homeTiles(){
  const open=(state.tasks||[]).filter(isOpen),n=f=>open.filter(f).length;
  return [
    ["overdue","Overdue","red",n(t=>t.due_state==="overdue"),"#/portfolio?due=overdue&open=1","Open work past its due date"],
    ["blocked","Blocked","purple",n(t=>t.is_blocked),"#/portfolio?risk=blocked&open=1","Open work waiting on an unfinished predecessor"],
    isOwner()&&["awaiting","Awaiting Owner","amber",(state.ownerRequests||[]).length,"#/inbox","Requests only you can decide"],
    ["week","Due in 7 days","blue",n(dueThisWeek),"#/portfolio?due=7&open=1","Open work due today or in the next 7 days"],
    ["critical","Critical path","red",n(t=>t.is_critical_path),"#/portfolio?risk=critical&open=1","Open tasks with no slack on a project's critical path"],
    ["undated","Undated","gray",n(t=>t.due_state==="undated"),"#/portfolio?due=undated&open=1","Open tasks and steps without a due date"],
    // 3FQEKB: owners and managers see how many of their tasks need a new assignee, when any do.
    ...reassignTile(open),
  ].filter(Boolean);
}
function reassignTile(open){
  const mine=open.filter(t=>(t.needs_new_assignee||t.needs_new_collaborator)&&canMoveOnBoard(t.project_id));
  return mine.length?[["reassign","Needs reassigning","amber",mine.length,"#/portfolio?risk=reassign&open=1","Open tasks whose assignee or a collaborator is the Chairman, or a viewer on a top-level task"]]:[];
}
function homeRow(t,chip){
  return `<li class="home-row"><button type="button" class="link row-title" data-detail="${escapeHtml(t.id)}">${escapeHtml(t.title)}</button>
    <span class="work-meta">${escapeHtml(t.project_name||"")} · ${escapeHtml(t.owner_name||"Unassigned")}</span>${chip}</li>`;
}
function riskChip(t){
  if(t.due_state==="overdue")return `<span class="tag" data-tone="red">▲ ${escapeHtml(dueText(t))}</span>`;
  if(t.is_blocked)return `<span class="tag" data-tone="purple">⊘ Blocked</span>`;
  if(t.is_critical_path)return `<span class="tag" data-tone="red">◆ Critical path</span>`;
  return `<span class="tag" data-tone="amber">Delayed</span>`;
}
function riskRank(t){return t.due_state==="overdue"?0:t.is_blocked?1:t.is_critical_path?2:3}
function renderHome(){
  const box=id=>document.querySelector(id),owner=isOwner(),tasks=state.tasks||[],projects=state.projects||[];
  const empty=!projects.length;
  box("#home-empty").hidden=!empty;box("#home-strip").hidden=box("#home-grid").hidden=box("#home-portfolio-card").hidden=box("#home-gantt-link").hidden=empty;
  if(empty){
    box("#home-empty").innerHTML=`<div class="card empty-state"><h2>No projects yet</h2>${owner
      ?'<p>Start a project to see its health, decisions and deadlines here.</p><a class="button-link primary" href="#/projects">Go to Projects</a>'
      :"<p>You will see work here once the App Owner adds you to a project.</p>"}</div>`;
  }
  box("#home-asof").textContent=empty?"":`Counts as of ${hhmm()}`;
  box("#home-strip").innerHTML=homeTiles().map(([key,label,tone,count,href,def])=>
    `<a class="tile" data-tile="${key}" data-tone="${tone}" href="${href}"><strong>${count}</strong><span class="tile-label">${escapeHtml(label)}</span><span class="tile-def">${escapeHtml(def)}</span></a>`).join("");
  // Needs Owner decision: owners only, with the live Approve / Reject of the Inbox.
  box("#home-decisions-card").hidden=!owner||empty;
  if(owner){
    const reqs=state.ownerRequests||[],shown=reqs.slice(0,5);
    box("#home-decisions").innerHTML=shown.length?`<ul class="home-list">${shown.map(r=>`<li class="decision-row">
      <span class="avatar-sm" aria-hidden="true">${escapeHtml(initials(r.requested_by_name))}</span>
      <div class="decision-main"><strong>${escapeHtml(requestTitle(r))}</strong>
        <span class="work-meta">${escapeHtml(r.requested_by_name||"")} · ${escapeHtml(r.project_name||"")} · ${escapeHtml(new Date(r.requested_at).toLocaleString())}${r.reason?` · “${escapeHtml(r.reason)}”`:""}</span>${requestGates(r)}</div>
      <div class="decision-actions">${r.task_id?`<button type="button" class="quiet" data-detail="${escapeHtml(r.task_id)}">Review</button>`:""}<button type="button" data-home-decision="approved" data-request-id="${escapeHtml(r.id)}">Approve</button><button type="button" class="quiet" data-home-decision="rejected" data-request-id="${escapeHtml(r.id)}">Reject</button></div></li>`).join("")}</ul>${reqs.length>shown.length?`<p class="fine"><a href="#/inbox">${reqs.length-shown.length} more in the Inbox</a></p>`:""}`
      :'<p class="empty-line">Nothing is waiting for your decision.</p>';
  }
  // My next actions: my open work, soonest first, grouped Today (overdue and today) / This week / Later.
  const me=state.user&&state.user.id,mine=tasks.filter(t=>t.owner_user_id===me&&isOpen(t))
    .sort((a,b)=>String(a.due_date||"9999").localeCompare(String(b.due_date||"9999")));
  const when=t=>t.due_state==="overdue"||t.due_state==="today"?"Today":dueThisWeek(t)?"This week":"Later";
  const next=mine.slice(0,7);
  box("#home-next").innerHTML=next.length?["Today","This week","Later"].map(g=>{const rows=next.filter(t=>when(t)===g);
    return rows.length?`<h3 class="group-head">${g}</h3><ul class="home-list">${rows.map(t=>homeRow(t,`<span class="due-chip" data-due="${workGroup(t)}">${escapeHtml(dueText(t)||"No due date")}</span>`)).join("")}</ul>`:""}).join("")+
    (mine.length>next.length?`<p class="fine"><a href="#/my-work">${mine.length-next.length} more in My Work</a></p>`:"")
    :'<p class="empty-line">Nothing is assigned to you. Tasks you own show up here, soonest first.</p>';
  // At risk: overdue, blocked, critical path or delayed, worst first.
  const risk=tasks.filter(t=>isOpen(t)&&isAtRisk(t)).sort((a,b)=>riskRank(a)-riskRank(b)||(a.days_to_due??9999)-(b.days_to_due??9999));
  box("#home-risk").innerHTML=risk.length?`<ul class="home-list">${risk.slice(0,6).map(t=>homeRow(t,riskChip(t))).join("")}</ul>${risk.length>6?`<p class="fine"><a href="#/portfolio?risk=atrisk&amp;open=1">${risk.length-6} more at risk</a></p>`:""}`
    :'<p class="empty-line">Nothing is overdue, blocked, delayed or on the critical path.</p>';
  // This week: open items due today and on each of the next 7 days, labelled from the server's today;
  // the bars add up to the "Due in 7 days" tile.
  const today=appToday(),days=[...Array(WEEK_AHEAD+1)].map((_,i)=>({i,d:utcDay(today,i),n:tasks.filter(t=>isOpen(t)&&t.days_to_due===i).length}));
  const peak=Math.max(1,...days.map(x=>x.n)),total=days.reduce((a,x)=>a+x.n,0);
  box("#home-week").innerHTML=`<p class="fine week-note">Today and the next ${WEEK_AHEAD} days · ${total} open item${total===1?"":"s"} due</p><ol class="week-strip">${days.map(({i,d,n})=>`<li class="week-day${i===0?" is-today":""}"><span class="week-bar" data-h="${Math.round(n/peak*4)}" aria-hidden="true"></span><strong>${n}</strong><span>${i===0?"Today":`${WEEKDAYS[(d.getUTCDay()+6)%7].slice(0,3)} ${d.getUTCDate()}`}</span><span class="sr-only"> open item${n===1?"":"s"} due${i===0?"":` ${WEEKDAYS[(d.getUTCDay()+6)%7]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`}</span></li>`).join("")}</ol>`;
  if(!empty)box("#home-portfolio").innerHTML=state.portfolio?portfolioCards(state.portfolio):'<p class="fine">Loading…</p>';
}
// Portfolio by entity: one renderer for the Home card and the More-menu dialog. Home fetches it once per
// visit (applyRoute), so the Inbox refresh that redraws Home does not fetch it again.
function portfolioCards(portfolio){
  return (portfolio||[]).length?`<div class="entity-cards">${portfolio.map(b=>{
    const budgets=Object.entries(b.budgets||{}).map(([c,a])=>`<span>${escapeHtml(c)} <strong>${Number(a).toLocaleString()}</strong></span>`).join("")||'<span class="muted">No budget set</span>';
    return `<div class="entity-card"><h3>${escapeHtml(b.entity_name)}</h3><p class="work-meta">${b.project_count} project${b.project_count===1?"":"s"} · ${b.open} open · ${b.overdue} overdue · ${b.critical} critical</p><div class="entity-budget">${budgets}</div></div>`}).join("")}</div>
    <p class="fine">Each project is counted once, under its primary entity. Budgets are per currency, never blended.</p>`
    :'<p class="empty-line">No projects are filed under an entity yet.</p>';
}
async function loadHomePortfolio(){
  try{const {portfolio}=await api("/api/portfolio");state.portfolio=portfolio||[];if(currentRoute().name==="home")document.querySelector("#home-portfolio").innerHTML=portfolioCards(state.portfolio)}
  catch(err){document.querySelector("#home-portfolio").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
}
document.querySelector("#home-view").addEventListener("click",e=>{
  const d=e.target.closest("[data-home-decision]");if(d){decideOwnerRequest(d.dataset.requestId,d.dataset.homeDecision,"home-decision-error");return}
  const b=e.target.closest("[data-detail]");if(b)openDetail(b.dataset.detail);
});
document.querySelector("#my-work-body").addEventListener("click",e=>{
  const more=e.target.closest("[data-cal-more]");
  if(more){const k=more.dataset.calMore;if(calExpanded.has(k))calExpanded.delete(k);else calExpanded.add(k);renderMyWork();document.querySelector(`[data-cal-more="${k}"]`)?.focus?.();return}
  const b=e.target.closest("[data-detail]");if(b)openDetail(b.dataset.detail);
});
// The filter box stays put while the groups under it redraw, so typing never loses focus.
document.querySelector("#my-work-body").addEventListener("input",e=>{
  if(e.target.id!=="my-work-search")return;
  state.workQuery=e.target.value;document.querySelector("#my-work-groups").innerHTML=filteredWorkHtml(openWork("mine"));
});
document.querySelector("#my-work-body").addEventListener("change",e=>{
  if(e.target.id!=="cal-scope")return;
  const r=currentRoute(),today=appToday(),[y,m]=monthParam(r.params.get("month"))||[+today.slice(0,4),+today.slice(5,7)-1];
  location.hash=calHref(y,m,e.target.value);
});
// Capture: the task form with the optional fields folded away; the Home project filter is preselected.
function openCapture(pidArg){
  const r=currentRoute(),pid=typeof pidArg==="string"?pidArg:r.name==="project"?r.id:r.name==="portfolio"?document.querySelector("#project-filter").value:"";
  const form=document.querySelector("#task-form"),project=form.querySelector('select[name="project_id"]');
  if(!state.projects.some(canCaptureProject)||(pid&&!state.projects.some(p=>p.id===pid&&canCaptureProject(p)))){showToast("You can add tasks only to an open project you manage.");return}
  if(pid&&[...project.options].some(o=>o.value===pid))project.value=pid;
  fillPredecessors();fillCaptureAssignees();
  form.querySelector(".error").textContent="";
  document.querySelector("#task-dialog").showModal();
}
// Menus (More, account): a button with aria-expanded and a list of menuitems. Arrow keys move, Escape
// closes and gives focus back to the button, a click outside closes, and choosing an item closes it first.
function closeMenus(except){document.querySelectorAll(".menu:not([hidden])").forEach(m=>{if(m===except)return;m.hidden=true;
  // Every card's Move to button controls #move-menu; the one that opened it is the one to reset (review 12a L6).
  const b=m.id==="move-menu"?drag.menuButton:document.querySelector(`[aria-controls="${m.id}"]`);if(b)b.setAttribute("aria-expanded","false")})}
function wireMenu(buttonId){
  const btn=document.querySelector(buttonId),menu=document.querySelector("#"+btn.getAttribute("aria-controls"));
  const items=()=>[...menu.querySelectorAll('[role="menuitem"]')].filter(i=>!i.hidden);
  const open=focusFirst=>{closeMenus(menu);menu.hidden=false;btn.setAttribute("aria-expanded","true");if(focusFirst)items()[0]?.focus()};
  const close=refocus=>{menu.hidden=true;btn.setAttribute("aria-expanded","false");if(refocus)btn.focus()};
  btn.addEventListener("click",e=>menu.hidden?open(e.detail===0):close(false));
  btn.addEventListener("keydown",e=>{if(e.key==="ArrowDown"){e.preventDefault();open(true)}});
  menu.addEventListener("click",e=>{if(e.target.closest('[role="menuitem"]'))close(true)},true);
  menu.addEventListener("keydown",e=>{
    const list=items(),i=list.indexOf(document.activeElement);
    if(e.key==="Escape"){e.preventDefault();e.stopPropagation();close(true)}
    else if(e.key==="Tab")close(false);
    else if(["ArrowDown","ArrowUp","Home","End"].includes(e.key)&&list.length){e.preventDefault();
      const next=e.key==="Home"?0:e.key==="End"?list.length-1:(i+(e.key==="ArrowDown"?1:-1)+list.length)%list.length;list[next].focus()}
  });
}
wireMenu("#more-btn");wireMenu("#user-menu-btn");
// The skip link moves focus without touching the hash, which the router owns.
document.querySelector("#skip-link").addEventListener("click",e=>{e.preventDefault();document.querySelector("#main").focus()});
document.addEventListener("click",e=>{if(!e.target.closest(".menu-wrap,.move-menu,[data-move-menu]"))closeMenus()});
document.addEventListener("keydown",e=>{if(e.key!=="Escape")return;const menu=document.querySelector(".menu:not([hidden])");if(!menu)return;
  const btn=document.querySelector(`[aria-controls="${menu.id}"]`),held=menu.contains(document.activeElement)||document.activeElement===btn;e.preventDefault();closeMenus();if(held&&btn)btn.focus()});
// Ctrl/Cmd+K jumps to search. There are no page-wide single-key shortcuts (WCAG 2.1.4); j/k work only while
// focus is inside the task panel. The account menu lists the keys.
function focusSearch(){const box=document.querySelector("#search-box");box.focus();box.select()}
document.addEventListener("keydown",e=>{
  if(state.user&&(e.ctrlKey||e.metaKey)&&!e.altKey&&String(e.key).toLowerCase()==="k"){e.preventDefault();focusSearch()}
});
document.querySelector("#keys-btn").addEventListener("click",()=>document.querySelector("#keys-dialog").showModal());
document.querySelector("#login-form").addEventListener("submit",async e=>{e.preventDefault();try{const data=await api("/api/login",{method:"POST",body:JSON.stringify({email:e.target.querySelector("#email").value,password:e.target.querySelector("#password").value})});Object.assign(state,data)}catch(err){document.querySelector("#login-error").textContent=err.message;return}e.target.querySelector("#password").value="";showSignedInState();if(!state.user.must_change_password)await loadOrSay()});
// H1: after signing out, reload the page so nothing the previous person saw (Inbox, requests, an open task,
// loaded tasks) survives for the next person on this browser. The hash is dropped too.
function signedOut(){state.user=state.csrf=null;state.dailyDigest=null;state.dailyDigestDate=null;state.dailyDigestError="";location.replace(location.pathname)}
document.querySelector("#logout").onclick=async()=>{await api("/api/logout",{method:"POST",body:"{}"});signedOut()};
document.querySelector("#logout-all").onclick=async()=>{await api("/api/logout-all",{method:"POST",body:"{}"});signedOut()};
async function changePasswordFromForm(form,errorElement,forced){
  const values=Object.fromEntries(new FormData(form));
  errorElement.textContent="";errorElement.classList.remove("is-info");
  if(values.new_password!==values.confirm_password){errorElement.textContent="The new passwords do not match.";return}
  try{
    const data=await api("/api/password/change",{method:"POST",body:JSON.stringify({current_password:values.current_password,new_password:values.new_password})});
    state.user=data.user;form.reset();
    if(forced){showApp();await loadOrSay()}
    else{document.querySelector("#password-change-dialog").close();showToast("Password changed. Other signed-in sessions were signed out.")}
  }catch(err){errorElement.textContent=err.message}
}
document.querySelector("#forced-password-form").addEventListener("submit",e=>{e.preventDefault();changePasswordFromForm(e.currentTarget,document.querySelector("#forced-password-error"),true)});
document.querySelector("#forced-password-logout").onclick=async()=>{await api("/api/logout",{method:"POST",body:"{}"});signedOut()};
document.querySelector("#change-password").onclick=()=>{document.querySelector("#user-menu").hidden=true;document.querySelector("#user-menu-btn").setAttribute("aria-expanded","false");document.querySelector("#password-change-error").textContent="";document.querySelector("#password-change-dialog").showModal()};
document.querySelector("#password-change-cancel").onclick=()=>document.querySelector("#password-change-dialog").close();
document.querySelector("#password-change-form").addEventListener("submit",e=>{e.preventDefault();changePasswordFromForm(e.currentTarget,document.querySelector("#password-change-error"),false)});
document.querySelector("#close-project").onclick=()=>closeProject(document.querySelector("#project-filter").value);
document.querySelector("#project-reopen").onclick=()=>openProjectAction("reopen",currentRoute().id);
function openProjectAction(action,pid){
  const dialog=document.querySelector("#project-action-dialog"),form=document.querySelector("#project-action-form");
  form.dataset.action=action;form.dataset.projectId=pid;form.reset();
  document.querySelector("#project-action-title").textContent=action==="reopen"?"Reopen project":"Close project";
  document.querySelector("#project-action-reason-label").firstChild.textContent=action==="reopen"?"Reason":"Closure note";
  document.querySelector("#project-action-exceptional-label").hidden=action!=="close";
  document.querySelector("#project-action-submit").textContent=action==="reopen"?"Reopen project":"Close project";
  form.querySelector(".error").textContent="";dialog.showModal();
}
function reopenProject(pid){openProjectAction("reopen",pid)}
function closeProject(pid){if(!pid){alert("Select a single project in the filter to close it.");return}openProjectAction("close",pid)}
document.querySelector("#project-action-form").addEventListener("submit",async e=>{
  e.preventDefault();const form=e.target;
  const action=form.dataset.action,pid=form.dataset.projectId,reason=form.elements.reason.value.trim();
  try{await api(action==="reopen"?`/api/projects/${pid}/reopen`:`/api/projects/${pid}/close`,{method:"POST",body:JSON.stringify(action==="reopen"?{reason}:{note:reason,exceptional:form.elements.exceptional.checked})});form.closest("dialog").close();await load();if(action==="reopen")showToast("Project reopened.")}
  catch(err){form.querySelector(".error").textContent=err.message}
});
// PZTYC9: a filter change rewrites the Home link (replaceState, so Back leaves the screen) and re-renders.
for(const id of ["project-filter","status-filter","entity-filter","crit-filter","band-filter","risk-filter"]){document.querySelector(`#${id}`).onchange=filtersChanged}document.querySelector("#open-only").onchange=filtersChanged;document.querySelector("#owner-filter").oninput=filtersChanged;
// QY0WG2: changing the sort re-fetches the list in the chosen server-side order.
document.querySelector("#sort-filter").onchange=e=>{state.sort=e.target.value;syncFilters();load()};
document.querySelector("#new-project").onclick=()=>document.querySelector("#project-dialog").showModal();document.querySelector("#new-task").onclick=openCapture;
document.querySelector("#portfolio-btn").onclick=openPortfolio;
// 5WZ4A8: project history (schedule changes, closure, imports, owner-action decisions).
// ZSZ9T2/K62ZAP: the server sends only schedule changes, closure and their own events to anyone
// other than the Owner, the Chairman or a project manager.
const PROJECT_EVENT_LABELS={board_reordered:"Board order changed",bulk_change:"Bulk change",bulk_change_undone:"Bulk change undone",wip_limit_changed:"Work-in-progress limit changed",wip_limit_override:"Work-in-progress limit overridden",project_schedule_changed:"Project dates changed",project_closed:"Project closed",project_reopened:"Project reopened",project_working_days_changed:"Working days changed",project_holiday_changed:"Project holiday changed",project_budget_changed:"Project budget changed",project_entities_changed:"Project entities changed",project_primary_entity_changed:"Primary entity changed",import_committed:"Import committed",protected_action_blocked:"Owner action blocked",protected_action_approved:"Owner request approved",protected_action_rejected:"Owner request rejected",protected_action_cancelled:"Owner request cancelled"};
document.querySelector("#project-history-btn").onclick=()=>{const pid=document.querySelector("#project-filter").value;if(pid)openProjectHistory(pid)};
async function openProjectHistory(projectId){
  const body=document.querySelector("#project-history-body"),project=state.projects.find(p=>p.id===projectId)||{};
  try{
    const {events}=await api(`/api/projects/${projectId}/events`);
    const items=events.slice().reverse().map(renderProjectEvent).join("")||"<li>No history yet.</li>";
    body.innerHTML=`<h2>Project history · ${escapeHtml(project.name||"")}</h2>
      <p class="muted">Every change to the project's dates is logged here with who made it, the old and new dates, and the reason. Newest first.</p>
      <div class="history"><ul>${items}</ul></div>`;
  }catch(err){body.innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
  const d=document.querySelector("#project-history-dialog");if(!d.open)d.showModal();
}
function renderProjectEvent(ev){
  const when=new Date(ev.occurred_at).toLocaleString(),who=ev.actor_name||"Unknown";
  const label=PROJECT_EVENT_LABELS[ev.event_type]||ev.event_type;
  let detail="";
  if(ev.event_type==="project_schedule_changed"){
    const d=safeParse(ev.detail_json),b=d.before||{},a=d.after||{};
    detail=[["start_date","Start date"],["target_date","Target date"]]
      .filter(([k])=>String(b[k]??"")!==String(a[k]??""))
      .map(([k,l])=>`<br>${escapeHtml(l)}: ${escapeHtml(b[k]||"—")} → ${escapeHtml(a[k]||"—")}`).join("");
  }
  if(ev.event_type==="bulk_change"||ev.event_type==="bulk_change_undone"){
    const d=safeParse(ev.detail_json),n=(d.tasks||[]).length;
    detail=`<br>${n} task${n===1?"":"s"}: ${escapeHtml((d.tasks||[]).map(t=>t.title).join(", "))}`;
  }
  if(!detail&&ev.detail_json){const d=safeParse(ev.detail_json),b=d.before,a=d.after;if(b&&a)detail=`<br>${escapeHtml(JSON.stringify(b))} → ${escapeHtml(JSON.stringify(a))}`;}
  if(ev.event_type==="wip_limit_changed"){const d=safeParse(ev.detail_json);detail=`<br>${escapeHtml(COL_LABEL[d.column]||d.column)}: ${escapeHtml(String(d.before??"none"))} → ${escapeHtml(String(d.after??"none"))}`}
  const reason=ev.reason?`<br><em>Reason: ${escapeHtml(ev.reason)}</em>`:"";
  return `<li><strong>${escapeHtml(label)}</strong> · ${escapeHtml(when)} · ${escapeHtml(who)}${reason}${detail}</li>`;
}
async function openPortfolio(){
  try{
    const {portfolio}=await api("/api/portfolio");state.portfolio=portfolio||[];
    document.querySelector("#portfolio-body").innerHTML=`<h2>Portfolio by entity</h2>${portfolioCards(state.portfolio)}`;
    const d=document.querySelector("#portfolio-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#portfolio-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#portfolio-dialog").showModal()}
}
document.querySelector("#templates-btn").onclick=openTemplates;
document.querySelector("#save-template-btn").onclick=()=>saveProjectAsTemplate();
async function openTemplates(){
  try{
    const {templates}=await api("/api/templates");
    renderTemplates(templates);
    const d=document.querySelector("#templates-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#templates-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#templates-dialog").showModal()}
}
function renderTemplates(templates){
  templatePicker.templates=templates||[];
  const rows=(templates||[]).map(t=>`<li><strong>${escapeHtml(t.name)}</strong> · <span class="muted">${escapeHtml(t.kind)} · ${t.task_count} task(s)${(t.roles||[]).length?` · roles: ${escapeHtml(t.roles.map(r=>TEMPLATE_ROLE_LABELS[r]||r).join(", "))}`:""}</span>
    ${t.description?`<br><em class="muted">${escapeHtml(t.description)}</em>`:""}
    <br><button type="button" class="link" data-use-template="${escapeHtml(t.id)}" data-kind="${escapeHtml(t.kind)}" data-roles="${escapeHtml((t.roles||[]).join(","))}">Use</button>
    <button type="button" class="link" data-delete-template="${escapeHtml(t.id)}">Delete</button></li>`).join("")||"<li>No templates yet. Save a project or a task as a template to reuse it.</li>";
  document.querySelector("#templates-body").innerHTML=`<h2>Templates</h2>
    <p class="fine">A template copies structure — titles, hierarchy, dependencies, criticality, attachment links, relative dates and a suggested owner <em>role</em> (App Owner, Project manager, member, or viewer for steps), never a named person. The Chairman is never an assignee, so a task last owned by the Chairman carries no suggestion. Never status, history or evidence. New tasks start in draft. When you use a template you pick who fills each role; a role you leave on automatic goes to its only holder on the target project, otherwise the task stays unassigned.</p>
    <ul class="people-list">${rows}</ul><div class="error" id="templates-error"></div>`;
  document.querySelectorAll("#templates-body [data-use-template]").forEach(b=>b.addEventListener("click",()=>useTemplate(b.dataset.useTemplate,b.dataset.kind,(b.dataset.roles||"").split(",").filter(Boolean))));
  document.querySelectorAll("#templates-body [data-delete-template]").forEach(b=>b.addEventListener("click",()=>deleteTemplate(b.dataset.deleteTemplate)));
}
async function saveProjectAsTemplate(pid=document.querySelector("#project-filter").value){
  if(!pid){alert("Pick a single project in the Project filter first, then save it as a template.");return}
  const name=prompt("Template name:");if(!name)return;
  const description=prompt("Template description (optional):")||"";
  try{await api("/api/templates/from-project",{method:"POST",body:JSON.stringify({project_id:pid,name,description})});alert("Saved as a template.");await openTemplates()}
  catch(x){alert(x.message)}
}
// 8B9NBH: templates carry suggested owner ROLES; the Owner picks a person per role when using one.
const TEMPLATE_ROLE_LABELS={owner:"App Owner",chairman:"Chairman",manager:"Project manager",member:"Project member",viewer:"Project viewer"};
async function useTemplate(id,kind,roles){
  const template=(templatePicker.templates||[]).find(t=>t.id===id);
  const name=template?.name||"Template",project=kind==="project";
  const body=document.querySelector("#templates-body");
  body.innerHTML=`<form id="template-role-form"><h2>Use ${escapeHtml(name)}</h2>
    <p class="fine">Copy the task structure into ${project?"a new project":"an existing project"}. History, evidence and accepted baselines are not copied.</p>
    ${project?'<label>New project name<input name="name" required></label>':`<label>Target project<select name="project_id" id="template-project" required><option value="">Choose a project…</option>${state.projects.filter(p=>p.status!=="closed").map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("")}</select></label><label>Part of task (optional)<select name="parent_task_id" id="template-parent"><option value="">Top-level task</option></select></label>`}
    <label>Schedule starts on (optional)<input name="anchor_date" type="date"></label>
    <p class="field-hint">Leave the schedule date blank to set dates later in Astra.</p>
    <h3>Responsible people</h3><div id="template-role-fields"><p role="status">Loading people…</p></div>
    <div class="actions"><button type="button" class="quiet" id="template-role-back">Back</button><button type="submit" id="template-create" disabled>Create ${project?"project":"tasks"}</button></div>
    <div class="error" id="templates-error" role="alert"></div></form>`;
  const form=document.querySelector("#template-role-form"),create=document.querySelector("#template-create");
  let ready=false,roleVersion=0;
  document.querySelector("#template-role-back").addEventListener("click",openTemplates);
  const populate=async()=>{
    const version=++roleVersion;ready=false;create.disabled=true;
    const pid=project?null:form.querySelector('[name="project_id"]').value;
    if(!project){document.querySelector("#template-parent").innerHTML='<option value="">Top-level task</option>'+state.tasks.filter(t=>t.project_id===pid).map(t=>`<option value="${escapeHtml(t.id)}">${escapeHtml(t.title)}</option>`).join("")}
    try{
      if(!project&&!pid){document.querySelector("#template-role-fields").innerHTML='<p class="field-hint">Choose a project to see its people.</p>';return}
      const {users}=await api(project?"/api/users":`/api/assignable-users?project_id=${encodeURIComponent(pid)}&for=reviewer`);
      if(version!==roleVersion||!form.isConnected)return;
      renderRolePicker(kind,roles,users);
      ready=true;create.disabled=false;document.querySelector("#templates-error").textContent="";
    }catch(err){if(version!==roleVersion||!form.isConnected)return;document.querySelector("#templates-error").textContent=`People could not be loaded. ${err.message}`;document.querySelector("#template-role-fields").innerHTML='<button type="button" id="template-people-retry">Retry people</button>';document.querySelector("#template-people-retry").addEventListener("click",populate)}
  };
  document.querySelector("#template-project")?.addEventListener("change",populate);
  form.addEventListener("submit",async ev=>{
    ev.preventDefault();if(!ready)return;
    const data=Object.fromEntries(new FormData(form)),role_assignments={};
    for(const role of roles)if(role!=="owner"&&data['role_'+role])role_assignments[role]=data['role_'+role];
    const payload=project?{name:data.name,anchor_date:data.anchor_date||null,role_assignments}
      :{project_id:data.project_id,parent_task_id:data.parent_task_id||null,anchor_date:data.anchor_date||null,role_assignments};
    create.disabled=true;
    try{await api(`/api/templates/${encodeURIComponent(id)}/${project?"create-project":"create-task"}`,{method:"POST",body:JSON.stringify(payload)});document.querySelector("#templates-dialog").close();await load();showToast(project?"Project created from template.":"Tasks created from template.")}
    catch(err){if(form.isConnected){document.querySelector("#templates-error").textContent=err.message;create.disabled=false}}
  });
  await populate();form.querySelector("input,select")?.focus();
}
const templatePicker={templates:[]};
function renderRolePicker(kind,roles,users){
  const active=(users||[]).filter(u=>u.active==null||!!u.active),project=kind==="project";
  const fallback=project?"Leave unassigned":"Automatic (only eligible person, otherwise unassigned)";
  const rows=roles.filter(r=>r!=="chairman").map(r=>{
    const label=escapeHtml(TEMPLATE_ROLE_LABELS[r]||r);
    if(r==="owner")return `<p class="field-hint">App Owner: ${escapeHtml(state.user.display_name)}</p>`;
    const people=active.filter(u=>project?u.global_role==="member":u.project_role===r&&u.global_role!=="chairman");
    const options=people.map(u=>`<option value="${escapeHtml(u.id)}">${escapeHtml(personLabel(u,people))}</option>`).join("");
    return `<label>${label}<select name="role_${escapeHtml(r)}"><option value="">${escapeHtml(fallback)}</option>${options}</select></label>`;
  }).join("");
  document.querySelector("#template-role-fields").innerHTML=rows||'<p class="field-hint">No suggested roles. New tasks will be unassigned.</p>';
}
async function markFinalResult(taskId,sourceType,sourceId){
  try{await api("/api/final-results",{method:"POST",body:JSON.stringify({task_id:taskId,source_type:sourceType,source_id:sourceId})});await refreshDetail(taskId)}
  catch(x){alert(x.message)}
}
async function unmarkFinalResult(taskId,resultId){
  try{await api("/api/final-results",{method:"DELETE",body:JSON.stringify({result_id:resultId})});await refreshDetail(taskId)}
  catch(x){alert(x.message)}
}
async function saveTaskAsTemplate(taskId){
  const name=prompt("Template name for this task subtree:");if(!name)return;
  const description=prompt("Template description (optional):")||"";
  try{await api("/api/templates/from-task",{method:"POST",body:JSON.stringify({task_id:taskId,name,description})});alert("Saved as a task template.")}
  catch(x){alert(x.message)}
}
async function deleteTemplate(id){
  if(!confirm("Delete this template? This does not affect any project or task already created from it."))return;
  try{await api("/api/templates",{method:"DELETE",body:JSON.stringify({template_id:id})});await openTemplates()}
  catch(x){const e=document.querySelector("#templates-error");if(e)e.textContent=x.message}
}
document.querySelector("#final-results-btn").onclick=()=>openFinalResults();
async function openFinalResults(filters={}){
  try{
    const q=new URLSearchParams();for(const k in filters){if(filters[k])q.set(k,filters[k])}
    const {results}=await api("/api/final-results"+(q.toString()?"?"+q:""));
    renderFinalResults(results,filters);
    const d=document.querySelector("#final-results-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#final-results-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#final-results-dialog").showModal()}
}
function renderFinalResults(results,filters){
  const projOpts=state.projects.map(p=>`<option value="${escapeHtml(p.id)}"${filters.project_id===p.id?" selected":""}>${escapeHtml(p.name)}</option>`).join("");
  const entOpts=(state.entities||[]).map(e=>`<option value="${escapeHtml(e.id)}"${filters.entity_id===e.id?" selected":""}>${escapeHtml(e.name)}</option>`).join("");
  const rows=(results||[]).map(r=>{
    const where=r.source_type!=="attachment"?`accepted submission v${escapeHtml(String(r.submission_version||""))}`
      :r.attachment_kind==="file"?`<a href="/api/tasks/${encodeURIComponent(r.task_id)}/attachments/${encodeURIComponent(r.attachment_id)}/download" download>${escapeHtml(r.attachment_path||"")}</a>`
      :r.attachment_kind==="link"?`<a href="${escapeHtml(r.attachment_path||"")}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.attachment_path||"")}</a>`
      :r.attachment_path?`<code class="att-path">${escapeHtml(r.attachment_path)}</code>`:`Local file link, not available on this server.`;
    const ents=(r.entities||[]).join(", ")||"—";
    return `<tr><td><strong>${escapeHtml(r.title)}</strong><br><small class="muted">${where}</small></td>
      <td>${escapeHtml(r.source_type)}</td>
      <td><button type="button" class="link" data-detail="${escapeHtml(r.task_id)}">${escapeHtml(r.task_title)}</button><br><small class="muted">${escapeHtml(r.project_name)} · ${escapeHtml(ents)}</small></td>
      <td><small>${escapeHtml(new Date(r.marked_at).toLocaleDateString())}</small></td></tr>`;
  }).join("")||`<tr><td colspan="4">No final results yet. Mark an accepted submission or an attachment as a final result.</td></tr>`;
  document.querySelector("#final-results-body").innerHTML=`<h2>Final results</h2>
    <p class="fine">Curated deliverables across your projects. Every final result is marked by hand — an accepted submission or an attachment. Acceptance alone does not add one.</p>
    <div class="add-dep" id="fr-filters">
      <select id="fr-project"><option value="">All projects</option>${projOpts}</select>
      <select id="fr-entity"><option value="">All entities</option>${entOpts}</select>
      <select id="fr-type"><option value="">All types</option><option value="submission"${filters.type==="submission"?" selected":""}>Submissions</option><option value="attachment"${filters.type==="attachment"?" selected":""}>Attachments</option></select>
      <label class="inline">Marked from<input id="fr-from" type="date" value="${escapeHtml(filters.from||"")}"></label>
      <label class="inline">to<input id="fr-to" type="date" value="${escapeHtml(filters.to||"")}"></label>
      <input id="fr-q" placeholder="Search title" value="${escapeHtml(filters.q||"")}">
      <button type="button" id="fr-apply">Filter</button>
      <button type="button" id="fr-export" class="quiet">Export CSV</button>
    </div>
    <table class="fr-table"><thead><tr><th>Result</th><th>Type</th><th>Task / project</th><th>Marked</th></tr></thead><tbody>${rows}</tbody></table>`;
  const collect=()=>({project_id:document.querySelector("#fr-project").value,entity_id:document.querySelector("#fr-entity").value,type:document.querySelector("#fr-type").value,from:document.querySelector("#fr-from").value,to:document.querySelector("#fr-to").value,q:document.querySelector("#fr-q").value});
  document.querySelector("#fr-apply").onclick=()=>openFinalResults(collect());
  document.querySelector("#fr-export").onclick=()=>{const f=collect();const p=new URLSearchParams();for(const k in f){if(f[k])p.set(k,f[k])}p.set("format","csv");const a=document.createElement("a");a.href="/api/final-results?"+p.toString();a.download="";document.body.appendChild(a);a.click();a.remove()};
  document.querySelectorAll("#final-results-body [data-detail]").forEach(b=>b.addEventListener("click",()=>{document.querySelector("#final-results-dialog").close();openDetail(b.dataset.detail)}));
}
document.querySelector("#export-btn").onclick=()=>{
  const p=new URLSearchParams();
  const map={project_id:"#project-filter",status:"#status-filter",entity_id:"#entity-filter",criticality:"#crit-filter",band:"#band-filter",risk:"#risk-filter",owner:"#owner-filter",sort:"#sort-filter"};
  for(const k in map){const v=document.querySelector(map[k]).value;if(v)p.set(k,v)}
  if(document.querySelector("#open-only").checked)p.set("open_only","1");
  p.set("format","csv");
  const a=document.createElement("a");a.href="/api/export?"+p.toString();a.download="";document.body.appendChild(a);a.click();a.remove();
};
document.querySelector("#search-box").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();openSearch(e.target.value)}});
async function openSearch(q){
  if(!q.trim())return;
  try{
    const {results}=await api(`/api/search?q=${encodeURIComponent(q)}`);
    const tasks=(results.tasks||[]).map(t=>`<li><button type="button" class="link" data-detail="${escapeHtml(t.id)}">${escapeHtml(t.title)}</button> · ${escapeHtml(t.status)} · <span class="muted">${escapeHtml(t.project_name)}</span></li>`).join("")||"<li>No matching tasks.</li>";
    const projects=(results.projects||[]).map(p=>`<li><a href="#/project/${encodeURIComponent(p.id)}/overview">${escapeHtml(p.name)}</a></li>`).join("")||"<li>No matching projects.</li>";
    document.querySelector("#search-body").innerHTML=`<h2>Search: ${escapeHtml(q)}</h2><h3>Tasks</h3><ul class="people-list">${tasks}</ul><h3>Projects</h3><ul class="people-list">${projects}</ul>`;
    document.querySelectorAll("#search-body [data-detail]").forEach(b=>b.addEventListener("click",()=>{document.querySelector("#search-dialog").close();openDetail(b.dataset.detail)}));
    document.querySelectorAll("#search-body a").forEach(a=>a.addEventListener("click",()=>document.querySelector("#search-dialog").close()));
    const d=document.querySelector("#search-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#search-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#search-dialog").showModal()}
}
document.querySelector('#task-form select[name="project_id"]').onchange=()=>{fillPredecessors();fillCaptureAssignees()};
// 3FQEKB: a viewer is offered only once the new task has a parent (a subtask).
function fillCaptureAssignees(){
  const form=document.querySelector("#task-form"),owner=form.querySelector('select[name="owner_user_id"]');
  fillAssignees(form.querySelector('select[name="project_id"]').value,owner,owner.value,form.querySelector('select[name="parent_task_id"]').value?"subtask":"task");
}
document.querySelector('#task-form select[name="parent_task_id"]').onchange=fillCaptureAssignees;
document.querySelector("#people").onclick=openPeople;
async function openInbox(){
  try{
    const [data,ownerQueue]=await Promise.all([
      api("/api/notifications"),
      state.user.global_role==="owner"?api("/api/owner-action-requests"):Promise.resolve({requests:[]}),
    ]);
    state.notifications=data.notifications;state.unread=data.unread;state.notificationsKnown=true;state.notificationsStale=false;updateBell();
    renderInbox(data.notifications,ownerQueue.requests);
    if(currentRoute().name==="home")renderHome();   // Home shows the same cached requests
  }catch(err){state.notificationsStale=true;updateBell();document.querySelector("#inbox-body").innerHTML=`<p class="error" role="alert">Notifications could not be refreshed. ${escapeHtml(err.message)}</p><button type="button" id="inbox-retry">Retry notifications</button>`;document.querySelector("#inbox-retry").addEventListener("click",openInbox)}
}
// FKVHH8: the Inbox has tabs. Needs action (Owners) holds the requests waiting for a decision; Unread and All
// hold notifications, grouped by day. An Owner lands on Needs action while anything waits there, anyone
// else on Unread while anything is unread. Opening a notification's task marks it read; nothing else does.
const INBOX_TABS=[["needs","Needs action"],["unread","Unread"],["all","All"]];
function inboxTab(items,requests){
  const owner=isOwner(),asked=currentRoute().params.get("tab"),tabs=INBOX_TABS.map(([k])=>k).filter(k=>k!=="needs"||owner);
  if(tabs.includes(asked))return asked;
  return owner&&requests.length?"needs":items.some(n=>!n.read_at)?"unread":owner?"needs":"all";
}
function noteDay(iso){
  const d=new Date(iso),today=new Date(),y=new Date();y.setDate(today.getDate()-1);
  return dayKey(d)===dayKey(today)?"Today":dayKey(d)===dayKey(y)?"Yesterday":"Earlier";
}
function noteRow(n){
  const unread=!n.read_at,when=new Date(n.created_at).toLocaleString([], {day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"});
  const open=n.kind==="daily_digest"&&n.digest_date?`<button type="button" class="link" data-digest-date="${escapeHtml(n.digest_date)}">View summary</button>`:n.task_id?`<button type="button" class="link" data-detail="${escapeHtml(n.task_id)}"${unread?` data-read-on-open="${escapeHtml(n.id)}"`:""}>Open task</button>`:"";
  const mark=unread?`<button type="button" class="link" data-read="${escapeHtml(n.id)}">Mark read</button>`:"";
  return `<li class="note-row${unread?" unread":""}"><span class="note-dot" aria-hidden="true"></span><div class="note-main"><p class="note-summary">${unread?'<span class="sr-only">Unread: </span>':""}${escapeHtml(n.summary)}</p>
    <p class="note-meta">${n.task_title&&!String(n.summary||"").includes(n.task_title)?`${escapeHtml(n.task_title)} · `:""}<time datetime="${escapeHtml(n.created_at)}">${escapeHtml(when)}</time></p></div><div class="note-actions">${open}${mark}</div></li>`;
}
function noteList(items){
  const days=["Today","Yesterday","Earlier"].map(label=>[label,items.filter(n=>noteDay(n.created_at)===label)]).filter(([,rows])=>rows.length);
  return days.map(([label,rows])=>`<h3 class="note-day">${label}</h3><ul class="note-list">${rows.map(noteRow).join("")}</ul>`).join("");
}
function digestTaskList(items,label){
  const shown=(items||[]).slice(0,5);
  if(!shown.length)return `<p class="digest-empty">None ${label}.</p>`;
  return `<ul class="digest-items">${shown.map(item=>`<li><strong>${escapeHtml(item.title||item.task_title||"Task")}</strong><span>${escapeHtml(item.project_name||"")}${item.due_date?` · due ${escapeHtml(item.due_date)}`:""}${item.checkpoint_date?` · checkpoint ${escapeHtml(item.checkpoint_date)}`:""}</span>${item.next_action&&item.next_action!=="None"?`<small>Next: ${escapeHtml(item.next_action)}</small>`:""}<a href="#/project/${encodeURIComponent(item.project_id)}/list?task=${encodeURIComponent(item.id||item.task_id)}">Open task</a></li>`).join("")}</ul>${items.length>shown.length?`<p class="fine">Showing ${shown.length} of ${items.length} tasks.</p>`:""}`;
}
function digestSection(title,items,label){return `<section class="digest-section"><h3>${escapeHtml(title)} <span class="count">${(items||[]).length}</span></h3>${digestTaskList(items,label)}</section>`}
function dailyDigestPanel(){
  if(state.dailyDigestError)return `<section class="daily-digest-panel"><p class="error" role="alert">${escapeHtml(state.dailyDigestError)}</p><button type="button" class="quiet" id="digest-close">Close summary</button></section>`;
  const digest=state.dailyDigest;if(!digest)return "";
  const s=digest.sections||{};
  return `<section class="daily-digest-panel" aria-labelledby="daily-digest-title"><div class="digest-head"><div><h2 id="daily-digest-title">Daily project summary</h2><p class="fine">${escapeHtml(digest.date)} · ${escapeHtml(digest.timezone||"")}</p></div><button type="button" class="quiet" id="digest-close">Close summary</button></div>
    ${digestSection("Overdue",s.overdue,"are overdue")}${digestSection("Due today",s.today,"due today")}${digestSection("Due in 1–7 days",s.next_7_days,"coming up")}${digestSection("Due in 8–30 days",s.next_30_days,"scheduled")}${digestSection("Awaiting review",s.reviews,"awaiting review")}
    <section class="digest-section"><h3>Open checkpoints due soon or overdue <span class="count">${(s.checkpoints||[]).length}</span></h3>${(s.checkpoints||[]).length?`<ul class="digest-items">${s.checkpoints.slice(0,5).map(item=>`<li><strong>${escapeHtml(item.task_title)}</strong><span>${escapeHtml(item.project_name)} · ${escapeHtml(item.checkpoint_date)}${item.reason?` · ${escapeHtml(item.reason)}`:""}</span><a href="#/project/${encodeURIComponent(item.project_id)}/list?task=${encodeURIComponent(item.task_id)}">Open task</a></li>`).join("")}</ul>${s.checkpoints.length>5?`<p class="fine">Showing 5 of ${s.checkpoints.length} checkpoints.</p>`:""}`:'<p class="digest-empty">No open checkpoints are overdue or due in the next 7 days.</p>'}</section>
    ${digestSection("Next actions",s.next_actions,"open")}</section>`;
}
async function openDailyDigest(digestDate){
  state.dailyDigest=null;state.dailyDigestError="";state.dailyDigestDate=digestDate;
  try{const {digest}=await api(`/api/daily-digest?date=${encodeURIComponent(digestDate)}`);state.dailyDigest=digest}
  catch(err){state.dailyDigestError=`The summary could not be opened. ${err.message}`}
  renderInbox(state.notifications||[],state.ownerRequests||[]);
}
function requestRow(r){
  return `<li class="unread owner-request"><strong>${escapeHtml(requestTitle(r))}</strong>${requestDetail(r)}
    <small>Requested by ${escapeHtml(r.requested_by_name)} · ${escapeHtml(new Date(r.requested_at).toLocaleString())}${r.task_id?` · <button type="button" class="link" data-detail="${escapeHtml(r.task_id)}">Open task</button>`:""}</small><div class="actions"><button type="button" data-request-decision="approved" data-request-id="${escapeHtml(r.id)}">Approve</button><button type="button" class="quiet" data-request-decision="rejected" data-request-id="${escapeHtml(r.id)}">Reject</button><button type="button" class="quiet" data-request-decision="cancelled" data-request-id="${escapeHtml(r.id)}">Cancel request</button></div></li>`;
}
function renderInbox(items,requests=[]){
  state.ownerRequests=requests;state.inboxLoads=state.loads;
  const tab=inboxTab(items,requests),unread=items.filter(n=>!n.read_at),owner=isOwner();
  const counts={needs:requests.length,unread:unread.length,all:items.length};
  const tabs=INBOX_TABS.filter(([k])=>k!=="needs"||owner).map(([k,label])=>`<a href="#/inbox?tab=${k}"${k===tab?' aria-current="page"':""}>${label} <span class="count">${counts[k]}</span></a>`).join("");
  const requestBlock=requests.length?`<section class="inbox-section"><h2>Needs your decision <span class="count">${requests.length}</span></h2><ul class="people-list">${requests.map(requestRow).join("")}</ul></section>`:"";
  const empty=(title,text)=>`<div class="empty-state"><h2>${title}</h2><p>${text}</p></div>`;
  const content=tab==="needs"?(requestBlock||empty("Nothing is waiting for your decision","Requests from managers and members to change a task or close a project appear here."))
    :tab==="unread"?(unread.length?noteList(unread):empty("You are all caught up","Nothing unread. <a href=\"#/inbox?tab=all\">See all notifications</a>."))
    :(owner?requestBlock:"")+(items.length?`<section class="inbox-section">${owner&&requests.length?"<h2>Notifications</h2>":""}${noteList(items)}</section>`:empty("No notifications yet","Assignments, reviews and changes to your tasks appear here."));
  document.querySelector("#inbox-body").innerHTML=`<div class="inbox-bar"><nav class="tabs" aria-label="Inbox views">${tabs}</nav><button type="button" id="read-all" class="quiet"${unread.length?"":" disabled"}>Mark all read</button></div>
    <div class="error" id="inbox-error" role="alert" tabindex="-1"></div>${dailyDigestPanel()}${content}`;
  document.querySelector("#read-all").addEventListener("click",markAllRead);
  document.querySelectorAll("#inbox-body [data-read]").forEach(b=>b.addEventListener("click",()=>markRead(b.dataset.read)));
  document.querySelectorAll("#inbox-body [data-request-decision]").forEach(b=>b.addEventListener("click",()=>decideOwnerRequest(b.dataset.requestId,b.dataset.requestDecision)));
  document.querySelectorAll("#inbox-body [data-detail]").forEach(b=>b.addEventListener("click",()=>{openDetail(b.dataset.detail);if(b.dataset.readOnOpen)markRead(b.dataset.readOnOpen)}));
  document.querySelectorAll("#inbox-body [data-digest-date]").forEach(b=>b.addEventListener("click",()=>openDailyDigest(b.dataset.digestDate)));
  document.querySelector("#digest-close")?.addEventListener("click",()=>{state.dailyDigest=null;state.dailyDigestError="";state.dailyDigestDate=null;renderInbox(state.notifications||[],state.ownerRequests||[])});
}
// 0D9Q3X: the Owner decides from the inbox, so each request says what it would change and why.
const REQUEST_LABELS={update_task_status:"Status change",accept_submission:"Accept submission",request_changes:"Request changes",reopen_task:"Reopen task",set_on_hold:"Put on hold",approve_schedule_proposal:"Approve schedule change",reject_schedule_proposal:"Reject schedule change",close_project:"Close project"};
function requestTitle(r){return `${REQUEST_LABELS[r.action]||r.action.replaceAll("_"," ")} · ${r.task_title||r.project_name}`}
function requestDetail(r){
  const p=r.payload||{};
  const change=r.action==="update_task_status"&&p.status
    ?`<p>Change status ${p.from_status?`from <strong>${escapeHtml(statusLabel(p.from_status))}</strong> `:""}to <strong>${escapeHtml(statusLabel(p.status))}</strong></p>`:"";
  const reason=r.reason?`<p><em>Reason: ${escapeHtml(r.reason)}</em></p>`:`<p class="muted">No reason given.</p>`;
  return `<div class="request-detail">${change}${reason}${requestGates(r)}</div>`;
}
// Review 12d M2: what approving would override, shown before the owner clicks Approve. The
// server checks the same rules again at decision time and asks the owner to confirm them.
function requestGates(r){
  const lines=(r.gates&&r.gates.lines)||[];
  return lines.length?`<p class="request-gates"><strong>Approving overrides:</strong> ${lines.map(escapeHtml).join(" · ")}</p>`:"";
}
// 0D9Q3X: a 409 means the record moved on under the user; show the current one instead of the stale form.
// The first line says what happened and what to do; the server's own reason follows on its own line.
const TASK_CONFLICT="This task changed since you opened it, so nothing was saved.";
function showConflict(box,text,detail){if(!box)return;box.classList.remove("message-info","message-success");box.innerHTML=escapeHtml(text)+(detail&&detail!==text?`<small class="conflict-detail">${escapeHtml(detail)}</small>`:"");box.focus?.()}
async function reloadTaskAfterConflict(taskId,errorId,detail){
  if(detailTaskId!==taskId){showToast("The earlier task changed; reopen it to review the latest version.");return}
  await load().catch(()=>{});if(detailTaskId!==taskId)return;const task=await openDetail(taskId);
  const next=!task?"It could not be reloaded."
    :CLOSED_STATUSES.includes(task.status)?`It is now ${statusLabel(task.status)}; this is the latest version.`
    :"It now shows the latest version; check it and try again.";
  let box=task?document.querySelector("#"+errorId):null;
  if(box){box.setAttribute("role","alert");box.tabIndex=-1}
  else{ // the reload removed the form (the task is read-only for this user now) or failed
    document.querySelector("#detail-body")?.insertAdjacentHTML("afterbegin",'<div class="error" id="detail-conflict" role="alert" tabindex="-1"></div>');
    box=document.querySelector("#detail-conflict");
  }
  showConflict(box,`${TASK_CONFLICT} ${next}`,detail);
}
function requestConflictText(id,decision){
  const r=(state.ownerRequests||[]).find(q=>q.id===id);
  if(!r)return "This request changed since you opened it, so nothing was decided. The inbox now shows the latest.";
  // A pending request keeps the state it was filed against, so an approve that conflicts once always will.
  return decision==="approved"
    ?`“${requestTitle(r)}” can no longer be approved: what it was filed against has changed. Reject or cancel it.`
    :`“${requestTitle(r)}” could not be ${decision}: it changed since you opened it. The inbox now shows the latest.`;
}
// Open task stacks the task over the inbox; if anything was saved there, show the inbox as it is now on Close.
document.querySelector("#detail-dialog").addEventListener("close",()=>{if(currentRoute().name==="inbox"&&state.inboxLoads!==state.loads)openInbox()});
async function decideOwnerRequest(id,decision,errorId="inbox-error"){
  const reason=prompt(decision==="approved"?"Decision note (optional)":`Reason this request is ${decision}:`);
  if(reason===null)return;
  if(decision!=="approved"&&!reason.trim()){alert("A reason is required.");return}
  const box=()=>document.querySelector(`#${errorId}`),err=box();if(err)clearFeedback(err);
  // Review 12d M2: an approval meets the same dependency, limit and date rules as acting
  // directly; each one the server names is confirmed in turn, or the approval is left alone.
  const r=(state.ownerRequests||[]).find(q=>q.id===id)||{};
  const task=(state.tasks||[]).find(t=>t.id===r.task_id)||{title:r.task_title||r.project_name||"",project_id:r.project_id};
  try{
    const out=await withConfirms(task,(r.gates&&r.gates.column)||null,more=>api(`/api/owner-action-requests/${id}/decision`,{method:"POST",body:JSON.stringify({decision,reason,...more})}));
    if(!out)return;
    await load();await openInbox()}
  catch(x){
    if(x.status===409){await load().catch(()=>{});await openInbox();showConflict(box(),requestConflictText(id,decision),x.message);return}
    showConflict(box(),x.message);
  }
}
async function markRead(id){
  try{await api(`/api/notifications/${id}/read`,{method:"POST",body:"{}"});await openInbox()}catch(x){alert(x.message)}
}
async function markAllRead(){
  try{await api("/api/notifications/read-all",{method:"POST",body:"{}"});await openInbox()}catch(x){alert(x.message)}
}
// 3FQEKB: an assignee picker never lists the Chairman and lists a project viewer only for a
// subtask ("(viewer)"); the reviewer picker keeps everyone with access. A current owner the rules
// no longer allow stays selected, marked, so saving other fields never unassigns them silently.
const assigneeLoads=new WeakMap();let assigneeHintCount=0;
function personLabel(user,people){const name=user.display_name||"Person",duplicates=people.filter(p=>(p.display_name||"").trim().toLowerCase()===name.trim().toLowerCase()).length>1;return name+(duplicates?` · ${user.email||user.id}`:"")}
async function fillAssignees(projectId,select,selectedId,purpose="task",currentName=""){
  if(!select)return false;
  const prior=assigneeLoads.get(select),hint=prior?.hint||document.createElement("p"),request={hint};
  if(!prior){hint.className="field-hint";hint.id=`assignee-hint-${++assigneeHintCount}`;hint.setAttribute("role","status");const label=select.closest?.("label");if(label)label.insertAdjacentElement("afterend",hint);else select.parentElement?.appendChild?.(hint);select.setAttribute("aria-describedby",hint.id)}
  assigneeLoads.set(select,request);select.disabled=true;select.dataset.assigneesState="loading";
  select.innerHTML='<option value="">Unassigned</option>';
  if(selectedId){const option=new Option(currentName||"Current owner",selectedId);option.selected=true;select.add(option)}
  hint.textContent=projectId?"Loading people. The existing assignment is kept.":"Choose a project first.";
  if(!projectId)return false;
  try{
    const {users}=await api(`/api/assignable-users?project_id=${encodeURIComponent(projectId)}&for=${encodeURIComponent(purpose)}`);
    if(assigneeLoads.get(select)!==request)return false;
    select.innerHTML='<option value="">Unassigned</option>';
    for(const u of users){const o=new Option(personLabel(u,users)+(u.project_role==="viewer"?" (viewer)":""),u.id);if(u.id===selectedId)o.selected=true;select.add(o)}
    if(selectedId&&!users.some(u=>u.id===selectedId)){const o=new Option(`${currentName||"Current owner"} (needs a new assignee)`,selectedId);o.selected=true;select.add(o)}
    select.disabled=false;select.dataset.assigneesState="ready";hint.textContent="";return true;
  }catch{
    if(assigneeLoads.get(select)!==request)return false;
    select.dataset.assigneesState="error";hint.textContent="People could not be loaded. The existing assignment is kept. ";
    const retry=document.createElement("button");retry.type="button";retry.className="link";retry.textContent="Retry people";retry.addEventListener("click",()=>fillAssignees(projectId,select,selectedId,purpose,currentName));hint.appendChild(retry);return false;
  }
}
// Cancel in these forms is a plain button, so Enter in a field submits with the form's only submit
// button (Create, Continue, Add task) and never closes the dialog unsaved.
for(const [button,dialog] of [["#project-cancel","#project-dialog"],["#project-action-cancel","#project-action-dialog"],["#task-cancel","#task-dialog"]])
  document.querySelector(button).onclick=()=>document.querySelector(dialog).close();
document.querySelector("#project-form").addEventListener("submit",async e=>{e.preventDefault();try{await api("/api/projects",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});e.target.reset();e.target.closest("dialog").close();await load()}catch(err){e.target.querySelector(".error").textContent=err.message}});
document.querySelector("#task-form").addEventListener("submit",async e=>{e.preventDefault();try{const data=Object.fromEntries(new FormData(e.target));const out=await withConfirms({title:data.title||"the new task"},COLUMN_OF_STATUS[data.status]||"draft",more=>api("/api/tasks",{method:"POST",body:JSON.stringify({...data,...more})}));if(!out)return;const {task}=out;e.target.reset();e.target.closest("dialog").close();await load();if(task&&currentRoute().name==="portfolio"&&!visibleTasks().some(t=>t.id===task.id))showToast(`“${task.title}” was added · the current filters hide it`,"Show it",showAllOnPortfolio)}catch(err){e.target.querySelector(".error").textContent=err.message}});
const STATUSES=["draft","assigned","in_progress","submitted","changes_requested","completed","on_hold","delayed","cancelled","abandoned","reopened"];
const CRITICALITIES=[["","Unrated"],["critical","Critical"],["high","High"],["normal","Normal"],["low","Low"]];
const GOVERNED=["submitted","completed","on_hold","reopened"];
// ARZWV7: a closed task is a fixed record; a Manager may only ask to move it back into ordinary work
// (service.py REOPEN_ONLY_STATUSES / REOPEN_EQUIVALENT_STATUSES). UI hints only — the server decides.
const BACK_TO_WORK=["draft","assigned","in_progress","delayed"];
const EVENT_LABELS={reviewer_added:"Reviewer added",reviewer_removed:"Reviewer removed",board_move_blocked:"Board move refused",dependency_override:"Dependency overridden",wip_limit_override:"Work-in-progress limit overridden",task_lock_forced:"Lock forced open",gantt_move_blocked:"Date drag refused",schedule_impact_confirmed:"Date change with consequences confirmed",import_committed:"Import committed",import_key_assigned:"Import key assigned",task_created:"Task created",task_updated:"Task updated",dependency_added:"Dependency added",dependency_removed:"Dependency removed",task_submitted:"Work submitted",submission_accepted:"Submission accepted",changes_requested:"Changes requested",task_reopened:"Task reopened",task_on_hold:"Put on hold",criticality_changed:"Criticality changed",parent_changed:"Parent changed",schedule_proposed:"Schedule change proposed",schedule_revised:"Schedule revised",schedule_proposal_rejected:"Schedule proposal rejected",attachment_added:"Attachment linked",attachment_removed:"Attachment link removed",attachment_downloaded:"File downloaded",attachment_download_blocked:"Download refused",direct_link_created:"Direct link created",direct_link_revoked:"Direct link revoked",attachment_direct_download:"Downloaded through a direct link"};
const DIFF_FIELDS=[["title","Title"],["status","Status"],["criticality","Criticality"],["start_date","Start date"],["due_date","Due date"],["progress","Progress"],["description","Description"]];
let detailTaskId=null,detailLoadVersion=0;

document.querySelector("#gantt").addEventListener("click",e=>{
  // The name in the Step pane (and a phase's open button) opens the task; a click on a bar opens Edit
  // Step, as in the block (a drag is not a click); the rest of a phase row folds or unfolds it.
  const b=e.target.closest("[data-detail]");
  if(b){openDetail(b.dataset.detail);return}
  const bar=e.target.closest("[data-bar]");
  if(bar){gxOpenBar(bar.dataset.bar);return}
  const phase=e.target.closest(".gx-pane [data-phase-row]");
  if(phase)gxTogglePhase(phase.dataset.phaseRow);
});
document.querySelector("#gantt").addEventListener("keydown",e=>{
  if((e.key!=="Enter"&&e.key!==" ")||e.repeat||gdrag.active)return;
  const bar=e.target.closest?.("[data-bar]");if(!bar||bar!==e.target)return;
  e.preventDefault();gxOpenBar(bar.dataset.bar);
});
document.querySelector("#schedule-table").addEventListener("click",e=>{const b=e.target.closest("[data-detail]");if(b)openDetail(b.dataset.detail)});

async function openDetail(taskId){
  const version=++detailLoadVersion;
  const moveFocus=panelState.shown!==taskId||document.querySelector("#detail-dialog").hidden;
  if(detailTaskId&&detailTaskId!==taskId&&leases.get(detailTaskId)?.kind==="edit")dropLease(detailTaskId,"edit");
  detailTaskId=taskId;
  panelState.task=null;
  document.querySelector("#detail-body").innerHTML='<h2 id="detail-heading" tabindex="-1">Loading task…</h2><p role="status">Please wait for the task details.</p>';
  openPanel(taskId);
  try{
    const [d,ev]=await Promise.all([api(taskApi(taskId)),api(taskApi(taskId,"/events"))]);
    if(version!==detailLoadVersion||detailTaskId!==taskId)return null;
    renderDetail(d.task,ev.events);
    openPanel(taskId);
    panelState.task=d.task;if(currentRoute().name==="task")shellTitle(currentRoute());
    if(moveFocus)document.querySelector("#detail-heading")?.focus({preventScroll:true});
    return d.task;
  }catch(err){if(version!==detailLoadVersion||detailTaskId!==taskId)return null;document.querySelector("#detail-body").innerHTML=`<p class="error" role="alert">${escapeHtml(err.message)}</p><button type="button" id="detail-retry">Retry task</button>`;document.querySelector("#detail-retry").addEventListener("click",()=>openDetail(taskId));return null}
}
async function refreshDetail(taskId){await load();if(detailTaskId!==taskId)return null;return openDetail(taskId)}
// DR3PKR: the task panel. It is docked on the right (non-modal) and has its own link: ?task=<id> over the
// current screen, or #/task/<id> as a full page. Opening adds a history entry, so Back closes it; closing
// fires "close" (as the old dialog did) so the Inbox can refresh. The aside keeps the id detail-dialog.
const panelState={shown:null,opener:null,openerKey:null,pushed:null,lastView:"#/home",quiet:false,task:null};
function taskLink(id){return `#/task/${encodeURIComponent(id)}`}
function taskApi(id,suffix=""){return `/api/tasks/${encodeURIComponent(id)}${suffix}`}
function routeHash(r,taskId){const p=new URLSearchParams(r.params);p.delete("task");if(taskId)p.set("task",taskId);const q=p.toString();return `#/${r.path||r.name}${q?"?"+q:""}`}
function openPanel(taskId){
  const panel=document.querySelector("#detail-dialog"),app=document.querySelector("#app"),r=currentRoute(),isNew=panelState.shown!==taskId,wasHidden=panel.hidden;
  if(wasHidden){const a=document.activeElement,ok=a&&a!==document.body&&!panel.contains(a);panelState.opener=ok?a:null;
    // A re-render can replace the opener, so also keep a selector that finds its replacement (as GF-6 does).
    const kind=ok&&a.hasAttribute("data-detail")?[...FOCUS_KINDS,"work-title"].find(k=>a.classList.contains(k)):null;
    panelState.openerKey=ok&&a.hasAttribute("data-detail")?`${kind?"."+kind:""}[data-detail="${CSS.escape(a.dataset.detail)}"]`:null}
  panel.hidden=false;panelState.shown=taskId;
  app.classList.add("panel-open");app.classList.toggle("task-page",r.name==="task");
  document.querySelector("#detail-full").setAttribute("href",taskLink(taskId));
  // A first open adds a history entry (Back closes the panel); swapping tasks while it is open replaces it.
  if(r.name!=="task"&&r.params.get("task")!==taskId){const h=routeHash(r,taskId);
    if(wasHidden){panelState.pushed=h;location.hash=h}else{if(history.replaceState)history.replaceState(null,"",h);if(panelState.pushed)panelState.pushed=h}}
  syncPanelInert();
  if(isNew)document.querySelector("#detail-heading")?.focus({preventScroll:true});
}
function closePanel(fromRoute){
  ++detailLoadVersion;detailTaskId=null;panelState.task=null;
  const panel=document.querySelector("#detail-dialog");
  if(panel.hidden)return;
  panel.hidden=true;panelState.shown=null;
  for(const [id,l] of leases)if(l.kind==="edit")dropLease(id,"edit");
  document.querySelector("#app").classList.remove("panel-open","task-page");
  syncPanelInert();
  panel.dispatchEvent(new Event("close"));
  if(!fromRoute){
    const r=currentRoute();
    if(r.name==="task"){panelState.quiet=true;location.hash=panelState.lastView}
    else if(location.hash===panelState.pushed&&history.back){panelState.quiet=true;history.back()}
    else if(history.replaceState)history.replaceState(null,"",routeHash(r,null));
  }
  panelState.pushed=null;
  let back=panelState.opener;
  if((!back||!back.isConnected)&&panelState.openerKey)back=document.querySelector(`[data-view]:not([hidden]) ${panelState.openerKey}`);
  panelState.opener=panelState.openerKey=null;
  if(back&&back.isConnected&&!back.closest("[hidden]"))back.focus({preventScroll:true});else document.querySelector("#page-title").focus();
}
// j/k: the next or previous task in the order the screen behind shows them (its visible task links).
function panelSequence(){
  const ids=[];
  document.querySelectorAll("[data-view]:not([hidden]) [data-detail]").forEach(n=>{if(!n.closest("[hidden]")&&!ids.includes(n.dataset.detail))ids.push(n.dataset.detail)});
  return ids;
}
function stepPanel(delta){
  const list=panelSequence(),i=list.indexOf(panelState.shown),next=list[i+delta];
  if(i<0||!next)return;
  const r=currentRoute();if(r.name!=="task"&&history.replaceState){const h=routeHash(r,next);history.replaceState(null,"",h);if(panelState.pushed)panelState.pushed=h}
  openDetail(next);
}
document.querySelector("#detail-close").addEventListener("click",()=>closePanel(false));
document.querySelector("#detail-copy").addEventListener("click",async()=>{
  const url=location.origin+location.pathname+taskLink(panelState.shown||detailTaskId);
  try{await navigator.clipboard.writeText(url);showToast("Link to this task copied.")}catch{showToast(`Copy this link: ${url}`,null,null,true)}
});
document.addEventListener("keydown",e=>{
  const panel=document.querySelector("#detail-dialog");
  if(panel.hidden||e.defaultPrevented||e.ctrlKey||e.metaKey||e.altKey||document.querySelector("dialog[open]")||document.querySelector(".menu:not([hidden])"))return;
  const inField=e.target.closest("input,textarea,select,[contenteditable]"),inPanel=panel.contains(e.target);
  // A first Esc in a panel field leaves the field but stays in the panel; the next one closes it.
  if(e.key==="Escape"){e.preventDefault();if(inField&&inPanel)document.querySelector("#detail-heading")?.focus();else closePanel(false)}
  else if(inPanel&&!inField&&(e.key==="j"||e.key==="k")){e.preventDefault();stepPanel(e.key==="j"?1:-1)}
});

// QY0WG2: an Unrated task has no confirmed consequence yet, so it must stand out rather than read
// like a level. It reuses the shared warning badge; rated levels keep their plain text.
function critLabel(level,strong){
  if(!level)return `<span class="badge" data-level="warning" title="No confirmed criticality yet — confirm a level in Details">Unrated</span>`;
  return strong?`<strong>${escapeHtml(level)}</strong>`:escapeHtml(level);
}

function fact(label,value){return `<div class="fact"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`}
// DR3PKR: state chips under the title: tint + dark text, and a glyph or word so colour is never the only cue.
function stateTags(task){
  const tag=(tone,text)=>`<span class="tag" data-tone="${tone}">${escapeHtml(text)}</span>`;
  const tone={draft:"gray",assigned:"blue",in_progress:"teal",submitted:"amber",changes_requested:"amber",completed:"green",on_hold:"purple",delayed:"red",cancelled:"gray",abandoned:"gray",reopened:"teal"}[task.status]||"gray";
  const out=[tag(tone,(task.status==="completed"?"✓ ":task.status==="on_hold"?"∥ ":"")+statusLabel(task.status))];
  const due=dueText(task);
  if(task.due_state==="overdue")out.push(tag("red",`▲ ${due||"Overdue"}`));
  else if(task.due_state==="today")out.push(tag("amber",due||"Due today"));
  else if(task.due_state!=="closed")out.push(tag("gray",due||(task.due_date?`Due ${fmtDay(task.due_date)}`:"No due date")));
  if(task.is_blocked)out.push(tag("purple","⊘ Blocked"));
  if(task.is_critical_path)out.push(tag("red","◆ Critical path"));
  if(task.needs_new_assignee||task.needs_new_collaborator)out.push(reassignChip(task));
  return out.join("");
}
function roleLine(perms){
  if(perms.can_decide_protected)return "You are the App Owner. Changes apply directly and are recorded in History.";
  if(perms.can_request_protected)return "You manage this project. Protected changes go to the App Owner as requests.";
  const acceptanceHint=perms.can_request_accept_submission?" You may request App Owner acceptance of submitted work.":"";
  if(perms.assign_only)return "You can assign this task to someone. Other changes are made by the project's managers."+acceptanceHint;
  if(perms.can_request_accept_submission)return "You are a designated approver."+acceptanceHint;
  if(perms.can_edit_ordinary)return "You can edit this task. Changes are recorded in History.";
  return "You can view this task.";
}

function renderDetail(task,events){
  const perms=task.permissions||{};
  const closed=CLOSED_STATUSES.includes(task.status),submitted=task.status==="submitted";
  const canReopen=closed&&(perms.can_decide_protected||perms.can_request_protected);
  const editable=submitted?[task.status]:STATUSES.filter(s=>!GOVERNED.includes(s));
  if(!editable.includes(task.status))editable.unshift(task.status);
  const opts=editable.map(s=>`<option${s===task.status?" selected":""}>${escapeHtml(s)}</option>`).join("");
  const crit=CRITICALITIES.map(([v,l])=>`<option value="${v}"${v===(task.criticality||"")?" selected":""}>${escapeHtml(l)}</option>`).join("");
  // DR3PKR: the panel opens on who, when and how far; the project and parent sit in the crumb above the title.
  // Critical path, blocked and days-to-due are computed for the task list, not the detail record, so read them there.
  const roll=task.subtask_rollup,listed=state.tasks.find(t=>t.id===task.id)||task;
  const facts=[
    fact("Owner",task.owner_name||"Unassigned"),
    fact("Start",task.start_date?fmtDay(task.start_date):"Not set"),
    fact("Due",task.due_date?fmtDay(task.due_date):"Not set"),
    fact("Criticality",task.criticality?task.criticality.charAt(0).toUpperCase()+task.criticality.slice(1):"Unrated"),
    fact("Progress",task.progress==null?"—":`${task.progress}%`),
    fact("Steps",roll&&roll.total?`${roll.completed} of ${roll.total} done`:"None"),
  ].join("");
  // Review 13a L1: someone who cannot edit (the Chairman, a viewer, a member) sees the lists, not the
  // forms the server would refuse (parent, criticality, proposal, dependencies, reviewers).
  const ro=perms.can_edit_ordinary===false,fixed=closed||ro;
  const deps=(task.dependencies||[]).map(dep=>{
    const other=dep.direction==="incoming"?dep.predecessor_title:dep.successor_title;
    const flag=dep.blocking?' <span class="blocked-text">(blocking)</span>':"";
    // A closed task cannot lose a predecessor (it is the successor); it may still stop blocking another task.
    if((closed&&dep.direction==="incoming")||ro)return `<li>${dep.direction==="incoming"?"Depends on":"Blocks"}: <strong>${escapeHtml(other)}</strong>${flag}</li>`;
    return `<li>${dep.direction==="incoming"?"Depends on":"Blocks"}: <strong>${escapeHtml(other)}</strong>${flag}
      <span class="dep-remove"><input class="dep-reason" placeholder="Reason to remove" aria-label="Reason to remove dependency">
      <button type="button" class="link" data-remove-pred="${escapeHtml(dep.predecessor_task_id)}" data-remove-succ="${escapeHtml(dep.successor_task_id)}">Remove</button></span></li>`;
  }).join("")||"<li>No dependencies.</li>";
  const candidates=state.tasks.filter(t=>t.project_id===task.project_id&&t.id!==task.id);
  const addOptions=candidates.map(t=>`<option value="${escapeHtml(t.id)}">${escapeHtml(t.title)}</option>`).join("");
  const timeline=events.slice().reverse().map(renderEvent).join("")||"<li>No history.</li>";
  const reviewers=buildReviewers(task,fixed);
  const attachments=buildAttachments(task);
  const subtasks=buildSubtasks(task,fixed);
  const schedule=buildSchedule(task,closed,{canPropose:!ro});
  const critForm=fixed?`<div class="crit-confirm"><h3>Criticality</h3><p>Current: ${critLabel(task.criticality,true)}</p></div>`:`<div class="crit-confirm"><h3>Criticality</h3>
    <p>Current: ${critLabel(task.criticality,true)} — changes are confirmed with a reason and recorded.</p>
    <form id="crit-form" data-revision="${escapeHtml(String(task.revision))}"><label>Set level<select name="criticality">${crit}</select></label>
      <label>Reason (evidence for this level)<input name="reason" required></label>
      <div class="actions"><button>Confirm criticality</button></div><div class="error" id="crit-error"></div></form></div>`;
  const closedNote=closed?`<div class="state-note" role="note"><p><strong>${escapeHtml(statusLabel(task.status))}.</strong> Reopen this task to change it.${perms.can_manage_files?" Attachments and final results can still be added.":""}</p>
    ${canReopen?`<button type="button" class="link" data-goto-reopen>${perms.can_decide_protected?"Reopen task…":"Request reopening…"}</button>`:`<p>Ask the App Owner to reopen it.</p>`}</div>`:"";
  // 5GK6SB: name the decision buttons this viewer actually has under Lifecycle.
  const decide=decisionLabels(perms.can_decide_protected);
  const submissionHint=perms.can_decide_protected||perms.can_request_protected?`Use ${decide.accept} or ${decide.changes} under Lifecycle.`
    :perms.can_request_accept_submission?`Use ${decide.accept} under Lifecycle.`:"The App Owner will Accept or Request changes.";
  const statusHint=submitted?`<p class="field-hint" id="status-locked-hint">Status is locked while this work is in review. ${escapeHtml(submissionHint)}</p>`:"";
  // The hint shares the Status grid cell, so it sits under the field it explains (not inside the label, which would add it to the select's name).
  const statusField=submitted?`<div><label>Status<select name="status" aria-disabled="true" aria-describedby="status-locked-hint">${opts}</select></label>${statusHint}</div>`
    :`<label>Status<select name="status">${opts}</select></label>`;
  const backToWork=BACK_TO_WORK.map(s=>`<option value="${s}">${escapeHtml(statusLabel(s))}</option>`).join("");
  const statusRequest=closed&&perms.can_edit_ordinary&&!perms.can_decide_protected?`<form id="detail-edit">
      <p class="field-hint">Or, instead of reopening, ask to move it straight back into work.</p>
      <input name="expected_revision" type="hidden" value="${task.revision}">
      <div class="grid">
        <label>Status<select name="status" required><option value="">Choose a status…</option>${backToWork}</select></label>
        <label>Reason<input name="reason" required></label>
      </div>
      <div class="actions"><button>Request status change</button></div>
      <div class="error" id="detail-edit-error"></div>
    </form>`:"";
  // 3FQEKB: the Chairman may change who a task is assigned to, and nothing else.
  const assignForm=closed?"":`<form id="detail-assign">
      <h3>Assign</h3>
      <input name="expected_revision" type="hidden" value="${task.revision}">
      <label>Assigned to<select name="owner_user_id"><option value="">Unassigned</option></select></label>
      <label>Reason (optional)<input name="reason" autocomplete="off"></label>
      <p class="field-hint">You can assign this ${task.parent_task_id?"subtask":"task"} to someone else. Other changes stay with the project's managers.</p>
      <div class="actions"><button value="save">Save assignee</button></div>
      <div class="error" id="detail-assign-error" role="alert"></div>
    </form>`;
  const editForm=perms.assign_only?assignForm:fixed?"":`<form id="detail-edit">
      <h3>Edit</h3>
      <input name="expected_revision" type="hidden" value="${task.revision}">
      <label>Title<input name="title" value="${escapeHtml(task.title)}" required></label>
      <label>Owner<select name="owner_user_id"><option value="">Unassigned</option></select></label>
      <div class="grid">
        ${statusField}
        <label>Start date<input name="start_date" type="date" value="${escapeHtml(task.start_date||"")}"></label>
        <label>Due date<input name="due_date" type="date" value="${escapeHtml(task.due_date||"")}"></label>
        <label>Progress<input name="progress" type="number" min="0" max="100" value="${task.progress==null?"":task.progress}"></label>
      </div>
      <label>Description<textarea name="description">${escapeHtml(task.description||"")}</textarea></label>
      <label>Reason (required for status or schedule changes)<input name="reason"></label>
      <div class="actions"><button value="save">Save changes</button></div>
      <div class="error" id="detail-edit-error"></div>
    </form>`;
  const lifecycle=buildLifecycle(task,statusRequest);
  const addDep=fixed?"":`<div class="add-dep">
        <select id="add-dep-select" aria-label="Predecessor task"><option value="">Add a predecessor…</option>${addOptions}</select>
        <button type="button" id="add-dep-button">Add predecessor</button>
      </div>`;
  // D73AQW: a step opened from the Gantt can return to its parent task.
  const parentLink=task.parent_task_id?`<p class="parent-link"><button type="button" class="link" data-detail="${escapeHtml(task.parent_task_id)}">◂ Parent: ${escapeHtml(task.parent_title||"parent task")}</button></p>`:"";
  document.querySelector("#detail-body").innerHTML=`
    ${parentLink}
    <p class="panel-crumb">${escapeHtml(task.project_name||"")}</p>
    <h2 id="detail-heading" tabindex="-1">${escapeHtml(task.title)}</h2>
    <div class="tags">${stateTags({...listed,...task,is_blocked:listed.is_blocked,is_critical_path:listed.is_critical_path,days_to_due:listed.days_to_due})}</div>
    <p class="role-line">${escapeHtml(roleLine(perms))}</p>
    <div id="lock-slot">${lockedByOther(task)?lockBanner(task.lock,"",perms.can_force_unlock):""}</div>
    <div class="facts">${facts}</div>
    <div class="panel-sections" role="group" aria-label="Jump to a section">${[["desc","Details"],["subtasks","Steps"],["deps","Dependencies"],["lifecycle","Lifecycle"],["reviewers","Reviewers"],["attachments","Files"],["schedule","Schedule"],["edit-section","Edit"],["history","History"]].map(([c,l])=>`<button type="button" class="link" data-jump="${c}">${l}</button>`).join("")}</div>
    ${closedNote}
    <p class="desc">${escapeHtml(task.description||"No description.")}</p>
    ${buildImportedFields(task)}
    ${subtasks}
    <div class="deps">
      <h3>Dependencies</h3>
      <ul>${deps}</ul>
      ${addDep}
      <div class="error" id="dep-error" role="alert"></div>
    </div>
    ${lifecycle}
    ${reviewers}
    ${attachments}
    ${critForm}
    ${schedule}
    <div class="edit-section">${editForm}</div>
    ${ro?"":'<p><button type="button" class="link" id="save-task-template">Save this task (and its subtasks) as a template</button></p>'}
    <div class="history"><h3>History</h3><ul>${timeline}</ul></div>`;
  document.querySelectorAll("#detail-body form").forEach(form=>{form.dataset.taskId=task.id});
  document.querySelector("#detail-edit")?.addEventListener("submit",e=>submitDetailEdit(e,{statusLocked:submitted}));
  document.querySelector("#detail-assign")?.addEventListener("submit",submitAssign);
  document.querySelectorAll("#detail-body [data-jump]").forEach(b=>b.addEventListener("click",()=>document.querySelector(`#detail-body .${b.dataset.jump}`)?.scrollIntoView({block:"start"})));
  document.querySelector("#add-dep-button")?.addEventListener("click",addDependency);
  document.querySelector("#detail-body [data-goto-reopen]")?.addEventListener("click",()=>{const f=document.querySelector("#reopen-form");if(!f)return;f.scrollIntoView({behavior:"smooth",block:"center"});f.querySelector("input")?.focus({preventScroll:true})});
  document.querySelector("#detail-body").querySelectorAll("[data-remove-pred]").forEach(b=>b.addEventListener("click",removeDependency));
  const ownerPurpose=task.parent_task_id?"subtask":"task";
  fillAssignees(task.project_id,document.querySelector('#detail-edit select[name="owner_user_id"],#detail-assign select[name="owner_user_id"]'),task.owner_user_id,ownerPurpose,task.owner_name);
  wireLifecycle(task);
  wireEditLease(task);
  wireReviewers(task);
  wireAttachments(task);
  document.querySelector("#save-task-template")?.addEventListener("click",()=>saveTaskAsTemplate(task.id));
  document.querySelectorAll("#detail-body [data-mark-fr-sub]").forEach(b=>b.addEventListener("click",()=>markFinalResult(task.id,"submission",b.dataset.markFrSub)));
  document.querySelectorAll("#detail-body [data-mark-fr-att]").forEach(b=>b.addEventListener("click",()=>markFinalResult(task.id,"attachment",b.dataset.markFrAtt)));
  document.querySelectorAll("#detail-body [data-unmark-fr]").forEach(b=>b.addEventListener("click",()=>unmarkFinalResult(task.id,b.dataset.unmarkFr)));
  document.querySelector("#crit-form")?.addEventListener("submit",submitCriticality);
  document.querySelector("#parent-form")?.addEventListener("submit",submitParent);
  document.querySelectorAll("#detail-body .subtasks [data-detail], #detail-body .parent-link [data-detail]").forEach(b=>b.addEventListener("click",()=>openDetail(b.dataset.detail)));
  document.querySelector("#sched-form")?.addEventListener("submit",submitSchedule);
  document.querySelectorAll("#detail-body [data-approve-sched]").forEach(b=>b.addEventListener("click",()=>decideSchedule(b.dataset.approveSched,"approve")));
  document.querySelectorAll("#detail-body [data-reject-sched]").forEach(b=>b.addEventListener("click",()=>decideSchedule(b.dataset.rejectSched,"reject",b)));
}

// Review 13b M1: the proposal form needs edit rights; a pending proposal's Approve / Request
// controls need the right to decide or request schedule changes (an owner or a manager).
function buildSchedule(task,closed,{canPropose=true}={}){
  const b=task.baseline||{};
  const props=task.schedule_proposals||[];
  const pending=props.filter(p=>p.status==="pending");
  const history=props.filter(p=>p.status!=="pending");
  const canDecide=task.permissions?.can_decide_protected,canRequest=task.permissions?.can_request_protected;
  const pendingRows=pending.map(p=>{const controls=canDecide||canRequest
    ?`<span class="dep-remove">${closed?"":`<button type="button" class="link" data-approve-sched="${escapeHtml(p.id)}">${canDecide?"Approve":"Request Owner approval"}</button>`}
      <input class="sched-reject-reason" placeholder="Reason to reject" aria-label="Reason to reject">
      <button type="button" class="link" data-reject-sched="${escapeHtml(p.id)}">${canDecide?"Reject":"Request Owner rejection"}</button></span>`
    :`<span class="blocked-text">Owner decision required</span>`;
    return `<li>Proposed <strong>${escapeHtml(p.start_date||"—")} → ${escapeHtml(p.due_date||"—")}</strong> by ${escapeHtml(p.proposed_by_name||"")} <em class="muted">(${escapeHtml(p.reason)})</em>${controls}</li>`}).join("")||"<li>No pending proposals.</li>";
  const historyRows=history.map(p=>`<li>${escapeHtml(p.status)} · ${escapeHtml(p.start_date||"—")} → ${escapeHtml(p.due_date||"—")} · proposed by ${escapeHtml(p.proposed_by_name||"")}${p.decided_by_name?` · decided by ${escapeHtml(p.decided_by_name)}`:""}</li>`).join("");
  return `<div class="schedule"><h3>Schedule</h3>
    <div class="facts">
      ${fact("Baseline (original)",(b.start_date||"—")+" → "+(b.due_date||"—"))}
      ${fact("Current (approved)",(task.start_date||"—")+" → "+(task.due_date||"—"))}
      ${fact("Pending",pending.length?pending.length+" proposal(s)":"none")}
    </div>
    <h4 class="sched-h">Pending proposals</h4>
    <ul>${pendingRows}</ul>
    ${closed||!canPropose?`<div class="error" id="sched-error"></div>`:`<form id="sched-form"><h4 class="sched-h">Propose a schedule change</h4>
      <div class="grid"><label>New start<input name="start_date" type="date"></label><label>New due<input name="due_date" type="date"></label></div>
      <label>Reason<input name="reason" required></label>
      <div class="actions"><button>Propose</button></div><div class="error" id="sched-error"></div></form>`}
    ${history.length?`<h4 class="sched-h">History</h4><ul>${historyRows}</ul>`:""}</div>`;
}

async function submitSchedule(e){
  const taskId=e.target.dataset.taskId||detailTaskId;
  e.preventDefault();const err=document.querySelector("#sched-error");clearFeedback(err);err.classList.remove("message-info","message-success");
  try{
    const {proposal}=await api(taskApi(taskId,"/schedule-proposals"),{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
    const impacted=proposal.impacted_successors||[];
    const shown=await refreshDetail(taskId);
    if(shown&&impacted.length){const el=document.querySelector("#sched-error");if(el){el.classList.add("message-info");el.textContent=`Heads up — approving this may affect: ${impacted.map(t=>t.title).join(", ")} (they are not moved automatically).`;}}
  }catch(x){err.textContent=x.message}
}
async function decideSchedule(id,action,btn){
  const taskId=detailTaskId;
  const err=document.querySelector("#sched-error");if(err)clearFeedback(err);
  try{
    let outcome;
    // Review 12d L1: approving new dates with consequences asks first, as on the chart.
    if(action==="approve"){outcome=await withConfirms(state.tasks.find(t=>t.id===taskId),null,more=>api(`/api/schedule-proposals/${id}/approve`,{method:"POST",body:JSON.stringify(more)}));if(!outcome)return}
    else{const reason=btn.parentElement.querySelector(".sched-reject-reason").value;outcome=await api(`/api/schedule-proposals/${id}/reject`,{method:"POST",body:JSON.stringify({reason})});}
    const shown=await refreshDetail(taskId);
    if(shown&&outcome.request){const current=document.querySelector("#sched-error");if(current){current.classList.add("message-success");current.textContent="Owner request created; the live schedule is unchanged."}}
  }catch(x){if(err)err.textContent=x.message}
}

function buildSubtasks(task,closed){
  const rollup=task.subtask_rollup||{total:0,completed:0};
  // D73AQW: same order, index and swatch as the Gantt segments, so dialog and bar agree.
  const rows=stepOrder(task.subtasks||[]).map((s,i)=>{const n=i+1;return `<li><i class="sw step-c${stepHue(n)}${n>STEP_HUES?" wrap":""}" aria-hidden="true">${n}</i> <button type="button" class="link" data-detail="${escapeHtml(s.id)}">Step ${n} · ${escapeHtml(s.title)}</button> · ${escapeHtml(statusLabel(s.status))} · ${escapeHtml(s.owner_name||"Unassigned")} · ${escapeHtml(s.start_date||"—")} → ${escapeHtml(s.due_date||"—")}${s.criticality?` · ${escapeHtml(s.criticality)}`:""}</li>`}).join("")||"<li>No subtasks.</li>";
  const candidates=state.tasks.filter(t=>t.project_id===task.project_id&&t.id!==task.id);
  const parentOptions=candidates.map(t=>`<option value="${escapeHtml(t.id)}"${t.id===task.parent_task_id?" selected":""}>${escapeHtml(t.title)}</option>`).join("");
  return `<div class="subtasks"><h3>Subtasks</h3>
    <p>Roll-up: <strong>${rollup.completed} of ${rollup.total}</strong> subtasks completed — separate from this task's own declared progress (${task.progress==null?"unset":task.progress+"%"}).</p>
    <ul>${rows}</ul>
    ${closed?"":`<form id="parent-form"><label>Parent task<select name="parent_task_id"><option value="">No parent</option>${parentOptions}</select></label>
      <div class="actions"><button>Set parent</button></div><div class="error" id="parent-error"></div></form>`}</div>`;
}

async function submitParent(e){
  const taskId=e.target.dataset.taskId||detailTaskId;
  e.preventDefault();const err=document.querySelector("#parent-error");clearFeedback(err);
  const parent_task_id=e.target.querySelector('select[name="parent_task_id"]').value;
  try{const t=panelState.task||{title:""};
    const out=await withConfirms(t,boardColumn(t),more=>api(taskApi(taskId,"/parent"),{method:"POST",body:JSON.stringify({parent_task_id,...more})}));
    if(!out)return;await refreshDetail(taskId)}
  catch(x){err.textContent=x.message}
}

async function submitCriticality(e){
  const taskId=e.target.dataset.taskId||detailTaskId;
  e.preventDefault();const err=document.querySelector("#crit-error");clearFeedback(err);
  try{await api(taskApi(taskId,"/criticality"),{method:"POST",body:JSON.stringify({...Object.fromEntries(new FormData(e.target)),expected_revision:Number(e.target.dataset.revision)})});await refreshDetail(taskId)}
  catch(x){err.textContent=x.message}
}

// 5GK6SB: one source for the submission-decision button labels, shared with the locked-Status hint.
function decisionLabels(canDecide){
  return canDecide?{accept:"Accept & complete",changes:"Request changes"}
    :{accept:"Request Owner acceptance",changes:"Request Owner to return changes"};
}

function buildLifecycle(task,extra=""){
  const canDecide=task.permissions?.can_decide_protected,canRequest=task.permissions?.can_request_protected;
  const canRequestAcceptance=task.permissions?.can_request_accept_submission;
  const decide=decisionLabels(canDecide);
  const frBySub={};(task.final_results||[]).forEach(f=>{if(f.submission_id)frBySub[f.submission_id]=f.id});
  const subs=(task.submissions||[]).map(s=>{
    const decided=s.status==="accepted"?` · accepted by ${escapeHtml(s.decided_by_name||"")}`:s.status==="changes_requested"?` · changes requested`:"";
    const note=s.note?` — ${escapeHtml(s.note)}`:"";
    const decisionNote=s.decision_note?` <em>(${escapeHtml(s.decision_note)})</em>`:"";
    let frCtl="";
    if(s.status==="accepted"&&task.permissions?.can_manage_files){
      frCtl=frBySub[s.id]
        ?` · <span class="fr-tag">★ final result</span> <button type="button" class="link" data-unmark-fr="${escapeHtml(frBySub[s.id])}">Unmark</button>`
        :` · <button type="button" class="link" data-mark-fr-sub="${escapeHtml(s.id)}">Mark as final result</button>`;
    }
    return `<li>v${s.version} · <strong>${escapeHtml(s.status)}</strong> · by ${escapeHtml(s.submitted_by_name||"")}${decided}${note}${decisionNote}${frCtl}</li>`;
  }).join("")||"<li>No submissions yet.</li>";
  const pending=(task.submissions||[]).find(s=>s.status==="submitted");
  const closed=CLOSED_STATUSES.includes(task.status);
  let actions="";
  if(!closed&&task.status!=="submitted"&&task.permissions?.can_submit!==false){
    actions+=`<form data-life="submit"><label>Submit work (note)<input name="note"></label><div class="actions"><button>Submit for acceptance</button></div></form>`;
  }
  if(task.status==="submitted"&&pending){
    if(canDecide||canRequest||canRequestAcceptance){
      actions+=`<form data-life="accept" data-sid="${escapeHtml(pending.id)}"><label>Acceptance note<input name="decision_note"></label><div class="actions"><button>${escapeHtml(decide.accept)}</button></div></form>`;
    }else actions+=`<p class="blocked-text">Only the App Owner can decide this submission.</p>`;
    if(canDecide||canRequest){
      actions+=`<form data-life="changes" data-sid="${escapeHtml(pending.id)}"><label>Reason for changes<input name="reason" required></label><div class="actions"><button>${escapeHtml(decide.changes)}</button></div></form>`;
    }
  }
  if(closed&&(canDecide||canRequest)){
    actions+=`<form data-life="reopen" id="reopen-form"><label>Reason to reopen<input name="reason" required></label><label>Revised due date<input name="new_due_date" type="date" required></label><div class="actions"><button>${canDecide?"Reopen":"Request Owner reopening"}</button></div></form>`;
  }
  if(!closed&&task.status!=="on_hold"&&(canDecide||canRequest)){
    actions+=`<form data-life="hold"><label>On-hold reason<input name="reason" required></label><label>Follow-up checkpoint<input name="checkpoint_date" type="date" required></label><label>Responsible owner<select name="owner_user_id"><option value="">Unassigned</option></select></label><div class="actions"><button>${canDecide||task.permissions?.can_edit_ordinary?"Put on hold":"Request Owner hold"}</button></div></form>`;
  }
  return `<div class="lifecycle"><h3>Lifecycle</h3>
    <ul class="submissions">${subs}</ul>${actions}
    <div class="error" id="lifecycle-error"></div>${extra}</div>`;
}

function buildReviewers(task,closed){
  const rows=(task.reviewers||[]).map(r=>`<li>${escapeHtml(r.display_name)} · ${escapeHtml(r.role)}${r.not_allowed?' <span class="tag reassign-chip" data-tone="amber">⚠ Not allowed as a collaborator here: remove</span>':""}
    ${closed?"":`<button type="button" class="link" data-remove-reviewer-user="${escapeHtml(r.user_id)}" data-remove-reviewer-role="${escapeHtml(r.role)}">Remove</button>`}</li>`).join("")||"<li>No reviewers or approvers.</li>";
  if(closed)return `<div class="reviewers"><h3>Reviewers &amp; approvers</h3><ul>${rows}</ul></div>`;
  return `<div class="reviewers"><h3>Reviewers &amp; approvers</h3><ul>${rows}</ul>
    <div class="add-reviewer">
      <select id="reviewer-user" aria-label="Reviewer person"><option value="">Choose a person…</option></select>
      <select id="reviewer-role" aria-label="Reviewer role"><option value="approver">Approver</option><option value="reviewer">Reviewer</option><option value="collaborator">Collaborator</option></select>
      <button type="button" id="add-reviewer-button">Add</button>
      <div class="error" id="reviewer-error"></div>
    </div></div>`;
}

function wireLifecycle(task){
  document.querySelectorAll("#detail-body [data-life]").forEach(form=>form.addEventListener("submit",e=>lifecycleAction(e,task)));
  const holdOwner=document.querySelector('[data-life="hold"] select[name="owner_user_id"]');
  if(holdOwner)fillAssignees(task.project_id,holdOwner,task.owner_user_id,task.parent_task_id?"subtask":"task",task.owner_name);
}

async function lifecycleAction(e,task){
  e.preventDefault();
  const form=e.target,kind=form.dataset.life,err=document.querySelector("#lifecycle-error");clearFeedback(err);
  if(kind==="hold"&&form.querySelector('select[name="owner_user_id"]')?.disabled){err.textContent="Load the people list before choosing a responsible owner. Use Retry people.";return}
  const body=Object.fromEntries(new FormData(form));
  try{
    let outcome;
    if(kind==="submit")outcome=await withDependencyConfirm(task,"submitted",more=>api(taskApi(task.id,"/submit"),{method:"POST",body:JSON.stringify({...body,...more})}));
    else if(kind==="accept")outcome=await withDependencyConfirm(task,"completed",more=>api(`/api/submissions/${form.dataset.sid}/accept`,{method:"POST",body:JSON.stringify({...body,...more})}));
    // Review 12c M1: every status change meets the work-in-progress limit, so these confirm too.
    else if(kind==="changes")outcome=await withConfirms(task,"progress",more=>api(`/api/submissions/${form.dataset.sid}/request-changes`,{method:"POST",body:JSON.stringify({...body,...more})}));
    else if(kind==="reopen")outcome=await withConfirms(task,"progress",more=>api(taskApi(task.id,"/reopen"),{method:"POST",body:JSON.stringify({...body,...more})}));
    else if(kind==="hold")outcome=await withConfirms(task,"blocked",more=>api(taskApi(task.id,"/hold"),{method:"POST",body:JSON.stringify({...body,...more})}));
    if(!outcome)return;   // an owner cancelled the dependency confirm
    const shown=await refreshDetail(task.id);
    if(shown&&outcome?.request){const current=document.querySelector("#lifecycle-error");current.classList.add("message-success");current.textContent=kind==="accept"
      ?"Owner request created. The submission is still awaiting an App Owner decision."
      :"Owner request created; the task is unchanged."}
  }catch(x){if(x.status===409)return reloadTaskAfterConflict(task.id,"lifecycle-error",x.message);err.textContent=x.message}
}

function buildAttachments(task){
  const canManageFiles=task.permissions?.can_manage_files;
  const frByAtt={};(task.final_results||[]).forEach(f=>{if(f.attachment_id)frByAtt[f.attachment_id]=f.id});
  const rows=(task.attachments||[]).map(a=>{
    const missing=a.exists===false?' <span class="blocked-text">(file not found)</span>':"";
    const note=a.note?`<br><em class="muted">${escapeHtml(a.note)}</em>`:"";
    const frCtl=!canManageFiles?"":frByAtt[a.id]
      ?`<span class="fr-tag">★ final result</span> <button type="button" class="link" data-unmark-fr="${escapeHtml(frByAtt[a.id])}">Unmark</button>`
      :`<button type="button" class="link" data-mark-fr-att="${escapeHtml(a.id)}">Mark as final result</button>`;
    const removeCtl=canManageFiles
      ?`<button type="button" class="link" data-remove-attachment="${escapeHtml(a.id)}">Remove</button>`:"";
    // MXY7BG Items 15-16: only the App Owner creates or revokes a permanent direct link; the
    // page shows that one exists, since when and by whom, never the link itself.
    const linkCtl=a.kind!=="file"?"":a.direct_link
      ?`<br><small class="muted">Direct link active since ${escapeHtml(new Date(a.direct_link.created_at).toLocaleString())} by ${escapeHtml(a.direct_link.created_by_name||"")}</small>${canManageFiles?` <button type="button" class="link" data-revoke-link="${escapeHtml(a.direct_link.id)}" data-att-name="${escapeHtml(a.display_name)}">Revoke direct link</button>`:""}`
      :canManageFiles?` <button type="button" class="link" data-direct-link="${escapeHtml(a.id)}" data-att-name="${escapeHtml(a.display_name)}">Create direct link</button>`:"";
    return `<li>${attachmentLine(task,a)}${missing}
      ${removeCtl}
      ${frCtl}${linkCtl}
      <br><small>Added by ${escapeHtml(a.added_by_name||"")} · ${escapeHtml(new Date(a.added_at).toLocaleString())}</small>${note}</li>`;
  }).join("")||"<li>No attachments linked.</li>";
  const pathForm=task.permissions?.can_link_paths?`<form id="attachment-form"><h4>Link a file on this computer</h4>
      <label>File path<input name="path" placeholder="C:\\folder\\deliverable.pdf" required></label>
      <div class="grid"><label>Display name (optional)<input name="display_name"></label>
        <label>Note (optional)<input name="note"></label></div>
      <div class="actions"><button>Link file</button></div></form>`:"";
  const form=canManageFiles?`<form id="upload-form"><h4>Upload a file</h4>
      <label>File (up to ${uploadLimitMb(task)} MB)<input name="file" type="file" required></label>
      <label>Note (optional)<input name="note"></label>
      <div class="actions"><button>Upload</button></div></form>
    <form id="link-form"><h4>Add a link</h4>
      <label>Link<input name="url" type="url" placeholder="https://" required></label>
      <div class="grid"><label>Display name (optional)<input name="display_name"></label>
        <label>Note (optional)<input name="note"></label></div>
      <div class="actions"><button>Add link</button></div></form>
    ${pathForm}<div class="error" id="attachment-error"></div>`:`<p class="blocked-text">Read/download only. File and final-result management is App Owner-only.</p><div class="error" id="attachment-error"></div>`;
  return `<div class="attachments"><h3>Attachments</h3>
    <ul>${rows}</ul>
    <div id="direct-link-panel" class="direct-link-panel" hidden></div>
    ${form}</div>`;
}
// MXY7BG Items 15-16: creating a direct link is a two-step act (warning, then confirm); the
// link is shown once with a copy button, because Astra keeps only its hash. Until the owner
// presses Done it is kept for its task: the other link buttons are off, and a redraw of the task
// (an upload, coming back to it) shows it again, so it is not lost before it has been copied.
const shownDirectLinks=new Map();
function directLinkPanel(html){const panel=document.querySelector("#direct-link-panel");if(!panel)return null;panel.innerHTML=html;panel.hidden=!html;return panel}
function closeDirectLinkPanel(trigger){directLinkPanel("");trigger?.focus?.()}
function setDirectLinkButtons(off){
  document.querySelectorAll("#detail-body [data-direct-link]").forEach(b=>{b.disabled=off});
  document.querySelectorAll("#detail-body [data-revoke-link]").forEach(b=>{b.disabled=off});
}
function showDirectLink(task,focus){
  const shown=shownDirectLinks.get(task.id);
  const panel=shown&&directLinkPanel(`<h4 id="direct-link-title" tabindex="-1">Direct link to ${escapeHtml(shown.name)}</h4>
      <p class="fine">Copy it now, then press Done. Astra keeps only a fingerprint of this link and cannot show it again; create a new one if it is lost. Anyone with it can download the file until it is revoked.</p>
      <p><code class="direct-link-url" id="direct-link-url">${escapeHtml(shown.url)}</code></p>
      <div class="actions"><button type="button" id="direct-link-copy">Copy link</button><button type="button" class="quiet" id="direct-link-done">Done</button></div>
      <p id="direct-link-status" class="form-hint" role="status"></p>`);
  if(!panel)return;
  setDirectLinkButtons(true);
  panel.querySelector("#direct-link-copy").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(shown.url);panel.querySelector("#direct-link-status").textContent="Copied."}catch{panel.querySelector("#direct-link-status").textContent="Select the link and copy it yourself."}});
  panel.querySelector("#direct-link-done").addEventListener("click",async()=>{
    shownDirectLinks.delete(task.id);
    if(detailTaskId!==task.id)return;
    directLinkPanel("");setDirectLinkButtons(false);await openDetail(task.id);
  });
  if(focus)panel.querySelector("#direct-link-title").focus();
}
let directLinkBusy=false;
async function createDirectLink(task,attachmentId,name,confirm,trigger){
  // One request at a time, with the link buttons off while it is on its way: a second answer
  // could otherwise replace the panel that shows the first link.
  if(directLinkBusy)return;
  directLinkBusy=true;setDirectLinkButtons(true);
  clearFeedback(document.querySelector("#attachment-error"));
  try{
    const {link}=await api(taskApi(task.id,`/attachments/${encodeURIComponent(attachmentId)}/direct-link`),{method:"POST",body:JSON.stringify(confirm?{confirm}:{})});
    shownDirectLinks.set(task.id,{linkId:link.id,name,url:`${location.origin}${link.url}`});
    if(detailTaskId===task.id)showDirectLink(task,true);
  }catch(x){
    // An answer belongs to the task it was asked on: another task's panel is left alone.
    if(detailTaskId!==task.id)return;
    if(x.status===409&&x.confirm){
      const panel=directLinkPanel(`<h4 id="direct-link-title" tabindex="-1">Create a direct link to ${escapeHtml(name)}?</h4>
        <p>${escapeHtml(x.message)}</p><ul class="fine">${(x.impact||[]).map(i=>`<li>${escapeHtml(i)}</li>`).join("")}</ul>
        <div class="actions"><button type="button" id="direct-link-confirm">Create the link</button><button type="button" class="quiet" id="direct-link-cancel">Cancel</button></div>`);
      if(!panel)return;
      panel.querySelector("#direct-link-confirm").addEventListener("click",()=>createDirectLink(task,attachmentId,name,x.confirm,trigger));
      panel.querySelector("#direct-link-cancel").addEventListener("click",()=>closeDirectLinkPanel(trigger));
      panel.querySelector("#direct-link-title").focus();
      return;
    }
    const err=document.querySelector("#attachment-error");if(err)err.textContent=x.message;
  }finally{
    directLinkBusy=false;
    if(detailTaskId===task.id&&!shownDirectLinks.has(task.id))setDirectLinkButtons(false);
  }
}
function askRevokeDirectLink(task,linkId,name,trigger){
  const panel=directLinkPanel(`<form id="revoke-link-form"><h4>Revoke the direct link to ${escapeHtml(name)}</h4>
    <p class="fine">Downloads through the link stop at once. The reason is recorded on the task and every App Owner is told.</p>
    <label>Reason<input name="reason" id="revoke-link-reason" maxlength="500" required></label>
    <div class="actions"><button>Revoke</button><button type="button" class="quiet" id="revoke-link-cancel">Cancel</button></div></form>`);
  if(!panel)return;
  panel.querySelector("#revoke-link-cancel").addEventListener("click",()=>closeDirectLinkPanel(trigger));
  panel.querySelector("#revoke-link-form").addEventListener("submit",async e=>{
    e.preventDefault();const err=document.querySelector("#attachment-error");clearFeedback(err);
    try{await api("/api/direct-links",{method:"DELETE",body:JSON.stringify({task_id:task.id,link_id:linkId,reason:e.target.elements.reason.value})});if(detailTaskId===task.id)await openDetail(task.id)}
    catch(x){err.textContent=x.message}
  });
  panel.querySelector("#revoke-link-reason").focus();
}

// MXY7BG: the installation's upload limit (Owner Item 8, set by the App Owner in People and
// access); a bigger file is shared as a link instead.
function uploadLimitMb(task){return Math.max(1,Math.floor((task.upload_limit_bytes||25*1048576)/1048576))}
function formatBytes(n){return n>=1048576?`${(n/1048576).toFixed(1)} MB`:n>=1024?`${Math.round(n/1024)} KB`:`${n} bytes`}
function attachmentLine(task,a){
  const name=escapeHtml(a.display_name);
  // A link opens in a new tab and Astra never fetches it (Items 12-13); a file downloads through
  // Astra after an access check (Item 14). Neither is ever described as safe or scanned (Item 11).
  if(a.kind==="link")return `<a href="${escapeHtml(a.url)}" target="_blank" rel="noopener noreferrer"><strong>${name}</strong></a>
      <br><small class="att-path">${escapeHtml(a.url)}</small>`;
  if(a.kind==="file")return `<a href="/api/tasks/${encodeURIComponent(task.id)}/attachments/${encodeURIComponent(a.id)}/download" download><strong>${name}</strong></a>
      <small class="muted">${escapeHtml(formatBytes(a.size_bytes||0))}</small>`;
  if(!a.path)return `<strong>${name}</strong><br><small class="muted">Local file link, not available on this server.</small>`;
  return `<strong>${name}</strong><br>
      <code class="att-path">${escapeHtml(a.path)}</code>
      <button type="button" class="link" data-copy-path="${escapeHtml(a.path)}">Copy path</button>`;
}
async function uploadAttachment(taskId,file,note){
  const response=await fetch(taskApi(taskId,"/files"),{method:"POST",body:file,headers:{
    "X-CSRF-Token":state.csrf||"","Content-Type":file.type||"application/octet-stream",
    "X-Filename":encodeURIComponent(file.name),"X-Note":encodeURIComponent(note||"")}});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.error||"Upload failed.");
  return data;
}
async function wireAttachments(task){
  const refresh=async()=>{if(detailTaskId===task.id)await openDetail(task.id)};
  document.querySelector("#upload-form")?.addEventListener("submit",async e=>{
    e.preventDefault();const err=document.querySelector("#attachment-error");clearFeedback(err);
    const form=e.target,file=form.querySelector('[name="file"]').files[0];
    if(!file){err.textContent="Choose a file.";return}
    const limitMb=uploadLimitMb(task);
    if(file.size>limitMb*1048576){err.textContent=`The file is larger than ${limitMb} MB. Put it in a shared folder and add a link to it instead.`;return}
    const button=form.querySelector("button");button.disabled=true;button.textContent="Uploading…";
    try{await uploadAttachment(task.id,file,form.querySelector('[name="note"]').value);await refresh()}
    catch(x){err.textContent=x.message;button.disabled=false;button.textContent="Upload"}
  });
  document.querySelector("#link-form")?.addEventListener("submit",async e=>{
    e.preventDefault();const err=document.querySelector("#attachment-error");clearFeedback(err);
    try{await api(taskApi(task.id,"/links"),{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await refresh()}
    catch(x){err.textContent=x.message}
  });
  document.querySelector("#attachment-form")?.addEventListener("submit",async e=>{
    e.preventDefault();const err=document.querySelector("#attachment-error");clearFeedback(err);
    try{await api(taskApi(task.id,"/attachments"),{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});if(detailTaskId===task.id)await openDetail(task.id)}
    catch(x){err.textContent=x.message}
  });
  document.querySelectorAll("#detail-body [data-direct-link]").forEach(b=>b.addEventListener("click",()=>createDirectLink(task,b.dataset.directLink,b.dataset.attName,undefined,b)));
  document.querySelectorAll("#detail-body [data-revoke-link]").forEach(b=>b.addEventListener("click",()=>askRevokeDirectLink(task,b.dataset.revokeLink,b.dataset.attName,b)));
  // A link still waiting to be copied comes back with the redrawn task. It is dropped when the
  // viewer can no longer manage files, or when the link is gone from the file. This redraw may
  // hold data read before the link was made, so "gone" takes a second, fresh look.
  const shown=shownDirectLinks.get(task.id);
  if(shown){
    if(!task.permissions?.can_manage_files)shownDirectLinks.delete(task.id);
    else if((task.attachments||[]).some(a=>a.direct_link?.id===shown.linkId))showDirectLink(task);
    else if(shown.rechecked)shownDirectLinks.delete(task.id);
    else if(detailTaskId===task.id){shown.rechecked=true;openDetail(task.id)}
  }
  document.querySelectorAll("#detail-body [data-remove-attachment]").forEach(b=>b.addEventListener("click",async()=>{
    try{await api("/api/task-attachments",{method:"DELETE",body:JSON.stringify({task_id:task.id,attachment_id:b.dataset.removeAttachment})});if(detailTaskId===task.id)await openDetail(task.id)}
    catch(x){document.querySelector("#attachment-error").textContent=x.message}
  }));
  document.querySelectorAll("#detail-body [data-copy-path]").forEach(b=>b.addEventListener("click",async()=>{
    try{await navigator.clipboard.writeText(b.dataset.copyPath);b.textContent="Copied";setTimeout(()=>{b.textContent="Copy path"},1200)}
    catch{const err=document.querySelector("#attachment-error");if(err)err.textContent="Copy failed — select the path and copy manually."}
  }));
}

function wireReviewers(task){
  // Only people who may add reviewers load the list (the Chairman and members are refused it).
  if((task.permissions||{}).can_edit_ordinary)fillAssignees(task.project_id,document.querySelector("#reviewer-user"),"","reviewer");
  document.querySelector("#add-reviewer-button")?.addEventListener("click",async()=>{
    const err=document.querySelector("#reviewer-error");clearFeedback(err);
    const picker=document.querySelector("#reviewer-user");if(picker.disabled){err.textContent="Load the people list before adding a reviewer. Use Retry people.";return}
    const user_id=document.querySelector("#reviewer-user").value,role=document.querySelector("#reviewer-role").value;
    try{await api("/api/task-reviewers",{method:"POST",body:JSON.stringify({task_id:task.id,user_id,role})});if(detailTaskId===task.id)await openDetail(task.id)}
    catch(x){err.textContent=x.message}
  });
  document.querySelectorAll("#detail-body [data-remove-reviewer-user]").forEach(b=>b.addEventListener("click",async()=>{
    try{await api("/api/task-reviewers",{method:"DELETE",body:JSON.stringify({task_id:task.id,user_id:b.dataset.removeReviewerUser,role:b.dataset.removeReviewerRole})});if(detailTaskId===task.id)await openDetail(task.id)}
    catch(x){document.querySelector("#reviewer-error").textContent=x.message}
  }));
}

// Aly, 2026-11-17: a download through a direct link names no person; nobody was signed in.
const NO_PERSON_EVENTS=new Set(["attachment_direct_download"]);
function renderEvent(ev){
  const when=new Date(ev.occurred_at).toLocaleString();
  const who=NO_PERSON_EVENTS.has(ev.event_type)?"":(ev.actor_name||"Unknown");
  const label=EVENT_LABELS[ev.event_type]||ev.event_type;
  let detail="";
  if(ev.event_type==="task_updated"){
    const before=safeParse(ev.before_json),after=safeParse(ev.after_json);
    const changes=DIFF_FIELDS.filter(([k])=>String(before[k]??"")!==String(after[k]??""))
      .map(([k,l])=>`${escapeHtml(l)}: ${escapeHtml(String(before[k]??"—"))} → ${escapeHtml(String(after[k]??"—"))}`);
    if((before.owner_user_id||null)!==(after.owner_user_id||null)){const owner=t=>t.owner_user_id?`${t.owner_name||"Person"} (${t.owner_user_id})`:"Unassigned";changes.push(`Owner: ${escapeHtml(owner(before))} → ${escapeHtml(owner(after))}`)}
    detail=changes.length?`<br>${changes.join("<br>")}`:"<br>No field changes.";
  }else if(ev.event_type==="dependency_added"){
    const a=safeParse(ev.after_json);detail=`<br>Predecessor: ${escapeHtml(a.predecessor_task_id||"")}`;
  }else if(ev.event_type==="dependency_removed"){
    const b=safeParse(ev.before_json);detail=`<br>Removed predecessor: ${escapeHtml(b.predecessor_task_id||"")}`;
  }
  const reason=ev.reason?`<br><em>Reason: ${escapeHtml(ev.reason)}</em>`:"";
  return `<li><strong>${escapeHtml(label)}</strong> · ${escapeHtml(when)}${who?` · ${escapeHtml(who)}`:""}${reason}${detail}</li>`;
}

function safeParse(text){try{return text?JSON.parse(text):{}}catch{return{}}}

// Review 12a M1: the panel meets the same dependency rule as the board. An owner confirms the
// override (recorded and noticed); a manager sees the server's refusal.
const STATUS_COLUMN={in_progress:"progress",submitted:"submitted",completed:"accepted"};
const COLUMN_OF_STATUS={draft:"draft",assigned:"ready",in_progress:"progress",delayed:"progress",on_hold:"blocked",submitted:"submitted"};
// Review 12b L2: the same loop answers a date change's consequences ("impact") and a
// work-in-progress limit ("wip"), each confirmed once, in turn.
const CONFIRM_FLAGS={dependencies:"override_dependencies",wip:"override_wip",impact:"confirmed"};
async function withConfirms(task,column,send,extra){
  let more={};
  for(;;){
    try{return await send(more)}
    catch(err){
      const flag=CONFIRM_FLAGS[err.confirm];
      if(err.status!==409||!flag||more[flag])throw err;
      const ok=await askMove(err.confirm,task||{title:""},column,{...err,...(extra||{})});
      if(!ok)return null;
      more={...more,...ok};
    }
  }
}
function withDependencyConfirm(task,status,send,extra){return withConfirms(task,STATUS_COLUMN[status]||COLUMN_OF_STATUS[status]||"progress",send,extra)}
async function submitDetailEdit(e,{statusLocked=false}={}){
  const taskId=e.target.dataset.taskId||detailTaskId;
  e.preventDefault();
  const form=e.target,error=document.querySelector("#detail-edit-error");clearFeedback(error);
  const body=Object.fromEntries(new FormData(form));
  if(statusLocked)delete body.status; // shown for context only; Accept or Request changes moves it
  body.expected_revision=Number(body.expected_revision);
  // Review 13a L1: an empty date field is no date (null), so a title-only save needs no reason.
  for(const k of ["start_date","due_date"])if(k in body&&!body[k])body[k]=null;
  try{
    const outcome=await withDependencyConfirm(panelState.task,body.status,more=>api(taskApi(taskId),{method:"POST",body:JSON.stringify({...body,...more})}),
      {dates:{start_date:body.start_date||null,due_date:body.due_date||null}});
    if(!outcome)return;
    await dropLease(taskId,"edit");
    const shown=await refreshDetail(taskId);
    if(shown&&outcome.request){const current=document.querySelector("#detail-edit-error");if(current){current.classList.add("message-success");current.textContent="Owner request created; accepted live state is unchanged."}}
  }catch(err){if(err.status===409)return reloadTaskAfterConflict(taskId,"detail-edit-error",err.message);error.textContent=err.message}
}

// 3FQEKB: the Chairman's assign-only save sends the assignee, a reason and the revision.
async function submitAssign(e){
  const taskId=e.target.dataset.taskId||detailTaskId;
  e.preventDefault();
  const form=e.target,error=document.querySelector("#detail-assign-error");clearFeedback(error);
  const picker=form.querySelector('select[name="owner_user_id"]');if(picker?.disabled){error.textContent="Load the people list before saving an assignment. Use Retry people.";return}
  const data=Object.fromEntries(new FormData(form));
  const body={owner_user_id:data.owner_user_id||null,reason:data.reason||"",expected_revision:Number(data.expected_revision)};
  try{
    await api(taskApi(taskId),{method:"POST",body:JSON.stringify(body)});
    await refreshDetail(taskId);showToast("Assignee saved.");
  }catch(err){if(err.status===409)return reloadTaskAfterConflict(taskId,"detail-assign-error",err.message);error.textContent=err.message}
}

async function addDependency(){
  const taskId=detailTaskId;
  const select=document.querySelector("#add-dep-select"),error=document.querySelector("#dep-error");clearFeedback(error);
  const predecessor=select.value;
  if(!predecessor){error.textContent="Choose a predecessor task.";return}
  try{
    await api("/api/task-dependencies",{method:"POST",body:JSON.stringify({predecessor_task_id:predecessor,successor_task_id:taskId})});
    await refreshDetail(taskId);
  }catch(err){error.textContent=err.message}
}

async function removeDependency(e){
  const taskId=detailTaskId;
  const button=e.target,error=document.querySelector("#dep-error");clearFeedback(error);
  const reason=button.parentElement.querySelector(".dep-reason").value;
  try{
    await api("/api/task-dependencies",{method:"DELETE",body:JSON.stringify({predecessor_task_id:button.dataset.removePred,successor_task_id:button.dataset.removeSucc,reason})});
    await refreshDetail(taskId);
  }catch(err){error.textContent=err.message}
}

document.querySelector("#people-body").addEventListener("click",e=>{const button=e.target.closest("[data-admin-section]");if(button){const section=document.querySelector("#admin-"+button.dataset.adminSection);section?.scrollIntoView({block:"start"});section?.focus({preventScroll:true})}if(e.target.id==="admin-templates"||e.target.id==="admin-results"){document.querySelector("#people-dialog").close();if(e.target.id==="admin-templates")openTemplates();else openFinalResults()}});
async function openPeople(){
  try{
    const [u,m,h]=await Promise.all([api("/api/users"),api("/api/memberships"),api("/api/user-events")]);
    renderPeople(u.users,m.memberships,h.events);
    const d=document.querySelector("#people-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#people-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
}
async function loadDailyDigestSettings(){
  const form=document.querySelector("#daily-digest-settings-form");if(!form)return;
  const error=document.querySelector("#daily-digest-settings-error"),status=document.querySelector("#daily-digest-settings-status");
  try{
    const {settings}=await api("/api/daily-digest/settings");
    if(!form.isConnected)return;
    form.elements.enabled.checked=!!settings.enabled;form.elements.delivery_time.value=settings.delivery_time||"09:00";
    form.elements.timezone.value=settings.timezone||"Asia/Karachi";
    status.textContent=settings.updated_at?`Last saved ${new Date(settings.updated_at).toLocaleString()}.`:"Daily summary is on by default at 09:00.";
    error.textContent="";
  }catch(err){error.textContent=`Settings could not be loaded. ${err.message}`}
  form.addEventListener("submit",saveDailyDigestSettings);
}
// MXY7BG slice 2: the App Owner's upload limit and denylist additions (Owner Items 8-9).
function fillAttachmentSettings(form,settings){
  form.elements.upload_limit_mb.value=settings.upload_limit_mb;form.elements.upload_limit_mb.max=settings.server_ceiling_mb;
  const lowered=settings.saved_limit_mb&&settings.saved_limit_mb!==settings.upload_limit_mb?` Your saved limit of ${settings.saved_limit_mb} MB is applied as ${settings.upload_limit_mb} MB because of the ceiling.`:"";
  document.querySelector("#attachment-ceiling").textContent=`This server admits uploads up to ${settings.server_ceiling_mb} MB; the ceiling itself is raised on the server, never here (deployment runbook, stage 9), and can never exceed ${settings.hard_limit_mb} MB.${lowered}`;
  document.querySelector("#attachment-settings-error").textContent=settings.unusable||"";
  form.elements.blocked_extensions.value=(settings.blocked_extensions||[]).join("\n");
  form.elements.blocked_mime_types.value=(settings.blocked_mime_types||[]).join("\n");
  const builtin=settings.builtin_extensions||[];
  document.querySelector("#attachment-builtin-summary").textContent=`Always blocked, whatever is entered here: ${builtin.length} file types`;
  document.querySelector("#attachment-builtin").textContent=builtin.join(" ");
}
async function loadAttachmentSettings(){
  const form=document.querySelector("#attachment-settings-form");if(!form)return;
  const error=document.querySelector("#attachment-settings-error"),status=document.querySelector("#attachment-settings-status");
  try{
    const {settings}=await api("/api/attachment-settings");
    if(!form.isConnected)return;
    fillAttachmentSettings(form,settings);
    status.textContent=settings.updated_at?`Last saved ${new Date(settings.updated_at).toLocaleString()} by ${settings.updated_by_name||"an owner"}.`:`Default: ${settings.default_limit_mb} MB, nothing added to the blocked list.`;
  }catch(err){error.textContent=`Settings could not be loaded. ${err.message}`}
  form.addEventListener("submit",saveAttachmentSettings);
}
async function saveAttachmentSettings(event){
  event.preventDefault();
  const form=event.currentTarget,error=document.querySelector("#attachment-settings-error"),status=document.querySelector("#attachment-settings-status");
  error.textContent="";status.textContent="Saving…";
  try{
    const {settings}=await api("/api/attachment-settings",{method:"PUT",body:JSON.stringify({upload_limit_mb:form.elements.upload_limit_mb.value.trim(),blocked_extensions:form.elements.blocked_extensions.value,blocked_mime_types:form.elements.blocked_mime_types.value})});
    fillAttachmentSettings(form,settings);
    status.textContent=`Saved. Uploads up to ${settings.upload_limit_mb} MB; ${settings.blocked_extensions.length} extension${settings.blocked_extensions.length===1?"":"s"} and ${settings.blocked_mime_types.length} media type${settings.blocked_mime_types.length===1?"":"s"} added to the blocked list.`;
  }catch(err){status.textContent="";error.textContent=`Settings were not saved. ${err.message}`}
}
async function saveDailyDigestSettings(event){
  event.preventDefault();
  const form=event.currentTarget,error=document.querySelector("#daily-digest-settings-error"),status=document.querySelector("#daily-digest-settings-status");
  error.textContent="";status.textContent="Saving…";
  try{
    const {settings}=await api("/api/daily-digest/settings",{method:"POST",body:JSON.stringify({enabled:form.elements.enabled.checked,delivery_time:form.elements.delivery_time.value,timezone:form.elements.timezone.value})});
    form.elements.enabled.checked=!!settings.enabled;form.elements.delivery_time.value=settings.delivery_time;form.elements.timezone.value=settings.timezone;
    status.textContent=`Saved. The summary is ${settings.enabled?"on":"off"} for ${settings.delivery_time} ${settings.timezone}.`;
  }catch(err){status.textContent="";error.textContent=`Settings were not saved. ${err.message}`}
}

// GTEYTG: every owner has role "owner"; only the primary owner may give or remove owner access.
const OWNER_EVENT_LABELS={secondary_owner_granted:"Made secondary owner",secondary_owner_revoked:"Owner access removed",owner_change_blocked:"Blocked owner change",import_blocked:"Blocked import without a project",primary_owner_transferred:"Primary owner transferred",password_reset:"Password reset",password_changed:"Password changed",entity_active_changed:"Entity active state changed",entity_renamed:"Entity renamed",import_template_config_changed:"Import template settings changed",daily_digest_settings_changed:"Daily summary settings changed",attachment_settings_changed:"Attachment settings changed",storage_migrated:"Uploaded files moved",storage_pruned:"Old copies of uploaded files removed"};
// PDDS2D/3M2AYA: a password reset is either a server command or done in the app by an owner.
const viaServerCommand=e=>["primary_owner_transferred","password_reset","storage_migrated","storage_pruned"].includes(e.event_type)&&e.reason==="server command";
// MXY7BG slice 4: a storage command's row says where the files went and how many, in place of
// the name of the owner whose record carries the audit row.
const storageEvent=e=>e.event_type==="storage_migrated"||e.event_type==="storage_pruned";
function storageEventText(e){
  const d=safeParse(e.detail_json),n=v=>Number(v)||0;
  const cut=d.interrupted===true?", interrupted before it finished":"";
  if(e.event_type==="storage_pruned")return `${n(d.pruned)} removed, ${n(d.failed)} failed${cut}`;
  return `to ${d.target==="s3"?"object storage":"the server folder"} (${n(d.moved)} copied and verified, ${n(d.restored)} switched back to a kept copy, ${n(d.failed)} failed${cut})`;
}
const MIN_PASSWORD=8;
function renderPeople(users,memberships,ownerEvents){
  const primary=!!state.user.is_primary_owner;
  const timeZones=[...new Set(["Asia/Karachi","UTC",...(Intl.supportedValuesOf?Intl.supportedValuesOf("timeZone"):[])])].sort();
  const digestTimeZoneOptions=timeZones.map(zone=>`<option value="${escapeHtml(zone)}"></option>`).join("");
  const rows=users.map(u=>{
    const isOwner=u.global_role==="owner",id=escapeHtml(u.id);
    const role=isOwner?`<span class="badge" data-level="${u.is_primary_owner?"ok":"info"}">${u.is_primary_owner?"Primary owner":"Secondary owner"}</span>`:escapeHtml(u.global_role);
    const toggle=isOwner?"":`<button type="button" class="link" data-toggle="${id}" data-active="${u.active?1:0}">${u.active?"Deactivate":"Reactivate"}</button>`;
    const ownerAction=!primary||u.is_primary_owner?"":isOwner?`<button type="button" class="link" data-owner-revoke="${id}">Remove secondary owner</button>`
      :u.active?`<button type="button" class="link" data-owner-grant="${id}">Make secondary owner</button>`:"";
    const reset=canResetPassword(u,primary)?`<button type="button" class="link" data-reset-password="${id}">Reset password</button>`:"";
    return `<li class="user-row"><span><strong>${escapeHtml(u.display_name)}</strong> · ${escapeHtml(u.email)} · ${role}${u.active?"":' · <em>inactive</em>'}</span><span class="row-actions">${toggle}${ownerAction}${reset}</span></li>`;
  }).join("");
  const ownerEventLabel=e=>{
    if(e.event_type==="owner_change_blocked"){try{if(JSON.parse(e.detail_json||"{}").action==="password reset of the primary owner")return "Blocked password reset of the primary owner"}catch{}}
    return OWNER_EVENT_LABELS[e.event_type]||e.event_type;
  };
  const ownerEventRow=e=>{let change="";if(e.detail_json){const d=safeParse(e.detail_json),b=d.before,a=d.after;if(b&&a)change=` · ${escapeHtml(JSON.stringify(b))} → ${escapeHtml(JSON.stringify(a))}`;}return `<li>${escapeHtml(new Date(e.occurred_at).toLocaleString())} · ${escapeHtml(ownerEventLabel(e))}${e.event_type==="import_blocked"?"":storageEvent(e)?`: ${escapeHtml(storageEventText(e))}`:`: <strong>${escapeHtml(e.target_name)}</strong>`}${viaServerCommand(e)?" via server command":` by ${escapeHtml(e.actor_name)}`}${e.reason&&!viaServerCommand(e)?` · ${escapeHtml(e.reason)}`:""}${change}</li>`};
  const blocked=e=>e.event_type==="owner_change_blocked"||e.event_type==="import_blocked";
  const settingEvents=new Set(["entity_active_changed","entity_renamed","import_template_config_changed","daily_digest_settings_changed","attachment_settings_changed"]);
  const ownerHistory=(ownerEvents||[]).filter(e=>!blocked(e)&&!settingEvents.has(e.event_type)).slice(0,20).map(ownerEventRow).join("")||"<li>No owner access changes yet.</li>";
  const settingsHistory=(ownerEvents||[]).filter(e=>settingEvents.has(e.event_type)).slice(0,20).map(ownerEventRow).join("")||"<li>No app setting changes yet.</li>";
  const blockedList=type=>(ownerEvents||[]).filter(e=>e.event_type===type).slice(0,10).map(ownerEventRow).join("")||"<li>None.</li>";
  const blockedHistory=blockedList("owner_change_blocked"),blockedImports=blockedList("import_blocked");
  const resetOptions=users.filter(u=>canResetPassword(u,primary)).map(u=>`<option value="${escapeHtml(u.id)}" data-name="${escapeHtml(u.display_name)}">${escapeHtml(u.display_name)} · ${escapeHtml(u.email)}</option>`).join("");
  // Only the primary may change an owner's project access, so others are not offered it.
  const ownerIds=new Set(users.filter(u=>u.global_role==="owner").map(u=>u.id));
  const userOptions=users.filter(u=>u.active&&(primary||!ownerIds.has(u.id))).map(u=>`<option value="${escapeHtml(u.id)}">${escapeHtml(personLabel(u,users))}</option>`).join("");
  const projectOptions=state.projects.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  const grants=memberships.map(m=>`<li>${escapeHtml(m.project_name)} · ${escapeHtml(m.user_name)} · ${escapeHtml(m.role)} ${!primary&&ownerIds.has(m.user_id)?"":`<button type="button" class="link" data-revoke-project="${escapeHtml(m.project_id)}" data-revoke-user="${escapeHtml(m.user_id)}">Revoke</button>`}</li>`).join("")||"<li>No access grants yet.</li>";
  const entityRows=(state.entities||[]).map(e=>`<li><strong>${escapeHtml(e.name)}</strong>${e.active?"":' · <em>inactive</em>'} <button type="button" class="link" data-entity-toggle="${escapeHtml(e.id)}" data-active="${e.active?1:0}">${e.active?"Deactivate":"Reactivate"}</button></li>`).join("")||"<li>No entities yet.</li>";
  const filingProjectOptions=state.projects.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  document.querySelector("#people-body").innerHTML=`
    <h2>People &amp; access</h2>
    <nav class="admin-sections" aria-label="Administration sections">${[["users","People"],["access","Project access"],["entities","Entities"],["calendar","Calendars"],["history","History"],...(primary?[["digest","Daily summary"]]:[]),["attachments","Attachments"]].map(([id,label])=>`<button type="button" class="quiet" data-admin-section="${id}">${label}</button>`).join("")}<button type="button" class="quiet" id="admin-templates">Templates</button><button type="button" class="quiet" id="admin-results">Final results</button></nav>
    ${primary?`<section class="daily-digest-settings" aria-labelledby="admin-digest"><h3 id="admin-digest" tabindex="-1">Daily summary</h3><p class="fine">Astra adds one private in-app summary to your Inbox each day. It never emails anyone or adds other recipients.</p><form id="daily-digest-settings-form"><label class="checkbox"><input name="enabled" type="checkbox"> Send me the daily summary</label><label>Delivery time<input name="delivery_time" type="time" required></label><label>Your time zone<input name="timezone" list="daily-digest-timezones" placeholder="Start typing a city or time zone" required></label><datalist id="daily-digest-timezones">${digestTimeZoneOptions}</datalist><p class="fine">Choose your local time zone, such as Asia/Karachi or America/Chicago.</p><div class="error" id="daily-digest-settings-error" role="alert"></div><p id="daily-digest-settings-status" class="form-hint" role="status"></p><div class="actions"><button>Save summary settings</button></div></form></section>`:""}
    <section class="attachment-settings" aria-labelledby="admin-attachments"><h3 id="admin-attachments" tabindex="-1">Attachments</h3><p class="fine">Uploads larger than the limit or of a blocked type are refused and nothing is kept. Astra does not scan files and never calls one safe.</p><form id="attachment-settings-form"><label>Upload limit in MB<input name="upload_limit_mb" type="number" min="1" max="250" step="1" inputmode="numeric" required></label><p class="fine" id="attachment-ceiling"></p><label>Also block these file extensions, one per line<textarea name="blocked_extensions" rows="3" placeholder=".xyz"></textarea></label><label>Also block these declared media types, one per line<textarea name="blocked_mime_types" rows="3" placeholder="application/x-example"></textarea></label><details class="fine"><summary id="attachment-builtin-summary">Always blocked, whatever is entered here</summary><p id="attachment-builtin" class="builtin-list"></p></details><div class="error" id="attachment-settings-error" role="alert"></div><p id="attachment-settings-status" class="form-hint" role="status"></p><div class="actions"><button>Save attachment settings</button></div></form></section>
    <h3 id="admin-users" tabindex="-1">Users</h3><ul class="people-list">${rows}</ul>
    <h3 id="admin-history" tabindex="-1">Owner access history</h3><ul class="people-list">${ownerHistory}</ul>
    <h3>Settings history</h3><ul class="people-list">${settingsHistory}</ul>
    <h3>Blocked owner-access attempts</h3><ul class="people-list">${blockedHistory}</ul>
    <h3>Blocked imports without a project</h3><ul class="people-list">${blockedImports}</ul>
    <form id="add-user-form"><h3>Add a user</h3><p class="form-hint">The user must change this temporary password after signing in before Astra opens.</p>
      <label>Email<input name="email" type="email" required></label>
      <label>Display name<input name="display_name" required></label>
      <label>Temporary password (min ${MIN_PASSWORD} characters)<input name="password" type="password" minlength="${MIN_PASSWORD}" autocomplete="new-password" required></label>
      <label>Role<select name="role"><option value="member">Member</option><option value="chairman">Chairman</option></select></label>
      <div class="actions"><button value="add">Create user</button></div><div class="error" id="add-user-error"></div></form>
    <form id="reset-password-form"><h3>Reset a password</h3>
      <p class="form-hint">For someone who has forgotten theirs. Other sessions are signed out; after signing in with the temporary password, they must choose a new one before using Astra.</p>
      <label>User<select name="user_id" id="reset-password-user" required><option value="">Choose a user…</option>${resetOptions}</select></label>
      <div class="grid">
        <label>New password (min ${MIN_PASSWORD} characters)<input name="password" type="password" minlength="${MIN_PASSWORD}" autocomplete="new-password" required></label>
        <label>Confirm new password<input name="confirm" type="password" minlength="${MIN_PASSWORD}" autocomplete="new-password" required></label>
      </div>
      <div class="actions"><button value="reset">Reset password</button></div><div class="error" id="reset-password-error" role="status"></div></form>
    <form id="grant-form"><h3 id="admin-access" tabindex="-1">Grant project access</h3>
      <div class="grid">
        <label>User<select name="user_id" required>${userOptions}</select></label>
        <label>Project<select name="project_id" required>${projectOptions}</select></label>
        <label>Role<select name="role"><option value="manager">Manager</option><option value="member">Member</option><option value="viewer">Viewer</option></select></label>
      </div>
      <div class="actions"><button value="grant">Grant access</button></div><div class="error" id="grant-error"></div></form>
    <h3>Current access</h3><ul class="people-list">${grants}</ul>
    <h3 id="admin-entities" tabindex="-1">Entities</h3><ul class="people-list">${entityRows}</ul>
    <form id="add-entity-form">
      <label>New entity name<input name="name" required></label>
      <div class="actions"><button value="add">Add entity</button><button type="button" id="seed-entities" class="quiet">Seed approved entities</button></div>
      <div class="error" id="entity-error"></div></form>
    <form id="rename-entity-form"><h3>Rename an entity</h3>
      <label>Entity to rename<select name="entity_id" required><option value="">Choose an entity…</option>${(state.entities||[]).map(e=>`<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)}</option>`).join("")}</select></label>
      <label>New name<input name="name" required></label>
      <p class="fine">Renaming keeps its projects and task links. The old and new names are recorded in Settings history.</p>
      <div class="actions"><button>Rename entity</button></div>
      <div class="error" id="rename-entity-error" role="alert"></div></form>
    <form id="filing-form"><h3>Project filing (entities)</h3>
      <label>Project<select id="filing-project"><option value="">Choose a project…</option>${filingProjectOptions}</select></label>
      <div id="filing-entities" class="filing-entities"></div>
      <div class="actions"><button value="save">Save filing</button></div>
      <div class="error" id="filing-error"></div></form>
    <form id="calendar-form"><h3 id="admin-calendar" tabindex="-1">Project calendar (working days &amp; holidays)</h3>
      <label>Project<select id="calendar-project"><option value="">Choose a project…</option>${filingProjectOptions}</select></label>
      <p class="fine">Every day counts by default. Uncheck days or add holidays only if this project should skip them.</p>
      <div id="calendar-body"></div>
      <div class="error" id="calendar-error"></div></form>`;
  document.querySelector("#add-user-form").addEventListener("submit",submitAddUser);
  document.querySelector("#reset-password-form").addEventListener("submit",submitResetPassword);
  document.querySelectorAll("#people-body [data-reset-password]").forEach(b=>b.addEventListener("click",()=>chooseResetUser(b.dataset.resetPassword)));
  document.querySelector("#grant-form").addEventListener("submit",submitGrant);
  document.querySelectorAll("#people-body [data-toggle]").forEach(b=>b.addEventListener("click",toggleUserActive));
  document.querySelectorAll("#people-body [data-owner-grant],#people-body [data-owner-revoke]").forEach(b=>b.addEventListener("click",changeOwnerAccess));
  document.querySelectorAll("#people-body [data-revoke-project]").forEach(b=>b.addEventListener("click",revokeAccess));
  document.querySelector("#add-entity-form").addEventListener("submit",submitAddEntity);
  document.querySelector("#rename-entity-form").addEventListener("submit",submitRenameEntity);
  document.querySelector("#seed-entities").addEventListener("click",seedEntities);
  document.querySelectorAll("#people-body [data-entity-toggle]").forEach(b=>b.addEventListener("click",toggleEntityActive));
  document.querySelector("#filing-project").addEventListener("change",e=>renderFilingEntities(e.target.value));
  document.querySelector("#filing-form").addEventListener("submit",submitFiling);
  document.querySelector("#calendar-project").addEventListener("change",e=>renderCalendar(e.target.value));
  document.querySelector("#calendar-form").addEventListener("submit",e=>e.preventDefault());
  if(primary)loadDailyDigestSettings();
  loadAttachmentSettings();
}

async function renderCalendar(projectId){
  const body=document.querySelector("#calendar-body"),err=document.querySelector("#calendar-error");clearFeedback(err);
  if(!projectId){body.innerHTML="";return}
  try{
    const {calendar}=await api(`/api/projects/${projectId}/calendar`);
    const working=new Set((calendar.working_days||"0123456").split("").map(Number));
    const names=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
    const boxes=names.map((n,i)=>`<label class="checkbox"><input type="checkbox" class="wd" value="${i}"${working.has(i)?" checked":""}> ${n}</label>`).join("");
    const holidays=(calendar.holidays||[]).map(h=>`<li>${escapeHtml(h.holiday_date)}${h.label?" · "+escapeHtml(h.label):""} <button type="button" class="link" data-remove-holiday="${escapeHtml(h.holiday_date)}">Remove</button></li>`).join("")||"<li>No holidays (every day counts).</li>";
    body.innerHTML=`<div class="filing-entities">${boxes}</div>
      <div class="actions"><button type="button" id="save-working-days">Save working days</button></div>
      <ul class="people-list">${holidays}</ul>
      <div class="add-reviewer"><input id="holiday-date" type="date"><input id="holiday-label" placeholder="Label (optional)"><button type="button" id="add-holiday-btn">Add holiday</button></div>`;
    document.querySelector("#save-working-days").addEventListener("click",()=>saveWorkingDays(projectId));
    document.querySelector("#add-holiday-btn").addEventListener("click",()=>addHoliday(projectId));
    body.querySelectorAll("[data-remove-holiday]").forEach(b=>b.addEventListener("click",()=>removeHoliday(projectId,b.dataset.removeHoliday)));
  }catch(x){err.textContent=x.message}
}
async function saveWorkingDays(projectId){
  const days=[...document.querySelectorAll("#calendar-body .wd:checked")].map(i=>i.value).join("");
  try{await api(`/api/projects/${projectId}/working-days`,{method:"POST",body:JSON.stringify({days})});await renderCalendar(projectId)}
  catch(x){document.querySelector("#calendar-error").textContent=x.message}
}
async function addHoliday(projectId){
  const date=document.querySelector("#holiday-date").value,label=document.querySelector("#holiday-label").value;
  if(!date){document.querySelector("#calendar-error").textContent="Pick a date.";return}
  try{await api(`/api/projects/${projectId}/holidays`,{method:"POST",body:JSON.stringify({date,label})});await renderCalendar(projectId)}
  catch(x){document.querySelector("#calendar-error").textContent=x.message}
}
async function removeHoliday(projectId,date){
  try{await api("/api/project-holidays",{method:"DELETE",body:JSON.stringify({project_id:projectId,date})});await renderCalendar(projectId)}
  catch(x){document.querySelector("#calendar-error").textContent=x.message}
}

function renderFilingEntities(projectId){
  const container=document.querySelector("#filing-entities");
  if(!projectId){container.innerHTML="";return}
  const project=state.projects.find(p=>p.id===projectId)||{};
  const current=projectEntityIds(projectId);
  const boxes=(state.entities||[]).filter(e=>e.active).map(e=>
    `<label class="checkbox"><input type="checkbox" value="${escapeHtml(e.id)}"${current.has(e.id)?" checked":""}> ${escapeHtml(e.name)}</label>`
  ).join("")||"<p>No active entities. Add or seed entities first.</p>";
  const linked=project.entities||[];
  const primaryOptions=linked.map(e=>`<option value="${escapeHtml(e.id)}"${e.id===project.primary_entity_id?" selected":""}>${escapeHtml(e.name)}</option>`).join("");
  container.innerHTML=`${boxes}
    <div class="budget-block">
      <label>Budget amount<input id="budget-amount" type="number" min="0" step="any" value="${project.budget_amount==null?"":project.budget_amount}"></label>
      <label>Currency<input id="budget-currency" value="${escapeHtml(project.budget_currency||"PKR")}" maxlength="3"></label>
      <label>Primary entity (budget rolls up here)<select id="primary-entity"><option value="">— none —</option>${primaryOptions}</select></label>
      <div class="actions"><button type="button" id="save-budget">Save budget &amp; primary</button></div>
      <div class="error" id="budget-error"></div>
    </div>
    <div class="budget-block">
      <div class="grid">
        <label>Project start date<input id="project-start" type="date" value="${escapeHtml(project.start_date||"")}"></label>
        <label>Agreed project deadline<input id="project-target" type="date" value="${escapeHtml(project.target_date||"")}"${isOwner()?"":" readonly"}></label>
      </div>
      <label>Reason for date change<input id="project-schedule-reason" placeholder="Required to change project dates"></label>
      <div class="actions"><button type="button" id="save-schedule">Save project dates</button></div>
      <p class="fine">Only App Owners change the agreed deadline. Project dates are logged but never block task dates.</p>
      <div class="error" id="schedule-error"></div>
    </div>`;
  document.querySelector("#save-budget").addEventListener("click",()=>saveBudget(projectId));
  document.querySelector("#save-schedule").addEventListener("click",()=>saveProjectSchedule(projectId));
}
async function saveProjectSchedule(projectId){
  const err=document.querySelector("#schedule-error");clearFeedback(err);err.classList.remove("message-info","message-success");
  const start_date=document.querySelector("#project-start").value||null,target_date=document.querySelector("#project-target").value||null,reason=document.querySelector("#project-schedule-reason").value;
  try{
    await api(`/api/projects/${projectId}/schedule`,{method:"POST",body:JSON.stringify({start_date,target_date,reason})});
    await load();err.classList.add("message-success");err.textContent="Saved and logged.";
  }catch(x){err.textContent=x.message}
}
async function saveBudget(projectId){
  const err=document.querySelector("#budget-error");clearFeedback(err);err.classList.remove("message-info","message-success");
  const amount=document.querySelector("#budget-amount").value,currency=document.querySelector("#budget-currency").value,primary=document.querySelector("#primary-entity").value;
  try{
    await api(`/api/projects/${projectId}/budget`,{method:"POST",body:JSON.stringify({amount:amount===""?null:Number(amount),currency})});
    await api(`/api/projects/${projectId}/primary-entity`,{method:"POST",body:JSON.stringify({entity_id:primary})});
    await load();err.classList.add("message-success");err.textContent="Saved.";
  }catch(x){err.textContent=x.message}
}

async function submitAddEntity(e){
  e.preventDefault();const err=document.querySelector("#entity-error");clearFeedback(err);
  try{await api("/api/entities",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await load();await openPeople()}
  catch(x){err.textContent=x.message}
}
async function submitRenameEntity(e){
  e.preventDefault();const err=document.querySelector("#rename-entity-error");clearFeedback(err);err.className="error";err.setAttribute("role","alert");
  const values=Object.fromEntries(new FormData(e.target));
  if(!values.entity_id){err.textContent="Choose an entity.";return}
  try{await api(`/api/entities/${encodeURIComponent(values.entity_id)}/rename`,{method:"POST",body:JSON.stringify({name:values.name})});await load();await openPeople();
    const message=document.querySelector("#rename-entity-error");message.className="fine";message.setAttribute("role","status");message.textContent="Entity name saved.";}
  catch(x){err.textContent=x.message}
}
async function seedEntities(){
  const err=document.querySelector("#entity-error");clearFeedback(err);
  try{const r=await api("/api/entities/seed",{method:"POST",body:"{}"});await load();await openPeople();
    document.querySelector("#entity-error").textContent=r.created.length?`Added ${r.created.length} entities.`:"All approved entities already exist.";}
  catch(x){err.textContent=x.message}
}
async function toggleEntityActive(e){
  const b=e.target;
  try{await api(`/api/entities/${b.dataset.entityToggle}/active`,{method:"POST",body:JSON.stringify({active:b.dataset.active!=="1"})});await load();await openPeople()}
  catch(x){document.querySelector("#entity-error").textContent=x.message}
}
async function submitFiling(e){
  e.preventDefault();const err=document.querySelector("#filing-error");clearFeedback(err);
  const pid=document.querySelector("#filing-project").value;
  if(!pid){err.textContent="Choose a project.";return}
  const entity_ids=[...document.querySelectorAll("#filing-entities input:checked")].map(i=>i.value);
  try{await api(`/api/projects/${pid}/entities`,{method:"POST",body:JSON.stringify({entity_ids})});await load();await openPeople();
    document.querySelector("#filing-error").textContent="Filing saved.";}
  catch(x){err.textContent=x.message}
}

async function submitAddUser(e){
  e.preventDefault();const err=document.querySelector("#add-user-error");clearFeedback(err);
  try{await api("/api/users",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});e.target.reset();await openPeople()}
  catch(x){err.textContent=x.message}
}
// 3M2AYA: any owner resets an active user's password; only the primary resets the primary's.
function canResetPassword(u,viewerIsPrimary){return !!u.active&&(!u.is_primary_owner||viewerIsPrimary)}
function chooseResetUser(userId){
  const form=document.querySelector("#reset-password-form");
  form.querySelector("#reset-password-user").value=userId;
  document.querySelector("#reset-password-error").textContent="";
  form.scrollIntoView({block:"nearest"});form.querySelector('input[name="password"]').focus();
}
async function submitResetPassword(e){
  e.preventDefault();const form=e.target,out=document.querySelector("#reset-password-error");
  out.textContent="";out.classList.remove("is-info");
  const data=Object.fromEntries(new FormData(form));
  if(!data.user_id){out.textContent="Choose a user.";return}
  if(data.password.length<MIN_PASSWORD){out.textContent=`Use at least ${MIN_PASSWORD} characters.`;return}
  if(data.password!==data.confirm){out.textContent="The two passwords do not match.";return}
  const name=form.querySelector("#reset-password-user").selectedOptions[0]?.dataset.name||"the user";
  const own=data.user_id===state.user.id;
  try{
    const reset=await api(`/api/users/${data.user_id}/password`,{method:"POST",body:JSON.stringify({password:data.password})});
    if(own){  // the server now requires a change before anything else, so go straight to that screen
      state.user={...state.user,...reset.user};form.reset();document.querySelector("#people-dialog").close();showSignedInState();
      const note=document.querySelector("#forced-password-error");note.classList.add("is-info");
      note.textContent="Your password was reset and your other sessions were signed out. Enter it as the current password, then choose a new one.";
      return}
    await openPeople();  // re-render, so the owner-access history shows the reset
    const done=document.querySelector("#reset-password-error");done.classList.add("is-info");
    done.textContent=`Password reset for ${name}. Give them the new password; they are signed out everywhere else.`;
    document.querySelector("#reset-password-form").scrollIntoView({block:"nearest"});
  }catch(x){out.textContent=x.message}
}
async function submitGrant(e){
  e.preventDefault();const err=document.querySelector("#grant-error");clearFeedback(err);
  try{await api("/api/project-access",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await load();await openPeople()}
  catch(x){err.textContent=x.message}
}
async function toggleUserActive(e){
  const b=e.target;
  try{await api(`/api/users/${b.dataset.toggle}/active`,{method:"POST",body:JSON.stringify({active:b.dataset.active!=="1"})});await load();await openPeople()}
  catch(x){document.querySelector("#people-body").insertAdjacentHTML("afterbegin",`<p class="error">${escapeHtml(x.message)}</p>`)}
}
async function changeOwnerAccess(e){
  const b=e.target,grant=!!b.dataset.ownerGrant;
  const reason=prompt(grant?"Reason for giving this person full owner access:":"Reason for removing their owner access:","");
  if(!reason||!reason.trim())return;
  try{await api(`/api/users/${grant?b.dataset.ownerGrant:b.dataset.ownerRevoke}/secondary-owner`,{method:grant?"POST":"DELETE",body:JSON.stringify({reason})});await openPeople()}
  catch(x){document.querySelector("#people-body").insertAdjacentHTML("afterbegin",`<p class="error">${escapeHtml(x.message)}</p>`)}
}
async function revokeAccess(e){
  const b=e.target;
  try{await api("/api/project-access",{method:"DELETE",body:JSON.stringify({project_id:b.dataset.revokeProject,user_id:b.dataset.revokeUser})});await load();await openPeople()}
  catch(x){document.querySelector("#people-body").insertAdjacentHTML("afterbegin",`<p class="error">${escapeHtml(x.message)}</p>`)}
}

// ---- C9KPH6: Excel / CSV import (three steps: Upload → Review → Confirm) ----
const importState={targets:null,file:null,preview:null,result:null,filter:"",opener:null,settings:null,view:"upload"};
async function apiUpload(path,file,headers){
  const response=await fetch(path,{method:"POST",headers:{"Content-Type":"application/octet-stream","X-CSRF-Token":state.csrf||"",...headers},body:file});
  const data=await response.json();if(!response.ok)throw new Error(data.error||"Request failed");return data;
}
async function refreshImportAccess(){
  const button=document.querySelector("#import-btn");
  try{const {targets}=await api("/api/import/targets");importState.targets=targets;button.hidden=!(targets.projects.length||targets.can_create_project);const r=currentRoute();if(r.name==="project")renderProject(r)}
  catch{importState.targets=null;button.hidden=true}
}
document.querySelector("#import-btn").onclick=openImport;
document.querySelector("#project-import").onclick=openImport;
const importDialog=document.querySelector("#import-dialog");
importDialog.addEventListener("close",()=>{const opener=importState.opener;importState.opener=null;if(opener&&typeof opener.focus==="function")opener.focus()});
async function openImport(){
  importState.opener=document.activeElement;
  importState.file=null;importState.preview=null;importState.result=null;importState.filter="";
  try{const {targets}=await api("/api/import/targets");importState.targets=targets}catch(err){importState.targets={projects:[],can_create_project:false}}
  renderImportStep("upload");
  if(!importDialog.open)importDialog.showModal();
}
function setImportStep(step){
  const order=["upload","review","confirm"];
  document.querySelectorAll("#import-steps .wiz-step").forEach(li=>{
    const mine=li.dataset.step;const done=order.indexOf(mine)<order.indexOf(step);
    li.classList.toggle("is-done",done);
    if(mine===step)li.setAttribute("aria-current","step");else li.removeAttribute("aria-current");
  });
}
function importError(message,info){const el=document.querySelector("#import-error");if(!el)return;el.textContent=message||"";el.classList.toggle("is-info",!!info)}
function focusImportBody(){const target=document.querySelector("#import-body h3, #import-body [autofocus]");if(target){target.setAttribute("tabindex","-1");target.focus()}}
function renderImportStep(step){
  importState.view=step;setImportStep(step==="settings"?"upload":step);
  if(step==="upload")renderImportUpload();
  else if(step==="review")renderImportReview();
  else if(step==="confirm")renderImportConfirm();
  else if(step==="settings")renderTemplateSettings();
  focusImportBody();
}
function renderImportUpload(){
  const targets=importState.targets||{projects:[],can_create_project:false,can_edit_template:false};
  const options=targets.projects.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  const createOption=targets.can_create_project?`<option value="">Create or find the project named in the file's Project column</option>`:"";
  const settings=targets.can_edit_template?`<button type="button" class="link" id="import-settings-btn">Template settings</button>`:"";
  const selected=currentRoute().name==="project"?currentRoute().id:document.querySelector("#project-filter").value;
  document.querySelector("#import-body").innerHTML=`
    <h3>Upload a filled template</h3>
    <p class="muted">Choose your project and download its Excel workplan. Fill Task, Responsible person, Start and Finish. Expand optional columns for named relationships and grouping. Astra maintains hidden IDs. Save as .xlsx, upload to the same project, and review before confirming. Imports never delete tasks.</p>
    <div class="import-links"><a href="/api/import/template.xlsx" id="import-template-xlsx" download>Download template (.xlsx)</a><a href="/api/import/template.csv" id="import-template-csv" download>Download template (.csv)</a>${settings}</div>
    <label>Target project<select id="import-project">${createOption}${options}</select></label>
    <div id="import-drop" class="dropzone" tabindex="0" role="button" aria-describedby="import-file-name"><strong>Drop your .xlsx or .csv here</strong><span>or press Enter / click to choose a file</span><input type="file" id="import-file" accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" class="sr-only" tabindex="-1"></div>
    <div id="import-file-name" class="muted">${importState.file?escapeHtml(`Selected: ${importState.file.name} (${Math.ceil(importState.file.size/1024)} KB)`):"No file selected."}</div>
    <div class="import-options">
      <label class="inline"><input type="checkbox" id="import-valid-only"> Import valid rows only (rows with errors are skipped)</label>
      <label>Default reason recorded on changes<input id="import-reason" placeholder="Excel import &lt;file&gt; row n" maxlength="200"></label>
    </div>
    <div class="actions"><button type="button" id="import-preview-btn"${importState.file?"":" disabled"}>Preview</button></div>
    <div class="error" id="import-error"></div>`;
  const select=document.querySelector("#import-project");
  if(selected&&[...select.options].some(o=>o.value===selected))select.value=selected;
  else if(!targets.can_create_project&&select.options.length)select.selectedIndex=0;
  // With a project chosen the template comes pre-filled with that project's tasks (GET ...?project_id=).
  const updateTemplateLinks=()=>{
    const pid=select.value,suffix=pid?`?project_id=${encodeURIComponent(pid)}`:"";
    const label=pid?"Download template (with this project's tasks)":"Download template";
    for(const [id,ext] of [["import-template-xlsx","xlsx"],["import-template-csv","csv"]]){const a=document.querySelector(`#${id}`);a.href=`/api/import/template.${ext}${suffix}${pid?"&workplan=1":""}`;a.textContent=pid?`Download project workplan (.${ext})`:`${label} (.${ext})`}
  };
  select.addEventListener("change",updateTemplateLinks);updateTemplateLinks();
  const drop=document.querySelector("#import-drop"),input=document.querySelector("#import-file");
  const pick=file=>{if(!file)return;importState.file=file;document.querySelector("#import-file-name").textContent=`Selected: ${file.name} (${Math.ceil(file.size/1024)} KB)`;document.querySelector("#import-preview-btn").disabled=false;importError("")};
  drop.addEventListener("click",()=>input.click());
  drop.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();input.click()}});
  drop.addEventListener("dragover",e=>{e.preventDefault();drop.classList.add("is-over")});
  drop.addEventListener("dragleave",()=>drop.classList.remove("is-over"));
  drop.addEventListener("drop",e=>{e.preventDefault();drop.classList.remove("is-over");pick(e.dataTransfer.files&&e.dataTransfer.files[0])});
  input.addEventListener("change",()=>pick(input.files&&input.files[0]));
  document.querySelector("#import-preview-btn").addEventListener("click",runImportPreview);
  document.querySelector("#import-settings-btn")?.addEventListener("click",()=>renderImportStep("settings"));
}
function importHeaders(){
  const options={valid_rows_only:!!importState.validOnly,default_reason:importState.defaultReason||""};
  return {"X-Filename":encodeURIComponent(importState.file.name),"X-Project-Id":encodeURIComponent(importState.projectId||""),"X-Options":encodeURIComponent(JSON.stringify(options))};
}
async function runImportPreview(){
  const file=importState.file;if(!file)return;
  if(file.size>5*1024*1024){importError("The file is larger than 5 MB. Split it or remove unused sheets.");return}
  importState.projectId=document.querySelector("#import-project").value;
  importState.validOnly=document.querySelector("#import-valid-only").checked;
  importState.defaultReason=document.querySelector("#import-reason").value.trim();
  const button=document.querySelector("#import-preview-btn");button.disabled=true;button.textContent="Checking…";importError("");
  try{const {preview}=await apiUpload("/api/import/preview",file,importHeaders());importState.preview=preview;importState.filter="";renderImportStep("review")}
  catch(err){importError(err.message);button.disabled=false;button.textContent="Preview"}
}
function fmtDmy(iso){if(!iso)return "";const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(iso);return m?`${m[3]}-${m[2]}-${m[1]}`:iso}
function fmtChange(value,change){
  if(!change)return escapeHtml(value??"");
  return `<span class="change"><s>${escapeHtml(change.from||"—")}</s> → ${escapeHtml(change.to||"—")}</span>`;
}
function renderImportReview(){
  const p=importState.preview,s=p.summary;
  const chips=[["create","Create",s.create],["update","Update",s.update],["unchanged","Unchanged",s.unchanged],["warnings","Warnings",s.warnings],["errors","Errors",s.errors]]
    .map(([k,label,n])=>`<button type="button" class="import-chip" data-kind="${k}" data-filter="${k}" aria-pressed="${importState.filter===k}">${escapeHtml(label)} <strong>${n}</strong></button>`).join("");
  const project=s.project||{};
  const projectLine=project.create?`<strong>${escapeHtml(project.name||"")}</strong> (a new project will be created)`:`<strong>${escapeHtml(project.name||"")}</strong>`;
  const header=p.project_header||{};
  // Every Project-sheet value is user input from the workbook: escape each one (review probe P15c).
  const headerBits=[header.manager_email?`manager ${escapeHtml(header.manager_email)}`:"",header.timezone?escapeHtml(header.timezone):"",header.start_date?`planned ${escapeHtml(fmtDmy(header.start_date))} → ${escapeHtml(fmtDmy(header.target_date)||"—")}`:"",header.as_of_date?`plan as of ${escapeHtml(fmtDmy(header.as_of_date))}`:""].filter(Boolean).join(" · ");
  const projectSheet=header.name?`<div>Project sheet: <strong>${escapeHtml(header.name)}</strong>${headerBits?` · ${headerBits}`:""}</div>`:"";
  const peopleRows=(p.people||[]).map(x=>`<li data-status="${escapeHtml(x.status)}"><span class="badge" data-level="${x.status==="ok"?"ok":"warning"}">${escapeHtml(x.status==="ok"?"ready":x.status.replace("_"," "))}</span> ${escapeHtml(x.email||x.name)}${x.name&&x.email?` · ${escapeHtml(x.name)}`:""}${x.role?` · ${escapeHtml(x.role)}`:""}${x.message?`<br><small>${escapeHtml(x.message)}</small>`:""}</li>`).join("");
  const people=peopleRows?`<details class="import-people"${(p.people||[]).some(x=>x.status!=="ok")?" open":""}><summary>People sheet: ${p.people.length} listed, ${p.people.filter(x=>x.status!=="ok").length} for the App Owner to add or grant</summary><ul class="findings">${peopleRows}</ul></details>`:"";
  const fileWarnings=(p.file_warnings||[]).filter(w=>!/^People row|has no email/.test(w));
  const notes=[projectSheet,...fileWarnings.map(w=>`<div>${escapeHtml(w)}</div>`),(p.unknown_columns||[]).length?`<div>Columns not imported: ${escapeHtml(p.unknown_columns.join(", "))}</div>`:""].filter(Boolean).join("");
  const custom=p.custom_columns||[];
  const head=["Row","Key","Action","Title","Owner","Start","Due","Status","Criticality",...custom.map(c=>c.label),"Findings"];
  const rows=p.rows.map(r=>{
    const v=r.values||{},c=r.changes||{};
    const findings=r.findings.map(f=>`<li data-level="${escapeHtml(f.level)}"><b>${escapeHtml(f.level)}</b>${f.column?escapeHtml(f.column)+": ":""}${escapeHtml(f.message)}</li>`).join("");
    const badgeLabel=r.level==="ok"?"OK":r.level==="warning"?"Warning":"Error";
    const cells=[
      ["Row",String(r.row)],["Key",escapeHtml(r.import_key||"")],["Action",escapeHtml(r.action)],
      ["Title",fmtChange(v.title,c.title)],["Owner",fmtChange(v.owner||"Unassigned",c.owner_user_id)],
      ["Start",fmtChange(v.start_date||"—",c.start_date)],["Due",fmtChange(v.due_date||"—",c.due_date)],
      ["Status",fmtChange(v.status||"—",c.status)],["Criticality",fmtChange(v.criticality||"Unrated",c.criticality)],
      ...custom.map(col=>[col.label,escapeHtml((v.extras||{})[col.key]??"—")]),
    ].map(([label,html])=>`<td data-label="${escapeHtml(label)}">${html}</td>`).join("");
    return `<tr data-level="${escapeHtml(r.level)}" data-action="${escapeHtml(r.action)}">${cells}<td class="import-findings" data-label="Findings"><span class="badge" data-level="${escapeHtml(r.level)}">${badgeLabel}</span>${findings?`<ul class="findings">${findings}</ul>`:""}</td></tr>`;
  }).join("");
  const importable=p.rows.filter(r=>r.action!=="error").length;
  const canCommit=p.can_commit&&importable>0;
  document.querySelector("#import-body").innerHTML=`
    <h3>Review ${p.rows.length} row${p.rows.length===1?"":"s"} from ${escapeHtml(p.filename)}</h3>
    <p class="muted">Target: ${projectLine}${s.not_in_file?` · ${s.not_in_file} existing task(s) not in this file stay untouched`:""}. Errors block their row${p.options.valid_rows_only?" and are skipped":"; fix them in the template or tick “Import valid rows only” in step 1"}.</p>
    <div class="import-summary">${chips}</div>
    ${notes?`<div class="import-notes">${notes}</div>`:""}
    ${people}
    <div class="import-table-wrap"><table class="import-table"><thead><tr>${head.map(h=>`<th scope="col">${escapeHtml(h)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>
    <div class="actions"><button type="button" class="quiet" id="import-back">Back</button><button type="button" id="import-commit-btn"${canCommit?"":" disabled"}>Import ${importable} row${importable===1?"":"s"}</button></div>
    <div class="error" id="import-error"></div>`;
  if(!canCommit)importError(importable?"Rows with errors block the import. Fix them in the template, or go back and tick “Import valid rows only”.":"Nothing can be imported until the errors are fixed.");
  document.querySelectorAll("#import-body .import-chip").forEach(chip=>chip.addEventListener("click",()=>{importState.filter=importState.filter===chip.dataset.filter?"":chip.dataset.filter;applyImportFilter()}));
  applyImportFilter();
  document.querySelector("#import-back").addEventListener("click",()=>renderImportStep("upload"));
  document.querySelector("#import-commit-btn").addEventListener("click",runImportCommit);
}
function applyImportFilter(){
  const f=importState.filter;
  document.querySelectorAll("#import-body .import-chip").forEach(c=>c.setAttribute("aria-pressed",String(c.dataset.filter===f)));
  document.querySelectorAll("#import-body .import-table tbody tr").forEach(tr=>{
    let show=true;
    if(f==="errors")show=tr.dataset.level==="error";
    else if(f==="warnings")show=tr.dataset.level==="warning";
    else if(f)show=tr.dataset.action===f;
    tr.hidden=!show;
  });
}
async function runImportCommit(){
  const button=document.querySelector("#import-commit-btn");button.disabled=true;button.textContent="Importing…";importError("");
  try{
    // The server refuses the commit (409) when the bytes or the plan they produce changed since the preview.
    const {result}=await apiUpload("/api/import/commit",importState.file,{...importHeaders(),"X-Sha256":importState.preview.sha256,"X-Plan-Fingerprint":importState.preview.plan_fingerprint||""});
    importState.result=result;await load();renderImportStep("confirm");
  }catch(err){importError(err.message);button.disabled=false;button.textContent="Retry import"}
}
function renderImportConfirm(){
  const r=importState.result;
  document.querySelector("#import-body").innerHTML=`
    <div class="import-result">
      <h3>Import complete</h3>
      <p class="muted">${escapeHtml(r.filename)} → <strong>${escapeHtml(r.project.name)}</strong>${r.project.create?" (new project)":""}. Nothing was deleted; existing baselines were kept. Every change is in each task's history, and the import is in the project's history (Project history, with this project selected).</p>
      <div class="facts">${fact("Created",String(r.create))}${fact("Updated",String(r.update))}${fact("Unchanged",String(r.unchanged))}${fact("Skipped (errors)",String(r.skipped_errors||0))}${fact("Dependencies",String(r.dependencies||0))}</div>
      <p><a href="${escapeHtml(r.report_url)}" download>Download the import report (.csv)</a></p>
      <p><a href="/api/import/template.xlsx?project_id=${encodeURIComponent(r.project.id)}&amp;workplan=1" download>Download updated Excel workplan</a> with the saved Task IDs for your next edits.</p>
      <div class="actions"><button type="button" id="import-done">Done</button></div>
    </div>`;
  document.querySelector("#import-done").addEventListener("click",()=>importDialog.close());
}
// ---- Owner-only template settings ----
async function renderTemplateSettings(){
  const body=document.querySelector("#import-body");
  if(!importState.settings){
    try{const {config}=await api("/api/import/template-config");importState.settings=config}
    catch(err){body.innerHTML=`<p class="error">${escapeHtml(err.message)}</p><div class="actions"><button type="button" class="quiet" id="tpl-cancel">Back</button></div>`;document.querySelector("#tpl-cancel").addEventListener("click",()=>renderImportStep("upload"));return}
  }
  const cfg=importState.settings,core=new Set(cfg.core_keys||[]);
  const items=cfg.columns.map((col,i)=>{
    const isCore=core.has(col.key);
    const kind=col.custom?`${col.type}${col.type==="list"?` (${(col.values||[]).join(", ")})`:""}${col.required?" · required":""}`:"built-in";
    return `<li data-index="${i}">
      <label class="inline"><input type="checkbox" class="tpl-enabled"${col.enabled?" checked":""}${isCore?" disabled":""} aria-label="Enable ${escapeHtml(col.label)}"> On</label>
      <input class="tpl-label" value="${escapeHtml(col.label)}"${isCore?" disabled":""} aria-label="Label for ${escapeHtml(col.label)}" maxlength="60">
      <span class="kind">${escapeHtml(kind)}${isCore?" · core":""}</span>
      <button type="button" class="link tpl-up"${i===0?" disabled":""} aria-label="Move ${escapeHtml(col.label)} up">Up</button>
      <button type="button" class="link tpl-down"${i===cfg.columns.length-1?" disabled":""} aria-label="Move ${escapeHtml(col.label)} down">Down</button>
      ${col.custom?`<button type="button" class="link tpl-remove" aria-label="Remove ${escapeHtml(col.label)}">Remove</button>`:"<span></span>"}
    </li>`;
  }).join("");
  body.innerHTML=`
    <h3>Template settings</h3>
    <p class="muted">Choose which columns the template carries, rename or reorder them, and add your own. Simple (the default) is nine columns with pre-filled keys; Full is the complete set with Project and People sheets. Core columns (Import Key, Title, Start Date, Due Date, Status, Owner Email) stay fixed. Saving changes the template's version: files downloaded before the change are rejected on upload and must be downloaded again.${cfg.updated_at?` Last saved ${escapeHtml(new Date(cfg.updated_at).toLocaleString())}${cfg.updated_by_name?` by ${escapeHtml(cfg.updated_by_name)}`:""}.`:""}</p>
    <div class="import-summary" role="group" aria-label="Presets"><span class="muted">Presets:</span><button type="button" class="import-chip" data-preset="simple">Simple (${(cfg.presets?.simple||[]).length} columns)</button><button type="button" class="import-chip" data-preset="full">Full (${(cfg.presets?.full||[]).length} columns)</button></div>
    <ol class="col-list" id="tpl-cols">${items}</ol>
    <form id="tpl-add" class="add-col">
      <label>New column label<input name="label" maxlength="60" required></label>
      <label>Type<select name="type"><option value="text">Text</option><option value="number">Number</option><option value="date">Date (dd-mm-yyyy)</option><option value="list">List (dropdown)</option></select></label>
      <label>Allowed values (comma-separated, lists only)<input name="values"></label>
      <label class="inline"><input type="checkbox" name="required"> Required</label>
      <button>Add column</button>
    </form>
    <div class="actions"><button type="button" class="quiet" id="tpl-reset">Reset to default</button><button type="button" class="quiet" id="tpl-cancel">Back</button><button type="button" id="tpl-save">Save template</button></div>
    <div class="error" id="tpl-error"></div>`;
  const list=document.querySelector("#tpl-cols");
  const readBack=()=>{list.querySelectorAll("li").forEach(li=>{const col=cfg.columns[Number(li.dataset.index)];col.enabled=li.querySelector(".tpl-enabled").checked;if(!core.has(col.key))col.label=li.querySelector(".tpl-label").value.trim()||col.label})};
  list.addEventListener("click",e=>{
    const button=e.target.closest("button");if(!button)return;
    const li=button.closest("li"),i=Number(li.dataset.index);readBack();
    if(button.classList.contains("tpl-up")&&i>0){[cfg.columns[i-1],cfg.columns[i]]=[cfg.columns[i],cfg.columns[i-1]]}
    else if(button.classList.contains("tpl-down")&&i<cfg.columns.length-1){[cfg.columns[i+1],cfg.columns[i]]=[cfg.columns[i],cfg.columns[i+1]]}
    else if(button.classList.contains("tpl-remove")){cfg.columns.splice(i,1)}
    renderTemplateSettings();
  });
  document.querySelector("#tpl-add").addEventListener("submit",e=>{
    e.preventDefault();readBack();const f=Object.fromEntries(new FormData(e.target));
    const values=String(f.values||"").split(",").map(v=>v.trim()).filter(Boolean);
    cfg.columns.push({key:"",label:String(f.label||"").trim(),enabled:true,custom:true,type:f.type,values,required:f.required==="on"});
    renderTemplateSettings();
  });
  document.querySelectorAll("#import-body [data-preset]").forEach(b=>b.addEventListener("click",()=>{
    readBack();const on=new Set((cfg.presets||{})[b.dataset.preset]||[]);
    cfg.columns.forEach(col=>{col.enabled=core.has(col.key)||on.has(col.key)});
    renderTemplateSettings();document.querySelector("#tpl-error").textContent=`${b.dataset.preset==="simple"?"Simple":"Full"} preset applied - press Save template to keep it.`;
  }));
  document.querySelector("#tpl-cancel").addEventListener("click",()=>{importState.settings=null;renderImportStep("upload")});
  document.querySelector("#tpl-reset").addEventListener("click",async()=>{
    if(!confirm("Reset the import template to its default columns? Custom columns are removed from the template (values already imported stay on their tasks)."))return;
    try{const {config}=await api("/api/import/template-config",{method:"PUT",body:JSON.stringify({reset:true})});importState.settings=config;renderTemplateSettings();document.querySelector("#tpl-error").textContent="Template reset to default."}
    catch(err){document.querySelector("#tpl-error").textContent=err.message}
  });
  document.querySelector("#tpl-save").addEventListener("click",async()=>{
    readBack();const err=document.querySelector("#tpl-error");clearFeedback(err);
    try{const {config}=await api("/api/import/template-config",{method:"PUT",body:JSON.stringify({columns:cfg.columns})});importState.settings=config;renderTemplateSettings();document.querySelector("#tpl-error").textContent="Saved. Download the template again before filling it."}
    catch(x){err.textContent=x.message}
  });
}
function buildImportedFields(task){
  const fields=task.imported_fields||[];
  if(!fields.length)return "";
  const rows=fields.map(f=>`<dt>${escapeHtml(f.label)}</dt><dd>${escapeHtml(f.value==null?"—":String(f.value))}</dd>`).join("");
  return `<div class="import-fields"><h3>Imported fields</h3><p class="muted">Custom template columns from the last import (read-only; re-import to change them).</p><dl>${rows}</dl></div>`;
}

// M3: only a failed /api/me means "signed out"; a failed first load says so and keeps the session.
async function loadOrSay(){try{await load()}catch(err){showToast(`Astra could not load your work (${err.message}). Reload the page to try again.`)}}
(async()=>{let data;try{data=await api("/api/me")}catch{showLogin();return}Object.assign(state,data);showSignedInState();if(!state.user.must_change_password)await loadOrSay()})();


// JM7CFP: task-row drops express dates, relationships and display order explicitly.
function timelineOrder(tasks){
  const projects=new Map();
  for(const task of tasks){if(!projects.has(task.project_id))projects.set(task.project_id,[]);projects.get(task.project_id).push(task)}
  for(const group of projects.values())group.sort((a,b)=>(a.timeline_order??1000000)-(b.timeline_order??1000000));
  const positions=new Map();
  return tasks.map(task=>{const index=positions.get(task.project_id)||0;positions.set(task.project_id,index+1);return projects.get(task.project_id)[index]});
}
function timelineTaskOrder(projectId){
  const tasks=state.tasks.filter(t=>t.project_id===projectId),byId=new Map(tasks.map(t=>[t.id,t])),groups=groupSteps(tasks),ids=[];
  const walk=t=>{ids.push(t.id);(groups.childrenOf.get(t.id)||[]).forEach(walk)};
  groups.top.forEach(walk);
  // Filters can hide a parent and promote its children to top-level rows.
  // Keep the drawn sibling sequence, while hidden siblings retain their slots.
  const drawn=new Map();
  for(const row of document.querySelectorAll("#gantt [data-timeline-task], #schedule-table tr[data-timeline-task]")){
    const task=byId.get(row.dataset.timelineTask);if(!task||row.closest("[hidden]"))continue;
    const parent=task.parent_task_id||null;if(!drawn.has(parent))drawn.set(parent,[]);drawn.get(parent).push(task.id);
  }
  for(const siblings of drawn.values()){
    const visible=new Set(siblings);let index=0;
    for(let slot=0;slot<ids.length;slot++)if(visible.has(ids[slot]))ids[slot]=siblings[index++];
  }
  return ids;
}
async function reviewTaskDrop(t,mode,target,start){
  const order=mode==="above"||mode==="below",duration=Math.max(1,t.start_date&&t.due_date?Math.round((Date.parse(t.due_date)-Date.parse(t.start_date))/DAY)+1:1);
  const payload={mode,expected_revision:t.revision,...(target?{target_task_id:target.id,target_revision:target.revision}:{}),order_event_id:t.timeline_order_event_id??null,...(order?{initial_task_order:timelineTaskOrder(t.project_id)}:{}),...(mode==="date"?{start_date:start,due_date:iso(Date.parse(start)+(duration-1)*DAY)}:{}),update_deadline:false};
  const preview=()=>api(taskApi(t.id,"/timeline-schedule-preview"),{method:"POST",body:JSON.stringify(payload)});
  let plan;try{plan=await preview()}catch(err){showToast(`Move needs review: ${err.message}`,null,null,true);return}
  const d=document.createElement("dialog");d.className="task-move-dialog";
  const description=mode==="above"?`“${t.title}” will become a prerequisite of “${target.title}”.`:mode==="below"||mode==="after"?`“${t.title}” will follow “${target.title}”.`:mode==="concurrent"?`“${t.title}” will run alongside “${target.title}”.`:`Schedule “${t.title}” at the dropped date.`;
  d.innerHTML=`<form><h2>Review linked schedule</h2><p>${escapeHtml(description)}</p>${mode==="date"?`<div class="grid"><label>Start<input name="start" type="date" value="${escapeHtml(payload.start_date)}" required></label><label>Finish<input name="finish" type="date" value="${escapeHtml(payload.due_date)}" required></label></div>`:""}<p>Linked tasks move together. Existing durations and gaps are preserved. Owners and approved baselines stay as they are.</p>${isOwner()?'<label class="schedule-deadline-choice"><input name="deadline" type="checkbox"> Update agreed project deadline to the scheduled finish</label>':""}<div data-schedule-preview></div><div class="error" role="alert"></div><div class="actions"><button type="button" class="quiet" data-cancel>Cancel</button><button type="submit">Apply linked schedule</button></div></form>`;
  document.body.appendChild(d);d.showModal();const f=d.querySelector("form"),apply=f.querySelector('[type="submit"]'),error=f.querySelector(".error");
  const dateText=dates=>`${dates.start_date||"—"} → ${dates.due_date||dates.finish_date||"—"}`;
  const draw=()=>{const p=plan.project;f.querySelector("[data-schedule-preview]").innerHTML=`<h3>${plan.changes.length} task date change${plan.changes.length===1?"":"s"}</h3><div class="schedule-preview-table"><table><thead><tr><th>Task</th><th>Current</th><th>New dates</th></tr></thead><tbody>${plan.changes.map(c=>`<tr><td>${escapeHtml(c.title)}</td><td><span class="schedule-preview-dates"><span>${escapeHtml(c.before.start_date||"—")}</span><span>${escapeHtml(c.before.due_date||"—")}</span></span></td><td><span class="schedule-preview-dates"><span>${escapeHtml(c.after.start_date||"—")}</span><span>${escapeHtml(c.after.due_date||"—")}</span></span></td></tr>`).join("")||'<tr><td colspan="3">Task dates already fit this relationship.</td></tr>'}</tbody></table></div>${plan.links.length?`<ul>${plan.links.map(l=>`<li>${escapeHtml(l.action)}: ${escapeHtml(l.predecessor)} → ${escapeHtml(l.successor)}</li>`).join("")}</ul>`:""}<p><strong>Current project schedule (${escapeHtml(p.plan)}):</strong> ${escapeHtml(dateText(p.before))}</p><p><strong>New project schedule:</strong> ${escapeHtml(dateText(p.after))}</p><p><strong>Agreed deadline:</strong> ${escapeHtml(p.agreed_deadline||"Not set")} → ${escapeHtml(p.new_deadline||"Not set")}</p>${p.after.undated_count?`<p>${p.after.undated_count} task${p.after.undated_count===1?"":"s"} still need complete dates. The scheduled finish is provisional.</p>`:""}${plan.requires_owner?'<p>This linked change needs the App Owner. Nothing has been saved.</p>':""}${plan.impacts.length?`<ul>${plan.impacts.map(s=>`<li>${escapeHtml(s)}</li>`).join("")}</ul>`:""}<p>Dependencies, task dates and project schedule save together; critical paths then recalculate.</p>`;apply.disabled=plan.requires_owner};
  draw();let generation=0;
  const refresh=async()=>{const version=++generation;apply.disabled=true;clearFeedback(error);payload.update_deadline=!!f.elements.deadline?.checked;if(mode==="date"){payload.start_date=f.elements.start.value;payload.due_date=f.elements.finish.value}try{const next=await preview();if(version===generation&&d.isConnected){plan=next;draw();return true}}catch(err){if(version===generation&&d.isConnected)error.textContent=err.message}return false};
  f.onchange=()=>refresh();
  const saved=await new Promise(resolve=>{let saving=false;const cancel=()=>{if(!saving)resolve(false)};d.addEventListener("cancel",e=>{if(saving)e.preventDefault();else cancel()});f.querySelector("[data-cancel]").onclick=cancel;f.onsubmit=async e=>{e.preventDefault();if(apply.disabled||saving)return;if(mode==="date"&&(payload.start_date!==f.elements.start.value||payload.due_date!==f.elements.finish.value)){await refresh();return}saving=true;apply.disabled=true;f.querySelector("[data-cancel]").disabled=true;try{await api(taskApi(t.id,"/timeline-schedule"),{method:"POST",body:JSON.stringify({...payload,fingerprint:plan.fingerprint,confirmed:true})});resolve(true)}catch(err){error.textContent=err.message;saving=false;f.querySelector("[data-cancel]").disabled=false;apply.disabled=true}}});
  generation++;d.close();d.remove();if(saved){showToast("Linked tasks and project schedule saved. Critical paths recalculated.");await load()}
}
const taskTimeline=document.querySelector("#gantt");
// The chart follows the shadcnstudio block: it has no row drag handles or drop zones. A task is moved
// through the reviewed Move dialog below, opened from the Schedule table.
// Keyboard and touch use the same reviewed service action, without a drag gesture.
function openTimelineTaskMove(e){const handle=e.target.closest("[data-task-move]");if(!handle)return;const t=state.tasks.find(x=>x.id===handle.dataset.taskMove);if(!t||!canMoveTimelineTask(t))return;const d=document.createElement("dialog");d.innerHTML=`<form><h2>Move ${escapeHtml(t.title)}</h2><label>Action<select name="mode"><option value="date">Place on timeline</option><option value="above">Move above</option><option value="below">Move below</option><option value="after">After another task finishes</option><option value="concurrent">Run concurrently</option></select></label><label>Related task<select name="target"><option value="">Choose task</option>${state.tasks.filter(x=>x.project_id===t.project_id&&x.id!==t.id).map(x=>`<option value="${escapeHtml(x.id)}">${escapeHtml(x.title)} (${escapeHtml(x.plan_option||"Shared")})</option>`).join("")}</select></label><label>Start for timeline placement<input name="start" type="date" value="${escapeHtml(t.start_date||ganttToday())}"></label><div class="error" role="alert"></div><div class="actions"><button type="button" data-cancel class="quiet">Cancel</button><button type="submit">Review move</button></div></form>`;document.body.appendChild(d);d.showModal();const close=()=>{d.close();d.remove()};d.addEventListener("cancel",()=>d.remove(),{once:true});d.querySelector("[data-cancel]").onclick=close;d.querySelector("form").onsubmit=ev=>{ev.preventDefault();const f=ev.currentTarget,mode=f.elements.mode.value,target=state.tasks.find(x=>x.id===f.elements.target.value);if(mode!=="date"&&!target){f.querySelector(".error").textContent="Choose a related task.";return}const start=mode==="date"?f.elements.start.value:mode==="after"&&target.due_date?iso(Date.parse(target.due_date)+DAY):target?.start_date||target?.due_date;close();reviewTaskDrop(t,mode,target,start)}}
taskTimeline.addEventListener("click",openTimelineTaskMove);
document.querySelector("#schedule-table").addEventListener("click",openTimelineTaskMove);
