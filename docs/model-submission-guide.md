# Model Submission Guide

A comprehensive guide for submitting new AI models to the AI-AAS Platform.

## Table of Contents

- [Overview](#overview)
- [Before You Begin](#before-you-begin)
- [Step-by-Step Submission Process](#step-by-step-submission-process)
- [Naming Conventions](#naming-conventions)
- [Testing Requirements](#testing-requirements)
- [Common Issues and Solutions](#common-issues-and-solutions)
- [Best Practices](#best-practices)
- [Review Checklist](#review-checklist)

## Overview

This guide walks you through the complete process of adding a new AI model to the AI-AAS Platform, from initial research to production deployment.

**Typical Timeline:**
- Development: 1-2 days (initial testing)
- Staging: 3-5 days (integration testing)
- Production: After successful staging validation

## Before You Begin

### Prerequisites

Before submitting a model, ensure you have:

**Access & Permissions:**
- Git clone access to ai-aas-config repository
- kubectl access to development cluster
- ArgoCD access for monitoring deployments

**Knowledge Requirements:**
- Basic understanding of Kubernetes concepts
- Familiarity with the model you're deploying
- Understanding of GPU resource requirements

**Research the Model:**
1. Find the model on HuggingFace: https://huggingface.co/models
2. Check model card for:
   - Model size (number of parameters)
   - Required GPU memory
   - Whether it requires `trustRemoteCode`
   - License and usage restrictions
   - Recommended inference settings

**Example Model Research:**

For `mistralai/Mistral-7B-Instruct-v0.3`:
- Size: 7B parameters
- GPU Memory: ~14GB (FP16)
- Trust Remote Code: Yes (custom architecture)
- License: Apache 2.0
- Recommended: `--max-model-len=8192`

## Step-by-Step Submission Process

### Step 1: Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-aas-config.git
cd ai-aas-config

# Add upstream remote
git remote add upstream https://github.com/otherjamesbrown/ai-aas-config.git

# Sync with latest
git checkout develop
git pull upstream develop
```

### Step 2: Create a Feature Branch

```bash
# Create a feature branch from develop
git checkout -b feature/add-mistral-7b-v03

# Branch naming convention:
# feature/<model-family>-<size>-<version>
```

### Step 3: Create Model Configuration

Create a new file at `environments/development/models/<model-name>.yaml`:

```bash
# Use the naming convention (see section below)
vim environments/development/models/mistral-7b-instruct-v03.yaml
```

**Use this template:**

```yaml
# AIModel CR for [Model Display Name]
#
# SECURITY WARNING: This configuration uses trustRemoteCode
# which allows the model to execute arbitrary Python code from HuggingFace.
# Only use with trusted model sources.
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: mistral-7b-instruct-v03
  namespace: development
  labels:
    app: vllm-inference
    model: mistral
    version: 7b-v03
    environment: development
spec:
  # REQUIRED: Model identity
  modelName: mistral-7b-instruct-v03
  modelID: mistralai/Mistral-7B-Instruct-v0.3

  # Deployment settings
  enabled: true
  runtime: vllm

  # Autoscaling
  minReplicas: 1
  maxReplicas: 1

  # Resources (adjust based on model size - see guide)
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
      nvidia.com/gpu: "1"
    limits:
      cpu: "8"
      memory: "32Gi"
      nvidia.com/gpu: "1"

  # GPU node scheduling
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
    - key: gpu-workload
      operator: Equal
      value: "true"
      effect: NoSchedule

  # vLLM runtime configuration
  runtimeArgs:
    - --dtype=auto
    - --max-model-len=8192
    - --gpu-memory-utilization=0.9

  # Security setting
  trustRemoteCode: true  # Set based on model requirements
```

**Key Decisions:**

1. **Resource Requests**: Use the [Resource Requirements Guide](aimodel-reference.md#resource-requirements-guide)
2. **trustRemoteCode**: Check model documentation
3. **runtimeArgs**: Start with defaults, tune based on testing
4. **minReplicas**: Use 1 for development, 0 for scale-to-zero in production

### Step 4: Validate Configuration

```bash
# YAML syntax validation
yamllint environments/development/models/mistral-7b-instruct-v03.yaml

# Kubernetes dry-run (requires kubectl access)
kubectl apply -f environments/development/models/mistral-7b-instruct-v03.yaml --dry-run=client

# Check for common issues
grep -E "trustRemoteCode|modelID|namespace" environments/development/models/mistral-7b-instruct-v03.yaml
```

**Expected output:**
```
namespace: development
modelID: mistralai/Mistral-7B-Instruct-v0.3
trustRemoteCode: true
```

### Step 5: Commit Changes

```bash
# Stage the file
git add environments/development/models/mistral-7b-instruct-v03.yaml

# Commit with conventional commit format
git commit -m "feat: Add Mistral-7B-Instruct-v0.3 model configuration

- Model: mistralai/Mistral-7B-Instruct-v0.3
- Size: 7B parameters
- Runtime: vLLM with FP16
- Resources: 1x GPU, 16GB memory
- trustRemoteCode: enabled for custom architecture"

# Push to your fork
git push origin feature/add-mistral-7b-v03
```

### Step 6: Create Pull Request

1. Go to GitHub: https://github.com/otherjamesbrown/ai-aas-config
2. Click "Compare & pull request"
3. **Set base branch to `develop`** (NOT main!)
4. Fill in PR template (see [CONTRIBUTING.md](../CONTRIBUTING.md#pull-request-requirements))

**PR Title:**
```
feat: Add Mistral-7B-Instruct-v0.3 model
```

**PR Description:**
```markdown
## Summary
Adds Mistral-7B-Instruct-v0.3, a state-of-the-art 7B parameter instruction-tuned model from Mistral AI.

## Model Details
- **Model ID**: mistralai/Mistral-7B-Instruct-v0.3
- **Model Size**: 7B parameters
- **Runtime**: vLLM
- **GPU Requirements**: 1x GPU, 16GB VRAM
- **License**: Apache 2.0

## Testing
- [x] YAML validation passed
- [x] Dry-run apply successful
- [ ] Model deployed and tested in development
- [ ] Inference endpoint responds correctly

## Security Review
- [x] trustRemoteCode flag set to `true` (required for Mistral's custom architecture)
- [x] Model source is trusted (official Mistral AI repository)
- [x] Resource limits are reasonable

## Checklist
- [x] Configuration follows naming conventions
- [x] Labels are complete and accurate
- [x] Resource requests match model requirements
- [x] Documentation updated (if needed)
```

5. Request review from maintainers
6. Wait for automated checks to pass

### Step 7: Monitor Deployment (After PR Merge)

Once your PR is merged to `develop`, ArgoCD will automatically sync:

```bash
# Set kubeconfig
export KUBECONFIG=/path/to/kubeconfig-development.yaml

# Watch AIModel status
kubectl get aimodel mistral-7b-instruct-v03 -n development -w

# Expected progression:
# NAME                        MODEL                        ... PHASE
# mistral-7b-instruct-v03    mistral-7b-instruct-v03   ... Pending
# mistral-7b-instruct-v03    mistral-7b-instruct-v03   ... Downloading
# mistral-7b-instruct-v03    mistral-7b-instruct-v03   ... Deploying
# mistral-7b-instruct-v03    mistral-7b-instruct-v03   ... Ready
```

**Monitor with ArgoCD:**
```bash
argocd login argocd.dev.ai-aas.local
argocd app get ai-models-development
```

### Step 8: Test Inference

Once the model is `Ready`:

```bash
# Get inference endpoint
ENDPOINT=$(kubectl get aimodel mistral-7b-instruct-v03 -n development -o jsonpath='{.status.inferenceEndpoint}')
echo $ENDPOINT

# Test inference
curl -X POST https://api.dev.ai-aas.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "mistral-7b-instruct-v03",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    "max_tokens": 200
  }' | jq .
```

**Expected Response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1702500000,
  "model": "mistral-7b-instruct-v03",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Quantum computing is a type of computing that..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 120,
    "total_tokens": 135
  }
}
```

### Step 9: Update PR with Test Results

After successful testing, update your PR:

```markdown
## Testing
- [x] YAML validation passed
- [x] Dry-run apply successful
- [x] Model deployed and tested in development
- [x] Inference endpoint responds correctly

**Test Results:**
- Deployment time: ~5 minutes
- First inference latency: ~2 seconds
- Subsequent latency: ~500ms
- GPU utilization: ~85%
- Memory usage: ~14GB / 16GB
```

### Step 10: Promote to Staging

After successful development testing (and when ready):

```bash
# Switch to develop branch
git checkout develop
git pull upstream develop

# Create promotion branch
git checkout -b promote/mistral-7b-to-staging

# Copy model config to staging
cp environments/development/models/mistral-7b-instruct-v03.yaml \
   environments/staging/models/mistral-7b-instruct-v03.yaml

# Update namespace and environment label
sed -i 's/namespace: development/namespace: staging/' \
    environments/staging/models/mistral-7b-instruct-v03.yaml
sed -i 's/environment: development/environment: staging/' \
    environments/staging/models/mistral-7b-instruct-v03.yaml

# Commit and push
git add environments/staging/models/mistral-7b-instruct-v03.yaml
git commit -m "chore: Promote Mistral-7B-Instruct-v0.3 to staging"
git push origin promote/mistral-7b-to-staging

# Create PR from develop to staging
```

### Step 11: Production Deployment

After staging validation:

```bash
# Create production promotion branch
git checkout staging
git pull upstream staging
git checkout -b promote/mistral-7b-to-production

# Copy to production
cp environments/staging/models/mistral-7b-instruct-v03.yaml \
   environments/production/models/mistral-7b-instruct-v03.yaml

# Update namespace and environment
sed -i 's/namespace: staging/namespace: production/' \
    environments/production/models/mistral-7b-instruct-v03.yaml
sed -i 's/environment: staging/environment: production/' \
    environments/production/models/mistral-7b-instruct-v03.yaml

# Consider production-specific tuning:
# - Increase minReplicas for availability
# - Adjust autoscaling for production load
# - Review resource limits

# Commit and push
git add environments/production/models/mistral-7b-instruct-v03.yaml
git commit -m "chore: Promote Mistral-7B-Instruct-v0.3 to production"
git push origin promote/mistral-7b-to-production

# Create PR from staging to main
# Requires 2 approvals for production
```

## Naming Conventions

### File Names

Use lowercase with hyphens (kebab-case):

**Format:** `{model-family}-{size}-{variant}-{version}.yaml`

**Examples:**
- `mistral-7b-instruct-v03.yaml`
- `llama-2-7b-chat.yaml`
- `gpt-neo-2.7b.yaml`
- `unsloth-gpt-oss-20b.yaml` (provider prefix)

**Rules:**
- Use hyphens, not underscores
- Include model size (7b, 13b, 70b)
- Include variant if applicable (instruct, chat, base)
- Include version if applicable (v03, v2)

### Metadata Name

Must match the file name (without .yaml):

```yaml
metadata:
  name: mistral-7b-instruct-v03  # Matches file name
```

### Model Labels

**Required labels:**
```yaml
labels:
  app: vllm-inference           # Standard for vLLM models
  model: mistral                # Model family
  version: 7b-v03               # Size and version
  environment: development      # Must match namespace
```

**Optional labels:**
```yaml
labels:
  provider: unsloth             # For provider-specific models
  architecture: transformer     # Model architecture
  task: text-generation         # Primary task
```

## Testing Requirements

### Pre-Submission Testing

Before submitting your PR, complete:

**1. YAML Validation**
```bash
yamllint environments/development/models/your-model.yaml
```

**2. Kubernetes Dry-Run**
```bash
kubectl apply -f environments/development/models/your-model.yaml --dry-run=client
```

**3. Field Validation**
- [ ] `modelName` matches `metadata.name`
- [ ] `namespace` matches environment
- [ ] `modelID` is correct HuggingFace ID
- [ ] Resource requests are appropriate for model size
- [ ] `trustRemoteCode` setting is correct

### Post-Deployment Testing

After deployment to development:

**1. Deployment Status**
```bash
kubectl get aimodel YOUR_MODEL -n development

# Should show:
# - ENABLED: true
# - READY: 1 (or configured replicas)
# - PHASE: Ready
```

**2. Pod Health**
```bash
kubectl get pods -n development -l model=YOUR_MODEL_FAMILY

# All pods should be Running
```

**3. Logs Check**
```bash
POD=$(kubectl get pod -n development -l model=YOUR_MODEL_FAMILY -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n development $POD --tail=50

# Look for:
# - No errors
# - "Server started" or similar
# - vLLM engine initialization complete
```

**4. Inference Testing**

**Test 1: Basic Inference**
```bash
curl -X POST https://api.dev.ai-aas.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "your-model-name",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

**Test 2: Longer Context**
```bash
curl -X POST https://api.dev.ai-aas.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "Write a detailed explanation of artificial intelligence."}
    ],
    "max_tokens": 500
  }'
```

**Test 3: Streaming**
```bash
curl -X POST https://api.dev.ai-aas.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "your-model-name",
    "messages": [{"role": "user", "content": "Count to 10."}],
    "stream": true
  }'
```

**5. Performance Benchmarking**

**Latency Test:**
```bash
# Run multiple requests and measure latency
for i in {1..10}; do
  time curl -X POST https://api.dev.ai-aas.local/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -d '{"model": "your-model", "messages": [{"role": "user", "content": "Hi"}]}'
done
```

**Expected Metrics:**
- First request (cold start): < 5 seconds
- Subsequent requests: < 2 seconds
- GPU utilization: 70-95%

## Common Issues and Solutions

### Issue: Model Stuck in "Downloading" Phase

**Symptoms:**
```bash
kubectl get aimodel my-model -n development
# PHASE: Downloading (for > 10 minutes)
```

**Solutions:**

1. **Check download progress:**
   ```bash
   kubectl get aimodel my-model -n development -o jsonpath='{.status.downloadProgress}'
   ```

2. **Check operator logs:**
   ```bash
   kubectl logs -n ai-model-operator -l app=ai-model-operator --tail=100
   ```

3. **Common causes:**
   - Slow network connection to HuggingFace
   - Large model size (70B+ models can take 30+ minutes)
   - HuggingFace rate limiting
   - Incorrect `modelID`

4. **Fix:**
   - Wait longer for large models
   - Verify `modelID` is correct
   - Use `s3Bucket` for pre-downloaded models

### Issue: Pod OOMKilled

**Symptoms:**
```bash
kubectl get pods -n development -l model=my-model
# STATUS: OOMKilled or CrashLoopBackOff
```

**Solutions:**

1. **Increase memory limits:**
   ```yaml
   resources:
     limits:
       memory: "32Gi"  # Increase from 16Gi
   ```

2. **Reduce GPU memory utilization:**
   ```yaml
   runtimeArgs:
     - --gpu-memory-utilization=0.8  # Reduce from 0.9
   ```

3. **Reduce max sequence length:**
   ```yaml
   runtimeArgs:
     - --max-model-len=4096  # Reduce from 8192
   ```

### Issue: GPU Allocation Failed

**Symptoms:**
```bash
kubectl describe pod -n development my-model-...
# Events: Failed to allocate GPU
```

**Solutions:**

1. **Check GPU availability:**
   ```bash
   kubectl get nodes -l nvidia.com/gpu=true
   kubectl describe node GPU_NODE_NAME | grep nvidia.com/gpu
   ```

2. **Verify tolerations:**
   ```yaml
   tolerations:
     - key: nvidia.com/gpu
       operator: Exists
       effect: NoSchedule
   ```

3. **Check node selector (if used):**
   ```yaml
   nodeSelector:
     gpu-type: a100  # Ensure nodes have this label
   ```

### Issue: Model Returns 404

**Symptoms:**
```bash
curl https://api.dev.ai-aas.local/v1/chat/completions ...
# {"error": "Model not found"}
```

**Solutions:**

1. **Check InferenceService status:**
   ```bash
   kubectl get inferenceservice -n development
   ```

2. **Verify API router configuration:**
   ```bash
   kubectl get configmap api-router-config -n system -o yaml
   ```

3. **Check model is registered:**
   ```bash
   # Should show your model in the list
   kubectl get aimodel -A
   ```

### Issue: trustRemoteCode Error

**Symptoms:**
```
Error: Untrusted remote code execution
```

**Solutions:**

1. **Enable trustRemoteCode:**
   ```yaml
   spec:
     trustRemoteCode: true
   ```

2. **Verify model requires it:**
   - Check model card on HuggingFace
   - Look for "custom architecture" or "custom tokenizer"

3. **Security review:**
   - Only enable for trusted model sources
   - Document in PR why it's required

## Best Practices

### Resource Allocation

**Start Conservative:**
```yaml
resources:
  requests:
    memory: "16Gi"  # Start with minimum
  limits:
    memory: "32Gi"  # 2x headroom
```

**Monitor and Adjust:**
```bash
# Check actual usage
kubectl top pod -n development -l model=my-model
```

### Autoscaling Strategy

**Development:**
```yaml
minReplicas: 1  # Keep running for testing
maxReplicas: 1  # No autoscaling needed
```

**Staging:**
```yaml
minReplicas: 1  # Always available
maxReplicas: 3  # Test scaling behavior
```

**Production:**
```yaml
minReplicas: 2  # High availability
maxReplicas: 10  # Scale for load
```

### Security Hardening

**Review trustRemoteCode:**
- Only enable when absolutely necessary
- Document in code comments WHY it's required
- Link to model documentation

**Set Resource Limits:**
- Always set memory limits (prevent OOM)
- Always set CPU limits (prevent CPU monopolization)
- GPU limits must equal requests

**Audit Model Sources:**
- Prefer official model repositories
- Check model license compatibility
- Review model card for security notes

### Performance Tuning

**Iterate on Runtime Args:**

1. **Start with defaults:**
   ```yaml
   runtimeArgs:
     - --dtype=auto
     - --max-model-len=2048
     - --gpu-memory-utilization=0.8
   ```

2. **Measure baseline performance**

3. **Tune one parameter at a time:**
   - Increase `--max-model-len` for longer contexts
   - Increase `--gpu-memory-utilization` for better throughput
   - Adjust `--max-num-seqs` for concurrency

4. **Benchmark after each change**

## Review Checklist

Before submitting your PR, ensure:

### Configuration Quality

- [ ] YAML syntax is valid (yamllint passes)
- [ ] File name follows naming conventions
- [ ] `metadata.name` matches file name
- [ ] All required labels are present
- [ ] `modelID` is correct and verified on HuggingFace
- [ ] Resource requests match model size
- [ ] Tolerations are complete
- [ ] `trustRemoteCode` is appropriate and documented

### Testing Completeness

- [ ] Dry-run apply succeeds
- [ ] Model deploys successfully in development
- [ ] All pods reach Running state
- [ ] Logs show no errors
- [ ] Inference endpoint responds correctly
- [ ] Basic inference test passes
- [ ] Streaming test passes (if applicable)
- [ ] Performance metrics are reasonable

### Documentation

- [ ] PR description is complete
- [ ] Model details are documented
- [ ] Security considerations are noted
- [ ] Test results are included
- [ ] Any special requirements are documented

### Security Review

- [ ] Model source is trusted
- [ ] `trustRemoteCode` usage is justified
- [ ] Resource limits are set
- [ ] No credentials or secrets in config
- [ ] License is compatible with platform usage

### Process Compliance

- [ ] PR targets `develop` branch
- [ ] Commit message follows conventional commits
- [ ] Branch name follows convention
- [ ] Automated checks pass
- [ ] At least 1 reviewer approval obtained

## Getting Help

### Documentation

- **[Getting Started](getting-started.md)**: Quick start guide
- **[AIModel Reference](aimodel-reference.md)**: Complete field reference
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Contribution guidelines

### Support Channels

- **GitHub Issues**: https://github.com/otherjamesbrown/ai-aas-config/issues
- **Platform Docs**: https://github.com/otherjamesbrown/ai-aas
- **Model Operator Logs**: `kubectl logs -n ai-model-operator -l app=ai-model-operator`

### External Resources

- **HuggingFace Models**: https://huggingface.co/models
- **vLLM Documentation**: https://docs.vllm.ai/
- **KServe Documentation**: https://kserve.github.io/website/

## Summary

This guide covered:
- Complete step-by-step submission process
- Naming conventions and best practices
- Comprehensive testing requirements
- Common issues and troubleshooting
- Review checklist

Follow this guide to ensure smooth model deployments and successful reviews. Happy submitting!
