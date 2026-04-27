import streamlit as st
from dataclasses import dataclass
from typing import List, Dict, Any


# =========================
# KURAL SONUCU
# =========================

@dataclass
class RuleResult:
    rule_id: str
    title: str
    level: str
    message: str
    score: int


# =========================
# SUT KURAL MOTORU
# =========================

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
        results = []

        for rule in self.rules:
            result = rule(prescription)
            if result:
                results.append(result)

        total_score = sum(r.score for r in results)
        final_score = min(total_score, 100)

        if final_score >= 80:
            overall = "YÜKSEK RİSK"
        elif final_score >= 40:
            overall = "ORTA RİSK"
        elif final_score > 0:
            overall = "DÜŞÜK RİSK"
        else:
            overall = "UYGUN GÖRÜNÜYOR"

        return {
            "overall_status": overall,
            "risk_score": final_score,
            "results": results
        }

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

    def rule_01_dual_antiplatelet(self, p):
        if self.count_group(p, ["ecopirin", "aspirin", "klogen", "clopidogrel", "plavix"]) >= 2:
            return RuleResult("R001", "İkili antiplatelet kullanımı", "UYARI",
                              "Reçetede birden fazla antiplatelet ilaç var.", 20)

    def rule_02_triple_antiplatelet(self, p):
        if self.count_group(p, ["ecopirin", "aspirin", "klogen", "clopidogrel", "plavix", "sinlon"]) >= 3:
            return RuleResult("R002", "Üçlü antiplatelet kullanımı", "YÜKSEK RİSK",
                              "Üç veya daha fazla antiplatelet benzeri ilaç var.", 35)

    def rule_03_antiplatelet_without_diagnosis(self, p):
        if self.has_any_drug(p, ["ecopirin", "aspirin", "klogen", "clopidogrel"]) and not self.has_diagnosis(
            p, ["koroner", "periferik", "serebral", "stent", "iskemi", "damar"]
        ):
            return RuleResult("R003", "Antiplatelet tanı kontrolü", "UYARI",
                              "Antiplatelet ilaç var ancak uygun tanı girilmemiş olabilir.", 15)

    def rule_04_clopidogrel_report_required(self, p):
        if self.has_any_drug(p, ["klogen", "clopidogrel", "plavix"]) and not p.get("has_report"):
            return RuleResult("R004", "Clopidogrel rapor kontrolü", "YÜKSEK RİSK",
                              "Clopidogrel grubu ilaç için rapor bilgisi bulunmuyor.", 30)

    def rule_05_high_dose_aspirin_warning(self, p):
        if self.has_any_drug(p, ["aspirin 300", "ecopirin 300"]):
            return RuleResult("R005", "Yüksek doz aspirin", "UYARI",
                              "Yüksek doz aspirin kullanımı var.", 10)

    def rule_06_ppi_with_antiplatelet_warning(self, p):
        if self.has_any_drug(p, ["omeprazol", "esomeprazol", "lansoprazol", "pantoprazol"]) and self.has_any_drug(
            p, ["klogen", "clopidogrel"]
        ):
            return RuleResult("R006", "PPI + Clopidogrel kontrolü", "UYARI",
                              "PPI ile clopidogrel birlikte kullanılmış.", 10)

    def rule_07_statin_without_diagnosis(self, p):
        if self.has_any_drug(p, ["ator", "atorvastatin", "rosuvastatin", "crestor", "lipitor"]) and not self.has_diagnosis(
            p, ["hiperlipidemi", "kolesterol", "koroner", "kardiyovasküler"]
        ):
            return RuleResult("R007", "Statin tanı kontrolü", "UYARI",
                              "Statin grubu ilaç var ancak uygun tanı eksik olabilir.", 15)

    def rule_08_high_dose_statin_report(self, p):
        if self.has_any_drug(p, ["atorvastatin 80", "rosuvastatin 40", "crestor 40"]) and not p.get("has_report"):
            return RuleResult("R008", "Yüksek doz statin rapor kontrolü", "YÜKSEK RİSK",
                              "Yüksek doz statin için rapor/tanı uygunluğu kontrol edilmeli.", 25)

    def rule_09_anticoagulant_antiplatelet_combo(self, p):
        if self.has_any_drug(p, ["eliquis", "xarelto", "pradaxa", "warfarin", "coumadin"]) and self.has_any_drug(
            p, ["ecopirin", "aspirin", "klogen", "clopidogrel"]
        ):
            return RuleResult("R009", "Antikoagülan + antiplatelet kombinasyonu", "YÜKSEK RİSK",
                              "Antikoagülan ve antiplatelet birlikte kullanılmış.", 30)

    def rule_10_duplicate_nsaid(self, p):
        if self.count_group(p, ["diclo", "diklofenak", "naproksen", "ibuprofen", "etodolak", "arveles"]) >= 2:
            return RuleResult("R010", "Çift NSAİ kullanımı", "YÜKSEK RİSK",
                              "Aynı gruptan birden fazla NSAİ ilaç var.", 25)

    def rule_11_nsaid_anticoagulant_risk(self, p):
        if self.has_any_drug(p, ["diklofenak", "naproksen", "ibuprofen", "arveles"]) and self.has_any_drug(
            p, ["eliquis", "xarelto", "pradaxa", "warfarin", "coumadin"]
        ):
            return RuleResult("R011", "NSAİ + antikoagülan riski", "YÜKSEK RİSK",
                              "NSAİ ve antikoagülan birlikte kullanılmış.", 30)

    def rule_12_pregnancy_risk_drugs(self, p):
        if p.get("pregnant") and self.has_any_drug(p, ["isotretinoin", "roaccutane", "aknetrent", "warfarin"]):
            return RuleResult("R012", "Gebelikte riskli ilaç", "BLOKE",
                              "Gebelik bilgisi mevcut ve yüksek riskli ilaç bulunuyor.", 50)

    def rule_13_child_age_warning(self, p):
        age = p.get("age")
        if age is not None and age < 12 and self.has_any_drug(p, ["aspirin", "tetrasiklin", "doksisiklin"]):
            return RuleResult("R013", "Çocuk yaş grubu kontrolü", "YÜKSEK RİSK",
                              "Çocuk yaş grubunda dikkat gerektiren ilaç var.", 25)

    def rule_14_elderly_polypharmacy(self, p):
        age = p.get("age")
        if age is not None and age >= 65 and len(self.drugs(p)) >= 5:
            return RuleResult("R014", "Yaşlı hastada çoklu ilaç", "UYARI",
                              "65 yaş üstü hastada 5 veya daha fazla ilaç var.", 15)

    def rule_15_duplicate_same_group(self, p):
        groups = [
            ["omeprazol", "pantoprazol", "esomeprazol", "lansoprazol"],
            ["loratadin", "desloratadin", "setirizin", "levosetirizin"],
            ["metformin", "glifor"],
        ]

        for group in groups:
            if self.count_group(p, group) >= 2:
                return RuleResult("R015", "Aynı gruptan mükerrer ilaç", "UYARI",
                                  "Aynı terapötik gruptan birden fazla ilaç bulunuyor.", 20)

    def rule_16_antibiotic_duration_warning(self, p):
        if self.has_any_drug(p, ["amoksisilin", "augmentin", "cipro", "sipro", "klaritromisin", "azithro"]) and p.get("duration_days", 0) > 14:
            return RuleResult("R016", "Uzun süreli antibiyotik", "UYARI",
                              "Antibiyotik kullanım süresi 14 günü aşıyor.", 15)

    def rule_17_insulin_report_required(self, p):
        if self.has_any_drug(p, ["insulin", "insülin", "lantus", "novorapid", "humalog", "levemir"]) and not p.get("has_report"):
            return RuleResult("R017", "İnsülin rapor kontrolü", "YÜKSEK RİSK",
                              "İnsülin grubu ilaç var ancak rapor bilgisi yok.", 30)

    def rule_18_diabetes_drug_without_diagnosis(self, p):
        if self.has_any_drug(p, ["metformin", "glifor", "jardiance", "forxiga", "ozempic", "trulicity"]) and not self.has_diagnosis(
            p, ["diyabet", "diabetes", "tip 2", "tip2"]
        ):
            return RuleResult("R018", "Diyabet ilacı tanı kontrolü", "UYARI",
                              "Diyabet ilacı var ancak diyabet tanısı girilmemiş olabilir.", 20)

    def rule_19_expensive_drug_report_required(self, p):
        if self.has_any_drug(p, ["humira", "enbrel", "cosentyx", "stelara", "dupixent"]) and not p.get("has_report"):
            return RuleResult("R019", "Yüksek maliyetli ilaç rapor kontrolü", "BLOKE",
                              "Yüksek maliyetli ilaç için rapor bilgisi yok.", 50)

    def rule_20_missing_report_general(self, p):
        if self.has_any_drug(p, ["klogen", "clopidogrel", "insülin", "insulin", "humira", "enbrel", "xarelto", "eliquis"]) and not p.get("has_report"):
            return RuleResult("R020", "Genel rapor eksikliği", "YÜKSEK RİSK",
                              "Rapor gerektirebilecek ilaçlar var ancak rapor bilgisi girilmemiş.", 25)


