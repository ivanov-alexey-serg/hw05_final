from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='Kit')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.author = User.objects.create_user(username='Kat')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Пробная группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        cls.post = Post.objects.create(
            text='Пробный пост',
            author=cls.author,
            group=cls.group,
        )

    def test_url_exists_at_desired_location(self):
        """Страницы, доступные любому пользователю."""
        post_id = PostURLTests.post.id
        url_list = [
            '/',
            '/group/test-slug/',
            '/profile/Kit/',
            f'/posts/{post_id}/',
        ]
        for url in url_list:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        """Неизвестная страница."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_url_redirect_anonymous(self):
        """Страницы, недоступные неавторизованному пользователю."""
        post_id = PostURLTests.post.id
        redurect_urls = {
            f'/posts/{post_id}/edit/':
                f'/auth/login/?next=/posts/{post_id}/edit/',
            '/create/':
                '/auth/login/?next=/create/',
        }
        for url, redirect_url in redurect_urls.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, redirect_url)

    def test_url_redirect_authorized(self):
        """Изменение поста недоступно клиенту, который не явлется автором."""
        post_id = PostURLTests.post.id
        response = self.authorized_client.get(f'/posts/{post_id}/edit/')
        self.assertRedirects(response, f'/posts/{post_id}/')

    def test_url_create(self):
        """Страница создания поста, доступная авторизованнному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_post_edit(self):
        """Страница редактирования поста, доступная автору поста."""
        post_id = PostURLTests.post.id
        response = self.author_client.get(f'/posts/{post_id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        post_id = PostURLTests.post.id
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/Kit/': 'posts/profile.html',
            f'/posts/{post_id}/': 'posts/post_detail.html',
            f'/posts/{post_id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.author_client.get(url)
                self.assertTemplateUsed(response, template)
