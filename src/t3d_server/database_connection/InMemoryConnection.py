from t3d_server.database_connection.BaseConnection import BaseConnection


class InMemoryConnection(BaseConnection):
    """
    A connection class that stores data in memory for testing and debugging purposes.
    This simulates a simple object store using nested dictionaries.

    Structure:
        self.store = {
            "collection1": {
                "object1": b"...",
                "object2": b"...",
                ...
            },
            ...
        }
    """

    def __init__(self):
        super().__init__()
        self.store: dict[str, dict[str, bytes]] = {}

    def list_collections(self) -> list[str]:
        return list(self.store.keys())

    def check_collections_exists(
        self, collection_names: list[str]
    ) -> list[bool]:
        return [name in self.store for name in collection_names]

    def create_collections(self, collection_names: list[str]) -> None:
        for name in collection_names:
            self.store.setdefault(name, {})

    def delete_collections(self, collection_names: list[str]) -> None:
        for name in collection_names:
            self.store.pop(name, None)

    def list_objects(self, collection_name: str) -> list[str]:
        return list(self.store.get(collection_name, {}).keys())

    def check_objects_exist(
        self, collection_name: str, object_names: list[str]
    ) -> list[bool]:
        collection = self.store.get(collection_name, {})
        return [name in collection for name in object_names]

    def delete_objects(
        self, collection_name: str, object_names: list[str]
    ) -> None:
        collection = self.store.get(collection_name, {})
        for name in object_names:
            collection.pop(name, None)

    def get_objects(
        self, collection_name: str, object_names: list[str]
    ) -> list[bytes]:
        collection = self.store.get(collection_name, {})
        return [collection[name] for name in object_names]

    def put_objects(
        self,
        collection_name: str,
        object_names: list[str],
        objects: list[bytes],
    ) -> None:
        self.store.setdefault(collection_name, {})
        for name, obj in zip(object_names, objects):
            self.store[collection_name][name] = obj

    def put_objects_with_duplicity_check(
        self,
        collection_name: str,
        object_names: list[str],
        objects: list[bytes],
    ) -> list[bool]:
        self.store.setdefault(collection_name, {})
        collection = self.store[collection_name]

        already_exists = [name in collection for name in object_names]
        for name, obj, exists in zip(object_names, objects, already_exists):
            if not exists:
                collection[name] = obj
        return already_exists
