import requests
import time
from urllib.parse import urlencode
import json
import os
import hashlib
import base64
import random

# Konfigurasi API Key (ganti dengan API key kamu)
API_KEY = "brRQpVvWF6riOI1rUgTeqjqmZce1eNEf"  # ← Ganti disini sctg

def read_referral_code():
    """Read single referral code from ref.txt"""
    try:
        if not os.path.exists("ref.txt"):
            print("❌ File ref.txt tidak ditemukan!")
            return None
            
        with open("ref.txt", "r", encoding="utf-8") as f:
            ref_code = f.readline().strip()  # Read only first line
            if not ref_code:
                print("❌ ref.txt kosong!")
                return None
                
        print(f"✅ Referral code loaded: {ref_code}")
        return ref_code
    except Exception as e:
        print(f"❌ Error reading ref.txt: {e}")
        return None

def read_proxies():
    """Read proxies from proxy.txt (one per line). Format: http://user:pass@ip:port"""
    try:
        if not os.path.exists("proxy.txt"):
            print("⚠ proxy.txt tidak ditemukan! Lanjut tanpa proxy.")
            return []

        proxies = []
        with open("proxy.txt", "r", encoding="utf-8") as f:
            for line in f:
                p = line.strip()
                if not p or p.startswith("#"):
                    continue
                if not (p.startswith("http://") or p.startswith("https://")):
                    print(f"⚠ Skip proxy invalid (harus http/https): {p}")
                    continue
                proxies.append(p)

        if proxies:
            print(f"✅ Loaded {len(proxies)} proxy dari proxy.txt")
        else:
            print("⚠ proxy.txt kosong/invalid! Lanjut tanpa proxy.")
        return proxies
    except Exception as e:
        print(f"❌ Error reading proxy.txt: {e}")
        return []

def build_proxy_dict(proxy_url):
    """requests proxy dict for both http & https."""
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}

def solve_pow(challenge_data):
    """Solve PoW dari /api/c response - GRATIS!"""
    try:
        # Decode base64 challenge + padding
        d = challenge_data["d"] + "=="
        ch = json.loads(base64.b64decode(d).decode())
        
        # Extract PoW parameters
        salt = ch.get("s")
        target = ch.get("c") 
        max_n = ch.get("m", 100000)
        
        print(f"🔧 PoW: salt={salt[:10]}..., target={target[:10]}..., max_n={max_n}")
        
        # Brute force SHA256
        for n in range(max_n + 1):
            if hashlib.sha256(f"{salt}{n}".encode()).hexdigest() == target:
                print(f"✅ PoW SOLVED! n={n}")
                
                # Buat proof JSON → base64
                proof = {
                    "algorithm": ch.get("a"), 
                    "challenge": target,
                    "number": n, 
                    "salt": salt, 
                    "signature": ch.get("g")
                }
                p_b64 = base64.b64encode(
                    json.dumps(proof, separators=(',',':')).encode()
                ).decode()
                return p_b64
        
        print("❌ PoW timeout!")
        return None
    except Exception as e:
        print(f"❌ PoW error: {e}")
        return None

def get_turnstile_token(proxy_url=None):
    """Get Turnstile token from sctg.xyz API"""
    proxies = build_proxy_dict(proxy_url)

    params = {
        "key": API_KEY,
        "method": "turnstile",
        "pageurl": "https://thenanobutton.com/",
        "sitekey": "0x4AAAAAACZpJ7kmZ3RsO1rU"
    }
    
    query_string = urlencode(params)
    url = "https://sctg.xyz/in.php?" + query_string
    
    print(f"→ Sending request to {url}")
    response = requests.get(url, timeout=30, proxies=proxies)
    result = response.text.strip()
    
    if "|" in result:
        status, task_id = result.split("|", 1)
        print(f"Task ID: {task_id}")
        
        # Poll for result
        max_wait = 300
        poll_interval = 5
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait:
            time.sleep(poll_interval)
            
            poll_params = {
                "key": API_KEY,
                "id": task_id,
                "action": "get"
            }
            poll_query = urlencode(poll_params)
            poll_url = "https://sctg.xyz/res.php?" + poll_query
            
            poll_response = requests.get(poll_url, timeout=30, proxies=proxies)
            poll_result = poll_response.text.strip()
            
            # ✅ HAPUS "OK|" dari turnstileToken
            clean_token = poll_result.replace("OK|", "")
            
            elapsed = time.time() - start_time
            print(f"  [{elapsed:.1f}s] Status: {poll_result[:50]}...")
            
            if "NOT_READY" not in poll_result and "PROCESSING" not in poll_result:
                print(f"\n✓ Clean Turnstile Token: {clean_token[:50]}...")
                return clean_token
        
        print("\n⚠ Timeout waiting for result")
        return None
    return None

