# -*- coding: utf-8 -*-
"""
================================================================================
NEXA CRM PRO — GENEL İŞ TAKİP & YAPILACAKLAR (TASKS & NOTES) SİSTEMİ
================================================================================
- SQLite tabanlı güvenilir kalıcı depolama (data/intelligence.db)
- Gemini Multimodal Audio ile Speech-to-Text (Türkçe ses kaydı -> Yapılandırılmış Görev)
- Gemini 3.8 Flash TTS (Text-to-Speech) ile Doğal Ses Sentezi ve Günlük Sesli Brifing
- Kanban Panosu, Liste / Tablo, Yapılacaklar Kontrol Listesi ve Not Kartları desteği
- Flask Blueprint ve REST API entegrasyonu
================================================================================
"""

import os
import re
import json
import sqlite3
import datetime
import base64
import traceback
from typing import Optional, Dict, Any, List, Tuple

import requests
from flask import Blueprint, request, jsonify, Response

# Google GenAI SDK (v3.0.0+)
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception as e:
    GENAI_AVAILABLE = False
    print(f"⚠ google-genai yüklenirken uyarı: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "intelligence.db")
ENV_PATH = os.path.join(BASE_DIR, ".env")

crm_tasks_bp = Blueprint("crm_tasks", __name__)

# ── Desteklenen Gemini TTS Sesleri (Resmi Google AI Studio Dokümantasyonu) ──
AVAILABLE_VOICES = [
    {"id": "Kore", "name": "Kore", "gender": "Kadın", "tone": "Kararlı & Profesyonel", "desc": "Net, kurumsal ve dengeli ses tonu (Varsayılan)"},
    {"id": "Zephyr", "name": "Zephyr", "gender": "Kadın", "tone": "Canlı & Enerjik", "desc": "Parlak, akıcı ve motive edici ton"},
    {"id": "Puck", "name": "Puck", "gender": "Erkek", "tone": "Samimi & Pozitif", "desc": "Dinamik, sıcak ve enerjik erkek sesi"},
    {"id": "Aoede", "name": "Aoede", "gender": "Kadın", "tone": "Ferah & Doğal", "desc": "Rahatlatıcı, berrak ve akıcı kadın sesi"},
    {"id": "Charon", "name": "Charon", "gender": "Erkek", "tone": "Bilgilendirici & Sakin", "desc": "Otoriter, güven veren brifing tonu"},
    {"id": "Despina", "name": "Despina", "gender": "Kadın", "tone": "Pürüzsüz & Sıcak", "desc": "Zarif, premium ve yumuşak tını"},
    {"id": "Fenrir", "name": "Fenrir", "gender": "Erkek", "tone": "Heyecanlı & Güçlü", "desc": "Girişimci ve yüksek odaklı ses"},
    {"id": "Sulafat", "name": "Sulafat", "gender": "Kadın", "tone": "Sıcak & Dostane", "desc": "Müşteri ilişkileri ve samimi görüşme tonu"}
]

# ── Desteklenen Kategoriler ──
TASK_CATEGORIES = [
    {"id": "Genel", "name": "Genel İşler", "icon": "fas fa-briefcase", "color": "#64748b"},
    {"id": "Müşteri Takip", "name": "Müşteri Takip & Görüşme", "icon": "fas fa-user-tie", "color": "#0ea5e9"},
    {"id": "Portföy & Yer Gösterme", "name": "Portföy & Yer Gösterme", "icon": "fas fa-home", "color": "#f59e0b"},
    {"id": "Tapu & Belediye & Hukuk", "name": "Tapu & Belediye & Hukuk", "icon": "fas fa-landmark", "color": "#8b5cf6"},
    {"id": "Sözleşme & Kapora", "name": "Sözleşme & Kapora", "icon": "fas fa-file-contract", "color": "#10b981"},
    {"id": "Pazarlama & Reklam", "name": "Pazarlama & Sosyal Medya", "icon": "fas fa-bullhorn", "color": "#ec4899"},
    {"id": "Finans & Muhasebe", "name": "Finans & Komisyon", "icon": "fas fa-coins", "color": "#eab308"}
]


ADMIN_UIDS = [
    'L8sPnXFGTpbaaAmGR2MdahJe9O32',
    'RnHhsj3K4VSWRY4cjc3Pc09JMFn2',
    'GP3Eiiz0cvPgibGnXPoNElCeWzW2',
    'N24DQxhNQHVYGHoX9bBi52mINYi1',
    'URaEvk4heBZmwTAIPbeDTNziqDx1'
]

def get_db_admin():
    """Firebase Admin SDK Firestore istemcisini güvenli şekilde döndürür."""
    try:
        from app import db_admin as active_db_admin, init_firebase_admin
        if active_db_admin is None:
            init_firebase_admin()
        from app import db_admin as resolved_db
        if resolved_db:
            return resolved_db
    except Exception:
        pass
    try:
        import firebase_admin
        from firebase_admin import firestore
        if firebase_admin._apps:
            return firestore.client()
    except Exception:
        pass
    return None

def get_db():
    """SQLite veritabanı bağlantısı açar (WAL modunda, row_factory ile)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_tasks_db():
    """Görev ve notlar tablosunu oluşturur ve boşsa örnek gerçekçi verileri yükler."""
    with get_db() as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crm_tasks_notes (
                id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT 'default',
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                category TEXT DEFAULT 'Genel',
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'todo',
                due_date TEXT DEFAULT '',
                is_pinned INTEGER DEFAULT 0,
                checklist TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                related_to TEXT DEFAULT '',
                voice_transcript TEXT DEFAULT '',
                audio_url TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON crm_tasks_notes(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON crm_tasks_notes(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON crm_tasks_notes(due_date)")
        con.commit()

        # Boşsa örnek gerçekçi verileri ekle
        cur.execute("SELECT COUNT(*) FROM crm_tasks_notes")
        count = cur.fetchone()[0]
        if count == 0:
            _seed_sample_tasks(con)


def _seed_sample_tasks(con):
    """Gayrimenkul danışmanlığına özel zengin örnek görevler tohumlar."""
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    next_week_str = (now + datetime.timedelta(days=4)).strftime("%Y-%m-%d")

    samples = [
        {
            "id": f"task_{int(now.timestamp())}_1",
            "title": "Kadıköy Moda 3+1 Daire - Tapu Harcı ve Devir Randevusu",
            "content": "Kadıköy Tapu Müdürlüğü 2. Kısım için randevu alındı. Harç ödemesi bankadan teyit edilecek ve mülk sahibi ile alıcı SMS ile bilgilendirilecek.",
            "category": "Tapu & Belediye & Hukuk",
            "priority": "urgent",
            "status": "todo",
            "due_date": f"{today_str}T14:30",
            "is_pinned": 1,
            "checklist": json.dumps([
                {"text": "Döner sermaye ve tapu harç makbuzlarını kontrol et", "done": True},
                {"text": "Kadıköy Belediyesi rayiç bedel ve borcu yoktur yazısını al", "done": False},
                {"text": "Alıcı ve satıcıya randevu saati ve gerekli belgeleri SMS/WhatsApp ilet", "done": False}
            ], ensure_ascii=False),
            "tags": json.dumps(["tapu", "kadikoy", "moda", "devir"], ensure_ascii=False),
            "related_to": "Ahmet Yılmaz (Alıcı) & Selim Kaya (Satıcı)",
            "voice_transcript": "Kadıköy Moda'daki dairenin tapu randevusu bugün saat 14:30'da. Harç makbuzları hazır, belediye rayiç bedel belgesi alınıp taraflara SMS çekilecek.",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        {
            "id": f"task_{int(now.timestamp())}_2",
            "title": "Suadiye Sahil Portföyü - Profesyonel Drone & İç Mekan Fotoğraf Çekimi",
            "content": "Portföye yeni alınan 4+1 deniz manzaralı lüks konutun pazarlama materyalleri için profesyonel çekim yapılacak. Sanal tur 360 linki oluşturulacak.",
            "category": "Pazarlama & Reklam",
            "priority": "high",
            "status": "in_progress",
            "due_date": f"{tomorrow_str}T11:00",
            "is_pinned": 1,
            "checklist": json.dumps([
                {"text": "Fotoğrafçı ile çekim saati ve ışık açısını teyit et", "done": True},
                {"text": "Mülk sahibine ev hazırlama rehberi gönder", "done": True},
                {"text": "Drone uçuş izinleri ve sahil çekim planını hazırla", "done": False},
                {"text": "Sanal tur ve YouTube 4K video teaser kurgusu yaptır", "done": False}
            ], ensure_ascii=False),
            "tags": json.dumps(["suadiye", "drone", "fotograf", "pazarlama"], ensure_ascii=False),
            "related_to": "Suadiye Sahil Konutları No:12",
            "voice_transcript": "Suadiye'deki 4+1 için yarın saat 11'de drone ve iç mekan çekimi var. Fotoğrafçı teyit edildi, video teaseri hazırlanacak.",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        {
            "id": f"task_{int(now.timestamp())}_3",
            "title": "Bağdat Caddesi Ticari Dükkan - Ekspertiz & Değerleme Raporu İncelemesi",
            "content": "SPK lisanslı değerleme uzmanından gelen rapor incelenecek. m² birim fiyatı ve amortisman süresi yatırımcı sunumuna işlenecek.",
            "category": "Finans & Muhasebe",
            "priority": "medium",
            "status": "in_progress",
            "due_date": tomorrow_str,
            "is_pinned": 0,
            "checklist": json.dumps([
                {"text": "Raporu indir ve piyasa emsal değerleriyle karşılaştır", "done": True},
                {"text": "Aylık net kira getirisi ve ROI projeksiyonunu güncelle", "done": False},
                {"text": "Mülk sahibine özet değerleme brifingi hazırla", "done": False}
            ], ensure_ascii=False),
            "tags": json.dumps(["bagdatcaddesi", "ticari", "ekspertiz", "degerleme"], ensure_ascii=False),
            "related_to": "Erenköy Dükkan Portföyü",
            "voice_transcript": "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        {
            "id": f"task_{int(now.timestamp())}_4",
            "title": "Ataşehir Residence 2+1 - Teklif ve Kapora Protokolü Hazırlığı",
            "content": "Alıcı adayı Canan Hanım 7.250.000 TL yazılı teklif sundu. Mülk sahibi ile pazarlık görüşmesi tamamlandı, kapora sözleşmesi düzenlenecek.",
            "category": "Sözleşme & Kapora",
            "priority": "high",
            "status": "review",
            "due_date": next_week_str,
            "is_pinned": 0,
            "checklist": json.dumps([
                {"text": "Standart CB Gayrimenkul kapora protokolünü hazırla", "done": False},
                {"text": "Tarafların kimlik ve vekaletname kontrollerini yap", "done": False},
                {"text": "Banka bloke çek veya havale açıklamasını netleştir", "done": False}
            ], ensure_ascii=False),
            "tags": json.dumps(["atasehir", "kapora", "sozlesme", "teklif"], ensure_ascii=False),
            "related_to": "Canan Demir (Alıcı)",
            "voice_transcript": "Canan Hanım'ın Ataşehir residence için verdiği 7.250 teklifi kabul edildi. Kapora sözleşmesi hazırlanıp taraflara iletilecek.",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        {
            "id": f"task_{int(now.timestamp())}_5",
            "title": "Haftalık Sahibinden & HepsiEmlak İlan Fiyat Güncellemeleri",
            "content": "Portföyümüzdeki tüm aktif ilanların liste fiyatları kontrol edildi, bölge emsal değişimlerine göre indirimler sisteme girildi.",
            "category": "Portföy & Yer Gösterme",
            "priority": "low",
            "status": "done",
            "due_date": today_str,
            "is_pinned": 0,
            "checklist": json.dumps([
                {"text": "Fiyatı güncellenen 3 ilanın afişini yenile", "done": True},
                {"text": "Sosyal medya ve WhatsApp durumunda haftanın fırsatlarını paylaş", "done": True}
            ], ensure_ascii=False),
            "tags": json.dumps(["portfoy", "fiyat", "guncelleme"], ensure_ascii=False),
            "related_to": "Tüm Aktif Portföyler",
            "voice_transcript": "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
    ]

    cur = con.cursor()
    for s in samples:
        cur.execute("""
            INSERT INTO crm_tasks_notes (
                id, user_id, title, content, category, priority, status,
                due_date, is_pinned, checklist, tags, related_to,
                voice_transcript, audio_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s["id"], "default", s["title"], s["content"], s["category"],
            s["priority"], s["status"], s["due_date"], s["is_pinned"],
            s["checklist"], s["tags"], s["related_to"], s["voice_transcript"],
            "", s["created_at"], s["updated_at"]
        ))
    con.commit()


