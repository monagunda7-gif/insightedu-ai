import streamlit as st
import os
from db import *
from ml.predict import predict_risk
from ui import *
st.set_page_config(page_title="InsightEdu AI",page_icon="🎓",layout="wide")
st.markdown("""
<style>
:root { --ink:#18243a; --muted:#718096; --line:#e7edf5; }
.stApp { background:linear-gradient(180deg,#f5f8ff 0%,#f8fafc 42%,#ffffff 100%); color:var(--ink); }
section[data-testid="stSidebar"] { background:linear-gradient(180deg,#17243b 0%,#243b61 100%); }
section[data-testid="stSidebar"] * { color:#f4f7ff !important; }
section[data-testid="stSidebar"] button { border:1px solid #536887 !important; border-radius:10px !important; }
div[data-testid="stMetric"] { background:white; border:1px solid var(--line); padding:16px 18px; border-radius:16px; box-shadow:0 5px 18px rgba(26,49,87,.05); min-width:0; overflow:visible; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { min-width:0; overflow:visible; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] > div { font-size:clamp(1.05rem, 2vw, 1.85rem) !important; line-height:1.25 !important; white-space:normal !important; overflow-wrap:anywhere !important; word-break:normal !important; }
div[data-testid="stMetric"] [data-testid="stMetricLabel"] { white-space:normal !important; overflow-wrap:anywhere !important; }
div[data-testid="stDataFrame"], div[data-testid="stTable"] { width:100%; max-width:100%; overflow-x:auto !important; }
div[data-testid="stDataFrame"] iframe { max-width:100%; }
div[data-testid="stExpander"] { border:1px solid var(--line); border-radius:14px; background:white; }
.stButton>button, .stDownloadButton>button { border-radius:10px; font-weight:600; min-height:2.5rem; }
.stButton>button[kind="primary"], button[kind="primary"] { background:linear-gradient(90deg,#315ee8,#6948d8); border:0; }
div[data-testid="stDataFrame"], div[data-testid="stTable"] { border-radius:12px; }
h1,h2,h3 { letter-spacing:-.035em; }
</style>
""",unsafe_allow_html=True)
init_db()
if "user" not in st.session_state: st.session_state.user=None
def configured_secret(name):
    try:
        value=st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.environ.get(name)

admin_setup_error=None
if not any_admin_exists():
    setup_username=configured_secret("INSIGHTEDU_ADMIN_USERNAME")
    setup_password=configured_secret("INSIGHTEDU_ADMIN_PASSWORD")
    if setup_username and setup_password:
        try:
            create_initial_admin(setup_username,setup_password)
        except Exception as exc:
            admin_setup_error=str(exc)

def login():
    st.markdown("<div style='padding:24px;border-radius:18px;background:#edf3ff'><h1>InsightEdu AI</h1><p>Explainable early academic risk monitoring</p></div>",unsafe_allow_html=True)
    a,b,c=st.columns(3)
    with a:
        st.subheader("Admin sign in")
        with st.form("al"):
            u=st.text_input("Admin username"); p=st.text_input("Admin password",type="password",key="ap")
            if st.form_submit_button("Sign in as Admin",type="primary"):
                x=auth(u,"admin",p)
                if x: st.session_state.user=x; st.rerun()
                else: st.error("Invalid Admin credentials.")
    with b:
        st.subheader("Teacher sign in")
        with st.form("tl"):
            u=st.text_input("Teacher username"); p=st.text_input("Password",type="password",key="tp")
            if st.form_submit_button("Sign in as Teacher"):
                x=auth(u,"teacher",p)
                if x: st.session_state.user=x; st.rerun()
                else: st.error("Invalid teacher credentials.")
    with c:
        st.subheader("Student sign in")
        with st.form("sl"):
            u=st.text_input("USN / Register number"); p=st.text_input("Password",type="password",key="sp")
            if st.form_submit_button("Sign in as Student"):
                x=auth(u.upper(),"student",p)
                if x: st.session_state.user=x; st.rerun()
                else: st.error("Invalid USN or password.")
    if admin_setup_error:
        st.error(f"Admin setup failed: {admin_setup_error}")
    if not any_admin_exists():
        st.warning("Administrator account is not configured yet. Set INSIGHTEDU_ADMIN_USERNAME and INSIGHTEDU_ADMIN_PASSWORD in your deployment environment or Streamlit secrets, then restart the app.")
    st.info("Risk scores are illustrative rule-based estimates, not validated predictions. Use fictional or appropriately protected data only.")
