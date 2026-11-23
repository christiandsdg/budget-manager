# AI Disclosure

I acknowledge the use of [Claude (Anthropic), model Claude Opus 5.5](https://claude.ai) to explain Python concepts and to generate most of the implementation of this budget manager: all five modules in `src/budget_manager/` (`models.py`, `validation.py`, `services.py`, `storage.py`, `cli.py`), the fixes to `pyproject.toml`, and a draft of this disclosure. Claude worked directly in my project folder, tested the code, and committed each change. Every AI-made commit carries a `Co-Authored-By: Claude` line, so its contributions can be seen in `git log`.

The prompts used include:

- "When you create a class, how do you specify the data types?" and "Why are you using frozenset?"
- "Help me create the repo and I'll have you do it."
- "Do not add the `__init__.py` because it's not in the requested architecture."
- Answers to Claude's design questions: reject unknown categories, accept any valid ISO currency, store amounts as `Decimal` with at most 2 decimal places, generate IDs automatically (T001, T002, …)
- "Just remember the scope from the slides. Do only what's necessary, while implementing validation."
- "Give me the error before I reach the end of creating the transaction."
- "The report menu looks strange. Make it look better."
- "Help me push to git."
- "Write the AI disclosure for me."

The output of these prompts was used to build Release 1 of the application. I set up the project with uv, decided the business rules and the scope listed above, asked for changes where the result didn't match what I wanted (removing filtering as out of scope, checking each field as it is typed, a clearer report layout), and agreed to the policy of refusing a data file with invalid rows rather than partly loading it. I ran the application on my machine (add, list, report, restart and reload) and tried invalid inputs to confirm they are rejected with clear messages. The generated code is kept as Claude wrote it, apart from the changes I requested.