# ==============================================================================
# CRUD VE FİLTRELEME İŞLEMLERİ
# ==============================================================================

def list_tasks(status: Optional[str] = None,
               category: Optional[str] = None,
               priority: Optional[str] = None,
               search: Optional[str] = None,
               user_id: Optional[str] = None,
               due_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Görevleri ve notları listeler (filtreleme ve arama destekli)."""
    init_tasks_db()
    with get_db() as con:
        cur = con.cursor()
        query = "SELECT * FROM crm_tasks_notes WHERE 1=1"
        params = []

        if user_id and user_id != "all":
            query += " AND (user_id = ? OR user_id = 'default')"
            params.append(user_id)

        if status and status != "all":
            query += " AND status = ?"
            params.append(status)

        if category and category != "all":
            query += " AND category = ?"
            params.append(category)

        if priority and priority != "all":
            query += " AND priority = ?"
            params.append(priority)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ? OR related_to LIKE ?)"
            params.extend([term, term, term, term])

        if due_date and due_date.strip():
            query += " AND due_date LIKE ?"
            params.append(f"{due_date.strip()}%")

        # Sabitlenenler en başta, sonra son tarihe göre, sonra en yeniler
        query += " ORDER BY is_pinned DESC, CASE WHEN due_date != '' THEN 0 ELSE 1 END, due_date ASC, updated_at DESC"

        cur.execute(query, params)
        rows = cur.fetchall()

        results = []
        for r in rows:
            d = dict(r)
            try:
                d["checklist"] = json.loads(d["checklist"]) if d.get("checklist") else []
            except Exception:
                d["checklist"] = []
            try:
                d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
            except Exception:
                d["tags"] = []
            results.append(d)

        # Dual-persistence: Stream from Firestore to guarantee 100% sync
        db_fs = get_db_admin()
        if db_fs:
            try:
                target_uid = user_id if user_id and user_id != 'all' and user_id != 'default' else ADMIN_UIDS[0]
                fs_stream = db_fs.collection("users").document(target_uid).collection("tasks").stream()
                fs_docs = [doc.to_dict() for doc in fs_stream]
                if not fs_docs and target_uid == ADMIN_UIDS[0]:
                    for alt_uid in ADMIN_UIDS[1:]:
                        alt_stream = db_fs.collection("users").document(alt_uid).collection("tasks").stream()
                        alt_docs = [doc.to_dict() for doc in alt_stream]
                        if alt_docs:
                            fs_docs = alt_docs
                            break
                if fs_docs:
                    existing_ids = {r["id"] for r in results}
                    for fd in fs_docs:
                        if fd and fd.get("id") and fd["id"] not in existing_ids:
                            results.append(fd)
                            # Backfill into SQLite
                            try:
                                now_iso = datetime.datetime.now().isoformat()
                                cur.execute("""
                                    INSERT OR REPLACE INTO crm_tasks_notes (
                                        id, user_id, title, content, category, priority, status,
                                        due_date, is_pinned, checklist, tags, related_to,
                                        voice_transcript, audio_url, created_at, updated_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    fd["id"], fd.get("user_id", "default"), fd.get("title", ""),
                                    fd.get("content", ""), fd.get("category", "Genel"),
                                    fd.get("priority", "medium"), fd.get("status", "todo"),
                                    fd.get("due_date", ""), 1 if fd.get("is_pinned") else 0,
                                    json.dumps(fd.get("checklist", []), ensure_ascii=False),
                                    json.dumps(fd.get("tags", []), ensure_ascii=False),
                                    fd.get("related_to", ""), fd.get("voice_transcript", ""),
                                    fd.get("audio_url", ""), fd.get("created_at", now_iso), fd.get("updated_at", now_iso)
                                ))
                                con.commit()
                            except Exception:
                                pass
            except Exception as fs_err:
                print(f"⚠ Firestore list_tasks stream warning: {fs_err}")

        return results


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Tekil bir görevi ID ile çeker."""
    init_tasks_db()
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM crm_tasks_notes WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["checklist"] = json.loads(d["checklist"]) if d.get("checklist") else []
        except Exception:
            d["checklist"] = []
        try:
            d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
        except Exception:
            d["tags"] = []
        return d


def create_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """Yeni görev veya not oluşturur."""
    init_tasks_db()
    now = datetime.datetime.now().isoformat()
    task_id = data.get("id") or f"task_{int(datetime.datetime.now().timestamp() * 1000)}"

    title = (data.get("title") or "Yeni Görev").strip()
    content = (data.get("content") or "").strip()
    category = data.get("category") or "Genel"
    priority = data.get("priority") or "medium"
    status = data.get("status") or "todo"
    due_date = data.get("due_date") or ""
    is_pinned = 1 if data.get("is_pinned") else 0
    user_id = data.get("user_id") or "default"
    related_to = (data.get("related_to") or "").strip()
    voice_transcript = data.get("voice_transcript") or ""
    audio_url = data.get("audio_url") or ""

    checklist = data.get("checklist") or []
    if isinstance(checklist, list):
        checklist_str = json.dumps(checklist, ensure_ascii=False)
    else:
        checklist_str = str(checklist)

    tags = data.get("tags") or []
    if isinstance(tags, list):
        tags_str = json.dumps(tags, ensure_ascii=False)
    else:
        tags_str = str(tags)

    with get_db() as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO crm_tasks_notes (
                id, user_id, title, content, category, priority, status,
                due_date, is_pinned, checklist, tags, related_to,
                voice_transcript, audio_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id, user_id, title, content, category, priority, status,
            due_date, is_pinned, checklist_str, tags_str, related_to,
            voice_transcript, audio_url, now, now
        ))
        con.commit()

    # Dual-persistence: Save to Firebase Firestore
    db_fs = get_db_admin()
    if db_fs:
        try:
            target_uid = user_id if user_id and user_id != 'default' else ADMIN_UIDS[0]
            fs_doc = {
                "id": task_id,
                "user_id": target_uid,
                "title": title,
                "content": content,
                "category": category,
                "priority": priority,
                "status": status,
                "due_date": due_date,
                "is_pinned": bool(is_pinned),
                "checklist": checklist if isinstance(checklist, list) else [],
                "tags": tags if isinstance(tags, list) else [],
                "related_to": related_to,
                "voice_transcript": voice_transcript,
                "audio_url": audio_url,
                "created_at": now,
                "updated_at": now
            }
            db_fs.collection("users").document(target_uid).collection("tasks").document(task_id).set(fs_doc, merge=True)
        except Exception as fs_err:
            print(f"⚠ Firestore create_task warning: {fs_err}")

    return get_task(task_id)


def update_task(task_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mevcut görevi günceller."""
    init_tasks_db()
    existing = get_task(task_id)
    if not existing:
        return None

    now = datetime.datetime.now().isoformat()

    title = data.get("title", existing["title"])
    content = data.get("content", existing["content"])
    category = data.get("category", existing["category"])
    priority = data.get("priority", existing["priority"])
    status = data.get("status", existing["status"])
    due_date = data.get("due_date", existing["due_date"])
    is_pinned = 1 if data.get("is_pinned", existing["is_pinned"]) else 0
    related_to = data.get("related_to", existing["related_to"])

    checklist = data.get("checklist", existing["checklist"])
    if isinstance(checklist, list):
        checklist_str = json.dumps(checklist, ensure_ascii=False)
    else:
        checklist_str = str(checklist)

    tags = data.get("tags", existing["tags"])
    if isinstance(tags, list):
        tags_str = json.dumps(tags, ensure_ascii=False)
    else:
        tags_str = str(tags)

    with get_db() as con:
        cur = con.cursor()
        cur.execute("""
            UPDATE crm_tasks_notes SET
                title = ?, content = ?, category = ?, priority = ?, status = ?,
                due_date = ?, is_pinned = ?, checklist = ?, tags = ?,
                related_to = ?, updated_at = ?
            WHERE id = ?
        """, (
            title, content, category, priority, status,
            due_date, is_pinned, checklist_str, tags_str,
            related_to, now, task_id
        ))
        con.commit()

    # Dual-persistence: Update in Firebase Firestore
    db_fs = get_db_admin()
    if db_fs:
        try:
            target_uid = existing.get("user_id")
            if not target_uid or target_uid == 'default':
                target_uid = ADMIN_UIDS[0]
            fs_update_doc = {
                "id": task_id,
                "title": title,
                "content": content,
                "category": category,
                "priority": priority,
                "status": status,
                "due_date": due_date,
                "is_pinned": bool(is_pinned),
                "checklist": checklist if isinstance(checklist, list) else [],
                "tags": tags if isinstance(tags, list) else [],
                "related_to": related_to,
                "updated_at": now
            }
            db_fs.collection("users").document(target_uid).collection("tasks").document(task_id).set(fs_update_doc, merge=True)
        except Exception as fs_err:
            print(f"⚠ Firestore update_task warning: {fs_err}")

    return get_task(task_id)


