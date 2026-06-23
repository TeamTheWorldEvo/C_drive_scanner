# -*- coding: utf-8 -*-
"""Category rules and classification for C Drive Scanner.

This module maps file/directory paths to categories, action types,
and descriptive metadata. It supports two modes:
1. KNOWN_PATHS: exact path matching for Phase 1 fast scanning
2. CATEGORY_PATTERNS: regex patterns for Phase 2-4 deep scanning
"""

import re
import os
from typing import Optional
from data_model import ScanItem, ActionType


def _build_rules():
    """Build and return KNOWN_PATHS dict and CATEGORY_PATTERNS list."""
    known = {}
    patterns = []

    # =========================================================================
    # SYSTEM FILES
    # =========================================================================
    system_items = [
        {
            "name": "hiberfil.sys",
            "path": r"c:\hiberfil.sys",
            "category": "系统文件",
            "description": "系统休眠文件。保存内存数据以支持快速启动和休眠功能。",
            "action": "建议关闭休眠",
            "action_type": ActionType.SYSTEM,
            "notes": (
                "管理员CMD执行: powercfg /h off\n"
                "如果不需要休眠功能，关闭后可释放大量空间"
            ),
        },
        {
            "name": "pagefile.sys",
            "path": r"c:\pagefile.sys",
            "category": "系统文件",
            "description": "虚拟内存页面文件。当物理内存不足时使用磁盘作为补充。",
            "action": "调整大小/迁移",
            "action_type": ActionType.SYSTEM,
            "notes": (
                "在「高级系统设置→性能→虚拟内存」中调整大小或迁移到D盘"
            ),
        },
        {
            "name": "swapfile.sys",
            "path": r"c:\swapfile.sys",
            "category": "系统文件",
            "description": "交换文件。用于现代Windows应用的虚拟内存管理。",
            "action": "系统管理",
            "action_type": ActionType.SYSTEM,
            "notes": "由系统自动管理，一般很小，不建议手动操作",
        },
        {
            "name": "WinSxS",
            "path": r"c:\windows\winsxs",
            "category": "系统文件",
            "description": "Windows组件存储。保存系统文件的多个版本，用于更新回滚。",
            "action": "磁盘清理",
            "action_type": ActionType.SYSTEM,
            "notes": (
                "运行「磁盘清理」→「清理系统文件」→勾选「Windows更新清理」\n"
                "可安全释放部分空间，不要直接删除此目录"
            ),
        },
        {
            "name": "Windows Installer",
            "path": r"c:\windows\installer",
            "category": "系统文件",
            "description": "MSI安装包的缓存文件。用于已安装软件的修复、更新和卸载。",
            "action": "部分清理",
            "action_type": ActionType.SYSTEM,
            "notes": "不要直接删除！使用「磁盘清理」或专用工具清理",
        },
        {
            "name": "Windows Update缓存",
            "path": r"c:\windows\softwaredistribution",
            "category": "系统文件",
            "description": "Windows Update下载的更新文件缓存。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "在「磁盘清理」中清理，或停止Windows Update服务后删除",
        },
        {
            "name": "回收站",
            "path": r"c:\$recycle.bin",
            "category": "系统文件",
            "description": "Windows回收站中的已删除文件。",
            "action": "清空回收站",
            "action_type": ActionType.DELETE,
            "notes": "右键回收站→清空回收站",
        },
    ]

    # =========================================================================
    # WECHAT & COMMUNICATION
    # =========================================================================
    comm_items = [
        {
            "name": "微信(xwechat)文件",
            "path": r"c:\users\{user}\xwechat_files",
            "category": "微信/通讯软件",
            "description": "微信PC客户端(英文版)聊天文件，含聊天记录中的图片、视频、文件。",
            "action": "迁移到D盘",
            "action_type": ActionType.MIGRATE,
            "notes": (
                "⚠️ 通常是最大空间占用项！\n"
                "在微信PC设置中更改「文件管理」路径到D盘\n"
                "手动迁移现有文件夹后创建符号链接"
            ),
        },
        {
            "name": "WeChat Files(中文版)",
            "path": r"c:\users\{user}\documents\wechat files",
            "category": "微信/通讯软件",
            "description": "微信中文版聊天文件，含File、Video、MsgAttach等子目录。",
            "action": "迁移到D盘",
            "action_type": ActionType.MIGRATE,
            "notes": "在微信设置中修改存储路径，或将整个目录迁移到其他磁盘",
        },
        {
            "name": "钉钉数据",
            "path": r"c:\users\{user}\appdata\roaming\dingtalk",
            "category": "微信/通讯软件",
            "description": "钉钉办公软件用户数据：聊天记录、文件缓存、日志(通常很大)。",
            "action": "清理缓存+日志",
            "action_type": ActionType.BOTH,
            "notes": "优先清理日志目录(log)；可在钉钉设置中清理缓存",
        },
        {
            "name": "钉钉(旧版本)",
            "path": r"c:\users\{user}\appdata\local\dingtalk_133",
            "category": "微信/通讯软件",
            "description": "钉钉旧版本残留数据。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "确认当前钉钉版本后删除旧版本数据",
        },
        {
            "name": "钉钉(旧版本)",
            "path": r"c:\users\{user}\appdata\local\dingtalk_108",
            "category": "微信/通讯软件",
            "description": "钉钉旧版本残留数据。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "确认当前钉钉版本后删除旧版本数据",
        },
    ]

    # =========================================================================
    # TENCENT APPS
    # =========================================================================
    tencent_items = [
        {
            "name": "腾讯软件数据",
            "path": r"c:\users\{user}\appdata\roaming\tencent",
            "category": "腾讯系列软件",
            "description": "腾讯系列软件数据：xwechat、WeChat、WeMeet、Sogou输入法等。",
            "action": "部分清理+迁移",
            "action_type": ActionType.BOTH,
            "notes": (
                "xwechat/WeChat可参照微信迁移方案\n"
                "WeMeet会议缓存可清理\n"
                "Sogou输入法用户词库可保留"
            ),
        },
    ]

    # =========================================================================
    # DEVELOPER CACHES
    # =========================================================================
    dev_items = [
        {
            "name": "pip缓存",
            "path": r"c:\users\{user}\appdata\local\pip",
            "category": "开发工具缓存",
            "description": "Python pip包管理器的下载缓存，存储已下载的.whl和.tar.gz文件。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "执行: pip cache purge 或直接删除目录",
        },
        {
            "name": "npm缓存",
            "path": r"c:\users\{user}\appdata\local\npm-cache",
            "category": "开发工具缓存",
            "description": "Node.js npm包管理器的下载缓存。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "执行: npm cache clean --force 或直接删除目录",
        },
        {
            "name": "NuGet缓存",
            "path": r"c:\users\{user}\.nuget",
            "category": "开发工具缓存",
            "description": ".NET NuGet包管理器的缓存。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "执行: dotnet nuget locals all --clear",
        },
        {
            "name": "npm全局包",
            "path": r"c:\users\{user}\appdata\roaming\npm",
            "category": "开发工具缓存",
            "description": "通过npm install -g全局安装的Node.js包。",
            "action": "检查后清理",
            "action_type": ActionType.DELETE,
            "notes": "npm ls -g --depth=0 查看已安装包，清理不需要的",
        },
        {
            "name": "uv缓存",
            "path": r"c:\users\{user}\appdata\local\uv",
            "category": "开发工具缓存",
            "description": "Python包管理器uv的下载和构建缓存。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "执行: uv cache clean 或直接删除目录",
        },
        {
            "name": "Yarn缓存",
            "path": r"c:\users\{user}\appdata\local\yarn",
            "category": "开发工具缓存",
            "description": "Yarn包管理器的缓存。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "执行: yarn cache clean",
        },
        {
            "name": "Gradle缓存",
            "path": r"c:\users\{user}\.gradle",
            "category": "开发工具缓存",
            "description": "Gradle构建工具的下载缓存。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "删除caches子目录，下次构建会自动重新下载依赖",
        },
        {
            "name": "Maven缓存",
            "path": r"c:\users\{user}\.m2",
            "category": "开发工具缓存",
            "description": "Maven构建工具的本仓库。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "删除repository子目录，下次构建会自动重新下载",
        },
    ]

    # =========================================================================
    # IDE AND EDITOR DATA
    # =========================================================================
    ide_items = [
        {
            "name": "PyCharm缓存",
            "path": r"c:\users\{user}\appdata\local\jetbrains",
            "category": "IDE缓存",
            "description": "JetBrains IDE(PyCharm等)的缓存：索引、代码存根、日志等。",
            "action": "清理缓存",
            "action_type": ActionType.DELETE,
            "notes": (
                "通过IDE: File→Invalidate Caches 清理\n"
                "或删除caches、log子目录\n"
                "index重建需要时间但会大幅缩小"
            ),
        },
        {
            "name": "VS Code数据",
            "path": r"c:\users\{user}\appdata\roaming\code",
            "category": "IDE缓存",
            "description": "Visual Studio Code的用户数据：扩展、设置、缓存等。",
            "action": "可部分清理",
            "action_type": ActionType.BOTH,
            "notes": "清理Cache和CachedData子目录；检查并卸载不需要的扩展",
        },
        {
            "name": "VS Code C++扩展",
            "path": r"c:\users\{user}\appdata\local\microsoft\vscode-cpptools",
            "category": "IDE数据",
            "description": "VS Code C/C++扩展的IntelliSense缓存和数据。",
            "action": "清理ipch缓存",
            "action_type": ActionType.BOTH,
            "notes": (
                "删除ipch目录下的IntelliSense缓存\n"
                "可在VS Code设置中更改ipch存储位置"
            ),
        },
        {
            "name": "CodeBuddy",
            "path": r"c:\users\{user}\appdata\roaming\codebuddy cn",
            "category": "IDE缓存",
            "description": "CodeBuddy CN的扩展和数据缓存。",
            "action": "可清理",
            "action_type": ActionType.DELETE,
            "notes": "清理缓存子目录",
        },
    ]

    # =========================================================================
    # BROWSER CACHES
    # =========================================================================
    browser_items = [
        {
            "name": "Chrome浏览器数据",
            "path": r"c:\users\{user}\appdata\local\google\chrome",
            "category": "浏览器缓存",
            "description": "Chrome浏览器用户数据：缓存、历史、扩展等。",
            "action": "清理浏览器缓存",
            "action_type": ActionType.DELETE,
            "notes": (
                "Chrome→设置→清除浏览数据→缓存的图片和文件\n"
                "不建议删除整个User Data目录"
            ),
        },
        {
            "name": "Edge浏览器数据",
            "path": r"c:\users\{user}\appdata\local\microsoft\edge",
            "category": "浏览器缓存",
            "description": "Microsoft Edge浏览器的用户数据。",
            "action": "清理浏览器缓存",
            "action_type": ActionType.DELETE,
            "notes": "Edge→设置→隐私→清除浏览数据",
        },
    ]

    # =========================================================================
    # OFFICE & PRODUCTIVITY
    # =========================================================================
    office_items = [
        {
            "name": "WPS Office数据",
            "path": r"c:\users\{user}\appdata\roaming\kingsoft",
            "category": "办公软件",
            "description": "WPS办公软件用户数据：备份文件、模板缓存等。",
            "action": "可清理",
            "action_type": ActionType.BOTH,
            "notes": "清理wps下的备份文件和缓存；在WPS设置中更改备份路径",
        },
        {
            "name": "Xmind数据",
            "path": r"c:\users\{user}\appdata\roaming\xmind",
            "category": "办公软件",
            "description": "Xmind思维导图的用户数据和缓存。",
            "action": "可迁移",
            "action_type": ActionType.MIGRATE,
            "notes": "迁移到D盘，在Xmind设置中更改工作目录",
        },
    ]

    # =========================================================================
    # TEMP & CRASH FILES
    # =========================================================================
    temp_items = [
        {
            "name": "用户临时文件",
            "path": r"c:\users\{user}\appdata\local\temp",
            "category": "临时文件",
            "description": "各类应用程序运行时产生的临时文件，大多数可安全删除。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "使用「磁盘清理」或手动删除；建议保留最近7天的文件",
        },
        {
            "name": "崩溃转储文件",
            "path": r"c:\users\{user}\appdata\local\crashdumps",
            "category": "临时文件",
            "description": "程序崩溃时自动生成的.dmp调试文件。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "直接删除，不影响正常使用",
        },
        {
            "name": "通用缓存",
            "path": r"c:\users\{user}\appdata\local\cache",
            "category": "临时文件",
            "description": "各类应用的通用缓存目录。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "可以安全删除",
        },
        {
            "name": "Java堆转储",
            "pattern": r"c:\\users\\.*\\java_error_in_.*\.hprof",
            "category": "临时文件",
            "description": "JVM崩溃时生成的堆转储文件，用于调试。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "直接删除即可，不影响正常使用",
            "is_file": True,
        },
    ]

    # =========================================================================
    # USER FOLDERS
    # =========================================================================
    user_items = [
        {
            "name": "Downloads",
            "path": r"c:\users\{user}\downloads",
            "category": "用户文件",
            "description": "浏览器和其他应用下载的文件目录。",
            "action": "清理+迁移",
            "action_type": ActionType.BOTH,
            "notes": "删除不需要的安装包和旧文件；将有用文件迁移到分类目录",
        },
        {
            "name": "Desktop",
            "path": r"c:\users\{user}\desktop",
            "category": "用户文件",
            "description": "存放在桌面上的文件和快捷方式。",
            "action": "整理+迁移",
            "action_type": ActionType.BOTH,
            "notes": "删除不再需要的文件；大文件移入其他分区",
        },
        {
            "name": "Documents(除微信)",
            "path": r"c:\users\{user}\documents",
            "category": "用户文件",
            "description": "用户文档目录，可能包含WeChat Files等大型子目录。",
            "action": "部分迁移",
            "action_type": ActionType.MIGRATE,
            "notes": "将不常用的项目文件迁移到D盘；微信文件通过微信设置迁移",
        },
    ]

    # =========================================================================
    # LARGE SOFTWARE
    # =========================================================================
    software_items = [
        {
            "name": "Microsoft SDKs",
            "path": r"c:\program files (x86)\microsoft sdks",
            "category": "大型软件",
            "description": "Windows软件开发工具包，可能包含多个旧版本。",
            "action": "卸载旧版本",
            "action_type": ActionType.BOTH,
            "notes": "在「设置→应用」中卸载不需要的旧版SDK",
        },
        {
            "name": "Docker Desktop",
            "path": r"c:\program files\docker",
            "category": "大型软件",
            "description": "Docker容器运行时和应用。",
            "action": "可迁移",
            "action_type": ActionType.MIGRATE,
            "notes": "在Docker设置中更改镜像存储位置；docker system prune -a 清理",
        },
        {
            "name": "Windows Kits",
            "path": r"c:\program files (x86)\windows kits",
            "category": "大型软件",
            "description": "Windows调试和开发工具包。",
            "action": "卸载旧版本",
            "action_type": ActionType.BOTH,
            "notes": "在应用设置中卸载不需要的旧版本",
        },
        {
            "name": "Microsoft Store应用",
            "path": r"c:\users\{user}\appdata\local\packages",
            "category": "大型软件",
            "description": "通过Microsoft Store安装的应用和游戏数据。",
            "action": "清理不用的应用",
            "action_type": ActionType.BOTH,
            "notes": "在「设置→应用」中卸载不使用的Store应用；不要直接删除目录",
        },
        {
            "name": "WSL数据",
            "path": r"c:\users\{user}\appdata\local\wsl",
            "category": "大型软件",
            "description": "Windows Subsystem for Linux的数据。",
            "action": "可迁移",
            "action_type": ActionType.MIGRATE,
            "notes": "使用 wsl --export 导出到D盘，然后 wsl --import 重新导入",
        },
        {
            "name": "Playwright浏览器",
            "path": r"c:\users\{user}\appdata\local\ms-playwright",
            "category": "开发工具",
            "description": "Playwright自动化测试框架下载的浏览器二进制文件。",
            "action": "可删除/重装",
            "action_type": ActionType.DELETE,
            "notes": (
                "如不使用Playwright可直接删除\n"
                "如需使用，设置PLAYWRIGHT_BROWSERS_PATH环境变量到D盘"
            ),
        },
    ]

    # =========================================================================
    # OTHER APPS
    # =========================================================================
    other_items = [
        {
            "name": "网易相关数据",
            "path": r"c:\users\{user}\appdata\local\netease",
            "category": "其他应用",
            "description": "网易软件(网易云音乐等)的缓存和数据文件。",
            "action": "可清理",
            "action_type": ActionType.DELETE,
            "notes": "删除缓存子目录，或通过对应软件设置清理",
        },
        {
            "name": "豆包AI",
            "path": r"c:\users\{user}\appdata\local\doubao",
            "category": "其他应用",
            "description": "字节跳动豆包AI助手的应用数据和缓存。",
            "action": "可清理",
            "action_type": ActionType.DELETE,
            "notes": "通过豆包设置清理缓存",
        },
        {
            "name": "微信开发者工具",
            "path": r"c:\users\{user}\appdata\local\微信开发者工具",
            "category": "开发工具",
            "description": "微信小程序开发IDE的缓存和数据文件。",
            "action": "可清理",
            "action_type": ActionType.DELETE,
            "notes": "清理工具缓存目录，或在设置中更改缓存位置",
        },
        {
            "name": "MathWorks/MATLAB",
            "path": r"c:\users\{user}\appdata\roaming\mathworks",
            "category": "大型软件",
            "description": "MathWorks MATLAB的用户数据和缓存。",
            "action": "可迁移",
            "action_type": ActionType.MIGRATE,
            "notes": "在MATLAB设置中更改用户数据目录位置",
        },
        {
            "name": "VMware",
            "path": r"c:\program files (x86)\vmware",
            "category": "大型软件",
            "description": "VMware Workstation的安装文件。",
            "action": "检查虚拟机位置",
            "action_type": ActionType.INFO,
            "notes": "检查虚拟机镜像(.vmdk)是否在C盘，是则迁移到D盘",
        },
        {
            "name": "VisualStudio安装残留",
            "path": r"c:\users\{user}\appdata\local\temp\aobhg2qe",
            "category": "临时文件",
            "description": "Visual Studio安装器的临时解压文件。",
            "action": "可删除",
            "action_type": ActionType.DELETE,
            "notes": "VS安装/更新完成后可安全删除",
        },
        {
            "name": "obsidian数据",
            "path": r"c:\users\{user}\appdata\roaming\obsidian",
            "category": "办公软件",
            "description": "Obsidian笔记软件的用户配置和缓存。",
            "action": "可迁移",
            "action_type": ActionType.MIGRATE,
            "notes": "在Obsidian设置中更改仓库(vault)位置",
        },
        {
            "name": "anythingllm",
            "path": r"c:\users\{user}\appdata\roaming\anythingllm-desktop",
            "category": "其他应用",
            "description": "AnythingLLM桌面应用的数据。",
            "action": "可清理",
            "action_type": ActionType.BOTH,
            "notes": "清理缓存数据",
        },
    ]

    # =========================================================================
    # PROGRAM FILES PATTERNS (for deep scanning)
    # =========================================================================
    pf_items = [
        {
            "name": "Microsoft Visual Studio",
            "path": r"c:\program files (x86)\microsoft visual studio",
            "category": "大型软件",
            "description": "Visual Studio IDE安装目录。",
            "action": "清理旧组件",
            "action_type": ActionType.BOTH,
            "notes": "在Visual Studio Installer中卸载不需要的组件和工作负载",
        },
        {
            "name": "dotnet SDK",
            "path": r"c:\program files (x86)\dotnet",
            "category": "开发工具",
            "description": ".NET SDK和运行时。",
            "action": "清理旧版本",
            "action_type": ActionType.BOTH,
            "notes": "在应用设置中卸载不再需要的旧版.NET SDK",
        },
        {
            "name": "Google Chrome",
            "path": r"c:\program files (x86)\google",
            "category": "浏览器缓存",
            "description": "Google Chrome浏览器安装文件。",
            "action": "无需操作",
            "action_type": ActionType.INFO,
            "notes": "浏览器本身占空间不大，缓存数据在AppData中",
        },
    ]

    # =========================================================================
    # Assemble all items
    # =========================================================================
    all_items = (
        system_items + comm_items + tencent_items + dev_items + ide_items +
        browser_items + office_items + temp_items + user_items +
        software_items + other_items + pf_items
    )

    for item in all_items:
        if "path" in item:
            known[item["path"]] = item
        elif "pattern" in item:
            patterns.append((
                re.compile(item["pattern"], re.IGNORECASE),
                item["category"],
                item["action"],
                item["action_type"],
                item["description"],
                item["notes"],
                item.get("is_file", False),
            ))

    # Additional regex patterns for deep scanning
    deep_patterns = [
        # Dev caches
        (re.compile(r"\\pip$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "pip缓存目录", "执行 pip cache purge"),
        (re.compile(r"\\npm-cache$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "npm缓存目录", "执行 npm cache clean --force"),
        (re.compile(r"\\\.nuget$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "NuGet缓存目录", "执行 dotnet nuget locals all --clear"),
        (re.compile(r"\\\.gradle$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "Gradle缓存", "删除caches子目录"),
        (re.compile(r"\\\.m2$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "Maven本地仓库", "删除repository子目录"),
        (re.compile(r"\\uv$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "uv缓存目录", "执行 uv cache clean"),
        (re.compile(r"\\\.cargo$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "Cargo(Rust)缓存", "删除registry子目录"),
        (re.compile(r"\\\.rustup$", re.IGNORECASE), "开发工具缓存", "可删除",
         ActionType.DELETE, "Rust工具链", "通过rustup管理"),

        # Temp & crash
        (re.compile(r"\\temp$", re.IGNORECASE), "临时文件", "可删除",
         ActionType.DELETE, "临时文件目录", "可以安全删除大部分内容"),
        (re.compile(r"\\crashdumps$", re.IGNORECASE), "临时文件", "可删除",
         ActionType.DELETE, "崩溃转储目录", "删除.dmp文件"),
        (re.compile(r"\\cache$", re.IGNORECASE), "临时文件", "可删除",
         ActionType.DELETE, "缓存目录", "可以安全清理"),
        (re.compile(r"\.dmp$", re.IGNORECASE), "临时文件", "可删除",
         ActionType.DELETE, "崩溃转储文件", "直接删除"),
        (re.compile(r"\.hprof$", re.IGNORECASE), "临时文件", "可删除",
         ActionType.DELETE, "Java堆转储文件", "直接删除"),

        # IDE caches
        (re.compile(r"\\jetbrains", re.IGNORECASE), "IDE缓存", "可清理",
         ActionType.DELETE, "JetBrains IDE缓存", "通过IDE清理或手动删除缓存"),
        (re.compile(r"\\vscode-cpptools", re.IGNORECASE), "IDE数据", "清理ipch",
         ActionType.BOTH, "VS Code C++工具数据", "清理IntelliSense缓存"),

        # Browser
        (re.compile(r"\\google\\chrome", re.IGNORECASE), "浏览器缓存", "可清理",
         ActionType.DELETE, "Chrome浏览器数据", "通过浏览器设置清理"),

        # Communication
        (re.compile(r"\\dingtalk", re.IGNORECASE), "微信/通讯软件", "清理缓存",
         ActionType.BOTH, "钉钉数据", "清理日志和缓存"),
        (re.compile(r"\\tencent", re.IGNORECASE), "腾讯系列软件", "部分清理",
         ActionType.BOTH, "腾讯软件数据", "清理缓存文件"),

        # Office
        (re.compile(r"\\kingsoft", re.IGNORECASE), "办公软件", "可清理",
         ActionType.BOTH, "WPS Office数据", "清理备份和模板缓存"),

        # Large packages
        (re.compile(r"\\packages$", re.IGNORECASE), "大型软件", "检查清理",
         ActionType.BOTH, "Microsoft Store应用数据", "卸载不用的Store应用"),
    ]

    patterns.extend(deep_patterns)
    return known, patterns


# Build rules at module load time
KNOWN_PATHS, CATEGORY_PATTERNS = _build_rules()


def classify_path(
    path: str,
    size_bytes: int,
    username: str = "",
    num_files: int = 0,
    num_subdirs: int = 0,
) -> Optional[ScanItem]:
    """Classify a file/directory path into a ScanItem with category metadata.

    Args:
        path: Absolute path to the item
        size_bytes: Size in bytes
        username: Windows username for path substitution
        num_files: Number of files (for directories)
        num_subdirs: Number of subdirectories (for directories)

    Returns:
        ScanItem with full metadata, or None if not classifiable
    """
    normalized = os.path.normpath(path).lower()

    # 1. Try exact path matching
    # First with username substitution
    if username:
        for template, rule in KNOWN_PATHS.items():
            expanded = template.replace(r"{user}", username)
            if os.path.normpath(expanded).lower() == normalized:
                item = ScanItem(
                    path=path,
                    name=rule.get("name", os.path.basename(path)),
                    size_bytes=size_bytes,
                    category=rule["category"],
                    description=rule["description"],
                    suggested_action=rule["action"],
                    action_type=rule["action_type"],
                    notes=rule.get("notes", ""),
                    num_files=num_files,
                    num_subdirs=num_subdirs,
                )
                return item

    # Try without username substitution (for exact paths)
    for template, rule in KNOWN_PATHS.items():
        norm_template = os.path.normpath(template).lower()
        if norm_template == normalized:
            item = ScanItem(
                path=path,
                name=rule.get("name", os.path.basename(path)),
                size_bytes=size_bytes,
                category=rule["category"],
                description=rule["description"],
                suggested_action=rule["action"],
                action_type=rule["action_type"],
                notes=rule.get("notes", ""),
                num_files=num_files,
                num_subdirs=num_subdirs,
            )
            return item

    # 2. Try pattern matching
    for entry in CATEGORY_PATTERNS:
        # Handle both 6 and 7 element tuples
        if len(entry) == 7:
            pattern, category, action, action_type, desc, notes, is_file = entry
        else:
            pattern, category, action, action_type, desc, notes = entry
            is_file = False
        if pattern.search(normalized):
            item = ScanItem(
                path=path,
                name=os.path.basename(path),
                size_bytes=size_bytes,
                category=category,
                description=desc,
                suggested_action=action,
                action_type=action_type,
                notes=notes,
                num_files=num_files,
                num_subdirs=num_subdirs,
            )
            return item

    return None  # Not classifiable
