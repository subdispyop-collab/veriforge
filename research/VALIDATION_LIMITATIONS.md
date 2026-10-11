# Validation limitations

## What each layer covers

| Layer | Protects against | Does not protect against |
| --- | --- | --- |
| Independent parser | A second reading of `+ - *`, literals, and rejected syntax | A shared mis-specification of the grammar |
| Independent evaluator | Concrete counterexamples and disagreement with the production evaluator on tested assignments | A bug both implementations copied from the same arithmetic idea |
| Polynomial oracle | Equivalence and inequivalence over all integers, inside the term budget | Mode B functional equivalence when polynomials differ but wraparound agrees; expressions over the term budget |
| Exhaustive oracle | Every assignment in a finite domain that fits the budget | Domains above 65,536; Mode A |
| Production Z3 | Equivalence in the encoded model, when installed and UNSAT | Encoder bugs that make unequal expressions look equal; solver bugs |
| Counterexample check | A SAT model that does not actually differ | False UNSAT |
| Testing baseline | Bugs hit by the boundary pool or the random draw | Bugs outside the sample; it is not a proof when it fails to distinguish |
| Ten mutants | The listed faults on the listed fixtures | Faults nobody seeded; survival outside those fixtures |
| Rule baseline | Only the four identity rewrites, syntactically | Every other equivalent pair; it abstains |

Checking one counterexample does not prove equivalence. UNSAT, polynomial identity, or a finished exhaustive domain does, and only inside that model.

The same solver was not used twice in the scored run because Z3 was absent. Sharing Z3 would still be a shared risk.

Unsigned Mode B and mathematical integers are different. Sixteen source pairs in the mode-trap table differ across modes. That is the expected modular-arithmetic behavior, not a universal bug.

Complete independence, complete security, and universal correctness are not claimed.
