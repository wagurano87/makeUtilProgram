import unittest
from unittest.mock import Mock

from webscrap import AccessRequired, check_access, is_naver_premium


class AccessChecks(unittest.TestCase):
    def page(self, text="Full article", url="https://example.com/article", password=False):
        page = Mock(url=url)
        page.locator.return_value.count.return_value = int(password)
        page.locator.return_value.inner_text.return_value = text
        return page

    def test_article_is_not_rejected_for_missing_cookie_names(self):
        context = Mock()
        context.cookies.return_value = []
        check_access(self.page(), context, "https://contents.premium.naver.com/article")
        context.cookies.assert_not_called()

    def test_logged_in_but_paywalled_is_blocked(self):
        context = Mock()
        context.cookies.return_value = [{"name": "NID_AUT"}, {"name": "NID_SES"}]
        with self.assertRaises(AccessRequired):
            check_access(self.page("구독하고 전체 콘텐츠 보기"), context,
                         "https://contents.premium.naver.com/article")

    def test_login_redirect_is_blocked(self):
        with self.assertRaises(AccessRequired):
            check_access(self.page(url="https://nid.naver.com/nidlogin.login"), Mock(),
                         "https://example.com/article")

    def test_password_form_is_blocked(self):
        with self.assertRaises(AccessRequired):
            check_access(self.page(password=True), Mock(), "https://example.com/article")

    def test_ordinary_login_link_does_not_block_article(self):
        check_access(self.page("로그인 | Full article"), Mock(), "https://example.com/article")

    def test_naver_host_match_is_exact(self):
        self.assertFalse(is_naver_premium("https://contents.premium.naver.com.example.org"))


if __name__ == "__main__":
    unittest.main()