def delete_task(task_id: str) -> bool:
    """Görevi siler (SQLite + Firestore)."""
    init_tasks_db()
    deleted = False
    with get_db() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM crm_tasks_notes WHERE id = ?", (task_id,))
        con.commit()
        deleted = cur.rowcount > 0

    # Dual-persistence: Delete from Firebase Firestore across admin UIDs
    db_fs = get_db_admin()
    if db_fs:
        for uid in ADMIN_UIDS:
            try:
                db_fs.collection("users").document(uid).collection("tasks").document(task_id).delete()
            except Exception:
                pass

    return deleted


def toggle_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Görevin tamamlandı durumunu hızlıca değiştirir (todo <-> done)."""
    task = get_task(task_id)
    if not task:
        return None

    new_status = "todo" if task["status"] == "done" else "done"
    return update_task(task_id, {"status": new_status})


def toggle_checklist_item(task_id: str, item_index: int) -> Optional[Dict[str, Any]]:
    """Göreve ait alt maddelerden birinin tamamlanma durumunu değiştirir."""
    task = get_task(task_id)
    if not task:
        return None

    checklist = task.get("checklist", [])
    if 0 <= item_index < len(checklist):
        checklist[item_index]["done"] = not checklist[item_index].get("done", False)

        all_done = len(checklist) > 0 and all(item.get("done") for item in checklist)
        new_status = task["status"]
        if all_done and task["status"] != "done":
            new_status = "done"
        elif not all_done and task["status"] == "done":
            new_status = "in_progress"

        return update_task(task_id, {"checklist": checklist, "status": new_status})

    return task


def get_task_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Görev ve iş takip istatistiklerini hesaplar."""
    init_tasks_db()
    tasks = list_tasks(user_id=user_id)

    total = len(tasks)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    todo_count = 0
    in_progress_count = 0
    review_count = 0
    done_count = 0
    urgent_count = 0
    due_today_count = 0
    overdue_count = 0

    for t in tasks:
        s = t.get("status")
        if s == "done":
            done_count += 1
        elif s == "in_progress":
            in_progress_count += 1
        elif s == "review":
            review_count += 1
        else:
            todo_count += 1

        if t.get("priority") in ("urgent", "high") and s != "done":
            urgent_count += 1

        due = t.get("due_date", "")
        if due and s != "done":
            due_day = due.split("T")[0]
            if due_day == today_str:
                due_today_count += 1
            elif due_day < today_str:
                overdue_count += 1

    completion_rate = int((done_count / total * 100)) if total > 0 else 0

    return {
        "total": total,
        "todo": todo_count,
        "in_progress": in_progress_count,
        "review": review_count,
        "done": done_count,
        "urgent": urgent_count,
        "due_today": due_today_count,
        "overdue": overdue_count,
        "completion_rate": completion_rate
    }


