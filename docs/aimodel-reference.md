# AIModel Custom Resource Reference

Complete reference documentation for the `AIModel` Custom Resource Definition (CRD).

## Table of Contents

- [Overview](#overview)
- [API Version and Kind](#api-version-and-kind)
- [Metadata](#metadata)
- [Spec Fields](#spec-fields)
  - [Required Fields](#required-fields)
  - [Optional Fields](#optional-fields)
  - [Resources](#resources)
  - [Autoscaling](#autoscaling)
  - [Scheduling](#scheduling)
  - [Runtime Configuration](#runtime-configuration)
  - [Security](#security)
- [Status Fields](#status-fields)
- [Resource Requirements Guide](#resource-requirements-guide)
- [Runtime Options](#runtime-options)
- [Complete Examples](#complete-examples)

## Overview

The `AIModel` Custom Resource (CR) is the primary interface for deploying AI models on the AI-AAS Platform. It provides a declarative way to specify:

- What model to deploy (HuggingFace model ID)
- How to deploy it (runtime, resources, scaling)
- Where to deploy it (namespace, node selection)
- Security settings (trust remote code, resource limits)

The AI Model Operator watches for `AIModel` resources and:
1. Downloads model artifacts (if needed)
2. Creates a KServe `InferenceService`
3. Manages lifecycle (updates, scaling, deletion)
4. Reports status and health

## API Version and Kind

```yaml
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
```

- **API Group**: `aimodel.ai-aas.io`
- **Version**: `v1alpha1` (alpha stability, subject to change)
- **Kind**: `AIModel`

## Metadata

Standard Kubernetes metadata fields.

### Required Fields

```yaml
metadata:
  name: string              # REQUIRED: Unique name within namespace
  namespace: string         # REQUIRED: Kubernetes namespace
```

### Recommended Labels

```yaml
metadata:
  labels:
    app: vllm-inference              # Standard label for vLLM-based models
    model: string                    # Model family (e.g., mistral, llama, gpt)
    version: string                  # Model version (e.g., v0.3, 7b, 20b)
    environment: string              # Environment (development, staging, production)
    provider: string                 # Optional: model provider (e.g., unsloth, openai)
```

**Example:**
```yaml
metadata:
  name: mistral-7b-instruct-v03
  namespace: development
  labels:
    app: vllm-inference
    model: mistral
    version: 7b-v03
    environment: development
```

## Spec Fields

The `spec` section defines the desired state of the model deployment.

### Required Fields

#### modelName

- **Type**: `string`
- **Required**: Yes
- **Description**: Human-readable name of the AI model
- **Validation**: Minimum length 1 character
- **Recommendation**: Match `metadata.name` for consistency

```yaml
spec:
  modelName: mistral-7b-instruct-v03
```

#### modelID

- **Type**: `string`
- **Required**: Yes
- **Description**: Unique identifier for the model, typically a HuggingFace model ID
- **Format**: `{organization}/{model-name}` or `{username}/{model-name}`

```yaml
spec:
  modelID: mistralai/Mistral-7B-Instruct-v0.3
```

**Common Model IDs:**
- `mistralai/Mistral-7B-Instruct-v0.3`
- `meta-llama/Llama-2-7b-hf`
- `meta-llama/Llama-2-70b-hf`
- `gpt2`
- `openai/gpt-oss-20b`

### Optional Fields

#### s3Bucket

- **Type**: `string`
- **Required**: No (optional when `trustRemoteCode: true`)
- **Description**: S3 bucket where model artifacts are stored
- **Usage**: Pre-downloaded models for faster deployment

```yaml
spec:
  s3Bucket: my-models-bucket
  s3Key: models/mistral-7b/
```

#### s3Key

- **Type**: `string`
- **Required**: No (optional when `trustRemoteCode: true`)
- **Description**: S3 key (path) to the model artifacts

#### enabled

- **Type**: `boolean`
- **Required**: No
- **Default**: `true`
- **Description**: Whether the model deployment should be active
- **Behavior**: When `false`, InferenceService is scaled to zero replicas

```yaml
spec:
  enabled: true   # Model is active
  # enabled: false  # Model is disabled (scaled to zero)
```

**Use Cases:**
- Temporarily disable a model without deleting the CR
- Cost savings by scaling unused models to zero
- A/B testing by toggling between model versions

#### runtime

- **Type**: `string`
- **Required**: No
- **Default**: `vllm`
- **Allowed Values**: `vllm`, `triton`, `tgi`
- **Description**: Inference runtime to use

```yaml
spec:
  runtime: vllm
```

See [Runtime Options](#runtime-options) for details on each runtime.

#### runtimeName

- **Type**: `string`
- **Required**: No
- **Description**: Name of a custom `ClusterServingRuntime` to use
- **Usage**: Override the default runtime for advanced customization

```yaml
spec:
  runtime: vllm
  runtimeName: custom-vllm-runtime  # Use custom runtime instead of default
```

### Autoscaling

#### minReplicas

- **Type**: `int32`
- **Required**: No
- **Default**: `0`
- **Minimum**: `0`
- **Description**: Minimum number of replicas for autoscaling
- **Special**: Set to `0` to enable scale-to-zero

```yaml
spec:
  minReplicas: 0   # Enable scale-to-zero
  # minReplicas: 1   # Always keep at least 1 replica running
```

**Considerations:**
- `minReplicas: 0` saves costs but adds cold-start latency
- `minReplicas: 1` ensures faster response times but costs more

#### maxReplicas

- **Type**: `int32`
- **Required**: No
- **Default**: `1`
- **Minimum**: `1`
- **Description**: Maximum number of replicas for autoscaling

```yaml
spec:
  minReplicas: 1
  maxReplicas: 5   # Scale up to 5 replicas under load
```

#### replicas (DEPRECATED)

- **Type**: `int32`
- **Required**: No
- **Status**: DEPRECATED - Use `minReplicas`/`maxReplicas` instead
- **Description**: Fixed number of replicas (no autoscaling)

### Resources

#### resources

- **Type**: `ResourceRequirements` (Kubernetes type)
- **Required**: No (but strongly recommended)
- **Description**: Compute resources required by the inference container

```yaml
spec:
  resources:
    requests:
      cpu: "4"                # CPU cores requested
      memory: "16Gi"          # Memory requested
      nvidia.com/gpu: "1"     # Number of GPUs requested
    limits:
      cpu: "8"                # Maximum CPU cores
      memory: "32Gi"          # Maximum memory
      nvidia.com/gpu: "1"     # GPU limit (must match request)
```

**Important:**
- GPU limits MUST equal GPU requests (GPUs are not overcommittable)
- Set reasonable limits to prevent resource exhaustion
- See [Resource Requirements Guide](#resource-requirements-guide)

### Scheduling

#### nodeSelector

- **Type**: `map[string]string`
- **Required**: No
- **Description**: Node labels for pod scheduling

```yaml
spec:
  nodeSelector:
    gpu-type: a100           # Require A100 GPUs
    zone: us-east-1a         # Specific availability zone
    node-role: gpu-inference # Custom node role
```

#### tolerations

- **Type**: `[]Toleration` (Kubernetes type)
- **Required**: No (but required for GPU nodes)
- **Description**: Tolerations for pod scheduling on tainted nodes

```yaml
spec:
  tolerations:
    - key: nvidia.com/gpu          # Standard GPU toleration
      operator: Exists
      effect: NoSchedule
    - key: gpu-workload            # Custom taint
      operator: Equal
      value: "true"
      effect: NoSchedule
```

**Common GPU Tolerations:**
```yaml
# Minimal (for basic GPU access)
tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule

# Complete (for production)
tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
  - key: gpu-workload
    operator: Equal
    value: "true"
    effect: NoSchedule
```

### Runtime Configuration

#### runtimeArgs

- **Type**: `[]string` (string array)
- **Required**: No
- **Description**: Additional command-line arguments for the runtime
- **Runtime-Specific**: Arguments depend on the selected runtime

**vLLM Runtime Arguments:**
```yaml
spec:
  runtime: vllm
  runtimeArgs:
    - --dtype=auto                      # Data type (auto, float16, bfloat16)
    - --max-model-len=8192              # Maximum sequence length
    - --gpu-memory-utilization=0.9      # GPU memory utilization (0.0-1.0)
    - --tensor-parallel-size=1          # Number of GPUs for tensor parallelism
    - --pipeline-parallel-size=1        # Number of GPUs for pipeline parallelism
    - --max-num-seqs=256                # Maximum concurrent sequences
    - --max-num-batched-tokens=8192     # Maximum tokens in a batch
```

**Common Arguments:**

| Argument | Description | Default | Recommended Values |
|----------|-------------|---------|-------------------|
| `--dtype` | Data type precision | `auto` | `auto`, `float16`, `bfloat16` |
| `--max-model-len` | Max sequence length | Model config | 2048, 4096, 8192, 16384 |
| `--gpu-memory-utilization` | GPU memory % to use | `0.9` | 0.8-0.95 |
| `--tensor-parallel-size` | GPUs for tensor parallelism | `1` | 1, 2, 4, 8 |
| `--max-num-seqs` | Max concurrent sequences | `256` | 128, 256, 512 |

See [vLLM Documentation](https://docs.vllm.ai/) for all options.

#### runtimeEnv

- **Type**: `[]EnvVar` (Kubernetes type)
- **Required**: No
- **Description**: Additional environment variables for the runtime container

```yaml
spec:
  runtimeEnv:
    - name: VLLM_WORKER_MULTIPROC_METHOD
      value: spawn
    - name: CUDA_VISIBLE_DEVICES
      value: "0"
    - name: VLLM_LOGGING_LEVEL
      value: INFO
```

**Common Environment Variables:**
- `VLLM_WORKER_MULTIPROC_METHOD`: Multiprocessing method (`spawn`, `fork`)
- `CUDA_VISIBLE_DEVICES`: GPU device selection
- `VLLM_LOGGING_LEVEL`: Logging verbosity
- `HF_HOME`: HuggingFace cache directory
- `TRANSFORMERS_CACHE`: Transformers cache directory

### Security

#### trustRemoteCode

- **Type**: `boolean`
- **Required**: No
- **Default**: `false`
- **Description**: Allow the runtime to execute custom model code from the model repository

```yaml
spec:
  trustRemoteCode: true   # Allow custom code execution
```

**SECURITY WARNING:**

Setting `trustRemoteCode: true` allows the model to execute arbitrary Python code during loading and inference. This code:
- Runs with full container permissions
- Can access network resources
- Can read/write files
- Is NOT sandboxed

**When to use `true`:**
- Model uses custom architecture not in standard `transformers`
- Model from trusted source (official org like Meta, Mistral AI)
- Custom tokenizers or processing logic required

**When to use `false`:**
- Model uses standard `transformers` architecture
- Security policy requires code review
- Unknown or untrusted model source

**Models Requiring `trustRemoteCode: true`:**
- Many custom architectures (Phi, StarCoder, etc.)
- Models with custom tokenizers
- Fine-tuned models with modified architectures

**Models NOT Requiring It:**
- Standard GPT-2, GPT-Neo models
- Standard BERT, RoBERTa models
- Most standard LLaMA-based models

## Status Fields

The `status` section is managed by the AI Model Operator and reflects the observed state.

### phase

- **Type**: `string` (enum)
- **Description**: Current phase of the AIModel deployment

**Possible Values:**

| Phase | Description |
|-------|-------------|
| `Pending` | Waiting to be processed |
| `Downloading` | Model artifacts being downloaded |
| `Deploying` | InferenceService being created/updated |
| `Ready` | Model ready to serve inference requests |
| `Failed` | Error occurred during deployment |
| `Disabled` | Model disabled (scaled to zero) |
| `RetryPending` | Retry scheduled after download failure |

### conditions

- **Type**: `[]Condition` (Kubernetes type)
- **Description**: Latest observations of the object's state

### inferenceServiceName

- **Type**: `string`
- **Description**: Name of the associated KServe InferenceService

### inferenceEndpoint

- **Type**: `string`
- **Description**: URL where the model can be accessed for inference

```bash
# Get inference endpoint
kubectl get aimodel my-model -o jsonpath='{.status.inferenceEndpoint}'
```

### readyReplicas

- **Type**: `int32`
- **Description**: Number of replicas ready to serve requests

### downloadProgress

- **Type**: `int32`
- **Range**: 0-100
- **Description**: Progress of model artifact download (percentage)

### message

- **Type**: `string`
- **Description**: Additional information about the current phase

### retryCount

- **Type**: `int32`
- **Description**: Number of download retry attempts

## Resource Requirements Guide

Guidelines for setting resource requests and limits based on model size.

### GPU Memory Requirements

| Model Size | GPU Memory | Recommended GPU | Example Models |
|------------|------------|-----------------|----------------|
| < 1B params | 4-6 GB | T4, RTX 3060 | GPT-2, DistilGPT-2 |
| 1-3B params | 6-12 GB | T4, RTX 3080 | GPT-Neo 2.7B, Pythia 2.8B |
| 3-7B params | 12-16 GB | RTX 3090, A10 | Mistral 7B, Llama 2 7B |
| 7-13B params | 16-24 GB | A10, A100 40GB | Llama 2 13B, Vicuna 13B |
| 13-30B params | 24-48 GB | A100 40GB, A100 80GB | Llama 2 30B, Falcon 40B |
| 30-70B params | 48-80 GB | A100 80GB, H100 | Llama 2 70B, Falcon 180B |
| 70B+ params | 80GB+ | A100 80GB (multi), H100 | Llama 3 70B, GPT-3 |

**Notes:**
- Requirements assume FP16 precision
- INT8/INT4 quantization can reduce requirements by 50-75%
- Tensor parallelism can distribute models across multiple GPUs

### CPU and Memory Recommendations

**Small Models (< 7B params):**
```yaml
resources:
  requests:
    cpu: "2"
    memory: "8Gi"
    nvidia.com/gpu: "1"
  limits:
    cpu: "4"
    memory: "16Gi"
    nvidia.com/gpu: "1"
```

**Medium Models (7-13B params):**
```yaml
resources:
  requests:
    cpu: "4"
    memory: "16Gi"
    nvidia.com/gpu: "1"
  limits:
    cpu: "8"
    memory: "32Gi"
    nvidia.com/gpu: "1"
```

**Large Models (13-70B params):**
```yaml
resources:
  requests:
    cpu: "8"
    memory: "32Gi"
    nvidia.com/gpu: "2"  # May require multiple GPUs
  limits:
    cpu: "16"
    memory: "64Gi"
    nvidia.com/gpu: "2"
```

### Multi-GPU Configuration

For models requiring multiple GPUs, use tensor parallelism:

```yaml
spec:
  resources:
    requests:
      nvidia.com/gpu: "4"
    limits:
      nvidia.com/gpu: "4"
  runtimeArgs:
    - --tensor-parallel-size=4       # Distribute across 4 GPUs
    - --gpu-memory-utilization=0.9
```

## Runtime Options

### vLLM (Default)

High-performance inference runtime optimized for LLMs.

**Strengths:**
- Excellent throughput for large batch sizes
- PagedAttention for efficient memory usage
- Continuous batching
- Fast for autoregressive generation

**Best For:**
- Large language models (GPT, LLaMA, Mistral)
- High-throughput scenarios
- Production deployments

**Configuration:**
```yaml
spec:
  runtime: vllm
  runtimeArgs:
    - --dtype=auto
    - --max-model-len=8192
    - --gpu-memory-utilization=0.9
```

### Triton Inference Server

NVIDIA's multi-framework inference server.

**Strengths:**
- Supports multiple frameworks (PyTorch, TensorFlow, ONNX)
- Dynamic batching
- Model ensembles
- Model versioning

**Best For:**
- Multi-model deployments
- Mixed framework environments
- Enterprise deployments

**Configuration:**
```yaml
spec:
  runtime: triton
  # Triton-specific configuration via runtimeArgs
```

### Text Generation Inference (TGI)

HuggingFace's inference runtime.

**Strengths:**
- Built by HuggingFace
- Tight integration with transformers
- Good developer experience
- Streaming support

**Best For:**
- HuggingFace models
- Developer-friendly environments
- Streaming use cases

**Configuration:**
```yaml
spec:
  runtime: tgi
  # TGI-specific configuration via runtimeArgs
```

## Complete Examples

### Small Model (GPT-2)

```yaml
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: gpt2-small
  namespace: development
  labels:
    app: vllm-inference
    model: gpt2
    environment: development
spec:
  modelName: gpt2-small
  modelID: gpt2
  enabled: true
  runtime: vllm
  minReplicas: 0  # Scale to zero when idle
  maxReplicas: 3
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
  trustRemoteCode: false
```

### Medium Model (Mistral 7B)

```yaml
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: mistral-7b-instruct-v03
  namespace: staging
  labels:
    app: vllm-inference
    model: mistral
    version: 7b-v03
    environment: staging
spec:
  modelName: mistral-7b-instruct-v03
  modelID: mistralai/Mistral-7B-Instruct-v0.3
  enabled: true
  runtime: vllm
  minReplicas: 1
  maxReplicas: 1
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
      nvidia.com/gpu: "1"
    limits:
      cpu: "8"
      memory: "32Gi"
      nvidia.com/gpu: "1"
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
    - key: gpu-workload
      operator: Equal
      value: "true"
      effect: NoSchedule
  runtimeArgs:
    - --dtype=auto
    - --max-model-len=8192
    - --gpu-memory-utilization=0.9
  trustRemoteCode: true
```

### Large Model (LLaMA 2 70B) - Multi-GPU

```yaml
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: llama2-70b-chat
  namespace: production
  labels:
    app: vllm-inference
    model: llama2
    version: 70b
    environment: production
spec:
  modelName: llama2-70b-chat
  modelID: meta-llama/Llama-2-70b-chat-hf
  enabled: true
  runtime: vllm
  minReplicas: 1
  maxReplicas: 2
  resources:
    requests:
      cpu: "16"
      memory: "64Gi"
      nvidia.com/gpu: "4"  # 4x A100 GPUs
    limits:
      cpu: "32"
      memory: "128Gi"
      nvidia.com/gpu: "4"
  nodeSelector:
    gpu-type: a100-80gb
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
    - key: gpu-workload
      operator: Equal
      value: "true"
      effect: NoSchedule
  runtimeArgs:
    - --dtype=bfloat16
    - --max-model-len=4096
    - --gpu-memory-utilization=0.95
    - --tensor-parallel-size=4      # Distribute across 4 GPUs
    - --max-num-seqs=128
  runtimeEnv:
    - name: VLLM_WORKER_MULTIPROC_METHOD
      value: spawn
  trustRemoteCode: false
```

### Model with S3 Storage

```yaml
apiVersion: aimodel.ai-aas.io/v1alpha1
kind: AIModel
metadata:
  name: custom-model
  namespace: production
  labels:
    app: vllm-inference
    model: custom
    environment: production
spec:
  modelName: custom-model
  modelID: myorg/custom-model
  s3Bucket: my-models-bucket
  s3Key: models/custom-model-v1/
  enabled: true
  runtime: vllm
  minReplicas: 2
  maxReplicas: 5
  resources:
    requests:
      cpu: "8"
      memory: "32Gi"
      nvidia.com/gpu: "2"
    limits:
      cpu: "16"
      memory: "64Gi"
      nvidia.com/gpu: "2"
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
  runtimeArgs:
    - --dtype=auto
    - --max-model-len=4096
    - --gpu-memory-utilization=0.9
    - --tensor-parallel-size=2
  trustRemoteCode: false
```

## Additional Resources

- **[Getting Started Guide](getting-started.md)**: Quick start tutorial
- **[Model Submission Guide](model-submission-guide.md)**: How to submit models
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Contribution guidelines
- **vLLM Documentation**: https://docs.vllm.ai/
- **KServe Documentation**: https://kserve.github.io/website/
- **HuggingFace Models**: https://huggingface.co/models
