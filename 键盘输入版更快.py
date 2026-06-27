import os
import time
import sys
import threading
import itertools
import tkinter as tk
from tkinter import messagebox, scrolledtext
import keyboard

class AutoCrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("纯数字字典生成与破译机 (纯键盘输入版)")
        self.root.geometry("580x820")
        self.root.attributes("-topmost", True)
        
        self.passwords = []
        self.total_passwords = 0
        self.current_index = 0  # 全局进度指针
        
        self.is_paused = True
        self.is_running = False
        
        self.setup_ui()
        self.setup_hotkeys()
        
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

        # --- 高级设置区 ---
        settings_frame = tk.LabelFrame(self.root, text="高级设置区 (可在运行时生效)", font=("微软雅黑", 10, "bold"), fg="#3b82f6")
        settings_frame.pack(pady=10, padx=20, fill="x")
        
        # Row 0: 按住时间 & 移动间隔
        tk.Label(settings_frame, text="按键按下保持时间 (秒):", font=("微软雅黑", 9)).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.entry_click_duration = tk.Entry(settings_frame, width=8, font=("微软雅黑", 10))
        self.entry_click_duration.insert(0, "0.08")
        self.entry_click_duration.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        tk.Label(settings_frame, text="按键之间间隔 (秒):", font=("微软雅黑", 9)).grid(row=0, column=2, padx=10, pady=5, sticky="e")
        self.entry_click_delay = tk.Entry(settings_frame, width=8, font=("微软雅黑", 10))
        self.entry_click_delay.insert(0, "0.1")  
        self.entry_click_delay.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # Row 1: 冷却时间 & 跳转进度
        tk.Label(settings_frame, text="等待冷却时间 (秒):", font=("微软雅黑", 9)).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_cooldown = tk.Entry(settings_frame, width=8, font=("微软雅黑", 10))
        self.entry_cooldown.insert(0, "0.8")
        self.entry_cooldown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # 跳转功能组件
        jump_frame = tk.Frame(settings_frame)
        jump_frame.grid(row=1, column=2, columnspan=2, sticky="w", padx=10)
        tk.Label(jump_frame, text="指定进度:", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.entry_jump = tk.Entry(jump_frame, width=5, font=("微软雅黑", 10))
        self.entry_jump.insert(0, "1")
        self.entry_jump.pack(side=tk.LEFT, padx=5)
        self.btn_jump = tk.Button(jump_frame, text="跳转", bg="#8b5cf6", fg="white", font=("微软雅黑", 8), command=self.jump_to_index)
        self.btn_jump.pack(side=tk.LEFT)

        # Row 2: 确认键选项
        self.confirm_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="每组密码输入后自动按 Enter 键确认", variable=self.confirm_var, font=("微软雅黑", 9)).grid(row=2, column=0, columnspan=4, pady=10)

        # --- 操作按钮区 ---
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        
        self.btn_generate = tk.Button(btn_frame, text="1. 生成字典并就绪", bg="#3b82f6", fg="white", font=("微软雅黑", 10, "bold"), command=self.prepare_attack)
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
        # 防溢出与清屏逻辑
        lines = int(self.log_area.index('end-1c').split('.')[0])
        if lines > 300:
            self.log_area.delete('1.0', '100.0')
            
        self.log_area.delete("end-2l", "end-1l")
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)

    def setup_hotkeys(self):
        keyboard.add_hotkey('F8', self.start_resume)
        keyboard.add_hotkey('F9', self.pause)

    def jump_to_index(self):
        if not self.passwords:
            messagebox.showinfo("提示", "请先点击【1. 生成字典并就绪】！")
            return
        try:
            idx = int(self.entry_jump.get())
            if 1 <= idx <= self.total_passwords:
                self.current_index = idx - 1  
                self.log(f"\n[+] 进度已成功跳转！下次将从第 {idx} 个组合开始输入。")
                pwd = self.passwords[self.current_index]
                self.update_progress(self.current_index + 1, self.total_passwords, pwd)
            else:
                messagebox.showwarning("范围错误", f"请输入 1 到 {self.total_passwords} 之间的数字！")
        except ValueError:
            messagebox.showwarning("格式错误", "请输入有效的数字！")

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
            
        parts.sort()
        
        self.log("\n[系统] 正在生成全排列组合(绝对顺序)...")
        permutations = list(itertools.permutations(parts))
        
        self.passwords = list(dict.fromkeys(["".join(p) for p in permutations]))
        self.total_passwords = len(self.passwords)
        self.current_index = 0  
        
        self.log(f"[系统] 生成完毕！共 {self.total_passwords} 种独特组合。")
        self.log("[+] 字典已就绪！请将焦点放置在目标输入框，然后点击【开始破译】或按 F8。")
        
        self.btn_generate.config(state=tk.NORMAL)
        self.btn_start.config(state=tk.NORMAL)

    def start_resume(self):
        if not self.passwords: return
        
        if self.current_index >= self.total_passwords:
            self.log("\n[提示] 已经破译完成，请重新生成字典或跳回前面的进度。")
            return
            
        if self.is_paused:
            self.is_paused = False
            self.btn_start.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL)
            self.log(f"\n[▶] 全速运行中... (从第 {self.current_index + 1} 个开始)")
            if not self.is_running:
                self.is_running = True
                threading.Thread(target=self.brute_force_thread, daemon=True).start()

    def pause(self):
        if not self.is_paused and self.is_running:
            self.is_paused = True
            self.btn_start.config(state=tk.NORMAL)
            self.btn_pause.config(state=tk.DISABLED)
            self.log("\n[⏸] 已暂停 (按 F8 继续)")

    def perform_keypress(self, key, duration):
        """模拟单个按键按下与释放"""
        keyboard.press(key)
        time.sleep(duration)
        keyboard.release(key)

    def brute_force_thread(self):
        self.log("\n[🚀] 开始自动化输入...\n")
        
        while self.current_index < self.total_passwords:
            if not self.is_running: break
            
            while self.is_paused:
                if not self.is_running: break
                time.sleep(0.1)
                
            if not self.is_running: break
            
            pwd = self.passwords[self.current_index]
            self.root.after(0, self.update_progress, self.current_index + 1, self.total_passwords, pwd)
            
            try:
                click_duration = float(self.entry_click_duration.get())
                click_delay = float(self.entry_click_delay.get())
                cooldown_delay = float(self.entry_cooldown.get())
            except ValueError:
                click_duration, click_delay, cooldown_delay = 0.08, 0.1, 0.8
            
            # 键盘输入字符
            for char in pwd:
                if self.is_paused: break
                self.perform_keypress(char, click_duration)
                time.sleep(click_delay)
                
            if self.is_paused: continue
                
            # 输入确认键 (Enter)
            if self.confirm_var.get() and not self.is_paused:
                self.perform_keypress('enter', click_duration)
                time.sleep(click_delay)
                
            # 冷却判定
            target_time = time.time() + cooldown_delay
            while time.time() < target_time and not self.is_paused:
                time.sleep(0.05)

            if self.is_paused: continue
            
            self.current_index += 1

        if not self.is_paused and self.current_index >= self.total_passwords:
            self.log("\n\n[🎉] 当前字典所有组合输入完毕！")
            self.is_running = False
            self.is_paused = True
            self.root.after(0, lambda: self.btn_start.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.btn_pause.config(state=tk.DISABLED))

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoCrackerApp(root)
    root.mainloop()