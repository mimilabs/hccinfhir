"""
Tests for the resolve_data_file function and file loading with custom paths.
"""
import pytest
from pathlib import Path
import tempfile
import os
from hccinfhir.utils import resolve_data_file, load_proc_filtering, load_dx_to_cc_mapping, load_hierarchies


def test_resolve_data_file_bundled():
    """Test that bundled data files can be found."""
    # Should find bundled file
    path = resolve_data_file("ra_eligible_cpt_hcpcs_2026.csv")
    assert path is not None
    assert Path(path).exists()
    assert "ra_eligible_cpt_hcpcs_2026.csv" in path


def test_resolve_data_file_absolute_path():
    """Test that absolute paths work correctly."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("test data")
        temp_path = f.name

    try:
        # Should find the file via absolute path
        resolved = resolve_data_file(temp_path)
        assert resolved == temp_path
        assert Path(resolved).exists()
    finally:
        os.unlink(temp_path)


def test_resolve_data_file_absolute_path_not_found():
    """Test that missing absolute path raises clear error."""
    with pytest.raises(FileNotFoundError) as exc_info:
        resolve_data_file("/nonexistent/path/file.csv")

    assert "File not found: /nonexistent/path/file.csv" in str(exc_info.value)


def test_resolve_data_file_current_directory():
    """Test that files in current directory are found."""
    # Create a file in current directory
    test_filename = "temp_test_file.csv"
    cwd_file = Path.cwd() / test_filename

    try:
        cwd_file.write_text("test,data\n1,2")

        # Should find file in current directory
        resolved = resolve_data_file(test_filename)
        assert Path(resolved).exists()
        assert test_filename in resolved
    finally:
        if cwd_file.exists():
            cwd_file.unlink()


def test_resolve_data_file_not_found():
    """Test that missing file raises informative error."""
    with pytest.raises(FileNotFoundError) as exc_info:
        resolve_data_file("nonexistent_file.csv")

    error_msg = str(exc_info.value)
    assert "nonexistent_file.csv" in error_msg
    assert "Current directory" in error_msg
    assert "Package data" in error_msg


def test_load_proc_filtering_custom_path():
    """Test loading proc filtering from custom absolute path."""
    # Create a temporary file with sample CPT codes
    # Note: load_proc_filtering includes ALL lines (including header)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("cpt_hcpcs_code\n")
        f.write("99213\n")
        f.write("99214\n")
        f.write("99215\n")
        temp_path = f.name

    try:
        # Load from absolute path
        result = load_proc_filtering(temp_path)
        assert isinstance(result, set)
        assert "cpt_hcpcs_code" in result  # Header is included
        assert "99213" in result
        assert "99214" in result
        assert "99215" in result
        assert len(result) == 4  # 3 codes + 1 header
    finally:
        os.unlink(temp_path)


def test_load_dx_to_cc_mapping_custom_path():
    """Test loading dx_to_cc mapping from custom absolute path."""
    # Create a temporary file with sample mapping
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("diagnosis_code,cc,model_name\n")
        f.write("E11.9,19,CMS-HCC Model V28\n")
        f.write("I10,85,CMS-HCC Model V28\n")
        temp_path = f.name

    try:
        # Load from absolute path
        result = load_dx_to_cc_mapping(temp_path)
        assert isinstance(result, dict)
        assert ("E11.9", "CMS-HCC Model V28") in result
        assert ("I10", "CMS-HCC Model V28") in result
        assert "19" in result[("E11.9", "CMS-HCC Model V28")]
        assert "85" in result[("I10", "CMS-HCC Model V28")]
    finally:
        os.unlink(temp_path)


def test_load_proc_filtering_not_found():
    """Test that missing proc filtering file raises error."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_proc_filtering("nonexistent_proc_file.csv")

    assert "Could not load proc_filtering file" in str(exc_info.value)


def test_load_dx_to_cc_mapping_not_found():
    """Test that missing dx_to_cc mapping file raises error."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_dx_to_cc_mapping("nonexistent_mapping_file.csv")

    assert "Could not load dx_to_cc mapping" in str(exc_info.value)


def test_file_priority_current_dir_over_bundled():
    """Test that files in current directory take priority over bundled files."""
    # Create a file in current directory with same name as bundled file
    test_filename = "ra_eligible_cpt_hcpcs_2026.csv"
    cwd_file = Path.cwd() / test_filename

    # Only run this test if the file doesn't already exist in CWD
    if cwd_file.exists():
        pytest.skip("Test file already exists in current directory")

    try:
        # Write custom content with header to match real file format
        cwd_file.write_text("cpt_hcpcs_code\nCUSTOM_CODE_12345\n")

        # Should load from current directory, not bundled
        result = load_proc_filtering(test_filename)
        assert "CUSTOM_CODE_12345" in result
        # Also verify it's not loading bundled codes
        assert len(result) == 2  # Only header + our custom code
    finally:
        if cwd_file.exists():
            cwd_file.unlink()


def test_load_hierarchies_custom_path():
    """Test loading hierarchies from custom absolute path."""
    # Create a temporary file with sample hierarchy mapping
    # Note: Format matches real file - cc_parent,cc_child,model_domain,model_version,model_fullname
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("cc_parent,cc_child,model_domain,model_version,model_fullname\n")
        f.write("17,18,CMS-HCC,V28,V28H87H1\n")
        f.write("18,19,CMS-HCC,V28,V28H87H1\n")
        temp_path = f.name

    try:
        # Load from absolute path
        result = load_hierarchies(temp_path)
        assert isinstance(result, dict)
        assert ("17", "CMS-HCC Model V28") in result
        assert ("18", "CMS-HCC Model V28") in result
        assert "18" in result[("17", "CMS-HCC Model V28")]
        assert "19" in result[("18", "CMS-HCC Model V28")]
    finally:
        os.unlink(temp_path)


def test_load_hierarchies_bundled():
    """Test that bundled hierarchy files can be found."""
    # Should find bundled file
    result = load_hierarchies("ra_hierarchies_2026.csv")
    assert isinstance(result, dict)
    assert len(result) > 0


def test_load_hierarchies_not_found():
    """Test that missing hierarchy file raises error."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_hierarchies("nonexistent_hierarchies.csv")

    assert "Could not load hierarchies" in str(exc_info.value)


def test_load_hierarchies_esrd_model_name():
    """Test that ESRD model names are constructed correctly."""
    # Create a temporary file with ESRD hierarchy
    # Note: Format matches real file with model_fullname column
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        f.write("cc_parent,cc_child,model_domain,model_version,model_fullname\n")
        f.write("134,135,ESRD,V21,V21H87H1\n")
        temp_path = f.name

    try:
        result = load_hierarchies(temp_path)
        # ESRD should have special model name format
        assert ("134", "CMS-HCC ESRD Model V21") in result
        assert "135" in result[("134", "CMS-HCC ESRD Model V21")]
    finally:
        os.unlink(temp_path)
