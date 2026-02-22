import requests
import time
from urllib.parse import urlencode
import json
import os
import hashlib
import base64
import asyncio
import websockets
import signal
from websockets_proxy import Proxy, proxy_connect
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Konfigurasi API Key (ganti dengan API key kamu)
API_KEY = "brRQpVvWF6riOI1rUgTeqjqmZce1eNEf"  # ← Ganti disini sctg

# Proxy Configuration
PROXY_URL = "http://yuspkugp-rotate:1utyz2m19pvm@p.webshare.io:80"
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL,
}

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

def get_turnstile_token():
    """Get Turnstile token from sctg.xyz API"""
    params = {
        "key": API_KEY,
        "method": "turnstile",
        "pageurl": "https://thenanobutton.com/",
        "sitekey": "0x4AAAAAACZpJ7kmZ3RsO1rU"
    }
    
    query_string = urlencode(params)
    url = "https://sctg.xyz/in.php?" + query_string
    
    print(f"→ Sending request to {url}")
    response = requests.get(url, timeout=30, proxies=PROXIES)
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
            
            poll_response = requests.get(poll_url, timeout=30, proxies=PROXIES)
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

def single_regis(ref_code):
    """Single registration process with referral code - FIXED CAPTCHA!"""
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
    response1 = requests.get(url1, headers=headers, proxies=PROXIES)
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
        turnstile_token = get_turnstile_token()
        if not turnstile_token:
            print("❌ Failed to get Turnstile token")
            return None
        
        # Get captcha challenge & SOLVE PoW ✅
        print("🔑 Getting captcha challenge...")
        url2 = "https://api.thenanobutton.com/api/c"
        response2 = requests.get(url2, headers=headers, proxies=PROXIES)
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
        response3 = requests.post(url3, headers=headers3, json=body, proxies=PROXIES)
        final_result = response3.json()
        
        print("✅ Captcha result:", final_result)
        return {
            "token": token,
            "invitationCode": invitation_code,
            "turnstileToken": turnstile_token,
            "p_data": p_data,  # Sekarang PoW proof
            "captcha_result": final_result
        }
    
    return {
        "token": token,
        "invitationCode": invitation_code
    }

async def solve_captcha_for_token(token):
    """Solve captcha during auto-click session (runs in thread to not block async)"""
    try:
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Referer": "https://thenanobutton.com/"
        }
        
        # Run blocking HTTP calls in thread
        loop = asyncio.get_event_loop()
        
        # 1. Get Turnstile token
        print("📱 Getting Turnstile token for captcha...")
        turnstile_token = await loop.run_in_executor(None, get_turnstile_token)
        if not turnstile_token:
            print("❌ Failed to get Turnstile token")
            return False
        
        # 2. Get PoW challenge
        print("🔑 Getting PoW challenge...")
        def get_challenge():
            r = requests.get("https://api.thenanobutton.com/api/c", headers=headers, proxies=PROXIES)
            return r.json()
        
        captcha_data = await loop.run_in_executor(None, get_challenge)
        
        # 3. Solve PoW
        p_data = await loop.run_in_executor(None, solve_pow, captcha_data)
        if not p_data:
            print("❌ PoW solve failed!")
            return False
        
        # 4. Submit captcha
        def submit_captcha():
            h = headers.copy()
            h["content-type"] = "application/json"
            body = {
                "token": token,
                "turnstileToken": turnstile_token,
                "p": p_data
            }
            r = requests.post("https://api.thenanobutton.com/api/captcha", headers=h, json=body, proxies=PROXIES)
            return r.json()
        
        result = await loop.run_in_executor(None, submit_captcha)
        print(f"✅ Captcha result: {result}")
        return result.get("captchaPassed", True)
        
    except Exception as e:
        print(f"❌ Captcha solve error: {e}")
        return False

