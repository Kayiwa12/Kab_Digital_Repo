import requests
import json

BASE_URL = "https://backend.kab.ac.ug/server/api"
COMMUNITY_UUID = "95cbea8b-fdc6-4d8a-9f20-d51ad2814f12"

headers = {
    "User-Agent": "Kabale-Research-Discovery/1.0",
    "Accept": "application/json"
}

def probe():
    print(f"--- 1. Testing root and communities ---")
    res = requests.get(f"{BASE_URL}/core/communities", headers=headers, timeout=15)
    print(f"Communities status: {res.status_code}")
    data = res.json()
    embedded = data.get("_embedded", {})
    communities = embedded.get("communities", [])
    print(f"Total top-level communities returned in page: {len(communities)}")
    for c in communities:
        print(f"  - UUID: {c.get('uuid')} | Name: {c.get('name')}")

    print(f"\n--- 2. Testing Postgraduate Community {COMMUNITY_UUID} ---")
    res_comm = requests.get(f"{BASE_URL}/core/communities/{COMMUNITY_UUID}", headers=headers, timeout=15)
    print(f"Target community status: {res_comm.status_code}")
    if res_comm.status_code == 200:
        comm_data = res_comm.json()
        print(f"Target Community Name: {comm_data.get('name')}")
        print(f"Links in target community: {list(comm_data.get('_links', {}).keys())}")
        
        # Check collections
        colls_link = comm_data.get('_links', {}).get('collections', {}).get('href')
        subcomms_link = comm_data.get('_links', {}).get('subcommunities', {}).get('href')
        print(f"Collections link: {colls_link}")
        print(f"Subcommunities link: {subcomms_link}")
        
        if colls_link:
            res_colls = requests.get(colls_link, headers=headers, timeout=15)
            print(f"Collections response status: {res_colls.status_code}")
            colls_data = res_colls.json()
            colls = colls_data.get('_embedded', {}).get('collections', [])
            print(f"Collections count: {len(colls)}")
            for col in colls:
                print(f"   * Collection: {col.get('name')} (UUID: {col.get('uuid')})")

        if subcomms_link:
            res_subs = requests.get(subcomms_link, headers=headers, timeout=15)
            print(f"Subcommunities status: {res_subs.status_code}")
            subs = res_subs.json().get('_embedded', {}).get('subcommunities', [])
            print(f"Subcommunities count: {len(subs)}")
            for sub in subs:
                print(f"   * Subcommunity: {sub.get('name')} (UUID: {sub.get('uuid')})")

    print(f"\n--- 3. Testing Discovery API (/discover/search/objects) ---")
    discovery_url = f"{BASE_URL}/discover/search/objects"
    params = {
        "scope": COMMUNITY_UUID,
        "size": 5
    }
    res_disc = requests.get(discovery_url, params=params, headers=headers, timeout=15)
    print(f"Discovery status: {res_disc.status_code}")
    if res_disc.status_code == 200:
        disc_data = res_disc.json()
        page = disc_data.get('_embedded', {}).get('searchResult', {}).get('page', {})
        print(f"Discovery totalElements: {page.get('totalElements')}, totalPages: {page.get('totalPages')}")
        objects = disc_data.get('_embedded', {}).get('searchResult', {}).get('_embedded', {}).get('objects', [])
        print(f"Objects returned in page: {len(objects)}")
        for i, obj in enumerate(objects):
            item = obj.get('_embedded', {}).get('indexableObject', {})
            print(f"\nSample Record #{i+1}:")
            print(f"  UUID: {item.get('uuid')}")
            print(f"  Name: {item.get('name')}")
            print(f"  Handle: {item.get('handle')}")
            print(f"  Metadata keys present: {list(item.get('metadata', {}).keys())[:10]}")
            # print sample metadata fields
            md = item.get('metadata', {})
            for key in ['dc.title', 'dc.contributor.author', 'dc.date.issued', 'dc.subject', 'dc.description.abstract', 'dc.type']:
                vals = md.get(key, [])
                print(f"    {key}: {[v.get('value') for v in vals][:3]}")
    else:
        print(f"Discovery returned {res_disc.status_code}: {res_disc.text[:300]}")

if __name__ == "__main__":
    probe()
