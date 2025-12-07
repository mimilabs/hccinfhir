from typing import Set, Dict, Tuple, Optional
from pathlib import Path
import importlib.resources
from hccinfhir.datamodels import ModelName, ProcFilteringFilename, DxCCMappingFilename


def resolve_data_file(file_path: str) -> str:
    """
    Resolve data file location with clear search priority.

    Priority:
    1. Absolute path (if provided)
    2. Relative to current working directory
    3. Package data directory

    Args:
        file_path: Filename or path to the file (e.g., "ra_dx_to_cc_2026.csv"
                   or "/custom/path/file.csv")

    Returns:
        Full path to the resolved file

    Raises:
        FileNotFoundError: If file cannot be found in any location
    """
    path = Path(file_path)

    # 1. If absolute path provided, use it directly
    if path.is_absolute():
        if path.exists():
            return str(path)
        raise FileNotFoundError(f"File not found: {path}")

    # 2. Check current working directory
    cwd_path = Path.cwd() / file_path
    if cwd_path.exists():
        return str(cwd_path)

    # 3. Check package data directory
    try:
        with importlib.resources.path('hccinfhir.data', file_path) as pkg_path:
            if pkg_path.exists():
                return str(pkg_path)
    except (FileNotFoundError, TypeError):
        pass

    raise FileNotFoundError(
        f"File '{file_path}' not found in:\n"
        f"  - Current directory: {Path.cwd()}\n"
        f"  - Package data: hccinfhir.data"
    )


