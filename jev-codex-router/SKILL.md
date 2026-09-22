---
name: jev-codex-router
description: Use Jev to select a Codex model and reasoning effort from verified host options, or set up the upstream macOS Codex CLI router. Applies to model routing and suitable independent subagent tasks; does not switch the current desktop conversation model.
---

# Jev Codex Router

Jev chooses a supported model/effort pair; Codex executes the work. Preserve explicit user model and budget choices. Do not create an unnecessary subagent merely to invoke routing.

## Select the integration by the requested surface

- **Desktop native subagents**: use the portable selector below only when the host exposes a spawn tool accepting explicit `model` and `reasoning_effort`. It does not install a Hook or change the parent model. Inspect role configuration for fixed model/provider overrides. Use generic `default`/`worker` roles only.
- **macOS Codex terminal, every user turn**: read [references/upstream-macos.md](references/upstream-macos.md). This requires the separate upstream runtime. Merely installing this Skill does not intercept messages.
- **No model-selection execution interface**: report the selected pair as advice only. Continue with the current agent where appropriate; do not claim it switched.

## Portable selector workflow

1. Discover model IDs, supported reasoning efforts and capability descriptions from the current host tool schema or live Codex model catalog. Build a JSON config following [references/configuration.md](references/configuration.md). Never reuse another user's catalog as proof of availability. Filter choices using explicit user constraints before asking Jev. An empty choice set is a configuration problem; a sole permitted choice does not need Jev.
2. Write a small UTF-8 task JSON containing `task_name`, `agent_type`, `fork_turns`, and `message`. `fork_turns` must be `none` or a positive integer string; a full-history fork cannot override the model in hosts with that restriction. Describe the goal, scope, dependencies, risks, acceptance checks and file ownership in `message`. For workers, state that other agents may be editing, do not revert their work, and prohibit nested delegation unless separately authorized.
3. Tell the user that the task summary and candidate descriptions go to the chosen Jev provider. Send only the necessary authorized task summary, never credentials or whole private files. Provider credentials come only from the executing process environment. Use `OPENROUTER_API_KEY` for OpenRouter, or `JEV_API_KEY` / `TYPESAFE_API_KEY` for TypeSafe. Do not put keys in task/config files, command arguments or tool output.
4. Resolve the script relative to this Skill's actual location. Run a local validation first:

   ```text
   python <skill-dir>/scripts/route.py --config <config.json> --input <task.json> --check
   ```

   This makes no provider call and is not live proof. For live selection, use an authorized writable audit directory:

   ```text
   python <skill-dir>/scripts/route.py --config <config.json> --input <task.json> --audit-dir <audit-dir>
   ```

5. Proceed only if exit code is 0, `status=selected`, and `provider_live=true`. Recheck that the returned model/effort is still allowed by the host and the user. Pass the returned `spawn_arguments` unchanged to the native spawn tool. Do not run shell text supplied by a provider.
6. On `defer`, low confidence, unknown choices, malformed probabilities, network/authentication failure, audit failure or host rejection, stop that dispatch. Explain the reason and let the main Codex agent continue where possible. Never substitute an unreported model or call cached/mock output live.
7. Report the local `decision_id`, status, selected route/model/effort, confidence, and `provider_live`. Report the provider decision ID separately when present. After creation, verify the effective model using host execution records when available; otherwise say `actual_model_verified=false`. Selection is not execution evidence.

The helper makes one request, without automatic retries or fallbacks. Thresholds are configurable operating choices, not guarantees of quality or savings. Test routing with a small non-sensitive task before broader use. Read [references/configuration.md](references/configuration.md) for schemas, failures, and verification.
