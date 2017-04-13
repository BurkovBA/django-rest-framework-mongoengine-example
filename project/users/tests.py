from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from rest_framework.reverse import reverse

from models import *


def create_superuser():
    """
    Creates and retuns a superuser - instance of settings.MONGOENGINE_USER_DOCUMENT
    """
    new_admin = User(
        id=1,
        username="admin@example.com",
        email="admin@example.com",
        name="admin",
        is_active=True,
        is_staff=True
    )
    new_admin.set_password('foobar')
    new_admin.save()
    return new_admin


def create_user():
    """
    Creates and returns a regular user - object of settings.MONGOENGINE_USER_DOCUMENT
    """
    new_user = User(
        id=10,
        username="user@example.com",
        email="user@example.com",
        name="user",
        is_active=True,
        is_staff=False
    )
    new_user.set_password('foobar')
    new_user.save()
    return new_user


class ObtainAuthTokenTestCase(APITestCase):
    def setUp(self):
        self.new_user = create_user()
        self.url = reverse("api:auth")

    def doCleanups(self):
        User.drop_collection()

    def test_post_correct_credentials(self):
        c = APIClient()

        response = c.post(self.url, {"username": "user@example.com", "password": "foobar"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, '{"token":"2c7e9e9465e917dcd34e620193ed2a7447140e5b"}')

    def test_post_incorrect_credentials(self):
        c = APIClient()

        response = c.post(self.url, {"username": "user@example.com", "password": ""})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
