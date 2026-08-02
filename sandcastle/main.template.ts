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
  setup: "pnpm install && pnpm exec playwright install chromium",
  testVite: "pnpm test:unit",
  // Sandbox-side pgTAP run: raw pg_prove against $DATABASE_URL. Intentionally
  // diverges from the host `pnpm test:db` (`supabase test db`) — `supabase
  // test db` does NOT re-apply this branch's migrations over the Docker
  // network, which is exactly why `resetDb` (below) exists as a prerequisite
  // step in the sandbox loop. Do NOT "unify" these two paths.
  testDb: "psql \"$DATABASE_URL\" -c \"CREATE EXTENSION IF NOT EXISTS pgtap;\" && pg_prove --dbname \"$DATABASE_URL\" --ext .sql supabase/tests/",
  testE2e: "pnpm test:e2e",
  typeCheck: "pnpm check",
  // In-sandbox DB reset over the Docker network. Replays THIS branch's
  // migrations + seed against the shared Supabase db container using the
  // migration files the agent just wrote (workspace is a bind-mount of the
  // branch worktree). Runs before the DB check so newly-authored migrations
  // are actually applied — `pg_prove` runs against the live db and does NOT
  // auto-apply migrations.
  // PGSSLMODE=disable: the local db container serves no TLS, but the CLI forces
  // TLS for --db-url targets unless told otherwise.
  resetDb: "PGSSLMODE=disable supabase db reset --db-url \"$DATABASE_URL\" --yes",
  // Host-side: ensure Supabase is running (kept alive between tasks)
  hostSetup: "supabase status > /dev/null 2>&1 || supabase start",
  // Host-side reset between tasks: replay migrations + seed, reinstall deps
  hostReset: "supabase db reset && pnpm install",
  agentLabel: "ready-for-agent",
};

// ─── Scoped Test Commands ────────────────────────────────────────────────────
// Implementers and reviewers run ONLY the tests covering the files they touched.
// The orchestrator guard (runChecks) still runs the full suite afterward, so
// these scoped runs are a fast local signal, not the source of truth.
// Vite + DB only — no e2e template: implementers author e2e specs but never
// run them in-loop (verified by the human smoke layer instead).
const scopedTests = {
  // vitest takes a positional path/substring filter
  vite: `${config.testVite} <file>`,
  // pg_prove targets a single .sql file instead of the whole supabase/tests/ dir
  db: config.testDb.replace("supabase/tests/", "supabase/tests/<file>"),
};

// ─── CLI Arg Parsing ─────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const prdIdx = args.indexOf("--prd");
const prdNumber = prdIdx !== -1 ? Number(args[prdIdx + 1]) : NaN;
const dryRun = args.includes("--dry-run");
const verbose = args.includes("--verbose") || args.includes("-v");