async def connect_websocket(token, auto_click=False, click_interval=1.0):
    """Connect to NanoButton WebSocket, optionally auto-click"""
    ws_url = f"wss://api.thenanobutton.com/ws?token={token}"
    
    headers = {
        "Origin": "https://thenanobutton.com",
        "Cache-Control": "no-cache",
        "Accept-Language": "en-US,en;q=0.9",
        "Pragma": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    }
    
    short_token = token[:12]
    state = {"captcha_needed": False, "total_clicks": 0, "done": False}
    
    print(f"\n[WS] [{short_token}] Connecting...")
    
    while True:
        try:
            proxy = Proxy.from_url(PROXY_URL)
            async with proxy_connect(
                ws_url,
                proxy=proxy,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
            ) as ws:
                print(f"[WS] [{short_token}] CONNECTED!")
                
                if auto_click:
                    listener_task = asyncio.create_task(ws_listener(ws, short_token, state))
                    clicker_task = asyncio.create_task(ws_auto_clicker(ws, short_token, click_interval, token, state))
                    
                    done, pending = await asyncio.wait(
                        [listener_task, clicker_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    
                    # Account done? Stop reconnecting
                    if state.get("done"):
                        print(f"[WS] [{short_token}] Account complete. Closing.")
                        return
                    
                    for task in done:
                        task.result()
                else:
                    await ws_listener(ws, short_token, state)
                        
        except websockets.exceptions.ConnectionClosed as e:
            if state.get("done"):
                return
            print(f"[WS] [{short_token}] Disconnected, reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            if state.get("done"):
                return
            print(f"[WS] [{short_token}] Error: {e}, reconnecting in 10s...")
            await asyncio.sleep(10)


async def ws_listener(ws, label, state=None):
    """Listen for incoming WebSocket messages"""
    hourly_limit_count = 0
    async for message in ws:
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            if msg_type == "init":
                session = data.get("session", {})
                current = session.get("currentNano", 0)
                clicks = session.get("clicks", 0)
                since_captcha = session.get("clicksSinceCaptcha", 0)
                captcha_req = session.get("captchaRequired", False)
                if state:
                    state["clicks_since_captcha"] = since_captcha
                    state["total_clicks"] = clicks
                    if captcha_req:
                        state["captcha_needed"] = True
                print(f"[INIT] [{label}] [{time.strftime('%H:%M:%S')}] Nano: {current} | Clicks: {clicks} | SinceCaptcha: {since_captcha} | CaptchaReq: {captcha_req}")
            
            elif msg_type == "click":
                amount = data.get("amount", 0)
                current = data.get("currentNano", 0)
                total = data.get("totalEarned", 0)
                clicks_since = data.get("clicksSinceCaptcha", 0)
                captcha_req = data.get("captchaRequired", False)
                
                if state:
                    state["clicks_since_captcha"] = clicks_since
                    state["accepted"] = state.get("accepted", 0) + 1
                    if hourly_limit_count > 0:
                        state["rate_limited"] = state.get("rate_limited", 0) + hourly_limit_count
                        hourly_limit_count = 0
                
                if clicks_since % 10 == 0 or captcha_req or amount == 0:
                    status = " >> CAPTCHA NEEDED!" if captcha_req else ""
                    print(f"[CLICK] [{label}] [{time.strftime('%H:%M:%S')}] +{amount} | Nano: {current} | Total: {total} | SinceCaptcha: {clicks_since}/100{status}")
                
                if state and captcha_req:
                    state["captcha_needed"] = True

            elif msg_type == "hourly_limit":
                hourly_limit_count += 1
                    
            elif msg_type == "stats":
                pass
            elif msg_type in ("leaderboard", "withdrawal"):
                pass
            elif msg_type == "error":
                print(f"[ERROR] [{label}] [{time.strftime('%H:%M:%S')}] {data}")
            else:
                print(f"[{msg_type.upper()}] [{label}] [{time.strftime('%H:%M:%S')}] {json.dumps(data)[:300]}")
            
            if msg_type != "hourly_limit":
                with open("ws_messages.log", "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{label}] {json.dumps(data)}\n")
                
        except json.JSONDecodeError:
            print(f"[MSG] [{label}] [{time.strftime('%H:%M:%S')}] Raw: {message[:200]}")


async def ws_auto_clicker(ws, label, interval, token, state):
    """Fire-and-forget clicker with fixed pace. No round-trip wait."""
    send_count = 0
    state["accepted"] = 0
    state["rate_limited"] = 0
    
    # Wait for init
    await asyncio.sleep(0.5)
    
    if state.get("captcha_needed"):
        print(f"[SKIP] [{label}] Already at 100 clicks (captcha needed). Skipping.")
        state["done"] = True
        return
    
    server_clicks = state.get("clicks_since_captcha", 0)
    remaining = 100 - server_clicks
    # ~0.5s per click = sweet spot (server accepts ~2/s, no rate limits)
    # Send a bit extra to account for potential rate-limits, listener tracks real count
    pace = 0.0001  # 5ms between sends — max speed
    print(f"[CLICKER] [{label}] Starting from {server_clicks}/100. Pace: {pace}s/click")
    
    while True:
        try:
            if state.get("captcha_needed") or state.get("clicks_since_captcha", 0) >= 100:
                break
            
            await ws.send("c")
            send_count += 1
            await asyncio.sleep(pace)
            
        except websockets.exceptions.ConnectionClosed:
            print(f"[WARN] [{label}] Connection lost at send {send_count}")
            raise
        except Exception as e:
            print(f"[ERROR] [{label}] Click error: {e}")
            await asyncio.sleep(1)
    
    # Wait a moment for final server responses to arrive
    await asyncio.sleep(1)
    
    state["done"] = True
    sc = state.get("clicks_since_captcha", 0)
    acc = state.get("accepted", 0)
    rl = state.get("rate_limited", 0)
    print(f"[DONE] [{label}] Server: {sc}/100 | Sent: {send_count} | Accepted: {acc} | RateLimited: {rl}")
    print(f"[DONE] [{label}] Efficiency: {acc}/{send_count} = {acc*100//max(send_count,1)}%")


async def multi_websocket(tokens, auto_click=False, click_interval=1.0):
    """Run multiple WebSocket connections concurrently"""
    tasks = [connect_websocket(t, auto_click, click_interval) for t in tokens]
    await asyncio.gather(*tasks)


def register_worker(worker_id, ref_code):
    """Worker thread: register 1 akun"""
    tag = f"W{worker_id}"
    try:
        print(f"[{tag}] Registering...")
        result = single_regis(ref_code)
        if result:
            print(f"[{tag}] SUKSES! Token: {result['token'][:16]}...")
            return result
        else:
            print(f"[{tag}] GAGAL!")
            return None
    except Exception as e:
        print(f"[{tag}] Error: {e}")
        return None


def multi_register(ref_code, count, max_workers=250):
    """Register multiple accounts using thread pool"""
    print(f"\n[REGISTER] {count} akun dengan {max_workers} threads...")
    print("=" * 50)
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i in range(count):
            future = executor.submit(register_worker, i + 1, ref_code)
            futures[future] = i + 1
        
        for future in as_completed(futures):
            wid = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"[W{wid}] Exception: {e}")
    
    return results


def main():
    """Main function"""
    print("NanoButton Bot")
    print("=" * 50)
    
    ref_code = read_referral_code()
    if not ref_code:
        print("[ERROR] Cannot proceed without referral code!")
        return
    
    try:
        print("\nMenu:")
        print("  1. Register saja (multi-thread)")
        print("  2. Auto-Click (masukkan token)")
        print("  3. Register + Auto-Click 100x (multi-thread)")
        print("  0. Exit")
        
        choice = input("\nPilih menu: ").strip()
        
        if choice == '0':
            return
        
        if choice == '2':
            token = input("Masukkan token: ").strip()
            if not token:
                print("[ERROR] Token kosong!")
                return
            print(f"\n[WS] Auto-Click 100x...")
            asyncio.run(connect_websocket(token, auto_click=True, click_interval=0))
            return
        
        if choice in ('1', '3'):
            count = input("\nBerapa akun? (0=exit): ").strip()
            if count == '0':
                return
            count = int(count)
            if count <= 0:
                print("[ERROR] Masukkan angka positif!")
                return
            
            workers = input(f"Jumlah thread (default 3, max {min(count, 250)}): ").strip()
            workers = int(workers) if workers else 3
            workers = min(workers, count, 250)
            
            # Multi-thread registration
            results = multi_register(ref_code, count, max_workers=workers)
            tokens = [r["token"] for r in results]
            
            # Summary
            print(f"\n{'='*50}")
            print(f"[SUMMARY] {len(results)}/{count} SUKSES")
            for i, r in enumerate(results, 1):
                print(f"  {i}. Token: {r['token'][:20]}... | Code: {r.get('invitationCode', '?')}")
            
            if results:
                with open("nanobutton_results.txt", "a") as f:
                    for i, result in enumerate(results, 1):
                        f.write(f"Registrasi {i} (ref: {ref_code}):\n")
                        f.write(json.dumps(result, indent=2))
                        f.write("\n" + "-"*50 + "\n\n")
                print("[SAVE] Hasil disimpan ke nanobutton_results.txt")
            
            # Auto-click if choice 3
            if choice == '3' and tokens:
                print(f"\n[WS] Auto-Click {len(tokens)} akun x 100 clicks...")
                asyncio.run(multi_websocket(tokens, auto_click=True, click_interval=0))
            
            print("\n[DONE] Selesai!")
        else:
            print("[ERROR] Pilihan tidak valid!")
        
    except ValueError:
        print("[ERROR] Input harus angka!")
    except KeyboardInterrupt:
        print("\n\nCancelled by user!")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
