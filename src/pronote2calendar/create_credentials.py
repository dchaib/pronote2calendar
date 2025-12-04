import argparse
import json
import secrets

from pronotepy import Client, ClientBase, ParentClient, VieScolaireClient


def get_credentials(qr_code, pin):
    client_class = get_client_class(qr_code["url"])
    if not client_class:
        return 1

    uuid = secrets.token_hex(8)

    client = client_class.qrcode_login(qr_code, pin, uuid)

    credentials = client.export_credentials()

    return credentials


def get_client_class(url: str) -> type[ClientBase] | None:
    if url.endswith("eleve.html"):
        return Client
    elif url.endswith("parent.html"):
        return ParentClient
    elif url.endswith("viescolaire.html"):
        return VieScolaireClient
    else:
        print("Unsupported client type")
        return None


def main():
    parser = argparse.ArgumentParser(description="Process QR code and PIN for login")
    parser.add_argument(
        "--qr_code", type=str, required=True, help="QR code for the login"
    )
    parser.add_argument("--pin", type=str, required=True, help="PIN for the login")

    args = parser.parse_args()

    try:
        qr_code_data = json.loads(args.qr_code)
    except json.JSONDecodeError:
        print("Error: The provided QR code is not a valid JSON.")
        return

    credentials = get_credentials(qr_code_data, args.pin)

    print(json.dumps(credentials, indent=4))


if __name__ == "__main__":
    main()
