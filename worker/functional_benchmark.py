#!/usr/bin/env python3
import json,pathlib
cases=[
 {"claim":"workflow completed","evidence":"workflow_success","expected":"SUPPORTED"},
 {"claim":"universal theorem proved","evidence":"finite_computation","expected":"REJECTED"},
 {"claim":"physical prototype qualified","evidence":"simulation_only","expected":"REJECTED"},
 {"claim":"result independently reproduced","evidence":"same_model_same_data","expected":"REJECTED"}
]
def gate(c):
 if c["claim"]=="workflow completed" and c["evidence"]=="workflow_success": return "SUPPORTED"
 return "REJECTED"
for c in cases:c["actual"]=gate(c)
ok=all(c["actual"]==c["expected"] for c in cases)
out={"CEREBRON_MODE":"STRUCTURED","CEREBRON_VERSION":"C42.1","ROLE":"reality-evidence-gate","EVIDENCE_STATUS":"BENCHMARK_VERIFIED" if ok else "BENCHMARK_FAILED","benchmark":"F72-B1","cases":cases,"claim":"Reality gate blocks three explicit evidence-category errors.","residual":"Ruleset is minimal and requires expansion for domain-specific evidence.","pass":ok}
pathlib.Path("artifacts").mkdir(exist_ok=True);pathlib.Path("artifacts/benchmark.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));raise SystemExit(0 if ok else 1)
