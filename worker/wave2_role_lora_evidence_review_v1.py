#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

REQ=pathlib.Path("requests/wave2-role-lora-evidence-review-v1.json")
OUT=pathlib.Path("artifacts/wave2-role-lora-evidence-review-v1.json")

def fetch(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        raw=r.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def main():
    req=json.loads(REQ.read_text())
    src=req["source"]
    audit,asha=fetch(src["repo"],src["commit"],src["canonical_audit"])
    candidate_roles=list(audit.get("candidate_roles",[]))
    results={}
    all_pass=True
    for c in req["candidates"]:
        role=c["role"]
        rec,rsha=fetch(src["repo"],src["commit"],c["receipt"])
        gains=rec.get("gains",{})
        checks={
          "role_match":rec.get("role")==role,
          "canonical_run_match":rec.get("run_id")==audit.get("run_id"),
          "real_training":rec.get("real_training") is True and rec.get("training_executed") is True,
          "weights_changed":rec.get("weights_changed") is True,
          "hf_readback":rec.get("hf_private_readback_sha_pass") is True,
          "cold_deny_training":rec.get("cold_deny_training") is True,
          "validation_gate":rec.get("validation_gate_pass") is True,
          "cold_gate":rec.get("cold_gate_pass") is True,
          "no_critical_regression":rec.get("any_critical_regression") is False,
          "m6_gain_positive":gains.get("M6",0)>0,
          "transfer_gain_positive":gains.get("TRANSFER",0)>0,
          "red_gain_nonnegative":gains.get("RED",0)>=0,
          "candidate_decision":str(rec.get("decision","")).startswith("G6_CANDIDATE"),
          "canonical_candidate":role in candidate_roles,
          "adapter_sha_expected":rec.get("adapter_sha256")==c["expected_adapter_sha256"],
          "audit_adapter_match":audit.get("roles",{}).get(role,{}).get("adapter_sha256")==rec.get("adapter_sha256"),
          "not_pre_promoted":rec.get("promotion")=="NOT_PROMOTED"
        }
        ok=all(checks.values())
        all_pass=all_pass and ok
        results[role]={
          "checks":checks,
          "review_pass":ok,
          "evidence_status":"SUPPORTED" if ok else "FAILED",
          "evidence_level":"E2" if ok else "E1",
          "adapter_sha256":rec.get("adapter_sha256"),
          "receipt_content_sha256":rsha,
          "route":"AFAH_WAVE2_MODEL_FINAL_REVIEW" if ok else "ROLLBACK_OR_REPAIR"
        }

    out={
      "schema":"F72_WAVE2_ROLE_LORA_EVIDENCE_REVIEW_V1",
      "farm_id":72,
      "farm_role":"reality-evidence-gate",
      "source_repo":src["repo"],
      "source_commit":src["commit"],
      "canonical_audit_content_sha256":asha,
      "candidate_roles":candidate_roles,
      "requested_roles":[c["role"] for c in req["candidates"]],
      "results":results,
      "all_requested_candidates_pass":all_pass,
      "training_released":False,
      "candidate_adapters_used_for_review":False,
      "independent_evidence_count":0,
      "claim_ceiling":"SUPPORTED_SCOPED_SYNTHETIC_NEURAL_ADAPTER_EVIDENCE_PER_ROLE",
      "residual":[
        "Wave2 training/evaluation is synthetic and role-scoped.",
        "Two shared base-model lineages remain correlated evidence.",
        "F72 review does not activate any adapter at runtime.",
        "Final deterministic AFAH policy review remains required."
      ]
    }
    out["result_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"candidate_roles":candidate_roles,"requested_roles":out["requested_roles"],"all_requested_candidates_pass":all_pass,"result_sha256":out["result_sha256"]},sort_keys=True))
    if not all_pass: raise SystemExit(2)

if __name__=="__main__": main()
