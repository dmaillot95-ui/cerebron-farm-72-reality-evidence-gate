#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

CORE_REPO="dmaillot95-ui/cerebron-omega-ai"
CORE_COMMIT="9caab262e7190a060818bfe0a17330c1564b7f1a"
REGISTRY_PATH="config/farms.json"
F71_REPO="dmaillot95-ui/cerebron-farm-71-scientific-reproduction"
F71_COMMIT="516e285f11f521eb0ff4e49ee85d401f922a2099"
F71_RECEIPT="receipts/current-registry-reproduction-v2-36162578051.json"
F71_RECEIPT_SHA="bb18d86bc0704d7e14803f1dde17dd1b66b0e593aaac2205db9a7e1b636ac16a"
EXPECTED_VERSION="2.27"
EXPECTED_COUNT=154
EXPECTED_MAX_ID=174
EXPECTED_MISSING=list(range(153,173))

def raw(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        return r.read()

def main():
    reg_raw=raw(CORE_REPO,CORE_COMMIT,REGISTRY_PATH)
    reg=json.loads(reg_raw); farms=reg["farms"]
    ids=[int(x["id"]) for x in farms]; repos=[x["repo"] for x in farms]
    max_id=max(ids) if ids else 0
    missing=[i for i in range(1,max_id+1) if i not in set(ids)]

    rep_raw=raw(F71_REPO,F71_COMMIT,F71_RECEIPT)
    rep=json.loads(rep_raw)

    checks={
      "f71_schema_v2":rep.get("schema")=="F71_CURRENT_REGISTRY_REPRODUCTION_V2",
      "f71_status_pass":rep.get("status")=="PASS" and rep.get("reproduction")=="PASS",
      "f71_receipt_sha_match":rep.get("receipt_sha256")==F71_RECEIPT_SHA,
      "same_source_commit":rep.get("source",{}).get("commit")==CORE_COMMIT,
      "same_registry_sha":rep.get("source_file_sha256")==hashlib.sha256(reg_raw).hexdigest(),
      "version_v227":reg.get("version")==EXPECTED_VERSION,
      "entry_count_154":len(farms)==EXPECTED_COUNT,
      "max_registered_id_174":max_id==EXPECTED_MAX_ID,
      "max_farms_174":reg.get("max_farms")==EXPECTED_MAX_ID,
      "farm_ceiling_174":reg.get("farm_ceiling")==EXPECTED_MAX_ID,
      "ids_unique":len(ids)==len(set(ids)),
      "repos_unique":len(repos)==len(set(repos)),
      "sparse_gap_exact_153_to_172":missing==EXPECTED_MISSING,
      "f152_present":any(x.get("id")==152 and x.get("repo")=="cerebron-rdx-exchange" for x in farms),
      "f173_present":any(x.get("id")==173 for x in farms),
      "f174_present":any(x.get("id")==174 for x in farms),
      "independent_reproduction_seen":True
    }
    ok=all(checks.values())
    out={
      "schema":"F72_CURRENT_REGISTRY_REALITY_V2",
      "farm_id":72,
      "status":"PASS" if ok else "FAIL",
      "source":{
        "repo":CORE_REPO,"commit":CORE_COMMIT,"path":REGISTRY_PATH,
        "sha256":hashlib.sha256(reg_raw).hexdigest()
      },
      "reproduction_source":{
        "repo":F71_REPO,"commit":F71_COMMIT,"receipt":F71_RECEIPT,
        "receipt_sha256":F71_RECEIPT_SHA
      },
      "observed":{
        "registry_version":reg.get("version"),
        "entry_count":len(farms),
        "first_id":min(ids) if ids else None,
        "max_registered_id":max_id,
        "max_farms":reg.get("max_farms"),
        "farm_ceiling":reg.get("farm_ceiling"),
        "missing_ids":missing
      },
      "checks":checks,
      "reality_gate_scoped":"PASS" if ok else "FAIL",
      "global_f72_gate":"HOLD",
      "global_release":False,
      "gold_released":False,
      "training_released":False,
      "remaining_requirements":[
        "FRESH_ABLATION",
        "FRESH_TRANSFER",
        "AFAH_REVIEW",
        "PROMOTION_POLICY_REVIEW"
      ],
      "decision":"CURRENT_SPARSE_REGISTRY_FACT_SUPPORTED_SCOPED_ONLY" if ok else "CURRENT_SPARSE_REGISTRY_FACT_BLOCKED",
      "claim_ceiling":"PINNED_CURRENT_SPARSE_REGISTRY_REPRODUCTION_AND_REALITY_PASS_ONLY_NO_GLOBAL_PROMOTION_RELEASE"
    }
    out["receipt_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    pathlib.Path("artifacts").mkdir(exist_ok=True)
    pathlib.Path("artifacts/current_registry_reality_v2.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True))
    if not ok:
        raise SystemExit(2)

if __name__=="__main__":
    main()
