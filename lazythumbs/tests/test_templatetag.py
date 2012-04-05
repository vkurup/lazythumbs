from unittest import TestCase

from django.template import TemplateSyntaxError, VariableDoesNotExist, Variable

from mock import Mock

from lazythumbs.templatetags.lazythumb import LazythumbNode


def node_factory(invocation):
    mt = Mock()
    mt.contents = invocation
    return LazythumbNode(Mock(), mt)


class TemplateTagSyntaxTest(TestCase):
    """ Test the arg validation of the template tag. """
    def test_too_many_args(self):
        mt = Mock()
        mt.contents = "tag url resize '48x48' as as_var extra"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_too_few_args(self):
        mt = Mock()
        mt.contents = "tag url resize"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_invalid_action(self):
        mt = Mock()
        mt.contents = "tag url boom '48' as as_var"
        self.assertRaises(TemplateSyntaxError, LazythumbNode, Mock(), mt)

    def test_url_str(self):
        node = node_factory("tag 'url' resize '30x30' as as_var")
        self.assertEqual(node.thing, 'url')

    def test_url_var(self):
        node = node_factory("tag url resize '30x30' as as_var")
        self.assertEqual(type(node.thing), Variable)
        self.assertEqual(node.thing.var, 'url')

class TemplateTagGeometryCompileTest(TestCase):
    """ test handling of geometry argument for each action """

    def test_resize_invalid_geo_str(self):
        invocation = "tag url resize 'boom' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)
        invocation = "tag url resize '48' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)
        invocation = "tag url resize 'x48' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)
        invocation = "tag url resize '48x50x48' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)
        invocation = "tag url resize '50x48x' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)

    def test_resize_valid_geo_str(self):
        node = node_factory("tag url resize '48x50' as as_var")
        self.assertEqual(node.raw_geometry, '48x50')
        self.assertEqual(node.width, '48')
        self.assertEqual(node.height, '50')

    def test_thumbnail_invalid_geo_str(self):
        invocation = "tag url thumbnail 'boom' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)
        invocation = "tag url thumbnail '48x50' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)
        invocation = "tag url thumbnail '50x' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)
        invocation = "tag url thumbnail 'x50x' as as_var"
        self.assertRaises(TemplateSyntaxError, node_factory, invocation)

    def test_thumbnail_valid_geo_str(self):
        node = node_factory("tag url thumbnail 'x50' as as_var")
        self.assertEqual(node.raw_geometry, 'x50')
        self.assertEqual(node.width, None)
        self.assertEqual(node.height, '50')
        node = node_factory("tag url thumbnail '50' as as_var")
        self.assertEqual(node.raw_geometry, '50')
        self.assertEqual(node.width, '50')
        self.assertEqual(node.height, None)

    def test_geo_var(self):
        node = node_factory("tag url thumbnail geo as as_var")
        self.assertEqual(type(node.raw_geometry), Variable)
        self.assertEqual(node.raw_geometry.var, 'geo')

