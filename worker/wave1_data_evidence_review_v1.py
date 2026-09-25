#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

REQ=pathlib.Path("requests/wave1-data-evidence-review-v1.json")
OUT=pathlib.Path("artifacts/wave1-data-evidence-review-v1.json")

def fetch_json(repo:str,commit:str,path:str):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        raw=r.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def main():
    req=json.loads(REQ.read_text())
    repo=req["source_repo"]
    commit=req["source_commit"]
    build,bsha=fetch_json(repo,commit,req["quarantine_build_receipt_path"])
    audit,asha=fetch_json(repo,commit,req["semantic_audit_receipt_path"])
    baseline,lsha=fetch_json(repo,commit,req["baseline_audit_receipt_path"])

    expected=req["expected_manifest_sha256"]
    checks={}
    checks["build_run"]=build.get("run_id")==36105250166
    checks["build_record_count"]=build.get("record_count")==432
    checks["role_counts"]=build.get("role_counts")=={"AELYS":96,"ETHERION":144,"AFAH":96,"METRION":96}
    checks["manifest_sha_expected"]=build.get("manifest_sha256")==expected
    checks["benchmark_overlap_zero"]=build.get("exact_benchmark_prompt_overlap_count")==0
    checks["build_training_locked"]=build.get("training_released") is False
    checks["build_state_quarantine"]=build.get("state")=="QUARANTINE"

    checks["audit_run"]=audit.get("run_id")==36107794532
    checks["audit_manifest_matches"]=audit.get("source_manifest_sha256")==expected
    checks["semantic_pass_432"]=audit.get("semantic_pass_count")==432
    checks["semantic_fail_zero"]=audit.get("semantic_fail_count")==0
    checks["unresolved_zero"]=audit.get("unresolved_count")==0
    checks["tamper_all_detected"]=(audit.get("tamper_case_count")==18 and audit.get("tamper_detected_count")==18)
    checks["audit_training_locked"]=audit.get("training_released") is False
    checks["audit_state"]=audit.get("state")=="AUDIT_COUNTER_AUDIT_PASS_F72_AFAH_PENDING"
    checks["audit_not_independent_model_evidence"]=audit.get("independent_model_evidence") is False

    checks["baseline_run"]=baseline.get("run_id")==36103514385
    checks["baseline_receipts_4"]=baseline.get("receipt_count")==4
    checks["baseline_real_inference_4"]=baseline.get("real_inference_count")==4
    checks["baseline_training_zero"]=baseline.get("training_executed_count")==0
    checks["shared_lineage_declared"]=baseline.get("unique_lineage_fingerprints")==1
    checks["independent_evidence_zero"]=baseline.get("independent_evidence_count")==0

    expected_content=req.get("expected_source_content_sha256",{})
    checks["build_content_sha"]=not expected_content.get("build") or bsha==expected_content["build"]
    checks["audit_content_sha"]=not expected_content.get("audit") or asha==expected_content["audit"]
    checks["baseline_content_sha"]=not expected_content.get("baseline") or lsha==expected_content["baseline"]

    all_pass=all(checks.values())
    if all_pass:
        evidence_status="SUPPORTED"
        evidence_level="E2"
        review_pass=True
        route="AFAH_WAVE1_DATA_ADMISSION_REVIEW"
        decision="F72_SUPPORTS_SYNTHETIC_CANDIDATE_POOL_ADMISSION"
    else:
        evidence_status="FAILED"
        evidence_level="E1"
        review_pass=False
        route="REPAIR_DATA_EVIDENCE"
        decision="F72_BLOCKS_WAVE1_DATA_ADMISSION"

    out={
      "schema":"F72_WAVE1_DATA_EVIDENCE_REVIEW_V1",
      "farm_id":72,
      "farm_role":"reality-evidence-gate",
      "source_repo":repo,
      "source_commit":commit,
      "source_receipt_content_sha256":{"build":bsha,"audit":asha,"baseline":lsha},
      "manifest_sha256":expected,
      "checks":checks,
      "review_pass":review_pass,
      "evidence_status":evidence_status,
      "evidence_level":evidence_level,
      "decision":decision,
      "route":route,
      "claim_reviewed":"Wave1 AELYS/ETHERION/AFAH/METRION synthetic contract candidate pool is structurally reproducible, benchmark-separated, semantically audited and tamper-checked; it may proceed to AFAH data-admission review while training remains locked.",
      "claim_ceiling":"SUPPORTED_SCOPED_SYNTHETIC_DATA_CONTRACT_EVIDENCE",
      "training_released":False,
      "residual":[
        "All candidate records are deterministic synthetic contract data, not empirical ground truth.",
        "Semantic audit is a separate code path in the same project, not independent external evidence.",
        "Shared Qwen baseline lineage does not create independent evidence.",
        "F72 review does not authorize training; AFAH admission review and fresh role-specific cold splits remain required."
      ],
      "rules_applied":["REALITY>COHERENCE","EVIDENCE>CONFIDENCE","CLAIM<=EVIDENCE","VERIFY_BEFORE_COMMIT","SIMULATION!=TEST","MEMORY!=TRAINING"]
    }
    canon=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    out["result_sha256"]=hashlib.sha256(canon).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({
      "review_pass":review_pass,
      "evidence_status":evidence_status,
      "evidence_level":evidence_level,
      "decision":decision,
      "route":route,
      "result_sha256":out["result_sha256"]
    },sort_keys=True))
    if not review_pass:
        raise SystemExit(2)

if __name__=="__main__":
    main()
