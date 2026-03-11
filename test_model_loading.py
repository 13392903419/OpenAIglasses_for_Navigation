# test_model_loading.py
import torch
from ultralytics import YOLO
import os

print("=" * 50)
print("测试模型加载")
print("=" * 50)

# 测试 CUDA
print(f"\nPyTorch 版本: {torch.__version__}")
print(f"CUDA 可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA 版本: {torch.version.cuda}")
    print(f"GPU 设备: {torch.cuda.get_device_name(0)}")

# 测试模型
models = {
    'yolo-seg.pt': '盲道分割',
    'yoloe-11l-seg.pt': '开放词汇检测',
    'shoppingbest5.pt': '物品识别',
    'trafficlight.pt': '红绿灯检测',
}

print("\n" + "=" * 50)
print("测试 YOLO 模型加载")
print("=" * 50)

for model_file, desc in models.items():
    model_path = f'model/{model_file}'
    if os.path.exists(model_path):
        try:
            print(f"\n加载 {desc} ({model_file})...")
            model = YOLO(model_path)
            print(f"✓ {desc} 加载成功")
        except Exception as e:
            print(f"✗ {desc} 加载失败: {e}")
    else:
        print(f"✗ {model_file} 文件不存在")

# 测试 MediaPipe
print("\n" + "=" * 50)
print("测试 MediaPipe 手部检测")
print("=" * 50)

hand_model = 'model/hand_landmarker.task'
if os.path.exists(hand_model):
    try:
        import mediapipe as mp
        print(f"✓ MediaPipe 版本: {mp.__version__}")
        print(f"✓ 手部模型文件存在")
    except Exception as e:
        print(f"✗ MediaPipe 测试失败: {e}")
else:
    print(f"✗ 手部模型文件不存在")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)