# ==============================================================================
# GEMINI API: SPEECH-TO-TEXT & AKILLI GÖREV ÇIKARICI
# ==============================================================================

def get_effective_gemini_key() -> str:
    """GEMINI_API_KEY ortam değişkenini veya .env dosyasındaki anahtarı döndürür."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ["GEMINI_API_KEY"] = val
                            return val
        except Exception:
            pass

    return ""


def save_gemini_key(new_key: str) -> bool:
    """Yeni Gemini API anahtarını hem .env dosyasına hem de geçerli çalışma ortamına kaydeder."""
    new_key = new_key.strip()
    os.environ["GEMINI_API_KEY"] = new_key

    try:
        lines = []
        key_found = False
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={new_key}\n")
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            new_lines.append(f"\n# Google Gemini API Key\nGEMINI_API_KEY={new_key}\n")

        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True
    except Exception as e:
        print(f"❌ .env güncellenirken hata: {e}")
        return False


def process_voice_task(audio_bytes: bytes, mime_type: str = "audio/webm") -> Dict[str, Any]:
    """
    Kullanıcının mikrofon kaydını Gemini Multimodal Audio ile işler.
    1. Konuşulan Türkçe metni tam olarak çözer (Speech to Text).
    2. CRM için yapılandırılmış görev nesnesi üretir (Başlık, Açıklama, Öncelik, Kategori, Son Tarih, Alt Maddeler).
    """
    api_key = get_effective_gemini_key()
    if not api_key:
        return {
            "ok": False,
            "error": "Gemini API anahtarı tanımlı değil. Lütfen ayarlardan Gemini API anahtarınızı girin.",
            "needs_key": True
        }

    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d %A (%d.%m.%Y)")

    system_prompt = f"""Sen Coldwell Banker VIP gayrimenkul danışmanları için çalışan üst düzey bir dijital sekreter ve yapay zeka asistanısın.
