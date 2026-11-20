# Mac 工作场景版 · 下载、使用与构建

当前发布为 Mac 工作场景版 v1.3.1，对应 Windows 工作场景版 v1.2.4。两个平台的源码已整合到 `main`。蓝色四宫格的工作场景版可配置网址、文档、文件夹和应用。单击场景方块会请求系统打开该场景内的各个项目。

## 下载和原版保留

- [Mac 工作场景版 v1.3.1 ZIP](https://github.com/ggc0214/floating-link-dock/releases/download/v1.3.1-macos-arm64-scenes/FloatingLinkDockScenes-macos-arm64.zip)：适用于 M 系列、macOS 26.0 或更新版本。名称放大为 14 号粗体，分类和数量标记缩小为 10 号。
- [Mac 常用网址版 v1.2.0 ZIP](https://github.com/ggc0214/floating-link-dock/releases/download/v1.2.0-macos-input-fix-2/FloatingLinkDock-macos-arm64-input-fix-2.zip)：保留绿色笑脸和原有网址功能，详见[使用说明](docs/macos/使用说明.md)。

使用现成应用无需构建。升级前从菜单栏退出对应旧版，解压后将 `.app` 替换到「应用程序」。两款应用各自保存配置，可以同时运行；均尚未经过 Apple 公证。

## 构建

1. 在 M 系列 Mac 上克隆本项目的 `main`，或从 GitHub 下载源码 ZIP 并解压。在 Mac 的 Codex 里打开包含 `launcher_scenes.py` 的项目文件夹。
2. 在 Mac 的登录桌面中使用原生 arm64 Python 和支持 `-stylemask` 的 Tk。下面的构建命令使用 Homebrew Python 3.13 和配套的 Tk。

~~~bash
brew install python@3.13 python-tk@3.13
"$(brew --prefix python@3.13)/bin/python3.13" -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHON=.venv/bin/python bash scripts/build_macos.sh --scenes
~~~

构建通过后，在 `dist/macos-scenes-arm64` 找到 `FloatingLinkDockScenes.app` 和 `FloatingLinkDockScenes-macos-arm64.zip`。脚本会检查 arm64 架构、依赖决定的最低 macOS 版本和本地签名。分享给其他 Mac 用户前，应实测启动与交互。本地签名尚未经过 Apple 公证。

构建原常用网址版时，去掉命令末尾的 `--scenes`；输出在 `dist/macos-arm64/`，不会覆盖工作场景版。构建产物的内部版本号以打包配置为准，上面的下载版本指对应已发布安装包。

## 使用

- 双击 `FloatingLinkDockScenes.app`。菜单栏的蓝色四宫格可唤回窗口。首次运行如果发现旧常用网址版数据，可以选择复制网址和布局。
- 在「工作场景」点「＋ 场景」，添加所需项目。应用请选择本机的 `.app`，例如 `/Applications/WeChat.app`。
- NAS 先在 Finder 用 `⌘K` 连接共享目录，再从「文件 / 文件夹」选择已挂载的文件或目录。也可以粘贴 `/Volumes/共享名/目录` 形式的路径。
- 返回后单击场景方块即可启动。右键场景方块可以编辑、重命名或删除。

工作场景版使用 `~/Library/Application Support/FloatingLinkDockScenes`。绿色常用网址版使用自己的配置目录，两款应用可以同时运行。

## 交给 Mac 上的 Codex

> 请阅读 AGENTS.md 和 README-MAC.md，检查这台 Mac 的 arm64 Python 和 Tk，在本机完成工作场景版 .app 打包，并实际验证首次打开、菜单栏、应用选择、场景一键打开和与旧版共存。
