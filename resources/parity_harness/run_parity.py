#!/usr/bin/env python3
"""
Numeric parity harness: CMS-HCC V28 reference engine vs. hccinfhir.

Runs the official CMS V28 Python engine (in resources/) and hccinfhir on the
same synthetic beneficiaries, then diffs HCC lists and per-segment scores.

Run it in the hccinfhir environment (so `import hccinfhir` works); it shells
out to a `python3` that has pandas+numpy installed to run the CMS engine:

    CMS_PYTHON=/path/to/python-with-pandas \
        hatch run python resources/parity_harness/run_parity.py

(Set CMS_PYTHON when the ambient `python3` lacks pandas — e.g. inside the hatch
env. It defaults to `python3`.)

Notes
-----
- Uses `switch_edits=True` (the CMS default). Do NOT use switch_edits=False:
  the reference engine has a bug in that branch (`if model_cc in cc_ids_list`
  compares an int against 'CCxxx' strings), so it assigns no CCs at all.
- MCE edits (only active under switch_edits=True) don't affect these
  beneficiaries because they're all adults (age >= 15); hccinfhir has no MCE
  layer, so parity holds for the adult population by construction.
- hccinfhir.risk_score is the raw factor sum (pre payment adjustments), which
  is what the CMS engine's SCORE_<segment> columns hold. Both round to 3 dp.
"""
import csv, os, re, shutil, subprocess, sys, tempfile
from hccinfhir.model_calculate import calculate_raf

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PKG = os.path.join(REPO, 'resources', 'CMS_HCC_v28_2027_T1_initial_package_v1', 'software')
CMS_PYTHON = os.environ.get('CMS_PYTHON', 'python3')  # needs pandas + numpy

CODES = ['E1122', 'I509', 'J449', 'C50912', 'F0390', 'I2510']
# DOB 01/01/YYYY -> age as of 2027-02-01 cutoff = 2027 - YYYY
BENES = {
    'B1': dict(dob='01/01/1957', age=70, sex='F', orec='0', dual='00', seg='COMMUNITY_NA'),
    'B2': dict(dob='01/01/1955', age=72, sex='M', orec='0', dual='02', seg='COMMUNITY_FBA'),
    'B3': dict(dob='01/01/1972', age=55, sex='M', orec='1', dual='00', seg='COMMUNITY_ND'),
    'B4': dict(dob='01/01/1959', age=68, sex='F', orec='1', dual='00', seg='COMMUNITY_NA'),
    'B5': dict(dob='01/01/1982', age=45, sex='F', orec='1', dual='00', seg='COMMUNITY_ND'),
}


def run_cms_engine(workdir):
    shutil.copytree(PKG, os.path.join(workdir, 'software'))
    base = os.path.join(workdir, 'software', 'CMS_HCC_v28')
    os.makedirs(os.path.join(base, 'data', 'output'), exist_ok=True)
    os.makedirs(os.path.join(base, 'logs'), exist_ok=True)
    udir = os.path.join(base, 'data', 'input', 'user_defined')
    with open(os.path.join(udir, 'beneficiaries.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['ID', 'DOB', 'SEX', 'OREC', 'LTIMCAID', 'NEMCAID'])
        for bid, d in BENES.items():
            w.writerow([bid, d['dob'], '1' if d['sex'] == 'M' else '2', d['orec'], 0, 0])
    with open(os.path.join(udir, 'diagnoses.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['ID', 'ICD10'])
        for bid in BENES:
            for c in CODES:
                w.writerow([bid, c])
    proc = subprocess.run([CMS_PYTHON, 'software/CMS_HCC_v28/transform.py'],
                          cwd=workdir, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"CMS engine failed (interpreter: {CMS_PYTHON}). Set CMS_PYTHON to a "
                 f"python with pandas+numpy.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    out = os.path.join(base, 'data', 'output', 'CMS_HCC_v28_2027_T1_initial_scores.csv')
    return {r['ID']: r for r in csv.DictReader(open(out))}


def cms_hccs(row):
    return {c[3:] for c, v in row.items()
            if re.fullmatch(r'HCC\d+', c) and str(v) in ('1', '1.0', '1.00')}


def main():
    with tempfile.TemporaryDirectory() as wd:
        cms = run_cms_engine(wd)
    print(f"{'ID':4} {'seg':14} {'HCCs':6} {'CMS':>9} {'ours':>9} {'Δ':>7}")
    allok = True
    for bid, d in BENES.items():
        row = cms[bid]
        cms_h, cms_s = cms_hccs(row), round(float(row[f"SCORE_{d['seg']}"]), 3)
        r = calculate_raf(CODES, 'CMS-HCC Model V28', age=d['age'], sex=d['sex'],
                          dual_elgbl_cd=d['dual'], orec=d['orec'])
        our_h, our_s = set(r.hcc_list), round(r.risk_score, 3)
        ok = cms_h == our_h and abs(our_s - cms_s) < 0.001
        allok &= ok
        print(f"{bid:4} {d['seg']:14} {'OK' if cms_h==our_h else 'DIFF':6} "
              f"{cms_s:>9} {our_s:>9} {round(our_s-cms_s,3):>7}  {'' if ok else '<-- MISMATCH'}")
        if cms_h != our_h:
            print(f"     CMS-ours={sorted(cms_h-our_h)}  ours-CMS={sorted(our_h-cms_h)}")
    print("\nALL MATCH" if allok else "\nMISMATCHES FOUND")
    sys.exit(0 if allok else 1)


if __name__ == '__main__':
    main()
