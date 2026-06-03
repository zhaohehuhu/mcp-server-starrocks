"""
Unit tests for TLS/SSL option builders in db_client.

These tests are pure-function tests and do NOT require a running StarRocks
cluster. They lock in the env-var -> mysql.connector / Arrow Flight SQL TLS
mapping (including the VERIFY_CA usage validated against bts JFK ISR).

Run with: pytest tests/test_ssl_options.py -v
"""

import os
import contextlib
import pytest

from src.mcp_server_starrocks.db_client import (
    _build_mysql_ssl_options,
    _build_flight_sql_tls,
    _env_flag,
)

# ADBC Flight SQL option keys (must match db_client implementation).
TLS_SKIP_VERIFY = "adbc.flight.sql.client_option.tls_skip_verify"
TLS_ROOT_CERTS = "adbc.flight.sql.client_option.tls_root_certs"

# All env vars consumed by the SSL/TLS builders.
SSL_ENV_KEYS = [
    "STARROCKS_SSL_DISABLED",
    "STARROCKS_SSL_CA",
    "STARROCKS_SSL_CERT",
    "STARROCKS_SSL_KEY",
    "STARROCKS_SSL_VERIFY_CERT",
    "STARROCKS_SSL_VERIFY_IDENTITY",
    "STARROCKS_TLS_VERSIONS",
    "STARROCKS_FE_ARROW_FLIGHT_SQL_USE_TLS",
]


@contextlib.contextmanager
def ssl_env(**overrides):
    """Clear all SSL env vars, apply only the given overrides, then restore."""
    saved = {k: os.environ.pop(k, None) for k in SSL_ENV_KEYS}
    try:
        for key, value in overrides.items():
            os.environ[key] = value
        yield
    finally:
        for key in SSL_ENV_KEYS:
            os.environ.pop(key, None)
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value


class TestEnvFlag:
    """Test cases for the _env_flag helper."""

    def test_unset_returns_default(self):
        with ssl_env():
            assert _env_flag("STARROCKS_SSL_VERIFY_CERT") is False
            assert _env_flag("STARROCKS_SSL_VERIFY_CERT", default=True) is True

    @pytest.mark.parametrize("value", ["true", "True", "1", "yes", "on", "  TRUE  "])
    def test_truthy_values(self, value):
        with ssl_env(STARROCKS_SSL_VERIFY_CERT=value):
            assert _env_flag("STARROCKS_SSL_VERIFY_CERT") is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "", "random"])
    def test_falsy_values(self, value):
        with ssl_env(STARROCKS_SSL_VERIFY_CERT=value):
            assert _env_flag("STARROCKS_SSL_VERIFY_CERT") is False


