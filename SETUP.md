# MitoCube - Installation & Environment Setup Guide 

## Prerequisites

- Python 3.11 (required - Newer version will not work)
- Node.js + Yarn 
- Neo4j Desktop 
- Podman (or Docker)
- Access to 4 Mitocube reporsitories: mitocube-backend, mitocube-frontend, mitocube-api-hooks, mitocube-viz 

---

## 0. Clone all repositories

```bash
git clone <mitocube-backend-url>
git clone <mitocube-frontend-url>
git clone <mitocube-api-hooks-url>
git clone <mitocube-viz-url>
```

## 1. Backend Environment Setup (mitocube-backend)

### 1.1 Install Python3.11 

 - Python 3.11

### 1.2 Create Virtual Environment 
```bash
cd mitocube-backend 
python3.11 -m venv venv
source venv/bin/activate 
```

### 1.3 Install requirements 
```bash
pip3 install -r requirements.txt
```

### 1.4 Create .env file 
Create a `.env` file containing credentials. 

**Note:** Do not commit this file to version control. Add `.env` to your `.gitignore`.

In mitocube-backend root:

```env
# mail
mail_username=""
mail_password=""

# tokens - long, random strings
jwt_key=""
jwt_share_key=""
share_token_pw=""

# AI settings
chat_ai_base_url=""
open_ai_api_key=""

# general
lead_contact_first_name="YourFirstName"
lead_contact_last_name="YourLastName"
lead_contact_institute="Your Institute"
lead_contact_group="Your Department"
lead_contact="your.email@domain.de"

# required paths - must exist on disk
mail_template_dir="/absolute/path/to/mitocube-backend/resources/templates/email"
frontend_build="/absolute/path/to/mitocube-frontend/dist"
frontend_build_assets="/absolute/path/to/mitocube-frontend/dist/assets"
network_dir="/absolute/path/to/mitocube-backend/resources/network"
CONTROL_PROTEOME_FILE="/absolute/path/to/mitocube-backend/resources/features/controls/data.txt"
instrument_states="/absolute/path/to/mitocube-backend/resources/maintenance/instrumentstates.txt"
use_terms_file="/absolute/path/to/mitocube-backend/resources/terms/usage.json"

Token=""

MFA_ENCRYPTION_KEY=""

```

Note: frontend_build, frontend_build_assets, mail_template_dir, network_dir, CONTROL_PROTEOME_FILE, instrument_states, and use_terms_file are all validated as paths that must already exist on disk - the app throws a validation error on startup otherwise.

Confirm required files/folders exist:
```bash
ls resources/attributes/attributes.json
ls resources/data
ls resources/users
```

### 1.5 Start Neo4j 

1. Download and install Neo4j Desktop.
2. Create a new instance.
3. Set a name and password for the instance - the password must match db_pw in your backend `.env`
4. Start the instance. 

The instance's connection URL, username, and password go directly into your backend .env:
```env
db_uri=""
db_user="neo4j"
db_pw="<password you set for the instance>"
```

### 1.6 Setup MongoDB via Podman(or Docker)

Add mongoDB credentials in the `.env` file;

```env
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=your-secure-password
MONGO_USER=admin
MONGO_PASSWORD=your-secure-password
AGENT_MONGO_DB_NAME=langgraph
```

From the directory containing your `.env` file, run:

```bash
podman run -d \
  --name mongodb \
  --restart unless-stopped \
  --env-file .env \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:latest
```

This command will:

* Start MongoDB in the background.
* Persist data in the `mongodb_data` Docker volume.
* Automatically restart MongoDB after a server reboot.
* Initialize the root user using the credentials from the `.env` file.

Verify it's running:
```bash
podman ps
podman logs -f mongodb
```
You should see a running container named mongodb. 

### 1.7 Set up the database (first run only)

Run the one-time setup:

```bash
python3 src/app.py --setup_database \
  --resources_path /path/to/mitocube-backend/resources \
  --users /path/to/mitocube-backend/users.json
```

If the `--users` path does not exist, the script skips user migration and generates just the lead admin account. 

### 1.8 Get Password and Log in 
- The lead account's password is randomly generated and emailed to lead_contact (from `.env`).
- After first login, enable Multi Factor Authentication in  account settings. 

### 1.9 Start the backend 
```bash
source venv/bin/activate
python3 src/app.py 
```

Runs at http://127.0.0.1:5002.

Note: do not pass --setup_database again after the first successful run.

---

## 2. API Hooks setup (mitocube-api-hooks)

```bash
cd mitocube-api-hooks
yarn install 
yarn link 
```

---

## 3. Viz Setup (mitocube-viz)

```bash 
cd mitocube-viz 
yarn install 
yarn link 
yarn link @mitocube/api-hooks 
```

**Note:** mitocube-viz imports from @mitocube/api-hooks internally, so it needs to be linked separately too. 

---

## 4. Frontend setup (mitocube-frontend)

To install required packages, use

```bash
cd mitocube-frontend 
yarn install 
yarn link @mitocube/api-hooks 
yarn link @mitocube/viz
```
This will install all the required packages and link api-hooks and viz 

For development, use

```bash
yarn dev
```

This will start the frontend at http://localhost:3000.

For deployment use

```bash
yarn build
```

This builds the frontend assets required by the backend (frontend_build / frontend_build_assets in `.env`).

---

## 5. First-time setup order (summary)

1. Clone all 4 repos as siblings
2. Install Python 3.11
3. Backend: venv, pip install -r requirements.txt, .env, start Neo4j (Desktop), start MongoDB (Podman), --setup_database (once), get lead password, log in, enable MFA
4. API Hooks: yarn install, yarn link
5. Viz: yarn install, yarn link, yarn link @mitocube/api-hooks
6. Frontend: yarn install, yarn link @mitocube/api-hooks, yarn link @mitocube/viz, yarn build, yarn dev
7. Start backend normally: python3 src/app.py
8. Visit http://localhost:3000 with backend running on port 5002

