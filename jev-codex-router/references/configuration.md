# 配置与使用

需要 Python 3.10+，仅使用标准库。Windows 可用 `py -3` 替换 `python`，macOS/Linux 可用 `python3`。安装 Skill 与调用 Jev 是两件事；离线安装不需要 Key。

## 第一次使用

把这段话发给安装好 Skill 的 Codex：

> 使用 $jev-codex-router。先检查当前宿主是否提供显式选模的原生子智能体工具，从宿主真实模型目录生成 router.json。使用我已配置的 Jev 提供方，为一个不含敏感信息的只读子任务做实时选模。报告决策 ID、置信度、选定模型与强度，并把选模结果和实际执行模型的验证分开说明。

创建 config 和 task 时，使用工作目录下的独立文件。不要修改 Skill 包中的示例，不要发送仓库完整内容。

## router.json

默认直接复制 `assets/router.example.json`，保留 `model_source: "codex"`。每次实时路由启动本机 `codex app-server`，通过 `initialize` → `initialized` → 分页 `model/list` 读取模型和推理档位，自动生成候选，不需要维护模型名称。未指定 `model_source` 且 `routes` 缺省或为空时，同样启用自动发现。

```json
{"provider": "openrouter", "model_source": "codex", "min_confidence": 0.65}
```

旧版非空 `routes` 继续按手工模式运行。升级时删除 `routes` 并加入 `model_source: "codex"`；不接受同时指定自动模式和非空固定候选，避免忽略原有约束。自动发现不使用本包的持久缓存；Codex 自身可能返回内置或缓存目录，目录成功不代表账户推理权限已验证。

自动生成或手工配置的候选包含：

| 字段 | 含义 |
| --- | --- |
| `model` | 当前宿主实际支持的执行模型 ID |
| `reasoning_effort` | 该模型支持的推理档位 |
| `description` | 来自宿主说明的能力描述，注明该档位适用任务和资源取舍 |

候选名可以用 `fast`、`balanced`、`deep`，不要求正好三个。不要根据名字虚构价格或基准分数。用户指定的模型/预算优先：先过滤候选，只有一个时直接遵守用户要求。

顶层字段：

- `provider`：`typesafe` 或 `openrouter`，必须明确选择，不自动跨提供方降级。
- `jev_model`：可选；TypeSafe 默认 `jev-latest`，OpenRouter 默认 `~typesafe/jev-latest`。它是作判断的模型，不是执行任务的模型。
- `min_confidence`：默认 0.65，低于阈值停止派发。
- `timeout_seconds`：默认 30，范围 1–60；单次请求，没有自动重试。
- `routes`：2–254 个候选；脚本额外加入 `defer`，留给无匹配/信息不足。
- `model_source`：`codex` 或 `manual`。没有固定候选时默认自动发现；手工模式必须提供非空 `routes`。
- `allowed_models` / `allowed_efforts`：可选非空字符串数组，用于自动发现时按用户要求限制候选；省略即接受目录内有效选项。设置模型白名单后，新模型只有加入白名单才会参与。
- `discovery_timeout_seconds`：目录发现总超时，默认 20 秒，范围 1–60。失败或候选数不在 2–254 范围时停止，不调用 Jev。
- `codex_command`：可选本机命令参数数组，例如 `["/absolute/path/to/codex"]`。默认从 PATH 查找，Windows 优先原生 `codex.exe`。用于选择与宿主一致的 CLI；只填写可信程序，不接受 shell 命令字符串。

用 `python <skill-dir>/scripts/route.py --config router.json --list-models` 查看当前候选，不需要任务文件或 Jev Key。该命令访问 Codex 模型目录，不向 Jev 发送任务。保持本机 Codex 更新并登录；脚本不会安装或升级 Codex。

桌面工具与单独安装的 CLI 可能有不同目录，调用方仍需检查最终模型/档位在当前宿主工具 schema 中受支持。宿主拒绝时停止，不暗中换模。脚本不更改主会话模型。

## Key 与提供方

| 提供方 | 进程环境变量 | API |
| --- | --- | --- |
| TypeSafe | `JEV_API_KEY`，也接受 `TYPESAFE_API_KEY` | `https://api.typesafe.ai/v1/systemone` |
| OpenRouter | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/alpha/decisions` |

通过用户自己的凭据管理方式设置进程环境。不要把 Key 发给聊天助手、保存到示例 JSON 或嵌入命令行。Windows 设置了用户环境变量后，旧进程未必继承；重开终端/Codex 后再试。本脚本不读取注册表、其他项目的 .env 或已有登录文件。

发送给提供方的是 `message` 任务摘要、角色和候选说明；审计文件不保存摘要正文。stdout 的 `spawn_arguments` 会包含原任务文本，所以仍需控制任务输入。OpenRouter Decisions 为 alpha 接口，未来可能变化；出现错误应停止并核对文档，不切换成聊天补全 API。

## 输入与输出

复制 `assets/task.example.json` 并修改为真实任务。必须包含 `task_name`、`agent_type`、`fork_turns`、`message`，不提前填写模型或强度。

在 `--check` 下退出码 0 仅表示离线配置/任务校验通过，`catalog_checked=false`、`provider_live=false`。`--list-models` 成功返回 `catalog_ready`，不代表 Jev 调用或模型推理成功。实时成功退出码 0 返回 `status=selected`、`provider_live=true`、完整 `spawn_arguments` 和审计路径；失败或 defer 退出码 2，不给可执行派发参数。

收据记录 `model_catalog_source`、模型数、候选数及 `resolved_routes_sha256`，便于核对候选变化；`catalog_access_verified=false` 表示未执行模型权限验证。

本地 UUID `decision_id` 用于审计关联，不是供应商 ID。若响应带 ID，另存为 `provider_decision_id`。`actual_model_verified` 始终初始为 false，因为脚本不创建智能体。

## 执行与验收

宿主提供 `collaboration.spawn_agent` 且允许动态模型参数时，把 `spawn_arguments` 原样传入。遵守当前宿主工具 schema、角色限制、用户预算及权限；本 Skill 不绕过宿主拒绝。

首轮采用只读子任务。分别记录：Skill 文件可发现、本地配置有效、实时 Jev 响应有效、宿主派发成功、子任务返回、实际模型记录可核对。不能读取执行记录时明确写“实际模型未验证”，不能用 Jev 结果或子智能体自述证明模型身份。

如果当前项目已经有专用路由入口或更具体的路由规则，优先遵守，不并联多个自动路由器。本 Skill 没有宿主 Hook，没有修改父会话模型的能力，也不会让所有会话自动逐轮选模。
