#!/usr/bin/env python3
"""
AIModel CR Validation Script

This script validates AIModel Custom Resources for the AI-AAS Platform.
It checks for:
- Required fields (apiVersion, kind, metadata, spec)
- Required spec fields (modelName, modelID)
- Security warnings (trustRemoteCode)
- Reasonable resource requests
- Kubernetes naming conventions
"""

import sys
import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

# ANSI color codes for output
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class ValidationResult:
    """Stores validation results for a single file"""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_aimodel = False

    def add_error(self, message: str):
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def parse_resource_value(value: str) -> float:
    """
    Parse Kubernetes resource values (e.g., "16Gi", "4", "1000m") to numeric values.
    Returns the value in base units (bytes for memory, cores for CPU).
    """
    if not value:
        return 0

    value_str = str(value)

    # Memory units
    memory_units = {
        'Ki': 1024,
        'Mi': 1024 ** 2,
        'Gi': 1024 ** 3,
        'Ti': 1024 ** 4,
        'Pi': 1024 ** 5,
        'K': 1000,
        'M': 1000 ** 2,
        'G': 1000 ** 3,
        'T': 1000 ** 4,
        'P': 1000 ** 5,
    }

    # Check for memory units
    for unit, multiplier in memory_units.items():
        if value_str.endswith(unit):
            try:
                return float(value_str[:-len(unit)]) * multiplier
            except ValueError:
                return 0

    # Check for millicores (CPU)
    if value_str.endswith('m'):
        try:
            return float(value_str[:-1]) / 1000.0
        except ValueError:
            return 0

    # Plain number
    try:
        return float(value_str)
    except ValueError:
        return 0


def validate_resources(spec: Dict[str, Any], result: ValidationResult):
    """Validate resource requests and limits"""
    if 'resources' not in spec:
        result.add_warning("No resource requests/limits specified - consider adding them for production deployments")
        return

    resources = spec['resources']

    # Check for requests
    if 'requests' in resources:
        requests = resources['requests']

        # Validate memory requests
        if 'memory' in requests:
            memory_bytes = parse_resource_value(requests['memory'])
            # Warn if less than 8Gi (typical minimum for LLM inference)
            if memory_bytes > 0 and memory_bytes < 8 * (1024 ** 3):
                result.add_warning(
                    f"Memory request '{requests['memory']}' is less than 8Gi - "
                    f"this may be insufficient for most LLM models"
                )
            # Warn if more than 1Ti (likely a typo or misconfiguration)
            if memory_bytes > 1024 ** 4:
                result.add_warning(
                    f"Memory request '{requests['memory']}' is very large (>1Ti) - "
                    f"please verify this is correct"
                )

        # Validate CPU requests
        if 'cpu' in requests:
            cpu_cores = parse_resource_value(requests['cpu'])
            # Warn if less than 2 cores
            if cpu_cores > 0 and cpu_cores < 2:
                result.add_warning(
                    f"CPU request '{requests['cpu']}' is less than 2 cores - "
                    f"this may result in slow inference"
                )
            # Warn if more than 128 cores
            if cpu_cores > 128:
                result.add_warning(
                    f"CPU request '{requests['cpu']}' is very large (>128 cores) - "
                    f"please verify this is correct"
                )

        # Check for GPU requests
        if 'nvidia.com/gpu' not in requests:
            result.add_warning(
                "No GPU resource request found - LLM inference typically requires GPU acceleration"
            )

    # Check that limits are >= requests
    if 'requests' in resources and 'limits' in resources:
        requests = resources['requests']
        limits = resources['limits']

        for resource_type in ['cpu', 'memory']:
            if resource_type in requests and resource_type in limits:
                req_val = parse_resource_value(requests[resource_type])
                lim_val = parse_resource_value(limits[resource_type])
                if req_val > 0 and lim_val > 0 and lim_val < req_val:
                    result.add_error(
                        f"Resource limit for '{resource_type}' ({limits[resource_type]}) "
                        f"is less than request ({requests[resource_type]})"
                    )


