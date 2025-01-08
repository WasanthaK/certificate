import os
import subprocess
from flask import Flask, request, send_from_directory

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_CERTS_DIR = os.path.join(BASE_DIR, "cert-issuer/user_certs")
CA_DIR = os.path.join(BASE_DIR, "cert-issuer/ca")
CA_CERT_PATH = os.path.join(CA_DIR, "ca_cert.crt")
CA_KEY_PATH = os.path.join(CA_DIR, "ca_private.key")

# Ensure directories exist
os.makedirs(USER_CERTS_DIR, exist_ok=True)
os.makedirs(CA_DIR, exist_ok=True)


def create_ca_if_not_exists():
    """Ensure CA certificate and private key exist."""
    if not os.path.exists(CA_CERT_PATH) or not os.path.exists(CA_KEY_PATH):
        try:
            # Generate CA private key
            subprocess.run(
                ["openssl", "genrsa", "-out", CA_KEY_PATH, "2048"],
                check=True
            )
            # Generate self-signed CA certificate
            subprocess.run(
                [
                    "openssl", "req", "-x509", "-new", "-nodes",
                    "-key", CA_KEY_PATH,
                    "-sha256", "-days", "365",
                    "-out", CA_CERT_PATH,
                    "-subj", "/CN=MyCertificateAuthority"
                ],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error creating CA: {e}")
            raise


@app.route("/upload_csr", methods=["POST"])
def upload_csr():
    """Sign the uploaded CSR and return the signed certificate."""
    uploaded_csr = request.files.get("csr_file")
    if not uploaded_csr:
        return "CSR file is required!", 400

    csr_filename = uploaded_csr.filename
    csr_path = os.path.join(USER_CERTS_DIR, csr_filename)
    cert_path = os.path.join(USER_CERTS_DIR, f"{os.path.splitext(csr_filename)[0]}.crt")

    # Save the uploaded CSR
    uploaded_csr.save(csr_path)

    try:
        # Ensure CA exists
        create_ca_if_not_exists()

        # Sign the CSR
        subprocess.run(
            [
                "openssl", "x509", "-req",
                "-in", csr_path,
                "-CA", CA_CERT_PATH,
                "-CAkey", CA_KEY_PATH,
                "-CAcreateserial",
                "-out", cert_path,
                "-days", "365"
            ],
            check=True
        )

        # Return the signed certificate
        return send_from_directory(USER_CERTS_DIR, os.path.basename(cert_path), as_attachment=True)

    except subprocess.CalledProcessError as e:
        return f"Failed to sign CSR: {e}", 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
