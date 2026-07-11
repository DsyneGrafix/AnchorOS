ANCHORCORE_DESIGN_LAWS.md

Platform Doctrine
-----------------

✅ Rule of Reuse

Can this capability be reused by another application?

If yes...

Move it to AnchorCore.

✅ Platform Before Product

Has this capability been considered for the platform first?

✅ Framework Before Workflow

Does this belong in a framework or in the platform?

✅ Event Before Coupling

Can this interaction occur through the Event Bus instead of a direct dependency?

✅ Discover → Verify → Register → Operate

Does this component satisfy the platform contract?


Runtime Doctrine
----------------
Execution must never outlive the conditions that justified it.
