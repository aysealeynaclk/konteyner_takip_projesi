"""
Konteyner Takip - Backend API
Bu aşamada henüz LLM yok - sadece düz Python fonksiyonlarıyla
veritabanı sorguları yapılıyor ve test endpoint'leriyle doğrulanıyor.

LLM entegrasyonu bir sonraki adımda bu fonksiyonların üzerine eklenecek.
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import re
from datetime import datetime
from pathlib import Path
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "containers.db"


app = FastAPI(title="Konteyner Takip API")

# Vue (localhost:5173 - Vite'ın varsayılan portu) frontend'in backend'e
# istek atabilmesi için CORS izni veriyoruz
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# KİMLİK DOĞRULAMA (AUTH) AYARLARI
# ---------------------------------------------------------

SECRET_KEY = "corex-gizli-anahtar-bunu-degistir-2026"  # Üretimde .env'e taşınmalı
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8


def create_token(username: str, user_id: int, is_admin: bool):
    payload = {
        "uid": user_id,
        "sub": username,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(authorization: str = None):
    """İstek header'ındaki token'ı doğrular. Geçersizse hata fırlatır."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Giriş yapmanız gerekiyor.")

    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Oturumunuzun süresi doldu, tekrar giriş yapın.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Geçersiz oturum.")


def get_current_user(authorization: str = Header(None)):
    """FastAPI dependency: doğrulanmış kullanıcıyı döner, doğrulama başarısız ise 401 fırlatır."""
    payload = verify_token(authorization)
    return payload


def get_current_admin(current_user: dict = Depends(get_current_user)):
    """FastAPI dependency: sadece is_admin=True olan kullanıcılara izin verir."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Bu işlem için admin yetkisi gerekiyor.")
    return current_user


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(request: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = ?", (request.username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı.")

    user = dict(row)
    password_valid = bcrypt.checkpw(request.password.encode("utf-8"), user["password_hash"].encode("utf-8"))

    if not password_valid:
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı.")

    token = create_token(user["username"], int(user["id"]), bool(user["is_admin"]))
    return {
        "token": token,
        "username": user["username"],
        "is_admin": bool(user["is_admin"]),
        "user_id": int(user["id"]),
    }



def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Sonuçları dict gibi kullanabilmek için
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_chat_history_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            messages_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("PRAGMA table_info(chat_sessions)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if "user_id" not in existing_columns:
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN user_id INTEGER")
    if "username" not in existing_columns:
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN username TEXT")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id_updated_at
        ON chat_sessions(user_id, updated_at DESC)
    """)
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event():
    ensure_chat_history_tables()


def get_ports_by_country(country_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, country, has_port, lat, lng FROM ports WHERE country = ?",
        (country_name,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_all_countries():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT country, has_port, name, lat, lng FROM ports ORDER BY country")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def resolve_chat_user(current_user: dict):
    user_id = current_user.get("uid")
    username = current_user.get("sub", "")

    if user_id is not None:
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            user_id = None

    if user_id is None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
          user_id = int(row["id"])
          username = row["username"]

    if user_id is None:
        raise HTTPException(status_code=401, detail="Kullanıcı doğrulanamadı.")

    return {"id": user_id, "username": username}


_CHAT_TITLE_STOPWORDS = {
    "ve", "veya", "ile", "icin", "için", "bir", "bu", "su", "şu", "simdi", "şimdi",
    "acaba", "lütfen", "lutfen", "mi", "mı", "mu", "mü", "de", "da", "ki", "ne",
    "nasıl", "nasil", "kaç", "kac", "hangi", "neden", "gibi", "olan", "var", "yok",
}


def _chat_title_from_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r'^(merhaba|selam|iyi\s+günler|iyi\s+akşamlar|günaydın)[,!.\s-]*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\n\r]+', ' ', cleaned)
    tokens = re.findall(r'[0-9A-Za-zÇĞİÖŞÜçğıöşü]+', cleaned, flags=re.UNICODE)

    meaningful = [token for token in tokens if token.lower() not in _CHAT_TITLE_STOPWORDS]
    if not meaningful:
        meaningful = tokens

    if not meaningful:
        return cleaned[:40].strip()

    title = ' '.join(meaningful[:5]).strip()
    return title[:40].strip()


# Konteyner numarası formatını yakalayan regex (4 harf + 7 rakam, örn: CMAU6962032)
CONTAINER_NO_PATTERN = re.compile(r'\b[A-Z]{4}\d{7}\b')


def _generate_llm_title(first_user_message: str) -> str:
    """LLM'e sohbeti kısa bir başlığa özetlettirir. Hata olursa None döner."""
    try:
        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Kullanıcının mesajını en fazla 4 kelimelik, kısa ve anlamlı "
                        "bir Türkçe başlığa dönüştür. Sadece başlığı yaz, başka hiçbir "
                        "şey ekleme, tırnak işareti kullanma, noktalama ekleme."
                    ),
                },
                {"role": "user", "content": first_user_message},
            ],
            max_tokens=20,
        )
        title = response.choices[0].message.content.strip().strip('"').strip("'")
        return title if title else None
    except Exception:
        return None


