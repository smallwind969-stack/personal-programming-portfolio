import os
import time
import csv
import psutil
import subprocess
import threading
import pandas as pd
import matplotlib.pyplot as plt

# ====== 中文字体设置 ======
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ========= 配置 =========
MONITOR_SECONDS = 120
APP_NAME = "app2.py"
TIMING_CSV = "timing_results.csv"
RESOURCE_CSV = "resource_usage_results.csv"

# ========= 全局数据 =========
mem_list = []
gpu_list = []
time_list = []
running = True


def find_app_process():
    """自动查找 app2.py 进程"""
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = p.info.get('cmdline')
            if cmdline and APP_NAME in ' '.join(cmdline):
                print(f"已找到 {APP_NAME} 进程 PID: {p.info['pid']}")
                return psutil.Process(p.info['pid'])
        except Exception:
            continue
    raise RuntimeError(f"未找到 {APP_NAME} 进程，请先启动系统后再运行监控脚本。")


def get_total_gpu_memory():
    """获取当前 GPU 总显存占用（MB）"""
    try:
        result = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits"
            ],
            encoding="utf-8",
            errors="ignore"
        ).strip().splitlines()

        values = []
        for line in result:
            line = line.strip()
            if line:
                values.append(int(line))
        return max(values) if values else 0
    except Exception:
        return 0


def get_existing_test_keys():
    """
    读取 timing_results.csv 中已有记录，
    用于判断本次监控期间是否新增了完整测试记录
    返回 set[(timestamp, patient_id)]
    """
    if not os.path.exists(TIMING_CSV):
        return set()

    try:
        df = pd.read_csv(TIMING_CSV, encoding="utf-8-sig")
    except Exception:
        return set()

    if "timestamp" not in df.columns or "patient_id" not in df.columns:
        return set()

    keys = set()
    for _, row in df.iterrows():
        keys.add((str(row["timestamp"]), str(row["patient_id"])))
    return keys


def get_newest_new_test(old_keys):
    """
    在监控结束后，从 timing_results.csv 中找出新增的一条完整测试记录
    返回 dict: {"timestamp": ..., "patient_id": ...}
    """
    if not os.path.exists(TIMING_CSV):
        return None

    try:
        df = pd.read_csv(TIMING_CSV, encoding="utf-8-sig")
    except Exception:
        return None

    if "timestamp" not in df.columns or "patient_id" not in df.columns:
        return None

    new_rows = []
    for _, row in df.iterrows():
        key = (str(row["timestamp"]), str(row["patient_id"]))
        if key not in old_keys:
            new_rows.append({
                "timestamp": str(row["timestamp"]),
                "patient_id": str(row["patient_id"])
            })

    if not new_rows:
        return None

    return new_rows[-1]


def append_resource_result(patient_id, mem_peak, gpu_peak, success):
    """
    将本次资源测试结果追加到 resource_usage_results.csv
    列名：
    病例ID    内存峰值/MB    GPU总显存峰值/MB    是否成功
    """
    row = {
        "病例ID": patient_id,
        "内存峰值/MB": round(mem_peak, 4),
        "GPU总显存峰值/MB": round(gpu_peak, 4),
        "是否成功": "是" if success else "否"
    }

    file_exists = os.path.exists(RESOURCE_CSV)

    with open(RESOURCE_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["病例ID", "内存峰值/MB", "GPU总显存峰值/MB", "是否成功"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"已更新资源测试结果到 CSV: {RESOURCE_CSV}")


def monitor():
    global running

    process = find_app_process()
    start = time.time()

    while running:
        now = time.time() - start

        # ===== app2.py 进程内存（MB）=====
        try:
            mem = process.memory_info().rss / 1024 / 1024
        except Exception:
            mem = 0.0

        # ===== GPU 总显存（MB）=====
        gpu_mem = get_total_gpu_memory()

        mem_list.append(mem)
        gpu_list.append(gpu_mem)
        time_list.append(now)

        time.sleep(0.5)


if __name__ == "__main__":
    print("====================================")
    print(f"开始监控 {APP_NAME} 资源，请在 {MONITOR_SECONDS} 秒内完成：")
    print("1. 上传CT")
    print("2. 点击检测")
    print("3. 点击识别")
    print("====================================")

    # 监控开始前，先记录 timing_results.csv 里已有的完整测试
    old_keys = get_existing_test_keys()

    t = threading.Thread(target=monitor)
    t.start()

    time.sleep(MONITOR_SECONDS)

    running = False
    t.join()

    print("监控结束，开始生成图像...")

    # ===== 内存图 =====
    plt.figure()
    plt.plot(time_list, mem_list)
    plt.xlabel("时间（秒）")
    plt.ylabel("内存占用（MB）")
    plt.title("系统运行过程中内存占用变化曲线")
    plt.grid()
    plt.tight_layout()
    plt.savefig("memory_usage_pid1.png", dpi=300)

    # ===== GPU图 =====
    plt.figure()
    plt.plot(time_list, gpu_list)
    plt.xlabel("时间（秒）")
    plt.ylabel("GPU总显存占用（MB）")
    plt.title("系统运行过程中GPU总显存占用变化曲线")
    plt.grid()
    plt.tight_layout()
    plt.savefig("gpu_usage_total1.png", dpi=300)

    mem_peak = max(mem_list) if mem_list else 0.0
    gpu_peak = max(gpu_list) if gpu_list else 0.0

    # 根据 timing_results.csv 判断本次是否成功，以及对应病例ID
    new_test = get_newest_new_test(old_keys)

    if new_test is not None:
        patient_id = new_test["patient_id"]
        success = True
        print(f"检测到本次完整测试成功，病例ID: {patient_id}")
    else:
        patient_id = ""
        success = False
        print("未检测到新的完整测试记录，本次记为失败。")

    # 写入资源测试 CSV
    append_resource_result(patient_id, mem_peak, gpu_peak, success)

    print("====================================")
    print("图已生成：")
    print("memory_usage_pid.png（app2.py进程内存）")
    print("gpu_usage_total.png（GPU总显存）")
    print("====================================")
    print(f"内存峰值：{mem_peak:.2f} MB")
    print(f"GPU总显存峰值：{gpu_peak:.2f} MB")
