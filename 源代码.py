import os
import json
import time
import sys
import threading
import itertools
import tkinter as tk
from tkinter import messagebox, scrolledtext
import pyautogui
import keyboard

# --- 核心安全与延迟设置 ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # 关闭原生延迟

CONFIG_FILE = "mouse_config.json"

class AutoCrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("纯数字字典生成与破译机 (防漏键增强版)")
        self.root.geometry("580x780")  # 增加一点高度
        self.root.attributes("-topmost", True)
        
        self.config = self.load_config()
        self.passwords = []
        self.total_passwords = 0
        self.is_paused = True
        self.is_running = False
        self.calibration_mode = False
        
        self.setup_ui()
        self.setup_hotkeys()
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def delete_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                os.remove(CONFIG_FILE)
                self.config = {}
                self.log("\n[+] 配置文件已成功删除！下次点击【1.生成字典】将重新校准坐标。")
                messagebox.showinfo("成功", "坐标配置文件已删除，请重新生成字典以触发校准。")
            except Exception as e:
                self.log(f"[-] 删除失败: {e}")
        else:
            self.log("\n[-] 配置文件不存在，无需删除。")
            messagebox.showinfo("提示", "配置文件不存在，无需删除。")

    def setup_ui(self):
        tk.Label(self.root, text="【第一步】输入 6 个数字密码碎片", font=("微软雅黑", 12, "bold")).pack(pady=5)
        
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=5)
        
        self.entries = {}
        labels = ["0", "2", "4", "5", "6", "7"]
        
        for i, lbl in enumerate(labels):
            row = i // 2
            col = (i % 2) * 2
            tk.Label(input_frame, text=f"提示 {lbl}:", font=("微软雅黑", 10)).grid(row=row, column=col, padx=10, pady=5, sticky="e")
            entry = tk.Entry(input_frame, width=15, font=("微软雅黑", 10))
            entry.grid(row=row, column=col+1, padx=5, pady=5)
            self.entries[lbl] = entry

        # --- 高级设置区 (调整为3行) ---
        settings_frame = tk.LabelFrame(self.root, text="高级设置区 (可在运行时生效)", font=("微软雅黑", 10, "bold"), fg="#3b82f6")
        settings_frame.pack(pady=10, padx=20, fill="x")
        
        # 1. 鼠标按下保持时间（解决游戏识别困难的核心）
        tk.Label(settings_frame, text="鼠标按住保持时间 (秒):", font=("微软雅黑", 9)).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.entry_click_duration = tk.Entry(settings_frame, width=8, font=("微软雅黑", 10))
        self.entry_click_duration.insert(0, "0.08")  # 默认按住 0.08 秒
        self.entry_click_duration.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # 2. 按键之间间隔
        tk.Label(settings_frame, text="按键之间移动间隔 (秒):", font=("微软雅黑", 9)).grid(row=0, column=2, padx=10, pady=5, sticky="e")
        self.entry_click_delay = tk.Entry(settings_frame, width=8, font=("微软雅黑", 10))
        self.entry_click_delay.insert(0, "0.1")  
        self.entry_click_delay.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # 3. 红盘冷却
        tk.Label(settings_frame, text="红盘等待冷却时间 (秒):", font=("微软雅黑", 9)).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_cooldown = tk.Entry(settings_frame, width=8, font=("微软雅黑", 10))
        self.entry_cooldown.insert(0, "0.8")
        self.entry_cooldown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # 4. 删除按钮
        self.btn_del_config = tk.Button(settings_frame, text="🗑️ 删除旧坐标配置", bg="#ef4444", fg="white", font=("微软雅黑", 9), command=self.delete_config)
        self.btn_del_config.grid(row=1, column=2, columnspan=2, pady=10)

        # --- 操作按钮区 ---
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        
        self.btn_generate = tk.Button(btn_frame, text="1. 生成字典并校验", bg="#3b82f6", fg="white", font=("微软雅黑", 10, "bold"), command=self.prepare_attack)
        self.btn_generate.grid(row=0, column=0, padx=10)
        
        self.btn_start = tk.Button(btn_frame, text="2. 开始破译 (F8)", bg="#22c55e", fg="white", font=("微软雅黑", 10, "bold"), state=tk.DISABLED, command=self.start_resume)
        self.btn_start.grid(row=0, column=1, padx=10)
        
        self.btn_pause = tk.Button(btn_frame, text="暂停 (F9)", bg="#f59e0b", fg="white", font=("微软雅黑", 10, "bold"), state=tk.DISABLED, command=self.pause)
        self.btn_pause.grid(row=0, column=2, padx=10)

        # --- 日志控制台 ---
        tk.Label(self.root, text="运行日志与进度：", font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=20)
        self.log_area = scrolledtext.ScrolledText(self.root, width=65, height=14, font=("Consolas", 9), bg="#1e1e1e", fg="#00ff00")
        self.log_area.pack(pady=5, padx=20)
        
        self.log("系统已启动。等待输入碎片...")

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self, current, total, pwd):
        progress = (current / total) * 100
        msg = f"[进度: {current}/{total} ({progress:.1f}%)] 正在输入: {pwd[:15]}..."
        self.log_area.delete("end-2l", "end-1l")
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)

    def setup_hotkeys(self):
        keyboard.add_hotkey('F8', self.start_resume)
        keyboard.add_hotkey('F9', self.pause)

    def prepare_attack(self):
        parts = []
        for lbl, entry in self.entries.items():
            val = entry.get().strip()
            if not val:
                messagebox.showwarning("警告", f"提示 {lbl} 的输入框不能为空！")
                return
            if not val.isdigit():
                messagebox.showwarning("警告", f"提示 {lbl} 包含非数字字符！")
                return
            parts.append(val)
            
        self.log("\n[系统] 正在生成全排列组合...")
        permutations = list(itertools.permutations(parts))
        self.passwords = list(set(["".join(p) for p in permutations]))
        self.total_passwords = len(self.passwords)
        
        self.log(f"[系统] 生成完毕！共 {self.total_passwords} 种独特组合。")
        
        required_keys = [str(i) for i in range(10)]
        missing_keys = [k for k in required_keys if k not in self.config]
        
        if missing_keys or "__CONFIRM__" not in self.config:
            self.btn_generate.config(state=tk.DISABLED)
            threading.Thread(target=self.calibration_thread, args=(missing_keys,), daemon=True).start()
        else:
            self.log("[+] 0-9 坐标已就绪！请点击【开始破译】或按 F8。")
            self.btn_start.config(state=tk.NORMAL)

    def calibration_thread(self, missing_keys):
        self.calibration_mode = True
        self.log("\n" + "="*40)
        self.log("【10键全局校准模式开启】")
        
        for key in missing_keys:
            self.log(f"👉 将鼠标移动到【 {key} 】位置，按 F10 记录...")
            keyboard.wait('f10')
            x, y = pyautogui.position()
            self.config[key] = {"x": x, "y": y}
            self.log(f"   [已记录] '{key}'")
            time.sleep(0.3)
            
        if "__CONFIRM__" not in self.config:
            ans = messagebox.askyesno("确认键", "是否需要点击密码盘上的【确认/提交】键？")
            if ans:
                self.log(f"\n👉 将鼠标移动到【确认/提交】位置，按 F10 记录...")
                keyboard.wait('f10')
                x, y = pyautogui.position()
                self.config["__CONFIRM__"] = {"x": x, "y": y}
                self.log(f"   [已记录] 确认键")
            else:
                self.config["__CONFIRM__"] = None

        self.save_config()
        self.log("="*40)
        self.log("[+] 校准完毕！请按 F8 开始。")
        
        self.calibration_mode = False
        self.root.after(0, lambda: self.btn_generate.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL))

    def start_resume(self):
        if self.calibration_mode or not self.passwords: return
        if self.is_paused:
            self.is_paused = False
            self.btn_start.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL)
            self.log("\n[▶] 全速运行中...")
            if not self.is_running:
                self.is_running = True
                threading.Thread(target=self.brute_force_thread, daemon=True).start()

    def pause(self):
        if not self.is_paused and self.is_running:
            self.is_paused = True
            self.btn_start.config(state=tk.NORMAL)
            self.btn_pause.config(state=tk.DISABLED)
            self.log("\n[⏸] 已暂停 (按 F8 继续)")

    def perform_click(self, x, y, duration):
        """核心修改：模拟真实的按下和抬起过程"""
        pyautogui.mouseDown(x, y)
        time.sleep(duration) # 按住一定时间让游戏识别
        pyautogui.mouseUp(x, y)

    def brute_force_thread(self):
        self.log("\n[🚀] 开始自动化输入...\n")
        
        for index, pwd in enumerate(self.passwords, start=1):
            while self.is_paused: time.sleep(0.1)
            self.root.after(0, self.update_progress, index, self.total_passwords, pwd)
            
            # 读取设置
            try:
                click_duration = float(self.entry_click_duration.get())
                click_delay = float(self.entry_click_delay.get())
                cooldown_delay = float(self.entry_cooldown.get())
            except ValueError:
                click_duration, click_delay, cooldown_delay = 0.08, 0.1, 0.8
            
            # 输入字符
            for char in pwd:
                if self.is_paused: break
                self.perform_click(self.config[char]["x"], self.config[char]["y"], click_duration)
                time.sleep(click_delay) # 抬手后的间隔
                
            # 输入确认键
            if self.config.get("__CONFIRM__") and not self.is_paused:
                self.perform_click(self.config["__CONFIRM__"]["x"], self.config["__CONFIRM__"]["y"], click_duration)
                time.sleep(click_delay)
                
            # 冷却判定
            target_time = time.time() + cooldown_delay
            while time.time() < target_time and not self.is_paused:
                time.sleep(0.05)

        if not self.is_paused:
            self.log("\n\n[🎉] 当前字典所有组合输入完毕！")
            self.is_running = False
            self.is_paused = True
            self.root.after(0, lambda: self.btn_start.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.btn_pause.config(state=tk.DISABLED))

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoCrackerApp(root)
    root.mainloop()