def _find_container_no_in_conversation(messages):
    """Sohbetteki TÜM mesajları (kullanıcı ve asistan) tarayıp ilk konteyner numarasını bulur."""
    for message in messages:
        content = message.get("content", "")
        match = CONTAINER_NO_PATTERN.search(content.upper())
        if match:
            return match.group(0)
    return None

def _chat_session_title(messages):
    first_user_message = next((message["content"] for message in messages if message.get("role") == "user"), "")

    if not first_user_message and not messages:
        return "Sohbet"

    # 1. ÖNCE: Sohbetin TAMAMINDA konteyner numarası ara (sadece ilk mesajda değil)
    container_no = _find_container_no_in_conversation(messages)
    if container_no:
        return f"{container_no} Sorgusu"

    # 2. Küçük sohbet mi? (çok kısa, selamlaşma kalıpları)
    generic_greetings = ["merhaba", "selam", "nasılsın", "teşekkür", "sağol", "iyi günler", "günaydın"]
    lowered = first_user_message.lower()
    if any(greeting in lowered for greeting in generic_greetings) and len(first_user_message.split()) <= 5:
        return "Genel Sohbet"

    # 3. Yukarıdakiler işe yaramadıysa: LLM'e özetlettir
    llm_title = _generate_llm_title(first_user_message)
    if llm_title:
        return llm_title

    # 4. Son çare: ilk 5 kelime
    words = first_user_message.split()
    fallback = " ".join(words[:5])
    return fallback if fallback else "Sohbet"


def _row_to_chat_session(row):
    session = dict(row)
    try:
        session["messages"] = json.loads(session.pop("messages_json"))
    except Exception:
        session["messages"] = []
        session.pop("messages_json", None)
    return session


def list_chat_sessions(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, username, title, messages_json, created_at, updated_at
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY datetime(updated_at) DESC, id DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_chat_session(row) for row in rows]


