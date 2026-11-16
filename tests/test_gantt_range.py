"""Behaviour tests for the period the Gantt shows: a calendar month or a Monday to Sunday week, the
previous / next / Today buttons, the ISO week numbers of the header, and the period the chart opens on.

Node runs the real src/astra/static/app.js (same DOM stub as test_gantt_zoom.py).
"""
import re
import unittest

from test_frontend_gaps_views import run_probe   # a function only: no test class is imported
from test_gantt_zoom import SETUP                # the shared probe prelude: no test class is imported
from test_web import STATIC


PROBE = r'''
globalThis.runProbe=async function(input,H){
  const out={};
''' + SETUP + r'''
  const per=(a,m)=>{const p=gxPeriod(a,m);return [gxIso(p.start),p.days,p.title]};
  out.period={
    june:per("2026-06-10","month"),feb:per("2026-02-15","month"),leapFeb:per("2028-02-29","month"),dec:per("2026-12-31","month"),first:per("2026-06-01","month"),
    wed:per("2026-06-10","week"),sun:per("2026-06-14","week"),mon:per("2026-06-08","week"),newYear:per("2027-01-01","week"),monthEdge:per("2026-07-01","week")};
  out.shift={
    nextMonth:gxShift("2026-06-10","month",1),prevMonth:gxShift("2026-06-10","month",-1),from31st:gxShift("2026-01-31","month",1),
    overYear:gxShift("2026-12-15","month",1),backOverYear:gxShift("2026-01-15","month",-1),
    nextWeek:gxShift("2026-06-10","week",1),prevWeek:gxShift("2026-06-10","week",-1),weekOverYear:gxShift("2026-12-30","week",1)};
  const wk=(y,m,d)=>gxWeek(Date.UTC(y,m-1,d));
  out.week={jan1_2026:wk(2026,1,1),dec28_2026:wk(2026,12,28),jan1_2027:wk(2027,1,1),jan3_2027:wk(2027,1,3),jan4_2027:wk(2027,1,4),
    dec30_2024:wk(2024,12,30),jan3_2021:wk(2021,1,3),jun8_2026:wk(2026,6,8),jun14_2026:wk(2026,6,14),jun15_2026:wk(2026,6,15)};

  // ---- the period the chart opens on ----
  const title=()=>H.store["#gantt-title"].textContent;
  const open=(tasks,o)=>{boot(tasks,o);return title()};
  out.open={
    today:open([T("a","A","2026-06-20","2026-06-25"),T("f","F","2026-09-01","2026-09-05")]),
    spansToday:open([T("a","A","2026-03-01","2026-08-25")]),
    future:open([T("f","F","2026-09-18","2026-09-25"),T("g","G","2026-11-01","2026-11-05")]),
    past:open([T("p","P","2026-01-10","2026-02-20")]),
    nearestIsPast:open([T("p","P","2026-05-01","2026-05-20"),T("f","F","2026-07-20","2026-07-25")]),
    nearestIsFuture:open([T("p","P","2026-04-01","2026-04-20"),T("f","F","2026-07-02","2026-07-25")]),
    undated:open([T("u","U",null,null)]),
    lastDay:open([T("a","A","2026-06-30","2026-07-04")]),
    firstDay:open([T("a","A","2026-05-20","2026-06-01")]),
    justBefore:open([T("a","A","2026-05-20","2026-05-31")]),
    milestone:open([T("m","M","2026-06-05","2026-08-20",{is_milestone:true})])};
  mem["astra.gantt.period"]="week";
  out.openWeek={
    today:open([T("a","A","2026-06-14","2026-06-20")]),
    nextWeek:open([T("a","A","2026-06-15","2026-06-20")]),
    lastWeek:open([T("a","A","2026-06-01","2026-06-05")])};
  delete mem["astra.gantt.period"];

  // ---- previous, next, Today ----
  const prev=H.store["#gantt-prev"],next=H.store["#gantt-next"],today=H.store["#gantt-today"];
  boot([T("a","A","2026-06-20","2026-06-25")]);
  out.nav=[title()];
  for(const b of [next,next,prev,prev,prev,today,prev,prev,prev,prev,prev,prev])  {b.onclick();out.nav.push(title())}
  today.onclick();next.onclick();out.navBars=(g.innerHTML.match(/data-bar=/g)||[]).length;out.navRows=(g.innerHTML.match(/data-timeline-task=/g)||[]).length;
  today.onclick();out.navBarsBack=(g.innerHTML.match(/data-bar=/g)||[]).length;
  // From a chart that opened on later work: the buttons step from that period, Today comes home.
  boot([T("f","F","2026-09-18","2026-09-25")]);
  out.navFar=[title()];next.onclick();out.navFar.push(title());today.onclick();out.navFar.push(title());
  mem["astra.gantt.period"]="week";boot([T("a","A","2026-06-09","2026-06-25")]);
  out.navWeek=[title()];
  for(const b of [next,next,prev,prev,prev,today]){b.onclick();out.navWeek.push(title())}
  // Changing the period keeps the day the chart is on.
  next.onclick();next.onclick();next.onclick();next.onclick();out.switch=[title()];
  H.store["#gantt-period"].onchange({target:{value:"month"}});out.switch.push(title());
  delete mem["astra.gantt.period"];

  // ---- the chosen period is kept until the page shows other projects ----
  const two=[{id:"pr1",name:"Release Plan",status:"active",can_manage:true},{id:"pr2",name:"Second",status:"active",can_manage:true}];
  boot([T("a","A","2026-06-20","2026-06-25")],{projects:two});next.onclick();
  out.keep=[title()];
  state.tasks=[T("a","A","2026-06-20","2026-06-25"),T("b","B","2026-06-21","2026-06-22")];renderGantt(state.tasks);out.keep.push(title());   // same project: kept
  g.scrollLeft=300;
  state.tasks=[T("x","X","2026-10-05","2026-10-09",{project_id:"pr2",project_name:"Second"})];renderGantt(state.tasks);out.keep.push(title());out.scrollAfterScope=g.scrollLeft;
  g.scrollLeft=300;renderGantt(state.tasks);out.scrollSameScope=g.scrollLeft;

  // ---- a project page uses the project's own today ----
  boot([T("a","A","2026-03-01","2026-03-09")]);state.ganttDay={today:"2026-03-05",timezone:"Asia/Karachi"};gx.anchor=null;gx.scope=null;renderGantt(state.tasks);
  out.projectDay={title:title(),pill:(/gx-today-pill">(\d+)</.exec(g.innerHTML)||[])[1]};
  next.onclick();today.onclick();out.projectDay.afterToday=title();
  state.ganttDay=null;

  // ---- the header over a year boundary ----
  const weeks=()=>[...g.innerHTML.matchAll(/<span class="gx-week" data-w="(\d+)"><span>([^<]*)<\/span>/g)].map(m=>[+m[1],m[2]]);
  boot([T("a","A","2026-12-20","2027-01-08")],{today:"2026-12-30"});out.december=weeks();
  next.onclick();out.january={title:title(),weeks:weeks(),pill:/gx-today-pill/.test(g.innerHTML),bar:(/data-bar="a"[^>]*data-l="(\d+)" data-w="(\d+)"/.exec(g.innerHTML)||[]).slice(1)};
  return out;
};
'''


class GanttPeriodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(PROBE, static=STATIC)

    # ---- gxPeriod -------------------------------------------------------------------------------
    def test_a_month_runs_from_its_first_day_to_its_last(self):
        p = self.out['period']
        self.assertEqual(p['june'], ['2026-06-01', 30, 'June 2026'])
        self.assertEqual(p['first'], ['2026-06-01', 30, 'June 2026'])
        self.assertEqual(p['feb'], ['2026-02-01', 28, 'February 2026'])
        self.assertEqual(p['leapFeb'], ['2028-02-01', 29, 'February 2028'])
        self.assertEqual(p['dec'], ['2026-12-01', 31, 'December 2026'])

    def test_a_week_runs_from_monday_to_sunday(self):
        p = self.out['period']
        for day in ('wed', 'sun', 'mon'):
            self.assertEqual(p[day], ['2026-06-08', 7, 'Week of Jun 8, 2026'], day)

    def test_a_week_is_named_after_its_monday_even_across_a_month_or_a_year(self):
        p = self.out['period']
        self.assertEqual(p['newYear'], ['2026-12-28', 7, 'Week of Dec 28, 2026'])
        self.assertEqual(p['monthEdge'], ['2026-06-29', 7, 'Week of Jun 29, 2026'])

    # ---- gxShift --------------------------------------------------------------------------------
    def test_a_month_step_lands_on_the_first_of_the_neighbouring_month(self):
        s = self.out['shift']
        self.assertEqual((s['nextMonth'], s['prevMonth']), ('2026-07-01', '2026-05-01'))
        self.assertEqual(s['from31st'], '2026-02-01')     # not March: a 31st has no February twin
        self.assertEqual((s['overYear'], s['backOverYear']), ('2027-01-01', '2025-12-01'))

    def test_a_week_step_is_seven_days(self):
        s = self.out['shift']
        self.assertEqual((s['nextWeek'], s['prevWeek'], s['weekOverYear']), ('2026-06-17', '2026-06-03', '2027-01-06'))

    # ---- gxWeek ---------------------------------------------------------------------------------
    def test_week_numbers_follow_iso_8601(self):
        w = self.out['week']
        self.assertEqual((w['jun8_2026'], w['jun14_2026'], w['jun15_2026']), (24, 24, 25))
        self.assertEqual(w['jan1_2026'], 1)                               # a Thursday: week 1
        self.assertEqual((w['dec28_2026'], w['jan1_2027'], w['jan3_2027']), (53, 53, 53))   # 2026 has 53 weeks
        self.assertEqual(w['jan4_2027'], 1)
        self.assertEqual(w['dec30_2024'], 1)                              # a Monday that already belongs to 2025
        self.assertEqual(w['jan3_2021'], 53)                              # a Sunday that still belongs to 2020

    # ---- the period the chart opens on ----------------------------------------------------------
    def test_the_chart_opens_on_today_when_any_work_falls_in_todays_period(self):
        o = self.out['open']
        self.assertEqual((o['today'], o['spansToday'], o['lastDay'], o['firstDay']), ('June 2026',) * 4)

    def test_with_no_work_in_todays_period_it_opens_on_the_nearest_dated_work(self):
        o = self.out['open']
        self.assertEqual(o['future'], 'September 2026')
        self.assertEqual(o['past'], 'February 2026')            # the end of past work is its nearest day
        self.assertEqual(o['justBefore'], 'May 2026')
        self.assertEqual(o['nearestIsPast'], 'May 2026')        # 21 days back beats 40 days ahead
        self.assertEqual(o['nearestIsFuture'], 'July 2026')     # 22 days ahead beats 51 days back

    def test_a_milestone_counts_on_its_due_date_only(self):
        self.assertEqual(self.out['open']['milestone'], 'August 2026')

    def test_with_no_dated_work_it_opens_on_today(self):
        self.assertEqual(self.out['open']['undated'], 'June 2026')

    def test_the_week_view_opens_the_same_way(self):
        o = self.out['openWeek']
        self.assertEqual(o['today'], 'Week of Jun 8, 2026')     # Sunday Jun 14 is in today's week
        self.assertEqual(o['nextWeek'], 'Week of Jun 15, 2026')
        self.assertEqual(o['lastWeek'], 'Week of Jun 1, 2026')

    # ---- previous, next, Today ------------------------------------------------------------------
    def test_next_and_previous_step_one_month_and_today_comes_back(self):
        self.assertEqual(self.out['nav'], ['June 2026', 'July 2026', 'August 2026', 'July 2026', 'June 2026', 'May 2026', 'June 2026',
                                           'May 2026', 'April 2026', 'March 2026', 'February 2026', 'January 2026', 'December 2025'])

    def test_a_period_with_no_work_keeps_the_rows_and_draws_no_bar(self):
        self.assertEqual((self.out['navBars'], self.out['navRows'], self.out['navBarsBack']), (0, 1, 1))

    def test_the_buttons_step_from_the_period_the_chart_opened_on(self):
        self.assertEqual(self.out['navFar'], ['September 2026', 'October 2026', 'June 2026'])

    def test_in_the_week_view_the_buttons_step_one_week(self):
        self.assertEqual(self.out['navWeek'], ['Week of Jun 8, 2026', 'Week of Jun 15, 2026', 'Week of Jun 22, 2026', 'Week of Jun 15, 2026',
                                               'Week of Jun 8, 2026', 'Week of Jun 1, 2026', 'Week of Jun 8, 2026'])

    def test_switching_between_week_and_month_keeps_the_day_the_chart_is_on(self):
        self.assertEqual(self.out['switch'], ['Week of Jul 6, 2026', 'July 2026'])

    def test_the_chosen_period_is_kept_across_redraws_of_the_same_projects(self):
        self.assertEqual(self.out['keep'][:2], ['July 2026', 'July 2026'])
        self.assertEqual(self.out['scrollSameScope'], 300)

    def test_other_projects_start_at_their_own_work_and_at_the_left_edge(self):
        self.assertEqual(self.out['keep'][2], 'October 2026')
        self.assertEqual(self.out['scrollAfterScope'], 0)

    def test_a_project_page_uses_the_projects_own_today(self):
        self.assertEqual(self.out['projectDay'], {'title': 'March 2026', 'pill': '5', 'afterToday': 'March 2026'})

    # ---- the header over a year boundary --------------------------------------------------------
    def test_december_ends_in_week_53_and_january_starts_in_it(self):
        self.assertEqual(self.out['december'], [[288, 'W49 · Dec 1 – 6'], [336, 'W50 · Dec 7 – 13'], [336, 'W51 · Dec 14 – 20'],
                                                [336, 'W52 · Dec 21 – 27'], [192, 'W53 · Dec 28 – 31']])
        j = self.out['january']
        self.assertEqual(j['title'], 'January 2027')
        self.assertEqual(j['weeks'][:2], [[144, 'W53 · Jan 1 – 3'], [336, 'W1 · Jan 4 – 10']])
        self.assertEqual(sum(w for w, _ in j['weeks']), 31 * 48)

    def test_a_bar_that_began_last_month_is_cut_at_the_first_and_today_is_not_marked_in_another_month(self):
        j = self.out['january']
        self.assertEqual(j['bar'], ['0', '384'])     # Jan 1 to Jan 8
        self.assertFalse(j['pill'])


