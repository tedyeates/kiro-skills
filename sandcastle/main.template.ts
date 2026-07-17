/**
 * Sandcastle Runner — per-project main.ts template.
 *
 * Copy to `.sandcastle/main.ts` in your project repo and customise the config.
 * Run: npx tsx .sandcastle/main.ts --prd <number> [--dry-run]
 */

import "dotenv/config";
import { createSandbox } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";
import { execSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

// ─── Project Config (edit per-repo) ──────────────────────────────────────────

const config = {
  repo: "your-org/your-repo",
  setup: "pnpm install",
  test: "pnpm test",
  typeCheck: "pnpm tsc --noEmit",
  // Host commands — run on host machine (not in sandbox).
  // Useful for supabase CLI, DB migrations, pgTap tests, etc.
  hostSetup: "",
  hostTest: "",
  hostTeardown: "", // always runs on completion or failure (e.g. "supabase stop --no-backup")
  timeoutSeconds: 900,
  agentLabel: "ready-for-agent", // only tasks carrying this label are implemented
};

// ─── CLI Arg Parsing ─────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const prdIdx = args.indexOf("--prd");
const prdNumber = prdIdx !== -1 ? Number(args[prdIdx + 1]) : NaN;
const dryRun = args.includes("--dry-run");
// --verbose / -v: stream agent + check output live to the terminal (for testing).
// Logs are still written to .sandcastle/logs/ regardless.
const verbose = args.includes("--verbose") || args.includes("-v");

if (isNaN(prdNumber)) {
  console.error("Usage: npx tsx .sandcastle/main.ts --prd <number> [--dry-run] [--verbose|-v]");
  process.exit(1);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function gh(cmd: string): string {
  return execSync(`gh ${cmd}`, { encoding: "utf-8" }).trim();
}

/** Run a gh command piping content via stdin (avoids shell-escaping issues with newlines). */
function ghStdin(cmd: string, input: string): string {
  return execSync(`gh ${cmd}`, { input, encoding: "utf-8" }).trim();
}

function log(msg: string) {
  const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
  console.log(`[${ts}] ${msg}`);
}

function elapsed(start: number): string {
  const s = Math.round((Date.now() - start) / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${s % 60}s`;
}

// Returns an onLine callback that mirrors sandbox output to the terminal when
// --verbose is set; otherwise undefined (output is only captured to the log).
function liveStream(prefix: string): ((line: string) => void) | undefined {
  if (!verbose) return undefined;
  return (line: string) => {
    const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
    process.stdout.write(`  │ [${ts}] ${prefix} ${line}\n`);
  };
}

// ─── Auth ────────────────────────────────────────────────────────────────────

function ensureAuth() {
  // Headless mode: KIRO_API_KEY env var is passed into the sandbox container.
  // When set, kiro-cli skips browser-based login entirely.
  if (!process.env.KIRO_API_KEY) {
    console.error(
      "ERROR: KIRO_API_KEY not set. Add it to .env or export it.\n" +
        "Generate one at https://app.kiro.dev → API Keys."
    );
    process.exit(1);
  }
  log("KIRO_API_KEY set — headless auth enabled.");
}

// ─── Task Sourcing ───────────────────────────────────────────────────────────

interface SubIssue {
  number: number;
  title: string;
  body: string;
  state: string;
  blockedBy: number[];
}

function fetchDesignPath(): string | undefined {
  const body = gh(`api repos/${config.repo}/issues/${prdNumber} --jq ".body"`);
  const match = body.match(/^Design:\s*(.+)$/m);
  return match?.[1]?.trim();
}

function fetchAllSubIssues(): SubIssue[] {
  const raw = gh(`api repos/${config.repo}/issues/${prdNumber}/sub_issues`);
  if (!raw) return [];

  const issues: Array<{
    number: number;
    title: string;
    body: string;
    state: string;
    labels?: Array<{ name: string }>;
    issue_dependencies_summary?: { blocked_by: number };
  }> = JSON.parse(raw);

  return issues
    .filter((i) => i.state === "open")
    .filter((i) => (i.labels ?? []).some((l) => l.name === config.agentLabel))
    .map((i) => {
      let blockedBy: number[] = [];
      if ((i.issue_dependencies_summary?.blocked_by ?? 0) > 0) {
        try {
          const deps = gh(
            `api repos/${config.repo}/issues/${i.number}/dependencies/blocked_by --jq "[.[].number]"`
          );
          blockedBy = JSON.parse(deps || "[]");
        } catch {
          // treat as unblocked if API fails
        }
      }
      return { ...i, blockedBy };
    })
    .sort((a, b) => a.number - b.number);
}

function nextUnblocked(issues: SubIssue[], done: Set<number>): SubIssue | undefined {
  return issues.find(
    (i) => !done.has(i.number) && i.blockedBy.every((b) => done.has(b))
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  ensureAuth();

  log(`Fetching PRD #${prdNumber}...`);
  const designPath = fetchDesignPath();
  const allIssues = fetchAllSubIssues();

  if (allIssues.length === 0) {
    log(`No open '${config.agentLabel}' sub-issues found. Nothing to do.`);
    process.exit(0);
  }

  log(`Found ${allIssues.length} open '${config.agentLabel}' sub-issue(s):`);
  for (const t of allIssues) console.log(`  #${t.number} — ${t.title}`);

  if (dryRun) {
    const unblocked: SubIssue[] = [];
    const blocked: SubIssue[] = [];

    // Fetch closed issues to know which blockers are already done
    const closedNumbers = new Set<number>();
    try {
      const closedRaw = gh(
        `api repos/${config.repo}/issues/${prdNumber}/sub_issues --jq "[.[] | select(.state == \\"closed\\") | .number]"`
      );
      for (const n of JSON.parse(closedRaw || "[]")) closedNumbers.add(n);
    } catch {
      // if fetch fails, treat nothing as closed
    }

    for (const t of allIssues) {
      if (t.blockedBy.every((b) => closedNumbers.has(b))) {
        unblocked.push(t);
      } else {
        blocked.push(t);
      }
    }

    if (unblocked.length > 0) {
      log(`Unblocked (ready to run):`);
      for (const t of unblocked) console.log(`  ✓ #${t.number} — ${t.title}`);
    }
    if (blocked.length > 0) {
      log(`Blocked (waiting on dependencies):`);
      for (const t of blocked) {
        const deps = t.blockedBy.map((b) => `#${b}`).join(", ");
        console.log(`  ✗ #${t.number} — ${t.title}  [blocked by: ${deps}]`);
      }
    }

    log("Dry run — exiting without execution.");
    process.exit(0);
  }

  // Halt before spinning up the sandbox if nothing is actionable right now.
  // Must consider already-closed sub-issues as satisfied dependencies.
  const closedNumbers = new Set<number>();
  try {
    const closedRaw = gh(
      `api repos/${config.repo}/issues/${prdNumber}/sub_issues --jq "[.[] | select(.state == \\"closed\\") | .number]"`
    );
    for (const n of JSON.parse(closedRaw || "[]")) closedNumbers.add(n);
  } catch {
    // if fetch fails, proceed — worst case tasks stay blocked
  }

  if (!nextUnblocked(allIssues, closedNumbers)) {
    log(
      `No unblocked '${config.agentLabel}' tasks — all remaining tasks are blocked by open dependencies. Halting.`
    );
    process.exit(1);
  }

  // ─── Branch & Sandbox Lifecycle ──────────────────────────────────────────

  const branch = `feature/prd-${prdNumber}`;
  log(`Target branch: ${branch}`);

  await using sandbox = await createSandbox({
    branch,
    sandbox: docker({
      imageName: "kiro-runner",
      env: {
        KIRO_API_KEY: process.env.KIRO_API_KEY!,
      },
      mounts: [
        { hostPath: "~/.kiro", sandboxPath: "/home/agent/.kiro", readonly: true },
        { hostPath: "~/.aws", sandboxPath: "/home/agent/.aws" },
      ],
    }),
    hooks: {
      sandbox: {
        onSandboxReady: [{ command: config.setup, timeoutMs: 300_000 }],
      },
    },
  });

  log("Sandbox ready.");

  // Carry the host's git-ignored .env into the workspace so type-check/test see
  // required env vars (e.g. framework `$env` imports). The sandbox worktree is
  // built from the branch, so git-ignored files like .env are never present.
  // base64 round-trips the contents through exec without shell-escaping issues
  // or logging secret values. Generic: only runs if the repo has a root .env.
  const hostEnv = resolve(".env");
  if (existsSync(hostEnv)) {
    const b64 = readFileSync(hostEnv).toString("base64");
    await sandbox.exec(`echo ${b64} | base64 -d > .env`, {
      cwd: "/home/agent/workspace",
    });
    log("Copied host .env into workspace.");
  }

  const logsDir = resolve(".sandcastle", "logs");
  mkdirSync(logsDir, { recursive: true });

  // Host-side setup: runs on the HOST against the bind-mounted worktree
  // (sandbox.worktreePath), where the host Docker daemon is reachable. Once.
  if (config.hostSetup) {
    log(`Host setup: ${config.hostSetup}`);
    execSync(config.hostSetup, { cwd: sandbox.worktreePath, stdio: "inherit" });
  }

  try {
    // ─── Task Loop with Verification ────────────────────────────────────────

    // Seed `done` with sub-issues already closed before this run, so that
    // dependency checks like `blockedBy.every(b => done.has(b))` correctly
    // recognise pre-completed blockers as satisfied.
    const done = new Set<number>();
    try {
      const closedRaw = gh(
        `api repos/${config.repo}/issues/${prdNumber}/sub_issues --jq "[.[] | select(.state == \\"closed\\") | .number]"`
      );
      for (const n of JSON.parse(closedRaw || "[]")) done.add(n);
    } catch {
      // if fetch fails, proceed with empty set — worst case tasks stay blocked
    }

    const completedTasks: SubIssue[] = [];
    let task: SubIssue | undefined;

    while ((task = nextUnblocked(allIssues, done))) {
      const taskStart = Date.now();
      log(`[task #${task.number}] implementing...`);

      const implPrompt = buildImplementerPrompt(task, designPath);
      const implResult = await sandbox.exec(
        `kiro-cli chat --no-interactive --agent implementer "${escapeShell(implPrompt)}"`,
        { cwd: "/home/agent/workspace", onLine: liveStream(`#${task.number} impl`) }
      );
      writeFileSync(
        resolve(logsDir, `${task.number}-implementer.log`),
        implResult.stdout + "\n" + implResult.stderr
      );

      // Post-implementer checks
      log(`[task #${task.number}] verifying...`);
      const postImpl = await runChecks(sandbox, sandbox.worktreePath);

      let reviewerContext: string;
      if (postImpl.passed) {
        reviewerContext = "Implementer checks passed. Review for code quality.";
      } else {
        reviewerContext = `Implementer checks FAILED:\n${postImpl.output.slice(-2000)}`;
      }

      // Reviewer always runs
      log(`[task #${task.number}] reviewing...`);
      const reviewPrompt = buildReviewerPrompt(task, reviewerContext, designPath);
      const revResult = await sandbox.exec(
        `kiro-cli chat --no-interactive --agent reviewer "${escapeShell(reviewPrompt)}"`,
        { cwd: "/home/agent/workspace", onLine: liveStream(`#${task.number} review`) }
      );
      writeFileSync(
        resolve(logsDir, `${task.number}-reviewer.log`),
        revResult.stdout + "\n" + revResult.stderr
      );

      // Final gate
      log(`[task #${task.number}] final checks...`);
      const finalChecks = await runChecks(sandbox, sandbox.worktreePath);

      if (!finalChecks.passed) {
        const tail = finalChecks.output.split("\n").slice(-30).join("\n");
        throw new Error(`[task #${task.number}] FAILED final checks:\n${tail}`);
      }

      done.add(task.number);
      completedTasks.push(task);
      gh(`issue close ${task.number} --repo ${config.repo}`);
      checkpointPR(branch, prdNumber, task);
      log(`[task #${task.number}] ✓ closed & pushed (${elapsed(taskStart)})`);
    }

    if (completedTasks.length === 0) {
      throw new Error("No tasks could be unblocked. Check dependency graph.");
    }

    // ─── Completion ──────────────────────────────────────────────────────────

    log(`✓ ${completedTasks.length} tasks completed. PR pushed incrementally.`);
  } finally {
    // Host teardown always runs — on success, task failure, or check failure.
    if (config.hostTeardown) {
      log(`Host teardown: ${config.hostTeardown}`);
      try {
        execSync(config.hostTeardown, { cwd: sandbox.worktreePath, stdio: "ignore" });
      } catch {
        // best-effort teardown; don't mask the original error
      }
    }
  }
}

// ─── Verification Logic ──────────────────────────────────────────────────────

interface CheckResult {
  passed: boolean;
  output: string;
}

// Run a command on the HOST (not the sandbox), capturing output. Used for
// steps that need the host Docker daemon (e.g. Supabase) against the
// bind-mounted worktree. Returns exit code rather than throwing.
function execHost(cmd: string, cwd: string): { exitCode: number; output: string } {
  try {
    const out = execSync(cmd, { cwd, encoding: "utf-8" });
    if (verbose) process.stdout.write(out);
    return { exitCode: 0, output: out };
  } catch (err) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    const output = `${e.stdout ?? ""}\n${e.stderr ?? ""}`;
    if (verbose) process.stdout.write(output);
    return { exitCode: e.status ?? 1, output };
  }
}

async function runChecks(
  sandbox: {
    exec: (cmd: string, opts?: { cwd?: string; onLine?: (line: string) => void }) => Promise<{ stdout: string; stderr: string; exitCode: number }>;
  },
  hostCwd: string
): Promise<CheckResult> {
  const testResult = await sandbox.exec(config.test, { cwd: "/home/agent/workspace", onLine: liveStream("test") });
  if (testResult.exitCode !== 0) {
    return { passed: false, output: `TEST FAILED:\n${testResult.stdout}\n${testResult.stderr}` };
  }

  const typeResult = await sandbox.exec(config.typeCheck, { cwd: "/home/agent/workspace", onLine: liveStream("tsc") });
  if (typeResult.exitCode !== 0) {
    return { passed: false, output: `TYPE-CHECK FAILED:\n${typeResult.stdout}\n${typeResult.stderr}` };
  }

  // Host-side tests (e.g. pgTAP via `supabase test db`) — run on the host
  // against the bind-mounted worktree. Skipped when hostTest is "".
  if (config.hostTest) {
    const hostResult = execHost(config.hostTest, hostCwd);
    if (hostResult.exitCode !== 0) {
      return { passed: false, output: `HOST TEST FAILED (${config.hostTest}):\n${hostResult.output}` };
    }
  }

  return { passed: true, output: "All checks passed." };
}

// ─── PR Checkpoint ───────────────────────────────────────────────────────────

function checkpointPR(branch: string, prd: number, closedIssue: SubIssue) {
  execSync(`git push -u origin ${branch}`, { stdio: "inherit" });

  const prNumber = gh(
    `pr list --head ${branch} --json number --jq ".[0].number"`
  );

  const entry = `- Closes #${closedIssue.number} — ${closedIssue.title}`;

  if (prNumber) {
    // Append to existing PR body
    const existingBody = gh(`pr view ${prNumber} --json body --jq ".body"`);
    const updatedBody = existingBody + "\n" + entry;
    ghStdin(`pr edit ${prNumber} --body-file -`, updatedBody);
    log(`PR #${prNumber} updated with #${closedIssue.number}.`);
  } else {
    // Create draft PR — title set once
    const body = [
      "## Summary",
      "",
      `Implements PRD #${prd}`,
      "",
      "## Tasks completed",
      "",
      entry,
      "",
      "---",
      `Parent: #${prd}`,
    ].join("\n");
    const url = ghStdin(
      `pr create --base main --head ${branch} --title "feat: PRD #${prd}" --body-file - --draft`,
      body
    );
    log(`Draft PR created: ${url}`);
  }
}

// ─── Prompt Builders ─────────────────────────────────────────────────────────

function buildImplementerPrompt(task: SubIssue, designPath?: string): string {
  let prompt = `Implement the following task.\n\n`;
  prompt += `## Task #${task.number}: ${task.title}\n\n${task.body}\n\n`;
  prompt += `## Check commands\n- Test: ${config.test}\n- Type-check: ${config.typeCheck}\n`;
  if (designPath) prompt += `\n## Design context\nRead ${designPath} for architectural decisions.\n`;
  return prompt;
}

function buildReviewerPrompt(task: SubIssue, context: string, designPath?: string): string {
  let prompt = `Review the implementation of the following task.\n\n`;
  prompt += `## Task #${task.number}: ${task.title}\n\n${task.body}\n\n`;
  prompt += `## Context\n${context}\n\n`;
  prompt += `## Check commands\n- Test: ${config.test}\n- Type-check: ${config.typeCheck}\n`;
  if (designPath) prompt += `\n## Design context\nRead ${designPath} for architectural decisions.\n`;
  return prompt;
}

function escapeShell(s: string): string {
  return s.replace(/"/g, '\\"').replace(/\$/g, "\\$").replace(/`/g, "\\`");
}

// ─── Run ─────────────────────────────────────────────────────────────────────

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
