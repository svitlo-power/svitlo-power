# Test Quality Guidelines

## Purpose

This repository uses Vitest and React Testing Library.

The purpose of tests is to provide reliable protection against regressions in externally observable behavior and important application contracts.

**Test count and code coverage are not quality goals by themselves.**

A smaller suite of meaningful tests is preferable to a large suite of tests that merely execute code.

---

## Core Principle

Every test must answer:

> What regression would this test catch?

If the answer is unclear, the test is probably not valuable.

A test is not meaningful merely because it:

- calls a function;
- renders a component;
- mounts a component;
- invokes an event handler;
- awaits a promise;
- advances timers;
- constructs an object;
- calls a mocked dependency;
- has one or more `expect()` statements.

The test must establish that the system produces the expected behavior.

---

## The Counterfactual Test

When evaluating or modifying a test, mentally introduce a plausible regression into the production code.

Ask:

> Would this test fail?

Examples:

### Good

```ts
await user.click(screen.getByRole('button', { name: /delete/i }));

expect(screen.getByRole('dialog')).toBeVisible();
```

If the delete button stopped opening the dialog, this test fails.

### Bad

```ts
await user.click(screen.getByRole('button', { name: /delete/i }));
```

Removing the click handler would not make this test fail.

### Weak

```ts
expect(openDialog).toHaveBeenCalled();
```

This may be insufficient if the important contract is *what* dialog was opened or *which item* was selected.

Prefer:

```ts
expect(openDialog).toHaveBeenCalledWith({
  id: 'delete-id',
  displayValue: 'Delete Help',
});
```

when those arguments represent the actual contract being tested.

---

# Test Validity

A test is considered **vacuous** when it executes behavior without verifying a meaningful outcome.

Examples include:

```ts
handler(input);
```

```ts
render(<Component />);
```

```ts
await service.doSomething();
```

```ts
vi.advanceTimersByTime(1000);
```

when none of these operations are followed by meaningful verification.

Do not repair such tests by adding arbitrary assertions.

Instead:

1. Determine the intended behavior.
2. Identify the observable outcome or contract.
3. Test that outcome.
4. If no meaningful behavior exists, delete the test.

---

# Assertions

Assertions must verify the behavior under test.

Prefer assertions in this order:

1. User-visible behavior.
2. Accessible DOM state.
3. Resulting application state.
4. Meaningful calls to external boundaries.
5. Internal implementation details only when they are themselves part of an important contract.

Prefer:

```ts
expect(screen.getByRole('alert')).toHaveTextContent('Help deleted');
```

over:

```ts
expect(deleteHelp).toHaveBeenCalled();
```

when the user-visible result is the important behavior.

For mocked functions, prefer checking meaningful arguments:

```ts
expect(deleteHelp).toHaveBeenCalledWith('help-123');
```

rather than:

```ts
expect(deleteHelp).toHaveBeenCalled();
```

Do not add assertions solely because a test currently has none.

---

# React Testing Library

Prefer testing the component as a user would interact with it.

Prefer:

```ts
screen.getByRole(...)
screen.getByLabelText(...)
screen.getByText(...)
screen.findByRole(...)
userEvent
```

Avoid implementation-oriented queries unless there is a specific reason:

```ts
container.querySelector(...)
wrapper.find(...)
component.instance(...)
```

Do not test React internals.

Do not test implementation details merely because they are easy to access.

---

# Event Handlers

Do not directly invoke component event handlers when the behavior can be exercised through the UI.

Prefer:

```ts
await user.click(
  screen.getByRole('button', { name: /delete/i })
);
```

over:

```ts
table.getAction('button.delete')!.handler!(row);
```

Direct invocation is acceptable when:

- the handler is genuinely exposed as a public contract;
- the abstraction itself is what is being tested;
- exercising the behavior through the UI is impossible or would obscure the contract.

Even then, verify the resulting behavior.

---

# Mocks

Mocks must not become the subject of the test unless the interaction with that dependency is itself important.

Avoid:

```ts
expect(mock).toHaveBeenCalled();
```

when this only proves that execution reached a line of code.

Prefer:

```ts
expect(mock).toHaveBeenCalledWith(expectedArguments);
```

