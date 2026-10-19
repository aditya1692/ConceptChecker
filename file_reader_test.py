import json

# Open the file and parse the JSON data
with open('golden_pairs.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# The data is now a standard Python dictionary or list
print(data)