def validate_metadata(metadata: Dict[str, Any], result: ValidationResult):
    """Validate metadata section"""
    # Check for required name field
    if 'name' not in metadata:
        result.add_error("metadata.name is required")
        return

    name = metadata['name']

    # Validate Kubernetes naming conventions
    # Must be lowercase alphanumeric, with '-' allowed (not at start/end)
    if not name:
        result.add_error("metadata.name cannot be empty")
    elif len(name) > 253:
        result.add_error(f"metadata.name '{name}' exceeds maximum length of 253 characters")
    elif not name[0].isalnum() or not name[-1].isalnum():
        result.add_error(f"metadata.name '{name}' must start and end with alphanumeric characters")
    elif not all(c.isalnum() or c == '-' for c in name):
        result.add_error(
            f"metadata.name '{name}' contains invalid characters "
            f"(only lowercase alphanumeric and '-' allowed)"
        )
    elif name != name.lower():
        result.add_error(f"metadata.name '{name}' must be lowercase")

    # Check for namespace
    if 'namespace' not in metadata:
        result.add_warning("metadata.namespace not specified - will use default namespace")


def validate_spec(spec: Dict[str, Any], result: ValidationResult):
    """Validate spec section of AIModel CR"""
    # Required fields
    required_fields = ['modelName', 'modelID']
    for field in required_fields:
        if field not in spec:
            result.add_error(f"spec.{field} is required")

    # Check modelName
    if 'modelName' in spec:
        model_name = spec['modelName']
        if not model_name or not isinstance(model_name, str):
            result.add_error("spec.modelName must be a non-empty string")

    # Check modelID
    if 'modelID' in spec:
        model_id = spec['modelID']
        if not model_id or not isinstance(model_id, str):
            result.add_error("spec.modelID must be a non-empty string")

    # Security warning for trustRemoteCode
    if spec.get('trustRemoteCode', False):
        result.add_warning(
            "spec.trustRemoteCode is set to 'true' - this allows execution of arbitrary Python code from the model repository. "
            "Only use with trusted model sources. Consider using models with built-in architectures when possible."
        )

    # Validate runtime
    if 'runtime' in spec:
        runtime = spec['runtime']
        valid_runtimes = ['vllm', 'triton', 'tgi']
        if runtime not in valid_runtimes:
            result.add_error(
                f"spec.runtime '{runtime}' is not valid. Must be one of: {', '.join(valid_runtimes)}"
            )

    # Validate replica settings
    if 'minReplicas' in spec:
        min_replicas = spec['minReplicas']
        if not isinstance(min_replicas, int) or min_replicas < 0:
            result.add_error("spec.minReplicas must be a non-negative integer")

    if 'maxReplicas' in spec:
        max_replicas = spec['maxReplicas']
        if not isinstance(max_replicas, int) or max_replicas < 1:
            result.add_error("spec.maxReplicas must be a positive integer")

    if 'minReplicas' in spec and 'maxReplicas' in spec:
        if spec['minReplicas'] > spec['maxReplicas']:
            result.add_error(
                f"spec.minReplicas ({spec['minReplicas']}) cannot be greater than "
                f"spec.maxReplicas ({spec['maxReplicas']})"
            )

    # Check for S3 configuration if trustRemoteCode is not set
    if not spec.get('trustRemoteCode', False):
        if 's3Bucket' not in spec:
            result.add_warning(
                "spec.s3Bucket not specified and trustRemoteCode is false - "
                "model deployment may fail without a model source"
            )
        if 's3Key' not in spec:
            result.add_warning(
                "spec.s3Key not specified and trustRemoteCode is false - "
                "model deployment may fail without a model source"
            )

    # Validate resources
    validate_resources(spec, result)


def validate_aimodel(data: Dict[str, Any], result: ValidationResult):
    """Validate an AIModel Custom Resource"""
    # Check apiVersion
    if 'apiVersion' not in data:
        result.add_error("apiVersion is required")
    elif not data['apiVersion'].startswith('aimodel.ai-aas.io/'):
        result.add_error(
            f"apiVersion '{data['apiVersion']}' is not valid for AIModel. "
            f"Expected 'aimodel.ai-aas.io/v1alpha1'"
        )

    # Check kind
    if 'kind' not in data:
        result.add_error("kind is required")
    elif data['kind'] != 'AIModel':
        # Not an AIModel CR, skip validation
        return False

    result.is_aimodel = True

    # Check metadata
    if 'metadata' not in data:
        result.add_error("metadata is required")
    else:
        validate_metadata(data['metadata'], result)

    # Check spec
    if 'spec' not in data:
        result.add_error("spec is required")
    else:
        validate_spec(data['spec'], result)

    return True


