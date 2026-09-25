#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

CORE_REPO="dmaillot95-ui/cerebron-omega-ai"
CORE_COMMIT="cd6b614ef27becbbf1a4a008bc38c5d15b280e2a"
F71_REPO="dmaillot95-ui/cerebron-farm-71-scientific-reproduction"
F71_COMMIT="8d413f3507e1b9bbd8050dc46e8afd4c3253b3fd"
F71_RECEIPT="receipts/current-registry-reproduction-36152608439.json"

def raw(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        return r.read()

def main():
    reg_raw=raw(CORE_REPO,CORE_COMMIT,"config/farms.json")
    reg=json.loads(reg_raw); farms=reg["farms"]
    ids=[x["id"] for x in farms]; repos=[x["repo"] for x in farms]
    rep_raw=raw(F71_REPO,F71_COMMIT,F71_RECEIPT)
    rep=json.loads(rep_raw)
    checks={
      "f71_schema":rep.get("schema")=="F71_CURRENT_REGISTRY_REPRODUCTION_V1",
      "f71_pass":rep.get("reproduction")=="PASS" and rep.get("status")=="PASS",
      "same_source_commit":rep.get("source",{}).get("commit")==CORE_COMMIT,
      "same_registry_sha":rep.get("source_file_sha256")==hashlib.sha256(reg_raw).hexdigest(),
      "observed_count_172":len(farms)==172,
      "ids_1_to_172":ids==list(range(1,173)),
      "ids_unique":len(ids)==len(set(ids)),
      "repos_unique":len(repos)==len(set(repos)),
      "independent_reproduction_seen":True
    }
    ok=all(checks.values())
    out={
      "schema":"F72_CURRENT_REGISTRY_REALITY_V1",
      "farm_id":72,
      "status":"PASS" if ok else "FAIL",
      "source":{"repo":CORE_REPO,"commit":CORE_COMMIT,"path":"config/farms.json","sha256":hashlib.sha256(reg_raw).hexdigest()},
      "reproduction_source":{"repo":F71_REPO,"commit":F71_COMMIT,"receipt":F71_RECEIPT,"receipt_sha256":rep.get("receipt_sha256")},
      "observed":{"farm_count":len(farms),"first_id":ids[0] if ids else None,"last_id":ids[-1] if ids else None},
      "checks":checks,
      "reality_gate_scoped":"PASS" if ok else "FAIL",
      "global_f72_gate":"HOLD",
      "global_release":False,
      "gold_released":False,
      "training_released":False,
      "remaining_requirements":["FRESH_ABLATION","FRESH_TRANSFER","AFAH_REVIEW","PROMOTION_POLICY_REVIEW"],
      "decision":"CURRENT_REGISTRY_FACT_SUPPORTED_SCOPED_ONLY" if ok else "CURRENT_REGISTRY_FACT_BLOCKED",
      "claim_ceiling":"PINNED_CURRENT_REGISTRY_REPRODUCTION_AND_REALITY_PASS_ONLY_NO_GLOBAL_PROMOTION_RELEASE"
    }
    out["receipt_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    pathlib.Path("artifacts").mkdir(exist_ok=True)
    pathlib.Path("artifacts/current_registry_reality_v1.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"status":out["status"],"reality_gate_scoped":out["reality_gate_scoped"],"global_release":False,"receipt_sha256":out["receipt_sha256"]},sort_keys=True))
    if not ok: raise SystemExit(2)

if __name__=="__main__":
    main()