if (isNaN(prdNumber)) {
  console.error("Usage: npx tsx .sandcastle/main.ts --prd <number> [--dry-run] [--verbose|-v]");
  process.exit(1);
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function gh(cmd: string): string {
  return execSync(`gh ${cmd}`, { encoding: "utf-8" }).trim();
}

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

function liveStream(prefix: string): ((line: string) => void) | undefined {
  if (!verbose) return undefined;
  return (line: string) => {
    const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
    process.stdout.write(`  │ [${ts}] ${prefix} ${line}\n`);
  };
}

// ─── Supabase Network Detection ──────────────────────────────────────────────

/**
 * Detect the Docker network Supabase CLI created for local dev.
 * Convention: supabase_network_<project-dir-name>
 */
function detectSupabaseNetwork(): string {
  const networks = execSync(
    `docker network ls --filter name=supabase_network --format "{{.Name}}"`,
    { encoding: "utf-8" }
  ).trim().split("\n").filter(Boolean);

  if (networks.length === 0) {
    throw new Error("No supabase_network_* Docker network found. Run 'supabase start' first.");
  }
  if (networks.length > 1) {
    log(`Multiple Supabase networks found: ${networks.join(", ")}. Using first.`);
  }
  return networks[0];
}

/**
 * Build a .env for the sandbox that uses Docker container hostnames
 * instead of localhost ports. Kong on the Supabase network exposes port 8000.
 */
function buildSandboxEnv(network: string): string {
  // Derive project suffix from network name: supabase_network_<suffix>
  const suffix = network.replace("supabase_network_", "");
  const kongHost = `supabase_kong_${suffix}`;

  // Read the host .env to get the anon key (not secret for local dev)
  const hostEnvPath = resolve(".env");
  let anonKey = "";
  if (existsSync(hostEnvPath)) {
    const content = readFileSync(hostEnvPath, "utf-8");
    const match = content.match(/PUBLIC_SUPABASE_ANON_KEY=(.+)/);
    anonKey = match?.[1]?.trim() ?? "";
  }

  if (!anonKey) {
    throw new Error("PUBLIC_SUPABASE_ANON_KEY not found in .env — needed for sandbox.");
  }

  return [
    `PUBLIC_SUPABASE_URL=http://${kongHost}:8000`,
    `PUBLIC_SUPABASE_ANON_KEY=${anonKey}`,
  ].join("\n") + "\n";
}

// ─── Auth ────────────────────────────────────────────────────────────────────

function ensureAuth() {
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
    const closedNumbers = new Set<number>();
    try {
      const closedRaw = gh(
        `api repos/${config.repo}/issues/${prdNumber}/sub_issues --jq "[.[] | select(.state == \\"closed\\") | .number]"`
      );
      for (const n of JSON.parse(closedRaw || "[]")) closedNumbers.add(n);
    } catch { /* noop */ }

    const unblocked: SubIssue[] = [];
    const blocked: SubIssue[] = [];

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

  // Check for unblocked tasks before expensive setup
  const closedNumbers = new Set<number>();
  try {
    const closedRaw = gh(
      `api repos/${config.repo}/issues/${prdNumber}/sub_issues --jq "[.[] | select(.state == \\"closed\\") | .number]"`
    );
    for (const n of JSON.parse(closedRaw || "[]")) closedNumbers.add(n);
  } catch { /* noop */ }

  if (!nextUnblocked(allIssues, closedNumbers)) {
    log(`No unblocked '${config.agentLabel}' tasks — all blocked by open dependencies. Halting.`);
    process.exit(1);
  }

  // ─── Host Setup: Start Supabase ────────────────────────────────────────────

  if (config.hostSetup) {
    log(`Host setup: ${config.hostSetup}`);
    execSync(config.hostSetup, { stdio: "inherit" });
  }

  // ─── Detect Supabase Network & Build Sandbox Env ───────────────────────────

  const supabaseNetwork = detectSupabaseNetwork();
  log(`Supabase Docker network: ${supabaseNetwork}`);

  const suffix = supabaseNetwork.replace("supabase_network_", "");
  const dbUrl = `postgresql://postgres:postgres@supabase_db_${suffix}:5432/postgres`;
  const sandboxEnvContent = buildSandboxEnv(supabaseNetwork);

  // ─── Branch & Sandbox Lifecycle ────────────────────────────────────────────

  const branch = `feature/prd-${prdNumber}`;
  log(`Target branch: ${branch}`);

  await using sandbox = await createSandbox({
    branch,
    sandbox: docker({
      imageName: "kiro-runner",
      network: supabaseNetwork,
      env: {
        KIRO_API_KEY: process.env.KIRO_API_KEY!,
        DATABASE_URL: dbUrl,
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

  log("Sandbox ready (attached to Supabase network).");

  // Write sandbox .env with container hostnames
  const b64Env = Buffer.from(sandboxEnvContent).toString("base64");
  await sandbox.exec(`echo ${b64Env} | base64 -d > .env`, {
    cwd: "/home/agent/workspace",
  });
  log("Wrote sandbox .env (Kong container hostname).");

  const logsDir = resolve(".sandcastle", "logs");
  mkdirSync(logsDir, { recursive: true });

  // ─── Task Loop ─────────────────────────────────────────────────────────────

  const done = new Set<number>(closedNumbers);
  const completedTasks: SubIssue[] = [];
  let task: SubIssue | undefined;

  while ((task = nextUnblocked(allIssues, done))) {
    const taskStart = Date.now();

    // Host-side: reset DB + reinstall deps before each task
    log(`[task #${task.number}] host reset: ${config.hostReset}`);
    execSync(config.hostReset, { stdio: "inherit" });

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
    const postImpl = await runChecks(sandbox);

    let reviewerContext: string;
    if (postImpl.passed) {
      reviewerContext = "All checks passed. Review for code quality.";
    } else {
      reviewerContext = `Implementer checks FAILED:\n${postImpl.output.slice(-2000)}`;
    }

    // Single reviewer pass — fail = hard fail
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

    // Post-reviewer checks
    log(`[task #${task.number}] post-review checks...`);
    const postReview = await runChecks(sandbox);

    if (!postReview.passed) {
      const tail = postReview.output.split("\n").slice(-30).join("\n");
      throw new Error(`[task #${task.number}] FAILED post-review checks:\n${tail}`);
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

  log(`✓ ${completedTasks.length} tasks completed.`);

  // Soft e2e nudge — one comment per PR, not a merge gate, not nightly.
  postE2eNudge(branch, prdNumber);
}

// ─── Verification ────────────────────────────────────────────────────────────

interface CheckResult {
  passed: boolean;
  output: string;
}

async function runChecks(sandbox: {
  exec: (cmd: string, opts?: { cwd?: string; onLine?: (line: string) => void }) => Promise<{ stdout: string; stderr: string; exitCode: number }>;
}): Promise<CheckResult> {
  // Fastest-fail ordering: typecheck (cheapest gate) → testVite (no DB
  // needed, so a failure here skips paying for an expensive DB reset) →
  // resetDb (bail hard on non-zero — DB/e2e checks would run against stale
  // schema otherwise) → testDb.
  const typeResult = await sandbox.exec(config.typeCheck, {
    cwd: "/home/agent/workspace",
    onLine: liveStream("check"),
  });
  if (typeResult.exitCode !== 0) {
    return { passed: false, output: `TYPE-CHECK FAILED:\n${typeResult.stdout}\n${typeResult.stderr}` };
  }

  const viteResult = await sandbox.exec(config.testVite, {
    cwd: "/home/agent/workspace",
    onLine: liveStream("test:vite"),
  });
  if (viteResult.exitCode !== 0) {
    return { passed: false, output: `VITEST FAILED:\n${viteResult.stdout}\n${viteResult.stderr}` };
  }

  const resetResult = await sandbox.exec(config.resetDb, {
    cwd: "/home/agent/workspace",
    onLine: liveStream("db:reset"),
  });
  if (resetResult.exitCode !== 0) {
    return { passed: false, output: `DB RESET FAILED:\n${resetResult.stdout}\n${resetResult.stderr}` };
  }

  const dbResult = await sandbox.exec(config.testDb, {
    cwd: "/home/agent/workspace",
    onLine: liveStream("test:db"),
  });
  if (dbResult.exitCode !== 0) {
    return { passed: false, output: `DB TEST FAILED:\n${dbResult.stdout}\n${dbResult.stderr}` };
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
    const existingBody = gh(`pr view ${prNumber} --json body --jq ".body"`);
    const updatedBody = existingBody + "\n" + entry;
    ghStdin(`pr edit ${prNumber} --body-file -`, updatedBody);
    log(`PR #${prNumber} updated with #${closedIssue.number}.`);
  } else {
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

// ─── E2E PR Nudge ────────────────────────────────────────────────────────────

/**
 * Soft, one-time nudge posted after the task loop completes: reminds a human
 * to run the Playwright smoke layer before merge. NOT a merge gate, NOT
 * nightly — e2e never runs in the agent loop (#58/#59). Keyed to the PR
 * number so it's posted at most once per PR per invocation.
 */
function postE2eNudge(branch: string, prd: number) {
  const prNumber = gh(`pr list --head ${branch} --json number --jq ".[0].number"`);
  if (!prNumber) {
    log("No PR found for e2e nudge — skipping.");
    return;
  }
  const comment = `Agent loop complete for PRD #${prd}. Please run \`${config.testE2e}\` locally before merging (human smoke layer — not run in the agent loop).`;
  gh(`pr comment ${prNumber} --body ${JSON.stringify(comment)}`);
  log(`Posted e2e nudge on PR #${prNumber}.`);
}

// ─── Prompt Builders ─────────────────────────────────────────────────────────

function buildImplementerPrompt(task: SubIssue, designPath?: string): string {
  let prompt = `Implement the following task.\n\n`;
  prompt += `## Task #${task.number}: ${task.title}\n\n${task.body}\n\n`;
  prompt += `## Environment\n`;
  prompt += `You are running inside a sandbox with full access to the Supabase database and services.\n`;
  prompt += `Do NOT check for Docker or Supabase availability — they are pre-configured.\n`;
  prompt += `DATABASE_URL is set in the environment — use it directly (no need to export).\n\n`;
  prompt += `## Running tests\n`;
  prompt += `The orchestrator runs the FULL test suite (unit + DB + type-check) as a guard after you finish. Do NOT run the whole suite yourself — it is slow and redundant. Run ONLY the tests covering the files you changed (substitute <file> with a real path):\n`;
  prompt += `- Unit/component: ${scopedTests.vite}   e.g. ${config.testVite} src/routes/checks/page.svelte.spec.ts\n`;
  prompt += `- Database: ${scopedTests.db.replace("<file>", "<your-test>.sql")}\n`;
  prompt += `- Type-check (whole-project, run only if you changed types/interfaces): ${config.typeCheck}\n`;
  prompt += `\nYou may author Playwright e2e specs under e2e/ when a flow genuinely needs a real browser + stack (auth redirect, Storage, RBAC surface) and jsdom/SSR/pgTAP cannot prove it — but do NOT run \`${config.testE2e}\` yourself; a human runs the smoke layer separately.\n`;
  prompt += `\nIMPORTANT: The database tests run against a live shared database and do NOT auto-apply migrations. If you add or edit any migration, run the DB reset command (${config.resetDb}) BEFORE running the database tests, otherwise your new schema/policies/functions will be missing and tests will fail misleadingly.\n`;
  if (designPath) prompt += `\n## Design context\nRead ${designPath} for architectural decisions.\n`;
  return prompt;
}

function buildReviewerPrompt(task: SubIssue, context: string, designPath?: string): string {
  let prompt = `Review the implementation of the following task.\n\n`;
  prompt += `## Task #${task.number}: ${task.title}\n\n${task.body}\n\n`;
  prompt += `## Context\n${context}\n\n`;
  prompt += `## Environment\n`;
  prompt += `You are running inside a sandbox with full access to the Supabase database and services.\n`;
  prompt += `Do NOT check for Docker or Supabase availability — they are pre-configured.\n`;
  prompt += `DATABASE_URL is set in the environment — use it directly (no need to export).\n\n`;
  prompt += `## Running tests\n`;
  prompt += `The orchestrator runs the FULL test suite (unit + DB + type-check) as a guard after you finish. Do NOT run the whole suite yourself — it is slow and redundant. After any fixes, run ONLY the tests covering the files you touched (substitute <file> with a real path):\n`;
  prompt += `- Unit/component: ${scopedTests.vite}   e.g. ${config.testVite} src/routes/checks/page.svelte.spec.ts\n`;
  prompt += `- Database: ${scopedTests.db.replace("<file>", "<your-test>.sql")}\n`;
  prompt += `- Type-check (whole-project, run only if you changed types/interfaces): ${config.typeCheck}\n`;
  prompt += `\nDo NOT run \`${config.testE2e}\` — a human runs the e2e smoke layer separately.\n`;
  prompt += `\nIMPORTANT: The database tests run against a live shared database and do NOT auto-apply migrations. If a fix adds or edits any migration, run the DB reset command (${config.resetDb}) BEFORE running the database tests.\n`;
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
