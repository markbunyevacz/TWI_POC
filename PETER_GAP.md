# Gap analízis: POC kód vs. platform specifikáció vs. supplier kommentek

**Dátum:** 2026-03-13
**Készítette:** agentize.eu belső elemzés
**Bemenet:** Agent Supplier Onboarding Guide v2.0, Máté Hajdu + Peter Perecz kommentek, POC backend kódbázis

---

## 1. Összefoglaló

A kódbázis közelebb áll a platform specifikációhoz, mint amit a supplier kommentek sugallnak. A kommentek több olyan problémát vetnek fel, amelyek a kódban nem léteznek. Az alábbi elemzés három kategóriában vizsgálja a helyzetet.

---

## 2. Kommentek vs. kód valóság — eltérések

| Komment | Mit állít | Mi van a kódban | Értékelés |
|---------|-----------|-----------------|-----------|
| Máté (old. 14): „nincs benne Gemini" | A Foundry-ra váltás szükséges | `ai_foundry.py`: Mistral Large a modell, `azure-ai-inference` SDK — Gemini sehol nincs a kódban | ✅ Már megoldva |
| Máté (old. 15): „langsmithben vannak a promptok" | LangSmith runtime prompt-letöltés problémás | `langsmith` benne van a `requirements.txt`-ben, de a kódban sehol nincs használva. Promptok hardcoded Python stringek a node fájlokban | ✅ Már megoldva |
| Máté (old. 15): „langchainből a chaint használjuk" | LangChain chain tiltás problémás | LangGraph 0.3 node-ok vannak, `langchain-core` csak BaseMessage-hez importálva, chain nincs | ✅ Már megoldva |
| Péter (old. 14): „Hogy működik a lang ebben a környezetben" | Foundry + LangGraph integráció kérdéses | `ai_foundry.py` + LangGraph node-ok = működő integráció, `PlatformLLMClient` helyett közvetlen `ChatCompletionsClient` | ✅ Működik |
| Máté (old. 22): „speciális a gráf, több lefutás" | Multi-step flow integrálása kérdéses | `graph.py`: interrupt-ok a `review` és `approve` előtt, revision loop max 3 iterációval, `/resume` endpoint a `main.py`-ban | ✅ Támogatott minta |
| Máté (old. 31): „hol laknak a promptok?" | Prompt storage tisztázandó | `intent.py`, `generate.py`: hardcoded system prompt stringek a konténerben | ✅ Pont ahogy a spec kéri |

**Következtetés:** A kommentek 6 fő technikai aggályából 6 a kódban MÁR nem probléma. A kommentek vagy egy korábbi verziót tükröznek, vagy a kommentelők nem nézték meg a jelenlegi kódot.

---

## 3. Ami MÁR megfelel a platform specifikációnak

| Platform spec követelmény | Kód állapot | Fájl |
|--------------------------|-------------|------|
| LangGraph alapú agent gráf | ✅ LangGraph 0.3 StateGraph | `app/agent/graph.py` |
| FastAPI backend | ✅ FastAPI 0.115 | `app/main.py` |
| Azure AI Foundry LLM hívások | ✅ `azure-ai-inference` SDK, Mistral Large | `app/services/ai_foundry.py` |
| HitL interrupt | ✅ Interrupt `review` és `approve` előtt | `app/agent/graph.py` |
| Adaptive Cards | ✅ 4 card típus (review, approval, result, welcome) | `app/bot/adaptive_cards.py` |
| Audit log Cosmos DB-be | ✅ Immutable audit trail | `app/services/cosmos_db.py` |
| EU AI Act jelölés | ✅ Automatikus figyelmeztetés minden kimeneten | `app/agent/nodes/generate.py` |
| Refusal node | ✅ `clarify_node` az unknown intent-hez | `app/agent/graph.py` |
| Promptok konténerben | ✅ Hardcoded, nincs külső letöltés | `app/agent/nodes/*.py` |
| Nem hív publikus AI API-t | ✅ Csak Foundry endpoint | `app/services/ai_foundry.py` |
| Python 3.11+ | ✅ Python 3.12 | `Dockerfile` |

---

## 4. Ami változtatást igényel — priorizált lista

### 🔴 Kritikus (blocker a platform integrációhoz)

#### 4.1 RBAC / Approver role ellenőrzés — HIÁNYZIK
- **Platform spec:** F3 — „A jóváhagyás kizárólag Approver szerepkörű felhasználóval lehetséges"
- **Kód:** Nincs role ellenőrzés. Bárki megnyomhatja a jóváhagyó gombot a Teams-ben.
- **Érintett fájlok:** `app/bot/bot_handler.py` (`_handle_card_action`), `app/agent/nodes/approve.py`
- **Szükséges:** `user_context.roles` ellenőrzés a HitL lépésnél
- **Becsült munka:** 2-3 nap
- **Megjegyzés:** Péterék NEM említették a kommentekben

#### 4.2 Tenant izoláció érvényesítése — HIÁNYZIK
- **Platform spec:** S2 — „Az agent nem ér el más tenant adatát"
- **Kód:** `tenant_id` van a state-ben és az audit logban, de a Cosmos DB lekérdezéseknél nincs szűrés tenant-ra. Nincs partition key.
- **Érintett fájlok:** `app/services/cosmos_db.py`
- **Szükséges:** Partition key tenant_id-ra, lekérdezések szűrése
- **Becsült munka:** 1-2 nap
- **Megjegyzés:** Péterék NEM említették

