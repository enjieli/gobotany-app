from gobotany import views, handlers
import gobotany
from piston.resource import Resource
from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    ('^$', views.default_view),

    (r'^taxon/(?P<scientific_name>[^/]+)/$',
     Resource(handler=handlers.TaxonQueryHandler)),
    (r'^taxon/$',
     Resource(handler=handlers.TaxonQueryHandler)),
    (r'^taxon-count/$',
     Resource(handler=handlers.TaxonCountHandler)),
    (r'^taxon-image/$',
     Resource(handler=handlers.TaxonImageHandler)),

    (r'^piles/$',
     Resource(handler=handlers.PileListingHandler)),
    (r'^piles/(?P<name>[^/]+)$',
     Resource(handler=handlers.PileHandler)),
    (r'^pilegroups/$',
     Resource(handler=handlers.PileGroupListingHandler)),
    (r'^pilegroups/(?P<name>[^/]+)$',
     Resource(handler=handlers.PileGroupHandler)),

    (r'^pile-search/(\w+)$', views.pile_search),
    (r'^taxon-search/$', views.taxon_search),
    (r'^glossary/?$', views.glossary_index),
    (r'^canonical-images?$', views.canonical_images),
    (r'^species-lists/$', views.species_lists),

    (r'^static/(?P<path>.*)$', 'gobotany.views.static_serve',
     {'package': gobotany, 'relative_path': 'static', 'show_indexes': True}),

    (r'^admin/', include(admin.site.urls)),

    (r'^piles-pile-groups$', views.piles_pile_groups),

    # django-haystack
    (r'^search/', include('haystack.urls')),
)

if gobotany.settings.DEBUG:
    urlpatterns += patterns(
        '',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': gobotany.settings.MEDIA_ROOT, 'show_indexes': True}),

        (r'^dojo/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': gobotany.settings.DEBUG_DOJO_ROOT, 'show_indexes': True}),
    )
