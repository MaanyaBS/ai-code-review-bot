import requests

response = requests.post('http://127.0.0.1:5000/fix', json={
    'code': 'def hello():\n    print("hello")',
    'language': 'python',
    'create_pr': False
})
print(response.json())
