# C盘清理分析工具 v1.0

---

## 简介

一个Windows桌面应用程序，用于扫描C盘空间占用情况，识别可清理/迁移的文件和目录，并生成详细的Excel分析报告。

**⚠️ 重要：本工具只做扫描分析，不会执行任何实际的删除或迁移操作！**

## excel导出示例

<img title="C盘可清理/迁移文件详细清单" src="docs\images\2026-06-23-09-58-25-image.png" alt="" data-align="inline">

![](docs\images\2026-06-23-09-59-01-image.png "C盘清理操作指南")

![](docs\images\2026-06-23-09-58-48-image.png "C盘清理分析报告")

---

## 快速使用

### 方法1：直接运行exe

1. 双击 `dist/CDriveScanner.exe`
2. 点击「🔍 扫描C盘」按钮开始扫描
3. 等待扫描完成（约1-3分钟）
4. 点击「📊 导出Excel报告」保存结果

### 方法2：Python源码运行

```bash
pip install openpyxl
python main.py
```

## 功能特性

- **4阶段深度扫描**：已知路径 → C盘根目录 → 用户目录 → Program Files
- **实时进度显示**：进度条、当前路径、已发现项目数、耗时
- **分类展示**：按类别分组，颜色标注操作类型
  - 红色：可删除
  - 绿色：可迁移
  - 橙色：删除或迁移均可
  - 灰色：系统文件，需谨慎
- **Excel报告**：3个工作表
  1. C盘清理总览（分类汇总）
  2. 可清理迁移详细清单（逐项说明）
  3. 操作指南（具体步骤）

## 系统要求

- Windows 10/11 (64位)
- 无需安装Python或其他依赖（exe版）

## 扫描范围

| 类别    | 扫描内容                                                  |
| ----- | ----------------------------------------------------- |
| 系统文件  | hiberfil.sys, pagefile.sys, WinSxS, Windows Installer |
| 微信/通讯 | xwechat_files, WeChat Files, 钉钉                       |
| 开发工具  | pip, npm, NuGet, uv, Gradle, Maven缓存                  |
| IDE   | PyCharm, VS Code, CodeBuddy缓存                         |
| 浏览器   | Chrome, Edge缓存                                        |
| 办公软件  | WPS Office, Xmind                                     |
| 临时文件  | Temp, CrashDumps, 通用缓存                                |
| 用户文件  | Downloads, Desktop, Documents                         |
| 大型软件  | Docker, MS SDKs, WSL, Store应用                         |

## 版本历史

- v1.0 (2026-06-23): 初始版本
