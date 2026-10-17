"""Behaviour tests for the Gantt's dependency arrows (the Asana / monday connector lines).

One elbow line runs from the right edge of a prerequisite's bar to the left edge of the task that waits for it, when both
bars are on screen. Node runs the real src/astra/static/app.js (same DOM stub as test_gantt_zoom.py).
"""
import re
import unittest

from test_frontend_gaps_views import run_probe   # a function only: no test class is imported
from test_web import STATIC


PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
  const T=(id,preds,extra)=>({id,title:id,predecessors:(preds||[]).map(p=>typeof p==="string"?{task_id:p,blocking:true}:p),is_critical_path:false,...extra});

  // ---- ganttDepPairs ----
  const tasks=[T("t0"),T("t1",["t0"],{is_critical_path:true}),T("t2",["t1","t0"],{is_critical_path:true}),
    T("t3",[{task_id:"t2",blocking:false},{task_id:"t2",blocking:false}]),T("t4",["t3"],{is_critical_path:true}),T("orphan",[{task_id:"gone",blocking:true}])];
  tasks[0].is_critical_path=true;
  out.pairs=ganttDepPairs(tasks);

  // ---- ganttDepPath ----
  out.paths={wide:ganttDepPath(100,40,200,90),narrow:ganttDepPath(100,40,108,90),flat:ganttDepPath(100,40,260,40),up:ganttDepPath(100,90,200,40),
    overlap:ganttDepPath(200,40,150,90),rounding:ganttDepPath(100.04,40.06,200.26,90.31)};

  // ---- ganttDepMarkup ----
  const rects={a:{left:0,right:50,top:10,bottom:30,row:"r1"},b:{left:80,right:120,top:50,bottom:70,row:"r2"},c:{left:150,right:190,top:52,bottom:72,row:"r2"},
    d:{left:0,right:10,top:90,bottom:110,row:"r4"},nan:{left:NaN,right:5,top:0,bottom:4,row:"r5"}};
  const measure=id=>rects[id]||null;
  const pairs=[{from:"a",to:"b",blocking:true,critical:false},{from:"b",to:"c",blocking:true,critical:false},{from:"a",to:"missing",blocking:true,critical:false},
    {from:"a",to:"d",blocking:true,critical:true},{from:"a",to:"nan",blocking:true,critical:false}];
  out.markup=ganttDepMarkup(pairs,measure,1234.2,800.7);
  out.empty=ganttDepMarkup([{from:"b",to:"c"}],measure,100,100);
  out.escaped=ganttDepMarkup([{from:'a"x',to:"b",blocking:true,critical:false}],id=>id==='a"x'?rects.a:rects.b,10,10);

  // ---- ganttMeasurer ----
  const fakeNode=(over)=>({offsetParent:{},closest:s=>s===".timeline"?{}:(s===".step-row"?(over.stepRow?{}:null):(s===".gantt-row"?over.row:null)),
    getBoundingClientRect:()=>over.rect});
  const nodes={t:[fakeNode({stepRow:false,row:"parentRow",rect:{left:300,right:340,top:60,bottom:80}}),fakeNode({stepRow:true,row:"stepRow",rect:{left:310,right:380,top:260,bottom:280}})],
    hidden:[{offsetParent:null,closest:s=>s===".timeline"?{}:null,getBoundingClientRect:()=>({left:0,right:1,top:0,bottom:1})}],
    linkOnly:[{offsetParent:{},closest:()=>null,getBoundingClientRect:()=>({left:0,right:1,top:0,bottom:1})}]};
  let queries=0;
  const fakeEl={getBoundingClientRect:()=>({left:10,top:20}),scrollLeft:100,scrollTop:200,
    querySelectorAll:sel=>{queries++;const m=/data-detail="([^"]+)"/.exec(sel);return m&&nodes[m[1]]||[]}};
  const mm=ganttMeasurer(fakeEl);
  out.measure={step:mm("t"),hidden:mm("hidden"),linkOnly:mm("linkOnly"),none:mm("none")};
  mm("t");mm("t");out.measureQueries=queries;
  // The layer sits inside the chart's border, so positions are measured from the padding box.
  const fakeEl2={getBoundingClientRect:()=>({left:10,top:20}),clientLeft:2,clientTop:3,scrollLeft:0,scrollTop:0,querySelectorAll:()=>nodes.t};
  out.measureBorder=ganttMeasurer(fakeEl2)("t");
  // A node inside the open "+N" popup is not a bar of the chart.
  const popup={offsetParent:{},closest:s=>s===".timeline"||s===".step-more-list"?{}:null,getBoundingClientRect:()=>({left:5,right:9,top:5,bottom:9})};
  out.measurePopup=ganttMeasurer({getBoundingClientRect:()=>({left:0,top:0}),scrollLeft:0,scrollTop:0,querySelectorAll:()=>[popup]})("x");

  // ---- drawGanttDependencies ----
  const g=document.querySelector("#gantt");
  const removed=[],inserted=[];
  g.hidden=false;g.scrollWidth=900;g.scrollHeight=700;
  g.querySelectorAll=sel=>sel===".dep-layer"?[{remove:()=>removed.push(1)}]:(/data-detail="([^"]+)"/.exec(sel)?(nodes[/data-detail="([^"]+)"/.exec(sel)[1]]||[]):[]);
  g.insertAdjacentHTML=(pos,html)=>inserted.push([pos,html]);
  g.getBoundingClientRect=()=>({left:0,top:0});g.scrollLeft=0;g.scrollTop=0;
  ganttShown=[T("p",[]),{...T("s",["p"]),predecessors:[{task_id:"p",blocking:true}]}];
  const realMeasurer=ganttMeasurer;
  ganttMeasurer=()=>id=>({p:{left:0,right:60,top:0,bottom:20,row:"A"},s:{left:100,right:160,top:80,bottom:100,row:"B"}})[id]||null;
  storage.get=(k,f)=>f;
  drawGanttDependencies();
  out.drawOn={removed:removed.length,inserted:inserted.length,html:inserted[0]&&inserted[0][1],pos:inserted[0]&&inserted[0][0]};
  inserted.length=0;removed.length=0;
  storage.get=(k,f)=>k==="astra.gantt.deps"?false:f;
  drawGanttDependencies();
  out.drawOff={removed:removed.length,inserted:inserted.length};
  storage.get=(k,f)=>f;g.hidden=true;inserted.length=0;removed.length=0;
  drawGanttDependencies();
  out.drawHidden={removed:removed.length,inserted:inserted.length};
  g.hidden=false;ganttShown=[];inserted.length=0;
  drawGanttDependencies();
  out.drawNothing={inserted:inserted.length};

  // ---- the toggle ----
  const writes=[];let drawn=0;
  storage.set=(k,v)=>writes.push([k,v]);
  const realDraw=drawGanttDependencies;drawGanttDependencies=()=>{drawn++};
  const box=H.store["#gantt-deps"];
  out.toggleHandler=typeof (box&&box.onchange);
  if(box&&box.onchange)box.onchange({target:{checked:false}});
  out.toggle={writes,drawn};
  drawGanttDependencies=realDraw;

  // ---- scheduling uses a timer, not requestAnimationFrame ----
  let timers=[];const realST=globalThis.setTimeout,realCT=globalThis.clearTimeout;
  globalThis.setTimeout=(f,ms)=>{timers.push(ms);return timers.length};globalThis.clearTimeout=()=>{};
  scheduleGanttDependencies();scheduleGanttDependencies();
  globalThis.setTimeout=realST;globalThis.clearTimeout=realCT;
  out.timers=timers;

  // ---- renderGantt draws the arrows at once and again after layout; toggleSteps schedules a redraw ----
  state.user={id:"u1",display_name:"Pat",global_role:"owner"};
  state.projects=[{id:"proj",name:"P",status:"active",can_manage:true}];
  state.today="2026-10-16";storage.get=(k,f)=>f;storage.set=()=>{};
  const W=o=>({project_id:"proj",project_name:"P",owner_name:"Sara",status:"in_progress",due_state:"scheduled",days_to_due:5,criticality:"high",is_blocked:false,is_critical_path:false,predecessors:[],...o});
  state.tasks=[W({id:"p",title:"Workstream",start_date:"2026-07-01",due_date:"2026-08-31"}),W({id:"c",title:"Step",parent_task_id:"p",start_date:"2026-07-01",due_date:"2026-07-31"})];
  let draws=0;drawGanttDependencies=()=>{draws++};
  const tm=[];globalThis.setTimeout=(f,ms)=>{tm.push(ms);return tm.length};globalThis.clearTimeout=()=>{};
  renderGantt(state.tasks);out.afterRender={draws,timers:[...tm]};
  draws=0;tm.length=0;toggleSteps("p");out.afterToggle={draws,timers:[...tm]};
  globalThis.setTimeout=realST;globalThis.clearTimeout=realCT;
  return out;
};
'''

DEP_TAIL = re.compile(r'<path class="([^"]+)" d="([^"]+)" marker-end="url\(#([^)]+)\)" data-from="([^"]*)" data-to="([^"]*)"/>')


class GanttDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(PROBE, static=STATIC)

    # ---- pairs -----------------------------------------------------------------------------------
    def test_every_link_is_listed_once_with_its_blocking_flag(self):
        got = [(p['from'], p['to'], p['blocking']) for p in self.out['pairs']]
        self.assertEqual(got, [('t0', 't1', True), ('t1', 't2', True), ('t0', 't2', True), ('t2', 't3', False), ('t3', 't4', True), ('gone', 'orphan', True)])

    def test_a_link_is_critical_only_when_both_ends_are_on_the_critical_path(self):
        crit = {(p['from'], p['to']): p['critical'] for p in self.out['pairs']}
        self.assertEqual(crit[('t0', 't1')], True)
        self.assertEqual(crit[('t1', 't2')], True)
        self.assertEqual(crit[('t2', 't3')], False)   # a critical prerequisite feeding a task that is not critical
        self.assertEqual(crit[('t3', 't4')], False)   # a prerequisite that is not critical feeding a critical task
        self.assertEqual(crit[('gone', 'orphan')], False)   # an unknown prerequisite is never critical

    # ---- path shapes -----------------------------------------------------------------------------
    def test_a_link_with_room_drops_beside_the_prerequisite_then_runs_to_the_successor(self):
        self.assertEqual(self.out['paths']['wide'], 'M100 40H106V90H200')

    def test_a_link_to_a_task_that_starts_right_after_steps_around_it(self):
        self.assertEqual(self.out['paths']['narrow'], 'M100 40H106V65H102V90H108')

    def test_two_bars_on_the_same_height_are_joined_by_a_straight_line(self):
        self.assertEqual(self.out['paths']['flat'], 'M100 40H260')

    def test_a_successor_above_its_prerequisite_is_drawn_upwards(self):
        self.assertEqual(self.out['paths']['up'], 'M100 90H106V40H200')

    def test_a_successor_that_starts_before_its_prerequisite_ends_still_gets_a_routed_line(self):
        self.assertEqual(self.out['paths']['overlap'], 'M200 40H206V65H144V90H150')

    def test_coordinates_are_rounded_to_a_tenth_of_a_pixel(self):
        self.assertEqual(self.out['paths']['rounding'], 'M100 40.1H106V90.3H200.3')

    # ---- markup ----------------------------------------------------------------------------------
    def test_only_links_with_two_visible_bars_in_different_rows_are_drawn(self):
        drawn = DEP_TAIL.findall(self.out['markup'])
        self.assertEqual([(d[3], d[4]) for d in drawn], [('a', 'b'), ('a', 'd')])   # b->c is one row, a->missing and a->nan can't be measured

    def test_the_layer_is_sized_to_the_scrolling_content_and_hidden_from_assistive_technology(self):
        m = self.out['markup']
        self.assertIn('class="dep-layer" width="1235" height="801" aria-hidden="true" focusable="false"', m)

    def test_critical_links_use_the_critical_class_and_arrowhead(self):
        drawn = {(d[3], d[4]): d for d in DEP_TAIL.findall(self.out['markup'])}
        self.assertEqual(drawn[('a', 'd')][0], 'dep-line critical')
        self.assertEqual(drawn[('a', 'd')][2], 'dep-arrow-critical')
        self.assertEqual(drawn[('a', 'b')][0], 'dep-line')
        self.assertEqual(drawn[('a', 'b')][2], 'dep-arrow')
        self.assertIn('<marker id="dep-arrow"', self.out['markup'])
        self.assertIn('<marker id="dep-arrow-critical"', self.out['markup'])

    def test_a_line_leaves_the_prerequisites_right_edge_and_enters_the_successors_left_edge(self):
        d = {(m[3], m[4]): m[1] for m in DEP_TAIL.findall(self.out['markup'])}
        self.assertEqual(d[('a', 'b')], 'M50 20H56V60H80')   # a: right 50, mid-height 20; b: left 80, mid-height 60

    def test_nothing_is_drawn_when_nothing_can_be_measured(self):
        self.assertEqual(self.out['empty'], '')

    def test_task_ids_are_escaped_in_the_markup(self):
        self.assertIn('data-from="a&quot;x"', self.out['escaped'])
        self.assertNotIn('data-from="a"x"', self.out['escaped'])

    # ---- measuring -------------------------------------------------------------------------------
    def test_a_step_rows_own_bar_wins_over_the_chip_in_its_parents_track(self):
        m = self.out['measure']['step']
        self.assertEqual(m['row'], 'stepRow')
        self.assertEqual((m['left'], m['right']), (310 - 10 + 100, 380 - 10 + 100))   # relative to the chart's scrolling content
        self.assertEqual((m['top'], m['bottom']), (260 - 20 + 200, 280 - 20 + 200))

    def test_hidden_bars_and_links_outside_the_timeline_are_ignored(self):
        self.assertIsNone(self.out['measure']['hidden'])
        self.assertIsNone(self.out['measure']['linkOnly'])
        self.assertIsNone(self.out['measure']['none'])

    def test_positions_are_measured_from_inside_the_charts_border(self):
        m = self.out['measureBorder']
        self.assertEqual((m['left'], m['right'], m['top'], m['bottom']), (310 - 12, 380 - 12, 260 - 23, 280 - 23))

    def test_a_bar_inside_the_open_plus_n_popup_is_not_measured(self):
        self.assertIsNone(self.out['measurePopup'])

    def test_each_task_is_measured_once(self):
        self.assertEqual(self.out['measureQueries'], 4)   # t, hidden, linkOnly, none; the repeat calls hit the cache

    # ---- drawing and the toggle ------------------------------------------------------------------
    def test_drawing_replaces_the_old_layer_and_adds_the_new_one_at_the_end_of_the_chart(self):
        d = self.out['drawOn']
        self.assertEqual((d['removed'], d['inserted'], d['pos']), (1, 1, 'beforeend'))
        self.assertIn('class="dep-line"', d['html'])
        self.assertIn('width="900" height="700"', d['html'])

    def test_turning_dependencies_off_removes_the_layer_and_draws_nothing(self):
        self.assertEqual(self.out['drawOff'], {'removed': 1, 'inserted': 0})

    def test_a_hidden_chart_draws_nothing(self):
        self.assertEqual(self.out['drawHidden']['inserted'], 0)

    def test_a_chart_with_no_tasks_draws_nothing(self):
        self.assertEqual(self.out['drawNothing']['inserted'], 0)

    def test_the_toggle_saves_the_choice_and_redraws(self):
        self.assertEqual(self.out['toggleHandler'], 'function')
        self.assertEqual(self.out['toggle'], {'writes': [['astra.gantt.deps', False]], 'drawn': 1})

    def test_a_render_draws_the_arrows_at_once_and_schedules_a_second_pass_after_layout(self):
        self.assertEqual(self.out['afterRender'], {'draws': 1, 'timers': [0]})

    def test_expanding_or_collapsing_steps_schedules_a_redraw(self):
        self.assertEqual(self.out['afterToggle']['draws'], 0)   # it schedules, it does not draw inside the click
        self.assertIn(0, self.out['afterToggle']['timers'])   # the announcement uses its own, longer timer

    def test_redrawing_is_scheduled_with_a_zero_delay_timer(self):
        self.assertEqual(self.out['timers'], [0, 0])   # not requestAnimationFrame, which a background tab never runs


class GanttDependencyCssTests(unittest.TestCase):
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    html = (STATIC / 'index.html').read_text(encoding='utf-8')

    def test_the_layer_sits_between_the_bars_and_the_pinned_columns(self):
        layer = int(re.search(r'\.dep-layer \{[^}]*z-index: (\d+)', self.css).group(1))
        pinned = int(re.search(r'#gantt \.gantt-row > \.task-name, #gantt \.gantt-row > \.task-meta \{[^}]*z-index: (\d+)', self.css).group(1))
        header = int(re.search(r'\.gantt-head \{[^}]*z-index: (\d+)', self.css).group(1))
        self.assertLess(layer, pinned)
        self.assertLess(pinned, header)

    def test_the_layer_never_intercepts_the_mouse(self):
        self.assertRegex(self.css, r'\.dep-layer \{[^}]*pointer-events: none')

    def test_the_chart_is_the_positioning_context_for_the_layer(self):
        self.assertRegex(self.css, r'#gantt \{ position: relative;')

    def test_lines_and_arrowheads_use_colour_tokens(self):
        for rule in (r'\.dep-line \{[^}]*stroke: var\(--gray\)', r'\.dep-line\.critical \{[^}]*stroke: var\(--crit\)',
                     r'\.dep-head \{ fill: var\(--gray\)', r'\.dep-head\.critical \{ fill: var\(--crit\)'):
            self.assertRegex(self.css, rule)

    def test_the_dependencies_toggle_is_a_labelled_checkbox_that_starts_on(self):
        self.assertRegex(self.html, r'<label class="inline dep-toggle"><input type="checkbox" id="gantt-deps" checked> Dependencies</label>')


if __name__ == '__main__':
    unittest.main()
