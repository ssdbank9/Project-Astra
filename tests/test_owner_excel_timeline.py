import io, json, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from astra import importer, workplan_excel
from astra.db import connect, transaction
from astra.service import AstraService, Forbidden, Conflict, TaskLocked
import test_web as web_fixture

NS=workplan_excel.NS

def fill(data, edits):
    with zipfile.ZipFile(io.BytesIO(data)) as z: parts={n:z.read(n) for n in z.namelist()}
    wb=ET.fromstring(parts['xl/workbook.xml']); rels=ET.fromstring(parts['xl/_rels/workbook.xml.rels'])
    lookup={r.attrib['Id']:'xl/'+r.attrib['Target'] for r in rels}
    sheet=next(s for s in wb.find('{'+NS+'}sheets') if s.attrib['name']=='Tasks')
    name=lookup[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
    root=ET.fromstring(parts[name]); rows=root.find('{'+NS+'}sheetData')
    for ref,value in edits.items():
        cell=next(c for r in rows for c in r if c.attrib['r']==ref)
        for child in list(cell): cell.remove(child)
        cell.attrib['t']='inlineStr'; ET.SubElement(ET.SubElement(cell,'{'+NS+'}is'),'{'+NS+'}t').text=value
    parts[name]=ET.tostring(root,encoding='utf-8')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in parts.items(): z.writestr(n,v)
    return out.getvalue()

class OwnerExcelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=connect(Path(self.temp.name)/'test.sqlite3');self.addCleanup(self.db.close)
        self.s=AstraService(self.db);self.owner=self.s.create_initial_owner('owner@example.org','Owner','synthetic password')
        self.p=self.s.create_project(self.owner,'School')
    def template(self): return self.s.import_template(self.owner,'xlsx',self.p['id'],workplan_csv=True)[0]
    def preview(self,data): return self.s.import_preview(self.owner,self.p['id'],'workplan.xlsx',data)
    def commit(self,data):
        p=self.preview(data)
        return self.s.import_commit(self.owner,self.p['id'],'workplan.xlsx',data,{},p['sha256'],p['plan_fingerprint'])
    def test_blank_template_hidden_identity_optional_fields_and_no_decide_option(self):
        data=self.template();wb=importer.read_workbook(data)
        self.assertEqual(wb.sheet('_astra').cell(1,1),workplan_excel.MARKER)
        self.assertTrue(wb.sheet('_astra').hidden)
        self.assertEqual(self.preview(data)['summary']['rows'],0)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            children=[child.tag.rsplit('}',1)[-1] for child in ET.fromstring(z.read('xl/workbook.xml'))]
            self.assertLess(children.index('definedNames'),children.index('calcPr'))
            xml=z.read('xl/worksheets/sheet3.xml').decode()
            self.assertIn('outlineLevel="1"',xml);self.assertIn('hidden="1"',xml)
            self.assertNotIn('Decide in Astra',xml)
            self.assertIn('Can run concurrently',xml)
    def test_named_relationship_import_replay_and_date_conflict(self):
        data=fill(self.template(),{'A5':'Construction','C5':'2026-10-01','D5':'2026-10-04','A6':'Inspection','C6':'2026-10-05','D6':'2026-10-05','E6':workplan_excel.AFTER,'F6':'Shared: Construction'})
        self.assertEqual(self.preview(data)['summary']['errors'],0)
        self.assertEqual(self.commit(data)['create'],2)
        self.assertEqual(self.commit(data)['create'],0)
        updated=self.template()
        self.assertEqual(self.preview(updated)['summary']['errors'],0)
        self.assertEqual(self.commit(updated)['create'],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],1)
        bad=fill(data,{'C6':'2026-10-04'})
        self.assertGreater(self.preview(bad)['summary']['errors'],0)
    def test_ambiguous_name_unknown_relationship_missing_and_self_targets(self):
        original=self.template()
        for edits in [
            {'A5':'Same','A6':'Same','A7':'Follower','E7':workplan_excel.AFTER,'F7':'Shared: Same'},
            {'A5':'Task','E5':'Decide in Astra'},
            {'A5':'Task','E5':workplan_excel.AFTER},
            {'A5':'Task','E5':workplan_excel.AFTER,'F5':'Shared: Task'},
            {'A5':'Task','G5':'Shared: Missing'}]:
            with self.subTest(edits=edits): self.assertGreater(self.preview(fill(original,edits))['summary']['errors'],0)
    def test_generated_relationship_labels_with_extra_whitespace_resolve(self):
        title='  Build  classroom  '
        # The workbook's dropdown formula concatenates the owner's raw title.
        selected='Shared: '+title
        data=fill(self.template(),{'A5':title,'C5':'2026-10-01','D5':'2026-10-02',
            'A6':'Paint walls','C6':'2026-10-03','D6':'2026-10-04',
            'E6':workplan_excel.AFTER,'F6':selected,'G6':selected})
        self.assertEqual(self.preview(data)['summary']['errors'],0)
        self.assertEqual(self.commit(data)['create'],2)
        parent=self.db.execute("SELECT id FROM tasks WHERE title=?",(title.strip(),)).fetchone()[0]
        child=self.db.execute("SELECT id,parent_task_id FROM tasks WHERE title='Paint walls'").fetchone()
        self.assertEqual(child['parent_task_id'],parent)
        self.assertEqual(self.db.execute('SELECT predecessor_task_id,successor_task_id FROM task_dependencies').fetchone()[:],(parent,child['id']))
    def test_project_entity_binding_rechecked_on_commit(self):
        data=fill(self.template(),{'A5':'New task'})
        other=self.s.create_project(self.owner,'Other')
        with self.assertRaises(ValueError): self.s.import_preview(self.owner,other['id'],'plan.xlsx',data)
        preview=self.preview(data)
        entity=self.s.create_entity(self.owner,'Colleges');self.s.set_project_entities(self.owner,self.p['id'],[entity['id']])
        with self.assertRaises(ValueError): self.s.import_commit(self.owner,self.p['id'],'plan.xlsx',data,{},preview['sha256'],preview['plan_fingerprint'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0],0)
    def test_concurrent_does_not_create_edge_and_grouping_is_separate(self):
        data=fill(self.template(),{'A5':'Parent','A6':'Step','G6':'Shared: Parent','E6':workplan_excel.CONCURRENT,'F6':'Shared: Parent'})
        self.assertEqual(self.commit(data)['create'],2)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],0)
        self.assertIsNotNone(self.db.execute("SELECT parent_task_id FROM tasks WHERE title='Step'").fetchone()[0])

    def test_responsible_person_label_resolves_to_existing_user(self):
        data=fill(self.template(),{'A5':'Task','B5':'Owner <owner@example.org>'})
        self.assertEqual(self.commit(data)['create'],1)
        self.assertEqual(self.db.execute('SELECT owner_user_id FROM tasks').fetchone()[0],self.owner['id'])

    def test_stripped_identity_refused(self):
        original=self.template()
        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            parts={n:archive.read(n) for n in archive.namelist()}
        workbook=ET.fromstring(parts['xl/workbook.xml'])
        sheets=workbook.find('{'+NS+'}sheets')
        sheets.remove(next(s for s in sheets if s.attrib['name']=='_astra'))
        parts['xl/workbook.xml']=ET.tostring(workbook,encoding='utf-8')
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:
            for name,content in parts.items(): archive.writestr(name,content)
        with self.assertRaises(ValueError): self.preview(out.getvalue())

    def test_concurrent_requires_distinct_compatible_unlinked_target(self):
        original=self.template()
        cases=[
            {'A5':'A','E5':workplan_excel.CONCURRENT},
            {'A5':'A','E5':workplan_excel.CONCURRENT,'F5':'Shared: A'},
            {'A5':'A','H5':'Private','A6':'B','H6':'Charter','E6':workplan_excel.CONCURRENT,'F6':'Private: A'},
            {'A5':'A','C5':'2026-10-01','D5':'2026-10-03','E5':workplan_excel.CONCURRENT,'F5':'Shared: B',
             'A6':'B','C6':'2026-10-04','D6':'2026-10-06','E6':workplan_excel.AFTER,'F6':'Shared: A'},
            {'A5':'A','C5':'2026-10-07','D5':'2026-10-09','E5':workplan_excel.AFTER,'F5':'Shared: B',
             'A6':'B','C6':'2026-10-04','D6':'2026-10-06','E6':workplan_excel.AFTER,'F6':'Shared: C',
             'A7':'C','C7':'2026-10-01','D7':'2026-10-03','E7':workplan_excel.CONCURRENT,'F7':'Shared: A'},
        ]
        for edits in cases:
            with self.subTest(edits=edits): self.assertGreater(self.preview(fill(original,edits))['summary']['errors'],0)

