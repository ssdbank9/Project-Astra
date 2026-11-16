"""Behaviour tests for the Gantt's dependency arrows.

One arrow runs from the right edge of a prerequisite's bar to the left edge of the step that waits for
it, when both are drawn. It is muted when idle, dark while the pointer or the keyboard focus is on either
end, and red when the two bars overlap or touch the wrong way round (a conflict). The Dependencies switch
turns the layer off. Node runs the real src/astra/static/app.js (same DOM stub as test_gantt_zoom.py).
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
  // ---- gxPath: rows are 48px tall, so row r has its middle at r * 48 + 24 ----
  const B=(l,w,row)=>({l,w,row});
  out.path={
    flat:gxPath(B(0,100,1),B(200,50,1)),
    down:gxPath(B(0,100,1),B(200,50,3)),
    up:gxPath(B(0,100,3),B(200,50,1)),
    exactGap:gxPath(B(0,100,1),B(125,50,2)),        // 24px of room: still the simple elbow
    tight:gxPath(B(0,100,1),B(120,50,2)),           // 19px of room: goes round
    back:gxPath(B(300,100,1),B(100,50,3)),          // the successor starts before its predecessor ends
    backUp:gxPath(B(300,100,3),B(100,50,1)),
    sameRowBack:gxPath(B(300,100,2),B(100,50,2))};

  // ---- the arrows of a drawn chart ----
  const tasks=()=>[
    T("a","Alpha","2026-06-01","2026-06-05",{status:"completed",timeline_order:1}),
    T("b","Beta","2026-06-08","2026-06-12",{predecessors:P(["a"]),timeline_order:2}),
    T("c","Gamma","2026-06-10","2026-06-15",{predecessors:P(["b"]),timeline_order:3}),
    T("d","Delta","2026-06-13","2026-06-14",{predecessors:P(["b"]),timeline_order:4}),
    T("m","Launch",null,"2026-06-20",{is_milestone:true,predecessors:P(["c","m","gone"]),timeline_order:5}),
    T("may","May work","2026-05-04","2026-05-08",{timeline_order:6}),
    T("e","Echo","2026-06-22","2026-06-23",{predecessors:P(["may","a"]),timeline_order:7}),
  ];
  const list=()=>[...paths().matchAll(/<path class="gx-dep gx-dep-(\w+)" data-from="([^"]*)" data-to="([^"]*)" d="([^"]*)" marker-end="([^"]*)"\/>/g)].map(m=>({st:m[1],from:m[2],to:m[3],d:m[4],marker:m[5]}));
  const states=()=>Object.fromEntries(list().map(p=>[p.from+">"+p.to,p.st]));
  boot(tasks());
  out.rows=[...g.innerHTML.matchAll(/class="gx-row gx-step[^"]*" data-timeline-task="([^"]+)"/g)].map(m=>m[1]);
  out.drawn=list();out.total=(paths().match(/<path/g)||[]).length;
  out.svg=(/<svg class="gx-deps"[^>]*>/.exec(g.innerHTML)||[])[0];
  out.markers=[...g.innerHTML.matchAll(/<marker id="([^"]+)"[^>]*><path class="([^"]+)"/g)].map(m=>[m[1],m[2]]);

  // ---- hover and keyboard focus ----
  const fire=(type,id)=>{for(const f of g._l[type]||[])f({target:{closest:s=>s==="[data-bar]"&&id?{dataset:{bar:id}}:null}})};
  fire("mouseover","b");out.hoverB=states();
  fire("mouseover","m");out.hoverM=states();
  fire("mouseover",null);out.hoverNothing=states();
  fire("mouseover","a");fire("mouseleave");out.left=states();
  fire("focusin","e");out.focusE=states();
  fire("focusin","e");fire("mouseover","b");out.focusAndHover=states();
  fire("mouseleave");fire("focusout");out.blurred=states();
  // A redraw keeps the highlight of the focused bar.
  fire("focusin","b");renderGantt(state.tasks);out.redrawKeepsFocus=states();fire("focusout");

  // ---- Space on a bar must not scroll the page ----
  const key=(k,onBar)=>{let stopped=false;for(const f of g._l.keydown||[])f({key:k,preventDefault(){stopped=true},target:{closest:s=>s==="[data-bar]"&&onBar?{dataset:{bar:"b"}}:null}});return stopped};
  out.keys={spaceOnBar:key(" ",true),spaceElsewhere:key(" ",false),enterOnBar:key("Enter",true)};

  // ---- the Dependencies switch ----
  const sw=H.store["#gantt-deps"];
  sw.onchange({target:{checked:false}});out.off={n:list().length,stored:mem["astra.gantt.deps"]};
  renderGantt(state.tasks);out.offAfterRedraw=list().length;
  fire("mouseover","b");out.offHover=list().length;fire("mouseleave");
  sw.onchange({target:{checked:true}});out.on={n:list().length,stored:mem["astra.gantt.deps"]};

  // ---- while a bar is dragged its arrows follow it, and a conflict shows before the drop ----
  const cell=(a,id)=>document.querySelector(`[${a}="${id}"]`).textContent;
  const tb=state.tasks.find(t=>t.id==="b"),geoB={...gx.geo.get("b")};
  gxDragLive(tb,{start_date:"2026-06-04",due_date:"2026-06-08"},geoB.l-4*48,geoB.w);
  out.dragEarlier={states:states(),dates:cell("data-dates","b"),len:cell("data-len","b"),d:list().find(p=>p.to==="b").d,stored:{...gx.geo.get("b")}};
  gxDragLive(tb,{start_date:"2026-06-08",due_date:"2026-06-09"},geoB.l,2*48);
  out.dragShorter={states:states(),dates:cell("data-dates","b"),len:cell("data-len","b")};
  gxDragLive(tb,tb,null);
  out.dragBack={states:states(),dates:cell("data-dates","b"),len:cell("data-len","b")};

  // ---- a collapsed phase takes its steps' arrows with it; the phase's own bar still links ----
  const nested=()=>[
    T("a","Alpha","2026-06-01","2026-06-02",{timeline_order:1}),
    T("par","Design","2026-06-08","2026-06-12",{predecessors:P(["a"]),timeline_order:2}),
    T("k1","Kid one","2026-06-08","2026-06-09",{parent_task_id:"par",predecessors:P(["a"])}),
    T("z","Zulu","2026-06-22","2026-06-23",{predecessors:P(["k1","par"]),timeline_order:3}),
  ];
  boot(nested());out.nestedOpen=Object.keys(states()).sort();
  mem["astra.gantt.collapsed"]=["t:par"];boot(nested());out.nestedClosed=Object.keys(states()).sort();
  mem["astra.gantt.collapsed"]=["p:pr1"];boot(nested());out.projectClosed=list().length;
  delete mem["astra.gantt.collapsed"];

  // ---- ids are escaped into the markup ----
  boot([T('q"1',"Quote","2026-06-01","2026-06-02",{timeline_order:1}),T("r<2","Angle","2026-06-08","2026-06-09",{predecessors:P(['q"1']),timeline_order:2})]);
  out.escaped=paths();
  return out;
};
'''


class GanttDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_probe(PROBE, static=STATIC)
        cls.drawn = {p['from'] + '>' + p['to']: p for p in cls.out['drawn']}

    # ---- gxPath ---------------------------------------------------------------------------------
    def test_two_bars_on_one_row_are_joined_by_a_straight_line(self):
        self.assertEqual(self.out['path']['flat'], 'M 100 72 L 199 72')

    def test_a_forward_arrow_leaves_the_right_edge_turns_12px_out_and_enters_the_left_edge(self):
        self.assertEqual(self.out['path']['down'], 'M 100 72 L 106 72 Q 112 72 112 78 L 112 162 Q 112 168 118 168 L 199 168')
        self.assertEqual(self.out['path']['up'], 'M 100 168 L 106 168 Q 112 168 112 162 L 112 78 Q 112 72 118 72 L 199 72')

    def test_24_pixels_of_room_is_enough_for_the_simple_elbow(self):
        self.assertEqual(self.out['path']['exactGap'], 'M 100 72 L 106 72 Q 112 72 112 78 L 112 114 Q 112 120 118 120 L 124 120')

    def test_with_less_room_the_line_goes_round_between_the_rows_and_comes_in_from_the_left(self):
        # The line between the rows only ever runs leftwards: no back-and-forth kink for a 12-24px gap.
        self.assertEqual(self.out['path']['tight'],
                         'M 100 72 L 106 72 Q 112 72 112 78 L 112 90 Q 112 96 106 96 L 106 96 Q 100 96 100 102 L 100 114 Q 100 120 106 120 L 119 120')

    def test_a_successor_that_starts_earlier_is_reached_round_the_predecessors_row(self):
        self.assertEqual(self.out['path']['back'],
                         'M 400 72 L 406 72 Q 412 72 412 78 L 412 90 Q 412 96 406 96 L 93 96 Q 87 96 87 102 L 87 162 Q 87 168 93 168 L 99 168')
        self.assertEqual(self.out['path']['backUp'],
                         'M 400 168 L 406 168 Q 412 168 412 162 L 412 150 Q 412 144 406 144 L 93 144 Q 87 144 87 138 L 87 78 Q 87 72 93 72 L 99 72')

    def test_every_path_ends_one_pixel_before_the_successors_left_edge_at_its_row_middle(self):
        ends = {k: v.rsplit('L ', 1)[1] for k, v in self.out['path'].items()}
        self.assertEqual(ends, {'flat': '199 72', 'down': '199 168', 'up': '199 72', 'exactGap': '124 120', 'tight': '119 120',
                                'back': '99 168', 'backUp': '99 72', 'sameRowBack': '99 120'})
        for d in self.out['path'].values():
            self.assertNotIn('NaN', d)

    # ---- which arrows are drawn -----------------------------------------------------------------
    def test_one_arrow_per_dependency_whose_two_ends_are_drawn(self):
        self.assertEqual(self.out['rows'], ['a', 'b', 'c', 'd', 'm', 'may', 'e'])
        self.assertEqual(sorted(self.drawn), ['a>b', 'a>e', 'b>c', 'b>d', 'c>m'])
        self.assertEqual(self.out['total'], 5)

    def test_a_prerequisite_outside_the_period_or_not_on_the_chart_draws_no_arrow(self):
        self.assertNotIn('may>e', self.drawn)     # May work is not in June
        self.assertNotIn('gone>m', self.drawn)    # not among the tasks

    def test_a_step_never_points_at_itself(self):
        self.assertNotIn('m>m', self.drawn)

    def test_an_arrow_runs_from_the_end_of_the_prerequisite_to_the_start_of_the_step(self):
        # a: Jun 1-5 (0..240) on row 1; b: Jun 8-12 (336..576) on row 2. Row 0 is the project.
        self.assertEqual(self.drawn['a>b']['d'], 'M 240 72 L 246 72 Q 252 72 252 78 L 252 114 Q 252 120 258 120 L 335 120')
        # c>m: Gamma ends Jun 15 (720) on row 3; the flag of Jun 20 starts at 922 on row 5.
        self.assertEqual(self.drawn['c>m']['d'], 'M 720 168 L 726 168 Q 732 168 732 174 L 732 258 Q 732 264 738 264 L 921 264')

    def test_the_layer_covers_every_day_and_every_row(self):
        self.assertEqual(self.out['svg'], '<svg class="gx-deps" width="1440" height="384" aria-hidden="true" focusable="false">')   # 30 days * 48, 8 rows * 48

    def test_there_is_an_arrowhead_for_each_of_the_three_states(self):
        self.assertEqual(self.out['markers'], [['gx-arrow', 'gx-head-idle'], ['gx-arrow-active', 'gx-head-active'], ['gx-arrow-conflict', 'gx-head-conflict']])

    # ---- idle, active, conflict -----------------------------------------------------------------
    def test_an_arrow_is_idle_until_something_points_at_it(self):
        self.assertEqual({k: p['st'] for k, p in self.drawn.items()},
                         {'a>b': 'idle', 'a>e': 'idle', 'b>c': 'conflict', 'b>d': 'idle', 'c>m': 'idle'})
        self.assertEqual(self.drawn['a>b']['marker'], 'url(#gx-arrow)')

    def test_a_step_that_starts_on_or_before_the_day_its_prerequisite_ends_is_a_conflict(self):
        # Gamma starts Jun 10, Beta ends Jun 12. Delta starts Jun 13, the day after: no conflict.
        self.assertEqual((self.drawn['b>c']['st'], self.drawn['b>c']['marker']), ('conflict', 'url(#gx-arrow-conflict)'))
        self.assertEqual(self.drawn['b>d']['st'], 'idle')

    def test_hovering_a_bar_turns_the_arrows_at_both_its_ends_active(self):
        self.assertEqual(self.out['hoverB'], {'a>b': 'active', 'a>e': 'idle', 'b>c': 'conflict', 'b>d': 'active', 'c>m': 'idle'})
        self.assertEqual(self.out['hoverM'], {'a>b': 'idle', 'a>e': 'idle', 'b>c': 'conflict', 'b>d': 'idle', 'c>m': 'active'})

    def test_a_conflict_stays_red_under_the_pointer(self):
        self.assertEqual(self.out['hoverB']['b>c'], 'conflict')

    def test_leaving_the_bar_or_the_chart_puts_the_arrows_back(self):
        idle = {'a>b': 'idle', 'a>e': 'idle', 'b>c': 'conflict', 'b>d': 'idle', 'c>m': 'idle'}
        self.assertEqual(self.out['hoverNothing'], idle)
        self.assertEqual(self.out['left'], idle)
        self.assertEqual(self.out['blurred'], idle)

    def test_keyboard_focus_on_a_bar_highlights_its_arrows_like_the_pointer_does(self):
        self.assertEqual(self.out['focusE'], {'a>b': 'idle', 'a>e': 'active', 'b>c': 'conflict', 'b>d': 'idle', 'c>m': 'idle'})
        self.assertEqual(self.out['focusAndHover'], {'a>b': 'active', 'a>e': 'active', 'b>c': 'conflict', 'b>d': 'active', 'c>m': 'idle'})
        self.assertEqual(self.out['redrawKeepsFocus']['a>b'], 'active')

    def test_space_on_a_bar_does_not_scroll_the_page(self):
        self.assertEqual(self.out['keys'], {'spaceOnBar': True, 'spaceElsewhere': False, 'enterOnBar': False})

    # ---- the switch -----------------------------------------------------------------------------
    def test_the_switch_clears_the_arrows_and_remembers_the_choice(self):
        self.assertEqual(self.out['off'], {'n': 0, 'stored': False})
        self.assertEqual(self.out['offAfterRedraw'], 0)
        self.assertEqual(self.out['offHover'], 0)
        self.assertEqual(self.out['on'], {'n': 5, 'stored': True})

    # ---- dragging -------------------------------------------------------------------------------
    def test_a_dragged_bar_takes_its_arrows_along_and_shows_the_conflict_it_would_cause(self):
        d = self.out['dragEarlier']
        # Beta moved to Jun 4-8: it now starts before Alpha ends (Jun 5), and no longer overlaps Gamma (Jun 10).
        self.assertEqual(d['states'], {'a>b': 'conflict', 'a>e': 'idle', 'b>c': 'active', 'b>d': 'active', 'c>m': 'idle'})
        self.assertEqual((d['dates'], d['len']), ('Jun 4 – 8', '5d'))
        self.assertTrue(d['d'].endswith('L 143 120'), d['d'])        # the arrow now ends at the dragged left edge (336 - 192 - 1)
        self.assertEqual(d['stored']['l'], 336)                      # the drawn place is not overwritten by the preview

    def test_a_resized_bar_updates_its_dates_and_length_while_the_pointer_is_down(self):
        d = self.out['dragShorter']
        self.assertEqual((d['dates'], d['len']), ('Jun 8 – 9', '2d'))
        self.assertEqual(d['states']['b>c'], 'active')               # Beta now ends Jun 9, before Gamma starts

    def test_cancelling_a_drag_puts_the_row_and_the_arrows_back(self):
        d = self.out['dragBack']
        self.assertEqual((d['dates'], d['len']), ('Jun 8 – 12', '5d'))
        self.assertEqual(d['states'], {'a>b': 'idle', 'a>e': 'idle', 'b>c': 'conflict', 'b>d': 'idle', 'c>m': 'idle'})

    # ---- phases ---------------------------------------------------------------------------------
    def test_a_task_with_steps_links_through_its_summary_bar(self):
        self.assertEqual(self.out['nestedOpen'], ['a>k1', 'a>par', 'k1>z', 'par>z'])

    def test_collapsing_a_phase_drops_the_arrows_of_the_steps_inside_it(self):
        self.assertEqual(self.out['nestedClosed'], ['a>par', 'par>z'])
        self.assertEqual(self.out['projectClosed'], 0)

    def test_ids_are_escaped_in_the_arrow_markup(self):
        self.assertIn('data-from="q&quot;1" data-to="r&lt;2"', self.out['escaped'])


class GanttDependencyCssTests(unittest.TestCase):
    css = (STATIC / 'style.css').read_text(encoding='utf-8')
    html = (STATIC / 'index.html').read_text(encoding='utf-8')

    def rule(self, selector):
        found = re.search(r'(?m)^%s \{([^}]*)\}' % re.escape(selector), self.css)
        self.assertIsNotNone(found, selector)
        return found.group(1)

    def test_the_arrow_layer_never_takes_a_click_from_a_bar(self):
        self.assertIn('pointer-events: none', self.rule('.gx-deps'))
        self.assertIn('position: absolute', self.rule('.gx-deps'))

    def test_an_arrow_is_a_line_with_no_fill(self):
        self.assertIn('fill: none', self.rule('.gx-dep'))

    def test_each_state_takes_its_colour_from_a_token(self):
        self.assertRegex(self.rule('.gx-dep-idle'), r'stroke: [^;]*var\(--gx-')
        self.assertRegex(self.rule('.gx-dep-active'), r'stroke: var\(--gx-primary\)')
        self.assertRegex(self.rule('.gx-dep-conflict'), r'stroke: var\(--gx-destructive\)')
        self.assertRegex(self.rule('.gx-head-active'), r'fill: var\(--gx-primary\)')
        self.assertRegex(self.rule('.gx-head-conflict'), r'fill: var\(--gx-destructive\)')

    def test_the_three_states_differ_in_colour_only_so_a_highlight_never_shifts_a_line(self):
        self.assertIn('stroke-width: 1.5', self.rule('.gx-dep'))
        for state in ('idle', 'active', 'conflict'):
            self.assertNotIn('stroke-width', self.rule('.gx-dep-' + state))

    def test_the_switch_is_a_real_checkbox_with_the_switch_role_and_starts_on(self):
        tag = re.search(r'<input[^>]*id="gantt-deps"[^>]*>', self.html).group(0)
        self.assertIn('type="checkbox"', tag)
        self.assertIn('role="switch"', tag)
        self.assertIn('checked', tag)
        self.assertRegex(self.html, r'<label class="gx-switch">\s*<input[^>]*id="gantt-deps"[^>]*>\s*<span class="gx-switch-track"[^>]*></span>\s*Dependencies\s*</label>')


if __name__ == '__main__':
    unittest.main()
