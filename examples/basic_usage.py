import os

from pytigo import TigoClient


def main() -> None:
    client = TigoClient(
        email=os.environ["TIGO_EMAIL"],
        password=os.environ["TIGO_PASSWORD"],
    )
    system_id = client.login()
    info = client.get_system_info(system_id)
    topology = client.get_system_topology(system_id)

    print(f"system_id={system_id}")
    print(f"system_name={info.system_name}")
    print(f"panels={len(topology.panels)}")
    print(f"inverters={len(topology.inverters)}")


if __name__ == "__main__":
    main()
