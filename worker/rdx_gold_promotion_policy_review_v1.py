#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

REQ_PATH=pathlib.Path("requests/rdx-gold-promotion-policy-review-v1.json")

def raw(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        return r.read()

def load_remote(repo,commit,path):
    b=raw(repo,commit,path)
    return json.loads(b),hashlib.sha256(b).hexdigest()

def main():
    req=json.loads(REQ_PATH.read_text())
    rdx_repo=req["rdx_repo"]; rdx_commit=req["rdx_commit"]
    central_repo=req["central_repo"]; central_commit=req["central_commit"]
    paths=req["rdx_paths"]

    objects,objects_sha=load_remote(rdx_repo,rdx_commit,paths["object_registry"])
    ilog,ilog_sha=load_remote(rdx_repo,rdx_commit,paths["integration_log"])
    pack,pack_sha=load_remote(rdx_repo,rdx_commit,paths["pack"])
    gov,gov_sha=load_remote(rdx_repo,rdx_commit,paths["governance"])
    policy,policy_sha=load_remote(central_repo,central_commit,req["central_policy_path"])

    reality=json.loads(pathlib.Path(req["f72_reality_receipt"]).read_text())

    sources=pack.get("sources",[])
    rights_clear=bool(sources) and all(
        s.get("commercial_use_right")=="GRANTED"
        and s.get("storage_right") not in {"NO_CORPUS_STORAGE_WITHOUT_PERMISSION","METADATA_ONLY"}
        for s in sources
    )
    object_count=int(objects.get("object_count",0) or 0)
    integration_entries=ilog.get("entries",[])
    executions=pack.get("executions",[])
    human_review=bool(pack.get("human_review",{}).get("completed"))
    open_work=pack.get("open_work",[])

    review_checks={
      "request_schema":req.get("schema")=="F72_RDX_GOLD_PROMOTION_POLICY_REVIEW_REQUEST_V1",
      "rdx_object_registry_schema":objects.get("schema_version")=="ARCHITECTON-OBJECT-REGISTRY-1.0",
      "rdx_integration_log_schema":ilog.get("schema_version")=="ARCHITECTON-INTEGRATION-LOG-1.0",
      "rdx_pack_present":pack.get("id")=="RDX-000001",
      "rdx_governance_present":gov.get("schema_version")=="RDX-GOV-1.0",
      "human_review_is_required":gov.get("human_review_required_for_material_claims") is True,
      "central_f72_fail_closed":policy.get("live_gates",{}).get("F72",{}).get("current")=="FAIL",
      "central_gold_blocked":str(policy.get("global_promotion_state","")).startswith("BLOCKED_PENDING_F72"),
      "f72_registry_reality_scoped_pass":reality.get("status")=="PASS" and reality.get("reality_gate_scoped")=="PASS",
      "f72_registry_reality_global_hold":reality.get("global_f72_gate")=="HOLD",
      "no_auto_release_requested":req.get("auto_gold_release") is False and req.get("auto_training_release") is False
    }
    review_integrity=all(review_checks.values())

    readiness={
      "canonical_objects_present":object_count>0,
      "integrated_handoffs_present":len(integration_entries)>0,
      "verified_executions_present":len(executions)>0,
      "human_review_complete":human_review,
      "source_rights_clear_for_training":rights_clear,
      "pack_open_work_empty":len(open_work)==0,
      "fresh_transfer_on_train_candidate":False,
      "afah_review_on_train_candidate":False
    }
    candidate_ready=all(readiness.values())

    blockers=[k.upper() for k,v in readiness.items() if not v]
    decision="READY_FOR_F72_CANDIDATE_ABLATION_TRANSFER_AFAH" if candidate_ready else "HOLD_NO_TRAIN_ELIGIBLE_GOLD_OBJECTS"

    out={
      "schema":"F72_RDX_GOLD_PROMOTION_POLICY_REVIEW_V1",
      "farm_id":72,
      "status":"PASS" if review_integrity else "FAIL",
      "review_pass":review_integrity,
      "source":{
        "rdx_repo":rdx_repo,
        "rdx_commit":rdx_commit,
        "central_repo":central_repo,
        "central_commit":central_commit
      },
      "source_sha256":{
        "object_registry":objects_sha,
        "integration_log":ilog_sha,
        "pack":pack_sha,
        "governance":gov_sha,
        "central_policy":policy_sha
      },
      "f72_registry_reality":{
        "receipt":req["f72_reality_receipt"],
        "receipt_sha256":reality.get("receipt_sha256"),
        "scoped":"PASS" if reality.get("reality_gate_scoped")=="PASS" else "FAIL",
        "global":reality.get("global_f72_gate")
      },
      "observed":{
        "canonical_object_count":object_count,
        "integration_entry_count":len(integration_entries),
        "pack_id":pack.get("id"),
        "pack_status":pack.get("status"),
        "execution_count":len(executions),
        "human_review_complete":human_review,
        "source_count":len(sources),
        "source_rights_clear_for_training":rights_clear,
        "open_work_count":len(open_work)
      },
      "review_checks":review_checks,
      "candidate_readiness":readiness,
      "candidate_ready":candidate_ready,
      "blockers":blockers,
      "promotion_policy_review":"PASS_HOLD" if review_integrity and not candidate_ready else ("PASS_READY" if candidate_ready else "FAIL"),
      "decision":decision,
      "global_f72_gate":"FAIL",
      "gold_released":False,
      "training_released":False,
      "next_requirements":[
        "INTEGRATE_VERIFIED_RDX_OBJECTS",
        "ESTABLISH_TRAINING_RIGHTS",
        "COMPLETE_REQUIRED_HUMAN_REVIEW",
        "FRESH_ABLATION_ON_ACTUAL_GOLD_CANDIDATE",
        "FRESH_TRANSFER_ON_ACTUAL_GOLD_CANDIDATE",
        "AFAH_REVIEW_ON_ACTUAL_GOLD_CANDIDATE"
      ],
      "claim_ceiling":"PROMOTION_POLICY_REVIEW_ONLY; CURRENT_RDX_SNAPSHOT_HAS_NO_TRAIN_ELIGIBLE_M4_GOLD_OBJECT; NO_GOLD_OR_TRAINING_RELEASE"
    }
    out["receipt_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    pathlib.Path("artifacts").mkdir(exist_ok=True)
    pathlib.Path("artifacts/rdx-gold-promotion-policy-review-v1.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({
      "status":out["status"],
      "promotion_policy_review":out["promotion_policy_review"],
      "candidate_ready":out["candidate_ready"],
      "decision":out["decision"],
      "blockers":out["blockers"],
      "receipt_sha256":out["receipt_sha256"]
    },sort_keys=True))
    if not review_integrity:
        raise SystemExit(2)

if __name__=="__main__":
    main()
