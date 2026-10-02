# Vitest/React Test Remediation

You are repairing an existing Vitest + React Testing Library test suite.

The objective is to increase **regression protection**, not test count or code coverage.

Follow the repository's `AGENTS.md` test-quality rules.

---

## Input

You will receive an audit describing tests that may be weak, vacuous, misleading, broken, obsolete, or duplicated.

Treat the audit as evidence, not unquestionable truth.

Before modifying a test, inspect the relevant production code.

---

## For Each Test

Follow this process:

### 1. Understand the behavior

Determine exactly what behavior the test is supposed to protect.

Do not rely solely on the test name or audit description.

### 2. Identify the contract

Determine the most appropriate observable contract:

- rendered UI;
- accessible state;
- user-visible result;
- application state;
- navigation;
- network boundary;
- persistence boundary;
- meaningful dependency interaction.

### 3. Construct the regression

Identify a plausible implementation mistake that should cause the test to fail.

Example:

> If the delete handler becomes a no-op, this test should fail.

### 4. Choose the verification level

Prefer the highest-level meaningful verification.

Generally:

UI behavior
→ application behavior
→ external boundary
→ implementation detail

Do not test implementation details when the same behavior can be verified through the UI.

### 5. Repair conservatively

If the existing test already provides sufficient protection, leave it unchanged.

If it is weak, improve it.

If it is vacuous or misleading, rewrite it.

If the behavior is obsolete or the test has no meaningful contract, delete it.

If you cannot determine the intended behavior, do not invent one. Mark it for review.

---

## Assertions

Every repaired test must contain assertions that establish its intended behavior.

However:

**Do not add assertions merely to satisfy this requirement.**

Bad repair:

```ts
handler(row);

expect(handler).toHaveBeenCalled();
```

If the handler itself was the code being executed, this proves little.

Good repair:

```ts
await user.click(
  screen.getByRole('button', { name: /delete/i })
);

expect(screen.getByRole('dialog')).toBeVisible();
```

when opening the dialog is the actual behavior.

---

## Mock Assertions

Do not replace behavioral assertions with mock assertions.

If a mock is the appropriate boundary, verify meaningful arguments and effects.

Prefer:

```ts
expect(deleteHelp).toHaveBeenCalledWith('help-123');
```

over:

```ts
expect(deleteHelp).toHaveBeenCalled();
```

unless the fact that the dependency was called, independent of arguments, is itself the contract.

---

## Direct Handler Calls

Replace direct event-handler invocation with user interaction when practical.

Before:

```ts
table.getAction('button.delete')!.handler!(row);
```

Prefer:

```ts
await user.click(
  screen.getByRole('button', { name: /delete/i })
);
```

Then verify the resulting behavior.

Do not replace a direct invocation blindly if the table abstraction itself is what the test legitimately needs to verify.

---

## Deleting Tests

Deleting a test is allowed and encouraged when:

- it is vacuous;
- it is obsolete;
- it duplicates stronger coverage;
- it tests an implementation detail with no meaningful contract;
- the supposed behavior no longer exists.

Do not preserve a test merely because deleting it reduces test count or coverage.

---

## Production Code

Do not modify production code to make a test easier.

If production behavior appears difficult to test, first attempt to test the existing public/user-facing behavior.

If production refactoring appears genuinely necessary, stop and report it for separate review.

---

## Verification

After repairing a test:

1. Run the test.
2. Run the relevant test file.
3. If practical, run related tests.
4. Review the diff.
5. Verify that the test would fail if the protected behavior were removed.

Do not consider a test repaired merely because it passes.

---

## No False Confidence

Never:

- add `expect(true).toBe(true)`;
- assert only that a mock was called when the outcome matters;
- add snapshots to avoid determining the correct assertion;
- assert internal state merely because it is convenient;
- weaken existing assertions;
- remove meaningful assertions;
- invent expected behavior;
- modify production code solely for test convenience.

When uncertain, leave the test unchanged and mark it for human review.

---

## Final Report

For every modified test report:

- original classification;
- final action;
- behavior protected;
- regression it now catches;
- files changed;
- test command used;
- whether the test passed.

Also report:

- tests deleted;
- tests rewritten;
- tests improved;
- tests left unchanged;
- tests requiring human review.