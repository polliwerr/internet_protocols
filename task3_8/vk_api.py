import requests


class VKClient:
    BASE_URL = "https://api.vk.com/method/"
    API_VERSION = "5.131"

    def __init__(self, token_path: str):
        self.token = self._load_token(token_path)

    def _load_token(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except FileNotFoundError:
            print(f"[Ошибка] Файл с токеном не найден: {path}")
            exit(1)

    def _request(self, method: str, **params) -> dict:
        payload = {
            "access_token": self.token,
            "v": self.API_VERSION,
            **params
        }
        try:
            response = requests.get(f"{self.BASE_URL}{method}", params=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise ValueError(data["error"]["error_msg"])
            return data["response"]
        except (requests.RequestException, ValueError) as e:
            print(f"[Ошибка запроса] {e}")
            return {}

    def get_user_info(self, user_identifier: str) -> dict:
        data = self._request("users.get", user_ids=user_identifier, name_case="nom")
        return data[0] if data else {}

    def get_friends(self, user_id: int) -> list:
        result = self._request("friends.get", user_id=user_id, order="name", fields="city")
        return result.get("items", [])


class FriendViewer:
    def __init__(self, api_client: VKClient):
        self.api = api_client

    def show_friends(self, user_input: str):
        user = self.api.get_user_info(user_input)
        if not user:
            print("Пользователь не найден.")
            return

        print(f"\nДрузья пользователя {user['first_name']} {user['last_name']} (ID: {user['id']}):\n")
        friends = self.api.get_friends(user['id'])

        if not friends:
            print("Нет доступных друзей для отображения.")
            return

        for idx, f in enumerate(friends, 1):
            print(f"{idx}. {f['first_name']} {f['last_name']} (ID: {f['id']})")


def main():
    vk = VKClient("token.txt")
    username = input("Введите ID или короткий URL пользователя: ").strip()
    viewer = FriendViewer(vk)
    viewer.show_friends(username)


if __name__ == "__main__":
    main()