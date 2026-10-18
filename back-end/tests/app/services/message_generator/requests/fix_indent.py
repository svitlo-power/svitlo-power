with open('test_requests.py', 'r') as f:
    content = f.read()

content = content.replace(
    '        result = await req.resolve(MagicMock())\n            assert result == "09:00"',
    '        result = await req.resolve(MagicMock())\n        assert result == "09:00"'
)

with open('test_requests.py', 'w') as f:
    f.write(content)
print('Fixed')