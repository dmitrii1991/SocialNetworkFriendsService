from django.test import TestCase, TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Friendship, User, StatusApplicationFriends
from .serializers import UserCreateSerializer
from .test_data import TEST_DATA_USERS
from .enums import StatusEnum, StatusApplicationEnum


def get_credits(data: dict) -> dict:
    return dict(email=data["email"], password=data["password"])


def create_user(data: dict) -> User:
    serializer = UserCreateSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.save()


class CreateUserAPIViewTests(TestCase):

    def test_post_success(self):
        response = self.client.post("/user/create/", data=TEST_DATA_USERS[0])
        self.assertEqual(response.status_code, 201)
        response_dict = response.json()
        for key, value in TEST_DATA_USERS[0].items():
            if key in set(TEST_DATA_USERS[0].keys()).intersection(set(response_dict.keys())):
                self.assertEqual(value, response_dict[key])

    def test_post_error(self):
        self.client.post("/user/create/", data=TEST_DATA_USERS[0])
        response = self.client.post("/user/create/", data=TEST_DATA_USERS[0])
        self.assertEqual(response.status_code, 400)
        response_dict = response.json()
        self.assertEqual(response_dict["email"][0], "Пользователь with this Почта already exists.")
        self.assertEqual(response_dict["username"][0], "Пользователь with this Никнейм already exists.")


class TokenObtainPairViewTests(TestCase):

    def setUp(self):
        create_user(TEST_DATA_USERS[0])

    def test_post_success(self):
        response = self.client.post("/api/token/", data=get_credits(TEST_DATA_USERS[0]))
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertTrue(isinstance(response_dict["refresh"], str))
        self.assertTrue(isinstance(response_dict["access"], str))

    def test_post_error_incorrect_password(self):
        test_data = TEST_DATA_USERS[0].copy()
        test_data["password"] += "1"
        response = self.client.post("/api/token/", data=get_credits(test_data))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "No active account found with the given credentials")

    def test_post_error_incorrect_email(self):
        test_data = TEST_DATA_USERS[0].copy()
        test_data["email"] += "1"
        response = self.client.post("/api/token/", data=get_credits(test_data))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "No active account found with the given credentials")


