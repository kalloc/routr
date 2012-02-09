"""

    routr.tests -- test suite
    =========================

"""

from unittest import TestCase
from webob import Request, exc

from routr.schema import QueryParams, String, Int, Optional
from routr import Route, Endpoint, RootEndpoint, RouteGroup
from routr import route, ViewRef, RouteConfigurationError
from routr import POST, GET
from routr.exc import (
    NoURLPatternMatched, RouteGuarded, MethodNotAllowed, RouteReversalError)

__all__ = ()

class TestRouting(TestCase):

    def assertNoMatch(self, r, url):
        if isinstance(url, Request):
            self.assertRaises(NoURLPatternMatched, r, url)
        else:
            self.assertRaises(NoURLPatternMatched, r, Request.blank(url))

class TestRootEnpoint(TestRouting):

    def test_reverse(self):
        r = route("view", name="news")
        self.assertEqual(r.reverse("news"), "/")
        self.assertRaises(RouteReversalError, r.reverse, "news2")

    def test_match(self):
        def view():
            return "hello"
        r = route(view)
        req = Request.blank("/")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "hello")

    def test_no_match(self):
        def view():
            return "hello"
        r = route(view)
        req = Request.blank("/news")
        self.assertRaises(NoURLPatternMatched, r, req)

class TestEndpoint(TestRouting):

    def test_reverse(self):
        r = route("news", "view", name="news")
        self.assertEqual(r.reverse("news"), "/news")
        self.assertRaises(RouteReversalError, r.reverse, "news2")

        r = route("news/{int}/", "view", name="news")
        self.assertEqual(r.reverse("news", 42), "/news/42/")
        self.assertRaises(RouteReversalError, r.reverse, "news2")

    def test_match(self):
        def view():
            return "hello"
        r = route("news", view)
        req = Request.blank("/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "hello")

    def test_no_match(self):
        self.assertNoMatch(
            route("news", "view"),
            "/new")
        self.assertNoMatch(
            route("news", "view"),
            "/newsweek")

    def test_method(self):
        def view():
            return "hello"
        r = route(POST, "news", view)

        req = Request.blank("/news", {"REQUEST_METHOD": "POST"})
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "hello")

        self.assertRaises(
            MethodNotAllowed,
            r, Request.blank("/news", {"REQUEST_METHOD": "DELETE"}))

    def test_param_pattern_int(self):
        def view(id):
            return id
        r = route("/news/{int}/", view)
        req = Request.blank("/news/42/")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), 42)

        self.assertNoMatch(r, Request.blank("/news/"))
        self.assertNoMatch(r, Request.blank("/news/a/"))
        self.assertNoMatch(r, Request.blank("/news//"))
        self.assertNoMatch(r, Request.blank("/news/122"))

        def view(a, b, c):
            return a, b, c

        r = route("/news/{int}/{int}/{int}/", view)
        req = Request.blank("/news/42/41/40/")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), (42, 41, 40))

    def test_param_pattern_string(self):
        def view(id):
            return id

        r = route("/news/{string}/", view)

        req = Request.blank("/news/42/")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "42")

        req = Request.blank("/news/abcdef-12/")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "abcdef-12")

    def test_param_pattern_path(self):
        def view(id):
            return id

        r = route("/news/{path}", view)

        req = Request.blank("/news/42/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "42/news")

        r = route("/news/{path}/comments", view)

        req = Request.blank("/news/42/news/comments")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "42/news")

    def test_param_guard(self):
        def view(id, q=None, page=1):
            return id, q, page
        r = route(
            "/news/{int}/", view,
            [QueryParams(q=Optional(String), page=Optional(Int))])

        req = Request.blank("/news/42/")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), (42, None, 1))

        req = Request.blank("/news/42/?q=search")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), (42, "search", 1))

        req = Request.blank("/news/42/?q=search&page=100")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), (42, "search", 100))

        self.assertRaises(
            exc.HTTPBadRequest,
            r, Request.blank("/news/42/?q=search&page=aa"))

