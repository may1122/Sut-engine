import streamlit as st
from dataclasses import dataclass
from typing import Dict, Any
from pypdf import PdfReader
import io
import json
import os


RULES_FILE = "rules.json"


# =========================
# JSON KURAL KAYIT
# =========================

def load_custom_rules():
    if not os.path.exists(RULES_FILE):
        return []

    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_custom_rules(rules):
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)


# =========================
# DATA MODEL
# =========================

@dataclass
class RuleResult:
    rule_id: str
    title: str
    level: str
    message: str
    score: int


# =========================
# SESSION STATE
# =========================

if "custom_rules" not in st.session_state:
    st.session_state.custom_rules = load_custom_rules()

if "last_suggestions" not in st.session_state:
    st.session_state.last_suggestions = []


# =========================
# PDF OKUMA
# =========================

def read_pdf_text(uploaded_file):
    pdf_bytes = uploaded_file.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))

    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


# =========================
# MAKALE / SUT TARAMA
# =========================

def extract_rule_suggestions(text: str):
    text_lower = text.lower()
    suggestions = []

    signals = [
        ("rapor", "Rapor Şartı", "Bu metinde rapor şartı olabilir.", "YÜKSEK", 30),
        ("sağlık kurulu raporu", "Sağlık Kurulu Raporu", "Sağlık kurulu raporu şartı olabilir.", "YÜKSEK", 35),
        ("uzman hekim", "Uzman Hekim Şartı", "Uzman hekim şartı olabilir.", "ORTA", 20),
        ("endikasyon", "Endikasyon Uyumu", "Endikasyon uyumu aranabilir.", "YÜKSEK", 30),
        ("icd", "ICD Tanı Kodu", "ICD tanı kodu kontrolü gerekebilir.", "YÜKSEK", 30),
        ("geri ödenmez", "Ödenmeme Riski", "Belirli durumda geri ödeme yapılmayabilir.", "YÜKSEK", 40),
        ("geri ödenir", "Geri Ödeme Koşulu", "Belirli koşullarda geri ödeme yapılabilir.", "ORTA", 20),
        ("en fazla", "Maksimum Limit", "Doz, kutu veya süre limiti olabilir.", "ORTA", 20),
        ("en az", "Minimum Şart", "Minimum süre, doz veya tedavi şartı olabilir.", "ORTA", 20),
        ("kombinasyon", "Kombinasyon Kontrolü", "Birlikte kullanım kısıtı olabilir.", "YÜKSEK", 30),
        ("birlikte kullanımı", "Birlikte Kullanım", "Birlikte kullanım ödeme/klinik risk oluşturabilir.", "YÜKSEK", 30),
        ("tedavi süresi", "Tedavi Süresi", "Tedavi süresiyle ilgili sınırlama olabilir.", "ORTA", 20),
        ("doz", "Doz Kontrolü", "Doz sınırı veya doz uyumu kontrolü gerekebilir.", "ORTA", 15),
        ("yaş", "Yaş Kriteri", "Hasta yaşıyla ilgili şart olabilir.", "ORTA", 15),
    ]

    for keyword, title, message, risk, score in signals:
        if keyword in text_lower:
            suggestions.append({
                "keyword": keyword,
                "title": title,
                "message": message,
                "risk": risk,
                "score": score
            })

    return suggestions


# =========================
# KURAL MOTORU
# =========================

