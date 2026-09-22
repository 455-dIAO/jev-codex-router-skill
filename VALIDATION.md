# 验证记录

版本：1.0.1。验证日期：2026-09-22。本次补充验证使用 Windows Codex 桌面、Ubuntu WSL 和 GitHub 托管 Ubuntu / macOS 系统。

安装器和路由脚本与 v1.0.0 相同；v1.0.1 更新测试夹具、跨平台工作流、README 和本记录。

## 已执行

- 官方 skill-creator 的 `quick_validate.py`：`Skill is valid!`。
- `python -m unittest discover -s tests -v`：Windows 17 项中 16 项通过；1 项符号链接用例因当前进程不允许创建测试链接而跳过。GitHub Ubuntu / macOS 四组各 17 项全部通过。
- 安装行为测试覆盖：首次安装、同内容重复安装、带中文和空格的路径、保留无关文件、拒绝覆盖个人修改、拒绝源码/目标重叠。
- 路由行为测试覆盖：候选映射、任务保持不变、defer、低置信度、未知选项、概率缺失/不合法、完整历史 fork 拒绝、审计失败停派、缺少 Key、重定向拒绝、UTF-8 BOM 和离线检查。
- 审计检查：mock 不标记 live，收据不保存任务正文或派发参数，实际执行模型初始明确标为未验证。

## 桌面子任务实际模型：已验证

本次用公开配置模板的只读 JSON 检查完成了完整链路：

1. 运行本包 `jev-codex-router/scripts/route.py` 做实时选择。
2. 遵守本机的额外派发规则，对同一任务运行既定宿主选择器；两者的完整派发参数一致，才调用原生 `collaboration.spawn_agent`。
3. 子智能体实际解析了两个示例 JSON 并完成返回。
4. 只读核对该子任务的 Codex 会话执行记录，确认 `turn_context.model` 和 `turn_context.effort`。

| 证据 | 结果 |
| --- | --- |
| 本包本地 decision_id | `37029ecd-d8a7-4e74-bc26-5973da4d2b7f` |
| 本包 provider_decision_id | `gen-dec-1790060698-9gDzg7Ko67CykNbTZiyh` |
| 本包实时选择 | `selected`，`provider_live=true`，`fast`，置信度 0.94 |
| 本机派发前核对 decision_id | `53a393f1-5e91-430e-b3c1-843158bb4ee1`，实时成功，置信度 0.97 |
| 子任务会话 ID | `01a0c7ee-c633-7540-b4b3-8aefe9ee3b88` |
| 期望模型与强度 | `gpt-5.6-luna / low` |
| 执行记录模型与强度 | `gpt-5.6-luna / low`，一致 |
| 子任务结果 | 正确列出两个 JSON 的顶层字段，确认 `routes={}`、`fork_turns=none` |

结论：本次 **单个只读子任务** 的实际模型已核验，依据是宿主执行记录，不是子智能体自述。原始会话日志保留在本机，不上传个人会话内容。选择脚本仍返回 `actual_model_verified=false`，因为它自身不负责执行或读取宿主记录；本表是执行后的独立补充证据。此结果不证明所有模型、所有角色或其他用户的宿主配置均有效。

## TypeSafe 官方直连：已验证

使用本机当前登录用户环境中的 TypeSafe 凭据，仅注入实际调用进程；没有写入仓库、安装包或 GitHub Secrets。调用的是官方 `https://api.typesafe.ai/v1/systemone`，不是 OpenRouter 转发。

首次调用返回 HTTP 401；用户确认账户环境后，重新读取凭据调用成功：

| 字段 | 结果 |
| --- | --- |
| 本地 decision_id | `d2db795f-2380-4d8d-8dc3-6a4605562e02` |
| provider | `typesafe` |
| status / provider_live | `selected` / `true` |
| selected_model / selected_effort | `gpt-5.6-luna` / `low` |
| confidence | 1.0 |
| 输入范围 | 合成的 Python 加法函数任务及候选能力说明 |

这是 TypeSafe 账户鉴权、官方 API 通信和本包响应解析的实时成功证据，不是任务执行或性能基准。OpenRouter 的成功记录仍独立列在下方。

## Ubuntu / macOS 真实系统：已验证

[通过的 GitHub Actions 运行](https://github.com/455-dIAO/jev-codex-router-skill/actions/runs/35697914357)，测试提交 `106ec5a1a1a430b64de970cae65956d57a0a5be3`：

| 系统来源 | Python | 结果 |
| --- | --- | --- |
| GitHub 托管 Ubuntu 24.04 | 3.10 | 17 / 17 通过 |
| GitHub 托管 Ubuntu 24.04 | 3.12 | 17 / 17 通过 |
| GitHub 托管 macOS 15 Intel | 3.10 | 17 / 17 通过 |
| GitHub 托管 macOS 15 Intel | 3.12 | 17 / 17 通过 |
| 本机 Ubuntu WSL2，Linux 6.6.87.2 | 3.12.3 | 修正前的 16 / 16 测试通过 |

覆盖真实文件系统安装、同内容重复安装、保留个人修改、拒绝符号链接、默认 `CODEX_HOME` 命令行安装，以及离线路由响应/审计边界。GitHub 作业未接收 Jev Key，不做付费模型调用。

首轮 macOS 的两个安装测试失败，原因是测试框架的临时目录经过系统 `/var` 符号链接，被安装器按设计拒绝。测试夹具改为解析后的真实临时目录，再验证首次安装与重复安装；单独的符号链接拒绝用例仍保留且通过。没有删除保护或跳过失败测试来获得通过结果。[首轮失败记录](https://github.com/455-dIAO/jev-codex-router-skill/actions/runs/35697630996)

这些是 GitHub 托管系统与 WSL 的真实运行，非静态源码推断；不等于用户个人 Mac 的桌面应用测试，也不包含原项目 macOS CLI 的账号登录和逐轮路由验证。

## 一次真实 OpenRouter 选择

测试输入是公开、合成的两数相加 Python 函数说明，未发送私有文件。候选来自本次宿主提供的模型与强度信息。这是当前账户的一次连通性与选择测试，不是模型质量基准或节省额度证明。

| 字段 | 结果 |
| --- | --- |
| status | selected |
| provider_live | true |
| 本地 decision_id | 5d9f3eb2-684c-4735-80b3-14719726efb2 |
| provider_decision_id | gen-dec-1790046121-Y8Vrt6uj4GerLVuokDcJ |
| selected_route | fast |
| selected_model | gpt-5.6-luna |
| selected_effort | low |
| confidence | 1.0 |
| actual_model_verified | false：未派发这个测试子任务 |

## 审查与平台限制

独立审查原计划通过本机既定 Jev 选模器派发。实时选择返回低置信度 0.55，状态 blocked，本地决策 ID `df7a8d8a-8260-4b7e-abd2-14251c486c1d`，provider_live=true。按配置停止派发，没有更改阈值、绕过路由或把主智能体检查称为独立批准。

该记录属于 v1.0.0 的历史审查尝试，本次执行验证不追溯替代完整 Skill 审查。当前剩余边界是原项目 macOS CLI 登录/逐轮路由、其他模型/角色与其他用户环境；已验证的 TypeSafe 直连、便携包跨平台运行和桌面子任务实际模型见上文。

本轮另由未编写测试改动的子智能体对 README、本记录、测试夹具、工作流及所列本地证据进行定向只读审查，未发现可操作的事实不一致或过度声明。该审查仅覆盖本次验证更新，不等于完整仓库审计。
