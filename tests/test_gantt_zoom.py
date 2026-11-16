"""Behaviour tests for the Gantt chart: the Step pane, the day grid, the bars, the month and week
periods, the day-width zoom, the Filter popover and the toolbar.

The chart follows the shadcnstudio "gantt-chart-04" block (Aly, 2026-11-09), drawn in Astra's plain
JavaScript. Node runs the real src/astra/static/app.js against the DOM stub that
tests/test_frontend_gaps_views.py already uses, so each test fails if the behaviour is removed.
"""
import re
import unittest
from html.parser import HTMLParser

from test_frontend_gaps_views import run_probe   # a function only: no test class is imported
from test_web import STATIC


# Shared by the other Gantt probes (test_gantt_dependencies.py, test_gantt_range.py, test_gantt_new_step.py).
# storage is an in-memory map; boot() signs a user in, loads one project and draws the chart.
SETUP = r'''
  const mem={...(input.mem||{})};storage.get=(k,f)=>k in mem?mem[k]:f;storage.set=(k,v)=>{mem[k]=v};
  const T=(id,title,s,e,x)=>({id,title,project_id:"pr1",project_name:"Release Plan",status:"assigned",start_date:s,due_date:e,
    predecessors:[],progress:0,revision:1,owner_user_id:"u1",owner_name:"Olive Owner",...x});
  const P=ids=>ids.map(id=>({task_id:id,title:id,status:"assigned",blocking:true}));
  const g=H.store["#gantt"];
  const boot=(tasks,o={})=>{
    state.user={id:"u1",display_name:"Olive Owner",global_role:o.owner?"owner":"member"};
    state.projects=o.projects||[{id:"pr1",name:"Release Plan",status:o.closed?"closed":"active",can_manage:o.manage!==false}];
    state.today=o.today||"2026-06-10";state.ganttDay=null;state.tasks=tasks;
    gx.anchor=null;gx.scope=null;gx.hiddenStatus.clear();gx.hiddenOwner.clear();gx.hover=null;gx.focus=null;
    renderGantt(state.tasks);
  };
  refreshGantt=()=>renderGantt(state.tasks);
  const paths=()=>(H.store["#gantt .gx-deps-paths"]||{}).innerHTML||"";
  const zoomBtn=k=>H.store[`#gantt-zoom [data-zoom="${k}"]`]||{};
'''

PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
''' + SETUP + r'''
  const props={};g.style={setProperty:(k,v)=>{props[k]=String(v)},removeProperty:k=>{delete props[k]}};
  const tasks=()=>[
    T("a","Alpha","2026-06-01","2026-06-05",{status:"completed"}),
    T("b","Beta","2026-06-08","2026-06-12",{status:"in_progress",progress:40,predecessors:P(["a"])}),
    T("c","Gamma <b>","2026-06-10","2026-06-15",{predecessors:P(["b","a"]),is_blocked:true,owner_user_id:"u2",owner_name:"Mo Member"}),
    T("m","Launch",null,"2026-06-20",{is_milestone:true}),
    T("late","Late one","2026-05-25","2026-06-02",{status:"delayed"}),
    T("long","Long one","2026-06-28","2026-07-04",{}),
    T("und","Undated",null,null,{owner_user_id:null,owner_name:null}),
    T("par","Design","2026-06-01","2026-06-19",{}),
    T("k1","Kid one","2026-06-02","2026-06-03",{parent_task_id:"par",status:"completed"}),
    T("k2","Kid two","2026-06-04","2026-06-09",{parent_task_id:"par",status:"in_progress",progress:50}),
  ];
  const tool=()=>({title:H.store["#gantt-title"].textContent,inOff:!!zoomBtn("in").disabled,outOff:!!zoomBtn("out").disabled,
    newHidden:H.store["#gantt-new-step"].hidden,navHidden:H.store["#gantt-nav"].hidden,zoomHidden:H.store["#gantt-zoom"].hidden,
    periodHidden:H.store["#gantt-period"].hidden,filterHidden:H.store["#gantt-filter-btn"].hidden,todayHidden:H.store["#gantt-today"].hidden});
  const snap=()=>({html:g.innerHTML,ds:{...g.dataset},props:{...props},hidden:g.hidden,tool:tool(),filter:H.store["#gantt-filter"].innerHTML});

  // ---- month view ----
  boot(tasks());out.month=snap();
  out.placed=(()=>{const bar=document.querySelectorAll("#gantt [data-bar]").find(n=>n.dataset.bar==="b"),fill=document.querySelectorAll("#gantt [data-pc]")[0];
    return {left:bar.style.left,width:bar.style.width,fill:fill.style.width}})();

  // ---- week view ----
  mem["astra.gantt.period"]="week";boot(tasks());out.week=snap();
  g.clientWidth=700;boot(tasks());out.weekNarrow={ds:{...g.dataset}};
  g.clientWidth=1180;delete mem["astra.gantt.period"];

  // ---- the period select ----
  boot(tasks());
  const period=H.store["#gantt-period"];
  period.onchange({target:{value:"week"}});out.selectWeek={stored:mem["astra.gantt.period"],mode:g.dataset.mode};
  period.onchange({target:{value:"zzz"}});out.selectBogus={stored:mem["astra.gantt.period"],mode:g.dataset.mode};
  mem["astra.gantt.period"]="quarter";boot(tasks());out.storedBogus=g.dataset.mode;
  delete mem["astra.gantt.period"];

  // ---- zoom: five day widths, month view only ----
  boot(tasks());
  const zoomClick=k=>{for(const f of H.store["#gantt-zoom"]._l.click||[])f({target:{closest:s=>s==="[data-zoom]"?{dataset:{zoom:k},disabled:!!zoomBtn(k).disabled}:null}})};
  out.zoom=[];
  for(const k of ["in","in","in","in","out","out","out","out","out"]){zoomClick(k);out.zoom.push([k,+g.dataset.day,mem["astra.gantt.dayw"],!!zoomBtn("in").disabled,!!zoomBtn("out").disabled])}
  await new Promise(r=>setTimeout(r,60));out.zoomSaid=H.store["#gantt-live"].textContent;
  for(const f of H.store["#gantt-zoom"]._l.click||[])f({target:{closest:()=>null}});out.zoomMiss=+g.dataset.day;
  out.zoomStored={};
  for(const v of [0,4,"2",7,-1,1.5,null]){mem["astra.gantt.dayw"]=v;boot(tasks());out.zoomStored[String(v)]=+g.dataset.day}
  delete mem["astra.gantt.dayw"];

  // ---- the pane follows the card's width ----
  out.pane={};
  for(const w of [500,639,640,1023,1024,1600]){g.clientWidth=w;boot(tasks());out.pane[w]=[g.dataset.pane,props["--gx-pane"]]}
  g.clientWidth=1180;

  // ---- who may drag, and who may add a step ----
  boot(tasks(),{manage:false});out.viewer={html:g.innerHTML,tool:tool()};
  boot(tasks(),{manage:false,owner:true});out.appOwner={tool:tool()};
  boot(tasks(),{closed:true,owner:true});out.closedProject={tool:tool()};
  const phone=matchMedia("(max-width: 760px)").matches;out.phone=phone;

  // ---- status, dates, length, progress, codes ----
  const S=x=>gxStatus({status:"assigned",...x});
  out.status={completed:S({status:"completed"}),completedBlocked:S({status:"completed",is_blocked:true}),blocked:S({is_blocked:true}),hold:S({status:"on_hold"}),
    cancelled:S({status:"cancelled",due_state:"overdue"}),abandoned:S({status:"abandoned"}),overdue:S({status:"in_progress",due_state:"overdue"}),delayed:S({status:"delayed"}),
    progress:["in_progress","submitted","reopened","changes_requested"].map(s=>S({status:s})),queued:["draft","assigned"].map(s=>S({status:s})),
    blockedOverdue:S({is_blocked:true,due_state:"overdue"})};
  out.units={
    span:[gxSpan({start_date:"2026-06-01",due_date:"2026-06-05"}),gxSpan({due_date:"2026-06-05"}),gxSpan({start_date:"2026-06-01"}),gxSpan({}),
      gxSpan({start_date:"2026-06-09",due_date:"2026-06-05"}),gxSpan({is_milestone:true,start_date:"2026-06-01",due_date:"2026-06-05"}),gxSpan({is_milestone:true,start_date:"2026-06-01"})],
    len:[gxLen({start_date:"2026-06-01",due_date:"2026-06-05"}),gxLen({due_date:"2026-06-05"}),gxLen({}),gxLen({is_milestone:true,due_date:"2026-06-05"}),gxLen({start_date:"2026-01-01",due_date:"2026-12-31"})],
    dates:[gxDates({start_date:"2026-06-03",due_date:"2026-06-07"}),gxDates({start_date:"2026-06-28",due_date:"2026-07-02"}),gxDates({due_date:"2026-06-05"}),gxDates({}),
      gxDates({start_date:"2026-12-30",due_date:"2027-01-02"})],
    progress:[gxProgress({status:"completed",progress:10}),gxProgress({progress:40.4}),gxProgress({progress:140}),gxProgress({progress:-3}),gxProgress({progress:null}),gxProgress({progress:"abc"})],
    code:[gxCode("Release Plan"),gxCode("Rupani Academy USA Charter School"),gxCode("alpha"),gxCode("Q3"),gxCode("  "),gxCode("R&D / Ops"),gxCode(null)]};

  // ---- the Filter popover ----
  boot(tasks());
  const change=t=>{for(const f of H.store["#gantt-filter"]._l.change||[])f({target:t})};
  const rowIds=()=>[...g.innerHTML.matchAll(/class="gx-row gx-step[^"]*" data-timeline-task="([^"]+)"/g)].map(m=>m[1]);
  const phases=()=>[...g.innerHTML.matchAll(/data-phase-row="([^"]+)"/g)].map(m=>m[1]);
  const fbtn=H.store["#gantt-filter-btn"];
  const fsnap=()=>({rows:rowIds(),phases:phases(),on:fbtn.classList.contains("is-on"),label:fbtn.getAttribute("aria-label"),paths:(paths().match(/<path/g)||[]).length,
    stat:(/data-phase-row="p:pr1".*?class="gx-stat">([^<]*)</.exec(g.innerHTML)||[])[1]});
  out.filter={all:fsnap()};
  change({dataset:{fstatus:"completed"},checked:false});out.filter.noCompleted=fsnap();out.filter.boxes=H.store["#gantt-filter"].innerHTML;
  change({dataset:{fstatus:"progress"},checked:false});out.filter.noDesign=fsnap();
  change({dataset:{fstatus:"completed"},checked:true});change({dataset:{fstatus:"progress"},checked:true});out.filter.back=fsnap();
  change({dataset:{fowner:"u2"},checked:false});out.filter.noMo=fsnap();
  change({dataset:{fowner:""},checked:false});out.filter.noUnassigned=fsnap();
  change({dataset:{},checked:false});out.filter.stray=fsnap();
  change({dataset:{fowner:"u1"},checked:false});out.filter.none=fsnap();out.filter.noneHtml=g.innerHTML;
  // The popover opens and closes from its button; a new portfolio scope keeps the hidden sets.
  // Another page (other projects) starts with every box ticked.
  gx.hiddenOwner.add("u2");state.tasks=[T("x","Xray","2026-06-02","2026-06-03",{project_id:"pr9",project_name:"Ninth"})];renderGantt(state.tasks);
  out.scopeReset={on:fbtn.classList.contains("is-on"),hidden:gx.hiddenOwner.size+gx.hiddenStatus.size};
  // A redraw while a box in the popover has focus gives focus back to the same box.
  boot(tasks());const popEl=H.store["#gantt-filter"],focused=[],realQS=popEl.querySelector;
  popEl.querySelector=s=>({focus(){focused.push(s)}});
  popEl.contains=()=>true;document.activeElement={dataset:{fowner:"u2"}};renderGantt(state.tasks);out.popFocus=focused.splice(0);
  document.activeElement={dataset:{fstatus:"risk"}};renderGantt(state.tasks);out.popFocusStatus=focused.splice(0);
  document.activeElement={dataset:{}};renderGantt(state.tasks);out.popFocusOther=focused.splice(0);
  popEl.contains=()=>false;document.activeElement={dataset:{fowner:"u2"}};renderGantt(state.tasks);out.popFocusOutside=focused.splice(0);
  popEl.querySelector=realQS;document.activeElement=null;
  const pop=H.store["#gantt-filter"];pop.hidden=true;
  fbtn.onclick();out.pop=[pop.hidden,fbtn.getAttribute("aria-expanded")];
  fbtn.onclick();out.pop.push(pop.hidden,fbtn.getAttribute("aria-expanded"));

  // ---- the Schedule table switch and the empty state ----
  mem["astra.gantt.view"]="table";boot(tasks());
  out.table={ganttHidden:g.hidden,tableHidden:H.store["#schedule-table"].hidden,tool:tool(),hasTable:H.store["#schedule-table"].innerHTML.includes('class="sched-table"')};
  delete mem["astra.gantt.view"];
  boot([]);out.empty={html:g.innerHTML,filter:H.store["#gantt-filter"].innerHTML,tool:tool()};

  // ---- two projects: one phase row each, in the order of state.projects ----
  boot([T("x","Xray","2026-06-02","2026-06-03",{project_id:"pr2",project_name:"Second"}),T("a","Alpha","2026-06-01","2026-06-05")],
    {projects:[{id:"pr1",name:"Release Plan",status:"active",can_manage:true},{id:"pr2",name:"Second",status:"active",can_manage:false}]});
  out.two={phases:phases(),rows:rowIds(),drag:[...g.innerHTML.matchAll(/data-drag="([^"]+)"/g)].map(m=>m[1])};

  // ---- owners in the popover: by name, the unassigned row last ----
  boot([T("a","A","2026-06-01","2026-06-02",{owner_user_id:"u9",owner_name:"Zed Last"}),T("b","B","2026-06-03","2026-06-04",{owner_user_id:null,owner_name:null}),
    T("c","C","2026-06-05","2026-06-06",{owner_user_id:"u3",owner_name:"Amy First"})]);
  out.ownerOrder=[...H.store["#gantt-filter"].innerHTML.matchAll(/data-fowner="([^"]*)"/g)].map(m=>m[1]);
  return out;
};
'''


class _Tags(HTMLParser):
    """Every start tag of a fragment, as (tag, attrs dict), in document order."""

    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def having(self, attr, value=None):
        return [a for _, a in self.tags if attr in a and (value is None or a[attr] == value)]

    def of_class(self, name):
        return [a for _, a in self.tags if name in (a.get('class') or '').split()]


def bar(html, task_id):
    found = _Tags(html).having('data-bar', task_id)
    assert len(found) == 1, (task_id, found)
    return found[0]


def text_of(html, attr, value):
    """The text inside the first element carrying attr="value"."""
    return re.search(r'%s="%s"[^>]*>([^<]*)<' % (attr, re.escape(value)), html).group(1)


class GanttChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(PROBE, static=STATIC)
        cls.month = cls.out['month']['html']
        cls.week = cls.out['week']['html']

    # ---- the frame ------------------------------------------------------------------------------
    def test_the_month_view_draws_one_cell_per_day_at_the_default_width(self):
        m = self.out['month']
        self.assertEqual(m['ds'], {'pane': 'lg', 'mode': 'month', 'day': 48})
        self.assertEqual(m['props'], {'--gx-day': '48px', '--gx-pane': '560px', '--gx-days': '30'})
        tags = _Tags(self.month)
        self.assertEqual(len(tags.of_class('gx-day')), 30)
        self.assertEqual(len(tags.of_class('gx-col')), 30)
        self.assertEqual(m['tool']['title'], 'June 2026')

    def test_the_header_groups_days_into_iso_weeks_with_their_date_range(self):
        weeks = re.findall(r'<span class="gx-week" data-w="(\d+)"><span>([^<]*)</span>', self.month)
        self.assertEqual(weeks, [('336', 'W23 · Jun 1 – 7'), ('336', 'W24 · Jun 8 – 14'), ('336', 'W25 · Jun 15 – 21'),
                                 ('336', 'W26 · Jun 22 – 28'), ('96', 'W27 · Jun 29 – 30')])

    def test_today_is_a_pill_in_the_header_and_a_marked_column(self):
        self.assertEqual(re.findall(r'<span class="gx-day today" aria-current="date"><b class="gx-today-pill">(\d+)</b>', self.month), ['10'])
        cols = [a['class'] for a in _Tags(self.month).of_class('gx-col')]
        self.assertEqual([i + 1 for i, c in enumerate(cols) if 'today' in c.split()], [10])
        self.assertEqual(self.month.count('aria-current'), 1)

    def test_saturday_and_sunday_are_marked_in_the_header_and_the_grid(self):
        days = [a['class'] for a in _Tags(self.month).of_class('gx-day')]
        cols = [a['class'] for a in _Tags(self.month).of_class('gx-col')]
        weekend = [6, 7, 13, 14, 20, 21, 27, 28]
        self.assertEqual([i + 1 for i, c in enumerate(days) if 'we' in c.split()], weekend)
        self.assertEqual([i + 1 for i, c in enumerate(cols) if 'we' in c.split()], weekend)

    def test_the_pane_has_the_five_columns_of_the_block(self):
        head = re.search(r'<div class="gx-pane-head">(.*?)</div>', self.month).group(1)
        self.assertEqual(re.findall(r'>([^<]+)</span>', head), ['Step', 'Owner', 'Status', 'Dates', 'Length'])

    def test_the_pane_width_follows_the_width_of_the_card(self):
        self.assertEqual(self.out['pane'], {'500': ['sm', '192px'], '639': ['sm', '192px'], '640': ['md', '288px'],
                                            '1023': ['md', '288px'], '1024': ['lg', '560px'], '1600': ['lg', '560px']})

    def test_positions_travel_as_data_attributes_and_are_applied_through_the_cssom(self):
        # The page's Content-Security-Policy forbids inline styles, so no style attribute may be written.
        self.assertNotIn('style=', self.month)
        self.assertEqual(self.out['placed'], {'left': '336px', 'width': '240px', 'fill': '32%'})

    # ---- phases ---------------------------------------------------------------------------------
    def test_a_project_is_the_top_phase_and_a_task_with_steps_is_a_phase_under_it(self):
        phases = _Tags(self.month).having('data-phase-row')
        self.assertEqual([(p['data-phase-row'], p['class']) for p in phases],
                         [('p:pr1', 'gx-row gx-phase gx-d0'), ('t:par', 'gx-row gx-phase gx-d1')])
        self.assertEqual(re.findall(r'<span class="gx-phase-name" title="[^"]*">([^<]*)</span><span class="gx-code">([^<]*)</span>', self.month),
                         [('Release Plan', 'RP'), ('Design', 'RP-01')])
        steps = {a['data-timeline-task']: a['class'] for a in _Tags(self.month).of_class('gx-step') if 'data-timeline-task' in a}
        self.assertIn('gx-d1', steps['a'].split())
        self.assertIn('gx-d2', steps['k1'].split())

    def test_a_phase_counts_its_finished_steps_and_averages_their_progress(self):
        stats = re.findall(r'<span class="gx-stat">([^<]*)<span class="gx-stat-pct">([^<]*)</span>', self.month)
        # Nine steps (the parent "Design" is a phase, not a step): a and k1 are done; 100+40+0+0+0+0+0+100+50 = 290 / 9 = 32.
        self.assertEqual(stats, [('2/9', ' · 32%'), ('1/2', ' · 75%')])

    def test_a_phase_draws_a_summary_bar_over_the_dates_of_its_steps(self):
        sums = _Tags(self.month).of_class('gx-sum')
        # The project: May 25 to Jul 4, cut to June. "Design": its own Jun 1 to Jun 19.
        self.assertEqual([(s['data-l'], s['data-w'], s['aria-label']) for s in sums],
                         [('0', '1440', 'Release Plan · 32%'), ('0', '912', 'Design · 75%')])
        self.assertEqual([a['data-pc'] for a in _Tags(self.month).of_class('gx-sum-fill')], ['32', '75'])

    def test_a_phase_that_is_a_task_can_be_opened_from_its_row(self):
        opens = _Tags(self.month).of_class('gx-open')
        self.assertEqual([(o['data-detail'], o['aria-label']) for o in opens], [('par', 'Open Design')])

    # ---- steps and bars -------------------------------------------------------------------------
    def test_a_bar_sits_on_its_start_day_and_is_as_wide_as_its_days(self):
        self.assertEqual([(bar(self.month, i)['data-l'], bar(self.month, i)['data-w']) for i in ('a', 'b', 'c', 'k1', 'k2')],
                         [('0', '240'), ('336', '240'), ('432', '288'), ('48', '96'), ('144', '288')])

    def test_a_bar_names_its_step_status_and_progress(self):
        b = bar(self.month, 'b')
        self.assertEqual(b['aria-label'], 'Beta · In Progress · 40%')
        self.assertEqual(b['title'], b['aria-label'])
        self.assertEqual((b['role'], b['tabindex'], b['class']), ('button', '0', 'gx-bar gx-s-progress'))
        row = self.month.split('data-bar="b"', 1)[1].split('</div>', 1)[0]
        self.assertIn('<i class="gx-fill" data-pc="40"></i>', row)
        self.assertIn('<span class="gx-bar-name">Beta</span><span class="gx-bar-pct">40%</span>', row)
        self.assertIn('<span class="gx-avatar" title="Olive Owner" role="img" aria-label="Owner: Olive Owner">OO</span>', row)

    def test_a_bar_that_starts_before_or_ends_after_the_period_is_cut_and_loses_that_grip(self):
        late, long = bar(self.month, 'late'), bar(self.month, 'long')
        self.assertEqual((late['data-l'], late['data-w'], late['class']), ('0', '96', 'gx-bar gx-s-risk cut-start'))
        self.assertEqual((long['data-l'], long['data-w'], long['class']), ('1296', '144', 'gx-bar gx-s-queued cut-end'))
        grips = lambda i: re.findall(r'data-edge="(\w+)"', self.month.split('data-bar="%s"' % i, 1)[1].split('</div>', 1)[0])
        self.assertEqual((grips('late'), grips('long'), grips('b')), (['end'], ['start'], ['start', 'end']))

    def test_a_milestone_is_a_flag_centred_on_its_day(self):
        m = bar(self.month, 'm')
        self.assertEqual((m['class'], m['data-l'], m['data-w']), ('gx-ms gx-s-queued', '922', '28'))   # day 20: 19 * 48 + (48 - 28) / 2
        self.assertIn('<span class="gx-ms-label">Launch</span>', self.month)
        self.assertEqual(text_of(self.month, 'data-len', 'm'), '—')
        self.assertEqual(text_of(self.month, 'data-dates', 'm'), 'Jun 20')

    def test_an_undated_step_keeps_its_row_and_has_no_bar(self):
        self.assertIn('data-timeline-task="und"', self.month)
        self.assertEqual(_Tags(self.month).having('data-bar', 'und'), [])
        self.assertEqual((text_of(self.month, 'data-dates', 'und'), text_of(self.month, 'data-len', 'und')), ('—', '—'))
        self.assertIn('<span class="gx-avatar gx-col-owner" title="Unassigned" role="img" aria-label="Owner: Unassigned">–</span>', self.month)

    def test_the_pane_row_shows_the_owner_the_status_the_dates_and_the_length(self):
        row = self.month.split('data-timeline-task="b"', 1)[1].split('</div>', 1)[0]
        self.assertIn('<span class="gx-avatar gx-col-owner" title="Olive Owner" role="img" aria-label="Owner: Olive Owner">OO</span>', row)
        self.assertIn('<span class="gx-badge gx-col-status" title="In progress"><i class="gx-dot"></i>In Progress</span>', row)
        self.assertIn('<span class="gx-col-dates" data-dates="b">Jun 8 – 12</span><span class="gx-col-len" data-len="b">5d</span>', row)
        self.assertIn('<span class="sr-only"> · In Progress</span>', row)

    def test_a_step_that_waits_for_others_shows_how_many(self):
        self.assertIn('<span class="gx-links" title="Depends on 1 step">', self.month.split('data-timeline-task="b"', 1)[1].split('</div>', 1)[0])
        self.assertIn('<span class="gx-links" title="Depends on 2 steps">', self.month.split('data-timeline-task="c"', 1)[1].split('</div>', 1)[0])
        self.assertNotIn('gx-links', self.month.split('data-timeline-task="a"', 1)[1].split('</div>', 1)[0])
        # The count is spoken as words; the bare number is for the eye only.
        row = self.month.split('data-timeline-task="c"', 1)[1].split('</div>', 1)[0]
        self.assertIn('<span aria-hidden="true">2</span><span class="sr-only"> · depends on 2 steps</span>', row)

    def test_a_title_is_escaped_everywhere_it_is_written(self):
        self.assertNotIn('<b>', self.month)
        self.assertIn('Gamma &lt;b&gt;', self.month)
        self.assertEqual(bar(self.month, 'c')['aria-label'], 'Gamma <b> · Blocked · 0%')   # the parser decodes the escaped attribute

    # ---- the five statuses ----------------------------------------------------------------------
    def test_astras_statuses_fold_into_the_five_colours_of_the_block(self):
        s = self.out['status']
        self.assertEqual((s['completed'], s['completedBlocked']), ('completed', 'completed'))
        self.assertEqual((s['blocked'], s['hold'], s['blockedOverdue']), ('blocked', 'blocked', 'blocked'))
        self.assertEqual((s['cancelled'], s['abandoned']), ('queued', 'queued'))
        self.assertEqual((s['overdue'], s['delayed']), ('risk', 'risk'))
        self.assertEqual(s['progress'], ['progress'] * 4)
        self.assertEqual(s['queued'], ['queued', 'queued'])

    def test_the_dates_the_length_the_progress_and_the_phase_code(self):
        u = self.out['units']
        self.assertEqual(u['span'], [{'s': '2026-06-01', 'e': '2026-06-05'}, {'s': '2026-06-05', 'e': '2026-06-05'},
                                     {'s': '2026-06-01', 'e': '2026-06-01'}, None, {'s': '2026-06-09', 'e': '2026-06-09'},
                                     {'s': '2026-06-05', 'e': '2026-06-05'}, {'s': '2026-06-01', 'e': '2026-06-01'}])
        self.assertEqual(u['len'], ['5d', '1d', '—', '—', '365d'])
        self.assertEqual(u['dates'], ['Jun 3 – 7', 'Jun 28 – Jul 2', 'Jun 5', '—', 'Dec 30 – Jan 2'])
        self.assertEqual(u['progress'], [100, 40, 100, 0, 0, 0])
        self.assertEqual(u['code'], ['RP', 'RAUC', 'ALP', 'Q3', 'PH', 'RDO', 'PH'])

    # ---- the week view --------------------------------------------------------------------------
    def test_the_week_view_shows_monday_to_sunday_of_todays_week(self):
        w = self.out['week']
        self.assertEqual(w['tool']['title'], 'Week of Jun 8, 2026')
        self.assertEqual(w['ds'], {'pane': 'lg', 'mode': 'week', 'day': 88})   # (1180 - 560) / 7, rounded down
        self.assertEqual(w['props']['--gx-days'], '7')
        self.assertEqual(re.findall(r'<span class="gx-day[^"]*"[^>]*><i>(\w+)</i> (?:<b class="gx-today-pill">)?(\d+)', self.week),
                         [('Mon', '8'), ('Tue', '9'), ('Wed', '10'), ('Thu', '11'), ('Fri', '12'), ('Sat', '13'), ('Sun', '14')])
        self.assertEqual(re.findall(r'<span class="gx-week" data-w="(\d+)"><span>([^<]*)</span>', self.week), [('616', 'W24 · Jun 8 – 14')])

    def test_the_week_view_cuts_bars_to_the_week(self):
        b, c = bar(self.week, 'b'), bar(self.week, 'c')
        self.assertEqual((b['data-l'], b['data-w'], b['class']), ('0', '440', 'gx-bar gx-s-progress'))
        self.assertEqual((c['data-l'], c['data-w'], c['class']), ('176', '440', 'gx-bar gx-s-blocked cut-end'))
        self.assertEqual(_Tags(self.week).having('data-bar', 'a'), [])     # Jun 1 to 5 is not in the week: the row stays, the bar does not
        self.assertIn('data-timeline-task="a"', self.week)

    def test_a_week_day_never_gets_narrower_than_48_pixels(self):
        self.assertEqual(self.out['weekNarrow']['ds'], {'pane': 'md', 'mode': 'week', 'day': 58})

    def test_the_period_select_saves_week_or_month_and_nothing_else(self):
        self.assertEqual(self.out['selectWeek'], {'stored': 'week', 'mode': 'week'})
        self.assertEqual(self.out['selectBogus'], {'stored': 'month', 'mode': 'month'})
        self.assertEqual(self.out['storedBogus'], 'month')

    # ---- zoom -----------------------------------------------------------------------------------
    def test_zoom_steps_through_five_day_widths_and_stops_at_each_end(self):
        self.assertEqual([z[:3] for z in self.out['zoom']],
                         [['in', 64, 2], ['in', 88, 3], ['in', 120, 4], ['in', 120, 4],
                          ['out', 88, 3], ['out', 64, 2], ['out', 48, 1], ['out', 32, 0], ['out', 32, 0]])
        self.assertEqual(self.out['zoomMiss'], 32)

    def test_the_zoom_button_at_an_end_is_disabled(self):
        flags = [(z[1], z[3], z[4]) for z in self.out['zoom']]
        self.assertIn((120, True, False), flags)
        self.assertIn((32, False, True), flags)
        self.assertIn((64, False, False), flags)
        m = self.out['month']['tool']
        self.assertEqual((m['inOff'], m['outOff']), (False, False))

    def test_zoom_is_off_in_the_week_view(self):
        w = self.out['week']['tool']
        self.assertEqual((w['inOff'], w['outOff']), (True, True))

    def test_a_zoom_change_is_announced(self):
        self.assertEqual(self.out['zoomSaid'], 'Day width 32 pixels.')

    def test_a_stored_zoom_that_is_not_one_of_the_steps_falls_back_to_the_default(self):
        self.assertEqual(self.out['zoomStored'], {'0': 32, '4': 120, '2': 48, '7': 48, '-1': 48, '1.5': 48, 'null': 48})

    # ---- who may drag and add -------------------------------------------------------------------
    def test_only_open_dated_bars_of_a_project_the_user_manages_can_be_dragged(self):
        self.assertEqual(sorted(a['data-drag'] for a in _Tags(self.month).having('data-drag')), ['b', 'c', 'k2', 'late', 'long', 'm'])
        self.assertNotIn('data-drag', self.out['viewer']['html'])
        self.assertNotIn('gx-grip', self.out['viewer']['html'])
        self.assertEqual(self.out['two']['drag'], ['a'])
        self.assertFalse(self.out['phone'])

    def test_new_step_shows_only_to_someone_who_can_add_a_task_to_an_open_project(self):
        self.assertFalse(self.out['month']['tool']['newHidden'])
        self.assertTrue(self.out['viewer']['tool']['newHidden'])
        self.assertFalse(self.out['appOwner']['tool']['newHidden'])
        self.assertTrue(self.out['closedProject']['tool']['newHidden'])

    # ---- the Filter popover ---------------------------------------------------------------------
    def test_the_popover_lists_the_five_statuses_and_the_owners_with_counts(self):
        f = self.out['month']['filter']
        self.assertEqual(re.findall(r'data-fstatus="(\w+)" checked><i class="gx-dot gx-s-\w+"></i><span class="gx-pop-label">([^<]*)</span><span class="gx-count">(\d+)</span>', f),
                         [('completed', 'Completed', '2'), ('progress', 'In Progress', '2'), ('risk', 'At Risk', '1'), ('blocked', 'Blocked', '1'), ('queued', 'Queued', '3')])
        self.assertEqual(re.findall(r'data-fowner="([^"]*)" checked><span class="gx-avatar">[^<]*</span><span class="gx-pop-label">([^<]*)</span><span class="gx-count">(\d+)</span>', f),
                         [('u2', 'Mo Member', '1'), ('u1', 'Olive Owner', '7'), ('', 'Unassigned', '1')])

    def test_owners_are_listed_by_name_with_unassigned_last(self):
        self.assertEqual(self.out['ownerOrder'], ['u3', 'u9', ''])     # "Unassigned" sorts before "Zed" by name, yet comes last

    def test_unticking_a_status_hides_its_steps_and_marks_the_button(self):
        f = self.out['filter']
        self.assertEqual(len(f['all']['rows']), 9)
        self.assertFalse(f['all']['on'])
        self.assertEqual(f['all']['label'], 'Filter')
        self.assertEqual(sorted(set(f['all']['rows']) - set(f['noCompleted']['rows'])), ['a', 'k1'])
        self.assertTrue(f['noCompleted']['on'])
        self.assertEqual(f['noCompleted']['label'], 'Filter (some steps are hidden)')
        self.assertRegex(f['boxes'], r'data-fstatus="completed"><i')          # the box stays unticked after the redraw
        self.assertRegex(f['boxes'], r'data-fstatus="progress" checked>')

    def test_a_phase_with_no_step_left_is_hidden_and_the_totals_do_not_change(self):
        f = self.out['filter']
        self.assertEqual(f['noCompleted']['phases'], ['p:pr1', 't:par'])
        self.assertEqual(f['noDesign']['phases'], ['p:pr1'])                    # k1 is completed and k2 in progress: nothing of "Design" is left
        self.assertEqual(f['noDesign']['stat'], f['all']['stat'])
        self.assertEqual(f['back'], f['all'])

    def test_an_arrow_is_dropped_when_one_of_its_ends_is_hidden(self):
        f = self.out['filter']
        self.assertEqual((f['all']['paths'], f['noCompleted']['paths'], f['noMo']['paths']), (3, 1, 1))   # a→b, b→c, a→c

    def test_unticking_an_owner_hides_that_persons_steps(self):
        f = self.out['filter']
        self.assertEqual(sorted(set(f['all']['rows']) - set(f['noMo']['rows'])), ['c'])
        self.assertEqual(sorted(set(f['noMo']['rows']) - set(f['noUnassigned']['rows'])), ['und'])
        self.assertEqual(f['stray'], f['noUnassigned'])

    def test_hiding_everything_says_so_and_keeps_the_header(self):
        f = self.out['filter']
        self.assertEqual((f['none']['rows'], f['none']['phases']), ([], []))
        self.assertIn('<div class="gx-none">No steps match the filter.</div>', f['noneHtml'])
        self.assertIn('class="gx-pane-head"', f['noneHtml'])

    def test_another_page_starts_with_every_filter_box_ticked(self):
        self.assertEqual(self.out['scopeReset'], {'on': False, 'hidden': 0})

    def test_a_redraw_gives_focus_back_to_the_box_in_the_popover_that_had_it(self):
        self.assertEqual(self.out['popFocus'], ['[data-fowner="u2"]'])
        self.assertEqual(self.out['popFocusStatus'], ['[data-fstatus="risk"]'])
        self.assertEqual(self.out['popFocusOther'], [])
        self.assertEqual(self.out['popFocusOutside'], [])     # focus elsewhere on the page is left alone

    def test_the_filter_button_opens_and_closes_the_popover(self):
        self.assertEqual(self.out['pop'], [False, 'true', True, 'false'])

    # ---- the Schedule table and the empty state --------------------------------------------------
    def test_the_schedule_table_replaces_the_chart_and_hides_the_chart_only_controls(self):
        t = self.out['table']
        self.assertEqual((t['ganttHidden'], t['tableHidden'], t['hasTable']), (True, False, True))
        tool = t['tool']
        self.assertEqual(tool['title'], 'Schedule')
        self.assertEqual((tool['navHidden'], tool['todayHidden'], tool['periodHidden'], tool['filterHidden'], tool['zoomHidden']), (True,) * 5)
        m = self.out['month']['tool']
        self.assertEqual((m['navHidden'], m['todayHidden'], m['periodHidden'], m['filterHidden'], m['zoomHidden']), (False,) * 5)

    def test_no_tasks_says_so_instead_of_drawing_an_empty_grid(self):
        e = self.out['empty']
        self.assertIn('No tasks match these filters.', e['html'])
        self.assertNotIn('gx-inner', e['html'])
        self.assertIn('No steps yet.', e['filter'])

    def test_each_project_is_its_own_phase_in_the_order_of_the_project_list(self):
        self.assertEqual(self.out['two']['phases'], ['p:pr1', 'p:pr2'])
        self.assertEqual(self.out['two']['rows'], ['a', 'x'])


class GanttChartCssTests(unittest.TestCase):
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    html = (STATIC / 'index.html').read_text(encoding='utf-8')

    def rule(self, selector):
        found = re.search(r'(?m)^%s \{([^}]*)\}' % re.escape(selector), self.css)
        self.assertIsNotNone(found, selector)
        return found.group(1)

    def test_the_chart_scrolls_inside_its_card_in_both_directions(self):
        rule = self.rule('#gantt')
        self.assertIn('overflow: auto', rule)
        self.assertIn('position: relative', rule)
        self.assertIn('max-height:', rule)

    def test_the_pinned_pane_never_covers_the_apps_own_navigation(self):
        # The pane (z-index 30) is pinned inside the chart; without its own stacking context it drew over the
        # phone's bottom navigation (z-index 20).
        self.assertIn('isolation: isolate', self.rule('#gantt'))
        rail = int(re.search(r'(?m)^\.rail \{[^}]*z-index: (\d+)', self.css).group(1))
        zoom = int(re.search(r'z-index: (\d+)', self.rule('.gx-zoom')).group(1))
        self.assertLess(zoom, rail)      # the zoom buttons float over the chart, under the navigation

    def test_the_step_pane_stays_put_while_the_days_scroll_sideways(self):
        pane = self.rule('.gx-pane')
        self.assertIn('position: sticky', pane)
        self.assertIn('left: 0', pane)
        self.assertIn('width: var(--gx-pane)', pane)
        self.assertIn('background: var(--gx-bg)', pane)

    def test_both_headers_stay_at_the_top_while_the_rows_scroll(self):
        for selector in ('.gx-pane-head', '.gx-time-head'):
            rule = self.rule(selector)
            self.assertIn('position: sticky', rule, selector)
            self.assertIn('top: 0', rule, selector)

    def test_a_row_is_48_pixels_tall_like_the_arrow_geometry_assumes(self):
        self.assertIn('height: 48px', self.rule('.gx-row'))
        self.assertIn('const GX_DAY=86400000,GX_ROW=48,', (STATIC / 'app.js').read_text(encoding='utf-8'))

    def test_a_day_cell_takes_its_width_from_the_zoom_variable(self):
        self.assertIn('var(--gx-day)', self.rule('.gx-day'))
        self.assertIn('var(--gx-day)', self.rule('.gx-col'))

    def test_each_status_sets_one_colour_variable_from_a_root_token(self):
        for status, token in (('completed', '--gx-green'), ('progress', '--gx-sky'), ('risk', '--gx-amber'),
                              ('blocked', '--gx-destructive'), ('queued', '--gx-zinc')):
            self.assertRegex(self.css, r'\.gx-s-%s \{ --gx-c: var\(%s\); \}' % (status, token))
        root = self.css[self.css.index(':root {'):self.css.index('}', self.css.index(':root {'))]
        for token in ('--gx-bg', '--gx-fg', '--gx-muted', '--gx-muted-fg', '--gx-border', '--gx-primary', '--gx-primary-fg', '--gx-ring',
                      '--gx-destructive', '--gx-green', '--gx-sky', '--gx-amber', '--gx-zinc'):
            self.assertIn(token + ':', root)

    def test_secondary_text_reaches_4_5_to_1_on_the_card_and_on_the_muted_rows(self):
        # The neutrals are greys (chroma 0), so relative luminance is the cube of the OKLCH lightness.
        root = self.css[self.css.index(':root {'):self.css.index('}', self.css.index(':root {'))]
        grey = lambda name: float(re.search(r'%s: oklch\(([\d.]+) 0 0\)' % name, root).group(1)) ** 3
        ratio = lambda fg, bg: (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
        for fg in ('--gx-muted-fg', '--gx-fg'):
            for bg in ('--gx-bg', '--gx-muted'):
                self.assertGreaterEqual(ratio(grey(fg), grey(bg)), 4.5, (fg, bg))
        self.assertGreaterEqual(ratio(grey('--gx-primary-fg'), grey('--gx-primary')), 4.5)

    def test_a_draggable_bar_shows_the_grab_cursor_and_its_grips_resize(self):
        self.assertIn('cursor: grab', self.rule('.gx-bar[data-drag], .gx-ms[data-drag]'))
        self.assertIn('cursor: ew-resize', self.rule('.gx-grip'))
        self.assertRegex(self.css, r'\.gx-bar\.is-dragging[^{]*\{[^}]*cursor: grabbing')

    def test_every_focus_ring_in_the_chart_is_the_apps_focus_colour_and_reaches_3_to_1(self):
        rules = [(sel, body) for sel, body in re.findall(r'(?m)^([^{}\n]*:focus-visible[^{}\n]*) \{([^}]*)\}', self.css) if 'gx-' in sel]
        ringed = [sel for sel, body in rules if 'box-shadow' in body or 'outline: 0' in body]
        for selector in ('.gx-bar:focus-visible', '.gx-name:focus-visible', '.gx-phase-toggle:focus-visible', '.gx-btn:focus-visible',
                         '.gx-switch input:focus-visible + .gx-switch-track', '.gx-sheet-foot button:focus-visible'):
            self.assertTrue(any(selector in sel for sel in ringed), selector)
        for sel, body in rules:
            if 'box-shadow' in body or 'outline: 0' in body:
                self.assertIn('0 0 0 4px var(--focus)', body, sel)
        self.assertNotIn('var(--gx-ring) 50%', self.css)
        focus = re.search(r'--focus: (#[0-9a-fA-F]{6})', self.css).group(1)
        lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        lum = 0.2126 * lin(int(focus[1:3], 16) / 255) + 0.7152 * lin(int(focus[3:5], 16) / 255) + 0.0722 * lin(int(focus[5:7], 16) / 255)
        for background in (1.0, 0.97 ** 3):             # white, and --gx-muted (a grey: luminance is L cubed)
            self.assertGreaterEqual((background + 0.05) / (lum + 0.05), 3.0)

    def test_the_toolbar_has_the_controls_of_the_block_and_astras_own(self):
        for needle in ('id="gantt-title"', 'id="gantt-prev"', 'id="gantt-next"', 'id="gantt-today"', 'id="gantt-period"',
                       'id="gantt-deps"', 'id="gantt-filter-btn"', 'id="gantt-filter"', 'id="gantt-new-step"',
                       'id="gantt-zoom"', 'data-zoom="in"', 'data-zoom="out"', 'id="view-table"', 'id="gantt-plan"', 'id="gantt-live"'):
            self.assertIn(needle, self.html)
        self.assertRegex(self.html, r'<select[^>]*id="gantt-period"[^>]*>\s*<option value="week">Week</option>\s*<option value="month" selected>Month</option>')
        self.assertRegex(self.html, r'<button[^>]*id="gantt-prev"[^>]*aria-label="Previous period"')
        self.assertRegex(self.html, r'<button[^>]*id="gantt-next"[^>]*aria-label="Next period"')
        self.assertRegex(self.html, r'<button[^>]*data-zoom="in"[^>]*aria-label="Zoom in"')
        self.assertRegex(self.html, r'<button[^>]*data-zoom="out"[^>]*aria-label="Zoom out"')

    def test_the_new_step_button_starts_hidden_until_the_user_is_known_to_manage_a_project(self):
        self.assertRegex(self.html, r'<button[^>]*id="gantt-new-step"[^>]*hidden')

    def test_the_live_region_announces_politely(self):
        self.assertRegex(self.html, r'<div[^>]*id="gantt-live"[^>]*aria-live="polite"')

    def test_the_old_chart_is_gone_from_the_stylesheet(self):
        for old in ('.gantt-row', '.gantt-head', '.axis-tick', '.bar.track', '.step-more-list', '.proj-flag', '.today-flag', '.dep-layer', '#step-tip'):
            self.assertNotIn(old, self.css, old)


if __name__ == '__main__':
    unittest.main()