class SUTRuleEngine:
    def drugs(self, p):
        return [d.lower().strip() for d in p.get("drugs", [])]

    def diagnoses(self, p):
        return [d.lower().strip() for d in p.get("diagnoses", [])]

    def has_any_drug(self, p, keywords):
        drugs = self.drugs(p)
        return any(any(k.lower() in d for k in keywords) for d in drugs)

    def count_group(self, p, keywords):
        drugs = self.drugs(p)
        return sum(1 for d in drugs if any(k.lower() in d for k in keywords))

    def has_diagnosis(self, p, keywords):
        diagnoses = self.diagnoses(p)
        return any(any(k.lower() in d for k in keywords) for d in diagnoses)

    def analyze(self, p: Dict[str, Any]):
        results = []

        builtin_results = [
            self.rule_01_dual_antiplatelet(p),
            self.rule_02_triple_antiplatelet(p),
            self.rule_03_antiplatelet_without_diagnosis(p),
            self.rule_04_clopidogrel_report_required(p),
            self.rule_05_anticoagulant_antiplatelet_combo(p),
            self.rule_06_duplicate_nsaid(p),
            self.rule_07_elderly_polypharmacy(p),
            self.rule_08_insulin_report_required(p),
            self.rule_09_diabetes_without_diagnosis(p),
            self.rule_10_expensive_drug_report_required(p),
        ]

        results.extend([r for r in builtin_results if r])

        # JSON'dan gelen özel kurallar
        for i, rule in enumerate(st.session_state.custom_rules, start=1):
            keyword = rule["keyword"].lower()

            drug_match = any(keyword in d for d in self.drugs(p))
            diagnosis_match = any(keyword in d for d in self.diagnoses(p))

            if drug_match or diagnosis_match:
                results.append(
                    RuleResult(
                        rule_id=f"C{i:03}",
                        title=rule["title"],
                        level=rule["risk"],
                        message=f"Eklenen özel kural tetiklendi: {rule['message']}",
                        score=rule["score"]
                    )
                )

        score = min(sum(r.score for r in results), 100)

        if score >= 80:
            status = "YÜKSEK RİSK"
        elif score >= 40:
            status = "ORTA RİSK"
        elif score > 0:
            status = "DÜŞÜK RİSK"
        else:
            status = "UYGUN GÖRÜNÜYOR"

        return {
            "score": score,
            "status": status,
            "results": results
        }

    def rule_01_dual_antiplatelet(self, p):
        if self.count_group(p, ["ecopirin", "aspirin", "klogen", "clopidogrel", "plavix"]) >= 2:
            return RuleResult("R001", "İkili antiplatelet", "UYARI", "Birden fazla antiplatelet ilaç var.", 20)

    def rule_02_triple_antiplatelet(self, p):
        if self.count_group(p, ["ecopirin", "aspirin", "klogen", "clopidogrel", "plavix", "sinlon"]) >= 3:
            return RuleResult("R002", "Üçlü antiplatelet", "YÜKSEK", "Üç veya daha fazla antiplatelet benzeri ilaç var.", 35)

    def rule_03_antiplatelet_without_diagnosis(self, p):
        if self.has_any_drug(p, ["ecopirin", "aspirin", "klogen", "clopidogrel"]) and not self.has_diagnosis(
            p, ["koroner", "periferik", "serebral", "stent", "iskemi", "damar"]
        ):
            return RuleResult("R003", "Antiplatelet tanı kontrolü", "UYARI", "Uygun damar hastalığı/tanı bilgisi eksik olabilir.", 15)

    def rule_04_clopidogrel_report_required(self, p):
        if self.has_any_drug(p, ["klogen", "clopidogrel", "plavix"]) and not p.get("has_report"):
            return RuleResult("R004", "Clopidogrel rapor kontrolü", "YÜKSEK", "Clopidogrel grubu ilaç için rapor bilgisi yok.", 30)

    def rule_05_anticoagulant_antiplatelet_combo(self, p):
        if self.has_any_drug(p, ["eliquis", "xarelto", "pradaxa", "warfarin", "coumadin"]) and self.has_any_drug(
            p, ["ecopirin", "aspirin", "klogen", "clopidogrel"]
        ):
            return RuleResult("R005", "Antikoagülan + antiplatelet", "YÜKSEK", "Antikoagülan ve antiplatelet birlikte kullanılmış.", 30)

    def rule_06_duplicate_nsaid(self, p):
        if self.count_group(p, ["diclo", "diklofenak", "naproksen", "ibuprofen", "etodolak", "arveles"]) >= 2:
            return RuleResult("R006", "Çift NSAİ", "YÜKSEK", "Aynı gruptan birden fazla NSAİ ilaç var.", 25)

    def rule_07_elderly_polypharmacy(self, p):
        if p.get("age", 0) >= 65 and len(self.drugs(p)) >= 5:
            return RuleResult("R007", "Yaşlı hastada çoklu ilaç", "UYARI", "65 yaş üstü hastada 5 veya daha fazla ilaç var.", 15)

    def rule_08_insulin_report_required(self, p):
        if self.has_any_drug(p, ["insulin", "insülin", "lantus", "novorapid", "humalog", "levemir"]) and not p.get("has_report"):
            return RuleResult("R008", "İnsülin rapor kontrolü", "YÜKSEK", "İnsülin grubu ilaç var ancak rapor bilgisi yok.", 30)

    def rule_09_diabetes_without_diagnosis(self, p):
        if self.has_any_drug(p, ["metformin", "glifor", "jardiance", "forxiga", "ozempic", "trulicity"]) and not self.has_diagnosis(
            p, ["diyabet", "diabetes", "tip 2", "tip2"]
        ):
            return RuleResult("R009", "Diyabet ilacı tanı kontrolü", "UYARI", "Diyabet ilacı var ancak diyabet tanısı eksik olabilir.", 20)

    def rule_10_expensive_drug_report_required(self, p):
        if self.has_any_drug(p, ["humira", "enbrel", "cosentyx", "stelara", "dupixent"]) and not p.get("has_report"):
            return RuleResult("R010", "Yüksek maliyetli ilaç rapor kontrolü", "BLOKE", "Yüksek maliyetli ilaç için rapor bilgisi yok.", 50)


