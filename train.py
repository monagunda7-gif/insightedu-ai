"""Optional training scaffold. CSV requires cie1,cie2,attendance,assignment,backlogs,at_risk.
This model is not loaded by the live dashboard; validate it on representative labelled data first."""
import sys
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, recall_score, f1_score, average_precision_score
def main(path):
 d=pd.read_csv(path); cols=["cie1","cie2","attendance","assignment","backlogs"]
 missing=set(cols+["at_risk"])-set(d.columns)
 if missing: raise ValueError(f"Missing columns: {sorted(missing)}")
 d["cie_momentum"]=d.cie2-d.cie1; d["attendance_deficit"]=(75-d.attendance).clip(lower=0)
 X=d[cols+["cie_momentum","attendance_deficit"]]; y=d.at_risk.astype(int)
 xa,xb,ya,yb=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
 try:
  from imblearn.pipeline import Pipeline as IP
  from imblearn.over_sampling import SMOTE
  model=IP([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler()),("smote",SMOTE(random_state=42)),("model",RandomForestClassifier(n_estimators=250,class_weight="balanced",random_state=42))])
 except ImportError:
  model=Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler()),("model",RandomForestClassifier(n_estimators=250,class_weight="balanced",random_state=42))])
 model.fit(xa,ya); pred=model.predict(xb); prob=model.predict_proba(xb)[:,1]
 print(classification_report(yb,pred,zero_division=0))
 print("At-risk recall:",recall_score(yb,pred,zero_division=0),"Macro F1:",f1_score(yb,pred,average="macro"),"PR-AUC:",average_precision_score(yb,prob))
 import joblib; joblib.dump(model,"ml/academic_risk_model.joblib")
if __name__=="__main__": main(sys.argv[1])
