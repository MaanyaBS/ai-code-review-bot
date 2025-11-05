import requests

# Test health endpoint
print("Testing /health:")
response = requests.get('http://127.0.0.1:5000/health')
print(response.json())

# Test status endpoint
print("\nTesting /status:")
response = requests.get('http://127.0.0.1:5000/status')
print(response.json())

# Test analyze endpoint
print("\nTesting /analyze:")
data = {
    'code': 'def hello():\n    print("hello")',
    'language': 'python'
}
response = requests.post('http://127.0.0.1:5000/analyze', json=data)
print(response.json())

# Test fix endpoint
print("\nTesting /fix:")
data = {
    'code': 'def hello():\n    print("hello")',
    'language': 'python',
    'create_pr': False
}
response = requests.post('http://127.0.0.1:5000/fix', json=data)
print(response.json())
