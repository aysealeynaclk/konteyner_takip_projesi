"""
Konteyner Takip - Backend API
Bu aşamada henüz LLM yok - sadece düz Python fonksiyonlarıyla
veritabanı sorguları yapılıyor ve test endpoint'leriyle doğrulanıyor.

LLM entegrasyonu bir sonraki adımda bu fonksiyonların üzerine eklenecek.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime
from pathlib import Path

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



def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Sonuçları dict gibi kullanabilmek için
    return conn


# ---------------------------------------------------------
# SORGU FONKSİYONLARI (ileride LLM bunlardan birini seçecek)
# ---------------------------------------------------------

def get_container_entry(container_no: str):
    """Bir konteynerin EN SON giriş kaydını döner."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM gate_transactions
        WHERE container_no = ? AND transaction_type = 'IN'
        ORDER BY gate_time DESC
        LIMIT 1
    """, (container_no,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_container_exit(container_no: str):
    """Bir konteynerin EN SON çıkış kaydını döner."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM gate_transactions
        WHERE container_no = ? AND transaction_type = 'OUT'
        ORDER BY gate_time DESC
        LIMIT 1
    """, (container_no,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_container_status(container_no: str):
    """

    Belirli bir konteyner numarasının limandaki güncel durumunu (limanda mı yoksa çıkış mı yaptı) sorgular.
    Parametre: container_no (str) - Sorgulanacak konteynerin benzersiz numarası.

    Bir konteynerin şu anki durumunu belirler:
    - Son hareketi IN ise -> hala limanda
    - Son hareketi OUT ise -> limandan çıkmış
    - Hiç kaydı yoksa -> bulunamadı
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM gate_transactions
        WHERE container_no = ?
        ORDER BY gate_time DESC
        LIMIT 1
    """, (container_no,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"status": "NOT_FOUND", "container_no": container_no}

    last_record = dict(row)
    status = "IN_YARD" if last_record["transaction_type"] == "IN" else "DEPARTED"
    return {"status": status, "last_record": last_record}


def get_containers_by_date_range(start_date: str, end_date: str):
    """Belirli bir tarih aralığındaki tüm hareketleri döner."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM gate_transactions
        WHERE date(gate_time) BETWEEN date(?) AND date(?)
        ORDER BY gate_time ASC
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_containers_in_yard():
    """Şu anda limanda olan (son hareketi IN olan) tüm konteynerleri listeler."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT container_no, MAX(gate_time) as last_time, transaction_type
        FROM gate_transactions
        GROUP BY container_no
        HAVING transaction_type = 'IN'
    """)
    # Not: Bu sorgu basit bir yaklaşım - GROUP BY ile MAX(gate_time) alıp
    # o satırın transaction_type'ının IN olup olmadığına bakıyoruz.
    # SQLite'ta GROUP BY + MAX kombinasyonu genelde doğru satırı döner
    # ama garanti değildir; ölçek büyürse bunu düzelteceğiz.
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


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
çıkmış mı) veya belirli tarih aralığındaki hareketler hakkında Türkçe sorular soracak.

Uygun fonksiyonu çağırarak veritabanından veriyi çek, sonra kullanıcıya
doğal, akıcı ve insana hitap eden bir Türkçe cümleyle açıkla.

İfade kuralları:
- Tarih/saatleri okunaklı yaz (örn. "5 Temmuz 2026, saat 14:32")
- Veritabanı sütun adlarını (örn. "time_entered_yard") ham haliyle asla gösterme
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
"""

# Cerebras/OpenAI formatı, fonksiyon şemalarını JSON olarak elle tanımlıyoruz
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_container_entry",
            "description": "Bir konteynerin en son giriş (IN) kaydını getirir.",
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
            "description": "Bir konteynerin en son çıkış (OUT) kaydını getirir.",
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
            "description": "Bir konteynerin şu anki durumunu (limanda mı, çıkmış mı) getirir.",
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
            "description": "Belirli bir tarih aralığındaki tüm giriş/çıkış hareketlerini getirir.",
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
            "description": "Şu anda limanda olan tüm konteynerleri listeler.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# Fonksiyon isimlerini gerçek Python fonksiyonlarına eşliyoruz



#--------------------------------------------------------------
#
#--------------------------------------------------------------

def get_container_entry(container_no: str):
    """Bir konteynerin limana/sahaya giriş zamanını döner (iptal edilmiş kayıtlar hariç)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT container_no, time_entered_yard
        FROM gate_transactions
        WHERE container_no = ? AND transaction_status != 'CANCEL'
        ORDER BY time_entered_yard DESC
        LIMIT 1
    """, (container_no,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_container_exit(container_no: str):
    """Bir konteynerin limandan/sahadan çıkış zamanını döner (iptal edilmiş kayıtlar hariç)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT container_no, time_exited_yard
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
    cursor.execute("""
        SELECT container_no, time_entered_yard, time_exited_yard
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
    cursor.execute("""
        SELECT container_no, time_entered_yard, time_exited_yard
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
    cursor.execute("""
        SELECT container_no, time_entered_yard
        FROM gate_transactions
        WHERE time_exited_yard IS NULL AND transaction_status != 'CANCEL'
        ORDER BY time_entered_yard DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


AVAILABLE_FUNCTIONS = {
    "get_container_entry": get_container_entry,
    "get_container_exit": get_container_exit,
    "get_container_status": get_container_status,
    "get_containers_by_date_range": get_containers_by_date_range,
    "list_containers_in_yard": list_containers_in_yard,
}


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": request.message},
        ]

        # 1. adım: Model hangi fonksiyonu çağıracağına karar veriyor
        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=messages,
            tools=TOOLS,
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)

            # 2. adım: Her bir fonksiyon çağrısını gerçekten çalıştır
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

            # 3. adım: Sonucu modele geri ver, doğal dil cevabı üretsin
            second_response = client.chat.completions.create(
                model="gpt-oss-120b",
                messages=messages,
            )
            return {"reply": second_response.choices[0].message.content}

        return {"reply": response_message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bir hata oluştu: {str(e)}")


