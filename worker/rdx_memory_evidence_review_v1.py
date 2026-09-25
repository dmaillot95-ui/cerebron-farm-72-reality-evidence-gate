#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

REQ=pathlib.Path("requests/rdx-memory-evidence-review-v1.json")
OUT=pathlib.Path("artifacts/rdx-memory-evidence-review-v1.json")

def fetch(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        raw=r.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def main():
    req=json.loads(REQ.read_text())
    src=req["sources"]
    docs={}
    content_sha={}
    for key,s in src.items():
        docs[key],content_sha[key]=fetch(s["repo"],s["commit"],s["receipt"])

    ingress=docs["ingress"]
    recall=docs["write_read_recall"]
    f114=docs["f114"]
    f115=docs["f115"]
    f116=docs["f116"]
    f72=docs["f72_state"]
    expected=req["expected_receipt_sha256"]

    checks={}
    checks["ingress_schema"]=ingress.get("schema")=="CEREBRON_RDX_INGRESS_DECISION_V1"
    checks["ingress_receipt"]=ingress.get("receipt_sha256")==expected["ingress"]
    checks["ingress_memory_only"]=(
        ingress.get("memory",{}).get("admissible") is True and
        ingress.get("memory",{}).get("rag_available") is True and
        ingress.get("memory",{}).get("classes")==["M1","M7"]
    )
    checks["ingress_gold_locked"]=ingress.get("gold",{}).get("eligible") is False
    checks["ingress_training_locked"]=(
        ingress.get("training",{}).get("eligible") is False and
        ingress.get("training",{}).get("weights_changed") is False
    )

    checks["recall_schema"]=recall.get("schema")=="CEREBRON_RDX_MEMORY_WRITE_READ_RECALL_CANARY_V1"
    checks["recall_receipt"]=recall.get("receipt_sha256")==expected["write_read_recall"]
    checks["recall_io_pass"]=all(recall.get(k)=="PASS" for k in [
        "write","authenticated_read","readback_sha","recall_index_lookup","recall_pointer_follow"
    ])
    checks["recall_classes"]=recall.get("memory_classes")==["M1","M7"]
    checks["recall_training_locked"]=recall.get("training")=="NOT_EXECUTED"
    checks["recall_semantic_not_claimed"]="SEMANTIC_RETRIEVAL_QUALITY_NOT_TESTED" in recall.get("claim_ceiling","")

    checks["f114_status"]=f114.get("status")=="PASS"
    checks["f114_receipt"]=f114.get("receipt_sha256")==expected["f114"]
    checks["f114_canonical_conflict"]=(
        f114.get("canonical_count")==2 and
        f114.get("exact_duplicate_count")==1 and
        f114.get("conflict_probe_detected") is True and
        f114.get("unexpected_conflicts")==[]
    )
    checks["f114_training_locked"]=f114.get("training_executed") is False

    checks["f115_status"]=f115.get("status")=="PASS"
    checks["f115_receipt"]=f115.get("receipt_sha256")==expected["f115"]
    checks["f115_model_pinned"]=(
        f115.get("model_id")=="sentence-transformers/all-MiniLM-L6-v2" and
        f115.get("model_revision_recorded") is True and
        bool(f115.get("resolved_model_revision"))
    )
    checks["f115_thresholds"]=(
        f115.get("query_count")==8 and
        f115.get("top1_correct")==7 and
        float(f115.get("top1_accuracy",0))>=0.75 and
        float(f115.get("mrr",0))>=0.8
    )
    checks["f115_scope_limited"]=(
        f115.get("training_executed") is False and
        f115.get("weights_changed") is False and
        "NOT_PRODUCTION_RAG_QUALITY" in f115.get("claim_ceiling","")
    )

    checks["f116_status"]=f116.get("status")=="PASS"
    checks["f116_receipt"]=f116.get("receipt_sha256")==expected["f116"]
    checks["f116_exact_dedup"]=(
        f116.get("input_count")==4 and
        f116.get("dedup_group_count")==2 and
        len(f116.get("groups",[]))==2
    )
    checks["f116_scope_limited"]=(
        f116.get("training_executed") is False and
        "NOT_SEMANTIC_DEDUP" in f116.get("claim_ceiling","")
    )

    checks["global_f72_still_fail"]=(
        f72.get("reality_gate")=="FAIL" and
        f72.get("residual")=="REALITY_FAILURE" and
        f72.get("decision")=="HOLD"
    )
    checks["no_global_release_requested"]=(
        req.get("global_promotion_release") is False and
        req.get("gold_release") is False and
        req.get("training_release") is False
    )

    ok=all(checks.values())
    out={
      "schema":"F72_RDX_MEMORY_EVIDENCE_REVIEW_V1",
      "farm_id":72,
      "farm_role":"reality-evidence-gate",
      "sources":{k:{"repo":v["repo"],"commit":v["commit"],"receipt":v["receipt"]} for k,v in src.items()},
      "source_content_sha256":content_sha,
      "checks":checks,
      "review_pass":ok,
      "evidence_status":"SUPPORTED" if ok else "FAILED",
      "evidence_level":"E2" if ok else "E1",
      "decision":"F72_SUPPORTS_RDX_MEMORY_CANARY_STACK_ONLY" if ok else "F72_BLOCKS_RDX_MEMORY_CANARY_STACK",
      "route":"AFAH_RDX_MEMORY_EVIDENCE_REVIEW_PENDING" if ok else "REPAIR_RDX_MEMORY_EVIDENCE",
      "global_f72_gate":"FAIL",
      "gold_released":False,
      "training_released":False,
      "production_rag_quality":"NOT_PROVEN",
      "semantic_canary_scope":"SYNTHETIC_ONLY",
      "claim_ceiling":"SUPPORTED_SCOPED_RDX_MEMORY_CANARY_EVIDENCE_NO_GOLD_NO_TRAINING" if ok else "FAILED_SCOPED_RDX_MEMORY_EVIDENCE",
      "residual":[
        "F115 semantic retrieval was measured only on an 8-query synthetic canary; production RAG quality is not established.",
        "F116 validates normalized exact deduplication and provenance fusion only; semantic deduplication is not established.",
        "These are internal CEREBRON canaries and do not constitute independent external scientific confirmation.",
        "Global F72 remains FAIL because the current reality-gate state has a separate REALITY_FAILURE.",
        "This scoped review does not authorize M4 GOLD promotion, dataset admission, neural training, or runtime activation."
      ]
    }
    out["result_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({
        "review_pass":ok,
        "evidence_status":out["evidence_status"],
        "decision":out["decision"],
        "failed_checks":[k for k,v in checks.items() if not v],
        "result_sha256":out["result_sha256"]
    },sort_keys=True))
    if not ok:
        raise SystemExit(2)

if __name__=="__main__":
    main()
