"""Readable project workplans; OOXML only, no third-party runtime dependencies."""
from __future__ import annotations
import io
import json
import zipfile
from collections import defaultdict
from xml.etree import ElementTree as ET
from . import importer, workplan
from .xlsx_reader import read_workbook

MARKER = 'Astra Owner Workplan'
VERSION = '1'
HEADERS = ('Task', 'Responsible person', 'Start', 'Finish', 'Timing relationship', 'Related task', 'Part of', 'Plan', 'Type', 'Task ID')
AFTER = 'After another task finishes'
CONCURRENT = 'Can run concurrently'
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

def reference_label(value):
    """Use the same whitespace rules for dropdown labels and named lookups."""
    return ' '.join(str(value).split())

def label(title, plan):
    return reference_label(f'{plan or "Shared"}: {title}')

def build(project, entities, tasks, people, blank_keys):
    # Reuse Astra's tested package and styles, replacing only workbook-specific sheets.
    raw = importer.build_template_xlsx(workplan.config(), tasks=tasks, people=people)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        parts = {n: archive.read(n) for n in archive.namelist()}
    root = ET.fromstring(parts['xl/workbook.xml'])
    sheets = root.find(f'{{{NS}}}sheets')
    rel_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    rels = ET.fromstring(parts['xl/_rels/workbook.xml.rels'])
    paths = {r.attrib['Id']: 'xl/'+r.attrib['Target'] for r in rels}
    names = {}
    for sheet in sheets:
        name = sheet.attrib['name']; names[name] = paths[sheet.attrib[f'{{{rel_ns}}}id']]
        if name in ('Tasks', importer.README_SHEET):
            sheet.attrib.pop('state', None)
        else:
            sheet.attrib['state'] = 'veryHidden' if name == '_astra' else 'hidden'
    owner_labels = {p[0]: f'{p[1]} <{p[0]}>' if p[1] else p[0] for p in (people or [])}
    title_by_key = {t['import_key']: label(t['title'], t.get('x_plan')) for t in tasks}
    data = []
    for t in tasks:
        predecessors = str(t.get('predecessors') or '').split(';')
        predecessors = [p.strip() for p in predecessors if p.strip()]
        data.append([t['title'], owner_labels.get(t.get('owner_email'), t.get('owner_email', '')), t.get('start_date'), t.get('due_date'),
                     AFTER if predecessors else '', '\n'.join(title_by_key.get(p, p) for p in predecessors),
                     title_by_key.get(t.get('parent_key'), ''), t.get('x_plan') or 'Shared', t.get('x_type') or 'Task', t['import_key']])
    data.extend([['', '', '', '', '', '', '', 'Shared', 'Task', k] for k in blank_keys[:20]])
    end = len(data)+4
    def row(number, values, locked=False):
        cells=[]
        for col, value in enumerate(values, 1):
            style=importer.XF_LOCKED if locked or col==10 else (importer.XF_DATE if col in (3,4) else importer.XF_TEXT)
            cells.append(importer._cell(f'{importer.column_letter(col)}{number}',value,style,style,style) or f'<c r="{importer.column_letter(col)}{number}" s="{style}"/>')
        return f'<row r="{number}" ht="30" customHeight="1">'+''.join(cells)+'</row>'
    task_rows = row(1,[project['name']],True)+row(2,['Entity: '+ '; '.join(e['name'] for e in entities)],True)
    task_rows += row(3,['Fill the first four columns. Expand the optional columns for grouping and relationships.'],True)
    task_rows += '<row r="4" ht="34" customHeight="1">'+''.join(importer._inline(f'{importer.column_letter(i)}4',h,importer.XF_HEAD_CORE if i<=4 else importer.XF_HEAD_OPTIONAL) for i,h in enumerate(HEADERS,1))+'</row>'
    task_rows += ''.join(row(n,v) for n,v in enumerate(data,5))
    validations = [importer._validation('list',f'B5:B{end}','Responsible person','Select an existing person.','Select an eligible Astra user.',formula1='_astraOwners'),
                   importer._validation('list',f'E5:E{end}','Timing relationship','Optional. Dates alone do not create links.','Select a timing relationship.',formula1='"'+CONCURRENT+','+AFTER+'"'),
                   importer._validation('list',f'F5:G{end}','Related task / grouping','Select by task name.','Select a task from this workbook.',formula1='_astraTaskNames',style='warning'),
                   importer._validation('list',f'H5:H{end}','Plan','Shared or an alternative plan.','Enter a plan name.',formula1='_astraPlans',style='warning'),
                   importer._validation('list',f'I5:I{end}','Type','Task, Milestone or Action item.','Select a task type.',formula1='"Task,Milestone,Action item"')]
    task_body=f'<dimension ref="A1:J{end}"/><sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="30" outlineLevelCol="1"/>'
    task_body+='<cols><col min="1" max="1" width="55" customWidth="1"/><col min="2" max="2" width="32" customWidth="1"/><col min="3" max="4" width="15" customWidth="1"/><col min="5" max="9" width="34" customWidth="1" hidden="1" outlineLevel="1"/><col min="10" max="10" width="14" customWidth="1" hidden="1" collapsed="1"/></cols>'
    task_body+='<sheetData>'+task_rows+'</sheetData><sheetProtection sheet="1" objects="1" scenarios="1" formatColumns="0" autoFilter="0"/><autoFilter ref="A4:J'+str(end)+'"/><dataValidations count="'+str(len(validations))+'">'+''.join(validations)+'</dataValidations>'
    parts[names['Tasks']]=importer._sheet(task_body).encode()
    list_rows=[]
    for n, values in enumerate(data,2):
        r=n+3
        formula=f'IF(Tasks!A{r}="","",IF(Tasks!H{r}="","Shared",Tasks!H{r})&": "&Tasks!A{r})'
        list_rows.append(f'<row r="{n}">'+importer._formula(f'A{n}',formula,importer.XF_LOCKED)+'</row>')
    # Names plus emails are mapped explicitly; no accounts are created by the file.
    for n,p in enumerate(people or [],2):
        list_rows.append(f'<row r="{n}">'+importer._inline(f'B{n}',owner_labels[p[0]],0)+importer._inline(f'C{n}',p[0],0)+'</row>')
    plans=sorted({'Shared'}|{str(t.get('x_plan') or 'Shared') for t in tasks})
    for n,plan in enumerate(plans,2): list_rows.append(f'<row r="{n}">'+importer._inline(f'D{n}',plan,0)+'</row>')
    # Multiple XML row elements with the same r are invalid: coalesce their cells.
    list_xml=ET.fromstring('<sheetData xmlns="'+NS+'">'+''.join(list_rows)+'</sheetData>')
    grouped={}
    for r in list_xml:
        grouped.setdefault(int(r.attrib['r']),[]).extend(list(r))
    lists='<sheetData>'+''.join('<row r="'+str(n)+'">'+''.join(ET.tostring(c,encoding='unicode') for c in cells)+'</row>' for n,cells in sorted(grouped.items()))+'</sheetData>'
    parts[names['Lists']]=importer._sheet(lists).encode()
    defs=root.find(f'{{{NS}}}definedNames')
    if defs is not None: root.remove(defs)
    defs=ET.Element(f'{{{NS}}}definedNames')
    # OOXML requires names before calcPr; Excel may repair an out-of-order workbook.
    calculation=root.find(f'{{{NS}}}calcPr')
    root.insert(list(root).index(calculation) if calculation is not None else len(root),defs)
    for name,target in [('_astraTaskNames',f'Lists!$A$2:$A${len(data)+1}'),('_astraOwners',f'Lists!$B$2:$B${max(2,len(people or [])+1)}'),('_astraPlans',f'Lists!$D$2:$D${len(plans)+1}')]:
        ET.SubElement(defs,f'{{{NS}}}definedName',name=name).text=target
    view=root.find(f'{{{NS}}}bookViews/{{{NS}}}workbookView')
    if view is not None: view.attrib['activeTab']=str(next(i for i,s in enumerate(sheets) if s.attrib['name']=='Tasks'))
    parts['xl/workbook.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    metadata=[(MARKER,VERSION),('Project ID',project['id']),('Entity IDs',json.dumps(sorted(e['id'] for e in entities)))]
    parts[names['_astra']]=importer._sheet('<sheetData>'+''.join(row(i,p,True) for i,p in enumerate(metadata,1))+'</sheetData>').encode()
    guide=[project['name'],'Fill Task, Responsible person, Start and Finish. Dates use yyyy-mm-dd.','Optional columns E to I are grouped. Expand them with the + above the columns.','Choose a timing relationship and a related task by name. Concurrent adds no predecessor.','After another task finishes requires that task to finish before this one starts. Conflicts appear in the upload preview.','Part of groups a step under another task; grouping does not create a dependency.','Plan separates alternatives such as Private and Charter. Shared work can support either.','Keep the hidden Task IDs and project information unchanged. New blank rows already have Astra-managed IDs.','Save as .xlsx. Upload to the same project, review the preview and confirm. Imports never delete tasks.','Changing a task name may require reselecting it in the related-task cells. Duplicate names within a plan must be distinguished.']
    parts[names[importer.README_SHEET]]=importer._sheet('<cols><col min="1" max="1" width="115" customWidth="1"/></cols><sheetData>'+''.join(f'<row r="{i}" ht="36" customHeight="1">'+importer._inline(f'A{i}',text,importer.XF_WRAP_LOCKED)+'</row>' for i,text in enumerate(guide,1))+'</sheetData>').encode()
    parts['xl/styles.xml']=parts['xl/styles.xml'].replace(b'dd-mm-yyyy',b'yyyy-mm-dd')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,content in parts.items(): archive.writestr(name,content)
    return out.getvalue()

def parse(workbook):
    marker=workbook.sheet('_astra')
    if not marker or marker.cell(1,1)!=MARKER or str(marker.cell(1,2))!=VERSION:
        raise importer.ImportFileError('The project workplan identity is missing or changed. Download a fresh Excel workplan.')
    try:
        entity_ids=json.loads(marker.cell(3,2))
        if not isinstance(entity_ids,list) or any(not isinstance(v,str) for v in entity_ids): raise ValueError()
    except (TypeError,ValueError):
        raise importer.ImportFileError('The workplan entity identifiers are invalid.') from None
    sheet=workbook.sheet('Tasks')
    if not sheet or tuple(sheet.row_values(4,10))!=HEADERS:
        raise importer.ImportFileError('The Excel workplan columns changed. Download a fresh workbook.')
    owners={}
    lists=workbook.sheet('Lists')
    if lists:
        for _,values in lists.iter_rows(4):
            if values[1] and values[2]: owners[str(values[1])]=str(values[2])
    parsed=[]; by_label=defaultdict(list)
    for number,values in sheet.iter_rows(10):
        if number<=4: continue
        title=importer.normalize_text(values[0])
        if not title:
            if any(v not in (None,'') for v in values[1:7]):
                parsed.append(importer.ParsedRow(number,{'title':'','import_key':values[9] or ''}))
            continue
        cells={'title':values[0],'owner_email':owners.get(str(values[1]),values[1]),'start_date':values[2],'due_date':values[3],workplan.PLAN_KEY:values[7] or 'Shared','x_type':values[8] or 'Task','import_key':values[9] or ''}
        row=importer.ParsedRow(number,cells); parsed.append(row)
        by_label[label(title,cells[workplan.PLAN_KEY])].append(row)
        row.cells['_timing']=values[4] or ''; row.cells['_related']=values[5] or ''; row.cells['_part_of']=values[6] or ''
    for row in parsed:
        for field in ('_timing','_related','_part_of'):
            if isinstance(row.cells.get(field),importer.CellError):
                row.workplan_errors.append('Fix the spreadsheet error in the relationship or grouping cell.')
                row.cells[field]=''
        def resolve(value):
            choices=by_label.get(reference_label(value),[])
            if len(choices)!=1 or not choices[0].cells.get('import_key'):
                row.workplan_errors.append(f'Row {row.number}: related task "{value}" is missing or ambiguous. Select a distinct task name from this file.')
                return ''
            return choices[0].cells['import_key']
        if row.cells.get('_part_of'): row.cells['parent_key']=resolve(row.cells['_part_of'])
        timing=row.cells.get('_timing',''); related=row.cells.get('_related','')
        if timing not in ('',CONCURRENT,AFTER): row.workplan_errors.append('Choose Can run concurrently or After another task finishes.')
        if timing==AFTER:
            if not related: row.workplan_errors.append('Select the task that must finish first.')
            choices=[related] if reference_label(related) in by_label else str(related).splitlines()
            row.cells['predecessors']=';'.join(filter(None,(resolve(v) for v in choices)))
        elif related and not timing: row.workplan_errors.append('Choose a timing relationship for the selected related task.')
        elif timing==CONCURRENT:
            if not related:
                row.workplan_errors.append('Select the task that can run concurrently.')
            else:
                key=resolve(related)
                row.cells['_concurrent_key']=key
                if key and str(key).upper()==str(row.cells.get('import_key')).upper():
                    row.workplan_errors.append('A task cannot run concurrently with itself.')
    if len(parsed)>importer.MAX_ROWS: raise importer.ImportTooLarge('The workplan has too many task rows.')
    return importer.ParsedUpload(format='xlsx',rows=parsed,unknown_columns=[],file_warnings=[],sheet_name='Tasks',date1904=workbook.date1904,workplan={'project_id':marker.cell(2,2),'entity_ids':entity_ids,'excel':True})
