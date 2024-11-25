import json
import requests

url = "https://app.mitocube.com/api/datasets/LOGtC9tNC13b/meta"

headers = {"content-type": "application/json",
           "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsYWJlbCI6ImZPdHNxWkNQIiwidmVyaWZpZWQiOnRydWUsInZlcmlmaWVkX2F0IjoxNzMwOTExNzU0LjY1MzY1MzEsImV4cCI6MTczMTA4NDU1NH0.-kCsYgc1ihiIqOgk02i-XzflF25Zelt3RY3Pf1UXCxc"}

arguments = dict(something = "sdfsdfdsfsd",
                 somethingelse ="sdfsdfdsfdsfds")

resp = requests.get(url= url, headers = headers)
# resp = requests.get(url= url, headers = headers, params = arguments)
# resp = requests.post(url= url, headers = headers, data = json.dumps(arguments))

# print(resp.json())

print(json.dumps(json.loads(resp.content), indent = 2))

