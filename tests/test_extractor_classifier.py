import unittest

from app.services.classifier import ContractClassifier
from app.services.extractor import ContractExtractor


class ExtractorAndClassifierTests(unittest.TestCase):
    SAMPLE_TEXT = """采购合同
甲方：甲公司
乙方：乙公司
合同总价：人民币10000元
争议解决：提交甲方所在地人民法院诉讼解决。"""

    def test_classifier_detects_procurement_contract(self) -> None:
        self.assertEqual(ContractClassifier().classify(self.SAMPLE_TEXT), "采购合同")

    def test_extractor_reads_core_fields(self) -> None:
        extracted = ContractExtractor().extract(self.SAMPLE_TEXT)

        self.assertEqual(extracted.contract_name, "采购合同")
        self.assertEqual(extracted.party_a, "甲公司")
        self.assertEqual(extracted.party_b, "乙公司")
        self.assertEqual(extracted.amount, "人民币10000")
        self.assertEqual(extracted.dispute_clause, "争议解决：提交甲方所在地人民法院诉讼解决。")


if __name__ == "__main__":
    unittest.main()
