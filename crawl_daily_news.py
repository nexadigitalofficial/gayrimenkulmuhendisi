# -*- coding: utf-8 -*-
"""
Ankara Gayrimenkul, Piyasa & Finans Günlük Haber Toplama Ajanı
GitHub Actions Cron Job veya Yerel Scheduler ile çalışır.
"""

import os
import json
import random
from datetime import datetime, timezone

def generate_daily_news():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("⚠️ GEMINI_API_KEY bulunamadı, varsayılan haber seti güncelleniyor.")
        return False

    print("🤖 Günlük Ankara Emlak & Finans Sinyalleri Taranıyor (Gemini 2.5 Flash)...")

    images_pool = [
        "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1582268611958-ebfd161ef9cf?auto=format&fit=crop&w=800&q=80"
    ]

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = """
        Türkiye ve Ankara özelinde güncel gayrimenkul piyasası, TCMB faiz kararları, konut kredisi faiz oranları, inşaat maliyet endeksi, kentsel dönüşüm teşvikleri ve yatırım bölgeleri (Çankaya, İncek, GOP, Çayyolu, Beytepe) hakkında 3 adet son derece profesyonel Türkçe haber/analiz yazısı hazırla.
        
        Aşağıdaki JSON şemasında çıktı ver:
        {
          "articles": [
            {
              "title": "Haber Başlığı",
              "summary": "1-2 cümlelik çarpıcı özet",
              "content": "Detaylı, paragraflara bölünmüş (en az 3 paragraf) tam makale metni",
              "category": "Kategori ('Yatırım', 'Piyasa Analizi', 'Ulaşım' veya 'Yaşam')",
              "readTime": "Okuma süresi (örneğin: '4 dk')"
            }
          ]
        }
        """

        resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )

        raw_text = (resp.text or "").strip()
        if "```" in raw_text:
            for part in raw_text.split("```"):
                p = part.strip()
                if p.lower().startswith("json"):
                    raw_text = p[4:].strip()
                elif p.startswith("{") or p.startswith("["):
                    raw_text = p
                    break

        payload = json.loads(raw_text)
        articles = payload.get("articles", [])

        if not articles:
            print("❌ Makale üretilemedi.")
            return False

        now = datetime.now(timezone.utc).isoformat()
        processed = []
        for art in articles:
            processed.append({
                "title": art.get("title", "").strip(),
                "summary": art.get("summary", "").strip(),
                "content": art.get("content", "").strip(),
                "image": random.choice(images_pool),
                "category": art.get("category", "Piyasa Analizi").strip(),
                "readTime": art.get("readTime", "3 dk").strip(),
                "published": True,
                "createdAt": now,
                "updatedAt": now
            })

        # Save to static JSON cache
        os.makedirs("static/data", exist_ok=True)
        cache_path = os.path.join("static", "data", "latest_news.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(processed, f, ensure_ascii=False, indent=2)

        print(f"✅ {len(processed)} adet yeni haber static/data/latest_news.json dosyasına kaydedildi.")
        return True

    except Exception as e:
        print(f"❌ Haber üretim hatası: {e}")
        return False

if __name__ == "__main__":
    generate_daily_news()
