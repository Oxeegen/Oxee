# ONNX Runtime 1.22.0's C/C++ pod, with CocoaPods trunk's settings for
# onnxruntime-c 1.22.0. onnxruntime.xcframework and Headers/ come from
# Microsoft's NuGet package, unpacked here in CI by
# brand/tools/onnxruntime_pods.py (trunk's download host is dead).
Pod::Spec.new do |s|
  s.name                = 'onnxruntime-c'
  s.version             = '1.22.0'
  s.summary             = 'ONNX Runtime C/C++ Pod'
  s.description         = 'A pod for the ONNX Runtime C/C++ library.'
  s.homepage            = 'https://onnxruntime.ai'
  s.license             = { :type => 'MIT', :file => 'LICENSE' }
  s.authors             = { 'ONNX Runtime' => 'onnxruntime@microsoft.com' }
  s.source              = { :path => '.' }
  s.platform            = :ios, '15.1'
  s.vendored_frameworks = 'onnxruntime.xcframework'
  s.static_framework    = true
  s.weak_frameworks     = 'CoreML'
  s.source_files        = 'Headers/*.h'
  s.preserve_paths      = 'LICENSE'
  s.libraries           = 'c++'
  s.pod_target_xcconfig = {
    'OTHER_CPLUSPLUSFLAGS' => '-fvisibility=hidden -fvisibility-inlines-hidden',
  }
end
