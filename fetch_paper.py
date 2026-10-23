import urllib.request
import urllib.parse
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

query = 'TITLE:"Impact of Storing Condition on Staling and Microbial Spoilage Behavior of Bread and Their Contribution to Prevent Food Waste"'
url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={urllib.parse.quote(query)}&format=json&resultType=core'
req = urllib.request.Request(url, headers={'User-Agent': 'test@example.com'})
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode('utf-8'))
        results = data.get('resultList', {}).get('result', [])
        if results:
            print('DOI:', results[0].get('doi'))
            print('Title:', results[0].get('title'))
            print('Abstract:', results[0].get('abstractText'))
        else:
            print('Not found')
except Exception as e:
    print(e)
