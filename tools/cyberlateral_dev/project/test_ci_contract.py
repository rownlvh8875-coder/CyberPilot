"""Semantic checks for the dedicated offline workflow's execution boundary."""

import json
import unittest

import yaml
from v1_helpers import ROOT


class CiContractTests(unittest.TestCase):
    def workflow(self):
        path = ROOT.parents[1] / '.github/workflows/cyberlateral-dev.yaml'
        self.assertTrue(path.is_file(), 'Missing dedicated offline workflow')
        return yaml.load(path.read_text(), Loader=yaml.BaseLoader)

    def test_only_scoped_push_pr_and_explicit_manual_triggers(self):
        w = self.workflow()
        self.assertEqual(set(w['on']), {'push', 'pull_request', 'workflow_dispatch'})
        self.assertEqual(set(w['on']['push']['branches']), {'main', 'feature/cyberlateral-dev-offline-ci'})
        self.assertEqual(w['on']['pull_request']['branches'], ['main'])
        for event in ['push', 'pull_request']:
            self.assertEqual(set(w['on'][event]['paths']), {'tools/cyberlateral_dev/**', '.github/workflows/cyberlateral-dev.yaml', 'README.md'})

    def test_read_only_ubuntu_no_submodules_lfs_or_credentials(self):
        w = self.workflow()
        self.assertEqual(w['permissions'], {'contents': 'read'})
        self.assertEqual(set(w['jobs']), {'verify'})
        job = w['jobs']['verify']
        self.assertEqual(job['runs-on'], 'ubuntu-24.04')
        checkout = job['steps'][0]
        self.assertEqual(checkout['with'], {'submodules': 'false', 'lfs': 'false', 'persist-credentials': 'false'})
        for step in job['steps']:
            if 'uses' in step:
                _, ref = step['uses'].rsplit('@', 1)
                self.assertRegex(ref, r'^[0-9a-f]{40}$')

    def test_exact_pinned_bootstrap_and_single_safe_command(self):
        steps = self.workflow()['jobs']['verify']['steps']
        self.assertEqual(steps[1]['with']['python-version'], '3.12.13')
        self.assertEqual(steps[2]['with']['version'], '0.12.23')
        commands = [s['run'] for s in steps if 'run' in s]
        self.assertEqual(
            commands, ['uv run --project tools/cyberlateral_dev --locked python -B tools/cyberlateral_dev/dev.py verify --output tools/cyberlateral_dev/out/ci']
        )
        artifact = steps[-1]
        self.assertEqual(artifact['with']['path'], 'tools/cyberlateral_dev/out/ci')

    def test_action_pins_match_verified_commit_objects_not_annotated_tags(self):
        records = json.loads((ROOT / 'reference/ci_action_commits.json').read_bytes())['actions']
        uses = [step['uses'] for step in self.workflow()['jobs']['verify']['steps'] if 'uses' in step]
        self.assertEqual(len(uses), len(records))
        for value in uses:
            action, pin = value.rsplit('@', 1)
            self.assertEqual(pin, records[action]['commit_sha'], 'Action pin must be the verified commit, not a tag object')


if __name__ == '__main__':
    unittest.main()
