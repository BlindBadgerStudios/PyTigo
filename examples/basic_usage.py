from pytigo import TigoClient


def main() -> None:
    client = TigoClient(username="you@example.com", password="super-secret")
    auth = client.login()
    page = client.list_systems()
    system = page.items[0]

    print(f"user_id={auth.user_id}")
    print(f"system_id={system.system_id}")
    print(f"system_name={system.name}")


if __name__ == "__main__":
    main()
