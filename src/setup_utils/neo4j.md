# Neo4j Cypher-Shell & Database Admin Commands (Ubuntu)

A practical cheat sheet for managing Neo4j and using Cypher Shell on Ubuntu.

---

# 1. Open Cypher Shell

## Connect using username/password

```bash
cypher-shell -u neo4j -p your_password
```

## Connect to a specific database

```bash
cypher-shell -u neo4j -p your_password -d neo4j
```

## Exit cypher-shell

```bash
:exit
```

---

# 2. Start / Stop Neo4j Server

## Stop Neo4j

```bash
sudo systemctl stop neo4j
```

## Start Neo4j

```bash
sudo systemctl start neo4j
```

## Restart Neo4j

```bash
sudo systemctl restart neo4j
```

## Check Neo4j service status

```bash
sudo systemctl status neo4j
```

---

# 3. Backup Database (Offline Backup)

For Neo4j Community Edition, it is recommended to stop the server before creating a backup.

## Step 1 — Stop Neo4j

```bash
sudo systemctl stop neo4j
```

## Step 2 — Create database dump

```bash
neo4j-admin database dump neo4j --to-path=/home/ubuntu/backups
```

Example output:

```text
/home/ubuntu/backups/neo4j.dump
```

## Step 3 — Restart Neo4j

```bash
sudo systemctl start neo4j
```

---

# 4. Restore Database Backup

## Step 1 — Stop Neo4j

```bash
sudo systemctl stop neo4j
```

## Step 2 — Restore dump file

```bash
neo4j-admin database load neo4j \
  --from-path=/home/ubuntu/backups \
  --overwrite-destination=true
```

## Step 3 — Restart Neo4j

```bash
sudo systemctl start neo4j
```

---

# 5. Show Indexes

Inside `cypher-shell`:

```cypher
SHOW INDEXES;
```

Older Neo4j versions:

```cypher
CALL db.indexes();
```

---

# 6. Show Constraints

```cypher
SHOW CONSTRAINTS;
```

Older Neo4j versions:

```cypher
CALL db.constraints();
```

---

# 7. Reset / Clear Database

## Option A — Delete all nodes and relationships

This preserves indexes and constraints.

```cypher
MATCH (n)
DETACH DELETE n;
```

---

## Option B — Completely reset database

### Stop Neo4j

```bash
sudo systemctl stop neo4j
```

### Delete database files

```bash
sudo rm -rf /var/lib/neo4j/data/databases/neo4j
sudo rm -rf /var/lib/neo4j/data/transactions/neo4j
```

### Restart Neo4j

```bash
sudo systemctl start neo4j
```

Neo4j automatically recreates a fresh empty database.

---

# 8. Show Existing Databases

Inside `cypher-shell`:

```cypher
SHOW DATABASES;
```

---

# 9. Create an Index

```cypher
CREATE INDEX person_name_index
FOR (p:Person)
ON (p.name);
```

---

# 10. Drop an Index

```cypher
DROP INDEX person_name_index;
```

---

# 11. Change Neo4j Password

## Connect using current password

```bash
cypher-shell -u neo4j -p oldpassword
```

## Change password

```cypher
ALTER CURRENT USER SET PASSWORD FROM 'oldpassword' TO 'newpassword';
```

---

# 12. Common Neo4j Paths on Ubuntu

| Purpose | Path |
|---|---|
| Database files | `/var/lib/neo4j/data/databases/` |
| Transaction logs | `/var/lib/neo4j/data/transactions/` |
| Logs | `/var/log/neo4j/` |
| Config file | `/etc/neo4j/neo4j.conf` |
| Import directory | `/var/lib/neo4j/import/` |

---

# 13. View Neo4j Logs

## Main log

```bash
tail -f /var/log/neo4j/neo4j.log
```

## Debug log

```bash
tail -f /var/log/neo4j/debug.log
```

---

# 14. Useful Cypher Queries

## Count all nodes

```cypher
MATCH (n)
RETURN count(n);
```

## Show all labels

```cypher
CALL db.labels();
```

## Show relationship types

```cypher
CALL db.relationshipTypes();
```

## Show property keys

