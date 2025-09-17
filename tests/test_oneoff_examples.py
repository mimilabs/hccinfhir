#!/usr/bin/env python3
"""
Test script to validate all README examples work correctly.
This ensures the documentation examples are accurate and functional.
"""

import sys
import traceback
from typing import Dict, Any
from hccinfhir.model_calculate import calculate_raf

def test_quick_start():
    

    diagnosis_codes = ['E119', 'I509']  # Diabetes without complications, Heart failure
    age = 67
    sex = 'F'
    model_name = "CMS-HCC Model V24"

    result = calculate_raf(
        diagnosis_codes=diagnosis_codes,
        model_name=model_name,
        age=age,
        sex=sex
    )
    print(f"Result: {result}")

if __name__ == "__main__":
    test_quick_start()