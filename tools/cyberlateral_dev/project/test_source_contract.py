"""Source identities guard the static state-binding authority before parsing."""
import unittest
from pathlib import Path
from unittest.mock import patch

from test_oracle import feature

REFERENCE = Path(__file__).resolve().parents[1] / "reference"


class ContractTests(unittest.TestCase):
    def test_exact_source_order_constants_and_initializers(self):
        module = feature("source_contract")
        result = module.derive_contract((REFERENCE / "carcontroller.py").read_bytes(), (REFERENCE / "lateral.py").read_bytes())
        self.assertEqual(result["order"], ["limiter", "fault", "inactive_gate", "previous_applied_update"])
        self.assertEqual(result["thresholds"]["MAX_ANGLE"]["value"], 85)
        self.assertEqual(result["thresholds"]["MAX_ANGLE_FRAMES"]["value"], 89)
        self.assertEqual(result["thresholds"]["MAX_ANGLE_CONSECUTIVE_FRAMES"]["value"], 2)
        self.assertEqual(result["initializers"]["self.apply_torque_last"]["value"], 0)
        self.assertEqual(result["initializers"]["self.angle_limit_counter"]["value"], 0)
        self.assertEqual([(r["start_line"], r["end_line"]) for r in result["ordered_records"]],
                         [(71, 71), (74, 76), (78, 79), (81, 81)])
        self.assertEqual(result["previous_requested_binding"], "MODEL_BOOKKEEPING_ONLY")
        self.assertEqual(result["controller_executable_code_compilations"], 0)

    def test_mismatched_source_rejects_before_ast(self):
        module = feature("source_contract")
        controller, helper = (REFERENCE / "carcontroller.py").read_bytes(), (REFERENCE / "lateral.py").read_bytes()
        for first, second in [(b"", helper), (controller + b"\nraise Exception()", helper),
                              (controller, helper[:-1]), (controller, helper.replace(b"np.clip", b"xx.clip", 1))]:
            with (self.subTest(controller_size=len(first), helper_size=len(second)),
                  patch("source_contract.ast.parse", side_effect=AssertionError("AST_MUST_NOT_RUN")),
                  self.assertRaises(module.ContractIdentityError)):
                module.derive_contract(first, second)


if __name__ == "__main__":
    unittest.main()
