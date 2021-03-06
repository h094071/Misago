from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.translation import gettext as _

from rest_framework import viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from misago.acl import add_acl
from misago.categories.models import THREADS_ROOT_NAME, Category
from misago.categories.permissions import allow_browse_category, allow_see_category
from misago.core.shortcuts import get_int_or_404, get_object_or_404
from misago.readtracker.categoriestracker import read_category

from ..models import Subscription
from ..moderation import threads as moderation
from ..subscriptions import make_subscription_aware
from ..threadtypes import trees_map
from ..viewmodels.thread import ForumThread
from .threadendpoints.list import threads_list_endpoint
from .threadendpoints.merge import threads_merge_endpoint
from .threadendpoints.patch import thread_patch_endpoint


class ViewSet(viewsets.ViewSet):
    thread = None
    TREE_ID = None

    def get_thread(self, request, pk):
        return self.thread(request, get_int_or_404(pk), read_aware=True, subscription_aware=True)

    def list(self, request):
        return threads_list_endpoint(request)

    def retrieve(self, request, pk):
        thread = self.get_thread(request, pk)
        return Response(thread.get_frontend_context())

    def partial_update(self, request, pk):
        thread = self.get_thread(request, pk)
        return thread_patch_endpoint.dispatch(request, thread.thread)

    def destroy(self, request, pk):
        thread = self.get_thread(request, pk).thread

        if thread.acl.get('can_hide') == 2:
            moderation.delete_thread(request.user, thread)
            return Response({'detail': 'ok'})
        else:
            raise PermissionDenied(_("You don't have permission to delete this thread."))


class ThreadViewSet(ViewSet):
    thread = ForumThread

    @list_route(methods=['post'])
    def merge(self, request):
        return threads_merge_endpoint(request)

    @list_route(methods=['post'])
    def read(self, request):
        if request.query_params.get('category'):
            threads_tree_id = trees_map.get_tree_id_for_root(THREADS_ROOT_NAME)

            category_id = get_int_or_404(request.query_params.get('category'))
            category = get_object_or_404(Category,
                id=category_id,
                tree_id=threads_tree_id,
            )

            allow_see_category(request.user, category)
            allow_browse_category(request.user, category)
        else:
            category = Category.objects.root_category()

        read_category(request.user, category)
        return Response({'detail': 'ok'})
