#!/usr/bin/env python3
"""
Build src/hccinfhir/data/ra_dx_edits.csv from the CMS SAS edit macros.

Source: CMS 2026 midyear-final model software packages (SAS), one edit macro
per model:
    V28I0ED3.TXT  -> CMS-HCC Model V28
    V22I0ED4.TXT  -> CMS-HCC Model V22
    V24I0ED3.TXT  -> CMS-HCC Model V24 AND CMS-HCC ESRD Model V24
    V21I0ED4.TXT  -> CMS-HCC ESRD Model V21
    R08I0ED1.TXT  -> RxHCC Model V08  (no mandatory RTI edits)

Only the MANDATORY ("RTI") edit block is parsed -- the section before the
`%IF &SEDITS` MCE block. MCE edits are intentionally NOT ported (they are a
separate, user-toggled behavior gated on age/sex validity formats).

Edit encoding (matches hccinfhir/model_edits.py semantics):
  - `&SEX="2" ... THEN CC="X"`            -> sex edit, sex=2, override -> X
  - `&AGE < N ... THEN CC="-1.0"`         -> age edit, age_max=N-1, invalid
  - `&AGE < N ... THEN CC="X"`            -> age edit, age_max=N-1, override -> X
  - `&AGE >= N ... THEN CC="-1.0"`        -> age edit, age_min=N,   invalid
  - `(&AGE < A OR &AGE > B) THEN CC="-1"` -> age edit, age_max=A-1, age_min=B+1, invalid
    (the OR-logic in apply_edits fires for age<=A-1 OR age>=B+1, i.e. outside [A,B])

Run from anywhere:  python resources/sas_edit_macros/build_ra_dx_edits.py
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(REPO, 'src', 'hccinfhir', 'data', 'ra_dx_edits.csv')

# macro file -> list of model_name(s) it applies to
MACRO_MODELS = {
    'V28I0ED3.TXT': ['CMS-HCC Model V28'],
    'V22I0ED4.TXT': ['CMS-HCC Model V22'],
    'V24I0ED3.TXT': ['CMS-HCC Model V24', 'CMS-HCC ESRD Model V24'],
    'V21I0ED4.TXT': ['CMS-HCC ESRD Model V21'],
    'R08I0ED1.TXT': ['RxHCC Model V08'],
}


def parse_macro(text):
    """Return list of dicts (one per ICD10) for the mandatory edit block."""
    # keep only the mandatory section (before the MCE / SEDITS block)
    body = re.split(r'%IF\s+&SEDITS', text, maxsplit=1)[0]

    rules = []
    # each mandatory statement: IF <condition> THEN CC="<target>";
    for m in re.finditer(r'IF\s+(.*?)\s+THEN\s+CC\s*=\s*"([^"]+)"', body, re.DOTALL | re.IGNORECASE):
        cond, target = m.group(1), m.group(2).strip()

        # collect ICD10 codes: either `IN ( "a","b",... )` or `= "code"`
        codes = []
        in_match = re.search(r'&ICD10\s+IN\s*\(([^)]*)\)', cond, re.IGNORECASE | re.DOTALL)
        if in_match:
            codes = re.findall(r'"([^"]+)"', in_match.group(1))
        else:
            eq_match = re.search(r'&ICD10\s*=\s*"([^"]+)"', cond, re.IGNORECASE)
            if eq_match:
                codes = [eq_match.group(1)]
        if not codes:
            continue

        # action / cc_override from target
        if target in ('-1.0', '-1'):
            action, cc_override = 'invalid', None
        else:
            # normalise numeric CC target ("112", "48", "22", possibly "22.0")
            cc_override = target[:-2] if target.endswith('.0') else target
            action, = ('override',)

        # sex vs age condition
        sex_match = re.search(r'&SEX\s*=\s*"(\d)"', cond)
        edit_type = sex = age_min = age_max = None
        if sex_match:
            edit_type, sex = 'sex', sex_match.group(1)
        else:
            edit_type = 'age'
            ages = re.findall(r'&AGE\s*(<=|>=|<|>)\s*(\d+)', cond)
            for op, num in ages:
                num = int(num)
                if op == '<':
                    age_max = num - 1
                elif op == '<=':
                    age_max = num
                elif op == '>':
                    age_min = num + 1
                elif op == '>=':
                    age_min = num
        rules.append(dict(codes=codes, edit_type=edit_type, sex=sex,
                          age_min=age_min, age_max=age_max, action=action,
                          cc_override=cc_override))
    return rules


def describe(model, r, code):
    parts = [model.replace('CMS-HCC ', '').replace('Model ', '')]
    if r['edit_type'] == 'sex':
        parts.append(f"sex={r['sex']}")
    else:
        if r['age_min'] is not None and r['age_max'] is not None:
            parts.append(f"invalid outside age {r['age_max']+1}-{r['age_min']-1}")
        elif r['age_max'] is not None:
            parts.append(f"age<{r['age_max']+1}")
        elif r['age_min'] is not None:
            parts.append(f"age>={r['age_min']}")
    if r['action'] == 'override':
        parts.append(f"-> CC{r['cc_override']}")
    else:
        parts.append("-> invalid")
    return ' '.join(parts)


def main():
    out_rows = []
    for fname, models in MACRO_MODELS.items():
        text = open(os.path.join(HERE, fname), encoding='utf-8', errors='replace').read()
        rules = parse_macro(text)
        for model in models:
            for r in rules:
                for code in r['codes']:
                    out_rows.append({
                        'icd10': code,
                        'edit_type': r['edit_type'],
                        'sex': r['sex'] or '',
                        'age_min': r['age_min'] if r['age_min'] is not None else '',
                        'age_max': r['age_max'] if r['age_max'] is not None else '',
                        'action': r['action'],
                        'cc_override': r['cc_override'] or '',
                        'model_name': model,
                        'description': describe(model, r, code),
                    })

    fields = ['icd10', 'edit_type', 'sex', 'age_min', 'age_max', 'action',
              'cc_override', 'model_name', 'description']
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    # summary
    from collections import Counter
    by_model = Counter(r['model_name'] for r in out_rows)
    print(f"wrote {len(out_rows)} rows to {OUT}")
    for m, n in sorted(by_model.items()):
        print(f"  {m}: {n}")


if __name__ == '__main__':
    main()
