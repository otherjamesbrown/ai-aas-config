#!/usr/bin/env python3
"""
CRD Schema Validation Script

This script validates AIModel YAML files against the CRD OpenAPI schema.
It catches schema violations like:
- Unknown fields (e.g., spec.deployment.deploymentMode instead of spec.deploymentMode)
- Incorrect field types
- Missing required fields
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

# ANSI color codes for output
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
NC = '\033[0m'


class SchemaValidator:
    """Validates YAML against CRD OpenAPI schema"""

    def __init__(self, crd_schema: Dict[str, Any]):
        self.crd_schema = crd_schema
        # Extract the OpenAPI schema for the CRD
        self.spec_schema = self._extract_spec_schema()

    def _extract_spec_schema(self) -> Dict[str, Any]:
        """Extract the spec schema from the CRD"""
        try:
            versions = self.crd_schema['spec']['versions']
            # Use the first version (should be v1alpha1)
            schema = versions[0]['schema']['openAPIV3Schema']
            return schema['properties']['spec']
        except (KeyError, IndexError) as e:
            print(f"{RED}ERROR: Could not extract spec schema from CRD: {e}{NC}")
            sys.exit(1)

    def validate_object(self, obj: Any, schema: Dict[str, Any], path: str = "spec") -> List[str]:
        """
        Recursively validate an object against a schema.
        Returns a list of error messages.
        """
        errors = []

        if not isinstance(obj, dict):
            return errors

        # Get allowed properties
        allowed_properties = schema.get('properties', {})
        allowed_keys = set(allowed_properties.keys())

        # Get object keys
        obj_keys = set(obj.keys())

        # Check if additionalProperties is allowed
        # NOTE: For CRD validation, we treat missing additionalProperties as false
        # because Kubernetes will ignore unknown fields even if not explicitly forbidden
        additional_properties = schema.get('additionalProperties')
        # Only allow additional properties if explicitly defined (not just missing)
        allows_additional = additional_properties is not None and additional_properties is not False

        # Get required properties
        required_properties = set(schema.get('required', []))

        # Check for unknown fields (only if additionalProperties is not allowed)
        if not allows_additional:
            unknown_keys = obj_keys - allowed_keys

            if unknown_keys:
                for key in sorted(unknown_keys):
                    errors.append(
                        f"Unknown field '{path}.{key}' - this field is not defined in the CRD schema. "
                        f"Kubernetes will silently ignore it, causing ArgoCD drift."
                    )

        # Check for missing required fields
        missing_keys = required_properties - obj_keys
        if missing_keys:
            for key in sorted(missing_keys):
                errors.append(f"Missing required field '{path}.{key}'")

        # Recursively validate known fields
        for key, value in obj.items():
            if key in allowed_properties:
                field_schema = allowed_properties[key]
                field_path = f"{path}.{key}"

                # Check type
                field_type = field_schema.get('type')

                if field_type == 'object' and isinstance(value, dict):
                    # Recursively validate nested object
                    errors.extend(self.validate_object(value, field_schema, field_path))
                elif field_type == 'array' and isinstance(value, list):
                    # Validate array items if schema is provided
                    items_schema = field_schema.get('items')
                    if items_schema and items_schema.get('type') == 'object':
                        for i, item in enumerate(value):
                            if isinstance(item, dict):
                                errors.extend(
                                    self.validate_object(item, items_schema, f"{field_path}[{i}]")
                                )
                elif field_type and not self._check_type(value, field_type):
                    errors.append(
                        f"Field '{field_path}' has incorrect type. "
                        f"Expected '{field_type}', got '{type(value).__name__}'"
                    )

                # Check enum values
                if 'enum' in field_schema:
                    allowed_values = field_schema['enum']
                    if value not in allowed_values:
                        errors.append(
                            f"Field '{field_path}' has invalid value '{value}'. "
                            f"Allowed values: {', '.join(map(str, allowed_values))}"
                        )

        return errors

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'object': dict,
            'array': list,
        }

        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, assume valid

        return isinstance(value, expected_python_type)

    def validate_aimodel(self, aimodel: Dict[str, Any]) -> List[str]:
        """Validate an AIModel resource"""
        errors = []

        # Check that it's an AIModel
        if aimodel.get('kind') != 'AIModel':
            return errors  # Not an AIModel, skip

        # Check apiVersion
        api_version = aimodel.get('apiVersion', '')
        if not api_version.startswith('aimodel.ai-aas.io/'):
            errors.append(
                f"Invalid apiVersion '{api_version}'. "
                f"Expected 'aimodel.ai-aas.io/v1alpha1'"
            )

        # Validate spec
        if 'spec' not in aimodel:
            errors.append("Missing required field 'spec'")
        else:
            spec = aimodel['spec']
            errors.extend(self.validate_object(spec, self.spec_schema))

        return errors


def load_crd_schema(crd_path: Path) -> Dict[str, Any]:
    """Load CRD schema from YAML file"""
    try:
        with open(crd_path, 'r') as f:
            crd = yaml.safe_load(f)
        return crd
    except Exception as e:
        print(f"{RED}ERROR: Could not load CRD schema from {crd_path}: {e}{NC}")
        sys.exit(1)


def validate_file(file_path: Path, validator: SchemaValidator) -> Tuple[bool, List[str]]:
    """
    Validate a single YAML file.
    Returns (is_aimodel, errors)
    """
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        if not data:
            return False, []

        # Handle multi-document YAML files
        if isinstance(data, list):
            all_errors = []
            is_aimodel = False
            for doc in data:
                if doc and doc.get('kind') == 'AIModel':
                    is_aimodel = True
                    all_errors.extend(validator.validate_aimodel(doc))
            return is_aimodel, all_errors
        else:
            kind = data.get('kind')
            if kind == 'AIModel':
                errors = validator.validate_aimodel(data)
                return True, errors
            return False, []

    except yaml.YAMLError as e:
        return False, [f"YAML parsing error: {e}"]
    except Exception as e:
        return False, [f"Unexpected error: {e}"]


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: validate-crd-schema.py <directory1> [directory2] ...")
        print()
        print("Validates AIModel Custom Resources against CRD schema.")
        sys.exit(1)

    # Find CRD schema file
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    crd_file = repo_root / 'schemas' / 'aimodel.ai-aas.io_aimodels.yaml'

    if not crd_file.exists():
        print(f"{RED}ERROR: CRD schema not found at: {crd_file}{NC}")
        print("Please ensure the CRD schema is copied from the ai-aas repository.")
        sys.exit(1)

    print(f"{BLUE}{'=' * 80}{NC}")
    print(f"{BLUE}AIModel CRD Schema Validation{NC}")
    print(f"{BLUE}{'=' * 80}{NC}")
    print()
    print(f"Using CRD schema: {crd_file}")
    print()

    # Load CRD schema
    crd_schema = load_crd_schema(crd_file)
    validator = SchemaValidator(crd_schema)

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
    total_files = 0
    files_with_errors = 0
    total_errors = 0

    for file_path in yaml_files:
        is_aimodel, errors = validate_file(file_path, validator)

        if not is_aimodel:
            continue

        total_files += 1

        # Print file path
        if errors:
            print(f"{RED}✗ {file_path}{NC}")
            files_with_errors += 1
            total_errors += len(errors)

            # Print errors
            for error in errors:
                print(f"  {RED}ERROR: {error}{NC}")
            print()
        else:
            print(f"{GREEN}✓ {file_path}{NC}")

    # Print summary
    print(f"{BLUE}{'=' * 80}{NC}")
    print(f"{BLUE}Summary{NC}")
    print(f"{BLUE}{'=' * 80}{NC}")
    print(f"Total AIModel CRs validated: {total_files}")
    print(f"{RED}Files with errors: {files_with_errors}{NC}")
    print(f"{RED}Total errors: {total_errors}{NC}")
    print(f"{GREEN}Files passed: {total_files - files_with_errors}{NC}")
    print()

    if files_with_errors > 0:
        print(f"{RED}❌ CRD schema validation failed{NC}")
        print()
        print("Common issues:")
        print("  - Unknown fields (e.g., spec.deployment.deploymentMode instead of spec.deploymentMode)")
        print("  - Incorrect field types (e.g., string instead of integer)")
        print("  - Missing required fields")
        print()
        print(f"Check the CRD schema at: {crd_file}")
        sys.exit(1)
    elif total_files == 0:
        print(f"{YELLOW}No AIModel CRs found to validate{NC}")
        sys.exit(0)
    else:
        print(f"{GREEN}✅ All AIModel CRs passed schema validation!{NC}")
        sys.exit(0)


if __name__ == '__main__':
    main()