# =========================
# UI
# =========================

st.set_page_config(
    page_title="YILMAZ | SUT Risk Motoru",
    page_icon="💊",
    layout="wide"
)

st.title("💊 YILMAZ")
st.caption("Akıllı SUT ve Reçete Risk Analiz Sistemi")

st.warning("Demo sistemdir. Resmi SUT/Medula kontrolü yerine geçmez.")

tab1, tab2, tab3 = st.tabs([
    "🧾 Reçete Analizi",
    "📚 Makale / PDF Tarama",
    "⚙️ Eklenen Kurallar"
])


# =========================
# TAB 1 - REÇETE ANALİZİ
# =========================

with tab1:
    left, right = st.columns([1, 1.3])

    with left:
        st.subheader("Reçete Bilgileri")

        patient_name = st.text_input("Hasta Adı", "Test Hasta")
        age = st.number_input("Hasta Yaşı", min_value=0, max_value=120, value=68)
        pregnant = st.checkbox("Gebelik Durumu")
        has_report = st.checkbox("Rapor Var mı?")
        duration_days = st.number_input("Tedavi Süresi / Gün", min_value=1, max_value=365, value=30)

        diagnoses_text = st.text_area(
            "Tanılar",
            value="Periferik serebral damar hastalığı",
            height=120
        )

        drugs_text = st.text_area(
            "İlaçlar",
            value="Klogen 75 mg\nEcopirin 100 mg\nSinlon 100 mg\nPantoprazol 40 mg\nXarelto 20 mg",
            height=200
        )

        analyze_button = st.button("🔍 Reçeteyi Analiz Et", use_container_width=True)

    with right:
        st.subheader("Risk Sonucu")

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

            c1, c2, c3 = st.columns(3)
            c1.metric("Risk Skoru", f"{report['score']}/100")
            c2.metric("Durum", report["status"])
            c3.metric("Tetiklenen Kural", len(report["results"]))

            st.progress(report["score"] / 100)

            if report["score"] >= 80:
                st.error("🚨 Yüksek riskli reçete. Detaylı kontrol önerilir.")
            elif report["score"] >= 40:
                st.warning("⚠️ Orta riskli reçete. Kontrol edilmelidir.")
            elif report["score"] > 0:
                st.info("ℹ️ Düşük riskli uyarılar mevcut.")
            else:
                st.success("✅ Belirgin risk bulunmadı.")

            st.divider()

            for r in report["results"]:
                if r.level in ["YÜKSEK", "BLOKE"]:
                    st.error(f"**{r.rule_id} | {r.title} | +{r.score}**\n\n{r.message}")
                elif r.level == "UYARI":
                    st.warning(f"**{r.rule_id} | {r.title} | +{r.score}**\n\n{r.message}")
                else:
                    st.info(f"**{r.rule_id} | {r.title} | +{r.score}**\n\n{r.message}")
        else:
            st.info("Sol taraftan reçete bilgilerini girip analiz butonuna basınız.")


