"""Pure timeline planning. No database writes or authorization decisions."""
from datetime import date, timedelta


def day(value):
    return date.fromisoformat(value) if value else None


def bounds(tasks):
    selected = [t for t in tasks if t['status'] not in {'cancelled', 'abandoned'}]
    starts = [t.get('start_date') or t.get('due_date') for t in selected]
    finishes = [t.get('due_date') or t.get('start_date') for t in selected]
    return {'start_date': min(filter(None, starts), default=None),
            'finish_date': max(filter(None, finishes), default=None),
            'undated_count': sum(not t.get('start_date') or not t.get('due_date') for t in selected)}


def forecasts(tasks):
    from .workplan import plan
    names = {plan(t) for t in tasks} | {'Shared'}
    result = {}
    for name in sorted(names):
        selected = [t for t in tasks if plan(t) in {'Shared', name}
                    and t['status'] not in {'cancelled', 'abandoned'}]
        result[name] = bounds(selected)
    return result


def build(tasks, edges, task_id, mode, target_id=None, start_date=None, due_date=None):
    """Keep durations and existing finish-to-start gaps; new edges have zero gap.

    Only the moved task and its affected successors change. Multiple predecessors
    use the latest required start. Independent tasks and other plans stay intact.
    """
    before = {t['id']: dict(t) for t in tasks}
    after = {tid: dict(t) for tid, t in before.items()}
    original = set(edges)
    links = set(edges)
    root = task_id
    if mode in {'above', 'below', 'after'}:
        pred, succ = (task_id, target_id) if mode == 'above' else (target_id, task_id)
        # Reversing a direct sequence is explicit in the preview. Indirect cycles
        # remain invalid; never guess which other prerequisites to remove.
        links.discard((succ, pred))
        links.add((pred, succ))
        root = succ
    elif mode == 'concurrent':
        links.discard((task_id, target_id))
        links.discard((target_id, task_id))
    elif mode != 'date':
        raise ValueError('Unknown timeline movement.')
    preds = {tid: [] for tid in before}
    children = {tid: [] for tid in before}
    for pred, succ in sorted(links):
        if pred not in before or succ not in before:
            raise ValueError('The dependency leaves this project.')
        preds[succ].append(pred)
        children[pred].append(succ)
    remaining = {tid: len(v) for tid, v in preds.items()}
    queue = sorted(tid for tid, n in remaining.items() if not n)
    topo = []
    while queue:
        tid = queue.pop(0)
        topo.append(tid)
        for child in children[tid]:
            remaining[child] -= 1
            if not remaining[child]:
                queue.append(child)
    if len(topo) != len(before):
        raise ValueError('This move would create a dependency cycle. Review the existing links.')
    if mode == 'concurrent':
        for source, destination in ((task_id, target_id), (target_id, task_id)):
            seen, todo = set(), [source]
            while todo:
                tid = todo.pop()
                if tid in seen:
                    continue
                seen.add(tid)
                todo.extend(children[tid])
            if destination in seen:
                raise ValueError('An indirect dependency still links these tasks; they cannot run concurrently.')
    affected, todo = set(), [root]
    while todo:
        tid = todo.pop()
        if tid in affected:
            continue
        affected.add(tid)
        todo.extend(children[tid])
    if mode == 'above':
        affected.add(task_id)
        todo = list(children[task_id])
        while todo:
            tid = todo.pop()
            if tid in affected:
                continue
            affected.add(tid)
            todo.extend(children[tid])
    durations = {}
    for tid in affected:
        t = before[tid]
        start, finish = day(t.get('start_date')), day(t.get('due_date'))
        if tid == task_id and mode == 'date':
            start, finish = day(start_date), day(due_date)
        if not start or not finish or finish < start:
            raise ValueError(f'Set valid start and finish dates for “{t["title"]}” before scheduling its chain.')
        durations[tid] = (finish - start).days + 1
    gaps = {}
    for pred, succ in links:
        pfinish, sstart = day(before[pred].get('due_date')), day(before[succ].get('start_date'))
        gaps[pred, succ] = max(0, (sstart - pfinish).days - 1) if (pred, succ) in original and pfinish and sstart else 0
    for tid in topo:
        if tid not in affected:
            continue
        proposed = day(before[tid].get('start_date'))
        required_starts = []
        for pred in preds[tid]:
            finish = day(after[pred].get('due_date'))
            if not finish:
                raise ValueError(f'Set a finish date for prerequisite “{before[pred]["title"]}”.')
            required_starts.append(finish + timedelta(days=1 + gaps[pred, tid]))
        if tid == task_id and mode == 'date':
            proposed = day(start_date)
            if required_starts and proposed < max(required_starts):
                raise ValueError('This date would start before a prerequisite finishes.')
        elif tid == task_id and mode == 'concurrent':
            proposed = day(before[target_id].get('start_date'))
            if not proposed:
                raise ValueError('The parallel task needs a start date.')
            if required_starts and proposed < max(required_starts):
                raise ValueError('Another prerequisite prevents these tasks starting together.')
        elif required_starts:
            proposed = max(required_starts)
        after[tid]['start_date'] = proposed.isoformat()
        after[tid]['due_date'] = (proposed + timedelta(days=durations[tid] - 1)).isoformat()
    changes = [{'task_id': tid, 'title': before[tid]['title'],
                'owner_user_id': before[tid].get('owner_user_id'),
                'before': {k: before[tid].get(k) for k in ('start_date', 'due_date')},
                'after': {k: after[tid].get(k) for k in ('start_date', 'due_date')}}
               for tid in topo if any(before[tid].get(k) != after[tid].get(k) for k in ('start_date', 'due_date'))]
    return {'changes': changes, 'affected_ids': sorted(affected),
            'add_links': sorted(links - original), 'remove_links': sorted(original - links),
            'before_forecasts': forecasts(list(before.values())),
            'forecasts': forecasts(list(after.values())),
            'before_schedule': bounds(list(before.values())), 'schedule': bounds(list(after.values()))}
