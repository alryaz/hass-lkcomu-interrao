#!/usr/bin/env python3
"""
Investigate why meters are not showing in HA integration.
Intercepts API calls to mosenergosbyt.ru and analyzes the Meters response.

Usage:
    python3 scripts/investigate_meters.py <username> <password>
"""

import asyncio
import json
import sys
from playwright.async_api import async_playwright

USERNAME = sys.argv[1] if len(sys.argv) > 1 else input("Username: ")
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else input("Password: ")

API_CALLS = []


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Intercept all API requests/responses
        async def on_response(response):
            url = response.url
            if "action=sql" in url or "lkcomu" in url or "energosbyt" in url.lower():
                try:
                    body = await response.json()
                except Exception:
                    try:
                        body = await response.text()
                    except Exception:
                        body = "<unreadable>"
                entry = {
                    "url": url,
                    "status": response.status,
                    "method": response.request.method,
                    "body": body,
                }
                API_CALLS.append(entry)
                print(f"\n[API] {response.status} {url[:80]}")
                if isinstance(body, dict):
                    kd_result = body.get("kd_result")
                    nm_result = body.get("nm_result") or body.get("nm_title") or ""
                    print(f"      kd_result={kd_result}  nm_result={nm_result}")
                    # Check for Meters-specific response
                    data_list = body.get("data", [])
                    if isinstance(data_list, list) and data_list:
                        first = data_list[0] if data_list else {}
                        if "nm_meter_num" in str(first):
                            print(f"      [METERS] Found {len(data_list)} meters!")
                            for m in data_list:
                                print(
                                    f"        - {m.get('nm_meter_num')} | {m.get('nm_meter')} | {m.get('nm_mrk')} | kd_result={m.get('kd_result')}"
                                )
                        elif "proxyquery" in url or "action=sql" in url:
                            # Any SQL action response - show what query it was
                            if "proxyquery" in str(response.request.url):
                                pass
                            print(
                                f"      data has {len(data_list)} items, keys={list(first.keys())[:5] if isinstance(first, dict) else '?'}"
                            )

        async def on_request(request):
            url = request.url
            if "action=sql" in url:
                post_data = request.post_data or ""
                # Extract proxyquery value
                import urllib.parse

                try:
                    params = dict(urllib.parse.parse_qsl(post_data))
                    query = params.get("proxyquery", "?")
                    plugin = params.get("plugin", "?")
                    print(f"  --> SQL request: proxyquery={query} plugin={plugin}")
                except Exception:
                    pass

        page.on("response", on_response)
        page.on("request", on_request)

        print("Opening site...")
        await page.goto("https://my.mosenergosbyt.ru/")
        await page.wait_for_load_state("networkidle")

        # Try to log in
        print("\nLogging in...")
        try:
            # Fill login form - try common selectors
            login_field = page.locator(
                "input[name='login'], input[type='email'], input[placeholder*='логин'], input[placeholder*='email'], input[id*='login'], input[id*='user']"
            ).first
            await login_field.fill(USERNAME)

            pass_field = page.locator(
                "input[name='password'], input[type='password']"
            ).first
            await pass_field.fill(PASSWORD)

            submit = page.locator(
                "button[type='submit'], input[type='submit'], button:has-text('Войти'), button:has-text('Вход')"
            ).first
            await submit.click()

            await page.wait_for_load_state("networkidle", timeout=15000)
            print("Login submitted, waiting for response...")

        except Exception as e:
            print(f"Login automation failed: {e}")
            print("Please log in manually in the browser window.")
            print(
                "Press Enter here when you are logged in and can see your accounts..."
            )
            await asyncio.get_event_loop().run_in_executor(None, input)

        # Wait for 2FA if needed
        await asyncio.sleep(3)

        # Try to navigate to meters page or trigger meter data fetch
        print("\nLooking for meters section...")
        try:
            # Common selectors for meter navigation
            meter_link = page.locator(
                "a:has-text('счётч'), a:has-text('показан'), a:has-text('Счетч'), nav a"
            ).first
            if await meter_link.count() > 0:
                await meter_link.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # Wait a bit to capture more API calls
        await asyncio.sleep(5)

        print("\n" + "=" * 60)
        print(f"Total API calls captured: {len(API_CALLS)}")

        # Find Meters calls specifically
        meters_calls = [
            c
            for c in API_CALLS
            if isinstance(c["body"], dict) and "nm_meter_num" in str(c["body"])
        ]
        sql_calls = [c for c in API_CALLS if "action=sql" in c["url"]]

        print(f"SQL action calls: {len(sql_calls)}")
        print(f"Calls with meter data: {len(meters_calls)}")

        if not meters_calls:
            print("\n[!] No Meters API response captured.")
            print("    SQL calls made:")
            for c in sql_calls:
                print(f"    - {c['url'][:100]}")

        # Save full log
        log_path = "/tmp/mosenergosbyt_api_log.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(API_CALLS, f, ensure_ascii=False, indent=2)
        print(f"\nFull API log saved to: {log_path}")

        input("\nPress Enter to close browser...")
        await browser.close()


asyncio.run(main())
