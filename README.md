# Floating Link Dock（桌面悬浮网址盒）

桌面上的悬浮启动工具。蓝色四宫格是工作场景版，可以把一项工作所需的网址、文件、文件夹和应用放进同一个场景，点一下就能一起打开。绿色笑脸是常用网址版，适合快速打开常用网站。两款应用各自保存配置，可以同时运行。

## 下载

| 应用 | 当前版本 | 下载 | 源码 |
| --- | --- | --- | --- |
| Windows 工作场景版 | v1.2.3 | [下载 EXE](https://github.com/ggc0214/floating-link-dock/releases/download/v1.2.3-windows-scenes/FloatingLinkDockScenes.exe) | [Windows 工作场景源码](https://github.com/ggc0214/floating-link-dock/tree/codex/windows-scenes-release) |
| Mac 工作场景版（M 系列，macOS 26.0 或更新版本） | v1.3.0 | [下载 ZIP](https://github.com/ggc0214/floating-link-dock/releases/download/v1.3.0-macos-arm64-scenes/FloatingLinkDockScenes-macos-arm64.zip) | [Mac 工作场景源码](https://github.com/ggc0214/floating-link-dock/tree/codex/macos-arm64-scenes) |
| Windows 常用网址版（绿色笑脸） | v1.2.0 | [下载 EXE](https://github.com/ggc0214/floating-link-dock/releases/download/v1.2.0-windows-links/FloatingLinkDock.exe) | [常用网址版源码](https://github.com/ggc0214/floating-link-dock/tree/v1.2.0-windows-links) |
| Mac 常用网址版（M 系列，macOS 26.0 或更新版本） | v1.2.0 试用版 | [下载 ZIP](https://github.com/ggc0214/floating-link-dock/releases/download/v1.2.0-macos-input-fix-2/FloatingLinkDock-macos-arm64-input-fix-2.zip) | [Mac 常用网址版源码](https://github.com/ggc0214/floating-link-dock/tree/v1.2.0-macos-input-fix-2) |

## 工作场景版怎么用

1. Windows 下载后双击 `FloatingLinkDockScenes.exe`。Mac 下载后解压，把 `FloatingLinkDockScenes.app` 拖进「应用程序」再打开。
2. 切到「工作场景」，点「＋ 场景」，再添加这个场景要用的网址、文件、文件夹和应用。Windows 的「应用」支持 `.exe`、`.lnk` 和 `.bat`，Mac 支持 `.app`。
3. 点「返回」后，左键单击场景方块即可一键启动。右键可以编辑、重命名或删除场景，按住方块可以拖动位置。

NAS 文件可通过 Windows 的共享路径添加。Mac 先在 Finder 连接共享目录，再选择已挂载的路径。Windows 升级时，先从系统托盘退出旧版。

[查看飞书使用说明](https://kocotree.feishu.cn/wiki/XNiMw4uJRieoA0kNPhycOXrrnXg) · [查看所有发布版本](https://github.com/ggc0214/floating-link-dock/releases)

## 从源码运行工作场景版

在 Windows 或 Mac 安装 `requirements.txt` 中的依赖后，运行 `python launcher_scenes.py`。Windows 使用 `FloatingLinkDockScenes.spec` 打包。Apple Silicon 的构建步骤见 [Mac 构建说明](README-MAC.md)。常用网址版的入口是 `launcher.py`。

## Windows 常用网址版

### 功能

- 始终置顶的无边框悬浮按钮，可拖到桌面任意位置。
- 单击展开或收起网址列表。
- 网站以独立方块显示，可在面板画布中自由拖动，位置自动保存。
- 支持添加网址，右键方块可编辑或删除。
- 使用 Windows 默认浏览器打开网站。
- 自动补全缺少的 `https://`，拒绝危险的非网页协议。
- 本地保存网址、窗口位置和偏好设置。
- 支持当前用户开机启动与单实例运行。
- 首次运行（包括升级到 1.1 后首次运行）自动展开网址面板。
- 系统托盘入口：单击显示网址，右键可显示、重置位置或退出。
- 收起后拖近屏幕边缘松手，会自动吸附（24 像素范围）。
- 右键勾选“贴边半隐藏”：贴边后鼠标离开约 0.7 秒，按钮藏起一半；移上去恢复。默认关闭。
- 启动和操作发生异常时弹窗提示，并写入本地 `errors.log`。
- 损坏的数据文件会先备份，再安全恢复。

### 直接使用 EXE

下载上表中的绿色笑脸版，双击 `FloatingLinkDock.exe` 即可运行。

基本操作：

- 单击悬浮按钮：展开或收起。
- 展开面板后，单击左上角箭头也可收起；拖动箭头仍可移动窗口。
- 拖动悬浮按钮：移动位置。
- 单击网址：用默认浏览器打开。
- 右键悬浮按钮或标题：设置保持置顶、开机启动，或退出。
- 展开后单击“添加”：新增网址。
- 单击网站方块打开网址；按住方块拖动可自由摆放，松手保存位置。
- 右键网站方块：打开、编辑或删除。网址较多时可滚轮向下浏览。

### 从源码运行

需要 Windows 10/11 与 Python 3.11 或更高版本。

```powershell
python -m pip install -r requirements.txt
.\run.bat
```

也可以直接运行：

```powershell
$env:PYTHONPATH="$PWD\src"
python -m floating_link_dock.main
```

### 数据位置

用户数据保存在：

```text
%LOCALAPPDATA%\FloatingLinkDock\
```

其中：

- `links.json`：网址列表。
- `settings.json`：窗口位置和设置。
- `backups\`：无法读取的数据文件备份。

删除 EXE 不会自动删除这些用户数据。如需完全清理，请先退出程序，再手动删除上述目录。

### 测试

安装开发依赖并运行：

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

### 构建独立 EXE

```powershell
.\build.bat
```

构建脚本会先运行完整测试，再重新生成应用图标，最后调用 PyInstaller。成功后文件位于：

```text
dist\FloatingLinkDock.exe
```

### 开机启动说明

开机启动仅写入当前 Windows 用户的启动项，名称为 `FloatingLinkDock`。关闭开关时只会移除该程序自己的启动项，不影响其他软件。

源码模式建议先在当前环境安装项目依赖；发布使用时建议使用 EXE，以确保启动路径稳定。
