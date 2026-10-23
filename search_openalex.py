import urllib.request
import urllib.parse
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

foods = [
    'almonds', 'cashews', 'walnuts', 'peanuts', 'pistachios',
    'plain biscuits', 'sweet biscuits', 'cream-filled biscuits', 'crackers',
    'bread', 'buns', 'cakes', 'muffins', 'pastries'
]

results = {}
for food in foods:
    query = f'"{food}" AND ("water activity" OR "moisture content") AND "shelf life" AND "packaging"'
    url = f'https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page=1&sort=cited_by_count:desc'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'mailto:test@example.com'})
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('results'):
                work = data['results'][0]
                results[food] = {
                    'title': work.get('title'),
                    'doi': work.get('doi'),
                    'abstract': work.get('abstract_inverted_index')
                }
            else:
                results[food] = 'No matches'
    except Exception as e:
        results[food] = str(e)
        
with open('food_audit_temp.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
