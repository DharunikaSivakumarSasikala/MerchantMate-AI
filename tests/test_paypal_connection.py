from app.paypal_service import get_access_token


def main():
    try:
        token = get_access_token()

        print("PayPal Sandbox connection successful.")
        print(f"Access token received: {token[:10]}...")

    except Exception as exc:
        print("PayPal Sandbox connection failed.")
        print(exc)


if __name__ == "__main__":
    main()