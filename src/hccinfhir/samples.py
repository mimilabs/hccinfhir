"""
Sample Data Module for HCCInFHIR

This module provides easy access to sample data files for testing and demonstration purposes.
End users can call functions to retrieve sample EOB (Explanation of Benefits) and 837 claim data.
"""

import importlib.resources
import json
from typing import List, Dict, Any, Union, Optional
from pathlib import Path


class SampleData:
    """
    A class that provides access to sample data files included with the HCCInFHIR package.
    
    This class allows end users to easily retrieve sample EOB and 837 claim data
    for testing, development, and demonstration purposes.
    """
    
    @staticmethod
    def get_eob_sample(case_number: int = 1) -> Dict[str, Any]:
        """
        Retrieve a specific EOB sample by case number.
        
        Args:
            case_number: The case number (1, 2, or 3). Default is 1.
            
        Returns:
            A dictionary containing the EOB data
            
        Raises:
            ValueError: If case_number is not 1, 2, or 3
            FileNotFoundError: If the sample file cannot be found
            
        Example:
            >>> sample_data = SampleData.get_eob_sample(1)
            >>> print(sample_data['resourceType'])
            'ExplanationOfBenefit'
        """
        if case_number not in [1, 2, 3]:
            raise ValueError("case_number must be 1, 2, or 3")
        
        try:
            with importlib.resources.open_text('hccinfhir.sample_files', f'sample_eob_{case_number}.json') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Sample EOB case {case_number} not found")
    
    @staticmethod
    def get_eob_sample_list(limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve a list of EOB samples from the large sample file.
        
        Args:
            limit: Maximum number of samples to return. If None, returns all 200 samples.
            
        Returns:
            A list of EOB data dictionaries
            
        Raises:
            FileNotFoundError: If the sample file cannot be found
            
        Example:
            >>> # Get first 10 samples
            >>> samples = SampleData.get_eob_sample_list(limit=10)
            >>> print(len(samples))
            10
            
            >>> # Get all 200 samples
            >>> all_samples = SampleData.get_eob_sample_list()
            >>> print(len(all_samples))
            200
        """
        try:
            output = []
            with importlib.resources.open_text('hccinfhir.sample_files', 'sample_eob_200.ndjson') as f:
                for i, line in enumerate(f):
                    if limit is not None and i >= limit:
                        break
                    eob_data = json.loads(line)
                    output.append(eob_data)
            return output
        except FileNotFoundError:
            raise FileNotFoundError("Sample EOB list file not found")
    
    @staticmethod
    def get_837_sample(case_number: int = 0) -> str:
        """
        Retrieve a specific 837 claim sample by case number.
        
        Args:
            case_number: The case number (0 through 12). Default is 0.
            
        Returns:
            A string containing the 837 X12 claim data
            
        Raises:
            ValueError: If case_number is not between 0 and 12
            FileNotFoundError: If the sample file cannot be found
            
        Example:
            >>> sample_837 = SampleData.get_837_sample(0)
            >>> print("ISA" in sample_837)
            True
        """
        if case_number < 0 or case_number > 12:
            raise ValueError("case_number must be between 0 and 12")
        
        try:
            with importlib.resources.open_text('hccinfhir.sample_files', f'sample_837_{case_number}.txt') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Sample 837 case {case_number} not found")
    
    @staticmethod
    def get_837_sample_list(case_numbers: Optional[List[int]] = None) -> List[str]:
        """
        Retrieve multiple 837 claim samples.
        
        Args:
            case_numbers: List of case numbers to retrieve. If None, returns all 12 samples.
            
        Returns:
            A list of 837 X12 claim data strings
            
        Raises:
            ValueError: If any case_number is not between 0 and 11
            FileNotFoundError: If any sample file cannot be found
            
        Example:
            >>> # Get specific cases
            >>> samples = SampleData.get_837_sample_list([0, 1, 2])
            >>> print(len(samples))
            3
            
            >>> # Get all samples
            >>> all_samples = SampleData.get_837_sample_list()
            >>> print(len(all_samples))
            13
        """
        if case_numbers is None:
            case_numbers = list(range(13))  # 0 through 12
        
        # Validate case numbers
        for case_num in case_numbers:
            if case_num < 0 or case_num > 12:
                raise ValueError(f"case_number {case_num} must be between 0 and 12")
        
        output = []
        for case_num in case_numbers:
            try:
                with importlib.resources.open_text('hccinfhir.sample_files', f'sample_837_{case_num}.txt') as f:
                    output.append(f.read())
            except FileNotFoundError:
                raise FileNotFoundError(f"Sample 837 case {case_num} not found")
        
        return output

    @staticmethod
    def get_834_sample(case_number: int = 1) -> str:
        """
        Retrieve a specific 834 enrollment sample by case number.

        Args:
            case_number: The case number (currently only 1 is available). Default is 1.

        Returns:
            A string containing the 834 X12 enrollment data

        Raises:
            ValueError: If case_number is not 1
            FileNotFoundError: If the sample file cannot be found

        Example:
            >>> sample_834 = SampleData.get_834_sample(1)
            >>> print("ISA" in sample_834)
            True
        """
        if case_number != 1:
            raise ValueError("case_number must be 1 (only one 834 sample currently available)")

        try:
            with importlib.resources.open_text('hccinfhir.sample_files', f'sample_834_0{case_number}.txt') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Sample 834 case {case_number} not found")

    @staticmethod
    def list_available_samples() -> Dict[str, Any]:
        """
        Get information about all available sample data.
        
        Returns:
            A dictionary containing information about available samples
            
        Example:
            >>> info = SampleData.list_available_samples()
            >>> print(info['eob_samples'])
            ['sample_eob_1.json', 'sample_eob_2.json', 'sample_eob_3.json', 'sample_eob_200.ndjson']
        """
        return {
            "eob_samples": [
                "sample_eob_1.json",
                "sample_eob_2.json",
                "sample_eob_3.json",
                "sample_eob_200.ndjson"
            ],
            "eob_case_numbers": [1, 2, 3],
            "eob_list_size": 200,
            "837_samples": [f"sample_837_{i}.txt" for i in range(13)],
            "837_case_numbers": list(range(13)),
            "834_samples": ["sample_834_01.txt"],
            "834_case_numbers": [1],
            "description": {
                "eob": "Explanation of Benefits (FHIR resources) for testing HCC calculations",
                "837": "X12 837 claim data for testing claim processing",
                "834": "X12 834 enrollment data for dual eligibility and demographics"
            }
        }


# Convenience functions for easy access
def get_eob_sample(case_number: int = 1) -> Dict[str, Any]:
    """
    Convenience function to get an EOB sample.
    
    Args:
        case_number: The case number (1, 2, or 3). Default is 1.
        
    Returns:
        A dictionary containing the EOB data
    """
    return SampleData.get_eob_sample(case_number)


def get_eob_sample_list(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Convenience function to get a list of EOB samples.
    
    Args:
        limit: Maximum number of samples to return. If None, returns all 200 samples.
        
    Returns:
        A list of EOB data dictionaries
    """
    return SampleData.get_eob_sample_list(limit)


def get_837_sample(case_number: int = 0) -> str:
    """
    Convenience function to get an 837 claim sample.
    
    Args:
        case_number: The case number (0 through 12). Default is 0.
        
    Returns:
        A string containing the 837 X12 claim data
    """
    return SampleData.get_837_sample(case_number)


def get_837_sample_list(case_numbers: Optional[List[int]] = None) -> List[str]:
    """
    Convenience function to get multiple 837 claim samples.

    Args:
        case_numbers: List of case numbers to retrieve. If None, returns all 12 samples.

    Returns:
        A list of 837 X12 claim data strings
    """
    return SampleData.get_837_sample_list(case_numbers)


def get_834_sample(case_number: int = 1) -> str:
    """
    Convenience function to get an 834 enrollment sample.

    Args:
        case_number: The case number (currently only 1 is available). Default is 1.

    Returns:
        A string containing the 834 X12 enrollment data
    """
    return SampleData.get_834_sample(case_number)


def list_available_samples() -> Dict[str, Any]:
    """
    Convenience function to get information about available samples.
    
    Returns:
        A dictionary containing information about available samples
    """
    return SampleData.list_available_samples()
