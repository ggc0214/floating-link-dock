# Floating Link Dock（桌面悬浮网址盒）

一个轻量的 Windows 桌面悬浮网址盒。收起时只占一个小按钮，单击后展开常用网站列表。

## 两款 Windows 应用

| 应用 | 启动文件 | 用途 |
|---|---|---|
| [常用网址版](https://github.com/ggc0214/floating-link-dock/releases/tag/v1.2.0-windows-links) | `FloatingLinkDock.exe` | 绿色笑脸，单击方块打开常用网站 |
| [工作场景版](https://github.com/ggc0214/floating-link-dock/releases/tag/v1.2.0-windows-scenes) | `FloatingLinkDockScenes.exe` | 蓝色四宫格，支持将网址、文件、文件夹和应用一起启动 |

两款应用可以同时运行，各自保存配置。工作场景版的操作步骤见[使用说明](docs/work-scenes/使用说明.md)。

本分支可从源码运行两款应用。安装依赖后，执行 `python launcher.py` 启动常用网址版，执行 `python launcher_scenes.py` 启动工作场景版。打包分别使用 `FloatingLinkDock.spec` 和 `FloatingLinkDockScenes.spec`。

## 功能

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

## 直接使用 EXE

从 GitHub Release 下载 `FloatingLinkDock.exe`，双击运行即可，不需要安装 Python。

基本操作：

- 单击悬浮按钮：展开或收起。
- 展开面板后，单击左上角箭头也可收起；拖动箭头仍可移动窗口。
- 拖动悬浮按钮：移动位置。
- 单击网址：用默认浏览器打开。
- 右键悬浮按钮或标题：设置保持置顶、开机启动，或退出。
- 展开后单击“添加”：新增网址。
- 单击网站方块打开网址；按住方块拖动可自由摆放，松手保存位置。
- 右键网站方块：打开、编辑或删除。网址较多时可滚轮向下浏览。

## 从源码运行

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

## 数据位置

用户数据保存在：

```text
%LOCALAPPDATA%\FloatingLinkDock\
```

其中：

- `links.json`：网址列表。
- `settings.json`：窗口位置和设置。
- `backups\`：无法读取的数据文件备份。

删除 EXE 不会自动删除这些用户数据。如需完全清理，请先退出程序，再手动删除上述目录。

## 测试

安装开发依赖并运行：

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

## 构建独立 EXE

```powershell
.\build.bat
```

构建脚本会先运行完整测试，再重新生成应用图标，最后调用 PyInstaller。成功后文件位于：

```text
dist\FloatingLinkDock.exe
```

## 开机启动说明

开机启动仅写入当前 Windows 用户的启动项，名称为 `FloatingLinkDock`。关闭开关时只会移除该程序自己的启动项，不影响其他软件。

源码模式建议先在当前环境安装项目依赖；发布使用时建议使用 EXE，以确保启动路径稳定。
