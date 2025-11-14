# td-sync

A helper function that **registers/updates your Tabsdata functions** when you run your tabsdata .py function file

Drop `sync_with_server()` into the bottom of any tabsdata function file. Every time your file runs, the function is registered or updated

---

## Install (from GitHub)

```bash
pip install git+https://github.com/adaydan-tabsdata/td-sync.git
```
---
### How to use 

### 1. Import Package into your file

```bash
from td_sync import sync_with_server
```

### 2. Call the Function within your file

```bash
sync_with_server()
```

The function takes a single parameter for  `collection_name`. If no collection name is provided, the function will prompt to select an existing collection or create a new one. 





