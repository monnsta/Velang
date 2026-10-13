from app.core.security import new_token, normalize_email, token_hash


def test_email_normalization():
	assert normalize_email("  TEST@Example.COM ") == "test@example.com"


def test_token_hash_is_stable_and_non_reversible():
	token = new_token()
	assert token_hash(token) == token_hash(token)
	assert token_hash(token) != token
	assert len(token_hash(token)) == 64