class TestBuildMysqlSslOptions:
    """Test cases for _build_mysql_ssl_options."""

    def test_no_env_returns_empty(self):
        """No SSL env vars -> empty dict (mysql.connector keeps its defaults)."""
        with ssl_env():
            assert _build_mysql_ssl_options() == {}

    def test_verify_ca_only(self):
        """The bts JFK ISR case: VERIFY_CA, no certs, no identity check."""
        with ssl_env(STARROCKS_SSL_VERIFY_CERT="true"):
            opts = _build_mysql_ssl_options()
        assert opts == {"ssl_verify_cert": True}
        # VERIFY_CA must NOT enable hostname verification.
        assert "ssl_verify_identity" not in opts
        # And must NOT require any certificate file.
        assert "ssl_ca" not in opts

    def test_verify_identity(self):
        with ssl_env(STARROCKS_SSL_VERIFY_CERT="true",
                     STARROCKS_SSL_VERIFY_IDENTITY="true"):
            opts = _build_mysql_ssl_options()
        assert opts == {"ssl_verify_cert": True, "ssl_verify_identity": True}

    def test_ca_path(self):
        with ssl_env(STARROCKS_SSL_CA="/tmp/ca.pem",
                     STARROCKS_SSL_VERIFY_CERT="true"):
            opts = _build_mysql_ssl_options()
        assert opts == {"ssl_ca": "/tmp/ca.pem", "ssl_verify_cert": True}

    def test_mutual_tls(self):
        with ssl_env(STARROCKS_SSL_CA="/tmp/ca.pem",
                     STARROCKS_SSL_CERT="/tmp/client.pem",
                     STARROCKS_SSL_KEY="/tmp/client.key",
                     STARROCKS_SSL_VERIFY_CERT="true"):
            opts = _build_mysql_ssl_options()
        assert opts == {
            "ssl_ca": "/tmp/ca.pem",
            "ssl_cert": "/tmp/client.pem",
            "ssl_key": "/tmp/client.key",
            "ssl_verify_cert": True,
        }

    def test_tls_versions_parsed_into_list(self):
        with ssl_env(STARROCKS_TLS_VERSIONS="TLSv1.2, TLSv1.3 ,"):
            opts = _build_mysql_ssl_options()
        assert opts == {"tls_versions": ["TLSv1.2", "TLSv1.3"]}

    def test_ssl_disabled_overrides_everything(self):
        with ssl_env(STARROCKS_SSL_DISABLED="true",
                     STARROCKS_SSL_CA="/tmp/ca.pem",
                     STARROCKS_SSL_VERIFY_CERT="true"):
            opts = _build_mysql_ssl_options()
        assert opts == {"ssl_disabled": True}


class TestBuildFlightSqlTls:
    """Test cases for _build_flight_sql_tls."""

    def test_plaintext_by_default(self):
        with ssl_env():
            uri, kwargs = _build_flight_sql_tls("fe-host", "9408")
        assert uri == "grpc://fe-host:9408"
        assert kwargs == {}

    def test_tls_skip_verify_when_not_verifying(self):
        with ssl_env(STARROCKS_FE_ARROW_FLIGHT_SQL_USE_TLS="true"):
            uri, kwargs = _build_flight_sql_tls("fe-host", "9408")
        assert uri == "grpc+tls://fe-host:9408"
        assert kwargs[TLS_SKIP_VERIFY] == "true"
        assert TLS_ROOT_CERTS not in kwargs

    def test_tls_verify_cert(self):
        with ssl_env(STARROCKS_FE_ARROW_FLIGHT_SQL_USE_TLS="true",
                     STARROCKS_SSL_VERIFY_CERT="true"):
            uri, kwargs = _build_flight_sql_tls("fe-host", "9408")
        assert uri == "grpc+tls://fe-host:9408"
        assert kwargs[TLS_SKIP_VERIFY] == "false"

    def test_tls_root_certs_read_from_ca_file(self, tmp_path):
        ca_file = tmp_path / "ca.pem"
        ca_file.write_text("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----\n")
        with ssl_env(STARROCKS_FE_ARROW_FLIGHT_SQL_USE_TLS="true",
                     STARROCKS_SSL_VERIFY_CERT="true",
                     STARROCKS_SSL_CA=str(ca_file)):
            uri, kwargs = _build_flight_sql_tls("fe-host", "9408")
        assert uri == "grpc+tls://fe-host:9408"
        assert kwargs[TLS_SKIP_VERIFY] == "false"
        assert "BEGIN CERTIFICATE" in kwargs[TLS_ROOT_CERTS]

    def test_missing_ca_file_is_tolerated(self):
        """A non-existent CA path should not raise; root certs key is just omitted."""
        with ssl_env(STARROCKS_FE_ARROW_FLIGHT_SQL_USE_TLS="true",
                     STARROCKS_SSL_CA="/nonexistent/ca.pem"):
            uri, kwargs = _build_flight_sql_tls("fe-host", "9408")
        assert uri == "grpc+tls://fe-host:9408"
        assert TLS_ROOT_CERTS not in kwargs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
