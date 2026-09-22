const state={user:null,csrf:null,projects:[],tasks:[],entities:[],unread:0,sort:"criticality"};
async function api(path,options={}){options.headers={"Content-Type":"application/json",...(state.csrf?{"X-CSRF-Token":state.csrf}:{}),...(options.headers||{})};const response=await fetch(path,options);const data=await response.json();if(!response.ok)throw new Error(data.error||"Request failed");return data}
function showLogin(){document.querySelector("#login").hidden=false;document.querySelector("#app").hidden=true}
function showApp(){document.querySelector("#login").hidden=true;document.querySelector("#app").hidden=false;document.querySelector("#user-name").textContent=`${state.user.display_name} · ${state.user.global_role}`;const isOwner=state.user.global_role==="owner";document.querySelector("#new-project").hidden=!isOwner;document.querySelector("#people").hidden=!isOwner;document.querySelector("#close-project").hidden=!isOwner;document.querySelector("#save-template-btn").hidden=!isOwner;refreshImportAccess()}
async function load(){const [p,t,e,n]=await Promise.all([api("/api/projects"),api(`/api/tasks?sort=${encodeURIComponent(state.sort)}`),api("/api/entities").catch(()=>({entities:[]})),api("/api/notifications").catch(()=>({notifications:[],unread:0}))]);state.projects=p.projects;state.tasks=t.tasks;state.entities=e.entities;state.notifications=n.notifications;state.unread=n.unread;updateBell();fillFilters();render()}
function updateBell(){document.querySelector("#unread-count").textContent=state.unread||0;document.querySelector("#inbox").classList.toggle("has-unread",(state.unread||0)>0)}
function fillFilters(){const pf=document.querySelector("#project-filter"),tp=document.querySelector('#task-form select[name="project_id"]');const selected=pf.value;pf.innerHTML='<option value="">All projects</option>';tp.innerHTML="";for(const p of state.projects){pf.add(new Option(p.status==="closed"?`${p.name} (closed)`:p.name,p.id));if(p.status!=="closed")tp.add(new Option(p.name,p.id))}pf.value=selected;const statuses=[...new Set(state.tasks.map(t=>t.status))].sort();document.querySelector("#status-filter").innerHTML='<option value="">All statuses</option>'+statuses.map(s=>`<option>${escapeHtml(s)}</option>`).join("");const ef=document.querySelector("#entity-filter"),efSel=ef.value;ef.innerHTML='<option value="">All entities</option>'+(state.entities||[]).map(e=>`<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)}</option>`).join("");ef.value=efSel;fillPredecessors()}
function projectEntityIds(projectId){const p=state.projects.find(p=>p.id===projectId);return new Set((p&&p.entities?p.entities:[]).map(e=>e.id))}
function fillPredecessors(){const project=document.querySelector('#task-form select[name="project_id"]').value,select=document.querySelector('#task-form select[name="predecessor_task_id"]'),parent=document.querySelector('#task-form select[name="parent_task_id"]');select.innerHTML='<option value="">No predecessor</option>';parent.innerHTML='<option value="">No parent</option>';for(const task of state.tasks.filter(t=>t.project_id===project)){select.add(new Option(task.title,task.id));parent.add(new Option(task.title,task.id))}}
function render(){
  const project=document.querySelector("#project-filter").value,status=document.querySelector("#status-filter").value,
    entity=document.querySelector("#entity-filter").value,crit=document.querySelector("#crit-filter").value,
    band=document.querySelector("#band-filter").value,owner=document.querySelector("#owner-filter").value.toLowerCase(),
    openOnly=document.querySelector("#open-only").checked;
  const tasks=state.tasks.filter(t=>
    (!project||t.project_id===project)&&
    (!status||t.status===status)&&
    (!entity||projectEntityIds(t.project_id).has(entity))&&
    (!crit||(crit==="unrated"?!t.criticality:t.criticality===crit))&&
    (!band||matchesBand(t,band))&&
    (!owner||(t.owner_name||"").toLowerCase().includes(owner))&&
    (!openOnly||!["completed","cancelled","abandoned"].includes(t.status)));
  document.querySelector("#project-count").textContent=state.projects.length;
  document.querySelector("#task-count").textContent=tasks.length;
  document.querySelector("#overdue-count").textContent=tasks.filter(t=>t.due_state==="overdue").length;
  document.querySelector("#attention-count").textContent=tasks.filter(t=>t.due_state==="undated").length;
  document.querySelector("#as-of").textContent=`As of ${new Date().toLocaleString()} (${Intl.DateTimeFormat().resolvedOptions().timeZone})`;
  renderBands(tasks);
  renderGantt(tasks);
}
function matchesBand(t,band){
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
function renderGantt(tasks){
  const el=document.querySelector("#gantt");
  if(!tasks.length){el.innerHTML='<div class="empty">No tasks match these filters. Undated or unassigned work will appear here rather than being hidden.</div>';return}
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
  const span=Math.max(1,max-min);
  const pct=d=>(d-min)/span*100;
  const inRange=x=>x>=0&&x<=100;
  const markerFlags=projMarkers.map(m=>{const x=pct(m.date);return inRange(x)?`<span class="proj-flag ${m.kind}" style="left:${x}%">${escapeHtml(m.label)}</span>`:""}).join("");
  const markerLines=projMarkers.map(m=>{const x=pct(m.date);return inRange(x)?`<span class="proj-line ${m.kind}" style="left:${x}%"></span>`:""}).join("");
  // weekly calendar ticks
  const ticks=[];const t0=new Date(min);t0.setHours(0,0,0,0);
  for(let t=t0.getTime();t<=max.getTime();t+=7*86400000)ticks.push(new Date(t));
  const now=new Date();now.setHours(0,0,0,0);
  const todayPct=pct(now);const showToday=todayPct>=0&&todayPct<=100;
  const axis=ticks.map(d=>`<span class="axis-tick" style="left:${pct(d)}%"><b>${d.getDate()}</b> ${escapeHtml(d.toLocaleDateString(undefined,{month:"short"}))}</span>`).join("");
  const todayFlag=showToday?`<span class="today-flag" style="left:${todayPct}%">Today</span>`:"";
  const header=`<div class="gantt-row gantt-head"><div class="task-name gantt-head-cap">Project / task</div><div class="task-meta gantt-head-cap">Owner · due · next action</div><div class="timeline axis">${axis}${markerLines}${markerFlags}${todayFlag}</div></div>`;
  const rows=tasks.map(t=>{
    let bar;
    if(!t.start_date&&!t.due_date){bar=`<span class="bar undated">Date required</span>`}
    else{
      const start=new Date(t.start_date||t.due_date),end=new Date(t.due_date||t.start_date);
      const left=Math.max(0,pct(start)),width=Math.max(.8,(end-start+86400000)/span*100);
      const cls=t.is_critical_path?"critical":(t.is_blocked?"blocked":t.due_state);
      bar=`<span class="bar ${cls}" style="left:${left}%;width:${width}%">${escapeHtml(t.title)}</span>`;
    }
    const todayLine=showToday?`<span class="today-line" style="left:${todayPct}%"></span>`:"";
    const blocked=t.is_blocked?`<br><span class="blocked-text">Blocked by ${escapeHtml(t.blocked_by.map(item=>item.title).join(", "))}</span>`:"";
    const cp=t.is_critical_path?`<br><span class="cp-text">On critical path</span>`:"";
    return `<div class="gantt-row"><div class="task-name">${escapeHtml(t.project_name)}<br><small>${escapeHtml(t.title)}</small><br><button type="button" class="link" data-detail="${escapeHtml(t.id)}">Details &amp; history</button></div><div class="task-meta">${escapeHtml(t.owner_name||"Unassigned")}<br>${escapeHtml(t.due_date||"No due date")} · ${escapeHtml(t.criticality||"Unrated")}${blocked}${cp}<br><span class="next-action">Next: ${escapeHtml(t.next_action||"—")}</span></div><div class="timeline">${markerLines}${todayLine}${bar}</div></div>`;
  }).join("");
  el.innerHTML=header+rows;
}
function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
document.querySelector("#login-form").addEventListener("submit",async e=>{e.preventDefault();try{const data=await api("/api/login",{method:"POST",body:JSON.stringify({email:e.target.querySelector("#email").value,password:e.target.querySelector("#password").value})});Object.assign(state,data);showApp();await load()}catch(err){document.querySelector("#login-error").textContent=err.message}});
document.querySelector("#logout").onclick=async()=>{await api("/api/logout",{method:"POST",body:"{}"});state.user=state.csrf=null;showLogin()};
document.querySelector("#logout-all").onclick=async()=>{await api("/api/logout-all",{method:"POST",body:"{}"});state.user=state.csrf=null;showLogin()};
document.querySelector("#close-project").onclick=async()=>{
  const pid=document.querySelector("#project-filter").value;
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
};
for(const id of ["project-filter","status-filter","entity-filter","crit-filter","band-filter"]){document.querySelector(`#${id}`).onchange=render}document.querySelector("#open-only").onchange=render;document.querySelector("#owner-filter").oninput=render;
// QY0WG2: changing the sort re-fetches the list in the chosen server-side order.
document.querySelector("#sort-filter").onchange=e=>{state.sort=e.target.value;load()};
document.querySelector("#new-project").onclick=()=>document.querySelector("#project-dialog").showModal();document.querySelector("#new-task").onclick=()=>document.querySelector("#task-dialog").showModal();
document.querySelector("#portfolio-btn").onclick=openPortfolio;
async function openPortfolio(){
  try{
    const {portfolio}=await api("/api/portfolio");
    const cards=portfolio.map(b=>{
      const budgets=Object.entries(b.budgets||{}).map(([c,a])=>`${escapeHtml(c)} ${Number(a).toLocaleString()}`).join(" · ")||"—";
      return `<div class="pf-card"><h3>${escapeHtml(b.entity_name)}</h3>
        <div class="facts">${fact("Projects",String(b.project_count))}${fact("Open",String(b.open))}${fact("Overdue",String(b.overdue))}${fact("Critical",String(b.critical))}</div>
        <div class="pf-budget">Budget roll-up: <strong>${budgets}</strong></div></div>`;
    }).join("")||"<p>No projects yet.</p>";
    document.querySelector("#portfolio-body").innerHTML=`<h2>Portfolio by entity</h2><p style="color:#667085;font-size:12px;">Each project is counted once, under its primary entity. Budgets shown per currency (never blended).</p>${cards}`;
    const d=document.querySelector("#portfolio-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#portfolio-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#portfolio-dialog").showModal()}
}
document.querySelector("#templates-btn").onclick=openTemplates;
document.querySelector("#save-template-btn").onclick=saveProjectAsTemplate;
async function openTemplates(){
  try{
    const {templates}=await api("/api/templates");
    renderTemplates(templates);
    const d=document.querySelector("#templates-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#templates-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#templates-dialog").showModal()}
}
function renderTemplates(templates){
  const rows=(templates||[]).map(t=>`<li><strong>${escapeHtml(t.name)}</strong> · <span style="color:#667085">${escapeHtml(t.kind)} · ${t.task_count} task(s)</span>
    ${t.description?`<br><em style="color:#667085">${escapeHtml(t.description)}</em>`:""}
    <br><button type="button" class="link" data-use-template="${escapeHtml(t.id)}" data-kind="${escapeHtml(t.kind)}">Use</button>
    <button type="button" class="link" data-delete-template="${escapeHtml(t.id)}">Delete</button></li>`).join("")||"<li>No templates yet. Save a project or a task as a template to reuse it.</li>";
  document.querySelector("#templates-body").innerHTML=`<h2>Templates</h2>
    <p style="color:#667085;font-size:12px;">A template copies structure — titles, hierarchy, dependencies, criticality, attachment links, relative dates and a suggested owner. Never status, history or evidence. New tasks start in draft; each suggested owner is pre-filled if they are still an assignable member, otherwise left unassigned.</p>
    <ul class="people-list">${rows}</ul><div class="error" id="templates-error"></div>`;
  document.querySelectorAll("#templates-body [data-use-template]").forEach(b=>b.addEventListener("click",()=>useTemplate(b.dataset.useTemplate,b.dataset.kind)));
  document.querySelectorAll("#templates-body [data-delete-template]").forEach(b=>b.addEventListener("click",()=>deleteTemplate(b.dataset.deleteTemplate)));
}
async function saveProjectAsTemplate(){
  const pid=document.querySelector("#project-filter").value;
  if(!pid){alert("Pick a single project in the Project filter first, then save it as a template.");return}
  const name=prompt("Template name:");if(!name)return;
  const description=prompt("Template description (optional):")||"";
  try{await api("/api/templates/from-project",{method:"POST",body:JSON.stringify({project_id:pid,name,description})});alert("Saved as a template.");await openTemplates()}
  catch(x){alert(x.message)}
}
async function useTemplate(id,kind){
  try{
    if(kind==="project"){
      const name=prompt("New project name:");if(!name)return;
      const anchor_date=prompt("Anchor date for relative schedule (YYYY-MM-DD, blank to leave dates unset):")||null;
      await api(`/api/templates/${id}/create-project`,{method:"POST",body:JSON.stringify({name,anchor_date})});
      alert("Project created from template.");document.querySelector("#templates-dialog").close();await load();
    }else{
      const project_id=prompt("Target project id to add this task subtree to:\n(Tip: open the project, a task's detail shows its project.)");if(!project_id)return;
      const parent_task_id=prompt("Parent task id (optional, blank for top-level):")||null;
      const anchor_date=prompt("Anchor date for relative schedule (YYYY-MM-DD, blank to leave dates unset):")||null;
      await api(`/api/templates/${id}/create-task`,{method:"POST",body:JSON.stringify({project_id,parent_task_id,anchor_date})});
      alert("Task subtree created from template.");document.querySelector("#templates-dialog").close();await load();
    }
  }catch(x){const e=document.querySelector("#templates-error");if(e)e.textContent=x.message;else alert(x.message)}
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
    return `<tr><td><strong>${escapeHtml(r.title)}</strong><br><small style="color:#667085">${where}</small></td>
      <td>${escapeHtml(r.source_type)}</td>
      <td><button type="button" class="link" data-detail="${escapeHtml(r.task_id)}">${escapeHtml(r.task_title)}</button><br><small style="color:#667085">${escapeHtml(r.project_name)} · ${escapeHtml(ents)}</small></td>
      <td><small>${escapeHtml(new Date(r.marked_at).toLocaleDateString())}</small></td></tr>`;
  }).join("")||`<tr><td colspan="4">No final results yet. Mark an accepted submission or an attachment as a final result.</td></tr>`;
  document.querySelector("#final-results-body").innerHTML=`<h2>Final results</h2>
    <p style="color:#667085;font-size:12px;">Curated deliverables across your projects. Every final result is marked by hand — an accepted submission or an attachment. Acceptance alone does not add one.</p>
    <div class="add-dep" id="fr-filters">
      <select id="fr-project"><option value="">All projects</option>${projOpts}</select>
      <select id="fr-entity"><option value="">All entities</option>${entOpts}</select>
      <select id="fr-type"><option value="">All types</option><option value="submission"${filters.type==="submission"?" selected":""}>Submissions</option><option value="attachment"${filters.type==="attachment"?" selected":""}>Attachments</option></select>
      <input id="fr-q" placeholder="Search title" value="${escapeHtml(filters.q||"")}">
      <button type="button" id="fr-apply">Filter</button>
      <button type="button" id="fr-export" class="quiet">Export CSV</button>
    </div>
    <table class="fr-table"><thead><tr><th>Result</th><th>Type</th><th>Task / project</th><th>Marked</th></tr></thead><tbody>${rows}</tbody></table>`;
  const collect=()=>({project_id:document.querySelector("#fr-project").value,entity_id:document.querySelector("#fr-entity").value,type:document.querySelector("#fr-type").value,q:document.querySelector("#fr-q").value});
  document.querySelector("#fr-apply").onclick=()=>openFinalResults(collect());
  document.querySelector("#fr-export").onclick=()=>{const f=collect();const p=new URLSearchParams();for(const k in f){if(f[k])p.set(k,f[k])}p.set("format","csv");const a=document.createElement("a");a.href="/api/final-results?"+p.toString();a.download="astra-final-results.csv";document.body.appendChild(a);a.click();a.remove()};
  document.querySelectorAll("#final-results-body [data-detail]").forEach(b=>b.addEventListener("click",()=>{document.querySelector("#final-results-dialog").close();openDetail(b.dataset.detail)}));
}
document.querySelector("#export-btn").onclick=()=>{
  const p=new URLSearchParams();
  const map={project_id:"#project-filter",status:"#status-filter",entity_id:"#entity-filter",criticality:"#crit-filter",band:"#band-filter",owner:"#owner-filter",sort:"#sort-filter"};
  for(const k in map){const v=document.querySelector(map[k]).value;if(v)p.set(k,v)}
  if(document.querySelector("#open-only").checked)p.set("open_only","1");
  p.set("format","csv");
  const a=document.createElement("a");a.href="/api/export?"+p.toString();a.download="astra-export.csv";document.body.appendChild(a);a.click();a.remove();
};
document.querySelector("#search-box").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();openSearch(e.target.value)}});
async function openSearch(q){
  if(!q.trim())return;
  try{
    const {results}=await api(`/api/search?q=${encodeURIComponent(q)}`);
    const tasks=(results.tasks||[]).map(t=>`<li><button type="button" class="link" data-detail="${escapeHtml(t.id)}">${escapeHtml(t.title)}</button> · ${escapeHtml(t.status)} · <span style="color:#667085">${escapeHtml(t.project_name)}</span></li>`).join("")||"<li>No matching tasks.</li>";
    const projects=(results.projects||[]).map(p=>`<li>${escapeHtml(p.name)}</li>`).join("")||"<li>No matching projects.</li>";
    document.querySelector("#search-body").innerHTML=`<h2>Search: ${escapeHtml(q)}</h2><h3>Tasks</h3><ul class="people-list">${tasks}</ul><h3>Projects</h3><ul class="people-list">${projects}</ul>`;
    document.querySelectorAll("#search-body [data-detail]").forEach(b=>b.addEventListener("click",()=>{document.querySelector("#search-dialog").close();openDetail(b.dataset.detail)}));
    const d=document.querySelector("#search-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#search-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`;document.querySelector("#search-dialog").showModal()}
}
document.querySelector('#task-form select[name="project_id"]').onchange=e=>{fillPredecessors();fillAssignees(e.target.value,document.querySelector('#task-form select[name="owner_user_id"]'))};
document.querySelector("#people").onclick=openPeople;
document.querySelector("#inbox").onclick=openInbox;
async function openInbox(){
  try{
    const [data,ownerQueue]=await Promise.all([
      api("/api/notifications"),
      state.user.global_role==="owner"?api("/api/owner-action-requests"):Promise.resolve({requests:[]}),
    ]);
    state.notifications=data.notifications;state.unread=data.unread;updateBell();
    renderInbox(data.notifications,ownerQueue.requests);
    const d=document.querySelector("#inbox-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#inbox-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
}
function renderInbox(items,requests=[]){
  const rows=items.map(n=>{
    const when=new Date(n.created_at).toLocaleString();
    const unread=!n.read_at;
    const mark=unread?`<button type="button" class="link" data-read="${escapeHtml(n.id)}">Mark read</button>`:"read";
    return `<li class="${unread?"unread":""}"><strong>${escapeHtml(n.summary)}</strong><br><small>${escapeHtml(when)}</small> · ${mark}</li>`;
  }).join("")||"<li>No notifications.</li>";
  const requestRows=requests.map(r=>`<li class="unread"><strong>${escapeHtml(r.action.replaceAll("_"," "))}</strong><br><small>${escapeHtml(r.requested_by_name)} · ${escapeHtml(r.task_title||r.project_name)} · ${escapeHtml(new Date(r.requested_at).toLocaleString())}</small></li>`).join("")||"<li>No pending Owner requests.</li>";
  document.querySelector("#inbox-body").innerHTML=`<h2>Needs action</h2><ul class="people-list">${requestRows}</ul><h2>Activity</h2>
    <div class="actions"><button type="button" id="read-all" class="quiet">Mark all read</button></div>
    <ul class="people-list">${rows}</ul>`;
  document.querySelector("#read-all").addEventListener("click",markAllRead);
  document.querySelectorAll("#inbox-body [data-read]").forEach(b=>b.addEventListener("click",()=>markRead(b.dataset.read)));
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
document.querySelector("#task-form").addEventListener("submit",async e=>{e.preventDefault();const button=e.submitter;if(button?.value==="cancel"){e.target.closest("dialog").close();return}try{await api("/api/tasks",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});e.target.reset();e.target.closest("dialog").close();await load()}catch(err){e.target.querySelector(".error").textContent=err.message}});
const STATUSES=["draft","assigned","in_progress","submitted","changes_requested","completed","on_hold","delayed","cancelled","abandoned","reopened"];
const CRITICALITIES=[["","Unrated"],["critical","Critical"],["high","High"],["normal","Normal"],["low","Low"]];
const GOVERNED=["submitted","completed","on_hold","reopened"];
const EVENT_LABELS={import_committed:"Import committed",task_created:"Task created",task_updated:"Task updated",dependency_added:"Dependency added",dependency_removed:"Dependency removed",task_submitted:"Work submitted",submission_accepted:"Submission accepted",changes_requested:"Changes requested",task_reopened:"Task reopened",task_on_hold:"Put on hold",criticality_changed:"Criticality changed",parent_changed:"Parent changed",schedule_proposed:"Schedule change proposed",schedule_revised:"Schedule revised",schedule_proposal_rejected:"Schedule proposal rejected",attachment_added:"Attachment linked",attachment_removed:"Attachment link removed"};
const DIFF_FIELDS=[["title","Title"],["status","Status"],["criticality","Criticality"],["start_date","Start date"],["due_date","Due date"],["progress","Progress"],["description","Description"]];
let detailTaskId=null;

document.querySelector("#gantt").addEventListener("click",e=>{const b=e.target.closest("[data-detail]");if(b)openDetail(b.dataset.detail)});

async function openDetail(taskId){
  detailTaskId=taskId;
  try{
    const [d,ev]=await Promise.all([api(`/api/tasks/${taskId}`),api(`/api/tasks/${taskId}/events`)]);
    renderDetail(d.task,ev.events);
    const dialog=document.querySelector("#detail-dialog");
    if(!dialog.open)dialog.showModal();
  }catch(err){document.querySelector("#detail-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
}

function fact(label,value){return `<div class="fact"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`}

function renderDetail(task,events){
  const editable=STATUSES.filter(s=>!GOVERNED.includes(s));
  if(!editable.includes(task.status))editable.unshift(task.status);
  const opts=editable.map(s=>`<option${s===task.status?" selected":""}>${escapeHtml(s)}</option>`).join("");
  const crit=CRITICALITIES.map(([v,l])=>`<option value="${v}"${v===(task.criticality||"")?" selected":""}>${escapeHtml(l)}</option>`).join("");
  const facts=[
    fact("Project",task.project_name),
    fact("Owner",task.owner_name||"Unassigned"),
    fact("Parent",task.parent_title||"None"),
    fact("Revision",String(task.revision)),
    fact("Due state",task.due_state),
  ].join("");
  const deps=(task.dependencies||[]).map(dep=>{
    const other=dep.direction==="incoming"?dep.predecessor_title:dep.successor_title;
    const flag=dep.blocking?' <span class="blocked-text">(blocking)</span>':"";
    return `<li>${dep.direction==="incoming"?"Depends on":"Blocks"}: <strong>${escapeHtml(other)}</strong>${flag}
      <span class="dep-remove"><input class="dep-reason" placeholder="Reason to remove" aria-label="Reason to remove dependency">
      <button type="button" class="link" data-remove-pred="${escapeHtml(dep.predecessor_task_id)}" data-remove-succ="${escapeHtml(dep.successor_task_id)}">Remove</button></span></li>`;
  }).join("")||"<li>No dependencies.</li>";
  const candidates=state.tasks.filter(t=>t.project_id===task.project_id&&t.id!==task.id);
  const addOptions=candidates.map(t=>`<option value="${escapeHtml(t.id)}">${escapeHtml(t.title)}</option>`).join("");
  const timeline=events.slice().reverse().map(renderEvent).join("")||"<li>No history.</li>";
  const lifecycle=buildLifecycle(task);
  const reviewers=buildReviewers(task);
  const attachments=buildAttachments(task);
  const subtasks=buildSubtasks(task);
  const schedule=buildSchedule(task);
  const critForm=`<div class="crit-confirm"><h3>Criticality</h3>
    <p>Current: <strong>${escapeHtml(task.criticality||"Unrated")}</strong> — changes are confirmed with a reason and recorded.</p>
    <form id="crit-form"><label>Set level<select name="criticality">${crit}</select></label>
      <label>Reason (evidence for this level)<input name="reason" required></label>
      <div class="actions"><button>Confirm criticality</button></div><div class="error" id="crit-error"></div></form></div>`;
  document.querySelector("#detail-body").innerHTML=`
    <h2>${escapeHtml(task.title)}</h2>
    <div class="facts">${facts}</div>
    <p class="desc">${escapeHtml(task.description||"No description.")}</p>
    ${buildImportedFields(task)}
    <p><button type="button" class="link" id="save-task-template">Save this task (and its subtasks) as a template</button></p>
    ${critForm}
    ${schedule}
    ${subtasks}
    ${lifecycle}
    ${reviewers}
    ${attachments}
    <form id="detail-edit">
      <h3>Edit</h3>
      <label>Title<input name="title" value="${escapeHtml(task.title)}" required></label>
      <label>Owner<select name="owner_user_id"><option value="">Unassigned</option></select></label>
      <div class="grid">
        <label>Status<select name="status">${opts}</select></label>
        <label>Start date<input name="start_date" type="date" value="${escapeHtml(task.start_date||"")}"></label>
        <label>Due date<input name="due_date" type="date" value="${escapeHtml(task.due_date||"")}"></label>
        <label>Progress<input name="progress" type="number" min="0" max="100" value="${task.progress==null?"":task.progress}"></label>
      </div>
      <label>Description<textarea name="description">${escapeHtml(task.description||"")}</textarea></label>
      <label>Reason (required for status or schedule changes)<input name="reason"></label>
      <div class="actions"><button value="save">Save changes</button></div>
      <div class="error" id="detail-edit-error"></div>
    </form>
    <div class="deps">
      <h3>Dependencies</h3>
      <ul>${deps}</ul>
      <div class="add-dep">
        <select id="add-dep-select"><option value="">Add a predecessor…</option>${addOptions}</select>
        <button type="button" id="add-dep-button">Add predecessor</button>
        <div class="error" id="add-dep-error"></div>
      </div>
    </div>
    <div class="history"><h3>History</h3><ul>${timeline}</ul></div>`;
  document.querySelector("#detail-edit").addEventListener("submit",submitDetailEdit);
  document.querySelector("#add-dep-button").addEventListener("click",addDependency);
  document.querySelector("#detail-body").querySelectorAll("[data-remove-pred]").forEach(b=>b.addEventListener("click",removeDependency));
  fillAssignees(task.project_id,document.querySelector('#detail-edit select[name="owner_user_id"]'),task.owner_user_id);
  wireLifecycle(task);
  wireReviewers(task);
  wireAttachments(task);
  document.querySelector("#save-task-template").addEventListener("click",()=>saveTaskAsTemplate(task.id));
  document.querySelectorAll("#detail-body [data-mark-fr-sub]").forEach(b=>b.addEventListener("click",()=>markFinalResult(task.id,"submission",b.dataset.markFrSub)));
  document.querySelectorAll("#detail-body [data-mark-fr-att]").forEach(b=>b.addEventListener("click",()=>markFinalResult(task.id,"attachment",b.dataset.markFrAtt)));
  document.querySelectorAll("#detail-body [data-unmark-fr]").forEach(b=>b.addEventListener("click",()=>unmarkFinalResult(task.id,b.dataset.unmarkFr)));
  document.querySelector("#crit-form").addEventListener("submit",submitCriticality);
  document.querySelector("#parent-form").addEventListener("submit",submitParent);
  document.querySelectorAll(".subtasks [data-detail]").forEach(b=>b.addEventListener("click",()=>openDetail(b.dataset.detail)));
  document.querySelector("#sched-form").addEventListener("submit",submitSchedule);
  document.querySelectorAll("#detail-body [data-approve-sched]").forEach(b=>b.addEventListener("click",()=>decideSchedule(b.dataset.approveSched,"approve")));
  document.querySelectorAll("#detail-body [data-reject-sched]").forEach(b=>b.addEventListener("click",()=>decideSchedule(b.dataset.rejectSched,"reject",b)));
}

function buildSchedule(task){
  const b=task.baseline||{};
  const props=task.schedule_proposals||[];
  const pending=props.filter(p=>p.status==="pending");
  const history=props.filter(p=>p.status!=="pending");
  const canDecide=task.permissions?.can_decide_protected,canRequest=task.permissions?.can_request_protected;
  const pendingRows=pending.map(p=>{const controls=canDecide||canRequest
    ?`<span class="dep-remove"><button type="button" class="link" data-approve-sched="${escapeHtml(p.id)}">${canDecide?"Approve":"Request Owner approval"}</button>
      <input class="sched-reject-reason" placeholder="Reason to reject" aria-label="Reason to reject">
      <button type="button" class="link" data-reject-sched="${escapeHtml(p.id)}">${canDecide?"Reject":"Request Owner rejection"}</button></span>`
    :`<span class="blocked-text">Owner decision required</span>`;
    return `<li>Proposed <strong>${escapeHtml(p.start_date||"—")} → ${escapeHtml(p.due_date||"—")}</strong> by ${escapeHtml(p.proposed_by_name||"")} <em style="color:#667085;">(${escapeHtml(p.reason)})</em>${controls}</li>`}).join("")||"<li>No pending proposals.</li>";
  const historyRows=history.map(p=>`<li>${escapeHtml(p.status)} · ${escapeHtml(p.start_date||"—")} → ${escapeHtml(p.due_date||"—")} · proposed by ${escapeHtml(p.proposed_by_name||"")}${p.decided_by_name?` · decided by ${escapeHtml(p.decided_by_name)}`:""}</li>`).join("");
  return `<div class="schedule"><h3>Schedule</h3>
    <div class="facts">
      ${fact("Baseline (original)",(b.start_date||"—")+" → "+(b.due_date||"—"))}
      ${fact("Current (approved)",(task.start_date||"—")+" → "+(task.due_date||"—"))}
      ${fact("Pending",pending.length?pending.length+" proposal(s)":"none")}
    </div>
    <h4 class="sched-h">Pending proposals</h4>
    <ul>${pendingRows}</ul>
    <form id="sched-form"><h4 class="sched-h">Propose a schedule change</h4>
      <div class="grid"><label>New start<input name="start_date" type="date"></label><label>New due<input name="due_date" type="date"></label></div>
      <label>Reason<input name="reason" required></label>
      <div class="actions"><button>Propose</button></div><div class="error" id="sched-error"></div></form>
    ${history.length?`<h4 class="sched-h">History</h4><ul>${historyRows}</ul>`:""}</div>`;
}

async function submitSchedule(e){
  e.preventDefault();const err=document.querySelector("#sched-error");err.textContent="";err.style.color="";
  try{
    const {proposal}=await api(`/api/tasks/${detailTaskId}/schedule-proposals`,{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
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

function buildSubtasks(task){
  const rollup=task.subtask_rollup||{total:0,completed:0};
  const rows=(task.subtasks||[]).map(s=>`<li><button type="button" class="link" data-detail="${escapeHtml(s.id)}">${escapeHtml(s.title)}</button> · ${escapeHtml(s.status)} · ${escapeHtml(s.owner_name||"Unassigned")}</li>`).join("")||"<li>No subtasks.</li>";
  const candidates=state.tasks.filter(t=>t.project_id===task.project_id&&t.id!==task.id);
  const parentOptions=candidates.map(t=>`<option value="${escapeHtml(t.id)}"${t.id===task.parent_task_id?" selected":""}>${escapeHtml(t.title)}</option>`).join("");
  return `<div class="subtasks"><h3>Subtasks</h3>
    <p>Roll-up: <strong>${rollup.completed} of ${rollup.total}</strong> subtasks completed — separate from this task's own declared progress (${task.progress==null?"unset":task.progress+"%"}).</p>
    <ul>${rows}</ul>
    <form id="parent-form"><label>Parent task<select name="parent_task_id"><option value="">No parent</option>${parentOptions}</select></label>
      <div class="actions"><button>Set parent</button></div><div class="error" id="parent-error"></div></form></div>`;
}

async function submitParent(e){
  e.preventDefault();const err=document.querySelector("#parent-error");err.textContent="";
  const parent_task_id=e.target.querySelector('select[name="parent_task_id"]').value;
  try{await api(`/api/tasks/${detailTaskId}/parent`,{method:"POST",body:JSON.stringify({parent_task_id})});await load();await openDetail(detailTaskId)}
  catch(x){err.textContent=x.message}
}

async function submitCriticality(e){
  e.preventDefault();const err=document.querySelector("#crit-error");err.textContent="";
  try{await api(`/api/tasks/${detailTaskId}/criticality`,{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await load();await openDetail(detailTaskId)}
  catch(x){err.textContent=x.message}
}

function buildLifecycle(task){
  const canDecide=task.permissions?.can_decide_protected,canRequest=task.permissions?.can_request_protected;
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
  const terminal=["completed","cancelled","abandoned"].includes(task.status);
  let actions="";
  if(!terminal&&task.status!=="submitted"){
    actions+=`<form data-life="submit"><label>Submit work (note)<input name="note"></label><div class="actions"><button>Submit for acceptance</button></div></form>`;
  }
  if(task.status==="submitted"&&pending){
    if(canDecide||canRequest){
      actions+=`<form data-life="accept" data-sid="${escapeHtml(pending.id)}"><label>Acceptance note<input name="decision_note"></label><div class="actions"><button>${canDecide?"Accept &amp; complete":"Request Owner acceptance"}</button></div></form>`;
      actions+=`<form data-life="changes" data-sid="${escapeHtml(pending.id)}"><label>Reason for changes<input name="reason" required></label><div class="actions"><button>${canDecide?"Request changes":"Request Owner to return changes"}</button></div></form>`;
    }else actions+=`<p class="blocked-text">Only the App Owner can decide this submission.</p>`;
  }
  if(task.status==="completed"&&(canDecide||canRequest)){
    actions+=`<form data-life="reopen"><label>Reason to reopen<input name="reason" required></label><label>Revised due date<input name="new_due_date" type="date" required></label><div class="actions"><button>${canDecide?"Reopen":"Request Owner reopening"}</button></div></form>`;
  }
  if(!terminal&&task.status!=="on_hold"&&(canDecide||canRequest)){
    actions+=`<form data-life="hold"><label>On-hold reason<input name="reason" required></label><label>Follow-up checkpoint<input name="checkpoint_date" type="date" required></label><label>Responsible owner<select name="owner_user_id"><option value="">Unassigned</option></select></label><div class="actions"><button>${canDecide?"Put on hold":"Request Owner hold"}</button></div></form>`;
  }
  return `<div class="lifecycle"><h3>Lifecycle</h3>
    <p>Status: <strong>${escapeHtml(task.status)}</strong></p>
    <ul class="submissions">${subs}</ul>${actions}
    <div class="error" id="lifecycle-error"></div></div>`;
}

function buildReviewers(task){
  const rows=(task.reviewers||[]).map(r=>`<li>${escapeHtml(r.display_name)} · ${escapeHtml(r.role)}
    <button type="button" class="link" data-remove-reviewer-user="${escapeHtml(r.user_id)}" data-remove-reviewer-role="${escapeHtml(r.role)}">Remove</button></li>`).join("")||"<li>No reviewers or approvers.</li>";
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
    if(kind==="submit")outcome=await api(`/api/tasks/${task.id}/submit`,{method:"POST",body:JSON.stringify(body)});
    else if(kind==="accept")outcome=await api(`/api/submissions/${form.dataset.sid}/accept`,{method:"POST",body:JSON.stringify(body)});
    else if(kind==="changes")outcome=await api(`/api/submissions/${form.dataset.sid}/request-changes`,{method:"POST",body:JSON.stringify(body)});
    else if(kind==="reopen")outcome=await api(`/api/tasks/${task.id}/reopen`,{method:"POST",body:JSON.stringify(body)});
    else if(kind==="hold")outcome=await api(`/api/tasks/${task.id}/hold`,{method:"POST",body:JSON.stringify(body)});
    await load();await openDetail(task.id);
    if(outcome?.request){const current=document.querySelector("#lifecycle-error");current.style.color="#0c7c86";current.textContent="Owner request created; accepted live state is unchanged."}
  }catch(x){err.textContent=x.message}
}

function buildAttachments(task){
  const canManageFiles=task.permissions?.can_manage_files;
  const frByAtt={};(task.final_results||[]).forEach(f=>{if(f.attachment_id)frByAtt[f.attachment_id]=f.id});
  const rows=(task.attachments||[]).map(a=>{
    const missing=a.exists===false?' <span class="blocked-text">(file not found)</span>':"";
    const note=a.note?`<br><em style="color:#667085;">${escapeHtml(a.note)}</em>`:"";
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
    try{await api(`/api/tasks/${task.id}/attachments`,{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await openDetail(task.id)}
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
  document.querySelector("#add-reviewer-button").addEventListener("click",async()=>{
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

async function submitDetailEdit(e){
  e.preventDefault();
  const form=e.target,error=document.querySelector("#detail-edit-error");error.textContent="";
  const body=Object.fromEntries(new FormData(form));
  try{
    const outcome=await api(`/api/tasks/${detailTaskId}`,{method:"POST",body:JSON.stringify(body)});
    await load();await openDetail(detailTaskId);
    if(outcome.request){const current=document.querySelector("#detail-edit-error");current.style.color="#0c7c86";current.textContent="Owner request created; accepted live state is unchanged."}
  }catch(err){error.textContent=err.message}
}

async function addDependency(){
  const select=document.querySelector("#add-dep-select"),error=document.querySelector("#add-dep-error");error.textContent="";
  const predecessor=select.value;
  if(!predecessor){error.textContent="Choose a predecessor task.";return}
  try{
    await api("/api/task-dependencies",{method:"POST",body:JSON.stringify({predecessor_task_id:predecessor,successor_task_id:detailTaskId})});
    await load();await openDetail(detailTaskId);
  }catch(err){error.textContent=err.message}
}

async function removeDependency(e){
  const button=e.target,error=document.querySelector("#add-dep-error");error.textContent="";
  const reason=button.parentElement.querySelector(".dep-reason").value;
  try{
    await api("/api/task-dependencies",{method:"DELETE",body:JSON.stringify({predecessor_task_id:button.dataset.removePred,successor_task_id:button.dataset.removeSucc,reason})});
    await load();await openDetail(detailTaskId);
  }catch(err){error.textContent=err.message}
}

async function openPeople(){
  try{
    const [u,m]=await Promise.all([api("/api/users"),api("/api/memberships")]);
    renderPeople(u.users,m.memberships);
    const d=document.querySelector("#people-dialog");if(!d.open)d.showModal();
  }catch(err){document.querySelector("#people-body").innerHTML=`<p class="error">${escapeHtml(err.message)}</p>`}
}

function renderPeople(users,memberships){
  const rows=users.map(u=>{
    const toggle=u.global_role==="owner"?"":`<button type="button" class="link" data-toggle="${escapeHtml(u.id)}" data-active="${u.active?1:0}">${u.active?"Deactivate":"Reactivate"}</button>`;
    return `<li><strong>${escapeHtml(u.display_name)}</strong> · ${escapeHtml(u.email)} · ${escapeHtml(u.global_role)}${u.active?"":' · <em>inactive</em>'} ${toggle}</li>`;
  }).join("");
  const userOptions=users.filter(u=>u.active).map(u=>`<option value="${escapeHtml(u.id)}">${escapeHtml(u.display_name)}</option>`).join("");
  const projectOptions=state.projects.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  const grants=memberships.map(m=>`<li>${escapeHtml(m.project_name)} · ${escapeHtml(m.user_name)} · ${escapeHtml(m.role)} <button type="button" class="link" data-revoke-project="${escapeHtml(m.project_id)}" data-revoke-user="${escapeHtml(m.user_id)}">Revoke</button></li>`).join("")||"<li>No access grants yet.</li>";
  const entityRows=(state.entities||[]).map(e=>`<li><strong>${escapeHtml(e.name)}</strong>${e.active?"":' · <em>inactive</em>'} <button type="button" class="link" data-entity-toggle="${escapeHtml(e.id)}" data-active="${e.active?1:0}">${e.active?"Deactivate":"Reactivate"}</button></li>`).join("")||"<li>No entities yet.</li>";
  const filingProjectOptions=state.projects.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`).join("");
  document.querySelector("#people-body").innerHTML=`
    <h2>People &amp; access</h2>
    <h3>Users</h3><ul class="people-list">${rows}</ul>
    <form id="add-user-form"><h3>Add a user</h3>
      <label>Email<input name="email" type="email" required></label>
      <label>Display name<input name="display_name" required></label>
      <label>Temporary password (min 12 chars)<input name="password" type="password" minlength="12" required></label>
      <label>Role<select name="role"><option value="member">Member</option><option value="chairman">Chairman</option></select></label>
      <div class="actions"><button value="add">Create user</button></div><div class="error" id="add-user-error"></div></form>
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
      <p style="color:#8792a2;font-size:12px;margin:4px 0;">Every day counts by default. Uncheck days or add holidays only if this project should skip them.</p>
      <div id="calendar-body"></div>
      <div class="error" id="calendar-error"></div></form>`;
  document.querySelector("#add-user-form").addEventListener("submit",submitAddUser);
  document.querySelector("#grant-form").addEventListener("submit",submitGrant);
  document.querySelectorAll("#people-body [data-toggle]").forEach(b=>b.addEventListener("click",toggleUserActive));
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
      <p style="color:#667085;font-size:12px;">Informational only — project dates are logged on every change but never block task dates.</p>
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
  document.querySelectorAll("#import-steps .step").forEach(li=>{
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
    <div id="import-drop" class="dropzone" tabindex="0" role="button" aria-describedby="import-file-name"><strong>Drop your .xlsx or .csv here</strong><span>or press Enter / click to choose a file</span><input type="file" id="import-file" accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" class="visually-hidden" tabindex="-1"></div>
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
    .map(([k,label,n])=>`<button type="button" class="chip" data-kind="${k}" data-filter="${k}" aria-pressed="${importState.filter===k}">${escapeHtml(label)} <strong>${n}</strong></button>`).join("");
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
  document.querySelectorAll("#import-body .chip").forEach(chip=>chip.addEventListener("click",()=>{importState.filter=importState.filter===chip.dataset.filter?"":chip.dataset.filter;applyImportFilter()}));
  applyImportFilter();
  document.querySelector("#import-back").addEventListener("click",()=>renderImportStep("upload"));
  document.querySelector("#import-commit-btn").addEventListener("click",runImportCommit);
}
function applyImportFilter(){
  const f=importState.filter;
  document.querySelectorAll("#import-body .chip").forEach(c=>c.setAttribute("aria-pressed",String(c.dataset.filter===f)));
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
    const {result}=await apiUpload("/api/import/commit",importState.file,{...importHeaders(),"X-Sha256":importState.preview.sha256});
    importState.result=result;await load();renderImportStep("confirm");
  }catch(err){importError(err.message);button.disabled=false;button.textContent="Retry import"}
}
function renderImportConfirm(){
  const r=importState.result;
  document.querySelector("#import-body").innerHTML=`
    <div class="import-result">
      <h3>Import complete</h3>
      <p class="muted">${escapeHtml(r.filename)} → <strong>${escapeHtml(r.project.name)}</strong>${r.project.create?" (new project)":""}. Nothing was deleted; existing baselines were kept. Every change is in each task's history and in the project activity.</p>
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
    <div class="import-summary" role="group" aria-label="Presets"><span class="muted">Presets:</span><button type="button" class="chip" data-preset="simple">Simple (${(cfg.presets?.simple||[]).length} columns)</button><button type="button" class="chip" data-preset="full">Full (${(cfg.presets?.full||[]).length} columns)</button></div>
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

(async()=>{try{const data=await api("/api/me");Object.assign(state,data);showApp();await load()}catch{showLogin()}})();
