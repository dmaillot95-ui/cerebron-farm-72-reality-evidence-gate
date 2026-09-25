#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

REQ=pathlib.Path("requests/wave2-data-evidence-review-v1.json")
OUT=pathlib.Path("artifacts/wave2-data-evidence-review-v1.json")

def fetch(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        raw=r.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def main():
    req=json.loads(REQ.read_text())
    src=req["source"]
    baseline,bsha=fetch(src["repo"],src["commit"],src["baseline_receipt"])
    data,dsha=fetch(src["repo"],src["commit"],src["quarantine_receipt"])
    manifest=req["expected_manifest_sha256"]

    checks={}
    checks["baseline_schema"]=baseline.get("schema")=="CEREBRON_WAVE2_PARALLEL_BASELINE_AUDIT_V1"
    checks["baseline_receipts_4"]=baseline.get("receipt_count")==4
    checks["baseline_real_inference_4"]=baseline.get("real_inference_count")==4
    checks["baseline_training_zero"]=baseline.get("training_executed_count")==0
    checks["baseline_independent_zero"]=baseline.get("independent_evidence_count")==0
    checks["baseline_lineages_declared"]=baseline.get("unique_lineage_fingerprints")==2
    checks["data_schema"]=data.get("schema")=="CEREBRON_WAVE2_QUARANTINE_BUILD_AUDIT_POINTER_V1"
    checks["manifest_match"]=data.get("manifest_sha256")==manifest
    checks["record_count_456"]=data.get("record_count")==456
    checks["role_counts"]=data.get("role_counts")=={"SPIRALION":96,"HYPERION":96,"ASTRION":96,"SAPHEA_MICRO":168}
    checks["semantic_pass_456"]=data.get("semantic_pass_count")==456 and data.get("semantic_fail_count")==0
    checks["unresolved_zero"]=data.get("unresolved_count")==0
    checks["baseline_overlap_zero"]=data.get("exact_baseline_prompt_overlap_count")==0
    checks["tamper_19_of_19"]=data.get("tamper_case_count")==19 and data.get("tamper_detected_count")==19
    checks["training_locked"]=data.get("training_released") is False
    checks["state_ready"]=data.get("state")=="AUDIT_COUNTER_AUDIT_PASS_F72_PENDING"

    ok=all(checks.values())
    out={
      "schema":"F72_WAVE2_DATA_EVIDENCE_REVIEW_V1",
      "farm_id":72,
      "farm_role":"reality-evidence-gate",
      "source_repo":src["repo"],
      "source_commit":src["commit"],
      "source_content_sha256":{"baseline":bsha,"quarantine":dsha},
      "manifest_sha256":manifest,
      "checks":checks,
      "review_pass":ok,
      "evidence_status":"SUPPORTED" if ok else "FAILED",
      "evidence_level":"E2" if ok else "E1",
      "decision":"F72_SUPPORTS_WAVE2_SYNTHETIC_CANDIDATE_POOL" if ok else "F72_BLOCKS_WAVE2_DATA_ADMISSION",
      "route":"AFAH_WAVE2_DATA_ADMISSION_REVIEW" if ok else "REPAIR_WAVE2_DATA_EVIDENCE",
      "training_released":False,
      "claim_ceiling":"SUPPORTED_SCOPED_SYNTHETIC_DATA_CONTRACT_EVIDENCE" if ok else "FAILED_SCOPED_EVIDENCE_GATE",
      "residual":[
        "Candidate data are deterministic synthetic contract records, not empirical ground truth.",
        "Semantic audit is an independent code path within the same project, not external independent evidence.",
        "Two shared model lineages in the baseline do not create independent scientific confirmation.",
        "F72 support does not authorize training or runtime activation."
      ]
    }
    out["result_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"review_pass":ok,"evidence_status":out["evidence_status"],"decision":out["decision"],"failed_checks":[k for k,v in checks.items() if not v],"result_sha256":out["result_sha256"]},sort_keys=True))
    if not ok: raise SystemExit(2)
if __name__=="__main__":
    main()
