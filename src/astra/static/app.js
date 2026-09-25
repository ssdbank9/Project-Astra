const state={user:null,csrf:null,projects:[],tasks:[],entities:[],unread:0,sort:"criticality"};
async function api(path,options={}){options.headers={"Content-Type":"application/json",...(state.csrf?{"X-CSRF-Token":state.csrf}:{}),...(options.headers||{})};const response=await fetch(path,options);const data=await response.json();if(!response.ok){const err=new Error(data.error||"Request failed");err.status=response.status;err.confirm=data.confirm;err.impact=data.impact;err.lock=data.lock;throw err}return data}
function showLogin(){document.querySelector("#login").hidden=false;document.querySelector("#app").hidden=true}
function showApp(){document.querySelector("#login").hidden=true;document.querySelector("#app").hidden=false;document.querySelector("#user-name").textContent=state.user.display_name;document.querySelector("#user-role").textContent=roleLabel(state.user);document.querySelector("#user-initials").textContent=initials(state.user.display_name);document.querySelector("#new-project").hidden=document.querySelector("#people").hidden=!isOwner();projectActions();refreshImportAccess()}
async function load(){if(!state.loads){const s=currentRoute().params.get("sort");if(s==="due_date")state.sort=s}const [p,t,e,n]=await Promise.all([api("/api/projects"),api(`/api/tasks?sort=${encodeURIComponent(state.sort)}`),api("/api/entities").catch(()=>({entities:[]})),api("/api/notifications").catch(()=>({notifications:[],unread:0}))]);state.projects=p.projects;state.tasks=t.tasks;state.today=t.today||null;state.timezone=t.timezone||null;state.entities=e.entities;state.notifications=n.notifications;state.unread=n.unread;state.loads=(state.loads||0)+1;updateBell();fillFilters();applyRoute(false,true)}
function updateBell(){const n=state.unread||0,badge=document.querySelector("#unread-count"),inbox=document.querySelector("#inbox");badge.textContent=n;badge.hidden=!n;inbox.classList.toggle("has-unread",n>0);inbox.setAttribute("aria-label",n?`Inbox, ${n} unread`:"Inbox")}
function fillFilters(){const pf=document.querySelector("#project-filter"),tp=document.querySelector('#task-form select[name="project_id"]');const selected=pf.value;pf.innerHTML='<option value="">All projects</option>';tp.innerHTML="";for(const p of state.projects){pf.add(new Option(p.status==="closed"?`${p.name} (closed)`:p.name,p.id));if(p.status!=="closed")tp.add(new Option(p.name,p.id))}pf.value=selected;const statuses=[...new Set(state.tasks.map(t=>t.status))].sort();document.querySelector("#status-filter").innerHTML='<option value="">All statuses</option>'+statuses.map(s=>`<option>${escapeHtml(s)}</option>`).join("");const ef=document.querySelector("#entity-filter"),efSel=ef.value;ef.innerHTML='<option value="">All entities</option>'+(state.entities||[]).map(e=>`<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)}</option>`).join("");ef.value=efSel;fillPredecessors()}
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
function matchesRisk(t,risk){return risk==="blocked"?!!t.is_blocked:risk==="critical"?!!t.is_critical_path:risk==="atrisk"?isAtRisk(t):true}
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
// D73AQW: a task's steps are its subtasks. They render as colour-coded segments inside the
// parent bar (hue = step index, Okabe-Ito order), expand to child rows on request, share one
// tooltip on hover and focus, and click through to the step's own record. Colour is never the
// only carrier: every segment shows its index, the legend pairs index with colour, and the
// Schedule table twin shows the same rows as text.
const STEP_HUES=7;
const CLOSED_STATUSES=["completed","cancelled","abandoned"];
const STATUS_LABELS={draft:"Draft",assigned:"Assigned",in_progress:"In progress",submitted:"Submitted",changes_requested:"Changes requested",completed:"Completed",on_hold:"On hold",delayed:"Delayed",cancelled:"Cancelled",abandoned:"Abandoned",reopened:"Reopened"};
const tipMeta=new Map();
// localStorage holds per-viewer conveniences only (expanded parents, chart/table choice).
const storage={get(k,f){try{const v=localStorage.getItem(k);return v==null?f:JSON.parse(v)}catch(e){return f}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
const storedExpanded=storage.get("astra.gantt.expanded",[]);
const expandedParents=new Set(Array.isArray(storedExpanded)?storedExpanded:[]);
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
function stepDays(t){const s=t.start_date||t.due_date,e=t.due_date||t.start_date;return Math.round((Date.parse(e)-Date.parse(s))/86400000)+1}
function stateClass(t){return t.is_critical_path?"critical":(t.is_blocked?"blocked":t.due_state)}
function tipLines(t,idx,total,extra){
  const head=idx?`Step ${idx} of ${total} · ${t.title}`:t.title;
  const owner=`Owner: ${t.owner_name||"Unassigned"}`;
  const dated=t.start_date||t.due_date;
  const n=dated?stepDays(t):0;
  const when=dated?`${fmtDay(t.start_date||t.due_date)} → ${fmtDay(t.due_date||t.start_date)} · ${n} day${n===1?"":"s"}`:"No dates yet";
  const st=[statusLabel(t.status),dueText(t),t.criticality||"Unrated"];
  if(t.is_critical_path)st.push("Critical path");if(t.is_blocked)st.push("Blocked");
  return [head,owner,when,st.filter(Boolean).join(" · "),...(extra||[]),"Click for details & history"];
}
// Registers the tooltip text for an element and returns its data-tip + aria-label attributes.
// GF-8: the label is short (position and name); the detail lives in the tooltip, which is
// linked by aria-describedby only while it is visible, so nothing is read twice.
function tipAttrs(t,idx,total,extra){const lines=tipLines(t,idx,total,extra);tipMeta.set(t.id,lines);const label=idx?`Step ${idx} of ${total}, ${t.title}`:(total?`${t.title}, ${total} step${total===1?"":"s"}`:t.title);return `data-tip="${escapeHtml(t.id)}" aria-label="${escapeHtml(label)}"`}
function groupSteps(tasks){
  const visible=new Set(tasks.map(t=>t.id));
  // Step index comes from ALL children of a parent (state.tasks), so a step keeps its
  // number and colour whatever the filters hide; only the drawn set follows the filters.
  const allChildren=new Map();
  for(const t of state.tasks){if(t.parent_task_id){if(!allChildren.has(t.parent_task_id))allChildren.set(t.parent_task_id,[]);allChildren.get(t.parent_task_id).push(t)}}
  const stepIndex=new Map();
  for(const kids of allChildren.values()){const ordered=stepOrder(kids);ordered.forEach((k,i)=>stepIndex.set(k.id,{idx:i+1,total:ordered.length}))}
  const childrenOf=new Map(),top=[];
  for(const t of tasks){
    if(t.parent_task_id&&visible.has(t.parent_task_id)){if(!childrenOf.has(t.parent_task_id))childrenOf.set(t.parent_task_id,[]);childrenOf.get(t.parent_task_id).push(t)}
    else top.push(t);
  }
  for(const [pid,kids] of childrenOf)childrenOf.set(pid,stepOrder(kids));
  return {top,childrenOf,stepIndex,visible,hasSteps:childrenOf.size>0};
}
function dateExtent(t,kids){
  const vals=[];const add=x=>{if(x.start_date||x.due_date){vals.push(Date.parse(x.start_date||x.due_date),Date.parse(x.due_date||x.start_date))}};
  add(t);kids.forEach(add);
  return vals.length?{start:Math.min(...vals),end:Math.max(...vals)}:null;
}
// CSP is style-src 'self', so inline style attributes are dropped by the browser. Positions
// travel as data-x / data-w percentages and are applied through the CSSOM after insertion.
function applyGeometry(root){root.querySelectorAll("[data-x]").forEach(n=>{n.style.left=`${n.dataset.x}%`;if(n.dataset.w!=null)n.style.width=`${n.dataset.w}%`})}
// GF-6: a re-render (resize, filter, view change) replaces the chart's DOM. If focus was inside it,
// remember which control held it (kind + id attribute) and put focus back on its replacement.
const FOCUS_ATTRS=["data-detail","data-more","data-expand"],FOCUS_KINDS=["step","track","chip","link","expand","step-more"];
function focusKeyIn(root){const a=document.activeElement;if(!a||!root.contains(a))return null;const attr=FOCUS_ATTRS.find(x=>a.hasAttribute(x));if(!attr)return null;const kind=FOCUS_KINDS.find(k=>a.classList.contains(k));return `${kind?"."+kind:""}[${attr}="${CSS.escape(a.getAttribute(attr))}"]`}
function restoreFocus(root,sel){if(!sel)return;const n=root.querySelector(sel);if(n&&!n.closest("[hidden]"))n.focus({preventScroll:true})}
const GRIPS='<i class="bar-grip start" data-edge="start" aria-hidden="true"></i><i class="bar-grip end" data-edge="end" aria-hidden="true"></i>';
function renderGantt(tasks){
  const el=document.querySelector("#gantt"),tableEl=document.querySelector("#schedule-table");
  const focusKey=focusKeyIn(el);
  tipMeta.clear();hideTip();
  const showTable=currentView()==="table";
  document.querySelector("#view-table").checked=showTable;
  el.hidden=showTable;tableEl.hidden=!showTable;
  const groups=groupSteps(tasks);
  document.querySelector("#step-legend").hidden=!groups.hasSteps;
  if(!tasks.length){const empty='<div class="empty">No tasks match these filters. Undated or unassigned work will appear here rather than being hidden.</div>';el.innerHTML=empty;tableEl.innerHTML=empty;return}
  if(showTable){renderScheduleTable(groups,tableEl);el.innerHTML="";return}
  tableEl.innerHTML="";
  const {top,childrenOf,stepIndex,visible}=groups;
  const dated=tasks.filter(t=>t.start_date||t.due_date);
  // 5WZ4A8: project start/target markers for each project shown in the view.
  const projIds=[...new Set(tasks.map(t=>t.project_id))];
  const singleProject=projIds.length===1;
  const projMarkers=[];
  for(const pid of projIds){
    const proj=(state.projects||[]).find(p=>p.id===pid);
    if(!proj)continue;
    const label=n=>singleProject?n:`${proj.name}: ${n}`;
    if(proj.start_date)projMarkers.push({date:Date.parse(proj.start_date),kind:"start",label:label("Start")});
    if(proj.target_date)projMarkers.push({date:Date.parse(proj.target_date),kind:"target",label:label("Target")});
  }
  const dateVals=[...dated.map(t=>Date.parse(t.start_date||t.due_date)),...dated.map(t=>Date.parse(t.due_date||t.start_date)),...projMarkers.map(m=>m.date)];
  let min=dateVals.length?new Date(Math.min(...dateVals)):new Date();
  let max=dateVals.length?new Date(Math.max(...dateVals)):new Date(min.getTime()+86400000*30);
  min.setDate(min.getDate()-3);max.setDate(max.getDate()+3);
  const span=Math.max(1,max-min);el.dataset.span=String(span);
  const pct=d=>(d-min)/span*100;
  const inRange=x=>x>=0&&x<=100;
  const markerFlags=projMarkers.map(m=>{const x=pct(m.date);return inRange(x)?`<span class="proj-flag ${m.kind}" data-x="${x}">${escapeHtml(m.label)}</span>`:""}).join("");
  const markerLines=projMarkers.map(m=>{const x=pct(m.date);return inRange(x)?`<span class="proj-line ${m.kind}" data-x="${x}"></span>`:""}).join("");
  // weekly calendar ticks
  // Task dates parse as UTC midnight, so ticks and the today line are in UTC too; today is the server's.
  const ticks=[];const t0=new Date(min);t0.setUTCHours(0,0,0,0);
  for(let t=t0.getTime();t<=max.getTime();t+=7*86400000)ticks.push(new Date(t));
  const todayPct=pct(Date.parse(ganttToday()));const showToday=todayPct>=0&&todayPct<=100;
  const axis=ticks.map(d=>`<span class="axis-tick" data-x="${pct(d)}"><b>${d.getUTCDate()}</b> ${escapeHtml(d.toLocaleDateString(undefined,{month:"short",timeZone:"UTC"}))}</span>`).join("");
  const todayFlag=showToday?`<span class="today-flag" data-x="${todayPct}">Today</span>`:"";
  const header=`<div class="gantt-row gantt-head"><div class="task-name gantt-head-cap">Project / task</div><div class="task-meta gantt-head-cap">Owner · due · next action</div><div class="timeline axis">${axis}${markerLines}${markerFlags}${todayFlag}</div></div>`;
  const todayLine=showToday?`<span class="today-line" data-x="${todayPct}"></span>`:"";
  // Pixel estimate of the timeline column (grid: 260px name, 210px meta, rest timeline).
  const tlw=Math.max(700,(el.clientWidth||1180)-470);
  const stepButton=(k,g)=>{
    const m=stepIndex.get(k.id);const closed=CLOSED_STATUSES.includes(k.status);
    const cls=["step",`step-c${stepHue(m.idx)}`,m.idx>STEP_HUES?"wrap":"",g.lane?"lane-2":"",closed?"done":"",k.status==="on_hold"?"hold":"",k.is_critical_path?"crit":"",g.solo?"solo":""].filter(Boolean).join(" ");
    const glyph=k.status==="completed"?"✓":(closed?"×":(k.status==="on_hold"?"∥":""));
    const showTitle=g.px>=72,showOwner=g.px>=110&&k.owner_name;
    const ttl=showTitle?`<span class="ttl">${glyph?glyph+" ":""}${escapeHtml(k.title)}</span>`:(glyph?`<span class="ttl">${glyph}</span>`:"");
    const own=showOwner?`<i class="own" aria-hidden="true">${escapeHtml(initials(k.owner_name))}</i>`:"";
    return `<button type="button" class="${cls}" data-detail="${escapeHtml(k.id)}" data-idx="${m.idx}" tabindex="${g.solo?0:-1}" ${tipAttrs(k,m.idx,m.total)} data-x="${g.x}" data-w="${g.w}"><span class="step-label"><b class="idx">${m.idx}</b>${ttl}${own}</span></button>`;
  };
  const stepListItem=k=>{const m=stepIndex.get(k.id);return `<li><button type="button" class="link" data-detail="${escapeHtml(k.id)}"><i class="sw step-c${stepHue(m.idx)}${m.idx>STEP_HUES?" wrap":""}" aria-hidden="true">${m.idx}</i> Step ${m.idx} · ${escapeHtml(k.title)}</button> <span class="muted">${escapeHtml(k.owner_name||"Unassigned")} · ${escapeHtml(k.start_date||"—")} → ${escapeHtml(k.due_date||"—")} · ${escapeHtml(statusLabel(k.status))}</span></li>`};
  const row=(t,depth)=>{
    const id=escapeHtml(t.id);
    const kids=childrenOf.get(t.id)||[];
    const meta=stepIndex.get(t.id);
    const isStep=depth>0&&!!meta;
    const expanded=expandedParents.has(t.id);
    const ownDates=!!(t.start_date||t.due_date);
    // GF-2: a dated parent's track is sized and tinted from its OWN dates. Steps that run past them
    // overhang onto a dashed neutral extension and are named in the tooltip and the meta column.
    // Only a parent without dates takes its extent from its steps (the dashed "derived" track).
    const ext=ownDates?dateExtent(t,[]):dateExtent(t,kids);
    const undatedKids=kids.filter(k=>!k.start_date&&!k.due_date),nUndated=undatedKids.length;
    // GF-1/GF-16: the "n steps need dates" chip lives in the meta column, never on the timeline, so
    // it can never cover a step and shows whether or not the parent itself has dates.
    const undatedChip=nUndated?`<br><button type="button" class="chip step-undated" data-detail="${id}" aria-label="${nUndated} step${nUndated===1?"":"s"} of ${escapeHtml(t.title)} need${nUndated===1?"s":""} dates; open the task">${nUndated} step${nUndated===1?"":"s"} need${nUndated===1?"s":""} dates</button>`:"";
    let bar,tall=false,derived="",overrunText="",metaMore="";
    if(!ext){bar=`<span class="bar undated">Date required</span>`}
    else{
      const left=Math.max(0,pct(ext.start)),width=Math.max(.8,(ext.end-ext.start+86400000)/span*100);
      // A parent with no dates of its own gets a dashed "derived" track (its extent comes
      // from its steps) rather than the static grey "Date required" chip styling.
      const cls=kids.length&&!ownDates?"derived":stateClass(t);
      if(kids.length){
        const datedKids=kids.filter(k=>k.start_date||k.due_date);
        const barPx=width/100*tlw,maxLanes=barPx>=160?2:1;
        const laneEnd=[],drawn=[],overflow=[],overruns=[];
        let extStart=ext.start,extEnd=ext.end;
        for(const k of datedKids){
          const ks=Date.parse(k.start_date||k.due_date),ke=Date.parse(k.due_date||k.start_date);
          if(ownDates){
            const idx=stepIndex.get(k.id).idx;
            if(ks<ext.start){const d=Math.round((ext.start-ks)/86400000);overruns.push(`Step ${idx} starts ${d} day${d===1?"":"s"} before the parent`);extStart=Math.min(extStart,ks)}
            if(ke>ext.end){const d=Math.round((ke-ext.end)/86400000);overruns.push(`Step ${idx} ends ${d} day${d===1?"":"s"} after the parent`);extEnd=Math.max(extEnd,ke)}
          }
          const wPct=(ke-ks+86400000)/span*100,px=wPct/100*tlw;
          if(px<8){overflow.push(k);continue}
          let lane=-1;for(let i=0;i<maxLanes;i++){if(laneEnd[i]==null||laneEnd[i]<ks){lane=i;break}}
          if(lane<0){overflow.push(k);continue}
          laneEnd[lane]=ke;
          // Track-relative geometry; a step outside the parent's dates overhangs (x<0 or x+w>100).
          drawn.push({k,g:{lane,px,x:(pct(ks)-left)/width*100,w:wPct/width*100}});
        }
        tall=laneEnd.length>1;
        const extBefore=extStart<ext.start?`<i class="track-ext before" data-x="${(pct(extStart)-left)/width*100}" data-w="${(pct(ext.start)-pct(extStart))/width*100}"></i>`:"";
        const extAfter=extEnd>ext.end?`<i class="track-ext after" data-x="100" data-w="${(pct(extEnd)-pct(ext.end))/width*100}"></i>`:"";
        if(overruns.length)overrunText=overruns.map(o=>`<br><span class="overrun-text">${escapeHtml(o)}</span>`).join("");
        const segs=drawn.map(({k,g})=>stepButton(k,g)).join("");
        // GF-1/GF-7: +N sits just outside the track's right edge, or its left edge when the track ends
        // near the timeline's end, or in the meta column when the track spans the whole timeline, so
        // neither it nor its 44px hit area can ever cover a drawn step.
        const need=40/tlw*100,place=100-(left+width)>=need?"":(left>=need?" flip":" in-meta");
        const moreBtn=overflow.length?`<button type="button" class="step-more${place}" data-more="${id}" aria-expanded="false" aria-controls="more-${id}" aria-label="${overflow.length} more step${overflow.length===1?"":"s"} not drawn at this scale (too small or overlapping); open the list">+${overflow.length}</button>`:"";
        const more=place===" in-meta"?"":moreBtn;
        const moreList=overflow.length?`<div class="step-more-list" id="more-${id}" data-x="${place===" in-meta"?0:Math.min(left,68)}" hidden><p class="muted">${overflow.length} more step${overflow.length===1?"":"s"} not drawn at this scale (too small or overlapping)</p><ul>${overflow.map(stepListItem).join("")}</ul></div>`:"";
        // In the meta column the list follows its button, so the disclosure stays adjacent in Tab order.
        if(place===" in-meta")metaMore=`<br>${moreBtn}${moreList}`;
        if(!ownDates)derived=`<br><span class="chip derived">Dates from steps</span>`;
        const drag=ownDates&&canDragBar(t)?` data-drag="${id}"`:"",grips=drag?GRIPS:"";
        bar=`<div class="bar track ${cls}${tall?" lanes-2":""}${expanded?" is-expanded":""}" role="group" tabindex="0" data-detail="${id}"${drag} ${tipAttrs(t,null,kids.length,overruns)} data-x="${left}" data-w="${width}">${extBefore}${extAfter}${segs}${more}${grips}</div>${place===" in-meta"?"":moreList}`;
      }
      else if(isStep){bar=stepButton(t,{lane:0,px:width/100*tlw,x:left,w:Math.min(100-left,width),solo:true})}
      else{const drag=canDragBar(t)&&!isStep?` data-drag="${id}"`:"";
        bar=`<button type="button" class="bar plain ${cls}" data-detail="${id}"${drag} ${tipAttrs(t,null,0)} data-x="${left}" data-w="${width}"><span class="bar-label">${escapeHtml(t.title)}</span>${drag?GRIPS:""}</button>`}
    }
    const blocked=t.is_blocked?`<br><span class="blocked-text">Blocked by ${escapeHtml(t.blocked_by.map(item=>item.title).join(", "))}</span>`:"";
    const cp=t.is_critical_path?`<br><span class="cp-text">On critical path</span>`:"";
    const expandBtn=kids.length?`<button type="button" class="expand" data-expand="${id}" aria-expanded="${expanded}" aria-controls="steps-${id}" aria-label="${expanded?"Hide":"Show"} ${kids.length} step${kids.length===1?"":"s"} of ${escapeHtml(t.title)}">${expanded?"▾":"▸"}</button>`:"";
    const swatch=isStep?`<i class="sw step-c${stepHue(meta.idx)}${meta.idx>STEP_HUES?" wrap":""}" aria-hidden="true">${meta.idx}</i> `:"";
    const nameTop=isStep?`<span class="step-kicker">${swatch}Step ${meta.idx} of ${meta.total}</span>`:escapeHtml(t.project_name);
    const name=`<div class="task-name${isStep?" is-step":""}"><div class="name-wrap">${expandBtn}<div>${nameTop}<br><small>${escapeHtml(t.title)}</small>${kids.length?`<br><small class="muted">${kids.length} step${kids.length===1?"":"s"}</small>`:""}<br><button type="button" class="link" data-detail="${id}">Details &amp; history</button></div></div></div>`;
    const metaCol=`<div class="task-meta">${escapeHtml(t.owner_name||"Unassigned")}<br>${escapeHtml(t.due_date||"No due date")} · ${critLabel(t.criticality)}${derived}${undatedChip}${metaMore}${overrunText}${blocked}${cp}<br><span class="next-action">Next: ${escapeHtml(t.next_action||"—")}</span></div>`;
    const html=`<div class="gantt-row${isStep?" step-row":""}">${name}${metaCol}<div class="timeline${tall?" tall":""}">${markerLines}${todayLine}${bar}</div></div>`;
    if(!kids.length)return html;
    return html+`<div class="step-rows" id="steps-${id}" role="group" aria-label="Steps of ${escapeHtml(t.title)}"${expanded?"":" hidden"}>${kids.map(k=>row(k,depth+1)).join("")}</div>`;
  };
  el.innerHTML=header+top.map(t=>row(t,0)).join("");
  applyGeometry(el);
  restoreFocus(el,focusKey);
}
function renderScheduleTable(groups,tableEl){
  const {top,childrenOf,stepIndex}=groups,scope=bulkScope();
  let steps=0;const rows=[];
  const cell=v=>`<td>${escapeHtml(v??"—")}</td>`;
  const walk=(t,parent)=>{
    const kids=childrenOf.get(t.id)||[];const m=stepIndex.get(t.id);const isStep=!!parent;
    const link=`<button type="button" class="link" data-detail="${escapeHtml(t.id)}">${escapeHtml(t.title)}</button>`;
    const stepNo=isStep?`<i class="sw step-c${stepHue(m.idx)}${m.idx>STEP_HUES?" wrap":""}" aria-hidden="true">${m.idx}</i><span class="sr-only">Step ${m.idx}</span> of ${m.total}`:"—";
    const pick=scope?`<td class="pick">${isStep?"":pickBox(t)}</td>`:"";
    rows.push(`<tr class="${isStep?"step-tr":"task-tr"}${bulk.ids.has(t.id)?" is-picked":""}">${pick}${cell(t.project_name)}<td>${isStep?escapeHtml(parent.title):link}</td><td>${stepNo}</td><td>${isStep?link:"—"}</td>${cell(t.owner_name||"Unassigned")}${cell(t.start_date||"—")}${cell(t.due_date||"—")}${cell(statusLabel(t.status))}<td>${critLabel(t.criticality)}</td>${cell(dueText(t)||t.due_state)}<td>${t.is_critical_path?"Yes":"No"}</td></tr>`);
    if(isStep)steps++;
    kids.forEach(k=>walk(k,t));
  };
  top.forEach(t=>walk(t,null));
  const asOf=document.querySelector("#as-of").textContent;
  const head=(scope?'<th scope="col" class="pick"><input type="checkbox" data-pick-all aria-label="Select every task in this list"></th>':"")+["Project","Task","Step #","Step","Owner","Start","Due","Status","Criticality","Due state","Critical path"].map(h=>`<th scope="col">${h}</th>`).join("");
  tableEl.innerHTML=`<table class="sched-table"><caption>Schedule table · ${top.length} task${top.length===1?"":"s"}, ${steps} step${steps===1?"":"s"} · same filters as the Gantt · ${escapeHtml(asOf)}</caption><thead><tr>${head}</tr></thead><tbody>${rows.join("")}</tbody></table>`;
}
// Shared tooltip (WCAG 1.4.13: hoverable, persistent, dismissible). Shown on hover after a
// short delay and on keyboard focus; never the title attribute.
const tipEl=document.querySelector("#step-tip");
let tipTimer=null,tipFor=null;
function placeTip(target){const r=target.getBoundingClientRect();const tw=tipEl.offsetWidth,th=tipEl.offsetHeight;const left=Math.min(Math.max(8,r.left),Math.max(8,window.innerWidth-tw-8));let top=r.bottom+8;if(top+th>window.innerHeight-8)top=r.top-th-8;tipEl.style.left=`${left}px`;tipEl.style.top=`${Math.max(8,top)}px`}
function showTip(target){const lines=tipMeta.get(target.dataset.tip);if(!lines)return;clearTimeout(tipTimer);tipTimer=null;if(tipFor&&tipFor!==target)tipFor.removeAttribute("aria-describedby");tipFor=target;tipEl.innerHTML=lines.map((l,i)=>`<span class="${i===0?"tip-head":(i===lines.length-1?"tip-hint":"")}">${escapeHtml(l)}</span>`).join("");tipEl.hidden=false;target.setAttribute("aria-describedby","step-tip");placeTip(target)}
function hideTip(){clearTimeout(tipTimer);tipTimer=null;if(tipFor){tipFor.removeAttribute("aria-describedby");tipFor=null}if(tipEl)tipEl.hidden=true}
function announce(msg){const live=document.querySelector("#gantt-live");if(!live)return;live.textContent="";setTimeout(()=>{live.textContent=msg},30)}
// GF-6: when the list being closed holds focus (Escape on a link), focus returns to its +N button.
function closeMoreLists(){document.querySelectorAll(".step-more-list:not([hidden])").forEach(l=>{const held=l.contains(document.activeElement);l.hidden=true;const b=document.querySelector(`[aria-controls="${CSS.escape(l.id)}"]`);if(b){b.setAttribute("aria-expanded","false");if(held)b.focus()}})}
function toggleSteps(id){
  const btn=document.querySelector(`[data-expand="${CSS.escape(id)}"]`),rows=document.getElementById(`steps-${id}`);
  if(!btn||!rows)return;
  const open=rows.hidden;rows.hidden=!open;
  btn.setAttribute("aria-expanded",String(open));btn.textContent=open?"▾":"▸";
  btn.setAttribute("aria-label",(btn.getAttribute("aria-label")||"").replace(/^(Show|Hide)/,open?"Hide":"Show"));
  if(open)expandedParents.add(id);else expandedParents.delete(id);
  storage.set("astra.gantt.expanded",[...expandedParents]);
  btn.closest(".gantt-row")?.querySelector(".track")?.classList.toggle("is-expanded",open);
  const n=rows.querySelectorAll(":scope > .gantt-row").length;
  announce(open?`Steps expanded, ${n} row${n===1?"":"s"}`:"Steps collapsed");
}
function toggleMore(btn){const list=document.getElementById(btn.getAttribute("aria-controls"));if(!list)return;const open=list.hidden;closeMoreLists();if(open){list.hidden=false;btn.setAttribute("aria-expanded","true");hideTip()}}
(function wireGantt(){
  const gantt=document.querySelector("#gantt");
  // The +N button and its list are DOM children of the track but not part of it: they never raise
  // the track's tooltip (GF-8).
  const isMore=n=>!!(n&&n.closest&&n.closest(".step-more,.step-more-list"));
  gantt.addEventListener("mouseover",e=>{if(isMore(e.target))return;const t=e.target.closest("[data-tip]");if(!t||t===tipFor)return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>showTip(t),150)});
  gantt.addEventListener("mouseout",e=>{const t=e.target.closest("[data-tip]");if(!t)return;const to=e.relatedTarget;if(to&&((t.contains(to)&&!isMore(to))||tipEl.contains(to)))return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>{if(!tipEl.matches(":hover"))hideTip()},120)});
  tipEl.addEventListener("mouseleave",()=>hideTip());
  // GF-8: only the focused element itself carries a tooltip (never an ancestor track when focus lands
  // on +N), and losing focus clears the tooltip and aria-describedby of that same element.
  gantt.addEventListener("focusin",e=>{if(e.target.matches("[data-tip]"))showTip(e.target)});
  gantt.addEventListener("focusout",e=>{if(e.target.matches("[data-tip]")&&e.target===tipFor)hideTip()});
  // Roving focus inside a parent bar: the bar is the tab stop, arrows move between its steps.
  gantt.addEventListener("keydown",e=>{
    if(e.key==="Escape"){hideTip();closeMoreLists();return}
    const track=e.target.closest(".track");
    if(!track)return;
    const steps=[...track.querySelectorAll(".step")];
    const cur=e.target.closest(".step");
    let i=cur?steps.indexOf(cur):-1;
    if(["ArrowRight","ArrowLeft","Home","End"].includes(e.key)){
      if(!steps.length)return;
      if(e.key==="ArrowRight")i=Math.min(steps.length-1,i+1);
      else if(e.key==="ArrowLeft")i=i<0?steps.length-1:Math.max(0,i-1);
      else if(e.key==="Home")i=0;else i=steps.length-1;
      e.preventDefault();steps[i].focus();return;
    }
    if((e.key==="Enter"||e.key===" ")&&e.target===track){e.preventDefault();hideTip();openDetail(track.dataset.detail)}
  });
  // Escape must also close a hover-only tooltip or an open +N list while focus is still on body,
  // so it is bound on document; the #gantt keydown branch above keeps the focused-step case.
  document.addEventListener("keydown",e=>{if(e.key==="Escape"){hideTip();closeMoreLists()}});
  document.addEventListener("click",e=>{if(!e.target.closest(".step-more,.step-more-list"))closeMoreLists()});
  window.addEventListener("scroll",()=>{if(tipFor)placeTip(tipFor)},true);
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
function boardCard(t,kids,movable){
  const done=kids.filter(k=>k.status==="completed").length,col=boardColumn(t),tags=[];
  if(t.is_blocked&&!CLOSED_STATUSES.includes(t.status))tags.push(`<span class="tag" data-tone="purple">⊘ Waits on ${escapeHtml((t.blocked_by&&t.blocked_by[0]&&t.blocked_by[0].title)||"a predecessor")}</span>`);
  if(t.status==="on_hold")tags.push('<span class="tag" data-tone="purple">∥ On hold</span>');
  if(t.status==="delayed")tags.push('<span class="tag" data-tone="amber">Delayed</span>');
  if(t.status==="changes_requested")tags.push('<span class="tag" data-tone="amber">Changes requested</span>');
  if(t.is_critical_path&&!CLOSED_STATUSES.includes(t.status))tags.push('<span class="tag" data-tone="red">◆ Critical path</span>');
  if(col==="accepted")tags.push('<span class="tag" data-tone="green">✓ Accepted</span>');
  if(col==="closed")tags.push(`<span class="tag">× ${escapeHtml(statusLabel(t.status))}</span>`);
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
      <span class="work-meta">${top.length} task${top.length===1?"":"s"} · steps show on their parent · ${movable?'<span class="drag-only">drag a card or </span>use Move to…; ordinary moves can be undone for 15 seconds':"read-only for your role"}</span></div>
    ${top.length?`<div class="board${LOCKED_COLUMNS.filter(shut).map(k=>" shut-"+k).join("")}" role="region" aria-label="Board" tabindex="0"><div class="board-cols board-head">${head}</div>${laneRows}</div>`
      :'<p class="empty-line">No tasks in this project yet. Use Add a task to start.</p>'}`;
}
function projectOverview(p,tasks){
  const ids=new Set(tasks.map(t=>t.id)),top=tasks.filter(t=>!t.parent_task_id||!ids.has(t.parent_task_id));
  const counted=top.filter(t=>t.status!=="cancelled"&&t.status!=="abandoned"),done=counted.filter(t=>t.status==="completed").length;
  const open=tasks.filter(isOpen),pct=counted.length?Math.round(done/counted.length*100):0;
  const facts=[
    fact("Status",p.status==="closed"?"Closed":p.status==="on_hold"?"On hold":"Active"),
    fact("Start",p.start_date?fmtDay(p.start_date):"Not set"),fact("Target",p.target_date?fmtDay(p.target_date):"Not set"),
    fact("Open tasks",String(open.length)),fact("Overdue",String(open.filter(t=>t.due_state==="overdue").length)),
    fact("Blocked",String(open.filter(t=>t.is_blocked).length)),fact("Critical path",String(open.filter(t=>t.is_critical_path).length)),
    fact("Timezone",p.timezone||"—"),
  ].join("");
  const next=open.filter(t=>t.due_date).sort((a,b)=>a.due_date.localeCompare(b.due_date)).slice(0,5);
  return `<div class="page-card overview">
    <div class="progress-line"><label for="project-progress">Progress</label><progress id="project-progress" max="100" value="${pct}">${pct}%</progress>
      <span><strong>${done} of ${counted.length}</strong> task${counted.length===1?"":"s"} accepted (${pct}%)</span></div>
    <div class="facts">${facts}</div>
    ${p.description?`<p class="desc">${escapeHtml(p.description)}</p>`:""}
    ${p.status==="closed"&&p.closure_note?`<div class="state-note"><p><strong>Closed.</strong> ${escapeHtml(p.closure_note)}</p></div>`:""}
    <h3 class="group-head">Next due</h3>${next.length?`<ul class="home-list">${next.map(t=>homeRow(t,`<span class="due-chip" data-due="${workGroup(t)}">${escapeHtml(dueText(t))}</span>`)).join("")}</ul>`:'<p class="empty-line">No open task has a due date.</p>'}
  </div>`;
}
function renderProject(r){
  const q=s=>document.querySelector(s),p=(state.projects||[]).find(x=>x.id===r.id),body=q("#project-body"),slot=q("#project-gantt-slot");
  q("#project-tabs").innerHTML=p?PROJECT_TABS.map(([k,l])=>`<a href="#/project/${encodeURIComponent(p.id)}/${k}"${k===r.tab?' aria-current="page"':""}>${l}</a>`).join(""):"";
  q("#project-capture").hidden=!p||p.status==="closed";
  q("#project-save-template").hidden=!p||!isOwner();
  q("#project-close").hidden=!p||!isOwner()||p.status==="closed";
  slot.hidden=!p||!(r.tab==="list"||r.tab==="timeline");body.hidden=!slot.hidden;
  if(!p){
    q("#project-facts").textContent="";
    body.innerHTML='<div class="card empty-state"><h2>This project is not available</h2><p>It may have been removed, or you are not a member of it.</p><a class="button-link primary" href="#/projects">All projects</a></div>';
    return;
  }
  const tasks=state.tasks.filter(t=>t.project_id===p.id),ents=(p.entities||[]).map(e=>e.name).join(", ");
  q("#project-facts").textContent=[ents,p.status==="closed"?"Closed":null,p.target_date?`Target ${fmtDay(p.target_date)}`:null,(()=>{const ids=new Set(tasks.map(t=>t.id)),steps=tasks.filter(t=>t.parent_task_id&&ids.has(t.parent_task_id)).length,top=tasks.length-steps;
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
    impact:["Confirm the new dates",`New dates for ${name}: ${escapeHtml(err&&err.dates?dateTip(t,err.dates,Math.round((Date.parse(err.dates.due_date)-Date.parse(t.due_date))/DAY)):"")}. This move has consequences:`,
      `<ul class="impact-list">${((err&&err.impact)||[]).map(i=>`<li>${escapeHtml(i)}</li>`).join("")}</ul><p class="muted">Tasks that follow are not moved for you. The other owners are told once you confirm.</p>`,"Move anyway"],
    unlock:["Force unlock",`${escapeHtml(err&&err.lock?lockText(err.lock):"")} Unlocking lets others change ${name} now; anything they have not saved will be refused, and they are told.`,
      `<label>Reason (optional)<input name="reason" autocomplete="off"></label>`,"Unlock"],
    wip:["Go over the limit",`${escapeHtml(((err&&err.impact)||[""])[0])} Move ${name} to ${COL_LABEL[column]} anyway? Going over is recorded and the other owners are told.`,"","Move anyway"],
    dependencies:["Override dependency",`${name} waits on ${escapeHtml(((err&&err.impact)||[]).join(", "))}. Move it to ${COL_LABEL[column]} anyway? The override is recorded and the other owners are told.`,"","Move anyway"],
  }[kind];
  f.innerHTML=`<h2 id="move-dialog-title">${view[0]}</h2><p>${view[1]}</p>${view[2]}<div class="error" id="move-error" role="alert"></div><div class="actions"><button type="button" class="quiet" data-move-cancel>Cancel</button><button type="submit">${view[3]}</button></div>`;
  if(kind==="hold")fillAssignees(t.project_id,f.querySelector('select[name="owner_user_id"]'),t.owner_user_id);
  return new Promise(resolve=>{
    let settled=false;const done=v=>{if(settled)return;settled=true;if(d.open)d.close();resolve(v)};
    f.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(f));
      if(kind==="dependencies")return done({override_dependencies:true});
      if(kind==="wip")return done({override_wip:true});
      if(kind==="impact")return done({confirmed:true});
      if(kind==="unlock")return done({reason:data.reason||""});
      if(kind==="submit"||kind==="accept")return done({confirmed:true,note:data.note||""});
      done(data)};
    f.querySelector("[data-move-cancel]").onclick=()=>done(null);
    d.addEventListener("close",()=>done(null),{once:true});
    d.showModal();(f.querySelector("input:not([type=radio]),textarea")||f.querySelector('button[type="submit"]'))?.focus();
  });
}
async function moveCard(t,column,beforeId=null){
  const pid=t.project_id,from=boardColumn(t),kind=moveDialogKind(t,column),fromOrder=columnOrder(pid,from);
  let extra={};
  if(kind){const answer=await askMove(kind,t,column);if(!answer){boardAnnounce("Move cancelled.");return}extra=answer}
  const send=more=>api(`/api/tasks/${encodeURIComponent(t.id)}/board-move`,{method:"POST",body:JSON.stringify({to_column:column,expected_revision:t.revision,...extra,...more})});
  try{
    // An owner confirms a dependency override and a work-in-progress override, one after the other.
    let out,more={};
    for(;;){
      try{out=await send(more);break}
      catch(err){
        if(err.status!==409||!["dependencies","wip"].includes(err.confirm)||more[err.confirm==="wip"?"override_wip":"override_dependencies"])throw err;
        const ok=await askMove(err.confirm,t,column,err);if(!ok){boardAnnounce("Move cancelled.");await load();return}
        more={...more,...ok};
      }
    }
    if(out.request){showToast(`Sent to an owner for approval: “${t.title}” to ${COL_LABEL[column]}.`);await load();return}
    const moved=out.task;Object.assign(t,moved);
    if(boardColumn(t)===column){   // land where it was dropped; from the menu or a column head, at the end
      const order=columnOrder(pid,column,t.id),at=beforeId?order.indexOf(beforeId):-1;
      order.splice(at<0?order.length:at,0,t.id);
      try{await saveColumnOrder(pid,column,order,false)}catch{}
    }
    const landed=boardColumn(t),waits=(t.blocked_by||[]).map(p=>p.title).join(", ");
    const text=`Moved “${t.title}” from ${COL_LABEL[from]} to ${COL_LABEL[column]}.`+(landed==="blocked"&&column!=="blocked"&&waits?` It shows under Blocked until ${waits} is completed.`:"");
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
    await api(`/api/tasks/${encodeURIComponent(t.id)}/undo-move`,{method:"POST",body:JSON.stringify({event_id:eventId})});
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
  drag.card=null;drag.active=false;drag.ghost=null;
  if(!active)return;
  drag.suppressClick=true;setTimeout(()=>{drag.suppressClick=false},0);
  const t=state.tasks.find(x=>x.id===id),lease=drag.lease;drag.lease=null;
  if(!drop||!over||!t){boardAnnounce("Move cancelled.");lease?.then(()=>dropLease(id));return}
  lease.then(got=>{
    if(!got.ok){const text=leaseRefusal(t,got.err);showToast(text,null,null,true);boardAnnounce(text);return load()}
    return Promise.resolve(placeDrop(t,over,before)).finally(()=>dropLease(id));
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
document.addEventListener("touchmove",e=>{if(drag.active)e.preventDefault()},{passive:false});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&drag.active){e.preventDefault();endDrag(false)}});
boardBody.addEventListener("click",e=>{if(drag.suppressClick){e.preventDefault();e.stopPropagation()}},true);
// The Move to menu: the same moves from the keyboard, a screen reader or a phone.
function openMoveMenu(btn){
  const menu=document.querySelector("#move-menu"),t=state.tasks.find(x=>x.id===btn.dataset.moveMenu);if(!t)return;
  const col=boardColumn(t),order=columnOrder(t.project_id,col),at=order.indexOf(t.id);
  const items=BOARD_COLUMNS.filter(([k])=>k!==col).map(([k,l])=>`<button type="button" role="menuitem" data-move-to="${k}">Move to ${l}</button>`);
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
async function takeLease(id,kind){
  const held=leases.get(id);if(held){held.last=Date.now();return {ok:true}}
  try{
    const {lock}=await api(taskApi(id,"/lock"),{method:"POST",body:JSON.stringify({kind})});
    const lease={token:lock.token,kind,last:Date.now(),timer:null};
    lease.timer=setInterval(async()=>{
      if(kind==="edit"&&Date.now()-lease.last>60000)return dropLease(id);   // an idle form lets go
      try{await api(taskApi(id,"/lock/renew"),{method:"POST",body:JSON.stringify({token:lease.token})})}
      catch(err){clearInterval(lease.timer);leases.delete(id);if(kind==="edit")showLockBanner(err.lock,err.message)}
    },20000);
    leases.set(id,lease);return {ok:true};
  }catch(err){if(err.status===409)return {ok:false,err};throw err}
}
async function dropLease(id){
  const lease=leases.get(id);if(!lease)return;leases.delete(id);clearInterval(lease.timer);
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
  await load();await openDetail(task.id);
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
  g.bar.style.left=`${g.x0}%`;g.bar.style.width=`${g.w0}%`;
  const done={...g};gdrag.bar=null;gdrag.active=false;return done;
}
async function rescheduleTask(t,dates,days){
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
      try{await api(taskApi(t.id,"/undo-move"),{method:"POST",body:JSON.stringify({event_id:out.undo.event_id})});showToast(`Dates restored for “${t.title}”.`)}
      catch(err){showToast(`The move was not undone: ${err.message}`,null,null,true)}
      await load();
    },false,out.undo.seconds*1000);
    else showToast(text);
    announce(text);
  }catch(err){showToast(`“${t.title}” keeps its dates: ${err.message}`,null,null,true);announce(err.message)}
  finally{await dropLease(t.id);await load()}
}
const ganttEl=document.querySelector("#gantt");
ganttEl.addEventListener("pointerdown",e=>{
  const bar=e.target.closest("[data-drag]");
  if(!bar||e.button>0||e.pointerType==="touch"||e.target.closest(".step,.step-more"))return;
  const t=state.tasks.find(x=>x.id===bar.dataset.drag);if(!t||!canDragBar(t))return;
  const tl=bar.closest(".timeline");
  Object.assign(gdrag,{bar,t,x:e.clientX,pointer:e.pointerId,edge:e.target.closest("[data-edge]")?.dataset.edge||null,
    x0:+bar.dataset.x,w0:+bar.dataset.w,dayPct:DAY/(+ganttEl.dataset.span)*100,px:tl.getBoundingClientRect().width,days:0,active:false,lease:null});
});
document.addEventListener("pointermove",e=>{
  const g=gdrag;if(!g.bar||e.pointerId!==g.pointer)return;
  const dx=e.clientX-g.x;
  if(!g.active){if(Math.abs(dx)<5)return;g.active=true;hideTip();g.bar.classList.add("is-dragging");document.body.classList.add("bar-dragging");
    try{g.bar.setPointerCapture(g.pointer)}catch{};g.lease=takeLease(g.t.id,"drag")}
  e.preventDefault();
  g.days=Math.round(dx/(g.px*g.dayPct/100));
  const d=g.days*g.dayPct;let left=g.x0,width=g.w0;
  if(g.edge==="start"){const cut=Math.min(d,g.w0-g.dayPct);left=g.x0+cut;width=g.w0-cut}
  else if(g.edge==="end")width=Math.max(g.dayPct,g.w0+d);else left=g.x0+d;
  g.bar.style.left=`${left}%`;g.bar.style.width=`${width}%`;
  g.next=barDates(g.t,g.edge,g.days);showDragTip(e.clientX,e.clientY,dateTip(g.t,g.next,g.days));
});
document.addEventListener("pointerup",async e=>{
  if(!gdrag.bar||e.pointerId!==gdrag.pointer)return;
  const g=endBarDrag();if(!g.active)return;
  gdrag.suppressClick=true;setTimeout(()=>{gdrag.suppressClick=false},0);
  const got=await g.lease;
  if(got&&!got.ok){showToast(leaseRefusal(g.t,got.err),null,null,true);return load()}
  if(!g.days||(g.next.start_date===g.t.start_date&&g.next.due_date===g.t.due_date)){await dropLease(g.t.id);return}
  await rescheduleTask(g.t,g.next,g.days);
});
document.addEventListener("pointercancel",e=>{if(gdrag.bar&&e.pointerId===gdrag.pointer){const g=endBarDrag();if(g&&g.active)g.lease?.then(()=>dropLease(g.t.id))}});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&gdrag.active){e.preventDefault();const g=endBarDrag();announce("Move cancelled.");g.lease?.then(()=>dropLease(g.t.id))}});
ganttEl.addEventListener("click",e=>{if(gdrag.suppressClick){e.preventDefault();e.stopPropagation()}},true);
// XV92JJ: bulk changes. On a project's Board and List, owners and the project's managers tick tasks
// (Shift-click for a range, Space to toggle, Shift+Arrow to extend in the list), then change status,
// assignee or due dates for all of them in one previewed, all-or-nothing, undoable change.
const bulk={ids:new Set(),pid:null,last:null,action:"status"};
function bulkScope(){const r=currentRoute();return r.name==="project"&&r.id&&canMoveOnBoard(r.id)?r.id:null}
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
    bar.innerHTML=`<span class="bulk-count" id="bulk-count"></span>
      <label class="bulk-field"><span class="bulk-label">Change</span><select id="bulk-action"><option value="status">Status</option><option value="assignee">Assignee</option><option value="due_shift">Due dates</option></select></label>
      <span id="bulk-value" class="bulk-field"></span>
      <button type="button" id="bulk-review">Review change…</button>
      <button type="button" class="quiet" id="bulk-clear">Clear selection</button>`;
    bar.querySelector("#bulk-action").value=bulk.action;fillBulkValue(pid);
    bar.querySelector("#bulk-action").addEventListener("change",e=>{bulk.action=e.target.value;fillBulkValue(pid)});
    bar.querySelector("#bulk-review").addEventListener("click",()=>reviewBulk(pid));
    bar.querySelector("#bulk-clear").addEventListener("click",()=>{clearBulk();document.querySelector("[data-pick]")?.focus()});
    bar.hidden=false;document.body.classList.add("has-bulk-bar");
  }
  bar.querySelector("#bulk-count").textContent=`${n} selected`;
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
  const payload=bulkPayload();
  let plan;
  try{({preview:plan}=await api(`/api/projects/${encodeURIComponent(pid)}/bulk/preview`,{method:"POST",body:JSON.stringify(payload)}))}
  catch(err){showToast(`Cannot change these tasks: ${err.message}`,null,null,true);return}
  const answer=await askBulk(plan);if(!answer)return;
  if(answer.drop){plan.blocked.forEach(b=>bulk.ids.delete(b.id));syncPicks();if(bulk.ids.size)return reviewBulk(pid);return}
  try{
    const out=await api(`/api/projects/${encodeURIComponent(pid)}/bulk/apply`,{method:"POST",body:JSON.stringify({...payload,
      expected_revisions:Object.fromEntries(plan.ok.map(i=>[i.id,i.revision])),override_wip:!!answer.override_wip})});
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
    try{
      for(const k of changed)await api(`/api/projects/${encodeURIComponent(pid)}/wip-limits`,{method:"POST",body:JSON.stringify({column:k,max_tasks:data[k]?Number(data[k]):null,reason:data.reason})});
      d.close();showToast(changed.length?`Saved ${changed.length} limit${changed.length===1?"":"s"}.`:"No limits changed.");await load();
    }catch(err){f.querySelector("#move-error").textContent=err.message;await load()}
  };
  d.showModal();f.querySelector("input")?.focus();
}
document.querySelector("#project-capture").addEventListener("click",()=>openCapture(currentRoute().id));
document.querySelector("#project-save-template").addEventListener("click",()=>saveProjectAsTemplate(currentRoute().id));
document.querySelector("#project-close").addEventListener("click",()=>closeProject(currentRoute().id));
// VPYGY5: the Command Center. Everything is drawn from what is already loaded (tasks, projects, the Owner's
// cached requests) plus /api/portfolio; each count links to the list behind it, and rows open the task panel.
function isOwner(){return !!state.user&&state.user.global_role==="owner"}
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
  ].filter(Boolean);
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
        <span class="work-meta">${escapeHtml(r.requested_by_name||"")} · ${escapeHtml(r.project_name||"")} · ${escapeHtml(new Date(r.requested_at).toLocaleString())}${r.reason?` · “${escapeHtml(r.reason)}”`:""}</span></div>
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
  if(pid&&[...project.options].some(o=>o.value===pid))project.value=pid;
  fillPredecessors();fillAssignees(project.value,form.querySelector('select[name="owner_user_id"]'));
  form.querySelector(".error").textContent="";
  document.querySelector("#task-dialog").showModal();
}
// Menus (More, account): a button with aria-expanded and a list of menuitems. Arrow keys move, Escape
// closes and gives focus back to the button, a click outside closes, and choosing an item closes it first.
function closeMenus(except){document.querySelectorAll(".menu:not([hidden])").forEach(m=>{if(m===except)return;m.hidden=true;const b=document.querySelector(`[aria-controls="${m.id}"]`);if(b)b.setAttribute("aria-expanded","false")})}
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
document.querySelector("#login-form").addEventListener("submit",async e=>{e.preventDefault();try{const data=await api("/api/login",{method:"POST",body:JSON.stringify({email:e.target.querySelector("#email").value,password:e.target.querySelector("#password").value})});Object.assign(state,data)}catch(err){document.querySelector("#login-error").textContent=err.message;return}showApp();await loadOrSay()});
// H1: after signing out, reload the page so nothing the previous person saw (Inbox, requests, an open task,
// loaded tasks) survives for the next person on this browser. The hash is dropped too.
function signedOut(){state.user=state.csrf=null;location.replace(location.pathname)}
document.querySelector("#logout").onclick=async()=>{await api("/api/logout",{method:"POST",body:"{}"});signedOut()};
document.querySelector("#logout-all").onclick=async()=>{await api("/api/logout-all",{method:"POST",body:"{}"});signedOut()};
document.querySelector("#close-project").onclick=()=>closeProject(document.querySelector("#project-filter").value);
async function closeProject(pid){
  if(!pid){alert("Select a single project in the filter to close it.");return}
  const note=prompt("Closure note (describe the outcome or any residual work):","");
  if(note===null)return;
  try{await api(`/api/projects/${pid}/close`,{method:"POST",body:JSON.stringify({note})});await load()}
  catch(err){
    if(/outstanding/i.test(err.message)&&confirm(`${err.message}\n\nProceed with an EXCEPTIONAL owner closure that preserves a residual-work snapshot?`)){
      try{await api(`/api/projects/${pid}/close`,{method:"POST",body:JSON.stringify({note,exceptional:true})});await load()}
      catch(e2){alert(e2.message)}
    }else{alert(err.message)}
  }
}
// PZTYC9: a filter change rewrites the Home link (replaceState, so Back leaves the screen) and re-renders.
for(const id of ["project-filter","status-filter","entity-filter","crit-filter","band-filter","risk-filter"]){document.querySelector(`#${id}`).onchange=filtersChanged}document.querySelector("#open-only").onchange=filtersChanged;document.querySelector("#owner-filter").oninput=filtersChanged;
// QY0WG2: changing the sort re-fetches the list in the chosen server-side order.
document.querySelector("#sort-filter").onchange=e=>{state.sort=e.target.value;syncFilters();load()};
document.querySelector("#new-project").onclick=()=>document.querySelector("#project-dialog").showModal();document.querySelector("#new-task").onclick=openCapture;
document.querySelector("#portfolio-btn").onclick=openPortfolio;
// 5WZ4A8: project history (schedule changes, closure, imports, owner-action decisions).
// ZSZ9T2/K62ZAP: the server sends only schedule changes, closure and their own events to anyone
// other than the Owner, the Chairman or a project manager.
const PROJECT_EVENT_LABELS={board_reordered:"Board order changed",bulk_change:"Bulk change",bulk_change_undone:"Bulk change undone",wip_limit_changed:"Work-in-progress limit changed",wip_limit_override:"Work-in-progress limit overridden",project_schedule_changed:"Project dates changed",project_closed:"Project closed",import_committed:"Import committed",protected_action_blocked:"Owner action blocked",protected_action_approved:"Owner request approved",protected_action_rejected:"Owner request rejected",protected_action_cancelled:"Owner request cancelled"};
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
  const rows=(templates||[]).map(t=>`<li><strong>${escapeHtml(t.name)}</strong> · <span class="muted">${escapeHtml(t.kind)} · ${t.task_count} task(s)${(t.roles||[]).length?` · roles: ${escapeHtml(t.roles.map(r=>TEMPLATE_ROLE_LABELS[r]||r).join(", "))}`:""}</span>
    ${t.description?`<br><em class="muted">${escapeHtml(t.description)}</em>`:""}
    <br><button type="button" class="link" data-use-template="${escapeHtml(t.id)}" data-kind="${escapeHtml(t.kind)}" data-roles="${escapeHtml((t.roles||[]).join(","))}">Use</button>
    <button type="button" class="link" data-delete-template="${escapeHtml(t.id)}">Delete</button></li>`).join("")||"<li>No templates yet. Save a project or a task as a template to reuse it.</li>";
  document.querySelector("#templates-body").innerHTML=`<h2>Templates</h2>
    <p class="fine">A template copies structure — titles, hierarchy, dependencies, criticality, attachment links, relative dates and a suggested owner <em>role</em> (App Owner, Chairman, Project manager, member or viewer), never a named person. Never status, history or evidence. New tasks start in draft. When you use a template you pick who fills each role; a role you leave on automatic goes to its only holder on the target project, otherwise the task stays unassigned.</p>
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
  try{
    let url,payload,done;
    if(kind==="project"){
      const name=prompt("New project name:");if(!name)return;
      const anchor_date=prompt("Anchor date for relative schedule (YYYY-MM-DD, blank to leave dates unset):")||null;
      url=`/api/templates/${id}/create-project`;payload={name,anchor_date};done="Project created from template.";
    }else{
      const project_id=prompt("Target project id to add this task subtree to:\n(Tip: open the project, a task's detail shows its project.)");if(!project_id)return;
      const parent_task_id=prompt("Parent task id (optional, blank for top-level):")||null;
      const anchor_date=prompt("Anchor date for relative schedule (YYYY-MM-DD, blank to leave dates unset):")||null;
      url=`/api/templates/${id}/create-task`;payload={project_id,parent_task_id,anchor_date};done="Task subtree created from template.";
    }
    const finish=async role_assignments=>{
      await api(url,{method:"POST",body:JSON.stringify({...payload,role_assignments})});
      alert(done);document.querySelector("#templates-dialog").close();await load();
    };
    if(!(roles||[]).some(r=>r!=="owner"))return await finish({});
    await renderRolePicker(kind,roles,finish);
  }catch(x){const e=document.querySelector("#templates-error");if(e)e.textContent=x.message;else alert(x.message)}
}
async function renderRolePicker(kind,roles,finish){
  const {users}=await api("/api/users");
  const active=(users||[]).filter(u=>u.active);
  const fallback=kind==="project"?"Leave unassigned":"Automatic (the role's only holder, else unassigned)";
  const rows=roles.map(r=>{
    const label=escapeHtml(TEMPLATE_ROLE_LABELS[r]||r);
    if(r==="owner")return `<label>${label}<select disabled><option>${escapeHtml(state.user.display_name)} (App Owner)</option></select></label>`;
    const people=active.filter(u=>r==="chairman"?u.global_role==="chairman":u.global_role==="member");
    const options=people.map(u=>`<option value="${escapeHtml(u.id)}">${escapeHtml(u.display_name)}</option>`).join("");
    return `<label>${label}<select name="${escapeHtml(r)}"><option value="">${escapeHtml(fallback)}</option>${options}</select></label>`;
  }).join("");
  const hint=kind==="project"?"Each person you pick is given that role on the new project and is pre-filled on its tasks.":"A person you pick must already hold that role on the target project.";
  document.querySelector("#templates-body").innerHTML=`<form id="template-role-form"><h2>Who fills each role?</h2>
    <p class="fine">${hint}</p>${rows}
    <div class="actions"><button type="button" class="quiet" id="template-role-back">Back</button><button>Create</button></div>
    <div class="error" id="templates-error"></div></form>`;
  document.querySelector("#template-role-back").addEventListener("click",openTemplates);
  document.querySelector("#template-role-form").addEventListener("submit",async ev=>{
    ev.preventDefault();
    const picks={};for(const [role,user] of new FormData(ev.target))if(user)picks[role]=user;
    try{await finish(picks)}catch(x){document.querySelector("#templates-error").textContent=x.message}
  });
}
async function markFinalResult(taskId,sourceType,sourceId){
  try{await api("/api/final-results",{method:"POST",body:JSON.stringify({task_id:taskId,source_type:sourceType,source_id:sourceId})});await openDetail(taskId)}
  catch(x){alert(x.message)}
}
async function unmarkFinalResult(taskId,resultId){
  try{await api("/api/final-results",{method:"DELETE",body:JSON.stringify({result_id:resultId})});await openDetail(taskId)}
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
    const where=r.source_type==="attachment"?`<code class="att-path">${escapeHtml(r.attachment_path||"")}</code>`:`accepted submission v${escapeHtml(String(r.submission_version||""))}`;
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
    const projects=(results.projects||[]).map(p=>`<li>${escapeHtml(p.name)}</li>`).join("")||"<li>No matching projects.</li>";
    document.querySelector("#search-body").innerHTML=`<h2>Search: ${escapeHtml(q)}</h2><h3>Tasks</h3><ul class="people-list">${tasks}</ul><h3>Projects</h3><ul class="people-list">${projects}</ul>`;
    document.querySelectorAll("#search-body [data-detail]").forEach(b=>b.addEventListener("click",()=>{document.querySelector("#search-dialog").close();openDetail(b.dataset.detail)}));
    const d=document.querySelector("#search-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#search-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#search-dialog").showModal()}
}
document.querySelector('#task-form select[name="project_id"]').onchange=e=>{fillPredecessors();fillAssignees(e.target.value,document.querySelector('#task-form select[name="owner_user_id"]'))};
document.querySelector("#people").onclick=openPeople;
async function openInbox(){
  try{
    const [data,ownerQueue]=await Promise.all([
      api("/api/notifications"),
      state.user.global_role==="owner"?api("/api/owner-action-requests"):Promise.resolve({requests:[]}),
    ]);
    state.notifications=data.notifications;state.unread=data.unread;updateBell();
    renderInbox(data.notifications,ownerQueue.requests);
    if(currentRoute().name==="home")renderHome();   // Home shows the same cached requests
  }catch(err){document.querySelector("#inbox-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
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
  const open=n.task_id?`<button type="button" class="link" data-detail="${escapeHtml(n.task_id)}"${unread?` data-read-on-open="${escapeHtml(n.id)}"`:""}>Open task</button>`:"";
  const mark=unread?`<button type="button" class="link" data-read="${escapeHtml(n.id)}">Mark read</button>`:"";
  return `<li class="note-row${unread?" unread":""}"><span class="note-dot" aria-hidden="true"></span><div class="note-main"><p class="note-summary">${unread?'<span class="sr-only">Unread: </span>':""}${escapeHtml(n.summary)}</p>
    <p class="note-meta">${n.task_title&&!String(n.summary||"").includes(n.task_title)?`${escapeHtml(n.task_title)} · `:""}<time datetime="${escapeHtml(n.created_at)}">${escapeHtml(when)}</time></p></div><div class="note-actions">${open}${mark}</div></li>`;
}
function noteList(items){
  const days=["Today","Yesterday","Earlier"].map(label=>[label,items.filter(n=>noteDay(n.created_at)===label)]).filter(([,rows])=>rows.length);
  return days.map(([label,rows])=>`<h3 class="note-day">${label}</h3><ul class="note-list">${rows.map(noteRow).join("")}</ul>`).join("");
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
    <div class="error" id="inbox-error" role="alert" tabindex="-1"></div>${content}`;
  document.querySelector("#read-all").addEventListener("click",markAllRead);
  document.querySelectorAll("#inbox-body [data-read]").forEach(b=>b.addEventListener("click",()=>markRead(b.dataset.read)));
  document.querySelectorAll("#inbox-body [data-request-decision]").forEach(b=>b.addEventListener("click",()=>decideOwnerRequest(b.dataset.requestId,b.dataset.requestDecision)));
  document.querySelectorAll("#inbox-body [data-detail]").forEach(b=>b.addEventListener("click",()=>{openDetail(b.dataset.detail);if(b.dataset.readOnOpen)markRead(b.dataset.readOnOpen)}));
}
// 0D9Q3X: the Owner decides from the inbox, so each request says what it would change and why.
const REQUEST_LABELS={update_task_status:"Status change",accept_submission:"Accept submission",request_changes:"Request changes",reopen_task:"Reopen task",set_on_hold:"Put on hold",approve_schedule_proposal:"Approve schedule change",reject_schedule_proposal:"Reject schedule change",close_project:"Close project"};
function requestTitle(r){return `${REQUEST_LABELS[r.action]||r.action.replaceAll("_"," ")} · ${r.task_title||r.project_name}`}
function requestDetail(r){
  const p=r.payload||{};
  const change=r.action==="update_task_status"&&p.status
    ?`<p>Change status ${p.from_status?`from <strong>${escapeHtml(statusLabel(p.from_status))}</strong> `:""}to <strong>${escapeHtml(statusLabel(p.status))}</strong></p>`:"";
  const reason=r.reason?`<p><em>Reason: ${escapeHtml(r.reason)}</em></p>`:`<p class="muted">No reason given.</p>`;
  return `<div class="request-detail">${change}${reason}</div>`;
}
// 0D9Q3X: a 409 means the record moved on under the user; show the current one instead of the stale form.
// The first line says what happened and what to do; the server's own reason follows on its own line.
const TASK_CONFLICT="This task changed since you opened it, so nothing was saved.";
function showConflict(box,text,detail){if(!box)return;box.style.color="";box.innerHTML=escapeHtml(text)+(detail&&detail!==text?`<small class="conflict-detail">${escapeHtml(detail)}</small>`:"");box.focus?.()}
async function reloadTaskAfterConflict(taskId,errorId,detail){
  await load().catch(()=>{});const task=await openDetail(taskId);
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
  const box=()=>document.querySelector(`#${errorId}`),err=box();if(err)err.textContent="";
  try{await api(`/api/owner-action-requests/${id}/decision`,{method:"POST",body:JSON.stringify({decision,reason})});await load();await openInbox()}
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
async function fillAssignees(projectId,select,selectedId){
  if(!select)return;
  select.innerHTML='<option value="">Unassigned</option>';
  if(!projectId)return;
  try{
    const {users}=await api(`/api/assignable-users?project_id=${encodeURIComponent(projectId)}`);
    for(const u of users){const o=new Option(u.display_name,u.id);if(u.id===selectedId)o.selected=true;select.add(o)}
  }catch{}
}
document.querySelector("#project-form").addEventListener("submit",async e=>{e.preventDefault();const button=e.submitter;if(button?.value==="cancel"){e.target.closest("dialog").close();return}try{await api("/api/projects",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});e.target.reset();e.target.closest("dialog").close();await load()}catch(err){e.target.querySelector(".error").textContent=err.message}});
document.querySelector("#task-form").addEventListener("submit",async e=>{e.preventDefault();const button=e.submitter;if(button?.value==="cancel"){e.target.closest("dialog").close();return}try{const {task}=await api("/api/tasks",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});e.target.reset();e.target.closest("dialog").close();await load();if(task&&currentRoute().name==="portfolio"&&!visibleTasks().some(t=>t.id===task.id))showToast(`“${task.title}” was added · the current filters hide it`,"Show it",showAllOnPortfolio)}catch(err){e.target.querySelector(".error").textContent=err.message}});
const STATUSES=["draft","assigned","in_progress","submitted","changes_requested","completed","on_hold","delayed","cancelled","abandoned","reopened"];
const CRITICALITIES=[["","Unrated"],["critical","Critical"],["high","High"],["normal","Normal"],["low","Low"]];
const GOVERNED=["submitted","completed","on_hold","reopened"];
// ARZWV7: a closed task is a fixed record; a Manager may only ask to move it back into ordinary work
// (service.py REOPEN_ONLY_STATUSES / REOPEN_EQUIVALENT_STATUSES). UI hints only — the server decides.
const BACK_TO_WORK=["draft","assigned","in_progress","delayed"];
const EVENT_LABELS={board_move_blocked:"Board move refused",dependency_override:"Dependency overridden",wip_limit_override:"Work-in-progress limit overridden",task_lock_forced:"Lock forced open",gantt_move_blocked:"Date drag refused",schedule_impact_confirmed:"Date change with consequences confirmed",import_committed:"Import committed",task_created:"Task created",task_updated:"Task updated",dependency_added:"Dependency added",dependency_removed:"Dependency removed",task_submitted:"Work submitted",submission_accepted:"Submission accepted",changes_requested:"Changes requested",task_reopened:"Task reopened",task_on_hold:"Put on hold",criticality_changed:"Criticality changed",parent_changed:"Parent changed",schedule_proposed:"Schedule change proposed",schedule_revised:"Schedule revised",schedule_proposal_rejected:"Schedule proposal rejected",attachment_added:"Attachment linked",attachment_removed:"Attachment link removed"};
const DIFF_FIELDS=[["title","Title"],["status","Status"],["criticality","Criticality"],["start_date","Start date"],["due_date","Due date"],["progress","Progress"],["description","Description"]];
let detailTaskId=null;

document.querySelector("#gantt").addEventListener("click",e=>{
  const ex=e.target.closest("[data-expand]");if(ex){toggleSteps(ex.dataset.expand);return}
  const more=e.target.closest("[data-more]");if(more){toggleMore(more);return}
  const b=e.target.closest("[data-detail]");
  if(b){
    // GF-6: a link inside a +N list hands focus to its +N button first, so closing the dialog
    // returns focus to a visible control instead of body.
    const list=b.closest(".step-more-list");
    if(list){const btn=document.querySelector(`[aria-controls="${CSS.escape(list.id)}"]`);if(btn)btn.focus()}
    hideTip();closeMoreLists();openDetail(b.dataset.detail);
  }
});
document.querySelector("#schedule-table").addEventListener("click",e=>{const b=e.target.closest("[data-detail]");if(b)openDetail(b.dataset.detail)});

async function openDetail(taskId){
  if(detailTaskId&&detailTaskId!==taskId&&leases.get(detailTaskId)?.kind==="edit")dropLease(detailTaskId);
  detailTaskId=taskId;
  try{
    const [d,ev]=await Promise.all([api(taskApi(taskId)),api(taskApi(taskId,"/events"))]);
    renderDetail(d.task,ev.events);
    openPanel(taskId);
    panelState.task=d.task;if(currentRoute().name==="task")shellTitle(currentRoute());
    return d.task;
  }catch(err){document.querySelector("#detail-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;openPanel(taskId);return null}
}
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
  const panel=document.querySelector("#detail-dialog");
  if(panel.hidden)return;
  panel.hidden=true;panelState.shown=null;
  for(const [id,l] of leases)if(l.kind==="edit")dropLease(id);
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
  return out.join("");
}
function roleLine(perms){
  if(perms.can_decide_protected)return "You are the App Owner. Changes apply directly and are recorded in History.";
  if(perms.can_request_protected)return "You manage this project. Protected changes go to the App Owner as requests.";
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
  const deps=(task.dependencies||[]).map(dep=>{
    const other=dep.direction==="incoming"?dep.predecessor_title:dep.successor_title;
    const flag=dep.blocking?' <span class="blocked-text">(blocking)</span>':"";
    // A closed task cannot lose a predecessor (it is the successor); it may still stop blocking another task.
    if(closed&&dep.direction==="incoming")return `<li>Depends on: <strong>${escapeHtml(other)}</strong>${flag}</li>`;
    return `<li>${dep.direction==="incoming"?"Depends on":"Blocks"}: <strong>${escapeHtml(other)}</strong>${flag}
      <span class="dep-remove"><input class="dep-reason" placeholder="Reason to remove" aria-label="Reason to remove dependency">
      <button type="button" class="link" data-remove-pred="${escapeHtml(dep.predecessor_task_id)}" data-remove-succ="${escapeHtml(dep.successor_task_id)}">Remove</button></span></li>`;
  }).join("")||"<li>No dependencies.</li>";
  const candidates=state.tasks.filter(t=>t.project_id===task.project_id&&t.id!==task.id);
  const addOptions=candidates.map(t=>`<option value="${escapeHtml(t.id)}">${escapeHtml(t.title)}</option>`).join("");
  const timeline=events.slice().reverse().map(renderEvent).join("")||"<li>No history.</li>";
  const reviewers=buildReviewers(task,closed);
  const attachments=buildAttachments(task);
  const subtasks=buildSubtasks(task,closed);
  const schedule=buildSchedule(task,closed);
  const critForm=closed?`<div class="crit-confirm"><h3>Criticality</h3><p>Current: ${critLabel(task.criticality,true)}</p></div>`:`<div class="crit-confirm"><h3>Criticality</h3>
    <p>Current: ${critLabel(task.criticality,true)} — changes are confirmed with a reason and recorded.</p>
    <form id="crit-form" data-revision="${escapeHtml(String(task.revision))}"><label>Set level<select name="criticality">${crit}</select></label>
      <label>Reason (evidence for this level)<input name="reason" required></label>
      <div class="actions"><button>Confirm criticality</button></div><div class="error" id="crit-error"></div></form></div>`;
  const closedNote=closed?`<div class="state-note" role="note"><p><strong>${escapeHtml(statusLabel(task.status))}.</strong> Reopen this task to change it.${perms.can_manage_files?" Attachments and final results can still be added.":""}</p>
    ${canReopen?`<button type="button" class="link" data-goto-reopen>${perms.can_decide_protected?"Reopen task…":"Request reopening…"}</button>`:`<p>Ask the App Owner to reopen it.</p>`}</div>`:"";
  // 5GK6SB: name the decision buttons this viewer actually has under Lifecycle.
  const decide=decisionLabels(perms.can_decide_protected);
  const statusHint=submitted?`<p class="field-hint" id="status-locked-hint">Status is locked while this work is in review. ${perms.can_decide_protected||perms.can_request_protected?escapeHtml(`Use ${decide.accept} or ${decide.changes} under Lifecycle.`):"The App Owner will Accept or Request changes."}</p>`:"";
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
  const editForm=closed?"":`<form id="detail-edit">
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
  const addDep=closed?"":`<div class="add-dep">
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
    <div class="panel-sections" role="group" aria-label="Jump to a section">${[["desc","Details"],["subtasks","Steps"],["deps","Dependencies"],["attachments","Files"],["history","History"]].map(([c,l])=>`<button type="button" class="link" data-jump="${c}">${l}</button>`).join("")}</div>
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
    ${editForm}
    <p><button type="button" class="link" id="save-task-template">Save this task (and its subtasks) as a template</button></p>
    <div class="history"><h3>History</h3><ul>${timeline}</ul></div>`;
  document.querySelector("#detail-edit")?.addEventListener("submit",e=>submitDetailEdit(e,{statusLocked:submitted}));
  document.querySelectorAll("#detail-body [data-jump]").forEach(b=>b.addEventListener("click",()=>document.querySelector(`#detail-body .${b.dataset.jump}`)?.scrollIntoView({block:"start"})));
  document.querySelector("#add-dep-button")?.addEventListener("click",addDependency);
  document.querySelector("#detail-body [data-goto-reopen]")?.addEventListener("click",()=>{const f=document.querySelector("#reopen-form");if(!f)return;f.scrollIntoView({behavior:"smooth",block:"center"});f.querySelector("input")?.focus({preventScroll:true})});
  document.querySelector("#detail-body").querySelectorAll("[data-remove-pred]").forEach(b=>b.addEventListener("click",removeDependency));
  fillAssignees(task.project_id,document.querySelector('#detail-edit select[name="owner_user_id"]'),task.owner_user_id);
  wireLifecycle(task);
  wireEditLease(task);
  wireReviewers(task);
  wireAttachments(task);
  document.querySelector("#save-task-template").addEventListener("click",()=>saveTaskAsTemplate(task.id));
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

function buildSchedule(task,closed){
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
    ${closed?`<div class="error" id="sched-error"></div>`:`<form id="sched-form"><h4 class="sched-h">Propose a schedule change</h4>
      <div class="grid"><label>New start<input name="start_date" type="date"></label><label>New due<input name="due_date" type="date"></label></div>
      <label>Reason<input name="reason" required></label>
      <div class="actions"><button>Propose</button></div><div class="error" id="sched-error"></div></form>`}
    ${history.length?`<h4 class="sched-h">History</h4><ul>${historyRows}</ul>`:""}</div>`;
}

async function submitSchedule(e){
  e.preventDefault();const err=document.querySelector("#sched-error");err.textContent="";err.style.color="";
  try{
    const {proposal}=await api(taskApi(detailTaskId,"/schedule-proposals"),{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
    const impacted=proposal.impacted_successors||[];
    await load();await openDetail(detailTaskId);
    if(impacted.length){const el=document.querySelector("#sched-error");if(el){el.style.color="#667085";el.textContent=`Heads up — approving this may affect: ${impacted.map(t=>t.title).join(", ")} (they are not moved automatically).`;}}
  }catch(x){err.textContent=x.message}
}
async function decideSchedule(id,action,btn){
  const err=document.querySelector("#sched-error");if(err)err.textContent="";
  try{
    let outcome;
    if(action==="approve"){outcome=await api(`/api/schedule-proposals/${id}/approve`,{method:"POST",body:"{}"});}
    else{const reason=btn.parentElement.querySelector(".sched-reject-reason").value;outcome=await api(`/api/schedule-proposals/${id}/reject`,{method:"POST",body:JSON.stringify({reason})});}
    await load();await openDetail(detailTaskId);
    if(outcome.request){const current=document.querySelector("#sched-error");current.style.color="#0c7c86";current.textContent="Owner request created; the live schedule is unchanged."}
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
  e.preventDefault();const err=document.querySelector("#parent-error");err.textContent="";
  const parent_task_id=e.target.querySelector('select[name="parent_task_id"]').value;
  try{await api(taskApi(detailTaskId,"/parent"),{method:"POST",body:JSON.stringify({parent_task_id})});await load();await openDetail(detailTaskId)}
  catch(x){err.textContent=x.message}
}

async function submitCriticality(e){
  e.preventDefault();const err=document.querySelector("#crit-error");err.textContent="";
  try{await api(taskApi(detailTaskId,"/criticality"),{method:"POST",body:JSON.stringify({...Object.fromEntries(new FormData(e.target)),expected_revision:Number(e.target.dataset.revision)})});await load();await openDetail(detailTaskId)}
  catch(x){err.textContent=x.message}
}

// 5GK6SB: one source for the submission-decision button labels, shared with the locked-Status hint.
function decisionLabels(canDecide){
  return canDecide?{accept:"Accept & complete",changes:"Request changes"}
    :{accept:"Request Owner acceptance",changes:"Request Owner to return changes"};
}

function buildLifecycle(task,extra=""){
  const canDecide=task.permissions?.can_decide_protected,canRequest=task.permissions?.can_request_protected;
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
  if(!closed&&task.status!=="submitted"){
    actions+=`<form data-life="submit"><label>Submit work (note)<input name="note"></label><div class="actions"><button>Submit for acceptance</button></div></form>`;
  }
  if(task.status==="submitted"&&pending){
    if(canDecide||canRequest){
      actions+=`<form data-life="accept" data-sid="${escapeHtml(pending.id)}"><label>Acceptance note<input name="decision_note"></label><div class="actions"><button>${escapeHtml(decide.accept)}</button></div></form>`;
      actions+=`<form data-life="changes" data-sid="${escapeHtml(pending.id)}"><label>Reason for changes<input name="reason" required></label><div class="actions"><button>${escapeHtml(decide.changes)}</button></div></form>`;
    }else actions+=`<p class="blocked-text">Only the App Owner can decide this submission.</p>`;
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
  const rows=(task.reviewers||[]).map(r=>`<li>${escapeHtml(r.display_name)} · ${escapeHtml(r.role)}
    ${closed?"":`<button type="button" class="link" data-remove-reviewer-user="${escapeHtml(r.user_id)}" data-remove-reviewer-role="${escapeHtml(r.role)}">Remove</button>`}</li>`).join("")||"<li>No reviewers or approvers.</li>";
  if(closed)return `<div class="reviewers"><h3>Reviewers &amp; approvers</h3><ul>${rows}</ul></div>`;
  return `<div class="reviewers"><h3>Reviewers &amp; approvers</h3><ul>${rows}</ul>
    <div class="add-reviewer">
      <select id="reviewer-user"><option value="">Choose a person…</option></select>
      <select id="reviewer-role"><option value="approver">Approver</option><option value="reviewer">Reviewer</option><option value="collaborator">Collaborator</option></select>
      <button type="button" id="add-reviewer-button">Add</button>
      <div class="error" id="reviewer-error"></div>
    </div></div>`;
}

function wireLifecycle(task){
  document.querySelectorAll("#detail-body [data-life]").forEach(form=>form.addEventListener("submit",e=>lifecycleAction(e,task)));
  const holdOwner=document.querySelector('[data-life="hold"] select[name="owner_user_id"]');
  if(holdOwner)fillAssignees(task.project_id,holdOwner,task.owner_user_id);
}

async function lifecycleAction(e,task){
  e.preventDefault();
  const form=e.target,kind=form.dataset.life,err=document.querySelector("#lifecycle-error");err.textContent="";
  const body=Object.fromEntries(new FormData(form));
  try{
    let outcome;
    if(kind==="submit")outcome=await api(taskApi(task.id,"/submit"),{method:"POST",body:JSON.stringify(body)});
    else if(kind==="accept")outcome=await api(`/api/submissions/${form.dataset.sid}/accept`,{method:"POST",body:JSON.stringify(body)});
    else if(kind==="changes")outcome=await api(`/api/submissions/${form.dataset.sid}/request-changes`,{method:"POST",body:JSON.stringify(body)});
    else if(kind==="reopen")outcome=await api(taskApi(task.id,"/reopen"),{method:"POST",body:JSON.stringify(body)});
    else if(kind==="hold")outcome=await api(taskApi(task.id,"/hold"),{method:"POST",body:JSON.stringify(body)});
    await load();await openDetail(task.id);
    if(outcome?.request){const current=document.querySelector("#lifecycle-error");current.style.color="#0c7c86";current.textContent="Owner request created; accepted live state is unchanged."}
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
    return `<li><strong>${escapeHtml(a.display_name)}</strong>${missing}<br>
      <code class="att-path">${escapeHtml(a.path)}</code>
      <button type="button" class="link" data-copy-path="${escapeHtml(a.path)}">Copy path</button>
      ${removeCtl}
      ${frCtl}
      <br><small>Added by ${escapeHtml(a.added_by_name||"")} · ${escapeHtml(new Date(a.added_at).toLocaleString())}</small>${note}</li>`;
  }).join("")||"<li>No attachments linked.</li>";
  const form=canManageFiles?`<form id="attachment-form">
      <label>File path<input name="path" placeholder="C:\\folder\\deliverable.pdf" required></label>
      <div class="grid"><label>Display name (optional)<input name="display_name"></label>
        <label>Note (optional)<input name="note"></label></div>
      <div class="actions"><button>Link file</button></div><div class="error" id="attachment-error"></div></form>`:`<p class="blocked-text">Read/download only. File and final-result management is App Owner-only.</p><div class="error" id="attachment-error"></div>`;
  return `<div class="attachments"><h3>Attachments</h3>
    <p>Links to files kept in a folder on this machine — Astra stores the link, not the file. Removing a link never deletes the file.</p>
    <ul>${rows}</ul>
    ${form}</div>`;
}

async function wireAttachments(task){
  document.querySelector("#attachment-form")?.addEventListener("submit",async e=>{
    e.preventDefault();const err=document.querySelector("#attachment-error");err.textContent="";
    try{await api(taskApi(task.id,"/attachments"),{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await openDetail(task.id)}
    catch(x){err.textContent=x.message}
  });
  document.querySelectorAll("#detail-body [data-remove-attachment]").forEach(b=>b.addEventListener("click",async()=>{
    try{await api("/api/task-attachments",{method:"DELETE",body:JSON.stringify({task_id:task.id,attachment_id:b.dataset.removeAttachment})});await openDetail(task.id)}
    catch(x){document.querySelector("#attachment-error").textContent=x.message}
  }));
  document.querySelectorAll("#detail-body [data-copy-path]").forEach(b=>b.addEventListener("click",async()=>{
    try{await navigator.clipboard.writeText(b.dataset.copyPath);b.textContent="Copied";setTimeout(()=>{b.textContent="Copy path"},1200)}
    catch{const err=document.querySelector("#attachment-error");if(err)err.textContent="Copy failed — select the path and copy manually."}
  }));
}

function wireReviewers(task){
  fillAssignees(task.project_id,document.querySelector("#reviewer-user"));
  document.querySelector("#add-reviewer-button")?.addEventListener("click",async()=>{
    const err=document.querySelector("#reviewer-error");err.textContent="";
    const user_id=document.querySelector("#reviewer-user").value,role=document.querySelector("#reviewer-role").value;
    try{await api("/api/task-reviewers",{method:"POST",body:JSON.stringify({task_id:task.id,user_id,role})});await openDetail(task.id)}
    catch(x){err.textContent=x.message}
  });
  document.querySelectorAll("#detail-body [data-remove-reviewer-user]").forEach(b=>b.addEventListener("click",async()=>{
    try{await api("/api/task-reviewers",{method:"DELETE",body:JSON.stringify({task_id:task.id,user_id:b.dataset.removeReviewerUser,role:b.dataset.removeReviewerRole})});await openDetail(task.id)}
    catch(x){document.querySelector("#reviewer-error").textContent=x.message}
  }));
}

function renderEvent(ev){
  const when=new Date(ev.occurred_at).toLocaleString();
  const who=ev.actor_name||"Unknown";
  const label=EVENT_LABELS[ev.event_type]||ev.event_type;
  let detail="";
  if(ev.event_type==="task_updated"){
    const before=safeParse(ev.before_json),after=safeParse(ev.after_json);
    const changes=DIFF_FIELDS.filter(([k])=>String(before[k]??"")!==String(after[k]??""))
      .map(([k,l])=>`${escapeHtml(l)}: ${escapeHtml(String(before[k]??"—"))} → ${escapeHtml(String(after[k]??"—"))}`);
    detail=changes.length?`<br>${changes.join("<br>")}`:"<br>No field changes.";
  }else if(ev.event_type==="dependency_added"){
    const a=safeParse(ev.after_json);detail=`<br>Predecessor: ${escapeHtml(a.predecessor_task_id||"")}`;
  }else if(ev.event_type==="dependency_removed"){
    const b=safeParse(ev.before_json);detail=`<br>Removed predecessor: ${escapeHtml(b.predecessor_task_id||"")}`;
  }
  const reason=ev.reason?`<br><em>Reason: ${escapeHtml(ev.reason)}</em>`:"";
  return `<li><strong>${escapeHtml(label)}</strong> · ${escapeHtml(when)} · ${escapeHtml(who)}${reason}${detail}</li>`;
}

function safeParse(text){try{return text?JSON.parse(text):{}}catch{return{}}}

async function submitDetailEdit(e,{statusLocked=false}={}){
  e.preventDefault();
  const form=e.target,error=document.querySelector("#detail-edit-error");error.textContent="";
  const body=Object.fromEntries(new FormData(form));
  if(statusLocked)delete body.status; // shown for context only; Accept or Request changes moves it
  body.expected_revision=Number(body.expected_revision);
  try{
    const outcome=await api(taskApi(detailTaskId),{method:"POST",body:JSON.stringify(body)});
    await dropLease(detailTaskId);
    await load();await openDetail(detailTaskId);
    if(outcome.request){const current=document.querySelector("#detail-edit-error");current.style.color="#0c7c86";current.textContent="Owner request created; accepted live state is unchanged."}
  }catch(err){if(err.status===409)return reloadTaskAfterConflict(detailTaskId,"detail-edit-error",err.message);error.textContent=err.message}
}

async function addDependency(){
  const select=document.querySelector("#add-dep-select"),error=document.querySelector("#dep-error");error.textContent="";
  const predecessor=select.value;
  if(!predecessor){error.textContent="Choose a predecessor task.";return}
  try{
    await api("/api/task-dependencies",{method:"POST",body:JSON.stringify({predecessor_task_id:predecessor,successor_task_id:detailTaskId})});
    await load();await openDetail(detailTaskId);
  }catch(err){error.textContent=err.message}
}

async function removeDependency(e){
  const button=e.target,error=document.querySelector("#dep-error");error.textContent="";
  const reason=button.parentElement.querySelector(".dep-reason").value;
  try{
    await api("/api/task-dependencies",{method:"DELETE",body:JSON.stringify({predecessor_task_id:button.dataset.removePred,successor_task_id:button.dataset.removeSucc,reason})});
    await load();await openDetail(detailTaskId);
  }catch(err){error.textContent=err.message}
}

async function openPeople(){
  try{
    const [u,m,h]=await Promise.all([api("/api/users"),api("/api/memberships"),api("/api/user-events")]);
    renderPeople(u.users,m.memberships,h.events);
    const d=document.querySelector("#people-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#people-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
}

// GTEYTG: every owner has role "owner"; only the primary owner may give or remove owner access.
const OWNER_EVENT_LABELS={secondary_owner_granted:"Made secondary owner",secondary_owner_revoked:"Owner access removed",owner_change_blocked:"Blocked owner change",import_blocked:"Blocked import without a project",primary_owner_transferred:"Primary owner transferred",password_reset:"Password reset"};
// PDDS2D/3M2AYA: a password reset is either a server command or done in the app by an owner.
const viaServerCommand=e=>(e.event_type==="primary_owner_transferred"||e.event_type==="password_reset")&&e.reason==="server command";
const MIN_PASSWORD=8;
function renderPeople(users,memberships,ownerEvents){
  const primary=!!state.user.is_primary_owner;
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
  const ownerEventRow=e=>`<li>${escapeHtml(new Date(e.occurred_at).toLocaleString())} · ${escapeHtml(ownerEventLabel(e))}${e.event_type==="import_blocked"?"":`: <strong>${escapeHtml(e.target_name)}</strong>`}${viaServerCommand(e)?" via server command":` by ${escapeHtml(e.actor_name)}`}${e.reason&&!viaServerCommand(e)?` · ${escapeHtml(e.reason)}`:""}</li>`;
  const blocked=e=>e.event_type==="owner_change_blocked"||e.event_type==="import_blocked";
  const ownerHistory=(ownerEvents||[]).filter(e=>!blocked(e)).slice(0,20).map(ownerEventRow).join("")||"<li>No owner access changes yet.</li>";
  const blockedList=type=>(ownerEvents||[]).filter(e=>e.event_type===type).slice(0,10).map(ownerEventRow).join("")||"<li>None.</li>";
  const blockedHistory=blockedList("owner_change_blocked"),blockedImports=blockedList("import_blocked");
  const resetOptions=users.filter(u=>canResetPassword(u,primary)).map(u=>`<option value="${escapeHtml(u.id)}" data-name="${escapeHtml(u.display_name)}">${escapeHtml(u.display_name)} · ${escapeHtml(u.email)}</option>`).join("");
  // Only the primary may change an owner's project access, so others are not offered it.
  const ownerIds=new Set(users.filter(u=>u.global_role==="owner").map(u=>u.id));
  const userOptions=users.filter(u=>u.active&&(primary||!ownerIds.has(u.id))).map(u=>`<option value="${escapeHtml(u.id)}">${escapeHtml(u.display_name)}</option>`).join("");
  const projectOptions=state.projects.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  const grants=memberships.map(m=>`<li>${escapeHtml(m.project_name)} · ${escapeHtml(m.user_name)} · ${escapeHtml(m.role)} ${!primary&&ownerIds.has(m.user_id)?"":`<button type="button" class="link" data-revoke-project="${escapeHtml(m.project_id)}" data-revoke-user="${escapeHtml(m.user_id)}">Revoke</button>`}</li>`).join("")||"<li>No access grants yet.</li>";
  const entityRows=(state.entities||[]).map(e=>`<li><strong>${escapeHtml(e.name)}</strong>${e.active?"":' · <em>inactive</em>'} <button type="button" class="link" data-entity-toggle="${escapeHtml(e.id)}" data-active="${e.active?1:0}">${e.active?"Deactivate":"Reactivate"}</button></li>`).join("")||"<li>No entities yet.</li>";
  const filingProjectOptions=state.projects.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  document.querySelector("#people-body").innerHTML=`
    <h2>People &amp; access</h2>
    <h3>Users</h3><ul class="people-list">${rows}</ul>
    <h3>Owner access history</h3><ul class="people-list">${ownerHistory}</ul>
    <h3>Blocked owner-access attempts</h3><ul class="people-list">${blockedHistory}</ul>
    <h3>Blocked imports without a project</h3><ul class="people-list">${blockedImports}</ul>
    <form id="add-user-form"><h3>Add a user</h3>
      <label>Email<input name="email" type="email" required></label>
      <label>Display name<input name="display_name" required></label>
      <label>Temporary password (min ${MIN_PASSWORD} characters)<input name="password" type="password" minlength="${MIN_PASSWORD}" autocomplete="new-password" required></label>
      <label>Role<select name="role"><option value="member">Member</option><option value="chairman">Chairman</option></select></label>
      <div class="actions"><button value="add">Create user</button></div><div class="error" id="add-user-error"></div></form>
    <form id="reset-password-form"><h3>Reset a password</h3>
      <p class="form-hint">For someone who has forgotten theirs. They are signed out everywhere else and sign in with the new password.</p>
      <label>User<select name="user_id" id="reset-password-user" required><option value="">Choose a user…</option>${resetOptions}</select></label>
      <div class="grid">
        <label>New password (min ${MIN_PASSWORD} characters)<input name="password" type="password" minlength="${MIN_PASSWORD}" autocomplete="new-password" required></label>
        <label>Confirm new password<input name="confirm" type="password" minlength="${MIN_PASSWORD}" autocomplete="new-password" required></label>
      </div>
      <div class="actions"><button value="reset">Reset password</button></div><div class="error" id="reset-password-error" role="status"></div></form>
    <form id="grant-form"><h3>Grant project access</h3>
      <div class="grid">
        <label>User<select name="user_id" required>${userOptions}</select></label>
        <label>Project<select name="project_id" required>${projectOptions}</select></label>
        <label>Role<select name="role"><option value="manager">Manager</option><option value="member">Member</option><option value="viewer">Viewer</option></select></label>
      </div>
      <div class="actions"><button value="grant">Grant access</button></div><div class="error" id="grant-error"></div></form>
    <h3>Current access</h3><ul class="people-list">${grants}</ul>
    <h3>Entities</h3><ul class="people-list">${entityRows}</ul>
    <form id="add-entity-form">
      <label>New entity name<input name="name" required></label>
      <div class="actions"><button value="add">Add entity</button><button type="button" id="seed-entities" class="quiet">Seed approved entities</button></div>
      <div class="error" id="entity-error"></div></form>
    <form id="filing-form"><h3>Project filing (entities)</h3>
      <label>Project<select id="filing-project"><option value="">Choose a project…</option>${filingProjectOptions}</select></label>
      <div id="filing-entities" class="filing-entities"></div>
      <div class="actions"><button value="save">Save filing</button></div>
      <div class="error" id="filing-error"></div></form>
    <form id="calendar-form"><h3>Project calendar (working days &amp; holidays)</h3>
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
  document.querySelector("#seed-entities").addEventListener("click",seedEntities);
  document.querySelectorAll("#people-body [data-entity-toggle]").forEach(b=>b.addEventListener("click",toggleEntityActive));
  document.querySelector("#filing-project").addEventListener("change",e=>renderFilingEntities(e.target.value));
  document.querySelector("#filing-form").addEventListener("submit",submitFiling);
  document.querySelector("#calendar-project").addEventListener("change",e=>renderCalendar(e.target.value));
  document.querySelector("#calendar-form").addEventListener("submit",e=>e.preventDefault());
}

async function renderCalendar(projectId){
  const body=document.querySelector("#calendar-body"),err=document.querySelector("#calendar-error");err.textContent="";
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
        <label>Project target date<input id="project-target" type="date" value="${escapeHtml(project.target_date||"")}"></label>
      </div>
      <label>Reason for date change<input id="project-schedule-reason" placeholder="Required to change project dates"></label>
      <div class="actions"><button type="button" id="save-schedule">Save project dates</button></div>
      <p class="fine">Informational only — project dates are logged on every change but never block task dates.</p>
      <div class="error" id="schedule-error"></div>
    </div>`;
  document.querySelector("#save-budget").addEventListener("click",()=>saveBudget(projectId));
  document.querySelector("#save-schedule").addEventListener("click",()=>saveProjectSchedule(projectId));
}
async function saveProjectSchedule(projectId){
  const err=document.querySelector("#schedule-error");err.textContent="";err.style.color="";
  const start_date=document.querySelector("#project-start").value||null,target_date=document.querySelector("#project-target").value||null,reason=document.querySelector("#project-schedule-reason").value;
  try{
    await api(`/api/projects/${projectId}/schedule`,{method:"POST",body:JSON.stringify({start_date,target_date,reason})});
    await load();err.style.color="#0c7c86";err.textContent="Saved and logged.";
  }catch(x){err.textContent=x.message}
}
async function saveBudget(projectId){
  const err=document.querySelector("#budget-error");err.textContent="";err.style.color="";
  const amount=document.querySelector("#budget-amount").value,currency=document.querySelector("#budget-currency").value,primary=document.querySelector("#primary-entity").value;
  try{
    await api(`/api/projects/${projectId}/budget`,{method:"POST",body:JSON.stringify({amount:amount===""?null:Number(amount),currency})});
    await api(`/api/projects/${projectId}/primary-entity`,{method:"POST",body:JSON.stringify({entity_id:primary})});
    await load();err.style.color="#0c7c86";err.textContent="Saved.";
  }catch(x){err.textContent=x.message}
}

async function submitAddEntity(e){
  e.preventDefault();const err=document.querySelector("#entity-error");err.textContent="";
  try{await api("/api/entities",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await load();await openPeople()}
  catch(x){err.textContent=x.message}
}
async function seedEntities(){
  const err=document.querySelector("#entity-error");err.textContent="";
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
  e.preventDefault();const err=document.querySelector("#filing-error");err.textContent="";
  const pid=document.querySelector("#filing-project").value;
  if(!pid){err.textContent="Choose a project.";return}
  const entity_ids=[...document.querySelectorAll("#filing-entities input:checked")].map(i=>i.value);
  try{await api(`/api/projects/${pid}/entities`,{method:"POST",body:JSON.stringify({entity_ids})});await load();await openPeople();
    document.querySelector("#filing-error").textContent="Filing saved.";}
  catch(x){err.textContent=x.message}
}

async function submitAddUser(e){
  e.preventDefault();const err=document.querySelector("#add-user-error");err.textContent="";
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
    await api(`/api/users/${data.user_id}/password`,{method:"POST",body:JSON.stringify({password:data.password})});
    await openPeople();  // re-render, so the owner-access history shows the reset
    const done=document.querySelector("#reset-password-error");done.classList.add("is-info");
    done.textContent=own?"Your password has been changed. Your other sessions were signed out."
      :`Password reset for ${name}. Give them the new password; they are signed out everywhere else.`;
    document.querySelector("#reset-password-form").scrollIntoView({block:"nearest"});
  }catch(x){out.textContent=x.message}
}
async function submitGrant(e){
  e.preventDefault();const err=document.querySelector("#grant-error");err.textContent="";
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
  try{const {targets}=await api("/api/import/targets");importState.targets=targets;button.hidden=!(targets.projects.length||targets.can_create_project)}
  catch{importState.targets=null;button.hidden=true}
}
document.querySelector("#import-btn").onclick=openImport;
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
  const selected=document.querySelector("#project-filter").value;
  document.querySelector("#import-body").innerHTML=`
    <h3>Upload a filled template</h3>
    <p class="muted">Choose the target project, download the template and fill its <strong>Project</strong> and <strong>Tasks</strong> sheets (dates as dd-mm-yyyy; the Example sheet shows worked rows), then upload it here. With a project chosen the download already lists that project's tasks with their Import Keys, so a re-upload updates them instead of duplicating; add new rows at the bottom. Nothing is written until you confirm in step 3. An import never deletes.</p>
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
    for(const [id,ext] of [["import-template-xlsx","xlsx"],["import-template-csv","csv"]]){const a=document.querySelector(`#${id}`);a.href=`/api/import/template.${ext}${suffix}`;a.textContent=`${label} (.${ext})`}
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
    readBack();const err=document.querySelector("#tpl-error");err.textContent="";
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
(async()=>{let data;try{data=await api("/api/me")}catch{showLogin();return}Object.assign(state,data);showApp();await loadOrSay()})();