Kullanıcının gönderdiği Türkçe ses kaydını pürüzsüzce dinle ve iki aşamalı bir işlem gerçekleştir:

BUGÜNÜN TARİHİ: {today_str}

GÖREVLERİN:
1. SESİ METNE ÇEVİR (Speech-to-Text):
   - Konuşulan sözleri hiçbir kelime atlamadan, Türkçe dilbilgisi kurallarına uygun, temiz ve eksiksiz bir metne dök (transcript).
   - Gayrimenkul terimlerini doğru yaz (örn: tapu, kat mülkiyeti, iskan, ipotek, rayiç bedel, amortisman, kapora, ekspertiz, vb.).

2. METNİ YAPILANDIRILMIŞ BİR CRM İŞ TAKİP / GÖREVİNE DÖNÜŞTÜR:
   - title: Görevi özetleyen net, profesyonel ve vurucu bir başlık (Maksimum 6-8 kelime).
   - content: Ses kaydındaki detayları içeren, okunaklı, profesyonel not metni veya paragraf.
   - category: Görevin konusuna göre aşağıdaki listeden EN UYGUN olanı seç:
     ['Genel', 'Müşteri Takip', 'Portföy & Yer Gösterme', 'Tapu & Belediye & Hukuk', 'Sözleşme & Kapora', 'Pazarlama & Reklam', 'Finans & Muhasebe']
   - priority: Önem ve aciliyet derecesi:
     ['urgent' (Acil/Kritik), 'high' (Yüksek), 'medium' (Normal), 'low' (Düşük)]
   - due_date: Ses kaydında 'yarın', 'pazartesi', 'saat 14'te', '2 gün sonra', 'ayın 15'inde' gibi zaman/tarih ifadeleri varsa, {today_str} referansına göre hesaplayıp 'YYYY-MM-DD' veya saat varsa 'YYYY-MM-DDTHH:MM' formatında ISO string ver. Belirli bir zaman belirtilmemişse boş string ('') ver.
   - checklist: Eğer konuşmada birden fazla yapılacak iş, madde veya alt adım sayıldıysa bunları `[{{"text": "adım açıklaması", "done": false}}]` şeklinde dizi olarak çıkar. Tek bir görevse boş dizi `[]` ver.
   - tags: Görevle ilgili 2-4 adet anahtar kelime/etiket (küçük harf, örn: ['kadikoy', 'tapu', 'ahmet-bey']).
   - related_to: Ses kaydında geçen müşteri adı, portföy veya kurum adı (örn: 'Ahmet Bey', 'Kadıköy Tapu Müd.'). Yoksa boş bırak.

