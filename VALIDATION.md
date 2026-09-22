# 验证记录

版本：1.0.0。验证日期：2026-09-22。平台：Windows，Python 3.12 / 本机 Anaconda Python。

## 已执行

- 官方 skill-creator 的 `quick_validate.py`：`Skill is valid!`。
- `python -m unittest discover -s tests -v`：16 项中 15 项通过；1 项符号链接用例因 Windows 不允许当前进程创建测试链接而跳过。
- 安装行为测试覆盖：首次安装、同内容重复安装、带中文和空格的路径、保留无关文件、拒绝覆盖个人修改、拒绝源码/目标重叠。
- 路由行为测试覆盖：候选映射、任务保持不变、defer、低置信度、未知选项、概率缺失/不合法、完整历史 fork 拒绝、审计失败停派、缺少 Key、重定向拒绝、UTF-8 BOM 和离线检查。
- 审计检查：mock 不标记 live，收据不保存任务正文或派发参数，实际执行模型初始明确标为未验证。

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

因此，本包没有独立子智能体审查通过的结论。TypeSafe 直连接口已按官方文档和本地契约测试实现，未做账户实时调用；macOS/Linux 安装及原项目运行时未在本轮实机验证。桌面子智能体实际模型核验也未完成。接收者应根据自己的宿主目录、工具能力和账户权限再验证。