```cypher
CALL db.propertyKeys();
```

---

# 15. Import a Cypher File

```bash
cypher-shell -u neo4j -p password -f import.cypher
```

---

# 16. Export Database Using APOC

If APOC is installed:

```cypher
CALL apoc.export.cypher.all("export.cypher", {});
```

---

# 17. Quick Full Reset Script

```bash
sudo systemctl stop neo4j

sudo rm -rf /var/lib/neo4j/data/databases/neo4j
sudo rm -rf /var/lib/neo4j/data/transactions/neo4j

sudo systemctl start neo4j
```

---

# 18. Verify Neo4j is Running

## Using curl

```bash
curl http://localhost:7474
```

## Open in browser

```text
http://localhost:7474
```

---

# 19. Helpful Notes

- Default Neo4j username is usually:

```text
neo4j
```

- Default Bolt port:

```text
7687
```

- Default Browser UI port:

```text
7474
```

- Cypher files usually use:

```text
.cypher
```

or

```text
.cql
```

extensions.
# 20. Configure RAM / Memory Settings for Neo4j Transactions

Neo4j memory settings are configured in:

```bash
/etc/neo4j/neo4j.conf
```

Edit the config file:

```bash
sudo nano /etc/neo4j/neo4j.conf
```

---

# 21. Main Neo4j Memory Settings

## Heap Memory (JVM RAM)

Controls RAM used for query execution and transactions.

Example:

```properties
server.memory.heap.initial_size=4G
server.memory.heap.max_size=4G
```

Recommended:
- Set both values equal
- Usually use 50–70% of available system RAM

Example for a 16GB server:

```properties
server.memory.heap.initial_size=8G
server.memory.heap.max_size=8G
```

---

## Page Cache Memory

Used for graph data caching.

Example:

```properties
server.memory.pagecache.size=4G
```

General recommendation:
- Leave RAM for OS
- Larger graphs benefit from larger page cache

---

# 22. Transaction Memory Settings

## Maximum memory per transaction

```properties
dbms.memory.transaction.total.max=2G
```

This limits total memory used by all running transactions.

---

## Memory limit per single transaction

```properties
db.memory.transaction.max=1G
```

Useful for preventing very large queries from consuming all RAM.

---

# 23. Example Full Memory Configuration

Example for a server with 16GB RAM:

```properties
server.memory.heap.initial_size=6G
server.memory.heap.max_size=6G

server.memory.pagecache.size=6G

dbms.memory.transaction.total.max=2G
db.memory.transaction.max=1G
```

Approximate allocation:
- Heap: 6GB
- Page Cache: 6GB
- Transactions: 2GB
- Remaining RAM reserved for Linux OS and filesystem cache

---

# 24. Apply Memory Changes

After editing configuration:

## Restart Neo4j

```bash
sudo systemctl restart neo4j
```

---

# 25. Verify Neo4j Memory Settings

Check active settings in logs:

```bash
cat /var/log/neo4j/debug.log | grep memory
```

Or inspect startup logs:

```bash
tail -100 /var/log/neo4j/debug.log
```

---

# 26. Check Server RAM on Ubuntu

## Show total RAM

```bash
free -h
```

## Show detailed memory usage

```bash
htop
```

If `htop` is not installed:

```bash
sudo apt install htop
```

---

# 27. Common Memory Problems

## Out Of Memory Error

Symptoms:
- Neo4j crashes
- JVM heap errors
- Transactions fail

Solutions:
- Increase heap size
- Increase transaction memory
- Optimize Cypher queries
- Add indexes

---

## Transactions Using Too Much RAM

You may see errors like:

```text
The allocation of an extra X MiB would use more than the limit
```

Increase:

```properties
db.memory.transaction.max
```

or:

```properties
dbms.memory.transaction.total.max
```

---

# 28. Recommended Production Setup

General guideline:

| Server RAM | Heap | Page Cache |
|---|---|---|
| 8GB | 3G | 3G |
| 16GB | 6G | 6G |
| 32GB | 12G | 12G |
| 64GB | 24G | 24G |

Always leave RAM available for:
- Ubuntu OS
- File system cache
- Background services

---