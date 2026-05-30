# Google Colab Cells Guide

Copy each section below into a separate cell in Google Colab.

---

## Cell 1: Install Dependencies

```python
!pip install beautifulsoup4 requests openai
```

## Cell 2: Imports and API Key Setup

```python
import json
import re
import time
import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openai import OpenAI
from google.colab import userdata

# Try to get API key from Colab secrets, fallback to manual input
try:
    OPENAI_API_KEY = userdata.get('OPENAI_API_KEY')
except:
    OPENAI_API_KEY = input("Enter your OpenAI API Key: ")

client = OpenAI(api_key=OPENAI_API_KEY)
print("✓ OpenAI client initialized")
```

## Cell 3: Scraping Functions (copy the full scraping section from colab_notebook.py)

## Cell 4: AI Enrichment Functions (copy the enrichment section from colab_notebook.py)

## Cell 5: Main Pipeline (copy the run_pipeline function and call it)

---

See `colab_notebook.py` for the complete code to paste into each cell.