class GanttPeriodMarkupTests(unittest.TestCase):
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    css = (STATIC / 'style.css').read_text(encoding='utf-8')

    def test_the_title_is_a_heading_that_names_the_chart_region(self):
        self.assertRegex(self.html, r'<h3[^>]*class="gx-title"[^>]*id="gantt-title"|<h3[^>]*id="gantt-title"[^>]*class="gx-title"')

    def test_previous_and_next_are_grouped_and_today_is_its_own_button(self):
        group = re.search(r'<div[^>]*id="gantt-nav"[^>]*>(.*?)</div>', self.html, re.S)
        self.assertIsNotNone(group)
        self.assertIn('role="group"', group.group(0))
        self.assertIn('id="gantt-prev"', group.group(1))
        self.assertIn('id="gantt-next"', group.group(1))
        self.assertNotIn('id="gantt-today"', group.group(1))
        self.assertRegex(self.html, r'<button[^>]*id="gantt-today"[^>]*>Today</button>')

    def test_the_today_pill_takes_its_colours_from_tokens(self):
        rule = re.search(r'(?m)^\.gx-today-pill \{([^}]*)\}', self.css).group(1)
        self.assertIn('background: var(--gx-primary)', rule)
        self.assertIn('color: var(--gx-primary-fg)', rule)


if __name__ == '__main__':
    unittest.main()
