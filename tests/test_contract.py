from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import contract  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FixtureRunner:
    def __init__(self) -> None:
        self.execution = load_fixture("execution_issue.json")
        self.goal = load_fixture("goal_issue.json")
        self.relation = load_fixture("native_parent.json")
        self.calls: list[dict[str, Any]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": list(argv), **kwargs})
        if argv[:3] == ["gh", "issue", "view"]:
            number = int(argv[3])
            payload = self.execution if number == 4 else self.goal if number == 1 else None
            if payload is None:
                return subprocess.CompletedProcess(argv, 1, "", "fixture Issue not found")
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")
        if argv[:3] == ["gh", "api", "graphql"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps(self.relation), "")
        if argv[:4] == ["gh", "api", "--method", "POST"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                json.dumps({"html_url": "https://github.com/zaurakworks/agent-contracts/issues/4#issuecomment-1"}),
                "",
            )
        return subprocess.CompletedProcess(argv, 1, "", "unexpected fixture command")


def receipt_for(package: dict[str, Any]) -> dict[str, Any]:
    source = package["source"]
    return {
        "schemaVersion": "1.0",
        "kind": "receipt",
        "receiptId": "receipt-agent-contracts-issue-loop-001",
        "contract": {
            "contractId": package["contractId"],
            "revision": package["revision"],
            "contractRef": package["contractRef"],
            "issueUrl": source["issueUrl"],
            "issueNumber": source["issueNumber"],
            "remoteVersion": source["remoteVersion"],
            "contentDigest": source["contentDigest"],
        },
        "outcome": "delivered",
        "summary": "Delivered the bounded execution loop for review.",
        "artifacts": [
            {
                "name": "Draft pull request",
                "url": "https://github.com/zaurakworks/agent-contracts/pull/5",
                "commit": "0123456789abcdef0123456789abcdef01234567",
            }
        ],
        "verification": [
            {"command": "python tools/validate.py", "result": "Parent validation pending."}
        ],
        "globalWrites": [],
        "remainingUnknowns": ["Maintainer acceptance is pending."],
        "submittedAt": "2026-08-16T15:00:00Z",
    }


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = FixtureRunner()
        self.client = contract.GhClient(self.runner)

    def capture(self) -> dict[str, Any]:
        return contract.capture(
            "https://github.com/zaurakworks/agent-contracts/issues/4", self.client
        )

    def test_valid_capture_uses_exact_snapshot_and_native_parent(self) -> None:
        package = self.capture()
        self.assertEqual(package["kind"], "execution-contract")
        self.assertEqual(package["contractRef"], "exec-agent-contracts-issue-loop-001@1")
        self.assertEqual(package["source"]["issueNumber"], 4)
        self.assertEqual(package["source"]["remoteVersion"], "2026-08-16T14:49:09Z")
        self.assertEqual(
            package["source"]["contentDigest"],
            contract.content_digest(self.runner.execution["body"]),
        )
        self.assertEqual(
            package["parentGoal"],
            {
                "contractId": "goal-agent-contracts-001",
                "relationship": "github-sub-issue",
                "issueUrl": "https://github.com/zaurakworks/agent-contracts/issues/1",
            },
        )
        self.assertTrue(all(isinstance(call["argv"], list) for call in self.runner.calls))

    def test_parent_mismatch_is_rejected(self) -> None:
        parent = self.runner.relation["data"]["repository"]["issue"]["parent"]
        parent["number"] = 9
        parent["url"] = "https://github.com/zaurakworks/agent-contracts/issues/9"
        with self.assertRaisesRegex(contract.ContractError, "native GitHub parent"):
            self.capture()

    def test_malformed_issue_form_is_rejected(self) -> None:
        self.runner.execution["body"] = self.runner.execution["body"].replace(
            "### 停止条件", "### 意外段落", 1
        )
        with self.assertRaisesRegex(contract.ContractError, "unsupported Issue Form section"):
            self.capture()

    def test_obsolete_english_heading_is_rejected(self) -> None:
        self.runner.execution["body"] = self.runner.execution["body"].replace(
            "### 当前目标", "### Current objective", 1
        )
        with self.assertRaisesRegex(contract.ContractError, "unsupported Issue Form section"):
            self.capture()

    def test_stale_source_is_rejected_before_render(self) -> None:
        package = self.capture()
        receipt = receipt_for(package)
        self.runner.execution["updatedAt"] = "2026-08-16T14:50:09Z"
        with self.assertRaisesRegex(contract.ContractError, "drifted"):
            contract.render_receipt(receipt, package, self.client)
        self.assertFalse(any(call["argv"][:4] == ["gh", "api", "--method", "POST"] for call in self.runner.calls))

    def test_wrong_receipt_binding_is_rejected(self) -> None:
        package = self.capture()
        receipt = receipt_for(package)
        receipt["contract"]["contentDigest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(contract.ContractError, "does not equal"):
            contract.validate_receipt(receipt, package)

    def test_dry_run_renders_without_posting(self) -> None:
        package = self.capture()
        receipt = receipt_for(package)
        rendered, result = contract.post_receipt(
            receipt, package, self.client, dry_run=True
        )
        self.assertIsNone(result)
        self.assertIn("Machine-readable Receipt JSON", rendered)
        self.assertIn("does not accept the work, close the Issue", rendered)
        self.assertFalse(any(call["argv"][:4] == ["gh", "api", "--method", "POST"] for call in self.runner.calls))

    def test_post_uses_captured_issue_and_json_stdin(self) -> None:
        package = self.capture()
        receipt = receipt_for(package)
        rendered, result = contract.post_receipt(receipt, package, self.client)
        self.assertEqual(
            self.runner.calls[-1]["argv"],
            [
                "gh",
                "api",
                "--method",
                "POST",
                "repos/zaurakworks/agent-contracts/issues/4/comments",
                "--input",
                "-",
            ],
        )
        submitted = json.loads(self.runner.calls[-1]["input"])
        self.assertEqual(submitted, {"body": rendered})
        self.assertNotIn("state", submitted)
        self.assertIn("#issuecomment-1", result["html_url"])

    def test_current_goal_issue_form_capture(self) -> None:
        goal = copy.deepcopy(self.runner.goal)
        goal["number"] = 6
        goal["url"] = "https://github.com/zaurakworks/agent-contracts/issues/6"
        goal["body"] = """### 合同 ID

goal-example-001

### 目标

把长期合同权威保留在 GitHub。

### 成功标准

- 新执行可以从 Goal 恢复工作。

### 权威与引用

- https://github.com/zaurakworks/agent-contracts/issues/6 —— 当前 Goal。

### 允许的动作与写入

- 在获准分支写入本仓。

### 禁止的动作与写入

- 修改用户级配置。

### 依赖

None

### 交付物

- 一份经过评审的合同产物。

### 停止条件

- 权威意外变化。

### 当前负责人动作

维护者评审下一份边界明确的 Execution Contract。"""
        package = contract.capture_goal(goal)
        self.assertEqual(package["kind"], "goal")
        self.assertEqual(package["dependencies"], [])
        self.assertEqual(
            package["ownerAction"],
            "维护者评审下一份边界明确的 Execution Contract。",
        )


if __name__ == "__main__":
    unittest.main()