DÖNÜŞ FORMATI:
SADECE ve SADECE aşağıdaki JSON şemasına uygun saf JSON döndür. Markdown backtick (```json) veya ekstra açıklama yazma:
{{
  "transcript": "kullanıcının söylediği ham Türkçe metin",
  "title": "Görev Başlığı",
  "content": "Görev açıklaması ve notlar",
  "category": "Tapu & Belediye & Hukuk",
  "priority": "high",
  "due_date": "2026-11-08T14:00",
  "checklist": [
    {{"text": "Alt madde 1", "done": false}},
    {{"text": "Alt madde 2", "done": false}}
  ],
  "tags": ["tapu", "harc", "randevu"],
  "related_to": "Ahmet Bey"
}}
"""

    # 1. Öncelik: google-genai SDK 3.0.0
    if GENAI_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            prompt_part = types.Part.from_text(text=system_prompt)

            candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[audio_part, prompt_part],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2
                        )
                    )
                    raw_text = response.text or ""
                    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
                    cleaned = re.sub(r"```$", "", cleaned.strip())
                    parsed = json.loads(cleaned)
                    return {"ok": True, "data": parsed, "model": model_name}
                except Exception as m_err:
                    print(f"⚠ Model {model_name} ses analiz denemesi: {m_err}")
                    continue

        except Exception as sdk_err:
            print(f"⚠ SDK ile ses analizinde istisna: {sdk_err}, REST API fallback deneniyor...")

    # 2. Fallback: REST API
    try:
        b64_data = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "contents": [{
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": b64_data}},
                    {"text": system_prompt}
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=45)
            if res.status_code == 200:
                data = res.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])
                text_out = parts[0].get("text", "")
                cleaned = re.sub(r"^```json\s*", "", text_out.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"```$", "", cleaned.strip())
                parsed = json.loads(cleaned)
                return {"ok": True, "data": parsed, "model": m}
            else:
                print(f"⚠ REST {m} hata: {res.status_code} - {res.text[:200]}")

        return {"ok": False, "error": "Gemini API ses kaydını işleyemedi. Lütfen API anahtarınızı kontrol edin."}

    except Exception as e:
        return {"ok": False, "error": f"Ses işleme hatası: {str(e)}"}


# ==============================================================================
# GEMINI 3.8 FLASH TTS: METİNDEN SES ÜRETİMİ (TEXT-TO-SPEECH)
# ==============================================================================

def generate_speech_tts(text: str,
                        voice: str = "Kore",
                        style: str = "cheerful and friendly",
                        model: str = "gemini-3.8-flash-tts") -> Tuple[Optional[bytes], Optional[str]]:
    """
    Google AI Studio Gemini 3.8 Flash TTS dokümantasyonuna uygun Text-to-Speech çağrısı yapar.
    - Model: 'gemini-3.8-flash-tts' veya 'gemini-3.8-flash-lite-tts'
    - Ses: Kore, Zephyr, Puck, Despina, Aoede vb.
    - Style: Turn-level speech_metadata.style
    - Unary yanıt WAV formatında döner.
    """
    api_key = get_effective_gemini_key()
    if not api_key:
        return None, "Gemini API anahtarı bulunamadı"

    text = text.strip()
    if not text:
        return None, "Seslendirilecek metin boş"

    # 1. Yöntem: google-genai 3.0.0 client.interactions.create
    if GENAI_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)
            interaction = client.interactions.create(
                model=model,
                input=[{
                    "type": "user_input",
                    "content": [{
                        "type": "text",
                        "text": text,
                        "annotations": [{
                            "type": "speech_metadata",
                            "style": style,
                        }],
                    }],
                }],
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [
                        {"voice": voice}
                    ]
                }
            )

            if hasattr(interaction, "output_audio") and interaction.output_audio:
                audio_data = interaction.output_audio.data
                raw_bytes = base64.b64decode(audio_data) if isinstance(audio_data, str) else audio_data
                return raw_bytes, None

            if hasattr(interaction, "steps"):
                for step in interaction.steps:
                    for c in getattr(step, "content", []):
                        if getattr(c, "data", None):
                            return base64.b64decode(c.data), None

        except Exception as sdk_err:
            print(f"⚠ Gemini SDK TTS çağrısında istisna: {sdk_err}, REST API deneniyor...")

    # 2. Yöntem: Gemini Interactions REST API
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/interactions?key={api_key}"
        payload = {
            "model": model,
            "input": [{
                "type": "user_input",
                "content": [{
                    "type": "text",
                    "text": text,
                    "annotations": [{
                        "type": "speech_metadata",
                        "style": style
                    }]
                }]
            }],
            "response_format": {"type": "audio"},
            "generation_config": {
                "speech_config": [
                    {"voice": voice}
                ]
            }
        }

        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=40)
        if res.status_code == 200:
            resp_json = res.json()
            steps = resp_json.get("steps", [])
            for st in steps:
                for cnt in st.get("content", []):
                    if cnt.get("data"):
                        return base64.b64decode(cnt.get("data")), None
            if resp_json.get("output_audio", {}).get("data"):
                return base64.b64decode(resp_json["output_audio"]["data"]), None

        if model != "gemini-3.8-flash-lite-tts":
            payload["model"] = "gemini-3.8-flash-lite-tts"
            res2 = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            if res2.status_code == 200:
                resp_json = res2.json()
                for st in resp_json.get("steps", []):
                    for cnt in st.get("content", []):
                        if cnt.get("data"):
                            return base64.b64decode(cnt.get("data")), None

        return None, f"TTS API yanıt veremedi (HTTP {res.status_code}): {res.text[:150]}"

    except Exception as e:
        return None, f"TTS üretim hatası: {str(e)}"


