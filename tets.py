# Dependencies to install:

# $ python -m pip install requests

import requests

url = "https://solana-gateway.moralis.io/token/mainnet/holders/FiApah1fxARNmW7mhFYkP3VuS21QieEu7rjPfhbxpump"

headers = {
  "Accept": "application/json",
  "X-API-Key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjkyZThkZmJhLTAyOGUtNGI5NC04ZjMzLWJkMTIwY2Y1MmM4MSIsIm9yZ0lkIjoiNDY3MjA2IiwidXNlcklkIjoiNDgwNjQ1IiwidHlwZUlkIjoiZmRlNTBkZmItNWIwNS00ZTIzLWIzODYtYjhiMzc5NTUwM2JlIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NTYxNDY2NjQsImV4cCI6NDkxMTkwNjY2NH0.iOqIBD7EERIIi38WSiqzcEfqwWxdAWjLDBL7tNZ-6MQ"
}

response = requests.request("GET", url, headers=headers)

print(response.text)