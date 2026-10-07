# claude-plugins

A [Claude Code](https://claude.com/claude-code) plugin marketplace.

## Plugins

- **[docs](docs/)** — bring a consistent `docs/` system to any project: scaffold the layout,
  add custom doc sections, file plan outcomes under the right doc, and keep doc statuses honest.
- **[jira](jira/)** — write Jira managers and engineers can both read: issues with a business-value summary and the
  business problem before the technical details, and reports posted as comments with a verdict panel, the facts
  behind it and the actions. ADF via REST.
- **[pr](pr/)** — shepherd your pull request to merge: fix failing GitHub Actions at the root cause, work through
  every review, rebase when the base runs ahead, and hand architectural and trade-off calls back to you as weighed
  options. And review a colleague's PR against its Jira task: preview numbered problems, post the ones you pick as one
  GitHub review, and re-review until they are fixed.

## Install

```
/plugin marketplace add valeriakononenko/claude-plugins
/plugin install docs@divergence082-plugins
/plugin install jira@divergence082-plugins
/plugin install pr@divergence082-plugins
```