class TimelineTaskDropTests(unittest.TestCase):
    setUp = OwnerExcelTests.setUp
    # Only this class's own scenarios; avoid inheriting the Excel tests again.
    def task(self,title,start='2026-10-01',finish='2026-10-03'):
        return self.s.create_task(self.owner,{'project_id':self.p['id'],'title':title,'start_date':start,'due_date':finish})
    def payload(self,t,target,mode='after',**extra):
        return dict(mode=mode,target_task_id=target['id'],expected_revision=t['revision'],target_revision=target['revision'],start_date='2026-10-04',due_date='2026-10-06',confirmed=True,**extra)
    def test_after_drop_atomic_dates_link_and_critical_path(self):
        a=self.task('A');b=self.task('B')
        self.s.timeline_drop(self.owner,b['id'],self.payload(b,a))
        self.assertEqual(self.s.get_task(self.owner,b['id'])['start_date'],'2026-10-04')
        self.assertEqual(len(self.s.get_task_dependencies(self.owner,b['id'])),1)
        self.assertTrue(all(t['is_critical_path'] for t in self.s.list_tasks(self.owner,self.p['id'])))
    def test_failed_schedule_rolls_back_new_dependency(self):
        a=self.task('A');b=self.task('B')
        with patch.object(self.s,'_reschedule_task',side_effect=ValueError('refused')):
            with self.assertRaises(ValueError): self.s.timeline_drop(self.owner,b['id'],self.payload(b,a))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],0)
        self.assertEqual(self.s.get_task(self.owner,b['id'])['start_date'],'2026-10-01')

    def test_concurrent_indirect_dependency_refused_and_direct_removal_rolled_back(self):
        a=self.task('A');b=self.task('B');c=self.task('C')
        self.s.add_task_dependency(self.owner,a['id'],b['id'])
        self.s.add_task_dependency(self.owner,b['id'],c['id'])
        self.s.add_task_dependency(self.owner,a['id'],c['id'])
        payload=self.payload(c,a,'concurrent');payload.update(start_date=c['start_date'],due_date=c['due_date'])
        with self.assertRaises(ValueError): self.s.timeline_drop(self.owner,c['id'],payload)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],3)
    def test_revision_and_cycle_refusals_do_not_change_state(self):
        a=self.task('A');b=self.task('B')
        with self.assertRaises(Conflict): self.s.timeline_drop(self.owner,b['id'],dict(self.payload(b,a),target_revision=99))
        self.s.add_task_dependency(self.owner,b['id'],a['id'])
        with self.assertRaises(ValueError): self.s.timeline_drop(self.owner,b['id'],self.payload(b,a))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],1)
    def test_concurrent_removes_only_direct_edge_and_order_persists(self):
        a=self.task('A');b=self.task('B');self.s.add_task_dependency(self.owner,a['id'],b['id'])
        p=self.payload(b,a,'concurrent');p.update(start_date=b['start_date'],due_date=b['due_date'])
        self.s.timeline_drop(self.owner,b['id'],p)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],0)
        b=self.s.get_task(self.owner,b['id'])
        self.s.timeline_drop(self.owner,b['id'],self.payload(b,a,'above',order_event_id=None))
        listed=self.s.list_tasks(self.owner,self.p['id']);order={t['id']:t['timeline_order'] for t in listed}
        self.assertLess(order[b['id']],order[a['id']])
        with self.assertRaises(Conflict): self.s.timeline_drop(self.owner,b['id'],self.payload(b,a,'below',order_event_id=None))
    def test_inactive_actor_and_closed_project_refused(self):
        a=self.task('A');b=self.task('B')
        with self.assertRaises(Forbidden): self.s.timeline_drop(dict(self.owner,active=0),b['id'],self.payload(b,a))
        self.db.execute("UPDATE projects SET status='closed' WHERE id=?",(self.p['id'],))
        with self.assertRaises(Forbidden): self.s.timeline_drop(self.owner,b['id'],self.payload(b,a,'above',order_event_id=None))

    def test_another_users_source_or_target_lease_refuses_drop(self):
        a=self.task('A');b=self.task('B')
        manager=self.s.create_user(self.owner,'manager@example.org','Manager','synthetic password')
        self.s.grant_project_access(self.owner,self.p['id'],manager['id'],'manager')
        for task in (a,b):
            lease=self.s.acquire_task_lock(manager,task['id'],'edit')
            with self.assertRaises(TaskLocked): self.s.timeline_drop(self.owner,b['id'],self.payload(b,a,'above',order_event_id=None))
            self.s.release_task_lock(manager,task['id'],lease['token'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],0)

    def test_nested_failure_preserves_outer_changes_until_outer_commit(self):
        with transaction(self.db):
            self.db.execute("UPDATE projects SET name='Outer' WHERE id=?",(self.p['id'],))
            try:
                with transaction(self.db):
                    self.db.execute("UPDATE projects SET name='Inner' WHERE id=?",(self.p['id'],))
                    raise ValueError('abort inner operation')
            except ValueError: pass
            self.assertTrue(self.db.in_transaction)
            self.assertEqual(self.db.execute('SELECT name FROM projects').fetchone()[0],'Outer')
        self.assertFalse(self.db.in_transaction)
    def test_owner_request_and_audit_failure_roll_back_link_and_dates(self):
        a=self.task('A');b=self.task('B')
        with patch.object(self.s,'_reschedule_task',return_value={'request':{'id':'synthetic'}}):
            with self.assertRaises(Forbidden): self.s.timeline_drop(self.owner,b['id'],self.payload(b,a))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],0)
        with patch.object(self.s,'_event',side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError): self.s.timeline_drop(self.owner,b['id'],self.payload(b,a))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM task_dependencies').fetchone()[0],0)
        self.assertEqual(self.s.get_task(self.owner,b['id'])['start_date'],'2026-10-01')

    def test_nonmanagers_and_cross_project_refused(self):
        a=self.task('A');b=self.task('B');member=self.s.create_user(self.owner,'member@example.org','Member','synthetic password')
        for role in ['member','viewer']:
            self.s.grant_project_access(self.owner,self.p['id'],member['id'],role)
            with self.assertRaises(Forbidden): self.s.timeline_drop(member,b['id'],self.payload(b,a))
        chair=self.s.create_user(self.owner,'chair@example.org','Chair','synthetic password','chairman')
        with self.assertRaises(Forbidden): self.s.timeline_drop(chair,b['id'],self.payload(b,a))
        other=self.s.create_project(self.owner,'Other');c=self.s.create_task(self.owner,{'project_id':other['id'],'title':'C','due_date':'2026-10-03'})
        with self.assertRaises(ValueError): self.s.timeline_drop(self.owner,b['id'],self.payload(b,c))