if not st.session_state.user: login(); st.stop()
u=st.session_state.user
st.sidebar.markdown("## ◈ InsightEdu AI")
st.sidebar.write(u["display_name"])
if st.sidebar.button("Sign out"):
    for session_key in list(st.session_state.keys()):
        del st.session_state[session_key]
    st.rerun()
if u["role"]=="admin":
    with st.sidebar.expander("Change admin password", expanded=False):
        with st.form("admin_change_password_form"):
            current_admin_pw=st.text_input("Current password",type="password",key="admin_current_pw")
            new_admin_pw=st.text_input("New password (minimum 12 characters)",type="password",key="admin_new_pw")
            confirm_admin_pw=st.text_input("Confirm new password",type="password",key="admin_confirm_pw")
            if st.form_submit_button("Update admin password",type="primary"):
                try:
                    change_admin_password(u["id"],current_admin_pw,new_admin_pw,confirm_admin_pw)
                    st.success("Admin password updated successfully.")
                except Exception as e:
                    st.error(str(e))
    page=st.sidebar.radio("Admin workspace",["Overview","Teacher Accounts","Student Directory"])
    if page=="Overview":
        header("Admin overview","Manage teacher accounts and oversee class activity.")
        stats=admin_overview()
        a,b,c=st.columns(3); a.metric("Teacher accounts",stats["teachers"]); b.metric("Classes",stats["classes"]); c.metric("Students",stats["students"])
        st.subheader("Teacher accounts")
        st.dataframe(list_teachers(),use_container_width=True,hide_index=True)
    elif page=="Teacher Accounts":
        header("Teacher accounts","Create and manage individual teacher access.")
        with st.expander("＋ Create teacher account",expanded=True):
            with st.form("create_teacher"):
                username=st.text_input("Username").strip().lower()
                name=st.text_input("Teacher display name")
                password=st.text_input("Temporary password (minimum 12 characters)",type="password")
                if st.form_submit_button("Create teacher",type="primary"):
                    try:
                        create_teacher(username,name,password)
                        st.success(f"Teacher account '{username}' created.")
                        st.rerun()
                    except Exception as e: st.error(str(e))
        teachers=list_teachers()
        for teacher in teachers:
            with st.container(border=True):
                left,right=st.columns([4,2])
                left.markdown(f"**{teacher['display']}** · `{teacher['username']}`")
                left.caption(f"{teacher['class_count']} classes · {teacher['student_count']} students · {'Active' if teacher['active'] else 'Inactive'}")
                if right.button("Deactivate" if teacher["active"] else "Activate",key=f"active{teacher['id']}"):
                    set_teacher_active(teacher["id"],not bool(teacher["active"]))
                    st.rerun()
                with st.expander(f"Change teacher password · {teacher['username']}"):
                    newpw=st.text_input("New teacher password (minimum 12 characters)",type="password",key=f"pw{teacher['id']}")
                    confirm_newpw=st.text_input("Confirm new password",type="password",key=f"pwconfirm{teacher['id']}")
                    if st.button("Save new password",key=f"reset{teacher['id']}"):
                        try:
                            if newpw != confirm_newpw: raise ValueError("The passwords do not match.")
                            reset_teacher_password(teacher["id"],newpw); st.success("Teacher password changed successfully.")
                        except Exception as e: st.error(str(e))
    else:
        header("Student directory","Read-only overview of enrolled students across teacher-managed classes.")
        import pandas as pd
        from db import con
        with con() as conn:
            rows=[dict(x) for x in conn.execute("SELECT s.usn,s.name,u.display AS teacher,c.name AS class_name,s.cie1,s.cie2,ROUND((s.cie1+s.cie2)/2.0,1) AS cie_average,s.attendance,s.backlogs FROM students s JOIN users u ON u.id=s.teacher_id JOIN classes c ON c.id=s.class_id ORDER BY u.display,c.name,s.usn")]
        st.dataframe(rows,use_container_width=True,hide_index=True)
