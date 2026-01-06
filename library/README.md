# Model Library

This directory contains the **base configurations** for all available AI models in the platform.

## Purpose

The library serves as the **single source of truth** for model definitions:
- Model identity (HuggingFace ID, display name, description)
- HuggingFace requirements (token, trust_remote_code)
- Available GPU architecture variants (Ada, Blackwell, etc.)
- **Build configurations** to reproduce engines
- S3 paths for pre-built engines
- Container versions and runtime requirements
- Default resource requests
- Known issues and limitations

## Structure

```
library/
├── README.md
└── models/
    ├── llama-3-1-8b-instruct-trtllm.yaml    # TensorRT-LLM variants
    ├── qwen2-vl-7b-instruct.yaml            # vLLM (trust_remote_code example)
    └── ...
```

## Library Entry Schema

### Top-Level Fields

```yaml
spec:
  modelID: meta-llama/Llama-3.1-8B-Instruct  # HuggingFace model ID
  displayName: "Human-readable name"
  description: "Model description"
  modelType: text | vision-language | embedding

  huggingface:
    # HuggingFace-specific configuration
    ...

  variants:
    ada:
      # GPU-specific variant
      ...
    blackwell:
      # Another GPU variant
      ...
```

### HuggingFace Configuration

```yaml
huggingface:
  modelId: meta-llama/Llama-3.1-8B-Instruct

  # Gated models (Llama, Mistral) require HF_TOKEN
  requiresToken: true
  tokenSecretRef: hf-token  # K8s secret name

  # Models with custom code (Qwen, some others)
  trustRemoteCode: true  # Maps to --trust-remote-code in vLLM

  # Pin to specific version for reproducibility
  revision: "main"  # or commit hash
```

### Variant Configuration

Each variant defines a GPU-specific deployment:

```yaml
variants:
  ada:
    gpuArchitecture: sm_89
    gpuName: "RTX 4000 Ada Generation"

    # Runtime config
    runtime: tensorrt-llm | vllm
    container: nvcr.io/nvidia/tritonserver:24.10-trtllm-python-py3
    s3Bucket: ai-aas
    s3Key: models/ada/llama-3.1-8b-instruct/trtllm-v1-fp8

    # Build config (for TensorRT-LLM)
    buildConfig:
      ...

    # vLLM config (for vLLM runtime)
    vllmConfig:
      ...

    # Deployment targeting
    nodeSelector:
      nvidia.com/gpu.product: NVIDIA-RTX-4000-Ada-Generation
    resources:
      ...
```

### Build Configuration (TensorRT-LLM)

For models that require pre-built engines:

```yaml
buildConfig:
  # Build environment
  container: nvcr.io/nvidia/tritonserver:24.10-trtllm-python-py3
  preInstall:
    - "pip install setuptools"  # Container quirks

  # TensorRT-LLM parameters
  trtllm:
    maxBatchSize: 32
    maxInputLen: 4096
    maxSeqLen: 8192
    maxNumTokens: 4096

  # Quantization
  quantization:
    algorithm: FP8 | BF16 | INT8
    kvCacheAlgo: FP8  # Optional

  # API version (changed between TRT-LLM versions)
  buildApi: hlapi | llmapi

  # Reference to detailed runbook
  runbook: docs/runbooks/rebuild-trtllm-fp8-ada.md

  # Expected build time
  buildTime: "5-15 minutes"
```

### vLLM Configuration

For models loaded directly from HuggingFace:

```yaml
vllmConfig:
  model: Qwen/Qwen2-VL-7B-Instruct
  trustRemoteCode: true  # Required for some models

  # Memory settings
  maxModelLen: 4096
  gpuMemoryUtilization: 0.90

  # Parallelism
  tensorParallelSize: 1

  # Optional quantization
  quantization: awq  # Use pre-quantized version
```

### Known Issues

Track bugs and workarounds:

```yaml
knownIssues:
  - issue: "/v1/chat/completions broken"
    description: "trtllm-serve has async bug"
    workaround: "Use /v1/completions endpoint"
    tracking: "https://github.com/NVIDIA/TensorRT-LLM/issues/5648"
    affectedVersions: ["0.20.0", "0.21.0"]
```

## GPU Architecture Reference

| GPU | Compute Capability | Directory | Container |
|-----|-------------------|-----------|-----------|
| RTX 4000 Ada | sm_89 | `models/ada/` | 24.10+ |
| RTX PRO 6000 Blackwell | sm_120 | `models/blackwell/` | 25.06+ |
| H100 | sm_90 | `models/hopper/` | 24.08+ |

## Common HuggingFace Flags

| Model | requiresToken | trustRemoteCode |
|-------|---------------|-----------------|
| Llama 3.x | Yes (gated) | No |
| Mistral | Yes (gated) | No |
| Qwen/Qwen2-VL | No | **Yes** |
| microsoft/phi-3 | No | **Yes** |
| deepseek-ai/* | No | **Yes** |

## Adding a New Model

1. **Create library entry**: `library/models/<model-name>.yaml`
2. **Define HuggingFace config**: token requirements, trust_remote_code
3. **Define variants** for each GPU architecture
4. **Add build config** if using TensorRT-LLM
5. **Document S3 paths** where engines are stored
6. **Add environment configs** that reference the library entry

## Engine Versioning Convention

TensorRT-LLM engine paths: `models/<gpu>/<model>/trtllm-v<N>[-<details>]/`

Examples:
- `trtllm-v1` - First version
- `trtllm-v1-fp8` - FP8 quantized
- `trtllm-v2-021` - Version 2, TRT-LLM 0.21.0

## Reproducing an Engine Build

1. Look up the model in `library/models/`
2. Find the variant for your GPU
3. Check `buildConfig` for parameters
4. Follow the linked `runbook` for step-by-step instructions
