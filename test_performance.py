# test_performance.py
import time
import psutil
import torch

def test_performance():
    print("=" * 50)
    print("性能测试")
    print("=" * 50)
    
    # CPU 使用率
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"\nCPU 使用率: {cpu_percent}%")
    
    # 内存使用
    memory = psutil.virtual_memory()
    print(f"内存使用: {memory.percent}% ({memory.used / 1024**3:.1f} GB / {memory.total / 1024**3:.1f} GB)")
    
    # GPU 使用（如果有）
    if torch.cuda.is_available():
        print(f"\nGPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU 内存使用: {torch.cuda.memory_allocated() / 1024**3:.1f} GB")
        print(f"GPU 内存缓存: {torch.cuda.memory_reserved() / 1024**3:.1f} GB")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_performance()