"""SAP'ta musteri ara — CardCode bulmak icin."""
import sys
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SAP_URL    = "https://10.11.10.46:50000/b1s/v1"
COMPANY_DB = "2026_Test"
USERNAME   = "manager"
PASSWORD   = "NyNl.2021"

def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "BASARI"

    s = requests.Session()
    s.verify = False

    # Login
    r = s.post(f"{SAP_URL}/Login", json={"CompanyDB": COMPANY_DB, "UserName": USERNAME, "Password": PASSWORD})
    if not r.ok:
        print(f"Login hatasi: {r.text[:200]}"); sys.exit(1)
    print(f"Login OK\n")

    # Ara
    r = s.get(f"{SAP_URL}/BusinessPartners", params={
        "$select": "CardCode,CardName,TaxOfficeNo,Phone1,EmailAddress",
        "$filter": f"contains(CardName, '{query}')",
        "$top": 20,
    })
    if not r.ok:
        print(f"Arama hatasi: {r.text[:200]}"); sys.exit(1)

    partners = r.json().get("value", [])
    if not partners:
        print(f"'{query}' ile esleşen musteri bulunamadi.")
    else:
        print(f"'{query}' araması — {len(partners)} sonuc:\n")
        print(f"{'CardCode':<15} {'CardName':<45} {'VKN':<12} {'Tel'}")
        print("-" * 90)
        for p in partners:
            print(f"{p.get('CardCode',''):<15} {p.get('CardName',''):<45} {p.get('TaxOfficeNo',''):<12} {p.get('Phone1','')}")

    s.post(f"{SAP_URL}/Logout")

if __name__ == "__main__":
    main()
