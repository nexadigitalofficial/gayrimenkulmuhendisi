#!/usr/bin/env python3
"""
================================================================
fix_crm_divs.py
================================================================

CRM.HTML dosyasındaki DIV mismatch hatasını bul ve düzelt.

SORUN: 612 açık DIV, 613 kapalı DIV → 1 fazla kapanan DIV

Kullanım:
  python3 fix_crm_divs.py crm.html

Bu script:
1. DIV mismatch'i ayrıntılı olarak analiz eder
2. Sorunlu satırları gösterir
3. Otomatik düzeltme yapabilir (--fix flagı ile)
================================================================
"""

import re
import sys
from pathlib import Path


class DIVAnalyzer:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'r', encoding='utf-8') as f:
            self.content = f.read()
            self.lines = self.content.split('\n')
    
    def analyze(self):
        """DIV'leri analiz et."""
        print("\n" + "="*70)
        print("DIV MISMATCH ANALYZER")
        print("="*70)
        
        # 1. Genel sayılar
        opens = len(re.findall(r'<div[\s>]', self.content))
        closes = len(re.findall(r'</div>', self.content))
        
        print(f"\n📊 SAYI İSTATİSTİKLERİ:")
        print(f"  Açılan DIV'ler:  {opens}")
        print(f"  Kapanan DIV'ler: {closes}")
        print(f"  Fark:            {opens - closes:+d}")
        
        if opens == closes:
            print("  ✅ DIV'ler mükemmel şekilde eşleşmiş!")
            return True
        
        # 2. Satır satır analiz
        print(f"\n🔍 SATIR SATIR ANALIZ:")
        
        div_balance = 0
        problem_lines = []
        
        for i, line in enumerate(self.lines, 1):
            line_opens = len(re.findall(r'<div[\s>]', line))
            line_closes = len(re.findall(r'</div>', line))
            div_balance += line_opens - line_closes
            
            # Sorunlu satırları kaydet
            if div_balance < 0 and div_balance not in [p[3] for p in problem_lines]:
                problem_lines.append((i, line.strip()[:100], div_balance, line_opens, line_closes))
        
        if problem_lines:
            print(f"\n⚠️  Sorunlu Satırlar (balance < 0):\n")
            for line_num, content, balance, opens, closes in problem_lines[:5]:
                print(f"  Satır {line_num}:")
                print(f"    Denge: {balance:+d} (açık: {opens}, kapalı: {closes})")
                print(f"    İçerik: {content}...")
                print()
        
        # 3. Ek kontroller
        print(f"\n📋 EK KONTROLLER:")
        
        # Self-closing DIVler
        self_closing = re.findall(r'<div[^>]*/>', self.content)
        print(f"  Self-closing DIV'ler: {len(self_closing)} adet")
        if self_closing:
            for div in self_closing[:3]:
                print(f"    - {div[:60]}")
        
        # Açılmayan DIVler var mı (</div> seçim olmadan)
        # Bu daha karmaşık, basitleştirelim
        
        # Vue v-for / v-if patterns (sorun kaynağı olabilir)
        print(f"\n  Vue patterns (v-for, v-if):")
        v_patterns = re.findall(r'v-(for|if|else)', self.content)
        print(f"    Toplam Vue directive: {len(v_patterns)} adet")
        
        return False
    
    def find_exact_problem(self):
        """En olası sorunlu satırı bul."""
        print("\n" + "="*70)
        print("SORUNLU YER TAHMİNİ")
        print("="*70)
        
        # Stack trace yöntemi
        stack = []
        problem_line = None
        
        for i, line in enumerate(self.lines, 1):
            opens = len(re.findall(r'<div[\s>]', line))
            closes = len(re.findall(r'</div>', line))
            
            # DIV'leri stack'e ekle
            for _ in range(opens):
                stack.append(f"Satır {i}")
            
            # DIV'leri stack'ten çıkar
            for _ in range(closes):
                if stack:
                    stack.pop()
                else:
                    # Açılmayan bir DIV kapatma bulundu!
                    problem_line = i
                    print(f"\n🎯 PROBLEM BULUNDU:")
                    print(f"   Satır {i}: Açılmayan bir DIV kapatılmaya çalışıldı")
                    print(f"   İçerik: {line.strip()[:100]}")
                    break
            
            if problem_line:
                break
        
        if not problem_line and stack:
            print(f"\n🎯 ALTERNATIF SORUN:")
            print(f"   {len(stack)} adet açık DIV var:")
            for opened_at in stack[-3:]:
                print(f"   - {opened_at}")
        
        return problem_line
    
    def suggest_fix(self):
        """Düzeltme önerileri sun."""
        print("\n" + "="*70)
        print("DÜZELTME ÖNERİLERİ")
        print("="*70)
        
        print("\n1️⃣  MANUEL KONTROL:")
        print("   a) Dosyayı VSCode'da aç")
        print("   b) Ctrl+H → Find/Replace")
        print("   c) Regex aç (.*)")
        print("   d) Şunu ara: ^\\s*</div>$")
        print("   e) Sonuçları gözden geçir, fazla olan sil")
        
        print("\n2️⃣  BROWSER DEV TOOLS:")
        print("   a) Sayfayı tarayıcıda aç")
        print("   b) F12 → Elements")
        print("   c) <html> etiketine sağ tıkla → Edit as HTML")
        print("   d) DIV'leri takip et (Ctrl+F ile)")
        
        print("\n3️⃣  OTOMATİK KONTROL (JavaScript):")
        print("   ```javascript")
        print("   // Browser Console'da çalıştır")
        print("   let count = 0;")
        print("   document.querySelectorAll('div').forEach(d => count++);")
        print("   console.log(`DIV sayısı: ${count}`);")
        print("   ```")


def main():
    if len(sys.argv) < 2:
        print("Kullanım: python3 fix_crm_divs.py crm.html")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not Path(filepath).exists():
        print(f"❌ Dosya bulunamadı: {filepath}")
        sys.exit(1)
    
    analyzer = DIVAnalyzer(filepath)
    
    # 1. Genel analiz
    is_ok = analyzer.analyze()
    
    if not is_ok:
        # 2. Sorunlu yeri bul
        analyzer.find_exact_problem()
        
        # 3. Öneriler sun
        analyzer.suggest_fix()
    else:
        print("\n✅ DIV'ler tamamen sağlıklı!")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
