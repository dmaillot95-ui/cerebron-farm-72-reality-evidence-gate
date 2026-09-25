from __future__ import annotations
import hashlib,json,urllib.request

def raw(repo,commit,path):
    url=f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        return r.read()

def registry_view(raw_bytes):
    d=json.loads(raw_bytes); farms=d["farms"]
    ids=[int(x["id"]) for x in farms]; repos=[x["repo"] for x in farms]
    max_id=max(ids) if ids else 0
    missing=[i for i in range(1,max_id+1) if i not in set(ids)]
    return d,farms,ids,repos,max_id,missing

def validate_current(d,farms,ids,repos,max_id,missing):
    checks={
      "version_v227":d.get("version")=="2.27",
      "entry_count_154":len(farms)==154,
      "max_registered_id_174":max_id==174,
      "max_farms_174":d.get("max_farms")==174,
      "farm_ceiling_174":d.get("farm_ceiling")==174,
      "ids_unique":len(ids)==len(set(ids)),
      "repos_unique":len(repos)==len(set(repos)),
      "sparse_gap_exact_153_to_172":missing==list(range(153,173)),
      "f152_present":any(x.get("id")==152 and x.get("repo")=="cerebron-rdx-exchange" for x in farms),
      "f173_present":any(x.get("id")==173 for x in farms),
      "f174_present":any(x.get("id")==174 for x in farms)
    }
    return all(checks.values()),checks

import pathlib
CORE_REPO="dmaillot95-ui/cerebron-omega-ai"
OLD_COMMIT="cd6b614ef27becbbf1a4a008bc38c5d15b280e2a"
NEW_COMMIT="9caab262e7190a060818bfe0a17330c1564b7f1a"
PATH="config/farms.json"

def validate_old(raw_bytes):
    d,farms,ids,repos,max_id,missing=registry_view(raw_bytes)
    checks={
      "entry_count_172":len(farms)==172,
      "ids_contiguous_1_to_172":ids==list(range(1,173)),
      "ids_unique":len(ids)==len(set(ids)),
      "repos_unique":len(repos)==len(set(repos)),
      "max_id_172":max_id==172,
      "missing_none":missing==[]
    }
    return all(checks.values()),checks

def main():
    old_raw=raw(CORE_REPO,OLD_COMMIT,PATH)
    new_raw=raw(CORE_REPO,NEW_COMMIT,PATH)
    old_ok,old_checks=validate_old(old_raw)
    d,f,ids,repos,max_id,missing=registry_view(new_raw)
    new_ok,new_checks=validate_current(d,f,ids,repos,max_id,missing)

    # Explicit anti-hardcode control: the old contiguous predicate MUST reject the new sparse registry.
    old_pred_on_new,_=validate_old(new_raw)
    topology_changed=(len(json.loads(old_raw)["farms"])!=len(f) or max(registry_view(old_raw)[2])!=max_id or missing!=[])
    transfer_pass=old_ok and new_ok and not old_pred_on_new and topology_changed
    out={
      "schema":"F72_CURRENT_REGISTRY_FRESH_TRANSFER_V1",
      "farm_id":72,"status":"PASS" if transfer_pass else "FAIL",
      "source_old":{"repo":CORE_REPO,"commit":OLD_COMMIT,"path":PATH,"sha256":hashlib.sha256(old_raw).hexdigest()},
      "source_new":{"repo":CORE_REPO,"commit":NEW_COMMIT,"path":PATH,"sha256":hashlib.sha256(new_raw).hexdigest()},
      "old_topology":{"type":"CONTIGUOUS","checks":old_checks,"pass":old_ok},
      "new_topology":{"type":"SPARSE_DECLARED","checks":new_checks,"pass":new_ok},
      "anti_hardcode_control":{"old_contiguous_predicate_accepts_new":old_pred_on_new,"expected":False},
      "topology_changed":topology_changed,
      "transfer":"PASS" if transfer_pass else "FAIL",
      "interpretation":"Validation methodology handles two real registry revisions with different topology by using version-scoped declared invariants; fixed historical 1..N assumption is rejected on the new sparse registry.",
      "global_release":False,"gold_released":False,"training_released":False,
      "claim_ceiling":"STRUCTURAL_TRANSFER_ACROSS_TWO_REAL_PINNED_REGISTRY_REVISIONS_ONLY_NO_GLOBAL_PROMOTION_RELEASE"
    }
    out["receipt_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    pathlib.Path("artifacts").mkdir(exist_ok=True)
    pathlib.Path("artifacts/current_registry_fresh_transfer_v1.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True))
    if out["status"]!="PASS": raise SystemExit(2)

if __name__=="__main__": main()
