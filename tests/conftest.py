import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

TEST_ENV = {
    "jwt_key": "test-jwt-key-not-for-production",
    "jwt_share_key": "test-share-key-not-for-production",
    "share_token_pw": "test-share-pw",
    "MFA_ENCRYPTION_KEY": "MuelleVfjEo1BUsHRtKSsAhF-8VkRY-tCTsNFgaAngs=",
    "frontend_build": str(SRC_DIR),
    "frontend_build_assets": str(SRC_DIR),
    "use_terms_file": str(SRC_DIR / "app.py"),
    "db_handler": "neo4j",
    "db_pw": "test-db-pw",
    "mail_username": "test-mail",
    "mail_password": "test-mail-pw",
    "mail_template_dir": str(SRC_DIR),
    "open_ai_api_key": "test-openai-key",
    "chat_ai_base_url": "https://example.invalid/v1",
}

for key, value in TEST_ENV.items():
    os.environ.setdefault(key, value)
