"""Behaviour tests for the zoomable Gantt: the scale, the two-tier header, the scroll, the milestone
diamond and the zoom buttons. Node runs the real src/astra/static/app.js against the DOM stub that
tests/test_frontend_gaps_views.py already uses, so each test fails if the behaviour is removed.

Why it exists: a 14-month plan was squeezed into one window, with 65 weekly labels drawn over each
other. Asana and monday keep a fixed pixels-per-day scale per zoom level and scroll sideways.
"""
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path

from test_frontend_gaps_views import DRIVER, run_probe   # names only: no test class is imported
from test_web import STATIC


PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
  const D=86400000;
  const choose=(c,days,avail)=>{storage.get=(k,f)=>k==="astra.gantt.zoom"?c:f;return ganttScale(days,avail)};
  out.scale={
    autoShort:choose("auto",30,777),autoLong:choose("auto",432,777),week:choose("week",432,777),
    month:choose("month",432,777),quarter:choose("quarter",432,777),fit:choose("fit",432,777),
    monthShortPlan:choose("month",20,777),bogus:choose("zzz",432,777)};
  // The Private plan of the workbook: Jun 28 2026 to Sep 3 2027 (432 days with the 3-day padding).
  const lo=Date.UTC(2026,5,28),hi=Date.UTC(2027,8,3),span=hi-lo;
  out.range={days:span/D};
  out.axis={};
  for(const z of ["fit","week","month","quarter"]){const sc=choose(z,span/D,777);out.axis[z]={px:sc.px,ppd:sc.ppd,scroll:sc.scroll,html:ganttAxis(lo,hi,span,sc)}}
  // The Charter plan is 26 months: Jun 28 2026 to Sep 3 2028.
  const hi2=Date.UTC(2028,8,3),span2=hi2-lo;
  out.charter={};
  for(const z of ["fit","month"]){const sc=choose(z,span2/D,777);out.charter[z]={px:sc.px,ppd:sc.ppd,html:ganttAxis(lo,hi2,span2,sc)}}

  // applyGanttScale: CSS variables, gridlines, Today position and the pressed zoom button.
  const g=document.querySelector("#gantt"),props={};
  g.style={setProperty:(k,v)=>{props[k]=v},removeProperty:k=>{delete props[k]}};
  document.querySelector("#gantt-host").innerHTML='<button data-zoom="fit"></button><button data-zoom="week"></button><button data-zoom="month"></button><button data-zoom="quarter"></button>';
  const pressed=()=>document.querySelectorAll("[data-zoom]").filter(b=>b.getAttribute("aria-pressed")==="true").map(b=>b.dataset.zoom);
  const snap=()=>({props:{...props},noGrid:g.classList.contains("no-grid"),todayPx:g.dataset.todayPx,pressed:pressed()});
  applyGanttScale(g,choose("month",span/D,777),lo,20);out.applyMonth=snap();
  for(const k of Object.keys(props))delete props[k];
  applyGanttScale(g,choose("fit",span/D,777),lo,null);out.applyFit=snap();
  applyGanttScale(g,choose("week",span/D,777),lo,50);out.applyWeek=snap();

  // ganttScrollToToday: Today lands a quarter of the way into the visible timeline; no Today means the start.
  g.clientWidth=1247;g.dataset.todayPx="660";g.scrollLeft=0;ganttScrollToToday(false);out.scrollToday=g.scrollLeft;
  g.dataset.todayPx="100";ganttScrollToToday(false);out.scrollNearStart=g.scrollLeft;
  g.dataset.todayPx="";g.scrollLeft=500;ganttScrollToToday(false);out.scrollNoToday=g.scrollLeft;
  const smooth=[];g.scrollTo=o=>smooth.push(o);g.dataset.todayPx="660";ganttScrollToToday(true);out.scrollSmooth=smooth;

  // The zoom buttons: one delegated click handler on the group, and Today.
  const writes=[];let refreshed=0;
  storage.set=(k,v)=>writes.push([k,v]);refreshGantt=()=>{refreshed++};
  const group=H.store["#gantt-zoom"],handlers=(group&&group._l.click)||[];
  out.groupHandlers=handlers.length;
  for(const f of handlers)f({target:{closest:s=>s==="[data-zoom]"?{dataset:{zoom:"week"}}:null}});
  for(const f of handlers)f({target:{closest:()=>null}});   // a click that is not on a zoom button
  out.zoomClick={writes,refreshed};
  const today=H.store["#gantt-today"];out.todayHandler=typeof (today&&today.onclick);

  // renderGantt: two-tier header, scale, a milestone diamond and a plain bar.
  state.user={id:"u1",display_name:"Pat",global_role:"owner"};
  state.projects=[{id:"proj",name:"P",status:"active",can_manage:true}];
  state.today="2026-10-16";
  const T=o=>({project_id:"proj",project_name:"P",owner_name:"Sara",status:"in_progress",due_state:"scheduled",days_to_due:5,
    criticality:"high",is_blocked:false,is_critical_path:false,...o});
  state.tasks=[
    T({id:"a",title:"Plan the school",start_date:"2026-07-01",due_date:"2026-08-31"}),
    T({id:"m",title:"Lease executed",start_date:"2026-08-31",due_date:"2026-08-31",is_milestone:1}),
    T({id:"z",title:"Open the school",start_date:"2027-08-01",due_date:"2027-08-31"}),
  ];
  storage.get=(k,f)=>f;
  renderGantt(state.tasks);
  out.render={html:g.innerHTML,scale:g.dataset.scale,todayPx:g.dataset.todayPx,zoomAttr:g.dataset.zoom===undefined?null:g.dataset.zoom,span:+g.dataset.span};

  // Review fixes. A milestone at the very end of the chart: its name goes to the left of the diamond; a viewer who may not move tasks gets no drag handle.
  state.tasks=[...state.tasks,T({id:"h",title:"Handover",start_date:"2027-08-31",due_date:"2027-08-31",is_milestone:1})];
  renderGantt(state.tasks);out.edge=g.innerHTML;
  state.user={id:"u2",display_name:"Viewer",global_role:"member"};state.projects=[{id:"proj",name:"P",status:"active",can_manage:false,role:"viewer"}];
  renderGantt(state.tasks);out.viewerHtml=g.innerHTML;
  state.user={id:"u1",display_name:"Pat",global_role:"owner"};state.projects=[{id:"proj",name:"P",status:"active",can_manage:true}];

  // Today outside the chart says so (only when the button was pressed); reduced motion turns the smooth scroll off; the pinned width is not the grid width.
  const toasts=[];showToast=m=>toasts.push(m);
  g.dataset.todayPx="";g.scrollLeft=300;ganttScrollToToday(true);out.todayOff={toasts:[...toasts],left:g.scrollLeft};
  toasts.length=0;ganttScrollToToday(false);out.todayOffQuiet=[...toasts];
  const realMedia=globalThis.matchMedia;globalThis.matchMedia=q=>({matches:/prefers-reduced-motion/.test(q)});
  const calm=[];g.scrollTo=o=>calm.push(o);g.dataset.todayPx="660";ganttScrollToToday(true);out.calmScroll=calm;globalThis.matchMedia=realMedia;
  globalThis.getComputedStyle=()=>({getPropertyValue:n=>n==="--pin-total"?"260px":"470px"});
  out.px={side:ganttSidePx(),pin:ganttPinPx()};
  g.clientWidth=1247;g.dataset.todayPx="660";g.scrollLeft=0;ganttScrollToToday(false);out.scrollPinned=g.scrollLeft;
  delete globalThis.getComputedStyle;

  // A date that cannot be read must not break the range or hang the axis.
  const sc2=choose("month",432,777);
  out.nan={range:ganttRange([NaN,Date.UTC(2026,6,15),Date.UTC(2026,7,2)],false),allBad:ganttRange([NaN,undefined],false),single:ganttRange([NaN,Date.UTC(2026,6,15)],true),
    axisNaN:ganttAxis(NaN,hi,span,sc2),axisFlat:ganttAxis(lo,lo,0,sc2),axisBackwards:ganttAxis(hi,lo,-span,sc2),axisOk:ganttAxis(lo,hi,span,sc2).length>0,today:ganttToday()};

  // The chart measures once more when the rows bring a scrollbar that narrows it; a width that never settles still stops after one retry.
  const avails=[],origScale=ganttScale;ganttScale=(d,a)=>{avails.push(a);return origScale(d,a)};
  const widthWith=(before,after)=>{Object.defineProperty(g,"clientWidth",{configurable:true,get(){return g.innerHTML.includes("gantt-row")?after:before}})};
  g.innerHTML="";widthWith(1280,1263);renderGantt(state.tasks);out.retry=[...avails];
  avails.length=0;g.innerHTML="";widthWith(1280,1280);renderGantt(state.tasks);out.steady=[...avails];
  avails.length=0;let n=0;Object.defineProperty(g,"clientWidth",{configurable:true,get(){return 1000+(n++)*50}});renderGantt(state.tasks);out.flapping=avails.length;
  ganttScale=origScale;
  return out;
};
'''

AXIS_TICK = re.compile(r'<span class="axis-tick tier-(\d)([^"]*)" data-x="([^"]+)" data-w="([^"]+)">(.*?)</span>')


def ticks(html, tier, px):
    found = []
    for t, extra, x, w, label in AXIS_TICK.findall(html):
        if int(t) == tier:
            found.append({'x': float(x), 'w': float(w), 'px': float(w) / 100 * px, 'extra': extra.strip(),
                          'text': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', label)).strip(), 'raw': label})
    return found


class GanttScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(PROBE, static=STATIC)

    # ---- ganttScale -------------------------------------------------------------------------------
    def test_a_short_plan_fits_and_a_long_plan_switches_to_the_month_scale(self):
        s = self.out['scale']
        self.assertEqual((s['autoShort']['zoom'], s['autoShort']['scroll']), ('fit', False))
        self.assertEqual((s['autoLong']['zoom'], s['autoLong']['scroll']), ('month', True))

    def test_each_zoom_has_a_fixed_pixels_per_day_and_fit_never_scrolls(self):
        s = self.out['scale']
        self.assertAlmostEqual(s['week']['ppd'], 22, places=1)
        self.assertAlmostEqual(s['month']['ppd'], 6, places=1)
        self.assertAlmostEqual(s['quarter']['ppd'], 2, places=1)
        self.assertEqual((s['fit']['px'], s['fit']['scroll']), (777, False))

    def test_a_fixed_zoom_is_never_narrower_than_the_window(self):
        s = self.out['scale']['monthShortPlan']
        self.assertEqual(s['px'], 777)   # 20 days at 6 px would leave empty space
        self.assertFalse(s['scroll'])

    def test_an_unknown_saved_zoom_falls_back_to_auto(self):
        self.assertEqual(self.out['scale']['bogus']['choice'], 'auto')

    # ---- ganttAxis --------------------------------------------------------------------------------
    def test_every_zoom_covers_the_whole_range_with_contiguous_top_tier_ticks(self):
        for z, a in self.out['axis'].items():
            with self.subTest(zoom=z):
                top = sorted(ticks(a['html'], 1, a['px']), key=lambda t: t['x'])
                self.assertGreater(len(top), 3)
                self.assertAlmostEqual(top[0]['x'], 0, places=4)
                self.assertAlmostEqual(top[-1]['x'] + top[-1]['w'], 100, places=3)
                for before, after in zip(top, top[1:]):
                    self.assertAlmostEqual(before['x'] + before['w'], after['x'], places=4)

    def test_no_label_is_drawn_in_a_slot_too_narrow_for_it(self):
        for scope, axes in (('plan', self.out['axis']), ('charter', self.out['charter'])):
            for z, a in axes.items():
                for tier in (1, 2):
                    for t in ticks(a['html'], tier, a['px']):
                        if t['text']:
                            with self.subTest(plan=scope, zoom=z, tier=tier, label=t['text']):
                                self.assertGreaterEqual(t['px'], 14)
                                if re.search(r'\d{4}', t['text']):
                                    self.assertGreaterEqual(t['px'], 64)   # a month or quarter with its year

    def test_the_month_scale_has_month_names_over_weekly_dates(self):
        a = self.out['axis']['month']
        months = [t['text'] for t in ticks(a['html'], 1, a['px']) if t['text']]
        self.assertEqual(months[:3], ['Jul 2026', 'Aug 2026', 'Sep 2026'])
        weeks = [t for t in ticks(a['html'], 2, a['px']) if t['text']]
        self.assertGreaterEqual(len(weeks), 60)           # 62 Mondays in 432 days
        starts = [datetime.fromtimestamp(a_x / 100 * 432 * 86400 + datetime(2026, 6, 28, tzinfo=timezone.utc).timestamp(),
                                         timezone.utc).weekday() for a_x in (w['x'] for w in weeks[1:-1])]
        self.assertTrue(all(day == 0 for day in starts), 'a week tick is not on a Monday')

    def test_the_week_scale_labels_every_day_with_its_weekday_and_marks_weekends(self):
        a = self.out['axis']['week']
        days = ticks(a['html'], 2, a['px'])
        self.assertGreaterEqual(len(days), 430)
        self.assertTrue(all('<i>' in d['raw'] for d in days if d['text']))
        weekends = sum('weekend' in d['extra'] for d in days)
        self.assertAlmostEqual(weekends, 432 * 2 / 7, delta=3)

    def test_the_far_out_scale_shows_quarters_over_month_initials(self):
        a = self.out['axis']['quarter']
        quarters = [t['text'] for t in ticks(a['html'], 1, a['px']) if t['text']]
        self.assertIn('Q3 2026', quarters)
        self.assertIn('Q1 2027', quarters)
        months = [t['text'] for t in ticks(a['html'], 2, a['px']) if t['text']]
        self.assertTrue({'Jul', 'Aug', 'Sep'} <= set(months))

    def test_a_26_month_plan_fitted_into_the_window_still_reads(self):
        a = self.out['charter']['fit']
        self.assertLess(a['ppd'], 1.5)
        self.assertTrue([t for t in ticks(a['html'], 2, a['px']) if t['text']], 'no month labels under the quarters')
        self.assertEqual(len([t for t in ticks(a['html'], 1, a['px']) if t['text'].startswith('Q')]), 9)   # the 2-day Q2 2026 sliver at the start has no room for a label

    # ---- applyGanttScale and scrolling ------------------------------------------------------------
    def test_a_scrolling_scale_sets_the_timeline_width_and_week_gridlines(self):
        m = self.out['applyMonth']
        self.assertEqual(m['props']['--tl-w'], '2592px')
        self.assertEqual(m['props']['--grid-px'], '42px')   # 7 days at 6 px
        self.assertFalse(m['noGrid'])
        self.assertEqual((m['todayPx'], m['pressed']), ('518', ['month']))   # 20% of 2592

    def test_fit_removes_the_width_and_drops_the_gridlines_when_a_day_is_under_3px(self):
        f = self.out['applyFit']
        self.assertNotIn('--tl-w', f['props'])
        self.assertTrue(f['noGrid'])
        self.assertEqual((f['todayPx'], f['pressed']), ('', ['fit']))

    def test_the_week_gridline_offset_lines_up_with_the_first_monday(self):
        w = self.out['applyWeek']
        # Jun 28 2026 is a Sunday, so the first Monday is one day in: 22 px.
        self.assertEqual(w['props']['--grid-off'], '22px')
        self.assertEqual(w['props']['--grid-px'], '154px')

    def test_today_scrolls_a_quarter_into_the_visible_timeline_and_never_below_zero(self):
        self.assertAlmostEqual(self.out['scrollToday'], 660 - (1247 - 470) * .25, places=2)
        self.assertEqual(self.out['scrollNearStart'], 0)
        self.assertEqual(self.out['scrollNoToday'], 0)
        self.assertEqual(self.out['scrollSmooth'][0]['behavior'], 'smooth')

    # ---- controls ---------------------------------------------------------------------------------
    def test_a_click_on_a_zoom_button_saves_the_zoom_and_redraws_once(self):
        self.assertEqual(self.out['groupHandlers'], 1)
        self.assertEqual(self.out['zoomClick'], {'writes': [['astra.gantt.zoom', 'week']], 'refreshed': 1})

    def test_the_today_button_has_a_handler(self):
        self.assertEqual(self.out['todayHandler'], 'function')

    # ---- renderGantt ------------------------------------------------------------------------------
    def test_the_header_has_two_tiers_and_the_chart_records_its_scale(self):
        r = self.out['render']
        self.assertIn('axis two-tier', r['html'])
        self.assertIn('axis-tick tier-1', r['html'])
        self.assertIn('axis-tick tier-2', r['html'])
        self.assertEqual(r['scale'], 'month')
        self.assertNotIn('data-zoom', r['html'])
        self.assertIsNone(r['zoomAttr'], 'the chart element carries data-zoom, which the zoom buttons use')

    def test_a_milestone_is_a_diamond_on_its_due_date_with_its_name_and_a_drag_handle(self):
        html = self.out['render']['html']
        diamond = re.search(r'<button type="button" class="bar milestone [^"]*" data-detail="m"([^>]*)>', html)
        self.assertIsNotNone(diamond, 'no milestone diamond was drawn')
        self.assertIn('data-drag="m"', diamond.group(1))
        self.assertIn('Milestone: Lease executed', html)
        label = re.search(r'<span class="ms-label" data-x="([^"]+)" aria-hidden="true">Lease executed</span>', html)
        self.assertIsNotNone(label)
        self.assertAlmostEqual(float(label.group(1)), float(re.search(r'data-x="([^"]+)"', diamond.group(1)).group(1)), places=6)
        # Position: the plan bar ends at the close of Aug 31 2026, so a milestone due that day sits half a day before that edge.
        bar = re.search(r'class="bar plain [^"]*" data-detail="a"[^>]*data-x="([^"]+)" data-w="([^"]+)"', self.out['render']['html'])
        self.assertIsNotNone(bar)
        bar_end = float(bar.group(1)) + float(bar.group(2))
        self.assertAlmostEqual(float(label.group(1)), bar_end - 43200000 / self.out['render']['span'] * 100, places=4)

    def test_an_ordinary_task_stays_a_bar_not_a_diamond(self):
        html = self.out['render']['html']
        self.assertIn('class="bar plain', html)
        self.assertEqual(html.count('bar milestone'), 1)

    # ---- review fixes -----------------------------------------------------------------------------
    def test_a_milestone_at_the_end_of_the_chart_puts_its_name_to_the_left_and_hides_it_from_screen_readers(self):
        html = self.out['edge']
        self.assertRegex(html, r'<span class="ms-label edge-r" data-x="[^"]+" aria-hidden="true">Handover</span>')
        self.assertRegex(html, r'<span class="ms-label" data-x="[^"]+" aria-hidden="true">Lease executed</span>')
        self.assertIn('Milestone: Handover', html)   # the diamond itself still carries the name for assistive tech

    def test_a_viewer_who_may_not_move_tasks_gets_no_drag_handle_on_a_milestone(self):
        diamond = re.search(r'<button type="button" class="bar milestone [^"]*" data-detail="m"([^>]*)>', self.out['viewerHtml'])
        self.assertIsNotNone(diamond)
        self.assertNotIn('data-drag', diamond.group(1))

    def test_pressing_today_when_today_is_off_the_chart_says_so_and_goes_to_the_start(self):
        self.assertEqual(self.out['todayOff'], {'toasts': ['Today is outside this timeline.'], 'left': 0})
        self.assertEqual(self.out['todayOffQuiet'], [], 'the automatic scroll after a render must not show a toast')

    def test_reduced_motion_scrolls_to_today_without_animation(self):
        self.assertEqual(self.out['calmScroll'][0]['behavior'], 'auto')

    def test_today_is_placed_by_the_pinned_width_not_the_whole_name_and_meta_width(self):
        self.assertEqual(self.out['px'], {'side': 470, 'pin': 260})
        self.assertAlmostEqual(self.out['scrollPinned'], 660 - (1247 - 260) * .25, places=2)

    def test_an_unreadable_date_is_ignored_by_the_range_and_the_axis(self):
        n = self.out['nan']
        ms = lambda y, m, d: datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000
        self.assertEqual((n['range']['start'], n['range']['end']), (ms(2026, 7, 1), ms(2026, 9, 1)))
        today = datetime.fromisoformat(n['today']).replace(tzinfo=timezone.utc).timestamp() * 1000
        self.assertEqual((n['allBad']['start'], n['allBad']['end']), (today, today + 30 * 86400000))
        self.assertEqual(n['single']['start'], ms(2026, 7, 15))
        self.assertEqual((n['axisNaN'], n['axisFlat'], n['axisBackwards']), ('', '', ''))
        self.assertTrue(n['axisOk'])

    def test_the_chart_measures_again_once_when_a_scrollbar_narrows_it(self):
        self.assertEqual(self.out['retry'], [810, 793])
        self.assertEqual(self.out['steady'], [810])
        self.assertEqual(self.out['flapping'], 2, 'a width that keeps changing must stop after one retry')


class GanttZoomCssTests(unittest.TestCase):
    css = (STATIC / 'style.css').read_text(encoding='utf-8')

    def test_the_timeline_column_takes_its_width_from_the_zoom_variable(self):
        self.assertRegex(self.css, r'\.gantt-row \{[^}]*grid-template-columns: var\(--side-1\) var\(--side-2\) var\(--tl-w, minmax\(700px, 1fr\)\)')
        self.assertIn('min-width: max-content', re.search(r'\.gantt-row \{[^}]*\}', self.css).group(0))

    def test_the_name_and_meta_columns_stay_put_while_the_chart_scrolls(self):
        self.assertRegex(self.css, r'#gantt \.gantt-row > \.task-name, #gantt \.gantt-row > \.task-meta \{[^}]*position: sticky')
        self.assertRegex(self.css, r'#gantt \.gantt-row > \.task-meta \{[^}]*left: var\(--side-1\)')

    def test_a_resize_grip_sits_above_a_lane_2_step_so_a_wide_bar_can_still_be_resized(self):
        grip = int(re.search(r'\.bar-grip \{[^}]*z-index: (\d+)', self.css).group(1))
        step = int(re.search(r'\.bar\.track\.lanes-2 \.step\.lane-2 \{[^}]*z-index: (\d+)', self.css).group(1))
        self.assertGreater(grip, step)

    def test_the_header_is_tall_enough_for_flags_and_two_tiers(self):
        self.assertRegex(self.css, r'\.gantt-head \{ position: sticky; top: 0; z-index: 7; background: var\(--palette-6\); min-height: 72px;')
        self.assertRegex(self.css, r'\.axis-tick\.tier-1 \{ top: 24px;')
        self.assertRegex(self.css, r'\.axis-tick\.tier-2 \{ top: 48px;')

    def test_below_1100px_only_the_task_name_stays_pinned(self):
        block = re.search(r'@media \(max-width: 1100px\) \{(.*?)\n\}', self.css, re.S).group(1)
        self.assertRegex(block, r'#gantt \.gantt-row > \.task-meta \{[^}]*position: relative')
        self.assertRegex(self.css, r'@media \(min-width: 761px\) and \(max-width: 1100px\) \{[^}]*\n  #gantt \{ --pin-total: 260px; \}')

    def test_no_stylesheet_block_after_the_phone_rules_is_another_760px_query(self):
        # tests/test_web.py (test_toolbar_wraps_instead_of_scrolling_sideways) reads the LAST 760px block for the top bar rule.
        last = self.css[self.css.rindex('@media (max-width: 760px)'):]
        self.assertRegex(last, r'\.topbar \{[^}]*flex-wrap: wrap;')

    def test_the_phone_layout_narrows_the_sticky_columns_through_the_variables(self):
        self.assertRegex(self.css, r'#gantt \{ --side-1: 200px; --side-2: 170px; --side-total: 370px; --pin-total: 200px; \}')

    def test_the_label_of_an_end_of_chart_milestone_is_flipped_to_the_left(self):
        self.assertRegex(self.css, r'\.ms-label\.edge-r \{[^}]*translate\(-100%, -50%\)')

    def test_the_chart_keeps_room_for_its_scrollbar_so_the_width_does_not_change_with_the_rows(self):
        self.assertRegex(self.css, r'#gantt \{ position: relative; overflow: auto; scrollbar-gutter: stable;')

    def test_the_today_flag_stays_in_the_flag_row_and_does_not_cover_the_dates(self):
        flag = re.search(r'\.gantt-head \.today-flag \{([^}]*)\}', self.css).group(1)
        self.assertNotIn('bottom', flag)
        self.assertNotIn('top:', flag)


if __name__ == '__main__':
    unittest.main()