def validate_file(file_path: Path) -> ValidationResult:
    """Validate a single YAML file"""
    result = ValidationResult(str(file_path))

    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        if not data:
            # Empty file or only comments
            return result

        # Handle multi-document YAML files
        if isinstance(data, list):
            for doc in data:
                if doc:
                    validate_aimodel(doc, result)
        else:
            validate_aimodel(data, result)

    except yaml.YAMLError as e:
        result.add_error(f"YAML parsing error: {e}")
    except Exception as e:
        result.add_error(f"Unexpected error: {e}")

    return result


def print_results(results: List[ValidationResult]) -> Tuple[int, int, int]:
    """
    Print validation results to stdout.
    Returns tuple of (total_files, files_with_errors, files_with_warnings)
    """
    total_files = 0
    files_with_errors = 0
    files_with_warnings = 0
    aimodel_count = 0

    print(f"\n{BLUE}{'=' * 80}{NC}")
    print(f"{BLUE}AIModel Validation Results{NC}")
    print(f"{BLUE}{'=' * 80}{NC}\n")

    for result in results:
        if not result.is_aimodel:
            # Skip non-AIModel files
            continue

        total_files += 1

        # Print file path
        status_icon = "✓"
        status_color = GREEN
        if result.has_errors():
            status_icon = "✗"
            status_color = RED
            files_with_errors += 1
        elif result.has_warnings():
            status_icon = "⚠"
            status_color = YELLOW
            files_with_warnings += 1

        print(f"{status_color}{status_icon} {result.file_path}{NC}")

        # Print errors
        for error in result.errors:
            print(f"  {RED}ERROR: {error}{NC}")

        # Print warnings
        for warning in result.warnings:
            print(f"  {YELLOW}WARNING: {warning}{NC}")

        if not result.has_errors() and not result.has_warnings():
            print(f"  {GREEN}All validations passed{NC}")

        print()

    # Print summary
    print(f"{BLUE}{'=' * 80}{NC}")
    print(f"{BLUE}Summary{NC}")
    print(f"{BLUE}{'=' * 80}{NC}")
    print(f"Total AIModel CRs validated: {total_files}")
    print(f"{RED}Files with errors: {files_with_errors}{NC}")
    print(f"{YELLOW}Files with warnings: {files_with_warnings}{NC}")
    print(f"{GREEN}Files passed: {total_files - files_with_errors - files_with_warnings}{NC}")
    print()

    return total_files, files_with_errors, files_with_warnings


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: validate-aimodels.py <directory1> [directory2] ...")
        print()
        print("Validates AIModel Custom Resources in the specified directories.")
        sys.exit(1)

    # Collect all YAML files
    yaml_files: List[Path] = []
    for directory in sys.argv[1:]:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"{RED}ERROR: Directory '{directory}' does not exist{NC}")
            sys.exit(1)

        if not dir_path.is_dir():
            print(f"{RED}ERROR: '{directory}' is not a directory{NC}")
            sys.exit(1)

        # Find all .yaml and .yml files
        yaml_files.extend(dir_path.rglob('*.yaml'))
        yaml_files.extend(dir_path.rglob('*.yml'))

    if not yaml_files:
        print(f"{YELLOW}WARNING: No YAML files found in specified directories{NC}")
        sys.exit(0)

    # Validate each file
    results = []
    for file_path in yaml_files:
        result = validate_file(file_path)
        results.append(result)

    # Print results
    total_files, files_with_errors, files_with_warnings = print_results(results)

    # Exit with appropriate code
    if files_with_errors > 0:
        print(f"{RED}Validation failed with {files_with_errors} error(s){NC}")
        sys.exit(1)
    elif total_files == 0:
        print(f"{YELLOW}No AIModel CRs found to validate{NC}")
        sys.exit(0)
    else:
        print(f"{GREEN}All validations passed!{NC}")
        if files_with_warnings > 0:
            print(f"{YELLOW}Note: {files_with_warnings} file(s) have warnings{NC}")
        sys.exit(0)


if __name__ == '__main__':
    main()
