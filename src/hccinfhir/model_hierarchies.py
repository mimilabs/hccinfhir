from typing import Dict, Set, Tuple, Optional
import importlib.resources
from hccinfhir.datamodels import ModelName  

def load_hierarchies(hierarchies_file: str) -> Dict[Tuple[str, ModelName], Set[str]]:
    """Load hierarchies from a CSV file."""
    hierarchies: Dict[Tuple[str, ModelName], Set[str]] = {}
    content: Optional[str] = None

    try:
        with open(hierarchies_file, "r", encoding="utf-8") as file:
            content = file.readlines()
    except FileNotFoundError:
        try:
            with importlib.resources.open_text('hccinfhir.data', hierarchies_file, encoding="utf-8") as file:
                content = file.readlines()
        except Exception as e:
            print(f"Error loading mapping file: {e}")
            return {}
    except Exception as e:
        print(f"Error loading mapping file: {e}")
        return {}

    if content is None:
        return {}

    for line in content[1:]:  # Skip header
        try:
            cc_parent, cc_child, model_domain, model_version, _ = line.strip().split(',')
            if model_domain == 'ESRD':
                model_name = f"CMS-HCC {model_domain} Model {model_version}"
            else:
                model_name = f"{model_domain} Model {model_version}"
            key = (cc_parent, model_name)
            if key not in hierarchies:
                hierarchies[key] = {cc_child}
            else:
                hierarchies[key].add(cc_child)
        except ValueError:
            continue  # Skip malformed lines
    return hierarchies

# Load default mappings from csv file
hierarchies_file_default = 'ra_hierarchies_2026.csv'
hierarchies_default: Dict[Tuple[str, ModelName], Set[str]] = load_hierarchies(hierarchies_file_default)

def apply_hierarchies(
    cc_set: Set[str],  # Set of active CCs
    model_name: ModelName = "CMS-HCC Model V28",
    hierarchies: Dict[Tuple[str, ModelName], Set[str]] = hierarchies_default
) -> Set[str]:
    """
    Apply hierarchical rules to a set of CCs based on model version.

    Args:
        ccs: Set of current active CCs
        model_name: HCC model name to use for hierarchy rules
        hierarchies: Optional custom hierarchy dictionary
        
    Returns:
        Set of CCs after applying hierarchies
    """
    # Track CCs that should be zeroed out
    to_remove = set()
    
    # For V28, if none of 221, 222, 224, 225, 226 are present, remove 223
    if model_name == "CMS-HCC Model V28":
        if ("223" in cc_set and 
            not any(cc in cc_set for cc in ["221", "222", "224", "225", "226"])):
            cc_set.remove("223")
    elif model_name == "CMS-HCC ESRD Model V21":
        if "134" in cc_set:
            cc_set.remove("134")
    elif model_name == "CMS-HCC ESRD Model V24":
        for cc in ["134", "135", "136", "137"]:
            if cc in cc_set:
                cc_set.remove(cc)

    # Apply hierarchies
    for cc in cc_set:
        hierarchy_key = (cc, model_name)
        if hierarchy_key in hierarchies:
            # If parent CC exists, remove all child CCs
            child_ccs = hierarchies[hierarchy_key]
            to_remove.update(child_ccs & cc_set)

    # Return CCs with hierarchical exclusions removed
    return cc_set - to_remove