class TestRouteGroup(TestRouting):

    def test_reverse(self):
        r = route("api",
            route("news", "news", name="news"),
            route("comments", "comments", name="comments"))
        self.assertEqual(r.reverse("news"), "/api/news")
        self.assertEqual(r.reverse("comments"), "/api/comments")
        self.assertRaises(RouteReversalError, r.reverse, "a")

        r = route("api",
            route("news/{str}/", "news", name="news"),
            route("comments", "comments", name="comments"))
        self.assertEqual(r.reverse("news", "hello"), "/api/news/hello/")

        r = route("api",
            route(GET, "news", name="get-news"),
            route(POST, "news", name="create-news"))
        self.assertEqual(r.reverse("get-news"), "/api")
        self.assertEqual(r.reverse("create-news"), "/api")

    def test_reverse_empty_prefix(self):
        r = route(
            route("news", name="news"))
        self.assertEqual(r.reverse("news"), "/")

    def test_simple(self):
        def news():
            return "news"
        def comments():
            return "comments"

        r = route(
            route("news", news),
            route("comments", comments))

        req = Request.blank("/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "news")

        req = Request.blank("/comments")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "comments")

        self.assertNoMatch(r, "/newsweeek")
        self.assertNoMatch(r, "/ne")

    def test_complex_match(self):
        def news():
            return "news"
        def comments():
            return "comments"
        def api_news():
            return "api_news"
        def api_comments():
            return "api_comments"

        r = route(
            route("api",
                route("news", api_news),
                route("comments", api_comments)),
            route("news", news),
            route("comments", comments))

        req = Request.blank("/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "news")

        req = Request.blank("/comments")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "comments")

        req = Request.blank("/api/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "api_news")

        req = Request.blank("/api/comments")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "api_comments")

    def test_by_method(self):
        r = route("api",
            route(GET, "news_get"),
            route(POST, "news_post"))

        req = Request.blank("/api", {"REQUEST_METHOD": "POST"})
        (args, kwargs), view = r(req)
        self.assertEqual(view, "news_post")

        req = Request.blank("/api")
        (args, kwargs), view = r(req)
        self.assertEqual(view, "news_get")

    def test_method_inner(self):
        def news():
            return "news"
        def comments_get():
            return "comments_get"
        def comments_post():
            return "comments_post"

        r = route(
            route("news", news),
            route(GET, "comments", comments_get),
            route(POST, "comments", comments_post))

        req = Request.blank("/news", {"REQUEST_METHOD": "GET"})
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "news")

        req = Request.blank("/news", {"REQUEST_METHOD": "POST"})
        self.assertRaises(
            RouteGuarded,
            r, req)

        req = Request.blank("/comments", {"REQUEST_METHOD": "POST"})
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "comments_post")

        req = Request.blank("/comments", {"REQUEST_METHOD": "DELETE"})
        self.assertRaises(
            RouteGuarded,
            r, req)

        self.assertNoMatch(r, "/newsweeek")
        self.assertNoMatch(r, "/ne")

    def test_guards(self):
        pass

class TestRouteDirective(TestCase):

    def test_root_endpoint(self):
        r = route("myapp.myview")
        self.assertEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, RootEndpoint)
        self.assertEqual(r.view, "myapp.myview")

    def test_root_endpoint_func(self):
        def view():
            pass
        r = route(view)
        self.assertEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, RootEndpoint)
        self.assertEqual(r.view, view)

    def test_root_endpoint_guards(self):
        r = route("myapp.myview", ["guard"])
        self.assertEqual(r.prefix, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.view, "myapp.myview")

    def test_endpoint(self):
        r = route("news", "myapp.myview")
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.view, "myapp.myview")

    def test_endpoint_func(self):
        def view():
            pass
        r = route("news", view)
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.view, view)

    def test_endpoint_guards(self):
        r = route("news", "myapp.myview", ["guard"])
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.view, "myapp.myview")

    def test_route_list_no_prefix(self):
        r = route(
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"))
        self.assertEqual(r.guards, [])
        self.assertEqual(r.prefix, None)
        self.assertIsInstance(r, RouteGroup)

    def test_route_list_no_prefix_guards(self):
        r = route(
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"),
            ["guard"])
        self.assertEqual(r.guards, ["guard"])
        self.assertEqual(r.prefix, None)
        self.assertIsInstance(r, RouteGroup)

    def test_route_list(self):
        r = route("api",
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"))
        self.assertEqual(r.guards, [])
        self.assertNotEqual(r.prefix, None)
        self.assertIsInstance(r, RouteGroup)

    def test_route_list_guards(self):
        r = route("api",
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"),
            ["guard"])
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, RouteGroup)

    def test_invalid_routes(self):
        self.assertRaises(RouteConfigurationError, route)
