# Jev Codex Router Skill

把“Jev 选择模型和推理强度，Codex 执行任务”的方法打包成可安装 Skill。适合分享给其他 Codex 用户。版本：1.0.0。

## 安装

从 [Releases 下载 ZIP 安装包](https://github.com/455-dIAO/jev-codex-router-skill/releases/latest)，解压后在包含 `install.py` 的目录运行：

```sh
python install.py
```

也可以从 GitHub 克隆安装：

```sh
git clone https://github.com/455-dIAO/jev-codex-router-skill.git
cd jev-codex-router-skill
python install.py
```

Release 同时提供 `.zip.sha256` 校验文件。Windows 使用 `Get-FileHash <ZIP路径> -Algorithm SHA256` 核对下载文件。

Windows 也可使用 `py -3 install.py`，macOS/Linux 可用 `python3 install.py`。要求 Python 3.10+，不需要 pip 依赖。默认安装到 `$CODEX_HOME/skills/jev-codex-router`；未设置 `CODEX_HOME` 时安装到 `~/.codex/skills/jev-codex-router`。

安装器只复制 Skill 的八个必要文件；不联网、不读 Key、不修改 Hooks、AGENTS.md 或现有模型配置。重复安装相同内容会返回 `already_installed`。遇到已有不同内容会停止，先自行备份旧目录再安装，避免覆盖改动。

也可以手动把完整的 `jev-codex-router` 文件夹复制到自己的 Skills 目录，或指定位置：

```sh
python install.py --skills-dir /your/custom/skills
```

在 Codex 新会话中输入 `$jev-codex-router`。若未发现，重启 Codex，并确认安装目录属于当前用户/当前 Codex 主目录。

## 发给 Codex 的使用提示词

> 使用 $jev-codex-router 帮我配置 Jev 模型路由。先检查当前环境支持的执行方式，从真实模型目录生成候选配置。使用我已设置的提供方凭据，为一个只读小任务做实时选模验证；报告决策 ID、置信度、所选模型和推理强度，再分别说明子任务是否执行、实际模型是否得到验证。

Skill 会指导 Codex 生成接收者自己的候选配置，不需要照搬作者机器的模型名称。先在进程环境中配置自己的 `OPENROUTER_API_KEY`，或 TypeSafe 的 `JEV_API_KEY` / `TYPESAFE_API_KEY`。密钥不需要写入本包。每次实时选模会发送任务摘要和候选描述到对应提供方，可能产生 API 费用。

## 两种接入方式

| 方式 | 用途 | 条件与边界 |
| --- | --- | --- |
| 便携选择器 | 给合适的独立子任务选模型和强度 | Python 3.10+；宿主必须支持原生子智能体显式模型参数；Windows/macOS/Linux 脚本可用，实际宿主权限需各自验证 |
| 原项目运行时 | Codex CLI 每次消息重新选模 | 另行安装 macOS 上游运行时；本 Skill 提供操作指引 |

**安装 Skill 不会自动切换 Codex 桌面主会话模型，也不会给所有消息安装拦截器。** 它没有后台服务或自动 Hook。无显式选模工具时只能给建议，不能声称已经切换。

示例流程：任务摘要 → 真实候选 → Jev 返回 choice/confidence → 本地校验与审计 → Codex 原生工具执行 → 核对实际执行模型。Jev 失败、低置信度或选择 defer 时停止该次派发，由主智能体继续分析。

## 文件与验证

- `jev-codex-router/SKILL.md`：智能体入口。
- `jev-codex-router/scripts/route.py`：独立路由脚本，只选择，不自动执行。
- `jev-codex-router/references/`：配置、上游安装、来源说明。
- `jev-codex-router/assets/`：任务和配置模板，候选模型需现场填入。
- `tests/`：离线回归测试，运行 `python -m unittest discover -s tests -v`。
- `VALIDATION.md`：本次交付的验证结果和未验证边界。

移除 Skill 时，只移除安装目录中的 `jev-codex-router` 文件夹；先确认路径并备份个人改动。工作目录中的配置、审计和独立上游运行时不由本包删除。

本包不是 TypeSafe、OpenAI 或原项目的官方产品。原理与参考链接见 `references/sources.md`；不承诺固定节省额度或更高任务成功率。
