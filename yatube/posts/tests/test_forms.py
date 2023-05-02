import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Post, Group, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Mul')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост 1',
            author=cls.author,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.non_authorized_client = Client()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        data = {
            'text': 'Тестовый пост 2',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=data['text'],
                image='posts/' + data['image'].name,
                group=data['group'],
                author=self.author,
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма изменяет ожидаемую запись в Post."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small1.gif',
            content=small_gif,
            content_type='image/gif'
        )
        data = {
            'text': 'Тестовый пост 1 изменён',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(
            Post.objects.get(pk=self.post.pk).text, data['text']
        )

    def test_non_authorized_client_cannot_create_post(self):
        """Неавторизованный пользователь не может опубликовать пост"""
        posts_count = Post.objects.count()
        response = self.non_authorized_client.post(
            reverse('posts:post_create'),
            data={'text': 'Тестовый пост 3'},
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse('posts:post_create'),
        )
        self.assertEqual(Post.objects.count(), posts_count)

    def test_non_authorized_client_cannot_create_comment(self):
        """Неавторизованный пользователь не может оставить комментарий"""
        comment_count = Comment.objects.count()
        response = self.non_authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data={'text': 'Тестовый комментарий'},
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('users:login')
            + '?next='
            + reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
        )
        self.assertEqual(Comment.objects.count(), comment_count)

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        comments_count = Comment.objects.count()
        data = {'text': 'Тестовый комментарий'}
        response = self.author_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=data['text'],
                post=self.post,
                author=self.author,
            ).exists()
        )
