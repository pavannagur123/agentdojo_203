# BASIL-Gate design

BASIL means **Budget-Aware Scoped Intent Ledger**. It is the PE6203 project's custom approval policy, not an upstream AgentDojo feature. It intercepts every valid tool call immediately before execution and returns one of the three decisions required by the brief: approve, deny, or escalate.

## Why it exists

Upstream AgentDojo executes a syntactically valid tool call as soon as an agent proposes it. This is useful for benchmarking agents, but it does not answer whether the user authorized the resulting side effect. BASIL treats the language model as a planner rather than as the final authority.

The policy adapts established ideas—least authority, provenance, effect classification, and human review—to AgentDojo's per-task escalation budget. Its project-specific mechanism is an evidence ledger: each decision records which trusted request clause authorized the effect, where the arguments came from, the risk classification, reviewer use, and the final outcome.

## Decision flow

1. Compile the original user request into an immutable authorization contract.
2. Classify the proposed tool as read, write, delete, communication, financial, permission-changing, authentication-related, or external.
3. Label every argument as originating from the user, prior tool output, or the agent.
4. Apply the selected policy:
   - `full-approve`: approve every valid call (baseline).
   - `full-escalate`: escalate every valid call (baseline).
   - `basil`: apply the scoped-intent rules below.
5. If escalation is requested and budget remains, ask the configured reviewer.
6. If the budget is exhausted, deny the call. This is a fail-closed decision.
7. Append the complete decision to the task ledger and either execute or return a blocked tool result to the agent.

Nested function calls embedded in arguments are checked before their parent call, preventing that path from bypassing the gate.

## Current BASIL rules

- Read-only discovery is automatically approved because it cannot directly change the simulated environment.
- A side effect without a matching affirmative action in the original request is automatically denied.
- An action conflicting with an explicit negative request clause is automatically denied.
- A directly authorized, medium-risk side effect with bounded arguments is automatically approved.
- High/critical-risk actions, weak authorization matches, and side-effect arguments derived from untrusted tool output are escalated.
- Any escalation after the task's budget `k` is exhausted becomes an automatic denial.

These rules are deterministic and inspectable. They can be revised after experiments reveal over-permissive or over-conservative cases.

## Reviewers

The deterministic reviewer exists for development, unit testing, and reproducible smoke tests. It is not the final experimental human simulation.

The `openai-compatible` reviewer is the assignment-facing simulated human. It receives only information a realistic reviewer could receive: the original request, request clauses, proposed tool and arguments, provenance labels, effects, risk, and policy reason. It is not given injection labels, expected task results, benchmark ground truth, or other oracle information.

## Decision evidence

Each AgentDojo JSON trace gains a `basil` object containing:

- selected policy and reviewer;
- escalation budget and number used;
- compiled request contract;
- ordered tool-call decisions;
- argument provenance and tool effects;
- policy and final decisions;
- reasons and matching request clauses; and
- reviewer token counts and cost field.

This makes individual trajectories suitable for the report's failure analysis.

