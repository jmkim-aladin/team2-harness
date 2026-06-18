from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CommonServicePolicyTests(unittest.TestCase):
    def test_policy_and_registry_exist(self) -> None:
        self.assertTrue((ROOT / "policies/common-service-policy.md").exists())
        self.assertTrue((ROOT / "catalog/common-services/registry.yaml").exists())

    def test_registry_includes_initial_common_services(self) -> None:
        registry = (ROOT / "catalog/common-services/registry.yaml").read_text(encoding="utf-8")

        self.assertIn("registry_kind: common-services", registry)
        self.assertRegex(registry, r"service_id:\s*aladin-auth\b")
        self.assertRegex(registry, r"service_id:\s*new-billing\b")
        self.assertIn("impact_check_required: true", registry)
        self.assertIn("profile: new-billing.yaml", registry)

    def test_policy_defines_required_impact_check(self) -> None:
        policy = (ROOT / "policies/common-service-policy.md").read_text(encoding="utf-8")

        required_phrases = [
            "공통 서비스 영향 확인",
            "알라딘 인증",
            "뉴빌링",
            "확정 지식으로 승격하지 않는다",
            "사용자 승인",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, policy)

    def test_harness_entrypoints_link_common_service_policy(self) -> None:
        targets = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "catalog/README.md",
            ROOT / "docs/harness-guide.md",
        ]
        for target in targets:
            text = target.read_text(encoding="utf-8")
            self.assertRegex(
                text,
                re.compile(r"common-service-policy\.md|common-services/registry\.yaml"),
                msg=f"{target} must link common service policy or registry",
            )

    def test_new_billing_profile_records_source_and_adoption_rule(self) -> None:
        profile = ROOT / "catalog/common-services/new-billing.yaml"
        text = profile.read_text(encoding="utf-8")

        required_phrases = [
            "https://github.com/AladinCommunication/billing-backend",
            "https://github.com/AladinCommunication/billing-frontend",
            "integration_state: no-active-team2-integration",
            "신규 빌링",
            "뉴빌링 API",
            "billing-api/src/main/kotlin/co/kr/aladin/billing/api/payment/single/shared/controller/SinglePaymentController.kt",
            "billing-frontend/src/requests/routes.ts",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
