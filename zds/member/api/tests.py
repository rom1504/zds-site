# coding: utf-8

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from oauth2_provider.models import Application, AccessToken
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.test import APIClient

from zds.member.factories import ProfileFactory, StaffProfileFactory
from zds.member.models import TokenRegister


overrided_drf = settings.REST_FRAMEWORK
overrided_drf['MAX_PAGINATE_BY'] = 20


@override_settings(REST_FRAMEWORK=overrided_drf)
class MemberListAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_of_users_empty(self):
        """
        Gets empty list of users in the database.
        """
        response = self.client.get(reverse('api-member-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)
        self.assertEqual(response.data.get('results'), [])
        self.assertIsNone(response.data.get('next'))
        self.assertIsNone(response.data.get('previous'))

    def test_list_of_users(self):
        """
        Gets list of users not empty in the database.
        """
        self.create_multiple_users()

        response = self.client.get(reverse('api-member-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), settings.REST_FRAMEWORK['PAGINATE_BY'])
        self.assertEqual(len(response.data.get('results')), settings.REST_FRAMEWORK['PAGINATE_BY'])
        self.assertIsNone(response.data.get('next'))
        self.assertIsNone(response.data.get('previous'))

    def test_list_of_users_with_several_pages(self):
        """
        Gets list of users with several pages in the database.
        """
        self.create_multiple_users(settings.REST_FRAMEWORK['PAGINATE_BY'] + 1)

        response = self.client.get(reverse('api-member-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), settings.REST_FRAMEWORK['PAGINATE_BY'] + 1)
        self.assertIsNotNone(response.data.get('next'))
        self.assertIsNone(response.data.get('previous'))

    def test_list_of_users_for_a_page_given(self):
        """
        Gets list of users with several pages and gets a page different that the first one.
        """
        self.create_multiple_users(settings.REST_FRAMEWORK['PAGINATE_BY'] + 1)

        response = self.client.get(reverse('api-member-list') + '?page=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 11)
        self.assertEqual(len(response.data.get('results')), 1)
        self.assertIsNone(response.data.get('next'))
        self.assertIsNotNone(response.data.get('previous'))

    def test_list_of_users_for_a_wrong_page_given(self):
        """
        Gets an error when the user asks a wrong page.
        """
        response = self.client.get(reverse('api-member-list') + '?page=2')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_of_users_with_a_custom_page_size(self):
        """
        Gets list of users with a custom page size. DRF allows to specify a custom
        size for the pagination.
        """
        self.create_multiple_users(settings.REST_FRAMEWORK['PAGINATE_BY'] * 2)

        page_size = 'page_size'
        response = self.client.get(reverse('api-member-list') + '?{}=20'.format(page_size))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 20)
        self.assertEqual(len(response.data.get('results')), 20)
        self.assertIsNone(response.data.get('next'))
        self.assertIsNone(response.data.get('previous'))
        self.assertEqual(settings.REST_FRAMEWORK['PAGINATE_BY_PARAM'], page_size)

    def test_list_of_users_with_a_wrong_custom_page_size(self):
        """
        Gets list of users with a custom page size but not good according to the
        value in settings.
        """
        page_size_value = settings.REST_FRAMEWORK['MAX_PAGINATE_BY'] + 1
        self.create_multiple_users(page_size_value)

        response = self.client.get(reverse('api-member-list') + '?page_size={}'.format(page_size_value))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), page_size_value)
        self.assertIsNotNone(response.data.get('next'))
        self.assertIsNone(response.data.get('previous'))
        self.assertEqual(settings.REST_FRAMEWORK['MAX_PAGINATE_BY'], len(response.data.get('results')))

    def test_search_in_list_of_users(self):
        """
        Gets list of users corresponding to the value given by the search parameter.
        """
        self.create_multiple_users()
        StaffProfileFactory()

        response = self.client.get(reverse('api-member-list') + '?search=firmstaff')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('count') > 0)

    def test_search_without_results_in_list_of_users(self):
        """
        Gets a list empty when there are users but which doesn't match with the search
        parameter value.
        """
        self.create_multiple_users()

        response = self.client.get(reverse('api-member-list') + '?search=zozor')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 0)
        self.assertIsNone(response.data.get('next'))
        self.assertIsNone(response.data.get('previous'))

    def test_register_new_user(self):
        """
        Registers a new user in the database.
        """
        data = {
            'username': 'Clem',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('username'), data.get('username'))
        self.assertEqual(response.data.get('email'), data.get('email'))
        self.assertNotEqual(response.data.get('password'), data.get('password'))

    def test_register_two_same_users(self):
        """
        Tries to register a user two times.
        """
        data = {
            'username': 'Clem',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('username'))
        self.assertIsNotNone(response.data.get('email'))

    def test_register_new_user_without_username(self):
        """
        Tries to register a new user in the database without an username.
        """
        data = {
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('username'))

    def test_register_new_user_with_username_empty(self):
        """
        Tries to register a new user in the database with an username empty.
        """
        data = {
            'username': '',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('username'))

    def test_register_new_user_with_comma_in_username(self):
        """
        Tries to register a new user in the database with comma in username.
        """
        data = {
            'username': 'Cle,m',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('username'))

    def test_register_new_user_with_username_start_and_end_with_space(self):
        """
        Tries to register a new user in the database with space at the start
        and end of the username.
        """
        data = {
            'username': ' Clem ',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('username'))

    def test_register_new_user_without_email(self):
        """
        Tries to register a new user in the database without an email.
        """
        data = {
            'username': 'Clem',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('email'))

    def test_register_new_user_with_forbidden_email(self):
        """
        Gets an error when the user tries to register a new user with a forbidden email.
        """
        data = {
            'username': 'Clem',
            'email': 'clem@yopmail.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('email'))

    def test_register_new_user_without_password(self):
        """
        Tries to register a new user in the database without a password.
        """
        data = {
            'username': 'Clem',
            'email': 'clem@zestedesavoir.com'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNotNone(response.data.get('password'))

    def test_register_new_user_is_inactive(self):
        """
        Registers a new user and checks that the user is inactive in the database.
        """
        data = {
            'username': 'Clem',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username=response.data.get('username'))
        self.assertFalse(user.is_active)

    def test_register_new_user_send_an_email_to_confirm_registration(self):
        """
        Registers a new user send an email in the inbox of the target user to confirm
        his registration.
        """
        data = {
            'username': 'Clem',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEquals(len(mail.outbox), 1)

    def test_register_new_user_create_a_token(self):
        """
        Registers a new user create a token used to confirm the registration of the
        future user.
        """
        data = {
            'username': 'Clem',
            'email': 'clem@zestedesavoir.com',
            'password': 'azerty'
        }
        response = self.client.post(reverse('api-member-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username=response.data.get('username'))
        token = TokenRegister.objects.get(user=user)
        self.assertIsNotNone(token)

    def test_member_list_url_with_put_method(self):
        """
        Gets an error when the user try to make a request with a method not allowed.
        """
        response = self.client.put(reverse('api-member-list'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_member_list_url_with_delete_method(self):
        """
        Gets an error when the user try to make a request with a method not allowed.
        """
        response = self.client.delete(reverse('api-member-list'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def create_multiple_users(self, number_of_users=settings.REST_FRAMEWORK['PAGINATE_BY']):
        for user in xrange(0, number_of_users):
            ProfileFactory()


class MemberDetailAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.profile = ProfileFactory()

        clientOAuth2 = create_oauth2_client(self.profile.user)
        self.clientAuthenticated = APIClient()
        authenticate_client(self.clientAuthenticated, clientOAuth2, self.profile.user.username, 'hostel77')

    def test_detail_of_a_member(self):
        """
        Gets all information about a user.
        """
        response = self.client.get(reverse('api-member-detail', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.profile.pk, response.data.get('pk'))
        self.assertEqual(self.profile.user.username, response.data.get('username'))
        self.assertEqual(self.profile.user.is_active, response.data.get('is_active'))
        self.assertEqual(self.profile.site, response.data.get('site'))
        self.assertEqual(self.profile.avatar_url, response.data.get('avatar_url'))
        self.assertEqual(self.profile.biography, response.data.get('biography'))
        self.assertEqual(self.profile.sign, response.data.get('sign'))
        self.assertEqual(self.profile.email_for_answer, response.data.get('email_for_answer'))
        self.assertIsNotNone(response.data.get('date_joined'))
        self.assertFalse(response.data.get('show_email'))
        self.assertIsNone(response.data.get('email'))

    def test_detail_of_a_member_who_accepts_to_show_his_email(self):
        """
        Gets all information about a user but not his email because the request isn't authenticated.
        """
        self.profile.show_email = True
        self.profile.save()

        response = self.client.get(reverse('api-member-detail', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data.get('email'))

    def test_detail_of_a_member_who_accepts_to_show_his_email_with_authenticated_request(self):
        """
        Gets all information about a user and his email.
        """
        self.profile.show_email = True
        self.profile.save()

        response = self.clientAuthenticated.get(reverse('api-member-detail', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('show_email'))
        self.assertEqual(self.profile.user.email, response.data.get('email'))

    def test_detail_of_a_member_not_present(self):
        """
        Gets an error when the user isn't present in the database.
        """
        response = self.client.get(reverse('api-member-detail', args=[42]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_member_details_without_any_change(self):
        """
        Updates a member but without any changes.
        """
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.profile.pk, response.data.get('pk'))
        self.assertEqual(self.profile.user.username, response.data.get('username'))
        self.assertEqual(self.profile.site, response.data.get('site'))
        self.assertEqual(self.profile.avatar_url, response.data.get('avatar_url'))
        self.assertEqual(self.profile.biography, response.data.get('biography'))
        self.assertEqual(self.profile.sign, response.data.get('sign'))
        self.assertEqual(self.profile.email_for_answer, response.data.get('email_for_answer'))
        self.assertFalse(response.data.get('show_email'))
        self.assertEqual(self.profile.user.email, response.data.get('email'))

    def test_update_member_details_not_exist(self):
        """
        Tries to update a member who doesn't exist in the database.
        """
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[42]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_member_details_with_a_problem_in_authentication(self):
        """
        Tries to update a member with a authentication not valid.
        """
        response = self.client.put(reverse('api-member-detail', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_member_details_without_permissions(self):
        """
        Tries to update information about a member when the user isn't the target user.
        """
        another = ProfileFactory()
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[another.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_member_details_username(self):
        """
        Updates username of a member given.
        """
        data = {
            'username': 'Clem'
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), data.get('username'))

    def test_update_member_details_email(self):
        """
        Updates email of a member given.
        """
        data = {
            'email': 'clem@zestedesavoir.com'
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('email'), data.get('email'))

    def test_update_member_details_with_email_malformed(self):
        """
        Gets an error when the user try to update a member given with an email malformed.
        """
        data = {
            'email': 'wrong email'
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_member_details_site(self):
        """
        Updates site of a member given.
        """
        data = {
            'site': 'www.zestedesavoir.com'
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('site'), data.get('site'))

    def test_update_member_details_avatar(self):
        """
        Updates url of the member's avatar given.
        """
        data = {
            'avatar_url': 'www.zestedesavoir.com'
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('avatar_url'), data.get('avatar_url'))

    def test_update_member_details_biography(self):
        """
        Updates biography of a member given.
        """
        data = {
            'biography': 'It is my awesome biography.'
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('biography'), data.get('biography'))

    def test_update_member_details_sign(self):
        """
        Updates sign of a member given.
        """
        data = {
            'sign': 'It is my awesome sign.'
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('sign'), data.get('sign'))

    def test_update_member_details_show_email(self):
        """
        Updates show email of a member given.
        """
        data = {
            'show_email': True
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('show_email'), data.get('show_email'))

    def test_update_member_details_show_sign(self):
        """
        Updates show sign of a member given.
        """
        data = {
            'show_sign': True
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('show_sign'), data.get('show_sign'))

    def test_update_member_details_hover_or_click(self):
        """
        Updates hover or click of a member given.
        """
        data = {
            'hover_or_click': True
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('hover_or_click'), data.get('hover_or_click'))

    def test_update_member_details_email_for_answer(self):
        """
        Updates email for answer of a member given.
        """
        data = {
            'email_for_answer': True
        }
        response = self.clientAuthenticated.put(reverse('api-member-detail', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('email_for_answer'), data.get('email_for_answer'))

    def test_member_detail_url_with_post_method(self):
        """
        Gets an error when the user try to make a request with a method not allowed.
        """
        response = self.client.post(reverse('api-member-detail', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_member_detail_url_with_delete_method(self):
        """
        Gets an error when the user try to make a request with a method not allowed.
        """
        response = self.client.delete(reverse('api-member-detail', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class MemberDetailReadingOnlyAPITest(APITestCase):
    def setUp(self):
        self.mas = ProfileFactory()
        settings.ZDS_APP['member']['bot_account'] = self.mas.user.username

        self.profile = ProfileFactory()
        self.staff = StaffProfileFactory()
        clientOAuth2 = create_oauth2_client(self.staff.user)
        self.clientAuthenticated = APIClient()
        authenticate_client(self.clientAuthenticated, clientOAuth2, self.staff.user.username, 'hostel77')

    def test_apply_read_only_at_a_member(self):
        """
        Applies a read only sanction at a member given by a staff user.
        """
        response = self.clientAuthenticated.post(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertFalse(response.data.get('can_write'))

    def test_apply_temporary_read_only_at_a_member(self):
        """
        Applies a temporary read only sanction at a member given by a staff user.
        """
        data = {
            'ls-jrs': 1
        }
        response = self.clientAuthenticated.post(reverse('api-member-read-only', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertFalse(response.data.get('can_write'))
        self.assertIsNotNone(response.data.get('end_ban_write'))

    def test_apply_read_only_at_a_member_with_justification(self):
        """
        Applies a read only sanction at a member given by a staff user with a justification.
        """
        data = {
            'ls-text': 'You are a bad boy!'
        }
        response = self.clientAuthenticated.post(reverse('api-member-read-only', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertFalse(response.data.get('can_write'))

    def test_apply_read_only_at_a_member_not_exist(self):
        """
        Applies a read only sanction at a member given but not present in the database.
        """
        response = self.clientAuthenticated.post(reverse('api-member-read-only', args=[42]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_apply_read_only_at_a_member_with_unauthenticated_client(self):
        """
        Tries to apply a read only sanction at a member with a user isn't authenticated.
        """
        client = APIClient()
        response = client.post(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_apply_read_only_at_a_member_without_permissions(self):
        """
        Tries to apply a read only sanction at a member with a user isn't authenticated.
        """
        clientOAuth2 = create_oauth2_client(self.profile.user)
        clientAuthenticated = APIClient()
        authenticate_client(clientAuthenticated, clientOAuth2, self.profile.user.username, 'hostel77')

        response = clientAuthenticated.post(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_read_only_at_a_member(self):
        """
        Removes a read only sanction at a member given by a staff user.
        """
        response = self.clientAuthenticated.post(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.clientAuthenticated.delete(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertTrue(response.data.get('can_write'))

    def test_remove_temporary_read_only_at_a_member(self):
        """
        Removes a temporary read only sanction at a member given by a staff user.
        """
        data = {
            'ls-jrs': 1
        }
        response = self.clientAuthenticated.post(reverse('api-member-read-only', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.clientAuthenticated.delete(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertTrue(response.data.get('can_write'))
        self.assertIsNone(response.data.get('end_ban_write'))

    def test_remove_read_only_at_a_member_with_justification(self):
        """
        Removes a read only sanction at a member given by a staff user with a justification.
        """
        data = {
            'ls-text': 'You are a bad boy!'
        }
        response = self.clientAuthenticated.post(reverse('api-member-read-only', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.clientAuthenticated.delete(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertTrue(response.data.get('can_write'))

    def test_remove_read_only_at_a_member_not_exist(self):
        """
        Removes a read only sanction at a member given but not present in the database.
        """
        response = self.clientAuthenticated.delete(reverse('api-member-read-only', args=[42]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_read_only_at_a_member_with_unauthenticated_client(self):
        """
        Tries to remove a read only sanction at a member with a user isn't authenticated.
        """
        client = APIClient()
        response = client.delete(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_remove_read_only_at_a_member_without_permissions(self):
        """
        Tries to remove a read only sanction at a member with a user isn't authenticated.
        """
        clientOAuth2 = create_oauth2_client(self.profile.user)
        clientAuthenticated = APIClient()
        authenticate_client(clientAuthenticated, clientOAuth2, self.profile.user.username, 'hostel77')

        response = clientAuthenticated.delete(reverse('api-member-read-only', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MemberDetailBanAPITest(APITestCase):
    def setUp(self):
        self.mas = ProfileFactory()
        settings.ZDS_APP['member']['bot_account'] = self.mas.user.username

        self.profile = ProfileFactory()
        self.staff = StaffProfileFactory()
        clientOAuth2 = create_oauth2_client(self.staff.user)
        self.clientAuthenticated = APIClient()
        authenticate_client(self.clientAuthenticated, clientOAuth2, self.staff.user.username, 'hostel77')

    def test_apply_ban_at_a_member(self):
        """
        Applies a ban sanction at a member given by a staff user.
        """
        response = self.clientAuthenticated.post(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertFalse(response.data.get('can_read'))

    def test_apply_temporary_ban_at_a_member(self):
        """
        Applies a temporary ban sanction at a member given by a staff user.
        """
        data = {
            'ban-jrs': 1
        }
        response = self.clientAuthenticated.post(reverse('api-member-ban', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertFalse(response.data.get('can_read'))
        self.assertIsNotNone(response.data.get('end_ban_read'))

    def test_apply_ban_at_a_member_with_justification(self):
        """
        Applies a ban sanction at a member given by a staff user with a justification.
        """
        data = {
            'ban-text': 'You are a bad boy!'
        }
        response = self.clientAuthenticated.post(reverse('api-member-ban', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertFalse(response.data.get('can_read'))

    def test_apply_ban_at_a_member_not_exist(self):
        """
        Applies a ban sanction at a member given but not present in the database.
        """
        response = self.clientAuthenticated.post(reverse('api-member-ban', args=[42]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_apply_ban_at_a_member_with_unauthenticated_client(self):
        """
        Tries to apply a ban sanction at a member with a user isn't authenticated.
        """
        client = APIClient()
        response = client.post(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_apply_ban_at_a_member_without_permissions(self):
        """
        Tries to apply a ban sanction at a member with a user isn't authenticated.
        """
        clientOAuth2 = create_oauth2_client(self.profile.user)
        clientAuthenticated = APIClient()
        authenticate_client(clientAuthenticated, clientOAuth2, self.profile.user.username, 'hostel77')

        response = clientAuthenticated.post(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_ban_at_a_member(self):
        """
        Removes a ban sanction at a member given by a staff user.
        """
        response = self.clientAuthenticated.post(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.clientAuthenticated.delete(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertTrue(response.data.get('can_read'))

    def test_remove_temporary_ban_at_a_member(self):
        """
        Removes a temporary ban sanction at a member given by a staff user.
        """
        data = {
            'ban-jrs': 1
        }
        response = self.clientAuthenticated.post(reverse('api-member-ban', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.clientAuthenticated.delete(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertTrue(response.data.get('can_read'))
        self.assertIsNone(response.data.get('end_ban_read'))

    def test_remove_ban_at_a_member_with_justification(self):
        """
        Removes a ban sanction at a member given by a staff user with a justification.
        """
        data = {
            'ban-text': 'You are a bad boy!'
        }
        response = self.clientAuthenticated.post(reverse('api-member-ban', args=[self.profile.pk]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.clientAuthenticated.delete(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('username'), self.profile.user.username)
        self.assertEqual(response.data.get('email'), self.profile.user.email)
        self.assertTrue(response.data.get('can_read'))

    def test_remove_ban_at_a_member_not_exist(self):
        """
        Removes a ban sanction at a member given but not present in the database.
        """
        response = self.clientAuthenticated.delete(reverse('api-member-ban', args=[42]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_ban_at_a_member_with_unauthenticated_client(self):
        """
        Tries to remove a ban sanction at a member with a user isn't authenticated.
        """
        client = APIClient()
        response = client.delete(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_remove_ban_at_a_member_without_permissions(self):
        """
        Tries to remove a ban sanction at a member with a user isn't authenticated.
        """
        clientOAuth2 = create_oauth2_client(self.profile.user)
        clientAuthenticated = APIClient()
        authenticate_client(clientAuthenticated, clientOAuth2, self.profile.user.username, 'hostel77')

        response = clientAuthenticated.delete(reverse('api-member-ban', args=[self.profile.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


def create_oauth2_client(user):
    client = Application.objects.create(user=user,
                                        client_type=Application.CLIENT_CONFIDENTIAL,
                                        authorization_grant_type=Application.GRANT_PASSWORD)
    client.save()
    return client


def authenticate_client(client, clientAuth, username, password):
    client.post('/oauth2/token/', {
        'client_id': clientAuth.client_id,
        'client_secret': clientAuth.client_secret,
        'username': username,
        'password': password,
        'grant_type': 'password'
    })
    access_token = AccessToken.objects.get(user__username=username)
    client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))