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
            self.rule_01,
            self.rule_02,
            self.rule_03,
            self.rule_04,
            self.rule_05,
            self.rule_06,
            self.rule_07,
            self.rule_08,
            self.rule_09,
            self.rule_10,
        ]

    def analyze(self, prescription: Dict[str, Any]):

        results = []

        for rule in self.rules:
            r = rule(prescription)
            if r:
                results.append(r)

        score = min(sum(r.score for r in results), 100)

        if score >= 80:
            status = "YÜKSEK RİSK"
        elif score >= 40:
            status = "ORTA RİSK"
        elif score > 0:
            status = "DÜŞÜK RİSK"
        else:
            status = "UYGUN"

        return {
            "score": score,
            "status": status,
            "results": results
        }

    def drugs(self, p):
        return [d.lower() for d in p["drugs"]]

    def has(self, p, keywords):
        return any(k in d for d in self.drugs(p) for k in keywords)

    def count(self, p, keywords):
        return sum(1 for d in self.drugs(p) if any(k in d for k in keywords))

    # --------------------
    # 10 KURAL (MVP)
    # --------------------

    def rule_01(self, p):
        if self.count(p, ["aspirin", "ecopirin", "klogen", "clopidogrel"]) >= 2:
            return RuleResult("R01", "İkili antiplatelet", "UYARI",
                              "Birden fazla antiplatelet var", 20)

    def rule_02(self, p):
        if self.count(p, ["aspirin", "ecopirin", "klogen", "clopidogrel"]) >= 3:
            return RuleResult("R02", "Üçlü antiplatelet", "YÜKSEK",
                              "3+ antiplatelet", 35)

    def rule_03(self, p):
        if self.has(p, ["klogen", "clopidogrel"]) and not p["has_report"]:
            return RuleResult("R03", "Clopidogrel rapor", "YÜKSEK",
                              "Rapor yok", 30)

    def rule_04(self, p):
        if self.has(p, ["xarelto", "eliquis"]) and self.has(p, ["aspirin", "ecopirin"]):
            return RuleResult("R04", "Antikoagülan + antiplatelet", "YÜKSEK",
                              "Riskli kombinasyon", 30)

    def rule_05(self, p):
        if self.count(p, ["ibuprofen", "naproksen", "diklofenak"]) >= 2:
            return RuleResult("R05", "Çift NSAİ", "YÜKSEK",
                              "Aynı gruptan 2 ilaç", 25)

    def rule_06(self, p):
        if p["age"] > 65 and len(p["drugs"]) >= 5:
            return RuleResult("R06", "Polifarmasi", "UYARI",
                              "Yaşlı + çok ilaç", 15)

    def rule_07(self, p):
        if self.has(p, ["insulin", "lantus"]) and not p["has_report"]:
            return RuleResult("R07", "İnsülin rapor", "YÜKSEK",
                              "Rapor yok", 30)

    def rule_08(self, p):
        if self.has(p, ["metformin"]) and not any("diyabet" in d for d in p["diagnoses"]):
            return RuleResult("R08", "Diyabet tanı", "UYARI",
                              "Tanı yok", 20)

    def rule_09(self, p):
        if p["pregnant"] and self.has(p, ["warfarin"]):
            return RuleResult("R09", "Gebelik risk", "BLOKE",
                              "Riskli ilaç", 50)

    def rule_10(self, p):
        if self.has(p, ["humira", "enbrel"]) and not p["has_report"]:
            return RuleResult("R10", "Pahalı ilaç rapor", "BLOKE",
                              "Rapor yok", 50)


# =========================
# MAKALE TARAMA
# =========================

def extract_rule_suggestions(text):

    keywords = [
        ("rapor", "Rapor gerekli olabilir"),
        ("endikasyon", "Endikasyon şartı olabilir"),
        ("geri ödenmez", "Kesinti riski"),
        ("uzman hekim", "Uzman şartı olabilir"),
        ("en fazla", "Limit olabilir"),
        ("kombinasyon", "Kombinasyon kuralı olabilir"),
    ]

    results = []

    for k, desc in keywords:
        if k in text.lower():
            results.append((k, desc))

    return results


# =========================
# UI
# =========================

st.set_page_config("YILMAZ", layout="wide")

st.title("💊 YILMAZ SUT Risk Motoru")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Reçete Girişi")

    age = st.number_input("Yaş", 0, 120, 65)
    pregnant = st.checkbox("Gebelik")
    has_report = st.checkbox("Rapor var")

    diag = st.text_area("Tanılar", "diyabet")
    drugs = st.text_area("İlaçlar",
                         "Klogen\nEcopirin\nXarelto\nPantoprazol")

    if st.button("Analiz Et"):

        p = {
            "age": age,
            "pregnant": pregnant,
            "has_report": has_report,
            "diagnoses": diag.split("\n"),
            "drugs": drugs.split("\n")
        }

        engine = SUTRuleEngine()
        r = engine.analyze(p)

        st.metric("Risk Skoru", r["score"])
        st.metric("Durum", r["status"])

        for x in r["results"]:
            st.write(f"{x.rule_id} - {x.title} ({x.score})")
            st.write(x.message)
            st.divider()


with col2:
    st.subheader("Makale Tarama")

    text = st.text_area("Metin")

    if st.button("Tara"):
        res = extract_rule_suggestions(text)

        if res:
            for k, d in res:
                st.warning(f"{k} → {d}")
        else:
            st.info("Kural bulunamadı")