#### 4.3 Proaktív Approval Routing — HIÁNYZIK
- **Platform spec:** F4, 3.4 fejezet — csatornás/csoportos kontextusban a jóváhagyó Card-ot proaktív üzenettel kell az Approver-hez juttatni
- **Kód:** A jóváhagyó Card mindig ugyanabba a chatbe megy, nincs proaktív routing
- **Érintett fájlok:** `app/bot/bot_handler.py`
- **Szükséges:** `ProactiveMessageSender` implementálás
- **Becsült munka:** 3-5 nap
- **Megjegyzés:** Péterék NEM említették

### 🟡 Közepes (szükséges, de nem blocker a POC-hoz)

#### 4.4 Checkpointing: MemorySaver → Cosmos DB — ✅ RÉSZBEN MEGOLDVA
- **Platform spec:** Cosmos DB checkpoint store (PlatformCheckpointer)
- **Kód:** `MongoDBSaver` implementálva (`app/agent/mongodb_checkpointer.py`), automatikus fallback `MemorySaver`-re ha Cosmos DB nem elérhető. A `create_agent_graph()` függvény a `_get_checkpointer()` helper-en keresztül inicializálja.
- **Érintett fájlok:** `app/agent/graph.py` (`create_agent_graph()`), `app/agent/mongodb_checkpointer.py`
- **Hátralevő:** `PlatformCheckpointer` SDK integráció (platform oldali függőség)
- **Megjegyzés:** Máté említette (old. 24), pozitívan

#### 4.5 Agent Descriptor YAML — HIÁNYZIK
- **Platform spec:** 6. fejezet — kötelező a platform regisztrációhoz
- **Kód:** Nincs `agent_descriptor.yaml`
- **Szükséges:** YAML fájl készítése a spec mintája alapján
- **Becsült munka:** fél nap

#### 4.6 Base image csere
- **Platform spec:** `agentize.eu/python-base:3.11-slim`
- **Kód:** `python:3.12-slim`
- **Érintett fájlok:** `Dockerfile`
- **Becsült munka:** 15 perc

#### 4.7 Token tracking kitöltése — ✅ MEGOLDVA
- **Platform spec:** Token-fogyasztás per-tenant mérése
- **Kód:** `ai_foundry.py` `call_llm()` visszaadja a `(response_text, prompt_tokens, completion_tokens)` tuple-t. A `generate_node()` kumulatívan tölti a `llm_tokens_input` és `llm_tokens_output` mezőket a state-ben, amelyeket az `audit_node` a Cosmos DB-be ment.
- **Érintett fájlok:** `app/services/ai_foundry.py`, `app/agent/nodes/generate.py`
- **Becsült munka:** 0 — kész

### 🟢 Kis változtatások / cleanup

#### 4.8 `langsmith` törlése a requirements.txt-ből — ✅ MEGOLDVA
- Eltávolítva a közvetlen függőség a `requirements.txt`-ből és `pyproject.toml`-ból. Tranzitív függőségként továbbra is települ a `langchain-core` révén.
- **Becsült munka:** 0 — kész

#### 4.9 Test bug fix
- `test_graph.py`: `after_revision()` teszt rossz route neveket vár (`"review"` vs. `"regenerate"`)
- A routing kód jó, a teszt hibás
- **Becsült munka:** 15 perc

---

## 5. Amit a platform oldalon kell biztosítani

| Téma | Teendő | Státusz |
|------|--------|---------|
| Observability / node-szintű trace | AuditLogger bővítése node-szintű logolással | Tervezés alatt |
| P95 target konfigurálhatóság | Agent descriptor-ban definiálható legyen | Elfogadva, spec módosítás kell |
| Web app hosting (JBS szerkesztő) | CI/CD + hosting megoldás definiálása | Közösen tisztázandó |
| Foundry dev endpoint | Sandbox tenant biztosítása teszteléshez | POC-hoz szükséges |
| PlatformCheckpointer SDK | Cosmos DB checkpointer biztosítása | SDK része |

---

## 6. Összesítő mátrix

| Kategória | Darab | Becsült össz. munka |
|-----------|-------|---------------------|
| Kommentben felvetett, de a kódban MÁR megoldott | 6 | 0 |
| Kritikus gap (nem említették) | 3 | 6-10 nap |
| Közepes gap (4.4 részben megoldva, 4.7 megoldva) | 2 nyitott + 2 kész | ~1.5 nap |
| Kis fix (4.8 megoldva) | 1 nyitott + 1 kész | 15 perc |
| Platform oldali teendő | 5 | — |

**Össz. supplier oldali munka:** ~7.5-11.5 nap (a kritikus gapek dominálnak, amiket nem is említettek)

---

## 7. Következtetés

A supplier kommentek a kód valós állapotához képest félrevezetők: 6 felvetett probléma a kódban nem létezik, míg 3 kritikus platform-követelmény (RBAC, tenant izoláció, proaktív routing) kimaradt a review-ból. A POC kódbázis architektúrálisan jó alapon áll — a tényleges munka a biztonsági és compliance réteg implementálása, nem a technológiai váltás.
