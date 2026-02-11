import asyncio
import pandas as pd
from urllib.parse import urlparse, parse_qs, urljoin
from playwright.async_api import async_playwright


CSV_PATH = "users.csv"
GROUP_URLS_PATH = "group_urls.txt"
OUTPUT_PATH = "disabled_users_report.csv"

HEADFUL_LOGIN = True  # True: you log in once manually; False: runs headless after you confirm it works


def load_users_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Username"] = df["Username"].astype(str).str.strip()
    df["Enabled_norm"] = df["Enabled"].astype(str).str.strip().str.upper()
    return df.set_index("Username", drop=False)


def extract_id_from_href(href: str) -> str | None:
    if not href:
        return None
    qs = parse_qs(urlparse(href).query)
    # /entity/open.act?id=chandt&type=user&direct=true
    if "id" in qs and qs["id"]:
        return qs["id"][0]
    return None


async def scrape_group_usernames(page, group_url: str) -> list[str]:
    await page.goto(group_url, wait_until="networkidle")

    # Select only user links in the users section
    anchors = await page.query_selector_all('#users a.asset-link[data-asset-type="user"]')

    usernames = []
    for a in anchors:
        # easiest: data-asset-id is already the username
        u = await a.get_attribute("data-asset-id")
        if not u:
            href = await a.get_attribute("href")
            u = extract_id_from_href(href or "")
        if u:
            usernames.append(u.strip())

    # de-dupe but keep stable order
    seen = set()
    out = []
    for u in usernames:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def main():
    users_df = load_users_csv(CSV_PATH)

    with open(GROUP_URLS_PATH, "r", encoding="utf-8") as f:
        group_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not HEADFUL_LOGIN)
        context = await browser.new_context()
        page = await context.new_page()

        # Open first page so you can log in once (SSO)
        await page.goto(group_urls[0], wait_until="domcontentloaded")
        if HEADFUL_LOGIN:
            input("Log in in the browser window, then press ENTER here...")

        for group_url in group_urls:
            usernames = await scrape_group_usernames(page, group_url)

            for username in usernames:
                if username in users_df.index:
                    row = users_df.loc[username]
                    if row["Enabled_norm"] == "FALSE":
                        results.append({
                            "group_url": group_url,
                            "username": username,
                            "full_name": row.get("Full Name", ""),
                            "email": row.get("Email", ""),
                            "enabled": row.get("Enabled", ""),
                            "last_login": row.get("Last Login", ""),
                            "groups_in_csv": row.get("Groups", ""),
                        })
                else:
                    # present on group page but not in CSV
                    results.append({
                        "group_url": group_url,
                        "username": username,
                        "full_name": "",
                        "email": "",
                        "enabled": "NOT_IN_CSV",
                        "last_login": "",
                        "groups_in_csv": "",
                    })

        await browser.close()

    out = pd.DataFrame(results).sort_values(["group_url", "enabled", "username"])
    out.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved: {OUTPUT_PATH} ({len(out)} flagged entries)")


if __name__ == "__main__":
    asyncio.run(main())
