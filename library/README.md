# Model Library

This directory contains the **base configurations** for all available AI models in the platform.

## Purpose

The library serves as the **single source of truth** for model definitions:
- Model identity (HuggingFace ID, display name, description)
- Available GPU architecture variants (Ada, Blackwell, etc.)
- S3 paths for pre-built engines
- Container versions and runtime requirements
- Default resource requests
- Known issues and limitations

## Structure

```
library/
└── models/
    ├── llama-3-1-8b-instruct-trtllm.yaml    # TensorRT-LLM variants
    ├── llama-3-1-8b-instruct-vllm.yaml      # vLLM variants
    ├── mistral-7b-instruct-v03.yaml
    └── ...
```

## How It Works

### 1. Library Entries Define Variants

Each library entry defines all available variants of a model:

```yaml
spec:
  modelID: meta-llama/Llama-3.1-8B-Instruct
  variants:
    ada:
      runtime: tensorrt-llm
      s3Key: models/ada/llama-3.1-8b-instruct/trtllm-v1-fp8
      nodeSelector:
        nvidia.com/gpu.product: NVIDIA-RTX-4000-Ada-Generation
    blackwell:
      runtime: tensorrt-llm-blackwell
      s3Key: models/blackwell/llama-3.1-8b-instruct/trtllm-v2-021
      nodeSelector:
        node.kubernetes.io/instance-type: g3-gpu-rtxpro6000-blackwell-1
```

### 2. Environment Configs Reference Library

Environment-specific AIModel CRs reference the library and select a variant:

```yaml
# environments/development/models/llama-3-1-8b-instruct-trtllm.yaml
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: llama-3-1-8b-instruct-trtllm
  namespace: development
spec:
  # Reference library entry
  libraryRef:
    name: llama-3-1-8b-instruct-trtllm
    variant: ada  # or "blackwell"

  # Environment-specific overrides
  enabled: true
  minReplicas: 1
  maxReplicas: 1
```

### 3. Operator Resolves Configuration

The ai-model-operator:
1. Reads the AIModel CR
2. Looks up the library entry
3. Merges variant defaults with environment overrides
4. Creates the actual deployment

## Adding a New Model

1. **Create library entry**: `library/models/<model-name>.yaml`
2. **Define variants** for each GPU architecture
3. **Document S3 paths** where engines are stored
4. **Add environment configs** that reference the library entry

## Adding a New Engine Version

When you build a new engine (e.g., upgraded TRT-LLM version):

1. Upload to S3 with new path: `models/<gpu>/model-name/trtllm-v2-021/`
2. Update library entry with new s3Key for the variant
3. Commit and push - ArgoCD syncs the change

## GPU Architecture Reference

| GPU | Compute Capability | Directory |
|-----|-------------------|-----------|
| RTX 4000 Ada | sm_89 | `models/ada/` |
| RTX PRO 6000 Blackwell | sm_120 | `models/blackwell/` |
| H100 | sm_90 | `models/hopper/` |

## Versioning Convention

Engine paths follow: `models/<gpu>/<model>/trtllm-v<N>[-<trtllm-version>]/`

Examples:
- `trtllm-v1` - First version
- `trtllm-v1-fp8` - FP8 quantized
- `trtllm-v2-021` - Second version, TRT-LLM 0.21.0
