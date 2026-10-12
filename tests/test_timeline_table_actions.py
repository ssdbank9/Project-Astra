"""Exercise actual table rendering and event dispatch without a browser fixture."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('node'), 'Node is required for timeline UI checks')
class TimelineTableActionTests(unittest.TestCase):
    def source(self):
        return (Path(__file__).parents[1] / 'src/astra/static/app.js').read_text(encoding='utf-8')

    def helpers(self, source):
        functions = []
        for name in ('escapeHtml', 'canMoveOnBoard', 'canMoveTimelineTask', 'timelineMoveButton'):
            match = re.search(r'^function ' + name + r'\([^\n]+', source, re.M)
            if match:
                functions.append(match.group(0))
        return '\n'.join(functions)

    def run_js(self, script):
        result = subprocess.run([shutil.which('node'), '-e', script], capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)

    def fixture(self):
        return '''
const assert=require('node:assert/strict');
const parent={id:'parent',title:'Parent',project_id:'p',project_name:'Project',status:'draft',start_date:'2026-10-01',due_date:'2026-10-03'};
const child={...parent,id:'child',title:'Child',parent_task_id:'parent',start_date:'2026-10-04',due_date:'2026-10-05'};
const state={tasks:[parent,child],projects:[{id:'p',can_manage:true,status:'active'}]};
const CLOSED_STATUSES=['completed','cancelled','abandoned'];
'''

    def test_table_renders_one_move_action_per_eligible_task_and_step(self):
        source = self.source()
        renderer = source[source.index('function renderScheduleTable('):source.index('// Shared tooltip')]
        script = self.fixture() + '''
const bulk={ids:new Set()},STEP_HUES=7;
const bulkScope=()=>false,stepHue=()=>1,statusLabel=String,dueText=()=>'',critLabel=()=>'',reassignChip=()=>'';
const document={querySelector:()=>({textContent:'As of 2026-10-12'})};
const table={innerHTML:''};
const groups={top:[parent],childrenOf:new Map([['parent',[child]]]),stepIndex:new Map([['child',{idx:1,total:1}]])};
''' + self.helpers(source) + '\n' + renderer + '''
const moveIds=()=>[...table.innerHTML.matchAll(/data-task-move="([^"]+)"/g)].map(m=>m[1]);
renderScheduleTable(groups,table);
assert.deepEqual(moveIds(),['parent','child']);
assert.match(table.innerHTML,/aria-label="Move task Child"/);
state.projects[0].can_manage=false;
renderScheduleTable(groups,table);assert.deepEqual(moveIds(),[]);
state.projects[0].can_manage=true;state.projects[0].status='closed';
renderScheduleTable(groups,table);assert.deepEqual(moveIds(),[]);
state.projects[0].status='active';parent.status='completed';child.status='cancelled';
renderScheduleTable(groups,table);assert.deepEqual(moveIds(),[]);
'''
        self.run_js(script)

    def test_table_click_uses_same_move_dialog_and_linked_review_as_gantt(self):
        source = self.source()
        start = source.find('function openTimelineTaskMove(')
        if start < 0:
            start = source.index('taskTimeline.addEventListener("click"')
        hooks = source[start:]
        script = self.fixture() + '''
const handlers={gantt:{},table:{}};
const taskTimeline={addEventListener:(kind,fn)=>handlers.gantt[kind]=fn};
const table={addEventListener:(kind,fn)=>handlers.table[kind]=fn};
let shown=0;
const form={elements:{mode:{value:'after'},target:{value:'parent'},start:{value:'2026-10-04'}}};
const cancel={};
const dialog={showModal:()=>shown++,close:()=>{},remove:()=>{},addEventListener:()=>{},querySelector:s=>s==='form'?form:cancel};
const document={querySelector:()=>table,createElement:()=>dialog,body:{appendChild:()=>{}}};
const DAY=86400000,iso=ms=>new Date(ms).toISOString().slice(0,10),ganttToday=()=> '2026-10-12';
const reviewed=[];
const reviewTaskDrop=(task,mode,target,start)=>reviewed.push([task.id,mode,target.id,start]);
''' + self.helpers(source) + '\n' + hooks + '''
assert.equal(typeof handlers.table.click,'function','Table rows must receive the accessible movement handler');
assert.equal(handlers.table.click,handlers.gantt.click,'Both views must share one handler');
const click={target:{closest:()=>({dataset:{taskMove:'child'}})}};
handlers.table.click(click);assert.equal(shown,1);
form.onsubmit({preventDefault:()=>{},currentTarget:form});
assert.deepEqual(reviewed,[['child','after','parent','2026-10-04']]);
state.projects[0].can_manage=false;handlers.table.click(click);assert.equal(shown,1);
'''
        self.run_js(script)

    def test_filtered_table_preserves_drawn_siblings_and_hidden_slots(self):
        source = self.source()
        renderer = source[source.index('function renderScheduleTable('):source.index('// Shared tooltip')]
        group = source[source.index('function groupSteps('):source.index('function dateExtent(')]
        order = source[source.index('function timelineOrder('):source.index('let timelineTaskDrag=')]
        snapshot = source[source.index('function timelineTaskOrder('):source.index('function clearTaskDrop(')]
        step = re.search(r'^function stepOrder\([^\n]+', source, re.M).group(0)
        script = self.fixture() + '''
const other={...parent,id:'other',title:'Other'};
const a={...child,id:'a',start_date:'2026-10-02'};
const b={...child,id:'b',start_date:'2026-10-01'};
const hidden={...child,id:'hidden',start_date:'2026-10-03'};
const c={...child,id:'c',start_date:'2026-10-04'};
state.tasks=[other,parent,a,c,b,hidden];
const bulk={ids:new Set()},STEP_HUES=7;
const bulkScope=()=>false,stepHue=()=>1,statusLabel=String,dueText=()=>'',critLabel=()=>'',reassignChip=()=>'';
const table={innerHTML:''};
const document={querySelector:()=>({textContent:'As of 2026-10-12'}),querySelectorAll:selector=>
 selector.includes('#schedule-table')?[...table.innerHTML.matchAll(/<tr[^>]*data-timeline-task="([^"]+)"/g)].map(m=>({dataset:{timelineTask:m[1]},closest:()=>null})):[]};
''' + self.helpers(source) + '\n' + step + '\n' + group + order + snapshot + renderer + '''
renderScheduleTable(groupSteps([other,a,c,b]),table);
assert.deepEqual(timelineTaskOrder('p'),['other','parent','a','c','hidden','b']);
'''
        self.run_js(script)