def get_chat_session(session_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, username, title, messages_json, created_at, updated_at
        FROM chat_sessions
        WHERE id = ? AND user_id = ?
        """,
        (session_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_chat_session(row) if row else None


def save_chat_session(user_id: int, username: str, messages, session_id: Optional[int] = None):
    title = _chat_session_title(messages)
    messages_json = json.dumps(messages, ensure_ascii=False)

    conn = get_connection()
    cursor = conn.cursor()

    if session_id is None:
        cursor.execute(
            """
            INSERT INTO chat_sessions (user_id, username, title, messages_json)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, title, messages_json),
        )
        session_id = cursor.lastrowid
    else:
        cursor.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Sohbet geçmişi bulunamadı.")

        cursor.execute(
            """
            UPDATE chat_sessions
            SET user_id = ?, username = ?, title = ?, messages_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (user_id, username, title, messages_json, session_id, user_id),
        )

    conn.commit()
    conn.close()
    return get_chat_session(session_id, user_id)


def delete_chat_session(session_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def rename_chat_session(session_id: int, user_id: int, new_title: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE chat_sessions
        SET title = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (new_title, session_id, user_id),
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    if not updated:
        return None
    return get_chat_session(session_id, user_id)


# ---------------------------------------------------------
# TEST ENDPOINT'LERİ (manuel test için - Postman/tarayıcı)
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend çalışıyor"}


@app.get("/api/container/{container_no}/entry")
def api_get_entry(container_no: str):
    result = get_container_entry(container_no)
    if not result:
        raise HTTPException(status_code=404, detail="Giriş kaydı bulunamadı")
    return result


@app.get("/api/container/{container_no}/exit")
def api_get_exit(container_no: str):
    result = get_container_exit(container_no)
    if not result:
        raise HTTPException(status_code=404, detail="Çıkış kaydı bulunamadı")
    return result


@app.get("/api/container/{container_no}/status")
def api_get_status(container_no: str):
    return get_container_status(container_no)


@app.get("/api/containers/by-date")
def api_get_by_date(start_date: str, end_date: str):
    return get_containers_by_date_range(start_date, end_date)


@app.get("/api/containers/in-yard")
def api_list_in_yard():
    return list_containers_in_yard()


@app.get('/api/ports')
def api_get_ports(country: Optional[str] = None):
    if not country:
        raise HTTPException(status_code=400, detail='country query parameter required')
    ports = get_ports_by_country(country)
    return {'count': len(ports), 'ports': ports}


@app.get('/api/countries')
def api_get_countries():
    countries = list_all_countries()
    return {'count': len(countries), 'countries': countries}


# ---------------------------------------------------------
# ADMIN ENDPOINT'LERİ (sadece is_admin=True kullanıcılar)
# ---------------------------------------------------------

class NewContainerEntryRequest(BaseModel):
    container_no: str
    time_entered_yard: str
    transaction_type: str
    freight_kind: str
    loc_name: Optional[str] = None
    damage: bool = False


class CloseExitRequest(BaseModel):
    time_exited_yard: str


class UpdateContainerDetailsRequest(BaseModel):
    loc_name: Optional[str] = None
    damage: Optional[bool] = None
    freight_kind: Optional[str] = None


@app.get("/api/admin/meta")
def api_admin_meta(current_admin: dict = Depends(get_current_admin)):
    return {"transaction_types": TRANSACTION_TYPES, "freight_kinds": FREIGHT_KINDS}


@app.post("/api/admin/containers")
def api_create_container_entry(request: NewContainerEntryRequest, current_admin: dict = Depends(get_current_admin)):
    record = create_container_entry(
        container_no=request.container_no,
        time_entered_yard=request.time_entered_yard,
        transaction_type=request.transaction_type,
        freight_kind=request.freight_kind,
        loc_name=request.loc_name,
        damage=request.damage,
    )
    return {"record": record}


@app.get("/api/admin/containers/search")
def api_search_containers(container_no: str, current_admin: dict = Depends(get_current_admin)):
    records = search_container_records(container_no)
    return {"count": len(records), "records": records}


@app.post("/api/admin/containers/{record_id}/exit")
def api_close_container_exit(record_id: int, request: CloseExitRequest, current_admin: dict = Depends(get_current_admin)):
    record = close_container_exit(record_id, request.time_exited_yard)
    return {"record": record}


@app.post("/api/admin/containers/{record_id}/cancel")
def api_cancel_container_record(record_id: int, current_admin: dict = Depends(get_current_admin)):
    record = cancel_container_record(record_id)
    return {"record": record}


@app.patch("/api/admin/containers/{record_id}")
def api_update_container_details(record_id: int, request: UpdateContainerDetailsRequest, current_admin: dict = Depends(get_current_admin)):
    record = update_container_details(
        record_id,
        loc_name=request.loc_name,
        damage=request.damage,
        freight_kind=request.freight_kind,
    )
    return {"record": record}

#----------------------------------------------------------
#----------------------------------------------------------
# ---------------------------------------------------------
# ---------------------------------------------------------
# ---------------------------------------------------------

# ---------------------------------------------------------
# CEREBRAS (GPT-OSS) LLM ENTEGRASYONU
# ---------------------------------------------------------

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = OpenAI(
    api_key="csk-9t84x9rh2khd8pwtvjvh289jyn63j9x4j5c3vc92y68dcwk3",
    base_url="https://api.cerebras.ai/v1",
)

SYSTEM_INSTRUCTION = """
Sen bir liman konteyner takip sisteminin asistanısın.
Kullanıcılar sana konteynerlerin giriş/çıkış zamanları, durumu (limanda mı,
çıkmış mı), belirli tarih aralığındaki hareketler, sahadaki konumu, sahada
geçirdiği süre, hasar durumu veya yük tipi hakkında Türkçe sorular soracak.

Uygun fonksiyonu çağırarak veritabanından veriyi çek, sonra kullanıcıya
doğal, akıcı ve insana hitap eden bir Türkçe cümleyle açıkla.

Fonksiyonların döndürdüğü kayıtlarda şu ham alanlar bulunur, bunları
yorumlayıp doğal Türkçe'ye çevirerek anlat:
- loc_name: konteynerin sahadaki (yard) konum/slot kodu (örn. "Y-YCT-C24273")
- truck_visit_minutes_in_yard: kamyonun sahada geçirdiği süre, dakika cinsinden
- transaction_type: işlem tipi — ReceiveExport (ihracat için limana kabul),
  DeliverImport (ithalat teslimatı), DeliverEmpty (boş konteyner teslimatı),
  ReceiveEmpty (boş konteyner kabulü), DrayOffExport/DrayOffImport (saha içi
  taşıma), DeliverBreakBulk (parça yük teslimatı)
- damage: hasar durumu — 1 ise hasarlı, 0 ise hasarsız
- freight_kind: yük tipi — FCL (dolu konteyner), MTY (boş konteyner),
  BBK (parça yük / break bulk)

İfade kuralları:
- EN ÖNEMLİ KURAL: SADECE kullanıcının sorduğu soruya cevap ver, başka HİÇBİR
  alandan bahsetme. Fonksiyonlar tek çağrıda giriş zamanı, çıkış zamanı,
  sahadaki konum (loc_name), sahada geçirilen süre (truck_visit_minutes_in_yard),
  işlem tipi (transaction_type), hasar durumu (damage) ve yük tipi
  (freight_kind) gibi bir sürü alanı BİRLİKTE döndürür — bu, kullanıcının
  hepsini bilmek istediği anlamına GELMEZ. Cevabını sadece sorulan konuyla
  sınırla, diğer alanları görmezden gel, "ayrıca şunu da belirteyim" tarzı
  gönüllü ek bilgi verme.
    - Soru: "CMAU6962032 girdi mi?" -> SADECE giriş yapıp yapmadığını ve
      giriş zamanını söyle. Çıkış yapıp yapmadığını, slotunu, sahada kaldığı
      süreyi, hasar durumunu veya yük tipini SÖYLEME — sorulmadı.
    - Soru: "CMAU6962032 çıktı mı?" -> SADECE çıkış bilgisini söyle, girişten
      bahsetme.
    - Soru: "CMAU6962032 sahada nerede?" -> SADECE loc_name'e göre cevap ver.
    - Soru: "CMAU6962032 hasarlı mı?" -> SADECE damage alanına göre cevap ver.
  Kullanıcı "tüm bilgileri ver" / "detaylı anlat" / "durumu nedir" gibi genel
  ve açık uçlu bir şey sorarsa, o zaman fonksiyonun döndürdüğü ilgili tüm
  alanları anlat.
- Tarih/saatleri okunaklı yaz (örn. "5 Temmuz 2026, saat 14:32")
- Veritabanı sütun adlarını (örn. "time_entered_yard", "loc_name") ham haliyle
  asla gösterme, kodları (ReceiveExport, FCL, vb.) da olduğu gibi tekrarlama —
  yukarıdaki açıklamalara göre doğal Türkçe'ye çevir
- Sonuç SIFIR (boş liste, hiç kayıt yok) ise bunu robotik bir sayı olarak değil,
  doğal bir cümleyle ifade et. Örnek:
    - KÖTÜ: "Limanda 0 konteyner bulunuyor."
    - İYİ: "Şu anda limanda konteyner bulunmuyor, saha boş görünüyor."
- Sonuç TEK bir kayıtsa, sayı vurgusu yapmadan direkt bilgiyi ver. Örnek:
    - KÖTÜ: "1 konteyner bulundu: X"
    - İYİ: "Evet, X konteyneri şu an limanda."
- Sonuç BİRDEN FAZLA kayıtsa, sayıyı doğal bir cümle içinde belirt ve listeyi
  madde işaretleriyle ver. Örnek:
    - "Şu anda limanda 5 konteyner var: ..."
- Konteyner bulunamazsa ("NOT_FOUND") nazikçe belirt, hata gibi gösterme.
- Kısa ve net cevap ver, gereksiz teknik detay verme, resmi ama samimi bir dil kullan.

Genel sohbet kuralları:
- Kullanıcı "merhaba", "nasılsın", "teşekkürler", "iyi günler" gibi normal bir
  sohbet cümlesi kurarsa, ASLA fonksiyon çağırma — doğal, samimi bir Türkçe
  cevap ver (örn. "Rica ederim, başka bir konuda yardımcı olabilirim." gibi).
- Sadece konteyner/liman ile ilgili somut bir soru olduğunda fonksiyon çağır.
- Önceki mesajlarda geçen konteyner numarasını hatırla — kullanıcı aynı
  sohbette "peki ne zaman çıktı?" gibi takip sorusu sorarsa, hangi konteynerden
  bahsettiğini önceki mesajlardan çıkar, tekrar sormasını isteme.
"""

SYSTEM_INSTRUCTION_EN = """
You are the assistant for a port container tracking system.
Users will ask you, in English, about containers' entry/exit times, current
status (still in the yard or already departed), movements within a date
range, their location in the yard, damage status, or freight type.

Call the appropriate function to fetch the data from the database, then
explain it to the user in a natural, fluent, human-friendly English sentence.

The records returned by the functions contain these raw fields — interpret
them and explain in natural English:
- loc_name: the container's location/slot code in the yard (e.g. "Y-YCT-C24273")
- truck_visit_minutes_in_yard: minutes the truck spent in the yard
- transaction_type: transaction type — ReceiveExport (received for export),
  DeliverImport (import delivery), DeliverEmpty (empty container delivery),
  ReceiveEmpty (empty container receipt), DrayOffExport/DrayOffImport
  (in-yard drayage), DeliverBreakBulk (break-bulk delivery)
- damage: damage status — 1 means damaged, 0 means undamaged
- freight_kind: freight type — FCL (full container load), MTY (empty
  container), BBK (break bulk)

Wording rules:
- MOST IMPORTANT RULE: answer ONLY the question the user asked, and mention
  NOTHING else. A single function call returns entry time, exit time,
  location (loc_name), time in yard (truck_visit_minutes_in_yard),
  transaction type (transaction_type), damage (damage), and freight type
  (freight_kind) all together — that does NOT mean the user wants to know
  all of it. Keep your answer limited to what was asked, ignore the other
  fields, don't volunteer extra information like "by the way, also...".
    - Question: "Did CMAU6962032 enter?" -> ONLY say whether it entered and
      when. Do NOT mention whether it exited, its slot, time in yard, damage,
      or freight type — not asked.
    - Question: "Did CMAU6962032 exit?" -> ONLY answer about the exit, don't
      mention entry.
    - Question: "Where is CMAU6962032 in the yard?" -> answer ONLY using
      loc_name.
    - Question: "Is CMAU6962032 damaged?" -> answer ONLY using the damage
      field.
  If the user asks something open-ended like "give me all the details" /
  "tell me its full status", then explain all the relevant fields returned.
- Write dates/times in a readable way (e.g. "July 5, 2026 at 2:32 PM")
- Never show raw database column names (e.g. "time_entered_yard", "loc_name"),
  and don't repeat raw codes (ReceiveExport, FCL, etc.) verbatim either —
  translate them into natural English per the explanations above
- If the result is ZERO (empty list, no records), phrase it as a natural
  sentence, not a robotic number. Example:
    - BAD: "There are 0 containers in the yard."
    - GOOD: "There are no containers in the yard right now, the yard looks empty."
- If the result is a SINGLE record, give the info directly without emphasizing
  the count. Example:
    - BAD: "1 container found: X"
    - GOOD: "Yes, container X is currently in the yard."
- If the result has MULTIPLE records, mention the count in a natural sentence
  and list them with bullet points. Example:
    - "There are currently 5 containers in the yard: ..."
- If a container isn't found ("NOT_FOUND"), state it gently, not like an error.
- Keep answers short and to the point, avoid unnecessary technical detail,
  use a professional but friendly tone.

General conversation rules:
- If the user says something conversational like "hello", "how are you",
  "thanks", "good morning", NEVER call a function — reply naturally and
  warmly in English (e.g. "You're welcome, happy to help with anything else.").
- Only call a function when there's a concrete container/port-related question.
- Remember container numbers mentioned earlier in the conversation — if the
  user asks a follow-up like "so when did it exit?" in the same chat, infer
  which container they mean from earlier messages, don't ask again.
"""

# Cerebras/OpenAI formatı, fonksiyon şemalarını JSON olarak elle tanımlıyoruz
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_container_entry",
            "description": "Bir konteynerin en son giriş (IN) kaydını getirir. Sahadaki konumu (loc_name), sahada geçirdiği süreyi (truck_visit_minutes_in_yard), işlem tipini (transaction_type), hasar durumunu (damage) ve yük tipini (freight_kind) de içerir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_no": {"type": "string", "description": "Konteyner numarası"}
                },
                "required": ["container_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_container_exit",
            "description": "Bir konteynerin en son çıkış (OUT) kaydını getirir. Sahadaki konumu (loc_name), sahada geçirdiği süreyi (truck_visit_minutes_in_yard), işlem tipini (transaction_type), hasar durumunu (damage) ve yük tipini (freight_kind) de içerir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_no": {"type": "string", "description": "Konteyner numarası"}
                },
                "required": ["container_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_container_status",
            "description": "Bir konteynerin şu anki durumunu (limanda mı, çıkmış mı) getirir. Sahadaki konumu (loc_name), sahada geçirdiği süreyi (truck_visit_minutes_in_yard), işlem tipini (transaction_type), hasar durumunu (damage) ve yük tipini (freight_kind) de içerir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "container_no": {"type": "string", "description": "Konteyner numarası"}
                },
                "required": ["container_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_containers_by_date_range",
            "description": "Belirli bir tarih aralığındaki tüm giriş/çıkış hareketlerini getirir. Her kayıtta sahadaki konum (loc_name), sahada geçirilen süre (truck_visit_minutes_in_yard), işlem tipi (transaction_type), hasar durumu (damage) ve yük tipi (freight_kind) de bulunur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Başlangıç tarihi YYYY-MM-DD formatında"},
                    "end_date": {"type": "string", "description": "Bitiş tarihi YYYY-MM-DD formatında"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_containers_in_yard",
            "description": "Şu anda limanda olan tüm konteynerleri listeler. Her kayıtta sahadaki konum (loc_name), sahada geçirilen süre (truck_visit_minutes_in_yard), işlem tipi (transaction_type), hasar durumu (damage) ve yük tipi (freight_kind) de bulunur.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# Fonksiyon isimlerini gerçek Python fonksiyonlarına eşliyoruz



#--------------------------------------------------------------
#
#--------------------------------------------------------------

# Bu alanlar temiz tabloda dolu ve tüm sorgu fonksiyonlarınca döndürülüyor:
# loc_name (sahadaki konumu), truck_visit_minutes_in_yard (sahada geçirdiği dakika),
# transaction_type (işlem tipi), damage (hasar var mı: 0/1), freight_kind (FCL/MTY/BBK)
_GATE_COLUMNS = """
    container_no, time_entered_yard, time_exited_yard, transaction_status,
    loc_name, truck_visit_minutes_in_yard, transaction_type, damage, freight_kind
"""


def get_container_entry(container_no: str):
    """Bir konteynerin limana/sahaya giriş kaydını döner (iptal edilmiş kayıtlar hariç)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {_GATE_COLUMNS}
        FROM gate_transactions
        WHERE container_no = ? AND transaction_status != 'CANCEL'
        ORDER BY time_entered_yard DESC
        LIMIT 1
    """, (container_no,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_container_exit(container_no: str):
    """Bir konteynerin limandan/sahadan çıkış kaydını döner (iptal edilmiş kayıtlar hariç)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {_GATE_COLUMNS}
        FROM gate_transactions
        WHERE container_no = ? AND time_exited_yard IS NOT NULL AND transaction_status != 'CANCEL'
        ORDER BY time_exited_yard DESC
        LIMIT 1
    """, (container_no,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_container_status(container_no: str):
    """Bir konteynerin şu anki durumunu belirler (iptal edilmiş kayıtlar hariç)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {_GATE_COLUMNS}
        FROM gate_transactions
        WHERE container_no = ? AND transaction_status != 'CANCEL'
        ORDER BY time_entered_yard DESC
        LIMIT 1
    """, (container_no,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"status": "NOT_FOUND", "container_no": container_no}

    record = dict(row)
    status = "IN_YARD" if record["time_exited_yard"] is None else "DEPARTED"
    return {"status": status, "record": record}


def get_containers_by_date_range(start_date: str, end_date: str):
    """Belirli bir tarih aralığında giriş yapan konteynerleri döner (iptal edilmiş kayıtlar hariç)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {_GATE_COLUMNS}
        FROM gate_transactions
        WHERE date(time_entered_yard) BETWEEN date(?) AND date(?)
          AND transaction_status != 'CANCEL'
        ORDER BY time_entered_yard ASC
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def list_containers_in_yard():
    """Şu anda limanda/sahada olan konteynerleri listeler (iptal edilmiş kayıtlar hariç)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {_GATE_COLUMNS}
        FROM gate_transactions
        WHERE time_exited_yard IS NULL AND transaction_status != 'CANCEL'
        ORDER BY time_entered_yard DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------------------------------------------------
# ADMIN: yeni konteyner kaydı ekleme / kayıt arama / kapatma / iptal etme
# Admin veri SİLEMEZ, sadece yeni kayıt ekleyebilir, açık bir kaydın çıkışını
# girebilir veya bir kaydı iptal (CANCEL) edebilir. Bu üç işlem dışında
# gate_transactions tablosuna dokunan başka bir yol yok.
# ---------------------------------------------------------

CONTAINER_NO_FULL_PATTERN = re.compile(r'^[A-Z]{4}\d{7}$')

TRANSACTION_TYPES = [
    "ReceiveExport", "DeliverImport", "DeliverEmpty",
    "ReceiveEmpty", "DrayOffExport", "DrayOffImport", "DeliverBreakBulk",
]
FREIGHT_KINDS = ["FCL", "MTY", "BBK"]

_ADMIN_COLUMNS = """
    id, container_no, time_entered_yard, time_exited_yard, transaction_status,
    loc_name, truck_visit_minutes_in_yard, transaction_type, damage, freight_kind
"""


def create_container_entry(
    container_no: str,
    time_entered_yard: str,
    transaction_type: str,
    freight_kind: str,
    loc_name: Optional[str] = None,
    damage: bool = False,
):
    container_no = container_no.strip().upper()
    if not CONTAINER_NO_FULL_PATTERN.match(container_no):
        raise HTTPException(status_code=400, detail="Konteyner no formatı geçersiz. Beklenen format: 4 harf + 7 rakam (örn. ABCD1234567).")
    if transaction_type not in TRANSACTION_TYPES:
        raise HTTPException(status_code=400, detail=f"Geçersiz işlem tipi. Geçerli değerler: {', '.join(TRANSACTION_TYPES)}")
    if freight_kind not in FREIGHT_KINDS:
        raise HTTPException(status_code=400, detail=f"Geçersiz yük tipi. Geçerli değerler: {', '.join(FREIGHT_KINDS)}")
    try:
        entered_dt = datetime.fromisoformat(time_entered_yard)
    except ValueError:
        raise HTTPException(status_code=400, detail="Giriş zamanı formatı geçersiz.")
    if entered_dt > datetime.now():
        raise HTTPException(status_code=400, detail="Giriş zamanı gelecekte bir zaman olamaz.")

    conn = get_connection()
    cursor = conn.cursor()

    # Bu konteynerin COMPLETE durumundaki tüm geçmiş kayıtlarına bak: herhangi
    # birinde çıkış (time_exited_yard) girilmemişse, konteyner hâlâ sahada
    # demektir — yeni bir giriş kaydı oluşturulmasına izin verilmez.
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM gate_transactions WHERE container_no = ? AND transaction_status = 'COMPLETE' AND time_exited_yard IS NULL",
        (container_no,),
    )
    open_count = cursor.fetchone()["cnt"]
    if open_count > 0:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"{container_no} için sahada hâlâ açık (çıkışı yapılmamış) bir kaydı var. Yeni giriş oluşturulamaz, önce mevcut kaydın çıkışı girilmeli.",
        )

    cursor.execute(
        """
        INSERT INTO gate_transactions
            (container_no, time_entered_yard, time_exited_yard, transaction_status,
             loc_name, truck_visit_minutes_in_yard, transaction_type, damage, freight_kind)
        VALUES (?, ?, NULL, 'COMPLETE', ?, NULL, ?, ?, ?)
        """,
        (container_no, time_entered_yard, loc_name, transaction_type, int(bool(damage)), freight_kind),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_gate_record_by_id(new_id)


def get_gate_record_by_id(record_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {_ADMIN_COLUMNS} FROM gate_transactions WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def search_container_records(container_no: str):
    container_no = container_no.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT {_ADMIN_COLUMNS}
        FROM gate_transactions
        WHERE container_no = ?
        ORDER BY time_entered_yard DESC
        """,
        (container_no,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def close_container_exit(record_id: int, time_exited_yard: str):
    record = get_gate_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    if record["transaction_status"] != "COMPLETE" or record["time_exited_yard"] is not None:
        raise HTTPException(status_code=400, detail="Bu kayıt zaten kapalı ya da iptal edilmiş, çıkış eklenemez.")

    entered = datetime.fromisoformat(record["time_entered_yard"])
    exited = datetime.fromisoformat(time_exited_yard)
    if exited <= entered:
        raise HTTPException(status_code=400, detail="Çıkış zamanı, giriş zamanından sonra olmalı.")

    minutes = round((exited - entered).total_seconds() / 60, 1)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE gate_transactions SET time_exited_yard = ?, truck_visit_minutes_in_yard = ? WHERE id = ?",
        (time_exited_yard, minutes, record_id),
    )
    conn.commit()
    conn.close()
    return get_gate_record_by_id(record_id)


def cancel_container_record(record_id: int):
    record = get_gate_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    if record["transaction_status"] == "CANCEL":
        raise HTTPException(status_code=400, detail="Bu kayıt zaten iptal edilmiş.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE gate_transactions SET transaction_status = 'CANCEL' WHERE id = ?",
        (record_id,),
    )
    conn.commit()
    conn.close()
    return get_gate_record_by_id(record_id)


def update_container_details(
    record_id: int,
    loc_name: Optional[str] = None,
    damage: Optional[bool] = None,
    freight_kind: Optional[str] = None,
):
    """Mevcut bir kaydın SADECE konum, hasar ve yük tipi bilgisini günceller.
    container_no, giriş/çıkış zamanları, işlem tipi ve durum burada asla
    değiştirilmez — bu alanlar zaman çizelgesi bütünlüğünü korur."""
    record = get_gate_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    if freight_kind is not None and freight_kind not in FREIGHT_KINDS:
        raise HTTPException(status_code=400, detail=f"Geçersiz yük tipi. Geçerli değerler: {', '.join(FREIGHT_KINDS)}")

    updates = []
    params = []
    if loc_name is not None:
        updates.append("loc_name = ?")
        params.append(loc_name)
    if damage is not None:
        updates.append("damage = ?")
        params.append(int(bool(damage)))
    if freight_kind is not None:
        updates.append("freight_kind = ?")
        params.append(freight_kind)

    if not updates:
        return record

    params.append(record_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE gate_transactions SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return get_gate_record_by_id(record_id)


AVAILABLE_FUNCTIONS = {
    "get_container_entry": get_container_entry,
    "get_container_exit": get_container_exit,
    "get_container_status": get_container_status,
    "get_containers_by_date_range": get_containers_by_date_range,
    "list_containers_in_yard": list_containers_in_yard,
}


class ChatMessage(BaseModel):
    role: str  # 'user' veya 'assistant'
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    session_id: Optional[int] = None
    language: Optional[str] = "tr"


@app.post("/api/chat")
def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    # Burada current_user doğrulanmış token payload'ını içerir.
    try:
        chat_user = resolve_chat_user(current_user)
        system_instruction = SYSTEM_INSTRUCTION_EN if request.language == "en" else SYSTEM_INSTRUCTION
        messages = [{"role": "system", "content": system_instruction}]

        # Önceki sohbet geçmişini ekle (hafıza için)
        for msg in request.history or []:
            messages.append({"role": msg.role, "content": msg.content})

        # Yeni kullanıcı mesajını ekle
        messages.append({"role": "user", "content": request.message})

        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=messages,
            tools=TOOLS,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                function_to_call = AVAILABLE_FUNCTIONS[function_name]
                function_result = function_to_call(**function_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_result, ensure_ascii=False, default=str),
                })
                

            second_response = client.chat.completions.create(
                model="gpt-oss-120b",
                messages=messages,
            )
            reply_text = second_response.choices[0].message.content or ""
            assistant_messages = (request.history or []) + [ChatMessage(role="user", content=request.message), ChatMessage(role="assistant", content=reply_text)]
            saved_session = save_chat_session(chat_user["id"], chat_user["username"], [{"role": msg.role, "content": msg.content} for msg in assistant_messages], request.session_id)
            return {"reply": reply_text, "session": saved_session}

        reply_text = response_message.content or ""
        assistant_messages = (request.history or []) + [ChatMessage(role="user", content=request.message), ChatMessage(role="assistant", content=reply_text)]
        saved_session = save_chat_session(chat_user["id"], chat_user["username"], [{"role": msg.role, "content": msg.content} for msg in assistant_messages], request.session_id)
        return {"reply": reply_text, "session": saved_session}

    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        # Dış servis yoğunluğu / rate-limit durumlarını daha kullanıcı-dostu ilet
        if '429' in msg or 'too_many_requests' in msg or 'queue_exceeded' in msg:
            raise HTTPException(status_code=503, detail="Dış LLM servisi şu anda yoğun. Birkaç saniye sonra tekrar deneyin.")
        raise HTTPException(status_code=500, detail=f"Bir hata oluştu: {msg}")


@app.get("/api/chat/sessions")
def list_chat_sessions_api(current_user: dict = Depends(get_current_user)):
    chat_user = resolve_chat_user(current_user)
    return {"sessions": list_chat_sessions(chat_user["id"])}


@app.delete("/api/chat/sessions/{session_id}")
def delete_chat_session_api(session_id: int, current_user: dict = Depends(get_current_user)):
    chat_user = resolve_chat_user(current_user)
    deleted = delete_chat_session(session_id, chat_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Sohbet geçmişi bulunamadı.")
    return {"status": "ok"}


class RenameChatSessionRequest(BaseModel):
    title: str


@app.patch("/api/chat/sessions/{session_id}")
def rename_chat_session_api(
    session_id: int,
    payload: RenameChatSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    chat_user = resolve_chat_user(current_user)
    new_title = payload.title.strip()[:40]
    if not new_title:
        raise HTTPException(status_code=400, detail="Başlık boş olamaz.")

    session = rename_chat_session(session_id, chat_user["id"], new_title)
    if not session:
        raise HTTPException(status_code=404, detail="Sohbet geçmişi bulunamadı.")
    return {"session": session}