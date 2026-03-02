#!/bin/bash

# Fix dashboard_aggregator.py repo_meta None checks
sed -i '' 's/f"CI\/CD enabled: {best_team\.repo_meta\.has_ci}"/f"CI\/CD enabled: {best_team.repo_meta.has_ci if best_team.repo_meta else False}"/g' src/analysis/dashboard_aggregator.py
sed -i '' 's/f"Workflow success rate: {best_team\.repo_meta\.workflow_success_rate:.1%}"/f"Workflow success rate: {best_team.repo_meta.workflow_success_rate:.1% if best_team.repo_meta else 0.0:.1%}"/g' src/analysis/dashboard_aggregator.py
sed -i '' 's/f"Total workflow runs: {best_team\.repo_meta\.workflow_run_count}"/f"Total workflow runs: {best_team.repo_meta.workflow_run_count if best_team.repo_meta else 0}"/g' src/analysis/dashboard_aggregator.py

# Fix models/test_execution.py - add type: ignore
sed -i '' 's/@property$/@property  # type: ignore[prop-decorator]/g' src/models/test_execution.py

# Fix agents/base.py - cast config to dict
sed -i '' 's/config: dict\[str, Any\] = AGENT_CONFIGS\.get(agent_name, {})/config = AGENT_CONFIGS.get(agent_name, {})\n        if not isinstance(config, dict):\n            config = {}/g' src/agents/base.py

# Fix remaining orchestrator issues - remove unused type: ignore
sed -i '' '/for _agent_name, response in agent_responses\.items():  # type: ignore\[assignment\]/s/  # type: ignore\[assignment\]//g' src/analysis/orchestrator.py

echo "✅ All remaining fixes applied"
