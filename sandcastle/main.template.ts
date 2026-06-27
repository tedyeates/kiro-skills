/**
 * Sandcastle Runner — per-project main.ts template.
 *
 * Copy to `.sandcastle/main.ts` in your project repo and customise the config.
 * Run: npx tsx .sandcastle/main.ts --prd <number> [--dry-run]
 */

import { createSandbox } from "@ai-hero/sandcastle";
import { docker } from "@ai-hero/sandcastle/sandboxes/docker";
import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

// ─── Project Config (edit per-repo) ──────────────────────────────────────────

const config = {
  repo: "tedyeates/stockmanager",
  setup:
    "cd stockmanagement_bg && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ../stockmanagement-fe && pnpm install",
  test: "cd stockmanagement_bg && .venv/bin/pytest && cd ../stockmanagement-fe && pnpm test",
  typeCheck:
    "cd stockmanagement_bg && .venv/bin/pyright && cd ../stockmanagement-fe && pnpm tsc --noEmit",
  timeoutSeconds: 900,
};

// ─── CLI Arg Parsing ─────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const prdIdx = args.indexOf("--prd");
const prdNumber = prdIdx !== -1 ? Number(args[prdIdx + 1]) : NaN;
const dryRun = args.includes("--dry-run");

if (isNaN(prdNumber)) {
  console.error("Usage: npx tsx .sandcastle/main.ts --prd <number> [--dry-run]");
  process.exit(1);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function gh(cmd: string): string {
  return execSync(`gh ${cmd}`, { encoding: "utf-8" }).trim();
}

function log(msg: string) {
  const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
  console.log(`[${ts}] ${msg}`);
}

function elapsed(start: number): string {
  const s = Math.round((Date.now() - start) / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${s % 60}s`;
}

// ─── Task Sourcing (#40) ─────────────────────────────────────────────────────

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
    issue_dependencies_summary?: { blocked_by: number };
  }> = JSON.parse(raw);

  return issues
    .filter((i) => i.state === "open")
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
  log(`Fetching PRD #${prdNumber}...`);
  const designPath = fetchDesignPath();
  const allIssues = fetchAllSubIssues();

  if (allIssues.length === 0) {
    log("No open sub-issues found.");
    process.exit(0);
  }

  log(`Found ${allIssues.length} open sub-issue(s):`);
  for (const t of allIssues) console.log(`  #${t.number} — ${t.title}`);

  if (dryRun) {
    log("Dry run — exiting without execution.");
    process.exit(0);
  }

  // ─── Branch & Sandbox Lifecycle (#41) ────────────────────────────────────

  const branch = `feature/prd-${prdNumber}`;

  try {
    execSync(`git checkout -b ${branch}`, { stdio: "ignore" });
  } catch {
    execSync(`git checkout ${branch}`, { stdio: "ignore" });
  }
  log(`On branch: ${branch}`);

  await using sandbox = await createSandbox({
    branch,
    sandbox: docker({
      imageName: "kiro-runner",
      mounts: [
        { hostPath: "~/.kiro", sandboxPath: "/home/agent/.kiro", readonly: true },
      ],
    }),
    hooks: {
      sandbox: {
        onSandboxReady: [{ command: config.setup, timeoutMs: 300_000 }],
      },
    },
  });

  log("Sandbox ready.");

  const logsDir = resolve(".sandcastle", "logs");
  mkdirSync(logsDir, { recursive: true });

  // ─── Task Loop with Verification (#42) ──────────────────────────────────

  const done = new Set<number>();
  const completedTasks: SubIssue[] = [];
  let task: SubIssue | undefined;

  while ((task = nextUnblocked(allIssues, done))) {
    const taskStart = Date.now();
    log(`[task #${task.number}] implementing...`);

    const implPrompt = buildImplementerPrompt(task, designPath);
    const implResult = await sandbox.exec(
      `kiro-cli chat --no-interactive --trust-all-tools --agent implementer "${escapeShell(implPrompt)}"`,
      { cwd: "/home/agent/workspace" }
    );
    writeFileSync(
      resolve(logsDir, `${task.number}-implementer.log`),
      implResult.stdout + "\n" + implResult.stderr
    );

    // Post-implementer checks
    log(`[task #${task.number}] verifying...`);
    const postImpl = await runChecks(sandbox);

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
      `kiro-cli chat --no-interactive --trust-all-tools --agent reviewer "${escapeShell(reviewPrompt)}"`,
      { cwd: "/home/agent/workspace" }
    );
    writeFileSync(
      resolve(logsDir, `${task.number}-reviewer.log`),
      revResult.stdout + "\n" + revResult.stderr
    );

    // Final gate
    log(`[task #${task.number}] final checks...`);
    const finalChecks = await runChecks(sandbox);

    if (!finalChecks.passed) {
      const tail = finalChecks.output.split("\n").slice(-30).join("\n");
      console.error(`\n[task #${task.number}] FAILED final checks:\n${tail}`);
      process.exit(1);
    }

    done.add(task.number);
    completedTasks.push(task);
    log(`[task #${task.number}] ✓ passed (${elapsed(taskStart)})`);
  }

  if (completedTasks.length === 0) {
    log("No tasks could be unblocked. Check dependency graph.");
    process.exit(1);
  }

  // ─── Completion: Push & PR (#43) ────────────────────────────────────────

  log("All tasks passed. Pushing...");
  execSync(`git push -u origin ${branch}`, { stdio: "inherit" });

  const prBody = buildPrBody(completedTasks, prdNumber);
  const prUrl = gh(
    `pr create --base main --head ${branch} --title "feat: PRD #${prdNumber}" --body "${escapeShell(prBody)}"`
  );

  log(`✓ ${completedTasks.length} tasks completed. PR: ${prUrl}`);
}

// ─── Verification Logic (#42) ────────────────────────────────────────────────

interface CheckResult {
  passed: boolean;
  output: string;
}

async function runChecks(sandbox: {
  exec: (cmd: string, opts?: { cwd?: string }) => Promise<{ stdout: string; stderr: string; exitCode: number }>;
}): Promise<CheckResult> {
  const testResult = await sandbox.exec(config.test, { cwd: "/home/agent/workspace" });
  if (testResult.exitCode !== 0) {
    return { passed: false, output: `TEST FAILED:\n${testResult.stdout}\n${testResult.stderr}` };
  }

  const typeResult = await sandbox.exec(config.typeCheck, { cwd: "/home/agent/workspace" });
  if (typeResult.exitCode !== 0) {
    return { passed: false, output: `TYPE-CHECK FAILED:\n${typeResult.stdout}\n${typeResult.stderr}` };
  }

  return { passed: true, output: "All checks passed." };
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

function buildPrBody(tasks: SubIssue[], prd: number): string {
  let body = `## Summary\n\nImplements PRD #${prd}\n\n## Tasks completed\n\n`;
  for (const t of tasks) body += `- Closes #${t.number} — ${t.title}\n`;
  body += `\n---\nParent: #${prd}`;
  return body;
}

function escapeShell(s: string): string {
  return s.replace(/"/g, '\\"').replace(/\$/g, "\\$").replace(/`/g, "\\`");
}

// ─── Run ─────────────────────────────────────────────────────────────────────

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
