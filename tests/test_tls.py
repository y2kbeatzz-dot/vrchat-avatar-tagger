"""Offline tests for VRChat's verified native TLS client configuration."""
import ssl
import sys
import unittest

import tagger_core


class TLSConfigurationTests(unittest.TestCase):
    def test_friendly_certificate_error(self):
        error = RuntimeError(
            "HTTPSConnectionPool(host='api.vrchat.cloud', port=443): "
            "Max retries exceeded (Caused by SSLError("
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "self-signed certificate in certificate chain))"
        )
        message = tagger_core.friendly_login_error(error)
        self.assertIn("Secure connection to VRChat could not be verified", message)
        self.assertIn("SSL verification remains enabled", message)
        self.assertNotIn("HTTPSConnectionPool(", message)

    def test_unrelated_error_does_not_claim_certificate_failure(self):
        message = tagger_core.friendly_login_error(ValueError("not a certificate issue"))
        self.assertTrue(message.startswith("ValueError:"))
        self.assertNotIn("SSL verification remains enabled", message)

    def test_connection_uses_verified_context_without_network_requests(self):
        # Client construction initializes the SDK's urllib3 PoolManager but does
        # not send any account credentials or contact VRChat.
        client, _save = tagger_core.create_session("ci-test-user", "ci-test-password")
        self.assertTrue(client.configuration.verify_ssl)
        self.assertTrue(client.rest_client.pool_manager.connection_pool_kw.get("cert_reqs") == ssl.CERT_REQUIRED)
        if sys.platform in ("darwin", "win32"):
            import truststore

            context = client.rest_client.pool_manager.connection_pool_kw.get("ssl_context")
            self.assertIsInstance(context, truststore.SSLContext)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)


if __name__ == "__main__":
    unittest.main()
