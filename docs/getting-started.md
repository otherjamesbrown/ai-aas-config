# Getting Started with AI-AAS Config

This guide will help you get started with deploying AI models using the AI-AAS Config repository.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Repository Structure](#repository-structure)
- [Quick Start: Deploy Your First Model](#quick-start-deploy-your-first-model)
- [Verification Steps](#verification-steps)
- [Next Steps](#next-steps)
- [Troubleshooting](#troubleshooting)

## Overview

The AI-AAS Config repository contains declarative configuration files for deploying AI models across different environments. Each model is defined using an `AIModel` Custom Resource (CR) that describes:

- Model identity and source (HuggingFace model ID)
- Compute resources (CPU, memory, GPUs)
- Runtime configuration (vLLM, Triton, or TGI)
- Autoscaling behavior
- Security settings

When an `AIModel` CR is applied to a Kubernetes cluster, the AI Model Operator:
1. Downloads the model (if needed)
2. Creates a KServe InferenceService
3. Deploys the model using the specified runtime
4. Exposes an inference endpoint

## Prerequisites

Before you begin, ensure you have:

### Required Access

- **Git**: Clone access to this repository
- **Kubernetes**: kubectl access to the development cluster
- **ArgoCD**: Access to ArgoCD UI (for monitoring deployments)

### Required Tools

```bash
# Git
git --version

# kubectl
kubectl version --client

# yamllint (optional, for validation)
pip install yamllint

# argocd CLI (optional)
brew install argocd  # macOS
# or
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
```

### Access Credentials

Refer to the platform documentation for:
- Kubeconfig files for each environment
- ArgoCD credentials
- API endpoints

See: [docs/platform/environment-access.md](https://github.com/otherjamesbrown/ai-aas/blob/main/docs/platform/environment-access.md) in the main AI-AAS repository.

## Repository Structure

```
ai-aas-config/
├── CONTRIBUTING.md           # Contribution guidelines
├── README.md                 # Repository overview
├── LICENSE                   # Apache 2.0 license
│
├── environments/             # Environment-specific configurations
│   ├── development/          # Development environment
│   │   └── models/           # Model configurations for dev
│   │       ├── mistral-7b-instruct-v03.yaml
│   │       └── openai-gpt-oss-20b.yaml
│   ├── staging/              # Staging environment
│   │   └── models/           # Model configurations for staging
│   └── production/           # Production environment
│       └── models/           # Model configurations for production
│
├── examples/                 # Example configurations
│   └── aimodel-template.yaml # Template for new models
│
├── schemas/                  # JSON schemas for validation
│   └── aimodel-schema.json   # AIModel CR schema (future)
│
└── docs/                     # Documentation
    ├── getting-started.md    # This file
    ├── aimodel-reference.md  # Complete field reference
    └── model-submission-guide.md  # How to submit models
```

### Key Directories

- **environments/{env}/models/**: Model configurations per environment
- **examples/**: Templates and examples for common scenarios
- **docs/**: Comprehensive documentation

## Quick Start: Deploy Your First Model

Let's deploy a small model to the development environment.

### Step 1: Clone the Repository

```bash
git clone https://github.com/otherjamesbrown/ai-aas-config.git
cd ai-aas-config
```

### Step 2: Create a New Model Configuration

Create a file at `environments/development/models/my-first-model.yaml`:

```yaml
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: my-first-model
  namespace: development
  labels:
    app: vllm-inference
    model: gpt2
    environment: development
spec:
  modelName: my-first-model
  modelID: gpt2                    # Small model, good for testing
  enabled: true
  runtime: vllm
  minReplicas: 1
  maxReplicas: 1
  resources:
    requests:
      cpu: "2"
      memory: "4Gi"
      nvidia.com/gpu: "1"
    limits:
      cpu: "4"
      memory: "8Gi"
      nvidia.com/gpu: "1"
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
  runtimeArgs:
    - --dtype=auto
    - --max-model-len=1024
    - --gpu-memory-utilization=0.8
  trustRemoteCode: false           # GPT-2 uses standard architecture
```

### Step 3: Validate the Configuration

```bash
# Check YAML syntax
yamllint environments/development/models/my-first-model.yaml

# Dry-run (requires kubectl access)
kubectl apply -f environments/development/models/my-first-model.yaml --dry-run=client
```

### Step 4: Commit and Push

```bash
# Create a feature branch
git checkout -b feature/add-my-first-model

# Add and commit
git add environments/development/models/my-first-model.yaml
git commit -m "feat: Add my-first-model (GPT-2) for testing"

# Push to GitHub
git push origin feature/add-my-first-model
```

### Step 5: Create a Pull Request

1. Go to GitHub: https://github.com/otherjamesbrown/ai-aas-config
2. Click "Compare & pull request"
3. Set base branch to `develop`
4. Fill in PR description (see [CONTRIBUTING.md](../CONTRIBUTING.md))
5. Submit PR for review

### Step 6: Monitor Deployment (After PR Merge)

Once your PR is merged to `develop`, ArgoCD will automatically sync the changes:

```bash
# Set kubeconfig for development
export KUBECONFIG=/path/to/kubeconfig-development.yaml

# Watch AIModel status
kubectl get aimodel my-first-model -n development -w

# Expected phases: Pending → Downloading → Deploying → Ready
```

Check ArgoCD:
```bash
# Login to ArgoCD
argocd login argocd.dev.ai-aas.local

# Check app status
argocd app get ai-models-development
```

Or use the ArgoCD UI: https://argocd.dev.ai-aas.local

## Verification Steps

After deployment, verify the model is working:

### 1. Check AIModel Status

```bash
kubectl get aimodel my-first-model -n development

# Output should show:
# NAME              MODEL            RUNTIME   ENABLED   READY   PHASE   AGE
# my-first-model    my-first-model   vllm      true      1       Ready   5m
```

### 2. Check Pod Status

```bash
kubectl get pods -n development -l model=gpt2

# Should show running pod(s)
```

### 3. Check Logs

```bash
# Get the pod name
POD=$(kubectl get pod -n development -l model=gpt2 -o jsonpath='{.items[0].metadata.name}')

# View logs
kubectl logs -n development $POD
```

### 4. Test Inference Endpoint

```bash
# Get the inference endpoint from AIModel status
kubectl get aimodel my-first-model -n development -o jsonpath='{.status.inferenceEndpoint}'

# Test with curl
curl -X POST https://api.dev.ai-aas.local/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "my-first-model",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 50
  }'
```

Expected response:
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1702500000,
  "model": "my-first-model",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 15,
    "total_tokens": 27
  }
}
```

## Next Steps

Now that you've deployed your first model, you can:

### Learn More

- **[AIModel Reference](aimodel-reference.md)**: Complete field reference and examples
- **[Model Submission Guide](model-submission-guide.md)**: Best practices for adding models
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Contribution guidelines and workflow

### Deploy More Models

Explore existing configurations:
```bash
ls environments/development/models/

# Example models:
# - mistral-7b-instruct-v03.yaml  (7B parameter model)
# - openai-gpt-oss-20b.yaml       (20B parameter model)
```

### Promote to Staging

After testing in development:
1. Copy model config to `environments/staging/models/`
2. Update namespace to `staging`
3. Create PR from `develop` to `staging`
4. Monitor deployment in staging environment

### Customize Runtime Settings

Experiment with different runtime arguments:
- `--max-model-len`: Control maximum sequence length
- `--gpu-memory-utilization`: Adjust GPU memory usage
- `--dtype`: Change data type (float16, bfloat16, auto)

See [AIModel Reference](aimodel-reference.md#runtime-arguments) for all options.

## Troubleshooting

### Model Stuck in "Downloading" Phase

Check download progress:
```bash
kubectl get aimodel my-first-model -n development -o jsonpath='{.status.downloadProgress}'
```

View operator logs:
```bash
kubectl logs -n ai-model-operator -l app=ai-model-operator --tail=100
```

### Model in "Failed" Phase

Check status message:
```bash
kubectl get aimodel my-first-model -n development -o jsonpath='{.status.message}'
```

Common issues:
- **OOMKilled**: Increase memory limits in `resources.limits.memory`
- **ImagePullBackOff**: Check runtime image availability
- **GPU allocation failed**: Verify GPU node availability and tolerations

### Pod Not Starting

Check pod events:
```bash
kubectl describe pod -n development -l model=gpt2
```

Common issues:
- **Insufficient GPU**: No GPU nodes available
- **Resource limits too high**: Reduce CPU/memory requests
- **Toleration mismatch**: Verify tolerations match node taints

### Inference Endpoint Returns 404

Verify InferenceService is ready:
```bash
kubectl get inferenceservice -n development
```

Check API router configuration:
```bash
# In main AI-AAS repo
kubectl get configmap api-router-config -n system -o yaml
```

### Need More Help?

- **Platform Logs**: Check Grafana dashboards at http://grafana.172.232.58.222.nip.io
- **ArgoCD**: View sync status at https://argocd.dev.ai-aas.local
- **Issues**: File a GitHub issue with logs and configuration
- **Documentation**: See [AI-AAS Platform Docs](https://github.com/otherjamesbrown/ai-aas)

## Additional Resources

- **HuggingFace Models**: https://huggingface.co/models
- **vLLM Documentation**: https://docs.vllm.ai/
- **KServe Documentation**: https://kserve.github.io/website/
- **Kubernetes Documentation**: https://kubernetes.io/docs/

## Summary

You've learned how to:
- Clone and navigate the ai-aas-config repository
- Create an AIModel configuration
- Submit a pull request
- Monitor deployment with kubectl and ArgoCD
- Verify model functionality
- Troubleshoot common issues

Next, explore the [AIModel Reference](aimodel-reference.md) for advanced configuration options!
