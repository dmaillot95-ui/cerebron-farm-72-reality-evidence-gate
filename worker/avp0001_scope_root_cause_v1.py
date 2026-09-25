#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

CORE_REPO="dmaillot95-ui/cerebron-omega-ai"
SOURCE_COMMIT="c738b2e415463fc176cb2635b4ef0548453e6760"
CURRENT_COMMIT="cd6b614ef27becbbf1a4a008bc38c5d15b280e2a"
F71_REPO="dmaillot95-ui/cerebron-farm-71-scientific-reproduction"
F71_COMMIT="4a07374eeff355bef1d77c911555549dba0b0fa5"
F72_REPO="dmaillot95-ui/cerebron-farm-72-reality-evidence-gate"
F72_COMMIT="644b2ebe1ed3a278a7ccc33eae495091ef477e2d"

def raw(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        b=r.read()
    return b,hashlib.sha256(b).hexdigest()

def jfetch(repo,commit,path):
    b,s=raw(repo,commit,path)
    return json.loads(b),s

def registry_checks(d):
    farms=d["farms"]
    ids=[x["id"] for x in farms]
    repos=[x["repo"] for x in farms]
    return {
      "count":len(farms),
      "first_id":ids[0] if ids else None,
      "last_id":ids[-1] if ids else None,
      "ids_unique":len(ids)==len(set(ids)),
      "repos_unique":len(repos)==len(set(repos)),
      "ids_contiguous_1_to_n":ids==list(range(1,len(ids)+1))
    }

def main():
    packet,packet_sha=jfetch(CORE_REPO,SOURCE_COMMIT,"agora/validation/AVP-0001.json")
    source_reg,source_sha=jfetch(CORE_REPO,SOURCE_COMMIT,"config/farms.json")
    current_reg,current_sha=jfetch(CORE_REPO,CURRENT_COMMIT,"config/farms.json")
    f71wf,f71_sha=raw(F71_REPO,F71_COMMIT,".github/workflows/agora-5m.yml")
    f72wf,f72_sha=raw(F72_REPO,F72_COMMIT,".github/workflows/agora-5m.yml")
    s=registry_checks(source_reg); c=registry_checks(current_reg)
    claim=packet["claim"]["text"]
    scope=packet["claim"]["scope"]

    checks={
      "packet_id":packet.get("packet_id")=="AVP-0001",
      "claim_is_74":("exactly 74 farms" in claim and "1 through 74" in claim),
      "claim_scope_is_source_commit":"source commit" in scope.lower(),
      "source_registry_count_74":s["count"]==74,
      "source_registry_ids_1_74":s["first_id"]==1 and s["last_id"]==74 and s["ids_contiguous_1_to_n"],
      "source_registry_unique":s["ids_unique"] and s["repos_unique"],
      "current_registry_changed":c["count"]!=74,
      "current_registry_count_172":c["count"]==172,
      "current_registry_contiguous":c["first_id"]==1 and c["last_id"]==172 and c["ids_contiguous_1_to_n"],
      "f71_reads_main_current":b"cerebron-omega-ai/main/config/farms.json" in f71wf,
      "f71_hardcodes_74":b"count_74" in f71wf and b"range(1,75)" in f71wf,
      "f72_reads_main_current":b"cerebron-omega-ai/main/config/farms.json" in f72wf,
      "f72_hardcodes_74":b"observed[\"count\"]==74" in f72wf and b"range(1,75)" in f72wf
    }
    ok=all(checks.values())
    out={
      "schema":"F72_AVP0001_SCOPE_ROOT_CAUSE_V1",
      "status":"PASS" if ok else "FAIL",
      "farm_id":72,
      "packet":{
        "repo":CORE_REPO,"source_commit":SOURCE_COMMIT,
        "packet_sha256":packet_sha,"claim":claim,"scope":scope
      },
      "source_registry":{"commit":SOURCE_COMMIT,"sha256":source_sha,"observed":s},
      "current_registry":{"commit":CURRENT_COMMIT,"sha256":current_sha,"observed":c},
      "scheduled_workflows":{
        "F71":{"commit":F71_COMMIT,"workflow_sha256":f71_sha},
        "F72":{"commit":F72_COMMIT,"workflow_sha256":f72_sha}
      },
      "checks":checks,
      "historical_claim_matches_source":bool(
        s["count"]==74 and s["first_id"]==1 and s["last_id"]==74 and
        s["ids_unique"] and s["repos_unique"] and s["ids_contiguous_1_to_n"]
      ),
      "historical_claim_matches_current":False,
      "diagnosis":"AVP0001_IS_HISTORICAL_CALIBRATION_BUT_F71_F72_COMPARE_IT_TO_MOVING_MAIN_REGISTRY",
      "decision":"SEPARATE_HISTORICAL_CALIBRATION_FROM_CURRENT_PROMOTION_GATE",
      "global_release":False,
      "gold_released":False,
      "training_released":False,
      "recommended_action":[
        "Pin AVP-0001 reproduction to its source commit for calibration evidence.",
        "Do not use historical AVP-0001 PASS as current RDX GOLD authorization.",
        "Create a fresh current-registry validation packet with an explicit pinned source commit before changing the global promotion gate.",
        "Keep current F72 global promotion HOLD until fresh reproduction, reality, ablation, transfer and AFAH requirements are satisfied."
      ],
      "claim_ceiling":"ROOT_CAUSE_AND_HISTORICAL_SCOPE_AUDIT_ONLY_NO_GLOBAL_F72_RELEASE"
    }
    out["receipt_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    pathlib.Path("artifacts").mkdir(exist_ok=True)
    pathlib.Path("artifacts/avp0001_scope_root_cause_v1.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"status":out["status"],"diagnosis":out["diagnosis"],"global_release":False,"receipt_sha256":out["receipt_sha256"]},sort_keys=True))
    if not ok:
        raise SystemExit(2)

if __name__=="__main__":
    main()
