#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

REQ=pathlib.Path("requests/rdx-memory-evidence-review-v2.json")
OUT=pathlib.Path("artifacts/rdx-memory-evidence-review-v2.json")

def fetch(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        raw=r.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def main():
    req=json.loads(REQ.read_text())
    docs={}; content_sha={}
    for key,s in req["sources"].items():
        docs[key],content_sha[key]=fetch(s["repo"],s["commit"],s["receipt"])

    dense=docs["f115_dense_stress"]
    hybrid=docs["f115_hybrid_holdout"]
    dedup=docs["f116_semantic_dedup"]
    archive=docs["f119_archive"]
    governor=docs["f120_governor"]
    f72=docs["f72_state"]

    checks={}
    checks["f115_dense_pointer_schema"]=dense.get("schema")=="F115_RDX_SEMANTIC_RECALL_STRESS_V2_POINTER"
    checks["f115_dense_scientific_pass"]=dense.get("result",{}).get("status")=="PASS"
    checks["f115_dense_24q"]=dense.get("result",{}).get("query_count")==24
    checks["f115_dense_metrics"]=(
        float(dense.get("result",{}).get("top1_accuracy",0))>=0.80 and
        float(dense.get("result",{}).get("top3_recall",0))>=0.95 and
        float(dense.get("result",{}).get("mrr",0))>=0.88
    )
    checks["f115_dense_no_training"]=dense.get("training_executed") is False and dense.get("weights_changed") is False

    checks["f115_hybrid_schema"]=hybrid.get("schema")=="F115_RDX_HYBRID_RETRIEVAL_FRESH_HOLDOUT_V1"
    checks["f115_hybrid_frozen_policy"]=hybrid.get("policy",{}).get("frozen_before_holdout") is True
    checks["f115_hybrid_no_training"]=hybrid.get("training_executed") is False and hybrid.get("weights_changed") is False
    checks["f115_hybrid_no_production_claim"]="NOT_PRODUCTION_RAG_QUALITY" in hybrid.get("claim_ceiling","")
    checks["f115_hybrid_decision_valid"]=hybrid.get("decision") in {
        "FRESH_HOLDOUT_GAIN","HOLD_NO_FRESH_GAIN","REJECT_POLICY_FRESH_REGRESSION"
    }

    checks["f116_schema"]=dedup.get("schema")=="F116_RDX_SEMANTIC_DEDUP_CANARY_V2"
    checks["f116_status"]=dedup.get("status") in {"PASS","HOLD"}
    checks["f116_dev_holdout_separation"]="DEV_ONLY_THEN_FROZEN_FOR_HOLDOUT" in dedup.get("method","")
    checks["f116_auto_merge_false"]=dedup.get("auto_merge_authorized") is False
    checks["f116_candidate_only"]=dedup.get("semantic_candidate_detection_only") is True
    checks["f116_no_training"]=dedup.get("training_executed") is False and dedup.get("weights_changed") is False

    checks["f119_archive_pass"]=archive.get("status")=="PASS" and archive.get("provenance_preserved") is True
    checks["f119_no_training"]=archive.get("training_executed") is False and archive.get("weights_changed") is False

    checks["f120_governor_pass"]=governor.get("status")=="PASS"
    checks["f120_gold_locked"]=governor.get("decisions",{}).get("M4_GOLD")=="BLOCK_BY_GLOBAL_F72"
    checks["f120_m6_deny"]=governor.get("decisions",{}).get("M6_TRAINING")=="DENY"
    checks["f120_training_locked"]=governor.get("training_executed") is False and governor.get("weights_changed") is False

    checks["global_f72_still_fail"]=f72.get("reality_gate")=="FAIL" and f72.get("decision")=="HOLD"
    checks["request_no_release"]=(
        req.get("gold_release") is False and
        req.get("training_release") is False and
        req.get("global_promotion_release") is False
    )

    ok=all(checks.values())
    out={
      "schema":"F72_RDX_MEMORY_EVIDENCE_REVIEW_V2",
      "farm_id":72,
      "farm_role":"reality-evidence-gate",
      "source_content_sha256":content_sha,
      "checks":checks,
      "review_pass":ok,
      "evidence_status":"SUPPORTED" if ok else "FAILED",
      "evidence_level":"E2" if ok else "E1",
      "decision":"F72_SUPPORTS_RDX_MEMORY_CANARY_STACK_V2_ONLY" if ok else "F72_BLOCKS_RDX_MEMORY_CANARY_STACK_V2",
      "global_f72_gate":"FAIL",
      "gold_released":False,
      "training_released":False,
      "production_rag_quality":"NOT_PROVEN",
      "semantic_dedup_auto_merge":"NOT_AUTHORIZED",
      "hybrid_policy_decision":hybrid.get("decision"),
      "claim_ceiling":"SUPPORTED_SCOPED_RDX_MEMORY_CANARY_EVIDENCE_V2_NO_GOLD_NO_TRAINING" if ok else "FAILED_SCOPED_RDX_MEMORY_EVIDENCE_V2",
      "residual":[
        "All semantic retrieval and semantic dedup results remain internal synthetic canaries.",
        "F115 holdout metrics do not establish production RAG quality on live heterogeneous RDX traffic.",
        "F116 semantic similarity may propose duplicate candidates but may not auto-merge knowledge.",
        "Global F72 remains FAIL due to the separate current REALITY_FAILURE.",
        "No M4 GOLD promotion, dataset admission, neural training, or runtime activation is authorized."
      ]
    }
    out["result_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"review_pass":ok,"decision":out["decision"],"hybrid_policy_decision":out["hybrid_policy_decision"],"failed_checks":[k for k,v in checks.items() if not v],"result_sha256":out["result_sha256"]},sort_keys=True))
    if not ok: raise SystemExit(2)

if __name__=="__main__":
    main()
