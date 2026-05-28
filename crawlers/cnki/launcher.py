#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知网爬虫 - 一键启动器 (Selenium版本)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import sys
import os
import threading
from datetime import datetime


class CNKISpiderLauncher:
    """知网爬虫启动器"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("知网(CNKI)学术文献爬虫 v2.0")
        self.root.geometry("750x600")
        self.root.resizable(False, False)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置UI界面"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="知网学术文献爬虫", 
            font=("Helvetica", 22, "bold")
        )
        title_label.pack(pady=(0, 5))
        
        # 副标题
        subtitle_label = ttk.Label(
            main_frame, 
            text="Selenium动态渲染版 | 自动处理JavaScript", 
            font=("Helvetica", 10),
            foreground="gray"
        )
        subtitle_label.pack(pady=(0, 15))
        
        # 搜索设置
        search_frame = ttk.LabelFrame(main_frame, text="🔍 搜索设置", padding="15")
        search_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 关键词输入
        ttk.Label(search_frame, text="搜索关键词:").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.keyword_entry = ttk.Entry(search_frame, width=45, font=("Helvetica", 12))
        self.keyword_entry.grid(row=0, column=1, padx=(10, 0), pady=8, sticky=tk.W+tk.E)
        
        # 文献类型
        ttk.Label(search_frame, text="文献类型:").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.type_var = tk.StringVar(value="全部")
        type_combo = ttk.Combobox(
            search_frame, 
            textvariable=self.type_var,
            values=["全部", "期刊", "学位论文", "会议", "报纸"],
            state="readonly",
            width=20
        )
        type_combo.grid(row=1, column=1, padx=(10, 0), pady=8, sticky=tk.W)
        
        # 页数
        ttk.Label(search_frame, text="搜索页数:").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.pages_var = tk.StringVar(value="3")
        pages_spin = ttk.Spinbox(
            search_frame, 
            from_=1, to=20,
            textvariable=self.pages_var,
            width=20
        )
        pages_spin.grid(row=2, column=1, padx=(10, 0), pady=8, sticky=tk.W)
        
        # 排序
        ttk.Label(search_frame, text="排序方式:").grid(row=3, column=0, sticky=tk.W, pady=8)
        self.sort_var = tk.StringVar(value="相关度")
        sort_combo = ttk.Combobox(
            search_frame, 
            textvariable=self.sort_var,
            values=["相关度", "发表时间", "被引次数", "下载次数"],
            state="readonly",
            width=20
        )
        sort_combo.grid(row=3, column=1, padx=(10, 0), pady=8, sticky=tk.W)
        
        search_frame.columnconfigure(1, weight=1)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="📋 运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            width=75, 
            height=10,
            font=("Consolas", 10),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        # 一键启动按钮
        self.start_btn = tk.Button(
            btn_frame,
            text="🚀 一键启动爬虫",
            font=("Helvetica", 15, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=35,
            pady=12,
            command=self.start_crawler
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 检查连接
        check_btn = tk.Button(
            btn_frame,
            text="🔍 检查连接",
            font=("Helvetica", 11),
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=10,
            command=self.check_connection
        )
        check_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 退出
        exit_btn = tk.Button(
            btn_frame,
            text="❌ 退出",
            font=("Helvetica", 11),
            bg="#f44336",
            fg="white",
            padx=20,
            pady=10,
            command=self.root.quit
        )
        exit_btn.pack(side=tk.LEFT)
        
        # 提示
        info_label = ttk.Label(
            main_frame, 
            text="⚠️ 将打开Chrome浏览器窗口，请勿关闭！按Ctrl+C可在终端停止", 
            font=("Helvetica", 9),
            foreground="#FF9800"
        )
        info_label.pack(pady=(10, 0))
        
        self.keyword_entry.bind('<Return>', lambda e: self.start_crawler())
    
    def _log(self, message: str):
        """输出日志"""
        def append():
            self.log_text.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, append)
        
    def start_crawler(self):
        """启动爬虫"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词！")
            return
        
        self.start_btn.config(state=tk.DISABLED, text="🔄 运行中(请等待)...")
        
        thread = threading.Thread(target=self._run_crawler, args=(keyword,))
        thread.daemon = True
        thread.start()
        
    def _run_crawler(self, keyword: str):
        """执行爬虫"""
        pages = self.pages_var.get()
        lit_type = self.get_type_code()
        
        self._log("=" * 55)
        self._log(f"🚀 开始搜索: {keyword}")
        self._log(f"   文献类型: {self.type_var.get()}")
        self._log(f"   搜索页数: {pages}")
        self._log("   模式: Selenium浏览器")
        self._log("⚠️ 请勿关闭弹出的Chrome浏览器窗口！")
        self._log("=" * 55)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(script_dir, "main.py")
        
        cmd = [sys.executable, main_script, "search", keyword, "-p", pages, "-f", "csv"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=script_dir
            )
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    self._log(line)
                
            process.wait()
            
            if process.returncode == 0:
                self._log("✅ 搜索完成！")
            else:
                self._log("⚠️ 搜索完成(可能需要手动检查)")
                
        except Exception as e:
            self._log(f"❌ 错误: {str(e)}")
            
        finally:
            def enable_btn():
                self.start_btn.config(state=tk.NORMAL, text="🚀 一键启动爬虫")
            self.root.after(0, enable_btn)
    
    def check_connection(self):
        """检查连接"""
        self._log("🔍 正在检查知网连接...")
        
        thread = threading.Thread(target=self._check_connection_thread)
        thread.daemon = True
        thread.start()
        
    def _check_connection_thread(self):
        """检查连接线程"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(script_dir, "main.py")
        
        try:
            result = subprocess.run(
                [sys.executable, main_script, "check"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=script_dir
            )
            
            for line in result.stdout.split('\n'):
                if line.strip():
                    self._log(line)
                    
        except subprocess.TimeoutExpired:
            self._log("❌ 连接超时")
        except Exception as e:
            self._log(f"❌ 检查失败: {str(e)}")
    
    def get_type_code(self) -> str:
        """获取文献类型代码"""
        type_map = {
            "全部": None,
            "期刊": "journal",
            "学位论文": "thesis", 
            "会议": "conference",
            "报纸": "newspaper"
        }
        return type_map.get(self.type_var.get())


def main():
    root = tk.Tk()
    app = CNKISpiderLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
