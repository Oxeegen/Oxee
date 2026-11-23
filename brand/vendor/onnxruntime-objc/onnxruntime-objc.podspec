# ONNX Runtime 1.22.0's Objective-C pod, with CocoaPods trunk's settings for
# onnxruntime-objc 1.22.0 (tests left out). The sources are committed here:
# see README.md. Used by brand/tools/onnxruntime_pods.py.
Pod::Spec.new do |s|
  s.name             = 'onnxruntime-objc'
  s.version          = '1.22.0'
  s.summary          = 'ONNX Runtime Objective-C Pod'
  s.description      = 'A pod for the ONNX Runtime Objective-C API.'
  s.homepage         = 'https://onnxruntime.ai'
  s.license          = { :type => 'MIT', :file => 'LICENSE' }
  s.authors          = { 'ONNX Runtime' => 'onnxruntime@microsoft.com' }
  s.source           = { :path => '.' }
  s.platform         = :ios, '15.1'
  s.preserve_paths   = 'LICENSE'
  s.default_subspecs = 'Core'
  s.static_framework = true

  s.subspec 'Core' do |core|
    core.dependency 'onnxruntime-c', '1.22.0'
    core.requires_arc = true
    core.compiler_flags = '-std=c++17', '-fobjc-arc-exceptions', '-Wall', '-Wextra', '-Werror'
    core.pod_target_xcconfig = {
      'HEADER_SEARCH_PATHS' => '"${PODS_TARGET_SRCROOT}/objectivec"',
      'OTHER_CPLUSPLUSFLAGS' => '-fvisibility=hidden -fvisibility-inlines-hidden',
    }
    core.public_header_files = 'objectivec/include/*.h'
    core.source_files = 'objectivec/*.{h,mm}', 'objectivec/include/*.h'
  end
end