class TemplateTagRenderTest(TestCase):
    """ test behavior of template tag's output """
    def setUp(self):
        self.context = {}
        mock_cxt = Mock()
        mock_cxt.__getitem__ = lambda _,x: self.context[x]
        mock_cxt.__setitem__ = lambda _,x,y: self.context.__setitem__(x,y)

        self.mock_cxt = mock_cxt

        class PseudoImageFile(object):
            def __init__(self, w, h):
                self.width = w
                self.height = h
                self.name = 'image_path'

        class PseudoPhoto(object):
            def __init__(self, w, h):
                self.photo = PseudoImageFile(w,h)

        self.PseudoImageFile = PseudoImageFile
        self.PseudoPhoto = PseudoPhoto

    def test_valid_basic(self):
        """ ensure sanity in the simplest case """
        node = node_factory("tag 'url' resize '48x50' as img_tag")
        node.render(self.mock_cxt)

        self.assertTrue('img_tag' in self.context)
        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 48)
        self.assertEqual(img_tag['height'], 50)
        print img_tag['src']
        self.assertTrue('url' in img_tag['src'])

    def test_resize_invalid_geo(self):
        """
        for a resize, if the geometry reference by the raw_geometry variable is
        malformed, set width and height to None.
        """
        self.context['url'] = 'i/p'
        node = node_factory("tag 'url' resize geo as img_tag")
        for bad_geo in ['boom', '40', 'x40', '40x', '40x40x', '40x40x40']:
            self.context['geo'] = bad_geo
            node.render(self.mock_cxt)
            img_tag = self.context['img_tag']
            self.assertEqual(img_tag['width'], '')
            self.assertEqual(img_tag['height'], '')

    def test_thumbnail_invalid_geo(self):
        """
        for a thumbnail, if the geometry reference by the raw_geometry variable is
        malformed, set width and height to None.
        """
        node = node_factory("tag 'url' thumbnail geo as img_tag")
        for bad_geo in ['boom', '40x40', '40x40x40', '40x']:
            self.context['geo'] = bad_geo
            node.render(self.mock_cxt)
            img_tag = self.context['img_tag']
            self.assertEqual(img_tag['width'], '')
            self.assertEqual(img_tag['height'], '')

    def test_resize_valid_geo(self):
        """
        for a resize, check that width/height are set appropriately in the as
        variable for a valid geometry Variable.
        """
        self.context['geo'] = '48x50'

        node = node_factory("tag 'url' resize geo as img")
        node.render(self.mock_cxt)

        img = self.context['img']
        self.assertEqual(img['width'], 48)
        self.assertEqual(img['height'], 50)

    def test_thumbnail_and_url_valid_geo(self):
        """
        for a thumbnail, check that width and/or height is set appropriately in
        the as variable for a valid geometry Variable.
        """
        self.context['geo'] = 'x48'
        node = node_factory("tag 'url' thumbnail geo as img")
        node.render(self.mock_cxt)
        self.assertTrue('img' in self.context)
        img = self.context['img']
        self.assertEqual(img['height'], 48)

    def test_invalid_geometry(self):
        """
        if the geometry reference by the raw_geometry variable is
        malformed, set width and height to None.
        """
        self.context['geo'] = 'boom'
        self.context['url'] = 'i/p'
        node = node_factory("tag 'url' resize geo as img_tag")
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['height'], '')
        self.assertEqual(img_tag['width'], '')
        self.assertTrue('url' in img_tag['src'])

        node = node_factory("tag 'url' thumbnail geo as img_tag")
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['height'], '')
        self.assertEqual(img_tag['width'], '')
        self.assertTrue('url' in img_tag['src'])

    def test_valid_single_geo(self):
        """ test geo variable that resolves to a single number """
        node = node_factory("tag 'url' thumbnail geo as img_tag")
        self.context['geo'] = '48'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 48)
        self.assertEqual(img_tag['height'], '')
        self.assertTrue('url' in img_tag['src'])

    def test_valid_double_geo(self):
        """ test geo variable that resolves to a pair of numbers """
        node = node_factory("tag 'url' resize geo as img_tag")
        self.context['geo'] = '48x100'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 48)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('url' in img_tag['src'])

    def test_thing_like_IF_introspection_noop(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an ImageFile like object.
        """
        node = node_factory("tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoImageFile(1000, 500)
        self.context['geo'] = 'boom'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 1000)
        self.assertEqual(img_tag['height'], 500)
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_IF_introspection_no_height(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an ImageFile like object.
        """
        node = node_factory("tag img_file thumbnail geo as img_tag")
        self.context['img_file'] = self.PseudoImageFile(100, 200)
        self.context['geo'] = '50'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 50)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_photo_introspection_noop(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an object that nests an ImageFile-like object
        """
        node = node_factory("tag img_file resize geo as img_tag")
        self.context['img_file'] = self.PseudoPhoto(1000, 500)
        self.context['geo'] = 'boom'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 1000)
        self.assertEqual(img_tag['height'], 500)
        self.assertTrue('image_path' in img_tag['src'])

    def test_thing_like_photo_introspection_no_height(self):
        """
        test behaviour for when url does not resolve to a string but rather
        an object that nests an ImageFile-like object with no height. height
        should be scaled.
        """
        node = node_factory("tag img_file thumbnail geo as img_tag")
        self.context['img_file'] = self.PseudoPhoto(100, 200)
        self.context['geo'] = '50'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 50)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('image_path' in img_tag['src'])

    def test_render_url_var_is_str(self):
        node = node_factory("tag url_var resize '30x100' as img_tag")
        self.context['url_var'] = 'some_url'
        node.render(self.mock_cxt)

        img_tag = self.context['img_tag']
        self.assertEqual(img_tag['width'], 30)
        self.assertEqual(img_tag['height'], 100)
        self.assertTrue('some_url' in img_tag['src'])

    def test_render_no_url(self):
        node = node_factory("tag img_file resize '48x48' as img_tag")
        self.assertRaises(VariableDoesNotExist, node.render, (node, {}))