# Contributing to AI-AAS Config

Thank you for your interest in contributing to the AI-AAS Config repository! This document provides guidelines for adding and managing AI model configurations.

## Table of Contents

- [Getting Started](#getting-started)
- [How to Add a New Model](#how-to-add-a-new-model)
- [AIModel CR Template](#aimodel-cr-template)
- [Branch Workflow](#branch-workflow)
- [Pull Request Requirements](#pull-request-requirements)
- [Security Considerations](#security-considerations)
- [Testing Your Changes](#testing-your-changes)

## Getting Started

Before contributing, please ensure you have:

1. Read the [Getting Started Guide](docs/getting-started.md)
2. Reviewed the [AIModel Reference](docs/aimodel-reference.md)
3. Understood the [Model Submission Guide](docs/model-submission-guide.md)
4. Set up access to the AI-AAS Platform development environment

## How to Add a New Model

Follow these steps to add a new AI model configuration:

### 1. Choose the Target Environment

Models should first be added to the `development` environment for testing:

```
environments/development/models/
```

After validation, they can be promoted to `staging` and then `production`.

### 2. Create the AIModel CR File

Create a new YAML file in the appropriate environment directory:

```bash
environments/development/models/my-model-name.yaml
```

**Naming conventions:**
- Use lowercase with hyphens (kebab-case)
- Include model family and size: `mistral-7b-instruct-v03.yaml`
- For provider-specific versions: `unsloth-gpt-oss-20b.yaml`

### 3. Use the AIModel Template

See the [AIModel CR Template](#aimodel-cr-template) section below for a complete template with all fields explained.

### 4. Set Appropriate Resource Requests

Refer to the [Resource Requirements Guide](docs/aimodel-reference.md#resource-requirements-guide) for GPU memory and CPU recommendations based on model size.

### 5. Test the Configuration

Before submitting, validate your configuration:

```bash
# Validate YAML syntax
yamllint environments/development/models/my-model-name.yaml

# Dry-run apply (requires kubectl access)
kubectl apply -f environments/development/models/my-model-name.yaml --dry-run=client
```

## AIModel CR Template

Here's a complete template with all fields explained:

```yaml
# AIModel CR for [Model Name]
#
# SECURITY WARNING: This configuration uses trustRemoteCode
# which allows the model to execute arbitrary Python code from HuggingFace.
# Only use with trusted model sources.
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: my-model-name              # REQUIRED: Unique identifier (kebab-case)
  namespace: development           # REQUIRED: Environment (development, staging, production)
  labels:
    app: vllm-inference            # Standard label for vLLM-based models
    model: my-model-family         # Model family (e.g., mistral, llama, gpt)
    version: v1                    # Model version
    environment: development       # Must match namespace
spec:
  # REQUIRED FIELDS
  modelName: my-model-name         # Human-readable name (must match metadata.name)
  modelID: org/model-id            # HuggingFace model ID (e.g., mistralai/Mistral-7B-Instruct-v0.3)

  # DEPLOYMENT CONTROL
  enabled: true                    # Set to false to scale deployment to zero
  runtime: vllm                    # Inference runtime: vllm, triton, or tgi (default: vllm)

  # AUTOSCALING
  minReplicas: 1                   # Minimum replicas (0 enables scale-to-zero)
  maxReplicas: 1                   # Maximum replicas for autoscaling

  # COMPUTE RESOURCES
  resources:
    requests:
      cpu: "4"                     # CPU cores requested
      memory: "16Gi"               # Memory requested
      nvidia.com/gpu: "1"          # Number of GPUs
    limits:
      cpu: "8"                     # CPU limit
      memory: "32Gi"               # Memory limit
      nvidia.com/gpu: "1"          # GPU limit (must match request)

  # GPU NODE SCHEDULING
  tolerations:
    - key: nvidia.com/gpu          # Standard GPU toleration
      operator: Exists
      effect: NoSchedule
    - key: gpu-workload            # Environment-specific toleration
      operator: Equal
      value: "true"
      effect: NoSchedule

  # RUNTIME CONFIGURATION (vLLM-specific)
  runtimeArgs:
    - --dtype=auto                 # Automatic data type selection
    - --max-model-len=8192         # Maximum sequence length
    - --gpu-memory-utilization=0.9 # GPU memory utilization (0.0-1.0)

  # SECURITY - IMPORTANT!
  trustRemoteCode: true            # Allow execution of custom model code
                                   # Set to false if model uses standard transformers architecture

# OPTIONAL FIELDS (uncomment if needed)
#
# # S3 Model Storage (optional when trustRemoteCode is true)
# s3Bucket: my-model-bucket        # S3 bucket for model artifacts
# s3Key: models/my-model/          # S3 path to model files
#
# # Custom Runtime
# runtimeName: custom-vllm-runtime # Override default runtime
#
# # Node Selection
# nodeSelector:
#   gpu-type: a100                 # Select nodes with specific labels
#   zone: us-east-1a
#
# # Additional Environment Variables
# runtimeEnv:
#   - name: VLLM_WORKER_MULTIPROC_METHOD
#     value: spawn
#   - name: CUDA_VISIBLE_DEVICES
#     value: "0"
```

## Branch Workflow

The AI-AAS Config repository follows a three-branch promotion workflow:

```
develop → staging → main
```

### Branch Mapping

| Branch | Environment | Purpose | ArgoCD Sync |
|--------|-------------|---------|-------------|
| `develop` | development | Fast iteration, experimental models | Automatic |
| `staging` | staging | Code review, integration testing | Automatic |
| `main` | production | Production-ready, stable models | Manual |

### Workflow Steps

1. **Create a feature branch from `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/add-mistral-7b
   ```

2. **Add your model configuration:**
   ```bash
   # Create the model file
   vim environments/development/models/mistral-7b-instruct-v03.yaml

   # Validate and test
   yamllint environments/development/models/mistral-7b-instruct-v03.yaml
   ```

3. **Commit your changes:**
   ```bash
   git add environments/development/models/mistral-7b-instruct-v03.yaml
   git commit -m "feat: Add Mistral-7B-Instruct-v0.3 model configuration"
   ```

4. **Push and create PR to `develop`:**
   ```bash
   git push origin feature/add-mistral-7b
   # Create PR via GitHub UI targeting 'develop' branch
   ```

5. **After merge to `develop`, promote to `staging`:**
   ```bash
   # Copy model config to staging environment
   cp environments/development/models/mistral-7b-instruct-v03.yaml \
      environments/staging/models/mistral-7b-instruct-v03.yaml

   # Update namespace in the file
   sed -i 's/namespace: development/namespace: staging/' \
       environments/staging/models/mistral-7b-instruct-v03.yaml

   # Create PR from develop to staging
   git checkout develop
   git pull origin develop
   git checkout -b promote/mistral-7b-to-staging
   # ... commit and push
   ```

6. **After staging validation, promote to `main`:**
   ```bash
   # Copy to production environment
   cp environments/staging/models/mistral-7b-instruct-v03.yaml \
      environments/production/models/mistral-7b-instruct-v03.yaml

   # Update namespace
   sed -i 's/namespace: staging/namespace: production/' \
       environments/production/models/mistral-7b-instruct-v03.yaml

   # Create PR from staging to main
   ```

## Pull Request Requirements

All pull requests must meet the following criteria:

### PR Title Format

Use conventional commits format:

```
<type>: <description>

Types:
- feat: New model configuration
- fix: Fix to existing configuration
- docs: Documentation changes
- refactor: Restructure without changing behavior
```

**Examples:**
- `feat: Add Mistral-7B-Instruct-v0.3 model`
- `fix: Update GPU memory for Llama-70B`
- `docs: Update resource requirements guide`

### PR Description

Include the following in your PR description:

```markdown
## Summary
Brief description of the change

## Model Details (for new models)
- **Model ID**: mistralai/Mistral-7B-Instruct-v0.3
- **Model Size**: 7B parameters
- **Runtime**: vLLM
- **GPU Requirements**: 1x GPU, 16GB VRAM

## Testing
- [ ] YAML validation passed
- [ ] Dry-run apply successful
- [ ] Model deployed and tested in development
- [ ] Inference endpoint responds correctly

## Security Review
- [ ] trustRemoteCode flag is appropriate for this model
- [ ] Model source is trusted (official model repository)
- [ ] Resource limits are reasonable

## Checklist
- [ ] Configuration follows naming conventions
- [ ] Labels are complete and accurate
- [ ] Resource requests match model requirements
- [ ] Documentation updated (if needed)
```

### Required Reviewers

- At least **1 approval** from a platform maintainer
- For production deployments: **2 approvals** required

### Automated Checks

PRs must pass:
- YAML syntax validation
- Schema validation (if schemas are defined)
- Branch protection rules

## Security Considerations

### trustRemoteCode Flag

The `trustRemoteCode` field is **critical** for security:

```yaml
trustRemoteCode: true  # or false
```

**When to use `true`:**
- Model uses custom architecture not in standard transformers library
- Model includes custom tokenizers or processing code
- Official model from trusted source (e.g., Meta, Mistral AI, OpenAI)

**When to use `false`:**
- Model uses standard transformers architecture
- Security policy requires code review of all custom code
- Model source is untrusted or unknown

**SECURITY WARNING:**

Setting `trustRemoteCode: true` allows the model to execute arbitrary Python code during loading and inference. This code:
- Runs with the same permissions as the inference service
- Can access network resources
- Can read/write files in the container
- Is NOT sandboxed or restricted

**Only enable this for models from trusted sources!**

### Resource Limits

Always set appropriate resource limits to prevent:
- Resource exhaustion attacks
- Unintended cost overruns
- Cluster instability

**Required limits:**
- CPU limits (prevent CPU monopolization)
- Memory limits (prevent OOM kills affecting other workloads)
- GPU limits (must match requests for GPU resources)

### Secrets and Credentials

**NEVER commit secrets to this repository:**
- API keys
- S3 credentials (use IAM roles or Kubernetes secrets)
- Database passwords
- Private model access tokens

Use Kubernetes secrets referenced in the AIModel CR if needed.

## Testing Your Changes

### 1. YAML Validation

```bash
# Install yamllint
pip install yamllint

# Validate syntax
yamllint environments/development/models/my-model.yaml
```

### 2. Schema Validation

```bash
# If schemas are available
# (Future: automated schema validation)
```

### 3. Dry-Run Apply

```bash
# Requires kubectl access to development cluster
kubectl apply -f environments/development/models/my-model.yaml --dry-run=client
```

### 4. Deployment Testing

After merging to `develop` and ArgoCD sync:

```bash
# Check AIModel status
kubectl get aimodel -n development

# Check deployment status
kubectl get pods -n development -l model=my-model-family

# Test inference endpoint
curl -X POST https://api.dev.ai-aas.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "my-model-name",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 5. Monitor Logs

Check for errors during deployment:

```bash
# View model operator logs
kubectl logs -n ai-model-operator -l app=ai-model-operator --tail=50

# View inference service logs
kubectl logs -n development -l model=my-model-family --tail=50
```

## Getting Help

- **Documentation**: Check [docs/](docs/) directory
- **Examples**: See [environments/development/models/](environments/development/models/)
- **Issues**: [GitHub Issues](https://github.com/otherjamesbrown/ai-aas-config/issues)
- **Platform Docs**: [AI-AAS Platform Documentation](https://github.com/otherjamesbrown/ai-aas)

## Code of Conduct

Please be respectful and professional in all interactions. We aim to maintain a welcoming and inclusive community.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
