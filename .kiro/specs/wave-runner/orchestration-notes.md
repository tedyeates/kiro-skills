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