# =========================
# TAB 2 - MAKALE / PDF TARAMA
# =========================

with tab2:
    st.subheader("Makale / SUT / PDF Tarama")

    input_type = st.radio(
        "Kaynak Türü",
        ["Metin Yapıştır", "PDF Yükle"],
        horizontal=True
    )

    article_text = ""

    if input_type == "Metin Yapıştır":
        article_text = st.text_area(
            "Makale / SUT / Duyuru Metni",
            height=300,
            placeholder="Buraya SUT maddesi, TEB duyurusu veya makale metni yapıştırınız..."
        )

    else:
        uploaded_pdf = st.file_uploader("PDF dosyası yükle", type=["pdf"])

        if uploaded_pdf:
            try:
                article_text = read_pdf_text(uploaded_pdf)
                st.success("PDF başarıyla okundu.")
                with st.expander("PDF’den Okunan Metni Göster"):
                    st.text_area("PDF Metni", article_text, height=300)
            except Exception as e:
                st.error(f"PDF okunurken hata oluştu: {e}")

    if st.button("📖 Tara ve Kural Öner", use_container_width=True):
        if not article_text.strip():
            st.warning("Lütfen metin giriniz veya PDF yükleyiniz.")
        else:
            st.session_state.last_suggestions = extract_rule_suggestions(article_text)

    suggestions = st.session_state.last_suggestions

    if suggestions:
        st.success(f"{len(suggestions)} adet kural adayı bulundu.")

        for idx, item in enumerate(suggestions):
            with st.container(border=True):
                st.markdown(f"### {item['title']}")
                st.write(f"**Yakalanan ifade:** `{item['keyword']}`")
                st.write(f"**Risk:** {item['risk']}")
                st.write(f"**Skor:** {item['score']}")
                st.write(item["message"])

                if st.button(f"➕ Bu Kuralı Sisteme Ekle", key=f"add_rule_{idx}"):
                    exists = any(
                        r["keyword"] == item["keyword"] and r["title"] == item["title"]
                        for r in st.session_state.custom_rules
                    )

                    if exists:
                        st.warning("Bu kural zaten eklenmiş.")
                    else:
                        st.session_state.custom_rules.append(item)
                        save_custom_rules(st.session_state.custom_rules)
                        st.success("Kural sisteme eklendi ve rules.json dosyasına kaydedildi.")

    else:
        st.info("Henüz kural önerisi oluşturulmadı.")


# =========================
# TAB 3 - EKLENEN KURALLAR
# =========================

with tab3:
    st.subheader("Sisteme Eklenen Kurallar")

    if not st.session_state.custom_rules:
        st.info("Henüz eklenmiş özel kural yok.")
    else:
        for i, rule in enumerate(st.session_state.custom_rules, start=1):
            with st.container(border=True):
                st.markdown(f"### C{i:03} - {rule['title']}")
                st.write(f"**Anahtar kelime:** `{rule['keyword']}`")
                st.write(f"**Risk:** {rule['risk']}")
                st.write(f"**Skor:** {rule['score']}")
                st.write(rule["message"])

                if st.button(f"🗑️ Kuralı Sil", key=f"delete_{i}"):
                    st.session_state.custom_rules.pop(i - 1)
                    save_custom_rules(st.session_state.custom_rules)
                    st.rerun()