# ==============================================================================
# GÜNLÜK SESLİ BRİFİNG ÜRETİCİ
# ==============================================================================

def generate_daily_briefing(user_id: Optional[str] = None, voice: str = "Kore") -> Dict[str, Any]:
    """
    Bugünün yapılacaklar listesini ve öncelikli işlerini analiz ederek
    doğal bir Türkçe sesli sabah brifingi metni ve Gemini TTS sesi üretir.
    """
    tasks = list_tasks(user_id=user_id)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    active_tasks = [t for t in tasks if t.get("status") != "done"]
    due_today = [t for t in active_tasks if (t.get("due_date") or "").startswith(today_str)]
    urgent_tasks = [t for t in active_tasks if t.get("priority") in ("urgent", "high")]
    overdue_tasks = [t for t in active_tasks if t.get("due_date") and t["due_date"].split("T")[0] < today_str]

    greetings = ["Harika bir gün dilerim!", "İyi çalışmalar dilerim!", "Bugün bereketli ve başarılı bir gün olsun!"]
    selected_greet = greetings[datetime.datetime.now().day % len(greetings)]

    script_parts = [
        f"{selected_greet} Nexa CRM günlük iş takip ve ajanda brifinginiz hazır. <short pause>"
    ]

    if not active_tasks:
        script_parts.append("Tebrikler! Şu anda yapılacaklar listenizde bekleyen hiçbir aktif görev bulunmuyor. Yeni bir portföy ekleyebilir veya sesli not alabilirsiniz.")
    else:
        script_parts.append(f"Bugün takip etmeniz gereken toplam {len(active_tasks)} aktif görev bulunuyor.")

        if due_today:
            script_parts.append(f"Günün ajandasında teslim edilmesi veya randevusu olan {len(due_today)} önemli konu var: <short pause>")
            for i, dt in enumerate(due_today[:3], 1):
                script_parts.append(f"{i}. madde: {dt.get('title')}. ")
        else:
            script_parts.append("Bugüne özel acil bir randevu veya teslim görünmüyor, genel işlerinize odaklanabilirsiniz.")

        if urgent_tasks:
            script_parts.append(f"<short pause> Ayrıca yüksek öncelikli {len(urgent_tasks)} görev dikkatinizi bekliyor.")

        if overdue_tasks:
            script_parts.append(f"Hatırlatma: Gecikmiş {len(overdue_tasks)} adet işiniz var, öncelikle bunları tamamlamanız önerilir.")

        script_parts.append("<short pause> İyi satışlar ve bol kazançlı bir gün dilerim!")

    full_script = " ".join(script_parts)

    audio_bytes, err = generate_speech_tts(
        text=full_script,
        voice=voice,
        style="warm and enthusiastic",
        model="gemini-3.8-flash-tts"
    )

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else None

    return {
        "ok": True,
        "script": full_script,
        "audio_base64": audio_b64,
        "total_active": len(active_tasks),
        "due_today": len(due_today),
        "urgent": len(urgent_tasks),
        "voice": voice,
        "has_audio": bool(audio_b64),
        "error": err
    }


# ==============================================================================
# FLASK BLUEPRINT ROUTES
# ==============================================================================

@crm_tasks_bp.route("/api/crm/tasks", methods=["GET"])
def api_list_tasks():
    status = request.args.get("status")
    category = request.args.get("category")
    priority = request.args.get("priority")
    search = request.args.get("search")
    user_id = request.args.get("user_id")
    due_date = request.args.get("due_date")

    tasks = list_tasks(status=status, category=category, priority=priority, search=search, user_id=user_id, due_date=due_date)
    stats = get_task_stats(user_id=user_id)
    return jsonify({
        "ok": True,
        "tasks": tasks,
        "stats": stats,
        "categories": TASK_CATEGORIES
    })


