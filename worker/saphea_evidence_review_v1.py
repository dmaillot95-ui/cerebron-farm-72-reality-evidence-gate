#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

REQ=pathlib.Path("requests/saphea-evidence-review-v1.json")
OUT=pathlib.Path("artifacts/saphea-evidence-review-v1.json")

def fetch_json(repo:str,commit:str,path:str)->dict:
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        raw=r.read()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()

def main():
    req=json.loads(REQ.read_text())
    repo=req["source_repo"]; commit=req["source_commit"]
    training,tsha=fetch_json(repo,commit,req["training_receipt_path"])
    transfer,xsha=fetch_json(repo,commit,req["transfer_receipt_path"])
    audit,asha=fetch_json(repo,commit,req["counter_audit_receipt_path"])

    checks={}
    checks["training_run"]=training.get("run_id")==36100266729
    checks["weights_changed"]=training.get("weights_changed") is True
    checks["m6_deny_training"]=training.get("m6_deny_training") is True
    checks["hf_private_readback"]=training.get("hf_private_readback_sha_pass") is True
    checks["cold_gain_positive"]=(training.get("cold_gain") or 0)>0
    checks["training_not_auto_promoted"]=training.get("promotion")=="NOT_PROMOTED"

    adapter=training.get("adapter_sha256")
    checks["adapter_sha_consistent"]=bool(adapter) and adapter==transfer.get("source_adapter_sha256")==audit.get("adapter_sha256")
    checks["transfer_run"]=transfer.get("run_id")==36101181888
    checks["transfer_frozen"]=transfer.get("transfer_deny_training") is True
    checks["transfer_disjoint"]=transfer.get("prompt_overlap_with_gold_m6")==0 and transfer.get("id_overlap_with_gold_m6")==0
    checks["transfer_gain_positive"]=(transfer.get("transfer_gain") or 0)>0
    checks["ablation_supports_value"]=transfer.get("ablation_supports_value") is True
    checks["no_transfer_critical_regression"]=transfer.get("critical_regression") is False

    checks["counter_audit_run"]=audit.get("run_id")==36101824432
    checks["codepath_reproduction_pass"]=audit.get("independent_codepath_reproduction_pass") is True
    checks["redteam_pass"]=audit.get("redteam_pass") is True
    checks["counter_audit_pass"]=audit.get("counter_audit_pass") is True
    note=str(audit.get("independence_note","")).lower()
    checks["external_independence_not_claimed"]="not external independent" in note

    all_pass=all(checks.values())
    if all_pass:
        evidence_status="SUPPORTED"
        evidence_level="E2"
        review_pass=True
        route="AFAH_SCOPED_PROMOTION_REVIEW"
    else:
        evidence_status="FAILED"
        evidence_level="E1"
        review_pass=False
        route="ROLLBACK_OR_REPAIR"
    residual=[
      "All evaluated datasets are synthetic and scoped to epistemic-status classification.",
      "Independent audit used a distinct evaluator/oracle code path but the same base-model lineage and project.",
      "No external laboratory, third-party model, or physical-world reproduction is present.",
      "This review does not establish general SAPHEA capability."
    ]
    out={
      "schema":"F72_SAPHEA_EVIDENCE_REVIEW_V1",
      "farm_id":72,
      "farm_role":"reality-evidence-gate",
      "source_repo":repo,
      "source_commit":commit,
      "source_receipt_content_sha256":{
        "training":tsha,"transfer":xsha,"counter_audit":asha
      },
      "adapter_sha256":adapter,
      "checks":checks,
      "review_pass":review_pass,
      "evidence_status":evidence_status,
      "evidence_level":evidence_level,
      "claim_reviewed":"SAPHEA G1 reversible LoRA changed adapter weights and improved scoped cold, held-out transfer, and adversarial synthetic evaluations.",
      "claim_ceiling":"SUPPORTED_SCOPED_SYNTHETIC_NEURAL_ADAPTER_EVIDENCE",
      "route":route,
      "residual":residual,
      "rules_applied":["REALITY>COHERENCE","EVIDENCE>CONFIDENCE","CLAIM<=EVIDENCE","VERIFY_BEFORE_COMMIT","SIMULATION!=TEST"],
    }
    canon=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    out["result_sha256"]=hashlib.sha256(canon).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({
      "review_pass":review_pass,
      "evidence_status":evidence_status,
      "evidence_level":evidence_level,
      "route":route,
      "result_sha256":out["result_sha256"]
    },sort_keys=True))

if __name__=="__main__":
    main()
