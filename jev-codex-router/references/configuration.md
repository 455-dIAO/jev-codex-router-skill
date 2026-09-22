# 配置与使用

需要 Python 3.10+，仅使用标准库。Windows 可用 `py -3` 替换 `python`，macOS/Linux 可用 `python3`。安装 Skill 与调用 Jev 是两件事；离线安装不需要 Key。

## 第一次使用

把这段话发给安装好 Skill 的 Codex：

> 使用 $jev-codex-router。先检查当前宿主是否提供显式选模的原生子智能体工具，从宿主真实模型目录生成 router.json。使用我已配置的 Jev 提供方，为一个不含敏感信息的只读子任务做实时选模。报告决策 ID、置信度、选定模型与强度，并把选模结果和实际执行模型的验证分开说明。

创建 config 和 task 时，使用工作目录下的独立文件。不要修改 Skill 包中的示例，不要发送仓库完整内容。

## router.json

`assets/router.example.json` 故意使用空 `routes`：它是配置模板，不能当作可用模型目录直接运行。Codex 应依据当前宿主工具 schema 或 `model/list` 填充至少两个真实候选。每个候选包含：

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

模型与档位组合的宿主兼容性由调用方检查，脚本只校验数据格式和候选集合。配置过期时重新发现目录，不自行猜测新模型名。

## Key 与提供方

| 提供方 | 进程环境变量 | API |
| --- | --- | --- |
| TypeSafe | `JEV_API_KEY`，也接受 `TYPESAFE_API_KEY` | `https://api.typesafe.ai/v1/systemone` |
| OpenRouter | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/alpha/decisions` |

通过用户自己的凭据管理方式设置进程环境。不要把 Key 发给聊天助手、保存到示例 JSON 或嵌入命令行。Windows 设置了用户环境变量后，旧进程未必继承；重开终端/Codex 后再试。本脚本不读取注册表、其他项目的 .env 或已有登录文件。

发送给提供方的是 `message` 任务摘要、角色和候选说明；审计文件不保存摘要正文。stdout 的 `spawn_arguments` 会包含原任务文本，所以仍需控制任务输入。OpenRouter Decisions 为 alpha 接口，未来可能变化；出现错误应停止并核对文档，不切换成聊天补全 API。

## 输入与输出

复制 `assets/task.example.json` 并修改为真实任务。必须包含 `task_name`、`agent_type`、`fork_turns`、`message`，不提前填写模型或强度。

在 `--check` 下退出码 0 仅表示本地校验通过，`provider_live=false`。实时成功退出码 0 返回 `status=selected`、`provider_live=true`、完整 `spawn_arguments` 和审计路径；失败或 defer 退出码 2，不给可执行派发参数。

本地 UUID `decision_id` 用于审计关联，不是供应商 ID。若响应带 ID，另存为 `provider_decision_id`。`actual_model_verified` 始终初始为 false，因为脚本不创建智能体。

## 执行与验收

宿主提供 `collaboration.spawn_agent` 且允许动态模型参数时，把 `spawn_arguments` 原样传入。遵守当前宿主工具 schema、角色限制、用户预算及权限；本 Skill 不绕过宿主拒绝。

首轮采用只读子任务。分别记录：Skill 文件可发现、本地配置有效、实时 Jev 响应有效、宿主派发成功、子任务返回、实际模型记录可核对。不能读取执行记录时明确写“实际模型未验证”，不能用 Jev 结果或子智能体自述证明模型身份。

如果当前项目已经有专用路由入口或更具体的路由规则，优先遵守，不并联多个自动路由器。本 Skill 没有宿主 Hook，没有修改父会话模型的能力，也不会让所有会话自动逐轮选模。
