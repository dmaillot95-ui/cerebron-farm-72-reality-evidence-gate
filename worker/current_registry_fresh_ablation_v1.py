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

import pathlib,copy,secrets,random
CORE_REPO="dmaillot95-ui/cerebron-omega-ai"
CORE_COMMIT="9caab262e7190a060818bfe0a17330c1564b7f1a"
PATH="config/farms.json"
REALITY_RECEIPT_SHA="4ecc74b6e381ad8b6f6f465b003095615f4b7fa90bef53b48d2cddde2a47c16c"

def eval_obj(obj):
    rb=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    d,farms,ids,repos,max_id,missing=registry_view(rb)
    ok,checks=validate_current(d,farms,ids,repos,max_id,missing)
    return ok,checks

def main():
    source=raw(CORE_REPO,CORE_COMMIT,PATH)
    base=json.loads(source)
    ok,base_checks=eval_obj(base)
    if not ok: raise SystemExit("BASELINE_NOT_PASS")

    cases={}
    x=copy.deepcopy(base); x["max_farms"]=173; cases["wrong_max_farms"]=x
    x=copy.deepcopy(base); x["farm_ceiling"]=173; cases["wrong_farm_ceiling"]=x
    x=copy.deepcopy(base); x["version"]="2.26"; cases["wrong_version"]=x
    x=copy.deepcopy(base); x["farms"].append(copy.deepcopy(x["farms"][0])); cases["duplicate_id_and_repo"]=x
    x=copy.deepcopy(base); x["farms"]=[f for f in x["farms"] if f.get("id")!=152]; cases["remove_f152"]=x
    x=copy.deepcopy(base); 
    for f in x["farms"]:
        if f.get("id")==173: f["id"]=153
    cases["fill_forbidden_sparse_id"]=x
    x=copy.deepcopy(base);
    for f in x["farms"]:
        if f.get("id")==174: f["repo"]=x["farms"][0]["repo"]
    cases["duplicate_repo"]=x

    seed=secrets.randbits(64); names=list(cases); random.Random(seed).shuffle(names)
    rows=[]
    for name in names:
        passed,checks=eval_obj(cases[name])
        rows.append({"case":name,"gate_pass":passed,"expected_gate_pass":False,"correct_rejection":not passed,
                     "failed_checks":sorted(k for k,v in checks.items() if not v)})
    all_rejected=all(r["correct_rejection"] for r in rows)
    out={
      "schema":"F72_CURRENT_REGISTRY_FRESH_ABLATION_V1",
      "farm_id":72,"status":"PASS" if all_rejected else "FAIL",
      "source":{"repo":CORE_REPO,"commit":CORE_COMMIT,"path":PATH,"sha256":hashlib.sha256(source).hexdigest()},
      "reality_v2_receipt_sha256":REALITY_RECEIPT_SHA,
      "baseline_pass":True,"baseline_checks":base_checks,
      "runtime_seed_sha256":hashlib.sha256(str(seed).encode()).hexdigest(),
      "ablation_count":len(rows),"ablations":rows,
      "all_critical_mutations_rejected":all_rejected,
      "global_release":False,"gold_released":False,"training_released":False,
      "claim_ceiling":"FRESH_GATE_SENSITIVITY_ABLATION_ONLY_NO_GLOBAL_PROMOTION_RELEASE"
    }
    out["receipt_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    pathlib.Path("artifacts").mkdir(exist_ok=True)
    pathlib.Path("artifacts/current_registry_fresh_ablation_v1.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True))
    if out["status"]!="PASS": raise SystemExit(2)

if __name__=="__main__": main()
