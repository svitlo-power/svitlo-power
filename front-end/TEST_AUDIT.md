# Vitest/React Test Quality Audit

You are auditing an existing Vitest + React Testing Library test suite.

Your job is to assess whether tests provide genuine regression protection.

**You are performing an audit, not a remediation.**

Do not modify any files.

Do not add assertions.

Do not rewrite tests.

Do not modify production code.

---

## Primary Question

For every test, determine:

> What specific regression would this test catch?

Then determine:

> Would the test actually fail if that regression occurred?

A test is valuable only if it provides meaningful evidence about behavior.

---

## Required Investigation

For each suspicious test:

1. Read the complete test.
2. Read relevant setup and helper functions.
3. Read the production implementation necessary to understand the behavior.
4. Follow relevant callbacks, handlers, mocks, and state transitions.
5. Identify what behavior the test claims to verify.
6. Identify what the test actually verifies.
7. Construct at least one plausible regression.
8. Determine whether the test would fail under that regression.

Do not infer behavior solely from the test name.

---

## Identify Vacuous Tests

Flag a test as `vacuous` when it primarily:

- renders something without verifying meaningful output;
- calls a function without verifying the result;
- invokes an event handler without checking the consequence;
- awaits an operation without checking the eventual state;
- advances timers without checking what changed;
- creates mocks without meaningful verification;
- verifies only that code did not throw when throwing is not the behavior under test.

Example:

```ts
it('exercises onDeleteClick', () => {
  renderPage();

  table.getAction('button.delete')!.handler!(row);
});
```

This is not meaningful merely because it executes the handler.

---

## Identify Misleading Tests

A test is `misleading` when its name or apparent intent claims to verify behavior that the assertions do not establish.

Example:

```ts
it('opens the delete dialog', () => {
  clickDelete();

  expect(true).toBe(true);
});
```

The test name claims a behavioral guarantee that the body does not establish.

---

## Evaluate Assertions

Do not equate the presence of `expect()` with test quality.

Evaluate whether the assertion establishes the intended behavior.

Weak:

```ts
expect(mock).toHaveBeenCalled();
```

Potentially meaningful:

```ts
expect(mock).toHaveBeenCalledWith('help-123');
```

More meaningful when applicable:

```ts
expect(screen.getByRole('dialog')).toBeVisible();
```

Determine which level is appropriate from the production behavior.

---

## React Testing Library

Prefer tests that exercise behavior through the user-facing interface.

Flag direct handler invocation for review when the same behavior can reasonably be exercised using:

- `userEvent`;
- accessible roles;
- labels;
- visible text;
- rendered state.

Do not automatically classify direct handler tests as bad.

Determine whether direct invocation is actually testing a legitimate abstraction.

---

## Mock Analysis

For every important mock assertion, ask:

> What behavior does this assertion prove?

Do not automatically reject mock assertions.

A mock assertion can be valid when interaction with an external boundary is the intended contract.

However, flag assertions that merely establish that execution reached a line of code.

---

## Counterfactual Requirement

For every `weak`, `vacuous`, `misleading`, `broken`, `obsolete`, or `duplicate` test, provide a concrete explanation.

Prefer:

> "If `onDeleteClick` became a no-op, this test would still pass."

Avoid:

> "This test has poor coverage."

The first describes an actual failure of regression protection.

---

## Classification

Use exactly one primary classification:

- `strong`
- `acceptable`
- `weak`
- `vacuous`
- `misleading`
- `duplicate`
- `obsolete`
- `broken`
- `unknown`

Use `unknown` when the available code does not provide enough information.

Do not guess.

---

## Recommended Action

For every non-strong test, recommend exactly one:

- `keep`
- `improve`
- `rewrite`
- `delete`
- `review`

Do not recommend `rewrite` unless you can describe what behavior should be verified.

Do not recommend adding assertions merely because assertions are missing.

---

## Output

Produce the audit in the repository's configured audit format.

For every flagged test include:

- file;
- line;
- test name;
- classification;
- confidence;
- behavior claimed;
- behavior actually verified;
- concrete regression not caught;
- recommended action;
- proposed verification strategy;
- relevant production files;
- concise reason.

Do not modify the repository.

At the end, provide aggregate counts and identify the five most common quality problems found.