elif u["role"]=="teacher":
    page=st.sidebar.radio("Workspace",["Overview","My Classes","Student Records","Semester SGPA","Daily Attendance","Assignments","ABL Activity","Risk Prediction","Analytics","Audit Log"])
    classes=teacher_classes(u["id"])
    if page=="Overview":
        header("Teacher overview","Manage your own classes and identify students who may need academic support.")
        students=[s for c in classes for s in class_students(c["id"],u["id"])]
        a,b,c,d=st.columns(4); a.metric("My classes",len(classes)); b.metric("Students",len(students)); c.metric("High risk",sum(predict_risk(s,semester_sgpa_records(s["id"]))["risk"]=="High" for s in students)); d.metric("Assessment","Demo baseline")
        st.subheader("Your classes")
        for cl in classes:
            with st.container(border=True): st.markdown(f"**{cl['name']}** · {cl['subject']}"); st.caption(f"{cl['year']} · {len(class_students(cl['id'],u['id']))} students")
    elif page=="My Classes":
        header("My classes","Create custom classes and sections. Each teacher sees only their own classes.")
        with st.form("newclass"):
            n=st.text_input("Class / section name",placeholder="5A – Data Science"); sub=st.text_input("Subject"); yr=st.text_input("Academic year","2026–2027"); desc=st.text_area("Description")
            if st.form_submit_button("＋ Create class",type="primary"):
                if n and sub: add_class(u["id"],n,sub,yr,desc); st.success("Class created."); st.rerun()
                else: st.error("Class name and subject are required.")
        for cl in classes:
            with st.container(border=True):
                x,y=st.columns([5,1]); x.markdown(f"### {cl['name']}"); x.caption(f"{cl['subject']} · {cl['year']}"); x.write(f"{len(class_students(cl['id'],u['id']))} students")
                if y.button("Delete",key=f"d{cl['id']}"): remove_class(cl["id"],u["id"]); st.rerun()
    elif page=="Student Records":
        header("Student records","Enroll students and update CIE, attendance and academic history.")
        if not classes: st.info("Create a class first.")
        else:
            cm={c["name"]:c for c in classes}; cl=cm[st.selectbox("Class",list(cm))]
            with st.expander("＋ Add student"):
                with st.form("addst"):
                    usn=st.text_input("USN").strip().upper(); name=st.text_input("Student name"); pw=st.text_input("Initial password (minimum 12 characters)",type="password")
                    if st.form_submit_button("Add student"):
                        try: add_student(u["id"],cl["id"],usn,name,pw); st.success("Student enrolled."); st.rerun()
                        except Exception as e: st.error(str(e))
            ss=class_students(cl["id"],u["id"])
            if ss:
                s=st.selectbox("Choose student",ss,format_func=lambda x:f"{x['usn']} · {x['name']}")
                with st.form("edit"):
                    a,b,c=st.columns(3); cie1=a.number_input("CIE-1",0.,100.,float(s["cie1"])); cie2=b.number_input("CIE-2",0.,100.,float(s["cie2"])); att=c.number_input("Attendance %",0.,100.,float(s["attendance"]))
                    a,b,c=st.columns(3); ass=a.number_input("Assignment average",0.,100.,float(s["assignment"])); b.metric("CIE average",f"{(cie1+cie2)/2:.1f}/100"); bl=c.number_input("Backlogs",0,30,int(s["backlogs"]))
                    if st.form_submit_button("Save academic record",type="primary"):
                        update_student(s["id"],u["id"],dict(cie1=cie1,cie2=cie2,attendance=att,assignment=ass,backlogs=bl)); audit(u["id"],"Updated academic record",s["usn"]); st.success("Saved."); st.rerun()
                with st.expander(f"Change password · {s['usn']}"):
                    new_student_pw=st.text_input("New student password (minimum 12 characters)",type="password",key=f"studentpw{s['id']}")
                    confirm_student_pw=st.text_input("Confirm new password",type="password",key=f"studentpwconfirm{s['id']}")
                    if st.button("Save student password",key=f"save_studentpw{s['id']}"):
                        try:
                            if new_student_pw != confirm_student_pw:
                                raise ValueError("The passwords do not match.")
                            reset_student_password(s["id"],u["id"],new_student_pw)
                            audit(u["id"],"Changed student password",s["usn"])
                            st.success(f"Password changed for {s['usn']}.")
                            st.rerun()
                        except Exception as e: st.error(str(e))
                st.dataframe([{"USN":x["usn"],"Name":x["name"],"CIE-1":x["cie1"],"CIE-2":x["cie2"],"CIE average":round((float(x["cie1"])+float(x["cie2"]))/2,1),"Attendance":x["attendance"],"Assignment average":x["assignment"],"Backlogs":x["backlogs"]} for x in ss],use_container_width=True,hide_index=True)
    elif page=="Semester SGPA":
        header("Semester SGPA","Add or update a student's previous semester SGPA. This history is used with current CIE average in the risk estimate.")
        if not classes:
            st.info("Create a class first.")
        else:
            cm={c["name"]:c for c in classes}
            cl=cm[st.selectbox("Class",list(cm),key="sgpa_class")]
            students=class_students(cl["id"],u["id"])
            if students:
                student=st.selectbox("Student",students,format_func=lambda x:f"{x['usn']} · {x['name']}",key="sgpa_student")
                existing=semester_sgpa_records(student["id"])
                with st.form("semester_sgpa_form"):
                    semester=st.selectbox("Semester", [f"Semester {i}" for i in range(1,9)],key="sgpa_semester")
                    old=next((x for x in existing if x["semester"]==semester),None)
                    sgpa=st.number_input("SGPA (out of 10)",min_value=0.0,max_value=10.0,value=float(old["sgpa"]) if old else 0.0,step=0.01,format="%.2f")
                    if st.form_submit_button("Save / Update SGPA",type="primary"):
                        save_semester_sgpa(student["id"],u["id"],semester,sgpa)
                        audit(u["id"],"Saved semester SGPA",f"{student['usn']} · {semester} · {sgpa:.2f}")
                        st.success("Semester SGPA saved."); st.rerun()
                if existing:
                    st.subheader("Past semester performance")
                    import pandas as pd
                    st.dataframe(existing,use_container_width=True,hide_index=True)
                    labels=[x["semester"] for x in existing]
                    chart=pd.DataFrame({"SGPA":[x["sgpa"] for x in existing]},index=labels)
                    st.line_chart(chart,use_container_width=True)
                    remove=st.selectbox("Remove an SGPA record",labels,key="delete_sgpa")
                    if st.button("Delete selected SGPA"):
                        delete_semester_sgpa(student["id"],u["id"],remove)
                        audit(u["id"],"Deleted semester SGPA",f"{student['usn']} · {remove}")
                        st.rerun()
                else:
                    st.info("No past semester SGPA recorded for this student yet.")
            else:
                st.info("Enroll students in this class first.")
    elif page=="Daily Attendance":
        header("Daily attendance","Choose a class and date. Mark each student Present or Absent with one click; reopen any past date to correct it.")
        if not classes:
            st.info("Create a class first.")
        else:
            cm={c["name"]:c for c in classes}
            cl=cm[st.selectbox("Class",list(cm),key="attendance_class")]
            date_value=st.date_input("Attendance date",key="attendance_date")
            date_key=date_value.isoformat()
            rows=attendance_for_date(cl["id"],u["id"],date_key)
            if rows:
                st.caption(f"{len(rows)} students · {date_key}")
                for row in rows:
                    name_col,status_col,present_col,absent_col=st.columns([5,1.5,1.5,1.5])
                    name_col.markdown(f"**{row['usn']}** · {row['name']}")
                    current=row["status"] or "Not marked"
                    status_col.caption(current)
                    if present_col.button("Present",key=f"present_{cl['id']}_{date_key}_{row['student_id']}",type="primary" if current=="Present" else "secondary",use_container_width=True):
                        set_one_attendance(cl["id"],u["id"],row["student_id"],date_key,"Present")
                        audit(u["id"],"Marked attendance",f"{row['usn']} Present · {date_key}")
                        st.rerun()
                    if absent_col.button("Absent",key=f"absent_{cl['id']}_{date_key}_{row['student_id']}",type="primary" if current=="Absent" else "secondary",use_container_width=True):
                        set_one_attendance(cl["id"],u["id"],row["student_id"],date_key,"Absent")
                        audit(u["id"],"Marked attendance",f"{row['usn']} Absent · {date_key}")
                        st.rerun()
            else:
                st.info("No students enrolled in this class.")
            history=attendance_history(cl["id"],u["id"])
            if history:
                with st.expander("Attendance history"):
                    st.dataframe(history,use_container_width=True,hide_index=True)
    elif page=="Assignments":
        header("Assignments","Teachers upload and manage assignment files. Students can view and download them.")
        import os
        from pathlib import Path
        if not classes:
            st.info("Create a class first.")
        else:
            cm={c["name"]:c for c in classes}
            cl=cm[st.selectbox("Class",list(cm),key="assignment_class")]
            with st.expander("＋ Upload assignment",expanded=True):
                with st.form("upload_assignment",clear_on_submit=True):
                    title=st.text_input("Assignment title")
                    description=st.text_area("Instructions / description")
                    uploaded=st.file_uploader("Assignment file (maximum 20 MB)")
                    if st.form_submit_button("Upload assignment",type="primary"):
                        if not title.strip() or uploaded is None:
                            st.error("Enter a title and choose a file.")
                        else:
                            folder=DATA_DIR/"uploads"/str(u["id"])/str(cl["id"])
                            folder.mkdir(parents=True,exist_ok=True)
                            safe_name=os.path.basename(uploaded.name).replace(" ","_")
                            stored=folder/f"{__import__('uuid').uuid4().hex}_{safe_name}"
                            stored.write_bytes(uploaded.getbuffer())
                            add_assignment(u["id"],cl["id"],title,description,uploaded.name,str(stored))
                            audit(u["id"],"Uploaded assignment",f"{cl['name']} · {title}")
                            st.success("Assignment uploaded."); st.rerun()
            for item in list_assignments(cl["id"],u["id"]):
                with st.container(border=True):
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{item['filename']} · {item['uploaded_at'][:10]}")
                    if item["description"]: st.write(item["description"])
                    if os.path.exists(item["stored_path"]):
                        with open(item["stored_path"],"rb") as f:
                            st.download_button("Download file",f.read(),file_name=item["filename"],key=f"teacher_download_{item['id']}")
                    else:
                        st.warning("The uploaded file is missing from storage. Ask the administrator to restore it.")
                    with st.expander("Modify assignment details"):
                        new_title=st.text_input("Title",item["title"],key=f"atitle{item['id']}")
                        new_desc=st.text_area("Description",item["description"],key=f"adesc{item['id']}")
                        replacement=st.file_uploader("Replace uploaded file (optional, maximum 20 MB)",key=f"areplace{item['id']}")
                        if st.button("Save changes",key=f"asave{item['id']}"):
                            update_assignment(item["id"],u["id"],new_title,new_desc)
                            if replacement is not None:
                                folder=DATA_DIR/"uploads"/str(u["id"])/str(cl["id"])
                                folder.mkdir(parents=True,exist_ok=True)
                                safe_name=os.path.basename(replacement.name).replace(" ","_")
                                new_path=folder/f"{__import__('uuid').uuid4().hex}_{safe_name}"
                                new_path.write_bytes(replacement.getbuffer())
                                old_path=replace_assignment_file(item["id"],u["id"],replacement.name,str(new_path))
                                if old_path and os.path.exists(old_path): os.remove(old_path)
                            audit(u["id"],"Modified assignment",item["title"]); st.rerun()
                        if st.button("Delete assignment",key=f"adel{item['id']}"):
                            path=delete_assignment(item["id"],u["id"])
                            if path and os.path.exists(path): os.remove(path)
                            audit(u["id"],"Deleted assignment",item["title"]); st.rerun()
    elif page=="ABL Activity":
        header("ABL activity","Record semester activities and marks for each student.")
        if not classes:
            st.info("Create a class first.")
        else:
            cm={c["name"]:c for c in classes}
            cl=cm[st.selectbox("Class",list(cm),key="abl_class")]
            with st.expander("＋ Add semester activity",expanded=True):
                with st.form("new_abl"):
                    semester=st.selectbox("Semester",[f"Semester {i}" for i in range(1,9)])
                    title=st.text_input("Activity name")
                    activity_date=st.date_input("Activity date")
                    description=st.text_area("Activity description")
                    max_marks=st.number_input("Maximum marks",min_value=1.0,max_value=100.0,value=10.0)
                    if st.form_submit_button("Add activity",type="primary"):
                        if title.strip():
                            add_abl_activity(u["id"],cl["id"],semester,title,activity_date.isoformat(),description,max_marks)
                            audit(u["id"],"Added ABL activity",f"{semester} · {title}"); st.rerun()
                        else: st.error("Enter an activity name.")
            activities=list_abl_activities(cl["id"],u["id"])
            if activities:
                labels={f"{a['semester']} · {a['title']} · {a['activity_date']}":a for a in activities}
                act=labels[st.selectbox("Select activity",list(labels))]
                st.caption(f"{act['description']} · Maximum marks: {act['max_marks']}")
                mark_rows=abl_activity_students(act["id"],u["id"],cl["id"])
                import pandas as pd
                frame=pd.DataFrame([{"USN":r["usn"],"Student":r["name"],"Marks":r["marks"],"Student ID":r["id"]} for r in mark_rows])
                edited=st.data_editor(frame,hide_index=True,use_container_width=True,disabled=["USN","Student","Student ID"],
                    column_order=["USN","Student","Marks"],
                    column_config={"Marks":st.column_config.NumberColumn("Marks",min_value=0,max_value=float(act["max_marks"]),step=0.5)})
                if st.button("Save activity marks",type="primary"):
                    save_abl_marks(act["id"],u["id"],cl["id"],{int(r["Student ID"]):r["Marks"] for _,r in edited.iterrows()})
                    audit(u["id"],"Updated ABL marks",act["title"]); st.success("Activity marks saved."); st.rerun()
            else: st.info("No ABL activities added yet.")
    elif page=="Risk Prediction":
        header("Risk prediction","Explainable demo baseline. Not a trained or validated model.")
        ss=[s for cl in classes for s in class_students(cl["id"],u["id"])]
        if ss:
            s=st.selectbox("Student",ss,format_func=lambda x:f"{x['usn']} · {x['name']}")
            history=semester_sgpa_records(s["id"])
            r=predict_risk(s,history)
            a,b,c=st.columns(3); a.metric("Risk category",r["risk"]); b.metric("Risk score",f"{r['score']}/100"); c.metric("Current CIE average",f"{r['cie_average']}/100")
            st.progress(r["score"]/100,text="Illustrative academic risk score")
            st.write(r["explanation"])
            import pandas as pd
            chart_rows=[{"Assessment":x["semester"],"Score":float(x["sgpa"])} for x in history]
            chart_rows += [{"Assessment":"Current CIE average","Score":r["cie_average"]/10}]
            st.subheader("Academic performance trend")
            st.caption("SGPA is out of 10. Current CIE average is converted from /100 to /10 for a comparable chart.")
            st.line_chart(pd.DataFrame(chart_rows).set_index("Assessment"),use_container_width=True)
            st.subheader("Contributing indicators")
            for k,v,n in r["drivers"]: st.write(f"**{k}:** {v} — {n}")
            st.warning("Do not use this demo score as the sole basis for academic decisions.")
        else: st.info("Add students first.")
    elif page=="Analytics":
        header("Class analytics","Review class-level trends.")
        if classes:
            cl={x["name"]:x for x in classes}[st.selectbox("Class", [x["name"] for x in classes])]
            ss=class_students(cl["id"],u["id"])
            if ss:
                import pandas as pd
                df=pd.DataFrame(ss); a,b,c=st.columns(3); a.metric("Students",len(ss)); b.metric("Avg attendance",f"{df.attendance.mean():.1f}%"); c.metric("Avg CIE",f"{((df.cie1+df.cie2)/2).mean():.1f}")
                st.bar_chart(df.set_index("usn")[["cie1","cie2"]])
                st.dataframe([{"USN":s["usn"],"Name":s["name"],"Risk":predict_risk(s,semester_sgpa_records(s["id"]))["risk"]} for s in ss],hide_index=True,use_container_width=True)
        else: st.info("Create a class first.")
    else:
        header("Audit log","Recent changes made in your teacher account.")
        st.dataframe(audit_rows(u["id"]),use_container_width=True,hide_index=True)
