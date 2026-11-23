# onnxruntime-objc 1.22.0

The `objectivec/` sources of ONNX Runtime 1.22.0 that CocoaPods trunk's
`onnxruntime-objc` 1.22.0 pod compiles (the same file list), with ONNX
Runtime's MIT `LICENSE`. They are committed because the pod's download host,
download.onnxruntime.ai, is dead, and so is `github.com/microsoft/onnxruntime`.

Source: Microsoft's release commit `f217402897f40ebba457e2421bc0a4702771968e`
(branch `rel-1.22.0`, named in the NuGet package Microsoft.ML.OnnxRuntime
1.22.0), taken from a surviving fork of the repository that holds that commit
(`intel/onnxruntime`). Every file's git blob hash matched the commit's tree.
Nothing was changed.

`brand/tools/onnxruntime_pods.py` builds the matching `onnxruntime-c` pod and
points the CI build's Podfile at both.
