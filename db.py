import sqlite3, hashlib, os, math
from pathlib import Path
from datetime import datetime
DATA_DIR=Path(os.environ.get("INSIGHTEDU_DATA_DIR", str(Path(__file__).parent/"data"))).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB=Path(os.environ.get("INSIGHTEDU_DATABASE_PATH", str(DATA_DIR/"insightedu_ai.db"))).expanduser()
DB.parent.mkdir(parents=True, exist_ok=True)
def con():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def hp(p,s=None):
 s=s or os.urandom(16).hex(); return s+"$"+hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(s),160000).hex()
def verify(p,h):
 try: s,d=h.split("$"); return hp(p,s).split("$")[1]==d
 except: return False
def init_db():
 with con() as c:
  c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,display TEXT,role TEXT,password TEXT,teacher_id INTEGER,active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY,teacher_id INTEGER,name TEXT,subject TEXT,year TEXT,description TEXT);
  CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE,teacher_id INTEGER,class_id INTEGER,usn TEXT UNIQUE,name TEXT,cie1 REAL DEFAULT 0,cie2 REAL DEFAULT 0,attendance REAL DEFAULT 0,assignment REAL DEFAULT 0,gpa REAL DEFAULT 0,backlogs INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,teacher_id INTEGER,action TEXT,details TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS assignments(
   id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, class_id INTEGER NOT NULL,
   title TEXT NOT NULL, description TEXT DEFAULT '', filename TEXT NOT NULL,
   stored_path TEXT NOT NULL, uploaded_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS abl_activities(
   id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, class_id INTEGER NOT NULL,
   semester TEXT NOT NULL, title TEXT NOT NULL, activity_date TEXT NOT NULL,
   description TEXT DEFAULT '', max_marks REAL DEFAULT 10
  );
  CREATE TABLE IF NOT EXISTS abl_marks(
   id INTEGER PRIMARY KEY, activity_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
   marks REAL DEFAULT 0, UNIQUE(activity_id,student_id),
   FOREIGN KEY(activity_id) REFERENCES abl_activities(id) ON DELETE CASCADE,
   FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
  );
  CREATE TABLE IF NOT EXISTS semester_sgpa(
   id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
   semester TEXT NOT NULL, sgpa REAL NOT NULL CHECK(sgpa>=0 AND sgpa<=10),
   updated_at TEXT NOT NULL, UNIQUE(student_id,semester),
   FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
  );
  CREATE TABLE IF NOT EXISTS daily_attendance(
   id INTEGER PRIMARY KEY,
   teacher_id INTEGER NOT NULL,
   class_id INTEGER NOT NULL,
   student_id INTEGER NOT NULL,
   attendance_date TEXT NOT NULL,
   status TEXT NOT NULL CHECK(status IN ('Present','Absent')),
   updated_at TEXT NOT NULL,
   UNIQUE(student_id,attendance_date),
   FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
  );""")
  cols=[x["name"] for x in c.execute("PRAGMA table_info(users)")]
  if "active" not in cols: c.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")
def create_initial_admin(username,password):
 username=(username or "").strip().lower()
 if not username or len(password or "")<12:
  raise ValueError("Set an admin username and a password of at least 12 characters.")
 with con() as c:
  if c.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone():
   return False
  c.execute("INSERT INTO users(username,display,role,password,active) VALUES(?,?,?,?,1)",
   (username,"InsightEdu AI Administrator","admin",hp(password)))
  return True

def auth(username,role,password,unused=None):
 with con() as c:
  x=c.execute("select * from users where username=? and role=? and active=1",(username,role)).fetchone()
  if x and verify(password,x["password"]): return dict(id=x["id"],username=x["username"],display_name=x["display"],role=x["role"])
def teacher_classes(t):
 with con() as c:return [dict(x) for x in c.execute("select * from classes where teacher_id=? order by name",(t,))]
def class_students(cid,t):
 with con() as c:return [dict(x) for x in c.execute("select * from students where class_id=? and teacher_id=? order by usn",(cid,t))]
def add_class(t,n,s,y,d):
 with con() as c:c.execute("insert into classes(teacher_id,name,subject,year,description) values(?,?,?,?,?)",(t,n,s,y,d))
def remove_class(cid,t):
 with con() as c:c.execute("delete from classes where id=? and teacher_id=?",(cid,t))
def add_student(t,cid,usn,name,pw):
 if not usn or not name.strip(): raise ValueError("USN and name required.")
 with con() as c:
  if not c.execute("select id from classes where id=? and teacher_id=?",(cid,t)).fetchone(): raise ValueError("Class ownership check failed.")
  x=c.execute("insert into users(username,display,role,password,teacher_id,active) values(?,?,?,?,?,1)",(usn,name,"student",hp(pw),t))
  c.execute("insert into students(user_id,teacher_id,class_id,usn,name) values(?,?,?,?,?)",(x.lastrowid,t,cid,usn,name))
def update_student(sid,t,**v):
 allowed={"cie1","cie2","attendance","assignment","gpa","backlogs"}
 if not set(v)<=allowed: raise ValueError("Invalid fields.")
 for key,value in v.items():
  if key in {"cie1","cie2","attendance","assignment"} and not 0 <= float(value) <= 100:
   raise ValueError(f"{key} must be between 0 and 100.")
  if key=="backlogs" and int(value)<0:
   raise ValueError("Backlogs cannot be negative.")
 with con() as c:
  if not c.execute("select id from students where id=? and teacher_id=?",(sid,t)).fetchone(): raise ValueError("Student ownership check failed.")
  c.execute("update students set "+",".join(k+"=?" for k in v)+" where id=? and teacher_id=?",(*v.values(),sid,t))
def student_record(usn):
 with con() as c:
  x=c.execute("select s.*,u.active from students s join users u on u.id=s.user_id where s.usn=?",(usn,)).fetchone(); return dict(x) if x else None
def attendance_for_date(class_id,teacher_id,attendance_date):
 with con() as c:
  rows=c.execute("""SELECT s.id AS student_id,s.usn,s.name,da.status
   FROM students s LEFT JOIN daily_attendance da
   ON da.student_id=s.id AND da.attendance_date=?
   WHERE s.class_id=? AND s.teacher_id=? ORDER BY s.usn""",(attendance_date,class_id,teacher_id))
  return [dict(x) for x in rows]
def save_daily_attendance(class_id,teacher_id,attendance_date,entries):
 if not attendance_date: raise ValueError("Attendance date is required.")
 if not entries: raise ValueError("No students found in this class.")
 with con() as c:
  if not c.execute("SELECT id FROM classes WHERE id=? AND teacher_id=?",(class_id,teacher_id)).fetchone():
   raise ValueError("Class ownership check failed.")
  valid={r["id"] for r in c.execute("SELECT id FROM students WHERE class_id=? AND teacher_id=?",(class_id,teacher_id))}
  now=datetime.utcnow().isoformat()
  for student_id,status in entries.items():
   if student_id not in valid: raise ValueError("Student ownership check failed.")
   if status not in ("Present","Absent"): raise ValueError("Invalid attendance status.")
   c.execute("""INSERT INTO daily_attendance(teacher_id,class_id,student_id,attendance_date,status,updated_at)
    VALUES(?,?,?,?,?,?) ON CONFLICT(student_id,attendance_date)
    DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at""",
    (teacher_id,class_id,student_id,attendance_date,status,now))
  # Recalculate percentage using all recorded attendance days for each student.
  for student_id in entries:
   c.execute("""UPDATE students SET attendance=(
    SELECT ROUND(100.0*SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END)/COUNT(*),1)
    FROM daily_attendance WHERE student_id=?
   ) WHERE id=? AND teacher_id=?""",(student_id,student_id,teacher_id))
def attendance_history(class_id,teacher_id,limit=200):
 with con() as c:
  rows=c.execute("""SELECT da.attendance_date,s.usn,s.name,da.status,da.updated_at
   FROM daily_attendance da JOIN students s ON s.id=da.student_id
   WHERE da.class_id=? AND da.teacher_id=?
   ORDER BY da.attendance_date DESC,s.usn LIMIT ?""",(class_id,teacher_id,limit))
  return [dict(x) for x in rows]
def audit(t,a,d):
 with con() as c:c.execute("insert into audit(teacher_id,action,details,created) values(?,?,?,?)",(t,a,d,datetime.utcnow().isoformat()))
def audit_rows(t):
 with con() as c:return [dict(x) for x in c.execute("select action,details,created from audit where teacher_id=? order by id desc",(t,))]
def create_teacher(username,name,password):
 username=username.strip().lower()
 if not username or not name.strip() or len(password)<12: raise ValueError("Enter username, name and a password of at least 12 characters.")
 with con() as c:
  c.execute("INSERT INTO users(username,display,role,password,active) VALUES(?,?,?,?,1)",(username,name.strip(),"teacher",hp(password)))
def list_teachers():
 with con() as c:return [dict(x) for x in c.execute("SELECT u.id,u.username,u.display,u.active,(SELECT COUNT(*) FROM classes cl WHERE cl.teacher_id=u.id) AS class_count,(SELECT COUNT(*) FROM students s WHERE s.teacher_id=u.id) AS student_count FROM users u WHERE role='teacher' ORDER BY display")]
def set_teacher_active(teacher_id,active):
 with con() as c:c.execute("UPDATE users SET active=? WHERE id=? AND role='teacher'",(1 if active else 0,teacher_id))
def reset_teacher_password(teacher_id,password):
 if len(password)<12: raise ValueError("Password must contain at least 12 characters.")
 with con() as c:c.execute("UPDATE users SET password=? WHERE id=? AND role='teacher'",(hp(password),teacher_id))
def reset_student_password(student_id,teacher_id,password):
 if len(password)<12: raise ValueError("Password must contain at least 12 characters.")
 with con() as c:
  row=c.execute("SELECT user_id FROM students WHERE id=? AND teacher_id=?",(student_id,teacher_id)).fetchone()
  if not row: raise ValueError("Student ownership check failed.")
  c.execute("UPDATE users SET password=? WHERE id=? AND role='student'",(hp(password),row["user_id"]))
def admin_overview():
 with con() as c:
  return {"teachers":c.execute("SELECT COUNT(*) FROM users WHERE role='teacher'").fetchone()[0],"classes":c.execute("SELECT COUNT(*) FROM classes").fetchone()[0],"students":c.execute("SELECT COUNT(*) FROM students").fetchone()[0]}


def set_one_attendance(class_id,teacher_id,student_id,attendance_date,status):
 save_daily_attendance(class_id,teacher_id,attendance_date,{student_id:status})

def add_assignment(teacher_id,class_id,title,description,filename,stored_path):
 with con() as c:
  if not c.execute("SELECT id FROM classes WHERE id=? AND teacher_id=?",(class_id,teacher_id)).fetchone():
   raise ValueError("Class ownership check failed.")
  cur=c.execute("INSERT INTO assignments(teacher_id,class_id,title,description,filename,stored_path,uploaded_at) VALUES(?,?,?,?,?,?,?)",
   (teacher_id,class_id,title.strip(),description.strip(),filename,stored_path,datetime.utcnow().isoformat()))
  return cur.lastrowid
def list_assignments(class_id,teacher_id):
 with con() as c:return [dict(x) for x in c.execute("SELECT * FROM assignments WHERE class_id=? AND teacher_id=? ORDER BY uploaded_at DESC",(class_id,teacher_id))]
def student_assignments(student_id):
 with con() as c:
  return [dict(x) for x in c.execute("""SELECT a.* FROM assignments a JOIN students s ON s.class_id=a.class_id
   WHERE s.id=? ORDER BY a.uploaded_at DESC""",(student_id,))]
def update_assignment(assignment_id,teacher_id,title,description):
 with con() as c:c.execute("UPDATE assignments SET title=?,description=? WHERE id=? AND teacher_id=?",(title.strip(),description.strip(),assignment_id,teacher_id))
def delete_assignment(assignment_id,teacher_id):
 with con() as c:
  row=c.execute("SELECT stored_path FROM assignments WHERE id=? AND teacher_id=?",(assignment_id,teacher_id)).fetchone()
  if row:
   c.execute("DELETE FROM assignments WHERE id=? AND teacher_id=?",(assignment_id,teacher_id))
   return row["stored_path"]
def add_abl_activity(teacher_id,class_id,semester,title,activity_date,description,max_marks):
 with con() as c:
  if not c.execute("SELECT id FROM classes WHERE id=? AND teacher_id=?",(class_id,teacher_id)).fetchone():
   raise ValueError("Class ownership check failed.")
  cur=c.execute("INSERT INTO abl_activities(teacher_id,class_id,semester,title,activity_date,description,max_marks) VALUES(?,?,?,?,?,?,?)",
   (teacher_id,class_id,semester,title.strip(),activity_date,description.strip(),max_marks))
  return cur.lastrowid
def list_abl_activities(class_id,teacher_id):
 with con() as c:return [dict(x) for x in c.execute("SELECT * FROM abl_activities WHERE class_id=? AND teacher_id=? ORDER BY semester,activity_date DESC",(class_id,teacher_id))]
def save_abl_marks(activity_id,teacher_id,class_id,marks):
 with con() as c:
  act=c.execute("SELECT id,max_marks FROM abl_activities WHERE id=? AND teacher_id=? AND class_id=?",(activity_id,teacher_id,class_id)).fetchone()
  if not act: raise ValueError("Activity ownership check failed.")
  for score in marks.values():
   if not math.isfinite(float(score)) or not 0 <= float(score) <= float(act["max_marks"]):
    raise ValueError(f"Activity marks must be between 0 and {act['max_marks']}.")
  valid={r["id"] for r in c.execute("SELECT id FROM students WHERE class_id=? AND teacher_id=?",(class_id,teacher_id))}
  for sid,score in marks.items():
   if sid not in valid: raise ValueError("Student ownership check failed.")
   c.execute("INSERT INTO abl_marks(activity_id,student_id,marks) VALUES(?,?,?) ON CONFLICT(activity_id,student_id) DO UPDATE SET marks=excluded.marks",(activity_id,sid,float(score)))
def abl_activity_students(activity_id,teacher_id,class_id):
 with con() as c:
  return [dict(x) for x in c.execute("""SELECT s.id,s.usn,s.name,COALESCE(m.marks,0) marks
   FROM students s LEFT JOIN abl_marks m ON m.student_id=s.id AND m.activity_id=?
   WHERE s.class_id=? AND s.teacher_id=? ORDER BY s.usn""",(activity_id,class_id,teacher_id))]
def student_abl_records(student_id):
 with con() as c:return [dict(x) for x in c.execute("""SELECT a.semester,a.title,a.activity_date,a.description,a.max_marks,m.marks
  FROM abl_activities a JOIN abl_marks m ON m.activity_id=a.id
  WHERE m.student_id=? ORDER BY a.semester,a.activity_date DESC""",(student_id,))]

def replace_assignment_file(assignment_id,teacher_id,filename,stored_path):
 with con() as c:
  row=c.execute("SELECT stored_path FROM assignments WHERE id=? AND teacher_id=?",(assignment_id,teacher_id)).fetchone()
  if not row: raise ValueError("Assignment ownership check failed.")
  c.execute("UPDATE assignments SET filename=?,stored_path=?,uploaded_at=? WHERE id=? AND teacher_id=?",
   (filename,stored_path,datetime.utcnow().isoformat(),assignment_id,teacher_id))
  return row["stored_path"]


def save_semester_sgpa(student_id,teacher_id,semester,sgpa):
 if not semester.strip(): raise ValueError("Select a semester.")
 if not math.isfinite(float(sgpa)) or not 0 <= float(sgpa) <= 10: raise ValueError("SGPA must be a valid number between 0 and 10.")
 with con() as c:
  if not c.execute("SELECT id FROM students WHERE id=? AND teacher_id=?",(student_id,teacher_id)).fetchone():
   raise ValueError("Student ownership check failed.")
  c.execute("""INSERT INTO semester_sgpa(teacher_id,student_id,semester,sgpa,updated_at)
   VALUES(?,?,?,?,?) ON CONFLICT(student_id,semester)
   DO UPDATE SET sgpa=excluded.sgpa,updated_at=excluded.updated_at""",
   (teacher_id,student_id,semester.strip(),float(sgpa),datetime.utcnow().isoformat()))
def semester_sgpa_records(student_id):
 with con() as c:return [dict(x) for x in c.execute("SELECT semester,sgpa,updated_at FROM semester_sgpa WHERE student_id=? ORDER BY CAST(REPLACE(semester,'Semester ','') AS INTEGER)",(student_id,))]
def delete_semester_sgpa(student_id,teacher_id,semester):
 with con() as c:c.execute("DELETE FROM semester_sgpa WHERE student_id=? AND teacher_id=? AND semester=?",(student_id,teacher_id,semester))


def change_admin_password(admin_id,current_password,new_password,confirm_password):
 if len(new_password)<12: raise ValueError("New password must contain at least 12 characters.")
 if new_password != confirm_password: raise ValueError("The new passwords do not match.")
 with con() as c:
  row=c.execute("SELECT password FROM users WHERE id=? AND role='admin' AND active=1",(admin_id,)).fetchone()
  if not row: raise ValueError("Admin account not found or inactive.")
  if not verify(current_password,row["password"]): raise ValueError("Current password is incorrect.")
  c.execute("UPDATE users SET password=? WHERE id=? AND role='admin'",(hp(new_password),admin_id))


def any_admin_exists():
 with con() as c:
  return c.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone() is not None
