# Reminders

## Prompt Structure Reference

- Reddit post: https://www.reddit.com/r/PromptEngineering/comments/1t42u52/i_spent_6_months_testing_every_major_prompting/
- Title: "I spent 6 months testing every major prompting technique. Here's what actually works (and what's overhyped) - with real examples."
- Useful takeaways for Flockr/agent work:
  - Prefer explicit structure over loose chat prompts.
  - XML tags can be useful for separating role, task, inputs, constraints, and output format.
  - Use prompt chaining instead of large all-in-one prompts.
  - Include contrastive examples: one good output and one bad output.
  - For reasoning-heavy steps, scaffold the reasoning path instead of only saying "think step by step."

## Open Questions

- Could Flockr use a persistent remote shell or `tmux` instead of batch SSH for sticky execution?
- Would one `tmux` window per command or per loop item make failure handling simpler?
- Can shell chaining like `cmd1 && cmd2` replace the current sticky marker protocol, or do we still need explicit done markers?
- Should `if_fail_run=#true` mean "log and continue to next loop item," while default failure stops the current item and the whole run?
