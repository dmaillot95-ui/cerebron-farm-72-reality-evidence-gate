#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

REQ=pathlib.Path("requests/wave1-afah-lora-evidence-review-v1.json")
OUT=pathlib.Path("artifacts/wave1-afah-lora-evidence-review-v1.json")

def fetch_json(repo:str,commit:str,path:str):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        raw=r.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def main():
    req=json.loads(REQ.read_text())
    repo=req["source_repo"];commit=req["source_commit"]
    receipt,rsha=fetch_json(repo,commit,req["role_receipt_path"])
    audit,asha=fetch_json(repo,commit,req["canonical_audit_path"])

    checks={}
    checks["canonical_run"]=receipt.get("run_id")==36109026167==audit.get("run_id")
    checks["role_afah"]=receipt.get("role")=="AFAH"
    checks["real_training"]=receipt.get("real_training") is True and receipt.get("training_executed") is True
    checks["weights_changed"]=receipt.get("weights_changed") is True
    checks["hf_readback"]=receipt.get("hf_private_readback_sha_pass") is True
    checks["cold_deny_training"]=receipt.get("cold_deny_training") is True
    checks["validation_gate"]=receipt.get("validation_gate_pass") is True
    checks["cold_gate"]=receipt.get("cold_gate_pass") is True
    checks["no_critical_regression"]=receipt.get("any_critical_regression") is False
    gains=receipt.get("gains",{})
    checks["m6_gain_positive"]=(gains.get("M6") or 0)>0
    checks["transfer_gain_positive"]=(gains.get("TRANSFER") or 0)>0
    checks["red_gain_nonnegative"]=(gains.get("RED") or 0)>=0
    checks["validation_gain_nonnegative"]=(gains.get("VALIDATION") or 0)>=0
    checks["candidate_not_promoted"]=receipt.get("promotion")=="NOT_PROMOTED"
    checks["candidate_decision"]=receipt.get("decision")=="G6_CANDIDATE_HOLD_F72_AFAH"
    checks["audit_one_candidate"]=audit.get("g6_candidate_count")==1 and audit.get("candidate_roles")==["AFAH"]
    checks["audit_three_rollbacks"]=audit.get("rollback_count")==3 and sorted(audit.get("rollback_roles",[]))==["AELYS","ETHERION","METRION"]
    checks["shared_lineage_declared"]=audit.get("unique_base_lineage_count")==1 and audit.get("independent_evidence_count")==0
    checks["adapter_sha_match"]=audit.get("roles",{}).get("AFAH",{}).get("adapter_sha256")==receipt.get("adapter_sha256")
    checks["report_sha_match"]=audit.get("roles",{}).get("AFAH",{}).get("report_sha256")==receipt.get("report_sha256")

    review_pass=all(checks.values())
    out={
      "schema":"F72_WAVE1_AFAH_LORA_EVIDENCE_REVIEW_V1",
      "farm_id":72,
      "farm_role":"reality-evidence-gate",
      "source_repo":repo,
      "source_commit":commit,
      "source_receipt_content_sha256":{"role_receipt":rsha,"canonical_audit":asha},
      "role":"AFAH",
      "adapter_sha256":receipt.get("adapter_sha256"),
      "checks":checks,
      "review_pass":review_pass,
      "evidence_status":"SUPPORTED" if review_pass else "FAILED",
      "evidence_level":"E2" if review_pass else "E1",
      "route":"AFAH_POLICY_FINAL_REVIEW" if review_pass else "ROLLBACK_OR_REPAIR",
      "claim_reviewed":"AFAH Wave1 LoRA changed adapter weights and improved scoped validation, M6, transfer and Red Team synthetic evaluations without critical regression.",
      "claim_ceiling":"SUPPORTED_SCOPED_SYNTHETIC_NEURAL_ADAPTER_EVIDENCE" if review_pass else "FAILED_SCOPED_EVIDENCE_GATE",
      "candidate_adapter_used_for_review":False,
      "training_released":False,
      "residual":[
        "Training and evaluations are synthetic and scoped to evidence-state classification.",
        "All Wave1 adapters share the same Qwen base-model lineage.",
        "This F72 review is not external third-party evidence.",
        "F72 support does not activate the adapter at runtime and does not establish general AFAH capability."
      ],
      "rules_applied":["REALITY>COHERENCE","EVIDENCE>CONFIDENCE","CLAIM<=EVIDENCE","VERIFY_BEFORE_COMMIT","TRANSFER BEFORE GENERALITY"]
    }
    canon=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    out["result_sha256"]=hashlib.sha256(canon).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({
      "review_pass":review_pass,
      "evidence_status":out["evidence_status"],
      "evidence_level":out["evidence_level"],
      "route":out["route"],
      "result_sha256":out["result_sha256"]
    },sort_keys=True))
    if not review_pass:
        raise SystemExit(2)

if __name__=="__main__":
    main()
