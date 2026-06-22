# Manual Orchestration Notes

Reference for implementing #20 (Executor impl+review) and #21 (Executor merge).

## Process Used (Wave 1: #16, #17, #18, #19)

### 1. Create worktrees

From the feature branch (`feature/wave-runner`), create one worktree per task:

```bash
git worktree add -b task/<number>-<slug> <repo>-waves/<prd>/<number>/ feature/wave-runner
```

Each worktree gets its own branch forked from the current feature branch HEAD.

### 2. Invoke implementers in parallel

Spawned 4 implementer agents simultaneously, each with:
- Working directory set to the worktree path
- Issue number and feature name in prompt

```
"Implement issue #<N> for feature wave-runner. Working directory: D:/Projects/skills-waves/wave-runner/<N>"
```

**Key finding:** Agents cannot switch working directory themselves — the subagent system runs them in the project root. The agent prompt says "Working directory: X" but whether it actually `cd`s there depends on the subagent infrastructure. The executor must set `cwd` on the subprocess.

### 3. Verify tests

Ran `python -m pytest tests/ -v` in each worktree after agents completed. All passed.

**Key finding:** The implementer agents could NOT run tests themselves due to `allowedCommands` patterns missing `.*` suffix on pytest entries. Fixed by changing `"pytest"` → `"pytest.*"`. The executor should verify tests pass as a deterministic step after the implementer finishes (belt and suspenders).

### 4. Invoke reviewers in parallel

Spawned 4 reviewer agents with:
- Issue number
- Working directory
- **Base ref** (critical — see below)

```
"Review issue #<N>. Working directory: D:/Projects/skills-waves/wave-runner/<N>. Base ref: feature/wave-runner"
```

### 5. Merge sequentially into feature branch

(Not yet done for this wave — documented from design.)

From the feature branch directory:
```bash
git merge task/<number>-<slug> --no-edit
# Run tests
# If conflict or test fail → invoke merger agent
# If success → remove worktree, delete branch
```

### Merge process (observed)

Merged #16 → #17 → #18 → #19 sequentially into `feature/wave-runner`.

**What happened:**
- #16, #17, #19: clean merges, tests pass immediately
- #18: conflict in `pyproject.toml` (both #16 and #18 created it independently)

**Conflict resolution pattern:**
1. `git merge task/<branch> --no-edit` → detects conflict
2. Read `git diff` to see conflict markers
3. Resolve (keep correct version — in this case HEAD had the standard `build_meta` backend and `>=3.11`)
4. `git add <resolved-files>` + `git commit --no-edit`
5. Run tests to confirm

**Key insight:** Conflicts from parallel implementation are typically in shared config files (`pyproject.toml`, `__init__.py`) where both branches create the same file. The merger agent should handle these easily — they're additive, not semantic conflicts.

**Cleanup:**
```bash
git worktree remove <path> --force  # may fail if OS has lock (antivirus, terminal cwd)
git worktree prune
git branch -D task/<number>-<slug>
```

**Windows gotcha:** `git worktree remove` fails with "Permission denied" if any process has the directory as cwd or an indexer holds a file lock. The executor should handle this gracefully (retry after delay, or leave for manual cleanup).

### --trust-all-tools not needed

Agent configs now have `write` and `shell` in `allowedTools`. Combined with `denyByDefault: true` on shell, the agent can write files and run allowed commands without any trust flag. The invocation is simply:

```python
subprocess.run(["kiro-cli", "chat", "--no-interactive", "--agent", name, prompt], cwd=worktree_path)
```

## Critical Learnings for Executor

### Agent prompt must include base-ref

The reviewer needs `git diff <base-ref>` to see only the task's changes. Without it, `git diff master` returns the entire feature branch history — hundreds of lines of unrelated changes that flood the agent's context and cause silent failures (no output).

### Concurrency vs reliability trade-off

Running 4 agents in parallel caused 3/4 reviewers to return "No result" on first attempt. Likely causes:
- Rate limiting on the model provider
- Context budget exhaustion from large diffs (the `git diff master` problem)

After fixing the diff target, retry with 3 concurrent should work. The executor should have retry logic (re-attempt once on "No result" before marking failed).

### Deterministic verification after agent steps

Don't trust the agent's claim of "tests pass" — always verify:
```python
# After implementer
result = subprocess.run(test_command, cwd=worktree_path)
if result.returncode != 0:
    # Label impl-failed, don't proceed to reviewer
```

### cwd MUST be enforced at OS level

The kiro-cli `subagent` tool has no `cwd` parameter — agents run in the parent's working directory. "Working directory: X" in the prompt is a hint the LLM may ignore. The executor MUST use `cwd=worktree_path` on the subprocess call to enforce isolation. Without this, agents can read/write files in the wrong worktree or the main repo.

```python
subprocess.run([...], cwd=worktree_path)  # non-negotiable
```

### Branch cleanup on success

After successful merge, the orchestrator (not LLM) should:
1. Remove worktree: `git worktree remove <path> --force`
2. Prune: `git worktree prune`
3. Delete branch: `git branch -D task/<number>-<slug>`

### Prompt template for executor

```python
IMPLEMENTER_PROMPT = "Implement issue #{number} for feature {feature}. Working directory: {worktree_path}"
REVIEWER_PROMPT = "Review issue #{number}. Working directory: {worktree_path}. Base ref: {feature_branch}"
MERGER_PROMPT = "Fix merge for issue #{number}. Repo: {repo}. Design: {design_path}. Failure:\n{failure_output}"
```


## Pre-Review Hook Pattern

The orchestrator runs deterministic checks BEFORE invoking the reviewer agent. This reduces the reviewer's context budget, eliminates redundant tool calls, and guarantees the diff is correct (three-dot against base_ref).

### What the hook runs

| Check | When | Source |
|-------|------|--------|
| `git diff {base_ref}...HEAD` | Always | Shows only this task's changes |
| `{test_command}` | Always | From project-config.md |
| `fallow dead-code` | JS/TS projects | Detects unused exports/files |

### Flow

```
Implementer finishes
  → Orchestrator runs pre-review hook (hooks.run_pre_review)
  → Hook output formatted (hooks.format_for_prompt)
  → Reviewer invoked with pre-computed results in prompt
  → Reviewer skips running diff/tests/fallow itself
  → Reviewer only re-runs commands if it needs to VERIFY a fix
```

### Reviewer prompt injection

The executor appends hook output to the reviewer prompt:

```python
from wave_runner.hooks import run_pre_review, format_for_prompt

hook_output = run_pre_review(
    cwd=worktree_path,
    base_ref=feature_branch,
    test_command=config.test_command,
    is_ts_project=has_ts_files(worktree_path),
)

reviewer_prompt = (
    f"Review issue #{number}. Working directory: {worktree_path}. "
    f"Base ref: {feature_branch}\n\n"
    f"# Pre-Review Check Results\n\n{format_for_prompt(hook_output)}"
)
```

### Benefits

- Reviewer context is smaller (no diagnose skill, no running commands to get diff)
- Three-dot diff guarantees only task changes shown (not accumulated feature branch history)
- Test results pre-computed = faster reviewer startup
- If tests already pass and no dead code, reviewer skips fix loop entirely