or verify the resulting observable behavior.

Do not mock a dependency merely to make an assertion possible.

Do not introduce mocks that hide the behavior the test should actually verify.

---

# Async Behavior

Tests involving asynchronous behavior must verify the eventual result.

Bad:

```ts
await user.click(button);
```

Good:

```ts
await user.click(button);

expect(await screen.findByRole('alert')).toHaveTextContent(
  'Saved successfully'
);
```

Use appropriate Vitest/Testing Library async utilities.

Do not use arbitrary sleeps:

```ts
await new Promise(resolve => setTimeout(resolve, 100));
```

unless there is a very specific reason.

---

# Snapshots

Do not introduce snapshots as a replacement for meaningful assertions.

Snapshots may be appropriate for genuinely complex, stable serialized output, but they must not be used to make a weak test appear comprehensive.

A snapshot that merely records a large DOM tree without verifying meaningful behavior is not sufficient.

---

# Test Names

A test name must describe behavior, not implementation mechanics.

Prefer:

```ts
it('opens the delete confirmation dialog for the selected help item', ...)
```

over:

```ts
it('calls onDeleteClick', ...)
```

The body of the test must actually verify the behavior described by its name.

A test whose name claims behavior that the body does not verify is a **misleading test**.

---

# Existing Tests

When modifying an existing test:

- Preserve meaningful assertions.
- Do not weaken existing coverage.
- Do not replace behavioral assertions with mock assertions.
- Do not remove assertions simply to make a test easier to maintain.
- Do not modify production code merely to make a test easier to write.

If an existing test is fundamentally invalid, rewrite it around the intended behavior.

If the behavior is no longer relevant, delete the test.

---

# Test Duplication

Do not preserve tests solely because they increase test count.

Tests that exercise the same behavior under equivalent conditions should be consolidated when appropriate.

Do not deduplicate tests merely because they look similar.

Different boundary conditions, error cases, permissions, states, or user flows may justify separate tests.

---

# Coverage

Coverage metrics are diagnostic information, not proof of test quality.

Do not add tests solely to increase:

- line coverage;
- branch coverage;
- function coverage;
- statement coverage.

A test that executes a line without verifying its behavior provides little regression protection.

---

# Production Code

Do not modify production code solely to make a test easier to write.

If production code is difficult to test, first determine whether:

- the test is targeting the wrong abstraction;
- the behavior can be tested through the UI;
- an existing public boundary can be exercised;
- the production design genuinely needs refactoring.

Production changes require independent justification.

---

# Remediation Rules

When repairing a test, follow this sequence:

1. Read the test.
2. Read the production code relevant to the behavior.
3. Identify the intended behavior.
4. Identify the observable contract.
5. Determine what regression should cause the test to fail.
6. Determine whether the existing test catches that regression.
7. If yes, leave it unchanged.
8. If no, rewrite it to verify the contract.
9. If no meaningful contract exists, delete the test.
10. Run the test.
11. Review the resulting test for false confidence.

Never add a meaningless assertion just to satisfy a structural requirement.

---

# Required Quality Check

Before considering a test complete, explicitly answer:

> If the behavior described by this test were accidentally removed or changed, would this test fail?

If the answer is no, the test is not complete.

Also answer:

> What specific behavior does this test protect?

The answer must be concrete enough to explain to another engineer.

---

# Classification

During test audits, classify tests using:

- `strong` — meaningful regression protection;
- `acceptable` — useful but could be improved;
- `weak` — has verification but provides limited protection;
- `vacuous` — executes behavior without meaningful verification;
- `misleading` — test name/intent claims behavior that is not actually verified;
- `duplicate` — redundant with another test;
- `obsolete` — tests behavior that is no longer relevant;
- `broken` — does not correctly exercise the intended scenario;
- `unknown` — insufficient context to determine quality.

Do not classify a test as weak or vacuous solely because it uses mocks.

---

# Remediation Safety

Automated remediation must be conservative.

When uncertain:

- do not invent behavior;
- do not invent expected values;
- do not weaken assertions;
- do not change production code;
- mark the test `unknown` and request human review.

A false-positive repair is worse than leaving a questionable test untouched.