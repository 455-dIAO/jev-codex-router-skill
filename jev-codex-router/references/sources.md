# 来源与实现边界

本 Skill 于 2026-09-22 根据下列公开资料及当前宿主的原生工具契约编写。Python helper 为独立编写的便携选择器，不包含上游源码副本，不是上游官方发布或 Windows 移植版。

- [原理来源与 macOS 前提](https://github.com/gholtzap/jev-codex-model-and-effort-router)
- [原项目路由器](https://github.com/gholtzap/jev-codex-model-and-effort-router/blob/main/router.py)
- [原项目终端 relay](https://github.com/gholtzap/jev-codex-model-and-effort-router/blob/main/native_proxy.py)
- [原项目安装器](https://github.com/gholtzap/jev-codex-model-and-effort-router/blob/main/install.py)
- [原项目命令入口](https://github.com/gholtzap/jev-codex-model-and-effort-router/blob/main/cli.py)
- [TypeSafe 官方 API 契约](https://docs.typesafe.ai/api)：`state`、`questions`、`choice`、概率分布和置信度。
- [OpenRouter 官方 OpenAPI](https://openrouter.ai/openapi.json)：查找 `/api/alpha/decisions`。
- [OpenRouter TypeSafe 模型页](https://openrouter.ai/typesafe)：Jev 模型与别名。模型页的通用聊天示例不能代替 Decisions 接口契约。

`main`、最新模型别名和 alpha API 会变化。实际安装应记录上游提交；每个接收者应重新发现自己宿主的模型候选。本包的源码检查、离线测试和某一个账户的实时测试都不证明其他账户拥有权限或同样模型。
