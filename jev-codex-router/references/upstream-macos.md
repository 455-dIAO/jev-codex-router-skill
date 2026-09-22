# 原项目：macOS Codex CLI 逐轮路由

来源：https://github.com/gholtzap/jev-codex-model-and-effort-router

2026-09-22 查阅的上游要求 macOS 和 Jev Key，使用 Unix socket 和 Codex app-server。Windows 原生和桌面 GUI 主会话不在这条安装路径的已验证范围。不要在 Windows 上直接执行它的安装器，也不要把 WSL 或桌面版兼容性说成已验证。

## 原理

原生终端 UI → 本地 relay → 截获 `turn/start` → 读取真实 `model/list` 和近期对话 → Jev 判断 → 修改 `model` / `effort` → Codex 执行。与本 Skill 的便携子智能体模式相比，上游会发送部分近期会话作为判断上下文。

## 安装流程

1. 用户要求安装原项目时，确认 macOS、可用 Python/Git、已安装且已登录的 Codex CLI。用 `command -v codex` 和 `codex --version` 核对真正使用的可执行文件。不要把 Codex 桌面应用存在当成 CLI 已安装。
2. 将上游克隆到用户选定的安装源码目录。记录 `git rev-parse HEAD`，检查 README、`install.py`、`cli.py` 和依赖安装行为；以该版本的帮助为准。本分发包没有内嵌或执行上游源码。

   ```sh
   git clone https://github.com/gholtzap/jev-codex-model-and-effort-router.git
   cd jev-codex-model-and-effort-router
   git rev-parse HEAD
   python3 install.py --help
   ```

3. 用户未要求接管 `codex` 命令时，先采用不改 shell、不包装原命令的路径：

   ```sh
   python3 install.py --no-wrap-codex --no-shell
   ```

   上游也支持 `--codex-path PATH` 和 `--env-file PATH`。不要把 API Key 放在参数里。用户明确要求默认接管方式时才使用其默认安装选项，并保留安装器备份与原始路径。查看安装器实际输出确定可执行文件位置；在 PATH 未更新时用绝对路径运行它。
4. 用 `jev-codex doctor --offline` 检查本地，再用 `jev-codex config show` 查看路由配置。缺 Key 时让用户通过交互式 `jev-codex auth login` 输入；不代替用户读取或输出 Key。
5. 先通过该版本 `jev-codex --help` 确认入口。做一个无敏感信息的实际对话，检查路由日志和最终执行模型。上游 `router.py` 提供 `--route-only`，但它只证明选模，不证明终端 relay 已执行；从源码调用时先核对依赖与帮助。不要将 `doctor --offline` 或 demo 当作实时路由证据。

## 配置与卸载

`jev-codex config show`；`jev-codex config set NAME VALUE`；macOS 菜单栏入口 `jev-codex settings`。可选模型、强度与上限以当前版本帮助和实际模型目录为准，不承诺节省比例。

用户要求移除上游运行时，使用 `jev-codex uninstall`。`--purge` 会额外删除保存的设置和 Key，只有用户要求清除这些数据时才加。卸载本 Skill 不等于卸载独立的上游运行时。