class UserMeAPIViewTests(TestCase):

    def setUp(self):
        user = create_user(TEST_DATA_USERS[0])
        self.token = RefreshToken.for_user(user).access_token

    def test_get(self):
        response = self.client.get("/user/me/profile/", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        for key, value in TEST_DATA_USERS[0].items():
            if key in set(TEST_DATA_USERS[0].keys()).intersection(set(response_dict.keys())):
                self.assertEqual(value, response_dict[key])
        self.assertTrue(isinstance(response_dict["date_joined"], str))
        self.assertTrue(isinstance(response_dict["friends"], list))
        self.assertTrue(isinstance(response_dict["id"], int))


class UserAPIViewTests(TestCase):
    def setUp(self):
        self.user_1 = create_user(TEST_DATA_USERS[0])
        self.token = RefreshToken.for_user(self.user_1).access_token
        self.user_2 = create_user(TEST_DATA_USERS[1])
        self.id_2 = self.user_2.id

    def test_get_success(self):
        response = self.client.get(f"/user/{self.id_2}/", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        for key, value in TEST_DATA_USERS[1].items():
            if key in set(TEST_DATA_USERS[1].keys()).intersection(set(response_dict.keys())):
                self.assertEqual(value, response_dict[key])
        self.assertTrue(isinstance(response_dict["date_joined"], str))
        self.assertTrue(isinstance(response_dict["friends"], list))
        self.assertTrue(isinstance(response_dict["id"], int))

    def test_get_error_not_exist_id(self):
        response = self.client.get("/user/22/", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Not found.")

    def test_delete_success(self):
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        response = self.client.delete(f"/user/{self.id_2}/", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Friendship.objects.filter(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.REJECTED
        ).exists())
        self.assertTrue(Friendship.objects.filter(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.REJECTED
        ).exists())
        with self.assertRaises(Friendship.DoesNotExist):
            Friendship.objects.get(
                outgoing_friend=self.user_1,
                incoming_friend=self.user_2,
                status=StatusApplicationFriends.ACCEPTED
            )

    def test_delete_error_not_exits(self):
        response = self.client.delete(f"/user/{self.id_2}/", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], 'Вы не можете удалить из друзей')


class SubmittedApplicationInANDOutViewSetTests(TestCase):
    def setUp(self):
        self.user_1 = create_user(TEST_DATA_USERS[0])
        self.token_1 = RefreshToken.for_user(self.user_1).access_token
        self.user_2 = create_user(TEST_DATA_USERS[1])
        self.token_2 = RefreshToken.for_user(self.user_2).access_token
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.SUBMITTED
        ).save()

    def test_get_in(self):
        response = self.client.get("/user/me/submitted/in/", headers={"Authorization": f"Bearer {self.token_1}"})
        self.assertEqual(response.status_code, 200)
        response_list = response.json()
        self.assertEqual(len(response_list), 1)
        self.assertEqual(response_list[0]["in_user"]["id"], self.user_2.id)
        self.assertEqual(response_list[0]["in_user"]["email"], self.user_2.email)
        self.assertEqual(response_list[0]["in_user"]["username"], self.user_2.username)

    def test_get_out(self):
        response = self.client.get("/user/me/submitted/out/", headers={"Authorization": f"Bearer {self.token_2}"})
        self.assertEqual(response.status_code, 200)
        response_list = response.json()
        self.assertEqual(len(response_list), 1)
        self.assertEqual(response_list[0]["out_user"]["id"], self.user_1.id)
        self.assertEqual(response_list[0]["out_user"]["email"], self.user_1.email)
        self.assertEqual(response_list[0]["out_user"]["username"], self.user_1.username)


class FriendsViewSetTests(TestCase):
    def setUp(self):
        self.user_1 = create_user(TEST_DATA_USERS[0])
        self.token_1 = RefreshToken.for_user(self.user_1).access_token
        self.user_2 = create_user(TEST_DATA_USERS[1])
        self.user_3 = create_user(TEST_DATA_USERS[2])
        self.token_3 = RefreshToken.for_user(self.user_3).access_token
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_3,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_3,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_3,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_3,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.ACCEPTED
        ).save()

    def test_get_friends_user1(self):
        response = self.client.get("/user/me/friends/", headers={"Authorization": f"Bearer {self.token_1}"})
        self.assertEqual(response.status_code, 200)
        response_list = response.json()
        self.assertEqual(len(response_list), 2)
        for i, item in enumerate(response_list):
            item["email"] = TEST_DATA_USERS[item["id"] - 1]["email"]
            item["username"] = TEST_DATA_USERS[item["id"] - 1]["username"]

    def test_get_friends_user2(self):
        response = self.client.get("/user/me/friends/", headers={"Authorization": f"Bearer {self.token_3}"})
        self.assertEqual(response.status_code, 200)
        response_list = response.json()
        self.assertEqual(len(response_list), 2)
        for i, item in enumerate(response_list):
            item["email"] = TEST_DATA_USERS[item["id"] - 1]["email"]
            item["username"] = TEST_DATA_USERS[item["id"] - 1]["username"]


