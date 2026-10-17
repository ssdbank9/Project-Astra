"""Behaviour tests for the Gantt's range: where the chart starts and ends.

Aly's rule (2026-10-17): on the dashboard, with several projects, the chart starts on the first day of the earliest
month. Inside one project it starts on that project's first day and scrolls month by month to the end, and when a
start date changes the chart's start follows it. Node runs the real app.js (same DOM stub as test_gantt_zoom.py).
"""
import re
import unittest
from datetime import date, datetime, timezone

from test_frontend_gaps_views import run_probe   # a function only: no test class is imported
from test_web import STATIC


PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
  const g=document.querySelector("#gantt");
  g.style={setProperty(){},removeProperty(){}};
  storage.get=(k,f)=>f;
  state.user={id:"u1",display_name:"Pat",global_role:"owner"};
  state.today="2026-10-16";
  const P=(id,extra)=>({id,name:id.toUpperCase(),status:"active",can_manage:true,start_date:null,target_date:null,...extra});
  const T=o=>({project_name:"P",owner_name:"Sara",status:"in_progress",due_state:"scheduled",days_to_due:5,
    criticality:"high",is_blocked:false,is_critical_path:false,...o});
  const read=()=>({start:+g.dataset.start,span:+g.dataset.span,html:g.innerHTML,scrollLeft:g.scrollLeft});
  const set=(projects,tasks)=>{state.projects=projects;state.tasks=tasks};
  const onProject=()=>{location.hash="#/project/11111111-1111-4111-8111-111111111111/timeline"},onDashboard=()=>{location.hash="#/portfolio"};
  onProject();

  // one project
  const a=T({id:"a",project_id:"p1",start_date:"2026-07-09",due_date:"2026-08-20"});
  const b=T({id:"b",project_id:"p1",start_date:"2026-09-02",due_date:"2026-10-05"});
  set([P("p1")],[a,b]);renderGantt(state.tasks);out.single=read();

  // the earliest start date moves earlier, and the chart's start follows
  set([P("p1")],[{...a,start_date:"2026-06-03"},b]);renderGantt(state.tasks);out.movedEarlier=read();
  // and moves later
  set([P("p1")],[{...a,start_date:"2026-07-20"},b]);renderGantt(state.tasks);out.movedLater=read();

  // the agreed project start is earlier than every task
  set([P("p1",{start_date:"2026-05-15"})],[a,b]);renderGantt(state.tasks);out.agreedEarlier=read();
  // the agreed deadline is later than every task: the chart runs to it
  set([P("p1",{target_date:"2027-01-31"})],[a,b]);renderGantt(state.tasks);out.targetLater=read();
  // the scheduled start (the project's forecast) is earlier than every task
  set([P("p1",{schedule_forecasts:{Shared:{start_date:"2026-04-01",finish_date:"2026-10-05",undated_count:0}}})],[a,b]);
  renderGantt(state.tasks);out.forecastEarlier=read();

  // a one-day project still gets a readable range
  set([P("p1")],[T({id:"m",project_id:"p1",start_date:"2026-09-10",due_date:"2026-09-10"})]);renderGantt(state.tasks);out.oneDay=read();
  // no dates at all
  set([P("p1")],[T({id:"u",project_id:"p1",start_date:null,due_date:null})]);renderGantt(state.tasks);out.undated=read();

  // the dashboard: two projects, month-aligned
  onDashboard();
  const c=T({id:"c",project_id:"p2",start_date:"2027-01-12",due_date:"2027-03-18"});
  set([P("p1"),P("p2")],[a,b,c]);renderGantt(state.tasks);out.dashboard=read();
  // the dashboard filtered down to one project is still the dashboard: whole months
  set([P("p1"),P("p2")],[c]);renderGantt(state.tasks);out.filteredToOne=read();
  // a dashboard with a single project in the whole app is still the dashboard
  set([P("p1")],[a,b]);renderGantt(state.tasks);out.dashboardOneProject=read();

  // scrolling: a new project opens at the start; a refresh after an edit keeps where you were
  onProject();set([P("p1")],[a,b]);renderGantt(state.tasks);
  g.scrollLeft=640;renderGantt(state.tasks);out.refreshKeepsScroll=g.scrollLeft;
  location.hash="#/project/22222222-2222-4222-8222-222222222222/timeline";set([P("p2")],[c]);renderGantt(state.tasks);out.newProjectOpensAtStart=g.scrollLeft;

  // a flag exactly at the start of the chart is anchored to the left edge, not centred on it
  onProject();set([P("p1",{start_date:"2026-07-09"})],[a,b]);renderGantt(state.tasks);out.edge=g.innerHTML;
  return out;
};
'''


def ms(day):
    y, m, d = map(int, day.split('-'))
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)


DAY = 86400000


class GanttRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(PROBE, static=STATIC)

    def assertRange(self, key, start, end):
        got = self.out[key]
        self.assertEqual(got['start'], ms(start), f'{key} starts on the wrong day')
        self.assertEqual(got['start'] + got['span'], ms(end), f'{key} ends on the wrong day')

    # ---- inside one project ----------------------------------------------------------------------
    def test_a_project_chart_starts_on_the_projects_first_day_and_ends_after_its_last(self):
        self.assertRange('single', '2026-07-09', '2026-10-06')   # the end is exclusive: Oct 5 is the last day shown

    def test_changing_the_earliest_start_date_earlier_moves_the_charts_start(self):
        self.assertRange('movedEarlier', '2026-06-03', '2026-10-06')

    def test_changing_the_earliest_start_date_later_moves_the_charts_start(self):
        self.assertRange('movedLater', '2026-07-20', '2026-10-06')

    def test_an_agreed_project_start_before_every_task_is_where_the_chart_starts(self):
        self.assertRange('agreedEarlier', '2026-05-15', '2026-10-06')

    def test_an_agreed_deadline_after_every_task_extends_the_chart_to_it(self):
        self.assertRange('targetLater', '2026-07-09', '2027-02-01')

    def test_the_scheduled_start_of_the_project_forecast_counts_too(self):
        self.assertRange('forecastEarlier', '2026-04-01', '2026-10-06')

    def test_there_is_no_padding_before_the_first_day(self):
        s = self.out['single']
        self.assertEqual(s['start'], ms('2026-07-09'))   # the old chart started 3 days earlier

    def test_a_one_day_project_still_gets_two_weeks_of_chart(self):
        self.assertEqual(self.out['oneDay']['span'], 14 * DAY)
        self.assertEqual(self.out['oneDay']['start'], ms('2026-09-10'))

    def test_a_project_with_no_dates_shows_the_next_30_days_from_today(self):
        self.assertRange('undated', '2026-10-16', '2026-11-15')

    # ---- the dashboard ---------------------------------------------------------------------------
    def test_the_dashboard_chart_starts_on_the_first_day_of_the_earliest_month(self):
        self.assertRange('dashboard', '2026-07-01', '2027-04-01')   # through the last day of March 2027

    def test_the_dashboard_range_always_covers_whole_months(self):
        d = self.out['dashboard']
        self.assertEqual(datetime.fromtimestamp(d['start'] / 1000, timezone.utc).day, 1)
        self.assertEqual(datetime.fromtimestamp((d['start'] + d['span']) / 1000, timezone.utc).day, 1)

    def test_filtering_the_dashboard_down_to_one_project_still_uses_whole_months(self):
        self.assertRange('filteredToOne', '2027-01-01', '2027-04-01')

    def test_a_dashboard_with_only_one_project_still_starts_on_the_first_of_the_month(self):
        self.assertRange('dashboardOneProject', '2026-07-01', '2026-11-01')   # not Jul 9: the page decides, not the project count

    # ---- scrolling and flags ---------------------------------------------------------------------
    def test_a_refresh_after_an_edit_keeps_the_scroll_position(self):
        self.assertEqual(self.out['refreshKeepsScroll'], 640)

    def test_opening_another_project_starts_at_the_beginning(self):
        self.assertEqual(self.out['newProjectOpensAtStart'], 0)

    def test_a_flag_at_the_start_of_the_chart_is_anchored_to_the_left_edge(self):
        html = self.out['edge']
        self.assertRegex(html, r'class="proj-flag start edge-l" data-x="0"')

    def test_a_flag_in_the_middle_is_not_given_an_edge_class(self):
        html = self.out['single']['html']
        self.assertNotIn('edge-l"', html.replace('today-flag', ''))


class GanttRangeCssTests(unittest.TestCase):
    css = (STATIC / 'style.css').read_text(encoding='utf-8')

    def test_edge_flags_stay_inside_the_chart(self):
        self.assertRegex(self.css, r'\.proj-flag\.edge-l, \.today-flag\.edge-l \{ transform: none; \}')
        self.assertRegex(self.css, r'\.proj-flag\.edge-r, \.today-flag\.edge-r \{ transform: translateX\(-100%\); \}')


if __name__ == '__main__':
    unittest.main()