# Share only setup/helpers, never a unittest class's inherited test methods.

class TimelineTaskHttpTests(unittest.TestCase):
    setUp=web_fixture.AstraWebTests.setUp
    tearDown=web_fixture.AstraWebTests.tearDown
    request=web_fixture.AstraWebTests.request
    def test_http_csrf_role_matrix_and_download(self):
        s=self.server.service;owner=dict(s.db.execute("SELECT * FROM users WHERE email='owner@example.org'").fetchone());p=s.create_project(owner,'Example')
        a=s.create_task(owner,{'project_id':p['id'],'title':'A','start_date':'2026-10-01','due_date':'2026-10-03'})
        b=s.create_task(owner,{'project_id':p['id'],'title':'B','start_date':'2026-10-04','due_date':'2026-10-06'})
        for role in ['owner','manager','member','viewer','chairman','secondary']:
            if role=='owner': user=owner
            else:
                user=s.create_user(owner,role+'@example.org',role,'correct horse battery','chairman' if role=='chairman' else 'member')
                if role in ['manager','member','viewer']: s.grant_project_access(owner,p['id'],user['id'],role)
                if role=='secondary': user=s.grant_secondary_owner(owner,user['id'],'Synthetic test')
            response,data=self.request('POST','/api/login',{'email':user['email'],'password':'correct horse battery'})
            cookie=response.getheader('Set-Cookie').split(';',1)[0];csrf=data['csrf']
            payload={'mode':'above','target_task_id':a['id'],'expected_revision':b['revision'],'target_revision':a['revision'],'order_event_id':s.list_tasks(owner,p['id'])[0]['timeline_order_event_id']}
            url='/api/tasks/'+b['id']+'/timeline-drop'
            response,_=self.request('POST',url,payload,cookie=cookie)
            self.assertEqual(response.status,403)
            response,_=self.request('POST',url,payload,cookie=cookie,csrf=csrf)
            self.assertEqual(response.status,200 if role in ['owner','manager','secondary'] else 403,role)
            self.connection.request('GET','/api/import/template.xlsx?project_id='+p['id']+'&workplan=1',headers={'Cookie':cookie})
            response=self.connection.getresponse();content=response.read()
            self.assertEqual(response.status,200 if role in ['owner','manager','secondary'] else 403,role)
            if response.status==200:
                parsed=workplan_excel.parse(importer.read_workbook(content))
                self.assertEqual(parsed.workplan['project_id'],p['id'])