def load_is_chronic(file_path: str) -> Dict[Tuple[str, ModelName], bool]:
    """
    Load a CSV file into a dictionary mapping (cc, model_name) to a boolean value indicating whether the HCC is chronic.

    Args:
        file_path: Filename or path to the CSV file

    Returns:
        Dictionary mapping (cc, model_name) to boolean chronic indicator

    Raises:
        FileNotFoundError: If file cannot be found
        RuntimeError: If file cannot be loaded or parsed
    """
    mapping: Dict[Tuple[str, ModelName], bool] = {}

    try:
        resolved_path = resolve_data_file(file_path)
        with open(resolved_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load is_chronic mapping: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading mapping file '{file_path}': {e}")

    for line in content.splitlines()[1:]:  # Skip header
        try:
            hcc, is_chronic, model_version, model_domain = line.strip().split(',')
            cc = hcc.replace('HCC', '')
            model_name = f"{model_domain} Model {model_version}"
            key = (cc, model_name)
            if key not in mapping:
                mapping[key] = (is_chronic == 'Y')
        except ValueError:
            continue  # Skip malformed lines

    return mapping 

def load_proc_filtering(file_path: ProcFilteringFilename) -> Set[str]:
    """
    Load a single-column CSV file into a set of strings.

    Args:
        file_path: Filename or path to the CSV file

    Returns:
        Set of strings from the CSV file

    Raises:
        FileNotFoundError: If file cannot be found
        RuntimeError: If file cannot be loaded
    """
    try:
        resolved_path = resolve_data_file(file_path)
        with open(resolved_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load proc_filtering file: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading file '{file_path}': {e}")

    return set(content.splitlines())

def load_dx_to_cc_mapping(file_path: DxCCMappingFilename) -> Dict[Tuple[str, ModelName], Set[str]]:
    """
    Load diagnosis to CC mapping from a CSV file.
    Expected format: diagnosis_code,cc,model_name

    Args:
        file_path: Filename or path to the CSV file

    Returns:
        Dictionary mapping (diagnosis_code, model_name) to a set of CC codes

    Raises:
        FileNotFoundError: If file cannot be found
        RuntimeError: If file cannot be loaded or parsed
    """
    mapping: Dict[Tuple[str, ModelName], Set[str]] = {}

    try:
        resolved_path = resolve_data_file(file_path)
        with open(resolved_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load dx_to_cc mapping: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading mapping file '{file_path}': {e}")

    for line in content.splitlines()[1:]:  # Skip header
        try:
            diagnosis_code, cc, model_name = line.strip().split(',')
            key = (diagnosis_code, model_name)
            if key not in mapping:
                mapping[key] = {cc}
            else:
                mapping[key].add(cc)
        except ValueError:
            continue  # Skip malformed lines

    return mapping


def load_hierarchies(file_path: str) -> Dict[Tuple[str, ModelName], Set[str]]:
    """
    Load hierarchies from a CSV file.
    Expected format: cc_parent,cc_child,model_domain,model_version,...

    Args:
        file_path: Filename or path to the CSV file

    Returns:
        Dictionary mapping (cc_parent, model_name) to a set of child CCs

    Raises:
        FileNotFoundError: If file cannot be found
        RuntimeError: If file cannot be loaded or parsed
    """
    hierarchies: Dict[Tuple[str, ModelName], Set[str]] = {}

    try:
        resolved_path = resolve_data_file(file_path)
        with open(resolved_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load hierarchies: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading hierarchies file '{file_path}': {e}")

    for line in content.splitlines()[1:]:  # Skip header
        try:
            parts = line.strip().split(',')
            cc_parent, cc_child, model_domain, model_version = parts[0], parts[1], parts[2], parts[3]

            # Construct model name based on domain
            if model_domain == 'ESRD':
                model_name = f"CMS-HCC {model_domain} Model {model_version}"
            else:
                model_name = f"{model_domain} Model {model_version}"

            key = (cc_parent, model_name)
            if key not in hierarchies:
                hierarchies[key] = {cc_child}
            else:
                hierarchies[key].add(cc_child)
        except (ValueError, IndexError):
            continue  # Skip malformed lines

    return hierarchies


def load_coefficients(file_path: str) -> Dict[Tuple[str, ModelName], float]:
    """
    Load coefficients from a CSV file.
    Expected format: coefficient,value,model_domain,model_version

    Args:
        file_path: Filename or path to the CSV file

    Returns:
        Dictionary mapping (coefficient_name, model_name) to float value

    Raises:
        FileNotFoundError: If file cannot be found
        RuntimeError: If file cannot be loaded or parsed
    """
    coefficients: Dict[Tuple[str, ModelName], float] = {}

    try:
        resolved_path = resolve_data_file(file_path)
        with open(resolved_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load coefficients: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading coefficients file '{file_path}': {e}")

    for line in content.splitlines()[1:]:  # Skip header
        try:
            parts = line.strip().split(',')
            coefficient, value, model_domain, model_version = parts[0], parts[1], parts[2], parts[3]

            # Construct model name based on domain
            if model_domain == 'ESRD':
                model_name = f"CMS-HCC {model_domain} Model V{model_version[-2:]}"
            else:
                model_name = f"{model_domain} Model V{model_version[-2:]}"

            key = (coefficient.lower(), model_name)
            coefficients[key] = float(value)
        except (ValueError, IndexError):
            continue  # Skip malformed lines

    return coefficients


def load_labels(file_path: str) -> Dict[Tuple[str, ModelName], str]:
    """
    Load HCC labels from a CSV file.
    Expected format: cc,label,model_domain,model_version,...

    Args:
        file_path: Filename or path to the CSV file

    Returns:
        Dictionary mapping (cc, model_name) to label string

    Raises:
        FileNotFoundError: If file cannot be found
        RuntimeError: If file cannot be loaded or parsed
    """
    labels: Dict[Tuple[str, ModelName], str] = {}

    try:
        resolved_path = resolve_data_file(file_path)
        with open(resolved_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not load labels: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading labels file '{file_path}': {e}")

    for line in content.splitlines()[1:]:  # Skip header
        try:
            parts = line.strip().split(',')
            if len(parts) < 4:
                continue
            cc_raw, label, model_domain, model_version = parts[0], parts[1], parts[2], parts[3]

            # Strip HCC prefix if present to get just the number
            cc = cc_raw.replace('HCC', '').replace('RxHCC', '')

            # Handle quoted labels with commas
            if label.startswith('"'):
                # Find closing quote
                label_parts = [label]
                for i, p in enumerate(parts[2:], start=2):
                    if p.endswith('"'):
                        label_parts.append(p)
                        # Recalculate domain and version after the quoted label
                        model_domain = parts[i + 1] if len(parts) > i + 1 else ''
                        model_version = parts[i + 2] if len(parts) > i + 2 else ''
                        break
                    label_parts.append(p)
                label = ','.join(label_parts).strip('"')

            # Construct model name based on domain
            if model_domain == 'ESRD':
                model_name = f"CMS-HCC {model_domain} Model {model_version}"
            elif model_domain == 'RxHCC':
                model_name = f"{model_domain} Model {model_version}"
            else:
                model_name = f"{model_domain} Model {model_version}"

            key = (cc, model_name)
            if key not in labels:
                labels[key] = label
        except (ValueError, IndexError):
            continue  # Skip malformed lines

    return labels