def single_regis(ref_code, proxy_url=None):
    """Single registration process with referral code - FIXED CAPTCHA! + PROXY"""
    proxies = build_proxy_dict(proxy_url)
    if proxy_url:
        print(f"🌐 Using proxy: {proxy_url}")

    # Common headers
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "Referer": "https://thenanobutton.com/"
    }
    
    # Step 1: Get session data with referral code
    url1 = f"https://api.thenanobutton.com/api/session?ref={ref_code}"
    response1 = requests.get(url1, headers=headers, timeout=30, proxies=proxies)
    session_data = response1.json()
    
    # Extract individual variables
    token = session_data["token"]
    invitation_code = session_data["invitationCode"]
    
    print(f"\n✅ Token: {token}")
    print(f"✅ Invitation Code: {invitation_code}")
    
    # Step 2: Check if captcha needed
    if not session_data["captchaPassed"]:
        print("🔄 Captcha required...")
        
        # Get dynamic Turnstile token (sctg.xyz)
        print("📱 Getting clean Turnstile token...")
        turnstile_token = get_turnstile_token(proxy_url=proxy_url)
        if not turnstile_token:
            print("❌ Failed to get Turnstile token")
            return None
        
        # Get captcha challenge & SOLVE PoW ✅
        print("🔑 Getting captcha challenge...")
        url2 = "https://api.thenanobutton.com/api/c"
        response2 = requests.get(url2, headers=headers, timeout=30, proxies=proxies)
        captcha_data = response2.json()
        
        print(f"✅ Raw challenge: {captcha_data['d'][:50]}...")
        
        # ✅ SOLVE PoW instead of raw p_data
        p_data = solve_pow(captcha_data)
        if not p_data:
            print("❌ PoW solve failed!")
            return None
        
        print(f"✅ PoW solved: {p_data[:50]}...")
        
        # Step 3: Submit captcha
        print("✅ Submitting captcha...")
        url3 = "https://api.thenanobutton.com/api/captcha"
        headers3 = headers.copy()
        headers3["content-type"] = "application/json"
        
        # ✅ Body dengan PoW proof yang benar
        body = {
            "token": token,
            "turnstileToken": turnstile_token,
            "p": p_data  # ✅ Proper base64(PoW JSON)
        }
        
        print(f"📤 POST: token={token[:20]}..., turnstile={turnstile_token[:20]}..., p={p_data[:20]}...")
        response3 = requests.post(url3, headers=headers3, json=body, timeout=30, proxies=proxies)
        final_result = response3.json()
        
        print("✅ Captcha result:", final_result)
        return {
            "token": token,
            "invitationCode": invitation_code,
            "proxy": proxy_url,
            "turnstileToken": turnstile_token,
            "p_data": p_data,  # Sekarang PoW proof
            "captcha_result": final_result
        }
    
    return {
        "token": token,
        "invitationCode": invitation_code,
        "proxy": proxy_url
    }

def main():
    """Main function - sekali jalan sesuai input"""
    print("🚀 NanoButton Auto Registration")
    print("=" * 50)
    
    # Load referral code once
    ref_code = read_referral_code()
    if not ref_code:
        print("❌ Cannot proceed without referral code!")
        return

    proxies_list = read_proxies()  # ✅ load proxy list (boleh kosong)
    
    try:
        count = input("\nBerapa kali ingin register? (0=exit): ").strip()
        
        if count.lower() == '0':
            print("👋 Goodbye!")
            return
        
        count = int(count)
        if count <= 0:
            print("❌ Masukkan angka positif!")
            return
        
        print(f"\n🔄 Memulai {count} registrasi dengan ref: {ref_code}")
        
        results = []
        last_proxy = None

        for i in range(count):
            print(f"\n{'='*20} REGISTRASI KE-{i+1}/{count} {'='*20}")

            # ✅ Random proxy tiap registrasi (hindari sama 2x berturut-turut)
            proxy_url = None
            if proxies_list:
                if len(proxies_list) == 1:
                    proxy_url = proxies_list[0]
                else:
                    proxy_url = random.choice(proxies_list)
                    while proxy_url == last_proxy:
                        proxy_url = random.choice(proxies_list)
                last_proxy = proxy_url
            
            result = single_regis(ref_code, proxy_url=proxy_url)
            if result:
                results.append(result)
                print(f"✅ Registrasi {i+1} SUKSES!")
            else:
                print(f"❌ Registrasi {i+1} GAGAL!")
            
            if i < count - 1:
                print("⏳ Delay 3 detik...")
                time.sleep(3)
        
        # Summary
        print(f"\n{'='*50}")
        print(f"📊 SUMMARY: {len(results)}/{count} SUKSES")
        
        if results:
            with open("nanobutton_results.txt", "a", encoding="utf-8") as f:
                for i, result in enumerate(results, 1):
                    f.write(f"Registrasi {i} (ref: {ref_code}):\n")
                    f.write(json.dumps(result, indent=2))
                    f.write("\n" + "-"*50 + "\n\n")
            print("💾 Hasil disimpan ke 'nanobutton_results.txt'")
        
        print("✅ Selesai!")
        
    except ValueError:
        print("❌ Input harus angka!")
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
