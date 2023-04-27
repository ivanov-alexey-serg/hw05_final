from django.test import TestCase
from http import HTTPStatus


class ErrorPageTests(TestCase):
    def test_page_404_uses_correct_template(self):
        """Страница 404 использует соответствующий шаблон."""
        response = self.client.get('/example/not/found/page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