class ApplicationAPIViewTests(TransactionTestCase):
    def setUp(self):
        self.user_1 = create_user(TEST_DATA_USERS[0])
        self.token_1 = RefreshToken.for_user(self.user_1).access_token
        self.user_2 = create_user(TEST_DATA_USERS[1])
        self.token_2 = RefreshToken.for_user(self.user_2).access_token

    def test_post_error_send_app_self(self):
        response = self.client.post(
            f"/user/{self.user_1.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 400)
        response_dict = response.json()
        self.assertEqual(response_dict["detail"], "Вы не можете отправить заявку самому себе")
        with self.assertRaises(Friendship.DoesNotExist):
            Friendship.objects.get(
                outgoing_friend=self.user_1,
                incoming_friend=self.user_1,
                status=StatusApplicationFriends.SUBMITTED
            )

    def test_post_error_send_app_not_exists_user(self):
        response = self.client.post("/user/122/application/", headers={"Authorization": f"Bearer {self.token_1}"})
        self.assertEqual(response.status_code, 404)

    def test_post_success_send_app(self):
        response = self.client.post(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 201)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusEnum.SUCCESS)
        self.assertEqual(response_dict["detail"], "Заявка успешно отправлена")
        self.assertTrue(Friendship.objects.get(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.SUBMITTED
        ))

    def test_post_error_send_app_twice(self):
        self.client.post(f"/user/{self.user_2.id}/application/", headers={"Authorization": f"Bearer {self.token_1}"})
        response = self.client.post(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 400)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusEnum.UNSUCCESS)
        self.assertEqual(response_dict["detail"], "Заявка и так отправлена")
        self.assertTrue(Friendship.objects.get(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.SUBMITTED
        ))

    def test_post_success_accept_app(self):
        self.client.post(f"/user/{self.user_2.id}/application/", headers={"Authorization": f"Bearer {self.token_1}"})
        response = self.client.post(
            f"/user/{self.user_1.id}/application/",
            headers={"Authorization": f"Bearer {self.token_2}"}
        )
        self.assertEqual(response.status_code, 201)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusEnum.SUCCESS)
        self.assertEqual(response_dict["detail"], "Вы теперь друзья")
        self.assertTrue(Friendship.objects.get(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.ACCEPTED
        ))
        self.assertTrue(Friendship.objects.get(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.ACCEPTED
        ))

    def test_post_error_send_app_when_are_friends(self):
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        response = self.client.post(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 400)
        response_dict = response.json()
        self.assertEqual(response_dict["detail"], "Вы и так друзья")

    def test_post_success_try_send_app_when_app_cancelled(self):
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.REJECTED
        ).save()
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.REJECTED
        ).save()
        response = self.client.post(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusEnum.UNSUCCESS)
        self.assertEqual(response_dict["detail"], "Вы не сможете стать друзьями")

    def test_delete_success_cancel_your_application(self):
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.SUBMITTED
        ).save()
        response = self.client.delete(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusEnum.SUCCESS)
        self.assertEqual(response_dict["detail"], "Заявка отменена")
        with self.assertRaises(Friendship.DoesNotExist):
            Friendship.objects.get(
                outgoing_friend=self.user_1,
                incoming_friend=self.user_2,
                status=StatusApplicationFriends.SUBMITTED
            )

    def test_delete_error_application_not_exist(self):
        response = self.client.delete(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 400)
        response_dict = response.json()
        self.assertEqual(response_dict["detail"], "Заявки не существует")

    def test_delete_success_cancel_out_application(self):
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.SUBMITTED
        ).save()
        response = self.client.delete(
            f"/user/{self.user_1.id}/application/",
            headers={"Authorization": f"Bearer {self.token_2}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusEnum.SUCCESS)
        self.assertEqual(response_dict["detail"], "Заявка отклонена. Следующие будут автоматом отклонены")
        self.assertTrue(Friendship.objects.get(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.REJECTED)
        )
        self.assertTrue(Friendship.objects.get(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.REJECTED)
        )

    def test_delete_error_self(self):
        response = self.client.delete(
            f"/user/{self.user_1.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 400)
        response_dict = response.json()
        self.assertEqual(response_dict["detail"], "Вы не можете удалить самого себя!")

    def test_get_error_self(self):
        response = self.client.get(
            f"/user/{self.user_1.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 400)
        response_dict = response.json()
        self.assertEqual(response_dict["detail"], "Не можете выбрать себя")

    def test_get_success_in(self):
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.SUBMITTED
        ).save()
        response = self.client.get(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusApplicationEnum.IN)

    def test_get_success_friend(self):
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.ACCEPTED
        ).save()
        response = self.client.get(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusApplicationEnum.FRI)

    def test_get_success_none(self):
        response = self.client.get(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusApplicationEnum.NONE)

    def test_get_success_out(self):
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.SUBMITTED
        ).save()
        response = self.client.get(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusApplicationEnum.OUT)

    def test_get_success_rej(self):
        Friendship(
            outgoing_friend=self.user_1,
            incoming_friend=self.user_2,
            status=StatusApplicationFriends.REJECTED
        ).save()
        Friendship(
            outgoing_friend=self.user_2,
            incoming_friend=self.user_1,
            status=StatusApplicationFriends.REJECTED
        ).save()
        response = self.client.get(
            f"/user/{self.user_2.id}/application/",
            headers={"Authorization": f"Bearer {self.token_1}"}
        )
        self.assertEqual(response.status_code, 200)
        response_dict = response.json()
        self.assertEqual(response_dict["status"], StatusApplicationEnum.REJ)
