# sut_engine.py
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class RuleResult:
    rule_id: str
    title: str
    level: str      # OK / WARNING / HIGH_RISK / BLOCK
    message: str
    score: int


class SUTRuleEngine:
    def __init__(self):
        self.rules = [
            self.rule_01_dual_antiplatelet,
            self.rule_02_triple_antiplatelet,
            self.rule_03_antiplatelet_without_diagnosis,
            self.rule_04_clopidogrel_report_required,
            self.rule_05_high_dose_aspirin_warning,
            self.rule_06_ppi_with_antiplatelet_warning,
            self.rule_07_statin_without_diagnosis,
            self.rule_08_high_dose_statin_report,
            self.rule_09_anticoagulant_antiplatelet_combo,
            self.rule_10_duplicate_nsaid,
            self.rule_11_nsaid_anticoagulant_risk,
            self.rule_12_pregnancy_risk_drugs,
            self.rule_13_child_age_warning,
            self.rule_14_elderly_polypharmacy,
            self.rule_15_duplicate_same_group,
            self.rule_16_antibiotic_duration_warning,
            self.rule_17_insulin_report_required,
            self.rule_18_diabetes_drug_without_diagnosis,
            self.rule_19_expensive_drug_report_required,
            self.rule_20_missing_report_general,
        ]

    def analyze(self, prescription: Dict[str, Any]) -> Dict[str, Any]:
        results: List[RuleResult] = []

        for rule in self.rules:
            result = rule(prescription)
            if result:
                results.append(result)

        total_score = sum(r.score for r in results)

        if total_score >= 80:
            overall = "HIGH_RISK"
        elif total_score >= 40:
            overall = "WARNING"
        else:
            overall = "LOW_RISK"

        return {
            "overall_status": overall,
            "risk_score": min(total_score, 100),
            "results": results
        }

    # -------------------------
    # Yardımcı Fonksiyonlar
    # -------------------------

    def drugs(self, p):
        return [d.lower().strip() for d in p.get("drugs", [])]

    def diagnoses(self, p):
        return [d.lower().strip() for d in p.get("diagnoses", [])]

    def has_any_drug(self, p, keywords):
        drugs = self.drugs(p)
        return any(any(k.lower() in d for k in keywords) for d in drugs)

    def count_group(self, p, group_keywords):
        drugs = self.drugs(p)
        return sum(1 for d in drugs if any(k.lower() in d for k in group_keywords))

    def has_diagnosis(self, p, keywords):
        diagnoses = self.diagnoses(p)
        return any(any(k.lower() in d for k in keywords) for d in diagnoses)

    # -------------------------
    # 20 MVP Kural
    # -------------------------

    def rule_01_dual_antiplatelet(self, p):
        antiplatelets = ["ecopirin", "aspirin", "klogen", "clopidogrel", "plavix"]
        if self.count_group(p, antiplatelets) >= 2:
            return RuleResult(
                "R001",
                "İkili antiplatelet kullanımı",
                "WARNING",
                "Reçetede birden fazla antiplatelet ilaç var. Tanı/rapor uyumu kontrol edilmeli.",
                20
            )

    def rule_02_triple_antiplatelet(self, p):
        antiplatelets = ["ecopirin", "aspirin", "klogen", "clopidogrel", "plavix", "sinlon"]
        if self.count_group(p, antiplatelets) >= 3:
            return RuleResult(
                "R002",
                "Üçlü antiplatelet kullanımı",
                "HIGH_RISK",
                "Reçetede üç veya daha fazla antiplatelet benzeri ilaç bulunuyor. Kesinti riski yüksek olabilir.",
                35
            )

    def rule_03_antiplatelet_without_diagnosis(self, p):
        antiplatelets = ["ecopirin", "aspirin", "klogen", "clopidogrel"]
        vascular_dx = ["koroner", "periferik", "serebral", "stent", "iskemi", "damar"]
        if self.has_any_drug(p, antiplatelets) and not self.has_diagnosis(p, vascular_dx):
            return RuleResult(
                "R003",
                "Antiplatelet tanı kontrolü",
                "WARNING",
                "Antiplatelet ilaç var ancak uygun damar hastalığı/tanı bilgisi girilmemiş görünüyor.",
                15
            )

    def rule_04_clopidogrel_report_required(self, p):
        if self.has_any_drug(p, ["klogen", "clopidogrel", "plavix"]) and not p.get("has_report"):
            return RuleResult(
                "R004",
                "Clopidogrel rapor kontrolü",
                "HIGH_RISK",
                "Clopidogrel grubu ilaç için rapor bilgisi bulunmuyor. Kontrol edilmesi gerekir.",
                30
            )

    def rule_05_high_dose_aspirin_warning(self, p):
        if self.has_any_drug(p, ["aspirin 300", "ecopirin 300"]):
            return RuleResult(
                "R005",
                "Yüksek doz aspirin",
                "WARNING",
                "Yüksek doz aspirin kullanımı var. Endikasyon ve doz uygunluğu kontrol edilmeli.",
                10
            )

    def rule_06_ppi_with_antiplatelet_warning(self, p):
        ppi = ["omeprazol", "esomeprazol", "lansoprazol", "pantoprazol"]
        antiplatelet = ["klogen", "clopidogrel"]
        if self.has_any_drug(p, ppi) and self.has_any_drug(p, antiplatelet):
            return RuleResult(
                "R006",
                "PPI + clopidogrel kontrolü",
                "WARNING",
                "PPI ile clopidogrel birlikte kullanılmış. Klinik ve ödeme açısından kontrol edilmeli.",
                10
            )

    def rule_07_statin_without_diagnosis(self, p):
        statins = ["ator", "atorvastatin", "rosuvastatin", "crestor", "lipitor"]
        dx = ["hiperlipidemi", "kolesterol", "koroner", "kardiyovasküler"]
        if self.has_any_drug(p, statins) and not self.has_diagnosis(p, dx):
            return RuleResult(
                "R007",
                "Statin tanı kontrolü",
                "WARNING",
                "Statin grubu ilaç var ancak uygun tanı bilgisi eksik olabilir.",
                15
            )

    def rule_08_high_dose_statin_report(self, p):
        high_dose = ["atorvastatin 80", "rosuvastatin 40", "crestor 40"]
        if self.has_any_drug(p, high_dose) and not p.get("has_report"):
            return RuleResult(
                "R008",
                "Yüksek doz statin rapor kontrolü",
                "HIGH_RISK",
                "Yüksek doz statin için rapor/tanı uygunluğu kontrol edilmeli.",
                25
            )

    def rule_09_anticoagulant_antiplatelet_combo(self, p):
        anticoagulants = ["eliquis", "xarelto", "pradaxa", "warfarin", "coumadin"]
        antiplatelets = ["ecopirin", "aspirin", "klogen", "clopidogrel"]
        if self.has_any_drug(p, anticoagulants) and self.has_any_drug(p, antiplatelets):
            return RuleResult(
                "R009",
                "Antikoagülan + antiplatelet kombinasyonu",
                "HIGH_RISK",
                "Antikoagülan ve antiplatelet birlikte kullanılmış. Tanı, rapor ve güvenlik açısından kontrol edilmeli.",
                30
            )

    def rule_10_duplicate_nsaid(self, p):
        nsaids = ["diclo", "diklofenak", "naproksen", "ibuprofen", "etodolak", "arveles"]
        if self.count_group(p, nsaids) >= 2:
            return RuleResult(
                "R010",
                "Çift NSAİ kullanımı",
                "HIGH_RISK",
                "Aynı gruptan birden fazla ağrı kesici/NSAİ ilaç var. Kesinti ve klinik risk oluşturabilir.",
                25
            )

    def rule_11_nsaid_anticoagulant_risk(self, p):
        nsaids = ["diklofenak", "naproksen", "ibuprofen", "arveles"]
        anticoagulants = ["eliquis", "xarelto", "pradaxa", "warfarin", "coumadin"]
        if self.has_any_drug(p, nsaids) and self.has_any_drug(p, anticoagulants):
            return RuleResult(
                "R011",
                "NSAİ + antikoagülan riski",
                "HIGH_RISK",
                "NSAİ ve antikoagülan birlikte kullanılmış. Kanama riski ve ödeme uygunluğu kontrol edilmeli.",
                30
            )

    def rule_12_pregnancy_risk_drugs(self, p):
        risky = ["isotretinoin", "roaccutane", "aknetrent", "warfarin"]
        if p.get("pregnant") and self.has_any_drug(p, risky):
            return RuleResult(
                "R012",
                "Gebelikte riskli ilaç",
                "BLOCK",
                "Gebelik bilgisi mevcut ve reçetede yüksek riskli ilaç bulunuyor. Mutlaka kontrol edilmeli.",
                50
            )

    def rule_13_child_age_warning(self, p):
        age = p.get("age")
        risky = ["aspirin", "tetrasiklin", "doksisiklin"]
        if age is not None and age < 12 and self.has_any_drug(p, risky):
            return RuleResult(
                "R013",
                "Çocuk yaş grubu ilaç kontrolü",
                "HIGH_RISK",
                "Hasta çocuk yaş grubunda ve dikkat gerektiren ilaç bulunuyor.",
                25
            )

    def rule_14_elderly_polypharmacy(self, p):
        age = p.get("age")
        if age is not None and age >= 65 and len(self.drugs(p)) >= 5:
            return RuleResult(
                "R014",
                "Yaşlı hastada çoklu ilaç kullanımı",
                "WARNING",
                "65 yaş üstü hastada 5 veya daha fazla ilaç var. Etkileşim ve uygunluk kontrol edilmeli.",
                15
            )

    def rule_15_duplicate_same_group(self, p):
        groups = [
            ["omeprazol", "pantoprazol", "esomeprazol", "lansoprazol"],
            ["loratadin", "desloratadin", "setirizin", "levosetirizin"],
            ["metformin", "glifor"],
        ]

        for group in groups:
            if self.count_group(p, group) >= 2:
                return RuleResult(
                    "R015",
                    "Aynı gruptan mükerrer ilaç",
                    "WARNING",
                    "Aynı terapötik gruptan birden fazla ilaç bulunuyor. Mükerrerlik kontrol edilmeli.",
                    20
                )

    def rule_16_antibiotic_duration_warning(self, p):
        antibiotics = ["amoksisilin", "augmentin", "cipro", "sipro", "klaritromisin", "azithro"]
        duration = p.get("duration_days", 0)
        if self.has_any_drug(p, antibiotics) and duration > 14:
            return RuleResult(
                "R016",
                "Uzun süreli antibiyotik kullanımı",
                "WARNING",
                "Antibiyotik kullanım süresi 14 günü aşıyor. Reçete/rapor uygunluğu kontrol edilmeli.",
                15
            )

    def rule_17_insulin_report_required(self, p):
        insulin = ["insulin", "insülin", "lantus", "novorapid", "humalog", "levemir"]
        if self.has_any_drug(p, insulin) and not p.get("has_report"):
            return RuleResult(
                "R017",
                "İnsülin rapor kontrolü",
                "HIGH_RISK",
                "İnsülin grubu ilaç var ancak rapor bilgisi bulunmuyor.",
                30
            )

    def rule_18_diabetes_drug_without_diagnosis(self, p):
        diabetes_drugs = ["metformin", "glifor", "jardiance", "forxiga", "ozempic", "trulicity"]
        dx = ["diyabet", "diabetes", "tip 2", "tip2"]
        if self.has_any_drug(p, diabetes_drugs) and not self.has_diagnosis(p, dx):
            return RuleResult(
                "R018",
                "Diyabet ilacı tanı kontrolü",
                "WARNING",
                "Diyabet ilacı var ancak diyabet tanısı girilmemiş görünüyor.",
                20
            )

    def rule_19_expensive_drug_report_required(self, p):
        expensive = ["humira", "enbrel", "cosentyx", "stelara", "dupixent"]
        if self.has_any_drug(p, expensive) and not p.get("has_report"):
            return RuleResult(
                "R019",
                "Yüksek maliyetli ilaç rapor kontrolü",
                "BLOCK",
                "Yüksek maliyetli ilaç için rapor bilgisi bulunmuyor. Kesinti riski çok yüksek olabilir.",
                50
            )

    def rule_20_missing_report_general(self, p):
        report_required_groups = [
            "klogen", "clopidogrel", "insülin", "insulin",
            "humira", "enbrel", "xarelto", "eliquis"
        ]
        if self.has_any_drug(p, report_required_groups) and not p.get("has_report"):
            return RuleResult(
                "R020",
                "Genel rapor eksikliği",
                "HIGH_RISK",
                "Reçetede rapor gerektirebilecek ilaçlar var ancak rapor bilgisi girilmemiş.",
                25
            )


# -------------------------
# Test
# -------------------------

if __name__ == "__main__":
    prescription = {
        "patient_name": "Test Hasta",
        "age": 68,
        "pregnant": False,
        "has_report": False,
        "duration_days": 30,
        "diagnoses": ["Periferik serebral damar hastalığı"],
        "drugs": [
            "Klogen 75 mg",
            "Ecopirin 100 mg",
            "Sinlon 100 mg",
            "Pantoprazol 40 mg",
            "Xarelto 20 mg"
        ]
    }

    engine = SUTRuleEngine()
    report = engine.analyze(prescription)

    print("GENEL DURUM:", report["overall_status"])
    print("RİSK SKORU:", report["risk_score"])

    for r in report["results"]:
        print(f"\n{r.rule_id} | {r.level} | {r.title}")
        print(r.message)