@crm_tasks_bp.route("/api/crm/tasks", methods=["POST"])
def api_create_task():
    data = request.get_json(silent=True) or {}
    if not (data.get("title") or "").strip():
        return jsonify({"ok": False, "error": "Görev başlığı boş olamaz"}), 400

    task = create_task(data)
    return jsonify({"ok": True, "task": task})


@crm_tasks_bp.route("/api/crm/tasks/<task_id>", methods=["GET"])
def api_get_task(task_id):
    task = get_task(task_id)
    if not task:
        return jsonify({"ok": False, "error": "Görev bulunamadı"}), 404
    return jsonify({"ok": True, "task": task})


@crm_tasks_bp.route("/api/crm/tasks/<task_id>", methods=["PUT"])
def api_update_task(task_id):
    data = request.get_json(silent=True) or {}
    task = update_task(task_id, data)
    if not task:
        return jsonify({"ok": False, "error": "Görev bulunamadı"}), 404
    return jsonify({"ok": True, "task": task})


@crm_tasks_bp.route("/api/crm/tasks/<task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    success = delete_task(task_id)
    return jsonify({"ok": success})


@crm_tasks_bp.route("/api/crm/tasks/<task_id>/toggle", methods=["POST"])
def api_toggle_task(task_id):
    task = toggle_task_status(task_id)
    if not task:
        return jsonify({"ok": False, "error": "Görev bulunamadı"}), 404
    return jsonify({"ok": True, "task": task})


@crm_tasks_bp.route("/api/crm/tasks/<task_id>/checklist/<int:item_index>/toggle", methods=["POST"])
def api_toggle_checklist(task_id, item_index):
    task = toggle_checklist_item(task_id, item_index)
    if not task:
        return jsonify({"ok": False, "error": "Görev veya madde bulunamadı"}), 404
    return jsonify({"ok": True, "task": task})


@crm_tasks_bp.route("/api/crm/voice/transcribe", methods=["POST"])
def api_voice_transcribe():
    """
    Ses kaydını alır (multipart dosya veya JSON base64) ve Gemini ile transkribe edip
    yapılandırılmış görev/not nesnesi üretir.
    """
    audio_bytes = None
    mime_type = "audio/webm"

    req_json = request.get_json(silent=True) or {}

    # 1. Multipart dosya yükleme
    if "audio" in request.files:
        f = request.files["audio"]
        audio_bytes = f.read()
        mime_type = f.mimetype or "audio/webm"
    elif "file" in request.files:
        f = request.files["file"]
        audio_bytes = f.read()
        mime_type = f.mimetype or "audio/webm"
    elif req_json.get("audio_base64"):
        b64 = req_json.get("audio_base64")
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        audio_bytes = base64.b64decode(b64)
        mime_type = req_json.get("mime_type", "audio/webm")

    if not audio_bytes:
        return jsonify({"ok": False, "error": "Ses verisi gönderilmedi"}), 400

    result = process_voice_task(audio_bytes, mime_type=mime_type)
    return jsonify(result)


@crm_tasks_bp.route("/api/crm/voice/tts", methods=["POST"])
def api_voice_tts():
    """
    Gemini 3.8 Flash TTS ile metni doğal sese çevirir.
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = data.get("voice") or "Kore"
    style = data.get("style") or "cheerful and friendly"
    model = data.get("model") or "gemini-3.8-flash-tts"

    if not text:
        return jsonify({"ok": False, "error": "Metin boş olamaz"}), 400

    audio_bytes, err = generate_speech_tts(text=text, voice=voice, style=style, model=model)
    if not audio_bytes:
        return jsonify({"ok": False, "error": err or "Ses sentezlenemedi"}), 500

    if request.args.get("json") == "1" or data.get("as_base64"):
        return jsonify({
            "ok": True,
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "mime_type": "audio/wav",
            "voice": voice
        })

    return Response(audio_bytes, mimetype="audio/wav", headers={
        "Content-Disposition": "inline; filename=crm_speech.wav",
        "Cache-Control": "no-cache"
    })


@crm_tasks_bp.route("/api/crm/voice/voices", methods=["GET"])
def api_get_voices():
    key = get_effective_gemini_key()
    return jsonify({
        "ok": True,
        "voices": AVAILABLE_VOICES,
        "categories": TASK_CATEGORIES,
        "has_gemini_key": bool(key)
    })


@crm_tasks_bp.route("/api/crm/tasks/daily-briefing", methods=["GET", "POST"])
def api_daily_briefing():
    req_j = request.get_json(silent=True) or {}
    voice = request.args.get("voice") or req_j.get("voice") or "Kore"
    user_id = request.args.get("user_id") or req_j.get("user_id")
    result = generate_daily_briefing(user_id=user_id, voice=voice)
    return jsonify(result)


@crm_tasks_bp.route("/api/crm/settings/gemini-key", methods=["GET", "POST"])
def api_gemini_key():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        new_key = (data.get("gemini_api_key") or "").strip()
        if not new_key:
            return jsonify({"ok": False, "error": "Geçerli bir API anahtarı giriniz"}), 400
        ok = save_gemini_key(new_key)
        if ok:
            return jsonify({"ok": True, "message": "Gemini API anahtarı başarıyla kaydedildi."})
        return jsonify({"ok": False, "error": ".env dosyasına yazılamadı."}), 500

    key = get_effective_gemini_key()
    masked = (key[:6] + "..." + key[-4:]) if len(key) > 10 else ("Tanımlı" if key else "Tanımlı Değil")
    return jsonify({
        "ok": True,
        "configured": bool(key),
        "masked_key": masked,
        "models": ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts", "gemini-2.5-flash", "gemini-2.0-flash"]
    })
