from collections import OrderedDict

from django.core.urlresolvers import NoReverseMatch

from rest_framework import routers, views, response
from rest_framework.reverse import reverse


class HybridRouter(routers.DefaultRouter):
    """
    This hybrid router registers both ViewSets and APIViews and shows them in the api_root_view.
    """
    def __init__(self, *args, **kwargs):
        super(HybridRouter, self).__init__(*args, **kwargs)
        self._api_view_urls = {}

    def add_api_view(self, name, url):
        self._api_view_urls[name] = url

    def remove_api_view(self, name):
        del self._api_view_urls[name]

    @property
    def api_view_urls(self):
        ret = {}
        ret.update(self._api_view_urls)
        return ret

    def get_urls(self):
        urls = super(HybridRouter, self).get_urls()
        for api_view_key in self._api_view_urls.keys():
            urls.append(self._api_view_urls[api_view_key])
        return urls

    def get_api_root_view(self):
        # callgraph:
        # HybridRouter.get_urls
        # DefaultRouter.get_urls
        # HybridRouter.get_api_root_view

        # Copy the following block from Default Router
        api_root_dict = {}
        list_name = self.routes[0].name
        for prefix, viewset, basename in self.registry:
            api_root_dict[prefix] = list_name.format(basename=basename)

        # In addition to that:
        api_view_urls = self._api_view_urls

        class APIRoot(views.APIView):
            _ignore_model_permissions = True

            def get(self, request, *args, **kwargs):
                ret = OrderedDict()
                namespace = request.resolver_match.namespace
                for key, url_name in api_root_dict.items():
                    if namespace:
                        url_name = namespace + ':' + url_name
                    try:
                        ret[key] = reverse(
                            url_name,
                            args=args,
                            kwargs=kwargs,
                            request=request,
                            format=kwargs.get('format', None)
                        )
                    except NoReverseMatch:
                        # Don't bail out if eg. no list routes exist, only detail routes.
                        continue

                # In addition to what had been added, now add the APIView urls
                for api_view_key in api_view_urls.keys():
                    # originally was: reverse(api_view_urls[api_view_key].name, request=request, format=format)
                    namespace = request.resolver_match.namespace
                    if namespace:
                        url_name = namespace + ":" + api_view_key
                    try:
                        ret[api_view_key] = reverse(
                            url_name,
                            args=args,
                            kwargs=kwargs,
                            request=request,
                            format=kwargs.get('format', None)
                        )
                    except NoReverseMatch:
                        continue

                return response.Response(ret)

        return APIRoot.as_view()
