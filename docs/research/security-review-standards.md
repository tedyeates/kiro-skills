# Research: Security Review Standards for Code Review

Date: 2026-07-16
Question: What security standards should a PR review skill use?

## Findings

### OWASP Top 10 (2021/2025)

Awareness-level ranking of 10 critical web application risk categories. The 2021 list covers: Broken Access Control, Cryptographic Failures, Injection, Insecure Design, Security Misconfiguration, Vulnerable Components, Authentication Failures, Software/Data Integrity Failures, Logging Failures, SSRF. The 2025 RC elevates Supply Chain Failures (A03) and Mishandling of Exceptional Conditions (A10).

**Actionability for code review:** High at category level — each maps to reviewable code patterns (missing authz checks, unsanitized inputs, hardcoded secrets). However, it is a risk taxonomy, not a checklist. Too coarse-grained to drive line-level PR comments without decomposition into specific checks.

**Gaps:** Does not provide pass/fail verification requirements. No severity scoring per item.

Source: https://owasp.org/Top10/2021/

### OWASP ASVS (v5.0, May 2025)

~350 verification requirements across 17 chapters (Authentication, Session Management, Access Control, Input Validation, Cryptography, Error Handling, etc.). Three assurance levels: L1 (basic), L2 (standard), L3 (critical apps). L2+ explicitly requires source code access.

**Actionability for code review:** Very high. Requirements are written as testable assertions ("Verify that X"). Chapters V2-V7 (Auth, Sessions, Access Control, Validation, Crypto, Error Handling) map directly to code review checks. Each requirement has a CWE mapping.

**Gaps:** Large scope (~350 items) — needs filtering to items detectable in a diff (vs. architectural/deployment concerns). L1 items are pen-test oriented; L2/L3 are code-review oriented.

Source: https://owasp.org/www-project-application-security-verification-standard/

### CWE Top 25 (2024)

Data-driven ranking of 25 most dangerous software weaknesses by MITRE, scored from 31,770 CVE records. Top items for web apps: CWE-79 (XSS), CWE-89 (SQLi), CWE-352 (CSRF), CWE-22 (Path Traversal), CWE-862 (Missing Authorization), CWE-78 (OS Command Injection), CWE-434 (Unrestricted Upload), CWE-287 (Improper Authentication).

**Actionability for code review:** High. Each CWE defines the root-cause weakness pattern at code level. Directly maps to what a reviewer looks for in a diff. Provides severity signal via KEV (Known Exploited Vulnerabilities) overlap.

**Gaps:** Includes memory-safety issues (CWE-787, CWE-125, CWE-416) irrelevant to managed-language web apps (TypeScript/JS). Needs filtering by language context.

Source: https://cwe.mitre.org/top25/archive/2024/2024_cwe_top25.html

### SANS Top 25

The SANS Top 25 evolved into the CWE Top 25. The current authoritative list is published by MITRE; SANS branding persists but they are the same list. No separate SANS list exists as of 2024.

**Recommendation:** Use CWE Top 25 directly. SANS adds no separate value.

Source: https://www.sans.org/top25/, https://deepsource.com/glossary/sans-top-25

### Snyk Code Patterns

Snyk Code is a SAST tool using DeepCode AI. It detects vulnerability patterns in source without compilation: injection sinks, hardcoded secrets, insecure crypto, prototype pollution, path traversal. Patterns align with CWE IDs.

**Actionability for code review:** The *categories* Snyk checks for are useful as a checklist source, but Snyk itself is a tool, not a standard. Its value is validating that the checklist covers what automated scanners also catch.

**Gaps:** Proprietary rule set; not an open standard to reference.

Source: https://docs.snyk.io/scan-with-snyk/snyk-code

## Recommended Approach

**Use OWASP Top 10 as the risk framing layer** (maps findings to categories for severity). **Use ASVS L2 chapters V2–V8 as the verification backbone** (testable requirements). **Use CWE Top 25 (web-relevant subset) as the weakness taxonomy** for labeling each finding.

This gives: risk context (OWASP Top 10) → specific check (ASVS requirement) → root-cause label (CWE ID).

## Recommended Checklist

Static code review items suitable for PR comments, with severity:

### Critical
1. **Injection (CWE-79/89/78)** — Unsanitized user input reaching SQL, HTML, OS command, or template sinks
2. **Missing authorization (CWE-862)** — Endpoint/action lacks server-side permission check; missing RLS policies on Supabase tables
3. **Broken authentication (CWE-287)** — JWT signature not verified, token expiry not checked, auth bypass paths
4. **Hardcoded secrets (CWE-798)** — API keys, passwords, tokens in source code

### High
5. **CSRF (CWE-352)** — State-changing request without anti-CSRF token or SameSite cookie
6. **Path traversal (CWE-22)** — User input used in file paths without sanitization
7. **Unrestricted upload (CWE-434)** — No server-side MIME/size validation
8. **Insecure deserialization (CWE-502)** — Untrusted data passed to deserializer
9. **SSRF (CWE-918)** — User-controlled URL in server-side fetch without allowlist

### Medium
10. **Sensitive data exposure** — PII/tokens logged, verbose errors in production, missing encryption at rest
11. **Weak cryptography** — MD5/SHA-1 for security purposes, missing key rotation, hardcoded IVs
12. **Session mismanagement** — Missing HttpOnly/Secure flags, no session expiry, no token rotation on privilege change
13. **Overly permissive CORS** — `Access-Control-Allow-Origin: *` on authenticated endpoints
14. **Missing rate limiting** — Auth endpoints or expensive operations without throttling

### Low
15. **Debug/dead code** — Console.log of secrets, commented-out auth checks, TODO security notes
16. **Dependency risk** — Unpinned versions, known CVE in direct dependency, unused packages

## Summary

For a code-review skill posting PR comments: use OWASP Top 10 categories for framing severity, ASVS L2 (V2–V8) for specific verification requirements, and CWE IDs for precise weakness labeling. The CWE Top 25 (filtered to web-app-relevant items) provides the empirical prioritization layer. SANS Top 25 is redundant with CWE Top 25. Snyk patterns validate coverage but are not a citable standard.

## Open Questions

- Should the skill reference OWASP Top 10 **2021** or the **2025 RC** (which restructures categories)?
- How many ASVS requirements to embed directly vs. link to? Full L2 is ~200 items — needs curated subset.
- Should severity levels (Critical/High/Medium/Low) map to GitHub review comment types (REQUEST_CHANGES vs. COMMENT)?
- Whether to include framework-specific checks (e.g., Supabase RLS, SvelteKit `+server.ts` auth guards) as an addendum or inline.
