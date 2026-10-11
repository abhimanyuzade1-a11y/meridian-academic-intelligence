"""Meridian Academic Intelligence: local, persistent results server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json, sqlite3, csv, io, os, uuid, math
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get('MERIDIAN_DB', os.path.join(ROOT, 'meridian.db'))
DEFAULT_RULES = {'A*':90,'A':80,'B':70,'C':60,'D':50}

def connect():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS students(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT,class_name TEXT NOT NULL,roll TEXT NOT NULL,UNIQUE(class_name,roll));
        CREATE TABLE IF NOT EXISTS subjects(id TEXT PRIMARY KEY,name TEXT NOT NULL,code TEXT NOT NULL UNIQUE,max_marks INTEGER NOT NULL DEFAULT 100,pass_mark INTEGER NOT NULL DEFAULT 40,weight REAL NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS terms(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,is_current INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS marks(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,term_id INTEGER NOT NULL REFERENCES terms(id),score REAL NOT NULL,updated_at TEXT NOT NULL,UNIQUE(student_id,subject_id,term_id));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS term_workflow(term_id INTEGER PRIMARY KEY REFERENCES terms(id) ON DELETE CASCADE,status TEXT NOT NULL DEFAULT 'Draft',updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        ''')
        mark_columns={r['name'] for r in c.execute('pragma table_info(marks)')}
        if 'source' not in mark_columns:
            c.execute("alter table marks add column source text not null default 'sample'")
            c.execute("update marks set source='user' where updated_at in (select at from events where action in ('Mark saved','Marks imported'))")
            c.execute("update marks set source='user' where updated_at>coalesce((select max(at) from events where action in ('Sample data initialized','Sample term history added','Sample roster updated')),'')")
        c.execute('insert or ignore into app_settings(key,value) values(?,?)',('grading_rules',json.dumps(DEFAULT_RULES)))
        if c.execute('select count(*) from students').fetchone()[0]==0:
            c.executemany('insert into students values(?,?,?,?,?)', [('S-1001','Abhimanyu Zade','abhimanyu.zade@example.edu','Year 10','01'),('S-1002','Abhishek Choudhary','abhishek.choudhary@example.edu','Year 10','02'),('S-1003','Khandu Bhange','khandu.bhange@example.edu','Year 10','03'),('S-1004','Sarthak Landge','sarthak.landge@example.edu','Year 10','04'),('S-1005','Omkar Gadhe','omkar.gadhe@example.edu','Year 10','05'),('S-1006','Harsh Shinde','harsh.shinde@example.edu','Year 10','06'),('S-2001','Aanad Karale','aanad.karale@example.edu','Year 11','01'),('S-2002','Vallabh Lawate','vallabh.lawate@example.edu','Year 11','02'),('S-2003','Ashutosh Sutar','ashutosh.sutar@example.edu','Year 11','03'),('S-2004','Sumit Patil','sumit.patil@example.edu','Year 11','04'),('S-2005','Arvind Garje','arvind.garje@example.edu','Year 11','05')])
            c.executemany('insert into subjects values(?,?,?,?,?,?)',[('SUB-MATH','RPA','RPA',100,40,1),('SUB-ENG','Big Data','BDA',100,40,1),('SUB-SCI','Blockchain Technology','BCT',100,40,1),('SUB-HIST','DSA','DSA',100,40,1),('SUB-ART','C++','CPP',100,40,1)])
            c.executemany('insert into terms(name,is_current) values(?,?)',[('Autumn 2025',0),('Spring 2026',0),('Summer 2026',1)])
            ids=[x[0] for x in c.execute('select id from students')]; subs=[x[0] for x in c.execute('select id from subjects')]; term=c.execute("select id from terms where name='Spring 2026'").fetchone()[0]
            scores=[[100,100,100,100,100],[72,85,76,80,79],[93,89,95,91,90],[58,63,51,67,72],[77,74,81,69,85],[66,72,61,58,74],[88,92,85,81,94],[71,68,74,77,70],[96,93,89,95,92],[63,59,72,66,61],[48,55,43,52,60]]
            now=datetime.now().isoformat(timespec='seconds')
            c.executemany("insert into marks(student_id,subject_id,term_id,score,updated_at,source) values(?,?,?,?,?,'sample')",[(ids[i],subs[j],term,scores[i][j],now) for i in range(len(ids)) for j in range(len(subs))])
            autumn=c.execute("select id from terms where name='Autumn 2025'").fetchone()[0]; summer=c.execute("select id from terms where name='Summer 2026'").fetchone()[0]
            c.executemany("insert into marks(student_id,subject_id,term_id,score,updated_at,source) values(?,?,?,?,?,'sample')",[(ids[i],subs[j],autumn,max(0,min(100,scores[i][j]-6+(i+j)%4)),now) for i in range(len(ids)) for j in range(len(subs))])
            summer_scores=[(ids[i],subs[j],summer,(36 if i==10 and j==0 else 38 if i==10 and j==2 else max(0,min(100,scores[i][j]+3+(i*2+j)%4))),now) for i in range(len(ids)) for j in range(len(subs))]
            c.executemany("insert into marks(student_id,subject_id,term_id,score,updated_at,source) values(?,?,?,?,?,'sample')",summer_scores)
            log(c,'System','Sample data initialized','11 students, 5 subjects, 3 terms. Sample data.')
        # Keep the demonstration leader current without overwriting any mark saved or imported by a user.
        now=datetime.now().isoformat(timespec='seconds')
        c.execute("update marks set score=(select max_marks from subjects where id=marks.subject_id),updated_at=? where student_id='S-1001' and source='sample' and score<(select max_marks from subjects where id=marks.subject_id)",(now,))
        if c.execute('select changes()').fetchone()[0]: log(c,'System','Sample ranking data refreshed','Abhimanyu Zade sample marks set to subject maximums; user-entered marks were preserved.')

def log(c,actor,action,detail): c.execute('insert into events(at,actor,action,detail) values(?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),actor,action,detail))
def rowdicts(cur): return [dict(r) for r in cur.fetchall()]
def get_rules(c):
    row=c.execute("select value from app_settings where key='grading_rules'").fetchone()
    return json.loads(row['value']) if row else DEFAULT_RULES.copy()
def calc(score, maxm=100, passm=40, rules=None):
    pct=(float(score)/float(maxm))*100
    bands=rules or DEFAULT_RULES
    grade='A*' if pct>=bands['A*'] else 'A' if pct>=bands['A'] else 'B' if pct>=bands['B'] else 'C' if pct>=bands['C'] else 'D' if pct>=bands['D'] else 'E' if float(score)>=float(passm) else 'U'
    return {'percentage':round(pct,1),'grade':grade,'passed':float(score)>=float(passm),'gpa':round(max(0,min(4,(pct-50)/12.5)),2)}
def results(c, qs):
    rules=get_rules(c)
    term=qs.get('term',[''])[0]
    if not term and qs.get('all',['0'])[0]!='1':
        current=c.execute('select id from terms where is_current=1').fetchone()
        term=str(current['id']) if current else ''
    cls=qs.get('class',[''])[0]; subject=qs.get('subject',[''])[0]; status=qs.get('status',[''])[0]; q=qs.get('q',[''])[0].lower()
    sql='''select s.id student_id,s.name,s.email,s.class_name,s.roll,sub.id subject_id,sub.name subject,sub.code,sub.max_marks,sub.pass_mark,sub.weight,m.score,m.updated_at,t.id term_id,t.name term
      from marks m join students s on s.id=m.student_id join subjects sub on sub.id=m.subject_id join terms t on t.id=m.term_id where 1=1'''; args=[]
    if term: sql+=' and t.id=?'; args.append(term)
    if cls: sql+=' and s.class_name=?'; args.append(cls)
    if subject: sql+=' and sub.id=?'; args.append(subject)
    if q: sql+=' and (lower(s.name) like ? or lower(s.id) like ? or lower(sub.name) like ?)'; args += ['%'+q+'%']*3
    rows=rowdicts(c.execute(sql,args));
    for r in rows: r.update(calc(r['score'],r['max_marks'],r['pass_mark'],rules))
    # status is derived from current term approval/publication state
    state=c.execute('select action from events where detail like ? order by id desc limit 1',(f"%term_id={term or ''}%",)).fetchone() if term else None
    if status: rows=[r for r in rows if (status=='needs-support' and not r['passed']) or (status=='pass' and r['passed'])]
    return rows

class Handler(BaseHTTPRequestHandler):
    def send(self,obj,status=200,ctype='application/json; charset=utf-8',extra_headers=None):
        body=obj if isinstance(obj,bytes) else json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body)))
        for name,value in (extra_headers or {}).items(): self.send_header(name,value)
        self.end_headers(); self.wfile.write(body)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(n); return json.loads(raw) if raw else {}
    def do_OPTIONS(self): self.send({},204)
    def do_GET(self):
        p=urlparse(self.path); path=p.path; qs=parse_qs(p.query)
        try:
            static={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/styles.css':'styles.css'}
            if path in static:
                file=static[path]; types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}
                with open(os.path.join(ROOT,file),'rb') as f: self.send(f.read(),200,types[os.path.splitext(file)[1]])
                return
            with connect() as c:
                if path=='/api/bootstrap':
                    students=rowdicts(c.execute('select * from students order by class_name,roll')); subjects=rowdicts(c.execute('select * from subjects order by name')); terms=rowdicts(c.execute('select * from terms order by id desc')); ev=rowdicts(c.execute('select * from events order by id desc limit 30'))
                    workflow={str(r['term_id']):r['status'] for r in c.execute('select * from term_workflow')}
                    self.send({'students':students,'subjects':subjects,'terms':terms,'events':ev,'workflow':workflow,'grading_rules':get_rules(c),'results':results(c,qs),'history':results(c,{'all':['1']})}); return
                if path=='/api/results': self.send(results(c,qs)); return
                if path=='/api/template': self.send(b'student_id,subject_code,term,score\nS-1001,RPA,Spring 2026,85\n',200,'text/csv',{'Content-Disposition':'attachment; filename="meridian-marks-template.csv"'}); return
                if path=='/api/report':
                    sid=qs.get('student',[''])[0]; term=qs.get('term',[''])[0]; st=c.execute('select * from students where id=?',(sid,)).fetchone()
                    if not st: self.send({'error':'Student not found'},404); return
                    rs=results(c,{'q':[sid],'term':[term] if term else []}); self.send({'student':dict(st),'results':rs}); return
                if path=='/api/export':
                    rows=results(c,qs); out=io.StringIO(); w=csv.writer(out); w.writerow(['Student ID','Student','Class','Subject','Term','Score','Max marks','Percent','Grade','Outcome'])
                    for r in rows:w.writerow([r['student_id'],r['name'],r['class_name'],r['subject'],r['term'],r['score'],r['max_marks'],r['percentage'],r['grade'],'Pass' if r['passed'] else 'Support needed'])
                    self.send(out.getvalue().encode(),200,'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="meridian-results.csv"'}); return
                self.send({'error':'Not found'},404)
        except Exception as e:self.send({'error':str(e)},500)
    def do_POST(self):
        path=urlparse(self.path).path
        try:
            data=self.body()
            with connect() as c:
                actor=data.get('actor','Administrator')
                if path=='/api/students':
                    if data.get('role')!='Administrator': raise ValueError('Only an administrator can add student records.')
                    sid=data.get('id','').strip() or 'S-'+uuid.uuid4().hex[:6].upper(); name=data.get('name','').strip(); cls=data.get('class_name','').strip(); roll=data.get('roll','').strip()
                    if not name or not cls or not roll: raise ValueError('Name, class, and roll number are required.')
                    c.execute('insert into students values(?,?,?,?,?)',(sid,name,data.get('email','').strip(),cls,roll)); log(c,actor,'Student added',f'{name} ({sid})'); self.send({'ok':True,'id':sid}); return
                if path=='/api/students/update':
                    if data.get('role')!='Administrator': raise ValueError('Only an administrator can edit student records.')
                    sid=data.get('id','').strip(); name=data.get('name','').strip(); cls=data.get('class_name','').strip(); roll=data.get('roll','').strip()
                    if not sid or not name or not cls or not roll: raise ValueError('Name, class, and roll number are required.')
                    if not c.execute('select 1 from students where id=?',(sid,)).fetchone(): raise ValueError('Student not found.')
                    c.execute('update students set name=?,email=?,class_name=?,roll=? where id=?',(name,data.get('email','').strip(),cls,roll,sid));log(c,actor,'Student updated',f'{name} ({sid})');self.send({'ok':True});return
                if path=='/api/subjects':
                    if data.get('role')!='Administrator': raise ValueError('Only an administrator can manage subjects.')
                    name=data.get('name','').strip(); code=data.get('code','').strip().upper(); maximum=float(data.get('max_marks',100)); passing=float(data.get('pass_mark',40))
                    if not name or not code or maximum<=0 or passing<0 or passing>maximum: raise ValueError('Provide a name, code, positive maximum, and valid pass mark.')
                    sid='SUB-'+uuid.uuid4().hex[:6].upper(); c.execute('insert into subjects values(?,?,?,?,?,?)',(sid,name,code,maximum,passing,float(data.get('weight',1))));log(c,actor,'Subject added',f'{name} ({code})');self.send({'ok':True,'id':sid});return
                if path=='/api/subjects/update':
                    if data.get('role')!='Administrator': raise ValueError('Only an administrator can edit subjects.')
                    sid=data.get('id');name=data.get('name','').strip();code=data.get('code','').strip().upper();maximum=float(data.get('max_marks',100));passing=float(data.get('pass_mark',40));weight=float(data.get('weight',1))
                    if not name or not code or maximum<=0 or passing<0 or passing>maximum or weight<=0: raise ValueError('Provide a name, code, positive maximum and weight, and valid pass mark.')
                    subject=c.execute('select * from subjects where id=?',(sid,)).fetchone()
                    if not subject:raise ValueError('Subject not found.')
                    if c.execute('select 1 from marks where subject_id=? and score>? limit 1',(sid,maximum)).fetchone():raise ValueError('Maximum cannot be lower than an existing recorded score.')
                    c.execute('update subjects set name=?,code=?,max_marks=?,pass_mark=?,weight=? where id=?',(name,code,maximum,passing,weight,sid));log(c,actor,'Subject updated',f'{name} ({code})');self.send({'ok':True});return
                if path=='/api/terms':
                    if data.get('role')!='Administrator': raise ValueError('Only an administrator can manage academic terms.')
                    name=data.get('name','').strip()
                    if not name:raise ValueError('Term name is required.')
                    c.execute('insert into terms(name,is_current) values(?,0)',(name,));log(c,actor,'Term added',name);self.send({'ok':True});return
                if path=='/api/marks':
                    if data.get('role') not in ('Teacher','Administrator'): raise ValueError('Teacher access required to record marks.')
                    try:score=float(data.get('score'))
                    except (TypeError,ValueError):raise ValueError('Score must be numeric.')
                    student=c.execute('select * from students where id=?',(data.get('student_id'),)).fetchone(); subject=c.execute('select * from subjects where id=?',(data.get('subject_id'),)).fetchone(); term=c.execute('select * from terms where id=?',(data.get('term_id'),)).fetchone()
                    if not student or not subject or not term:raise ValueError('Choose a valid student, subject, and term.')
                    if score<0 or score>subject['max_marks']:raise ValueError(f"Score must be between 0 and {subject['max_marks']} for {subject['name']}.")
                    c.execute("insert into marks(student_id,subject_id,term_id,score,updated_at,source) values(?,?,?,?,?,'user') on conflict(student_id,subject_id,term_id) do update set score=excluded.score,updated_at=excluded.updated_at,source='user'",(student['id'],subject['id'],term['id'],score,datetime.now().isoformat(timespec='seconds')));log(c,actor,'Mark saved',f"{student['name']} · {subject['code']} · {term['name']} · {score}");self.send({'ok':True});return
                if path=='/api/import/preview':
                    if data.get('role') not in ('Teacher','Administrator'): raise ValueError('Teacher access required to import marks.')
                    content=data.get('csv',''); raw=list(csv.DictReader(io.StringIO(content))); mapping=data.get('mapping',{}); term_by={r['name'].lower():r['id'] for r in c.execute('select * from terms')}; st_by={r['id'].lower():r['id'] for r in c.execute('select id from students')}; st_by.update({r['name'].lower():r['id'] for r in c.execute('select id,name from students')}); sub_by={r['code'].lower():r for r in c.execute('select * from subjects')}; sub_by.update({r['name'].lower():r for r in c.execute('select * from subjects')}); seen=set(); out=[]
                    for ix,row in enumerate(raw,2):
                        def val(key,default): return str(row.get(mapping.get(key,default),'')).strip()
                        sid=st_by.get(val('student','student_id').lower()); sub=sub_by.get(val('subject','subject_code').lower()); term=term_by.get(val('term','term').lower()); score_txt=val('score','score'); errs=[]
                        try: score=float(score_txt)
                        except: score=None
                        if not sid:errs.append('Unknown student ID/name')
                        if not sub:errs.append('Unknown subject code/name')
                        if not term:errs.append('Unknown term')
                        if score is None:errs.append('Score must be numeric')
                        elif sub and (score<0 or score>sub['max_marks']):errs.append(f"Score must be 0–{sub['max_marks']}")
                        key=(sid,sub['id'] if sub else '',term)
                        if key in seen:errs.append('Duplicate row in this file')
                        seen.add(key)
                        if sid and sub and term and c.execute('select 1 from marks where student_id=? and subject_id=? and term_id=?',key).fetchone():errs.append('Existing mark will be updated')
                        out.append({'line':ix,'student_id':sid or val('student','student_id'),'student':c.execute('select name from students where id=?',(sid,)).fetchone()[0] if sid else val('student','student_id'),'subject':sub['name'] if sub else val('subject','subject_code'),'term':val('term','term'),'score':score_txt,'errors':errs,'valid':not any(e!='Existing mark will be updated' for e in errs),'update': 'Existing mark will be updated' in errs})
                    self.send({'rows':out,'valid':sum(1 for r in out if r['valid']),'errors':sum(1 for r in out if not r['valid'])});return
                if path=='/api/import/commit':
                    if data.get('role') not in ('Teacher','Administrator'): raise ValueError('Teacher access required to import marks.')
                    n=0; seen=set()
                    for r in data.get('rows',[]):
                        if not r.get('valid'):continue
                        student=c.execute('select id from students where id=?',(r.get('student_id'),)).fetchone();sub=c.execute('select * from subjects where name=?',(r.get('subject'),)).fetchone();term=c.execute('select id from terms where name=?',(r.get('term'),)).fetchone()
                        if not student or not sub or not term:raise ValueError('An imported row refers to an unknown student, subject, or term.')
                        try:score=float(r.get('score'))
                        except (TypeError,ValueError):raise ValueError('Imported scores must be numeric.')
                        if score<0 or score>sub['max_marks']:raise ValueError(f"Score must be between 0 and {sub['max_marks']} for {sub['name']}.")
                        key=(student['id'],sub['id'],term['id'])
                        if key in seen:raise ValueError('The import payload contains duplicate student-subject-term rows.')
                        seen.add(key)
                        c.execute("insert into marks(student_id,subject_id,term_id,score,updated_at,source) values(?,?,?,?,?,'user') on conflict(student_id,subject_id,term_id) do update set score=excluded.score,updated_at=excluded.updated_at,source='user'",(student['id'],sub['id'],term['id'],score,datetime.now().isoformat(timespec='seconds')));n+=1
                    log(c,actor,'Marks imported',f'{n} rows processed');self.send({'ok':True,'count':n});return
                if path=='/api/workflow':
                    action=data.get('action');term=data.get('term_id');role=data.get('role','Teacher');
                    if action not in ('submit','approve','publish','return'):raise ValueError('Unknown workflow action.')
                    if action in ('submit','return') and role not in ('Teacher','Administrator'):raise ValueError('Teacher access required.')
                    if action in ('approve','publish') and role!='Administrator':raise ValueError('Administrator access required.')
                    termrow=c.execute('select name from terms where id=?',(term,)).fetchone()
                    if not termrow:raise ValueError('Select a valid term.')
                    state=c.execute('select status from term_workflow where term_id=?',(term,)).fetchone(); state=state['status'] if state else 'Draft'
                    allowed={'submit':('Draft','Returned for correction'),'return':('Submitted for review',),'approve':('Submitted for review',),'publish':('Approved',)}
                    if state not in allowed[action]: raise ValueError(f"Cannot {action} while this term is {state.lower()}.")
                    label={'submit':'Submitted for review','approve':'Approved','publish':'Published','return':'Returned for correction'}[action]
                    c.execute('insert into term_workflow(term_id,status,updated_at) values(?,?,?) on conflict(term_id) do update set status=excluded.status,updated_at=excluded.updated_at',(term,label,datetime.now().isoformat(timespec='seconds')))
                    log(c,actor,label,f"term_id={term} · {termrow['name']}");self.send({'ok':True});return
                if path=='/api/terms/current':
                    if data.get('role')!='Administrator': raise ValueError('Only an administrator can change the current term.')
                    current=c.execute('select name from terms where id=?',(data.get('term_id'),)).fetchone()
                    if not current:raise ValueError('Select a valid term.')
                    c.execute('update terms set is_current=0');c.execute('update terms set is_current=1 where id=?',(data.get('term_id'),));log(c,actor,'Current term changed',current['name']);self.send({'ok':True});return
                if path=='/api/grading-rules':
                    if data.get('role')!='Administrator':raise ValueError('Only an administrator can edit grading rules.')
                    raw=data.get('rules',{}); names=['A*','A','B','C','D']
                    try:rules={k:float(raw[k]) for k in names}
                    except (KeyError,TypeError,ValueError):raise ValueError('Enter a numeric threshold for every grade band.')
                    values=[rules[k] for k in names]
                    if any(not math.isfinite(x) or x<0 or x>100 for x in values):raise ValueError('Grade thresholds must be between 0 and 100.')
                    if any(values[i]<values[i+1] for i in range(len(values)-1)):raise ValueError('Thresholds must descend from A* through D.')
                    c.execute("insert into app_settings(key,value) values('grading_rules',?) on conflict(key) do update set value=excluded.value",(json.dumps(rules),));log(c,actor,'Grading rules updated',', '.join(f'{k} {rules[k]:g}%' for k in names));self.send({'ok':True,'rules':rules});return
                self.send({'error':'Not found'},404)
        except (ValueError,sqlite3.IntegrityError) as e:self.send({'error':str(e)},400)
        except Exception as e:self.send({'error':str(e)},500)
    def log_message(self,*args):pass

if __name__=='__main__':
    init(); port=int(os.environ.get('PORT','8000')); host=os.environ.get('HOST','0.0.0.0'); print(f'Meridian running at http://{host}:{port}'); ThreadingHTTPServer((host,port),Handler).serve_forever()