else:
    s=student_record(u["username"])
    if not s: st.error("Student record unavailable."); st.stop()
    page=st.sidebar.radio("Student portal",["My overview","Academic record","Assignments","ABL Activity","Risk assessment"])
    if page=="My overview":
        header(f"Hello, {s['name']}","Your academic snapshot. Your records are read-only.")
        a,b,c,d=st.columns(4); a.metric("CIE-1",f"{s['cie1']}/100"); b.metric("CIE-2",f"{s['cie2']}/100"); c.metric("Attendance",f"{s['attendance']}%"); d.metric("CIE average",f"{(float(s['cie1'])+float(s['cie2']))/2:.1f}/100")
        history=semester_sgpa_records(s["id"])
        r=predict_risk(s,history)
        x,y=st.columns(2); x.metric("Risk category",r["risk"]); y.metric("Illustrative risk score",f"{r['score']}/100")
        st.progress(r["score"]/100,text="Academic risk estimate")
        st.write(r["explanation"])
        if history:
            import pandas as pd
            chart_rows=[{"Assessment":x["semester"],"Score":float(x["sgpa"])} for x in history]
            chart_rows += [{"Assessment":"Current CIE average","Score":r["cie_average"]/10}]
            st.subheader("Your academic trend")
            st.line_chart(pd.DataFrame(chart_rows).set_index("Assessment"),use_container_width=True)
        else:
            st.info("Your teacher has not added past semester SGPA yet. Your current risk estimate uses CIE average only.")
    elif page=="Academic record":
        header("My academic record","Only your teacher can update these details.")
        sgpa_history=semester_sgpa_records(s["id"])
        record_rows=[{"Metric":k,"Value":v} for k,v in {"CIE-1":s["cie1"],"CIE-2":s["cie2"],"Attendance":f"{s['attendance']}%","Assignment average":s["assignment"],"CIE average":round((float(s["cie1"])+float(s["cie2"]))/2,1),"Backlogs":s["backlogs"]}.items()]
        record_rows += [{"Metric":x["semester"]+" SGPA","Value":x["sgpa"]} for x in sgpa_history]
        st.dataframe(record_rows,hide_index=True,use_container_width=True)
    elif page=="Assignments":
        header("Assignments","View and download assignment work uploaded by your teacher. This section is read-only.")
        import os
        items=student_assignments(s["id"])
        if items:
            for item in items:
                with st.container(border=True):
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{item['filename']} · {item['uploaded_at'][:10]}")
                    if item["description"]: st.write(item["description"])
                    if os.path.exists(item["stored_path"]):
                        with open(item["stored_path"],"rb") as f:
                            st.download_button("Download assignment",f.read(),file_name=item["filename"],key=f"student_assignment_{item['id']}")
        else: st.info("No assignments uploaded yet.")
    elif page=="ABL Activity":
        header("ABL activity","View semester activities and your recorded marks. This section is read-only.")
        items=student_abl_records(s["id"])
        if items:
            st.dataframe(items,use_container_width=True,hide_index=True)
        else: st.info("No ABL activity marks have been recorded yet.")
    else:
        header("My risk assessment","Understand the indicators that may need attention.")
        history=semester_sgpa_records(s["id"])
        r=predict_risk(s,history)
        a,b=st.columns(2); a.metric("Risk category",r["risk"]); b.metric("Risk score",f"{r['score']}/100")
        st.progress(r["score"]/100,text="Illustrative academic risk score")
        st.write(r["explanation"])
        if history:
            import pandas as pd
            chart_rows=[{"Assessment":x["semester"],"Score":float(x["sgpa"])} for x in history]
            chart_rows += [{"Assessment":"Current CIE average","Score":r["cie_average"]/10}]
            st.subheader("SGPA and current marks trend")
            st.line_chart(pd.DataFrame(chart_rows).set_index("Assessment"),use_container_width=True)
        for k,v,n in r["drivers"]: st.write(f"**{k}:** {v} — {n}")
        st.warning("This is an illustrative baseline, not a validated model. Discuss concerns with your teacher.")
