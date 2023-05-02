from http import HTTPStatus
import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import Post, Group, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Kat')
        cls.author2 = User.objects.create_user(username='Kit')
        cls.author3 = User.objects.create_user(username='Kut')
        cls.group = Group.objects.create(
            title='Пробная группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Пробный пост',
            author=cls.author,
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.author2_client = Client()
        self.author2_client.force_login(self.author2)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.author}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/create_post.html',
            reverse('posts:post_create'):
                'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_show_correct_context(self):
        """Шаблон сформирован с ожидаемым количеством объектов
        и правильным контекстом."""
        reverse_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author})
        ]
        for reverse_page in reverse_pages:
            with self.subTest(reverse_page=reverse_page):
                response = self.author_client.get(reverse_page)
                self.assertEqual(len(response.context['page_obj']), 1)
                first_object = response.context['page_obj'][0]
                fields_context = {
                    first_object.text: self.post.text,
                    first_object.author: self.post.author,
                    first_object.group: self.post.group,
                    first_object.created.replace(second=0, microsecond=0):
                        timezone.now().replace(second=0, microsecond=0),
                    first_object.image: self.post.image,
                }
                for field, field_context in fields_context.items():
                    with self.subTest(field=field):
                        self.assertEqual(field, field_context)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.author_client.
                    get(reverse('posts:post_detail',
                                kwargs={'post_id': self.post.pk})))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').
                         created.replace(second=0, microsecond=0),
                         self.post.created.replace(second=0, microsecond=0))
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_create_and_edit_pages_show_correct_context(self):
        """Шаблоны create и edit с правильным контекстом."""
        reverse_pages = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
        ]
        for reverse_page in reverse_pages:
            with self.subTest(reverse_page=reverse_page):
                response = self.author_client.get(reverse_page)
                form_fields = {
                    'text': forms.fields.CharField,
                    'group': forms.fields.ChoiceField,
                }
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = (response.context.
                                      get('form').fields.get(value))
                        self.assertIsInstance(form_field, expected)

    def test_new_post_not_in_other_group(self):
        """Новый пост не попадает в другую группу."""
        group_2 = Group.objects.create(
            title='Пробная группа 2',
            slug='test-slug-2',
            description='Тестовое описание-2',
        )
        Post.objects.create(
            text='Пробный пост-2',
            author=self.author,
            group=group_2,
        )
        response = self.author_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}
        ))
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_index_page_uses_cache(self):
        """Кеширование записей на главной странице."""
        cache.clear()
        text = 'Пост для тестирования кэша'
        post = Post.objects.create(
            text=text,
            author=self.author
        )
        self.author_client.get(reverse('posts:index'))
        post.delete()
        response = self.author_client.get(reverse('posts:index'))
        self.assertTrue(text in response.content.decode())
        cache.clear()
        response = self.author_client.get(reverse('posts:index'))
        self.assertFalse(text in response.content.decode())

    def test_authorized_user_followes_to_other_users(self):
        """Авторизованный пользователь может подписаться на
        других пользователей."""
        self.assertFalse(self.author.follower.filter(author=self.author2))
        self.author_client.get(reverse('posts:profile_follow',
                               kwargs={'username': self.author2.username}))
        self.author_client.get(reverse('posts:profile_follow',
                               kwargs={'username': self.author2.username}))
        self.assertEqual(
            self.author.follower.filter(author=self.author2).count(), 1
        )

    def test_authorized_user_unfollowes_from_other_users(self):
        """Авторизованный пользователь может отписаться от
        других пользователей."""
        Follow.objects.get_or_create(user=self.author, author=self.author2)
        self.assertTrue(self.author.follower.filter(author=self.author2))
        self.author_client.get(reverse('posts:profile_unfollow',
                               kwargs={'username': self.author2.username}))
        self.assertFalse(self.author.follower.filter(author=self.author2))

    def test_new_post_in_follow_page(self):
        """Новая запись появляется в ленте подписанных пользователей."""
        self.author2_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.author3.username})
        )
        response1 = self.author2_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response1.context['page_obj']), 0)
        response2 = self.author_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response2.context['page_obj']), 0)
        Post.objects.create(
            text='Новая запись',
            author=self.author3,
        )
        response3 = self.author2_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response3.context['page_obj']), 1)
        response4 = self.author_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response4.context['page_obj']), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Kat')
        cls.group = Group.objects.create(
            title='Пробная группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        posts = []
        for i in range(13):
            post = Post(text=f'Пробный пост {i+1}',
                        author=self.author,
                        group=self.group,)
            posts.append(post)
        Post.objects.bulk_create(posts)
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.reverse_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author})
        ]

    def test_first_page_ten_posts(self):
        """Количество постов на первой странице"""
        for reverse_page in self.reverse_pages:
            with self.subTest(reverse_page=reverse_page):
                response = self.author_client.get(reverse_page)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_posts(self):
        """Количество постов на второй странице"""
        for reverse_page in self.reverse_pages:
            with self.subTest(reverse_page=reverse_page):
                response = self.author_client.get(reverse_page + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)