# =========================
# STREAMLIT ARAYÜZ
# =========================

st.set_page_config(
    page_title="YILMAZ | SUT Risk Motoru",
    page_icon="💊",
    layout="wide"
)

st.markdown("""
<style>
.main {
    background-color: #f8fafc;
}

.block-container {
    padding-top: 2rem;
}

.big-title {
    font-size: 38px;
    font-weight: 800;
    color: #0f172a;
}

.sub-title {
    font-size: 18px;
    color: #475569;
    margin-bottom: 25px;
}

.card {
    background: white;
    padding: 22px;
    border-radius: 18px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}

.risk-high {
    background: #fee2e2;
    border: 1px solid #fecaca;
    color: #991b1b;
    padding: 18px;
    border-radius: 16px;
    font-weight: 700;
}

.risk-medium {
    background: #fef3c7;
    border: 1px solid #fde68a;
    color: #92400e;
    padding: 18px;
    border-radius: 16px;
    font-weight: 700;
}

.risk-low {
    background: #dcfce7;
    border: 1px solid #bbf7d0;
    color: #166534;
    padding: 18px;
    border-radius: 16px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


st.markdown('<div class="big-title">YILMAZ</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Akıllı SUT ve Reçete Risk Analiz Sistemi</div>',
    unsafe_allow_html=True
)

st.warning(
    "Bu demo resmi SUT kontrol sistemi değildir. MVP amaçlıdır. Gerçek kullanımda kurallar eczacı/uzman kontrolüyle doğrulanmalıdır."
)

left, right = st.columns([1, 1.3])

with left:
    st.markdown("### 🧾 Reçete Bilgileri")

    patient_name = st.text_input("Hasta Adı", "Test Hasta")
    age = st.number_input("Hasta Yaşı", min_value=0, max_value=120, value=68)
    pregnant = st.checkbox("Gebelik Durumu")
    has_report = st.checkbox("Rapor Var mı?")
    duration_days = st.number_input("Tedavi Süresi / Gün", min_value=1, max_value=365, value=30)

    diagnoses_text = st.text_area(
        "Tanılar",
        value="Periferik serebral damar hastalığı",
        height=100,
        help="Her tanıyı yeni satıra yazabilirsin."
    )

    drugs_text = st.text_area(
        "İlaçlar",
        value="Klogen 75 mg\nEcopirin 100 mg\nSinlon 100 mg\nPantoprazol 40 mg\nXarelto 20 mg",
        height=180,
        help="Her ilacı yeni satıra yaz."
    )

    analyze_button = st.button("🔍 Reçeteyi Analiz Et", use_container_width=True)


with right:
    st.markdown("### 📊 Risk Analizi")

    if analyze_button:
        prescription = {
            "patient_name": patient_name,
            "age": age,
            "pregnant": pregnant,
            "has_report": has_report,
            "duration_days": duration_days,
            "diagnoses": [x.strip() for x in diagnoses_text.splitlines() if x.strip()],
            "drugs": [x.strip() for x in drugs_text.splitlines() if x.strip()],
        }

        engine = SUTRuleEngine()
        report = engine.analyze(prescription)

        score = report["risk_score"]
        status = report["overall_status"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Skoru", f"{score}/100")
        c2.metric("Genel Durum", status)
        c3.metric("Tespit Edilen Kural", len(report["results"]))

        st.progress(score / 100)

        if score >= 80:
            st.markdown(f'<div class="risk-high">🚨 {status} - Kesinti riski yüksek olabilir.</div>', unsafe_allow_html=True)
        elif score >= 40:
            st.markdown(f'<div class="risk-medium">⚠️ {status} - Reçete detaylı kontrol edilmeli.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="risk-low">✅ {status} - Büyük bir risk görünmüyor.</div>', unsafe_allow_html=True)

        st.divider()

        if report["results"]:
            st.markdown("### Tespit Edilen Kurallar")

            for r in report["results"]:
                if r.level in ["YÜKSEK RİSK", "BLOKE"]:
                    st.error(f"{r.rule_id} | {r.title} | +{r.score} puan\n\n{r.message}")
                elif r.level == "UYARI":
                    st.warning(f"{r.rule_id} | {r.title} | +{r.score} puan\n\n{r.message}")
                else:
                    st.info(f"{r.rule_id} | {r.title} | +{r.score} puan\n\n{r.message}")
        else:
            st.success("Herhangi bir risk kuralı tetiklenmedi.")

    else:
        st.info("Sol taraftan reçete bilgilerini girip analiz butonuna basınız.")


st.divider()

with st.expander("📌 Sistemdeki 20 Demo Kural"):
    rules = [
        "İkili antiplatelet kullanımı",
        "Üçlü antiplatelet kullanımı",
        "Antiplatelet tanı kontrolü",
        "Clopidogrel rapor kontrolü",
        "Yüksek doz aspirin",
        "PPI + Clopidogrel kontrolü",
        "Statin tanı kontrolü",
        "Yüksek doz statin rapor kontrolü",
        "Antikoagülan + antiplatelet kombinasyonu",
        "Çift NSAİ kullanımı",
        "NSAİ + antikoagülan riski",
        "Gebelikte riskli ilaç",
        "Çocuk yaş grubu ilaç kontrolü",
        "Yaşlı hastada çoklu ilaç kullanımı",
        "Aynı gruptan mükerrer ilaç",
        "Uzun süreli antibiyotik kullanımı",
        "İnsülin rapor kontrolü",
        "Diyabet ilacı tanı kontrolü",
        "Yüksek maliyetli ilaç rapor kontrolü",
        "Genel rapor eksikliği",
    ]

    for i, rule in enumerate(rules, start=1):
        st.write(f"{i}. {rule}")
