# CMS Group Access Auditor

```bash
# create virtual env
python3 -m venv venv

# activate virtual env
source venv/bin/activate # MacOS
venv\Scripts\activate # Windows

# download dependencies
pip install pandas playwright
playwright install chromium

# run script
python check_disabled.py
```

Before running script:
- download a list of CLA users
- name it `users.csv`
- create a file called `group_urls.txt`
- make sure `group_urls.txt` is valid
    -  the file should have 1 url per line

After running script:
- a page should pop up
- log in with information
- come back to terminal
- press `enter`
- let program run