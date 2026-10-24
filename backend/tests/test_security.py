from app.security import hash_password, verify_password


def test_password_round_trip():
    stored = hash_password("gizli-parola")
    assert verify_password("gizli-parola", stored)
    assert not verify_password("baska-parola", stored)


def test_same_password_gets_different_salt():
    assert hash_password("ayni") != hash_password("ayni")


def test_malformed_hash_is_rejected():
    assert not verify_password("x", "bozuk-ozet")
